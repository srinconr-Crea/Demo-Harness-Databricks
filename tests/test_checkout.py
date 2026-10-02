import subprocess
from pathlib import Path

import pytest
from harness.checkout import GitCheckout, restore_checkpoint, snapshot_changes
from harness.store import LocalRunStore


def git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def make_remote(tmp_path: Path, *, link: bool = False):
    source = tmp_path / "source"
    source.mkdir()
    git("init", "-b", "develop", str(source))
    git("config", "user.email", "test@example.com", cwd=source)
    git("config", "user.name", "Test", cwd=source)
    (source / "openspec").mkdir()
    (source / "openspec" / "config.yaml").write_text("schema: spec-driven\n", encoding="utf-8")
    (source / "code.py").write_text("print(1)\n", encoding="utf-8")
    git("add", ".", cwd=source)
    if link:
        result = subprocess.run(["git", "hash-object", "-w", "--stdin"], cwd=source, input="code.py", capture_output=True, text=True, check=True)
        target_blob = result.stdout.strip()
        git("update-index", "--add", "--cacheinfo", f"120000,{target_blob},link.py", cwd=source)
    git("commit", "-m", "initial", cwd=source)
    initial = git("rev-parse", "HEAD", cwd=source)
    (source / "code.py").write_text("print(2)\n", encoding="utf-8")
    git("commit", "-am", "second", cwd=source)
    return source, initial


def test_checkout_pins_exact_base_and_does_not_store_token(tmp_path: Path, monkeypatch):
    source, initial = make_remote(tmp_path)
    checkout = GitCheckout(source.as_uri(), "develop")
    destination = tmp_path / "client"
    checkout.clone(destination, initial, token="private-test-token")
    assert git("rev-parse", "HEAD", cwd=destination) == initial
    assert (destination / "code.py").read_text(encoding="utf-8") == "print(1)\n"
    assert "private-test-token" not in (destination / ".git" / "config").read_text(encoding="utf-8")
    assert "private-test-token" not in git("remote", "-v", cwd=destination)


def test_checkout_rejects_wrong_sha_and_leaves_no_checked_out_files(tmp_path: Path):
    source, _ = make_remote(tmp_path)
    destination = tmp_path / "client"
    with pytest.raises(ValueError, match="SHA"):
        GitCheckout(source.as_uri(), "develop").clone(destination, "0" * 40, token="secret")
    assert not (destination / "code.py").exists()


def test_checkout_rejects_symlink_before_checkout(tmp_path: Path):
    source, initial = make_remote(tmp_path, link=True)
    destination = tmp_path / "client"
    with pytest.raises(ValueError, match="enlace"):
        GitCheckout(source.as_uri(), "develop").clone(destination, initial, token="secret")
    assert not (destination / "link.py").exists()


def test_checkpoint_restores_exact_modified_created_and_deleted_files(tmp_path: Path):
    source, initial = make_remote(tmp_path)
    first = tmp_path / "first"
    second = tmp_path / "second"
    checkout = GitCheckout(source.as_uri(), "develop")
    checkout.clone(first, initial, token="secret")
    (first / "code.py").write_text("print(99)\n", encoding="utf-8")
    (first / "new.py").write_text("new\n", encoding="utf-8")
    (first / "openspec" / "config.yaml").unlink()
    changes = snapshot_changes(first, initial, lambda path: path == "code.py" or path == "new.py" or path.startswith("openspec/"))
    store = LocalRunStore(tmp_path.parent / "r")
    checkpoint_id = store.save_checkpoint("a" * 32, "b" * 32, 2, initial, changes)

    checkout.clone(second, initial, token="secret")
    restore_checkpoint(second, store.load_checkpoint("a" * 32, "b" * 32, checkpoint_id),
                       initial, lambda path: path == "code.py" or path == "new.py" or path.startswith("openspec/"))
    assert snapshot_changes(second, initial, lambda _path: True) == changes
    assert not (second / "openspec" / "config.yaml").exists()


def test_checkpoint_rejects_unapproved_path_before_restoration(tmp_path: Path):
    source, initial = make_remote(tmp_path)
    root = tmp_path / "client"
    GitCheckout(source.as_uri(), "develop").clone(root, initial, token="secret")
    with pytest.raises(ValueError, match="fuera"):
        restore_checkpoint(root, {"base_sha": initial, "revision": 1,
                                  "files": {".github/workflows/evil.yml": b"evil"}}, initial, lambda _path: True)
    assert not (root / ".github").exists()
