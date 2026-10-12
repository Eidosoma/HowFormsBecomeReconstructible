"""Frozen builders for Wagner PH renewal and evolvability v1."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from .artifacts import canonical_digest
from .local_ph_config import (
    CopyNoiseSpec,
    LocalCarrierGenome,
    LocalConditionSpec,
    LocalStudySpec,
)
from .wagner_ph_renewal_config import (
    MutationNeighborhoodSpec,
    RenewalCampaignSpec,
    RenewalEvolutionSpec,
    RenewalFrontierSpec,
)


RENEWAL_SEED = canonical_digest("wagner-ph-renewal-v1-campaign-2026-08-23")
FRONTIER_SEED = canonical_digest("wagner-ph-renewal-v1-frontier-fresh")
EVOLUTION_SEED = canonical_digest("wagner-ph-renewal-v1-paired-evolution-fresh")
AUDIT_SEED = canonical_digest("wagner-ph-renewal-v1-heldout-mutation-fresh")

RENEWAL_ENVIRONMENTS = (
    CopyNoiseSpec("nominal", 0.95, 0.02, 0.05),
    CopyNoiseSpec("mild-dilution", 0.85, 0.02, 0.05),
    CopyNoiseSpec("moderate-dropout", 0.95, 0.10, 0.05),
    CopyNoiseSpec("mixed-moderate", 0.85, 0.10, 0.10),
    CopyNoiseSpec("heavy", 0.70, 0.10, 0.10),
    CopyNoiseSpec("severe", 0.70, 0.20, 0.15),
)


def capacity_carrier(base: LocalCarrierGenome, k: int, name: str | None = None) -> LocalCarrierGenome:
    """Resize a carrier without granting an outcome-aware mask."""

    result = replace(
        base,
        name=name or f"renewal-k{k}",
        topology="all" if k == 10 else "outgoing",
        k=k,
    )
    result.validate()
    return result


def renewal_frontier_spec(
    base: LocalCarrierGenome, *, smoke: bool = False
) -> RenewalFrontierSpec:
    genomes = tuple(capacity_carrier(base, k) for k in (3, 5, 7, 10))
    conditions: list[LocalConditionSpec] = []
    for genome in genomes:
        for noise in RENEWAL_ENVIRONMENTS:
            prefix = f"k{genome.k}.{noise.name}"
            conditions.extend(
                (
                    LocalConditionSpec(
                        f"{prefix}.intact", genome.name, "intact", noise.name, True
                    ),
                    LocalConditionSpec(
                        f"{prefix}.renewal-off",
                        genome.name,
                        "renewal_off",
                        noise.name,
                    ),
                )
            )
    conditions.extend(
        (
            LocalConditionSpec("zero", None, "zero", "nominal"),
            LocalConditionSpec("perfect-latch", None, "perfect_latch", "nominal"),
        )
    )
    study = LocalStudySpec(
        "wagner-ph-renewal-v1-frontier-smoke"
        if smoke
        else "wagner-ph-renewal-v1-frontier",
        "renewal-dependence-capacity-copy-frontier",
        FRONTIER_SEED,
        1 if smoke else 32,
        genomes,
        RENEWAL_ENVIRONMENTS,
        tuple(conditions),
        checkpoint_generations=(0, 4, 8, 12, 16),
        challenges=("forced_break", "release_only"),
        futures_per_history=4 if smoke else 16,
        generation_cycles=2 if smoke else 4,
        horizon=12 if smoke else 32,
        strict_run=2 if smoke else 8,
        stable_run=2 if smoke else 3,
        bootstrap_repetitions=64 if smoke else 1024,
        exploratory=True,
    )
    result = RenewalFrontierSpec(
        study=study,
        environment_order=tuple(value.name for value in RENEWAL_ENVIRONMENTS),
    )
    result.validate()
    return result


def renewal_evolution_spec(
    base: LocalCarrierGenome, *, smoke: bool = False
) -> RenewalEvolutionSpec:
    result = RenewalEvolutionSpec(
        cohort_id="wagner-ph-renewal-v1-evolution-smoke"
        if smoke
        else "wagner-ph-renewal-v1-evolution",
        master_seed=EVOLUTION_SEED,
        initial_carrier=base,
        selected_noise=RENEWAL_ENVIRONMENTS[0],
        harsher_noise=RENEWAL_ENVIRONMENTS[1],
        selected_environment=RENEWAL_ENVIRONMENTS[0].name,
        harsher_environment=RENEWAL_ENVIRONMENTS[1].name,
        populations_per_treatment=1 if smoke else 10,
        population_size=4 if smoke else 32,
        generations=1 if smoke else 32,
        elite_count=1 if smoke else 4,
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


def mutation_neighborhood_spec(*, smoke: bool = False) -> MutationNeighborhoodSpec:
    result = MutationNeighborhoodSpec(
        cohort_id="wagner-ph-renewal-v1-audit-smoke"
        if smoke
        else "wagner-ph-renewal-v1-audit",
        master_seed=AUDIT_SEED,
        futures_per_history=4 if smoke else 64,
        bootstrap_repetitions=64 if smoke else 4096,
    )
    result.validate()
    return result


def renewal_campaign_spec(
    prior_evolution_selection: dict[str, Any], *, smoke: bool = False
) -> RenewalCampaignSpec:
    base = LocalCarrierGenome(**prior_evolution_selection["genome"])
    base.validate()
    result = RenewalCampaignSpec(
        cohort_id="wagner-ph-renewal-v1-smoke" if smoke else "wagner-ph-renewal-v1",
        master_seed=RENEWAL_SEED,
        frontier=renewal_frontier_spec(base, smoke=smoke),
        evolution_template=renewal_evolution_spec(base, smoke=smoke),
        mutation_audit=mutation_neighborhood_spec(smoke=smoke),
    )
    result.validate()
    return result


def selected_evolution_spec(
    campaign: RenewalCampaignSpec, selection: dict[str, Any]
) -> RenewalEvolutionSpec:
    environments = {value.name: value for value in RENEWAL_ENVIRONMENTS}
    selected = str(selection["selected_environment"])
    harsher = str(selection["next_harsher_environment"])
    result = replace(
        campaign.evolution_template,
        initial_carrier=LocalCarrierGenome(**selection["selected_genome"]),
        selected_noise=environments[selected],
        harsher_noise=environments[harsher],
        selected_environment=selected,
        harsher_environment=harsher,
    )
    result.validate()
    return result


def protocol_digest(spec: RenewalCampaignSpec) -> str:
    return canonical_digest(spec.to_dict())
