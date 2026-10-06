"""Trusted role prompts and bounded tools. Schemas never replace repository policy."""
import json
import re
from pathlib import Path

import yaml

from .patch import FileOperation
from .repository_policy import valid_relative
from .skills import digest
from .models import sanitize_log_value

CATALOG = Path(__file__).resolve().parents[1] / 'config/defaults/prompts.yaml'


class ArtifactPresentationError(ValueError):
    """Recoverable document presentation, never a policy or manifest denial."""
    category = 'invalid_contract'


def required_headings(payload):
    if payload.get('artifact') in {'specs', 'tasks'}:
        return []
    return sorted({m.group(1).strip() for line in _document_lines(payload.get('template') or '')
                   if '<!--' not in line and (m := re.match(r'^ {0,3}## +(.+?) *#*$', line))})


def artifact_structure(payload):
    return {'required_headings': required_headings(payload),
            'instruction': 'Conserva literalmente los encabezados requeridos de la plantilla, sin traducirlos. '
                           'Redacta el cuerpo en español. Specs conserva secciones delta y tasks sus checkboxes; '
                           'content se serializa una sola vez. Una solicitud de contexto no contiene el documento final.'}


def validate_planner_manifest(manifest, profile, artifact='proposal'):
    policy = profile.general_patch
    if not isinstance(manifest, list) or not 1 <= len(manifest) <= policy.max_files:
        raise ValueError('La propuesta requiere resumen y manifiesto explícitos')
    paths = set()
    for index, item in enumerate(manifest, 1):
        reason = None
        if not isinstance(item, dict) or set(item) != {'op', 'path'} or not isinstance(item.get('path'), str):
            reason = 'campos o tipos inválidos'
        elif item['op'] not in policy.operations:
            reason = 'operación no permitida'
        elif not valid_relative(item['path']):
            reason = 'ruta relativa inválida'
        elif profile.allows_openspec(item['path']):
            reason = 'OpenSpec se gestiona fuera del manifiesto de código'
        elif not profile.allows_code(item['path']):
            reason = 'ruta fuera del perfil'
        elif Path(item['path']).suffix not in policy.extensions:
            reason = 'extensión no permitida'
        elif item['path'] in paths:
            reason = 'ruta duplicada'
        if reason:
            # The original path remains in protected response evidence. Do not echo
            # arbitrary model strings into the public failure message.
            raise ValueError(f'El manifiesto excede la política del cliente ({artifact}, entrada {index}: {reason})')
        paths.add(item['path'])
    return paths


def _document_lines(content):
    lines, fence = [], None
    for line in content.splitlines():
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})', line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence) and not line[marker.end():].strip():
                fence = None
            continue
        if fence is None:
            lines.append(line)
    return lines


def validate_artifact_content(content, payload):
    artifact = payload.get('artifact')
    if artifact not in {'proposal', 'specs', 'design', 'tasks'}:
        return
    if not isinstance(content, str) or not 20 <= len(content) <= 50000:
        raise ValueError(f'El planner devolvió un artefacto OpenSpec inválido ({artifact})')
    lines = _document_lines(content)
    headings = {m.group(1).strip() for line in lines
                if (m := re.match(r'^ {0,3}## +(.+?) *#*$', line))}
    required = set(required_headings(payload))
    if artifact == 'specs':
        required = set()
        valid = bool(headings & {'ADDED Requirements', 'MODIFIED Requirements', 'REMOVED Requirements', 'RENAMED Requirements'})
    elif artifact == 'tasks':
        valid = any(re.match(r'^ {0,3}- \[[ xX]\] +\S', line) for line in lines)
    else:
        valid = any(re.match(r'^ {0,3}#{1,6} +\S', line) for line in lines)
    if len(lines) < 2 or not valid or not required <= headings:
        reason = 'serialización adicional del Markdown' if '\\n' in content and '\n' not in content else 'estructura Markdown requerida ausente'
        missing = sorted(required - headings)
        detail = '; encabezados requeridos ausentes: ' + ', '.join(missing[:10]) if missing else ''
        detail = sanitize_log_value(detail, 500)
        raise ArtifactPresentationError(f'Contrato del artefacto inválido ({artifact}: {reason}{detail})')


def validate_planner_output(value, payload, profile=None):
    """Validate authority before diagnosing document presentation in every route."""
    if payload.get('expected_expression') is not None:
        from .contracts import parse_agent_output
        if not isinstance(value, dict) or set(value) != {'content', 'strategy', 'code_path', 'expression'}:
            raise ValueError('Contrato del artefacto inválido')
        result = parse_agent_output('planner', json.dumps(value, ensure_ascii=False))
        if (profile is None or profile.strategy is None
                or result['strategy'] != profile.strategy.kind
                or result['code_path'] != profile.strategy.notebook
                or result['expression'] != payload['expected_expression']
                or not profile.allows(result['code_path'])):
            raise ValueError('El manifiesto del planner excede la política validada')
    else:
        if (not isinstance(value, dict) or set(value) - {'content', 'summary', 'manifest', 'capabilities'}
                or not isinstance(value.get('content'), str) or not 20 <= len(value['content']) <= 50000):
            raise ValueError('Contrato del artefacto inválido')
        if payload.get('artifact') == 'proposal' and profile and profile.general_patch:
            if not isinstance(value.get('summary'), str) or not 1 <= len(value['summary']) <= 10000:
                raise ValueError('Propuesta requiere manifiesto')
            validate_planner_manifest(value.get('manifest'), profile)
        if payload.get('artifact') == 'proposal' and 'capability_inventory' in payload:
            from .capability_contract import validate_capabilities
            validate_capabilities(value.get('capabilities'), payload['capability_inventory'])
    validate_artifact_content(value['content'], payload)


