"""Tests du confinement au répertoire et de la traçabilité des suppressions."""

from pathlib import Path
import pytest
from officeai.core.runner import ScriptRunner
from officeai.core.sandbox import analyze_code


@pytest.mark.parametrize("code", [
    "import subprocess",
    "from socket import socket",
    "eval('1+1')",
    "import os\nos.system('dir')",
    "open('C:\\\\Windows\\\\win.ini')",
    "open('../secret.txt')",
])
def test_static_analysis_rejects(code):
    assert not analyze_code(code).is_safe


def test_static_analysis_detects_deletions():
    a = analyze_code("import os\nos.remove('a.txt')\nfrom pathlib import Path\nPath('b').unlink()")
    assert a.is_safe and len(a.deletions) == 2
    assert not analyze_code("l=[1]\nl.remove(1)\n'a'.replace('a','b')").deletes_files


def test_runner_refuses_forbidden_code(tmp_path: Path):
    r = ScriptRunner.run_code("import subprocess", working_dir=tmp_path)
    assert not r.success and "refusé" in r.stderr


def test_runtime_blocks_read_outside(tmp_path: Path):
    outside = tmp_path / "outside.txt"
    outside.write_text("secret")
    work = tmp_path / "work"
    work.mkdir()
    # chemin construit dynamiquement : l'analyse statique ne le voit pas, le hook d'exécution l'arrête
    code = f"import pathlib\nprint(pathlib.Path('/'.join(['{tmp_path.as_posix()}', 'outside.txt'])).read_text())"
    r = ScriptRunner.run_code(code, working_dir=work)
    assert not r.success and "Action refusée" in r.stderr and "secret" not in r.stdout


def test_runtime_blocks_write_outside(tmp_path: Path):
    work = tmp_path / "work"
    work.mkdir()
    target = tmp_path / "escaped.txt"
    code = f"import pathlib\npathlib.Path('/'.join(['{tmp_path.as_posix()}', 'escaped.txt'])).write_text('x')"
    r = ScriptRunner.run_code(code, working_dir=work)
    assert not r.success and not target.exists()


def test_delete_blocked_without_approval(tmp_path: Path):
    f = tmp_path / "a.txt"
    f.write_text("x")
    r = ScriptRunner.run_code("from pathlib import Path\nPath('a.txt').unlink()", working_dir=tmp_path)
    assert not r.success and f.exists() and not r.deleted_files


def test_delete_allowed_and_reported(tmp_path: Path):
    f = tmp_path / "a.txt"
    f.write_text("x")
    r = ScriptRunner.run_code("from pathlib import Path\nPath('a.txt').unlink()", working_dir=tmp_path, allow_delete=True)
    assert r.success and not f.exists()
    assert [p.name for p in r.deleted_files] == ["a.txt"]


def test_overwrite_is_reported_as_modified(tmp_path: Path):
    (tmp_path / "a.txt").write_text("avant")
    r = ScriptRunner.run_code("open('a.txt','w').write('apres, plus long')", working_dir=tmp_path)
    assert r.success and [p.name for p in r.modified_files] == ["a.txt"]


def test_cannot_overwrite_by_rename_without_approval(tmp_path: Path):
    (tmp_path / "a.txt").write_text("1")
    (tmp_path / "b.txt").write_text("2")
    r = ScriptRunner.run_code("import os\nos.replace('a.txt','b.txt')", working_dir=tmp_path)
    assert not r.success and (tmp_path / "a.txt").exists()
