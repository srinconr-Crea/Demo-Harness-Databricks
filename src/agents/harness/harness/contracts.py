"""Manual story and client policy contracts."""

from __future__ import annotations

import json
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path, PurePosixPath
from typing import Literal

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    StrictBool,
    ValidationError,
    field_validator,
    model_validator,
)


class Story(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=160)
    architecture: str = Field(min_length=1, max_length=10000)
    source_target: str = Field(min_length=1, max_length=10000)
    business_rules: str = Field(min_length=1, max_length=10000)
    nonfunctional: str = Field(min_length=1, max_length=10000)
    validation: str = Field(min_length=1, max_length=10000)

    @field_validator("id", "title", "architecture", "source_target", "business_rules", "nonfunctional", "validation")
    @classmethod
    def nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El campo no puede estar vacío")
        return value


class StoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hu: str = Field(min_length=1, max_length=4000)
    description: str = Field(min_length=1, max_length=20000)

    @field_validator("hu", "description")
    @classmethod
    def nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El campo no puede estar vacío")
        return value


RunStage = Literal[
    "exploring", "awaiting_clarification", "proposing", "awaiting_plan_review",
    "updating", "applying", "correcting", "verifying", "preparing_final_diff",
    "awaiting_diff_review", "publishing", "complete", "failed", "cancelled",
]
RunState = Literal[
    "queued", "running", "awaiting_clarification", "awaiting_plan_review",
    "awaiting_diff_review", "complete", "failed", "cancelled", "interrupted",
]


class RunApproval(BaseModel):
    kind: Literal["plan", "diff"]
    revision: int = Field(ge=1)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    actor: str = Field(min_length=1)
    at: datetime | None = None


class RunEvent(BaseModel):
    seq: int = Field(ge=1)
    stage: RunStage | None = None
    kind: str = Field(min_length=1)
    revision: int = Field(ge=0)
    at: datetime | None = None
    actor: str | None = None
    details: dict = Field(default_factory=dict)


class SafeRatioStrategy(BaseModel):
    kind: Literal["silver_safe_ratio"]
    notebook: str
    table: str
    anchor_column: str
    allowed_source_columns: list[str] = Field(min_length=2)

    @field_validator("table", "anchor_column")
    @classmethod
    def valid_identifier(cls, value: str) -> str:
        if re.fullmatch(r"[a-z][a-z0-9_]{1,63}", value) is None:
            raise ValueError("Identificador de estrategia inválido")
        return value

    @field_validator("allowed_source_columns")
    @classmethod
    def valid_source_columns(cls, values: list[str]) -> list[str]:
        if any(re.fullmatch(r"[a-z][a-z0-9_]{1,63}", value) is None for value in values):
            raise ValueError("Columnas permitidas inválidas")
        return values


class RepositoryPolicy(BaseModel):
    scope: Literal['prefixes', 'repository'] = 'prefixes'
    read_only_paths: list[str] = Field(default_factory=lambda: ['.github/', 'openspec/', 'AGENTS.md'])
    denied_paths: list[str] = Field(default_factory=list)
    max_searches: int = Field(default=10, ge=1, le=50)
    max_reads: int = Field(default=20, ge=1, le=100)
    max_context_bytes: int = Field(default=200000, ge=1000, le=1000000)
    max_file_bytes: int = Field(default=50000, ge=1000, le=200000)
    max_rounds: int = Field(default=20, ge=1, le=30)
    timeout_seconds: int = Field(default=30, ge=1, le=120)

    @field_validator('read_only_paths', 'denied_paths')
    @classmethod
    def paths_valid(cls, values):
        from .repository_policy import valid_relative
        if any(not valid_relative(p.rstrip('/')) for p in values):
            raise ValueError('Ruta de política inválida')
        return values


class ImpactRule(BaseModel):
    paths: list[str] = Field(min_length=1)
    test_paths: list[str] = Field(default_factory=list)
    adapters: list[str] = Field(default_factory=list)


