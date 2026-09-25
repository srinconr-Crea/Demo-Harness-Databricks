"""GitHub App installation client restricted to a configured repository."""

from __future__ import annotations

import base64
import time
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
        http: httpx.Client | None = None,
    ):
        self.app_id = app_id
        self.installation_id = installation_id
        self.private_key = private_key
        self.repository = repository
        self.http = http or httpx.Client(base_url="https://api.github.com", timeout=30)
        self._token: str | None = None
        self._expires_at = 0.0

    def _installation_token(self) -> str:
        if self._token and time.time() < self._expires_at - 120:
            return self._token
        now = int(time.time())
        assertion = jwt.encode(
            {"iat": now - 30, "exp": now + 540, "iss": str(self.app_id)},
            self.private_key,
            algorithm="RS256",
        )
        response = self.http.post(
            f"/app/installations/{self.installation_id}/access_tokens",
            headers={"Authorization": f"Bearer {assertion}", "Accept": "application/vnd.github+json"},
            json={"repositories": [self.repository.split("/", 1)[1]], "permissions": {"contents": "write", "pull_requests": "write"}},
        )
        response.raise_for_status()
        payload = response.json()
        self._token = payload["token"]
        self._expires_at = time.time() + 3300
        return self._token

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
        if base_branch != "develop":
            raise ValueError("La rama base aprobada es develop")
        data = self._request("GET", f"/repos/{self.repository}/git/ref/heads/{base_branch}")
        return data["object"]["sha"]

    def read_file(self, path: str, *, ref: str) -> tuple[str, str]:
        encoded_path = quote(path, safe="/")
        data = self._request("GET", f"/repos/{self.repository}/contents/{encoded_path}", params={"ref": ref})
        if data.get("type") != "file":
            raise ValueError("La ruta solicitada no es un archivo")
        return base64.b64decode(data["content"]).decode("utf-8"), data["sha"]

    def create_feature_pr(
        self,
        repository: str,
        branch: str,
        base_branch: str,
        title: str,
        body: str,
        base_sha: str,
        files: dict[str, tuple[str, str]],
    ) -> str:
        self._check_repo(repository)
        if base_branch != "develop" or not branch.startswith("feature/") or ".." in branch:
            raise ValueError("Rama Git fuera de política")
        owner = repository.split("/", 1)[0]
        existing = self._request("GET", f"/repos/{repository}/pulls", params={"head": f"{owner}:{branch}", "base": base_branch, "state": "open"})
        if existing:
            return existing[0]["html_url"]
        ref_path = f"/repos/{repository}/git/ref/heads/{quote(branch, safe='/')}"
        try:
            ref = self._request("GET", ref_path)
        except httpx.HTTPStatusError as error:
            if error.response.status_code != 404:
                raise
            self._request("POST", f"/repos/{repository}/git/refs", json={"ref": f"refs/heads/{branch}", "sha": base_sha})
        else:
            if ref["object"]["sha"] != base_sha:
                if len(files) != 1:
                    raise ValueError("La rama feature existente divergió del commit base")
                only_path, (expected_content, _) = next(iter(files.items()))
                current_content, _ = self.read_file(only_path, ref=branch)
                if current_content != expected_content:
                    raise ValueError("La rama feature existente tiene cambios distintos")
                pr = self._request("POST", f"/repos/{repository}/pulls", json={"title": title, "head": branch, "base": base_branch, "body": body, "draft": False})
                return pr["html_url"]
        for path, (content, source_sha) in files.items():
            if path.startswith(("/", ".github/")) or ".." in path.split("/"):
                raise ValueError("Ruta de publicación fuera de política")
            self._request(
                "PUT", f"/repos/{repository}/contents/{quote(path, safe='/')}",
                json={
                    "message": f"feat: {title}",
                    "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
                    "sha": source_sha,
                    "branch": branch,
                },
            )
        pr = self._request("POST", f"/repos/{repository}/pulls", json={"title": title, "head": branch, "base": base_branch, "body": body, "draft": False})
        return pr["html_url"]
