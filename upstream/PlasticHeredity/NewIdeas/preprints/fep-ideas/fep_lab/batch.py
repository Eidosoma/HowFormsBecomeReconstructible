from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .homeostat import build_homeostat_model
from .pymdp_backend import PymdpBackend
from .simulation import ControllerName, agent_model_for_controller, oracle_policy
from .types import Action, Reservoir


@dataclass(frozen=True)
class BatchTrace:
    states: np.ndarray
    observations: np.ndarray
    beliefs: np.ndarray
    predictive_priors: np.ndarray
    vfe: np.ndarray
    log_evidence: np.ndarray
    expected_utility: np.ndarray
    state_info_gain: np.ndarray
    neg_efe: np.ndarray
    policy_posterior: np.ndarray
    intended_actions: np.ndarray
    executed_actions: np.ndarray
    action_costs: np.ndarray

    def to_arrays(self) -> dict[str, np.ndarray]:
        return {
            "states": self.states,
            "observations": self.observations,
            "beliefs": self.beliefs,
            "predictive_priors": self.predictive_priors,
            "vfe": self.vfe,
            "log_evidence": self.log_evidence,
            "expected_utility": self.expected_utility,
            "state_info_gain": self.state_info_gain,
            "neg_efe": self.neg_efe,
            "policy_posterior": self.policy_posterior,
            "intended_actions": self.intended_actions,
            "executed_actions": self.executed_actions,
            "action_costs": self.action_costs,
        }


