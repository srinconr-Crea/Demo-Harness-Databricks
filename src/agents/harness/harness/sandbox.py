"""Remote SQL check on the isolated harness warehouse with synthetic values."""

from __future__ import annotations

import time
from decimal import Decimal
from pathlib import Path

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
    from .validation import validate_file, validation_plan
    plan = validation_plan(profile, paths)
    evidence = []
    for check in plan['checks']:
        if check['adapter'] not in {'pytest_sandbox', 'databricks_bundle_validate'}:
            evidence.append(validate_file(root, check['path'], check['adapter'], policy.schemas))
    binding = {'revision': revision, 'validation_plan': plan}
    if plan['requires_job']:
        if job_runner is None:
            raise ValueError('Los cambios de código requieren un Job sandbox dedicado')
        kwargs = {'run_id': run_id, 'attempt_id': attempt_id, 'revision': revision, 'test_paths': plan['test_paths']}
        # The production runner supports the new trusted bundle parameters.
        from .sandbox_job import SandboxJobRunner
        if isinstance(job_runner, SandboxJobRunner):
            kwargs.update(profile=profile, bundle_target=plan['bundle_target'])
        result = job_runner.run(root, **kwargs)
        return {**binding, 'passed': result.get('passed') is True,
                'evidence': evidence + list(result.get('evidence') or []),
                'job_run_id': result.get('job_run_id'), 'archive_sha256': result.get('archive_sha256')}
    return {**binding, 'passed': True, 'evidence': evidence}
