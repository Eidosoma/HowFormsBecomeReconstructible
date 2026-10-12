from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from numpy.typing import NDArray

from fep_lab.seeds import derive_seed
from fep_ph1.gard import generate_beta, generate_initial_composition

from .config import MOLECULAR_DOSES, SCREEN_BUDGETS, ExperimentConfig, regime_specs
from .environment import EnvironmentDesign, GardGoalAlignmentEnvironment, oracle_action
from .types import (
    Action,
    ActionChannel,
    ActuatorSetting,
    ChallengeSelection,
    ChallengeTier,
    EnvironmentFamily,
)


@dataclass(frozen=True)
class ScreenCombination:
    candidate: str
    family: EnvironmentFamily
    channel: ActionChannel

    @property
    def key(self) -> str:
        return f"c{self.candidate}--{self.family}--{self.channel}"


def screen_combinations() -> tuple[ScreenCombination, ...]:
    return tuple(
        ScreenCombination(candidate, family, channel)
        for candidate in ("02", "03")
        for family in EnvironmentFamily
        for channel in ActionChannel
    )


def _seed(config: ExperimentConfig, domain: str, *parts: object) -> int:
    return derive_seed(config.master_seed, f"fep_ph15.screen.{domain}", *parts)


def screen_seed_domains(config: ExperimentConfig) -> dict[str, int]:
    return {
        name: _seed(config, name, "fixture")
        for name in (
            "beta",
            "initial",
            "chemistry",
            "environment",
            "observation",
            "partition",
            "permutation",
        )
    }


def _placeholder(polarity: str = "direct", dose: int = 1) -> ActuatorSetting:
    return ActuatorSetting(polarity, dose, "NON_ACTIONABLE", 0.0, 0.0)


def _design(
    config: ExperimentConfig,
    combination: ScreenCombination,
    matrix_id: int,
    regime_index: int,
    growth_budget: int,
    setting: ActuatorSetting,
) -> EnvironmentDesign:
    regime = regime_specs()[regime_index]
    return EnvironmentDesign(
        combination.family,
        combination.channel,
        regime,
        combination.candidate,
        _seed(config, "partition", combination.family, matrix_id),
        _seed(config, "permutation", combination.family, matrix_id),
        growth_budget,
        setting,
    )


def _beta(config: ExperimentConfig, matrix_id: int) -> NDArray[np.float64]:
    return generate_beta(config.gard, np.random.default_rng(_seed(config, "beta", matrix_id)))


def _initial(
    config: ExperimentConfig,
    combination: ScreenCombination,
    matrix_id: int,
    regime_index: int,
    branch: int,
) -> NDArray[np.int64]:
    return generate_initial_composition(
        config.gard,
        np.random.default_rng(
            _seed(config, "initial", combination.key, matrix_id, regime_index, branch)
        ),
    )


def _process_seeds(
    config: ExperimentConfig,
    combination: ScreenCombination,
    matrix_id: int,
    regime_index: int,
    branch: int,
) -> tuple[int, int, int]:
    return tuple(
        _seed(config, kind, combination.key, matrix_id, regime_index, branch)
        for kind in ("chemistry", "environment", "observation")
    )  # type: ignore[return-value]


def _episode(
    config: ExperimentConfig,
    combination: ScreenCombination,
    beta: NDArray[np.float64],
    initial: NDArray[np.int64],
    regime_index: int,
    matrix_id: int,
    branch: int,
    growth_budget: int,
    setting: ActuatorSetting,
    *,
    oracle: bool,
) -> tuple[NDArray[np.int8], NDArray[np.int32]]:
    environment = GardGoalAlignmentEnvironment(
        config,
        _design(config, combination, matrix_id, regime_index, growth_budget, setting),
        beta,
        initial,
        *_process_seeds(config, combination, matrix_id, regime_index, branch),
    )
    completed = np.zeros(config.screen_horizon, dtype=np.int8)
    growth = np.full(config.screen_horizon, growth_budget + 1, dtype=np.int32)
    for step in range(config.screen_horizon):
        action = oracle_action(environment.regime) if oracle else int(Action.WAIT)
        result = environment.step(action)
        completed[step] = int(result.completed)
        growth[step] = int(result.raw_observation.growth_steps)
        if not result.completed:
            break
    return completed, growth


def counterfactual_completion(
    growth_steps: NDArray[np.int32], completed_at_max: NDArray[np.int8], budget: int
) -> float:
    growth = np.asarray(growth_steps, dtype=np.int64)
    completed = np.asarray(completed_at_max, dtype=bool)
    valid = completed & (growth <= int(budget))
    failures = np.flatnonzero(~valid)
    count = int(failures[0]) if failures.size else len(valid)
    return count / len(valid)


def select_challenges(
    no_action_growth: NDArray[np.int32],
    no_action_completed: NDArray[np.int8],
    budgets: tuple[int, ...] = SCREEN_BUDGETS,
) -> ChallengeSelection:
    values = {
        budget: float(
            np.mean(
                [
                    counterfactual_completion(growth, completed, budget)
                    for growth, completed in zip(
                        no_action_growth.reshape((-1, no_action_growth.shape[-1])),
                        no_action_completed.reshape((-1, no_action_completed.shape[-1])),
                        strict=True,
                    )
                ]
            )
        )
        for budget in budgets
    }
    hard = min(budgets, key=lambda budget: (abs(values[budget] - 0.40), budget))
    transition = min(
        (budget for budget in budgets if budget != hard),
        key=lambda budget: (abs(values[budget] - 0.70), budget),
    )
    result = ChallengeSelection(transition, hard, values[transition], values[hard])
    result.validate(budgets)
    return result


