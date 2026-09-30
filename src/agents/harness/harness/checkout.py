"""Pinned local Git checkout with installation credentials confined to the process env."""

from __future__ import annotations

import base64
import os
import re
import subprocess
from pathlib import Path
from collections.abc import Callable

from .store import _checkpoint_path


class GitCheckout:
    def __init__(self, remote_url: str, base_branch: str, *, max_files: int = 2000, max_bytes: int = 50_000_000):
        if not remote_url or re.fullmatch(r"[A-Za-z0-9._/-]+", base_branch) is None or ".." in base_branch:
            raise ValueError("Origen Git inválido")
        self.remote_url = remote_url
        self.base_branch = base_branch
        self.max_files = max_files
        self.max_bytes = max_bytes

    @staticmethod
    def _git(args: list[str], *, cwd: Path | None, env: dict[str, str]) -> bytes:
        try:
            result = subprocess.run(
                ["git", *args], cwd=cwd, env=env, capture_output=True,
                timeout=120, check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise TimeoutError("Git excedió el tiempo límite") from error
        if result.returncode:
            # Git output may contain credentials from transport errors; never return it.
            raise ValueError("Falló la operación Git del repositorio cliente")
        return result.stdout

    def clone(self, destination: Path, base_sha: str, *, token: str) -> None:
        if re.fullmatch(r"[a-f0-9]{40}", base_sha) is None:
            raise ValueError("SHA base inválido")
        if destination.exists():
            raise ValueError("El destino del checkout ya existe")
        if not token:
            raise ValueError("Falta token temporal para el checkout")
        env = os.environ.copy()
        authorization = base64.b64encode(f"x-access-token:{token}".encode("utf-8")).decode("ascii")
        env.update({
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
            "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {authorization}",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_LFS_SKIP_SMUDGE": "1",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TRACE": "0",
            "GIT_TRACE_CURL": "0",
        })
        self._git(
            ["clone", "--no-checkout", "--single-branch", "--branch", self.base_branch,
             "--", self.remote_url, str(destination)],
            cwd=None, env=env,
        )
        try:
            actual = self._git(["rev-parse", "--verify", f"{base_sha}^{{commit}}"], cwd=destination, env=env).decode("ascii").strip()
        except ValueError as error:
            raise ValueError("El SHA base no está disponible en el checkout") from error
        if actual != base_sha:
            raise ValueError("El SHA base no está disponible en el checkout")
        tree = self._git(["ls-tree", "-r", "-l", "-z", base_sha], cwd=destination, env=env)
        files = tree.split(b"\0")
        total = 0
        count = 0
        for item in files:
            if not item:
                continue
            metadata, _, _name = item.partition(b"\t")
            fields = metadata.split()
            if len(fields) != 4 or fields[0] not in {b"100644", b"100755"} or fields[1] != b"blob":
                raise ValueError("El checkout contiene un enlace o submódulo no admitido")
            count += 1
            total += int(fields[3])
        if count > self.max_files or total > self.max_bytes:
            raise ValueError("El checkout excede los límites de archivos o tamaño")
        self._git(["checkout", "--detach", base_sha], cwd=destination, env=env)
        if self._git(["rev-parse", "HEAD"], cwd=destination, env=env).decode("ascii").strip() != base_sha:
            raise ValueError("El checkout no quedó en el SHA base autorizado")


def _current_sha(root: Path) -> str:
    return GitCheckout._git(["rev-parse", "HEAD"], cwd=root, env=os.environ.copy()).decode("ascii").strip()


def _allowed_path(root: Path, path: str, allows: Callable[[str], bool]) -> Path:
    _checkpoint_path(path)
    if path.startswith(".github/") or not allows(path):
        raise ValueError("Ruta de checkpoint fuera de la política del perfil")
    target = root.joinpath(*path.split("/"))
    if any(part.is_symlink() for part in (target, *target.parents) if part == root or root in part.parents):
        raise ValueError("El checkout contiene un enlace fuera de política")
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("Ruta de checkpoint fuera del checkout")
    return target


def snapshot_changes(root: Path, base_sha: str, allows: Callable[[str], bool]) -> dict[str, bytes | None]:
    """Capture only exact bytes differing from a pinned, complete checkout."""
    if _current_sha(root) != base_sha:
        raise ValueError("El SHA del checkout no coincide con la base")
    tracked_bytes = GitCheckout._git(["ls-files", "-z"], cwd=root, env=os.environ.copy())
    tracked = {item.decode("utf-8") for item in tracked_bytes.split(b"\0") if item}
    present: set[str] = set()
    for directory, folders, files in os.walk(root, followlinks=False):
        current = Path(directory)
        folders[:] = [name for name in folders if name != ".git"]
        for name in folders:
            if (current / name).is_symlink():
                raise ValueError("El checkout contiene un enlace fuera de política")
        for name in files:
            relative = (current / name).relative_to(root).as_posix()
            present.add(relative)
    changes: dict[str, bytes | None] = {}
    for path in sorted(tracked | present):
        target = root.joinpath(*path.split("/"))
        if path not in present:
            _allowed_path(root, path, allows)
            changes[path] = None
            continue
        if target.is_symlink() or not target.is_file():
            raise ValueError("El checkout contiene un enlace o tipo de archivo no admitido")
        current_bytes = target.read_bytes()
        if path in tracked:
            before = GitCheckout._git(["show", f"{base_sha}:{path}"], cwd=root, env=os.environ.copy())
            if current_bytes == before:
                continue
        _allowed_path(root, path, allows)
        changes[path] = current_bytes
    if len(changes) > 300 or sum(len(value or b"") for value in changes.values()) > 10_000_000:
        raise ValueError("El borrador excede los límites del checkpoint")
    return changes


def restore_checkpoint(root: Path, checkpoint: dict, base_sha: str, allows: Callable[[str], bool]) -> None:
    """Apply an integrity-checked checkpoint to a fresh checkout of the same base."""
    if checkpoint.get("base_sha") != base_sha or _current_sha(root) != base_sha:
        raise ValueError("El SHA del checkpoint no coincide con el checkout")
    files = checkpoint.get("files")
    if not isinstance(files, dict) or len(files) > 300 or sum(len(value or b"") for value in files.values()) > 10_000_000:
        raise ValueError("Checkpoint fuera de límites")
    destinations = {path: _allowed_path(root, path, allows) for path in files}
    for path, target in destinations.items():
        contents = files[path]
        if contents is None:
            if target.exists():
                target.unlink()
        elif isinstance(contents, bytes):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(contents)
        else:
            raise ValueError("El checkpoint no contiene bytes exactos")
    if snapshot_changes(root, base_sha, allows) != files:
        raise ValueError("La restauración del checkout no coincide con el checkpoint")
