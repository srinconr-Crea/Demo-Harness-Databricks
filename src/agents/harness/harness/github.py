"""GitHub App installation client restricted to a configured repository."""

from __future__ import annotations

import base64
import time
from collections.abc import Callable
from urllib.parse import quote

import httpx
import jwt


class GitHubAppClient:
    def __init__(
        self,
        app_id: int,
        installation_id: int,
        private_key: str,
        *,
        repository: str,
        base_branch: str,
        http: httpx.Client | None = None,
    ):
        self.app_id = app_id
        self.installation_id = installation_id
        self.private_key = private_key
        self.repository = repository
        self.base_branch = base_branch
        self.http = http or httpx.Client(base_url="https://api.github.com", timeout=30)
        self._token: str | None = None
        self._expires_at = 0.0

    def _installation_token(self) -> str:
        if self._token and time.time() < self._expires_at - 120:
            return self._token
        self._token = self._new_installation_token({"contents": "write", "pull_requests": "write"})
        self._expires_at = time.time() + 3300
        return self._token

    def _new_installation_token(self, permissions: dict[str, str]) -> str:
        now = int(time.time())
        assertion = jwt.encode(
            {"iat": now - 30, "exp": now + 540, "iss": str(self.app_id)},
            self.private_key,
            algorithm="RS256",
        )
        response = self.http.post(
            f"/app/installations/{self.installation_id}/access_tokens",
            headers={"Authorization": f"Bearer {assertion}", "Accept": "application/vnd.github+json"},
            json={"repositories": [self.repository.split("/", 1)[1]], "permissions": permissions},
        )
        response.raise_for_status()
        payload = response.json()
        return payload["token"]

    def _checks_request(self, path: str) -> dict:
        token = self._new_installation_token({"checks": "read"})
        response = self.http.get(path, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
        response.raise_for_status()
        return response.json()

    def _request(self, method: str, path: str, **kwargs) -> dict | list:
        response = self.http.request(
            method,
            path,
            headers={"Authorization": f"Bearer {self._installation_token()}", "Accept": "application/vnd.github+json"},
            **kwargs,
        )
        response.raise_for_status()
        return response.json()

    def _check_repo(self, repository: str) -> None:
        if repository != self.repository:
            raise ValueError("Repositorio fuera de la instalación autorizada")

    def base_sha(self, base_branch: str) -> str:
        if base_branch != self.base_branch:
            raise ValueError("La rama base no coincide con el perfil autorizado")
        data = self._request("GET", f"/repos/{self.repository}/git/ref/heads/{base_branch}")
        return data["object"]["sha"]

    def pr_check_status(self, repository: str, branch: str) -> str:
        """Snapshot of checks after PR creation; absence or API denial is never a pass."""
        self._check_repo(repository)
        try:
            data = self._checks_request(f"/repos/{repository}/commits/{quote(branch, safe='/')}/check-runs")
        except httpx.HTTPError:
            return "unavailable"
        runs = data.get("check_runs", [])
        if not runs:
            return "pending"
        if any(item.get("status") != "completed" for item in runs):
            return "pending"
        return "passed" if all(item.get("conclusion") in {"success", "skipped", "neutral"} for item in runs) else "failed"

    def read_file(self, path: str, *, ref: str) -> tuple[str, str]:
        encoded_path = quote(path, safe="/")
        data = self._request("GET", f"/repos/{self.repository}/contents/{encoded_path}", params={"ref": ref})
        if data.get("type") != "file":
            raise ValueError("La ruta solicitada no es un archivo")
        return base64.b64decode(data["content"]).decode("utf-8"), data["sha"]

    def _verify_branch_diff(self, repository: str, branch: str, base_sha: str, files: dict[str, tuple[str, str]]) -> None:
        comparison = self._request("GET", f"/repos/{repository}/compare/{base_sha}...{quote(branch, safe='/')}")
        if comparison.get("merge_base_commit", {}).get("sha") != base_sha:
            raise ValueError("La rama feature no nació del commit base validado")
        changed = {item.get("filename") for item in comparison.get("files", [])}
        if changed != set(files):
            raise ValueError("La rama feature contiene archivos adicionales o faltantes")

    def create_feature_pr(
        self,
        repository: str,
        branch: str,
        base_branch: str,
        title: str,
        body: str,
        base_sha: str,
        files: dict[str, tuple[str, str]],
        *,
        on_progress: Callable[..., None] | None = None,
    ) -> str:
        self._check_repo(repository)
        if base_branch != self.base_branch or not branch.startswith("feature/") or ".." in branch:
            raise ValueError("Rama Git fuera de política")
        if not files or any(path.startswith(("/", ".github/")) or ".." in path.split("/") for path in files):
            raise ValueError("Ruta de publicación fuera de política")
        owner = repository.split("/", 1)[0]
        existing = self._request("GET", f"/repos/{repository}/pulls", params={"head": f"{owner}:{branch}", "base": base_branch, "state": "open"})
        if existing:
            self._verify_branch_diff(repository, branch, base_sha, files)
            for path, (expected_content, _) in files.items():
                current_content, _ = self.read_file(path, ref=branch)
                if current_content != expected_content:
                    raise ValueError("El PR existente contiene cambios distintos a la HU validada")
            url = existing[0]["html_url"]
            if on_progress:
                on_progress("pr_created", pr_url=url, branch=branch, reused=True)
            return url
        ref_path = f"/repos/{repository}/git/ref/heads/{quote(branch, safe='/')}"
        try:
            ref = self._request("GET", ref_path)
        except httpx.HTTPStatusError as error:
            if error.response.status_code != 404:
                raise
            self._request("POST", f"/repos/{repository}/git/refs", json={"ref": f"refs/heads/{branch}", "sha": base_sha})
            if on_progress:
                on_progress("branch_created", branch=branch, base_sha=base_sha)
        else:
            if on_progress:
                on_progress("branch_created", branch=branch, base_sha=base_sha, reused=True)
            if ref["object"]["sha"] != base_sha:
                self._verify_branch_diff(repository, branch, base_sha, files)
                if len(files) != 1:
                    raise ValueError("La rama feature existente divergió del commit base")
                only_path, (expected_content, _) = next(iter(files.items()))
                current_content, _ = self.read_file(only_path, ref=branch)
                if current_content != expected_content:
                    raise ValueError("La rama feature existente tiene cambios distintos")
                pr = self._request("POST", f"/repos/{repository}/pulls", json={"title": title, "head": branch, "base": base_branch, "body": body, "draft": False})
                if on_progress:
                    on_progress("pr_created", pr_url=pr["html_url"], branch=branch)
                return pr["html_url"]
        for path, (content, source_sha) in files.items():
            updated = self._request(
                "PUT", f"/repos/{repository}/contents/{quote(path, safe='/')}",
                json={
                    "message": f"feat: {title}",
                    "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
                    "sha": source_sha,
                    "branch": branch,
                },
            )
            if on_progress:
                on_progress("file_pushed", branch=branch, path=path, commit_sha=updated.get("commit", {}).get("sha"))
        pr = self._request("POST", f"/repos/{repository}/pulls", json={"title": title, "head": branch, "base": base_branch, "body": body, "draft": False})
        if on_progress:
            on_progress("pr_created", pr_url=pr["html_url"], branch=branch)
        return pr["html_url"]
