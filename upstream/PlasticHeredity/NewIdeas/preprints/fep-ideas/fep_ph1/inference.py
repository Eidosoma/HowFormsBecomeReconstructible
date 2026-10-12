from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from numpy.typing import NDArray

from fep_lab.reference import softmax
from fep_lab.types import CategoricalModel, InferenceResult, PolicyResult

from .config import ExperimentConfig
from .models import action_costs


def _entropy_rows(probabilities: NDArray[np.float64]) -> NDArray[np.float64]:
    values = np.asarray(probabilities, dtype=np.float64)
    positive = values > 0.0
    terms = np.zeros_like(values)
    terms[positive] = values[positive] * np.log(values[positive])
    return -terms.sum(axis=1)


@dataclass
class FastInferenceBackend:
    """Vectorized algebraic equivalent of the independent reference scorer."""

    model: CategoricalModel
    config: ExperimentConfig

    def __post_init__(self) -> None:
        self.model.validate()
        self._transition_by_step = tuple(
            np.transpose(self.model.B[:, :, self.model.policies[:, step]], (2, 0, 1))
            for step in range(self.model.horizon)
        )
        self._likelihood_entropy = tuple(
            _entropy_rows(likelihood.T) for likelihood in self.model.A
        )
        costs = action_costs(self.config)
        self._policy_cost = costs[self.model.policies].sum(axis=1)
        self._policy_prior = (
            self.model.policy_prior
            if self.model.policy_prior is not None
            else np.full(len(self.model.policies), 1.0 / len(self.model.policies))
        )

    def infer_states(
        self, observation: Sequence[int], predictive_prior: NDArray[np.float64]
    ) -> InferenceResult:
        prior = np.asarray(predictive_prior, dtype=np.float64)
        if prior.shape != (self.model.n_states,):
            raise ValueError("predictive prior has the wrong shape")
        likelihood = np.ones(self.model.n_states, dtype=np.float64)
        for modality, observed in zip(self.model.A, observation, strict=True):
            likelihood *= modality[int(observed)]
        unnormalized = prior * likelihood
        evidence = float(unnormalized.sum())
        if evidence <= 0.0 or not np.isfinite(evidence):
            raise ValueError("observation has zero or non-finite evidence")
        posterior = unnormalized / evidence
        safe = np.finfo(np.float64).tiny
        vfe = float(
            np.sum(
                posterior
                * (
                    np.log(np.maximum(posterior, safe))
                    - np.log(np.maximum(prior, safe))
                    - np.log(np.maximum(likelihood, safe))
                )
            )
        )
        return InferenceResult(
            posterior=posterior,
            predictive_prior=prior.copy(),
            log_evidence=float(np.log(evidence)),
            vfe=vfe,
        )

    def score_policies(self, posterior: NDArray[np.float64]) -> PolicyResult:
        current = np.broadcast_to(
            np.asarray(posterior, dtype=np.float64),
            (len(self.model.policies), self.model.n_states),
        ).copy()
        utility = np.zeros(len(self.model.policies), dtype=np.float64)
        information = np.zeros_like(utility)
        for transition in self._transition_by_step:
            current = np.einsum("pij,pj->pi", transition, current)
            for likelihood, preference, likelihood_entropy in zip(
                self.model.A,
                self.model.C,
                self._likelihood_entropy,
                strict=True,
            ):
                predicted_observation = current @ likelihood.T
                if self.model.use_utility:
                    utility += predicted_observation @ preference
                if self.model.use_states_info_gain:
                    information += _entropy_rows(predicted_observation) - (
                        current @ likelihood_entropy
                    )
        adjusted = utility + information - self._policy_cost
        q_pi = softmax(
            self.model.gamma * adjusted
            + np.log(np.maximum(self._policy_prior, np.finfo(np.float64).tiny))
        )
        return PolicyResult(
            policies=self.model.policies.copy(),
            expected_utility=utility,
            state_info_gain=information,
            neg_efe=adjusted,
            posterior=q_pi,
        )

    def sample_action(self, result: PolicyResult, rng: np.random.Generator) -> int:
        marginal = np.bincount(
            result.policies[:, 0],
            weights=result.posterior,
            minlength=self.model.n_actions,
        ).astype(np.float64)
        marginal /= marginal.sum()
        return int(rng.choice(self.model.n_actions, p=marginal))

    def predictive_prior(
        self, posterior: NDArray[np.float64], action: int
    ) -> NDArray[np.float64]:
        return self.model.B[:, :, int(action)] @ np.asarray(posterior, dtype=np.float64)

