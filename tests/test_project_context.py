"""Check that the development-context entry points remain usable."""

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def missing_local_links(source, root):
    missing = []
    for target in re.findall(r"\]\(([^)]+)\)", source.read_text(encoding="utf-8")):
        if "://" in target or target.startswith("#"):
            continue
        path = (source.parent / target.split("#", 1)[0]).resolve()
        if not path.is_relative_to(root.resolve()) or not path.exists():
            missing.append(target)
    return missing


def test_context_yaml_budget_and_canonical_sources():
    config = yaml.safe_load((ROOT / "openspec/config.yaml").read_text(encoding="utf-8"))
    context = config["context"]
    assert isinstance(context, str) and 0 < len(context.encode("utf-8")) <= 8192
    for path in re.findall(r"(?:docs|src|openspec)/[\w./-]+", context):
        assert (ROOT / path.rstrip(".;")).exists(), path
    assert config["schema"] == "spec-driven"
    assert set(config["rules"]) == {"proposal", "specs", "design", "tasks"}
    assert set(config["operations"]) == {"apply", "archive"}


@pytest.mark.parametrize("relative", ["AGENTS.md", "README.md", "docs/operacion.md", "docs/contexto-proyecto.md"])
def test_entry_point_links_resolve(relative):
    source = ROOT / relative
    assert missing_local_links(source, ROOT) == []
    if relative != "docs/contexto-proyecto.md":
        assert "contexto-proyecto.md" in source.read_text(encoding="utf-8")


def test_link_check_detects_missing_and_external_paths(tmp_path):
    source = tmp_path / "guide.md"
    source.write_text("[missing](missing.md) [escape](../escape.md) [web](https://example.com)", encoding="utf-8")
    assert missing_local_links(source, tmp_path) == ["missing.md", "../escape.md"]
