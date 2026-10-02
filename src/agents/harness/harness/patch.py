"""Typed full-file edits constrained by a trusted client profile."""

from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from .contracts import ClientProfile


class FileOperation(BaseModel):
    op: Literal["create", "modify", "delete"]
    path: str = Field(min_length=1, max_length=500)
    content: str | None = None
    expected_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def valid_shape(self):
        if self.op == "create" and (self.content is None or self.expected_sha256 is not None):
            raise ValueError("Creación de archivo inválida")
        if self.op == "modify" and (self.content is None or self.expected_sha256 is None):
            raise ValueError("Modificación de archivo inválida")
        if self.op == "delete" and (self.content is not None or self.expected_sha256 is None):
            raise ValueError("Eliminación de archivo inválida")
        return self


def _target(root: Path, profile: ClientProfile, path: str) -> Path:
    policy = profile.general_patch
    pure = PurePosixPath(path)
    if (
        policy is None or pure.is_absolute() or "\\" in path or "//" in path
        or any(part in {"", ".", ".."} for part in path.split("/"))
        or path.startswith((".github/", ".git/", "openspec/"))
        or pure.suffix not in policy.extensions
        or not profile.allows_code(path)
    ):
        raise ValueError("Ruta de edición fuera de la política del perfil")
    target = root.joinpath(*path.split("/"))
    if target.is_symlink() or any(parent.is_symlink() for parent in target.parents if parent == root or root in parent.parents):
        raise ValueError("La edición no admite enlaces simbólicos")
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("Ruta de edición fuera del checkout")
    return target


def apply_file_operations(root: Path, profile: ClientProfile, operations: list[FileOperation]) -> list[str]:
    policy = profile.general_patch
    if policy is None:
        raise ValueError("El perfil no habilita cambios generales")
    if not operations or len(operations) > policy.max_files:
        raise ValueError("Cantidad de operaciones fuera de la política")
    if len({operation.path for operation in operations}) != len(operations):
        raise ValueError("La propuesta contiene operaciones duplicadas")
    prepared = []
    total = 0
    for operation in operations:
        if operation.op not in policy.operations:
            raise ValueError("Operación de archivo fuera de la política")
        target = _target(root, profile, operation.path)
        if target.exists() and not target.is_file():
            raise ValueError("La ruta de edición no es un archivo regular")
        if operation.op == "create" and target.exists():
            raise ValueError("El archivo nuevo ya existe")
        if operation.op != "create" and (
            not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != operation.expected_sha256
        ):
            raise ValueError("El hash del archivo ya no coincide con el borrador")
        content = operation.content.encode("utf-8") if operation.content is not None else None
        if content is not None and b"\0" in content:
            raise ValueError("Contenido binario no admitido")
        total += len(content or b"")
        prepared.append((operation, target, content))
    if total > policy.max_bytes:
        raise ValueError("El parche excede el límite de bytes")
    for operation, target, content in prepared:
        if operation.op == "delete":
            target.unlink()
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    return sorted(operation.path for operation in operations)
