"""
Client d'intégration officiel Google GenAI pour Gemini.
"""

from __future__ import annotations
import re
from google import genai
from google.genai import types
from officeai.config import Config


class GeminiClient:
    """Wrapper pour les interactions avec l'API Google Gemini via google-genai."""

    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        self.api_key = api_key or Config.get_api_key()
        if not self.api_key:
            raise ValueError(
                "Clé d'API Gemini non trouvée. Veuillez renseigner GEMINI_API_KEY dans votre environnement "
                "ou dans un fichier .env."
            )
        self.model_name = model_name or Config.get_model()
        self.client = genai.Client(api_key=self.api_key)

    @staticmethod
    def extract_python_code(raw_text: str) -> str:
        """Extrait le code Python des balises markdown si présentes."""
        pattern = r"```(?:python)?\s*(.*?)\s*```"
        matches = re.findall(pattern, raw_text, re.DOTALL)
        if matches:
            # Retourne le bloc le plus long ou le premier
            return max(matches, key=len).strip()
        return raw_text.strip()

    def generate_plan_and_code(
        self,
        system_instruction: str,
        user_prompt: str,
        context: str = "",
        temperature: float = 0.2,
    ) -> tuple[str, str]:
        """
        Génère une explication textuelle ainsi que le code Python d'exécution.
        Retourne (explication, code_python).
        """
        full_prompt = (
            f"CONTEXTE DES FICHIERS :\n{context}\n\n"
            f"DEMANDE UTILISATEUR :\n{user_prompt}\n\n"
            "INSTRUCTIONS DE SORTIE :\n"
            "Fournis une brève explication de la démarche, puis obligatoirement "
            "le code Python complet et autonome dans un bloc ```python ... ```."
        )

        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction,
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=full_prompt,
            config=config,
        )

        raw_response = response.text or ""
        code = self.extract_python_code(raw_response)

        # L'explication correspond à la réponse sans le bloc de code
        explanation = re.sub(r"```(?:python)?\s*.*?\s*```", "", raw_response, flags=re.DOTALL).strip()
        if not explanation:
            explanation = "Génération du script de traitement bureautique..."

        return explanation, code

    def auto_repair_code(
        self,
        failed_code: str,
        error_message: str,
        context: str = "",
        temperature: float = 0.1,
    ) -> str:
        """
        Demande à Gemini de corriger un script Python ayant rencontré une exception.
        """
        prompt = (
            f"Le code Python suivant a généré une erreur lors de son exécution :\n\n"
            f"```python\n{failed_code}\n```\n\n"
            f"TRACEBACK / ERREUR :\n{error_message}\n\n"
            f"CONTEXTE DES FICHIERS :\n{context}\n\n"
            "Corrige le code pour résoudre cette erreur. Retourne UNIQUEMENT le bloc ```python ... ``` corrigé."
        )

        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=(
                "Tu es un expert en débogage de scripts Python d'automatisation bureautique "
                "(pandas, openpyxl, xlrd, python-docx, docxtpl). Corrige le code fourni."
            ),
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config,
        )

        return self.extract_python_code(response.text or "")
