from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from fep_ph1.types import RawObservation

from .types import Action, ConditionSpec


PSEUDOCOUNT = 0.5
HISTORY_LAGS = 2
HISTORY_WIDTH = 11


def composition_clr(composition: NDArray[np.integer]) -> NDArray[np.float64]:
    values = np.asarray(composition, dtype=np.float64) + PSEUDOCOUNT
    logs = np.log(values)
    return logs - float(logs.mean())


def clr_proportions(clr: NDArray[np.floating]) -> NDArray[np.float64]:
    values = np.asarray(clr, dtype=np.float64)
    shifted = values - float(np.max(values))
    weights = np.exp(shifted)
    return weights / float(weights.sum())


def normalized_entropy(clr: NDArray[np.floating]) -> float:
    probabilities = clr_proportions(clr)
    positive = probabilities > 0.0
    return float(-np.sum(probabilities[positive] * np.log(probabilities[positive])) / np.log(len(probabilities)))


def cue_probabilities(cue: int) -> NDArray[np.float64]:
    output = np.zeros(4, dtype=np.float64)
    output[int(cue)] = 1.0
    return output


def _history_row(
    growth: float,
    similarity: float,
    alignment: float,
    cue: NDArray[np.floating],
    action: int,
) -> NDArray[np.float64]:
    action_values = np.zeros(4, dtype=np.float64)
    action_values[int(action)] = 1.0
    return np.concatenate((np.asarray((growth, similarity, alignment)), np.asarray(cue), action_values))


@dataclass(frozen=True)
class BodyState:
    clr: NDArray[np.float64]
    mass_norm: float
    growth_norm: float
    similarity: float
    alignment: float
    cue_probs: NDArray[np.float64]
    regime_belief: NDArray[np.float64]
    previous_action: int
    history: NDArray[np.float64]

    def validate(self) -> None:
        if self.clr.shape != (100,):
            raise ValueError("body CLR state must have 100 components")
        if self.cue_probs.shape != (4,) or self.regime_belief.shape != (3,):
            raise ValueError("body categorical beliefs have invalid shape")
        if self.history.shape != (HISTORY_LAGS, HISTORY_WIDTH):
            raise ValueError("body history has invalid shape")
        if not np.all(np.isfinite(self.clr)) or not np.all(np.isfinite(self.history)):
            raise ValueError("body state contains non-finite values")


def initial_body_state(
    composition: NDArray[np.integer], raw: RawObservation, belief: NDArray[np.floating]
) -> BodyState:
    clr = composition_clr(composition)
    state = BodyState(
        clr,
        float(np.asarray(composition).sum() / 80.0),
        0.0,
        float(raw.boundary_similarity),
        float(raw.alignment_score),
        cue_probabilities(raw.cue),
        np.asarray(belief, dtype=np.float64).copy(),
        int(Action.WAIT),
        np.zeros((HISTORY_LAGS, HISTORY_WIDTH), dtype=np.float64),
    )
    state.validate()
    return state


def advance_body_state(
    previous: BodyState,
    composition: NDArray[np.integer],
    raw: RawObservation,
    belief: NDArray[np.floating],
    action: int,
    growth_budget: int,
) -> BodyState:
    growth = float(np.log1p(max(0, raw.growth_steps)) / np.log1p(growth_budget))
    current_row = _history_row(
        previous.growth_norm,
        previous.similarity,
        previous.alignment,
        previous.cue_probs,
        previous.previous_action,
    )
    history = np.vstack((current_row, previous.history[0]))
    state = BodyState(
        composition_clr(composition),
        float(np.asarray(composition).sum() / 80.0),
        growth,
        float(raw.boundary_similarity),
        float(raw.alignment_score),
        cue_probabilities(raw.cue),
        np.asarray(belief, dtype=np.float64).copy(),
        int(action),
        history,
    )
    state.validate()
    return state


def context_features(condition: ConditionSpec) -> NDArray[np.float64]:
    output: list[float] = []
    output.extend((float(condition.candidate == "02"), float(condition.candidate == "03")))
    output.extend((float(str(condition.family) == "nutrient"), float(str(condition.family) == "catalytic")))
    output.extend((float(str(condition.channel) == "uptake"), float(str(condition.channel) == "molecular")))
    output.extend((float(str(condition.tier) == "transition"), float(str(condition.tier) == "hard")))
    output.extend((float(condition.volatility == "slow"), float(condition.volatility == "fast")))
    output.append(float(condition.growth_budget / 480.0))
    return np.asarray(output, dtype=np.float64)


def state_features(state: BodyState, condition: ConditionSpec, *, rich: bool) -> NDArray[np.float64]:
    action = np.zeros(4, dtype=np.float64)
    action[state.previous_action] = 1.0
    common = np.concatenate(
        (
            np.asarray((state.mass_norm, state.growth_norm, state.similarity, state.alignment)),
            state.cue_probs,
            state.regime_belief,
            action,
            state.history.reshape(-1),
            context_features(condition),
        )
    )
    if not rich:
        return common
    return np.concatenate((state.clr, np.asarray((normalized_entropy(state.clr),)), common))


def initial_regime_belief() -> NDArray[np.float64]:
    return np.asarray((0.475, 0.475, 0.05), dtype=np.float64)


def update_regime_belief(
    prior: NDArray[np.floating], cue: int, switch_probability: float,
    shock_probability: float, cue_accuracy: float, *, transition: bool = True,
) -> NDArray[np.float64]:
    belief = np.asarray(prior, dtype=np.float64)
    if transition:
        base = belief[:2]
        base_total = float(base.sum())
        if base_total <= 0.0:
            base = np.asarray((0.5, 0.5))
        else:
            base = base / base_total
        switched = np.asarray(
            (
                (1.0 - switch_probability) * base[0] + switch_probability * base[1],
                switch_probability * base[0] + (1.0 - switch_probability) * base[1],
            )
        )
        predicted = np.asarray(
            ((1.0 - shock_probability) * switched[0], (1.0 - shock_probability) * switched[1], shock_probability),
            dtype=np.float64,
        )
    else:
        total = float(belief.sum())
        predicted = (
            np.full(3, 1.0 / 3.0, dtype=np.float64)
            if total <= 0.0
            else belief / total
        )
    if int(cue) == 0:
        likelihood = np.full(3, 1.0 - cue_accuracy, dtype=np.float64)
    else:
        likelihood = np.zeros(3, dtype=np.float64)
        likelihood[int(cue) - 1] = cue_accuracy
    posterior = predicted * likelihood
    total = float(posterior.sum())
    return predicted if total <= 0.0 else posterior / total
