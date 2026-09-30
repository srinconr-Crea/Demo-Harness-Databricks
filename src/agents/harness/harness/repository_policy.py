"""Shared path decisions; model output never changes these permissions."""

from pathlib import Path


def valid_relative(path: str) -> bool:
    return (
        bool(path)
        and not path.startswith("/")
        and "\\" not in path
        and ":" not in path
        and all(part not in {"", ".", ".."} for part in path.split("/"))
    )


def matches(path: str, prefix: str) -> bool:
    path, prefix = path.casefold(), prefix.rstrip("/").casefold()
    return path == prefix or path.startswith(prefix + "/")


def denied(path: str, extra=()) -> bool:
    if not valid_relative(path):
        return True
    parts = path.casefold().split("/")
    return any(
        matches(path, p) for p in (".git", ".aws", ".ssh", ".secrets", *extra)
    ) or any(
        p.startswith(".env")
        or p.endswith((".pem", ".key", ".p12", ".pfx"))
        or p
        in {
            ".git",
            ".aws",
            ".ssh",
            ".secrets",
            "credentials",
            "secrets.json",
            "secrets.yaml",
            "secrets.yml",
        }
        for p in parts
    )


def safe_target(root: Path, path: str) -> Path:
    if not valid_relative(path):
        raise ValueError("Ruta relativa inválida")
    target = root.joinpath(*path.split("/"))
    if any(
        p.is_symlink()
        for p in (target, *target.parents)
        if p == root or root in p.parents
    ):
        raise ValueError("El checkout no admite enlaces")
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("Ruta fuera del checkout")
    return target
