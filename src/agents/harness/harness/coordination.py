"""Durable compare-and-set coordination for resumable run stages."""

from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path


class SqliteRunCoordinator:
    """Local coordinator with the same lease transitions as the remote adapter."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS run_state ("
                "run_id TEXT NOT NULL, attempt_id TEXT NOT NULL, stage TEXT NOT NULL, "
                "version INTEGER NOT NULL, lease_owner TEXT, lease_until REAL, "
                "last_action_key TEXT, checkpoint_id TEXT, "
                "PRIMARY KEY (run_id, attempt_id))"
            )

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _read(connection, run_id: str, attempt_id: str) -> dict | None:
        row = connection.execute(
            "SELECT * FROM run_state WHERE run_id = ? AND attempt_id = ?",
            (run_id, attempt_id),
        ).fetchone()
        return dict(row) if row else None

    def get(self, run_id: str, attempt_id: str) -> dict | None:
        with self._connect() as connection:
            return self._read(connection, run_id, attempt_id)

    def create(self, run_id: str, attempt_id: str, stage: str) -> dict:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO run_state (run_id, attempt_id, stage, version) VALUES (?, ?, ?, 0)",
                (run_id, attempt_id, stage),
            )
            return self._read(connection, run_id, attempt_id)

    def claim(
        self, run_id: str, attempt_id: str, *, expected_version: int,
        owner: str, key: str, now: float, ttl_seconds: float,
    ) -> dict | None:
        if ttl_seconds <= 0 or not owner or not key:
            raise ValueError("Lease inválido")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = self._read(connection, run_id, attempt_id)
            if current and current["last_action_key"] == key and current["lease_owner"] == owner:
                return current
            updated = connection.execute(
                "UPDATE run_state SET version = version + 1, lease_owner = ?, "
                "lease_until = ?, last_action_key = ? WHERE run_id = ? AND attempt_id = ? "
                "AND version = ? AND (lease_until IS NULL OR lease_until <= ?)",
                (owner, now + ttl_seconds, key, run_id, attempt_id, expected_version, now),
            )
            return self._read(connection, run_id, attempt_id) if updated.rowcount == 1 else None

    def finish(
        self, run_id: str, attempt_id: str, *, expected_version: int, owner: str,
        key: str, stage: str, checkpoint_id: str | None, now: float,
    ) -> dict | None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = self._read(connection, run_id, attempt_id)
            if current and current["last_action_key"] == key and current["stage"] == stage and current["checkpoint_id"] == checkpoint_id:
                return current
            updated = connection.execute(
                "UPDATE run_state SET version = version + 1, stage = ?, checkpoint_id = ?, "
                "lease_owner = NULL, lease_until = NULL, last_action_key = ? "
                "WHERE run_id = ? AND attempt_id = ? AND version = ? "
                "AND lease_owner = ? AND lease_until > ?",
                (stage, checkpoint_id, key, run_id, attempt_id, expected_version, owner, now),
            )
            return self._read(connection, run_id, attempt_id) if updated.rowcount == 1 else None


class DeltaRunCoordinator:
    """Remote coordinator backed by a dedicated Unity Catalog Delta table."""

    def __init__(self, api, warehouse_id: str, table_name: str):
        parts = table_name.split(".")
        if (
            len(parts) != 3 or not parts[0].startswith("demo_harness_")
            or parts[2] != "demo_harness_run_state"
            or any(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", part) is None for part in parts)
        ):
            raise ValueError("Tabla de coordinación fuera del catálogo del harness")
        self.api = api
        self.warehouse_id = warehouse_id
        self.table_name = ".".join(f"`{part}`" for part in parts)

    def provision(self) -> None:
        self._execute(
            f"CREATE TABLE IF NOT EXISTS {self.table_name} ("
            "run_id STRING NOT NULL, attempt_id STRING NOT NULL, stage STRING NOT NULL, "
            "version BIGINT NOT NULL, lease_owner STRING, lease_until DOUBLE, "
            "last_action_key STRING, checkpoint_id STRING) USING DELTA "
            "TBLPROPERTIES ('delta.enableDeletionVectors' = 'true')"
        )

    def _execute(self, statement: str, **values) -> dict:
        parameters = []
        for name, value in values.items():
            entry = {"name": name, "value": None if value is None else str(value)}
            if isinstance(value, int):
                entry["type"] = "BIGINT"
            elif isinstance(value, float):
                entry["type"] = "DOUBLE"
            parameters.append(entry)
        response = self.api.do("POST", "/api/2.0/sql/statements", body={
            "warehouse_id": self.warehouse_id, "statement": statement,
            "parameters": parameters, "wait_timeout": "30s", "on_wait_timeout": "CONTINUE",
            "format": "JSON_ARRAY", "row_limit": 2,
        })
        deadline = time.monotonic() + 60
        while response.get("status", {}).get("state") in {"PENDING", "RUNNING"}:
            if time.monotonic() > deadline or not response.get("statement_id"):
                raise TimeoutError("La coordinación SQL excedió el tiempo límite")
            time.sleep(0.5)
            response = self.api.do("GET", f"/api/2.0/sql/statements/{response['statement_id']}")
        if response.get("status", {}).get("state") != "SUCCEEDED":
            raise RuntimeError("Falló una transición de coordinación SQL")
        return response

    def get(self, run_id: str, attempt_id: str) -> dict | None:
        response = self._execute(
            f"SELECT run_id, attempt_id, stage, version, lease_owner, lease_until, "
            f"last_action_key, checkpoint_id FROM {self.table_name} "
            "WHERE run_id = :run_id AND attempt_id = :attempt_id LIMIT 2",
            run_id=run_id, attempt_id=attempt_id,
        )
        rows = (response.get("result") or {}).get("data_array") or []
        if len(rows) > 1:
            raise ValueError("La tabla de coordinación contiene intentos duplicados")
        if not rows:
            return None
        row = rows[0]
        return {
            "run_id": row[0], "attempt_id": row[1], "stage": row[2],
            "version": int(row[3]), "lease_owner": row[4],
            "lease_until": float(row[5]) if row[5] is not None else None,
            "last_action_key": row[6], "checkpoint_id": row[7],
        }

    def create(self, run_id: str, attempt_id: str, stage: str) -> dict:
        self._execute(
            f"MERGE INTO {self.table_name} t USING "
            "(SELECT :run_id AS run_id, :attempt_id AS attempt_id, :stage AS stage) s "
            "ON t.run_id = s.run_id AND t.attempt_id = s.attempt_id "
            "WHEN NOT MATCHED THEN INSERT "
            "(run_id, attempt_id, stage, version) VALUES (s.run_id, s.attempt_id, s.stage, 0)",
            run_id=run_id, attempt_id=attempt_id, stage=stage,
        )
        result = self.get(run_id, attempt_id)
        if result is None:
            raise RuntimeError("No se creó el estado de coordinación")
        return result

    def claim(
        self, run_id: str, attempt_id: str, *, expected_version: int,
        owner: str, key: str, now: float, ttl_seconds: float,
    ) -> dict | None:
        if ttl_seconds <= 0 or not owner or not key:
            raise ValueError("Lease inválido")
        self._execute(
            f"UPDATE {self.table_name} SET version = version + 1, "
            "lease_owner = :owner, lease_until = :expires, last_action_key = :key "
            "WHERE run_id = :run_id AND attempt_id = :attempt_id "
            "AND version = :expected_version AND (lease_until IS NULL OR lease_until <= :now)",
            owner=owner, expires=now + ttl_seconds, key=key,
            run_id=run_id, attempt_id=attempt_id, expected_version=expected_version, now=now,
        )
        result = self.get(run_id, attempt_id)
        return result if result and result["lease_owner"] == owner and result["last_action_key"] == key and result["version"] in {expected_version, expected_version + 1} else None

    def finish(
        self, run_id: str, attempt_id: str, *, expected_version: int, owner: str,
        key: str, stage: str, checkpoint_id: str | None, now: float,
    ) -> dict | None:
        self._execute(
            f"UPDATE {self.table_name} SET version = version + 1, stage = :stage, "
            "checkpoint_id = :checkpoint_id, lease_owner = NULL, lease_until = NULL, "
            "last_action_key = :key WHERE run_id = :run_id AND attempt_id = :attempt_id "
            "AND version = :expected_version AND lease_owner = :owner AND lease_until > :now",
            stage=stage, checkpoint_id=checkpoint_id, key=key,
            run_id=run_id, attempt_id=attempt_id, expected_version=expected_version,
            owner=owner, now=now,
        )
        result = self.get(run_id, attempt_id)
        return result if result and result["stage"] == stage and result["checkpoint_id"] == checkpoint_id and result["last_action_key"] == key and result["version"] in {expected_version, expected_version + 1} else None