def planner_artifact_output(artifact, profile=None):
    output = {'content': 'Markdown completo, serializado una sola vez en el JSON externo; tras parsear contiene saltos reales.'}
    if artifact == 'proposal' and profile and profile.general_patch:
        output.update(summary='Objetivo y comportamiento previsto en español',
                      manifest=[{'op': 'create|modify|delete', 'path': 'ruta de código o pruebas permitida; nunca OpenSpec'}])
    return output

TOOLS = {
    'list_tree': {'arguments': {'op': 'list_tree'},
                  'result': 'paths[], truncated; error/reason for rejected or bounded request'},
    'search_text': {'arguments': {'op': 'search_text', 'query': 'string 1..200'},
                    'result': 'matches[{path,line,text,sha256}], truncated; error/reason'},
    'read_file': {'arguments': {'op': 'read_file', 'path': 'authorized relative regular file'},
                  'result': 'path, sha256, content, truncated; error/reason'},
}


def context_contract():
    return (
        'Una sola operación de contexto por turno. Responde exclusivamente con '
        'context_request como objeto, nunca lista, null ni mezclado con salida final. '
        'Formas exactas: {"context_request":{"op":"list_tree"}}; '
        '{"context_request":{"op":"read_file","path":"src/common/schema.py"}}; '
        '{"context_request":{"op":"search_text","query":"normalize_table_name"}}. '
        'op es string. list_tree solo admite op; read_file admite op y path '
        '(string relativo autorizado, hasta 500 caracteres); search_text admite op y query '
        '(string de 1 a 200 caracteres). No agregues path a list_tree o search_text. '
        'Los límites de lecturas, búsquedas, rondas, bytes y tiempo son los del perfil. '
        'Después del resultado solicita otra operación individual o entrega el contrato '
        'final del rol, sin context_request. Los rechazos no amplían permisos.'
    )


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
        received = 'lista' if isinstance(request, list) else 'null' if request is None else 'otro tipo'
        raise ValueError(f'context_request debe ser un objeto; se recibió {received}')
    op = request.get('op')
    expected = {'list_tree': {'op'}, 'read_file': {'op', 'path'}, 'search_text': {'op', 'query'}}
    if not isinstance(op, str) or op not in expected or set(request) != expected[op]:
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
        validate_planner_output(value, payload, profile)
    elif role == 'developer':
        if profile.general_patch:
            if set(value) - {'operations', 'notes', 'coverage'} or not isinstance(value.get('operations'), list):
                raise ValueError('Operaciones inválidas')
            if not 0 <= len(value['operations']) <= profile.general_patch.max_files:
                raise ValueError('Límite de operaciones')
            for item in value['operations']:
                if not isinstance(item, dict) or set(item) - {'op', 'path', 'content', 'expected_sha256'}:
                    raise ValueError('Campos de operación inválidos')
                operation = FileOperation.model_validate(item)
                if not profile.allows_code(operation.path):
                    raise ValueError('Operación fuera del perfil')
            if payload.get('workflow_version') == 'classified-corrections-v1':
                from .patch import ManifestCoverage
                coverage = value.get('coverage')
                if not isinstance(coverage, list) or len(coverage) > profile.general_patch.max_files:
                    raise ValueError('Cobertura inválida')
                for item in coverage:
                    ManifestCoverage.model_validate(item)
        elif set(value) - {'expression', 'notes'} or not isinstance(value.get('expression'), str) or not 1 <= len(value['expression']) <= 500:
            raise ValueError('Expresión inválida')
    else:
        classified = role == 'openspec_verifier' and payload.get('workflow_version') == 'classified-corrections-v1'
        if (role not in {'openspec_verifier', 'verifier'} or set(value) - {'approved', 'findings', 'notes'}
                or type(value.get('approved')) is not bool or not isinstance(value.get('findings'), list)
                or len(value['findings']) > 100 or (not classified and any(not isinstance(f, str) or len(f) > 10000 for f in value['findings']))):
            raise ValueError('Contrato de verificación inválido')
        if classified:
            from .failure_routing import parse_findings
            parse_findings(value['findings'])
            if bool(value['findings']) == value['approved']:
                raise ValueError('Aprobación y hallazgos bloqueantes contradictorios')
    if 'notes' in value and (not isinstance(value['notes'], str) or len(value['notes']) > 10000):
        raise ValueError('Notas inválidas')
    if len(json.dumps(value, ensure_ascii=False).encode('utf-8')) > 2097152:
        raise ValueError('Salida fuera del presupuesto')
