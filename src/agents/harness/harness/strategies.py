"""Registered deterministic editors; each strategy owns its own validation gates."""

from __future__ import annotations

from .contracts import ClientProfile, RatioSpec, Story, parse_ratio_story
from .notebook_edit import apply_safe_ratio, extract_target_source


class SilverSafeRatioEditor:
    def parse(self, story: Story, profile: ClientProfile) -> RatioSpec:
        return parse_ratio_story(story, profile)

    def source(self, notebook: str, profile: ClientProfile) -> str:
        return extract_target_source(notebook, profile.strategy)

    def edit(self, notebook: str, profile: ClientProfile, spec: RatioSpec) -> str:
        return apply_safe_ratio(notebook, profile.strategy, spec)

    def validate(self, notebook: str, profile: ClientProfile, spec: RatioSpec) -> None:
        path = profile.strategy.notebook
        source = self.source(notebook, profile)
        compile(source, path, "exec")
        if source.count(f".withColumn('{spec.output_column}', {spec.expression})") != 1:
            raise ValueError("La edición no cumple el contrato Silver")


_EDITORS = {"silver_safe_ratio": SilverSafeRatioEditor()}


def get_editor(kind: str):
    try:
        return _EDITORS[kind]
    except KeyError as error:
        raise ValueError("No existe un editor validado para este perfil") from error
