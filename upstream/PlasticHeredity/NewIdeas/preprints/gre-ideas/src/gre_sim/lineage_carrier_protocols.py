"""Frozen protocols for the Wagner-primary lineage-carrier campaign."""

from __future__ import annotations

from dataclasses import replace

from .lineage_carrier_config import (
    LineageArmSpec,
    LineageEvolutionSpec,
    LineageSourceSpec,
    LineageStudySpec,
    LineageWriterSpec,
)
from .plastic_heredity_v2_config import (
    CarrierV2Spec,
    PlasticHeredityV2Spec,
    V2Condition,
    WriterV2Spec,
)
from .plastic_heredity_v2_protocols import STATE_CARRIERS, carrier_grid, cue_grid


WRITER_CALIBRATION_SEEDS = {
    "wagner": "f8f0b13fb542b99316979bc3f7cb45f3ac63f49c1e3351e1d7155a3b95c9ee16",
    "boolean": "c87ea4b9638e0db3954de6823ab5f444f519182ca1839acbedbb58f485728cd2",
}
CARRIER_CALIBRATION_SEED = "8c06ff687bf35cf70651cb19a8dce012490cc3b97f82f23ea5402c501761f6d4"
DISCOVERY_SEED = "149871cf8fb5671d5887cc932fa8f0404ccfa1db28762e0ca1569545447b83ab"
CONFIRMATION_SEED = "824cc395173ee998f81a165adc9959145c37cdf7bb7c9039f79271c10c810431"
COMPATIBILITY_SEED = "958034882c47c68098813a67a099e85e617c7d43d7163a14f66ab8dad0ec7ea"
EVOLUTION_SEED = "2e1471a5546120b9314f87109ff2785424cc4ab5d22ece0a5da5b3f7775ce63"
INITIAL_REPLICATION_SEED = (
    "046211eb6738eca7e0fe34c1f1253d17a9ff9e96271bc3fae176e70bddb97eac"
)


def writer_calibration_spec(engine: str) -> PlasticHeredityV2Spec:
    """Return an engine-specific, acquisition-only natural-writer screen."""

    if engine not in {"boolean", "wagner"}:
        raise ValueError(f"unknown lineage writer engine: {engine}")
    writers = tuple(
        WriterV2Spec(
            f"{engine}.natural-{dose.fraction:g}x{dose.dwell}",
            "natural_clamp",
            dose.fraction,
            dose.dwell,
            (engine,),
        )
        for dose in cue_grid()
    )
    conditions = tuple(
        V2Condition(
            f"calibration.{writer.name}",
            writer.name,
            ("state_transplant",),
            (0,),
            ("release_only",),
            16,
        )
        for writer in writers
    )
    return PlasticHeredityV2Spec(
        f"wagner-lineage-v1-{engine}-writer-calibration",
        f"{engine}-natural-writer-acquisition-calibration",
        WRITER_CALIBRATION_SEEDS[engine],
        10,
        64 if engine == "wagner" else 32,
        writers,
        (next(value for value in STATE_CARRIERS if value.name == "state_transplant"),),
        conditions,
        engines=(engine,),
        exploratory=True,
    )


def exact_writer(engine: str) -> LineageWriterSpec:
    return LineageWriterSpec(f"{engine}.exact-upper-bound", engine, "exact", 1.0, 1)


def _source_specs(wagner: int, boolean: int) -> tuple[LineageSourceSpec, ...]:
    return (
        LineageSourceSpec("wagner", wagner),
        LineageSourceSpec("boolean", boolean),
    )


def _calibration_arms() -> tuple[LineageArmSpec, ...]:
    return (
        LineageArmSpec("natural-full", primary=True),
        LineageArmSpec("zero", bottleneck="zero"),
    )


def carrier_calibration_spec(
    selected_writers: tuple[LineageWriterSpec, ...],
    *,
    smoke: bool = False,
) -> LineageStudySpec:
    """Natural writing of all engine-neutral carrier settings."""

    return LineageStudySpec(
        "wagner-lineage-v1-carrier-calibration",
        "natural-carrier-calibration",
        CARRIER_CALIBRATION_SEED,
        _source_specs(2 if smoke else 48, 1 if smoke else 24),
        selected_writers,
        carrier_grid()[:2] if smoke else carrier_grid(),
        _calibration_arms(),
        (0, 1),
        ("forced_break",),
        4 if smoke else 16,
        midpoint_count=1 if smoke else 2,
        generation_cycles=2 if smoke else 4,
        horizon=12 if smoke else 32,
        strict_run=2 if smoke else 8,
        stable_run=2 if smoke else 3,
        bootstrap_repetitions=64 if smoke else 4096,
        exploratory=True,
    )


