"""
Exécuteur de scripts Python d'automatisation bureautique avec capture d'erreurs.
"""

from __future__ import annotations
import os
import sys
import subprocess
import tempfile
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ExecutionResult:
    success: bool
    stdout: str
    stderr: str
    return_code: int
    script_path: Path
    created_files: list[Path]


class ScriptRunner:
    """Exécute de manière isolée un script Python généré par l'agent."""

    @classmethod
    def run_code(cls, python_code: str, working_dir: Path | None = None) -> ExecutionResult:
        cwd = working_dir or Path.cwd()
        cache_dir = cwd / ".officeai_cache"
        cache_dir.mkdir(exist_ok=True)

        script_file = cache_dir / "latest_task.py"
        script_file.write_text(python_code, encoding="utf-8")

        # Snapshot des fichiers avant exécution
        files_before = set(cwd.glob("*"))

        # Exécuter avec l'interpréteur Python actuel (.venv)
        python_exec = sys.executable

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        # S'assurer que le répertoire de travail est dans PYTHONPATH
        existing_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(cwd) + (os.pathsep + existing_pythonpath if existing_pythonpath else "")

        process = subprocess.run(
            [python_exec, str(script_file)],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )

        files_after = set(cwd.glob("*"))
        created_files = [f for f in (files_after - files_before) if f.name != ".officeai_cache"]

        return ExecutionResult(
            success=(process.returncode == 0),
            stdout=process.stdout,
            stderr=process.stderr,
            return_code=process.returncode,
            script_path=script_file,
            created_files=created_files,
        )
