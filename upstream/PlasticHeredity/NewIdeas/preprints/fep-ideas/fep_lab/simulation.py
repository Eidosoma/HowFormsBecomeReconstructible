from __future__ import annotations

from functools import lru_cache
from typing import Literal

import numpy as np

from .homeostat import HomeostatEnvironment, build_homeostat_model, decode_state
from .reference import ReferenceBackend
from .types import (
    Action,
    CategoricalModel,
    EpisodeTrace,
    InferenceBackend,
    Reservoir,
)

ControllerName = Literal[
    "active_inference",
    "epistemic_lesion",
    "scrambled_likelihood",
    "reversed_preferences",
    "action_lesion",
    "random",
    "fixed_feedback",
    "no_op",
    "oracle",
]

CONTROLLERS: tuple[ControllerName, ...] = (
    "active_inference",
    "epistemic_lesion",
    "scrambled_likelihood",
    "reversed_preferences",
    "action_lesion",
    "random",
    "fixed_feedback",
    "no_op",
    "oracle",
)


def agent_model_for_controller(
    scenario: str, controller: ControllerName
) -> CategoricalModel:
    variant = {
        "epistemic_lesion": "epistemic_lesion",
        "scrambled_likelihood": "scrambled",
        "reversed_preferences": "reversed",
    }.get(controller, "standard")
    return build_homeostat_model(scenario, variant)  # type: ignore[arg-type]


@lru_cache(maxsize=3)
def oracle_policy(scenario: str) -> np.ndarray:
    model = build_homeostat_model(scenario, "standard")  # type: ignore[arg-type]
    rewards = np.zeros((model.n_states, model.n_actions), dtype=np.float64)
    for state in range(model.n_states):
        for action in Action:
            expected_viability = 0.0
            for next_state, probability in enumerate(model.B[:, state, int(action)]):
                _regime, reservoir, _sensor = decode_state(next_state)
                expected_viability += probability * float(reservoir == Reservoir.VIABLE)
            rewards[state, int(action)] = expected_viability - (
                0.15 if action == Action.SAMPLE else 0.0
            )
    value = np.zeros(model.n_states, dtype=np.float64)
    discount = 0.95
    for _ in range(10_000):
        q_values = rewards + discount * np.stack(
            [model.B[:, :, action].T @ value for action in range(model.n_actions)],
            axis=1,
        )
        updated = q_values.max(axis=1)
        if float(np.max(np.abs(updated - value))) < 1e-13:
            value = updated
            break
        value = updated
    else:  # pragma: no cover - contraction should always converge
        raise RuntimeError("oracle value iteration did not converge")
    q_values = rewards + discount * np.stack(
        [model.B[:, :, action].T @ value for action in range(model.n_actions)], axis=1
    )
    return np.argmax(q_values, axis=1).astype(np.int64)


def _controller_action(
    controller: ControllerName,
    observation: tuple[int, ...],
    state: int,
    policy_result: object,
    backend: InferenceBackend,
    model: CategoricalModel,
    rng: np.random.Generator,
    scenario: str,
) -> int:
    if controller == "random":
        return int(rng.integers(0, model.n_actions))
    if controller == "fixed_feedback":
        reservoir_observation = int(observation[1])
        if reservoir_observation == int(Reservoir.DEPLETED):
            return int(Action.ADMIT)
        if reservoir_observation == int(Reservoir.OVERLOADED):
            return int(Action.EXPEL)
        return int(Action.WAIT)
    if controller == "no_op":
        return int(Action.WAIT)
    if controller == "oracle":
        return int(oracle_policy(scenario)[state])
    return backend.sample_action(  # type: ignore[arg-type]
        policy_result, model.n_actions, rng
    )


