from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from fep_lab.seeds import derive_seed
from fep_lab.types import CategoricalModel
from fep_ph15.controllers import ActiveInferenceController
from fep_ph15.models import action_costs

from .causal_model import (
    CausalEnsemble,
    EnsemblePrediction,
    expected_information_gain,
    observed_likelihood_vector,
    predicted_state,
    uniform_weights,
    update_member_weights,
)
from .config import ExperimentConfig
from .environment import (
    GardGoalAlignmentEnvironment,
    PlanningSeeds,
    clone_environment,
    planning_clone,
)
from .state import BodyState, state_features
from .types import Action, ConditionSpec, ObservationThresholds


ACTION_PRIORITY = (int(Action.WAIT), int(Action.SAMPLE), int(Action.ADAPT_A), int(Action.ADAPT_B))


@dataclass(frozen=True)
class PlanDecision:
    action: int
    action_scores: NDArray[np.float64]
    information_values: NDArray[np.float64]
    action_probabilities: NDArray[np.float64]
    categorical_posterior: NDArray[np.float64]
    model_weights: NDArray[np.float64]
    planning_fissions: int = 0


def _empty_decision(action: int, members: int = 0) -> PlanDecision:
    probability = np.zeros(4, dtype=np.float64)
    probability[int(action)] = 1.0
    return PlanDecision(
        int(action),
        np.full(4, np.nan),
        np.full(4, np.nan),
        probability,
        np.full(9, np.nan),
        np.full(members, np.nan),
    )


def _action_cost(config: ExperimentConfig, condition: ConditionSpec, action: int) -> float:
    if int(action) == int(Action.SAMPLE):
        return config.action_cost_sample
    if int(action) not in (int(Action.ADAPT_A), int(Action.ADAPT_B)):
        return 0.0
    if str(condition.channel) == "uptake":
        return config.action_cost_uptake
    return config.molecular_base_cost + config.molecular_increment_cost * (
        condition.actuator.molecular_dose - 1
    )


def _growth_preference(growth_norm: float, thresholds: ObservationThresholds, budget: int) -> float:
    lower = np.log1p(thresholds.growth[0]) / np.log1p(budget)
    upper = np.log1p(thresholds.growth[1]) / np.log1p(budget)
    return 0.50 if growth_norm <= lower else 0.20 if growth_norm <= upper else -0.50


def _similarity_preference(similarity: float) -> float:
    return -0.50 if similarity < 0.85 else 0.0 if similarity <= 0.90 else 0.50


def _predicted_member_utility(
    prediction: EnsemblePrediction,
    action: int,
    config: ExperimentConfig,
    condition: ConditionSpec,
    thresholds: ObservationThresholds,
) -> NDArray[np.float64]:
    output = np.empty(len(prediction.members), dtype=np.float64)
    cost = _action_cost(config, condition, action)
    for index, member in enumerate(prediction.members):
        completed = float(member[0])
        ordinary = _growth_preference(float(member[1]), thresholds, condition.growth_budget)
        ordinary += _similarity_preference(float(member[2]))
        output[index] = completed * ordinary + (1.0 - completed) * -4.0 - cost
    return output


def _actual_step_utility(
    completed: bool,
    growth_steps: int,
    similarity: float,
    action_cost_value: float,
    thresholds: ObservationThresholds,
) -> float:
    if not completed:
        return -4.0 - action_cost_value
    growth = 0.50 if growth_steps <= thresholds.growth[0] else 0.20 if growth_steps <= thresholds.growth[1] else -0.50
    return growth + _similarity_preference(similarity) - action_cost_value


def _softmax(values: NDArray[np.floating], precision: float) -> NDArray[np.float64]:
    scores = precision * np.asarray(values, dtype=np.float64)
    scores -= float(np.max(scores))
    weights = np.exp(scores)
    return weights / float(weights.sum())


def _sample(probability: NDArray[np.floating], rng: np.random.Generator) -> int:
    draw = float(rng.random())
    return int(np.searchsorted(np.cumsum(probability), draw, side="right").clip(max=3))


class NoopController:
    def reset(self) -> None:
        return None

    def decide(self, **_: Any) -> PlanDecision:
        return _empty_decision(int(Action.WAIT))

    def observe(self, **_: Any) -> None:
        return None


class ReactiveController(NoopController):
    def decide(self, *, body_state: BodyState, **_: Any) -> PlanDecision:
        cue = int(np.argmax(body_state.cue_probs))
        action = int(Action.ADAPT_A) if cue == 1 else int(Action.ADAPT_B) if cue == 2 else int(Action.WAIT)
        return _empty_decision(action)


class ScheduledController(NoopController):
    def __init__(self, schedule: NDArray[np.integer]) -> None:
        self.schedule = np.asarray(schedule, dtype=np.int8)
        self.index = 0

    def reset(self) -> None:
        self.index = 0

    def decide(self, **_: Any) -> PlanDecision:
        action = int(self.schedule[self.index]) if self.index < len(self.schedule) else int(Action.WAIT)
        self.index += 1
        return _empty_decision(action)