def _candidate_settings(channel: ActionChannel) -> tuple[ActuatorSetting, ...]:
    doses = (1,) if channel == ActionChannel.UPTAKE else MOLECULAR_DOSES
    return tuple(_placeholder(polarity, dose) for dose in doses for polarity in ("direct", "inverted"))


def actionability_label(transition_gain: float, hard_gain: float) -> str:
    mean_gain = 0.5 * (transition_gain + hard_gain)
    if mean_gain >= 0.10 and transition_gain >= 0.0 and hard_gain >= 0.0:
        return "ACTIONABLE"
    if transition_gain > 0.0 or hard_gain > 0.0:
        return "MIXED"
    return "NON_ACTIONABLE"


def choose_actuator(
    channel: ActionChannel,
    settings: tuple[ActuatorSetting, ...],
    oracle_completion: NDArray[np.float64],
    baselines: NDArray[np.float64],
) -> ActuatorSetting:
    if oracle_completion.shape != (len(settings), 2) or baselines.shape != (2,):
        raise ValueError("screen summary has the wrong shape")
    gains = oracle_completion - baselines[None, :]
    best = min(
        range(len(settings)),
        key=lambda index: (
            -float(gains[index].mean()),
            settings[index].molecular_dose if channel == ActionChannel.MOLECULAR else 1,
            0 if settings[index].polarity == "direct" else 1,
        ),
    )
    selected = settings[best]
    transition_gain, hard_gain = (float(value) for value in gains[best])
    return ActuatorSetting(
        selected.polarity,
        selected.molecular_dose,
        actionability_label(transition_gain, hard_gain),
        transition_gain,
        hard_gain,
    )


def generate_screen_combination(
    config: ExperimentConfig, combination: ScreenCombination
) -> tuple[dict[str, NDArray], dict[str, object]]:
    shape = (len(regime_specs()), config.screen_matrices, config.screen_branches, config.screen_horizon)
    no_action_completed = np.zeros(shape, dtype=np.int8)
    no_action_growth = np.full(shape, config.gard.max_growth_steps + 1, dtype=np.int32)
    for regime_index in range(len(regime_specs())):
        for matrix_id in range(config.screen_matrices):
            beta = _beta(config, matrix_id)
            for branch in range(config.screen_branches):
                initial = _initial(config, combination, matrix_id, regime_index, branch)
                completed, growth = _episode(
                    config, combination, beta, initial, regime_index, matrix_id,
                    branch, config.gard.max_growth_steps, _placeholder(), oracle=False,
                )
                no_action_completed[regime_index, matrix_id, branch] = completed
                no_action_growth[regime_index, matrix_id, branch] = growth
    selection = select_challenges(no_action_growth, no_action_completed)
    baselines = np.asarray(
        [
            np.mean(
                [
                    counterfactual_completion(growth, completed, selection.budget(tier))
                    for growth, completed in zip(
                        no_action_growth.reshape((-1, config.screen_horizon)),
                        no_action_completed.reshape((-1, config.screen_horizon)),
                        strict=True,
                    )
                ]
            )
            for tier in (ChallengeTier.TRANSITION, ChallengeTier.HARD)
        ],
        dtype=np.float64,
    )
    settings = _candidate_settings(combination.channel)
    oracle_episode_completion = np.zeros(
        (len(settings), 2, len(regime_specs()), config.screen_matrices, config.screen_branches),
        dtype=np.float64,
    )
    for setting_index, setting in enumerate(settings):
        for tier_index, tier in enumerate((ChallengeTier.TRANSITION, ChallengeTier.HARD)):
            budget = selection.budget(tier)
            for regime_index in range(len(regime_specs())):
                for matrix_id in range(config.screen_matrices):
                    beta = _beta(config, matrix_id)
                    for branch in range(config.screen_branches):
                        initial = _initial(config, combination, matrix_id, regime_index, branch)
                        completed, _growth = _episode(
                            config, combination, beta, initial, regime_index,
                            matrix_id, branch, budget, setting, oracle=True,
                        )
                        oracle_episode_completion[setting_index, tier_index, regime_index, matrix_id, branch] = float(completed.sum() / config.screen_horizon)
    oracle_summary = oracle_episode_completion.mean(axis=(2, 3, 4))
    actuator = choose_actuator(combination.channel, settings, oracle_summary, baselines)
    arrays: dict[str, NDArray] = {
        "no_action_completed": no_action_completed,
        "no_action_growth": no_action_growth,
        "screen_budgets": np.asarray(SCREEN_BUDGETS, dtype=np.int32),
        "setting_names": np.asarray([f"d{setting.molecular_dose}-{setting.polarity}" for setting in settings]),
        "oracle_episode_completion": oracle_episode_completion,
        "oracle_summary": oracle_summary,
        "baseline_summary": baselines,
    }
    metadata: dict[str, object] = {
        "schema": "fep-ph15-screen-cell-v1",
        "combination": combination.key,
        "candidate": combination.candidate,
        "family": str(combination.family),
        "channel": str(combination.channel),
        "challenge": asdict(selection),
        "actuator": asdict(actuator),
        "retained_even_if_non_actionable": True,
        "volatilities_pooled": [spec.volatility for spec in regime_specs()],
    }
    return arrays, metadata

