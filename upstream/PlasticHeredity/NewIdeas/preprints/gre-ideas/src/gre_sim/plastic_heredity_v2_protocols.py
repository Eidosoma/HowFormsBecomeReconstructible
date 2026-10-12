"""Frozen staged protocols for the Plastic Heredity v2 campaign."""

from __future__ import annotations

from dataclasses import replace

from .plastic_heredity_v2_config import (
    CarrierStudyV2Spec,
    CarrierV2Spec,
    EvolutionV2Spec,
    PlasticHeredityV2Spec,
    V2Condition,
    WriterV2Spec,
)
from .plastic_memory_config import (
    CueDose,
    MarkSetting,
    MemoryCondition,
    MemoryModelSpec,
    MemorySourceSpec,
    PlasticMemorySpec,
)


FIXTURE_SEED = "a75a5e58b7038e0defc3fbd0d9bd2f682c75c3c8f5c0a66361801a309d60abc0"
STATE_DISCOVERY_SEED = "903c5fb58b2e9040fabb0942e921fefdaf13969dd62c150bfe9f5e85ea6cbc07"
STATE_CONFIRMATION_SEED = "5eda74252d303aa11eba502c3ba6252cd54e687aeb32359470351dac3f28214c"
CUE_CALIBRATION_SEED = "1a3d0a96fe7ca77e0239abd3b8026589ae19e06f99a465b4bf7b6325d98c7cb3"
CUE_DISCOVERY_SEED = "677041e0f976d7816e5b2adeb03b075e0d7cf6474379e37d388eece6313db9b4"
CUE_CONFIRMATION_SEED = "0709917d51f7ab40ec42f12bbe3eca11849807a8993544ddb31eb15f0431b5e5"
ATLAS_SEED = "af1ee2d6e4d61511a913b61bca41b27a07bb5cdaa682d3fab2496ce3d63bf04a"
ATLAS_CONFIRMATION_SEED = "0fc494c4ce59575f4d11ad38450b8a110e532afd8f5ee112aeed636a2cab7ff7"
CARRIER_CALIBRATION_SEED = "93fe7431775a14567a61b7ed35de69b53d15ea2191e288320ea8e7297aeae282"
CARRIER_DISCOVERY_SEED = "cf94f6bce72e2e620df84d098f121076c871a48b0d1eb4210ba3446be706dbe0"
CARRIER_CONFIRMATION_SEED = "1cbfa92a1751789e61669a7f6819bd6ec697b58e496e6f389e4fa287241b932b"
COMMON_RESCORE_SEED = "08212d00aaf43e3f92c702fec6e32f9414c7280857b5de59d67bb6dc722d4eb6"
EVOLUTION_DISCOVERY_SEED = "b3f166da761b27d39325795581553d10966e383d12c0b747551278d763771cb9"
EVOLUTION_CONFIRMATION_SEED = "301db95a9379d31b9f2099ee45b24ec5160885705a43dc71cb25226043e00d5e"
NATIVE_CARRIER_CALIBRATION_SEED = "38ce436cb534e5d63501116f9444748f58898f2acc5b3dfc300c557d3847a084"
NATIVE_CARRIER_DISCOVERY_SEED = "72ce873e79177f761f9d664d429ad1bdfe5954356eae613897d05181656c22a4"
NATIVE_CARRIER_CONFIRMATION_SEED = "3a4ef11591d1062cd375bdc6b0fddc3bed7bc89556a060931aee156cd52597a5"

NO_MARK = MarkSetting("none", 0, 0.0)
EXACT_WRITER = WriterV2Spec("exact-target", "exact_target", 1.0, 1)

STATE_CARRIERS = tuple(
    CarrierV2Spec(name, "state", name)
    for name in (
        "self_continuation",
        "state_transplant",
        "reset_both",
        "destination_matched_donor",
        "descriptor_matched_null",
        "state_pattern_shuffle",
    )
)


