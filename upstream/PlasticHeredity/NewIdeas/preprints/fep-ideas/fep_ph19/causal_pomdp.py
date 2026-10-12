from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from numpy.typing import NDArray

from fep_lab.integrity import sha256_bytes
from fep_ph18.hybrid_model import predicted_regime_prior
from fep_ph18.state import BodyState

from .config import MODEL_ACTIONS, ExperimentConfig
from .types import Action, ConditionSpec


REGIMES = 3
GROWTH_CLASSES = 3
SIMILARITY_CLASSES = 3
BODY_CLASSES = GROWTH_CLASSES * SIMILARITY_CLASSES
CANDIDATES = ("02", "03")


def growth_class(growth_norm: float) -> int:
    value = float(growth_norm)
    return 0 if value < 0.75 else 1 if value < 0.95 else 2


def similarity_class(similarity: float) -> int:
    value = float(similarity)
    return 2 if value >= 0.90 else 1 if value >= 0.80 else 0


def body_class(growth_norm: float, similarity: float) -> int:
    return growth_class(growth_norm) * SIMILARITY_CLASSES + similarity_class(similarity)


def state_body_class(state: BodyState) -> int:
    return body_class(state.growth_norm, state.similarity)


def candidate_index(candidate: str) -> int:
    try:
        return CANDIDATES.index(str(candidate))
    except ValueError as error:
        raise ValueError(f"unknown FEP–PH1.9 candidate {candidate!r}") from error


def _model_action_cost(config: ExperimentConfig, action: int) -> float:
    value = int(action)
    if value == int(Action.SAMPLE):
        return float(config.action_cost_sample)
    if value in (int(Action.ADAPT_A), int(Action.ADAPT_B)):
        return float(config.action_cost_uptake)
    if value >= 4:
        physical = value - 4
        return float(config.action_cost_sample) + (
            float(config.action_cost_uptake)
            if physical in (int(Action.ADAPT_A), int(Action.ADAPT_B))
            else 0.0
        )
    return 0.0


@dataclass(frozen=True)
class ExactCausalPOMDP:
    body_transition: NDArray[np.float64]
    completion_probability: NDArray[np.float64]
    inherited_probability: NDArray[np.float64]
    cell_counts: NDArray[np.int64]
    qualification: dict[str, float | bool]
    pseudocount: float

    def validate(self) -> None:
        base = (len(CANDIDATES), MODEL_ACTIONS, REGIMES, BODY_CLASSES)
        if self.body_transition.shape != base + (BODY_CLASSES,):
            raise ValueError("causal body transition shape is invalid")
        for value in (self.completion_probability, self.inherited_probability):
            if value.shape != base or np.any((value <= 0.0) | (value >= 1.0)):
                raise ValueError("causal outcome probability is invalid")
        if self.cell_counts.shape != base:
            raise ValueError("causal count shape is invalid")
        if not np.allclose(self.body_transition.sum(axis=-1), 1.0):
            raise ValueError("causal transition rows are not normalized")
        if not all(np.all(np.isfinite(value)) for value in (
            self.body_transition,
            self.completion_probability,
            self.inherited_probability,
        )):
            raise ValueError("causal model contains non-finite values")

    def immediate_value(
        self,
        candidate: str,
        body: int,
        belief: NDArray[np.floating],
        action: int,
        config: ExperimentConfig,
    ) -> float:
        ci = candidate_index(candidate)
        probability = np.asarray(belief, dtype=np.float64)
        inherited = float(
            probability @ self.inherited_probability[ci, int(action), :, int(body)]
        )
        completion = float(
            probability @ self.completion_probability[ci, int(action), :, int(body)]
        )
        return (
            inherited
            + 0.15 * completion
            - config.action_cost_weight * _model_action_cost(config, int(action))
        )

    def action_value(
        self,
        state: BodyState,
        condition: ConditionSpec,
        action: int,
        config: ExperimentConfig,
        *,
        depth: int | None = None,
    ) -> float:
        body = state_body_class(state)
        belief = np.asarray(state.regime_belief, dtype=np.float64)
        immediate = self.immediate_value(
            condition.candidate, body, belief, int(action), config
        )
        remaining = int(config.selected_planner_depth or 1) if depth is None else int(depth)
        if remaining <= 1:
            return immediate
        ci = candidate_index(condition.candidate)
        body_distribution = np.einsum(
            "r,rn->n",
            belief,
            self.body_transition[ci, int(action), :, body, :],
        )
        next_belief = predicted_regime_prior(
            belief, condition.switch_probability, 0.05
        )
        future = 0.0
        for next_body, probability in enumerate(body_distribution):
            if probability <= 0.0:
                continue
            best = max(
                self.immediate_value(
                    condition.candidate,
                    next_body,
                    next_belief,
                    physical,
                    config,
                )
                for physical in (0, 1, 2)
            )
            future += float(probability) * best
        return float(immediate + 0.90 * future)

    def best_physical_action(
        self,
        state: BodyState,
        condition: ConditionSpec,
        config: ExperimentConfig,
        *,
        compound: bool,
    ) -> tuple[float, int]:
        values = [
            (
                self.action_value(
                    state,
                    condition,
                    4 + physical if compound else physical,
                    config,
                ),
                physical,
            )
            for physical in (0, 1, 2)
        ]
        return max(values, key=lambda item: (item[0], -item[1]))