def run_episode(
    scenario: str,
    controller: ControllerName,
    backend: InferenceBackend,
    steps: int,
    process_seed: int,
    agent_seed: int,
) -> EpisodeTrace:
    if steps <= 0:
        raise ValueError("episode length must be positive")
    environment = HomeostatEnvironment(scenario)  # type: ignore[arg-type]
    model = agent_model_for_controller(scenario, controller)
    process_rng = np.random.default_rng(process_seed)
    agent_rng = np.random.default_rng(agent_seed)
    current = environment.reset(process_rng)
    predictive_prior = model.D.copy()

    states = np.empty(steps, dtype=np.int64)
    observations = np.empty((steps, len(model.A)), dtype=np.int64)
    beliefs = np.empty((steps, model.n_states), dtype=np.float64)
    priors = np.empty_like(beliefs)
    vfe = np.empty(steps, dtype=np.float64)
    log_evidence = np.empty(steps, dtype=np.float64)
    expected_utility = np.empty((steps, len(model.policies)), dtype=np.float64)
    state_info_gain = np.empty_like(expected_utility)
    neg_efe = np.empty_like(expected_utility)
    policy_posterior = np.empty_like(expected_utility)
    intended_actions = np.empty(steps, dtype=np.int64)
    executed_actions = np.empty(steps, dtype=np.int64)
    action_costs = np.empty(steps, dtype=np.float64)

    for timestep in range(steps):
        inference = backend.infer_states(model, current.observation, predictive_prior)
        policies = backend.score_policies(model, inference.posterior)
        intended = _controller_action(
            controller,
            current.observation,
            current.state,
            policies,
            backend,
            model,
            agent_rng,
            scenario,
        )
        executed = int(Action.WAIT) if controller == "action_lesion" else intended

        states[timestep] = current.state
        observations[timestep] = current.observation
        beliefs[timestep] = inference.posterior
        priors[timestep] = inference.predictive_prior
        vfe[timestep] = inference.vfe
        log_evidence[timestep] = inference.log_evidence
        expected_utility[timestep] = policies.expected_utility
        state_info_gain[timestep] = policies.state_info_gain
        neg_efe[timestep] = policies.neg_efe
        policy_posterior[timestep] = policies.posterior
        intended_actions[timestep] = intended
        executed_actions[timestep] = executed

        current = environment.step(current.state, executed, process_rng)
        action_costs[timestep] = current.action_cost
        believed_action = intended if controller == "action_lesion" else executed
        predictive_prior = model.B[:, :, believed_action] @ inference.posterior

    return EpisodeTrace(
        states=states,
        observations=observations,
        beliefs=beliefs,
        predictive_priors=priors,
        vfe=vfe,
        log_evidence=log_evidence,
        expected_utility=expected_utility,
        state_info_gain=state_info_gain,
        neg_efe=neg_efe,
        policy_posterior=policy_posterior,
        intended_actions=intended_actions,
        executed_actions=executed_actions,
        action_costs=action_costs,
    )


def trace_metrics(trace: EpisodeTrace) -> dict[str, float]:
    regimes = np.empty(len(trace.states), dtype=np.int64)
    reservoirs = np.empty(len(trace.states), dtype=np.int64)
    true_regime_probability = np.empty(len(trace.states), dtype=np.float64)
    posterior_entropy = np.empty(len(trace.states), dtype=np.float64)
    for index, state in enumerate(trace.states):
        regime, reservoir, _sensor = decode_state(int(state))
        regimes[index] = int(regime)
        reservoirs[index] = int(reservoir)
        matching = [
            candidate
            for candidate in range(trace.beliefs.shape[1])
            if int(decode_state(candidate)[0]) == int(regime)
        ]
        probability = float(trace.beliefs[index, matching].sum())
        true_regime_probability[index] = probability
        marginal = np.asarray(
            [
                trace.beliefs[index, :6].sum(),
                trace.beliefs[index, 6:].sum(),
            ]
        )
        positive = marginal > 0.0
        posterior_entropy[index] = float(
            -np.sum(marginal[positive] * np.log(marginal[positive]))
        )
    return {
        "viable_fraction": float(np.mean(reservoirs == int(Reservoir.VIABLE))),
        "depleted_fraction": float(np.mean(reservoirs == int(Reservoir.DEPLETED))),
        "overloaded_fraction": float(np.mean(reservoirs == int(Reservoir.OVERLOADED))),
        "sample_fraction": float(np.mean(trace.executed_actions == int(Action.SAMPLE))),
        "mean_action_cost": float(np.mean(trace.action_costs)),
        "regime_log_loss": float(
            -np.mean(np.log(np.maximum(true_regime_probability, 1e-300)))
        ),
        "mean_regime_entropy": float(np.mean(posterior_entropy)),
        "mean_vfe": float(np.mean(trace.vfe)),
    }


def reference_backend() -> ReferenceBackend:
    return ReferenceBackend()
