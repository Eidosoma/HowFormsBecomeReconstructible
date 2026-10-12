from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from numpy.typing import NDArray

from fep_lab.reference import softmax
from fep_lab.types import CategoricalModel, InferenceResult, PolicyResult


def _entropy_rows(probabilities: NDArray[np.float64]) -> NDArray[np.float64]:
    values = np.asarray(probabilities, dtype=np.float64)
    terms = np.zeros_like(values)
    positive = values > 0.0
    terms[positive] = values[positive] * np.log(values[positive])
    return -terms.sum(axis=1)


@dataclass
class FastInferenceBackend:
    model: CategoricalModel
    costs: NDArray[np.float64]

    def __post_init__(self) -> None:
        self.model.validate()
        self.costs = np.asarray(self.costs, dtype=np.float64)
        if self.costs.shape != (self.model.n_actions,) or np.any(self.costs < 0.0):
            raise ValueError("action costs must be one nonnegative value per action")
        self._transition_by_step = tuple(
            np.transpose(self.model.B[:, :, self.model.policies[:, step]], (2, 0, 1))
            for step in range(self.model.horizon)
        )
        self._likelihood_entropy = tuple(_entropy_rows(value.T) for value in self.model.A)
        self._policy_cost = self.costs[self.model.policies].sum(axis=1)
        self._policy_prior = self.model.policy_prior if self.model.policy_prior is not None else np.full(len(self.model.policies), 1.0 / len(self.model.policies))

    def infer_states(
        self, observation: Sequence[int], predictive_prior: NDArray[np.float64]
    ) -> InferenceResult:
        prior = np.asarray(predictive_prior, dtype=np.float64)
        likelihood = np.ones(self.model.n_states, dtype=np.float64)
        for modality, observed in zip(self.model.A, observation, strict=True):
            likelihood *= modality[int(observed)]
        unnormalized = prior * likelihood
        evidence = float(unnormalized.sum())
        if evidence <= 0.0 or not np.isfinite(evidence):
            raise ValueError("observation has zero or non-finite evidence")
        posterior = unnormalized / evidence
        safe = np.finfo(np.float64).tiny
        vfe = float(np.sum(posterior * (np.log(np.maximum(posterior, safe)) - np.log(np.maximum(prior, safe)) - np.log(np.maximum(likelihood, safe)))))
        return InferenceResult(posterior, prior.copy(), float(np.log(evidence)), vfe)

    def score_policies(self, posterior: NDArray[np.float64]) -> PolicyResult:
        current = np.broadcast_to(np.asarray(posterior, dtype=np.float64), (len(self.model.policies), self.model.n_states)).copy()
        utility = np.zeros(len(self.model.policies), dtype=np.float64)
        information = np.zeros_like(utility)
        for transition in self._transition_by_step:
            current = np.einsum("pij,pj->pi", transition, current)
            for likelihood, preference, likelihood_entropy in zip(self.model.A, self.model.C, self._likelihood_entropy, strict=True):
                predicted = current @ likelihood.T
                if self.model.use_utility:
                    utility += predicted @ preference
                if self.model.use_states_info_gain:
                    information += _entropy_rows(predicted) - current @ likelihood_entropy
        adjusted = utility + information - self._policy_cost
        posterior_policy = softmax(
            self.model.gamma * adjusted
            + np.log(np.maximum(self._policy_prior, np.finfo(np.float64).tiny))
        )
        return PolicyResult(self.model.policies.copy(), utility, information, adjusted, posterior_policy)

    def action_probabilities(self, result: PolicyResult) -> NDArray[np.float64]:
        marginal = np.bincount(result.policies[:, 0], weights=result.posterior, minlength=self.model.n_actions).astype(np.float64)
        return marginal / marginal.sum()

    def sample_action(self, result: PolicyResult, rng: np.random.Generator) -> int:
        probability = self.action_probabilities(result)
        draw = float(rng.random())
        return int(np.searchsorted(np.cumsum(probability), draw, side="right").clip(max=self.model.n_actions - 1))

    def predictive_prior(self, posterior: NDArray[np.float64], action: int) -> NDArray[np.float64]:
        return self.model.B[:, :, int(action)] @ np.asarray(posterior, dtype=np.float64)

