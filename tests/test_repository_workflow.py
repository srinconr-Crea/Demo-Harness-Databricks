import hashlib
import io
import json
import zipfile

import pytest
import yaml
from fastapi.testclient import TestClient
from harness.contracts import ClientProfile, RunAttempt, StoryRequest
from harness.conversation_webapp import create_conversation_app
from harness.models import ModelInvocationError
from harness.patch import FileOperation, apply_file_operations
from harness.progress import checklist
from harness.repo_context import RepoContext, contextual_answer
from harness.sandbox_job import SandboxJobRunner
from harness.validation import (
    notebook_validate,
    validate_file,
    validation_plan,
)
from jsonschema import ValidationError
from sqlglot.errors import ParseError
from test_conversation import FakeModels, make_engine


def repository_profile():
    return ClientProfile(
        repository="example/client",
        base_branch="develop",
        openspec_root="openspec",
        repository_policy={
            "scope": "repository",
            "read_only_paths": [".github/", "openspec/", "AGENTS.md", "locked/"],
            "denied_paths": ["private/"],
        },
        general_patch={
            "extensions": [
                ".py",
                ".sql",
                ".ipynb",
                ".yaml",
                ".yml",
                ".json",
                ".toml",
                ".md",
                ".txt",
            ],
            "operations": ["create", "modify", "delete"],
            "max_files": 100,
            "max_bytes": 5000000,
            "test_adapters": [
                "python_compile",
                "pytest_sandbox",
                "sql_lint",
                "yaml_validate",
                "json_validate",
                "toml_validate",
                "notebook_validate",
                "markdown_structure",
                "text_validate",
                "databricks_bundle_validate",
            ],
            "test_paths": ["tests"],
            "bundle_target": "sandbox",
            "impact_rules": [
                {"paths": ["config/"], "test_paths": ["tests/test_config.py"]}
            ],
            "schemas": {"config.json": {"type": "object", "required": ["value"]}},
        },
    )


@pytest.mark.parametrize(
    "path",
    [
        ".github",
        ".github/workflows/x.yaml",
        "openspec/specs/x.md",
        "AGENTS.md",
        ".git",
        ".git/config",
        "nested/.git/config",
        ".env",
        ".envrc",
        "private/a.py",
        "locked/a.py",
        "../escape.py",
        "C:/escape.py",
        "src/../a.py",
    ],
)
def test_repository_protected_paths(path, tmp_path):
    profile = repository_profile()
    assert not profile.allows_code(path)
    with pytest.raises(ValueError):
        apply_file_operations(
            tmp_path, profile, [FileOperation(op="create", path=path, content="x")]
        )


def test_repository_root_operations_are_atomic(tmp_path):
    profile = repository_profile()
    apply_file_operations(
        tmp_path,
        profile,
        [FileOperation(op="create", path="config.json", content='{"value":2}')],
    )
    with pytest.raises(ValueError):
        apply_file_operations(
            tmp_path,
            profile,
            [
                FileOperation(op="create", path="new.txt", content="new"),
                FileOperation(
                    op="modify",
                    path="config.json",
                    content="{}",
                    expected_sha256="0" * 64,
                ),
            ],
        )
    assert not (tmp_path / "new.txt").exists()
    assert profile.allows(
        "src-other/value.py"
    )  # Repository scope deliberately includes this path.


def test_context_read_only_and_denied_search_and_hash(tmp_path):
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github/x.yaml").write_text("value: 2")
    (tmp_path / ".env").write_text("SENSITIVE=value")
    context = RepoContext(tmp_path, repository_profile())
    result = context.request({"op": "read_file", "path": ".github/x.yaml"})
    assert result["sha256"] == hashlib.sha256(b"value: 2").hexdigest()
    assert context.request({"op": "list_tree"})["paths"] == [".github/x.yaml"]
    assert context.request({"op": "search_text", "query": "SENSITIVE"})["matches"] == []
    with pytest.raises(ValueError):
        context.request({"op": "read_file", "path": ".env"})
    context.policy.max_reads = 1
    with pytest.raises(ValueError, match="lecturas"):
        context.request({"op": "read_file", "path": ".github/x.yaml"})