class GeneralPatchPolicy(BaseModel):
    allowed_paths: list[str] = Field(default_factory=list)
    extensions: list[str] = Field(min_length=1)
    operations: list[Literal["create", "modify", "delete"]] = Field(min_length=1)
    max_files: int = Field(ge=1, le=300)
    max_bytes: int = Field(ge=1, le=10_000_000)
    test_adapters: list[Literal["python_compile", "markdown_structure", "pytest_sandbox", "sql_lint", "yaml_validate", "json_validate", "toml_validate", "notebook_validate", "databricks_bundle_validate", "text_validate"]] = Field(min_length=1)
    test_paths: list[str] = Field(default_factory=list)
    impact_rules: list[ImpactRule] = Field(default_factory=list)
    schemas: dict[str, dict] = Field(default_factory=dict)
    bundle_target: str | None = Field(default=None, pattern=r'^[a-zA-Z][a-zA-Z0-9_-]{0,63}$')
    bundle_paths: list[str] = Field(default_factory=lambda: ['databricks.yml', 'resources/'])

    @field_validator("allowed_paths")
    @classmethod
    def valid_paths(cls, values: list[str]) -> list[str]:
        if any(not path or path.startswith(("/", ".")) or "\\" in path or ".." in PurePosixPath(path).parts for path in values):
            raise ValueError("Prefijo de edición general inválido")
        return values

    @field_validator("extensions")
    @classmethod
    def valid_extensions(cls, values: list[str]) -> list[str]:
        if any(re.fullmatch(r"\.[a-z0-9]{1,10}", value) is None for value in values):
            raise ValueError("Extensión de edición general inválida")
        return values

    @field_validator("test_paths")
    @classmethod
    def valid_test_paths(cls, values: list[str]) -> list[str]:
        if any(not path or path.startswith(("/", ".")) or "\\" in path or ".." in PurePosixPath(path).parts for path in values):
            raise ValueError("Objetivo de pruebas fuera de política")
        return values

    @model_validator(mode="after")
    def job_requires_targets(self):
        if "pytest_sandbox" in self.test_adapters and not self.test_paths:
            raise ValueError("El Job sandbox requiere objetivos de prueba configurados")
        from .repository_policy import valid_relative
        for rule in self.impact_rules:
            if any(not valid_relative(p.rstrip('/')) for p in [*rule.paths, *rule.test_paths]):
                raise ValueError('Regla de impacto inválida')
            if any(a not in self.test_adapters for a in rule.adapters):
                raise ValueError('Adaptador de impacto no habilitado')
        if any(not valid_relative(p.rstrip('/')) for p in self.bundle_paths):
            raise ValueError('Ruta de bundle inválida')
        if 'databricks_bundle_validate' in self.test_adapters and not self.bundle_target:
            raise ValueError('La validación de bundle requiere target confiable')
        return self


class RatioSpec(BaseModel):
    output_column: str
    numerator: str
    denominator: str

    @field_validator("output_column", "numerator", "denominator")
    @classmethod
    def valid_identifier(cls, value: str) -> str:
        if re.fullmatch(r"[a-z][a-z0-9_]{1,63}", value) is None:
            raise ValueError("Identificador de columna inválido")
        return value

    @property
    def expression(self) -> str:
        return f"safe_divide(F.col('{self.numerator}'), F.col('{self.denominator}'))"


class OpenSpecArtifactRef(BaseModel):
    artifact_id: str
    sha256: str
    revision: int | None = Field(default=None, ge=0)


class OpenSpecAttempt(BaseModel):
    change_id: str | None = None
    state: Literal["initializing", "planning", "validated", "archived", "published"] | None = None
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    prepared_files: list[str] = Field(default_factory=list)
    prepared_hashes: dict[str, str] = Field(default_factory=dict)
    published_hashes: dict[str, str] = Field(default_factory=dict)
    artifacts: dict[str, OpenSpecArtifactRef] = Field(default_factory=dict)
    artifact_history: dict[str, list[OpenSpecArtifactRef]] = Field(default_factory=dict)
    published_files: list[str] = Field(default_factory=list)


