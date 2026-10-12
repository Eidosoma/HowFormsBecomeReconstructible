from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np
from numpy.typing import NDArray

from fep_ph18.controllers import (
    AlwaysSenseReflex,
    NoopController,
    PlanDecision,
    ReactiveController,
    TrueRegimeOracle,
)
from fep_ph18.hybrid_model import (
    cue_distribution,
    entropy,
    expected_regime_information,
    posterior_for_cue,
    predicted_regime_prior,
)
from fep_ph18.state import BodyState, cue_probabilities

from .causal_pomdp import ExactCausalPOMDP
from .config import MODEL_ACTIONS, ExperimentConfig
from .recurrent_model import RecurrentModel
from .types import Action, ConditionSpec, InformationArm, SensingTiming


PLAN_CHOICES = 4
PHYSICAL_ACTIONS = (0, 1, 2)


def _model_action_cost(config: ExperimentConfig, action: int) -> float:
    value = int(action)
    if value == int(Action.SAMPLE):
        return float(config.action_cost_sample)
    if value in (int(Action.ADAPT_A), int(Action.ADAPT_B)):
        return float(config.action_cost_uptake)
    if value >= 4:
        physical = value - 4
        return float(config.action_cost_sample) + (
            float(config.action_cost_uptake)
            if physical in (int(Action.ADAPT_A), int(Action.ADAPT_B))
            else 0.0
        )
    return 0.0


def _softmax(values: NDArray[np.floating], precision: float) -> NDArray[np.float64]:
    scores = float(precision) * np.asarray(values, dtype=np.float64)
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


def _reflex_action(cue: int) -> int:
    return 1 if int(cue) == 1 else 2 if int(cue) == 2 else 0


def _information(
    config: ExperimentConfig, condition: ConditionSpec, state: BodyState
) -> float:
    transition = condition.sensing_timing == SensingTiming.DELAYED
    accuracy = (
        config.informative_sample_accuracy
        if condition.information_arm == InformationArm.INFORMATIVE
        else config.sham_sample_accuracy
    )
    sensed = expected_regime_information(
        state.regime_belief,
        condition.switch_probability,
        0.05,
        accuracy,
        transition=transition,
    )
    passive = expected_regime_information(
        state.regime_belief,
        condition.switch_probability,
        0.05,
        config.passive_cue_accuracy,
        transition=transition,
    )
    return max(0.0, sensed - passive)


