"""Execute a delivered CostOps SELECT through SQL Statement Execution."""
import argparse
import json
import shutil
import subprocess
import time
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import credentials_strategy


@credentials_strategy("costops-cli", ["profile"])
def cli_credentials(config):
    """Ask the CLI for its refreshed credentials without logging credentials."""
    def headers():
        result = subprocess.run(
            [shutil.which("databricks") or "databricks", "auth", "token", "--profile", config.profile],
            check=True, capture_output=True, text=True,
        )
        token = json.loads(result.stdout)["access_token"]
        return {"Authorization": "Bearer " + token}
    return headers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--profile", default="CREA_DEV")
    parser.add_argument("--warehouse", default="9e696889dea65361")
    args = parser.parse_args()
    sql = args.file.read_text(encoding="utf-8")
    workspace = WorkspaceClient(profile=args.profile, credentials_strategy=cli_credentials)
    result = workspace.statement_execution.execute_statement(
        warehouse_id=args.warehouse, statement=sql, wait_timeout="50s",
    )
    deadline = time.monotonic() + 900
    while result.status.state.value in {"PENDING", "RUNNING"}:
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Statement {result.statement_id} aún activo; consulte su estado")
        time.sleep(2)
        result = workspace.statement_execution.get_statement(result.statement_id)
    if result.status.state.value != "SUCCEEDED":
        raise RuntimeError(json.dumps({"statement_id": result.statement_id, "status": result.status.as_dict()}))
    rows = list(result.result.data_array or []) if result.result else []
    next_chunk = result.result.next_chunk_index if result.result else None
    while next_chunk is not None:
        chunk = workspace.statement_execution.get_statement_result_chunk_n(result.statement_id, next_chunk)
        rows.extend(chunk.data_array or [])
        next_chunk = chunk.next_chunk_index
    print(json.dumps({"statement_id": result.statement_id,
                      "columns": [column.name for column in result.manifest.schema.columns],
                      "rows": rows}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
