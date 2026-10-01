"""
Conversion locale de documents Word / OpenDocument en PDF via LibreOffice (mode headless).

Aucune donnee ne quitte la machine. La conversion reste confinee au repertoire de travail
et n'ecrase jamais un PDF existant sans demande explicite.
"""

from __future__ import annotations
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

SUPPORTED_EXTENSIONS = {".docx", ".doc", ".odt"}
_WINDOWS_CANDIDATES = (
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
)


class PdfConversionError(Exception):
    """Erreur de conversion (fichier non supporte, LibreOffice absent, echec...)."""


class PdfConverter:
    TIMEOUT_SECONDS = 180

    @staticmethod
    def find_soffice() -> str | None:
        """Localise l'executable LibreOffice (variable OFFICEAI_SOFFICE, PATH, emplacements Windows)."""
        env = os.environ.get("OFFICEAI_SOFFICE")
        if env and Path(env).exists():
            return env
        for name in ("soffice", "libreoffice", "soffice.exe"):
            found = shutil.which(name)
            if found:
                return found
        for candidate in _WINDOWS_CANDIDATES:
            if Path(candidate).exists():
                return candidate
        return None

    @classmethod
    def convert(
        cls,
        source: Path,
        working_dir: Path | None = None,
        overwrite: bool = False,
    ) -> Path:
        """Convertit `source` en PDF (meme nom, meme dossier). Retourne le chemin du PDF cree."""
        base = (working_dir or Path.cwd()).resolve()
        src = Path(source)
        src = (src if src.is_absolute() else base / src).resolve()

        if src != base and base not in src.parents:
            raise PdfConversionError(f"Fichier hors du repertoire de travail : {source}")
        if not src.is_file():
            raise PdfConversionError(f"Fichier introuvable : {source}")
        if src.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise PdfConversionError(
                f"Format non supporte ({src.suffix or 'sans extension'}). Formats acceptes : "
                + ", ".join(sorted(SUPPORTED_EXTENSIONS))
            )

        dest = src.with_suffix(".pdf")
        if dest.exists() and not overwrite:
            raise PdfConversionError(f"{dest.name} existe deja (utilisez --force pour l'ecraser).")

        soffice = cls.find_soffice()
        if not soffice:
            raise PdfConversionError(
                "LibreOffice est introuvable. Installez-le (https://www.libreoffice.org) "
                "ou definissez OFFICEAI_SOFFICE avec le chemin de soffice."
            )

        # Conversion dans un dossier temporaire, puis deplacement : un echec ne laisse jamais de PDF partiel.
        with tempfile.TemporaryDirectory(prefix="officeai_pdf_") as tmp:
            tmp_path = Path(tmp)
            profile = tmp_path / "profile"
            out_dir = tmp_path / "out"
            out_dir.mkdir()
            cmd = [
                soffice,
                f"-env:UserInstallation={profile.as_uri()}",
                "--headless", "--norestore",
                "--convert-to", "pdf",
                "--outdir", str(out_dir),
                str(src),
            ]
            try:
                proc = subprocess.run(
                    cmd, capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=cls.TIMEOUT_SECONDS,
                )
            except subprocess.TimeoutExpired as exc:
                raise PdfConversionError(f"Delai depasse pendant la conversion de {src.name}.") from exc
            except OSError as exc:
                raise PdfConversionError(f"Impossible de lancer LibreOffice : {exc}") from exc

            produced = out_dir / (src.stem + ".pdf")
            if proc.returncode != 0 or not produced.exists():
                detail = (proc.stderr or proc.stdout or "").strip()
                raise PdfConversionError(f"Echec de la conversion de {src.name}. {detail}".strip())
            shutil.move(str(produced), str(dest))

        return dest
