from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from fep_lab.seeds import derive_seed
from fep_ph15.types import ExternalRegime

from .config import ExperimentConfig
from .environment import (
    GardGoalAlignmentEnvironment,
    PlanningSeeds,
    clone_environment,
    planning_clone,
)
from .hybrid_model import (
    HybridModel,
    expected_regime_information,
    predicted_regime_prior,
    uniform_weights,
)
from .state import BodyState, HISTORY_LAGS, HISTORY_WIDTH, normalized_entropy
from .types import Action, ConditionSpec, InformationArm, ObservationThresholds


ACTION_PRIORITY = (
    int(Action.WAIT),
    int(Action.SAMPLE),
    int(Action.ADAPT_A),
    int(Action.ADAPT_B),
)


@dataclass(frozen=True)
class PlanDecision:
    action: int
    action_scores: NDArray[np.float64]
    information_values: NDArray[np.float64]
    action_probabilities: NDArray[np.float64]
    posterior: NDArray[np.float64]
    model_weights: NDArray[np.float64]
    planning_fissions: int = 0


def _empty_decision(action: int) -> PlanDecision:
    probability = np.zeros(4)
    probability[int(action)] = 1.0
    return PlanDecision(
        int(action),
        np.zeros(4),
        np.zeros(4),
        probability,
        np.full(3, np.nan),
        np.asarray([], dtype=np.float64),
        0,
    )


def _action_cost(config: ExperimentConfig, action: int) -> float:
    if int(action) == int(Action.SAMPLE):
        return config.action_cost_sample
    if int(action) in (int(Action.ADAPT_A), int(Action.ADAPT_B)):
        return config.action_cost_uptake
    return 0.0


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
        action = (
            int(Action.ADAPT_A)
            if cue == 1
            else int(Action.ADAPT_B)
            if cue == 2
            else int(Action.WAIT)
        )
        return _empty_decision(action)


class TrueRegimeOracle(NoopController):
    def decide(
        self, *, environment: GardGoalAlignmentEnvironment, **_: Any
    ) -> PlanDecision:
        regime = int(environment.regime)
        action = (
            int(Action.ADAPT_A)
            if regime == int(ExternalRegime.A)
            else int(Action.ADAPT_B)
            if regime == int(ExternalRegime.B)
            else int(Action.WAIT)
        )
        return _empty_decision(action)


class ScheduledController(NoopController):
    def __init__(self, actions: NDArray[np.integer]) -> None:
        self.actions = np.asarray(actions, dtype=np.int8)

    def decide(self, *, step: int, **_: Any) -> PlanDecision:
        return _empty_decision(int(self.actions[step]))


def _legacy_step_utility(
    completed: bool,
    growth_steps: int,
    similarity: float,
    cost: float,
    thresholds: ObservationThresholds,
) -> float:
    if not completed:
        return -4.0 - cost
    growth = (
        0.50
        if growth_steps <= thresholds.growth[0]
        else 0.20
        if growth_steps <= thresholds.growth[1]
        else -0.50
    )
    similarity_value = -0.50 if similarity < 0.85 else 0.0 if similarity <= 0.90 else 0.50
    return growth + similarity_value - cost


@dataclass
class _OracleNode:
    sequence: tuple[int, ...]
    environment: GardGoalAlignmentEnvironment
    legacy_score: float
    inherited: int
    completed: int
    cost: float


