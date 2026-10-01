"""
Configuration et gestion des clés d'environnement pour OfficeAI.
"""

from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables du fichier .env du répertoire courant ou parent
load_dotenv(override=False)

DEFAULT_MODEL = "gemini-2.5-flash"


class Config:
    @staticmethod
    def get_api_key() -> str | None:
        """Récupère la clé d'API Gemini depuis l'environnement ou .env."""
        return os.getenv("GEMINI_API_KEY")

    @staticmethod
    def get_model() -> str:
        """Récupère le nom du modèle Gemini à utiliser."""
        return os.getenv("GEMINI_MODEL", DEFAULT_MODEL)

    @staticmethod
    def is_configured() -> bool:
        """Vérifie si la clé d'API est présente et non vide."""
        key = Config.get_api_key()
        return bool(key and key.strip() and key != "votre_cle_api_gemini_ici")

    @staticmethod
    def set_api_key(api_key: str, env_file_path: Path | None = None) -> Path:
        """Sauvegarde la clé d'API dans un fichier .env."""
        target_file = env_file_path or (Path.cwd() / ".env")
        lines = []
        key_found = False

        if target_file.exists():
            for line in target_file.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("GEMINI_API_KEY="):
                    lines.append(f"GEMINI_API_KEY={api_key.strip()}")
                    key_found = True
                else:
                    lines.append(line)

        if not key_found:
            lines.append(f"GEMINI_API_KEY={api_key.strip()}")

        target_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.environ["GEMINI_API_KEY"] = api_key.strip()
        return target_file