class RunAttempt(BaseModel):
    attempt_id: str
    profile_provenance: dict | None = None
    publication_mode: Literal['diff_review', 'approved_plan'] = 'diff_review'
    state: RunState
    stage: RunStage | None = None
    revision: int = Field(default=0, ge=0)
    base_sha: str | None = Field(default=None, pattern=r"^[a-f0-9]{40}$")
    checkpoint_id: str | None = None
    approvals: list[RunApproval] = Field(default_factory=list)
    timeline: list[RunEvent] = Field(default_factory=list)
    messages: list[dict] = Field(default_factory=list)
    context: dict = Field(default_factory=dict)
    queued_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    failure: dict | None = None
    changed_files: list[str] = Field(default_factory=list)
    result: dict | None = None
    publication: dict = Field(default_factory=lambda: {"stage": "not_started"})
    events: list[dict] = Field(default_factory=list)
    openspec: OpenSpecAttempt = Field(default_factory=OpenSpecAttempt)
    cancel_requested_at: datetime | None = None
    cancel_requested_by: str | None = None


class RunContract(BaseModel):
    schema_version: int = 5
    run_id: str
    story_id: str
    story: Story | StoryRequest | None = None
    client_profile: str | None = None
    client_profile_version: str | None = None
    repository: str | None = None
    state: RunState
    attempt_id: str | None = None
    instance_id: str | None = None
    attempts: list[RunAttempt] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    changed_files: list[str] = Field(default_factory=list)
    result: dict | None = None
    error: str | None = None
    stop_requests: list[dict] = Field(default_factory=list)


class AgentCallContract(BaseModel):
    schema_version: int = 3
    call_id: str
    run_id: str
    attempt_id: str
    story_id: str
    role: str
    stage: RunStage | None = None
    revision: int | None = Field(default=None, ge=0)
    candidate_revision: int | None = Field(default=None, ge=0)
    candidate_hash: str | None = Field(default=None, pattern=r'^[a-f0-9]{64}$')
    approved_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    instruction_provenance: dict | None = None
    profile_provenance: dict | None = None
    context_provenance: dict | None = None
    model: str
    status: Literal["complete", "failed"] = "complete"
    finish_reason: str | None = None
    effective_max_tokens: int | None = Field(default=None, gt=0)
    acceptance: str | None = None
    parent_call_id: str | None = None
    recovery_index: int | None = Field(default=None, ge=1, le=1)
    normalized_sha256: str | None = None
    response_evidence_sha256: str | None = None
    input_text: str | None = None
    output_text: str | None = None
    parsed_output: dict | None = None
    input_sha256: str | None = None
    output_sha256: str | None = None
    client_request_id: str | None = None
    databricks_request_id: str | None = None
    response: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None
    error: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: Decimal | None = None
    currency: Literal["USD"] = "USD"
    pricing_source: str


class AnalystOutput(BaseModel):
    valid: StrictBool
    notes: str = ""
    evidence: list[str] = Field(default_factory=list)


class PlannerOutput(BaseModel):
    content: str = Field(min_length=20, max_length=50000)
    strategy: Literal["silver_safe_ratio"]
    expression: str = Field(min_length=1, max_length=500)
    code_path: str = Field(min_length=1, max_length=500)


class DeveloperOutput(BaseModel):
    expression: str
    notes: str = ""


class VerifierOutput(BaseModel):
    approved: StrictBool
    notes: str = ""
    findings: list[str] = Field(default_factory=list)


_ROLE_OUTPUTS = {"analyst": AnalystOutput, "planner": PlannerOutput, "developer": DeveloperOutput, "verifier": VerifierOutput}


