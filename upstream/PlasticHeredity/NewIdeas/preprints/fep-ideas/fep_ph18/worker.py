from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from fep_lab.seeds import derive_seed
from fep_ph15.environment import encode_observation
from fep_ph15.types import ExternalRegime

from .config import MODEL_ACTIONS, ExperimentConfig
from .controllers import (
    AlwaysSenseReflex,
    ContingentPlanner,
    NoopController,
    PosteriorReflex,
    ReactiveController,
    TrueRegimeOracle,
)
from .data import beta_for, cue_accuracy, environment_design, initial_for, process_seeds
from .environment import GardGoalAlignmentEnvironment
from .hybrid_model import HybridModel, entropy, load_model, model_digest
from .state import (
    advance_body_state,
    initial_body_state,
    initial_regime_belief,
    update_regime_belief,
)
from .types import (
    Action,
    CellSpec,
    ControllerName,
    ExperimentStage,
    ObservationThresholds,
    SensingTiming,
    STAGE_A_CONTROLLERS,
    STAGE_B_CONTROLLERS,
)


def hybrid_model_path(fit_root: Path) -> Path:
    return fit_root / "hybrid" / "hybrid-body-regime-model.npz"


def _seed(config: ExperimentConfig, domain: str, *parts: object) -> int:
    return derive_seed(config.master_seed, f"fep_ph18.{domain}", *parts)


def _belief9(regime_belief: NDArray[np.floating]) -> NDArray[np.float64]:
    values = np.asarray(regime_belief, dtype=np.float64)
    return np.repeat(values / 3.0, 3)


def _template(config: ExperimentConfig) -> dict[str, NDArray[Any]]:
    h, n, m = config.horizon, config.gard.n_types, config.ensemble_members
    return {
        "completed": np.zeros(h, dtype=np.int8),
        "growth_steps": np.full(h, -1, dtype=np.int32),
        "similarity": np.full(h, np.nan),
        "alignment_score": np.full(h, np.nan),
        "decision_regime": np.full(h, -1, dtype=np.int8),
        "result_regime": np.full(h, -1, dtype=np.int8),
        "observations": np.full((h, 4), -1, dtype=np.int8),
        "pre_action_cues": np.full(h, -1, dtype=np.int8),
        "sensed_cues": np.full(h, -1, dtype=np.int8),
        "sense_decisions": np.zeros(h, dtype=np.int8),
        "model_actions": np.full(h, -1, dtype=np.int8),
        "physical_actions": np.full(h, int(Action.WAIT), dtype=np.int8),
        "intended_actions": np.full(h, int(Action.WAIT), dtype=np.int8),
        "executed_actions": np.full(h, int(Action.WAIT), dtype=np.int8),
        "abstract_action_cost": np.zeros(h),
        "physical_action_cost": np.zeros(h),
        "parents": np.zeros((h, n), dtype=np.int16),
        "compositions": np.zeros((h, n), dtype=np.int16),
        "beliefs": np.full((h, 9), np.nan),
        "body_regime_belief": np.full((h, 3), np.nan),
        "pre_action_belief": np.full((h, 3), np.nan),
        "posterior_entropy": np.full(h, np.nan),
        "correct_regime_action": np.full(h, np.nan),
        "adaptation_opportunity": np.zeros(h, dtype=np.int8),
        "adapted": np.zeros(h, dtype=np.int8),
        "sampled": np.zeros(h, dtype=np.int8),
        "model_weights": np.full((h, m), np.nan),
        "plan_scores": np.full((h, 4), np.nan),
        "action_scores": np.full((h, MODEL_ACTIONS), np.nan),
        "action_probabilities": np.full((h, MODEL_ACTIONS), np.nan),
        "state_information_gain": np.full((h, MODEL_ACTIONS), np.nan),
        "cue_action_tree": np.full((h, 4), -1, dtype=np.int8),
        "policy_contingency": np.zeros(h),
        "instrumental_value": np.full(h, np.nan),
        "epistemic_value": np.full(h, np.nan),
        "planning_nodes": np.zeros(h, dtype=np.int32),
        "planning_fissions": np.zeros(h, dtype=np.int32),
        "vfe": np.full(h, np.nan),
    }


