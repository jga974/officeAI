"""
Tests unitaires pour la fabrique de fournisseurs Multi-LLM et le MockProvider.
"""

from officeai.core.providers.factory import ProviderFactory
from officeai.core.providers.mock_provider import MockProvider


def test_provider_factory_demo():
    provider = ProviderFactory.create(provider_name="demo")
    assert isinstance(provider, MockProvider)

    explanation, code = provider.generate_plan_and_code(
        system_instruction="Test system",
        user_prompt="analyse f1.xls et genere rapport_ventes.docx",
    )
    assert len(explanation) > 0
    assert "import pandas as pd" in code
    assert "DocxStyler" in code
