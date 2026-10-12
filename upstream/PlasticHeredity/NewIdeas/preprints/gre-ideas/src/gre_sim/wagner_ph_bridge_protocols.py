"""Frozen protocol builders for the Wagner plastic-heredity bridge."""

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
from .local_ph_protocols import NOMINAL_COPY_NOISE, STRONG_COPY_NOISE
from .wagner_ph_bridge_config import (
    BridgeCampaignSpec,
    CoevolutionSpec,
    PhaseCellSpec,
    PhaseDiagramSpec,
    PrecisionReplicationSpec,
    ReliabilityMetricSpec,
)


BRIDGE_SEED = "0e6327971bf120f794ec6e502b75e02e9a2971d6683d89873fc41c3db7ae5244"
PRECISION_SEED = "0656c12ad05c39bf72f3af146c0f36c043040c9a3e5edb66b7912cf91827fafb"
PHASE_SEED = "40047c70fe6627f66b30336576d3c24ea26dc690bf5b93cf2e5b03275c557301"
CAUSAL_SEED = "ae69bf9bc9d936b3ed7ee9b03de6a373e213e481e6badf69d1f35b48eb2a66ed"
COEVOLUTION_SEED = "b7b749daaa96f48d45637218da0b7c6acc9d31d4aa754367a570989478a55b5c"


def _genome(
    label: str,
    base: LocalCarrierGenome,
    *,
    write_rate: float | None = None,
    decay: float | None = None,
    coupling: float | None = None,
    hysteresis: int | None = None,
    topology: str | None = None,
    k: int | None = None,
) -> LocalCarrierGenome:
    capacity = base.k if k is None else int(k)
    structure = base.topology if topology is None else str(topology)
    if structure == "all" and capacity < 10:
        structure = "outgoing"
    return LocalCarrierGenome(
        label,
        base.write_rate if write_rate is None else float(write_rate),
        base.decay if decay is None else float(decay),
        base.coupling if coupling is None else float(coupling),
        base.hysteresis if hysteresis is None else int(hysteresis),
        structure,
        capacity,
    )


def frozen_candidate_family(selection: dict[str, Any]) -> tuple[LocalCarrierGenome, ...]:
    """Freeze k=3/5/10 reductions of both prior top mechanisms."""

    raw = selection.get("diagnostic_top_two", [])
    if len(raw) != 2:
        raise ValueError("bridge campaign requires exactly two prior diagnostic leaders")
    values: list[LocalCarrierGenome] = []
    for family, item in enumerate(raw, start=1):
        base = LocalCarrierGenome(**item)
        for k in (3, 5, 10):
            values.append(
                _genome(
                    f"bridge-family-{family}.k{k}",
                    base,
                    topology="all" if k == 10 else "outgoing",
                    k=k,
                )
            )
    for value in values:
        value.validate()
    return tuple(values)


def precision_replication_spec(
    candidates: tuple[LocalCarrierGenome, ...], *, smoke: bool = False
) -> PrecisionReplicationSpec:
    if len(candidates) != 6:
        raise ValueError("precision audit requires the frozen six-member family")
    conditions = tuple(
        LocalConditionSpec(f"{value.name}.intact", value.name, "intact", "nominal", True)
        for value in candidates
    ) + (
        LocalConditionSpec("zero", None, "zero", "nominal"),
        LocalConditionSpec("perfect-latch", None, "perfect_latch", "nominal"),
    )
    study = LocalStudySpec(
        "wagner-ph-bridge-v1-precision",
        "prospective-four-block-repeatability-audit",
        PRECISION_SEED,
        2 if smoke else 64,
        candidates,
        (NOMINAL_COPY_NOISE,),
        conditions,
        checkpoint_generations=(0, 4, 8, 16),
        challenges=("forced_break", "release_only"),
        futures_per_history=4 if smoke else 64,
        generation_cycles=2 if smoke else 4,
        horizon=12 if smoke else 32,
        strict_run=2 if smoke else 8,
        stable_run=2 if smoke else 3,
        bootstrap_repetitions=64 if smoke else 1024,
        exploratory=True,
    )
    reliability = (
        ReliabilityMetricSpec(
            blocks=2,
            block_size=2,
            minimum_sign_concordance=0.50,
            minimum_positive_blocks=1,
        )
        if smoke
        else ReliabilityMetricSpec()
    )
    result = PrecisionReplicationSpec(study, reliability)
    result.validate()
    return result


