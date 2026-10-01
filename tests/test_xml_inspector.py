"""Tests de l'inspecteur XML et de la question « nombre d'erreurs par type »."""

from pathlib import Path
import pytest
from rich.console import Console

from officeai.core.agent import OfficeAIAgent
from officeai.inspectors.xml_inspector import XmlInspector

XML = """<?xml version="1.0" encoding="utf-8"?>
<journal>
  <erreur type="Réseau" code="E01"><message>Délai dépassé</message></erreur>
  <erreur type="Réseau" code="E01"><message>Connexion refusée</message></erreur>
  <erreur type="Base de données" code="E07"><message>Verrou</message></erreur>
  <erreur type="Authentification" code="E03"><message>Jeton expiré</message></erreur>
  <erreur type="Réseau" code="E02"><message>DNS</message></erreur>
</journal>
"""


@pytest.fixture
def toto(tmp_path: Path) -> Path:
    p = tmp_path / "toto.xml"
    p.write_text(XML, encoding="utf-8")
    return p


def test_inspect_structure(toto: Path):
    d = XmlInspector.inspect(toto)
    assert d["root_tag"] == "journal" and d["record_tag"] == "erreur"
    assert d["elements"]["erreur"]["count"] == 5
    assert d["elements"]["erreur"]["attributes"]["type"]["distinct"] == 3
    assert "message" in d["elements"]["erreur"]["children"]


def test_prompt_contains_structure_not_all_data(toto: Path):
    txt = XmlInspector.format_for_prompt(toto)
    assert "<erreur> x5" in txt and "attribut 'type'" in txt and "Réseau" in txt


def test_rejects_entity_declarations(tmp_path: Path):
    p = tmp_path / "evil.xml"
    p.write_text('<?xml version="1.0"?><!DOCTYPE a [<!ENTITY x "boom">]><a>&x;</a>', encoding="utf-8")
    with pytest.raises(ValueError, match="securite"):
        XmlInspector.inspect(p)


def test_agent_context_includes_xml(toto: Path):
    ctx = OfficeAIAgent(provider_name="demo", console=Console(record=True)).scan_and_inspect_directory(toto.parent)
    assert "FICHIER XML : toto.xml" in ctx


def test_errors_per_type_end_to_end(toto: Path, monkeypatch):
    monkeypatch.chdir(toto.parent)
    agent = OfficeAIAgent(provider_name="demo", console=Console(record=True, width=120))
    res = agent.process_request(
        "utilise le fichier toto.xml, calcule le nombre d'erreur par type d'erreur.",
        working_dir=toto.parent, confirm_callback=lambda e, c: True,
    )
    assert res.success
    assert "Réseau : 3" in res.stdout and "Base de données : 1" in res.stdout and "Total : 5" in res.stdout
    assert not res.deleted_files and not res.modified_files and not res.created_files
