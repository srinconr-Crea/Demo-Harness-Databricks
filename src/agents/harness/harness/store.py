"""Run record storage for local tests and Databricks Unity Catalog volumes."""

from __future__ import annotations

import io
import hashlib
import json
import os
import re
import uuid
from pathlib import Path, PurePosixPath


def _checkpoint_path(path: str) -> None:
    pure = PurePosixPath(path)
    if (
        not path or pure.is_absolute() or "\\" in path or "//" in path
        or any(part in {"", ".", ".."} for part in path.split("/"))
        or pure.parts[0] in {".git", ".github"}
    ):
        raise ValueError("Ruta de checkpoint fuera del checkout")


class _CheckpointStore:
    def _write_checkpoint_file(self, relative: str, contents: bytes) -> None:
        raise NotImplementedError

    def _read_checkpoint_file(self, relative: str) -> bytes:
        raise NotImplementedError

    def save_review_diff(self, run_id: str, attempt_id: str, revision: int, diff: str) -> str:
        _safe_key(run_id, attempt_id)
        if revision < 1 or len(diff.encode("utf-8")) > 1_000_000:
            raise ValueError("Diff de revisión fuera de límites")
        payload = diff.encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        self._write_checkpoint_file(f"reviews/{run_id}/{attempt_id}/{revision}-{digest}.diff", payload)
        return digest

    def load_review_diff(self, run_id: str, attempt_id: str, revision: int, digest: str) -> str:
        _safe_key(run_id, attempt_id, digest)
        if revision < 1 or re.fullmatch(r"[a-f0-9]{64}", digest) is None:
            raise ValueError("Referencia de diff inválida")
        payload = self._read_checkpoint_file(f"reviews/{run_id}/{attempt_id}/{revision}-{digest}.diff")
        if hashlib.sha256(payload).hexdigest() != digest:
            raise ValueError("Falló la integridad del diff de revisión")
        return payload.decode("utf-8")

    def save_checkpoint(
        self, run_id: str, attempt_id: str, revision: int, base_sha: str,
        files: dict[str, bytes | None],
        *, metadata: dict | None = None,
    ) -> str:
        _safe_key(run_id, attempt_id)
        if revision < 1 or re.fullmatch(r"[a-f0-9]{40}", base_sha) is None:
            raise ValueError("Metadatos de checkpoint inválidos")
        if len(files) > 300 or sum(len(data or b"") for data in files.values()) > 10_000_000:
            raise ValueError("Checkpoint excede los límites")
        for path, contents in files.items():
            _checkpoint_path(path)
            if contents is not None and not isinstance(contents, bytes):
                raise ValueError("El checkpoint exige bytes exactos")
        checkpoint_id = uuid.uuid4().hex
        relative = f"checkpoints/{run_id}/{attempt_id}/{checkpoint_id}"
        entries = {}
        for path, contents in sorted(files.items()):
            if contents is None:
                entries[path] = None
                continue
            blob = f"{hashlib.sha256(path.encode('utf-8')).hexdigest()[:24]}.bin"
            self._write_checkpoint_file(f"{relative}/{blob}", contents)
            entries[path] = {"blob": blob, "sha256": hashlib.sha256(contents).hexdigest()}
        metadata = metadata or {}
        if len(json.dumps(metadata, ensure_ascii=False, default=str).encode("utf-8")) > 1_000_000:
            raise ValueError("Metadatos de checkpoint fuera de límites")
        manifest = {"base_sha": base_sha, "revision": revision, "files": entries, "metadata": metadata}
        payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        manifest["manifest_sha256"] = hashlib.sha256(payload).hexdigest()
        self._write_checkpoint_file(f"{relative}/manifest.json", json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        return checkpoint_id

    def load_checkpoint(self, run_id: str, attempt_id: str, checkpoint_id: str) -> dict:
        _safe_key(run_id, attempt_id, checkpoint_id)
        relative = f"checkpoints/{run_id}/{attempt_id}/{checkpoint_id}"
        manifest = json.loads(self._read_checkpoint_file(f"{relative}/manifest.json").decode("utf-8"))
        digest = manifest.pop("manifest_sha256", None)
        payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if digest != hashlib.sha256(payload).hexdigest():
            raise ValueError("Falló la integridad del manifiesto de checkpoint")
        result = {}
        for path, entry in manifest["files"].items():
            _checkpoint_path(path)
            if entry is None:
                result[path] = None
                continue
            expected_blob = f"{hashlib.sha256(path.encode('utf-8')).hexdigest()[:24]}.bin"
            if entry.get("blob") != expected_blob:
                raise ValueError("Falló la integridad de la ruta del checkpoint")
            contents = self._read_checkpoint_file(f"{relative}/{expected_blob}")
            if hashlib.sha256(contents).hexdigest() != entry.get("sha256"):
                raise ValueError("Falló la integridad del contenido del checkpoint")
            result[path] = contents
        return {"base_sha": manifest["base_sha"], "revision": manifest["revision"], "files": result, "metadata": manifest.get("metadata", {})}


class LocalRunStore(_CheckpointStore):
    def __init__(self, directory: Path):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    def save(self, run_id: str, record: dict) -> None:
        destination = self.directory / f"{run_id}.json"
        temporary = self.directory / f"{run_id}.{uuid.uuid4().hex}.tmp"
        temporary.write_text(json.dumps(record, ensure_ascii=False, default=str), encoding="utf-8")
        os.replace(temporary, destination)

    def load(self, run_id: str) -> dict | None:
        path = self.directory / f"{run_id}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def list_runs(self) -> list[str]:
        return [path.stem for path in self.directory.glob("*.json")]

    def save_agent_call(self, run_id: str, call_id: str, record: dict) -> None:
        _safe_key(run_id, call_id)
        directory = self.directory / "agent_calls"
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / f"{run_id}-{call_id}.json"
        temporary = directory / f"{run_id}-{call_id}.{uuid.uuid4().hex}.tmp"
        temporary.write_text(json.dumps(record, ensure_ascii=False, default=str), encoding="utf-8")
        os.replace(temporary, destination)

    def list_agent_calls(self, run_id: str, attempt_id: str | None = None) -> list[dict]:
        _safe_key(run_id)
        records = [json.loads(path.read_text(encoding="utf-8")) for path in
                   (self.directory / "agent_calls").glob(f"{run_id}-*.json")]
        return [item for item in records if attempt_id is None or item.get("attempt_id") == attempt_id]

    def save_openspec_artifact(self, run_id: str, attempt_id: str, artifact_id: str, record: dict) -> None:
        _safe_key(run_id, attempt_id, artifact_id)
        directory = self.directory / "openspec" / run_id / attempt_id
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / f"{artifact_id}.json"
        temporary = directory / f"{artifact_id}.{uuid.uuid4().hex}.tmp"
        temporary.write_text(json.dumps(record, ensure_ascii=False, default=str), encoding="utf-8")
        os.replace(temporary, destination)

    def load_openspec_artifact(self, run_id: str, attempt_id: str, artifact_id: str) -> dict | None:
        _safe_key(run_id, attempt_id, artifact_id)
        path = self.directory / "openspec" / run_id / attempt_id / f"{artifact_id}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def _write_checkpoint_file(self, relative: str, contents: bytes) -> None:
        destination = self.directory / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_bytes(contents)
        os.replace(temporary, destination)

    def _read_checkpoint_file(self, relative: str) -> bytes:
        return (self.directory / relative).read_bytes()


def _safe_key(*values: str) -> None:
    if any(re.fullmatch(r"[A-Za-z0-9_-]+", value) is None for value in values):
        raise ValueError("Identificador de registro inválido")


class VolumeRunStore(_CheckpointStore):
    def __init__(self, files, directory: str):
        if not directory.startswith("/Volumes/"):
            raise ValueError("El almacenamiento remoto debe ser un volumen UC")
        self.files = files
        self.directory = directory.rstrip("/")
        self._created = False
        self._created_calls = False
        self._created_openspec: set[str] = set()
        self._created_checkpoints: set[str] = set()

    def _path(self, run_id: str) -> str:
        return f"{self.directory}/{run_id}.json"

    def save(self, run_id: str, record: dict) -> None:
        if not self._created:
            self.files.create_directory(self.directory)
            self._created = True
        payload = json.dumps(record, ensure_ascii=False, default=str).encode("utf-8")
        self.files.upload(self._path(run_id), io.BytesIO(payload), overwrite=True)

    def load(self, run_id: str) -> dict | None:
        try:
            response = self.files.download(self._path(run_id))
        except Exception as error:
            if isinstance(error, FileNotFoundError) or getattr(error, "error_code", None) in {"RESOURCE_DOES_NOT_EXIST", "NOT_FOUND"}:
                return None
            raise
        with response.contents as stream:
            return json.loads(stream.read().decode("utf-8"))

    def list_runs(self) -> list[str]:
        try:
            entries = self.files.list_directory_contents(self.directory)
            return [entry.name[:-5] for entry in entries if not entry.is_directory and entry.name and entry.name.endswith(".json")]
        except Exception as error:
            if getattr(error, "error_code", None) in {"RESOURCE_DOES_NOT_EXIST", "NOT_FOUND"}:
                return []
            raise

    def save_agent_call(self, run_id: str, call_id: str, record: dict) -> None:
        _safe_key(run_id, call_id)
        directory = f"{self.directory}/agent_calls"
        if not self._created_calls:
            self.files.create_directory(directory)
            self._created_calls = True
        payload = json.dumps(record, ensure_ascii=False, default=str).encode("utf-8")
        self.files.upload(f"{directory}/{run_id}-{call_id}.json", io.BytesIO(payload), overwrite=True)

    def list_agent_calls(self, run_id: str, attempt_id: str | None = None) -> list[dict]:
        _safe_key(run_id)
        directory = f"{self.directory}/agent_calls"
        try:
            entries = self.files.list_directory_contents(directory)
        except Exception as error:
            if getattr(error, "error_code", None) in {"RESOURCE_DOES_NOT_EXIST", "NOT_FOUND"}:
                return []
            raise
        records = []
        for entry in entries:
            if entry.is_directory or not entry.name or not re.fullmatch(rf"{re.escape(run_id)}-[A-Za-z0-9_-]+\.json", entry.name):
                continue
            response = self.files.download(f"{directory}/{entry.name}")
            with response.contents as stream:
                item = json.loads(stream.read().decode("utf-8"))
            if attempt_id is None or item.get("attempt_id") == attempt_id:
                records.append(item)
        return records

    def save_openspec_artifact(self, run_id: str, attempt_id: str, artifact_id: str, record: dict) -> None:
        _safe_key(run_id, attempt_id, artifact_id)
        directory = f"{self.directory}/openspec/{run_id}/{attempt_id}"
        if directory not in self._created_openspec:
            self.files.create_directory(directory)
            self._created_openspec.add(directory)
        payload = json.dumps(record, ensure_ascii=False, default=str).encode("utf-8")
        self.files.upload(f"{directory}/{artifact_id}.json", io.BytesIO(payload), overwrite=True)

    def load_openspec_artifact(self, run_id: str, attempt_id: str, artifact_id: str) -> dict | None:
        _safe_key(run_id, attempt_id, artifact_id)
        path = f"{self.directory}/openspec/{run_id}/{attempt_id}/{artifact_id}.json"
        try:
            response = self.files.download(path)
        except Exception as error:
            if isinstance(error, FileNotFoundError) or getattr(error, "error_code", None) in {"RESOURCE_DOES_NOT_EXIST", "NOT_FOUND"}:
                return None
            raise
        with response.contents as stream:
            return json.loads(stream.read().decode("utf-8"))

    def _write_checkpoint_file(self, relative: str, contents: bytes) -> None:
        directory = f"{self.directory}/{relative.rsplit('/', 1)[0]}"
        if directory not in self._created_checkpoints:
            self.files.create_directory(directory)
            self._created_checkpoints.add(directory)
        self.files.upload(f"{self.directory}/{relative}", io.BytesIO(contents), overwrite=True)

    def _read_checkpoint_file(self, relative: str) -> bytes:
        response = self.files.download(f"{self.directory}/{relative}")
        with response.contents as stream:
            return stream.read()
