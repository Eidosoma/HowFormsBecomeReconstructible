"""Registered protocols for Wagner PH origin/discrimination v1."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from .artifacts import canonical_digest
from .local_ph_config import CopyNoiseSpec, LocalCarrierGenome
from .wagner_ph_origin_config import (
    OriginAuditSpec,
    OriginCampaignSpec,
    OriginEvolutionSpec,
    OriginScreenSpec,
)


ORIGIN_SEED = canonical_digest("wagner-ph-origin-v1-campaign-production-2026-08-23")
SCREEN_SEED = canonical_digest(
    "wagner-ph-origin-v1-discrimination-screen-production-2026-08-23"
)
EVOLUTION_SEED = canonical_digest(
    "wagner-ph-origin-v1-factorial-evolution-production-2026-08-23"
)
AUDIT_SEED = canonical_digest(
    "wagner-ph-origin-v1-heldout-causal-pedigree-production-2026-08-23"
)
SMOKE_SCREEN_SEED = canonical_digest("wagner-ph-origin-v1-screen-software-smoke")
SMOKE_EVOLUTION_SEED = canonical_digest("wagner-ph-origin-v1-evolution-software-smoke")
SMOKE_AUDIT_SEED = canonical_digest("wagner-ph-origin-v1-audit-software-smoke")


ORIGIN_ENVIRONMENTS = (
    CopyNoiseSpec("d095-p002", 0.95, 0.02, 0.05),
    CopyNoiseSpec("d090-p002", 0.90, 0.02, 0.05),
    CopyNoiseSpec("d085-p002", 0.85, 0.02, 0.05),
    CopyNoiseSpec("d095-p010", 0.95, 0.10, 0.05),
    CopyNoiseSpec("d090-p010", 0.90, 0.10, 0.05),
    CopyNoiseSpec("d080-p002", 0.80, 0.02, 0.05),
    CopyNoiseSpec("d085-p010", 0.85, 0.10, 0.05),
    CopyNoiseSpec("d080-p010", 0.80, 0.10, 0.05),
)


def origin_scaffolds() -> tuple[LocalCarrierGenome, ...]:
    values = (
        LocalCarrierGenome(
            "origin-dormant", 0.0, 0.20, 0.0, 1, "outgoing", 1
        ),
        LocalCarrierGenome(
            "origin-weak", 0.10, 0.20, 0.10, 1, "outgoing", 1
        ),
    )
    for value in values:
        value.validate()
    return values


def origin_screen_spec(*, smoke: bool = False) -> OriginScreenSpec:
    result = OriginScreenSpec(
        cohort_id="wagner-ph-origin-v1-screen-smoke"
        if smoke
        else "wagner-ph-origin-v1-screen",
        master_seed=SMOKE_SCREEN_SEED if smoke else SCREEN_SEED,
        environments=ORIGIN_ENVIRONMENTS,
        futures_per_history=4 if smoke else 32,
        bootstrap_repetitions=64 if smoke else 4096,
    )
    result.validate()
    return result


def origin_evolution_template(*, smoke: bool = False) -> OriginEvolutionSpec:
    result = OriginEvolutionSpec(
        cohort_id="wagner-ph-origin-v1-evolution-smoke"
        if smoke
        else "wagner-ph-origin-v1-evolution",
        master_seed=SMOKE_EVOLUTION_SEED if smoke else EVOLUTION_SEED,
        scaffolds=origin_scaffolds(),
        selected_noise=ORIGIN_ENVIRONMENTS[2],
        harsher_noise=ORIGIN_ENVIRONMENTS[3],
        selected_environment=ORIGIN_ENVIRONMENTS[2].name,
        harsher_environment=ORIGIN_ENVIRONMENTS[3].name,
        populations_per_treatment=1 if smoke else 6,
        population_size=4 if smoke else 24,
        generations=1 if smoke else 28,
        elite_count=1 if smoke else 3,
        tournament_size=2 if smoke else 3,
        training_replicates=4,
        generation_cycles=2 if smoke else 4,
        horizon=12 if smoke else 16,
        strict_run=2 if smoke else 8,
        stable_run=2 if smoke else 3,
        bootstrap_repetitions=64 if smoke else 4096,
    )
    result.validate()
    return result


def origin_audit_spec(*, smoke: bool = False) -> OriginAuditSpec:
    result = OriginAuditSpec(
        cohort_id="wagner-ph-origin-v1-audit-smoke"
        if smoke
        else "wagner-ph-origin-v1-audit",
        master_seed=SMOKE_AUDIT_SEED if smoke else AUDIT_SEED,
        futures_per_history=4 if smoke else 64,
        bootstrap_repetitions=64 if smoke else 4096,
    )
    result.validate()
    return result


def origin_campaign_spec(*, smoke: bool = False) -> OriginCampaignSpec:
    result = OriginCampaignSpec(
        cohort_id="wagner-ph-origin-v1-smoke" if smoke else "wagner-ph-origin-v1",
        master_seed=ORIGIN_SEED,
        screen=origin_screen_spec(smoke=smoke),
        evolution_template=origin_evolution_template(smoke=smoke),
        audit=origin_audit_spec(smoke=smoke),
    )
    result.validate()
    return result


def selected_origin_evolution_spec(
    campaign: OriginCampaignSpec, selection: dict[str, Any]
) -> OriginEvolutionSpec:
    environments = {value.name: value for value in campaign.screen.environments}
    selected = str(selection["selected_environment"])
    harsher = str(selection["next_harsher_environment"])
    result = replace(
        campaign.evolution_template,
        selected_noise=environments[selected],
        harsher_noise=environments[harsher],
        selected_environment=selected,
        harsher_environment=harsher,
    )
    result.validate()
    return result


def protocol_digest(spec: OriginCampaignSpec) -> str:
    return canonical_digest(spec.to_dict())
