"""One-time provisioning of the harness coordination table before app deployment."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from databricks.sdk import WorkspaceClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness.coordination import DeltaRunCoordinator


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--warehouse-id", required=True)
    parser.add_argument("--table", required=True)
    options = parser.parse_args()
    workspace = WorkspaceClient(profile=options.profile)
    DeltaRunCoordinator(workspace.api_client, options.warehouse_id, options.table).provision()
    print("Tabla de coordinación del harness preparada")


if __name__ == "__main__":
    main()
