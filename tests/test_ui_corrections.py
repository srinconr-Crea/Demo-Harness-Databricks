"""Exercise the UI with persisted correction/candidate fixtures and a small DOM."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest


PAGE = Path(__file__).resolve().parents[1] / "src/agents/harness/app/index.html"


def render_fixture(attempt, checklist):
    source = PAGE.read_text(encoding="utf-8")
    functions = source[source.index("function showChecklist(run)"):source.index("fetch('/configuration')")]
    categories = source[source.index("const categoryLabels="):source.index("function actionStatus")]
    script = """
const elements={};
function node(tag,text){return {tag,text,children:[],append(...items){this.children.push(...items)}};}
const document={getElementById(id){return elements[id]??=Object.assign(node('div'),{replaceChildren(){this.children=[]}})}};
function texts(element){return [element.text??'',...element.children.flatMap(texts)].filter(Boolean);}
""" + categories + functions + "\nconst attempt=" + json.dumps(attempt) + ";\n"
    script += "showChecklist({attempts:[attempt],checklist:" + json.dumps(checklist) + "});showCorrection(attempt);"
    script += "process.stdout.write(JSON.stringify(Object.fromEntries(Object.entries(elements).map(([k,v])=>[k,texts(v)]))));"
    executable = shutil.which("node")
    if not executable:
        pytest.skip("Node is required for the UI fixture")
    result = subprocess.run([executable, "-"], input=script, text=True, encoding="utf-8", capture_output=True, check=True)
    return json.loads(result.stdout)


def test_correction_keeps_plan_revision_and_shows_pending_current_candidate():
    attempt = {
        "stage": "correcting", "revision": 3,
        "context": {"implementation_correction_count": 1, "candidate_revision": 2, "code_candidate_hash": "new"},
        "tests": {"passed": True, "candidate_hash": "old"},
        "timeline": [{"kind": "failure_classified", "details": {"route": "correcting", "findings": [{"category": "implementation", "criterion": "Import correcto", "code": "Import incorrecto."}]}}],
    }
    rendered = render_fixture(attempt, [{"phase": "verify", "status": "ok"}])
    assert "verify: Pendiente" in rendered["checklist"][0]
    assert any("1 de 2 · Revisión del plan 3" in text for text in rendered["correction"])
    assert "Causa: Implementación" in rendered["correction"]
    assert "Import correcto: Import incorrecto." in rendered["correction"]
    assert any("Verificación pendiente" in text for text in rendered["correction"])


def test_previous_success_does_not_verify_new_bytes_after_correcting():
    rendered = render_fixture({
        "stage": "verifying", "revision": 1,
        "context": {"code_candidate_hash": "new"},
        "tests": {"candidate_hash": "old"},
        "timeline": [{"kind": "correction_started", "details": {"category": "implementation"}}],
    }, [{"phase": "verify", "status": "ok"}])
    assert "verify: Pendiente" in rendered["checklist"][0]
    assert any("Verificación pendiente" in text for text in rendered["correction"])


def test_verified_current_candidate_and_historical_workflow_remain_visible():
    for context, tests in [({}, {}), ({"code_candidate_hash": "same", "tests": {"candidate_hash": "same"}}, {})]:
        rendered = render_fixture({"stage": "complete", "revision": 1, "context": context, "tests": tests, "timeline": []},
                                  [{"phase": "verify", "status": "ok"}])
        assert "verify: OK" in rendered["checklist"][0]
        assert rendered["correction"] == []


def test_advisory_preserves_haiku_unavailability_without_correction():
    rendered = render_fixture({"stage": "verifying", "revision": 1,
                               "context": {"advisory": {"status": "failed", "findings": []}}, "timeline": []}, [])
    assert "Recomendaciones de Haiku · No disponible" in rendered["advisory"]
    assert rendered["correction"] == []
