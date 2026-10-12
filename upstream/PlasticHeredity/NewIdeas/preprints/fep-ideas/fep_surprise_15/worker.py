from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.stats import spearmanr

from . import compat as _compat  # noqa: F401
from .config import Campaign15Config, Stage15Scale
from .observers import (
    ALL_OBSERVERS,
    FIXED_SHELF,
    INVARIANT_KNN,
    LEGACY_KNN,
    PRIMARY_OBSERVERS,
    SHELF,
    ObserverEnsemble,
    fit_observer_ensemble,
    nearest_shelf_distance,
    proportional_state,
)
from fep_surprise.dynamics import meanfield_forms, nearest_form_distance, rq_alignment
from fep_surprise.tracing import TracedFission, trace_future
from plastic_heredity.config import CANDIDATES, GardConfig
from plastic_heredity.regime_confirmation import evaluate_regime
from plastic_heredity.seeds import derive_seed
from plastic_heredity.simulator import generate_beta, generate_initial_composition


HOMOGENEOUS_VALUE = float(np.exp(4.0))
BASELINE_FEATURE_NAMES = (
    *(f"h_lag_{index}" for index in range(10)),
    "history_length",
    "break_time_fraction",
    "landmark_fraction",
    "parent_mass",
    "daughter_mass",
    "growth_steps",
    "occupied_parent",
    "occupied_daughter",
    "occupied_delta",
    "entropy_parent",
    "entropy_daughter",
    "entropy_delta",
    "atlas_parent",
    "atlas_daughter",
    "atlas_delta",
    "rq_parent",
    "rq_daughter",
    "rq_delta",
    "meanfield_parent",
    "meanfield_daughter",
    "meanfield_delta",
    "growth_atlas_start",
    "growth_atlas_end",
    "growth_atlas_delta",
    "growth_rq_start",
    "growth_rq_end",
    "growth_rq_delta",
    "growth_meanfield_start",
    "growth_meanfield_end",
    "growth_meanfield_delta",
)
ANOMALY_FEATURE_NAMES = (
    "anomaly_parent",
    "anomaly_daughter",
    "anomaly_boundary_jump",
    "growth_anomaly_start",
    "growth_anomaly_end",
    "growth_anomaly_delta",
    "growth_anomaly_auc",
)


@dataclass(frozen=True)
class Cell15Spec:
    stage: str
    matrix_id: int
    candidate: str
    mechanism: str
    output: Path
    force: bool = False

    @property
    def stem(self) -> str:
        return (
            f"cell_{self.stage}_{self.mechanism}_"
            f"c{self.candidate}_m{self.matrix_id:04d}"
        )


def _rng(master: str, domain: str, *parts: object) -> np.random.Generator:
    return np.random.default_rng(derive_seed(master, domain, *parts))


def _active_beta(source: np.ndarray, mechanism: str) -> np.ndarray:
    if mechanism == "NATURAL_GARD":
        return source
    if mechanism in ("HOMOGENEOUS_GENERATIVE", "FISSION_ONLY_GENERATIVE"):
        return np.full_like(source, HOMOGENEOUS_VALUE)
    raise ValueError(mechanism)


def _update_trace_digest(
    digest: Any, traced: list[TracedFission], complete: bool
) -> None:
    digest.update(bytes([int(complete)]))
    digest.update(np.asarray([len(traced)], dtype=np.int16).tobytes())
    for item in traced:
        record = item.record
        for value in (
            record.parent,
            record.daughter,
            np.asarray([record.h], dtype=np.float64),
            np.asarray([record.growth_steps], dtype=np.int64),
            item.phase_compositions,
        ):
            digest.update(np.ascontiguousarray(value).tobytes())


