"""
Publipostage local : un document Word par ligne d'un fichier de donnees (Excel, ODS, CSV),
a partir d'un modele .docx contenant des variables {{ variable }} (syntaxe docxtpl/Jinja2).

100 % local, sans LLM : aucune donnee ne quitte la machine. Les fichiers sont crees dans un
dossier du repertoire de travail et aucun fichier existant n'est ecrase sans demande explicite.
"""

from __future__ import annotations
import math
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Callable

import pandas as pd
from docxtpl import DocxTemplate

DATA_EXTENSIONS = {".xls", ".xlsx", ".xlsm", ".ods", ".csv"}
_FORBIDDEN_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


class MailingError(Exception):
    """Erreur bloquante (fichier invalide, variable manquante, fichier existant...)."""


@dataclass
class MailingResult:
    generated: list[Path] = field(default_factory=list)
    overwritten: list[Path] = field(default_factory=list)
    pdfs: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    output_dir: Path | None = None


def slugify(name: str) -> str:
    """'Date de naissance' -> 'date_de_naissance' (nom de variable de modele valide)."""
    text = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^0-9a-zA-Z]+", "_", text).strip("_").lower()
    if not text:
        text = "colonne"
    return "_" + text if text[0].isdigit() else text


def _format_value(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        if math.isnan(v):
            return ""
        return str(int(v)) if v.is_integer() else str(v)
    if isinstance(v, (pd.Timestamp, datetime)):
        if pd.isna(v):
            return ""
        return v.strftime("%d/%m/%Y") if (v.hour, v.minute, v.second) == (0, 0, 0) else v.strftime("%d/%m/%Y %H:%M")
    if isinstance(v, date):
        return v.strftime("%d/%m/%Y")
    return str(v).strip()


class MailingEngine:
    def __init__(self, working_dir: Path | None = None):
        self.base = (working_dir or Path.cwd()).resolve()

    # -- chemins ---------------------------------------------------------
    def _inside(self, path: Path, label: str) -> Path:
        p = Path(path)
        p = (p if p.is_absolute() else self.base / p).resolve()
        if p != self.base and self.base not in p.parents:
            raise MailingError(f"{label} hors du repertoire de travail : {path}")
        return p

    # -- donnees ---------------------------------------------------------
    @staticmethod
    def _detect_delimiter(path: Path, encoding: str) -> str:
        """Separateur le plus frequent dans l'en-tete (le sniffer de pandas se trompe sur 1 colonne)."""
        with open(path, encoding=encoding, newline="") as f:
            header = f.readline()
        counts = {d: header.count(d) for d in (";", "\t", "|", ",")}
        best = max(counts, key=counts.get)
        return best if counts[best] else ","

    def load_records(self, data_file: Path, sheet: str | None = None) -> tuple[list[str], list[dict[str, str]]]:
        """Retourne (colonnes d'origine, lignes) avec toutes les valeurs en texte propre."""
        path = self._inside(data_file, "Fichier de donnees")
        if not path.is_file():
            raise MailingError(f"Fichier de donnees introuvable : {data_file}")
        ext = path.suffix.lower()
        if ext not in DATA_EXTENSIONS:
            raise MailingError(f"Format de donnees non supporte ({ext}). Acceptes : {', '.join(sorted(DATA_EXTENSIONS))}")
        try:
            if ext == ".csv":
                df = None
                for enc in ("utf-8-sig", "cp1252"):
                    try:
                        df = pd.read_csv(path, sep=self._detect_delimiter(path, enc), encoding=enc)
                        break
                    except UnicodeDecodeError:
                        continue
                if df is None:
                    raise MailingError("Encodage du CSV illisible (UTF-8 ou cp1252 attendus).")
            else:
                engine = {".xls": "xlrd", ".ods": "odf"}.get(ext, "openpyxl")
                df = pd.read_excel(path, engine=engine, sheet_name=sheet if sheet else 0)
        except MailingError:
            raise
        except Exception as exc:
            raise MailingError(f"Lecture impossible de {path.name} : {exc}") from exc

        columns = [str(c).strip() for c in df.columns]
        slugs = [slugify(c) for c in columns]
        if len(set(slugs)) != len(slugs):
            raise MailingError("Deux colonnes donnent le meme nom de variable : " + ", ".join(columns))
        df.columns = columns
        records = []
        for _, row in df.iterrows():
            rec = {c: _format_value(row[c]) for c in columns}
            if any(rec.values()):  # ignore les lignes entierement vides
                records.append(rec)
        if not records:
            raise MailingError(f"Aucune ligne de donnees dans {path.name}.")
        return columns, records

    # -- modele ----------------------------------------------------------
    def template_variables(self, template: Path) -> set[str]:
        path = self._inside(template, "Modele")
        if not path.is_file():
            raise MailingError(f"Modele introuvable : {template}")
        if path.suffix.lower() != ".docx":
            raise MailingError("Le modele doit etre un fichier Word .docx.")
        try:
            variables = DocxTemplate(str(path)).get_undeclared_template_variables()
        except Exception as exc:
            raise MailingError(f"Modele illisible ou syntaxe {{{{ }}}} invalide : {exc}") from exc
        if not variables:
            raise MailingError("Le modele ne contient aucune variable {{ ... }} : rien a personnaliser.")
        return set(variables)

    # -- generation ------------------------------------------------------
    @staticmethod
    def _filename(pattern: str, context: dict[str, str], index: int, stem: str) -> str:
        class _Safe(dict):
            def __missing__(self, key):
                raise MailingError(f"Variable inconnue dans le motif de nom de fichier : {{{key}}}")

        values = _Safe(context)
        values.update(n=index, template_stem=stem)
        try:
            name = pattern.format_map(values)
        except (ValueError, IndexError) as exc:
            raise MailingError(f"Motif de nom de fichier invalide ({exc}).") from exc
        name = _FORBIDDEN_FILENAME_CHARS.sub("_", name).strip(" .")
        if not name.lower().endswith(".docx"):
            name += ".docx"
        return name[:150] if len(name) > 150 else name

    def plan(
        self,
        template: Path,
        data_file: Path,
        output_dir: Path | None = None,
        name_pattern: str | None = None,
        sheet: str | None = None,
    ) -> tuple[Path, list[tuple[dict[str, str], Path]]]:
        """Valide tout (variables, noms de fichiers) et retourne (dossier, [(contexte, chemin de sortie)])."""
        tpl = self._inside(template, "Modele")
        variables = self.template_variables(tpl)
        columns, records = self.load_records(data_file, sheet)

        by_slug = {slugify(c): c for c in columns}
        missing = sorted(v for v in variables if v not in by_slug and v not in columns and v != "row")
        if missing:
            raise MailingError(
                "Variable(s) du modele absente(s) des donnees : " + ", ".join(missing)
                + "\nVariables disponibles : " + ", ".join(sorted(by_slug))
            )

        out_dir = self._inside(output_dir if output_dir else Path(f"mailing_{tpl.stem}"), "Dossier de sortie")
        pattern = name_pattern or "{template_stem}_{n:03d}.docx"

        planned: list[tuple[dict[str, str], Path]] = []
        used: dict[str, int] = {}
        for i, rec in enumerate(records, start=1):
            context = {slugify(c): rec[c] for c in columns}
            name = self._filename(pattern, context, i, tpl.stem)
            key = name.lower()
            if key in used:  # homonymes : suffixe numerique
                used[key] += 1
                name = f"{Path(name).stem}_{used[key]}.docx"
            else:
                used[key] = 1
            planned.append((context, out_dir / name))
        return out_dir, planned

    def run(
        self,
        template: Path,
        data_file: Path,
        output_dir: Path | None = None,
        name_pattern: str | None = None,
        sheet: str | None = None,
        overwrite: bool = False,
        to_pdf: bool = False,
        progress: Callable[[int, int], None] | None = None,
    ) -> MailingResult:
        tpl = self._inside(template, "Modele")
        out_dir, planned = self.plan(template, data_file, output_dir, name_pattern, sheet)

        existing = [p for _, p in planned if p.exists()]
        if existing and not overwrite:
            shown = ", ".join(p.name for p in existing[:5]) + (" ..." if len(existing) > 5 else "")
            raise MailingError(
                f"{len(existing)} fichier(s) existent deja ({shown}). Rien n'a ete genere ; "
                "utilisez --force pour ecraser, ou changez le dossier de sortie."
            )

        result = MailingResult(output_dir=out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        converter = None
        if to_pdf:
            from officeai.converters.pdf_converter import PdfConverter
            if PdfConverter.find_soffice() is None:
                raise MailingError("Option --pdf : LibreOffice est introuvable (voir 'officeai pdf').")
            converter = PdfConverter

        for i, (context, dest) in enumerate(planned, start=1):
            try:
                doc = DocxTemplate(str(tpl))
                doc.render({**context, "row": context}, autoescape=True)
                was_there = dest.exists()
                doc.save(str(dest))
                result.generated.append(dest)
                if was_there:
                    result.overwritten.append(dest)
                if converter:
                    result.pdfs.append(converter.convert(dest, working_dir=self.base, overwrite=True))
            except Exception as exc:  # une ligne en erreur n'arrete pas le lot
                result.errors.append(f"{dest.name} : {exc}")
            if progress:
                progress(i, len(planned))
        return result
