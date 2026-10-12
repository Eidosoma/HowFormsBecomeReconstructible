from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from fep_lab.types import CategoricalModel

from .config import ExperimentConfig
from .controllers import ActiveInferenceController, NoopController, ReactiveController, ScheduledController
from .environment import EnvironmentDesign, GardGoalAlignmentEnvironment, encode_observation
from .models import ModelCounts, action_costs, hidden_state
from .types import Action, ControllerName, ObservationThresholds, PreferenceMode, RawObservation


class Controller(Protocol):
    def reset(self) -> None: ...
    def decide(self, observation: tuple[int, ...], true_regime: int | None, rng: np.random.Generator): ...
    def advance(self, posterior: NDArray[np.float64], executed_action: int) -> None: ...


@dataclass(frozen=True)
class BehaviorTrace:
    regimes: NDArray[np.int8]
    raw_growth: NDArray[np.int32]
    raw_similarity: NDArray[np.float64]
    raw_alignment: NDArray[np.float64]
    cues: NDArray[np.int8]
    terminal: NDArray[np.int8]
    actions: NDArray[np.int8]


def fitted_thresholds(traces: list[BehaviorTrace]) -> ObservationThresholds:
    if not traces:
        raise ValueError("at least one trace is required")
    alignment = np.concatenate([trace.raw_alignment for trace in traces])
    growth_parts = [trace.raw_growth[trace.terminal == 0] for trace in traces if np.any(trace.terminal == 0)]
    growth = np.concatenate(growth_parts) if growth_parts else np.asarray((60.0, 120.0))
    a_cut = np.quantile(alignment, (1.0 / 3.0, 2.0 / 3.0))
    g_cut = np.quantile(growth, (1.0 / 3.0, 2.0 / 3.0))
    if a_cut[1] - a_cut[0] < 1e-9:
        center = float(a_cut.mean())
        a_cut = np.asarray((center - 1e-6, center + 1e-6))
    g_cut[0] = max(1.0, float(g_cut[0]))
    g_cut[1] = max(float(g_cut[1]), float(g_cut[0]) + 1.0)
    value = ObservationThresholds((float(a_cut[0]), float(a_cut[1])), (float(g_cut[0]), float(g_cut[1])))
    value.validate()
    return value


def _raw_at(trace: BehaviorTrace, index: int) -> RawObservation:
    return RawObservation(int(trace.raw_growth[index]), float(trace.raw_similarity[index]), float(trace.raw_alignment[index]), int(trace.cues[index]), bool(trace.terminal[index]))


def counts_from_behavior(traces: list[BehaviorTrace], thresholds: ObservationThresholds) -> ModelCounts:
    counts = ModelCounts.empty()
    for trace in traces:
        observations = [encode_observation(_raw_at(trace, index), thresholds) for index in range(len(trace.regimes))]
        states = [hidden_state(int(regime), int(observation[2])) for regime, observation in zip(trace.regimes, observations, strict=True)]
        counts.add_initial(states[0], observations[0])
        for index, action in enumerate(trace.actions):
            if index + 1 >= len(states):
                break
            counts.add_transition(states[index], int(action), states[index + 1], observations[index + 1])
    return counts


def run_behavior_trace(
    config: ExperimentConfig,
    design: EnvironmentDesign,
    beta: NDArray[np.float64],
    initial: NDArray[np.int64],
    seeds: tuple[int, int, int],
    steps: int,
    action_offset: int,
) -> BehaviorTrace:
    environment = GardGoalAlignmentEnvironment(config, design, beta, initial, *seeds, thresholds=ObservationThresholds())
    first = environment.initial_step()
    regimes = [first.external_regime]
    raw = [first.raw_observation]
    actions: list[int] = []
    for step in range(steps):
        action = int((step + action_offset) % 4)
        result = environment.step(action)
        actions.append(action)
        regimes.append(result.external_regime)
        raw.append(result.raw_observation)
        if not result.completed:
            break
    return BehaviorTrace(
        np.asarray(regimes, dtype=np.int8),
        np.asarray([value.growth_steps for value in raw], dtype=np.int32),
        np.asarray([value.boundary_similarity for value in raw], dtype=np.float64),
        np.asarray([value.alignment_score for value in raw], dtype=np.float64),
        np.asarray([value.cue for value in raw], dtype=np.int8),
        np.asarray([value.terminal for value in raw], dtype=np.int8),
        np.asarray(actions, dtype=np.int8),
    )


