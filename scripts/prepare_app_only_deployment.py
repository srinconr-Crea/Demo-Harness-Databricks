"""Prepare an App-only deployment while the dedicated sandbox Job is pending.

Input is the JSON from `databricks bundle validate -o json`. This script only
writes request files; the operator runs the CLI mutations explicitly.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def prepare(config: dict) -> tuple[dict, dict]:
    def resolve(value):
        if isinstance(value, dict):
            return {key: resolve(item) for key, item in value.items()}
        if isinstance(value, list):
            return [resolve(item) for item in value]
        if not isinstance(value, str):
            return value
        for _ in range(20):
            if "${" not in value:
                return value
            def replace(match):
                item = config
                for key in match.group(1).split("."):
                    item = item[key]
                return str(item)
            value = re.sub(r"\$\{([^}]+)\}", replace, value)
        raise ValueError("Unresolved bundle reference")

    app = config["resources"]["apps"]["harness"]
    resources = resolve([item for item in app["resources"]
                         if item["name"] not in {
                             "sandbox-job", "sandbox-volume-read", "sandbox-volume-write"}])
    env = resolve([item for item in app["config"]["env"]
                   if item["name"] not in {"HARNESS_SANDBOX_JOB_ID", "HARNESS_SANDBOX_DIR"}])
    update = {"name": app["name"], "description": app["description"],
              "resources": resources}
    deployment = {"source_code_path": app["source_code_path"], "mode": "SNAPSHOT",
                  "command": app["config"]["command"], "env_vars": env}
    return update, deployment


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8-sig"))
    update, deployment = prepare(config)
    for name, body in (("app-only-update.json", update),
                       ("app-only-deployment.json", deployment)):
        destination = args.config.parent / name
        destination.write_text(json.dumps(body, indent=2), encoding="utf-8")
        print(destination)