class CategoricalController:
    def __init__(
        self,
        model: CategoricalModel,
        config: ExperimentConfig,
        condition: ConditionSpec,
        *,
        true_regime: bool,
    ) -> None:
        adapt = _action_cost(config, condition, int(Action.ADAPT_A))
        self.model = model
        self.controller = ActiveInferenceController(
            model,
            action_costs(config, adapt),
            true_regime_planner=true_regime,
        )
        self.last_posterior = model.D.copy()
        self.last_action = int(Action.WAIT)

    def reset(self) -> None:
        self.controller.reset()
        self.last_posterior = self.model.D.copy()
        self.last_action = int(Action.WAIT)

    def decide(
        self,
        *,
        categorical_observation: tuple[int, ...],
        environment: GardGoalAlignmentEnvironment,
        rng: np.random.Generator,
        **_: Any,
    ) -> PlanDecision:
        decision = self.controller.decide(categorical_observation, environment.regime, rng)
        probability = np.bincount(
            self.model.policies[:, 0],
            weights=decision.policy_posterior,
            minlength=4,
        ).astype(np.float64)
        probability /= float(probability.sum())
        scores = np.full(4, -np.inf, dtype=np.float64)
        information = np.zeros(4, dtype=np.float64)
        for action in range(4):
            mask = self.model.policies[:, 0] == action
            if np.any(mask):
                scores[action] = float(np.max(decision.adjusted_neg_efe[mask]))
                information[action] = float(np.max(decision.state_information_gain[mask]))
        self.last_posterior = decision.posterior.copy()
        self.last_action = int(decision.intended_action)
        return PlanDecision(
            self.last_action,
            scores,
            information,
            probability,
            decision.posterior.copy(),
            np.asarray([], dtype=np.float64),
        )

    def observe(self, *, executed_action: int, **_: Any) -> None:
        self.controller.advance(self.last_posterior, int(executed_action))


@dataclass
class _OracleNode:
    sequence: tuple[int, ...]
    environment: GardGoalAlignmentEnvironment
    score: float


class PhysicalRolloutOracle:
    def __init__(
        self,
        config: ExperimentConfig,
        condition: ConditionSpec,
        thresholds: ObservationThresholds,
        planning_domain: tuple[object, ...],
    ) -> None:
        self.config = config
        self.condition = condition
        self.thresholds = thresholds
        self.planning_domain = planning_domain

    def reset(self) -> None:
        return None

    def _seeds(self, step: int, replica: int) -> PlanningSeeds:
        values = tuple(
            derive_seed(
                self.config.master_seed,
                "fep_ph16.physical_oracle",
                *self.planning_domain,
                step,
                replica,
                kind,
            )
            for kind in ("chemistry", "environment", "observation")
        )
        return PlanningSeeds(*values)

    def decide(
        self,
        *,
        environment: GardGoalAlignmentEnvironment,
        step: int,
        **_: Any,
    ) -> PlanDecision:
        action_scores = np.zeros((self.config.oracle_replicas, 4), dtype=np.float64)
        fissions = 0
        for replica in range(self.config.oracle_replicas):
            root = planning_clone(environment, self._seeds(step, replica))
            nodes = [_OracleNode((), root, 0.0)]
            for depth in range(self.config.oracle_depth):
                expanded: list[_OracleNode] = []
                for node in nodes:
                    if node.environment.terminal:
                        expanded.append(node)
                        continue
                    for action in ACTION_PRIORITY:
                        branch = clone_environment(node.environment)
                        result = branch.step(action)
                        fissions += 1
                        score = node.score + _actual_step_utility(
                            result.completed,
                            result.raw_observation.growth_steps,
                            result.raw_observation.boundary_similarity,
                            result.abstract_action_cost,
                            self.thresholds,
                        )
                        sequence = node.sequence + (action,)
                        expanded.append(_OracleNode(sequence, branch, score))
                if not expanded:
                    break
                expanded.sort(
                    key=lambda node: (
                        -node.score,
                        tuple(ACTION_PRIORITY.index(action) for action in node.sequence),
                    )
                )
                if depth == 0:
                    nodes = expanded
                else:
                    # Preserve at least one continuation for every first action so
                    # all four root scores have the same look-ahead depth.
                    chosen: list[_OracleNode] = []
                    for first_action in ACTION_PRIORITY:
                        group = [node for node in expanded if node.sequence[0] == first_action]
                        if group:
                            chosen.append(group[0])
                    chosen_ids = {id(node) for node in chosen}
                    remaining = [node for node in expanded if id(node) not in chosen_ids]
                    nodes = (chosen + remaining)[: max(4, self.config.oracle_beam)]
            best_by_first = np.full(4, -np.inf, dtype=np.float64)
            for node in nodes:
                if node.sequence:
                    best_by_first[node.sequence[0]] = max(
                        best_by_first[node.sequence[0]], node.score
                    )
            action_scores[replica] = best_by_first
        scores = np.mean(action_scores, axis=0)
        ranked = sorted(ACTION_PRIORITY, key=lambda action: (-scores[action], ACTION_PRIORITY.index(action)))
        action = int(ranked[0])
        probability = np.zeros(4, dtype=np.float64)
        probability[action] = 1.0
        return PlanDecision(
            action,
            scores,
            np.zeros(4, dtype=np.float64),
            probability,
            np.full(9, np.nan),
            np.asarray([], dtype=np.float64),
            fissions,
        )

    def observe(self, **_: Any) -> None:
        return None


