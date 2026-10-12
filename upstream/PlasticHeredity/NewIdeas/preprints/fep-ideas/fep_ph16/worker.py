from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from fep_lab.integrity import sha256_bytes
from fep_lab.seeds import derive_seed
from fep_ph15.environment import encode_observation
from fep_ph15.models import load_model as load_categorical_model

from .causal_model import (
    CausalEnsemble,
    action_calibration_offsets,
    load_model as load_causal_model,
    model_digest,
)
from .config import ExperimentConfig
from .controllers import (
    CategoricalController,
    CausalMPCController,
    NoopController,
    PhysicalRolloutOracle,
    ReactiveController,
    ScheduledController,
    exact_multiset_yoke,
)
from .data import (
    beta_for,
    calibration_data,
    environment_design,
    initial_for,
    process_seeds,
)
from .environment import GardGoalAlignmentEnvironment
from .state import (
    advance_body_state,
    initial_body_state,
    initial_regime_belief,
    update_regime_belief,
)
from .types import (
    Action,
    CellSpec,
    ConditionSpec,
    CONTROLLERS,
    ControllerName,
    ObservationThresholds,
)


@dataclass(frozen=True)
class FitPaths:
    coarse: Path
    rich: Path
    categorical: Path


def mechanism_model_paths(fit_root: Path, mechanism_key: str) -> tuple[Path, Path]:
    return (
        fit_root / "causal" / f"{mechanism_key}--coarse.npz",
        fit_root / "causal" / f"{mechanism_key}--rich.npz",
    )


def categorical_model_path(fit_root: Path, condition: ConditionSpec) -> Path:
    return fit_root / "categorical" / f"{condition.key}.npz"


def _seed(config: ExperimentConfig, domain: str, *parts: object) -> int:
    return derive_seed(config.master_seed, f"fep_ph16.{domain}", *parts)


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
    categorical_model: object,
    coarse: CausalEnsemble,
    rich: CausalEnsemble,
    coarse_offsets: NDArray[np.float64],
    rich_offsets: NDArray[np.float64],
    branch: int,
    schedule: NDArray[np.integer] | None,
):
    if name == ControllerName.NOOP:
        return NoopController()
    if name == ControllerName.REACTIVE:
        return ReactiveController()
    if name == ControllerName.CATEGORICAL_AI:
        return CategoricalController(
            categorical_model, config, cell.condition, true_regime=False  # type: ignore[arg-type]
        )
    if name == ControllerName.CATEGORICAL_ORACLE:
        return CategoricalController(
            categorical_model, config, cell.condition, true_regime=True  # type: ignore[arg-type]
        )
    if name == ControllerName.PHYSICAL_ORACLE:
        return PhysicalRolloutOracle(
            config,
            cell.condition,
            thresholds,
            (cell.condition.key, cell.matrix_id, branch),
        )
    if name == ControllerName.COARSE_REWARD:
        return CausalMPCController(
            coarse,
            config,
            cell.condition,
            thresholds,
            coarse_offsets,
            epistemic=False,
        )
    if name == ControllerName.RICH_REWARD:
        return CausalMPCController(
            rich,
            config,
            cell.condition,
            thresholds,
            rich_offsets,
            epistemic=False,
        )
    if name == ControllerName.RICH_EFE:
        return CausalMPCController(
            rich,
            config,
            cell.condition,
            thresholds,
            rich_offsets,
            epistemic=True,
        )
    if name == ControllerName.RICH_EFE_SHUFFLED:
        return CausalMPCController(
            rich,
            config,
            cell.condition,
            thresholds,
            rich_offsets,
            epistemic=True,
            shuffled_actions=True,
        )
    if name == ControllerName.RICH_EFE_YOKED:
        if schedule is None:
            raise ValueError("yoked rich controller requires an action schedule")
        return ScheduledController(schedule)
    raise ValueError(f"unsupported FEP-PH1.6 controller {name}")


