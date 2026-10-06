"""Typed full-file edits constrained by a trusted client profile."""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .checkout import GitCheckout, snapshot_changes
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


class ManifestCoverage(BaseModel):
    """Evidence for one approved path, independent of checkout edit operations."""

    model_config = ConfigDict(extra="forbid", strict=True)
    path: str = Field(min_length=1, max_length=500)
    status: Literal["applied", "already_conformant", "blocked"]
    sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    reason: str | None = Field(default=None, min_length=1, max_length=4000)

    @model_validator(mode="after")
    def valid_evidence(self):
        if self.status == "already_conformant" and self.sha256 is None:
            raise ValueError("La cobertura conforme requiere hash de evidencia")
        if self.status == "blocked" and (self.reason is None or not self.reason.strip()):
            raise ValueError("La cobertura bloqueada requiere motivo")
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
    if any(parent.exists() and not parent.is_dir() for parent in target.parents
           if parent == root or root in parent.parents):
        raise ValueError("La ruta de edición requiere directorios regulares")
    return target


def _prepare_operations(root: Path, profile: ClientProfile, operations: list[FileOperation]):
    policy = profile.general_patch
    if policy is None:
        raise ValueError("El perfil no habilita cambios generales")
    if not operations or len(operations) > policy.max_files:
        raise ValueError("Cantidad de operaciones fuera de la política")
    if len({operation.path for operation in operations}) != len(operations):
        raise ValueError("La propuesta contiene operaciones duplicadas")
    paths = {PurePosixPath(operation.path) for operation in operations}
    if any(parent in paths for path in paths for parent in path.parents):
        raise ValueError("La propuesta contiene rutas de archivos superpuestas")
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
    return prepared


def apply_file_operations(root: Path, profile: ClientProfile, operations: list[FileOperation]) -> list[str]:
    prepared = _prepare_operations(root, profile, operations)
    for operation, target, content in prepared:
        if operation.op == "delete":
            target.unlink()
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    return sorted(operation.path for operation in operations)


def validate_manifest_coverage(
    root: Path,
    profile: ClientProfile,
    base_sha: str,
    approved_manifest: list[dict],
    operations: list[FileOperation],
    coverage: list[ManifestCoverage | dict],
) -> list[str]:
    """Validate the complete projected candidate before any checkout writes.

    Return cumulative code paths differing from the pinned base, including
    earlier changes and deletions. A deleted path's no-op evidence hashes its
    exact base bytes; other no-op evidence hashes its current checkout bytes.
    This checks evidence/scope, never semantic correctness or test success.
    """
    policy = profile.general_patch
    if policy is None:
        raise ValueError("El perfil no habilita cambios generales")
    if re.fullmatch(r"[a-f0-9]{40}", base_sha) is None:
        raise ValueError("SHA base inválido")
    if not isinstance(approved_manifest, list) or not 1 <= len(approved_manifest) <= policy.max_files:
        raise ValueError("Cantidad de archivos del manifiesto fuera de la política")
    manifest = {}
    for item in approved_manifest:
        if (not isinstance(item, dict) or set(item) != {"op", "path"}
                or not isinstance(item.get("path"), str) or item.get("op") not in policy.operations):
            raise ValueError("Manifiesto aprobado inválido")
        _target(root, profile, item["path"])
        if item["path"] in manifest:
            raise ValueError("El manifiesto contiene rutas duplicadas")
        manifest[item["path"]] = item["op"]

    if not isinstance(coverage, list) or len(coverage) != len(manifest):
        raise ValueError("Cobertura incompleta del manifiesto aprobado")
    evidence = {}
    for value in coverage:
        entry = ManifestCoverage.model_validate(value)
        if entry.path not in manifest or entry.path in evidence:
            raise ValueError("Cobertura fuera del manifiesto o duplicada")
        if entry.status == "blocked":
            raise ValueError("Cobertura bloqueada: falta evidencia de conformidad")
        evidence[entry.path] = entry

    if not isinstance(operations, list):
        raise ValueError("Lista de operaciones inválida")
    prepared = _prepare_operations(root, profile, operations) if operations else []
    edits = {operation.path: (operation, contents) for operation, _, contents in prepared}
    if not edits.keys() <= manifest.keys():
        raise ValueError("Operación fuera del manifiesto aprobado")
    for path, entry in evidence.items():
        if (entry.status == "applied") != (path in edits):
            raise ValueError("La cobertura no coincide con las operaciones propuestas")

    # Snapshot also rejects unapproved checkout changes. OpenSpec artifacts have
    # their own manager and limits and do not count as developer code operations.
    changed = snapshot_changes(root, base_sha, lambda path: profile.allows_code(path) or profile.allows_openspec(path))
    projected = {path: content for path, content in changed.items() if not profile.allows_openspec(path)}
    if not projected.keys() <= manifest.keys():
        raise ValueError("El diff acumulado excede el manifiesto aprobado")
    tree = GitCheckout._git(["ls-tree", "-r", "-z", base_sha], cwd=root, env=os.environ.copy())
    base_entries = {}
    for record in tree.split(b"\0"):
        if record:
            metadata, _, name = record.partition(b"\t")
            base_entries[name.decode("utf-8")] = metadata.split()
    base_contents = {}
    for path, approved_op in manifest.items():
        metadata = base_entries.get(path)
        if metadata is not None and (metadata[0] not in {b"100644", b"100755"} or metadata[1] != b"blob"):
            raise ValueError("La base contiene un tipo de archivo no admitido")
        before = (GitCheckout._git(["show", f"{base_sha}:{path}"], cwd=root, env=os.environ.copy())
                  if metadata is not None else None)
        base_contents[path] = before
        if (approved_op == "create") != (before is None):
            raise ValueError("La operación del manifiesto no corresponde al SHA base")
        target = _target(root, profile, path)
        if target.exists() and not target.is_file():
            raise ValueError("La cobertura no admite tipos de archivo no regulares")
        current = target.read_bytes() if target.is_file() else None
        if path in edits:
            operation, after = edits[path]
            permitted = {"create", "modify"} if approved_op == "create" else {approved_op}
            if operation.op not in permitted:
                raise ValueError("La operación acumulada difiere del manifiesto aprobado")
        else:
            after = current
            proof = before if approved_op == "delete" and current is None else current
            if proof is None or hashlib.sha256(proof).hexdigest() != evidence[path].sha256:
                raise ValueError("El hash de cobertura ya no coincide con la evidencia")
        if (approved_op == "delete") != (after is None):
            raise ValueError("El estado del candidato no corresponde al manifiesto aprobado")
        if after is not None and b"\0" in after:
            raise ValueError("Contenido binario no admitido en cobertura")
        if after is not None:
            try:
                after.decode("utf-8")
            except UnicodeDecodeError as error:
                raise ValueError("La cobertura requiere contenido UTF-8") from error
        if before == after:
            projected.pop(path, None)
        else:
            projected[path] = after

    if len(projected) > policy.max_files:
        raise ValueError("El diff acumulado excede el límite de archivos")
    # Count both removed and retained bytes: deleting a large base file cannot
    # evade the bound, and a small repair cannot hide a large earlier candidate.
    total = sum(max(len(base_contents[path] or b""), len(content or b""))
                for path, content in projected.items())
    if total > policy.max_bytes:
        raise ValueError("El diff acumulado excede el límite de bytes")
    return sorted(projected)
