"""
Lanceur sécurisé : exécute un script généré après avoir installé un audit hook
qui confine le processus au répertoire de travail.

Usage : python _guard_launcher.py <script.py>
Variables : OFFICEAI_ROOT (dossier autorisé), OFFICEAI_ALLOW_DELETE ("1" si la
suppression a été explicitement approuvée), OFFICEAI_CACHE (dossier technique).

Garde-fou contre les erreurs et dérives du LLM, pas une machine virtuelle :
l'isolation forte (conteneur, utilisateur dédié) reste hors périmètre.
"""

import os
import sys
import runpy
import sysconfig
import threading

ROOT = os.path.realpath(os.environ["OFFICEAI_ROOT"])
CACHE = os.path.realpath(os.environ.get("OFFICEAI_CACHE", os.path.join(ROOT, ".officeai_cache")))
ALLOW_DELETE = os.environ.get("OFFICEAI_ALLOW_DELETE") == "1"

_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC


def _norm(path: str) -> str:
    return os.path.normcase(os.path.realpath(path))


def _under(path: str, base: str) -> bool:
    return path == base or path.startswith(base.rstrip(os.sep) + os.sep)


ROOT_N = _norm(ROOT)
CACHE_N = _norm(CACHE)

_READ_ROOTS = {ROOT_N}
for _p in (sys.prefix, sys.base_prefix, sys.exec_prefix, sys.base_exec_prefix, CACHE):
    _READ_ROOTS.add(_norm(_p))
for _k in ("stdlib", "platstdlib", "purelib", "platlib"):
    _v = sysconfig.get_paths().get(_k)
    if _v:
        _READ_ROOTS.add(_norm(_v))
for _p in sys.path:
    if _p and os.path.isdir(_p):
        _READ_ROOTS.add(_norm(_p))
for _p in (os.environ.get("WINDIR"), "/usr/share/zoneinfo", "/usr/share/fonts"):
    if _p and os.path.isdir(_p):
        _READ_ROOTS.add(_norm(_p))
_READ_FILES = {_norm(p) for p in (os.devnull, "/dev/urandom", "/dev/random", "/dev/zero")}

_local = threading.local()


def _to_path(p):
    if p is None:
        return os.getcwd()
    if isinstance(p, int):
        return None  # descripteur déjà ouvert
    try:
        return os.fsdecode(p)
    except TypeError:
        return None


def _deny(msg: str):
    raise PermissionError(f"[OfficeAI] Action refusée : {msg}")


def _check_inside(path, action: str):
    if path is None:
        return None
    n = _norm(path)
    if not _under(n, ROOT_N):
        _deny(f"{action} en dehors du répertoire de travail ({path})")
    return n


def _check_readable(path):
    if path is None:
        return
    n = _norm(path)
    if n in _READ_FILES or any(_under(n, r) for r in _READ_ROOTS):
        return
    _deny(f"lecture en dehors du répertoire de travail ({path})")


def _check_delete(path, what: str):
    n = _check_inside(path, "suppression")
    if n is not None and _under(n, CACHE_N):
        return
    if not ALLOW_DELETE:
        _deny(f"{what} non approuvée par l'utilisateur ({path})")


def _check(event: str, args: tuple):
    if event == "open":
        path = _to_path(args[0])
        flags = args[2] if len(args) > 2 and isinstance(args[2], int) else 0
        mode = args[1] if len(args) > 1 and isinstance(args[1], str) else ""
        writing = bool(flags & _WRITE_FLAGS) or any(c in mode for c in "wax+")
        if writing:
            _check_inside(path, "écriture")
        else:
            _check_readable(path)
    elif event in ("os.listdir", "os.scandir"):
        _check_readable(_to_path(args[0]))
    elif event in ("os.remove", "os.unlink"):
        _check_delete(_to_path(args[0]), "suppression de fichier")
    elif event == "os.rmdir":
        _check_delete(_to_path(args[0]), "suppression de dossier")
    elif event == "shutil.rmtree":
        _check_delete(_to_path(args[0]), "suppression de dossier")
    elif event in ("os.rename", "os.replace"):
        src, dst = _to_path(args[0]), _to_path(args[1])
        _check_inside(src, "déplacement")
        dn = _check_inside(dst, "déplacement")
        if dn is not None and os.path.lexists(dst):
            _check_delete(dst, "écrasement de fichier")
    elif event in ("os.mkdir", "os.chdir", "os.chmod", "os.chown", "os.truncate", "os.utime"):
        _check_inside(_to_path(args[0]), "accès")
    elif event == "shutil.copyfile" or event == "shutil.copymode" or event == "shutil.copystat":
        _check_inside(_to_path(args[1]), "écriture")
    elif event == "ctypes.dlopen":
        # Les bibliothèques (numpy...) chargent leurs DLL ; jamais une DLL venant du dossier de travail
        name = args[0]
        if name is not None and (os.sep in str(name) or "/" in str(name)):
            n = _norm(str(name))
            if not any(_under(n, r) for r in _READ_ROOTS if r != ROOT_N):
                _deny(f"chargement de bibliothèque hors Python ({name})")
    elif event == "ctypes.dlsym":
        return
    elif event in ("os.symlink", "os.link"):
        _deny("création de lien symbolique")
    elif event in (
        "subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn",
        "os.fork", "os.forkpty", "os.startfile",
        "socket.connect", "socket.bind", "socket.getaddrinfo", "socket.gethostbyname",
        "webbrowser.open",
    ):
        _deny(f"opération système/réseau interdite ({event})")


def _hook(event, args):
    if getattr(_local, "busy", False):
        return
    _local.busy = True
    try:
        _check(event, args)
    finally:
        _local.busy = False


def main():
    script = sys.argv[1]
    os.chdir(ROOT)
    sys.argv = [script]
    sys.addaudithook(_hook)
    runpy.run_path(script, run_name="__main__")


if __name__ == "__main__":
    main()
