"""Tests de la CLI (Typer) et du traitement par lot : confirmations et suppressions."""

from pathlib import Path
from rich.console import Console
from typer.testing import CliRunner

from officeai.batch.batch_processor import BatchProcessor
from officeai.cli import app
from officeai.core.agent import OfficeAIAgent

runner = CliRunner()


def test_cli_run_answers_question(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.xls").write_bytes(b"x")
    r = runner.invoke(app, ["run", "quel est le nombre de fichiers ?", "-p", "demo", "-y"])
    assert r.exit_code == 0 and "1 fichier" in r.output


def test_cli_delete_requires_confirmation_even_with_yes(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "a.txt"
    f.write_text("x")
    r = runner.invoke(app, ["run", "supprime a.txt", "-p", "demo", "-y"], input="n\n")
    assert r.exit_code != 0 and f.exists()
    r = runner.invoke(app, ["run", "supprime a.txt", "-p", "demo", "-y"], input="y\n")
    assert r.exit_code == 0 and not f.exists() and "SUPPRIME" in r.output


def test_batch_declined_confirmation_runs_nothing(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "x.txt").write_text("1")
    agent = OfficeAIAgent(provider_name="demo", console=Console(record=True))
    results = BatchProcessor(agent, Console(record=True)).process_batch(
        pattern="x.txt", prompt_template="supprime {file}", working_dir=tmp_path,
        auto_confirm=True, delete_callback=lambda d: False,
    )
    assert not results[0][1].success and (tmp_path / "x.txt").exists()
