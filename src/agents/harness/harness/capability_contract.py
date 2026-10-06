"""Explicit OpenSpec destinations; narrative never grants write authority."""
from dataclasses import dataclass
import re

from .repository_policy import valid_relative


class CapabilityArtifactDefect(ValueError):
    """Runtime output disagrees with the validated declaration; never replan it."""
    category = 'harness_defect'


@dataclass(frozen=True)
class Capability:
    kind: str
    path: str

    def model_dump(self):
        return {'kind': self.kind, 'path': self.path}


def capability_output_contract():
    return [{'kind': 'new|modified', 'path': 'identificador relativo exacto de capacidad; no ruta OpenSpec ni spec.md'}]


def validate_capabilities(value, inventory):
    if not isinstance(value, list) or not 1 <= len(value) <= 100:
        raise ValueError('La propuesta requiere capacidades explícitas')
    result, seen = [], set()
    for item in value:
        if (not isinstance(item, dict) or set(item) != {'kind', 'path'}
                or item.get('kind') not in {'new', 'modified'}
                or not isinstance(item.get('path'), str)
                or not valid_relative(item['path']) or len(item['path']) > 300
                or any(not re.fullmatch(r'[a-z0-9][a-z0-9-]*', p) for p in item['path'].split('/'))):
            raise ValueError('Contrato de capacidad o ruta inválido')
        key = item['path'].casefold()
        if key in seen:
            raise ValueError('Capacidad duplicada')
        seen.add(key)
        exists = item['path'] in inventory
        if (item['kind'] == 'modified') != exists:
            raise ValueError('Capacidad modificada ausente o nueva ya existente en base')
        result.append(Capability(**item))
    return result


def validate_delta(content, capability, base_spec):
    """Check references before CLI strict validation of complete requirement bodies."""
    from .prompt_contracts import _document_lines
    lines = _document_lines(content)
    base_names = {m.group(1).strip() for line in _document_lines(base_spec or '')
                  if (m := re.match(r'^### Requirement: (.+)$', line))}
    section, seen = None, set()
    for line in lines:
        heading = re.match(r'^## (ADDED|MODIFIED|REMOVED|RENAMED) Requirements\s*$', line)
        if heading:
            section = heading.group(1)
            if capability.kind == 'new' and section != 'ADDED':
                raise ValueError('Una capacidad nueva solo admite requisitos ADDED')
        requirement = re.match(r'^### Requirement: (.+)$', line)
        if requirement:
            name = requirement.group(1).strip()
            if section is None or name in seen:
                raise ValueError('Sección o requisito delta duplicado/inválido')
            seen.add(name)
            if section in {'MODIFIED', 'REMOVED'} and name not in base_names:
                raise ValueError('El requisito delta no existe en la capacidad base')
            if section == 'ADDED' and name in base_names:
                raise ValueError('El requisito ADDED ya existe en la capacidad base')
        if section == 'RENAMED' and (rename := re.match(r'^- FROM: `### Requirement: (.+)`$', line)):
            if rename.group(1) not in base_names:
                raise ValueError('El requisito RENAMED no existe en la capacidad base')