def _growth_norm(raw_growth: int, growth_budget: int) -> float:
    return float(np.log1p(max(0, int(raw_growth))) / np.log1p(int(growth_budget)))


def _fit_arrays(
    cells: Iterable[tuple[dict[str, NDArray[Any]], dict[str, Any]]],
    pseudocount: float,
    *,
    excluded_fold: int | None = None,
    folds: int = 1,
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], NDArray[np.int64]]:
    shape = (len(CANDIDATES), MODEL_ACTIONS, REGIMES, BODY_CLASSES)
    transition = np.full(shape + (BODY_CLASSES,), float(pseudocount))
    completion_success = np.full(shape, float(pseudocount))
    inherited_success = np.full(shape, float(pseudocount))
    totals = np.full(shape, 2.0 * float(pseudocount))
    observed = np.zeros(shape, dtype=np.int64)
    for arrays, metadata in cells:
        candidate = candidate_index(str(metadata["candidate"]))
        budget = int(metadata["growth_budget"])
        for index in range(len(arrays["action"])):
            matrix = int(arrays["matrix_id"][index])
            if excluded_fold is not None and matrix % folds == excluded_fold:
                continue
            action = int(arrays["action"][index])
            regime = int(arrays["current_regime"][index])
            current = body_class(
                _growth_norm(int(arrays["current_growth"][index]), budget),
                float(arrays["current_similarity"][index]),
            )
            following = body_class(
                _growth_norm(int(arrays["next_growth"][index]), budget),
                float(arrays["next_similarity"][index]),
            )
            key = (candidate, action, regime, current)
            transition[key + (following,)] += 1.0
            completed = int(arrays["completed"][index])
            inherited = int(
                completed == 1 and float(arrays["next_similarity"][index]) >= 0.90
            )
            completion_success[key] += completed
            inherited_success[key] += inherited
            totals[key] += 1.0
            observed[key] += 1
    transition /= transition.sum(axis=-1, keepdims=True)
    return transition, completion_success / totals, inherited_success / totals, observed


def _concordance(observed: NDArray[np.float64], predicted: NDArray[np.float64]) -> float:
    concordant = 0
    total = 0
    for left in range(len(observed)):
        for right in range(left + 1, len(observed)):
            if observed[left] == observed[right]:
                continue
            concordant += int(
                np.sign(observed[left] - observed[right])
                == np.sign(predicted[left] - predicted[right])
            )
            total += 1
    return float(concordant / total) if total else 0.5