def parse_agent_output(role: str, response: str) -> dict:
    if role not in _ROLE_OUTPUTS:
        raise ValueError("Rol de agente no configurado")
    body = response.strip()
    if body.startswith("```json\n") and body.endswith("```"):
        body = body[len("```json\n"):-3].strip()
    elif body.startswith("```\n") and body.endswith("```"):
        body = body[len("```\n"):-3].strip()
    try:
        value = json.loads(body)
        return _ROLE_OUTPUTS[role].model_validate(value).model_dump()
    except (json.JSONDecodeError, ValidationError, TypeError) as error:
        raise ValueError(f"Salida no válida del rol {role}") from error


class ContextPolicy(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)
    enabled: bool = False
    version: Literal['deterministic-context-v1'] = 'deterministic-context-v1'
    max_input_tokens: int = Field(default=524288, ge=1024, le=2097152)
    output_reserve_tokens: int = Field(default=12000, ge=1, le=100000)
    max_prompt_bytes: int = Field(default=524288, ge=1024, le=2097152)
    cache_ttl_seconds: int = Field(default=300, ge=1, le=86400)
    cache_max_bytes: int = Field(default=1048576, ge=1024, le=10485760)
    cache_max_entries: int = Field(default=100, ge=1, le=1000)

    @model_validator(mode='after')
    def reserve_fits(self):
        if self.output_reserve_tokens >= self.max_input_tokens:
            raise ValueError('La reserva debe caber en el presupuesto')
        return self