def _controller(
    name: ControllerName,
    config: ExperimentConfig,
    cell: CellSpec,
    model: HybridModel | None,
):
    if name == ControllerName.NOOP:
        return NoopController()
    if name == ControllerName.REACTIVE:
        return ReactiveController()
    if name == ControllerName.TRUE_REGIME_ORACLE:
        return TrueRegimeOracle()
    if name == ControllerName.POSTERIOR_REFLEX:
        return PosteriorReflex()
    if name == ControllerName.ALWAYS_SENSE:
        return AlwaysSenseReflex(cell.condition.sensing_timing)
    if model is None:
        raise ValueError(f"Stage B controller {name} requires a hybrid model")
    if name == ControllerName.CONTINGENT_UTILITY:
        return ContingentPlanner(
            model, config, cell.condition, epistemic_coefficient=0.0
        )
    if name == ControllerName.CONTINGENT_EFE:
        return ContingentPlanner(
            model,
            config,
            cell.condition,
            epistemic_coefficient=config.selected_epistemic_coefficient,
        )
    if name == ControllerName.OPEN_LOOP_EFE:
        return ContingentPlanner(
            model,
            config,
            cell.condition,
            epistemic_coefficient=config.selected_epistemic_coefficient,
            contingent=False,
        )
    if name == ControllerName.SAMPLE_LESION:
        return ContingentPlanner(
            model,
            config,
            cell.condition,
            epistemic_coefficient=config.selected_epistemic_coefficient,
            sample_lesion=True,
        )
    if name == ControllerName.SHUFFLED:
        return ContingentPlanner(
            model,
            config,
            cell.condition,
            epistemic_coefficient=config.selected_epistemic_coefficient,
            shuffled_actions=True,
        )
    raise ValueError(f"unsupported FEP-PH1.8 controller {name}")


def _agent_pair(name: ControllerName) -> str:
    if name in (
        ControllerName.CONTINGENT_UTILITY,
        ControllerName.CONTINGENT_EFE,
        ControllerName.OPEN_LOOP_EFE,
        ControllerName.SAMPLE_LESION,
        ControllerName.SHUFFLED,
    ):
        return "model-planner-paired"
    return str(name)


def _sensor_accuracy(config: ExperimentConfig, cell: CellSpec) -> float:
    return cue_accuracy(config, cell.condition, int(Action.SAMPLE))