def controller_for(
    name: ControllerName,
    config: ExperimentConfig,
    pooled: CategoricalModel,
    local: CategoricalModel,
    variants: dict[str, CategoricalModel],
    adapt_cost: float,
    schedule: NDArray[np.int64] | None = None,
) -> Controller:
    costs = action_costs(config, adapt_cost)
    if name == ControllerName.BALANCED_AI_LOCAL:
        return ActiveInferenceController(variants["balanced_ai_local"], costs)
    if name == ControllerName.BALANCED_REWARD_LOCAL:
        return ActiveInferenceController(variants["balanced_reward_local"], costs)
    if name == ControllerName.BALANCED_YOKED_LOCAL:
        if schedule is None:
            raise ValueError("yoked controller requires a schedule")
        return ScheduledController(schedule, local.D)
    if name == ControllerName.GROWTH_AI_LOCAL:
        return ActiveInferenceController(variants["growth_ai_local"], costs)
    if name == ControllerName.GROWTH_REWARD_LOCAL:
        return ActiveInferenceController(variants["growth_reward_local"], costs)
    if name == ControllerName.BALANCED_AI_POOLED:
        return ActiveInferenceController(variants["balanced_ai_pooled"], costs)
    if name == ControllerName.BALANCED_REWARD_POOLED:
        return ActiveInferenceController(variants["balanced_reward_pooled"], costs)
    if name == ControllerName.REACTIVE:
        return ReactiveController(local.D)
    if name == ControllerName.NOOP:
        return NoopController(local.D)
    if name == ControllerName.ORACLE_BALANCED:
        return ActiveInferenceController(variants["balanced_reward_local"], costs, true_regime_planner=True)
    if name == ControllerName.SCRAMBLED_LOCAL:
        return ActiveInferenceController(variants["scrambled_local"], costs)
    if name == ControllerName.SENSORY_LESION:
        return ActiveInferenceController(variants["balanced_ai_local"], costs, sensory_lesion=True)
    if name == ControllerName.ACTION_LESION:
        return ActiveInferenceController(variants["balanced_ai_local"], costs)
    raise ValueError(f"unsupported controller {name}")


def _template(config: ExperimentConfig) -> dict[str, NDArray]:
    h, n = config.horizon, config.gard.n_types
    return {
        "completed": np.zeros(h, dtype=np.int8),
        "growth_steps": np.full(h, -1, dtype=np.int32),
        "similarity": np.full(h, np.nan),
        "alignment_score": np.full(h, np.nan),
        "decision_regime": np.full(h, -1, dtype=np.int8),
        "result_regime": np.full(h, -1, dtype=np.int8),
        "true_state": np.full(h, -1, dtype=np.int8),
        "observations": np.full((h, 4), -1, dtype=np.int8),
        "intended_actions": np.full(h, int(Action.WAIT), dtype=np.int8),
        "executed_actions": np.full(h, int(Action.WAIT), dtype=np.int8),
        "abstract_action_cost": np.zeros(h),
        "physical_action_cost": np.zeros(h),
        "edit_remove": np.full(h, -1, dtype=np.int16),
        "edit_add": np.full(h, -1, dtype=np.int16),
        "parents": np.zeros((h, n), dtype=np.int16),
        "compositions": np.zeros((h, n), dtype=np.int16),
        "beliefs": np.full((h, 9), np.nan),
        "predictive_priors": np.full((h, 9), np.nan),
        "vfe": np.full(h, np.nan),
        "log_evidence": np.full(h, np.nan),
        "expected_utility": np.full((h, 16), np.nan),
        "state_information_gain": np.full((h, 16), np.nan),
        "adjusted_neg_efe": np.full((h, 16), np.nan),
        "policy_posterior": np.full((h, 16), np.nan),
    }


def run_episode(
    config: ExperimentConfig,
    design: EnvironmentDesign,
    beta: NDArray[np.float64],
    initial: NDArray[np.int64],
    thresholds: ObservationThresholds,
    controller_name: ControllerName,
    controller: Controller,
    process_seeds: tuple[int, int, int],
    agent_seed: int,
) -> dict[str, NDArray]:
    environment = GardGoalAlignmentEnvironment(config, design, beta, initial, *process_seeds, thresholds=thresholds)
    controller.reset()
    rng = np.random.default_rng(agent_seed)
    current = environment.initial_step()
    observation = encode_observation(current.raw_observation, thresholds)
    arrays = _template(config)
    for step in range(config.horizon):
        regime = environment.regime
        state = hidden_state(regime, observation[2])
        decision = controller.decide(observation, regime, rng)
        lesion = controller_name == ControllerName.ACTION_LESION
        result = environment.step(decision.intended_action, action_lesion=lesion)
        arrays["completed"][step] = int(result.completed)
        arrays["growth_steps"][step] = result.raw_observation.growth_steps
        arrays["similarity"][step] = result.raw_observation.boundary_similarity
        arrays["alignment_score"][step] = result.raw_observation.alignment_score
        arrays["decision_regime"][step] = regime
        arrays["result_regime"][step] = result.external_regime
        arrays["true_state"][step] = state
        arrays["observations"][step] = observation
        arrays["intended_actions"][step] = decision.intended_action
        arrays["executed_actions"][step] = result.executed_action
        arrays["abstract_action_cost"][step] = result.abstract_action_cost
        arrays["physical_action_cost"][step] = result.physical_action_cost
        arrays["edit_remove"][step] = result.edit_remove
        arrays["edit_add"][step] = result.edit_add
        if result.parent is not None:
            arrays["parents"][step] = result.parent
        arrays["compositions"][step] = result.composition
        arrays["beliefs"][step] = decision.posterior
        arrays["predictive_priors"][step] = decision.predictive_prior
        arrays["vfe"][step] = decision.vfe
        arrays["log_evidence"][step] = decision.log_evidence
        arrays["expected_utility"][step] = decision.expected_utility
        arrays["state_information_gain"][step] = decision.state_information_gain
        arrays["adjusted_neg_efe"][step] = decision.adjusted_neg_efe
        arrays["policy_posterior"][step] = decision.policy_posterior
        controller.advance(decision.posterior, decision.intended_action if lesion else result.executed_action)
        current = result
        observation = encode_observation(result.raw_observation, thresholds)
        if not result.completed:
            break
    return arrays
