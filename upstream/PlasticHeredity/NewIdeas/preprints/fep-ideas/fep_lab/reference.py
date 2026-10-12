from __future__ import annotations

from typing import Sequence

import numpy as np

from .types import CategoricalModel, InferenceResult, PolicyResult

EPSILON = np.finfo(np.float64).tiny


def _safe_log(values: np.ndarray) -> np.ndarray:
    return np.log(np.maximum(np.asarray(values, dtype=np.float64), EPSILON))


def entropy(probabilities: np.ndarray) -> float:
    values = np.asarray(probabilities, dtype=np.float64)
    positive = values > 0.0
    return float(-np.sum(values[positive] * np.log(values[positive])))


def softmax(logits: np.ndarray) -> np.ndarray:
    values = np.asarray(logits, dtype=np.float64)
    shifted = values - np.max(values)
    exponentiated = np.exp(shifted)
    return exponentiated / exponentiated.sum()


class ReferenceBackend:
    """Small, brute-force implementation used as the numerical authority."""

    name = "reference"

    def infer_states(
        self,
        model: CategoricalModel,
        observation: Sequence[int],
        predictive_prior: np.ndarray,
    ) -> InferenceResult:
        if len(observation) != len(model.A):
            raise ValueError("observation has the wrong number of modalities")
        prior = np.asarray(predictive_prior, dtype=np.float64)
        if prior.shape != (model.n_states,):
            raise ValueError("predictive prior has the wrong shape")
        likelihood = np.ones(model.n_states, dtype=np.float64)
        for modality, observed in zip(model.A, observation):
            if not 0 <= int(observed) < modality.shape[0]:
                raise ValueError("observation category is out of range")
            likelihood *= modality[int(observed), :]
        unnormalized = prior * likelihood
        evidence = float(unnormalized.sum())
        if evidence <= 0.0 or not np.isfinite(evidence):
            raise ValueError("observation has zero or non-finite evidence")
        posterior = unnormalized / evidence
        vfe = float(
            np.sum(
                posterior
                * (
                    _safe_log(posterior)
                    - _safe_log(prior)
                    - _safe_log(likelihood)
                )
            )
        )
        return InferenceResult(
            posterior=posterior,
            predictive_prior=prior.copy(),
            log_evidence=float(np.log(evidence)),
            vfe=vfe,
        )

    def score_policies(
        self, model: CategoricalModel, posterior: np.ndarray
    ) -> PolicyResult:
        current = np.asarray(posterior, dtype=np.float64)
        if current.shape != (model.n_states,):
            raise ValueError("posterior has the wrong shape")
        utilities = np.zeros(len(model.policies), dtype=np.float64)
        information = np.zeros(len(model.policies), dtype=np.float64)
        for policy_index, policy in enumerate(model.policies):
            predicted = current.copy()
            for action in policy:
                predicted = model.B[:, :, int(action)] @ predicted
                for likelihood, preference in zip(model.A, model.C):
                    predicted_observation = likelihood @ predicted
                    if model.use_utility:
                        utilities[policy_index] += float(
                            predicted_observation @ preference
                        )
                    if model.use_states_info_gain:
                        expected_likelihood_entropy = float(
                            predicted
                            @ np.asarray(
                                [entropy(likelihood[:, state]) for state in range(model.n_states)]
                            )
                        )
                        information[policy_index] += (
                            entropy(predicted_observation) - expected_likelihood_entropy
                        )
        neg_efe = utilities + information
        prior = (
            model.policy_prior
            if model.policy_prior is not None
            else np.full(len(model.policies), 1.0 / len(model.policies))
        )
        q_pi = softmax(model.gamma * neg_efe + _safe_log(prior))
        return PolicyResult(
            policies=model.policies.copy(),
            expected_utility=utilities,
            state_info_gain=information,
            neg_efe=neg_efe,
            posterior=q_pi,
        )

    def sample_action(
        self,
        result: PolicyResult,
        n_actions: int,
        rng: np.random.Generator,
    ) -> int:
        marginal = np.bincount(
            result.policies[:, 0], weights=result.posterior, minlength=n_actions
        ).astype(np.float64)
        marginal /= marginal.sum()
        return int(rng.choice(n_actions, p=marginal))

    @staticmethod
    def predictive_prior(
        model: CategoricalModel, posterior: np.ndarray, action: int
    ) -> np.ndarray:
        return model.B[:, :, int(action)] @ np.asarray(posterior, dtype=np.float64)


def variational_free_energy(
    q: np.ndarray,
    prior: np.ndarray,
    likelihood: np.ndarray,
) -> float:
    distribution = np.asarray(q, dtype=np.float64)
    return float(
        np.sum(
            distribution
            * (
                _safe_log(distribution)
                - _safe_log(np.asarray(prior, dtype=np.float64))
                - _safe_log(np.asarray(likelihood, dtype=np.float64))
            )
        )
    )
