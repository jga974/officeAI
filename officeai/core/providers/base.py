"""
Classe de base abstraite pour les fournisseurs d'IA (LLMProvider).
"""

from __future__ import annotations
from abc import ABC, abstractmethod
import re


class LLMProvider(ABC):
    """Interface unifiée pour tous les moteurs d'IA (Gemini, Albert, Mistral, Local)."""

    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        self.api_key = api_key
        self.model_name = model_name

    @staticmethod
    def extract_python_code(raw_text: str) -> str:
        """Extrait le code Python d'un bloc markdown ```python ... ```. Retourne vide si aucun bloc n'est présent."""
        pattern = r"```(?:python)?\s*(.*?)\s*```"
        matches = re.findall(pattern, raw_text, re.DOTALL)
        if matches:
            return max(matches, key=len).strip()
        return ""

    @abstractmethod
    def generate_plan_and_code(
        self,
        system_instruction: str,
        user_prompt: str,
        context: str = "",
        temperature: float = 0.2,
    ) -> tuple[str, str]:
        """Génère (explication, code_python) à partir de la demande utilisateur."""
        pass

    @abstractmethod
    def auto_repair_code(
        self,
        failed_code: str,
        error_message: str,
        context: str = "",
        temperature: float = 0.1,
    ) -> str:
        """Corrige un script Python ayant échoué."""
        pass
