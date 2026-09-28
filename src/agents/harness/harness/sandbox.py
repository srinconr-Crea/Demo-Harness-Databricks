"""Remote SQL check on the isolated harness warehouse with synthetic values."""

from __future__ import annotations

import time
from decimal import Decimal

from .contracts import RatioSpec


def _safe_ratio_sql(spec: RatioSpec) -> str:
    return f"""
WITH samples (id, {spec.numerator}, {spec.denominator}) AS (
  SELECT * FROM VALUES
    (1, CAST(20 AS DOUBLE), CAST(10 AS DOUBLE)),
    (2, CAST(20 AS DOUBLE), CAST(0 AS DOUBLE)),
    (3, CAST(20 AS DOUBLE), CAST(NULL AS DOUBLE))
)
SELECT id,
       CASE WHEN {spec.denominator} IS NULL OR {spec.denominator} = 0
            THEN NULL ELSE {spec.numerator} / {spec.denominator} END AS {spec.output_column}
FROM samples ORDER BY id
""".strip()


def verify_safe_ratio(api, warehouse_id: str, spec: RatioSpec, *, timeout_seconds: int = 180) -> bool:
    if not warehouse_id:
        raise ValueError("Falta warehouse aislado para pruebas")
    result = api.do("POST", "/api/2.0/sql/statements", body={"warehouse_id": warehouse_id, "statement": _safe_ratio_sql(spec), "wait_timeout": "30s", "on_wait_timeout": "CONTINUE"})
    deadline = time.monotonic() + timeout_seconds
    while result.get("status", {}).get("state") in {"PENDING", "RUNNING"}:
        statement_id = result.get("statement_id")
        if not statement_id or time.monotonic() > deadline:
            raise TimeoutError("La prueba remota no terminó")
        time.sleep(2)
        result = api.do("GET", f"/api/2.0/sql/statements/{statement_id}")
    if result.get("status", {}).get("state") != "SUCCEEDED":
        raise ValueError("La prueba remota falló: " + str(result.get("status", {})))
    rows = result.get("result", {}).get("data_array", [])
    if len(rows) != 3 or [str(row[0]) for row in rows] != ["1", "2", "3"]:
        raise ValueError("Resultado incompleto de prueba remota")
    if Decimal(str(rows[0][1])) != Decimal(2) or rows[1][1] is not None or rows[2][1] is not None:
        raise ValueError("El cálculo Silver no satisface positivo/cero/NULL")
    return True