class PhysicalRolloutOracle:
    def __init__(
        self,
        config: ExperimentConfig,
        condition: ConditionSpec,
        thresholds: ObservationThresholds,
        planning_domain: tuple[object, ...],
        *,
        depth: int,
        beam: int,
        replicas: int,
        goal_aligned: bool,
    ) -> None:
        self.config = config
        self.condition = condition
        self.thresholds = thresholds
        self.planning_domain = planning_domain
        self.depth = int(depth)
        self.beam = int(beam)
        self.replicas = int(replicas)
        self.goal_aligned = bool(goal_aligned)

    def reset(self) -> None:
        return None

    def _seeds(self, step: int, replica: int) -> PlanningSeeds:
        values = tuple(
            derive_seed(
                self.config.master_seed,
                "fep_ph17.stage-a-planning",
                *self.planning_domain,
                step,
                replica,
                kind,
            )
            for kind in ("chemistry", "environment", "observation")
        )
        return PlanningSeeds(*values)

    def _rank(self, node: _OracleNode) -> tuple[float, ...]:
        if not self.goal_aligned:
            return (node.legacy_score,)
        alive = float(not node.environment.terminal)
        return (
            float(node.inherited),
            alive,
            float(node.completed),
            -node.cost,
        )

    def decide(
        self,
        *,
        environment: GardGoalAlignmentEnvironment,
        step: int,
        **_: Any,
    ) -> PlanDecision:
        replica_scores = np.zeros((self.replicas, 4, 4))
        fissions = 0
        for replica in range(self.replicas):
            root = planning_clone(environment, self._seeds(step, replica))
            nodes = [_OracleNode((), root, 0.0, 0, 0, 0.0)]
            for _depth in range(self.depth):
                expanded: list[_OracleNode] = []
                for node in nodes:
                    if node.environment.terminal:
                        expanded.append(node)
                        continue
                    for action in ACTION_PRIORITY:
                        branch = clone_environment(node.environment)
                        result = branch.step(action)
                        fissions += 1
                        expanded.append(
                            _OracleNode(
                                node.sequence + (action,),
                                branch,
                                node.legacy_score
                                + _legacy_step_utility(
                                    result.completed,
                                    result.raw_observation.growth_steps,
                                    result.raw_observation.boundary_similarity,
                                    result.abstract_action_cost,
                                    self.thresholds,
                                ),
                                node.inherited
                                + int(
                                    result.completed
                                    and result.raw_observation.boundary_similarity > 0.90
                                ),
                                node.completed + int(result.completed),
                                node.cost + float(result.abstract_action_cost),
                            )
                        )
                expanded.sort(
                    key=lambda node: (
                        tuple(-value for value in self._rank(node)),
                        tuple(ACTION_PRIORITY.index(action) for action in node.sequence),
                    )
                )
                chosen: list[_OracleNode] = []
                for first_action in ACTION_PRIORITY:
                    group = [
                        node
                        for node in expanded
                        if node.sequence and node.sequence[0] == first_action
                    ]
                    if group:
                        chosen.append(group[0])
                chosen_ids = {id(node) for node in chosen}
                remaining = [node for node in expanded if id(node) not in chosen_ids]
                nodes = (chosen + remaining)[: max(4, self.beam)]
            for action in ACTION_PRIORITY:
                group = [node for node in nodes if node.sequence and node.sequence[0] == action]
                if not group:
                    replica_scores[replica, action] = -1.0e9
                    continue
                best = max(group, key=self._rank)
                if self.goal_aligned:
                    replica_scores[replica, action] = np.asarray(self._rank(best))
                else:
                    replica_scores[replica, action, 0] = best.legacy_score
        aggregate = replica_scores.mean(axis=0)
        if self.goal_aligned:
            ranked = sorted(
                ACTION_PRIORITY,
                key=lambda action: (
                    tuple(-value for value in aggregate[action]),
                    ACTION_PRIORITY.index(action),
                ),
            )
            scalar = (
                1_000_000.0 * aggregate[:, 0]
                + 10_000.0 * aggregate[:, 1]
                + 100.0 * aggregate[:, 2]
                + aggregate[:, 3]
            )
        else:
            scalar = aggregate[:, 0]
            ranked = sorted(
                ACTION_PRIORITY,
                key=lambda action: (-scalar[action], ACTION_PRIORITY.index(action)),
            )
        action = int(ranked[0])
        probability = np.zeros(4)
        probability[action] = 1.0
        return PlanDecision(
            action,
            scalar,
            np.zeros(4),
            probability,
            np.full(3, np.nan),
            np.asarray([], dtype=np.float64),
            fissions,
        )

    def observe(self, **_: Any) -> None:
        return None


@dataclass
class _HybridNode:
    sequence: tuple[int, ...]
    state: BodyState
    score: float
    information: float


