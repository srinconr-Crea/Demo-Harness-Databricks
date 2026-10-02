"""Trusted role prompts and bounded tools. Schemas never replace repository policy."""
import json
from pathlib import Path

import yaml

from .patch import FileOperation
from .repository_policy import valid_relative
from .skills import digest

CATALOG = Path(__file__).resolve().parents[1] / 'config/defaults/prompts.yaml'

TOOLS = {
    'list_tree': {'arguments': {'op': 'list_tree'},
                  'result': 'paths[], truncated; error/reason for rejected or bounded request'},
    'search_text': {'arguments': {'op': 'search_text', 'query': 'string 1..200'},
                    'result': 'matches[{path,line,text,sha256}], truncated; error/reason'},
    'read_file': {'arguments': {'op': 'read_file', 'path': 'authorized relative regular file'},
                  'result': 'path, sha256, content, truncated; error/reason'},
}


class PromptContracts:
    def __init__(self):
        self.catalog = yaml.safe_load(CATALOG.read_text(encoding='utf-8'))
        if (set(self.catalog) != {'version', 'base', 'roles'}
                or set(self.catalog['roles']) != {'explorer', 'planner', 'developer', 'openspec_verifier', 'verifier'}):
            raise ValueError('Catálogo de prompts inválido')
        self.sha256 = digest(self.catalog)

    def compose(self, role, phase):
        contract = self.catalog['roles'].get(role)
        if not contract or phase not in contract['phases']:
            raise ValueError('Rol/fase sin contrato compatible')
        system = '\n'.join((self.catalog['base'], f'ROLE: {role}; PHASE: {phase}',
                            'RESPONSIBILITY: ' + contract['responsibility'], 'OUTPUT: ' + contract['output']))
        return system, {'version': self.catalog['version'], 'catalog_sha256': self.sha256,
                        'prompt_sha256': digest(system), 'contract_sha256': digest(contract)}


def validate_request(request):
    if not isinstance(request, dict):
        raise ValueError('Solicitud de contexto inválida')  # noqa: TRY004 - public validation contract
    op = request.get('op')
    expected = {'list_tree': {'op'}, 'read_file': {'op', 'path'}, 'search_text': {'op', 'query'}}
    if op not in expected or set(request) != expected[op]:
        raise ValueError('Operación o campos de contexto inválidos')
    if op == 'read_file' and (not isinstance(request['path'], str)
                              or len(request['path']) > 500 or not valid_relative(request['path'])):
        raise ValueError('Ruta de lectura inválida')
    if op == 'search_text' and (not isinstance(request['query'], str) or not 1 <= len(request['query']) <= 200):
        raise ValueError('Consulta inválida')


def validate_output(role, value, payload, profile):
    if not isinstance(value, dict):
        raise ValueError('Contrato final inválido')  # noqa: TRY004 - public validation contract
    if role == 'explorer':
        if (set(value) - {'summary', 'questions'} or not isinstance(value.get('summary'), str)
                or not 1 <= len(value['summary']) <= 10000 or not isinstance(value.get('questions'), list)
                or len(value['questions']) > 5 or any(not isinstance(q, str) or not 1 <= len(q) <= 2000 for q in value['questions'])):
            raise ValueError('Contrato de exploración inválido')
    elif role == 'planner':
        if (set(value) - {'content', 'summary', 'manifest'} or not isinstance(value.get('content'), str)
                or not 20 <= len(value['content']) <= 50000):
            raise ValueError('Contrato del artefacto inválido')
        if payload.get('artifact') == 'proposal' and profile.general_patch:
            manifest = value.get('manifest')
            if (not isinstance(value.get('summary'), str) or not 1 <= len(value['summary']) <= 10000
                    or not isinstance(manifest, list) or not 1 <= len(manifest) <= profile.general_patch.max_files):
                raise ValueError('Propuesta requiere manifiesto')
            paths = set()
            for item in manifest:
                if (not isinstance(item, dict) or set(item) != {'op', 'path'} or not isinstance(item['path'], str)
                        or item['op'] not in profile.general_patch.operations or not profile.allows_code(item['path'])
                        or Path(item['path']).suffix not in profile.general_patch.extensions or item['path'] in paths):
                    raise ValueError('Manifiesto fuera de política')
                paths.add(item['path'])
    elif role == 'developer':
        if profile.general_patch:
            if set(value) - {'operations', 'notes'} or not isinstance(value.get('operations'), list):
                raise ValueError('Operaciones inválidas')
            if not 1 <= len(value['operations']) <= profile.general_patch.max_files:
                raise ValueError('Límite de operaciones')
            for item in value['operations']:
                if not isinstance(item, dict) or set(item) - {'op', 'path', 'content', 'expected_sha256'}:
                    raise ValueError('Campos de operación inválidos')
                operation = FileOperation.model_validate(item)
                if not profile.allows_code(operation.path):
                    raise ValueError('Operación fuera del perfil')
            # Exact approved-manifest comparison remains at the existing transition.
        elif set(value) - {'expression', 'notes'} or not isinstance(value.get('expression'), str) or not 1 <= len(value['expression']) <= 500:
            raise ValueError('Expresión inválida')
    else:
        if (role not in {'openspec_verifier', 'verifier'} or set(value) - {'approved', 'findings', 'notes'}
                or type(value.get('approved')) is not bool or not isinstance(value.get('findings'), list)
                or len(value['findings']) > 100 or any(not isinstance(f, str) or len(f) > 10000 for f in value['findings'])):
            raise ValueError('Contrato de verificación inválido')
    if 'notes' in value and (not isinstance(value['notes'], str) or len(value['notes']) > 10000):
        raise ValueError('Notas inválidas')
    if len(json.dumps(value, ensure_ascii=False).encode('utf-8')) > 2097152:
        raise ValueError('Salida fuera del presupuesto')