class DecisionRecord(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    id: str
    kind: Literal['clarification', 'change', 'fact', 'interpretation']
    text: str = Field(min_length=1, max_length=10000)
    scope: str
    run_id: str
    attempt_id: str
    revision: int = Field(ge=0)
    origin_ref: str
    evidence_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    actor: str | None = None
    status: Literal['proposed', 'confirmed', 'superseded', 'conflict', 'stale']
    supersedes: str | None = None
    key: str | None = None
    value: str | None = None


class SelectionRecord(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    role: str
    phase: str
    included: list[str]
    excluded: list[dict]
    reason: str
    bytes_before: int = Field(ge=0)
    bytes_after: int = Field(ge=0)
    estimated_input_tokens: int = Field(ge=0)
    output_reserve_tokens: int = Field(ge=1)
    cache: dict


class ContextEnvelope(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    version: Literal['deterministic-context-v1'] = 'deterministic-context-v1'
    run_id: str
    attempt_id: str
    repository: str
    profile_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    base_sha: str = Field(pattern=r'^[a-f0-9]{40}$')
    revision: int = Field(ge=0)
    stage: str
    role: str
    checkpoint_id: str | None
    policy_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    prompt_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    sources: list[dict]
    decisions: list[DecisionRecord]
    questions: list[str]
    selection: SelectionRecord


class OpenSpecSkillPolicy(BaseModel):
    compatible_versions: list[str] = Field(default_factory=lambda: ['1.13.2'], min_length=1)
    max_skill_bytes: int = Field(default=131072, ge=1024, le=262144)
    max_catalog_bytes: int = Field(default=1048576, ge=1024, le=2097152)
    max_prompt_bytes: int = Field(default=524288, ge=1024, le=2097152)


class ClientProfile(BaseModel):
    _source_bytes: bytes = PrivateAttr(default=b'')
    _source_mode: str = PrivateAttr(default='in_memory')
    name: str = "default"
    version: str = "1"
    repository: str
    base_branch: str
    allowed_paths: list[str] = Field(default_factory=list)
    repository_policy: RepositoryPolicy = Field(default_factory=RepositoryPolicy)
    openspec_skills: OpenSpecSkillPolicy = Field(default_factory=OpenSpecSkillPolicy)
    openspec_root: Literal["openspec"]
    strategy: SafeRatioStrategy | None = None
    general_patch: GeneralPatchPolicy | None = None
    github_app_id: int | None = None
    github_installation_id: int | None = None
    reviewers: list[str] = Field(default_factory=list)
    ui: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def general_paths_within_profile(self):
        if self.repository_policy.scope == 'repository' and self.general_patch is None:
            raise ValueError('El alcance de repositorio requiere general_patch')
        if self.repository_policy.scope == 'prefixes' and self.general_patch and any(
            not any(path.rstrip("/") == prefix.rstrip("/") or path.startswith(prefix.rstrip("/") + "/") for prefix in self.allowed_paths)
            for path in self.general_patch.allowed_paths
        ):
            raise ValueError("Las rutas de edición general exceden el perfil cliente")
        return self

    def allows(self, path: str) -> bool:
        from .repository_policy import denied, matches
        policy = self.repository_policy
        if denied(path, policy.denied_paths) or any(matches(path, p) for p in [
            '.github', '.agents', '.harness', self.openspec_root, 'AGENTS.md', *policy.read_only_paths]):
            return False
        return policy.scope == 'repository' or any(matches(path, p) for p in self.allowed_paths)

    def allows_read(self, path: str) -> bool:
        from .repository_policy import denied
        return not denied(path, self.repository_policy.denied_paths)

    def allows_code(self, path: str) -> bool:
        from .repository_policy import matches
        return self.allows(path) and (self.general_patch is None or self.repository_policy.scope == 'repository'
            or any(matches(path, p) for p in self.general_patch.allowed_paths))

    def allows_openspec(self, path: str) -> bool:
        pure = PurePosixPath(path)
        return (
            not pure.is_absolute()
            and "\\" not in path
            and ".." not in pure.parts
            and path.startswith(self.openspec_root + "/")
            and all(part not in {"", ".", ".."} for part in path.split("/"))
        )

    def feature_branch(self, story: Story) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", f"{story.id}-{story.title}".lower()).strip("-")
        return f"feature/{slug[:90].rstrip('-')}"


def load_profile(path: str | Path) -> ClientProfile:
    return ClientProfile.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


def load_client_profile(directory: str | Path, name: str) -> ClientProfile:
    if re.fullmatch(r"[a-z][a-z0-9_-]*", name) is None:
        raise ValueError("Nombre de perfil inválido")
    return load_profile(Path(directory) / f"{name}.yaml")


_IDENTIFIER = r"[a-z][a-z0-9_]{1,63}"
_RATIO = re.compile(rf"(?<![a-z0-9_])({_IDENTIFIER})\s*=\s*({_IDENTIFIER})\s*/\s*({_IDENTIFIER})(?![a-z0-9_])", re.IGNORECASE)


def parse_ratio_story(story: Story, profile: ClientProfile) -> RatioSpec:
    strategy = profile.strategy
    if strategy is None:
        raise ValueError("El cliente no tiene una estrategia de edición configurada")
    if strategy.table not in story.source_target:
        raise ValueError("La HU no identifica la tabla configurada")
    matches = _RATIO.findall(story.business_rules)
    if len(matches) != 1:
        raise ValueError("La HU debe definir exactamente una razón como columna = numerador / denominador")
    output, numerator, denominator = (part.lower() for part in matches[0])
    if numerator not in strategy.allowed_source_columns or denominator not in strategy.allowed_source_columns:
        raise ValueError("La HU usa columnas fuera de las permitidas por el perfil")
    if output in strategy.allowed_source_columns:
        raise ValueError("La columna de salida coincide con una columna de origen")
    return RatioSpec(output_column=output, numerator=numerator, denominator=denominator)


def estimate_cost(
    input_tokens: int | None,
    output_tokens: int | None,
    input_usd_per_token: Decimal,
    output_usd_per_token: Decimal,
) -> Decimal | None:
    if input_tokens is None or output_tokens is None:
        return None
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("El uso de tokens no puede ser negativo")
    return input_usd_per_token * input_tokens + output_usd_per_token * output_tokens
