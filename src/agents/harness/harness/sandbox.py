"""Remote SQL check on the isolated harness warehouse with synthetic values."""

from __future__ import annotations

import time
import json
from pathlib import Path
from decimal import Decimal

import yaml

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


def verify_general_patch(root: Path, profile, paths: list[str], job_runner,
                         *, run_id: str, attempt_id: str, revision: int) -> dict:
    """Static checks plus a separate-identity Job for executable client changes."""
    policy = profile.general_patch
    if policy is None or not paths:
        raise ValueError("No hay una política de pruebas generales verificable")
    evidence = []
    executable = False
    for relative in paths:
        if not profile.allows(relative) or not any(relative.startswith(prefix.rstrip("/") + "/") for prefix in policy.allowed_paths):
            raise ValueError("Ruta de prueba fuera del perfil")
        path = root / relative
        suffix = path.suffix.lower()
        if not path.exists():
            executable = True
            evidence.append(f"Archivo eliminado: {relative}")
            continue
        if suffix == ".py":
            if "python_compile" not in policy.test_adapters:
                raise ValueError("Falta comprobación Python obligatoria")
            compile(path.read_text(encoding="utf-8"), relative, "exec")
            evidence.append(f"Sintaxis Python válida: {relative}")
            executable = True
        elif suffix == ".ipynb":
            if "python_compile" not in policy.test_adapters:
                raise ValueError("Falta comprobación de notebook obligatoria")
            notebook = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(notebook.get("cells"), list):
                raise ValueError("Notebook sin celdas válidas")
            for cell in notebook["cells"]:
                if cell.get("cell_type") == "code":
                    source = cell.get("source", [])
                    compile("".join(source) if isinstance(source, list) else source, relative, "exec")
            evidence.append(f"Estructura y sintaxis de notebook válidas: {relative}")
            executable = True
        elif suffix == ".md":
            if "markdown_structure" not in policy.test_adapters:
                raise ValueError("Falta comprobación Markdown obligatoria")
            content = path.read_text(encoding="utf-8")
            if not any(line.startswith("# ") for line in content.splitlines()):
                raise ValueError("Markdown sin título principal")
            evidence.append(f"Estructura Markdown válida: {relative}")
        elif suffix in {".yaml", ".yml", ".json"}:
            content = path.read_text(encoding="utf-8")
            json.loads(content) if suffix == ".json" else yaml.safe_load(content)
            evidence.append(f"Estructura de datos válida: {relative}")
            executable = True
        else:
            raise ValueError("El tipo de archivo no tiene un validador obligatorio")
    if executable:
        if "pytest_sandbox" not in policy.test_adapters or not policy.test_paths or job_runner is None:
            raise ValueError("Los cambios de código requieren un Job sandbox dedicado")
        result = job_runner.run(root, run_id=run_id, attempt_id=attempt_id,
                                revision=revision, test_paths=policy.test_paths)
        if result.get("passed") is not True:
            return {"passed": False, "evidence": evidence + list(result.get("evidence") or []),
                    "job_run_id": result.get("job_run_id")}
        return {"passed": True, "evidence": evidence + list(result.get("evidence") or []),
                "job_run_id": result.get("job_run_id")}
    return {"passed": True, "evidence": evidence}
