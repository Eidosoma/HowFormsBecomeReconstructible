"""Frozen staged protocols for the plastic-memory causal campaign."""

from __future__ import annotations

from .plastic_memory_config import (
    CueDose,
    MarkSetting,
    MemoryCondition,
    MemoryModelSpec,
    MemorySourceSpec,
    PlasticMemorySpec,
)


CALIBRATION_SEED = "9016b8de711fb4df3cb65baa98099ef657e229c746f9fa9fd4ba1f478f577b2d"
DISCOVERY_SEED = "f607dce86ae4cc93411269be120e291ba2838583712c8d08a9530f5bb7d9295"
CONFIRMATION_SEED = "b10f49fbf03e8995dcc8a9b142f72309fd87e28341a0e207736320a3fcc8f860"
EVOLUTION_SEED = "51d909a7654d84e920385e237b7493dca29712b7f3e34a5b166a9c4268e78c88"
GARD_MIRROR_SEED = "34e1ff1b3bb27ecdf5b72c83891b5d8515023c701d0624cc52a040d3000c4cd2"


NO_MARK = MarkSetting("none", 0, 0.0)
MARK_GRID = tuple(
    MarkSetting(f"half-{half_life}.mu-{coupling:g}", half_life, coupling)
    for half_life in (1, 4, 8)
    for coupling in (0.25, 0.50)
)


def _sources(count: int, genes: int = 10) -> tuple[MemorySourceSpec, ...]:
    return (
        MemorySourceSpec("boolean_n10", "boolean", genes, count, "boolean_sync"),
        MemorySourceSpec("wagner_n10", "wagner", genes, count, "wagner_sequential"),
    )


def _primary_models() -> tuple[MemoryModelSpec, ...]:
    return (
        MemoryModelSpec("boolean-primary", "boolean_n10", "boolean_sync", 0.0, True),
        MemoryModelSpec(
            "wagner-primary", "wagner_n10", "wagner_sequential", 0.10, True
        ),
    )


def _all_discovery_models() -> tuple[MemoryModelSpec, ...]:
    return (
        *_primary_models(),
        MemoryModelSpec(
            "wagner-low-noise", "wagner_n10", "wagner_sequential", 0.03, False
        ),
        MemoryModelSpec(
            "wagner-deterministic", "wagner_n10", "wagner_sequential", 0.0, False
        ),
        MemoryModelSpec(
            "wagner-synchronous", "wagner_n10", "wagner_synchronous", 0.10, False
        ),
    )


def cue_grid() -> tuple[CueDose, ...]:
    return tuple(
        CueDose(fraction, dwell)
        for fraction in (0.25, 0.50, 0.75, 1.0)
        for dwell in (1, 4, 16)
    )


def calibration_spec() -> PlasticMemorySpec:
    conditions = tuple(
        MemoryCondition(
            f"calibrate-{model.name}-{dose.name}",
            model.name,
            dose,
            (NO_MARK.name,),
            ("state_transplant",),
            (0,),
            ("release_only",),
            16,
        )
        for model in _primary_models()
        for dose in cue_grid()
    )
    return PlasticMemorySpec(
        cohort_id="plastic-memory-v1-calibration",
        phase="cue-calibration",
        master_seed=CALIBRATION_SEED,
        sources=_sources(32),
        models=_primary_models(),
        mark_settings=(NO_MARK,),
        conditions=conditions,
        exploratory=True,
    )


def discovery_spec(cues: dict[str, CueDose]) -> PlasticMemorySpec:
    models = _all_discovery_models()
    conditions: list[MemoryCondition] = []
    for model in models:
        cue = cues[model.name if model.primary else "wagner-primary"]
        if model.primary:
            conditions.extend(
                (
                    MemoryCondition(
                        f"{model.name}-state-core",
                        model.name,
                        cue,
                        (NO_MARK.name,),
                        (
                            "self_continuation",
                            "state_transplant",
                            "reset_both",
                            "destination_matched_donor",
                            "descriptor_matched_null",
                            "state_pattern_shuffle",
                        ),
                        (0, 1, 2, 4, 8),
                        ("release_only", "neutral_damage", "forced_break"),
                        64,
                    ),
                    MemoryCondition(
                        f"{model.name}-mark-screen",
                        model.name,
                        cue,
                        tuple(mark.name for mark in MARK_GRID),
                        ("mark_transplant", "reset_both"),
                        (0, 4, 8),
                        ("forced_break",),
                        64,
                    ),
                    MemoryCondition(
                        f"{model.name}-mark-mechanism",
                        model.name,
                        cue,
                        tuple(mark.name for mark in MARK_GRID),
                        (
                            "state_and_mark_transplant",
                            "reset_both",
                            "mark_pattern_shuffle",
                            "write_disabled",
                            "mark_inert",
                            "mark_ablation",
                            "mark_random_ablation",
                            "mark_rescue",
                        ),
                        (0, 8),
                        ("neutral_damage", "forced_break"),
                        32,
                    ),
                )
            )
        else:
            conditions.append(
                MemoryCondition(
                    f"{model.name}-state-diagnostic",
                    model.name,
                    cue,
                    (NO_MARK.name,),
                    ("state_transplant", "reset_both", "destination_matched_donor"),
                    (0, 4, 8),
                    ("neutral_damage", "forced_break"),
                    32,
                )
            )
    return PlasticMemorySpec(
        cohort_id="plastic-memory-v1-discovery",
        phase="causal-carrier-discovery",
        master_seed=DISCOVERY_SEED,
        sources=_sources(64),
        models=models,
        mark_settings=(NO_MARK, *MARK_GRID),
        conditions=tuple(conditions),
        exploratory=True,
    )


