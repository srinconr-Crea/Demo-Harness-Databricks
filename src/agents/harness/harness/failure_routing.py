"""Evidence-bearing failure proposals; only the runtime chooses repair authority."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .repository_policy import valid_relative
from .skills import digest

WORKFLOW_VERSION = 'classified-corrections-v1'


class WorkflowFailure(ValueError):
    def __init__(self, message, category='infrastructure_evidence'):
        super().__init__(message)
        self.category = category


class Finding(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    category: Literal['implementation', 'scope_spec', 'infrastructure_evidence', 'harness_defect']
    code: str = Field(min_length=1, max_length=100, pattern=r'^[a-z][a-z0-9_]*$')
    criterion: str = Field(min_length=1, max_length=1000)
    evidence: str = Field(min_length=1, max_length=10000)
    paths: list[str] = Field(default_factory=list, max_length=100)
    operations: list[Literal['create', 'modify', 'delete']] = Field(default_factory=list, max_length=3)
    recommendation: str = Field(min_length=1, max_length=2000)


def parse_findings(values):
    if not isinstance(values, list) or len(values) > 100:
        raise ValueError('Contrato de hallazgos inválido')
    items = [Finding.model_validate(item) for item in values]
    if any(not valid_relative(path) for item in items for path in item.paths):
        raise ValueError('Ruta de hallazgo inválida')
    return items


def failure_route(values, manifest):
    items = parse_findings(values)
    if not items:
        raise ValueError('Rechazo sin evidencia clasificable')
    categories = {item.category for item in items}
    if categories & {'harness_defect', 'infrastructure_evidence'}:
        return 'failed'
    allowed = {item['path']: item['op'] for item in manifest}
    if 'scope_spec' in categories:
        return 'updating'
    for item in items:
        if not item.paths:
            raise ValueError('Corrección sin archivo afectado verificable')
        if any(path not in allowed for path in item.paths):
            return 'updating'
        if item.operations and any(op != allowed[path] and not (op == 'modify' and allowed[path] == 'create')
                                   for path in item.paths for op in item.operations):
            return 'updating'
    return 'correcting'


def progress_key(values, candidate_hash, manifest):
    items = parse_findings(values)
    blocker = sorted((item.category, item.code, tuple(sorted(item.paths)),
                      tuple(sorted(item.operations))) for item in items)
    relevant_paths = {path for item in items for path in item.paths}
    return digest({'blockers': blocker, 'candidate': candidate_hash,
                   'scope': sorted((item['op'], item['path']) for item in manifest if item['path'] in relevant_paths)})


def finding_contract():
    return {'category': 'implementation|scope_spec|infrastructure_evidence|harness_defect',
            'code': 'stable_lowercase_code', 'criterion': 'Criterio aprobado incumplido',
            'evidence': 'Referencia o resultado real, nunca una prueba inventada',
            'paths': ['ruta autorizada afectada'], 'operations': [],
            'recommendation': 'Corrección propuesta sin conferir permisos'}