def test_context_rounds_and_explicit_truncation(tmp_path):
    (tmp_path / "value.txt").write_text("x" * 2000)
    context = RepoContext(tmp_path, repository_profile())
    context.policy.max_context_bytes = 1000
    assert context.request({"op": "read_file", "path": "value.txt"})["truncated"]

    class Model:
        def complete(self, *_args, **kwargs):
            return type(
                "Response",
                (),
                {"text": json.dumps({"context_request": {"op": "list_tree"}})},
            )()

    context.policy.max_rounds = 2
    with pytest.raises(ValueError, match="rondas"):
        contextual_answer(Model(), "developer", {}, context)


def test_adapter_selection_covers_impact_and_bundle():
    profile = repository_profile()
    plan = validation_plan(
        profile, ["config/app.yaml", "resources/job.yml", "query.sql"]
    )
    assert {
        "pytest_sandbox",
        "yaml_validate",
        "databricks_bundle_validate",
        "sql_lint",
    } <= {c["adapter"] for c in plan["checks"]}
    assert (
        "tests/test_config.py" in plan["test_paths"]
        and plan["bundle_target"] == "sandbox"
    )
    profile.general_patch.test_adapters.remove("sql_lint")
    with pytest.raises(ValueError, match="validador"):
        validation_plan(profile, ["query.sql"])


@pytest.mark.parametrize(
    "name,adapter,valid,invalid",
    [
        ("x.sql", "sql_lint", "SELECT 1", "SELECT ( FROM"),
        ("x.yaml", "yaml_validate", "value: 2", "value: [oops"),
        ("x.json", "json_validate", '{"value":2}', "{oops"),
        ("x.toml", "toml_validate", "value = 2", "value = ["),
        ("x.py", "python_compile", "VALUE = 2", "def ("),
        ("x.md", "markdown_structure", "# Title", "missing title"),
        ("x.txt", "text_validate", "text", "text\0binary"),
    ],
)
def test_static_adapters_positive_negative(tmp_path, name, adapter, valid, invalid):
    path = tmp_path / name
    path.write_text(valid)
    assert "válido" in validate_file(tmp_path, name, adapter, {})
    path.write_text(invalid)
    with pytest.raises((ValueError, SyntaxError, yaml.YAMLError, ParseError)):
        validate_file(tmp_path, name, adapter, {})


def test_schema_rejects_missing_required_and_external_references(tmp_path):
    (tmp_path / "config.json").write_text("{}")
    with pytest.raises(ValidationError):
        validate_file(
            tmp_path,
            "config.json",
            "json_validate",
            repository_profile().general_patch.schemas,
        )
    with pytest.raises(ValueError, match="externa"):
        validate_file(
            tmp_path,
            "config.json",
            "json_validate",
            {"config.json": {"$ref": "https://example.com/schema"}},
        )


def test_notebook_languages_magics_and_invalid_syntax():
    import nbformat

    notebook = nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_code_cell("%sql\nSELECT 1"),
            nbformat.v4.new_code_cell("value = 2"),
        ]
    )
    notebook_validate(nbformat.writes(notebook))
    notebook.cells[0].source = "%sh\ncat /etc/passwd"
    with pytest.raises(ValueError, match="Lenguaje"):
        notebook_validate(nbformat.writes(notebook))
    with pytest.raises(ValueError):
        notebook_validate('{"cells": []}')


def test_archive_excludes_secrets_but_includes_read_only(tmp_path):
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github/x.yml").write_text("read only")
    (tmp_path / ".env").write_text("secret")
    (tmp_path / "private").mkdir()
    (tmp_path / "private/x.txt").write_text("secret")
    with zipfile.ZipFile(
        io.BytesIO(SandboxJobRunner._archive(tmp_path, repository_profile()))
    ) as archive:
        assert archive.namelist() == [".github/x.yml"]


def prepare_new_run(tmp_path, model=None):
    engine, github, _models, store, _coordinator, _profile = make_engine(tmp_path)
    engine.publication_mode = "approved_plan"
    if model:
        engine.models_factory = lambda *_args: model
    run_id = engine.submit(
        StoryRequest(hu="HU-AUTO", description="Cambiar VALUE a 2"),
        actor="ana@example.com",
    )
    engine.advance(run_id)
    engine.act(
        run_id,
        "answer",
        actor="ana@example.com",
        text="Dos",
        expected_revision=0,
        key="answer",
    )
    return engine, github, store, run_id


