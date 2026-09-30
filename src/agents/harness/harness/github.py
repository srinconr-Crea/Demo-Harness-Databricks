"""GitHub App installation client restricted to a configured repository."""

from __future__ import annotations

import base64
import time
from collections.abc import Callable
from urllib.parse import quote

import httpx
import jwt

from .checkout import GitCheckout


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

    def checkout(self, destination, base_sha: str) -> None:
        """Clone the configured repository at its exact approved base commit."""
        from pathlib import Path

        GitCheckout(f"https://github.com/{self.repository}.git", self.base_branch).clone(
            Path(destination), base_sha, token=self._installation_token(),
        )

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

    def read_openspec_files(self, base_sha: str) -> dict[str, tuple[str, str]]:
        """Read the client's existing OpenSpec tree from the validated base commit."""
        commit = self._request("GET", f"/repos/{self.repository}/git/commits/{base_sha}")
        tree_sha = commit.get("tree", {}).get("sha")
        if not tree_sha:
            raise ValueError("El commit base no contiene un árbol Git válido")
        tree = self._request("GET", f"/repos/{self.repository}/git/trees/{tree_sha}?recursive=1")
        if tree.get("truncated"):
            raise ValueError("El árbol Git del cliente está truncado")
        paths = []
        for entry in tree.get("tree", []):
            path = entry.get("path", "")
            if not path.startswith("openspec/"):
                continue
            if entry.get("type") != "blob" or ".." in path.split("/") or "\\" in path:
                raise ValueError("Ruta OpenSpec no válida en el repositorio cliente")
            if not path.endswith((".md", ".yaml", ".yml", ".gitkeep")):
                raise ValueError("Archivo OpenSpec no admitido en el repositorio cliente")
            paths.append(path)
        if len(paths) > 300:
            raise ValueError("Demasiados archivos OpenSpec en el repositorio cliente")
        if sum(entry.get("size", 0) or 0 for entry in tree.get("tree", []) if entry.get("path") in paths) > 4_000_000:
            raise ValueError("El contexto OpenSpec del cliente excede el límite")
        result = {path: self.read_file(path, ref=base_sha) for path in paths}
        if sum(len(content.encode("utf-8")) for content, _sha in result.values()) > 4_000_000:
            raise ValueError("El contexto OpenSpec del cliente excede el límite")
        return result

    def _verify_branch_diff(self, repository: str, branch: str, base_sha: str, files: dict[str, tuple[str | None, str | None]]) -> None:
        comparison = self._request("GET", f"/repos/{repository}/compare/{base_sha}...{quote(branch, safe='/')}")
        if comparison.get("merge_base_commit", {}).get("sha") != base_sha:
            raise ValueError("La rama feature no nació del commit base validado")
        if len(comparison.get("files", [])) >= 300:
            raise ValueError("La comparación de la rama feature puede estar truncada")
        changed = {item.get("filename") for item in comparison.get("files", [])}
        if changed != set(files):
            raise ValueError("La rama feature contiene archivos adicionales o faltantes")
        for item in comparison["files"]:
            path = item["filename"]
            expected_content = files[path][0]
            if expected_content is None:
                if item.get("status") != "removed":
                    raise ValueError("La rama feature no borró el archivo aprobado")
            else:
                if item.get("status") == "removed":
                    raise ValueError("La rama feature borró un archivo aprobado")
                current_content, _ = self.read_file(path, ref=branch)
                if current_content != expected_content:
                    raise ValueError("La rama feature contiene cambios distintos a la HU validada")

    def create_feature_pr(
        self,
        repository: str,
        branch: str,
        base_branch: str,
        title: str,
        body: str,
        base_sha: str,
        files: dict[str, tuple[str | None, str | None]],
        *,
        on_progress: Callable[..., None] | None = None,
    ) -> str:
        self._check_repo(repository)
        if base_branch != self.base_branch or not branch.startswith("feature/") or ".." in branch:
            raise ValueError("Rama Git fuera de política")
        if not files or any(path.startswith(("/", ".github/")) or ".." in path.split("/") or "\\" in path or "//" in path for path in files):
            raise ValueError("Ruta de publicación fuera de política")
        owner = repository.split("/", 1)[0]
        existing = self._request("GET", f"/repos/{repository}/pulls", params={"head": f"{owner}:{branch}", "base": base_branch, "state": "open"})
        if existing:
            self._verify_branch_diff(repository, branch, base_sha, files)
            url = existing[0]["html_url"]
            if on_progress:
                on_progress("pr_created", pr_url=url, branch=branch, reused=True)
            return url
        ref_path = f"/repos/{repository}/git/ref/heads/{quote(branch, safe='/')}"
        branch_exists = False
        try:
            ref = self._request("GET", ref_path)
        except httpx.HTTPStatusError as error:
            if error.response.status_code != 404:
                raise
        else:
            branch_exists = True
            if ref["object"]["sha"] != base_sha:
                self._verify_branch_diff(repository, branch, base_sha, files)
                pr = self._request("POST", f"/repos/{repository}/pulls", json={"title": title, "head": branch, "base": base_branch, "body": body, "draft": False})
                if on_progress:
                    on_progress("pr_created", pr_url=pr["html_url"], branch=branch)
                return pr["html_url"]
        base_commit = self._request("GET", f"/repos/{repository}/git/commits/{base_sha}")
        base_tree = base_commit.get("tree", {}).get("sha")
        if not base_tree:
            raise ValueError("El commit base no contiene un árbol Git válido")
        entries = []
        for path, (content, _source_sha) in sorted(files.items()):
            if content is None:
                entries.append({"path": path, "mode": "100644", "type": "blob", "sha": None})
            else:
                blob = self._request("POST", f"/repos/{repository}/git/blobs", json={"content": content, "encoding": "utf-8"})
                entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        tree = self._request("POST", f"/repos/{repository}/git/trees", json={"base_tree": base_tree, "tree": entries})
        commit = self._request("POST", f"/repos/{repository}/git/commits", json={"message": f"feat: {title}", "tree": tree["sha"], "parents": [base_sha]})
        if branch_exists:
            self._request("PATCH", f"/repos/{repository}/git/refs/heads/{quote(branch, safe='/')}", json={"sha": commit["sha"], "force": False})
        else:
            self._request("POST", f"/repos/{repository}/git/refs", json={"ref": f"refs/heads/{branch}", "sha": commit["sha"]})
        if on_progress:
            on_progress("branch_created", branch=branch, base_sha=base_sha, commit_sha=commit["sha"], reused=branch_exists)
            on_progress("files_pushed", branch=branch, paths=sorted(files), commit_sha=commit["sha"])
        pr = self._request("POST", f"/repos/{repository}/pulls", json={"title": title, "head": branch, "base": base_branch, "body": body, "draft": False})
        if on_progress:
            on_progress("pr_created", pr_url=pr["html_url"], branch=branch)
        return pr["html_url"]