def _collect_reference(
    config: Campaign15Config,
    scale: Stage15Scale,
    spec: Cell15Spec,
    beta: np.ndarray,
    gard: GardConfig,
    digest: Any,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    contract = CANDIDATES[spec.candidate]
    fission_only = spec.mechanism == "FISSION_ONLY_GENERATIVE"
    parents: list[np.ndarray] = []
    phases: list[np.ndarray] = []
    lineage_ids: list[int] = []
    attempts_used = []
    for lineage in range(scale.reference_lineages):
        initial = generate_initial_composition(
            gard,
            _rng(
                config.master_seed,
                f"{spec.stage}.reference.initial",
                spec.mechanism,
                spec.matrix_id,
                spec.candidate,
                lineage,
            ),
        )
        accepted: list[TracedFission] | None = None
        for attempt in range(100):
            traced, complete = trace_future(
                initial,
                beta,
                gard,
                contract,
                scale.reference_fissions,
                _rng(
                    config.master_seed,
                    f"{spec.stage}.reference.dynamics",
                    spec.mechanism,
                    spec.candidate,
                    spec.matrix_id,
                    lineage,
                    attempt,
                ),
                config.phase_grid,
                fission_only=fission_only,
            )
            if complete:
                accepted = traced
                attempts_used.append(attempt)
                _update_trace_digest(digest, traced, complete)
                break
        if accepted is None:
            attempts_used.append(100)
            continue
        for item in accepted[scale.reference_burnin :]:
            parents.append(item.record.parent.copy())
            phases.append(item.phase_compositions.copy())
            lineage_ids.append(lineage)
    if not parents:
        raise RuntimeError("no viable reference states")
    return (
        np.stack(parents),
        np.asarray(lineage_ids, dtype=np.int16),
        np.stack(phases),
        {
            "requested_lineages": scale.reference_lineages,
            "completed_lineages": int(len(set(lineage_ids))),
            "attempts_used": attempts_used,
            "states": len(parents),
        },
    )


def _fit_observers(
    config: Campaign15Config,
    spec: Cell15Spec,
    parents: np.ndarray,
    phases: np.ndarray,
    lineages: np.ndarray,
) -> ObserverEnsemble:
    seed = derive_seed(
        config.master_seed,
        f"{spec.stage}.observer.fit",
        spec.mechanism,
        spec.candidate,
        spec.matrix_id,
    ) % (2**32 - 1)
    return fit_observer_ensemble(
        parents,
        phases,
        lineages,
        pseudocount=config.pseudocount,
        reference_mass=config.reference_mass,
        pca_variance=config.pca_variance,
        pca_min=config.pca_min,
        pca_max=config.pca_max,
        knn_k=config.knn_k,
        mixture_k_max=config.mixture_k_max,
        training_subsample=config.training_subsample_per_half,
        seed=int(seed),
    )


def _independent_probe(
    config: Campaign15Config,
    scale: Stage15Scale,
    spec: Cell15Spec,
    beta: np.ndarray,
    gard: GardConfig,
    digest: Any,
) -> np.ndarray:
    initial = generate_initial_composition(
        gard,
        _rng(
            config.master_seed,
            f"{spec.stage}.probe.initial",
            spec.mechanism,
            spec.candidate,
            spec.matrix_id,
        ),
    )
    horizon = max(96, min(200, scale.reference_fissions))
    burnin = min(32, horizon // 3)
    for attempt in range(100):
        traced, complete = trace_future(
            initial,
            beta,
            gard,
            CANDIDATES[spec.candidate],
            horizon,
            _rng(
                config.master_seed,
                f"{spec.stage}.probe.dynamics",
                spec.mechanism,
                spec.candidate,
                spec.matrix_id,
                attempt,
            ),
            (0.0, 1.0),
            fission_only=spec.mechanism == "FISSION_ONLY_GENERATIVE",
        )
        if complete:
            _update_trace_digest(digest, traced, complete)
            return np.stack(
                [item.record.parent for item in traced[burnin : burnin + 64]]
            )
    raise RuntimeError("independent probe failed after 100 attempts")


def _meanfield_for_cell(
    config: Campaign15Config,
    spec: Cell15Spec,
    beta: np.ndarray,
    gard: GardConfig,
) -> np.ndarray:
    # Keep cached auxiliary forms inside the cell output root.  Replay cells use
    # isolated temporary roots, so no prior profile or concurrent audit can leak
    # a cached form into a regeneration.
    auxiliary = spec.output / "_auxiliary"
    auxiliary.mkdir(parents=True, exist_ok=True)
    target = auxiliary / (
        f"meanfield_{spec.stage}_{spec.mechanism}_m{spec.matrix_id:04d}.joblib"
    )
    if target.exists():
        return np.asarray(joblib.load(target), dtype=np.float64)
    if spec.mechanism != "NATURAL_GARD":
        forms = np.ones((1, gard.n_types), dtype=np.float64)
        forms /= np.linalg.norm(forms, axis=1, keepdims=True)
    else:
        if config.profile == "full":
            starts, iterations = 8, 500
        elif config.profile == "quick":
            starts, iterations = 4, 200
        else:
            starts, iterations = 2, 50
        forms = meanfield_forms(
            beta,
            gard,
            starts=starts,
            iterations=iterations,
            seed=derive_seed(
                config.master_seed,
                f"{spec.stage}.meanfield",
                spec.mechanism,
                spec.matrix_id,
            )
            % (2**32 - 1),
        )
    temporary = target.with_name(target.name + f".{os.getpid()}.tmp")
    joblib.dump(forms, temporary, compress=3)
    temporary.replace(target)
    return forms


def _main_path(
    config: Campaign15Config,
    scale: Stage15Scale,
    spec: Cell15Spec,
    beta: np.ndarray,
    initial: np.ndarray,
    gard: GardConfig,
    digest: Any,
) -> tuple[list[TracedFission], int]:
    for attempt in range(100):
        traced, complete = trace_future(
            initial,
            beta,
            gard,
            CANDIDATES[spec.candidate],
            scale.main_generations,
            _rng(
                config.master_seed,
                f"{spec.stage}.main_path",
                spec.mechanism,
                spec.candidate,
                spec.matrix_id,
                attempt,
            ),
            config.phase_grid,
            fission_only=spec.mechanism == "FISSION_ONLY_GENERATIVE",
        )
        if complete:
            _update_trace_digest(digest, traced, complete)
            return traced, attempt
    raise RuntimeError("main path failed after 100 attempts")


def _future(
    config: Campaign15Config,
    scale: Stage15Scale,
    spec: Cell15Spec,
    landmark: int,
    branch: int,
    beta: np.ndarray,
    restored: np.ndarray,
    gard: GardConfig,
) -> tuple[list[TracedFission], bool]:
    return trace_future(
        restored,
        beta,
        gard,
        CANDIDATES[spec.candidate],
        scale.horizon,
        _rng(
            config.master_seed,
            f"{spec.stage}.future",
            spec.mechanism,
            spec.candidate,
            spec.matrix_id,
            landmark,
            branch,
        ),
        config.phase_grid,
        fission_only=spec.mechanism == "FISSION_ONLY_GENERATIVE",
    )


def _entropy(counts: np.ndarray) -> float:
    values = np.asarray(counts, dtype=np.float64)
    probability = values / max(float(values.sum()), 1.0)
    selected = probability > 0
    return float(-np.sum(probability[selected] * np.log(probability[selected])))


def _baseline_features(
    traced: list[TracedFission],
    break_index: int,
    landmark: int,
    scale: Stage15Scale,
    beta: np.ndarray,
    gard: GardConfig,
    atlas_centers: np.ndarray,
    forms: np.ndarray,
) -> np.ndarray:
    records = [item.record for item in traced]
    history = [record.h for record in records[max(0, break_index - 9) : break_index + 1]]
    padded = np.ones(10, dtype=np.float64)
    padded[-len(history) :] = history
    item = traced[break_index]
    parent = item.record.parent
    daughter = item.record.daughter
    start = item.phase_compositions[0]
    end = item.phase_compositions[-1]
    values = (parent, daughter, start, end)
    atlas = nearest_shelf_distance(np.stack(values), atlas_centers)
    rq = np.asarray([rq_alignment(value, beta, gard) for value in values])
    meanfield = nearest_form_distance(np.stack(values), forms)
    occupied = [float(np.count_nonzero(value)) for value in (parent, daughter)]
    entropy = [_entropy(value) for value in (parent, daughter)]
    tail = np.asarray(
        [
            len(history),
            (break_index + 1) / scale.horizon,
            landmark / scale.main_generations,
            float(parent.sum()),
            float(daughter.sum()),
            item.record.growth_steps,
            occupied[0],
            occupied[1],
            occupied[1] - occupied[0],
            entropy[0],
            entropy[1],
            entropy[1] - entropy[0],
            atlas[0],
            atlas[1],
            atlas[1] - atlas[0],
            rq[0],
            rq[1],
            rq[1] - rq[0],
            meanfield[0],
            meanfield[1],
            meanfield[1] - meanfield[0],
            atlas[2],
            atlas[3],
            atlas[3] - atlas[2],
            rq[2],
            rq[3],
            rq[3] - rq[2],
            meanfield[2],
            meanfield[3],
            meanfield[3] - meanfield[2],
        ],
        dtype=np.float64,
    )
    output = np.concatenate([padded, tail])
    if len(output) != len(BASELINE_FEATURE_NAMES):
        raise AssertionError("baseline schema mismatch")
    return output


def _trace_scores(
    traced: list[TracedFission],
    observers: ObserverEnsemble,
    observer: str,
) -> dict[str, np.ndarray]:
    parents = np.stack([item.record.parent for item in traced])
    daughters = np.stack([item.record.daughter for item in traced])
    phases = np.stack([item.phase_compositions for item in traced])
    last_phase = phases.shape[1] - 1
    return {
        "raw_parent": observers.raw(parents, observer),
        "raw_daughter": observers.raw(daughters, observer),
        "raw_phase_start": observers.raw(phases[:, 0], observer),
        "anomaly_parent": observers.anomaly(parents, last_phase, observer),
        "anomaly_daughter": observers.anomaly(daughters, 0, observer),
        "anomaly_phase": observers.anomaly_grid(phases, observer),
    }


def _anomaly_features(scores: dict[str, np.ndarray], break_index: int) -> np.ndarray:
    parent = scores["anomaly_parent"][break_index]
    daughter = scores["anomaly_daughter"][break_index]
    profile = scores["anomaly_phase"][break_index]
    output = np.asarray(
        [
            parent,
            daughter,
            daughter - parent,
            profile[0],
            profile[-1],
            profile[-1] - profile[0],
            float(np.mean(profile - profile[0])),
        ],
        dtype=np.float64,
    )
    if len(output) != len(ANOMALY_FEATURE_NAMES):
        raise AssertionError("anomaly feature schema mismatch")
    return output


def _cycle_row(
    scores: dict[str, np.ndarray],
    traced: list[TracedFission],
    observers: ObserverEnsemble,
    observer: str,
    outcome: Any,
) -> dict[str, Any]:
    parent = scores["anomaly_parent"]
    daughter = scores["anomaly_daughter"]
    phase = scores["anomaly_phase"]
    raw_parent = scores["raw_parent"]
    raw_daughter = scores["raw_daughter"]
    raw_start = scores["raw_phase_start"]
    h = np.asarray([item.record.h for item in traced])
    breaks = h <= 0.9
    inherited = ~breaks
    jump = daughter - parent
    raw_jump = raw_daughter - raw_parent
    break_excess = (
        float(np.mean(jump[breaks]) - np.mean(jump[inherited]))
        if breaks.any() and inherited.any()
        else np.nan
    )
    proportional = np.stack(
        [
            proportional_state(item.record.parent, float(item.record.daughter.sum()))
            for item in traced
        ]
    )
    proportional_raw = observers.raw(proportional, observer)
    scale_term = proportional_raw - raw_parent
    composition_term = raw_daughter - proportional_raw
    growth_launches = np.stack([item.phase_compositions[0] for item in traced])
    standardized_launches = np.stack(
        [
            proportional_state(launch, float(parent_state.sum()))
            for launch, parent_state in zip(growth_launches, (item.record.parent for item in traced))
        ]
    )
    standardized_launch_raw = observers.raw(standardized_launches, observer)
    growth_scale_term = standardized_launch_raw - raw_start
    growth_composition_term = raw_parent - standardized_launch_raw
    break_index = int(outcome.first_break_index)
    recovery = np.nan
    if break_index >= 0 and break_index + 9 <= len(traced):
        recovery = float(
            np.mean(parent[break_index + 1 : break_index + 9] - daughter[break_index])
        )
    return {
        "phase_shock": float(np.mean(jump)),
        "phase_growth": float(np.mean(parent - phase[:, 0])),
        "break_excess": break_excess,
        "postbreak_recovery": recovery,
        "raw_shock": float(np.mean(raw_jump)),
        "raw_growth": float(np.mean(raw_parent - raw_start)),
        "scale_term": float(np.mean(scale_term)),
        "scale_term_max_abs": float(np.max(np.abs(scale_term))),
        "composition_term": float(np.mean(composition_term)),
        "growth_scale_term": float(np.mean(growth_scale_term)),
        "growth_composition_term": float(np.mean(growth_composition_term)),
        "strict8": bool(outcome.primary_all8),
        "has_run8": bool(outcome.first_run8_start >= 0),
        "run8_near_miss": bool(
            outcome.first_run8_start >= 0 and not outcome.primary_all8
        ),
        "first_break": break_index,
        "first_run8_start": int(outcome.first_run8_start),
        "strict8_onset": int(outcome.primary_all8_onset),
        "first_run8_min_pairwise": float(
            outcome.first_run8_minimum_pairwise_all8
        ),
        "first_run8_max_anchor": float(outcome.first_run8_maximum_anchor_all8),
        "phase_profile": np.mean(phase, axis=0).tolist(),
    }


def _reference_reliability(
    observers: ObserverEnsemble, probe: np.ndarray, phase: int
) -> dict[str, float]:
    output = {}
    for observer in PRIMARY_OBSERVERS:
        values = observers.anomaly_halves(probe, phase, observer)
        correlation = spearmanr(values[:, 0], values[:, 1]).statistic
        output[observer] = float(correlation) if np.isfinite(correlation) else 0.0
    return output


def _shelf_stability(observers: ObserverEnsemble) -> dict[str, Any]:
    left, right = observers.halves
    output: dict[str, Any] = {
        "selected_k": [left.selected_k, right.selected_k],
        "stable_multishelf_eligible": False,
        "matched_center_min_cosine": None,
        "matched_center_mean_cosine": None,
    }
    if left.selected_k != right.selected_k or left.selected_k < 2:
        return output
    similarity = left.shelf.centers @ right.shelf.centers.T
    rows, columns = linear_sum_assignment(-similarity)
    matched = similarity[rows, columns]
    output["matched_center_min_cosine"] = float(np.min(matched))
    output["matched_center_mean_cosine"] = float(np.mean(matched))
    output["stable_multishelf_eligible"] = bool(np.min(matched) > 0.90)
    return output


def _beta_descriptor(beta: np.ndarray) -> list[float]:
    log_beta = np.log(np.maximum(np.asarray(beta, dtype=np.float64), 1e-300))
    row_sums = np.asarray(beta, dtype=np.float64).sum(axis=1)
    return [
        float(np.mean(log_beta)),
        float(np.std(log_beta, ddof=1)),
        float(np.log(np.linalg.norm(beta))),
        float(np.log(np.mean(row_sums))),
        float(np.log(np.std(row_sums, ddof=1) + 1e-12)),
    ]


def _stack_or_empty(rows: list[np.ndarray], width: int) -> np.ndarray:
    return np.stack(rows) if rows else np.empty((0, width), dtype=np.float64)


def run_cell(spec: Cell15Spec, config: Campaign15Config) -> Path:
    spec.output.mkdir(parents=True, exist_ok=True)
    target = spec.output / f"{spec.stem}.joblib"
    model_target = spec.output / f"{spec.stem}_observers.joblib"
    if target.exists() and model_target.exists() and not spec.force:
        return target
    scale = config.development if spec.stage == "development" else config.confirmation
    gard = GardConfig(generations=scale.main_generations)
    source_beta = generate_beta(
        gard,
        _rng(config.master_seed, f"{spec.stage}.beta", spec.matrix_id),
    )
    beta = _active_beta(source_beta, spec.mechanism)
    initial = generate_initial_composition(
        gard,
        _rng(config.master_seed, f"{spec.stage}.main.initial", spec.matrix_id),
    )
    digest = hashlib.sha256()
    digest.update(np.ascontiguousarray(source_beta).tobytes())
    digest.update(np.ascontiguousarray(beta).tobytes())
    digest.update(np.ascontiguousarray(initial).tobytes())
    reference, lineage_ids, phase_reference, reference_meta = _collect_reference(
        config, scale, spec, beta, gard, digest
    )
    if len(reference) < min(
        config.minimum_reference_states,
        scale.reference_lineages * (scale.reference_fissions - scale.reference_burnin),
    ):
        raise RuntimeError("reference pool is below the frozen minimum")
    observers = _fit_observers(
        config, spec, reference, phase_reference, lineage_ids
    )
    forms = _meanfield_for_cell(config, spec, beta, gard)
    main, main_attempt = _main_path(
        config, scale, spec, beta, initial, gard, digest
    )
    probe = _independent_probe(config, scale, spec, beta, gard, digest)
    phase_count = len(config.phase_grid)

    prediction: dict[str, list[Any]] = {
        "landmark": [],
        "branch": [],
        "half": [],
        "outcome": [],
        "first_break": [],
        "baseline": [],
        **{observer: [] for observer in ALL_OBSERVERS},
    }
    cycles: dict[str, list[dict[str, Any]]] = {
        observer: [] for observer in ALL_OBSERVERS
    }
    certification_probe: list[np.ndarray] = []
    trace_lengths: list[int] = []
    future_parents: list[np.ndarray] = []
    future_daughters: list[np.ndarray] = []
    break_phase_counts: list[np.ndarray] = []
    completed_flags: list[int] = []

    for landmark in scale.landmarks:
        restored = main[landmark - 1].record.daughter
        for branch in range(scale.branches):
            traced, complete = _future(
                config, scale, spec, landmark, branch, beta, restored, gard
            )
            _update_trace_digest(digest, traced, complete)
            trace_lengths.append(len(traced))
            completed_flags.append(int(complete))
            future_parents.extend(item.record.parent.copy() for item in traced)
            future_daughters.extend(item.record.daughter.copy() for item in traced)
            records = [item.record for item in traced]
            outcome = evaluate_regime(records)
            if not traced:
                continue
            score_map = {
                observer: _trace_scores(traced, observers, observer)
                for observer in ALL_OBSERVERS
            }
            half_name = "A" if branch < scale.branches // 2 else "B"
            for observer, scores in score_map.items():
                cycles[observer].append(
                    {
                        "landmark": landmark,
                        "branch": branch,
                        "half": half_name,
                        "complete": bool(complete),
                        **_cycle_row(scores, traced, observers, observer, outcome),
                    }
                )
            break_index = int(outcome.first_break_index)
            if break_index >= 0 and break_index + 9 <= len(traced):
                prediction["landmark"].append(landmark)
                prediction["branch"].append(branch)
                prediction["half"].append(
                    0 if branch < scale.branches // 2 else 1
                )
                prediction["outcome"].append(int(outcome.primary_all8))
                prediction["first_break"].append(break_index)
                prediction["baseline"].append(
                    _baseline_features(
                        traced,
                        break_index,
                        landmark,
                        scale,
                        beta,
                        gard,
                        observers.atlas_centers,
                        forms,
                    )
                )
                for observer in ALL_OBSERVERS:
                    prediction[observer].append(
                        _anomaly_features(score_map[observer], break_index)
                    )
                break_phase_counts.append(
                    traced[break_index].phase_compositions.copy()
                )
            if outcome.primary_all8 and outcome.primary_all8_onset >= 0:
                start = int(outcome.primary_all8_onset)
                certification_probe.extend(
                    item.record.daughter.copy() for item in traced[start : start + 8]
                )

    model_hash = joblib.hash(observers)
    reference_reliability = _reference_reliability(
        observers, probe, phase_count - 1
    )
    payload: dict[str, Any] = {
        "format": "fep-surprise-15-cell-v1",
        "metadata": {
            "stage": spec.stage,
            "profile": config.profile,
            "matrix_id": spec.matrix_id,
            "candidate": spec.candidate,
            "mechanism": spec.mechanism,
            "main_attempt": main_attempt,
            "reference": reference_meta,
            "selected_k": [half.selected_k for half in observers.halves],
            "pca_dimensions": [
                len(half.projection.coordinate_mean) for half in observers.halves
            ],
            "meanfield_forms": len(forms),
            "scientific_digest": digest.hexdigest(),
            "observer_model_hash": model_hash,
            "beta_descriptor": _beta_descriptor(source_beta),
            "reference_reliability": reference_reliability,
            "shelf_stability": _shelf_stability(observers),
            "scale_max_abs": {
                observer: max(
                    (
                        float(row["scale_term_max_abs"])
                        for row in cycles[observer]
                    ),
                    default=0.0,
                )
                for observer in PRIMARY_OBSERVERS
            },
        },
        "cycles": cycles,
        "prediction": {
            key: np.asarray(value)
            for key, value in prediction.items()
            if key not in ("baseline", *ALL_OBSERVERS)
        },
        "baseline": _stack_or_empty(
            prediction["baseline"], len(BASELINE_FEATURE_NAMES)
        ),
        **{
            observer: _stack_or_empty(
                prediction[observer], len(ANOMALY_FEATURE_NAMES)
            )
            for observer in ALL_OBSERVERS
        },
        "reference_probe": np.asarray(probe, dtype=np.uint8),
        "certification_probe": (
            np.stack(certification_probe[:64]).astype(np.uint8)
            if certification_probe
            else np.empty((0, gard.n_types), dtype=np.uint8)
        ),
        "trace_lengths": np.asarray(trace_lengths, dtype=np.int16),
        "completed": np.asarray(completed_flags, dtype=np.int8),
        "future_parents": (
            np.stack(future_parents).astype(np.uint8)
            if future_parents
            else np.empty((0, gard.n_types), dtype=np.uint8)
        ),
        "future_daughters": (
            np.stack(future_daughters).astype(np.uint8)
            if future_daughters
            else np.empty((0, gard.n_types), dtype=np.uint8)
        ),
        "break_phase_counts": (
            np.stack(break_phase_counts).astype(np.uint8)
            if break_phase_counts
            else np.empty((0, phase_count, gard.n_types), dtype=np.uint8)
        ),
        "reference_parents": reference.astype(np.uint8),
        "reference_phases": phase_reference.astype(np.uint8),
        "reference_lineages": lineage_ids,
    }
    model_temporary = model_target.with_name(
        model_target.name + f".{os.getpid()}.tmp"
    )
    joblib.dump(observers, model_temporary, compress=3)
    model_temporary.replace(model_target)
    temporary = target.with_name(target.name + f".{os.getpid()}.tmp")
    joblib.dump(payload, temporary, compress=3)
    temporary.replace(target)
    (spec.output / f"{spec.stem}.json").write_text(
        json.dumps(payload["metadata"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def load_cell(path: Path) -> dict[str, Any]:
    payload = joblib.load(path)
    if payload.get("format") != "fep-surprise-15-cell-v1":
        raise ValueError(f"unsupported Experiment 1.5 cell: {path}")
    return payload


def load_observers(path: Path) -> ObserverEnsemble:
    model = joblib.load(path)
    if not isinstance(model, ObserverEnsemble):
        raise ValueError(f"unsupported observer artifact: {path}")
    return model
