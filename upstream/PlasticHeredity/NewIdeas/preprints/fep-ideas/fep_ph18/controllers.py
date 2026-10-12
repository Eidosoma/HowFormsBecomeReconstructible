from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import numpy as np
from numpy.typing import NDArray

from fep_ph15.types import ExternalRegime

from .config import MODEL_ACTIONS, ExperimentConfig
from .environment import GardGoalAlignmentEnvironment
from .hybrid_model import (
    HybridModel,
    cue_distribution,
    expected_regime_information,
    posterior_for_cue,
    predicted_regime_prior,
    uniform_weights,
)
from .state import BodyState, HISTORY_LAGS, HISTORY_WIDTH, cue_probabilities
from .types import Action, ConditionSpec, InformationArm, SensingTiming


PHYSICAL_ACTIONS = (int(Action.WAIT), int(Action.ADAPT_A), int(Action.ADAPT_B))
PLAN_CHOICES = 4  # WAIT, ADAPT_A, ADAPT_B, SENSE


@dataclass(frozen=True)
class PlanDecision:
    sense: int
    physical_action: int
    model_action: int
    cue_actions: NDArray[np.int8]
    plan_scores: NDArray[np.float64]
    action_scores: NDArray[np.float64]
    information_values: NDArray[np.float64]
    action_probabilities: NDArray[np.float64]
    posterior: NDArray[np.float64]
    model_weights: NDArray[np.float64]
    instrumental_value: float = 0.0
    epistemic_value: float = 0.0
    policy_contingency: float = 0.0
    planning_nodes: int = 0

    @property
    def action(self) -> int:
        """Compatibility alias for non-compound callers."""

        return int(Action.SAMPLE) if self.sense else int(self.physical_action)


def _empty_decision(action: int, posterior: NDArray[np.floating] | None = None) -> PlanDecision:
    plan_probability = np.zeros(PLAN_CHOICES)
    plan_probability[min(int(action), 2)] = 1.0
    model_probability = np.zeros(MODEL_ACTIONS)
    model_probability[int(action)] = 1.0
    return PlanDecision(
        sense=0,
        physical_action=int(action),
        model_action=int(action),
        cue_actions=np.full(4, int(action), dtype=np.int8),
        plan_scores=np.zeros(PLAN_CHOICES),
        action_scores=np.zeros(MODEL_ACTIONS),
        information_values=np.zeros(MODEL_ACTIONS),
        action_probabilities=model_probability,
        posterior=(
            np.asarray(posterior, dtype=np.float64).copy()
            if posterior is not None
            else np.full(3, np.nan)
        ),
        model_weights=np.asarray([], dtype=np.float64),
    )


def _softmax(values: NDArray[np.floating], precision: float) -> NDArray[np.float64]:
    scores = precision * np.asarray(values, dtype=np.float64)
    scores -= float(np.max(scores))
    weights = np.exp(scores)
    return weights / float(weights.sum())


def _sample(probability: NDArray[np.floating], rng: np.random.Generator) -> int:
    draw = float(rng.random())
    return int(
        np.searchsorted(np.cumsum(probability), draw, side="right").clip(
            max=len(probability) - 1
        )
    )


def _reflex_action_from_cue(cue: int) -> int:
    return (
        int(Action.ADAPT_A)
        if int(cue) == 1
        else int(Action.ADAPT_B)
        if int(cue) == 2
        else int(Action.WAIT)
    )


def _reflex_action_from_belief(belief: NDArray[np.floating]) -> int:
    regime = int(np.argmax(np.asarray(belief, dtype=np.float64)))
    return (
        int(Action.ADAPT_A)
        if regime == int(ExternalRegime.A)
        else int(Action.ADAPT_B)
        if regime == int(ExternalRegime.B)
        else int(Action.WAIT)
    )


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
        return _empty_decision(_reflex_action_from_cue(cue), body_state.regime_belief)


class TrueRegimeOracle(NoopController):
    def decide(
        self, *, environment: GardGoalAlignmentEnvironment, **_: Any
    ) -> PlanDecision:
        return _empty_decision(_reflex_action_from_belief(np.eye(3)[environment.regime]))


