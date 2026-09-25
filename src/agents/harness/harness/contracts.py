"""Manual story and client policy contracts."""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path, PurePosixPath

import yaml
from pydantic import BaseModel, Field, field_validator


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


class ClientProfile(BaseModel):
    repository: str
    base_branch: str
    allowed_paths: list[str]
    pilot: dict[str, str] = Field(default_factory=dict)

    def allows(self, path: str) -> bool:
        pure = PurePosixPath(path)
        if pure.is_absolute() or ".." in pure.parts or "\\" in path:
            return False
        return any(path.startswith(prefix) for prefix in self.allowed_paths)

    def feature_branch(self, story: Story) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", f"{story.id}-{story.title}".lower()).strip("-")
        return f"feature/{slug[:90].rstrip('-')}"


def load_profile(path: str | Path) -> ClientProfile:
    return ClientProfile.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


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
