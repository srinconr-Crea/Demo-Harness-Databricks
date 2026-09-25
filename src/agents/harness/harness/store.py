"""Run record storage for local tests and Databricks Unity Catalog volumes."""

from __future__ import annotations

import io
import json
import os
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


class VolumeRunStore:
    def __init__(self, files, directory: str):
        if not directory.startswith("/Volumes/"):
            raise ValueError("El almacenamiento remoto debe ser un volumen UC")
        self.files = files
        self.directory = directory.rstrip("/")
        self._created = False

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
