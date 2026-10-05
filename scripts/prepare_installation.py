"""Build a local deployment package. Does not deploy or change permissions."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/agents/harness'))
from harness.client_config import profile_bytes, read_profile
from harness.models import load_model_config


def prepare(installation: str, profile_path: Path, environment_path: Path, *, root: Path = ROOT) -> Path:
    if re.fullmatch(r'[a-z][a-z0-9_-]{0,63}', installation) is None:
        raise ValueError('Identificador de instalación inválido')
    profile = read_profile(profile_path, mode='external')
    env = yaml.safe_load(environment_path.read_text(encoding='utf-8-sig'))
    if not isinstance(env, dict) or set(env) != {'bundle_name', 'workspace_host', 'variables'}:
        raise ValueError('El entorno requiere bundle_name, workspace_host y variables')
    if not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}', env['bundle_name']) or not re.fullmatch(r'https://[A-Za-z0-9.-]+', env['workspace_host']):
        raise ValueError('Identidad o host de instalación inválido')
    config = yaml.safe_load((root / 'databricks.yml').read_text(encoding='utf-8'))
    variables = env['variables']
    if not isinstance(variables, dict) or set(variables) - set(config['variables']) or any(
        not isinstance(v, str) or not v or '${' in v for v in variables.values()):
        raise ValueError('Variables de instalación inválidas')
    required = ({k for k, v in config['variables'].items() if 'default' not in v}
                | {'sandbox_service_principal'}) - {'client_profile_sha256'}
    if not required <= set(variables) or set(variables) & {'client_profile_path', 'client_profile_sha256'}:
        raise ValueError('Faltan variables requeridas o se intentó sustituir el perfil entregado')
    if variables.get('sandbox_service_principal') == 'SET_DEDICATED_SANDBOX_SERVICE_PRINCIPAL':
        raise ValueError('Configurar la identidad sandbox dedicada')
    routing, _, _ = load_model_config(root / 'src/agents/harness/config/defaults/models.yaml')
    if (variables['sonnet_endpoint'] != routing['planner']
            or variables['verifier_endpoint'] != routing['verifier']):
        raise ValueError('Los endpoints de instalación no coinciden con el routing del producto')
    parent = root / '.deployments'
    if parent.is_symlink() or getattr(parent, 'is_junction', lambda: False)():
        raise ValueError('El destino no admite enlaces')
    destination = parent / installation
    if not destination.resolve().is_relative_to(root.resolve()) or destination.exists():
        raise ValueError('Destino existente o fuera del workspace')
    # Include pending product additions; explicit roots and exclusions bound the copy.
    tracked = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=root, check=True, capture_output=True).stdout.decode().split('\0')
    excluded = {'.git', '.venv', 'node_modules', '__pycache__', 'clients', 'deployment', '.runs', '.aws', '.databricks'}
    files = []
    for relative in tracked:
        path = Path(relative)
        if not relative or not (relative.startswith(('src/agents/', 'resources/', 'scripts/')) or relative == '.gitignore'):
            continue
        if any(p in excluded or p.startswith('.env') or p.endswith(('.pem', '.key', '.pyc')) for p in path.parts):
            continue
        source = root / path
        if not source.exists():
            continue  # tracked profile moved to examples during this migration
        if any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)() for p in (source, *source.parents)):
            raise ValueError('La fuente no admite enlaces')
        files.append((relative, source))
    data = profile_bytes(profile)
    digest = hashlib.sha256(data).hexdigest()
    config['bundle']['name'] = env['bundle_name']
    config['targets']['dev']['workspace'] = {'host': env['workspace_host']}
    config['targets']['dev']['variables'] = {**variables, 'client_profile_sha256': digest}
    destination.mkdir(parents=True)
    for relative, source in files:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    profile_target = destination / 'src/agents/harness/config/deployment/client.yaml'
    profile_target.parent.mkdir(parents=True, exist_ok=True)
    profile_target.write_bytes(data)
    # Packages contain only vetted files; keep exclusions only if they match.
    # CLI strict validation rejects unmatched patterns in an assembled package.
    config['sync']['exclude'] = [pattern for pattern in config['sync'].get('exclude', [])
                                 if any(destination.glob(pattern))]
    (destination / 'databricks.yml').write_text(yaml.safe_dump(config, sort_keys=False), encoding='utf-8')
    revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
    hashes = {relative: hashlib.sha256(source.read_bytes()).hexdigest() for relative, source in files}
    (destination / 'installation.json').write_text(json.dumps({
        'installation': installation, 'product_revision': revision, 'source_sha256': hashes,
        'profile_sha256': digest, 'environment': env}, indent=2), encoding='utf-8')
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installation', required=True)
    parser.add_argument('--client-profile', required=True, type=Path)
    parser.add_argument('--environment', required=True, type=Path)
    args = parser.parse_args()
    print(prepare(args.installation, args.client_profile, args.environment))