@pytest.mark.parametrize("advice", ["reject", "invalid", "timeout"])
def test_new_story_publishes_automatically_with_advisory_failures(tmp_path, advice):
    class Model(FakeModels):
        def complete(self, role, prompt, **kwargs):
            if role == "verifier":
                if advice == "timeout":
                    raise ModelInvocationError("timeout")
                return type(
                    "Response",
                    (),
                    {
                        "text": "bad"
                        if advice == "invalid"
                        else '{"approved":false,"findings":["Review naming"]}'
                    },
                )()
            return super().complete(role, prompt, **kwargs)

    engine, github, store, run_id = prepare_new_run(tmp_path, Model())
    attempt = store.load(run_id)["attempts"][-1]
    engine.act(
        run_id,
        "approve",
        actor="ana@example.com",
        expected_revision=attempt["revision"],
        expected_hash=attempt["context"]["plan_hash"],
        key="plan",
    )
    run = engine.get(run_id)
    assert run["state"] == "complete" and len(github.published) == 1
    final = run["attempts"][-1]
    assert [a["kind"] for a in final["approvals"]] == ["plan"]
    assert not final["context"].get("correction_count")
    assert all(
        row["status"] == "ok" for row in run["checklist"] if row["phase"] not in {"update", "correcting"}
    )
    if advice == "reject":
        from harness.checkout import restore_checkpoint

        root = tmp_path / "tampered-candidate"
        github.checkout(root, final["base_sha"])
        restore_checkpoint(
            root,
            store.load_checkpoint(run_id, final["attempt_id"], final["checkpoint_id"]),
            final["base_sha"],
            engine._allows,
        )
        (root / "src/value.py").write_text("VALUE = 99\n")
        final["stage"] = "publishing"
        with pytest.raises(ValueError, match="candidato"):
            engine._step(root, run, final, github, Model(), None)
        assert len(github.published) == 1
    with TestClient(create_conversation_app(engine, engine.profile)) as client:
        assert (
            client.get(
                f"/runs/{run_id}/diff", headers={"x-forwarded-user": "ana@example.com"}
            ).status_code
            == 200
        )


def test_storage_errors_are_not_swallowed_as_advisory(tmp_path):
    class Model(FakeModels):
        def complete(self, role, prompt, **kwargs):
            if role == "verifier":
                raise ValueError("checkpoint damaged")
            return super().complete(role, prompt, **kwargs)

    engine, github, store, run_id = prepare_new_run(tmp_path, Model())
    attempt = store.load(run_id)["attempts"][-1]
    with pytest.raises(ValueError, match="damaged"):
        engine.act(
            run_id,
            "approve",
            actor="ana@example.com",
            expected_revision=attempt["revision"],
            expected_hash=attempt["context"]["plan_hash"],
            key="plan",
        )
    assert not github.published


def test_candidate_tamper_and_missing_tests_block_publication(tmp_path):
    engine, github, store, run_id = prepare_new_run(tmp_path)
    attempt = store.load(run_id)["attempts"][-1]
    engine.test_runner = lambda *_args: {"passed": False, "evidence": ["test missing"]}
    engine.act(
        run_id,
        "approve",
        actor="ana@example.com",
        expected_revision=attempt["revision"],
        expected_hash=attempt["context"]["plan_hash"],
        key="plan",
    )
    assert (
        engine.get(run_id)["state"] == "failed" and not github.published
    )
    assert (
        RunAttempt(attempt_id="legacy", state="queued").publication_mode
        == "diff_review"
    )


def test_checklist_never_infers_archive_or_pr_success():
    attempt = {
        "revision": 1,
        "stage": "publishing",
        "timeline": [
            {
                "seq": 1,
                "kind": "sync",
                "stage": "preparing_final_diff",
                "revision": 1,
                "at": "2026-09-30T15:00:00Z",
            }
        ],
    }
    rows = {r["phase"]: r for r in checklist(attempt)}
    assert (
        rows["sync"]["status"] == "ok"
        and rows["archive"]["status"] == "pending"
        and rows["PR"]["status"] == "running"
    )


