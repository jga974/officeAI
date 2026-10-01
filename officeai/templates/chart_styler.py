"""
Générateur de graphiques statistiques harmonisés avec la charte graphique pour OfficeAI.
"""

from __future__ import annotations
from pathlib import Path
import matplotlib
matplotlib.use("Agg")  # Mode sans interface graphique pour Windows CLI
import matplotlib.pyplot as plt
import pandas as pd


class ChartStyler:
    """Crée des visualisations graphiques cohérentes avec la charte d'entreprise."""

    # Palette corporate moderne
    COLORS = ["#1F497D", "#2E75B6", "#5B9BD5", "#ED7D31", "#A5A5A5", "#70AD47"]

    @classmethod
    def create_bar_chart(
        cls,
        df: pd.DataFrame,
        x_col: str,
        y_col: str,
        title: str,
        output_path: str | Path,
        xlabel: str | None = None,
        ylabel: str | None = None,
    ) -> Path:
        """Génère un graphique à barres verticales stylisé."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        fig, ax = plt.subplots(figsize=(8, 4.5), dpi=200)
        bars = ax.bar(df[x_col].astype(str), df[y_col], color=cls.COLORS[0], width=0.55, edgecolor="none")

        # Titre et labels
        ax.set_title(title, fontsize=14, fontweight="bold", color="#1F497D", pad=15)
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=11, fontweight="medium", color="#333333")
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=11, fontweight="medium", color="#333333")

        # Style minimaliste et aéré
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#CCCCCC")
        ax.spines["bottom"].set_color("#CCCCCC")
        ax.yaxis.grid(True, linestyle="--", alpha=0.5, color="#CCCCCC")
        ax.set_axisbelow(True)

        # Ajout des étiquettes de valeur au-dessus des barres
        for bar in bars:
            height = bar.get_height()
            ax.annotate(
                f"{height:,.0f}".replace(",", " "),
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
                color="#1F497D",
            )

        plt.xticks(rotation=20, ha="right", fontsize=10)
        plt.tight_layout()
        plt.savefig(str(out), format="png")
        plt.close(fig)
        return out