def _state_conditions(writer: str, full: bool = True) -> tuple[V2Condition, ...]:
    core_futures = 128 if full else 4
    persistence_futures = 64 if full else 4
    return (
        V2Condition(
            "state-primary",
            writer,
            tuple(value.name for value in STATE_CARRIERS),
            (0,),
            ("neutral_damage",),
            core_futures,
        ),
        V2Condition(
            "state-recurrence",
            writer,
            ("state_transplant", "reset_both"),
            (0,),
            ("forced_break",),
            core_futures,
        ),
        V2Condition(
            "state-persistence",
            writer,
            ("state_transplant", "reset_both", "state_pattern_shuffle"),
            (1, 2, 4, 8) if full else (1,),
            ("release_only", "neutral_damage", "forced_break") if full else ("release_only",),
            persistence_futures,
        ),
    )


def exact_state_fixture_spec() -> PlasticHeredityV2Spec:
    return PlasticHeredityV2Spec(
        "plastic-heredity-v2-fixture",
        "exact-state-engineering-fixture",
        FIXTURE_SEED,
        4,
        1,
        (EXACT_WRITER,),
        STATE_CARRIERS,
        _state_conditions(EXACT_WRITER.name, full=False),
        midpoint_count=1,
        horizon=12,
        stable_run=2,
        strict_run=2,
        minimum_basin_fraction=0.0,
        minimum_form_distance=0.25,
        maximum_source_proposals=100_000,
        bootstrap_repetitions=64,
        exploratory=True,
    )


def exact_state_discovery_spec() -> PlasticHeredityV2Spec:
    """The registered 2,555,904-future fair-engine discovery."""

    return PlasticHeredityV2Spec(
        "plastic-heredity-v2-state-discovery",
        "matched-exact-state-discovery",
        STATE_DISCOVERY_SEED,
        10,
        96,
        (EXACT_WRITER,),
        STATE_CARRIERS,
        _state_conditions(EXACT_WRITER.name),
        exploratory=True,
    )


def exact_state_confirmation_spec() -> PlasticHeredityV2Spec:
    """The untouched 6,389,760-future fair-engine confirmation."""

    return PlasticHeredityV2Spec(
        "plastic-heredity-v2-state-confirmation",
        "matched-exact-state-confirmation",
        STATE_CONFIRMATION_SEED,
        10,
        240,
        (EXACT_WRITER,),
        STATE_CARRIERS,
        _state_conditions(EXACT_WRITER.name),
        exploratory=False,
    )


def cue_grid() -> tuple[CueDose, ...]:
    return tuple(
        CueDose(fraction, dwell)
        for fraction in (0.25, 0.50, 0.75, 1.0)
        for dwell in (1, 4, 16)
    )


def natural_cue_calibration_spec() -> PlasticHeredityV2Spec:
    writers = tuple(
        WriterV2Spec(
            f"{engine}.natural-{dose.fraction:g}x{dose.dwell}",
            "natural_clamp",
            dose.fraction,
            dose.dwell,
            (engine,),
        )
        for engine in ("boolean", "wagner")
        for dose in cue_grid()
    )
    carriers = (CarrierV2Spec("state_transplant", "state", "state_transplant"),)
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
        "plastic-heredity-v2-cue-calibration",
        "balanced-natural-cue-calibration",
        CUE_CALIBRATION_SEED,
        10,
        32,
        writers,
        carriers,
        conditions,
        exploratory=True,
    )


def natural_cue_state_spec(
    selected: dict[str, CueDose],
    confirmation: bool,
) -> PlasticHeredityV2Spec:
    """Build the one-writer-per-engine naturalistic transfer test."""

    missing = set(("boolean", "wagner")) - set(selected)
    if missing:
        raise ValueError(f"natural cue selection missing engines: {sorted(missing)}")
    writers = tuple(
        WriterV2Spec(
            f"{engine}.selected-natural",
            "natural_clamp",
            selected[engine].fraction,
            selected[engine].dwell,
            (engine,),
        )
        for engine in ("boolean", "wagner")
    )
    conditions = tuple(
        replace(condition, name=f"{writer.name}.{condition.name}")
        for writer in writers
        for condition in _state_conditions(writer.name)
    )
    return PlasticHeredityV2Spec(
        (
            "plastic-heredity-v2-cue-confirmation"
            if confirmation
            else "plastic-heredity-v2-cue-discovery"
        ),
        (
            "untouched-natural-cue-transfer-confirmation"
            if confirmation
            else "natural-cue-transfer-discovery"
        ),
        CUE_CONFIRMATION_SEED if confirmation else CUE_DISCOVERY_SEED,
        10,
        240 if confirmation else 96,
        writers,
        STATE_CARRIERS,
        conditions,
        exploratory=not confirmation,
    )


