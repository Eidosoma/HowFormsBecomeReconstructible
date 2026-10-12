from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from fep_lab.seeds import derive_seed
from fep_ph15.environment import encode_observation
from fep_ph15.types import ExternalRegime

from .config import ExperimentConfig
from .controllers import (
    HybridPlanner,
    NoopController,
    PhysicalRolloutOracle,
    ReactiveController,
    ScheduledController,
    TrueRegimeOracle,
    exact_multiset_yoke,
)
from .data import (
    beta_for,
    cue_accuracy,
    environment_design,
    initial_for,
    process_seeds,
)
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
    STAGE_A_CONTROLLERS,
    STAGE_B_CONTROLLERS,
)


def hybrid_model_path(fit_root: Path) -> Path:
    return fit_root / "hybrid" / "hybrid-body-regime-model.npz"


def _seed(config: ExperimentConfig, domain: str, *parts: object) -> int:
    return derive_seed(config.master_seed, f"fep_ph17.{domain}", *parts)


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
        "intended_actions": np.full(h, int(Action.WAIT), dtype=np.int8),
        "executed_actions": np.full(h, int(Action.WAIT), dtype=np.int8),
        "abstract_action_cost": np.zeros(h),
        "physical_action_cost": np.zeros(h),
        "parents": np.zeros((h, n), dtype=np.int16),
        "compositions": np.zeros((h, n), dtype=np.int16),
        "beliefs": np.full((h, 9), np.nan),
        "body_regime_belief": np.full((h, 3), np.nan),
        "posterior_entropy": np.full(h, np.nan),
        "correct_regime_action": np.full(h, np.nan),
        "sampled": np.zeros(h, dtype=np.int8),
        "model_weights": np.full((h, m), np.nan),
        "action_scores": np.full((h, 4), np.nan),
        "action_probabilities": np.full((h, 4), np.nan),
        "state_information_gain": np.full((h, 4), np.nan),
        "planning_fissions": np.zeros(h, dtype=np.int32),
        "vfe": np.full(h, np.nan),
    }


def _controller(
    name: ControllerName,
    config: ExperimentConfig,
    cell: CellSpec,
    thresholds: ObservationThresholds,
    model: HybridModel | None,
    branch: int,
    schedule: NDArray[np.integer] | None = None,
):
    if name == ControllerName.NOOP:
        return NoopController()
    if name == ControllerName.REACTIVE:
        return ReactiveController()
    if name == ControllerName.TRUE_REGIME_ORACLE:
        return TrueRegimeOracle()
    if name == ControllerName.LEGACY_PROXY_D3:
        return PhysicalRolloutOracle(
            config,
            cell.condition,
            thresholds,
            (cell.condition.key, cell.matrix_id, branch, "paired-physical-oracle"),
            depth=config.legacy_oracle_depth,
            beam=config.legacy_oracle_beam,
            replicas=config.legacy_oracle_replicas,
            goal_aligned=False,
        )
    if name == ControllerName.GOAL_D3:
        return PhysicalRolloutOracle(
            config,
            cell.condition,
            thresholds,
            (cell.condition.key, cell.matrix_id, branch, "paired-physical-oracle"),
            depth=config.goal_short_depth,
            beam=config.goal_short_beam,
            replicas=config.goal_short_replicas,
            goal_aligned=True,
        )
    if name == ControllerName.GOAL_D8:
        return PhysicalRolloutOracle(
            config,
            cell.condition,
            thresholds,
            (cell.condition.key, cell.matrix_id, branch, "paired-physical-oracle"),
            depth=config.goal_long_depth,
            beam=config.goal_long_beam,
            replicas=config.goal_long_replicas,
            goal_aligned=True,
        )
    if model is None:
        raise ValueError(f"Stage B controller {name} requires a hybrid model")
    coefficient = config.selected_epistemic_coefficient
    if coefficient is None:
        raise ValueError("Stage B requires a frozen epistemic coefficient")
    if name == ControllerName.PRAGMATIC:
        return HybridPlanner(model, config, cell.condition, epistemic_coefficient=0.0)
    if name == ControllerName.ACTIVE_INFERENCE:
        return HybridPlanner(
            model, config, cell.condition, epistemic_coefficient=coefficient
        )
    if name == ControllerName.SAMPLE_LESION:
        return HybridPlanner(
            model,
            config,
            cell.condition,
            epistemic_coefficient=coefficient,
            sample_lesion=True,
        )
    if name == ControllerName.EFE_SHUFFLED:
        return HybridPlanner(
            model,
            config,
            cell.condition,
            epistemic_coefficient=coefficient,
            shuffled_actions=True,
        )
    if name == ControllerName.EFE_YOKED:
        if schedule is None:
            raise ValueError("EFE yoke requires an exact action schedule")
        return ScheduledController(schedule)
    raise ValueError(f"unsupported FEP-PH1.7 controller {name}")


