from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from fep_surprise_15 import compat as _compat  # noqa: F401
from fep_surprise_15.observers import (
    INVARIANT_KNN,
    SHELF,
    ObserverEnsemble,
    fit_observer_ensemble,
)
from fep_surprise.dynamics import expected_flux, rq_alignment
from fep_surprise.tracing import TracedFission, trace_future
from plastic_heredity.config import CANDIDATES as SIMULATOR_CONTRACTS
from plastic_heredity.config import GardConfig
from plastic_heredity.regime_confirmation import evaluate_regime
from plastic_heredity.seeds import derive_seed
from plastic_heredity.simulator import generate_beta, generate_initial_composition

from .atlas import AtlasRegistry, destination_label, mismatch_jump, shelf_profile
from .config import ARMS, Campaign2Config, Stage2Scale
from .interventions import (
    LAUNCH_METRIC_NAMES,
    arm_launches,
    beta_variants,
    launch_metrics,
    nested_swap_orders,
)


BASELINE_FEATURE_NAMES = (
    "landmark_fraction",
    "state_mass",
    "occupied_types",
    "composition_entropy",
    "last_h",
    "recent_mean_h",
    "recent_break_fraction",
    "log_catalytic_throughput",
    "expected_flux_norm",
    "rq_alignment",
    "native_shelf_distance",
)
ACTUAL_ATLASES = ("native", "morph_025", "morph_050", "morph_075")


@dataclass(frozen=True)
class Cell2Spec:
    stage: str
    matrix_id: int
    candidate: str
    output: Path
    force: bool = False

    @property
    def stem(self) -> str:
        return f"cell_{self.stage}_c{self.candidate}_m{self.matrix_id:04d}"

    @property
    def design_path(self) -> Path:
        return self.output / f"{self.stem}_design.joblib"

    @property
    def atlas_path(self) -> Path:
        return self.output / f"{self.stem}_atlases.joblib"

    @property
    def future_path(self) -> Path:
        return self.output / f"{self.stem}_futures.joblib"

    @property
    def metadata_path(self) -> Path:
        return self.output / f"{self.stem}.json"


def _scale(config: Campaign2Config, stage: str) -> Stage2Scale:
    if stage == "development":
        return config.development
    if stage == "confirmation":
        return config.confirmation
    raise ValueError(stage)


def _rng(master: str, domain: str, *parts: object) -> np.random.Generator:
    return np.random.default_rng(derive_seed(master, domain, *parts))


def _atomic_dump(value: Any, target: Path) -> None:
    temporary = target.with_name(target.name + f".{os.getpid()}.tmp")
    joblib.dump(value, temporary, compress=3)
    temporary.replace(target)


def _update_trace_digest(
    digest: Any,
    traced: list[TracedFission],
    complete: bool,
    order: np.ndarray | None = None,
) -> None:
    digest.update(bytes([int(complete)]))
    digest.update(np.asarray([len(traced)], dtype=np.int16).tobytes())
    for item in traced:
        values = (
            item.record.parent,
            item.record.daughter,
            np.asarray([item.record.h], dtype=np.float64),
            np.asarray([item.record.growth_steps], dtype=np.int64),
            item.phase_compositions,
        )
        for index, value in enumerate(values):
            array = np.asarray(value)
            if order is not None and index in (0, 1, 4):
                array = array[..., order]
            digest.update(np.ascontiguousarray(array).tobytes())


