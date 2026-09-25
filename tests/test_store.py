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