def test_context_symlink_and_prefix_neighbor_are_rejected(tmp_path, monkeypatch):
    (tmp_path / "link.txt").write_text("should not read")
    original = type(tmp_path).is_symlink
    monkeypatch.setattr(
        type(tmp_path), "is_symlink", lambda p: p.name == "link.txt" or original(p)
    )
    with pytest.raises(ValueError, match="enlaces"):
        RepoContext(tmp_path, repository_profile()).request(
            {"op": "read_file", "path": "link.txt"}
        )
    from test_general_patch import profile

    assert not profile().allows_code("src-other/a.py")


def test_automatic_publication_rechecks_base_after_archive(tmp_path):
    from test_conversation import git

    engine, github, store, run_id = prepare_new_run(tmp_path)
    plan = store.load(run_id)["attempts"][-1]
    original = github.base_sha

    def advanced_base(branch):
        if engine.get(run_id)["attempts"][-1]["stage"] == "publishing":
            (github.source / "README.md").write_text("advanced base")
            git("add", ".", cwd=github.source)
            git("commit", "-m", "advance base", cwd=github.source)
            github.sha = git("rev-parse", "HEAD", cwd=github.source)
        return original(branch)

    github.base_sha = advanced_base
    engine.act(
        run_id,
        "approve",
        actor="ana@example.com",
        expected_revision=plan["revision"],
        expected_hash=plan["context"]["plan_hash"],
        key="plan",
    )
    final = engine.get(run_id)["attempts"][-1]
    assert final["stage"] == "awaiting_clarification" and not github.published
    assert final["base_sha"] == github.sha and "candidate_hash" not in final["context"]


def test_sonnet_scope_rejection_needs_new_plan(tmp_path):
    class Model(FakeModels):
        def complete(self, role, prompt, **kwargs):
            response = super().complete(role, prompt, **kwargs)
            if role == "openspec_verifier":
                response.text = json.dumps({'approved': False, 'findings': [{'category': 'scope_spec',
                    'code': 'output_contract', 'criterion': 'Salida autorizada', 'evidence': 'Contrato requiere nueva salida',
                    'paths': ['src/value.py'], 'operations': ['modify'], 'recommendation': 'Revisar contrato'}]})
            return response

    engine, github, store, run_id = prepare_new_run(tmp_path, Model())
    plan = store.load(run_id)["attempts"][-1]
    engine.act(
        run_id,
        "approve",
        actor="ana@example.com",
        expected_revision=plan["revision"],
        expected_hash=plan["context"]["plan_hash"],
        key="sonnet",
    )
    assert (
        engine.get(run_id)["state"] == "awaiting_plan_review" and not github.published
    )
    assert engine.get(run_id)["attempts"][-1]["context"]["implementation_correction_count"] == 0


def test_manifest_expansion_needs_new_plan(tmp_path):
    engine, github, store, run_id = prepare_new_run(tmp_path)

    # Scope cannot grow through a developer response even inside the writable prefix.
    class Extra(FakeModels):
        def complete(self, role, prompt, **kwargs):
            response = super().complete(role, prompt, **kwargs)
            if role == "developer":
                value = json.loads(response.text)
                value["operations"].append(
                    {
                        "op": "modify",
                        "path": "src/other.py",
                        "content": "VALUE=2",
                        "expected_sha256": "0" * 64,
                    }
                )
                response.text = json.dumps(value)
            return response

    engine.models_factory = lambda *_args: Extra()
    plan = store.load(run_id)["attempts"][-1]
    engine.act(
        run_id,
        "approve",
        actor="ana@example.com",
        expected_revision=plan["revision"],
        expected_hash=plan["context"]["plan_hash"],
        key="scope",
    )
    assert (
        engine.get(run_id)["state"] == "awaiting_plan_review" and not github.published
    )
    assert any(
        event["kind"] == "failure_classified" and event['details']['route'] == 'updating'
        for event in engine.get(run_id)["attempts"][-1]["timeline"]
    )
