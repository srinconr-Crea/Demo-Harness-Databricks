import json
from pathlib import Path

import pytest
from harness.contracts import ClientProfile, RatioSpec, Story, StoryRequest
from harness.openspec import (
    OpenSpecCLI,
    prepare_client_workspace,
    propose_client_change,
)
from openspec_helpers import prepare_manual, write_skills


def profile():
    return ClientProfile(
        repository="example/client", base_branch="develop",
        allowed_paths=["notebooks/"], openspec_root="openspec",
        strategy={"kind": "silver_safe_ratio", "notebook": "notebooks/a.ipynb", "table": "tabla", "anchor_column": "anchor", "allowed_source_columns": ["num", "den"]},
    )


def test_client_workspace_requires_existing_openspec_before_planning(tmp_path: Path):
    cli = OpenSpecCLI()
    root = tmp_path / "client"
    root.mkdir()

    with pytest.raises(ValueError, match="preparación"):
        prepare_client_workspace(root, profile())
    assert not (root / "openspec").exists()

    prepare_manual(root, profile(), cli)
    prepare_client_workspace(root, profile())

    config = (root / "openspec" / "config.yaml").read_text(encoding="utf-8")
    assert "schema: spec-driven" in config
    assert "example/client" in config
    assert (root / "openspec" / "specs").is_dir()
    assert (root / "openspec" / "changes").is_dir()


def test_client_workspace_preserves_existing_config_and_specs(tmp_path: Path):
    root = tmp_path / "client"
    root.mkdir()
    existing = {
        "openspec/config.yaml": ("schema: spec-driven\ncontext: Client owned context\n", "config-sha"),
        "openspec/specs/existing/spec.md": (
            ("# Existing\n\n## Purpose\nClient owned capability.\n\n## Requirements\n"
            "### Requirement: Keep\nThe client SHALL keep this.\n\n"
            "#### Scenario: Kept\n- **WHEN** loaded\n- **THEN** it remains.\n"), "spec-sha"
        ),
    }

    for path, (content, _sha) in existing.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    (root / "openspec" / "changes").mkdir()
    write_skills(root)
    prepare_client_workspace(root, profile())

    assert (root / "openspec" / "config.yaml").read_text(encoding="utf-8") == existing["openspec/config.yaml"][0]
    assert (root / "openspec" / "specs" / "existing" / "spec.md").read_text(encoding="utf-8") == existing["openspec/specs/existing/spec.md"][0]


def test_client_workspace_never_calls_init_for_existing_base(tmp_path: Path):
    root = tmp_path / "client"
    root.mkdir()
    (root / "openspec" / "specs").mkdir(parents=True)
    (root / "openspec" / "changes").mkdir()
    (root / "openspec" / "config.yaml").write_text("schema: spec-driven\ncontext: Approved\n", encoding="utf-8")

    write_skills(root)

    class NoInit:
        def version(self):
            return "1.13.2"

        def initialize(self, _root):
            raise AssertionError("init no debe ejecutarse para una HU")

    prepare_client_workspace(root, profile(), {}, NoInit())