def _phase_genome(
    axis: str,
    level: str,
    base: LocalCarrierGenome,
    **changes: Any,
) -> LocalCarrierGenome:
    return _genome(f"phase-{axis}-{level}", base, **changes)


def phase_diagram_spec(
    base: LocalCarrierGenome, *, smoke: bool = False
) -> PhaseDiagramSpec:
    """Return 29 mechanism cells plus one zero-carrier baseline."""

    genomes: list[LocalCarrierGenome] = []
    noises: dict[str, CopyNoiseSpec] = {"nominal": NOMINAL_COPY_NOISE}
    conditions: list[LocalConditionSpec] = []
    cells: list[PhaseCellSpec] = []

    def add(
        axis: str,
        level: str,
        genome: LocalCarrierGenome,
        *,
        noise: CopyNoiseSpec = NOMINAL_COPY_NOISE,
        intervention: str = "intact",
    ) -> None:
        condition = f"phase.{axis}.{level}"
        genomes.append(genome)
        noises[noise.name] = noise
        conditions.append(
            LocalConditionSpec(condition, genome.name, intervention, noise.name, True)
        )
        cells.append(
            PhaseCellSpec(
                condition,
                axis,
                level,
                condition,
                genome.name,
                noise.name,
                intervention,
            )
        )

    for k in (1, 2, 3, 5, 7, 10):
        add(
            "capacity",
            f"k{k}",
            _phase_genome(
                "capacity", f"k{k}", base, k=k, topology="all" if k == 10 else "outgoing"
            ),
        )
    for value in (0.25, 0.50, 0.75, 1.00):
        label = f"{value:.2f}".replace(".", "p")
        add("coupling", label, _phase_genome("coupling", label, base, coupling=value))
    for value in (0.25, 0.50, 0.75, 1.00):
        label = f"{value:.2f}".replace(".", "p")
        add("write", label, _phase_genome("write", label, base, write_rate=value))
    for value in (0.0, 0.01, 0.03, 0.10):
        label = f"{value:.2f}".replace(".", "p")
        add("decay", label, _phase_genome("decay", label, base, decay=value))
    for value in (1.0, 0.85, 0.70):
        label = f"{value:.2f}".replace(".", "p")
        noise = CopyNoiseSpec(f"dilution-{label}", value, 0.02, 0.05)
        add("dilution", label, _phase_genome("dilution", label, base), noise=noise)
    for value in (0.0, 0.10, 0.20):
        label = f"{value:.2f}".replace(".", "p")
        noise = CopyNoiseSpec(f"dropout-{label}", 0.95, value, 0.05)
        add("dropout", label, _phase_genome("dropout", label, base), noise=noise)
    for value in (0.0, 0.15):
        label = f"{value:.2f}".replace(".", "p")
        noise = CopyNoiseSpec(f"sigma-{label}", 0.95, 0.02, value)
        add("sigma", label, _phase_genome("sigma", label, base), noise=noise)
    add(
        "topology",
        "outgoing",
        _phase_genome("topology", "outgoing", base, topology="outgoing", k=5),
    )
    add(
        "topology",
        "self-feedback",
        _phase_genome("topology", "self-feedback", base, topology="self_feedback", k=5),
    )
    add(
        "topology",
        "random-mask",
        _phase_genome("topology", "random-mask", base, topology="outgoing", k=5),
        intervention="random_mask",
    )
    conditions.append(LocalConditionSpec("zero", None, "zero", "nominal"))
    cells.append(PhaseCellSpec("zero", "control", "zero", "zero", None, "nominal", "zero"))
    study = LocalStudySpec(
        "wagner-ph-bridge-v1-phase-map",
        "explicit-local-carrier-causal-phase-screen",
        PHASE_SEED,
        2 if smoke else 32,
        tuple(genomes),
        tuple(noises.values()),
        tuple(conditions),
        checkpoint_generations=(0, 1, 2, 4, 8, 16),
        challenges=("forced_break",),
        futures_per_history=4 if smoke else 8,
        generation_cycles=2 if smoke else 4,
        horizon=12 if smoke else 32,
        strict_run=2 if smoke else 8,
        stable_run=2 if smoke else 3,
        bootstrap_repetitions=64 if smoke else 512,
        exploratory=True,
    )
    result = PhaseDiagramSpec(
        study,
        tuple(cells),
        confirmation_sources=3 if smoke else 48,
        confirmation_futures_per_history=4 if smoke else 16,
    )
    result.validate()
    return result


