"""Run record storage for local tests and Databricks Unity Catalog volumes."""

from __future__ import annotations

import io
import json
import os
import re
import uuid
from pathlib import Path


class LocalRunStore:
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


def _safe_key(*values: str) -> None:
    if any(re.fullmatch(r"[A-Za-z0-9_-]+", value) is None for value in values):
        raise ValueError("Identificador de registro inválido")


class VolumeRunStore:
    def __init__(self, files, directory: str):
        if not directory.startswith("/Volumes/"):
            raise ValueError("El almacenamiento remoto debe ser un volumen UC")
        self.files = files
        self.directory = directory.rstrip("/")
        self._created = False
        self._created_calls = False
        self._created_openspec: set[str] = set()

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
