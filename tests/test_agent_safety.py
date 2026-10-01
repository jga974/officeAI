"""Tests de bout en bout (fournisseur demo) : questions sur le dossier et suppression encadrée."""

from pathlib import Path
from rich.console import Console
from officeai.core.agent import OfficeAIAgent


def _agent():
    return OfficeAIAgent(provider_name="demo", console=Console(record=True, width=120))


def test_inventory_lists_all_files(tmp_path: Path):
    (tmp_path / "notes.txt").write_text("x")
    (tmp_path / "sous").mkdir()
    ctx = _agent().scan_and_inspect_directory(tmp_path)
    assert "notes.txt" in ctx and "sous/" in ctx and "INVENTAIRE" in ctx


def test_deletion_refused_by_default(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.txt").write_text("x")
    res = _agent().process_request("supprime a.txt", working_dir=tmp_path, confirm_callback=lambda e, c: True)
    assert not res.success and (tmp_path / "a.txt").exists()


def test_deletion_approved_is_reported(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.txt").write_text("x")
    agent = _agent()
    res = agent.process_request(
        "supprime a.txt", working_dir=tmp_path,
        confirm_callback=lambda e, c: True, delete_callback=lambda d: True,
    )
    assert res.success and not (tmp_path / "a.txt").exists()
    assert "SUPPRIME" in agent.console.export_text()
