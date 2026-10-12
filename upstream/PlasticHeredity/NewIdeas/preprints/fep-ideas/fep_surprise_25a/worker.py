from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from fep_surprise.tracing import TracedFission, trace_future as retained_trace_future, traced_advance
from fep_surprise_15 import observers as observer_module
from fep_surprise_2.worker import _update_trace_digest
from fep_surprise_25 import worker as base_worker
from fep_surprise_25.config import ARMS, Campaign25Config
from plastic_heredity.config import GardConfig, SimulationContract
from plastic_heredity.seeds import derive_seed
from plastic_heredity.simulator import SimulationError, generate_initial_composition

from .config import AMENDMENT_LABEL, reference_half_quota, reference_lineages


TERMINAL_CAUSE_CODES = {
    "NONE": 0,
    "EXTINCT": 1,
    "GROWTH_TIMEOUT": 2,
    "OTHER_SIMULATION_ERROR": 3,
}


class ReferenceShortfall(RuntimeError):
    """Raised before the design seal when a frozen reference quota is impossible."""


def _cause(error: SimulationError) -> str:
    message = str(error)
    if "became extinct" in message:
        return "EXTINCT"
    if "did not reach mass" in message:
        return "GROWTH_TIMEOUT"
    return "OTHER_SIMULATION_ERROR"


def trace_future_with_cause(
    initial: np.ndarray,
    beta: np.ndarray,
    config: GardConfig,
    contract: SimulationContract,
    horizon: int,
    rng: np.random.Generator,
    phase_grid: tuple[float, ...],
    fission_only: bool = False,
) -> tuple[list[TracedFission], bool, str]:
    """Trace identically to the retained simulator while preserving terminal cause."""

    if fission_only:
        traced, complete = retained_trace_future(
            initial, beta, config, contract, horizon, rng, phase_grid, True
        )
        return traced, complete, "NONE" if complete else "OTHER_SIMULATION_ERROR"
    current = np.asarray(initial, dtype=np.int64).copy()
    output: list[TracedFission] = []
    for _ in range(horizon):
        try:
            item = traced_advance(current, beta, config, contract, rng, phase_grid)
        except SimulationError as error:
            return output, False, _cause(error)
        output.append(item)
        current = item.record.daughter
    return output, True, "NONE"


def _rank(
    master_seed: str,
    spec: base_worker.Cell25Spec,
    atlas_key: str,
    lineage: int,
    fission: int,
) -> int:
    return derive_seed(
        master_seed,
        "experiment25a.amendment1.reference.selection",
        spec.matrix_id,
        spec.candidate,
        atlas_key,
        lineage,
        fission,
    )


