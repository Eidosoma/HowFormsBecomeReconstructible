"""Frozen staged protocols for the exploratory Wagner rescue funnel."""

from __future__ import annotations

from typing import Any

from .rng import digest_parts
from .wagner_rescue_config import (
    CueIntervention,
    RescueModelSpec,
    WagnerRescueCondition,
    WagnerRescueSpec,
)


def _seed(stage: str) -> str:
    return digest_parts("wagner-induction-rescue-v1", stage, size=32)


def _model_name(variant: str, variance: float) -> str:
    update = variant.removeprefix("wagner_")
    return f"wagner-{update}-theta-{variance:g}"


def _condition_name(prefix: str, model: str, intervention: CueIntervention) -> str:
    return f"{prefix}.{model}.{intervention.name}"


def screen_spec() -> WagnerRescueSpec:
    models = tuple(
        RescueModelSpec(_model_name(variant, variance), variant, variance)
        for variant in ("wagner_sequential", "wagner_synchronous")
        for variance in (0.0, 0.01, 0.03, 0.10)
    )
    active = (
        *(
            CueIntervention("initialization", fraction, dwell)
            for fraction in (0.50, 0.75, 1.0)
            for dwell in (1, 4, 16)
        ),
        *(
            CueIntervention("persistent_hard", fraction, dwell)
            for fraction in (0.50, 0.75, 1.0)
            for dwell in (1, 4, 16)
        ),
        *(
            CueIntervention("target_field", fraction, dwell, strength)
            for fraction in (0.50, 0.75, 1.0)
            for dwell in (1, 4, 16)
            for strength in (0.50, 1.0, 2.0)
        ),
    )
    conditions: list[WagnerRescueCondition] = []
    for model in models:
        for intervention in active:
            conditions.append(
                WagnerRescueCondition(
                    _condition_name("screen", model.name, intervention),
                    model.name,
                    intervention,
                    "candidate",
                    8,
                )
            )
        for intervention, role in (
            (CueIntervention("no_cue", 0.0, 1), "no_cue"),
            (CueIntervention("target_injection", 1.0, 1), "target_injection"),
        ):
            conditions.append(
                WagnerRescueCondition(
                    _condition_name("screen-control", model.name, intervention),
                    model.name,
                    intervention,
                    role,
                    8,
                )
            )
    spec = WagnerRescueSpec(
        cohort_id="wagner-induction-rescue-v1-screen",
        phase="mechanism-screen",
        master_seed=_seed("mechanism-screen"),
        genes=10,
        source_count=24,
        eligibility_variants=("wagner_sequential", "wagner_synchronous"),
        models=models,
        conditions=tuple(conditions),
        horizon=12,
        bootstrap_repetitions=2048,
        simultaneous_tests=1,
    )
    spec.validate()
    return spec


def _model_from_cell(cell: dict[str, Any]) -> RescueModelSpec:
    model = cell["model"]
    return RescueModelSpec(
        str(model["name"]),
        str(model["variant"]),
        float(model["gamma_variance"]),
    )


def _intervention_from_cell(cell: dict[str, Any]) -> CueIntervention:
    value = cell["intervention"]
    return CueIntervention(
        str(value["mode"]),
        float(value["fraction"]),
        int(value["dwell"]),
        float(value["field_strength"]),
    )


def _unique_models(values: list[RescueModelSpec]) -> tuple[RescueModelSpec, ...]:
    mapping = {model.name: model for model in values}
    return tuple(mapping[name] for name in sorted(mapping))


