"""
Fournisseur Google Gemini via le SDK officiel google-genai.
"""

from __future__ import annotations
import re
from google import genai
from google.genai import types
from officeai.config import Config
from officeai.core.providers.base import LLMProvider


class GeminiProvider(LLMProvider):
    """Implémentation du fournisseur Google Gemini."""

    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        key = api_key or Config.get_api_key()
        if not key:
            raise ValueError(
                "Clé d'API Gemini non trouvée. Renseignez GEMINI_API_KEY ou utilisez "
                "'officeai config --api-key <VOTRE_CLE>'."
            )
        super().__init__(api_key=key, model_name=model_name or Config.get_model())
        self.client = genai.Client(api_key=self.api_key)

    def generate_plan_and_code(
        self,
        system_instruction: str,
        user_prompt: str,
        context: str = "",
        temperature: float = 0.2,
    ) -> tuple[str, str]:
        full_prompt = (
            f"CONTEXTE DES FICHIERS LOCAUX :\n{context}\n\n"
            f"DEMANDE UTILISATEUR :\n{user_prompt}\n\n"
            "DIRECTIVES DE REPONSE :\n"
            "- Si la demande concerne une question generale (culture, meteo, cours financier/devises, conversation, aide, etc.) : "
            "reponds directement et clairement en texte naturel SANS aucun bloc de code Python.\n"
            "- Si la demande implique de manipuler, calculer ou analyser des fichiers locaux ou de generer un document : "
            "fournis une breve explication puis obligatoirement le code Python complet et autonome dans un bloc ```python ... ```."
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
        explanation = re.sub(r"```(?:python)?\s*.*?\s*```", "", raw_response, flags=re.DOTALL).strip()
        if not explanation:
            explanation = "Génération du traitement bureautique avec Google Gemini..."

        return explanation, code

    def auto_repair_code(
        self,
        failed_code: str,
        error_message: str,
        context: str = "",
        temperature: float = 0.1,
    ) -> str:
        prompt = (
            f"Le code Python suivant a généré une erreur :\n\n"
            f"```python\n{failed_code}\n```\n\n"
            f"TRACEBACK / ERREUR :\n{error_message}\n\n"
            f"CONTEXTE :\n{context}\n\n"
            "Corrige le code et retourne UNIQUEMENT le bloc ```python ... ``` corrigé."
        )

        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=(
                "Tu es un expert en correction de scripts Python d'automatisation bureautique. Corrige le code fourni."
            ),
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config,
        )

        return self.extract_python_code(response.text or "")