def _collect_reference(
    config: Campaign2Config,
    scale: Stage2Scale,
    spec: Cell2Spec,
    atlas_key: str,
    beta: np.ndarray,
    gard: GardConfig,
    digest: Any,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    parents: list[np.ndarray] = []
    phases: list[np.ndarray] = []
    lineage_ids: list[int] = []
    attempts_used: list[int] = []
    contract = SIMULATOR_CONTRACTS[spec.candidate]
    for lineage in range(scale.reference_lineages):
        initial = generate_initial_composition(
            gard,
            _rng(
                config.master_seed,
                f"{spec.stage}.reference.initial",
                spec.matrix_id,
                spec.candidate,
                atlas_key,
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
                    spec.matrix_id,
                    spec.candidate,
                    atlas_key,
                    lineage,
                    attempt,
                ),
                config.phase_grid,
            )
            if complete:
                accepted = traced
                attempts_used.append(attempt)
                _update_trace_digest(digest, traced, True)
                break
        if accepted is None:
            attempts_used.append(100)
            continue
        for item in accepted[scale.reference_burnin :]:
            parents.append(item.record.parent.copy())
            phases.append(item.phase_compositions.copy())
            lineage_ids.append(lineage)
    if len(parents) < scale.minimum_reference_states:
        raise RuntimeError(
            f"{atlas_key} reference pool has {len(parents)} states; "
            f"requires {scale.minimum_reference_states}"
        )
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


def _fit_atlas(
    config: Campaign2Config,
    spec: Cell2Spec,
    atlas_key: str,
    parents: np.ndarray,
    lineages: np.ndarray,
    phases: np.ndarray,
) -> ObserverEnsemble:
    seed = derive_seed(
        config.master_seed,
        f"{spec.stage}.atlas.fit",
        spec.matrix_id,
        spec.candidate,
        atlas_key,
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
        training_subsample=_scale(config, spec.stage).training_subsample,
        seed=int(seed),
    )


def _main_path(
    config: Campaign2Config,
    scale: Stage2Scale,
    spec: Cell2Spec,
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
            SIMULATOR_CONTRACTS[spec.candidate],
            scale.main_generations,
            _rng(
                config.master_seed,
                f"{spec.stage}.main_path",
                spec.matrix_id,
                spec.candidate,
                attempt,
            ),
            config.phase_grid,
        )
        if complete:
            _update_trace_digest(digest, traced, True)
            return traced, attempt
    raise RuntimeError("native main path failed after 100 attempts")


def _entropy(counts: np.ndarray) -> float:
    values = np.asarray(counts, dtype=np.float64)
    probability = values / max(float(values.sum()), 1.0)
    selected = probability > 0
    return float(-np.sum(probability[selected] * np.log(probability[selected])))


def _baseline_features(
    traced: list[TracedFission],
    landmark: int,
    scale: Stage2Scale,
    beta: np.ndarray,
    gard: GardConfig,
    native: ObserverEnsemble,
) -> np.ndarray:
    restored = traced[landmark - 1].record.daughter
    history = np.asarray(
        [item.record.h for item in traced[max(0, landmark - 4) : landmark]],
        dtype=np.float64,
    )
    vector = np.asarray(restored, dtype=np.float64)
    normalized = vector / max(float(np.linalg.norm(vector)), 1e-12)
    shelf_centers = native.atlas_centers
    throughput = max(float(vector @ beta @ vector), 1e-300)
    output = np.asarray(
        [
            landmark / scale.main_generations,
            float(vector.sum()),
            float(np.count_nonzero(vector)),
            _entropy(vector),
            float(history[-1]),
            float(np.mean(history)),
            float(np.mean(history <= 0.9)),
            float(np.log(throughput)),
            float(np.linalg.norm(expected_flux(vector, beta, gard))),
            rq_alignment(vector, beta, gard),
            float(1.0 - np.max(normalized @ shelf_centers.T)),
        ],
        dtype=np.float64,
    )
    if len(output) != len(BASELINE_FEATURE_NAMES):
        raise AssertionError("Experiment 2 baseline schema mismatch")
    return output


def prepare_cell(spec: Cell2Spec, config: Campaign2Config) -> Path:
    """Generate beta, independent atlases, native landmarks, and frozen doses."""

    spec.output.mkdir(parents=True, exist_ok=True)
    if (
        spec.design_path.exists()
        and spec.atlas_path.exists()
        and spec.metadata_path.exists()
        and not spec.force
    ):
        return spec.design_path
    scale = _scale(config, spec.stage)
    gard = GardConfig(generations=scale.main_generations)
    beta = generate_beta(
        gard,
        _rng(config.master_seed, f"{spec.stage}.beta", spec.matrix_id),
    )
    order_seed = derive_seed(
        config.master_seed, f"{spec.stage}.nested_swaps", spec.matrix_id
    ) % (2**32 - 1)
    orders = nested_swap_orders(gard.n_types, int(order_seed))
    variants = beta_variants(beta, orders)
    initial = generate_initial_composition(
        gard,
        _rng(config.master_seed, f"{spec.stage}.main.initial", spec.matrix_id),
    )
    digest = hashlib.sha256()
    for value in (beta, initial, *orders.values()):
        digest.update(np.ascontiguousarray(value).tobytes())

    actual: dict[str, ObserverEnsemble] = {}
    reference_meta: dict[str, Any] = {}
    for atlas_key in ACTUAL_ATLASES:
        parents, lineages, phases, metadata = _collect_reference(
            config,
            scale,
            spec,
            atlas_key,
            variants[atlas_key],
            gard,
            digest,
        )
        actual[atlas_key] = _fit_atlas(
            config, spec, atlas_key, parents, lineages, phases
        )
        reference_meta[atlas_key] = metadata
    registry = AtlasRegistry(actual=actual, permutation_orders=orders)
    main, main_attempt = _main_path(
        config, scale, spec, beta, initial, gard, digest
    )

    restored = np.stack(
        [main[landmark - 1].record.daughter for landmark in scale.landmarks]
    )
    baselines = np.stack(
        [
            _baseline_features(main, landmark, scale, beta, gard, actual["native"])
            for landmark in scale.landmarks
        ]
    )
    metrics = np.empty(
        (len(scale.landmarks), len(ARMS), len(LAUNCH_METRIC_NAMES)),
        dtype=np.float64,
    )
    jumps = {
        observer: np.empty((len(scale.landmarks), len(ARMS), 2), dtype=np.float64)
        for observer in (INVARIANT_KNN, SHELF)
    }
    profiles: list[list[dict[str, Any]]] = []
    for landmark_index, state in enumerate(restored):
        launches = arm_launches(beta, state, orders)
        row_profiles = []
        for arm_index, arm in enumerate(ARMS):
            launch = launches[arm]
            target = registry.get(launch.atlas_key)
            metrics[landmark_index, arm_index] = launch_metrics(
                beta,
                state,
                launch,
                gard,
                SIMULATOR_CONTRACTS[spec.candidate],
            )
            jump = mismatch_jump(
                actual["native"], target, state, launch.composition, 0
            )
            for observer in jumps:
                jumps[observer][landmark_index, arm_index] = jump[observer]
            row_profiles.append(
                shelf_profile(
                    target,
                    launch.composition,
                    minimum_cosine=config.shelf_stability_cosine,
                )
            )
        profiles.append(row_profiles)

    atlas_hash = joblib.hash(registry)
    design: dict[str, Any] = {
        "format": "fep-surprise-2-design-cell-v1",
        "metadata": {
            "stage": spec.stage,
            "profile": config.profile,
            "matrix_id": spec.matrix_id,
            "candidate": spec.candidate,
            "main_attempt": main_attempt,
            "reference": reference_meta,
            "atlas_hash": atlas_hash,
            "scientific_digest": digest.hexdigest(),
            "actual_atlases": list(ACTUAL_ATLASES),
            "selected_k": {
                key: [half.selected_k for half in model.halves]
                for key, model in actual.items()
            },
            "pca_dimensions": {
                key: [len(half.projection.coordinate_mean) for half in model.halves]
                for key, model in actual.items()
            },
        },
        "beta": beta,
        "orders": orders,
        "landmarks": np.asarray(scale.landmarks, dtype=np.int16),
        "restored": restored,
        "baseline": baselines,
        "launch_metrics": metrics,
        "mismatch_jump": jumps,
        "shelf_profiles": profiles,
        "baseline_feature_names": BASELINE_FEATURE_NAMES,
        "launch_metric_names": LAUNCH_METRIC_NAMES,
        "arms": ARMS,
    }
    _atomic_dump(registry, spec.atlas_path)
    _atomic_dump(design, spec.design_path)
    sidecar = {
        **design["metadata"],
        "format": design["format"],
        "design_hash": joblib.hash(design),
    }
    temporary = spec.metadata_path.with_name(
        spec.metadata_path.name + f".{os.getpid()}.tmp"
    )
    temporary.write_text(
        json.dumps(sidecar, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(spec.metadata_path)
    return spec.design_path


def _f12(records: list[Any]) -> bool:
    inherited = np.asarray([item.h > 0.9 for item in records[:12]], dtype=bool)
    breaks = np.flatnonzero(~inherited)
    if not len(breaks):
        return False
    first = int(breaks[0])
    for start in range(first + 1, len(inherited) - 2):
        if bool(inherited[start : start + 3].all()):
            return True
    return False


def run_futures(spec: Cell2Spec, config: Campaign2Config) -> Path:
    """Shoot outcome streams from the already frozen cell design."""

    if spec.future_path.exists() and not spec.force:
        return spec.future_path
    design = load_design(spec.design_path)
    registry = load_atlases(spec.atlas_path)
    if joblib.hash(registry) != design["metadata"]["atlas_hash"]:
        raise ValueError("atlas artifact differs from frozen design")
    scale = _scale(config, spec.stage)
    gard = GardConfig(generations=scale.main_generations)
    beta = np.asarray(design["beta"])
    orders = {int(key): np.asarray(value) for key, value in design["orders"].items()}
    shape = (len(scale.landmarks), len(ARMS), scale.branches)
    strict8 = np.zeros(shape, dtype=np.int8)
    f12 = np.zeros(shape, dtype=np.int8)
    first_break = np.full(shape, -1, dtype=np.int16)
    complete = np.zeros(shape, dtype=np.int8)
    lengths = np.zeros(shape, dtype=np.int16)
    destination = np.full(shape, -1, dtype=np.int16)
    digest = hashlib.sha256()
    digest.update(design["metadata"]["scientific_digest"].encode("ascii"))
    contract = SIMULATOR_CONTRACTS[spec.candidate]

    for landmark_index, landmark in enumerate(scale.landmarks):
        state = np.asarray(design["restored"][landmark_index])
        launches = arm_launches(beta, state, orders)
        for branch in range(scale.branches):
            no_op_trace: list[TracedFission] | None = None
            no_op_complete = False
            for arm_index, arm_name in enumerate(ARMS):
                launch = launches[arm_name]
                if arm_name == "ISOMORPHIC_BOTH_100":
                    if no_op_trace is None:
                        raise AssertionError("NOOP must precede the isomorphism arm")
                    traced, completed = no_op_trace, no_op_complete
                    digest.update(arm_name.encode("ascii"))
                    _update_trace_digest(digest, traced, completed, orders[100])
                else:
                    traced, completed = trace_future(
                        launch.composition,
                        launch.beta,
                        gard,
                        contract,
                        scale.horizon,
                        _rng(
                            config.master_seed,
                            f"{spec.stage}.future.common",
                            spec.matrix_id,
                            spec.candidate,
                            landmark,
                            branch,
                        ),
                        config.phase_grid,
                    )
                    digest.update(arm_name.encode("ascii"))
                    _update_trace_digest(digest, traced, completed)
                    if arm_name == "NOOP":
                        no_op_trace, no_op_complete = traced, completed
                records = [item.record for item in traced]
                outcome = evaluate_regime(records)
                strict8[landmark_index, arm_index, branch] = int(
                    outcome.primary_all8
                )
                f12[landmark_index, arm_index, branch] = int(_f12(records))
                first_break[landmark_index, arm_index, branch] = int(
                    outcome.first_break_index
                )
                complete[landmark_index, arm_index, branch] = int(completed)
                lengths[landmark_index, arm_index, branch] = len(traced)
                profile = design["shelf_profiles"][landmark_index][arm_index]
                if (
                    outcome.primary_all8
                    and outcome.primary_all8_onset >= 0
                    and profile["eligible"]
                ):
                    start = int(outcome.primary_all8_onset)
                    daughters = np.stack(
                        [item.record.daughter for item in traced[start : start + 8]]
                    )
                    if arm_name == "ISOMORPHIC_BOTH_100":
                        daughters = daughters[:, orders[100]]
                    destination[landmark_index, arm_index, branch] = destination_label(
                        daughters, profile["centers"]
                    )

    payload: dict[str, Any] = {
        "format": "fep-surprise-2-futures-cell-v1",
        "metadata": {
            "stage": spec.stage,
            "profile": config.profile,
            "matrix_id": spec.matrix_id,
            "candidate": spec.candidate,
            "design_hash": joblib.hash(design),
            "atlas_hash": joblib.hash(registry),
            "scientific_digest": digest.hexdigest(),
        },
        "strict8": strict8,
        "f12": f12,
        "first_break": first_break,
        "complete": complete,
        "trace_lengths": lengths,
        "destination": destination,
        "arms": ARMS,
        "landmarks": np.asarray(scale.landmarks, dtype=np.int16),
    }
    _atomic_dump(payload, spec.future_path)
    return spec.future_path


def load_design(path: Path) -> dict[str, Any]:
    payload = joblib.load(path)
    if payload.get("format") != "fep-surprise-2-design-cell-v1":
        raise ValueError(f"unsupported Experiment 2 design cell: {path}")
    return payload


def load_atlases(path: Path) -> AtlasRegistry:
    payload = joblib.load(path)
    if not isinstance(payload, AtlasRegistry):
        raise ValueError(f"unsupported Experiment 2 atlas bundle: {path}")
    return payload


def load_futures(path: Path) -> dict[str, Any]:
    payload = joblib.load(path)
    if payload.get("format") != "fep-surprise-2-futures-cell-v1":
        raise ValueError(f"unsupported Experiment 2 future cell: {path}")
    return payload
