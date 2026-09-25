"""Fail-closed pilot workflow: read, analyze, edit, validate, review, PR."""

from __future__ import annotations

import difflib
import json
from dataclasses import dataclass
from decimal import Decimal

from .contracts import ClientProfile, Story
from .notebook_edit import (
    EXPRESSION,
    MEASURE,
    apply_pilot_measure,
    extract_pilot_source,
)

DEFAULT_NOTEBOOK = "notebooks/comercial/silver/04_business_derivations.ipynb"


@dataclass(frozen=True)
class RunReport:
    story_id: str
    base_sha: str
    branch: str
    pr_url: str
    diff: str
    model_cost_usd: Decimal | None
    remote_check: str


def _json_response(models, role: str, prompt: str) -> dict:
    response = models.complete(role, prompt)
    body = response.text.strip()
    if body.startswith("```json\n") and body.endswith("```"):
        body = body[len("```json\n"):-3].strip()
    elif body.startswith("```\n") and body.endswith("```"):
        body = body[len("```\n"):-3].strip()
    try:
        value = json.loads(body)
    except json.JSONDecodeError as error:
        raise ValueError(f"Salida no JSON del rol {role}") from error
    if not isinstance(value, dict):
        raise TypeError(f"Salida inesperada del rol {role}")
    return value


def run_story(story: Story, profile: ClientProfile, github, models, sandbox_verify) -> RunReport:
    path = profile.pilot.get("notebook", DEFAULT_NOTEBOOK)
    if not profile.allows(path):
        raise ValueError("El notebook queda fuera de las rutas permitidas")
    if profile.base_branch != "develop":
        raise ValueError("El piloto exige base develop")
    if not all(term in story.business_rules for term in ("margen_bruto", "costo_total")):
        raise ValueError("La HU no describe la medida aprobada para este piloto")
    branch = profile.feature_branch(story)
    base_sha = github.base_sha(profile.base_branch)
    original, source_sha = github.read_file(path, ref=profile.base_branch)
    original_source = extract_pilot_source(original)
    analyst = _json_response(models, "analyst", json.dumps({"task": "Confirma que la HU afecta únicamente la medida indicada; responde valid y notes", "story": story.model_dump(), "path": path, "source_excerpt": original_source[:12000]}, ensure_ascii=False))
    if analyst.get("valid") is not True:
        raise ValueError("El analista no aprobó el alcance de la HU")
    developer = _json_response(models, "developer", json.dumps({"task": "Propón la expresión Python exacta de margen_sobre_costo_pct como expression; no cambies otros campos", "story": story.model_dump(), "source_excerpt": original_source[:12000]}, ensure_ascii=False))
    if developer.get("expression") != EXPRESSION:
        raise ValueError("La expresión propuesta no coincide con la regla aprobada")
    updated = apply_pilot_measure(original)
    updated_source = extract_pilot_source(updated)
    compile(updated_source, path, "exec")
    if updated_source.count(f".withColumn('{MEASURE}', {EXPRESSION})") != 1:
        raise ValueError("La edición no cumple el contrato Silver")
    if not sandbox_verify(updated_source):
        raise ValueError("Falló la validación remota en sandbox")
    diff = "\n".join(difflib.unified_diff(original.splitlines(), updated.splitlines(), fromfile=path, tofile=path, lineterm=""))
    verifier = _json_response(models, "verifier", json.dumps({"task": "Revisa el diff y las pruebas. Responde approved boolean y notes", "story": story.model_dump(), "diff": diff, "remote_check": "three synthetic SQL rows: positive, zero, NULL passed"}, ensure_ascii=False))
    if verifier.get("approved") is not True:
        raise ValueError("El verificador rechazó el cambio")
    costs = [getattr(call, "cost_usd", None) for call in getattr(models, "calls", [])]
    model_cost = sum(costs, Decimal(0)) if costs and all(cost is not None for cost in costs) else None
    body = (
        f"## HU {story.id}\n{story.title}\n\n"
        f"- Rama base: `{profile.base_branch}` @ `{base_sha}`\n"
        f"- Cambio: `{MEASURE} = margen_bruto / costo_total`, NULL para costo cero o NULL.\n"
        "- Gates: sintaxis Python, expresión exacta, prueba remota con tres filas sintéticas y revisión Haiku.\n"
        f"- Costo estimado de modelos: {model_cost if model_cost is not None else 'uso no reportado'} USD.\n"
        "- Validación humana pendiente; sin merge ni despliegue de NaturaPet.\n"
    )
    pr_url = github.create_feature_pr(profile.repository, branch, profile.base_branch, story.title, body, base_sha, {path: (updated, source_sha)})
    return RunReport(story.id, base_sha, branch, pr_url, diff, model_cost, "passed")