def _agent_pair(name: ControllerName) -> str:
    if name in (
        ControllerName.RICH_REWARD,
        ControllerName.RICH_EFE,
        ControllerName.RICH_EFE_SHUFFLED,
    ):
        return "rich-causal-paired"
    if name in (ControllerName.CATEGORICAL_AI, ControllerName.CATEGORICAL_ORACLE):
        return "categorical-paired"
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
    environment = GardGoalAlignmentEnvironment(
        config,
        environment_design(config, cell.condition, cell.matrix_id, "evaluation"),
        beta,
        initial,
        *process_seeds(
            config, "evaluation", cell.condition, cell.matrix_id, 0, branch
        ),
        thresholds=thresholds,
    )
    controller.reset()
    rng = np.random.default_rng(
        _seed(
            config,
            "evaluation.agent",
            cell.condition.key,
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
        config.passive_cue_accuracy,
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
            categorical_observation=categorical_observation,
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
        if np.all(np.isfinite(decision.categorical_posterior)):
            arrays["beliefs"][step] = decision.categorical_posterior
        else:
            arrays["beliefs"][step] = _belief9(body.regime_belief)
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
        accuracy = (
            config.sampled_cue_accuracy
            if result.executed_action == int(Action.SAMPLE)
            else config.passive_cue_accuracy
        )
        following_belief = update_regime_belief(
            body.regime_belief,
            result.raw_observation.cue,
            regime_spec.switch_probability,
            regime_spec.shock_probability,
            accuracy,
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


def _offset_digest(coarse: NDArray[np.float64], rich: NDArray[np.float64]) -> str:
    return sha256_bytes(
        np.ascontiguousarray(coarse).tobytes() + np.ascontiguousarray(rich).tobytes()
    )


def generate_evaluation_cell(
    config: ExperimentConfig,
    cell: CellSpec,
    fit_root: Path,
    thresholds: ObservationThresholds,
) -> tuple[dict[str, NDArray[Any]], dict[str, Any]]:
    coarse_path, rich_path = mechanism_model_paths(
        fit_root, cell.condition.mechanism_key
    )
    coarse = load_causal_model(coarse_path)
    rich = load_causal_model(rich_path)
    categorical, _counts = load_categorical_model(
        categorical_model_path(fit_root, cell.condition)
    )
    calibration = calibration_data(config, cell)
    coarse_offsets = action_calibration_offsets(
        coarse,
        calibration["coarse_features"],
        calibration["action"].astype(np.int8),
        calibration["coarse_targets"],
        config.calibration_shrinkage,
    )
    rich_offsets = action_calibration_offsets(
        rich,
        calibration["rich_features"],
        calibration["action"].astype(np.int8),
        calibration["rich_targets"],
        config.calibration_shrinkage,
    )
    beta = beta_for(config, "evaluation", cell.matrix_id)
    episodes: dict[tuple[ControllerName, int], dict[str, NDArray[Any]]] = {}
    for branch in range(config.branches):
        initial = initial_for(
            config,
            "evaluation",
            cell.matrix_id,
            cell.condition,
            0,
            branch,
        )
        for name in CONTROLLERS:
            if name == ControllerName.RICH_EFE_YOKED:
                continue
            controller = _controller(
                name,
                config,
                cell,
                thresholds,
                categorical,
                coarse,
                rich,
                coarse_offsets,
                rich_offsets,
                branch,
                None,
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
        schedule = exact_multiset_yoke(
            episodes[(ControllerName.RICH_EFE, branch)]["intended_actions"],
            _seed(
                config,
                "evaluation.yoked",
                cell.condition.key,
                cell.matrix_id,
                branch,
            ),
        )
        yoked = _controller(
            ControllerName.RICH_EFE_YOKED,
            config,
            cell,
            thresholds,
            categorical,
            coarse,
            rich,
            coarse_offsets,
            rich_offsets,
            branch,
            schedule,
        )
        episodes[(ControllerName.RICH_EFE_YOKED, branch)] = run_episode(
            config,
            cell,
            beta,
            initial,
            thresholds,
            ControllerName.RICH_EFE_YOKED,
            yoked,
            branch,
        )
    arrays: dict[str, NDArray[Any]] = {
        "controller_names": np.asarray([str(name) for name in CONTROLLERS]),
        "matrix_id": np.asarray((cell.matrix_id,), dtype=np.int32),
        "growth_budget": np.asarray((cell.condition.growth_budget,), dtype=np.int32),
        "coarse_offsets": coarse_offsets,
        "rich_offsets": rich_offsets,
    }
    schema = tuple(next(iter(episodes.values())))
    for name in schema:
        arrays[name] = np.stack(
            [
                np.stack(
                    [episodes[(controller, branch)][name] for branch in range(config.branches)]
                )
                for controller in CONTROLLERS
            ]
        )
    metadata = {
        "schema": "fep-ph16-evaluation-cell-v1",
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
        "actionability": cell.condition.actuator.actionability,
        "controllers": [str(name) for name in CONTROLLERS],
        "coarse_model_digest": model_digest(coarse),
        "rich_model_digest": model_digest(rich),
        "calibration_rows": int(len(calibration["action"])),
        "calibration_offset_digest": _offset_digest(coarse_offsets, rich_offsets),
        "learned_agent_access": "blanket_limited",
        "physical_oracle_access": "full_state_planning_stream_only",
    }
    return arrays, metadata