def confirmation_spec(
    cues: dict[str, CueDose],
    selected_marks: dict[str, str | None],
) -> PlasticMemorySpec:
    conditions: list[MemoryCondition] = []
    active_marks: list[MarkSetting] = []
    for model in _primary_models():
        cue = cues[model.name]
        conditions.extend(
            (
                MemoryCondition(
                    f"{model.name}-state-primary",
                    model.name,
                    cue,
                    (NO_MARK.name,),
                    (
                        "self_continuation",
                        "state_transplant",
                        "reset_both",
                        "destination_matched_donor",
                        "descriptor_matched_null",
                        "state_pattern_shuffle",
                    ),
                    (0,),
                    ("neutral_damage",),
                    128,
                ),
                MemoryCondition(
                    f"{model.name}-state-recurrence",
                    model.name,
                    cue,
                    (NO_MARK.name,),
                    ("state_transplant", "reset_both"),
                    (0,),
                    ("forced_break",),
                    128,
                ),
                MemoryCondition(
                    f"{model.name}-state-persistence",
                    model.name,
                    cue,
                    (NO_MARK.name,),
                    ("state_transplant", "reset_both"),
                    (1, 2, 4, 8),
                    ("release_only", "neutral_damage", "forced_break"),
                    64,
                ),
            )
        )
        selected = selected_marks.get(model.name)
        if selected is not None:
            mark = next(value for value in MARK_GRID if value.name == selected)
            if mark not in active_marks:
                active_marks.append(mark)
            conditions.extend(
                (
                    MemoryCondition(
                        f"{model.name}-mark-primary",
                        model.name,
                        cue,
                        (mark.name,),
                        ("mark_transplant", "reset_both"),
                        (0,),
                        ("forced_break",),
                        128,
                    ),
                    MemoryCondition(
                        f"{model.name}-mark-persistence",
                        model.name,
                        cue,
                        (mark.name,),
                        ("mark_transplant", "reset_both"),
                        (1, 2, 4, 8),
                        ("release_only", "neutral_damage", "forced_break"),
                        64,
                    ),
                    MemoryCondition(
                        f"{model.name}-mark-mechanism",
                        model.name,
                        cue,
                        (mark.name,),
                        (
                            "state_and_mark_transplant",
                            "mark_pattern_shuffle",
                            "write_disabled",
                            "mark_inert",
                            "mark_ablation",
                            "mark_random_ablation",
                            "mark_rescue",
                        ),
                        (0, 8),
                        ("neutral_damage", "forced_break"),
                        64,
                    ),
                )
            )
    return PlasticMemorySpec(
        cohort_id="plastic-memory-v1-confirmation",
        phase="untouched-transfer-confirmation",
        master_seed=CONFIRMATION_SEED,
        sources=_sources(200),
        models=_primary_models(),
        mark_settings=(NO_MARK, *active_marks),
        conditions=tuple(conditions),
        exploratory=False,
    )


def quick_spec() -> PlasticMemorySpec:
    sources = (
        MemorySourceSpec("boolean_n4", "boolean", 4, 1, "boolean_sync"),
        MemorySourceSpec("wagner_n4", "wagner", 4, 1, "wagner_sequential"),
    )
    models = (
        MemoryModelSpec("boolean-quick", "boolean_n4", "boolean_sync"),
        MemoryModelSpec(
            "wagner-quick", "wagner_n4", "wagner_sequential", 0.03
        ),
    )
    marks = (NO_MARK, MarkSetting("half-1.mu-0.5", 1, 0.5))
    conditions = tuple(
        MemoryCondition(
            f"{model.name}-quick",
            model.name,
            CueDose(1.0, 2),
            tuple(mark.name for mark in marks),
            (
                "self_continuation",
                "state_transplant",
                "mark_transplant",
                "reset_both",
                "mark_inert",
            ),
            (0, 1),
            ("release_only", "neutral_damage", "forced_break"),
            4,
        )
        for model in models
    )
    return PlasticMemorySpec(
        cohort_id="plastic-memory-quick",
        phase="engineering-fixture",
        master_seed="a162324757567965f7243f205e63d62c8194764edb1c56ca61dd5060dbd081ae",
        sources=sources,
        models=models,
        mark_settings=marks,
        conditions=conditions,
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
