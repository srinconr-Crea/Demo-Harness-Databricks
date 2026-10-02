import hashlib
from pathlib import Path

import pytest
from harness.contracts import ClientProfile, load_profile
from harness.patch import FileOperation, apply_file_operations
from harness.sandbox import verify_general_patch


def profile():
    return ClientProfile(
        repository="example/client", base_branch="develop",
        allowed_paths=["src/", "docs/"], openspec_root="openspec",
        general_patch={
            "allowed_paths": ["src/", "docs/"],
            "extensions": [".py", ".md"],
            "operations": ["create", "modify", "delete"],
            "max_files": 3, "max_bytes": 1000,
            "test_adapters": ["python_compile"],
        },
    )


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def test_general_example_profile_requires_configured_sandbox_tests():
    sample = load_profile(Path(__file__).parent / "fixtures" / "clients" / "general.yaml")
    assert sample.general_patch.test_paths == ["tests/test_value.py"]
    assert not sample.allows(".github/workflows/unsafe.yaml")


def test_general_patch_creates_modifies_and_deletes_allowed_text(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "src" / "a.py").write_bytes(b"print(1)\n")
    (tmp_path / "docs" / "old.md").write_bytes(b"old\n")
    operations = [
        FileOperation(op="modify", path="src/a.py", content="print(2)\n", expected_sha256=sha(b"print(1)\n")),
        FileOperation(op="create", path="docs/new.md", content="# New\n"),
        FileOperation(op="delete", path="docs/old.md", expected_sha256=sha(b"old\n")),
    ]
    changed = apply_file_operations(tmp_path, profile(), operations)
    assert changed == ["docs/new.md", "docs/old.md", "src/a.py"]
    assert (tmp_path / "src" / "a.py").read_text(encoding="utf-8") == "print(2)\n"
    assert not (tmp_path / "docs" / "old.md").exists()


@pytest.mark.parametrize("path", ["../outside.py", ".github/workflows/x.py", "src/../../x.py", "src/file.exe"])
def test_general_patch_rejects_unapproved_paths(tmp_path: Path, path: str):
    with pytest.raises(ValueError):
        apply_file_operations(tmp_path, profile(), [FileOperation(op="create", path=path, content="x")])


def test_general_patch_rejects_stale_hash_and_binary(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_bytes(b"print(1)\n")
    with pytest.raises(ValueError, match="hash"):
        apply_file_operations(tmp_path, profile(), [FileOperation(op="modify", path="src/a.py", content="print(2)\n", expected_sha256="0" * 64)])
    with pytest.raises(ValueError, match="binario"):
        apply_file_operations(tmp_path, profile(), [FileOperation(op="create", path="src/b.py", content="x\x00y")])


def test_general_code_requires_dedicated_job_for_publication(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("VALUE = 2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Job"):
        verify_general_patch(tmp_path, profile(), ["src/a.py"], None,
                             run_id="a" * 32, attempt_id="b" * 32, revision=1)


def test_general_code_combines_syntax_and_job_evidence(tmp_path: Path):
    configured = profile().model_copy(update={"general_patch": profile().general_patch.model_copy(
        update={"test_adapters": ["python_compile", "pytest_sandbox"], "test_paths": ["tests"]})})
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("VALUE = 2\n", encoding="utf-8")

    class Job:
        def run(self, root, **kwargs):
            assert root == tmp_path and kwargs["test_paths"] == ["tests"]
            return {"passed": True, "evidence": ["1 passed"], "job_run_id": 42}

    result = verify_general_patch(tmp_path, configured, ["src/a.py"], Job(),
                                  run_id="a" * 32, attempt_id="b" * 32, revision=1)
    assert result["passed"] is True and result["job_run_id"] == 42
