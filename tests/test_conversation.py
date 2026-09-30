import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from harness.checkout import GitCheckout
from harness.contracts import ClientProfile, StoryRequest
from harness.coordination import SqliteRunCoordinator
from harness.conversation import ConversationEngine
from harness.store import LocalRunStore
from test_notebook_edit import fixture_notebook


def git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class FakeGithub:
    def __init__(self, source, sha):
        self.source, self.sha = source, sha
        self.published = []
        self.fail_check_once = False

    def base_sha(self, branch):
        assert branch == "develop"
        return self.sha

    def checkout(self, destination, base_sha):
        GitCheckout(self.source.as_uri(), "develop").clone(destination, base_sha, token="fake-token")

    def create_feature_pr(self, repository, branch, base_branch, title, body, base_sha, files, **kwargs):
        self.published.append(files)
        assert repository == "example/client" and branch.startswith("feature/")
        assert base_branch == "develop" and base_sha == self.sha
        if kwargs.get("on_progress"):
            kwargs["on_progress"]("branch_created", branch=branch, base_sha=base_sha, commit_sha="c" * 40)
            kwargs["on_progress"]("pr_created", branch=branch, pr_url="https://github.com/example/client/pull/7")
        return "https://github.com/example/client/pull/7"

    def pr_check_status(self, *_args):
        if self.fail_check_once:
            self.fail_check_once = False
            raise RuntimeError("checks temporarily unavailable")
        return "pending"


class FakeCLI:
    def new_change(self, root, name):
        (root / "openspec" / "changes" / name).mkdir(parents=True)

    def instructions(self, root, artifact, name):
        suffix = {"proposal": "proposal.md", "design": "design.md", "tasks": "tasks.md"}.get(artifact, "specs")
        return {"schemaName": "spec-driven", "changeDir": str(root / "openspec" / "changes" / name),
                "resolvedOutputPath": str(root / "openspec" / "changes" / name / suffix),
                "instruction": "write", "template": "", "context": "", "rules": []}

    def validate(self, root, name):
        assert (root / "openspec" / "changes" / name / "proposal.md").is_file()

    def archive(self, root, name):
        change = root / "openspec" / "changes" / name
        archive = root / "openspec" / "changes" / "archive" / name
        archive.parent.mkdir(parents=True, exist_ok=True)
        change.rename(archive)
        (root / "openspec" / "specs" / name).mkdir(parents=True)
        (root / "openspec" / "specs" / name / "spec.md").write_text("# Synced\n", encoding="utf-8")


class FakeModels:
    def __init__(self):
        self.calls = []

    def complete(self, role, prompt, **kwargs):
        self.calls.append((role, kwargs.get("stage")))
        if role == "explorer":
            value = {"summary": "Se requiere una actualización pequeña", "questions": [] if json.loads(prompt).get('clarifications') else ["¿Qué salida espera?"]}
        elif role == "planner":
            artifact = json.loads(prompt)["artifact"]
            value = {"summary": "Cambiar VALUE a 2; probar salida. La aprobación autoriza crear el PR automáticamente.",
                     "manifest": [{'op': 'modify', 'path': 'src/value.py'}], "content": {
                "proposal": "# Proposal\n\n## Why\nSe necesita salida nueva.\n\n## What Changes\nAñadir salida.\n",
                "specs": "# Spec Delta\n\n## ADDED Requirements\n\n### Requirement: Salida\nEl sistema SHALL cambiar salida.\n\n#### Scenario: Correcto\n- **WHEN** se llama\n- **THEN** devuelve 2\n",
                "design": "# Design\n\n## Context\nCódigo cliente.\n\n## Decisions\nCambiar función.\n",
                "tasks": "# Tasks\n\n- [ ] 1.1 Cambiar función y verificar salida.\n",
            }[artifact]}
        elif role == "developer":
            previous = b"VALUE = 2\n" if "VALUE = 2" in json.loads(prompt).get("source_summary", "") else b"VALUE = 1\n"
            value = {"operations": [{"op": "modify", "path": "src/value.py", "content": "VALUE = 2\n",
                                      "expected_sha256": hashlib.sha256(previous).hexdigest()}], "notes": "Cambio aplicado"}
        else:
            value = {"approved": True, "findings": []}
        return type("Response", (), {"text": json.dumps(value, ensure_ascii=False)})()


