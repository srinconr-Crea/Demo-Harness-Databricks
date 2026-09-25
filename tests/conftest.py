"""Put deployed App sources on the import path for local tests."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "agents" / "harness"))