def carrier_grid() -> tuple[CarrierV2Spec, ...]:
    values: list[CarrierV2Spec] = []
    for mechanism in ("trace", "recurrent_field"):
        for half_life in (1, 4, 8, 16):
            for coupling in (0.25, 0.50, 0.75):
                values.append(
                    CarrierV2Spec(
                        f"{mechanism}.half-{half_life}.mu-{coupling:g}",
                        mechanism,
                        "carrier_transplant",
                        half_life=half_life,
                        coupling=coupling,
                    )
                )
    for threshold in (1, 2):
        for retention in (4, 8, 16):
            for coupling in (0.50, 1.0):
                values.append(
                    CarrierV2Spec(
                        f"latch.threshold-{threshold}.retention-{retention}.mu-{coupling:g}",
                        "latch",
                        "carrier_transplant",
                        coupling=coupling,
                        write_threshold=threshold,
                        retention=retention,
                    )
                )
    return tuple(values)


def carrier_calibration_spec() -> CarrierStudyV2Spec:
    return CarrierStudyV2Spec(
        "plastic-heredity-v2-carrier-calibration",
        "engine-neutral-carrier-calibration",
        CARRIER_CALIBRATION_SEED,
        32,
        carrier_grid(),
        16,
        ("carrier_transplant", "reset"),
        (0,),
        ("forced_break",),
        exploratory=True,
    )


def carrier_discovery_spec(
    selected: tuple[CarrierV2Spec, ...],
) -> CarrierStudyV2Spec:
    if not 1 <= len(selected) <= 4:
        raise ValueError("carrier discovery accepts one to four engine nominations")
    return CarrierStudyV2Spec(
        "plastic-heredity-v2-carrier-discovery",
        "engine-neutral-carrier-causal-discovery",
        CARRIER_DISCOVERY_SEED,
        96,
        selected,
        32,
        (
            "carrier_transplant",
            "reset",
            "write_disabled",
            "inert",
            "pattern_shuffle",
            "ablation_0",
            "ablation_25",
            "ablation_50",
            "ablation_100",
            "random_ablation_25",
            "random_ablation_50",
            "rescue",
        ),
        (0, 1),
        ("forced_break",),
        exploratory=True,
    )


def carrier_confirmation_spec(
    selected: tuple[CarrierV2Spec, ...],
) -> CarrierStudyV2Spec:
    if not 1 <= len(selected) <= 2:
        raise ValueError("carrier confirmation accepts at most one candidate per engine")
    return CarrierStudyV2Spec(
        "plastic-heredity-v2-carrier-confirmation",
        "untouched-engine-neutral-carrier-confirmation",
        CARRIER_CONFIRMATION_SEED,
        240,
        selected,
        32,
        (
            "carrier_transplant",
            "reset",
            "write_disabled",
            "inert",
            "pattern_shuffle",
            "ablation_0",
            "ablation_25",
            "ablation_50",
            "ablation_100",
            "random_ablation_25",
            "random_ablation_50",
            "rescue",
        ),
        (0, 1),
        ("forced_break",),
        exploratory=False,
    )


def substrate_native_carrier_grid() -> tuple[CarrierV2Spec, ...]:
    values: list[CarrierV2Spec] = []
    for half_life in (4, 8, 16):
        for coupling in (0.50, 0.75, 1.0):
            values.append(
                CarrierV2Spec(
                    f"boolean-transition.half-{half_life}.mu-{coupling:g}",
                    "boolean_transition_trace",
                    "carrier_transplant",
                    half_life=half_life,
                    coupling=coupling,
                    engines=("boolean",),
                )
            )
            values.append(
                CarrierV2Spec(
                    f"wagner-edge.half-{half_life}.mu-{coupling:g}",
                    "wagner_edge_trace",
                    "carrier_transplant",
                    half_life=half_life,
                    coupling=coupling,
                    engines=("wagner",),
                )
            )
    return tuple(values)