@dataclass
class _ModelNode:
    sequence: tuple[int, ...]
    state: BodyState
    score: float
    information: float


class CausalMPCController:
    def __init__(
        self,
        model: CausalEnsemble,
        config: ExperimentConfig,
        condition: ConditionSpec,
        thresholds: ObservationThresholds,
        offsets: NDArray[np.floating],
        *,
        epistemic: bool,
        shuffled_actions: bool = False,
    ) -> None:
        self.model = model
        self.config = config
        self.condition = condition
        self.thresholds = thresholds
        self.offsets = np.asarray(offsets, dtype=np.float64)
        self.epistemic = bool(epistemic)
        self.shuffled_actions = bool(shuffled_actions)
        self.weights = uniform_weights(model)
        self.last_prediction: EnsemblePrediction | None = None

    def reset(self) -> None:
        self.weights = uniform_weights(self.model)
        self.last_prediction = None

    def _expand(self, node: _ModelNode, action: int) -> _ModelNode:
        features = state_features(node.state, self.condition, rich=self.model.rich)
        prediction = self.model.predict(
            features,
            action,
            offsets=self.offsets,
            shuffled_actions=self.shuffled_actions,
        )
        member_utility = _predicted_member_utility(
            prediction, action, self.config, self.condition, self.thresholds
        )
        mean_utility = float(np.dot(self.weights, member_utility))
        variance = float(np.dot(self.weights, (member_utility - mean_utility) ** 2))
        information = expected_information_gain(prediction, self.weights)
        increment = mean_utility - self.config.risk_coefficient * np.sqrt(max(0.0, variance))
        if self.epistemic:
            increment += self.config.epistemic_coefficient * information
        following = predicted_state(
            node.state, prediction, self.weights, action, rich=self.model.rich
        )
        return _ModelNode(
            node.sequence + (int(action),),
            following,
            node.score + increment,
            node.information + information,
        )

    def decide(
        self,
        *,
        body_state: BodyState,
        rng: np.random.Generator,
        **_: Any,
    ) -> PlanDecision:
        nodes = [_ModelNode((), body_state, 0.0, 0.0)]
        for _depth in range(self.config.mpc_depth):
            expanded = [self._expand(node, action) for node in nodes for action in ACTION_PRIORITY]
            expanded.sort(
                key=lambda node: (
                    -node.score,
                    tuple(ACTION_PRIORITY.index(action) for action in node.sequence),
                )
            )
            nodes = expanded[: self.config.mpc_beam]
        scores = np.full(4, -1.0e9, dtype=np.float64)
        information = np.zeros(4, dtype=np.float64)
        for node in nodes:
            first = node.sequence[0]
            if node.score > scores[first]:
                scores[first] = node.score
                information[first] = node.information
        finite = np.isfinite(scores) & (scores > -1.0e8)
        floor = float(np.min(scores[finite])) - 1.0 if np.any(finite) else -1.0
        scores[~finite] = floor
        probability = _softmax(scores, self.config.policy_precision)
        action = _sample(probability, rng)
        features = state_features(body_state, self.condition, rich=self.model.rich)
        self.last_prediction = self.model.predict(
            features,
            action,
            offsets=self.offsets,
            shuffled_actions=self.shuffled_actions,
        )
        return PlanDecision(
            action,
            scores,
            information,
            probability,
            np.full(9, np.nan),
            self.weights.copy(),
        )

    def observe(
        self,
        *,
        composition: NDArray[np.integer],
        raw_observation: Any,
        completed: bool,
        growth_budget: int,
        **_: Any,
    ) -> None:
        if self.last_prediction is None:
            return
        observed = observed_likelihood_vector(
            composition, raw_observation, completed, growth_budget
        )
        self.weights = update_member_weights(
            self.weights, self.last_prediction, observed
        )


def exact_multiset_yoke(actions: NDArray[np.integer], seed: int) -> NDArray[np.int8]:
    values = np.asarray(actions, dtype=np.int8).copy()
    return values[np.random.default_rng(seed).permutation(len(values))]
