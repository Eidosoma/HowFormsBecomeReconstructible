"""Frozen protocol builders for Wagner local-memory plastic heredity."""

from __future__ import annotations

from dataclasses import replace

from .local_ph_config import (
    CopyNoiseSpec,
    LocalCarrierGenome,
    LocalConditionSpec,
    LocalSearchSpec,
    LocalStudySpec,
)


SEARCH_SEED = "b6841b44a03be122acf25419f1d36ded96dcc2100f5b811dd16fe572d1892f0a"
CONFIRMATION_SEED = "57dd56bef8f24045dbcaea06349bbdc602955e5d776e8ac9c4641490f2a3a942"

NOMINAL_COPY_NOISE = CopyNoiseSpec("nominal", 0.95, 0.02, 0.05)
STRONG_COPY_NOISE = CopyNoiseSpec("strong", 0.85, 0.10, 0.15)


def local_search_spec(*, smoke: bool = False) -> LocalSearchSpec:
    base = LocalSearchSpec("wagner-local-ph-v1-search", SEARCH_SEED)
    if not smoke:
        return base
    return replace(
        base,
        cohort_id="wagner-local-ph-v1-search-smoke",
        training_sources=2,
        validation_sources=3,
        population_size=8,
        generations=1,
        rotating_panel_size=1,
        training_futures_per_history=4,
        validation_futures_per_history=4,
        generation_cycles=2,
        horizon=12,
        strict_run=2,
        stable_run=2,
        bootstrap_repetitions=64,
    )


def _conditions(genomes: tuple[LocalCarrierGenome, ...]) -> tuple[LocalConditionSpec, ...]:
    values: list[LocalConditionSpec] = []
    for genome in genomes:
        prefix = genome.name
        values.extend(
            (
                LocalConditionSpec(f"{prefix}.intact", prefix, "intact", "nominal", True),
                LocalConditionSpec(f"{prefix}.strong", prefix, "intact", "strong"),
                LocalConditionSpec(f"{prefix}.random-mask", prefix, "random_mask", "nominal"),
                LocalConditionSpec(f"{prefix}.founder-write-off", prefix, "founder_write_off", "nominal"),
                LocalConditionSpec(f"{prefix}.renewal-off", prefix, "renewal_off", "nominal"),
                LocalConditionSpec(f"{prefix}.reader-off", prefix, "reader_off", "nominal"),
                LocalConditionSpec(f"{prefix}.shuffle", prefix, "shuffle", "nominal"),
                LocalConditionSpec(f"{prefix}.erase-g2", prefix, "erase_g2", "nominal"),
                LocalConditionSpec(f"{prefix}.reverse-g2", prefix, "reverse_g2", "nominal"),
                LocalConditionSpec(
                    f"{prefix}.erase-g2-rescue-g3",
                    prefix,
                    "erase_g2_rescue_g3",
                    "nominal",
                ),
            )
        )
    values.extend(
        (
            LocalConditionSpec("zero", None, "zero", "nominal"),
            LocalConditionSpec("perfect-latch", None, "perfect_latch", "nominal"),
        )
    )
    return tuple(values)


def local_confirmation_spec(
    nominees: tuple[LocalCarrierGenome, ...], *, smoke: bool = False
) -> LocalStudySpec:
    if not 1 <= len(nominees) <= 2:
        raise ValueError("local confirmation requires one or two frozen nominees")
    spec = LocalStudySpec(
        "wagner-local-ph-v1-confirmation",
        "untouched-local-noisy-causal-confirmation",
        CONFIRMATION_SEED,
        96,
        nominees,
        (NOMINAL_COPY_NOISE, STRONG_COPY_NOISE),
        _conditions(nominees),
    )
    if not smoke:
        spec.validate()
        return spec
    keep = tuple(
        value
        for value in spec.conditions
        if value.name in {f"{nominees[0].name}.intact", "zero", "perfect-latch"}
    )
    result = replace(
        spec,
        cohort_id="wagner-local-ph-v1-confirmation-smoke",
        source_count=2,
        genomes=(nominees[0],),
        conditions=keep,
        checkpoint_generations=(0, 1),
        challenges=("forced_break",),
        futures_per_history=4,
        generation_cycles=2,
        horizon=12,
        strict_run=2,
        stable_run=2,
        bootstrap_repetitions=64,
        exploratory=True,
    )
    result.validate()
    return result


def local_failure_atlas_spec(
    genomes: tuple[LocalCarrierGenome, ...], *, smoke: bool = False
) -> LocalStudySpec:
    """Exploratory fallback when no mechanism qualifies for confirmation."""

    if not genomes:
        raise ValueError("failure atlas requires diagnostic genomes")
    conditions = tuple(
        condition
        for genome in genomes
        for condition in (
            LocalConditionSpec(f"{genome.name}.intact", genome.name, "intact", "nominal", True),
            LocalConditionSpec(f"{genome.name}.strong", genome.name, "intact", "strong"),
        )
    ) + (
        LocalConditionSpec("zero", None, "zero", "nominal"),
        LocalConditionSpec("perfect-latch", None, "perfect_latch", "nominal"),
    )
    result = LocalStudySpec(
        "wagner-local-ph-v1-failure-atlas",
        "exploratory-failure-localization",
        SEARCH_SEED,
        16 if not smoke else 3,
        genomes,
        (NOMINAL_COPY_NOISE, STRONG_COPY_NOISE),
        conditions,
        checkpoint_generations=(0, 4, 8) if not smoke else (0, 1),
        challenges=("forced_break", "neutral_damage") if not smoke else ("forced_break",),
        futures_per_history=8 if not smoke else 4,
        generation_cycles=4 if not smoke else 2,
        horizon=32 if not smoke else 12,
        strict_run=8 if not smoke else 2,
        stable_run=3 if not smoke else 2,
        bootstrap_repetitions=1024 if not smoke else 64,
        exploratory=True,
    )
    result.validate()
    return result
