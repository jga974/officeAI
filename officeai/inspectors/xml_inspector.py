"""
Inspecteur de fichiers XML : resume la structure (racine, elements repetes, attributs,
sous-elements) pour guider le LLM sans lui envoyer les donnees completes.
"""

from __future__ import annotations
from collections import Counter, defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

MAX_BYTES = 50 * 1024 * 1024
MAX_SAMPLE_CHARS = 60
MAX_VALUES_SHOWN = 6


class XmlInspector:
    EXTENSIONS = {".xml"}

    @classmethod
    def can_inspect(cls, file_path: str | Path) -> bool:
        return Path(file_path).suffix.lower() in cls.EXTENSIONS

    @staticmethod
    def _parse(path: Path) -> ET.Element:
        if path.stat().st_size > MAX_BYTES:
            raise ValueError(f"fichier XML trop volumineux (> {MAX_BYTES // (1024 * 1024)} Mo)")
        raw = path.read_bytes()
        # Protection contre les entites malveillantes (billion laughs, XXE)
        head = raw[:4096].upper()
        if b"<!ENTITY" in head or (b"<!DOCTYPE" in head and b"[" in head):
            raise ValueError("declaration DOCTYPE/ENTITY refusee pour des raisons de securite")
        return ET.fromstring(raw)

    @classmethod
    def inspect(cls, file_path: str | Path) -> dict:
        path = Path(file_path)
        root = cls._parse(path)

        counts: Counter = Counter()
        attrs: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
        children: dict[str, set[str]] = defaultdict(set)
        for el in root.iter():
            counts[el.tag] += 1
            for k, v in el.attrib.items():
                attrs[el.tag][k][v] += 1
            for c in el:
                children[el.tag].add(c.tag)

        elements = {}
        for tag, n in counts.items():
            elements[tag] = {
                "count": n,
                "attributes": {
                    k: {"distinct": len(vc), "top_values": [v for v, _ in vc.most_common(MAX_VALUES_SHOWN)]}
                    for k, vc in attrs[tag].items()
                },
                "children": sorted(children[tag]),
            }

        # Element "enregistrement" principal : le plus repete (hors racine)
        repeated = [(t, n) for t, n in counts.items() if t != root.tag and n > 1]
        record_tag = max(repeated, key=lambda x: x[1])[0] if repeated else None

        sample = ET.tostring(next(root.iter(record_tag)) if record_tag else root, encoding="unicode")
        return {
            "file_name": path.name,
            "file_path": str(path.resolve()),
            "size_kb": round(path.stat().st_size / 1024, 1),
            "root_tag": root.tag,
            "record_tag": record_tag,
            "elements": elements,
            "sample": sample[:600].strip(),
        }

    @classmethod
    def format_for_prompt(cls, file_path: str | Path) -> str:
        d = cls.inspect(file_path)
        lines = [
            f"--- FICHIER XML : {d['file_name']} ({d['size_kb']} Ko) ---",
            f"Chemin absolu : {d['file_path']}",
            f"Element racine : <{d['root_tag']}>",
            f"Element repete principal (enregistrement) : <{d['record_tag']}>" if d["record_tag"]
            else "Aucun element repete detecte.",
            "Elements :",
        ]
        for tag, info in d["elements"].items():
            line = f"  * <{tag}> x{info['count']}"
            if info["children"]:
                line += f", sous-elements : {', '.join(info['children'])}"
            lines.append(line)
            for k, a in info["attributes"].items():
                vals = ", ".join(repr(v[:MAX_SAMPLE_CHARS]) for v in a["top_values"])
                lines.append(f"      attribut '{k}' ({a['distinct']} valeur(s) distincte(s)) ex: {vals}")
        lines.append("Extrait du premier enregistrement :")
        lines.append(d["sample"])
        lines.append("(Lecture en Python : xml.etree.ElementTree, ET.parse('fichier.xml').getroot())")
        return "\n".join(lines)
