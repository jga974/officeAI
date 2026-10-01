"""
Module des fournisseurs d'intelligence artificielle (Provider Pattern) pour OfficeAI.
Supporte Google Gemini, Albert (LLM Souverain de l'État), Mistral AI et le mode hors-ligne.
"""

from officeai.core.providers.base import LLMProvider
from officeai.core.providers.factory import ProviderFactory

__all__ = ["LLMProvider", "ProviderFactory"]
