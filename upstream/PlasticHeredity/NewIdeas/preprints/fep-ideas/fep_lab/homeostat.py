from __future__ import annotations

from dataclasses import replace
from itertools import product
from typing import Literal

import numpy as np

from .types import (
    Action,
    CategoricalModel,
    NutrientRegime,
    Reservoir,
    SensorMode,
    StepResult,
)

Scenario = Literal["epistemic", "known", "disturbed"]
ModelVariant = Literal["standard", "epistemic_lesion", "scrambled", "reversed"]

N_REGIMES = 2
N_RESERVOIRS = 3
N_SENSOR_MODES = 2
N_STATES = N_REGIMES * N_RESERVOIRS * N_SENSOR_MODES


def state_index(regime: int, reservoir: int, sensor_mode: int) -> int:
    return (int(regime) * N_RESERVOIRS + int(reservoir)) * N_SENSOR_MODES + int(
        sensor_mode
    )


def decode_state(state: int) -> tuple[NutrientRegime, Reservoir, SensorMode]:
    sensor = SensorMode(state % N_SENSOR_MODES)
    quotient = state // N_SENSOR_MODES
    reservoir = Reservoir(quotient % N_RESERVOIRS)
    regime = NutrientRegime(quotient // N_RESERVOIRS)
    return regime, reservoir, sensor


def enumerate_policies(n_actions: int = 4, horizon: int = 2) -> np.ndarray:
    return np.asarray(tuple(product(range(n_actions), repeat=horizon)), dtype=np.int64)


def _initial_distribution(scenario: Scenario) -> np.ndarray:
    value = np.zeros(N_STATES, dtype=np.float64)
    if scenario == "known":
        value[state_index(NutrientRegime.LEAN, Reservoir.VIABLE, SensorMode.PASSIVE)] = 1.0
        return value
    reservoir_weights = (
        np.asarray([0.0, 1.0, 0.0])
        if scenario == "epistemic"
        else np.asarray([0.25, 0.50, 0.25])
    )
    for regime in NutrientRegime:
        for reservoir in Reservoir:
            value[state_index(regime, reservoir, SensorMode.PASSIVE)] = (
                0.5 * reservoir_weights[int(reservoir)]
            )
    return value


def _next_reservoir_distribution(
    reservoir: Reservoir, next_regime: NutrientRegime, action: Action
) -> np.ndarray:
    current = int(reservoir)
    value = np.zeros(N_RESERVOIRS, dtype=np.float64)
    if action == Action.WAIT:
        target = max(0, current - 1)
        value[current] += 0.90
        value[target] += 0.10
    elif action == Action.ADMIT:
        target = min(N_RESERVOIRS - 1, current + 1)
        probability = 0.55 if next_regime == NutrientRegime.LEAN else 0.90
        value[target] += probability
        value[current] += 1.0 - probability
    elif action == Action.EXPEL:
        target = max(0, current - 1)
        value[target] += 0.90
        value[current] += 0.10
    elif action == Action.SAMPLE:
        target = max(0, current - 1)
        value[target] += 0.11
        value[current] += 0.89
    else:  # pragma: no cover - IntEnum conversion normally rejects this first
        raise ValueError(f"unknown action {action}")
    return value


def _transition_model(regime_switch_probability: float = 0.03) -> np.ndarray:
    value = np.zeros((N_STATES, N_STATES, len(Action)), dtype=np.float64)
    for current in range(N_STATES):
        regime, reservoir, _sensor = decode_state(current)
        for action in Action:
            next_sensor = (
                SensorMode.SAMPLING if action == Action.SAMPLE else SensorMode.PASSIVE
            )
            for next_regime in NutrientRegime:
                regime_probability = (
                    1.0 - regime_switch_probability
                    if next_regime == regime
                    else regime_switch_probability
                )
                reservoir_probabilities = _next_reservoir_distribution(
                    reservoir, next_regime, action
                )
                for next_reservoir in Reservoir:
                    target = state_index(next_regime, next_reservoir, next_sensor)
                    value[target, current, int(action)] += (
                        regime_probability * reservoir_probabilities[int(next_reservoir)]
                    )
    return value


def _likelihood_model() -> tuple[np.ndarray, np.ndarray]:
    nutrient = np.zeros((3, N_STATES), dtype=np.float64)
    reservoir_obs = np.full((3, N_STATES), 0.05, dtype=np.float64)
    for state in range(N_STATES):
        regime, reservoir, sensor = decode_state(state)
        correct = 0 if regime == NutrientRegime.LEAN else 2
        incorrect = 2 if regime == NutrientRegime.LEAN else 0
        if sensor == SensorMode.PASSIVE:
            nutrient[correct, state] = 0.55
            nutrient[1, state] = 0.35
            nutrient[incorrect, state] = 0.10
        else:
            nutrient[correct, state] = 0.90
            nutrient[1, state] = 0.08
            nutrient[incorrect, state] = 0.02
        reservoir_obs[int(reservoir), state] = 0.90
    return nutrient, reservoir_obs


def build_homeostat_model(
    scenario: Scenario = "epistemic", variant: ModelVariant = "standard"
) -> CategoricalModel:
    if scenario not in {"epistemic", "known", "disturbed"}:
        raise ValueError(f"unknown scenario {scenario!r}")
    if variant not in {"standard", "epistemic_lesion", "scrambled", "reversed"}:
        raise ValueError(f"unknown model variant {variant!r}")
    nutrient, reservoir_obs = _likelihood_model()
    if variant == "scrambled":
        nutrient = nutrient[[2, 1, 0], :]
    reservoir_preferences = np.asarray([-4.0, 4.0, -5.0], dtype=np.float64)
    if variant == "reversed":
        reservoir_preferences = -reservoir_preferences
    policies = enumerate_policies()
    model = CategoricalModel(
        A=(nutrient, reservoir_obs),
        B=_transition_model(0.03),
        C=(np.zeros(3, dtype=np.float64), reservoir_preferences),
        D=_initial_distribution(scenario),
        policies=policies,
        gamma=16.0,
        policy_prior=np.full(len(policies), 1.0 / len(policies), dtype=np.float64),
        use_utility=True,
        use_states_info_gain=variant != "epistemic_lesion",
        labels={
            "state_factors": ("nutrient_regime", "reservoir", "sensor_mode"),
            "nutrient_regime": ("lean", "rich"),
            "reservoir": ("depleted", "viable", "overloaded"),
            "sensor_mode": ("passive", "sampling"),
            "nutrient_observation": ("lean", "ambiguous", "rich"),
            "reservoir_observation": ("depleted", "viable", "overloaded"),
            "actions": tuple(action.name.lower() for action in Action),
        },
    )
    model.validate()
    return model


class HomeostatEnvironment:
    """Generative process; callers receive observations, never privileged state."""

    def __init__(self, scenario: Scenario = "epistemic") -> None:
        self.model = build_homeostat_model(scenario, "standard")
        self.scenario = scenario

    def _observe(self, state: int, rng: np.random.Generator) -> tuple[int, ...]:
        return tuple(
            int(rng.choice(likelihood.shape[0], p=likelihood[:, state]))
            for likelihood in self.model.A
        )

    def reset(self, rng: np.random.Generator) -> StepResult:
        state = int(rng.choice(self.model.n_states, p=self.model.D))
        return StepResult(
            observation=self._observe(state, rng),
            state=state,
            action_cost=0.0,
            diagnostics={"scenario": self.scenario},
        )

    def step(
        self, state: int, action: int, rng: np.random.Generator
    ) -> StepResult:
        selected = Action(int(action))
        next_state = int(
            rng.choice(self.model.n_states, p=self.model.B[:, state, int(selected)])
        )
        return StepResult(
            observation=self._observe(next_state, rng),
            state=next_state,
            action_cost=0.15 if selected == Action.SAMPLE else 0.0,
            diagnostics={"scenario": self.scenario},
        )


def with_initial_distribution(
    model: CategoricalModel, distribution: np.ndarray
) -> CategoricalModel:
    """Return a validated model with a caller-specified initial belief."""

    result = replace(model, D=np.asarray(distribution, dtype=np.float64).copy())
    result.validate()
    return result