def _predicted_body(
    previous: BodyState,
    mean: NDArray[np.float64],
    model: HybridModel,
    action: int,
    condition: ConditionSpec,
) -> BodyState:
    previous_action = np.zeros(4)
    previous_action[int(previous.previous_action)] = 1.0
    history_row = np.concatenate(
        (
            np.asarray((previous.growth_norm, previous.similarity, previous.alignment)),
            previous.cue_probs,
            previous_action,
        )
    )
    history = np.vstack((history_row, previous.history[0]))
    regime = predicted_regime_prior(
        previous.regime_belief,
        0.08 if condition.volatility == "slow" else 0.25,
        0.05,
    )
    body = BodyState(
        model.projection.inverse(mean[13:]),
        float(mean[5]),
        float(mean[2]),
        float(mean[3]),
        float(mean[4]),
        np.asarray(mean[6:10]),
        regime,
        int(action),
        history.reshape(HISTORY_LAGS, HISTORY_WIDTH),
    )
    body.validate()
    return body


class HybridPlanner:
    def __init__(
        self,
        model: HybridModel,
        config: ExperimentConfig,
        condition: ConditionSpec,
        *,
        epistemic_coefficient: float,
        sample_lesion: bool = False,
        shuffled_actions: bool = False,
    ) -> None:
        model.validate()
        self.model = model
        self.config = config
        self.condition = condition
        self.epistemic_coefficient = float(epistemic_coefficient)
        self.sample_lesion = bool(sample_lesion)
        self.shuffled_actions = bool(shuffled_actions)
        self.weights = uniform_weights(model)

    def reset(self) -> None:
        self.weights = uniform_weights(self.model)

    def _cue_accuracy(self, action: int) -> float:
        if int(action) != int(Action.SAMPLE):
            return self.config.passive_cue_accuracy
        return (
            self.config.informative_sample_accuracy
            if self.condition.information_arm == InformationArm.INFORMATIVE
            else self.config.sham_sample_accuracy
        )

    def _expand(self, node: _HybridNode, action: int) -> _HybridNode:
        prediction = self.model.predict(
            node.state,
            self.condition,
            action,
            shuffled_actions=self.shuffled_actions,
        )
        mean = prediction.mean(self.weights)
        variance = float(
            np.dot(self.weights, (prediction.members[:, 0] - mean[0]) ** 2)
        )
        pragmatic = (
            float(mean[0])
            - self.config.action_cost_weight * _action_cost(self.config, action)
            - self.config.risk_coefficient * np.sqrt(max(0.0, variance))
        )
        information = expected_regime_information(
            node.state.regime_belief,
            0.08 if self.condition.volatility == "slow" else 0.25,
            0.05,
            self._cue_accuracy(action),
        )
        following = _predicted_body(
            node.state, mean, self.model, action, self.condition
        )
        return _HybridNode(
            node.sequence + (int(action),),
            following,
            node.score + pragmatic + self.epistemic_coefficient * information,
            node.information + information,
        )

    def decide(
        self,
        *,
        body_state: BodyState,
        rng: np.random.Generator,
        **_: Any,
    ) -> PlanDecision:
        allowed = (
            tuple(action for action in ACTION_PRIORITY if action != int(Action.SAMPLE))
            if self.sample_lesion
            else ACTION_PRIORITY
        )
        nodes = [_HybridNode((), body_state, 0.0, 0.0)]
        for _depth in range(self.config.hybrid_depth):
            expanded = [self._expand(node, action) for node in nodes for action in allowed]
            expanded.sort(
                key=lambda node: (
                    -node.score,
                    tuple(ACTION_PRIORITY.index(action) for action in node.sequence),
                )
            )
            nodes = expanded[: self.config.hybrid_beam]
        scores = np.full(4, -1.0e9)
        information = np.zeros(4)
        for node in nodes:
            first = node.sequence[0]
            if node.score > scores[first]:
                scores[first] = node.score
                information[first] = node.information
        finite = scores > -1.0e8
        floor = float(np.min(scores[finite]) - 1.0) if np.any(finite) else -1.0
        scores[~finite] = floor
        probability = _softmax(scores, self.config.policy_precision)
        if self.sample_lesion:
            probability[int(Action.SAMPLE)] = 0.0
            probability /= probability.sum()
        action = _sample(probability, rng)
        return PlanDecision(
            action,
            scores,
            information,
            probability,
            body_state.regime_belief.copy(),
            self.weights.copy(),
            0,
        )

    def observe(self, **_: Any) -> None:
        return None


def exact_multiset_yoke(
    actions: NDArray[np.integer], seed: int
) -> NDArray[np.int8]:
    values = np.asarray(actions, dtype=np.int8).copy()
    return values[np.random.default_rng(seed).permutation(len(values))]
