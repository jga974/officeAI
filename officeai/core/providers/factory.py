"""
Fabrique (Factory) des fournisseurs d'intelligence artificielle pour OfficeAI.
"""

from __future__ import annotations
import os
from officeai.config import Config
from officeai.core.providers.base import LLMProvider
from officeai.core.providers.gemini_provider import GeminiProvider
from officeai.core.providers.albert_provider import AlbertProvider
from officeai.core.providers.mistral_provider import MistralProvider
from officeai.core.providers.mock_provider import MockProvider


class ProviderFactory:
    """Instancie le fournisseur d'IA approprié selon la configuration ou les options passées."""

    SUPPORTED_PROVIDERS = {"gemini", "albert", "mistral", "demo", "mock"}

    @classmethod
    def create(
        cls,
        provider_name: str | None = None,
        api_key: str | None = None,
        model_name: str | None = None,
    ) -> LLMProvider:
        prov = (provider_name or os.getenv("OFFICEAI_PROVIDER", "gemini")).lower()

        if prov in ("demo", "mock"):
            return MockProvider(api_key=api_key, model_name=model_name)
        elif prov in ("albert", "etat", "dinum"):
            return AlbertProvider(api_key=api_key, model_name=model_name)
        elif prov in ("mistral", "mistralai"):
            return MistralProvider(api_key=api_key, model_name=model_name)
        elif prov == "gemini":
            return GeminiProvider(api_key=api_key, model_name=model_name)
        else:
            raise ValueError(
                f"Fournisseur d'IA inconnu : '{prov}'. "
                f"Fournisseurs supportés : {', '.join(cls.SUPPORTED_PROVIDERS)}"
            )