def test_generic_proposal_can_be_updated_and_strictly_validated(tmp_path: Path):
    root = tmp_path / "client"
    root.mkdir()
    cli = OpenSpecCLI()
    prepare_manual(root, profile(), cli)

    class Model:
        def complete(self, role, prompt, **kwargs):
            assert role == "planner" and kwargs["stage"] in {"proposing", "updating"}
            artifact = json.loads(prompt)["artifact"]
            contents = {
                "proposal": "# Proposal\n\n## Why\nEl cliente requiere una capacidad de reporte.\n\n## What Changes\n- Añadir reporte.\n\n## Capabilities\n\n### New Capabilities\n- `add-report`: generar reporte.\n\n### Modified Capabilities\n\n## Impact\nCódigo del cliente.\n",
                "specs": "# Spec Delta\n\n## Purpose\nGenerar el reporte solicitado.\n\n## ADDED Requirements\n\n### Requirement: Reporte nuevo\nEl sistema SHALL generar un reporte.\n\n#### Scenario: Solicitud válida\n- **WHEN** se solicita el reporte\n- **THEN** se genera un resultado\n",
                "design": "# Design\n\n## Context\nCliente de prueba.\n\n## Goals / Non-Goals\nGenerar reporte.\n\n## Decisions\nAñadir función.\n\n## Risks / Trade-offs\nRequiere pruebas.\n",
                "tasks": "# Tasks\n\n## 1. Reporte\n\n- [ ] 1.1 Implementar y probar el reporte del cliente.\n",
            }
            return type("Response", (), {"text": json.dumps({"content": contents[artifact]})})()

    request = StoryRequest(hu="HU-12", description="Añadir reporte")
    first = propose_client_change(cli, root, "add-report", request, Model())
    second = propose_client_change(cli, root, "add-report", request, Model(), feedback="Aclarar pruebas")
    assert len(first.artifacts) == len(second.artifacts) == 4
    assert first.hashes == second.hashes


def test_client_workspace_rejects_path_escape(tmp_path: Path):
    root = tmp_path / "client"
    root.mkdir()
    with pytest.raises(ValueError, match="OpenSpec"):
        prepare_client_workspace(root, profile(), {"openspec/../outside.txt": ("bad", "sha")}, OpenSpecCLI())
    assert not (tmp_path / "outside.txt").exists()


def test_openspec_cli_fails_closed_when_missing(tmp_path: Path):
    root = tmp_path / "client"
    root.mkdir()
    with pytest.raises(ValueError, match="OpenSpec"):
        OpenSpecCLI(app_root=tmp_path).inventory(root)


def test_openspec_cli_timeout_is_failure(tmp_path: Path, monkeypatch):
    import subprocess

    root = tmp_path / "client"
    root.mkdir()
    app_root = tmp_path / "app"
    entry = app_root / "node_modules" / "@fission-ai" / "openspec" / "bin" / "openspec.js"
    entry.parent.mkdir(parents=True)
    entry.write_text("", encoding="utf-8")

    def timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired("node", 1)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(TimeoutError, match="OpenSpec"):
        OpenSpecCLI(app_root=app_root, timeout_seconds=1).inventory(root)


def story():
    return Story(
        id="HU-001", title="Razón segura", architecture="Capa Silver",
        source_target="tabla prueba", business_rules="ratio = a / b",
        nonfunctional="Sin cambios externos", validation="Positivo, cero y NULL",
    )


class FakePlanner:
    def __init__(self, expression: str, *, wrong_path: bool = False):
        self.expression = expression
        self.wrong_path = wrong_path
        self.calls = []

    def complete(self, role, prompt, **_kwargs):
        assert role == "planner"
        artifact = json.loads(prompt)["artifact"]
        self.calls.append(artifact)
        contents = {
            "proposal": "# Proposal\n\n## Why\nLa historia necesita una razón segura verificable.\n\n## What Changes\n- Agregar razón.\n\n## Capabilities\n\n### New Capabilities\n- `silver-safe-ratio`: cálculo seguro.\n\n### Modified Capabilities\n\n## Impact\nNotebook Silver.\n",
            "specs": "# Spec Delta\n\n## Purpose\nCalcular una razón segura en Silver para la historia del cliente.\n\n## ADDED Requirements\n\n### Requirement: Razón segura\nEl sistema SHALL devolver NULL si el denominador es cero o NULL.\n\n#### Scenario: Denominador cero\n- **WHEN** el denominador es cero\n- **THEN** el resultado es NULL\n",
            "design": "# Design\n\n## Context\nNotebook Silver existente.\n\n## Goals / Non-Goals\nCalcular una razón segura.\n\n## Decisions\nUsar safe_divide.\n\n## Risks / Trade-offs\nNo ejecutar el notebook completo.\n",
            "tasks": "# Tasks\n\n## 1. Edición\n\n- [ ] 1.1 Aplicar la razón segura y comprobar los tres casos sintéticos.\n",
        }
        value = {
            "content": contents[artifact], "strategy": "silver_safe_ratio",
            "expression": self.expression,
            "code_path": "notebooks/other.ipynb" if self.wrong_path else json.loads(prompt)["code_path"],
        }
        return type("Response", (), {"text": json.dumps(value, ensure_ascii=False)})()