def _agent_pair(name: ControllerName) -> str:
    if name in (
        ControllerName.PRAGMATIC,
        ControllerName.ACTIVE_INFERENCE,
        ControllerName.SAMPLE_LESION,
        ControllerName.EFE_SHUFFLED,
    ):
        return "hybrid-paired"
    return str(name)


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
                cell.condition.paired_information_key
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
        result = environment.step(decision.action)
        arrays["completed"][step] = int(result.completed)
        arrays["growth_steps"][step] = result.raw_observation.growth_steps
        arrays["similarity"][step] = result.raw_observation.boundary_similarity
        arrays["alignment_score"][step] = result.raw_observation.alignment_score
        arrays["decision_regime"][step] = decision_regime
        arrays["result_regime"][step] = result.external_regime
        arrays["observations"][step] = categorical_observation
        arrays["intended_actions"][step] = decision.action
        arrays["executed_actions"][step] = result.executed_action
        arrays["abstract_action_cost"][step] = result.abstract_action_cost
        arrays["physical_action_cost"][step] = result.physical_action_cost
        if result.parent is not None:
            arrays["parents"][step] = result.parent
        arrays["compositions"][step] = result.composition
        arrays["body_regime_belief"][step] = body.regime_belief
        arrays["beliefs"][step] = _belief9(body.regime_belief)
        arrays["posterior_entropy"][step] = entropy(body.regime_belief)
        if decision_regime in (int(ExternalRegime.A), int(ExternalRegime.B)):
            expected = (
                int(Action.ADAPT_A)
                if decision_regime == int(ExternalRegime.A)
                else int(Action.ADAPT_B)
            )
            arrays["correct_regime_action"][step] = float(
                int(result.executed_action) == expected
            )
        arrays["sampled"][step] = int(result.executed_action == int(Action.SAMPLE))
        if decision.model_weights.size:
            arrays["model_weights"][step, : len(decision.model_weights)] = decision.model_weights
        arrays["action_scores"][step] = decision.action_scores
        arrays["action_probabilities"][step] = decision.action_probabilities
        arrays["state_information_gain"][step] = decision.information_values
        arrays["planning_fissions"][step] = decision.planning_fissions
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
            body.regime_belief,
            result.raw_observation.cue,
            regime_spec.switch_probability,
            regime_spec.shock_probability,
            cue_accuracy(config, cell.condition, result.executed_action),
        )
        body = advance_body_state(
            body,
            result.composition,
            result.raw_observation,
            following_belief,
            result.executed_action,
            cell.condition.growth_budget,
        )
        categorical_observation = encode_observation(
            result.raw_observation, thresholds
        )
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
        initial = initial_for(
            config, cohort, cell.matrix_id, cell.condition, 0, branch
        )
        for name in controllers:
            if name == ControllerName.EFE_YOKED:
                continue
            controller = _controller(
                name, config, cell, thresholds, model, branch
            )
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
        if not stage_a:
            schedule = exact_multiset_yoke(
                episodes[(ControllerName.ACTIVE_INFERENCE, branch)]["intended_actions"],
                _seed(
                    config,
                    "stage-b.yoked",
                    cell.condition.paired_information_key,
                    cell.matrix_id,
                    branch,
                ),
            )
            controller = _controller(
                ControllerName.EFE_YOKED,
                config,
                cell,
                thresholds,
                model,
                branch,
                schedule,
            )
            episodes[(ControllerName.EFE_YOKED, branch)] = run_episode(
                config,
                cell,
                beta,
                initial,
                thresholds,
                ControllerName.EFE_YOKED,
                controller,
                branch,
            )
    arrays: dict[str, NDArray[Any]] = {
        "controller_names": np.asarray([str(name) for name in controllers]),
        "matrix_id": np.asarray((cell.matrix_id,), dtype=np.int32),
        "growth_budget": np.asarray((cell.condition.growth_budget,), dtype=np.int32),
        "authority_scale": np.asarray((cell.condition.authority_scale,)),
    }
    schema = tuple(next(iter(episodes.values())))
    for field in schema:
        arrays[field] = np.stack(
            [
                np.stack(
                    [episodes[(controller, branch)][field] for branch in range(config.branches)]
                )
                for controller in controllers
            ]
        )
    metadata = {
        "schema": "fep-ph17-evaluation-cell-v1",
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
        "growth_budget": cell.condition.growth_budget,
        "authority_scale": cell.condition.authority_scale,
        "information_arm": str(cell.condition.information_arm),
        "actionability": cell.condition.actuator.actionability,
        "controllers": [str(name) for name in controllers],
        "hybrid_model_digest": None if model is None else model_digest(model),
        "learned_agent_access": "blanket_limited",
        "physical_oracle_access": (
            "full_state_isolated_planning_stream_only" if stage_a else "not_present"
        ),
        "strict_events_used_for_control": False,
    }
    return arrays, metadata
