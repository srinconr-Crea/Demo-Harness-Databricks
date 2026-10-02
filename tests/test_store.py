import io

import pytest
from harness.store import LocalRunStore, VolumeRunStore


class FakeFiles:
    def __init__(self):
        self.values = {}
        self.directories = []

    def create_directory(self, path):
        self.directories.append(path)

    def upload(self, path, contents, overwrite):
        assert overwrite
        self.values[path] = contents.read()

    def download(self, path):
        if path not in self.values:
            raise FileNotFoundError(path)
        return type("Download", (), {"contents": io.BytesIO(self.values[path])})()


def test_volume_store_round_trip():
    files = FakeFiles()
    store = VolumeRunStore(files, "/Volumes/harness/schema/artifacts/runs")
    assert store.load("abc") is None
    store.save("abc", {"state": "running"})
    assert store.load("abc") == {"state": "running"}
    assert files.directories == ["/Volumes/harness/schema/artifacts/runs"]


def test_volume_store_persists_agent_calls_joinable_by_run_and_attempt():
    files = FakeFiles()
    store = VolumeRunStore(files, "/Volumes/harness/schema/artifacts/runs")
    store.save_agent_call("run123", "call456", {"run_id": "run123", "attempt_id": "attempt789", "call_id": "call456", "role": "analyst", "estimated_cost_usd": "0.02"})
    assert files.values["/Volumes/harness/schema/artifacts/runs/agent_calls/run123-call456.json"]


def test_historical_and_new_call_json_join_same_attempt_without_invented_cost(tmp_path):
    store = LocalRunStore(tmp_path)
    store.save_agent_call("run123", "old", {"schema_version": 2, "run_id": "run123",
                          "attempt_id": "attempt789", "call_id": "old", "role": "analyst",
                          "estimated_cost_usd": "0.02"})
    store.save_agent_call("run123", "new", {"schema_version": 3, "run_id": "run123",
                          "attempt_id": "attempt789", "call_id": "new", "role": "planner",
                          "stage": "proposing", "revision": 1, "estimated_cost_usd": None})
    calls = store.list_agent_calls("run123", "attempt789")
    assert {item["call_id"] for item in calls} == {"old", "new"}
    assert next(item for item in calls if item["call_id"] == "new")["estimated_cost_usd"] is None
    assert store.list_agent_calls("run123", "another") == []


def test_volume_store_lists_only_run_records():
    files = FakeFiles()
    files.list_directory_contents = lambda path: [type("Entry", (), {"name": "run123.json", "is_directory": False})(), type("Entry", (), {"name": "agent_calls", "is_directory": True})()]
    store = VolumeRunStore(files, "/Volumes/harness/schema/artifacts/runs")
    assert store.list_runs() == ["run123"]


def test_openspec_artifacts_are_isolated_by_attempt_in_local_and_volume_stores(tmp_path):
    for store in (LocalRunStore(tmp_path), VolumeRunStore(FakeFiles(), "/Volumes/harness/schema/artifacts/runs")):
        store.save_openspec_artifact("run123", "attempt001", "artifact001", {"content": "first"})
        store.save_openspec_artifact("run123", "attempt002", "artifact001", {"content": "second"})
        assert store.load_openspec_artifact("run123", "attempt001", "artifact001") == {"content": "first"}
        assert store.load_openspec_artifact("run123", "attempt002", "artifact001") == {"content": "second"}
        assert store.load_openspec_artifact("run123", "attempt003", "artifact001") is None


def test_checkpoint_preserves_exact_bytes_deletions_and_base_for_both_stores(tmp_path):
    for store in (LocalRunStore(tmp_path), VolumeRunStore(FakeFiles(), "/Volumes/harness/schema/artifacts/runs")):
        checkpoint_id = store.save_checkpoint(
            "run123", "attempt001", 2, "a" * 40,
            {"src/new.py": b"x = '\xc3\xb1'\n", "src/old.py": None},
        )
        checkpoint = store.load_checkpoint("run123", "attempt001", checkpoint_id)
        assert checkpoint["base_sha"] == "a" * 40
        assert checkpoint["revision"] == 2
        assert checkpoint["files"] == {"src/new.py": b"x = '\xc3\xb1'\n", "src/old.py": None}


def test_volume_checkpoint_rejects_modified_blob():
    files = FakeFiles()
    store = VolumeRunStore(files, "/Volumes/harness/schema/artifacts/runs")
    checkpoint_id = store.save_checkpoint("run123", "attempt001", 1, "b" * 40, {"src/a.py": b"print(1)\n"})
    blob = next(path for path in files.values if path.endswith(".bin"))
    files.values[blob] = b"print(2)\n"
    with pytest.raises(ValueError, match="integridad"):
        store.load_checkpoint("run123", "attempt001", checkpoint_id)


def test_checkpoint_rejects_paths_outside_checkout(tmp_path):
    store = LocalRunStore(tmp_path)
    with pytest.raises(ValueError):
        store.save_checkpoint("run123", "attempt001", 1, "b" * 40, {"../secret": b"x"})


def test_checkpoint_carries_state_for_recovery_after_control_transition(tmp_path):
    store = LocalRunStore(tmp_path)
    checkpoint_id = store.save_checkpoint(
        "run123", "attempt001", 3, "a" * 40,
        {"src/a.py": b"print(1)\n"},
        metadata={"stage": "awaiting_plan_review", "plan_hash": "b" * 64},
    )
    checkpoint = store.load_checkpoint("run123", "attempt001", checkpoint_id)
    assert checkpoint["metadata"]["stage"] == "awaiting_plan_review"