def run_episode(
    config: ExperimentConfig,
    cell: CellSpec,
    beta: NDArray[np.float64],
    initial: NDArray[np.int64],
    thresholds: ObservationThresholds,
    name: ControllerName,
    controller: Any,
    branch: int,
) -> dict[str, NDArray[Any]]:
    cohort = "stage-a" if cell.condition.stage == ExperimentStage.HEADROOM else "stage-b"
    environment = GardGoalAlignmentEnvironment(
        config,
        environment_design(config, cell.condition, cell.matrix_id, cohort),
        beta,
        initial,
        *process_seeds(config, cohort, cell.condition, cell.matrix_id, 0, branch),
        thresholds=thresholds,
    )
    controller.reset()
    rng = np.random.default_rng(
        _seed(
            config,
            f"{cohort}.agent",
            (
                cell.condition.paired_exogenous_key
                if cohort == "stage-b"
                else cell.condition.key
            ),
            cell.matrix_id,
            branch,
            _agent_pair(name),
        )
    )
    first = environment.initial_step()
    regime_spec = environment.design.regime
    belief = update_regime_belief(
        initial_regime_belief(),
        first.raw_observation.cue,
        regime_spec.switch_probability,
        regime_spec.shock_probability,
        cue_accuracy(config, cell.condition, int(Action.WAIT)),
        transition=False,
    )
    body = initial_body_state(first.composition, first.raw_observation, belief)
    categorical_observation = encode_observation(first.raw_observation, thresholds)
    arrays = _template(config)
    for step in range(config.horizon):
        decision_regime = int(environment.regime)
        decision = controller.decide(
            environment=environment,
            body_state=body,
            rng=rng,
            step=step,
        )
        sensed_cue = -1
        decision_belief = body.regime_belief.copy()
        if decision.sense and cell.condition.sensing_timing == SensingTiming.SAME_CYCLE:
            sensed_cue = int(environment.sense_current())
            decision_belief = update_regime_belief(
                body.regime_belief,
                sensed_cue,
                regime_spec.switch_probability,
                regime_spec.shock_probability,
                _sensor_accuracy(config, cell),
                transition=False,
            )
            physical_action = int(decision.cue_actions[sensed_cue])
            model_action = 4 + physical_action
            result = environment.step_compound(physical_action, sensed=True)
            result_accuracy = config.passive_cue_accuracy
        elif decision.sense:
            physical_action = int(Action.SAMPLE)
            model_action = int(Action.SAMPLE)
            result = environment.step(physical_action)
            sensed_cue = int(result.raw_observation.cue)
            result_accuracy = _sensor_accuracy(config, cell)
        else:
            physical_action = int(decision.physical_action)
            model_action = int(decision.model_action)
            result = environment.step(physical_action)
            result_accuracy = cue_accuracy(config, cell.condition, physical_action)

        arrays["completed"][step] = int(result.completed)
        arrays["growth_steps"][step] = result.raw_observation.growth_steps
        arrays["similarity"][step] = result.raw_observation.boundary_similarity
        arrays["alignment_score"][step] = result.raw_observation.alignment_score
        arrays["decision_regime"][step] = decision_regime
        arrays["result_regime"][step] = result.external_regime
        arrays["observations"][step] = categorical_observation
        arrays["pre_action_cues"][step] = int(np.argmax(body.cue_probs))
        arrays["sensed_cues"][step] = sensed_cue
        arrays["sense_decisions"][step] = int(decision.sense)
        arrays["model_actions"][step] = model_action
        arrays["physical_actions"][step] = physical_action
        arrays["intended_actions"][step] = physical_action
        arrays["executed_actions"][step] = result.executed_action
        arrays["abstract_action_cost"][step] = result.abstract_action_cost
        arrays["physical_action_cost"][step] = result.physical_action_cost
        if result.parent is not None:
            arrays["parents"][step] = result.parent
        arrays["compositions"][step] = result.composition
        arrays["body_regime_belief"][step] = body.regime_belief
        arrays["pre_action_belief"][step] = decision_belief
        arrays["beliefs"][step] = _belief9(decision_belief)
        arrays["posterior_entropy"][step] = entropy(decision_belief)
        if decision_regime in (int(ExternalRegime.A), int(ExternalRegime.B)):
            arrays["adaptation_opportunity"][step] = 1
            if result.executed_action in (int(Action.ADAPT_A), int(Action.ADAPT_B)):
                arrays["adapted"][step] = 1
                expected = (
                    int(Action.ADAPT_A)
                    if decision_regime == int(ExternalRegime.A)
                    else int(Action.ADAPT_B)
                )
                arrays["correct_regime_action"][step] = float(
                    int(result.executed_action) == expected
                )
        arrays["sampled"][step] = int(decision.sense)
        if decision.model_weights.size:
            arrays["model_weights"][step, : len(decision.model_weights)] = decision.model_weights
        arrays["plan_scores"][step] = decision.plan_scores
        arrays["action_scores"][step] = decision.action_scores
        arrays["action_probabilities"][step] = decision.action_probabilities
        arrays["state_information_gain"][step] = decision.information_values
        arrays["cue_action_tree"][step] = decision.cue_actions
        arrays["policy_contingency"][step] = decision.policy_contingency
        arrays["instrumental_value"][step] = decision.instrumental_value
        arrays["epistemic_value"][step] = decision.epistemic_value
        arrays["planning_nodes"][step] = decision.planning_nodes
        controller.observe(
            composition=result.composition,
            raw_observation=result.raw_observation,
            completed=result.completed,
            growth_budget=cell.condition.growth_budget,
            executed_action=result.executed_action,
        )
        if not result.completed:
            break
        following_belief = update_regime_belief(
            decision_belief,
            result.raw_observation.cue,
            regime_spec.switch_probability,
            regime_spec.shock_probability,
            result_accuracy,
        )
        body = advance_body_state(
            body,
            result.composition,
            result.raw_observation,
            following_belief,
            result.executed_action,
            cell.condition.growth_budget,
        )
        categorical_observation = encode_observation(result.raw_observation, thresholds)
    return arrays