def replication_spec(finalists: list[dict[str, Any]]) -> WagnerRescueSpec:
    if not finalists:
        raise ValueError("narrow rescue replication requires finalists")
    baseline = RescueModelSpec(
        _model_name("wagner_sequential", 0.10),
        "wagner_sequential",
        0.10,
    )
    models = _unique_models([*(_model_from_cell(cell) for cell in finalists), baseline])
    conditions: list[WagnerRescueCondition] = []
    for index, cell in enumerate(finalists):
        model = _model_from_cell(cell)
        intervention = _intervention_from_cell(cell)
        conditions.append(
            WagnerRescueCondition(
                _condition_name(f"finalist-{index + 1}", model.name, intervention),
                model.name,
                intervention,
                "candidate",
                32,
            )
        )
    baseline_intervention = CueIntervention("initialization", 1.0, 1)
    conditions.append(
        WagnerRescueCondition(
            _condition_name("original-baseline", baseline.name, baseline_intervention),
            baseline.name,
            baseline_intervention,
            "baseline",
            32,
        )
    )
    for model in models:
        for intervention, role in (
            (CueIntervention("no_cue", 0.0, 1), "no_cue"),
            (CueIntervention("target_injection", 1.0, 1), "target_injection"),
        ):
            conditions.append(
                WagnerRescueCondition(
                    _condition_name("replication-control", model.name, intervention),
                    model.name,
                    intervention,
                    role,
                    32,
                )
            )
    spec = WagnerRescueSpec(
        cohort_id="wagner-induction-rescue-v1-replication",
        phase="narrow-replication",
        master_seed=_seed("narrow-replication"),
        genes=10,
        source_count=48,
        eligibility_variants=("wagner_sequential", "wagner_synchronous"),
        models=models,
        conditions=tuple(conditions),
        horizon=32,
        bootstrap_repetitions=4096,
        simultaneous_tests=max(1, len(finalists) * 4),
    )
    spec.validate()
    return spec


def validation_spec(candidate: dict[str, Any]) -> WagnerRescueSpec:
    selected_model = _model_from_cell(candidate)
    baseline = RescueModelSpec(
        _model_name("wagner_sequential", 0.10),
        "wagner_sequential",
        0.10,
    )
    models = _unique_models([selected_model, baseline])
    intervention = _intervention_from_cell(candidate)
    baseline_intervention = CueIntervention("initialization", 1.0, 1)
    conditions = [
        WagnerRescueCondition(
            _condition_name("validation-candidate", selected_model.name, intervention),
            selected_model.name,
            intervention,
            "candidate",
            64,
        ),
        WagnerRescueCondition(
            _condition_name("validation-baseline", baseline.name, baseline_intervention),
            baseline.name,
            baseline_intervention,
            "baseline",
            64,
        ),
        WagnerRescueCondition(
            _condition_name(
                "validation-control",
                selected_model.name,
                CueIntervention("no_cue", 0.0, 1),
            ),
            selected_model.name,
            CueIntervention("no_cue", 0.0, 1),
            "no_cue",
            64,
        ),
        WagnerRescueCondition(
            _condition_name(
                "validation-control",
                selected_model.name,
                CueIntervention("target_injection", 1.0, 1),
            ),
            selected_model.name,
            CueIntervention("target_injection", 1.0, 1),
            "target_injection",
            64,
        ),
    ]
    spec = WagnerRescueSpec(
        cohort_id="wagner-induction-rescue-v1-validation",
        phase="candidate-validation",
        master_seed=_seed("candidate-validation"),
        genes=10,
        source_count=64,
        eligibility_variants=tuple(sorted({model.variant for model in models})),
        models=models,
        conditions=tuple(conditions),
        horizon=32,
        bootstrap_repetitions=4096,
        simultaneous_tests=4,
    )
    spec.validate()
    return spec


def quick_rescue_spec() -> WagnerRescueSpec:
    model = RescueModelSpec("wagner-quick", "wagner_sequential", 0.0)
    interventions = (
        (CueIntervention("initialization", 1.0, 1), "candidate"),
        (CueIntervention("no_cue", 0.0, 1), "no_cue"),
        (CueIntervention("target_injection", 1.0, 1), "target_injection"),
    )
    return WagnerRescueSpec(
        cohort_id="wagner-rescue-quick",
        phase="quick",
        master_seed=_seed("quick"),
        genes=4,
        source_count=1,
        eligibility_variants=("wagner_sequential",),
        models=(model,),
        conditions=tuple(
            WagnerRescueCondition(
                _condition_name("quick", model.name, intervention),
                model.name,
                intervention,
                role,
                4,
            )
            for intervention, role in interventions
        ),
        horizon=12,
        strict_run=3,
        stable_run=2,
        bootstrap_repetitions=16,
        simultaneous_tests=4,
    )
