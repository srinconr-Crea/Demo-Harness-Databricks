"""Operator-selected policy. Repository content never activates a profile."""
from __future__ import annotations

import hashlib
import os
import re
import stat
from pathlib import Path

import yaml

from .contracts import ClientProfile

MAX_PROFILE_BYTES = 131072


def profile_bytes(profile: ClientProfile) -> bytes:
    return profile._source_bytes or yaml.safe_dump(profile.model_dump(mode='json'), sort_keys=True).encode('utf-8')


def provenance(profile: ClientProfile) -> dict:
    return {'name': profile.name, 'version': profile.version, 'repository': profile.repository,
            'mode': profile._source_mode, 'sha256': hashlib.sha256(profile_bytes(profile)).hexdigest()}


def read_profile(path: Path, *, mode: str, expected_hash: str | None = None) -> ClientProfile:
    try:
        if any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)() for p in (path, *path.parents)):
            raise ValueError('El perfil no admite enlaces')
        with path.open('rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError('El perfil debe ser un archivo regular')
            data = stream.read(MAX_PROFILE_BYTES + 1)
        if len(data) > MAX_PROFILE_BYTES:
            raise ValueError('El perfil excede 128 KiB')
        digest = hashlib.sha256(data).hexdigest()
        if expected_hash is not None and digest != expected_hash:
            raise ValueError('El hash del perfil no coincide')
        value = yaml.safe_load(data.decode('utf-8-sig'))
        if not isinstance(value, dict) or set(value) - set(ClientProfile.model_fields):
            raise ValueError('El perfil contiene campos no admitidos')
        # The profile has no credential fields; prevent accidental embedded credentials.
        def check(item):
            if isinstance(item, dict):
                for key, nested in item.items():
                    if re.search(r'private_key|password|token|secret', str(key), re.IGNORECASE):
                        raise ValueError('El perfil no admite secretos')
                    check(nested)
            elif isinstance(item, list):
                for nested in item:
                    check(nested)
            elif isinstance(item, str) and re.search(r'-----BEGIN .*PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]+', item):
                raise ValueError('El perfil no admite secretos')
        check(value)
        profile = ClientProfile.model_validate(value)
    except (OSError, UnicodeError, yaml.YAMLError):
        raise ValueError('No se pudo leer o validar el perfil seleccionado') from None
    except ValueError:
        # Do not expose Pydantic input_value or raw YAML in startup logs.
        raise ValueError('Perfil inválido: comprobar archivo, contrato, tamaño e integridad') from None
    profile._source_bytes, profile._source_mode = data, mode
    return profile


def load_selected_profile(root: Path, environ=None) -> ClientProfile:
    env = os.environ if environ is None else environ
    external, legacy, digest = (env.get(k, '') for k in
        ('HARNESS_CLIENT_PROFILE_PATH', 'HARNESS_CLIENT_PROFILE', 'HARNESS_CLIENT_PROFILE_SHA256'))
    if (external and legacy) or (digest and not external) or not (external or legacy):
        raise ValueError('Configurar un único selector de perfil, sin hash huérfano')
    if external:
        if re.fullmatch(r'[a-f0-9]{64}', digest) is None:
            raise ValueError('El perfil externo requiere HARNESS_CLIENT_PROFILE_SHA256 válido')
        path = Path(external)
        if not path.is_absolute():
            if '..' in path.parts:
                raise ValueError('Ruta de perfil relativa inválida')
            path = root / path
            if not path.resolve().is_relative_to(root.resolve()):
                raise ValueError('Ruta de perfil fuera de ROOT')
        return read_profile(path, mode='external', expected_hash=digest)
    if re.fullmatch(r'[a-z][a-z0-9_-]*', legacy) is None:
        raise ValueError('Nombre de perfil inválido')
    return read_profile(root / 'config' / 'clients' / f'{legacy}.yaml', mode='legacy')