def _sample_rows(probabilities: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    values = np.asarray(probabilities, dtype=np.float64)
    if values.ndim != 2:
        raise ValueError("row sampler requires a probability matrix")
    uniforms = rng.random(values.shape[0])
    cumulative = np.cumsum(values, axis=1)
    cumulative[:, -1] = 1.0
    return np.sum(uniforms[:, None] > cumulative, axis=1).astype(np.int64)


def _observe_batch(
    likelihoods: tuple[np.ndarray, ...],
    states: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    return np.stack(
        [_sample_rows(likelihood[:, states].T, rng) for likelihood in likelihoods],
        axis=1,
    )


def _policy_actions(
    policies: np.ndarray,
    q_pi: np.ndarray,
    n_actions: int,
    rng: np.random.Generator,
) -> np.ndarray:
    selector = np.eye(n_actions, dtype=np.float64)[policies[:, 0]]
    marginals = q_pi @ selector
    return _sample_rows(marginals, rng)


def _transition_priors(
    transition: np.ndarray, posteriors: np.ndarray, actions: np.ndarray
) -> np.ndarray:
    selected = np.transpose(transition[:, :, actions], (2, 0, 1))
    return np.einsum("nij,nj->ni", selected, posteriors)


def _log_evidence_batch(
    model: object, observations: np.ndarray, priors: np.ndarray
) -> np.ndarray:
    likelihood = np.ones_like(priors)
    for modality_index, modality in enumerate(model.A):
        likelihood *= modality[observations[:, modality_index], :]
    evidence = np.sum(priors * likelihood, axis=1)
    return np.log(np.maximum(evidence, 1e-300))


def _policy_components_batch(
    model: object, posteriors: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    episodes = len(posteriors)
    policies = model.policies
    utilities = np.zeros((episodes, len(policies)), dtype=np.float64)
    information = np.zeros_like(utilities)
    likelihood_entropies = []
    for likelihood in model.A:
        positive = likelihood > 0.0
        terms = np.zeros_like(likelihood)
        terms[positive] = likelihood[positive] * np.log(likelihood[positive])
        likelihood_entropies.append(-terms.sum(axis=0))
    for policy_index, policy in enumerate(policies):
        predicted = posteriors.copy()
        for action in policy:
            predicted = predicted @ model.B[:, :, int(action)].T
            for modality_index, (likelihood, preference) in enumerate(
                zip(model.A, model.C)
            ):
                predicted_observation = predicted @ likelihood.T
                if model.use_utility:
                    utilities[:, policy_index] += predicted_observation @ preference
                if model.use_states_info_gain:
                    positive = predicted_observation > 0.0
                    log_values = np.zeros_like(predicted_observation)
                    log_values[positive] = np.log(predicted_observation[positive])
                    observation_entropy = -np.sum(
                        np.where(
                            positive,
                            predicted_observation * log_values,
                            0.0,
                        ),
                        axis=1,
                    )
                    expected_likelihood_entropy = (
                        predicted @ likelihood_entropies[modality_index]
                    )
                    information[:, policy_index] += (
                        observation_entropy - expected_likelihood_entropy
                    )
    return utilities, information


def run_batch(
    scenario: str,
    controller: ControllerName,
    backend: PymdpBackend,
    episodes: int,
    steps: int,
    process_seed: int,
    agent_seed: int,
) -> BatchTrace:
    if episodes <= 0 or steps <= 0:
        raise ValueError("episodes and steps must be positive")
    process = build_homeostat_model(scenario, "standard")  # type: ignore[arg-type]
    agent_model = agent_model_for_controller(scenario, controller)
    process_rng = np.random.default_rng(process_seed)
    agent_rng = np.random.default_rng(agent_seed)

    states_now = _sample_rows(np.broadcast_to(process.D, (episodes, process.n_states)), process_rng)
    observations_now = _observe_batch(process.A, states_now, process_rng)
    priors_now = np.broadcast_to(agent_model.D, (episodes, agent_model.n_states)).copy()

    states = np.empty((episodes, steps), dtype=np.int16)
    observations = np.empty((episodes, steps, len(process.A)), dtype=np.int8)
    beliefs = np.empty((episodes, steps, agent_model.n_states), dtype=np.float64)
    priors = np.empty_like(beliefs)
    vfe = np.empty((episodes, steps), dtype=np.float64)
    log_evidence = np.empty((episodes, steps), dtype=np.float64)
    expected_utility = np.empty((episodes, steps, len(agent_model.policies)), dtype=np.float64)
    state_info_gain = np.empty_like(expected_utility)
    neg_efe = np.empty((episodes, steps, len(agent_model.policies)), dtype=np.float64)
    q_pi = np.empty_like(neg_efe)
    intended_actions = np.empty((episodes, steps), dtype=np.int8)
    executed_actions = np.empty_like(intended_actions)
    action_costs = np.empty((episodes, steps), dtype=np.float64)

    for timestep in range(steps):
        posterior, timestep_vfe = backend.infer_states_batch(
            agent_model, observations_now, priors_now
        )
        timestep_q_pi, timestep_neg_efe = backend.score_policies_batch(
            agent_model, posterior
        )
        timestep_utility, timestep_information = _policy_components_batch(
            agent_model, posterior
        )
        if controller == "random":
            intended = agent_rng.integers(0, agent_model.n_actions, size=episodes)
        elif controller == "fixed_feedback":
            reservoir_observation = observations_now[:, 1]
            intended = np.full(episodes, int(Action.WAIT), dtype=np.int64)
            intended[reservoir_observation == int(Reservoir.DEPLETED)] = int(Action.ADMIT)
            intended[reservoir_observation == int(Reservoir.OVERLOADED)] = int(Action.EXPEL)
        elif controller == "no_op":
            intended = np.full(episodes, int(Action.WAIT), dtype=np.int64)
        elif controller == "oracle":
            intended = oracle_policy(scenario)[states_now]
        else:
            intended = _policy_actions(
                agent_model.policies,
                timestep_q_pi,
                agent_model.n_actions,
                agent_rng,
            )
        executed = (
            np.full(episodes, int(Action.WAIT), dtype=np.int64)
            if controller == "action_lesion"
            else intended
        )

        states[:, timestep] = states_now
        observations[:, timestep] = observations_now
        beliefs[:, timestep] = posterior
        priors[:, timestep] = priors_now
        vfe[:, timestep] = timestep_vfe
        log_evidence[:, timestep] = _log_evidence_batch(
            agent_model, observations_now, priors_now
        )
        expected_utility[:, timestep] = timestep_utility
        state_info_gain[:, timestep] = timestep_information
        neg_efe[:, timestep] = timestep_neg_efe
        q_pi[:, timestep] = timestep_q_pi
        intended_actions[:, timestep] = intended
        executed_actions[:, timestep] = executed
        action_costs[:, timestep] = np.where(executed == int(Action.SAMPLE), 0.15, 0.0)

        process_probabilities = np.transpose(
            process.B[:, states_now, executed], (1, 0)
        )
        states_now = _sample_rows(process_probabilities, process_rng)
        observations_now = _observe_batch(process.A, states_now, process_rng)
        believed_actions = intended if controller == "action_lesion" else executed
        priors_now = _transition_priors(agent_model.B, posterior, believed_actions)

    return BatchTrace(
        states=states,
        observations=observations,
        beliefs=beliefs,
        predictive_priors=priors,
        vfe=vfe,
        log_evidence=log_evidence,
        expected_utility=expected_utility,
        state_info_gain=state_info_gain,
        neg_efe=neg_efe,
        policy_posterior=q_pi,
        intended_actions=intended_actions,
        executed_actions=executed_actions,
        action_costs=action_costs,
    )


def batch_metrics(trace: BatchTrace) -> dict[str, np.ndarray]:
    state_values = np.asarray(trace.states, dtype=np.int64)
    reservoirs = (state_values // 2) % 3
    regimes = state_values // 6
    lean_probability = trace.beliefs[:, :, :6].sum(axis=2)
    true_probability = np.where(regimes == 0, lean_probability, 1.0 - lean_probability)
    entropy = -(
        lean_probability * np.log(np.maximum(lean_probability, 1e-300))
        + (1.0 - lean_probability)
        * np.log(np.maximum(1.0 - lean_probability, 1e-300))
    )
    return {
        "viable_fraction": np.mean(reservoirs == int(Reservoir.VIABLE), axis=1),
        "depleted_fraction": np.mean(reservoirs == int(Reservoir.DEPLETED), axis=1),
        "overloaded_fraction": np.mean(reservoirs == int(Reservoir.OVERLOADED), axis=1),
        "sample_fraction": np.mean(
            trace.executed_actions == int(Action.SAMPLE), axis=1
        ),
        "first_sample": (
            trace.executed_actions[:, 0] == int(Action.SAMPLE)
        ).astype(np.float64),
        "mean_action_cost": np.mean(trace.action_costs, axis=1),
        "regime_log_loss": -np.mean(
            np.log(np.maximum(true_probability, 1e-300)), axis=1
        ),
        "mean_regime_entropy": np.mean(entropy, axis=1),
        "mean_vfe": np.mean(trace.vfe, axis=1),
    }