def discovery_arms() -> tuple[LineageArmSpec, ...]:
    return (
        LineageArmSpec("natural-full", primary=True),
        LineageArmSpec("targeted-k5", bottleneck="targeted", k=5),
        LineageArmSpec("targeted-k3", bottleneck="targeted", k=3),
        LineageArmSpec("targeted-k1", bottleneck="targeted", k=1),
        LineageArmSpec("random-k5", bottleneck="random", k=5),
        LineageArmSpec("random-k3", bottleneck="random", k=3),
        LineageArmSpec("random-k1", bottleneck="random", k=1),
        LineageArmSpec("pattern-shuffle", bottleneck="shuffle"),
        LineageArmSpec("opposite-history", bottleneck="opposite"),
        LineageArmSpec("zero", bottleneck="zero"),
        LineageArmSpec("write-disabled", write_enabled=False),
        LineageArmSpec("read-disabled", read_enabled=False),
        LineageArmSpec("no-rewrite", rewrite=False),
        LineageArmSpec("ablate-generation-2", ablate_generation=2),
        LineageArmSpec(
            "ablate-2-rescue-3", ablate_generation=2, rescue_generation=3
        ),
        LineageArmSpec("exact-full", writer_mode="exact"),
    )


def lineage_discovery_spec(
    selected_writers: tuple[LineageWriterSpec, ...],
    candidates: tuple[CarrierV2Spec, ...],
    *,
    smoke: bool = False,
) -> LineageStudySpec:
    if not 1 <= len(candidates) <= 3:
        raise ValueError("lineage discovery accepts two Wagner and one Boolean candidate")
    return LineageStudySpec(
        "wagner-lineage-v1-discovery",
        "multigeneration-causal-discovery",
        DISCOVERY_SEED,
        _source_specs(2 if smoke else 96, 1 if smoke else 48),
        selected_writers,
        candidates,
        discovery_arms()[:4] if smoke else discovery_arms(),
        (0, 1) if smoke else (0, 1, 2, 4, 8),
        ("forced_break",) if smoke else ("forced_break", "neutral_damage"),
        4 if smoke else 16,
        midpoint_count=1 if smoke else 2,
        generation_cycles=2 if smoke else 4,
        horizon=12 if smoke else 32,
        strict_run=2 if smoke else 8,
        stable_run=2 if smoke else 3,
        bootstrap_repetitions=64 if smoke else 4096,
        exploratory=True,
    )


def confirmation_arms(k: int) -> tuple[LineageArmSpec, ...]:
    if k not in {1, 3, 5, 10}:
        raise ValueError("confirmation bottleneck k must be one of 1, 3, 5, 10")
    arms = [
        LineageArmSpec("natural-full"),
        LineageArmSpec(f"selected-targeted-k{k}", bottleneck="targeted", k=k, primary=True),
        LineageArmSpec(f"matched-random-k{k}", bottleneck="random", k=k),
    ]
    smaller = {10: 5, 5: 3, 3: 1}.get(k)
    if smaller is not None:
        arms.append(
            LineageArmSpec(
                f"one-smaller-targeted-k{smaller}", bottleneck="targeted", k=smaller
            )
        )
    arms.extend(
        (
            LineageArmSpec("pattern-shuffle", bottleneck="shuffle"),
            LineageArmSpec("opposite-history", bottleneck="opposite"),
            LineageArmSpec("zero", bottleneck="zero"),
            LineageArmSpec("write-disabled", write_enabled=False),
            LineageArmSpec("read-disabled", read_enabled=False),
            LineageArmSpec("no-rewrite", rewrite=False),
            LineageArmSpec(
                "ablate-generation-2",
                bottleneck="targeted",
                k=k,
                ablate_generation=2,
            ),
            LineageArmSpec(
                "ablate-2-rescue-3",
                bottleneck="targeted",
                k=k,
                ablate_generation=2,
                rescue_generation=3,
            ),
            LineageArmSpec("exact-full", writer_mode="exact"),
        )
    )
    return tuple(arms)