def test_planner_creates_and_validates_client_change(tmp_path: Path):
    from harness.openspec import plan_client_change

    root = tmp_path / "client"
    root.mkdir()
    cli = OpenSpecCLI()
    prepare_manual(root, profile(), cli)
    spec = RatioSpec(output_column="ratio", numerator="num", denominator="den")
    models = FakePlanner(spec.expression)

    plan = plan_client_change(cli, root, "hu-001-attempt-1", story(), profile(), spec, "source", models)

    assert models.calls == ["proposal", "specs", "design", "tasks"]
    assert plan.change_id == "hu-001-attempt-1"
    assert any(path.endswith("/proposal.md") for path in plan.artifacts)
    assert len(plan.artifacts) == 4


def test_planner_rejects_manifest_outside_profile_before_developer(tmp_path: Path):
    from harness.openspec import plan_client_change

    root = tmp_path / "client"
    root.mkdir()
    cli = OpenSpecCLI()
    prepare_manual(root, profile(), cli)
    spec = RatioSpec(output_column="ratio", numerator="num", denominator="den")
    with pytest.raises(ValueError, match="política"):
        plan_client_change(cli, root, "hu-001-attempt-2", story(), profile(), spec, "source", FakePlanner(spec.expression, wrong_path=True))


def test_client_change_archives_and_collects_publishable_files(tmp_path: Path):
    from harness.openspec import (
        collect_changed_openspec,
        mark_tasks_complete,
        plan_client_change,
    )

    root = tmp_path / "client"
    root.mkdir()
    cli = OpenSpecCLI()
    client = profile()
    prepare_manual(root, client, cli)
    spec = RatioSpec(output_column="ratio", numerator="num", denominator="den")
    plan_client_change(cli, root, "hu-001-attempt-3", story(), client, spec, "source", FakePlanner(spec.expression))

    mark_tasks_complete(root, "hu-001-attempt-3")
    cli.archive(root, "hu-001-attempt-3")
    files = collect_changed_openspec(root, client, {})

    assert "openspec/config.yaml" in files
    assert "openspec/specs/silver-safe-ratio/spec.md" in files
    assert any(path.endswith("/proposal.md") and "/archive/" in path for path in files)
    assert all(sha is None for _content, sha in files.values())


def test_archived_change_preserves_existing_client_config(tmp_path: Path):
    from harness.openspec import (
        collect_changed_openspec,
        mark_tasks_complete,
        plan_client_change,
    )

    root = tmp_path / "client"
    root.mkdir()
    cli = OpenSpecCLI()
    existing = {"openspec/config.yaml": ("schema: spec-driven\ncontext: Client context\n", "existing-sha")}
    prepare_manual(root, profile(), cli)
    (root / "openspec" / "config.yaml").write_text(existing["openspec/config.yaml"][0], encoding="utf-8")
    spec = RatioSpec(output_column="ratio", numerator="num", denominator="den")
    plan_client_change(cli, root, "hu-001-existing", story(), profile(), spec, "source", FakePlanner(spec.expression))
    mark_tasks_complete(root, "hu-001-existing")
    cli.archive(root, "hu-001-existing")
    files = collect_changed_openspec(root, profile(), existing)
    assert "openspec/config.yaml" not in files
    assert "openspec/specs/silver-safe-ratio/spec.md" in files
    assert any("/archive/" in path for path in files)