class PosteriorReflex(NoopController):
    def decide(self, *, body_state: BodyState, **_: Any) -> PlanDecision:
        return _empty_decision(
            _reflex_action_from_belief(body_state.regime_belief),
            body_state.regime_belief,
        )


class AlwaysSenseReflex(NoopController):
    """Use every available observation/action slot without hiding the delay."""

    def __init__(self, timing: SensingTiming) -> None:
        self.timing = timing
        self.pending_delayed_cue = False

    def reset(self) -> None:
        self.pending_delayed_cue = False

    def decide(self, *, body_state: BodyState, **_: Any) -> PlanDecision:
        cue_actions = np.asarray(
            [_reflex_action_from_cue(cue) for cue in range(4)], dtype=np.int8
        )
        if self.timing == SensingTiming.DELAYED and self.pending_delayed_cue:
            self.pending_delayed_cue = False
            return _empty_decision(
                _reflex_action_from_cue(int(np.argmax(body_state.cue_probs))),
                body_state.regime_belief,
            )
        self.pending_delayed_cue = self.timing == SensingTiming.DELAYED
        probability = np.zeros(MODEL_ACTIONS)
        probability[3 if self.timing == SensingTiming.DELAYED else 4] = 1.0
        return PlanDecision(
            sense=1,
            physical_action=int(Action.WAIT),
            model_action=(3 if self.timing == SensingTiming.DELAYED else 4),
            cue_actions=cue_actions,
            plan_scores=np.asarray((0.0, 0.0, 0.0, 1.0)),
            action_scores=np.zeros(MODEL_ACTIONS),
            information_values=np.zeros(MODEL_ACTIONS),
            action_probabilities=probability,
            posterior=body_state.regime_belief.copy(),
            model_weights=np.asarray([], dtype=np.float64),
            policy_contingency=1.0,
        )


def _model_action_cost(config: ExperimentConfig, model_action: int) -> float:
    value = int(model_action)
    if value == int(Action.SAMPLE):
        return float(config.action_cost_sample)
    if value in (int(Action.ADAPT_A), int(Action.ADAPT_B)):
        return float(config.action_cost_uptake)
    if value >= 4:
        physical = value - 4
        return float(config.action_cost_sample) + (
            float(config.action_cost_uptake) if physical in (1, 2) else 0.0
        )
    return 0.0


def _predicted_body(
    previous: BodyState,
    mean: NDArray[np.float64],
    model: HybridModel,
    physical_action: int,
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
        previous.regime_belief, condition.switch_probability, 0.05
    )
    body = BodyState(
        model.projection.inverse(mean[13:]),
        float(mean[5]),
        float(mean[2]),
        float(mean[3]),
        float(mean[4]),
        np.asarray(mean[6:10]),
        regime,
        int(physical_action),
        history.reshape(HISTORY_LAGS, HISTORY_WIDTH),
    )
    body.validate()
    return body