def lineage_confirmation_spec(
    selected_writers: tuple[LineageWriterSpec, ...],
    candidates: tuple[CarrierV2Spec, ...],
    selected_k: int,
    *,
    smoke: bool = False,
) -> LineageStudySpec:
    if not any("wagner" in value.engines for value in candidates):
        raise ValueError("lineage confirmation requires a Wagner candidate")
    return LineageStudySpec(
        "wagner-lineage-v1-confirmation",
        "untouched-multigeneration-confirmation",
        CONFIRMATION_SEED,
        _source_specs(2 if smoke else 240, 1 if smoke else 96),
        selected_writers,
        candidates,
        confirmation_arms(selected_k)[:4] if smoke else confirmation_arms(selected_k),
        (0, 1) if smoke else (0, 1, 2, 4, 8, 16),
        ("forced_break",) if smoke else (
            "forced_break",
            "neutral_damage",
            "release_only",
        ),
        4 if smoke else 32,
        midpoint_count=1 if smoke else 2,
        generation_cycles=2 if smoke else 4,
        horizon=12 if smoke else 32,
        strict_run=2 if smoke else 8,
        stable_run=2 if smoke else 3,
        bootstrap_repetitions=64 if smoke else 4096,
        exploratory=False,
    )


def bounded_initial_replication_spec(
    writer: LineageWriterSpec,
    candidate: CarrierV2Spec,
    selected_k: int,
) -> LineageStudySpec:
    """Compute-bounded, Wagner-only replication that cannot replace confirmation."""

    if writer.engine != "wagner" or candidate.engines != ("wagner",):
        raise ValueError("bounded initial replication is Wagner-only")
    base = lineage_confirmation_spec((writer,), (candidate,), selected_k)
    return replace(
        base,
        cohort_id="wagner-lineage-v1-initial-replication-12h",
        phase="compute-bounded-prospective-wagner-replication",
        master_seed=INITIAL_REPLICATION_SEED,
        sources=(LineageSourceSpec("wagner", 128),),
        futures_per_cell=16,
        exploratory=True,
    )


def compatibility_spec(
    writer: LineageWriterSpec,
    candidate: CarrierV2Spec,
    selected_k: int,
    *,
    smoke: bool = False,
) -> LineageStudySpec:
    return LineageStudySpec(
        "wagner-lineage-v1-compatibility",
        "confirmed-carrier-recipient-compatibility",
        COMPATIBILITY_SEED,
        (LineageSourceSpec("wagner", 2 if smoke else 96),),
        (writer,),
        (candidate,),
        (
            LineageArmSpec("natural-full"),
            LineageArmSpec(
                f"selected-targeted-k{selected_k}",
                bottleneck="targeted",
                k=selected_k,
                primary=True,
            ),
            LineageArmSpec("pattern-shuffle", bottleneck="shuffle"),
            LineageArmSpec("zero", bottleneck="zero"),
        ),
        (0, 1) if smoke else (0, 1, 4, 8),
        ("forced_break",),
        4 if smoke else 16,
        recipient_modes=("clone",) if smoke else (
            "clone",
            "destination_matched",
            "descriptor_matched",
        ),
        midpoint_count=1 if smoke else 2,
        generation_cycles=2 if smoke else 4,
        horizon=12 if smoke else 32,
        strict_run=2 if smoke else 8,
        stable_run=2 if smoke else 3,
        bootstrap_repetitions=64 if smoke else 4096,
        exploratory=True,
    )


def evolution_spec(
    writer: LineageWriterSpec,
    candidate: CarrierV2Spec,
    selected_k: int,
    *,
    smoke: bool = False,
) -> LineageEvolutionSpec:
    return LineageEvolutionSpec(
        "wagner-lineage-v1-evolution-pilot",
        EVOLUTION_SEED,
        candidate,
        writer,
        selected_k,
        populations_per_treatment=1 if smoke else 32,
        population_size=4 if smoke else 64,
        generations=2 if smoke else 100,
        training_replicates=4,
        assay_replicates=4 if smoke else 32,
        heritability_offspring=1 if smoke else 8,
        exploratory=True,
    )
