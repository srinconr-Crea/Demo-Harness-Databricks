"""Bounded, read-only model context with content hashes and explicit truncation."""

import hashlib
import json
import os
import time
from pathlib import Path

from .repository_policy import safe_target


class ContextResponseError(ValueError):
    pass


class RepoContext:
    def __init__(self, root: Path, profile, *, cache=None, identity=None):
        self.root, self.profile = root, profile
        self.policy = profile.repository_policy
        self.reads = self.searches = self.used = self.requests = 0
        self.deadline = time.monotonic() + self.policy.timeout_seconds
        self.cache, self.identity = cache, identity

    def fingerprint(self, request):
        from .prompt_contracts import validate_request
        from .skills import digest
        validate_request(request)
        if request['op'] == 'read_file':
            item = self._read(request['path'])
            state = item.get('sha256', item)
        else:
            # Inventory includes contents, so new/deleted files and modified matches invalidate search.
            state = []
            for relative in self._files():
                target = safe_target(self.root, relative)
                if target.stat().st_size <= self.policy.max_file_bytes:
                    checksum = hashlib.sha256(target.read_bytes()).hexdigest()
                else:
                    checksum = (target.stat().st_size, target.stat().st_mtime_ns)
                state.append((relative, checksum))
        return digest([self.identity, request, state])

    def _files(self):
        count = 0
        for directory, folders, files in os.walk(self.root, followlinks=False):
            folders[:] = sorted(
                n
                for n in folders
                if not (Path(directory) / n).is_symlink()
                and self.profile.allows_read(
                    (Path(directory) / n).relative_to(self.root).as_posix()
                )
            )
            for name in sorted(files):
                count += 1
                if count > 2000 or time.monotonic() > self.deadline:
                    raise ValueError("Límite de inventario o tiempo del contexto")
                path = Path(directory) / name
                relative = path.relative_to(self.root).as_posix()
                if (
                    not path.is_symlink()
                    and path.is_file()
                    and self.profile.allows_read(relative)
                ):
                    yield relative

    def _read(self, relative):
        if not self.profile.allows_read(relative):
            raise ValueError("Lectura fuera de política")
        path = safe_target(self.root, relative)
        if not path.is_file():
            raise ValueError("Lectura requiere archivo regular")
        if path.stat().st_size > self.policy.max_file_bytes:
            return {"path": relative, "truncated": True, "reason": "max_file_bytes"}
        raw = path.read_bytes()
        if b"\0" in raw:
            raise ValueError("Contexto binario no admitido")
        return {
            "path": relative,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "content": raw.decode("utf-8"),
            "truncated": False,
        }

    def request(self, request):
        from .prompt_contracts import validate_request
        validate_request(request)
        key = self.fingerprint(request) if self.cache else None
        if self.cache:
            from .skills import digest
            self.cache.bind(digest([self.identity, request]), key)
        cached = self.cache.get(key) if self.cache else None
        if cached is not None:
            self.requests += 1
            self.reads += request['op'] == 'read_file'
            self.searches += request['op'] == 'search_text'
            if (self.requests > self.policy.max_rounds or self.reads > self.policy.max_reads
                    or self.searches > self.policy.max_searches or time.monotonic() > self.deadline):
                raise ValueError('Límite de contexto')
            size = len(json.dumps(cached, ensure_ascii=False).encode('utf-8'))
            if self.used + size > self.policy.max_context_bytes:
                return {'truncated': True, 'reason': 'max_context_bytes'}
            self.used += size
            return cached
        result = self._request(request)
        if self.cache:
            self.cache.put(key, result)
        return result

    def _request(self, request):
        self.requests += 1
        if self.requests > self.policy.max_rounds or time.monotonic() > self.deadline:
            raise ValueError("Límite de rondas o tiempo del contexto")
        op = request.get("op")
        if op == "read_file":
            self.reads += 1
            if self.reads > self.policy.max_reads:
                raise ValueError("Límite de lecturas del contexto")
            result = self._read(request.get("path", ""))
        elif op == "list_tree":
            result = {"paths": list(self._files()), "truncated": False}
        elif op == "search_text":
            self.searches += 1
            query = request.get("query")
            if (
                self.searches > self.policy.max_searches
                or not isinstance(query, str)
                or not 1 <= len(query) <= 200
            ):
                raise ValueError("Límite o consulta de búsqueda inválida")
            hits = []
            for relative in self._files():
                try:
                    item = self._read(relative)
                except (UnicodeDecodeError, ValueError):
                    continue
                for n, line in enumerate(item.get("content", "").splitlines(), 1):
                    if query in line:
                        hits.append(
                            {
                                "path": relative,
                                "line": n,
                                "text": line[:500],
                                "sha256": item["sha256"],
                            }
                        )
                        if len(hits) >= 100:
                            break
                if len(hits) >= 100:
                    break
            result = {"matches": hits, "truncated": len(hits) >= 100}
        else:
            raise ValueError("Operación de contexto no autorizada")
        size = len(json.dumps(result, ensure_ascii=False).encode("utf-8"))
        if self.used + size > self.policy.max_context_bytes:
            return {"truncated": True, "reason": "max_context_bytes"}
        self.used += size
        return result


