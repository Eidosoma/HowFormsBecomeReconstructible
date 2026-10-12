from __future__ import annotations

import hashlib
import json
import os
import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from . import compat as _compat  # noqa: F401
from .config import CampaignConfig, CohortScale
from .dynamics import meanfield_forms, nearest_form_distance, rq_alignment
from .landscape import (
    LandscapeEnsemble,
    PhaseConditionalEnsemble,
    fit_fixed_target_landscape,
    fit_landscape_ensemble,
    fit_phase_conditional_ensemble,
    nearest_atlas_distance,
)
from .tracing import TracedFission, trace_future
from plastic_heredity.config import CANDIDATES, GardConfig
from plastic_heredity.regime_confirmation import evaluate_regime
from plastic_heredity.seeds import derive_seed
from plastic_heredity.simulator import generate_beta, generate_initial_composition


HOMOGENEOUS_VALUE = float(np.exp(4.0))
ESTIMATORS = ("mixture", "knn")
BASELINE_FEATURE_NAMES = (
    *(f"h_lag_{index}" for index in range(10)),
    "history_length",
    "break_fraction",
    "landmark_fraction",
    "parent_mass",
    "daughter_mass",
    "growth_steps",
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
SURPRISE_FEATURE_NAMES = (
    "surprise_parent",
    "surprise_daughter",
    "surprise_fission_jump",
    "growth_surprise_start",
    "growth_surprise_end",
    "growth_surprise_delta",
    "growth_surprise_auc",
)


@dataclass(frozen=True)
class CellSpec:
    stage: str
    matrix_id: int
    candidate: str
    mechanism: str
    output: Path
    save_landscape: bool = False
    force: bool = False


def _rng(master: str, domain: str, *parts: object) -> np.random.Generator:
    return np.random.default_rng(derive_seed(master, domain, *parts))


def _active_beta(source: np.ndarray, mechanism: str) -> np.ndarray:
    if mechanism == "NATURAL_GARD":
        return source
    if mechanism in ("HOMOGENEOUS_GENERATIVE", "FISSION_ONLY_GENERATIVE"):
        return np.full_like(source, HOMOGENEOUS_VALUE)
    raise ValueError(mechanism)


def _collect_reference(
    config: CampaignConfig,
    scale: CohortScale,
    stage: str,
    matrix_id: int,
    candidate: str,
    mechanism: str,
    beta: np.ndarray,
    gard: GardConfig,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    contract = CANDIDATES[candidate]
    fission_only = mechanism == "FISSION_ONLY_GENERATIVE"
    counts: list[np.ndarray] = []
    phase_counts: list[np.ndarray] = []
    lineage_ids: list[int] = []
    attempts_used = []
    for lineage in range(scale.reference_lineages):
        initial = generate_initial_composition(
            gard,
            _rng(
                config.master_seed,
                f"{stage}.reference.initial",
                matrix_id,
                candidate,
                lineage,
            ),
        )
        traced = None
        for attempt in range(100):
            stream = _rng(
                config.master_seed,
                f"{stage}.reference.dynamics",
                candidate,
                matrix_id,
                lineage,
                attempt,
            )
            items, complete = trace_future(
                initial,
                beta,
                gard,
                contract,
                scale.reference_fissions,
                stream,
                config.phase_grid,
                fission_only=fission_only,
            )
            if complete:
                traced = items
                attempts_used.append(attempt)
                break
        if traced is None:
            attempts_used.append(100)
            continue
        for item in traced[scale.reference_burnin :]:
            counts.append(item.record.parent.copy())
            phase_counts.append(item.phase_compositions.copy())
            lineage_ids.append(lineage)
    if not counts:
        raise RuntimeError("no viable reference states")
    return (
        np.stack(counts),
        np.asarray(lineage_ids, dtype=np.int16),
        np.stack(phase_counts),
        {
            "requested_lineages": scale.reference_lineages,
            "completed_lineages": int(len(set(lineage_ids))),
            "attempts_used": attempts_used,
            "states": len(counts),
        },
    )


def _fit_landscape(
    config: CampaignConfig,
    counts: np.ndarray,
    lineages: np.ndarray,
    stage: str,
    matrix_id: int,
    candidate: str,
    mechanism: str,
) -> LandscapeEnsemble:
    seed = derive_seed(
        config.master_seed,
        f"{stage}.landscape.fit",
        mechanism,
        candidate,
        matrix_id,
    ) % (2**32 - 1)
    return fit_landscape_ensemble(
        counts,
        lineages,
        pseudocount=config.pseudocount,
        pca_variance=config.pca_variance,
        pca_min=config.pca_min,
        pca_max=config.pca_max,
        k_max=config.mixture_k_max,
        knn_k=config.knn_k,
        subsample=config.landscape_subsample_per_half,
        seed=int(seed),
    )


def _independent_reference_probe(
    config: CampaignConfig,
    scale: CohortScale,
    spec: CellSpec,
    beta: np.ndarray,
    gard: GardConfig,
) -> np.ndarray:
    """Fresh viable parents used only for native-versus-wrong-beta scoring."""

    initial = generate_initial_composition(
        gard,
        _rng(
            config.master_seed,
            f"{spec.stage}.reference_probe.initial",
            spec.matrix_id,
            spec.candidate,
        ),
    )
    horizon = max(96, min(200, scale.reference_fissions))
    burnin = min(32, horizon // 3)
    for attempt in range(100):
        items, complete = trace_future(
            initial,
            beta,
            gard,
            CANDIDATES[spec.candidate],
            horizon,
            _rng(
                config.master_seed,
                f"{spec.stage}.reference_probe.dynamics",
                spec.candidate,
                spec.matrix_id,
                attempt,
            ),
            (0.0, 1.0),
            fission_only=spec.mechanism == "FISSION_ONLY_GENERATIVE",
        )
        if complete:
            return np.stack(
                [item.record.parent for item in items[burnin : burnin + 64]]
            )
    raise RuntimeError("independent reference probe failed after 100 attempts")


def _meanfield_for_cell(
    spec: CellSpec,
    config: CampaignConfig,
    beta: np.ndarray,
    gard: GardConfig,
) -> np.ndarray:
    auxiliary = spec.output / "auxiliary"
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
            mf_starts, mf_iterations = 8, 500
        elif config.profile == "quick":
            mf_starts, mf_iterations = 4, 200
        else:
            mf_starts, mf_iterations = 2, 50
        forms = meanfield_forms(
            beta,
            gard,
            starts=mf_starts,
            iterations=mf_iterations,
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
    # Two candidate workers may race; both values are deterministic.
    temporary.replace(target)
    return forms


def _main_path(
    config: CampaignConfig,
    scale: CohortScale,
    stage: str,
    matrix_id: int,
    candidate: str,
    mechanism: str,
    beta: np.ndarray,
    initial: np.ndarray,
    gard: GardConfig,
) -> tuple[list[TracedFission], int]:
    contract = CANDIDATES[candidate]
    fission_only = mechanism == "FISSION_ONLY_GENERATIVE"
    for attempt in range(100):
        # Mechanism is intentionally absent: common random streams.
        stream = _rng(
            config.master_seed,
            f"{stage}.main_path",
            candidate,
            matrix_id,
            attempt,
        )
        items, complete = trace_future(
            initial,
            beta,
            gard,
            contract,
            scale.main_generations,
            stream,
            config.phase_grid,
            fission_only=fission_only,
        )
        if complete:
            return items, attempt
    raise RuntimeError("main path failed after 100 attempts")


def _future(
    config: CampaignConfig,
    scale: CohortScale,
    stage: str,
    matrix_id: int,
    candidate: str,
    mechanism: str,
    landmark: int,
    branch: int,
    beta: np.ndarray,
    initial: np.ndarray,
    gard: GardConfig,
) -> tuple[list[TracedFission], bool]:
    # Mechanism is intentionally absent: common random streams.
    stream = _rng(
        config.master_seed,
        f"{stage}.future",
        candidate,
        matrix_id,
        landmark,
        branch,
    )
    return trace_future(
        initial,
        beta,
        gard,
        CANDIDATES[candidate],
        scale.horizon,
        stream,
        config.phase_grid,
        fission_only=mechanism == "FISSION_ONLY_GENERATIVE",
    )


def _score_trace(
    traced: list[TracedFission],
    landscape: LandscapeEnsemble,
    estimator: str,
    phase_conditional: PhaseConditionalEnsemble | None = None,
) -> dict[str, np.ndarray]:
    parents = np.stack([item.record.parent for item in traced])
    daughters = np.stack([item.record.daughter for item in traced])
    phases = np.stack([item.phase_compositions for item in traced])
    shape = phases.shape
    result = {
        "parent": landscape.score(parents, estimator),
        "daughter": landscape.score(daughters, estimator),
        "phase": landscape.score(phases.reshape(-1, shape[-1]), estimator).reshape(
            shape[:2]
        ),
        "parent_halves": landscape.score_halves(parents, estimator),
        "daughter_halves": landscape.score_halves(daughters, estimator),
        "phase_halves": landscape.score_halves(
            phases.reshape(-1, shape[-1]), estimator
        ).reshape(shape[0], shape[1], 2),
    }
    if phase_conditional is not None:
        result["phase_conditioned"] = phase_conditional.score(phases)
    return result


def _baseline_features(
    traced: list[TracedFission],
    break_index: int,
    landmark: int,
    scale: CohortScale,
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
    atlas = nearest_atlas_distance(np.stack([parent, daughter, start, end]), atlas_centers)
    rq = np.asarray(
        [rq_alignment(value, beta, gard) for value in (parent, daughter, start, end)]
    )
    meanfield = nearest_form_distance(np.stack([parent, daughter, start, end]), forms)
    tail = np.asarray(
        [
            len(history),
            (break_index + 1) / scale.horizon,
            landmark / scale.main_generations,
            float(parent.sum()),
            float(daughter.sum()),
            item.record.growth_steps,
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
    out = np.concatenate([padded, tail])
    if len(out) != len(BASELINE_FEATURE_NAMES):
        raise AssertionError("baseline feature schema mismatch")
    return out


def _surprise_features(scores: dict[str, np.ndarray], break_index: int) -> np.ndarray:
    parent = scores["parent"][break_index]
    daughter = scores["daughter"][break_index]
    profile = scores["phase"][break_index]
    out = np.asarray(
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
    return out


def _empty_rows() -> dict[str, list[Any]]:
    return {
        "landmark": [],
        "branch": [],
        "half": [],
        "outcome": [],
        "first_break": [],
        "completed": [],
        "baseline": [],
        "mixture": [],
        "knn": [],
        "fixed": [],
    }


def _cycle_row(
    scores: dict[str, np.ndarray],
    traced: list[TracedFission],
    break_index: int,
    positive: bool,
    onset: int,
) -> dict[str, float]:
    parent = scores["parent"]
    daughter = scores["daughter"]
    phase = scores["phase"]
    hs = np.asarray([item.record.h for item in traced])
    shock = daughter - parent
    growth = parent - phase[:, 0]
    breaks = hs <= 0.9
    inherited = ~breaks
    break_excess = (
        float(np.mean(shock[breaks]) - np.mean(shock[inherited]))
        if breaks.any() and inherited.any()
        else np.nan
    )
    recovery = np.nan
    postbreak_daughters = np.nan
    if break_index >= 0 and break_index + 9 <= len(traced):
        anchor = daughter[break_index]
        recovery = float(np.mean(parent[break_index + 1 : break_index + 9] - anchor))
        postbreak_daughters = float(np.mean(daughter[break_index + 1 : break_index + 9]))
    certification = np.nan
    if positive and onset >= 0 and onset + 8 <= len(traced):
        certification = float(np.mean(daughter[onset : onset + 8]))
    return {
        "shock": float(np.mean(shock)),
        "growth": float(np.mean(growth)),
        "break_excess": break_excess,
        "postbreak_recovery": recovery,
        "postbreak_daughters": postbreak_daughters,
        "certification": certification,
        "positive": float(positive),
        "phase_profile": np.mean(phase, axis=0).tolist(),
        "phase_conditioned_profile": (
            np.mean(scores["phase_conditioned"], axis=0).tolist()
            if "phase_conditioned" in scores
            else None
        ),
    }


def _scientific_digest_update(digest: hashlib._Hash, traced: list[TracedFission], complete: bool) -> None:
    digest.update(bytes([int(complete)]))
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


def run_cell(spec: CellSpec, config: CampaignConfig) -> Path:
    spec.output.mkdir(parents=True, exist_ok=True)
    target = spec.output / (
        f"cell_{spec.stage}_{spec.mechanism}_c{spec.candidate}_m{spec.matrix_id:04d}.joblib"
    )
    if target.exists() and not spec.force:
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
    reference, lineage_ids, phase_reference, reference_meta = _collect_reference(
        config,
        scale,
        spec.stage,
        spec.matrix_id,
        spec.candidate,
        spec.mechanism,
        beta,
        gard,
    )
    minimum = min(
        config.minimum_reference_states_full,
        scale.reference_lineages * (scale.reference_fissions - scale.reference_burnin),
    )
    if len(reference) < minimum:
        raise RuntimeError(f"reference pool has {len(reference)} states, needs {minimum}")
    landscape = _fit_landscape(
        config,
        reference,
        lineage_ids,
        spec.stage,
        spec.matrix_id,
        spec.candidate,
        spec.mechanism,
    )
    phase_conditional = fit_phase_conditional_ensemble(
        phase_reference, lineage_ids, landscape
    )
    fixed = fit_fixed_target_landscape(landscape)
    forms = _meanfield_for_cell(spec, config, beta, gard)
    main, main_attempt = _main_path(
        config,
        scale,
        spec.stage,
        spec.matrix_id,
        spec.candidate,
        spec.mechanism,
        beta,
        initial,
        gard,
    )
    rows = _empty_rows()
    cycles: dict[str, list[dict[str, Any]]] = {name: [] for name in ESTIMATORS}
    half_cycles: dict[str, list[list[dict[str, Any]]]] = {
        name: [[], []] for name in ESTIMATORS
    }
    digest = hashlib.sha256()
    cert_probes: list[np.ndarray] = []
    for landmark in scale.landmarks:
        restored = main[landmark - 1].record.daughter
        for branch in range(scale.branches):
            traced, complete = _future(
                config,
                scale,
                spec.stage,
                spec.matrix_id,
                spec.candidate,
                spec.mechanism,
                landmark,
                branch,
                beta,
                restored,
                gard,
            )
            _scientific_digest_update(digest, traced, complete)
            records = [item.record for item in traced]
            outcome = evaluate_regime(records)
            score_map = {
                estimator: _score_trace(
                    traced, landscape, estimator, phase_conditional=phase_conditional
                )
                for estimator in ESTIMATORS
            }
            fixed_scores = _score_trace(traced, fixed, "mixture")
            for estimator, scores in score_map.items():
                cycles[estimator].append(
                    {
                        "landmark": landmark,
                        "branch": branch,
                        "half": "A" if branch < scale.branches // 2 else "B",
                        **_cycle_row(
                            scores,
                            traced,
                            outcome.first_break_index,
                            outcome.primary_all8,
                            outcome.primary_all8_onset,
                        ),
                    }
                )
                for half_index in range(2):
                    half_score = {
                        "parent": scores["parent_halves"][:, half_index],
                        "daughter": scores["daughter_halves"][:, half_index],
                        "phase": scores["phase_halves"][:, :, half_index],
                    }
                    half_cycles[estimator][half_index].append(
                        _cycle_row(
                            half_score,
                            traced,
                            outcome.first_break_index,
                            outcome.primary_all8,
                            outcome.primary_all8_onset,
                        )
                    )
            b = outcome.first_break_index
            if b >= 0 and b + 9 <= len(traced):
                rows["landmark"].append(landmark)
                rows["branch"].append(branch)
                rows["half"].append(0 if branch < scale.branches // 2 else 1)
                rows["outcome"].append(int(outcome.primary_all8))
                rows["first_break"].append(b)
                rows["completed"].append(int(complete))
                rows["baseline"].append(
                    _baseline_features(
                        traced,
                        b,
                        landmark,
                        scale,
                        beta,
                        gard,
                        landscape.atlas_centers,
                        forms,
                    )
                )
                rows["mixture"].append(_surprise_features(score_map["mixture"], b))
                rows["knn"].append(_surprise_features(score_map["knn"], b))
                rows["fixed"].append(_surprise_features(fixed_scores, b))
            if outcome.primary_all8 and outcome.primary_all8_onset >= 0:
                start = outcome.primary_all8_onset
                cert_probes.extend(item.record.daughter.copy() for item in traced[start : start + 8])

    reference_probe = (
        _independent_reference_probe(config, scale, spec, beta, gard)
        if spec.mechanism == "NATURAL_GARD"
        else reference[: min(64, len(reference))].copy()
    )
    payload: dict[str, Any] = {
        "format": "fep-surprise-cell-v1",
        "metadata": {
            "stage": spec.stage,
            "profile": config.profile,
            "matrix_id": spec.matrix_id,
            "candidate": spec.candidate,
            "mechanism": spec.mechanism,
            "main_attempt": main_attempt,
            "reference": reference_meta,
            "selected_k": [half.selected_k for half in landscape.halves],
            "pca_dimensions": [len(half.projection.scale_mean) for half in landscape.halves],
            "meanfield_forms": len(forms),
            "scientific_digest": digest.hexdigest(),
        },
        "cycle": cycles,
        "half_cycle": half_cycles,
        "prediction": {
            name: np.asarray(values)
            for name, values in rows.items()
            if name not in ("baseline", "mixture", "knn", "fixed")
        },
        "reference_probe": reference_probe,
        "certification_probe": np.stack(cert_probes[:64])
        if cert_probes
        else np.empty((0, gard.n_types), dtype=np.int64),
        "baseline": np.stack(rows["baseline"])
        if rows["baseline"]
        else np.empty((0, len(BASELINE_FEATURE_NAMES))),
        "mixture": np.stack(rows["mixture"])
        if rows["mixture"]
        else np.empty((0, len(SURPRISE_FEATURE_NAMES))),
        "knn": np.stack(rows["knn"])
        if rows["knn"]
        else np.empty((0, len(SURPRISE_FEATURE_NAMES))),
        "fixed": np.stack(rows["fixed"])
        if rows["fixed"]
        else np.empty((0, len(SURPRISE_FEATURE_NAMES))),
    }
    temporary = target.with_suffix(".joblib.tmp")
    joblib.dump(payload, temporary, compress=3)
    temporary.replace(target)
    if spec.save_landscape:
        model_target = target.with_name(target.stem + "_landscape.joblib")
        model_temporary = model_target.with_suffix(".joblib.tmp")
        scoring_landscape = copy.deepcopy(landscape)
        for half in scoring_landscape.halves:
            # These raw reference counts are needed to construct the K=1
            # comparator above, but not to score native/wrong-beta probes.
            half.training_counts = np.empty((0, gard.n_types), dtype=np.int16)
            half.calibration_counts = np.empty((0, gard.n_types), dtype=np.int16)
        joblib.dump(scoring_landscape, model_temporary, compress=3)
        model_temporary.replace(model_target)
    summary = target.with_suffix(".json")
    summary.write_text(json.dumps(payload["metadata"], indent=2, sort_keys=True) + "\n")
    return target


def load_cell(path: Path) -> dict[str, Any]:
    value = joblib.load(path)
    if value.get("format") != "fep-surprise-cell-v1":
        raise ValueError(f"unsupported cell artifact: {path}")
    return value
