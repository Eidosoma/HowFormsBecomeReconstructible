from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from fep_surprise.tracing import TracedFission, trace_future
from fep_surprise_2.worker import _update_trace_digest
from plastic_heredity.config import CANDIDATES as SIMULATOR_CONTRACTS
from plastic_heredity.config import GardConfig
from plastic_heredity.regime_confirmation import evaluate_regime
from plastic_heredity.seeds import derive_seed
from plastic_heredity.simulator import generate_beta, generate_initial_composition

from .config import CANDIDATES, Campaign25Config
from .interventions import nested_swap_orders


@dataclass(frozen=True)
class Screen25Spec:
    matrix_id: int
    output: Path
    force: bool = False

    @property
    def path(self) -> Path:
        return self.output / f"screen_m{self.matrix_id:04d}.joblib"


def _rng(master: str, domain: str, *parts: object) -> np.random.Generator:
    return np.random.default_rng(derive_seed(master, domain, *parts))


def _atomic_dump(value: Any, target: Path) -> None:
    temporary = target.with_name(target.name + f".{os.getpid()}.tmp")
    joblib.dump(value, temporary, compress=3)
    temporary.replace(target)


def screen_matrix(spec: Screen25Spec, config: Campaign25Config) -> Path:
    """Generate one untouched beta and its candidate-specific no-op screen."""

    if spec.path.exists() and not spec.force:
        return spec.path
    spec.output.mkdir(parents=True, exist_ok=True)
    scale = config.screen
    gard = GardConfig(generations=scale.main_generations)
    beta = generate_beta(
        gard, _rng(config.master_seed, "experiment25.screen.beta", spec.matrix_id)
    )
    order_seed = derive_seed(
        config.master_seed, "experiment25.screen.permutation", spec.matrix_id
    ) % (2**32 - 1)
    order = nested_swap_orders(gard.n_types, int(order_seed))[100]
    digest = hashlib.sha256()
    digest.update(np.ascontiguousarray(beta).tobytes())
    digest.update(np.ascontiguousarray(order).tobytes())
    candidate_payload: dict[str, Any] = {}
    for candidate in CANDIDATES:
        initial = generate_initial_composition(
            gard,
            _rng(
                config.master_seed,
                "experiment25.screen.main.initial",
                spec.matrix_id,
                candidate,
            ),
        )
        main, main_complete = trace_future(
            initial,
            beta,
            gard,
            SIMULATOR_CONTRACTS[candidate],
            scale.main_generations,
            _rng(
                config.master_seed,
                "experiment25.screen.main.dynamics",
                spec.matrix_id,
                candidate,
            ),
            config.phase_grid,
        )
        _update_trace_digest(digest, main, main_complete)
        usable = bool(main_complete and len(main) >= max(scale.landmarks))
        states = np.zeros((len(scale.landmarks), gard.n_types), dtype=np.int64)
        break_outcomes = np.zeros(
            (len(scale.landmarks), scale.branches), dtype=np.int8
        )
        strict8 = np.zeros_like(break_outcomes)
        complete = np.zeros_like(break_outcomes)
        lengths = np.zeros_like(break_outcomes, dtype=np.int16)
        if usable:
            states = np.stack(
                [main[landmark - 1].record.daughter for landmark in scale.landmarks]
            )
            for landmark_index, landmark in enumerate(scale.landmarks):
                for branch in range(scale.branches):
                    traced, completed = trace_future(
                        states[landmark_index],
                        beta,
                        gard,
                        SIMULATOR_CONTRACTS[candidate],
                        scale.horizon,
                        _rng(
                            config.master_seed,
                            "experiment25.screen.noop.future",
                            spec.matrix_id,
                            candidate,
                            landmark,
                            branch,
                        ),
                        config.phase_grid,
                    )
                    _update_trace_digest(digest, traced, completed)
                    outcome = evaluate_regime([item.record for item in traced])
                    break_outcomes[landmark_index, branch] = int(
                        outcome.first_break_index >= 0
                    )
                    strict8[landmark_index, branch] = int(outcome.primary_all8)
                    complete[landmark_index, branch] = int(completed)
                    lengths[landmark_index, branch] = len(traced)
        candidate_payload[candidate] = {
            "main_complete": main_complete,
            "usable": usable,
            "states": states,
            "break": break_outcomes,
            "strict8": strict8,
            "complete": complete,
            "trace_lengths": lengths,
            "break_probability": float(break_outcomes.mean()) if usable else None,
        }
    payload = {
        "format": "fep-surprise-25-screen-cell-v1",
        "profile": config.profile,
        "matrix_id": spec.matrix_id,
        "beta": beta,
        "order": order,
        "landmarks": np.asarray(scale.landmarks, dtype=np.int16),
        "candidates": candidate_payload,
        "scientific_digest": digest.hexdigest(),
    }
    _atomic_dump(payload, spec.path)
    return spec.path


def load_screen(path: Path) -> dict[str, Any]:
    value = joblib.load(path)
    if value.get("format") != "fep-surprise-25-screen-cell-v1":
        raise ValueError(f"unsupported Experiment 2.5 screen cell: {path}")
    return value


def classify_break_regime(
    candidate_probabilities: dict[str, float], config: Campaign25Config
) -> str | None:
    values = [float(candidate_probabilities[candidate]) for candidate in CANDIDATES]
    if all(value <= config.stable_max_break for value in values):
        return "stable"
    if all(
        config.transitional_min_break <= value <= config.transitional_max_break
        for value in values
    ):
        return "transitional"
    if all(value >= config.saturated_min_break for value in values):
        return "saturated"
    return None


def mass_preserving_perturbations(
    state: np.ndarray, count: int, seed: int
) -> np.ndarray:
    """Frozen one-molecule transfers; no perturbation changes total mass."""

    values = np.asarray(state, dtype=np.int64)
    occupied = np.flatnonzero(values > 0)
    if not len(occupied):
        raise ValueError("cannot perturb an empty state")
    rng = np.random.default_rng(seed)
    donor_order = occupied[rng.permutation(len(occupied))]
    recipient_order = rng.permutation(len(values))
    output = []
    used: set[tuple[int, int]] = set()
    cursor = 0
    while len(output) < count and cursor < len(values) * max(len(occupied), 1) * 2:
        donor = int(donor_order[cursor % len(donor_order)])
        recipient = int(recipient_order[cursor % len(recipient_order)])
        cursor += 1
        if donor == recipient or (donor, recipient) in used:
            continue
        changed = values.copy()
        changed[donor] -= 1
        changed[recipient] += 1
        used.add((donor, recipient))
        output.append(changed)
    if len(output) != count:
        raise RuntimeError("could not construct requested unique perturbations")
    return np.stack(output)


def trace_digest_of_screen(payload: dict[str, Any]) -> str:
    return str(payload["scientific_digest"])