def deterministic_reference_indices(
    lineage_ids: np.ndarray,
    fission_ids: np.ndarray,
    quota: int,
    master_seed: str,
    spec: base_worker.Cell25Spec,
    atlas_key: str,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Select equal-size parity halves without losing a contributing lineage."""

    lineages = np.asarray(lineage_ids, dtype=np.int64)
    fissions = np.asarray(fission_ids, dtype=np.int64)
    chosen_halves: list[np.ndarray] = []
    metadata: dict[str, Any] = {"available_by_half": [], "lineages_by_half": []}
    for half in (0, 1):
        available = np.flatnonzero(lineages % 2 == half)
        contributors = np.unique(lineages[available])
        metadata["available_by_half"].append(int(len(available)))
        metadata["lineages_by_half"].append(int(len(contributors)))
        if len(available) < quota:
            raise ReferenceShortfall(
                "AMENDMENT_REFERENCE_SHORTFALL_NO_VERDICT: "
                f"{atlas_key} candidate {spec.candidate} matrix {spec.matrix_id} "
                f"half {half} retained {len(available)} states; requires {quota}"
            )
        mandatory: list[int] = []
        for lineage in contributors:
            members = available[lineages[available] == lineage]
            mandatory.append(
                min(
                    members.tolist(),
                    key=lambda index: (
                        _rank(
                            master_seed,
                            spec,
                            atlas_key,
                            int(lineages[index]),
                            int(fissions[index]),
                        ),
                        int(index),
                    ),
                )
            )
        mandatory_set = set(mandatory)
        remainder = [int(index) for index in available if int(index) not in mandatory_set]
        remainder.sort(
            key=lambda index: (
                _rank(
                    master_seed,
                    spec,
                    atlas_key,
                    int(lineages[index]),
                    int(fissions[index]),
                ),
                index,
            )
        )
        selected = np.asarray(
            sorted(mandatory + remainder[: quota - len(mandatory)]), dtype=np.int64
        )
        if len(selected) != quota:
            raise AssertionError("reference selector did not fill its frozen quota")
        chosen_halves.append(selected)
    return np.concatenate(chosen_halves), metadata


def _collect_reference_amended(
    config: Campaign25Config,
    spec: base_worker.Cell25Spec,
    atlas_key: str,
    beta: np.ndarray,
    gard: GardConfig,
    digest: Any,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    scale = config.confirmation
    requested = reference_lineages(config.profile, atlas_key)
    quota = reference_half_quota(config.profile)
    parents: list[np.ndarray] = []
    phases: list[np.ndarray] = []
    lineages: list[int] = []
    fissions: list[int] = []
    lengths: list[int] = []
    complete_flags: list[bool] = []
    causes: list[str] = []
    for lineage in range(requested):
        initial = generate_initial_composition(
            gard,
            np.random.default_rng(
                derive_seed(
                    config.master_seed,
                    "experiment25a.amendment1.reference.initial",
                    spec.matrix_id,
                    spec.candidate,
                    atlas_key,
                    lineage,
                )
            ),
        )
        traced, complete, cause = trace_future_with_cause(
            initial,
            beta,
            gard,
            base_worker.SIMULATOR_CONTRACTS[spec.candidate],
            scale.reference_fissions,
            np.random.default_rng(
                derive_seed(
                    config.master_seed,
                    "experiment25a.amendment1.reference.dynamics",
                    spec.matrix_id,
                    spec.candidate,
                    atlas_key,
                    lineage,
                )
            ),
            config.phase_grid,
        )
        _update_trace_digest(digest, traced, complete)
        lengths.append(len(traced))
        complete_flags.append(bool(complete))
        causes.append(cause)
        for fission, item in enumerate(traced[scale.reference_burnin :], start=scale.reference_burnin):
            parents.append(item.record.parent.copy())
            phases.append(item.phase_compositions.copy())
            lineages.append(lineage)
            fissions.append(fission)
    if not parents:
        raise ReferenceShortfall(
            "AMENDMENT_REFERENCE_SHORTFALL_NO_VERDICT: "
            f"{atlas_key} candidate {spec.candidate} matrix {spec.matrix_id} retained no states"
        )
    parent_array = np.stack(parents)
    phase_array = np.stack(phases)
    lineage_array = np.asarray(lineages, dtype=np.int16)
    fission_array = np.asarray(fissions, dtype=np.int16)
    selected, selection = deterministic_reference_indices(
        lineage_array,
        fission_array,
        quota,
        config.master_seed,
        spec,
        atlas_key,
    )
    selected_parents = parent_array[selected]
    proportions = selected_parents.astype(np.float64)
    proportions /= np.maximum(proportions.sum(axis=1, keepdims=True), 1.0)
    positive = proportions > 0
    entropy = -np.sum(
        np.where(positive, proportions * np.log(np.maximum(proportions, 1e-300)), 0.0),
        axis=1,
    )
    cause_counts = Counter(causes)
    return (
        selected_parents,
        lineage_array[selected],
        phase_array[selected],
        {
            "amendment": AMENDMENT_LABEL,
            "requested_lineages": requested,
            "complete_lineages": int(sum(complete_flags)),
            "terminal_prefixes": int(requested - sum(complete_flags)),
            "terminal_causes": {
                name: int(cause_counts.get(name, 0))
                for name in TERMINAL_CAUSE_CODES
                if name != "NONE"
            },
            "trace_lengths": lengths,
            "raw_retained_states": int(len(parent_array)),
            "raw_retained_by_half": selection["available_by_half"],
            "contributing_lineages_by_half": selection["lineages_by_half"],
            "selected_states_by_half": [quota, quota],
            "retained_states": int(2 * quota),
            "selection_rule": "lineage-preserving-hash-rank-v1",
            "mean_dominant_molecule_fraction": float(
                np.mean(np.max(proportions, axis=1))
            ),
            "mean_effective_species": float(np.mean(np.exp(entropy))),
        },
    )


def _fit_observer_amended(
    parent_counts: np.ndarray,
    phase_counts: np.ndarray,
    lineage_ids: np.ndarray,
    *,
    pseudocount: float,
    reference_mass: float,
    pca_variance: float,
    pca_min: int,
    pca_max: int,
    knn_k: int,
    mixture_k_max: int,
    training_subsample: int,
    seed: int,
) -> observer_module.ObserverEnsemble:
    """Fit the two observers on the registered numeric lineage parities."""

    parents = np.asarray(parent_counts)
    phases = np.asarray(phase_counts)
    lineages = np.asarray(lineage_ids)
    if len(parents) != len(phases) or len(parents) != len(lineages):
        raise ValueError("amended reference arrays do not align")
    halves = []
    minimum_lineages = 4 if training_subsample >= 600 else 2
    for half in (0, 1):
        training = lineages % 2 == half
        calibration = lineages % 2 == 1 - half
        if len(np.unique(lineages[training])) < minimum_lineages or not calibration.any():
            raise ReferenceShortfall(
                "AMENDMENT_REFERENCE_SHORTFALL_NO_VERDICT: "
                f"reference half {half} lacks {minimum_lineages} contributing lineages"
            )
        halves.append(
            observer_module._fit_half(
                parents[training],
                lineages[training],
                phases[calibration],
                pseudocount=pseudocount,
                reference_mass=reference_mass,
                pca_variance=pca_variance,
                pca_min=pca_min,
                pca_max=pca_max,
                knn_k=knn_k,
                mixture_k_max=mixture_k_max,
                training_subsample=training_subsample,
                seed=seed + half,
            )
        )
    return observer_module.ObserverEnsemble((halves[0], halves[1]))


def prepare_cell(spec: base_worker.Cell25Spec, config: Campaign25Config) -> Path:
    if (
        spec.design_path.exists()
        and spec.atlas_path.exists()
        and spec.metadata_path.exists()
        and not spec.force
    ):
        return spec.design_path
    original = base_worker._collect_reference
    original_fit = base_worker.fit_observer_ensemble
    base_worker._collect_reference = _collect_reference_amended
    base_worker.fit_observer_ensemble = _fit_observer_amended
    try:
        path = base_worker.prepare_cell(spec, config)
    finally:
        base_worker._collect_reference = original
        base_worker.fit_observer_ensemble = original_fit
    design = joblib.load(path)
    design["metadata"]["amendment"] = AMENDMENT_LABEL
    design["metadata"]["source_screen_reused_read_only"] = True
    base_worker._atomic_dump(design, path)
    sidecar = {
        **design["metadata"],
        "format": design["format"],
        "design_hash": joblib.hash(design),
    }
    temporary = spec.metadata_path.with_name(spec.metadata_path.name + ".tmp")
    temporary.write_text(
        json.dumps(sidecar, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(spec.metadata_path)
    return path


def run_futures(spec: base_worker.Cell25Spec, config: Campaign25Config) -> Path:
    if spec.future_path.exists() and not spec.force:
        return spec.future_path
    calls: list[tuple[bool, str, int]] = []
    original = base_worker.trace_future

    def traced(*args: Any, **kwargs: Any) -> tuple[list[TracedFission], bool]:
        values, complete, cause = trace_future_with_cause(*args, **kwargs)
        calls.append((complete, cause, len(values)))
        return values, complete

    base_worker.trace_future = traced
    try:
        path = base_worker.run_futures(spec, config)
    finally:
        base_worker.trace_future = original
    payload = joblib.load(path)
    shape = payload["complete"].shape
    main_causes = np.zeros(shape, dtype=np.int8)
    durability_causes = np.zeros(shape, dtype=np.int8)
    cursor = 0
    for landmark_index in range(shape[0]):
        for branch in range(shape[2]):
            native_code = 0
            for arm_index, arm in enumerate(ARMS):
                if arm == "ISOMORPHIC_BOTH_100":
                    main_causes[landmark_index, arm_index, branch] = native_code
                    continue
                _, cause, _ = calls[cursor]
                cursor += 1
                code = TERMINAL_CAUSE_CODES[cause]
                main_causes[landmark_index, arm_index, branch] = code
                if arm == "ALIGNED_NATIVE":
                    native_code = code
    for landmark_index in range(shape[0]):
        for arm_index, arm in enumerate(ARMS):
            followed = np.flatnonzero(payload["durability_followed"][landmark_index, arm_index])
            if arm == "ISOMORPHIC_BOTH_100":
                durability_causes[landmark_index, arm_index, followed] = (
                    durability_causes[landmark_index, 0, followed]
                )
                continue
            for branch in followed:
                _, cause, _ = calls[cursor]
                cursor += 1
                durability_causes[landmark_index, arm_index, branch] = TERMINAL_CAUSE_CODES[cause]
    if cursor != len(calls):
        raise AssertionError(f"unmapped future trace calls: {cursor} of {len(calls)}")
    payload["metadata"]["amendment"] = AMENDMENT_LABEL
    payload["metadata"]["terminal_cause_codes"] = TERMINAL_CAUSE_CODES
    payload["terminal_cause"] = main_causes
    payload["durability_terminal_cause"] = durability_causes
    base_worker._atomic_dump(payload, path)
    return path


Cell25Spec = base_worker.Cell25Spec
load_atlases = base_worker.load_atlases
load_design = base_worker.load_design
load_futures = base_worker.load_futures


__all__ = [
    "Cell25Spec",
    "ReferenceShortfall",
    "TERMINAL_CAUSE_CODES",
    "deterministic_reference_indices",
    "load_atlases",
    "load_design",
    "load_futures",
    "prepare_cell",
    "run_futures",
    "trace_future_with_cause",
]
