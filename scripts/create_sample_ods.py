"""
Générateur de fichier tableur OpenOffice / LibreOffice (.ods).
"""

from pathlib import Path
import pandas as pd


def create_sample_ods(filepath: Path):
    data = {
        "Date": ["2026-02-01", "2026-02-05", "2026-02-10", "2026-02-15", "2026-02-20"],
        "Direction_Regionale": ["Bretagne", "Nouvelle-Aquitaine", "Grand-Est", "Occitanie", "Auvergne-Rhone-Alpes"],
        "Responsable": ["Elodie Blanc", "Julien Giraud", "Claire Martin", "David Lambert", "Sarah Benali"],
        "Service": ["Formation Numerique", "Assistance Technique", "Audit Securite", "Formation Numerique", "Conseil Organisation"],
        "Nombre_Ventes": [18, 22, 9, 31, 14],
        "Prix_Unitaire_EUR": [950.0, 600.0, 2400.0, 950.0, 1800.0],
    }
    df = pd.DataFrame(data)
    df["Total_Ventes_EUR"] = df["Nombre_Ventes"] * df["Prix_Unitaire_EUR"]

    # Sauvegarde au format OpenOffice Calc .ods
    df.to_excel(filepath, engine="odf", index=False)
    print(f"Fichier OpenOffice ODS cree avec succes : {filepath}")


if __name__ == "__main__":
    create_sample_ods(Path("ventes_nationales.ods"))