def substrate_native_calibration_spec() -> CarrierStudyV2Spec:
    return CarrierStudyV2Spec(
        "plastic-heredity-v2-native-carrier-calibration",
        "substrate-native-carrier-calibration",
        NATIVE_CARRIER_CALIBRATION_SEED,
        32,
        substrate_native_carrier_grid(),
        16,
        ("carrier_transplant", "reset"),
        (0,),
        ("forced_break",),
        exploratory=True,
    )


def substrate_native_discovery_spec(
    selected: tuple[CarrierV2Spec, ...],
) -> CarrierStudyV2Spec:
    if not 1 <= len(selected) <= 2:
        raise ValueError("native discovery accepts at most one candidate per engine")
    return CarrierStudyV2Spec(
        "plastic-heredity-v2-native-carrier-discovery",
        "substrate-native-carrier-causal-discovery",
        NATIVE_CARRIER_DISCOVERY_SEED,
        96,
        selected,
        32,
        (
            "carrier_transplant",
            "reset",
            "write_disabled",
            "inert",
            "pattern_shuffle",
            "ablation_0",
            "ablation_25",
            "ablation_50",
            "ablation_100",
            "random_ablation_25",
            "random_ablation_50",
            "rescue",
        ),
        (0, 1),
        ("forced_break",),
        exploratory=True,
    )


def substrate_native_confirmation_spec(
    selected: tuple[CarrierV2Spec, ...],
) -> CarrierStudyV2Spec:
    if not 1 <= len(selected) <= 2:
        raise ValueError("native confirmation accepts at most one candidate per engine")
    return CarrierStudyV2Spec(
        "plastic-heredity-v2-native-carrier-confirmation",
        "untouched-substrate-native-carrier-confirmation",
        NATIVE_CARRIER_CONFIRMATION_SEED,
        240,
        selected,
        32,
        (
            "carrier_transplant",
            "reset",
            "write_disabled",
            "inert",
            "pattern_shuffle",
            "ablation_0",
            "ablation_25",
            "ablation_50",
            "ablation_100",
            "random_ablation_25",
            "random_ablation_50",
            "rescue",
        ),
        (0, 1),
        ("forced_break",),
        exploratory=False,
    )


def mechanism_atlas_specs(source_count: int = 96) -> tuple[PlasticMemorySpec, ...]:
    """Registered four-noise atlas with within-engine shared rulebooks."""

    result: list[PlasticMemorySpec] = []
    for flip in (0.0, 0.01, 0.05, 0.10):
        sources = (
            MemorySourceSpec("boolean_n10", "boolean", 10, source_count, "boolean_sync"),
            MemorySourceSpec("wagner_n10", "wagner", 10, source_count, "wagner_sequential"),
        )
        models = (
            MemoryModelSpec("boolean.sync", "boolean_n10", "boolean_sync"),
            MemoryModelSpec("boolean.sequential", "boolean_n10", "boolean_sequential"),
            *tuple(
                MemoryModelSpec(
                    f"wagner.sequential.theta-{theta:g}",
                    "wagner_n10",
                    "wagner_sequential",
                    theta,
                )
                for theta in (0.0, 0.0025, 0.01, 0.03)
            ),
            *tuple(
                MemoryModelSpec(
                    f"wagner.synchronous.theta-{theta:g}",
                    "wagner_n10",
                    "wagner_synchronous",
                    theta,
                )
                for theta in (0.0, 0.0025, 0.01, 0.03)
            ),
        )
        conditions = tuple(
            MemoryCondition(
                f"atlas.{model.name}",
                model.name,
                CueDose(1.0, 1),
                ("none",),
                ("state_transplant", "reset_both"),
                (0, 1, 4, 8),
                ("release_only", "neutral_damage", "forced_break"),
                16,
            )
            for model in models
        )
        result.append(
            PlasticMemorySpec(
                f"plastic-heredity-v2-atlas-flip-{flip:g}",
                "matched-update-and-noise-atlas",
                ATLAS_SEED,
                sources,
                models,
                (NO_MARK,),
                conditions,
                expression_flip_probability=flip,
                exploratory=True,
            )
        )
    return tuple(result)