class ExactPlanner:
    def __init__(
        self,
        model: ExactCausalPOMDP,
        config: ExperimentConfig,
        condition: ConditionSpec,
        *,
        epistemic_coefficient: float,
        sensing_lesion: bool = False,
        forced_schedule: NDArray[np.bool_] | None = None,
    ) -> None:
        self.model = model
        self.config = config
        self.condition = condition
        self.epistemic_coefficient = float(epistemic_coefficient)
        self.sensing_lesion = bool(sensing_lesion)
        self.forced_schedule = (
            None
            if forced_schedule is None
            else np.asarray(forced_schedule, dtype=bool).copy()
        )

    def reset(self) -> None:
        return None

    def _accuracy(self) -> float:
        return float(
            self.config.informative_sample_accuracy
            if self.condition.information_arm == InformationArm.INFORMATIVE
            else self.config.sham_sample_accuracy
        )

    def _sense_plan(
        self, state: BodyState
    ) -> tuple[float, NDArray[np.int8], int]:
        transition = self.condition.sensing_timing == SensingTiming.DELAYED
        prior = (
            predicted_regime_prior(
                state.regime_belief, self.condition.switch_probability, 0.05
            )
            if transition
            else np.asarray(state.regime_belief, dtype=np.float64)
        )
        probability = cue_distribution(prior, self._accuracy())
        cue_actions = np.zeros(4, dtype=np.int8)
        branch_value = 0.0
        for cue, weight in enumerate(probability):
            posterior = posterior_for_cue(prior, cue, self._accuracy())
            branch = replace(
                state,
                regime_belief=posterior,
                cue_probs=cue_probabilities(cue),
            )
            value, action = self.model.best_physical_action(
                branch,
                self.condition,
                self.config,
                compound=not transition,
            )
            cue_actions[cue] = action
            branch_value += float(weight) * value
        if transition:
            sample = self.model.action_value(
                state,
                self.condition,
                int(Action.SAMPLE),
                self.config,
                depth=1,
            )
            branch_value = sample + 0.90 * branch_value
            model_action = int(Action.SAMPLE)
        else:
            model_action = 4 + int(cue_actions[0])
        return float(branch_value), cue_actions, model_action

    def decide(
        self,
        *,
        body_state: BodyState,
        rng: np.random.Generator,
        step: int = 0,
        **_: Any,
    ) -> PlanDecision:
        plan_scores = np.full(PLAN_CHOICES, -1.0e9, dtype=np.float64)
        action_scores = np.full(MODEL_ACTIONS, -1.0e9, dtype=np.float64)
        information_values = np.zeros(MODEL_ACTIONS, dtype=np.float64)
        for physical in PHYSICAL_ACTIONS:
            value = self.model.action_value(
                body_state, self.condition, physical, self.config
            )
            plan_scores[physical] = value
            action_scores[physical] = value
        cue_actions = np.zeros(4, dtype=np.int8)
        sense_model_action = int(Action.SAMPLE)
        information = 0.0
        sense_instrumental = float("-inf")
        if not self.sensing_lesion:
            sense_instrumental, cue_actions, sense_model_action = self._sense_plan(body_state)
            information = _information(self.config, self.condition, body_state)
            plan_scores[3] = sense_instrumental + self.epistemic_coefficient * information
            action_scores[sense_model_action] = plan_scores[3]
            information_values[sense_model_action] = information
        probabilities = _softmax(plan_scores, self.config.policy_precision)
        forced: bool | None = None
        if self.forced_schedule is not None and int(step) < len(self.forced_schedule):
            forced = bool(self.forced_schedule[int(step)])
        choice = (
            3
            if forced is True
            else int(np.argmax(plan_scores[:3]))
            if forced is False
            else _sample(probabilities, rng)
        )
        model_probability = np.zeros(MODEL_ACTIONS, dtype=np.float64)
        model_probability[:3] = probabilities[:3]
        model_probability[sense_model_action] += probabilities[3]
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
                model_weights=np.asarray([], dtype=np.float64),
                instrumental_value=sense_instrumental,
                epistemic_value=self.epistemic_coefficient * information,
                policy_contingency=contingency,
                planning_nodes=MODEL_ACTIONS,
            )
        return PlanDecision(
            sense=0,
            physical_action=choice,
            model_action=choice,
            cue_actions=np.full(4, choice, dtype=np.int8),
            plan_scores=plan_scores,
            action_scores=action_scores,
            information_values=information_values,
            action_probabilities=model_probability,
            posterior=body_state.regime_belief.copy(),
            model_weights=np.asarray([], dtype=np.float64),
            instrumental_value=float(plan_scores[choice]),
            epistemic_value=0.0,
            planning_nodes=MODEL_ACTIONS,
        )

    def commit(self, **_: Any) -> None:
        return None

    def observe(self, **_: Any) -> None:
        return None


class EntropyThresholdController(NoopController):
    def __init__(self, config: ExperimentConfig, condition: ConditionSpec) -> None:
        self.config = config
        self.condition = condition

    def decide(self, *, body_state: BodyState, **_: Any) -> PlanDecision:
        cue_actions = np.asarray([_reflex_action(cue) for cue in range(4)], dtype=np.int8)
        should_sense = entropy(body_state.regime_belief) / np.log(3.0) >= self.config.entropy_threshold
        if not should_sense:
            action = _reflex_action(int(np.argmax(body_state.cue_probs)))
            probability = np.zeros(MODEL_ACTIONS)
            probability[action] = 1.0
            return PlanDecision(
                sense=0,
                physical_action=action,
                model_action=action,
                cue_actions=np.full(4, action, dtype=np.int8),
                plan_scores=np.asarray((1.0, 0.0, 0.0, 0.0)),
                action_scores=np.zeros(MODEL_ACTIONS),
                information_values=np.zeros(MODEL_ACTIONS),
                action_probabilities=probability,
                posterior=body_state.regime_belief.copy(),
                model_weights=np.asarray([], dtype=np.float64),
            )
        timing = self.condition.sensing_timing
        model_action = 3 if timing == SensingTiming.DELAYED else 4
        probability = np.zeros(MODEL_ACTIONS)
        probability[model_action] = 1.0
        return PlanDecision(
            sense=1,
            physical_action=int(Action.WAIT),
            model_action=model_action,
            cue_actions=cue_actions,
            plan_scores=np.asarray((0.0, 0.0, 0.0, 1.0)),
            action_scores=np.zeros(MODEL_ACTIONS),
            information_values=np.zeros(MODEL_ACTIONS),
            action_probabilities=probability,
            posterior=body_state.regime_belief.copy(),
            model_weights=np.asarray([], dtype=np.float64),
            policy_contingency=1.0,
        )


