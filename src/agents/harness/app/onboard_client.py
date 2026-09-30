"""One-time OpenSpec setup PR for a configured client repository."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.contracts import load_client_profile
from harness.github import GitHubAppClient
from harness.openspec import onboard_client


def main() -> None:
    parser = argparse.ArgumentParser(description="Crear PR de preparación OpenSpec de un cliente")
    parser.add_argument("--profile", required=True, help="Nombre del perfil cliente confiable")
    args = parser.parse_args()
    profile = load_client_profile(ROOT / "config" / "clients", args.profile)
    if profile.github_app_id is None or profile.github_installation_id is None:
        raise ValueError("El perfil no configura la GitHub App")
    private_key = os.environ["GITHUB_APP_PRIVATE_KEY"].replace("\\n", "\n")
    github = GitHubAppClient(
        profile.github_app_id, profile.github_installation_id, private_key,
        repository=profile.repository, base_branch=profile.base_branch,
    )
    print(onboard_client(profile, github))


if __name__ == "__main__":
    main()
