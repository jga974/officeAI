"""
Inspecteur de fichiers tableurs (Excel .xls, .xlsx et CSV) pour OfficeAI.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any
import pandas as pd


class ExcelInspector:
    """Analyse la structure, les feuilles, colonnes et échantillons de fichiers Excel."""

    SUPPORTED_EXTENSIONS = {".xls", ".xlsx", ".xlsm", ".csv", ".ods"}

    @classmethod
    def can_inspect(cls, file_path: str | Path) -> bool:
        path = Path(file_path)
        return path.suffix.lower() in cls.SUPPORTED_EXTENSIONS

    @classmethod
    def inspect(cls, file_path: str | Path, max_sample_rows: int = 5) -> dict[str, Any]:
        """
        Inspecte le fichier et retourne une structure détaillée des métadonnées.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Fichier introuvable : {path}")

        ext = path.suffix.lower()
        sheets_data = {}

        if ext == ".csv":
            # Traitement CSV
            df = pd.read_csv(path, nrows=1000)
            sheets_data["Sheet1"] = cls._extract_df_info(df, max_sample_rows)
        elif ext == ".ods":
            # OpenDocument Spreadsheet (.ods) via odf
            xls = pd.ExcelFile(path, engine="odf")
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name, nrows=1000)
                sheets_data[sheet_name] = cls._extract_df_info(df, max_sample_rows)
        elif ext == ".xls":
            # Excel 97-2003 (.xls) via xlrd
            xls = pd.ExcelFile(path, engine="xlrd")
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name, nrows=1000)
                sheets_data[sheet_name] = cls._extract_df_info(df, max_sample_rows)
        else:
            # Excel moderne (.xlsx, .xlsm) via openpyxl
            xls = pd.ExcelFile(path, engine="openpyxl")
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name, nrows=1000)
                sheets_data[sheet_name] = cls._extract_df_info(df, max_sample_rows)

        return {
            "file_name": path.name,
            "file_path": str(path.resolve()),
            "extension": ext,
            "size_kb": round(path.stat().st_size / 1024, 2),
            "sheets": sheets_data,
        }

    @classmethod
    def _extract_df_info(cls, df: pd.DataFrame, max_sample_rows: int) -> dict[str, Any]:
        """Extrait les informations essentielles d'un DataFrame."""
        columns_info = []
        for col in df.columns:
            dtype_str = str(df[col].dtype)
            null_count = int(df[col].isnull().sum())
            sample_val = None
            non_null = df[col].dropna()
            if not non_null.empty:
                sample_val = str(non_null.iloc[0])
                if len(sample_val) > 40:
                    sample_val = sample_val[:37] + "..."

            columns_info.append({
                "name": str(col),
                "type": dtype_str,
                "nulls": null_count,
                "example": sample_val,
            })

        # Calcul de statistiques numériques simples si applicable
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        stats = {}
        for col in numeric_cols:
            series = df[col].dropna()
            if not series.empty:
                stats[str(col)] = {
                    "count": int(series.count()),
                    "sum": float(round(series.sum(), 2)),
                    "min": float(round(series.min(), 2)),
                    "max": float(round(series.max(), 2)),
                    "mean": float(round(series.mean(), 2)),
                }

        # Échantillon des premières lignes en markdown
        sample_df = df.head(max_sample_rows).fillna("")
        try:
            sample_markdown = sample_df.to_markdown(index=False) if not sample_df.empty else "*(Feuille vide)*"
        except Exception:
            # Fallback simple si tabulate n'est pas disponible
            sample_markdown = sample_df.to_string(index=False) if not sample_df.empty else "*(Feuille vide)*"

        return {
            "total_rows_inspected": len(df),
            "columns_count": len(df.columns),
            "columns": columns_info,
            "sample_markdown": sample_markdown,
            "numeric_stats": stats,
        }

    @classmethod
    def format_for_prompt(cls, file_path: str | Path) -> str:
        """
        Formate les métadonnées sous forme de texte optimisé pour le prompt de Gemini.
        """
        data = cls.inspect(file_path)
        lines = [
            f"--- FICHIER TABLEUR : {data['file_name']} ({data['extension']}, {data['size_kb']} Ko) ---",
            f"Chemin absolu : {data['file_path']}",
            f"Nombre de feuilles : {len(data['sheets'])}",
        ]

        for sheet_name, sinfo in data["sheets"].items():
            lines.append(f"\n[Feuille: '{sheet_name}']")
            lines.append(f"- Lignes analysées : {sinfo['total_rows_inspected']}, Colonnes : {sinfo['columns_count']}")
            lines.append("- Colonnes détectées :")
            for col in sinfo["columns"]:
                lines.append(f"  * '{col['name']}' (type: {col['type']}, exemple: {col['example']})")

            if sinfo["numeric_stats"]:
                lines.append("- Statistiques rapides des colonnes numériques :")
                for col_name, st in sinfo["numeric_stats"].items():
                    lines.append(f"  * {col_name} : somme={st['sum']}, moyenne={st['mean']}, min={st['min']}, max={st['max']}")

            lines.append("- Échantillon des premières lignes :")
            lines.append(sinfo["sample_markdown"])

        return "\n".join(lines)
