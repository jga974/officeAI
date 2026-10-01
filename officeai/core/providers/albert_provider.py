"""
Fournisseur pour le LLM Souverain de l'État (Albert / DINUM / Plateforme IA État).
Compatible avec l'API standard souveraine (OpenAI-compatible) hébergée par l'État français.
"""

from __future__ import annotations
import os
import re
import httpx
from officeai.core.providers.base import LLMProvider

DEFAULT_ALBERT_URL = "https://albert.api.etalab.gouv.fr/v1"
DEFAULT_ALBERT_MODEL = "albert-large"


class AlbertProvider(LLMProvider):
    """
    Client pour l'API souveraine Albert de la DINUM (Direction Interministérielle du Numérique).
    Permet un traitement souverain respectant le cadre de confiance de l'administration française.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
    ):
        key = api_key or os.getenv("ALBERT_API_KEY") or os.getenv("ETAT_LLM_API_KEY")
        if not key:
            raise ValueError(
                "Clé d'API Albert (LLM Souverain) non trouvée. "
                "Définissez ALBERT_API_KEY ou passez-la avec --api-key."
            )
        super().__init__(api_key=key, model_name=model_name or os.getenv("ALBERT_MODEL", DEFAULT_ALBERT_MODEL))
        self.base_url = base_url or os.getenv("ALBERT_API_URL", DEFAULT_ALBERT_URL).rstrip("/")

    def generate_plan_and_code(
        self,
        system_instruction: str,
        user_prompt: str,
        context: str = "",
        temperature: float = 0.2,
    ) -> tuple[str, str]:
        messages = [
            {"role": "system", "content": system_instruction},
            {
                "role": "user",
                "content": (
                    f"CONTEXTE DES FICHIERS LOCAUX :\n{context}\n\n"
                    f"DEMANDE UTILISATEUR :\n{user_prompt}\n\n"
                    "DIRECTIVES :\n"
                    "- Si c'est une question generale (culture, meteo, cours financier, conversation, etc.), "
                    "reponds directement en texte clair sans bloc de code Python.\n"
                    "- Si c'est une instruction traitant des fichiers locaux ou demandant de creer un document, "
                    "explique brievement puis fournis le code Python complet dans un bloc ```python ... ```."
                ),
            },
        ]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
        }

        with httpx.Client(timeout=60.0) as client:
            resp = client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        raw_response = data["choices"][0]["message"]["content"]
        code = self.extract_python_code(raw_response)
        explanation = re.sub(r"```(?:python)?\s*.*?\s*```", "", raw_response, flags=re.DOTALL).strip()
        if not explanation:
            explanation = "Génération du traitement bureautique avec le LLM Souverain Albert..."

        return explanation, code

    def auto_repair_code(
        self,
        failed_code: str,
        error_message: str,
        context: str = "",
        temperature: float = 0.1,
    ) -> str:
        messages = [
            {
                "role": "system",
                "content": "Tu es un expert en débogage de scripts Python bureautiques (pandas, python-docx, odf). Corrige le code.",
            },
            {
                "role": "user",
                "content": (
                    f"Le code Python suivant a échoué :\n```python\n{failed_code}\n```\n\n"
                    f"TRACEBACK / ERREUR :\n{error_message}\n\n"
                    f"CONTEXTE :\n{context}\n\n"
                    "Corrige l'erreur et retourne UNIQUEMENT le bloc ```python ... ``` corrigé."
                ),
            },
        ]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
        }

        with httpx.Client(timeout=60.0) as client:
            resp = client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        raw_response = data["choices"][0]["message"]["content"]
        return self.extract_python_code(raw_response)