class RecurrentPlanner:
    def __init__(
        self,
        model: RecurrentModel,
        config: ExperimentConfig,
        condition: ConditionSpec,
        *,
        epistemic_coefficient: float,
    ) -> None:
        self.model = model
        self.config = config
        self.condition = condition
        self.epistemic_coefficient = float(epistemic_coefficient)
        self.hidden = model.initial_hidden()

    def reset(self) -> None:
        self.hidden = self.model.initial_hidden()

    def _score(
        self, outputs: NDArray[np.float64], action: int
    ) -> float:
        return float(
            outputs[int(action), 0]
            + 0.15 * outputs[int(action), 1]
            - self.config.action_cost_weight
            * _model_action_cost(self.config, int(action))
        )

    def _sense_plan(
        self, state: BodyState
    ) -> tuple[float, NDArray[np.int8], int]:
        transition = self.condition.sensing_timing == SensingTiming.DELAYED
        accuracy = (
            self.config.informative_sample_accuracy
            if self.condition.information_arm == InformationArm.INFORMATIVE
            else self.config.sham_sample_accuracy
        )
        prior = (
            predicted_regime_prior(
                state.regime_belief, self.condition.switch_probability, 0.05
            )
            if transition
            else state.regime_belief
        )
        probabilities = cue_distribution(prior, accuracy)
        actions = np.zeros(4, dtype=np.int8)
        total = 0.0
        for cue, weight in enumerate(probabilities):
            branch = replace(
                state,
                regime_belief=posterior_for_cue(prior, cue, accuracy),
                cue_probs=cue_probabilities(cue),
            )
            _following, outputs = self.model.predict_all(
                self.hidden, branch, self.condition
            )
            offset = 0 if transition else 4
            scored = [(self._score(outputs, offset + action), action) for action in PHYSICAL_ACTIONS]
            value, action = max(scored, key=lambda item: (item[0], -item[1]))
            actions[cue] = action
            total += float(weight) * value
        model_action = int(Action.SAMPLE) if transition else 4 + int(actions[0])
        if transition:
            _following, outputs = self.model.predict_all(
                self.hidden, state, self.condition
            )
            total = self._score(outputs, int(Action.SAMPLE)) + 0.90 * total
        return float(total), actions, model_action

    def decide(
        self,
        *,
        body_state: BodyState,
        rng: np.random.Generator,
        **_: Any,
    ) -> PlanDecision:
        _following, outputs = self.model.predict_all(
            self.hidden, body_state, self.condition
        )
        plan_scores = np.full(4, -1.0e9)
        action_scores = np.full(MODEL_ACTIONS, -1.0e9)
        for action in PHYSICAL_ACTIONS:
            plan_scores[action] = self._score(outputs, action)
            action_scores[action] = plan_scores[action]
        instrumental, cue_actions, model_action = self._sense_plan(body_state)
        information = _information(self.config, self.condition, body_state)
        plan_scores[3] = instrumental + self.epistemic_coefficient * information
        action_scores[model_action] = plan_scores[3]
        information_values = np.zeros(MODEL_ACTIONS)
        information_values[model_action] = information
        probabilities = _softmax(plan_scores, self.config.policy_precision)
        choice = _sample(probabilities, rng)
        model_probability = np.zeros(MODEL_ACTIONS)
        model_probability[:3] = probabilities[:3]
        model_probability[model_action] += probabilities[3]
        if choice == 3:
            return PlanDecision(
                sense=1,
                physical_action=0,
                model_action=model_action,
                cue_actions=cue_actions,
                plan_scores=plan_scores,
                action_scores=action_scores,
                information_values=information_values,
                action_probabilities=model_probability,
                posterior=body_state.regime_belief.copy(),
                model_weights=np.full(self.model.members, 1.0 / self.model.members),
                instrumental_value=instrumental,
                epistemic_value=self.epistemic_coefficient * information,
                policy_contingency=float(len(set(int(v) for v in cue_actions[1:])) > 1),
                planning_nodes=MODEL_ACTIONS,
            )
        return PlanDecision(
            sense=0,
            physical_action=choice,
            model_action=choice,
            cue_actions=np.full(4, choice, dtype=np.int8),
            plan_scores=plan_scores,
            action_scores=action_scores,
            information_values=information_values,
            action_probabilities=model_probability,
            posterior=body_state.regime_belief.copy(),
            model_weights=np.full(self.model.members, 1.0 / self.model.members),
            instrumental_value=float(plan_scores[choice]),
            epistemic_value=0.0,
            planning_nodes=MODEL_ACTIONS,
        )

    def commit(
        self,
        *,
        body_state: BodyState,
        **_: Any,
    ) -> None:
        self.hidden, _outputs = self.model.predict_all(
            self.hidden, body_state, self.condition
        )

    def observe(self, **_: Any) -> None:
        return None


__all__ = (
    "AlwaysSenseReflex",
    "EntropyThresholdController",
    "ExactPlanner",
    "NoopController",
    "PlanDecision",
    "ReactiveController",
    "RecurrentPlanner",
    "TrueRegimeOracle",
)
