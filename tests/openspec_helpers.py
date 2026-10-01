"""Explicit human-preparation equivalents for synthetic repositories only."""
import json
import os
import shutil
import subprocess
from pathlib import Path
from harness.openspec import OpenSpecCLI
from harness.skills import SKILLS

def write_skills(root):
    for name in SKILLS.values():
        path = root / '.agents' / 'skills' / name / 'SKILL.md'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'---\nname: {name}\nmetadata:\n  generatedBy: "1.13.2"\n---\n'
                        f'Workflow de prueba {name}. Respetar el contrato del Harness.\n', encoding='utf-8')

def prepare_manual(root, profile=None, cli=None):
    cli = cli or OpenSpecCLI()
    config_root = root.parent / ('config-' + root.name)
    (config_root / 'openspec').mkdir(parents=True, exist_ok=True)
    (config_root / 'openspec' / 'config.json').write_text(json.dumps({
        'profile': 'custom', 'delivery': 'skills', 'workflows': list(SKILLS)}), encoding='utf-8')
    env = {**os.environ, 'XDG_CONFIG_HOME': str(config_root), 'OPENSPEC_TELEMETRY': '0',
           'OPENSPEC_NO_UPDATE_CHECK': '1'}
    subprocess.run([shutil.which('node'), str(cli.entry), 'init', '--tools', 'agents',
                    '--profile', 'custom', '--no-animation'], cwd=root, env=env,
                   check=True, capture_output=True)
    (root / 'openspec' / 'config.yaml').write_text('schema: spec-driven\ncontext: '
        + (profile.repository if profile else 'Cliente sintético preparado') + '\n', encoding='utf-8')
