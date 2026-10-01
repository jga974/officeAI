"""
Tests unitaires pour l'exécuteur de script Python local.
"""

from pathlib import Path
from officeai.core.runner import ScriptRunner


def test_script_runner_success(tmp_path: Path):
    code = """
import sys
print("Traitement termine")
with open("test_output.txt", "w") as f:
    f.write("OK")
"""
    result = ScriptRunner.run_code(code, working_dir=tmp_path)
    assert result.success is True
    assert "Traitement termine" in result.stdout
    assert (tmp_path / "test_output.txt").exists()
    assert any(f.name == "test_output.txt" for f in result.created_files)


def test_script_runner_error(tmp_path: Path):
    code = """
raise ValueError("Erreur simulee de calcul")
"""
    result = ScriptRunner.run_code(code, working_dir=tmp_path)
    assert result.success is False
    assert "ValueError: Erreur simulee de calcul" in result.stderr
    assert result.return_code != 0