def make_engine(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    git("init", "-b", "develop", str(source))
    git("config", "user.email", "test@example.com", cwd=source)
    git("config", "user.name", "Test", cwd=source)
    (source / "src").mkdir()
    (source / "src" / "value.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "openspec" / "specs").mkdir(parents=True)
    (source / "openspec" / "changes").mkdir()
    (source / "openspec" / "config.yaml").write_text("schema: spec-driven\ncontext: Cliente preparado\n", encoding="utf-8")
    (source / "openspec" / "specs" / ".gitkeep").write_text("", encoding="utf-8")
    (source / "openspec" / "changes" / ".gitkeep").write_text("", encoding="utf-8")
    git("add", ".", cwd=source)
    git("commit", "-m", "base", cwd=source)
    sha = git("rev-parse", "HEAD", cwd=source)
    profile = ClientProfile(repository="example/client", base_branch="develop", allowed_paths=["src/"],
                            openspec_root="openspec", general_patch={"allowed_paths": ["src/"],
                            "extensions": [".py"], "operations": ["modify"], "max_files": 2,
                            "max_bytes": 1000, "test_adapters": ["python_compile", "pytest_sandbox"],
                            "test_paths": ["tests"]})
    store = LocalRunStore(tmp_path.parent / "records")
    coordinator = SqliteRunCoordinator(tmp_path / "state.db")
    github = FakeGithub(source, sha)
    models = FakeModels()
    engine = ConversationEngine(profile, store, coordinator, lambda: github,
                                lambda _run, _attempt: models, FakeCLI(),
                                lambda _root, _profile, _paths, _record, _attempt: {"passed": True, "evidence": ["synthetic test passed"]})
    engine.publication_mode = 'diff_review'  # Exercise the persisted historical modality in these tests.
    return engine, github, models, store, coordinator, profile


def test_full_conversation_waits_for_both_human_approvals(tmp_path: Path):
    engine, github, models, store, coordinator, profile = make_engine(tmp_path)
    run_id = engine.submit(StoryRequest(hu="HU-9", description="Cambiar VALUE a 2"), actor="ana@example.com")
    engine.advance(run_id)
    run = store.load(run_id)
    assert run["state"] == "awaiting_clarification"
    engine.act(run_id, "answer", actor="ana@example.com", text="La salida debe ser 2", expected_revision=0, key="answer-1")
    run = store.load(run_id)
    attempt = run["attempts"][-1]
    assert run["state"] == "awaiting_plan_review"
    assert github.published == []
    assert len([event for event in attempt["timeline"] if event["kind"] == "artifact_ready"]) == 4
    with pytest.raises(ValueError, match="obsolet"):
        engine.act(run_id, "approve", actor="ana@example.com", expected_revision=0,
                   expected_hash=attempt["context"]["plan_hash"], key="stale")
    engine.act(run_id, "approve", actor="ana@example.com", expected_revision=attempt["revision"],
               expected_hash=attempt["context"]["plan_hash"], key="plan-1")
    run = store.load(run_id)
    attempt = run["attempts"][-1]
    assert run["state"] == "awaiting_diff_review"
    assert github.published == []
    assert "VALUE = 2" in store.load_review_diff(run_id, attempt["attempt_id"], attempt["revision"], attempt["context"]["diff_sha256"])
    engine.act(run_id, "approve", actor="ana@example.com", expected_revision=attempt["revision"],
               expected_hash=attempt["context"]["candidate_hash"], key="diff-1")
    assert store.load(run_id)["state"] == "complete"
    assert len(github.published) == 1
    assert "src/value.py" in github.published[0]
    assert any(role == "developer" and stage == "applying" for role, stage in models.calls)


def test_restart_keeps_plan_wait_and_exact_revision(tmp_path: Path):
    engine, github, models, store, coordinator, profile = make_engine(tmp_path)
    run_id = engine.submit(StoryRequest(hu="HU-10", description="Cambiar VALUE"), actor="ana@example.com")
    engine.advance(run_id)
    engine.act(run_id, "answer", actor="ana@example.com", text="Dos", expected_revision=0, key="answer-1")
    before = store.load(run_id)["attempts"][-1]
    restarted = ConversationEngine(profile, store, coordinator, lambda: github,
                                   lambda _run, _attempt: models, FakeCLI(),
                                   lambda _root, _profile, _paths, _record, _attempt: {"passed": True, "evidence": ["ok"]})
    assert restarted.get(run_id)["state"] == "awaiting_plan_review"
    assert restarted.get(run_id)["attempts"][-1]["context"]["plan_hash"] == before["context"]["plan_hash"]


def test_diff_correction_restores_prearchive_change_before_update(tmp_path: Path):
    engine, github, _models, store, _coordinator, _profile = make_engine(tmp_path)
    run_id = engine.submit(StoryRequest(hu="HU-11", description="Cambiar VALUE"), actor="ana@example.com")
    engine.advance(run_id)
    engine.act(run_id, "answer", actor="ana@example.com", text="Dos", expected_revision=0, key="answer-1")
    attempt = store.load(run_id)["attempts"][-1]
    engine.act(run_id, "approve", actor="ana@example.com", expected_revision=attempt["revision"],
               expected_hash=attempt["context"]["plan_hash"], key="plan-1")
    attempt = store.load(run_id)["attempts"][-1]
    engine.act(run_id, "changes", actor="ana@example.com", expected_revision=attempt["revision"],
               text="Aclarar el diseño", key="changes-1")
    updated = store.load(run_id)["attempts"][-1]
    assert updated["stage"] == "awaiting_plan_review"
    checkpoint = store.load_checkpoint(run_id, updated["attempt_id"], updated["checkpoint_id"])
    assert any(path.endswith("/proposal.md") and "/archive/" not in path for path in checkpoint["files"])
    assert github.published == []


def test_base_advance_invalidates_approved_candidate(tmp_path: Path):
    engine, github, _models, store, _coordinator, _profile = make_engine(tmp_path)
    run_id = engine.submit(StoryRequest(hu="HU-12", description="Cambiar VALUE"), actor="ana@example.com")
    engine.advance(run_id)
    engine.act(run_id, "answer", actor="ana@example.com", text="Dos", expected_revision=0, key="answer-1")
    attempt = store.load(run_id)["attempts"][-1]
    engine.act(run_id, "approve", actor="ana@example.com", expected_revision=attempt["revision"],
               expected_hash=attempt["context"]["plan_hash"], key="plan-1")
    attempt = store.load(run_id)["attempts"][-1]
    (github.source / "README.md").write_text("new base\n", encoding="utf-8")
    git("add", ".", cwd=github.source)
    git("commit", "-m", "advance base", cwd=github.source)
    github.sha = git("rev-parse", "HEAD", cwd=github.source)
    engine.act(run_id, "approve", actor="ana@example.com", expected_revision=attempt["revision"],
               expected_hash=attempt["context"]["candidate_hash"], key="diff-1")
    updated = store.load(run_id)["attempts"][-1]
    assert updated["stage"] == "awaiting_clarification"
    assert updated["base_sha"] == github.sha
    assert "candidate_hash" not in updated["context"]
    assert github.published == []


def test_ratio_editor_remains_available_in_conversational_apply(tmp_path: Path):
    engine, github, models, store, _coordinator, _profile = make_engine(tmp_path)
    notebook_path = "notebooks/comercial/silver/04_business_derivations.ipynb"
    target = github.source / notebook_path
    target.parent.mkdir(parents=True)
    target.write_text(fixture_notebook(), encoding="utf-8")
    git("add", ".", cwd=github.source)
    git("commit", "-m", "ratio fixture", cwd=github.source)
    github.sha = git("rev-parse", "HEAD", cwd=github.source)
    engine.profile = ClientProfile(
        repository="example/client", base_branch="develop",
        allowed_paths=["notebooks/comercial/silver/"], openspec_root="openspec",
        strategy={"kind": "silver_safe_ratio", "notebook": notebook_path,
                  "table": "fact_ventas_cabecera", "anchor_column": "margen_pct",
                  "allowed_source_columns": ["margen_bruto", "costo_total", "base_neta_sin_iva"]},
    )

    class RatioModels(FakeModels):
        def complete(self, role, prompt, **kwargs):
            if role == "developer":
                self.calls.append((role, kwargs.get("stage")))
                return type("Response", (), {"text": json.dumps({"expression": json.loads(prompt)["expected_expression"]})})()
            return super().complete(role, prompt, **kwargs)

    models = RatioModels()
    engine.models_factory = lambda _run, _attempt: models
    run_id = engine.submit(StoryRequest(
        hu="HU-RATIO", description="En fact_ventas_cabecera: margen_sobre_costo_pct = margen_bruto / costo_total; NULL si costo es cero o NULL",
    ), actor="ana@example.com")
    engine.advance(run_id)
    engine.act(run_id, "answer", actor="ana@example.com", text="Validar tres casos", expected_revision=0, key="answer-ratio")
    attempt = store.load(run_id)["attempts"][-1]
    engine.act(run_id, "approve", actor="ana@example.com", expected_revision=attempt["revision"],
               expected_hash=attempt["context"]["plan_hash"], key="plan-ratio")
    attempt = store.load(run_id)["attempts"][-1]
    assert attempt["stage"] == "awaiting_diff_review"
    assert attempt["context"]["ratio_spec"]["output_column"] == "margen_sobre_costo_pct"
    assert "margen_sobre_costo_pct" in store.load_review_diff(run_id, attempt["attempt_id"], attempt["revision"], attempt["context"]["diff_sha256"])


def test_failed_client_tests_return_to_plan_revision_without_diff(tmp_path: Path):
    engine, github, _models, store, _coordination, _profile = make_engine(tmp_path)
    engine.test_runner = lambda *_args: {"passed": False, "evidence": ["assertion failed"]}
    run_id = engine.submit(StoryRequest(hu="HU-FAIL", description="Cambiar salida"), actor="ana@example.com")
    engine.advance(run_id)
    engine.act(run_id, "answer", actor="ana@example.com", text="Salida 2", expected_revision=0, key="answer-fail")
    attempt = store.load(run_id)["attempts"][-1]
    engine.act(run_id, "approve", actor="ana@example.com", expected_revision=attempt["revision"],
               expected_hash=attempt["context"]["plan_hash"], key="plan-fail")
    updated = store.load(run_id)["attempts"][-1]
    assert updated["stage"] == "awaiting_plan_review"
    assert updated["revision"] == 2
    assert any(event["kind"] == "verify_failed" for event in updated["timeline"])
    assert github.published == []


def test_full_synthetic_story_corrects_failed_test_then_creates_pr(tmp_path: Path):
    engine, github, models, store, _coordination, _profile = make_engine(tmp_path)
    checks = iter([False, True])
    engine.test_runner = lambda *_args: {"passed": next(checks), "evidence": ["synthetic"]}
    run_id = engine.submit(StoryRequest(hu="HU-REPAIR", description="VALUE debe ser 2"), actor="ana@example.com")
    engine.advance(run_id)
    engine.act(run_id, "answer", actor="ana@example.com", text="Salida 2", expected_revision=0, key="answer-repair")
    first = store.load(run_id)["attempts"][-1]
    engine.act(run_id, "approve", actor="ana@example.com", expected_revision=first["revision"],
               expected_hash=first["context"]["plan_hash"], key="plan-repair-1")
    second = store.load(run_id)["attempts"][-1]
    assert second["revision"] == 2 and second["stage"] == "awaiting_plan_review"
    engine.act(run_id, "approve", actor="ana@example.com", expected_revision=second["revision"],
               expected_hash=second["context"]["plan_hash"], key="plan-repair-2")
    candidate = store.load(run_id)["attempts"][-1]
    assert candidate["stage"] == "awaiting_diff_review"
    engine.act(run_id, "approve", actor="ana@example.com", expected_revision=candidate["revision"],
               expected_hash=candidate["context"]["candidate_hash"], key="diff-repair")
    final = store.load(run_id)["attempts"][-1]
    assert final["stage"] == "complete" and len(github.published) == 1
    assert {"explore", "propose", "verify_failed", "update", "archive", "diff_approved", "pr_created"}.issubset(
        {event["kind"] for event in final["timeline"]}
    )
    assert [role for role, _stage in models.calls].count("planner") == 8


def test_pr_identity_survives_failure_after_pr_creation(tmp_path: Path):
    engine, github, _models, store, _coordinator, _profile = make_engine(tmp_path)
    run_id = engine.submit(StoryRequest(hu="HU-PR-RETRY", description="VALUE debe ser 2"), actor="ana@example.com")
    engine.advance(run_id)
    engine.act(run_id, "answer", actor="ana@example.com", text="Salida 2", expected_revision=0, key="answer-pr")
    plan = store.load(run_id)["attempts"][-1]
    engine.act(run_id, "approve", actor="ana@example.com", expected_revision=plan["revision"],
               expected_hash=plan["context"]["plan_hash"], key="plan-pr")
    candidate = store.load(run_id)["attempts"][-1]
    github.fail_check_once = True
    with pytest.raises(RuntimeError, match="checks temporarily unavailable"):
        engine.act(run_id, "approve", actor="ana@example.com", expected_revision=candidate["revision"],
                   expected_hash=candidate["context"]["candidate_hash"], key="diff-pr")
    saved = store.load(run_id)["attempts"][-1]
    assert saved["stage"] == "publishing"
    assert saved["publication"]["pr_url"] == "https://github.com/example/client/pull/7"
    assert saved["publication"]["commit_sha"] == "c" * 40
    engine.advance(run_id)
    completed = store.load(run_id)
    assert completed["state"] == "complete"
    assert completed["attempts"][-1]["publication"]["commit_sha"] == "c" * 40
    assert completed["attempts"][-1]["timeline"][-1]["kind"] == "publication_complete"
