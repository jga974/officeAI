"""
Exécuteur de scripts Python d'automatisation bureautique avec capture d'erreurs.

Le script est confiné au répertoire de travail (analyse statique + audit hook)
et tout changement du disque (créations, modifications, suppressions) est
constaté par comparaison d'instantanés, indépendamment de ce que déclare le code.
"""

from __future__ import annotations
import os
import sys
import subprocess
from pathlib import Path
from dataclasses import dataclass, field

from officeai.core.sandbox import analyze_code

CACHE_DIRNAME = ".officeai_cache"
LAUNCHER = Path(__file__).with_name("_guard_launcher.py")


@dataclass
class ExecutionResult:
    success: bool
    stdout: str
    stderr: str
    return_code: int
    script_path: Path
    created_files: list[Path]
    deleted_files: list[Path] = field(default_factory=list)
    modified_files: list[Path] = field(default_factory=list)


def _snapshot(root: Path) -> dict[Path, tuple[int, int]]:
    """Instantané récursif {chemin: (taille, mtime_ns)} du dossier, hors dossier technique."""
    snap: dict[Path, tuple[int, int]] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != CACHE_DIRNAME]
        for name in dirnames:
            snap[Path(dirpath) / name] = (-1, 0)
        for name in filenames:
            p = Path(dirpath) / name
            try:
                st = p.stat()
            except OSError:
                continue
            snap[p] = (st.st_size, st.st_mtime_ns)
    return snap


class ScriptRunner:
    """Exécute de manière confinée un script Python généré par l'agent."""

    @classmethod
    def run_code(
        cls,
        python_code: str,
        working_dir: Path | None = None,
        allow_delete: bool = False,
    ) -> ExecutionResult:
        cwd = (working_dir or Path.cwd()).resolve()
        cache_dir = cwd / CACHE_DIRNAME
        cache_dir.mkdir(exist_ok=True)
        tmp_dir = cache_dir / "tmp"
        tmp_dir.mkdir(exist_ok=True)

        script_file = cache_dir / "latest_task.py"
        script_file.write_text(python_code, encoding="utf-8")

        analysis = analyze_code(python_code)
        if not analysis.is_safe:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="Code refusé (sécurité) :\n- " + "\n- ".join(analysis.violations),
                return_code=126,
                script_path=script_file,
                created_files=[],
            )

        before = _snapshot(cwd)

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["OFFICEAI_ROOT"] = str(cwd)
        env["OFFICEAI_CACHE"] = str(cache_dir)
        env["OFFICEAI_ALLOW_DELETE"] = "1" if allow_delete else "0"
        # Fichiers temporaires et caches des bibliothèques restent dans le dossier de travail
        for var in ("TMPDIR", "TEMP", "TMP"):
            env[var] = str(tmp_dir)
        env["MPLCONFIGDIR"] = str(cache_dir / "mpl")
        existing_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(cwd) + (os.pathsep + existing_pythonpath if existing_pythonpath else "")

        process = subprocess.run(
            [sys.executable, str(LAUNCHER), str(script_file)],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )

        after = _snapshot(cwd)
        created = sorted(p for p in after if p not in before)
        deleted = sorted(p for p in before if p not in after)
        modified = sorted(p for p in after if p in before and before[p] != after[p])

        return ExecutionResult(
            success=(process.returncode == 0),
            stdout=process.stdout,
            stderr=process.stderr,
            return_code=process.returncode,
            script_path=script_file,
            created_files=created,
            deleted_files=deleted,
            modified_files=modified,
        )