def generate_evaluation_cell(
    config: ExperimentConfig,
    cell: CellSpec,
    fit_root: Path,
    thresholds: ObservationThresholds,
) -> tuple[dict[str, NDArray[Any]], dict[str, Any]]:
    stage_a = cell.condition.stage == ExperimentStage.HEADROOM
    controllers = STAGE_A_CONTROLLERS if stage_a else STAGE_B_CONTROLLERS
    model = None if stage_a else load_model(hybrid_model_path(fit_root))
    cohort = "stage-a" if stage_a else "stage-b"
    beta = beta_for(config, cohort, cell.matrix_id)
    episodes: dict[tuple[ControllerName, int], dict[str, NDArray[Any]]] = {}
    for branch in range(config.branches):
        initial = initial_for(config, cohort, cell.matrix_id, cell.condition, 0, branch)
        for name in controllers:
            controller = _controller(name, config, cell, model)
            episodes[(name, branch)] = run_episode(
                config,
                cell,
                beta,
                initial,
                thresholds,
                name,
                controller,
                branch,
            )
    arrays: dict[str, NDArray[Any]] = {
        "controller_names": np.asarray([str(name) for name in controllers]),
        "matrix_id": np.asarray((cell.matrix_id,), dtype=np.int32),
        "growth_budget": np.asarray((cell.condition.growth_budget,), dtype=np.int32),
        "authority_scale": np.asarray((cell.condition.authority_scale,)),
        "switch_probability": np.asarray((cell.condition.switch_probability,)),
    }
    schema = tuple(next(iter(episodes.values())))
    for field in schema:
        arrays[field] = np.stack(
            [
                np.stack(
                    [
                        episodes[(controller, branch)][field]
                        for branch in range(config.branches)
                    ]
                )
                for controller in controllers
            ]
        )
    metadata = {
        "schema": "fep-ph18-evaluation-cell-v1",
        "stage": str(cell.condition.stage),
        "stem": cell.stem,
        "matrix_id": cell.matrix_id,
        "condition": cell.condition.key,
        "mechanism": cell.condition.mechanism_key,
        "candidate": cell.condition.candidate,
        "family": str(cell.condition.family),
        "channel": str(cell.condition.channel),
        "tier": str(cell.condition.tier),
        "volatility": cell.condition.volatility,
        "switch_probability": cell.condition.switch_probability,
        "growth_budget": cell.condition.growth_budget,
        "authority_scale": cell.condition.authority_scale,
        "sensing_timing": str(cell.condition.sensing_timing),
        "information_arm": str(cell.condition.information_arm),
        "actionability": cell.condition.actuator.actionability,
        "controllers": [str(name) for name in controllers],
        "hybrid_model_digest": None if model is None else model_digest(model),
        "learned_agent_access": "blanket_limited",
        "true_regime_access": (
            [str(ControllerName.TRUE_REGIME_ORACLE)]
            if str(ControllerName.TRUE_REGIME_ORACLE) in [str(value) for value in controllers]
            else []
        ),
        "strict_events_used_for_control": False,
    }
    return arrays, metadata