def fit_exact_model(
    cells: list[tuple[dict[str, NDArray[Any]], dict[str, Any]]],
    config: ExperimentConfig,
) -> ExactCausalPOMDP:
    folds = config.ensemble_members
    predictions: list[float] = []
    inherited_targets: list[float] = []
    completion_predictions: list[float] = []
    completion_targets: list[float] = []
    action_observed = np.zeros(MODEL_ACTIONS)
    action_predicted = np.zeros(MODEL_ACTIONS)
    action_counts = np.zeros(MODEL_ACTIONS)
    for fold in range(folds):
        transition, completion, inherited, _counts = _fit_arrays(
            cells,
            config.causal_pseudocount,
            excluded_fold=fold,
            folds=folds,
        )
        for arrays, metadata in cells:
            ci = candidate_index(str(metadata["candidate"]))
            budget = int(metadata["growth_budget"])
            for index in range(len(arrays["action"])):
                if int(arrays["matrix_id"][index]) % folds != fold:
                    continue
                action = int(arrays["action"][index])
                regime = int(arrays["current_regime"][index])
                body = body_class(
                    _growth_norm(int(arrays["current_growth"][index]), budget),
                    float(arrays["current_similarity"][index]),
                )
                completed = float(arrays["completed"][index])
                target = float(
                    completed > 0.5
                    and float(arrays["next_similarity"][index]) >= 0.90
                )
                ip = float(inherited[ci, action, regime, body])
                cp = float(completion[ci, action, regime, body])
                predictions.append(ip)
                inherited_targets.append(target)
                completion_predictions.append(cp)
                completion_targets.append(completed)
                action_observed[action] += target
                action_predicted[action] += ip
                action_counts[action] += 1.0
    inherited_expected = np.asarray(inherited_targets)
    inherited_forecast = np.asarray(predictions)
    completion_expected = np.asarray(completion_targets)
    completion_forecast = np.asarray(completion_predictions)
    inherited_brier = float(np.mean((inherited_expected - inherited_forecast) ** 2))
    completion_brier = float(np.mean((completion_expected - completion_forecast) ** 2))
    inherited_intercept = float(
        np.mean((inherited_expected - inherited_expected.mean()) ** 2)
    )
    completion_intercept = float(
        np.mean((completion_expected - completion_expected.mean()) ** 2)
    )
    valid_actions = action_counts > 0
    observed_order = action_observed[valid_actions] / action_counts[valid_actions]
    predicted_order = action_predicted[valid_actions] / action_counts[valid_actions]
    transition, completion, inherited, counts = _fit_arrays(
        cells, config.causal_pseudocount
    )
    provisional = ExactCausalPOMDP(
        transition,
        completion,
        inherited,
        counts,
        {},
        config.causal_pseudocount,
    )
    branch_correct: dict[str, float] = {}
    for candidate in CANDIDATES:
        ci = candidate_index(candidate)
        for regime, label, correct_action in ((0, "A", 1), (1, "B", 2)):
            values: list[bool] = []
            for body in range(BODY_CLASSES):
                if int(counts[ci, :, regime, body].sum()) == 0:
                    continue
                scores = [
                    float(inherited[ci, 4 + action, regime, body])
                    + 0.15 * float(completion[ci, 4 + action, regime, body])
                    for action in (0, 1, 2)
                ]
                values.append(int(np.argmax(scores)) == correct_action)
            branch_correct[f"candidate_{candidate}_regime_{label}"] = (
                float(np.mean(values)) if values else 0.0
            )
    qualification: dict[str, float | bool] = {
        "inherited_brier": inherited_brier,
        "inherited_intercept_brier": inherited_intercept,
        "inherited_skill": float(
            1.0 - inherited_brier / max(inherited_intercept, 1.0e-12)
        ),
        "completion_brier": completion_brier,
        "completion_intercept_brier": completion_intercept,
        "completion_skill": float(
            1.0 - completion_brier / max(completion_intercept, 1.0e-12)
        ),
        "action_order_concordance": _concordance(observed_order, predicted_order),
        **branch_correct,
    }
    branch_min = min(branch_correct.values()) if branch_correct else 0.0
    qualification["minimum_branch_concordance"] = branch_min
    qualification["qualified"] = bool(
        qualification["inherited_skill"] > 0.0
        and qualification["completion_skill"] > 0.0
        and qualification["action_order_concordance"] >= 0.65
        and branch_min >= 0.50
    )
    model = ExactCausalPOMDP(
        transition,
        completion,
        inherited,
        counts,
        qualification,
        config.causal_pseudocount,
    )
    model.validate()
    return model


def model_arrays(model: ExactCausalPOMDP) -> dict[str, NDArray[Any]]:
    names = sorted(model.qualification)
    return {
        "body_transition": model.body_transition,
        "completion_probability": model.completion_probability,
        "inherited_probability": model.inherited_probability,
        "cell_counts": model.cell_counts,
        "pseudocount": np.asarray((model.pseudocount,), dtype=np.float64),
        "qualification_names": np.asarray(names),
        "qualification_values": np.asarray(
            [float(model.qualification[name]) for name in names], dtype=np.float64
        ),
    }


def model_from_arrays(arrays: dict[str, NDArray[Any]]) -> ExactCausalPOMDP:
    names = [str(value) for value in arrays["qualification_names"]]
    values = [float(value) for value in arrays["qualification_values"]]
    qualification: dict[str, float | bool] = dict(zip(names, values, strict=True))
    if "qualified" in qualification:
        qualification["qualified"] = bool(qualification["qualified"])
    model = ExactCausalPOMDP(
        np.asarray(arrays["body_transition"], dtype=np.float64),
        np.asarray(arrays["completion_probability"], dtype=np.float64),
        np.asarray(arrays["inherited_probability"], dtype=np.float64),
        np.asarray(arrays["cell_counts"], dtype=np.int64),
        qualification,
        float(np.asarray(arrays["pseudocount"])[0]),
    )
    model.validate()
    return model


def save_model(path: Path, model: ExactCausalPOMDP) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **model_arrays(model))


def load_model(path: Path) -> ExactCausalPOMDP:
    with np.load(path, allow_pickle=False) as archive:
        return model_from_arrays({name: archive[name].copy() for name in archive.files})


def model_digest(model: ExactCausalPOMDP) -> str:
    chunks: list[bytes] = []
    for name, array in sorted(model_arrays(model).items()):
        value = np.ascontiguousarray(array)
        chunks.extend(
            (name.encode(), str(value.shape).encode(), value.dtype.str.encode(), value.tobytes())
        )
    return sha256_bytes(b"".join(chunks))


__all__ = (
    "ExactCausalPOMDP",
    "body_class",
    "fit_exact_model",
    "load_model",
    "model_arrays",
    "model_digest",
    "save_model",
    "state_body_class",
)
