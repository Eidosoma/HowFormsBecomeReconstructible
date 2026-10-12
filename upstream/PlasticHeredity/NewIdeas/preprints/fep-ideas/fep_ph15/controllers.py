from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from fep_lab.types import CategoricalModel

from .inference import FastInferenceBackend
from .types import Action, ControllerDecision, ExternalRegime


def _empty_decision(action: int, prior: NDArray[np.float64]) -> ControllerDecision:
    values = np.full(16, np.nan, dtype=np.float64)
    return ControllerDecision(
        int(action), np.asarray(prior, dtype=np.float64).copy(),
        np.asarray(prior, dtype=np.float64).copy(), float("nan"), float("nan"),
        values.copy(), values.copy(), values.copy(), np.full(16, 1.0 / 16.0),
    )


class ActiveInferenceController:
    def __init__(
        self,
        model: CategoricalModel,
        costs: NDArray[np.float64],
        *,
        sensory_lesion: bool = False,
        true_regime_planner: bool = False,
    ) -> None:
        self.model = model
        self.backend = FastInferenceBackend(model, costs)
        self.initial = model.D.copy()
        self.prior = self.initial.copy()
        self.sensory_lesion = sensory_lesion
        self.true_regime_planner = true_regime_planner

    def reset(self) -> None:
        self.prior = self.initial.copy()

    def decide(
        self,
        observation: tuple[int, ...],
        true_regime: int | None,
        rng: np.random.Generator,
    ) -> ControllerDecision:
        values = tuple(int(value) for value in observation)
        if self.sensory_lesion:
            values = (values[0], values[1], 1, 0)
        inferred = self.backend.infer_states(values, self.prior)
        posterior = inferred.posterior.copy()
        if self.true_regime_planner:
            if true_regime is None:
                raise ValueError("oracle planner requires the true external regime")
            mask = np.zeros_like(posterior)
            mask[3 * int(true_regime) : 3 * int(true_regime) + 3] = 1.0
            posterior *= mask
            total = float(posterior.sum())
            posterior = posterior / total if total > 0.0 else mask / mask.sum()
        policy = self.backend.score_policies(posterior)
        action = self.backend.sample_action(policy, rng)
        return ControllerDecision(
            action, posterior, inferred.predictive_prior, inferred.vfe,
            inferred.log_evidence, policy.expected_utility,
            policy.state_info_gain, policy.neg_efe, policy.posterior,
        )

    def advance(self, posterior: NDArray[np.float64], executed_action: int) -> None:
        self.prior = self.backend.predictive_prior(posterior, int(executed_action))


class NoopController:
    def __init__(self, prior: NDArray[np.float64]) -> None:
        self.initial = np.asarray(prior, dtype=np.float64).copy()
        self.prior = self.initial.copy()

    def reset(self) -> None:
        self.prior = self.initial.copy()

    def decide(self, observation: tuple[int, ...], true_regime: int | None, rng: np.random.Generator) -> ControllerDecision:
        del observation, true_regime, rng
        return _empty_decision(int(Action.WAIT), self.prior)

    def advance(self, posterior: NDArray[np.float64], executed_action: int) -> None:
        del posterior, executed_action


class ReactiveController(NoopController):
    def decide(self, observation: tuple[int, ...], true_regime: int | None, rng: np.random.Generator) -> ControllerDecision:
        del true_regime, rng
        cue = int(observation[3])
        action = int(Action.ADAPT_A) if cue == int(ExternalRegime.A) + 1 else int(Action.ADAPT_B) if cue == int(ExternalRegime.B) + 1 else int(Action.WAIT)
        return _empty_decision(action, self.prior)


@dataclass
class ScheduledController(NoopController):
    schedule: NDArray[np.int64]
    initial_prior: NDArray[np.float64]

    def __post_init__(self) -> None:
        NoopController.__init__(self, self.initial_prior)
        self.index = 0

    def reset(self) -> None:
        super().reset()
        self.index = 0

    def decide(self, observation: tuple[int, ...], true_regime: int | None, rng: np.random.Generator) -> ControllerDecision:
        del observation, true_regime, rng
        action = int(self.schedule[self.index]) if self.index < len(self.schedule) else int(Action.WAIT)
        self.index += 1
        return _empty_decision(action, self.prior)


def yoked_random_schedule(actions: NDArray[np.int64], seed: int) -> NDArray[np.int64]:
    values = np.asarray(actions, dtype=np.int64)
    rng = np.random.default_rng(seed)
    output = np.full(values.shape, int(Action.WAIT), dtype=np.int64)
    sample_count = int(np.count_nonzero(values == int(Action.SAMPLE)))
    adapt_count = int(np.count_nonzero((values == int(Action.ADAPT_A)) | (values == int(Action.ADAPT_B))))
    locations = rng.permutation(len(values))
    output[locations[:sample_count]] = int(Action.SAMPLE)
    if adapt_count:
        output[locations[sample_count : sample_count + adapt_count]] = rng.choice(
            (int(Action.ADAPT_A), int(Action.ADAPT_B)), size=adapt_count
        )
    return output