def contextual_answer(
    models, role, prompt: dict, context: RepoContext | None = None, *, context_manager=None, phase=None, **kwargs
):
    payload = dict(prompt)
    max_prompt_bytes = kwargs.pop('max_prompt_bytes', None)
    if context:
        payload["context_tools"] = ["list_tree", "search_text", "read_file"]
        payload["context_contract"] = (
            "Solicita JSON context_request {op,path o query}; al terminar devuelve el contrato final solicitado."
        )
    limit = context.policy.max_rounds if context else 1
    history = []
    for _ in range(limit):
        if context_manager:
            serialized, system, metadata = context_manager.prepare(role, phase, payload, history, context,
                max_bytes=max_prompt_bytes, max_tokens=kwargs.get('max_tokens', getattr(models, 'max_tokens', 0)))
            kwargs.update(system_prompt=system, context_provenance=metadata)
        else:
            serialized = json.dumps({**payload, "context_history": history}, ensure_ascii=False)
        if not context_manager and max_prompt_bytes and len(serialized.encode('utf-8')) > max_prompt_bytes:
            raise ValueError('El prompt OpenSpec excede el presupuesto; no se truncaron instrucciones')
        response = models.complete(
            role,
            serialized,
            **kwargs,
        )
        body = response.text.strip()
        if body.startswith("```json") and body.endswith("```"):
            body = body[7:-3].strip()
        try:
            value = json.loads(body)
        except json.JSONDecodeError as error:
            raise ContextResponseError(
                f"El rol {role} devolvió JSON inválido"
            ) from error
        if not isinstance(value, dict):
            raise ContextResponseError(f"El rol {role} devolvió un contrato inválido")
        request = value.get("context_request")
        if request is None:
            if context_manager:
                try:
                    context_manager.validate(role, value, payload)
                except ValueError as error:
                    raise ContextResponseError(str(error)) from error
            return value
        if not context or not isinstance(request, dict):
            raise ValueError("Solicitud de contexto inválida")
        try:
            if context_manager and set(value) != {'context_request'}:
                raise ValueError('Campos de solicitud de contexto inválidos')
            result = context.request(request)
            fingerprint = context.fingerprint(request) if context_manager else None
            if context_manager and result.get('content') and result.get('sha256') and not result.get('truncated'):
                context_manager.observe_fact(result['path'], result['content'], result['sha256'])
        except (ValueError, UnicodeDecodeError):
            result = {
                "error": "Solicitud rechazada por política, formato o presupuesto"
            }
            fingerprint = None
        item = {"request": request, "result": result}
        if context_manager:
            item['fingerprint'] = fingerprint
        history.append(item)
    raise ValueError("El modelo agotó las rondas de contexto sin contrato final")