class ContingentPlanner:
    """A bounded policy tree whose sensing branch conditions on each cue."""

    def __init__(
        self,
        model: HybridModel,
        config: ExperimentConfig,
        condition: ConditionSpec,
        *,
        epistemic_coefficient: float,
        contingent: bool = True,
        sample_lesion: bool = False,
        shuffled_actions: bool = False,
    ) -> None:
        model.validate()
        self.model = model
        self.config = config
        self.condition = condition
        self.epistemic_coefficient = float(epistemic_coefficient)
        self.contingent = bool(contingent)
        self.sample_lesion = bool(sample_lesion)
        self.shuffled_actions = bool(shuffled_actions)
        self.weights = uniform_weights(model)
        self.depth = int(config.selected_planner_depth or min(config.planner_depths))

    def reset(self) -> None:
        self.weights = uniform_weights(self.model)

    def _accuracy(self) -> float:
        return float(
            self.config.informative_sample_accuracy
            if self.condition.information_arm == InformationArm.INFORMATIVE
            else self.config.sham_sample_accuracy
        )

    def _value(
        self, state: BodyState, model_action: int
    ) -> tuple[float, BodyState, int]:
        prediction = self.model.predict(
            state,
            self.condition,
            model_action,
            shuffled_actions=self.shuffled_actions,
        )
        mean = prediction.mean(self.weights)
        disagreement = float(
            np.dot(self.weights, (prediction.members[:, 0] - mean[0]) ** 2)
        )
        pragmatic = (
            float(mean[0])
            + 0.15 * float(mean[1])
            - self.config.action_cost_weight
            * _model_action_cost(self.config, model_action)
            - self.config.risk_coefficient * np.sqrt(max(0.0, disagreement))
        )
        physical = (
            model_action - 4
            if model_action >= 4
            else int(Action.SAMPLE)
            if model_action == int(Action.SAMPLE)
            else model_action
        )
        return (
            pragmatic,
            _predicted_body(state, mean, self.model, physical, self.condition),
            1,
        )

    def _best_physical(
        self,
        state: BodyState,
        depth: int,
        *,
        compound: bool = False,
    ) -> tuple[float, int, int]:
        scored = [
            self._physical_plan(state, physical, depth, compound=compound)
            for physical in PHYSICAL_ACTIONS
        ]
        return max(scored, key=lambda value: (value[0], -value[1]))

    def _physical_plan(
        self,
        state: BodyState,
        physical: int,
        depth: int,
        *,
        compound: bool = False,
    ) -> tuple[float, int, int]:
        model_action = 4 + physical if compound else physical
        immediate, following, nodes = self._value(state, model_action)
        frontier: list[tuple[float, BodyState, tuple[int, ...]]] = [
            (immediate, following, (int(physical),))
        ]
        for tail_index in range(max(0, int(depth) - 1)):
            expanded: list[tuple[float, BodyState, tuple[int, ...]]] = []
            for score, current, sequence in frontier:
                for tail_action in PHYSICAL_ACTIONS:
                    value, next_state, used = self._value(current, tail_action)
                    nodes += used
                    expanded.append(
                        (
                            score + (0.90 ** (tail_index + 1)) * value,
                            next_state,
                            sequence + (tail_action,),
                        )
                    )
            expanded.sort(key=lambda value: (-value[0], value[2]))
            frontier = expanded[: self.config.contingent_beam]
        best = max(frontier, key=lambda value: (value[0], tuple(-x for x in value[2])))
        return float(best[0]), int(physical), int(nodes)

    def _sense_plan(
        self, state: BodyState
    ) -> tuple[float, float, NDArray[np.int8], int, int]:
        accuracy = self._accuracy()
        timing = self.condition.sensing_timing
        transition = timing == SensingTiming.DELAYED
        prior = (
            predicted_regime_prior(
                state.regime_belief, self.condition.switch_probability, 0.05
            )
            if transition
            else state.regime_belief / float(state.regime_belief.sum())
        )
        probabilities = cue_distribution(prior, accuracy)
        cue_actions = np.zeros(4, dtype=np.int8)
        sensed_information = expected_regime_information(
            state.regime_belief,
            self.condition.switch_probability,
            0.05,
            accuracy,
            transition=transition,
        )
        passive_information = expected_regime_information(
            state.regime_belief,
            self.condition.switch_probability,
            0.05,
            self.config.passive_cue_accuracy,
            transition=transition,
        )
        # All controllers receive passive evidence. EFE values only the
        # incremental precision supplied by deliberate sensing, making the
        # sham arm (sense accuracy == passive accuracy) an exact coefficient
        # lesion while leaving its timing available to the utility planner.
        information = max(0.0, sensed_information - passive_information)
        nodes = 0
        if not self.contingent:
            # The open-loop control receives the same information bonus but
            # commits to one action before seeing the cue.
            if timing == SensingTiming.SAME_CYCLE:
                instrumental, action, nodes = self._best_physical(
                    state, self.depth, compound=True
                )
                cue_actions[:] = action
                model_action = 4 + action
            else:
                immediate, sampled_state, used = self._value(
                    state, int(Action.SAMPLE)
                )
                committed, action, tail_nodes = self._best_physical(
                    sampled_state, max(1, self.depth - 1), compound=False
                )
                instrumental = immediate + 0.90 * committed
                cue_actions[:] = action
                model_action = int(Action.SAMPLE)
                nodes = used + tail_nodes
            return (
                float(instrumental),
                float(information),
                cue_actions,
                model_action,
                nodes,
            )
        if timing == SensingTiming.DELAYED:
            immediate, sampled_state, used = self._value(state, int(Action.SAMPLE))
            nodes += used
            branch_total = 0.0
            for cue, probability in enumerate(probabilities):
                posterior = posterior_for_cue(prior, cue, accuracy)
                branch = replace(
                    sampled_state,
                    regime_belief=posterior,
                    cue_probs=cue_probabilities(cue),
                )
                value, action, used = self._best_physical(
                    branch, max(1, self.depth - 1), compound=False
                )
                cue_actions[cue] = action
                branch_total += float(probability) * value
                nodes += used
            instrumental = immediate + 0.90 * branch_total
            model_action = int(Action.SAMPLE)
        else:
            instrumental = 0.0
            for cue, probability in enumerate(probabilities):
                posterior = posterior_for_cue(prior, cue, accuracy)
                branch = replace(
                    state,
                    regime_belief=posterior,
                    cue_probs=cue_probabilities(cue),
                )
                value, action, used = self._best_physical(
                    branch, self.depth, compound=True
                )
                cue_actions[cue] = action
                instrumental += float(probability) * value
                nodes += used
            model_action = 4 + int(cue_actions[0])
        return float(instrumental), float(information), cue_actions, model_action, nodes

    def decide(
        self,
        *,
        body_state: BodyState,
        rng: np.random.Generator,
        **_: Any,
    ) -> PlanDecision:
        plan_scores = np.full(PLAN_CHOICES, -1.0e9)
        action_scores = np.full(MODEL_ACTIONS, -1.0e9)
        information_values = np.zeros(MODEL_ACTIONS)
        nodes = 0
        for physical in PHYSICAL_ACTIONS:
            value, _action, used = self._physical_plan(
                body_state, physical, self.depth, compound=False
            )
            plan_scores[physical] = value
            action_scores[physical] = value
            nodes += used
        sense_instrumental = float("-inf")
        information = 0.0
        cue_actions = np.zeros(4, dtype=np.int8)
        sense_model_action = int(Action.SAMPLE)
        if not self.sample_lesion:
            (
                sense_instrumental,
                information,
                cue_actions,
                sense_model_action,
                used,
            ) = self._sense_plan(body_state)
            nodes += used
            plan_scores[3] = (
                sense_instrumental + self.epistemic_coefficient * information
            )
            action_scores[sense_model_action] = plan_scores[3]
            information_values[sense_model_action] = information
        plan_probability = _softmax(plan_scores, self.config.policy_precision)
        choice = _sample(plan_probability, rng)
        model_probability = np.zeros(MODEL_ACTIONS)
        model_probability[:3] = plan_probability[:3]
        model_probability[sense_model_action] += plan_probability[3]
        if choice == 3:
            contingency = float(len(set(int(value) for value in cue_actions[1:])) > 1)
            return PlanDecision(
                sense=1,
                physical_action=int(Action.WAIT),
                model_action=sense_model_action,
                cue_actions=cue_actions,
                plan_scores=plan_scores,
                action_scores=action_scores,
                information_values=information_values,
                action_probabilities=model_probability,
                posterior=body_state.regime_belief.copy(),
                model_weights=self.weights.copy(),
                instrumental_value=sense_instrumental,
                epistemic_value=(self.epistemic_coefficient * information),
                policy_contingency=contingency if self.contingent else 0.0,
                planning_nodes=nodes,
            )
        return PlanDecision(
            sense=0,
            physical_action=int(choice),
            model_action=int(choice),
            cue_actions=np.full(4, int(choice), dtype=np.int8),
            plan_scores=plan_scores,
            action_scores=action_scores,
            information_values=information_values,
            action_probabilities=model_probability,
            posterior=body_state.regime_belief.copy(),
            model_weights=self.weights.copy(),
            instrumental_value=float(plan_scores[choice]),
            epistemic_value=0.0,
            policy_contingency=0.0,
            planning_nodes=nodes,
        )

    def observe(self, **_: Any) -> None:
        return None


def exact_multiset_yoke(
    actions: NDArray[np.integer], seed: int
) -> NDArray[np.int8]:
    values = np.asarray(actions, dtype=np.int8).copy()
    return values[np.random.default_rng(seed).permutation(len(values))]
