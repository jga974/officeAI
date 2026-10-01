"""
Tests unitaires pour l'inspecteur Excel et CSV.
"""

from pathlib import Path
import pandas as pd
import pytest
from officeai.inspectors.excel_inspector import ExcelInspector


@pytest.fixture
def sample_xlsx(tmp_path: Path) -> Path:
    file_path = tmp_path / "test_ventes.xlsx"
    df = pd.DataFrame({
        "Date": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"],
        "Vendeur": ["Alice", "Bob", "Alice", "Charlie"],
        "Produit": ["Widget A", "Widget B", "Widget A", "Widget C"],
        "Quantite": [10, 5, 8, 12],
        "Prix_Unitaire": [15.0, 25.5, 15.0, 40.0],
    })
    df["Total"] = df["Quantite"] * df["Prix_Unitaire"]
    df.to_excel(file_path, index=False, engine="openpyxl")
    return file_path


def test_excel_inspector_xlsx(sample_xlsx: Path):
    assert ExcelInspector.can_inspect(sample_xlsx)
    data = ExcelInspector.inspect(sample_xlsx)

    assert data["file_name"] == "test_ventes.xlsx"
    assert "Sheet1" in data["sheets"]
    sheet = data["sheets"]["Sheet1"]
    assert sheet["total_rows_inspected"] == 4
    assert sheet["columns_count"] == 6

    col_names = [c["name"] for c in sheet["columns"]]
    assert "Quantite" in col_names
    assert "Total" in col_names

    # Vérification des stats
    stats = sheet["numeric_stats"]
    assert stats["Quantite"]["sum"] == 35.0

    # Vérification du prompt format
    prompt_text = ExcelInspector.format_for_prompt(sample_xlsx)
    assert "test_ventes.xlsx" in prompt_text
    assert "Quantite" in prompt_text


def test_excel_inspector_ods(tmp_path: Path):
    file_path = tmp_path / "test_ventes.ods"
    df = pd.DataFrame({
        "Region": ["Nord", "Sud"],
        "Ventes": [100, 250],
    })
    df.to_excel(file_path, engine="odf", index=False)

    assert ExcelInspector.can_inspect(file_path)
    data = ExcelInspector.inspect(file_path)
    assert data["file_name"] == "test_ventes.ods"
    assert "Sheet1" in data["sheets"]
    sheet = data["sheets"]["Sheet1"]
    assert sheet["total_rows_inspected"] == 2
    assert sheet["numeric_stats"]["Ventes"]["sum"] == 350.0
