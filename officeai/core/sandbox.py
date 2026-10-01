"""
Analyse statique du code généré par le LLM avant exécution.

Premier rempart (le second, à l'exécution, est `_guard_launcher.py`) :
- refuse le code qui tente de sortir du répertoire de travail, de lancer des
  processus, d'ouvrir le réseau ou d'évaluer du code dynamique ;
- repère les suppressions de fichiers afin d'en demander la confirmation
  explicite à l'utilisateur AVANT l'exécution.
"""

from __future__ import annotations
import ast
import re
from dataclasses import dataclass, field

FORBIDDEN_MODULES = {
    "subprocess", "ctypes", "socket", "multiprocessing", "requests", "urllib",
    "urllib3", "http", "httpx", "ftplib", "smtplib", "telnetlib", "webbrowser",
    "importlib", "pty", "asyncio.subprocess",
}
FORBIDDEN_BUILTINS = {"eval", "exec", "compile", "__import__"}
FORBIDDEN_OS_CALLS = {
    "system", "popen", "startfile", "fork", "forkpty", "kill", "killpg",
    "symlink", "link", "chroot",
}
FORBIDDEN_OS_PREFIXES = ("exec", "spawn", "posix_spawn")
# Appels qui suppriment toujours des fichiers/dossiers
DELETE_ATTRS = {"unlink", "rmdir", "rmtree", "removedirs"}

_ABSOLUTE_PATH = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\|~[\\/]?$|~[\\/])")
_PARENT_SEGMENT = re.compile(r"(?:^|[\\/])\.\.(?:[\\/]|$)")


@dataclass
class CodeAnalysis:
    violations: list[str] = field(default_factory=list)
    deletions: list[str] = field(default_factory=list)

    @property
    def is_safe(self) -> bool:
        return not self.violations

    @property
    def deletes_files(self) -> bool:
        return bool(self.deletions)


def _root_name(node: ast.AST) -> str | None:
    while isinstance(node, ast.Attribute):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def analyze_code(code: str) -> CodeAnalysis:
    """Analyse un script Python. Une erreur de syntaxe n'est pas une violation (elle sera remontée à l'exécution)."""
    result = CodeAnalysis()
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return result

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in FORBIDDEN_MODULES:
                    result.violations.append(f"import interdit : {alias.name} (ligne {node.lineno})")
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] in FORBIDDEN_MODULES:
                result.violations.append(f"import interdit : {node.module} (ligne {node.lineno})")
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in FORBIDDEN_BUILTINS:
                result.violations.append(f"appel interdit : {func.id}() (ligne {node.lineno})")
            elif isinstance(func, ast.Attribute):
                attr = func.attr
                root = _root_name(func)
                if root == "os" and (attr in FORBIDDEN_OS_CALLS or attr.startswith(FORBIDDEN_OS_PREFIXES)):
                    result.violations.append(f"appel interdit : os.{attr}() (ligne {node.lineno})")
                if attr in DELETE_ATTRS or (attr == "remove" and root == "os"):
                    result.deletions.append(f"{attr}() (ligne {node.lineno})")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            s = node.value
            if len(s) < 260 and "\n" not in s and (_ABSOLUTE_PATH.match(s) or _PARENT_SEGMENT.search(s)):
                result.violations.append(
                    f"chemin hors du répertoire de travail : {s!r} (ligne {node.lineno})"
                )

    return result
