"""Manual story and client policy contracts."""

from __future__ import annotations

import json
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path, PurePosixPath
from typing import Literal

import yaml
from pydantic import BaseModel, Field, StrictBool, ValidationError, field_validator


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


class RunAttempt(BaseModel):
    attempt_id: str
    state: Literal["queued", "running", "complete", "failed", "cancelled", "interrupted"]
    queued_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    changed_files: list[str] = Field(default_factory=list)
    result: dict | None = None
    publication: dict = Field(default_factory=lambda: {"stage": "not_started"})
    events: list[dict] = Field(default_factory=list)
    cancel_requested_at: datetime | None = None
    cancel_requested_by: str | None = None


class RunContract(BaseModel):
    schema_version: int = 3
    run_id: str
    story_id: str
    story: Story | None = None
    client_profile: str | None = None
    client_profile_version: str | None = None
    repository: str | None = None
    state: Literal["queued", "running", "complete", "failed", "cancelled", "interrupted"]
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
    schema_version: int = 2
    call_id: str
    run_id: str
    attempt_id: str
    story_id: str
    role: str
    model: str
    status: Literal["complete", "failed"] = "complete"
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


class DeveloperOutput(BaseModel):
    expression: str
    notes: str = ""


class VerifierOutput(BaseModel):
    approved: StrictBool
    notes: str = ""
    findings: list[str] = Field(default_factory=list)


_ROLE_OUTPUTS = {"analyst": AnalystOutput, "developer": DeveloperOutput, "verifier": VerifierOutput}


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


class ClientProfile(BaseModel):
    name: str = "default"
    version: str = "1"
    repository: str
    base_branch: str
    allowed_paths: list[str]
    strategy: SafeRatioStrategy | None = None
    github_app_id: int | None = None
    github_installation_id: int | None = None
    ui: dict[str, str] = Field(default_factory=dict)

    def allows(self, path: str) -> bool:
        pure = PurePosixPath(path)
        if pure.is_absolute() or ".." in pure.parts or "\\" in path or path.startswith(".github/"):
            return False
        return any(path == prefix.rstrip("/") or path.startswith(prefix.rstrip("/") + "/") for prefix in self.allowed_paths)

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