def mechanism_atlas_confirmation_specs(
    nominations: tuple[dict[str, object], ...]
) -> tuple[PlasticMemorySpec, ...]:
    """Build fresh paired baseline/candidate confirmations for at most two variants."""

    if not 1 <= len(nominations) <= 2:
        raise ValueError("mechanism atlas confirmation requires one or two nominations")

    def model(name: str, source_set: str) -> MemoryModelSpec:
        if name.startswith("boolean."):
            variant = "boolean_sync" if name == "boolean.sync" else "boolean_sequential"
            return MemoryModelSpec(name, source_set, variant)
        timing, theta_text = name.removeprefix("wagner.").split(".theta-")
        return MemoryModelSpec(
            name,
            source_set,
            "wagner_sequential" if timing == "sequential" else "wagner_synchronous",
            float(theta_text),
        )

    result: list[PlasticMemorySpec] = []
    for index, nomination in enumerate(nominations):
        engine = str(nomination["engine"])
        candidate_name = str(nomination["candidate"])
        baseline_name = str(nomination["baseline"])
        flip = float(nomination["expression_flip_probability"])
        source_set = f"{engine}_n10"
        source = MemorySourceSpec(
            source_set,
            engine,
            10,
            240,
            "boolean_sync" if engine == "boolean" else "wagner_sequential",
        )
        models = (model(baseline_name, source_set), model(candidate_name, source_set))
        conditions = tuple(
            MemoryCondition(
                f"atlas-confirmation.{value.name}",
                value.name,
                CueDose(1.0, 1),
                ("none",),
                ("state_transplant", "reset_both"),
                (0, 1, 4, 8),
                ("release_only", "neutral_damage", "forced_break"),
                32,
            )
            for value in models
        )
        result.append(
            PlasticMemorySpec(
                f"plastic-heredity-v2-atlas-confirmation-{index}",
                "untouched-mechanism-atlas-confirmation",
                ATLAS_CONFIRMATION_SEED,
                (source,),
                models,
                (NO_MARK,),
                conditions,
                expression_flip_probability=flip,
                exploratory=False,
            )
        )
    return tuple(result)


def posthoc_rescore_spec(parent_root: str) -> EvolutionV2Spec:
    return EvolutionV2Spec(
        "plastic-heredity-v2-posthoc-common-rescore",
        COMMON_RESCORE_SEED,
        parent_root,
        64,
        128,
        200,
        32,
        128,
        exploratory=True,
    )


def prospective_evolution_spec(
    parent_root: str,
    confirmation: bool,
) -> EvolutionV2Spec:
    return EvolutionV2Spec(
        (
            "plastic-heredity-v2-evolution-confirmation"
            if confirmation
            else "plastic-heredity-v2-evolution-discovery"
        ),
        EVOLUTION_CONFIRMATION_SEED if confirmation else EVOLUTION_DISCOVERY_SEED,
        parent_root,
        64 if confirmation else 32,
        128 if confirmation else 64,
        200 if confirmation else 100,
        32,
        128,
        exploratory=not confirmation,
    )


def reduced_for_test(
    spec: PlasticHeredityV2Spec,
    *,
    sources: int = 1,
    futures: int = 4,
) -> PlasticHeredityV2Spec:
    """Return a deterministic smoke-sized copy without changing production builders."""

    return replace(
        spec,
        source_count_per_engine=sources,
        conditions=tuple(
            replace(condition, futures_per_cell=futures) for condition in spec.conditions
        ),
        genes=4,
        midpoint_count=1,
        horizon=12,
        stable_run=2,
        strict_run=2,
        minimum_basin_fraction=0.0,
        minimum_form_distance=0.25,
        bootstrap_repetitions=64,
    )
