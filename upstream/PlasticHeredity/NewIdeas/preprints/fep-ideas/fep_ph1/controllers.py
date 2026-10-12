from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from fep_lab.types import CategoricalModel

from .config import ExperimentConfig
from .inference import FastInferenceBackend
from .types import Action, ControllerDecision, ExternalRegime


def _empty_decision(action: int, prior: np.ndarray) -> ControllerDecision:
    policy_values = np.full(16, np.nan, dtype=np.float64)
    return ControllerDecision(
        intended_action=int(action),
        posterior=np.asarray(prior, dtype=np.float64).copy(),
        predictive_prior=np.asarray(prior, dtype=np.float64).copy(),
        vfe=float("nan"),
        log_evidence=float("nan"),
        expected_utility=policy_values.copy(),
        state_information_gain=policy_values.copy(),
        adjusted_neg_efe=policy_values.copy(),
        policy_posterior=np.full(16, 1.0 / 16.0, dtype=np.float64),
    )


class ActiveInferenceController:
    def __init__(
        self,
        model: CategoricalModel,
        config: ExperimentConfig,
        *,
        sensory_lesion: bool = False,
    ) -> None:
        self.model = model
        self.config = config
        self.sensory_lesion = sensory_lesion
        self.backend = FastInferenceBackend(model, config)
        self.prior = model.D.copy()

    def reset(self) -> None:
        self.prior = self.model.D.copy()

    def decide(
        self,
        observation: tuple[int, ...],
        true_regime: int | None,
        rng: np.random.Generator,
    ) -> ControllerDecision:
        del true_regime
        values = tuple(int(value) for value in observation)
        if self.sensory_lesion:
            values = (values[0], values[1], 1, 0)
        inferred = self.backend.infer_states(values, self.prior)
        policy = self.backend.score_policies(inferred.posterior)
        action = self.backend.sample_action(policy, rng)
        return ControllerDecision(
            intended_action=action,
            posterior=inferred.posterior,
            predictive_prior=inferred.predictive_prior,
            vfe=inferred.vfe,
            log_evidence=inferred.log_evidence,
            expected_utility=policy.expected_utility,
            state_information_gain=policy.state_info_gain,
            adjusted_neg_efe=policy.neg_efe,
            policy_posterior=policy.posterior,
        )

    def advance(self, posterior: np.ndarray, executed_action: int) -> None:
        self.prior = self.backend.predictive_prior(posterior, int(executed_action))


class NoopController:
    def __init__(self, prior: np.ndarray) -> None:
        self.initial = np.asarray(prior, dtype=np.float64).copy()
        self.prior = self.initial.copy()

    def reset(self) -> None:
        self.prior = self.initial.copy()

    def decide(
        self,
        observation: tuple[int, ...],
        true_regime: int | None,
        rng: np.random.Generator,
    ) -> ControllerDecision:
        del observation, true_regime, rng
        return _empty_decision(int(Action.WAIT), self.prior)

    def advance(self, posterior: np.ndarray, executed_action: int) -> None:
        del posterior, executed_action


class ReactiveController(NoopController):
    def decide(
        self,
        observation: tuple[int, ...],
        true_regime: int | None,
        rng: np.random.Generator,
    ) -> ControllerDecision:
        del true_regime, rng
        cue = int(observation[3])
        action = (
            Action.ADAPT_A
            if cue == int(ExternalRegime.A) + 1
            else Action.ADAPT_B
            if cue == int(ExternalRegime.B) + 1
            else Action.WAIT
        )
        return _empty_decision(int(action), self.prior)


class OracleController(NoopController):
    def decide(
        self,
        observation: tuple[int, ...],
        true_regime: int | None,
        rng: np.random.Generator,
    ) -> ControllerDecision:
        del observation, rng
        action = (
            Action.ADAPT_A
            if true_regime == int(ExternalRegime.A)
            else Action.ADAPT_B
            if true_regime == int(ExternalRegime.B)
            else Action.WAIT
        )
        return _empty_decision(int(action), self.prior)


@dataclass
class ScheduledController(NoopController):
    schedule: np.ndarray
    initial_prior: np.ndarray

    def __post_init__(self) -> None:
        NoopController.__init__(self, self.initial_prior)
        self.index = 0

    def reset(self) -> None:
        super().reset()
        self.index = 0

    def decide(
        self,
        observation: tuple[int, ...],
        true_regime: int | None,
        rng: np.random.Generator,
    ) -> ControllerDecision:
        del observation, true_regime, rng
        action = (
            int(self.schedule[self.index])
            if self.index < len(self.schedule)
            else int(Action.WAIT)
        )
        self.index += 1
        return _empty_decision(action, self.prior)


def yoked_random_schedule(actions: np.ndarray, seed: int) -> np.ndarray:
    """Preserve counts of sampling and adaptation while randomizing times/directions."""

    values = np.asarray(actions, dtype=np.int64)
    rng = np.random.default_rng(seed)
    schedule = np.full(values.shape, int(Action.WAIT), dtype=np.int64)
    sample_count = int(np.count_nonzero(values == int(Action.SAMPLE)))
    adapt_count = int(
        np.count_nonzero(
            (values == int(Action.ADAPT_A)) | (values == int(Action.ADAPT_B))
        )
    )
    positions = rng.permutation(len(values))
    sample_positions = positions[:sample_count]
    adapt_positions = positions[sample_count : sample_count + adapt_count]
    schedule[sample_positions] = int(Action.SAMPLE)
    if adapt_count:
        schedule[adapt_positions] = rng.choice(
            (int(Action.ADAPT_A), int(Action.ADAPT_B)), size=adapt_count
        )
    return schedule