def causal_confirmation_spec(
    phase: PhaseDiagramSpec,
    nominees: tuple[LocalCarrierGenome, ...],
    *,
    smoke: bool = False,
) -> LocalStudySpec:
    if not 1 <= len(nominees) <= phase.maximum_nominees:
        raise ValueError("causal confirmation requires one or two frozen nominees")
    conditions: list[LocalConditionSpec] = []
    for genome in nominees:
        prefix = genome.name
        conditions.extend(
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
        for locus in range(10):
            conditions.append(
                LocalConditionSpec(
                    f"{prefix}.ablate-locus-{locus}-g2",
                    prefix,
                    f"ablate_locus_{locus}_g2",
                    "nominal",
                )
            )
    conditions.extend(
        (
            LocalConditionSpec("zero", None, "zero", "nominal"),
            LocalConditionSpec("perfect-latch", None, "perfect_latch", "nominal"),
        )
    )
    spec = LocalStudySpec(
        "wagner-ph-bridge-v1-causal-confirmation",
        "fresh-causal-information-confirmation",
        CAUSAL_SEED,
        phase.confirmation_sources,
        nominees,
        (NOMINAL_COPY_NOISE, STRONG_COPY_NOISE),
        tuple(conditions),
        checkpoint_generations=phase.confirmation_checkpoints,
        challenges=phase.confirmation_challenges,
        futures_per_history=phase.confirmation_futures_per_history,
        generation_cycles=2 if smoke else 4,
        horizon=12 if smoke else 32,
        strict_run=2 if smoke else 8,
        stable_run=2 if smoke else 3,
        bootstrap_repetitions=64 if smoke else 1024,
        exploratory=True,
    )
    spec.validate()
    return spec


def coevolution_spec(
    initial_carrier: LocalCarrierGenome, *, smoke: bool = False
) -> CoevolutionSpec:
    result = CoevolutionSpec(
        "wagner-ph-bridge-v1-coevolution",
        COEVOLUTION_SEED,
        initial_carrier,
        NOMINAL_COPY_NOISE,
        STRONG_COPY_NOISE,
        populations_per_treatment=1 if smoke else 8,
        population_size=4 if smoke else 32,
        generations=2 if smoke else 30,
        elite_count=1 if smoke else 4,
        tournament_size=2 if smoke else 3,
        heldout_replicates=4 if smoke else 16,
        heritability_offspring=1 if smoke else 4,
        horizon=12 if smoke else 16,
        strict_run=2 if smoke else 8,
        stable_run=2 if smoke else 3,
        bootstrap_repetitions=64 if smoke else 2048,
    )
    result.validate()
    return result


def bridge_campaign_spec(
    prior_selection: dict[str, Any], *, smoke: bool = False
) -> BridgeCampaignSpec:
    candidates = frozen_candidate_family(prior_selection)
    precision = precision_replication_spec(candidates, smoke=smoke)
    strongest = candidates[2]
    phase = phase_diagram_spec(strongest, smoke=smoke)
    template = coevolution_spec(strongest, smoke=smoke)
    result = BridgeCampaignSpec(
        "wagner-ph-bridge-v1-smoke" if smoke else "wagner-ph-bridge-v1",
        BRIDGE_SEED,
        precision,
        phase,
        template,
    )
    result.validate()
    return result


def protocol_digest(spec: BridgeCampaignSpec) -> str:
    return canonical_digest(spec.to_dict())
