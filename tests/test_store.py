import io

from harness.store import VolumeRunStore


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


def test_volume_store_lists_only_run_records():
    files = FakeFiles()
    files.list_directory_contents = lambda path: [type("Entry", (), {"name": "run123.json", "is_directory": False})(), type("Entry", (), {"name": "agent_calls", "is_directory": True})()]
    store = VolumeRunStore(files, "/Volumes/harness/schema/artifacts/runs")
    assert store.list_runs() == ["run123"]
