from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from fep_surprise.dynamics import expected_flux, rq_alignment
from fep_surprise.tracing import TracedFission, trace_future
from fep_surprise_15.observers import (
    INVARIANT_KNN,
    SHELF,
    ObserverEnsemble,
    fit_observer_ensemble,
)
from fep_surprise_2.worker import _update_trace_digest
from plastic_heredity.config import CANDIDATES as SIMULATOR_CONTRACTS
from plastic_heredity.config import GardConfig
from plastic_heredity.regime_confirmation import evaluate_regime
from plastic_heredity.seeds import derive_seed
from plastic_heredity.simulator import cosine_similarity, generate_initial_composition

from .atlas import Atlas25Registry, destination_label, mismatch_jump, shelf_profile
from .config import ACTUAL_ATLASES, ARMS, Campaign25Config
from .interventions import (
    LAUNCH_METRIC_NAMES,
    arm_launches25,
    beta_variants25,
    launch_metrics25,
)
from .regime import load_screen, mass_preserving_perturbations


BASELINE_FEATURE_NAMES = (
    "landmark_fraction",
    "state_mass",
    "occupied_types",
    "composition_entropy",
    "log_catalytic_throughput",
    "expected_flux_norm",
    "rq_alignment",
    "native_shelf_distance",
)
REGIME_FEATURE_NAMES = (
    "screen_break_probability",
    "damage_mean",
    "damage_sd",
    "damage_complete_fraction",
    "native_shelf_k",
    "native_occupancy_entropy",
    "native_dominant_occupancy",
)


@dataclass(frozen=True)
class Cell25Spec:
    matrix_id: int
    candidate: str
    stratum: str
    screen_path: Path
    output: Path
    force: bool = False

    @property
    def stem(self) -> str:
        return f"cell_{self.stratum}_c{self.candidate}_m{self.matrix_id:04d}"

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


def _rng(master: str, domain: str, *parts: object) -> np.random.Generator:
    return np.random.default_rng(derive_seed(master, domain, *parts))


def _atomic_dump(value: Any, target: Path) -> None:
    temporary = target.with_name(target.name + f".{os.getpid()}.tmp")
    joblib.dump(value, temporary, compress=3)
    temporary.replace(target)


def _entropy(values: np.ndarray) -> float:
    vector = np.asarray(values, dtype=np.float64)
    probability = vector / max(float(vector.sum()), 1.0)
    selected = probability > 0
    return float(-np.sum(probability[selected] * np.log(probability[selected])))


def _collect_reference(
    config: Campaign25Config,
    spec: Cell25Spec,
    atlas_key: str,
    beta: np.ndarray,
    gard: GardConfig,
    digest: Any,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    scale = config.confirmation
    parents: list[np.ndarray] = []
    phases: list[np.ndarray] = []
    lineages: list[int] = []
    lengths: list[int] = []
    completed: list[bool] = []
    for lineage in range(scale.reference_lineages):
        initial = generate_initial_composition(
            gard,
            _rng(
                config.master_seed,
                "experiment25.confirmation.reference.initial",
                spec.matrix_id,
                spec.candidate,
                atlas_key,
                lineage,
            ),
        )
        traced, complete = trace_future(
            initial,
            beta,
            gard,
            SIMULATOR_CONTRACTS[spec.candidate],
            scale.reference_fissions,
            _rng(
                config.master_seed,
                "experiment25.confirmation.reference.dynamics",
                spec.matrix_id,
                spec.candidate,
                atlas_key,
                lineage,
            ),
            config.phase_grid,
        )
        _update_trace_digest(digest, traced, complete)
        lengths.append(len(traced))
        completed.append(bool(complete))
        for item in traced[scale.reference_burnin :]:
            parents.append(item.record.parent.copy())
            phases.append(item.phase_compositions.copy())
            lineages.append(lineage)
    if len(parents) < scale.minimum_reference_states:
        raise RuntimeError(
            f"{atlas_key} retained {len(parents)} reference states; "
            f"requires {scale.minimum_reference_states}"
        )
    return (
        np.stack(parents),
        np.asarray(lineages, dtype=np.int16),
        np.stack(phases),
        {
            "requested_lineages": scale.reference_lineages,
            "complete_lineages": int(sum(completed)),
            "terminal_prefixes": int(len(completed) - sum(completed)),
            "trace_lengths": lengths,
            "retained_states": len(parents),
        },
    )


def _fit_atlas(
    config: Campaign25Config,
    spec: Cell25Spec,
    atlas_key: str,
    parents: np.ndarray,
    lineages: np.ndarray,
    phases: np.ndarray,
) -> ObserverEnsemble:
    seed = derive_seed(
        config.master_seed,
        "experiment25.confirmation.atlas.fit",
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
        training_subsample=config.confirmation.training_subsample,
        seed=int(seed),
    )


def _eligible_profile(
    observer: Any, state: np.ndarray, config: Campaign25Config
) -> dict[str, Any]:
    profile = shelf_profile(
        observer, state, minimum_cosine=config.shelf_stability_cosine
    )
    occupancy = np.asarray(profile.get("occupancy", []), dtype=np.float64)
    profile["occupancy_ceiling_pass"] = bool(
        profile["eligible"]
        and len(occupancy)
        and float(np.max(occupancy)) <= config.shelf_max_occupancy
    )
    profile["eligible"] = bool(profile["occupancy_ceiling_pass"])
    return profile


def _baseline(
    state: np.ndarray,
    landmark: int,
    beta: np.ndarray,
    gard: GardConfig,
    native: ObserverEnsemble,
    max_landmark: int,
) -> np.ndarray:
    vector = np.asarray(state, dtype=np.float64)
    normed = vector / max(float(np.linalg.norm(vector)), 1e-12)
    throughput = max(float(vector @ beta @ vector), 1e-300)
    return np.asarray(
        [
            landmark / max_landmark,
            float(vector.sum()),
            float(np.count_nonzero(vector)),
            _entropy(vector),
            float(np.log(throughput)),
            float(np.linalg.norm(expected_flux(vector, beta, gard))),
            rq_alignment(vector, beta, gard),
            float(1.0 - np.max(normed @ native.atlas_centers.T)),
        ],
        dtype=np.float64,
    )


def _damage_metrics(
    config: Campaign25Config,
    spec: Cell25Spec,
    state: np.ndarray,
    beta: np.ndarray,
    landmark: int,
    gard: GardConfig,
    digest: Any,
) -> tuple[float, float, float]:
    scale = config.confirmation
    seed = derive_seed(
        config.master_seed,
        "experiment25.confirmation.damage.design",
        spec.matrix_id,
        spec.candidate,
        landmark,
    ) % (2**32 - 1)
    perturbations = mass_preserving_perturbations(
        state, scale.damage_perturbations, int(seed)
    )
    distances = []
    completed = []
    for index, changed in enumerate(perturbations):
        parts = (spec.matrix_id, spec.candidate, landmark, index)
        native, native_complete = trace_future(
            state, beta, gard, SIMULATOR_CONTRACTS[spec.candidate],
            scale.damage_horizon,
            _rng(config.master_seed, "experiment25.confirmation.damage.future", *parts),
            config.phase_grid,
        )
        perturbed, perturbed_complete = trace_future(
            changed, beta, gard, SIMULATOR_CONTRACTS[spec.candidate],
            scale.damage_horizon,
            _rng(config.master_seed, "experiment25.confirmation.damage.future", *parts),
            config.phase_grid,
        )
        _update_trace_digest(digest, native, native_complete)
        _update_trace_digest(digest, perturbed, perturbed_complete)
        valid = bool(native and perturbed)
        completed.append(bool(native_complete and perturbed_complete))
        if valid:
            distances.append(
                1.0
                - cosine_similarity(
                    native[-1].record.daughter, perturbed[-1].record.daughter
                )
            )
    if not distances:
        return 1.0, 0.0, 0.0
    return (
        float(np.mean(distances)),
        float(np.std(distances, ddof=0)),
        float(np.mean(completed)),
    )


def _distribution_summary(probability: np.ndarray) -> tuple[float, float]:
    values = np.asarray(probability, dtype=np.float64)
    if not len(values):
        return 0.0, 0.0
    selected = values > 0
    entropy = float(-np.sum(values[selected] * np.log(values[selected])))
    return entropy, float(np.max(values))


def _pilot(
    config: Campaign25Config,
    spec: Cell25Spec,
    beta: np.ndarray,
    state: np.ndarray,
    order: np.ndarray,
    profiles: list[dict[str, Any]],
    landmark: int,
    gard: GardConfig,
    digest: Any,
) -> list[dict[str, Any]]:
    scale = config.confirmation
    launches = arm_launches25(beta, state, order)
    breaks = np.zeros((len(ARMS), scale.pilot_branches), dtype=np.int8)
    complete = np.zeros_like(breaks)
    labels: list[list[int]] = [[] for _ in ARMS]
    for branch in range(scale.pilot_branches):
        native_trace: list[TracedFission] | None = None
        native_complete = False
        for arm_index, arm in enumerate(ARMS):
            launch = launches[arm]
            if arm == "ISOMORPHIC_BOTH_100":
                if native_trace is None:
                    raise AssertionError("native pilot must precede isomorphism")
                traced, completed = native_trace, native_complete
                _update_trace_digest(digest, traced, completed, order)
            else:
                traced, completed = trace_future(
                    launch.composition,
                    launch.beta,
                    gard,
                    SIMULATOR_CONTRACTS[spec.candidate],
                    scale.pilot_horizon,
                    _rng(
                        config.master_seed,
                        "experiment25.confirmation.pilot.future",
                        spec.matrix_id,
                        spec.candidate,
                        landmark,
                        branch,
                    ),
                    config.phase_grid,
                )
                _update_trace_digest(digest, traced, completed)
                if arm == "ALIGNED_NATIVE":
                    native_trace, native_complete = traced, completed
            breaks[arm_index, branch] = int(
                any(item.record.h <= 0.9 for item in traced)
            )
            complete[arm_index, branch] = int(completed)
            profile = profiles[arm_index]
            if traced and profile["eligible"]:
                endpoint = np.asarray(traced[-1].record.daughter)
                if arm == "ISOMORPHIC_BOTH_100":
                    endpoint = endpoint[order]
                normalized = endpoint / max(float(np.linalg.norm(endpoint)), 1e-12)
                labels[arm_index].append(
                    int(np.argmax(normalized @ np.asarray(profile["centers"]).T))
                )
    output = []
    for arm_index, profile in enumerate(profiles):
        count = len(np.asarray(profile.get("occupancy", [])))
        if profile["eligible"] and count:
            frequencies = np.bincount(labels[arm_index], minlength=count).astype(float)
            probability = (frequencies + 0.5) / (frequencies.sum() + 0.5 * count)
        else:
            probability = np.empty(0, dtype=np.float64)
        entropy, maximum = _distribution_summary(probability)
        output.append(
            {
                "break_probability": float(breaks[arm_index].mean()),
                "complete_fraction": float(complete[arm_index].mean()),
                "destination_probability": probability,
                "destination_entropy": entropy,
                "destination_maximum": maximum,
            }
        )
    return output


def prepare_cell(spec: Cell25Spec, config: Campaign25Config) -> Path:
    if (
        spec.design_path.exists()
        and spec.atlas_path.exists()
        and spec.metadata_path.exists()
        and not spec.force
    ):
        return spec.design_path
    spec.output.mkdir(parents=True, exist_ok=True)
    screen = load_screen(spec.screen_path)
    if int(screen["matrix_id"]) != spec.matrix_id:
        raise ValueError("screen cell and confirmation matrix differ")
    source = screen["candidates"][spec.candidate]
    if not source["usable"]:
        raise ValueError("selected screen source is unusable")
    states = np.asarray(source["states"], dtype=np.int64)
    beta = np.asarray(screen["beta"], dtype=np.float64)
    order = np.asarray(screen["order"], dtype=np.int64)
    variants = beta_variants25(beta, order)
    scale = config.confirmation
    gard = GardConfig(generations=max(scale.landmarks))
    digest = hashlib.sha256()
    digest.update(str(screen["scientific_digest"]).encode("ascii"))
    digest.update(spec.stratum.encode("ascii"))

    actual: dict[str, ObserverEnsemble] = {}
    reference_meta: dict[str, Any] = {}
    for atlas_key in ACTUAL_ATLASES:
        parents, lineages, phases, metadata = _collect_reference(
            config, spec, atlas_key, variants[atlas_key], gard, digest
        )
        actual[atlas_key] = _fit_atlas(
            config, spec, atlas_key, parents, lineages, phases
        )
        reference_meta[atlas_key] = metadata
    views = {
        "perm_native": ("native", order),
        "perm_sigma_250": ("sigma_250", order),
        "perm_sigma_325": ("sigma_325", order),
        "perm_sigma_500": ("sigma_500", order),
    }
    registry = Atlas25Registry(actual=actual, views=views)
    baselines = np.stack(
        [
            _baseline(
                state, landmark, beta, gard, actual["native"], max(scale.landmarks)
            )
            for state, landmark in zip(states, scale.landmarks)
        ]
    )
    regime = np.empty((len(scale.landmarks), len(REGIME_FEATURE_NAMES)))
    metrics = np.empty(
        (len(scale.landmarks), len(ARMS), len(LAUNCH_METRIC_NAMES)), dtype=float
    )
    jumps = {
        observer: np.empty((len(scale.landmarks), len(ARMS), 2), dtype=float)
        for observer in (INVARIANT_KNN, SHELF)
    }
    profiles: list[list[dict[str, Any]]] = []
    pilots: list[list[dict[str, Any]]] = []
    screen_landmark_break = np.asarray(source["break"], dtype=float).mean(axis=1)
    for landmark_index, (landmark, state) in enumerate(
        zip(scale.landmarks, states)
    ):
        launches = arm_launches25(beta, state, order)
        row_profiles = []
        for arm_index, arm in enumerate(ARMS):
            launch = launches[arm]
            target = registry.get(launch.atlas_key)
            metrics[landmark_index, arm_index] = launch_metrics25(
                beta, state, launch, gard, SIMULATOR_CONTRACTS[spec.candidate]
            )
            jump = mismatch_jump(
                actual["native"], target, state, launch.composition, 0
            )
            for observer in jumps:
                jumps[observer][landmark_index, arm_index] = jump[observer]
            row_profiles.append(_eligible_profile(target, launch.composition, config))
        profiles.append(row_profiles)
        damage_mean, damage_sd, damage_complete = _damage_metrics(
            config, spec, state, beta, landmark, gard, digest
        )
        native_occupancy = np.asarray(row_profiles[0].get("occupancy", []), dtype=float)
        occupancy_entropy, dominant = _distribution_summary(native_occupancy)
        regime[landmark_index] = np.asarray(
            [
                screen_landmark_break[landmark_index],
                damage_mean,
                damage_sd,
                damage_complete,
                float(len(native_occupancy)),
                occupancy_entropy,
                dominant,
            ]
        )
        pilots.append(
            _pilot(
                config, spec, beta, state, order, row_profiles,
                landmark, gard, digest,
            )
        )
    design = {
        "format": "fep-surprise-25-design-cell-v1",
        "metadata": {
            "profile": config.profile,
            "matrix_id": spec.matrix_id,
            "candidate": spec.candidate,
            "stratum": spec.stratum,
            "screen_digest": screen["scientific_digest"],
            "reference": reference_meta,
            "atlas_hash": joblib.hash(registry),
            "scientific_digest": digest.hexdigest(),
            "actual_atlases": list(ACTUAL_ATLASES),
            "selected_k": {
                key: [len(half.shelf.weights) for half in model.halves]
                for key, model in actual.items()
            },
            "pca_dimensions": {
                key: [len(half.projection.coordinate_mean) for half in model.halves]
                for key, model in actual.items()
            },
        },
        "beta": beta,
        "order": order,
        "landmarks": np.asarray(scale.landmarks, dtype=np.int16),
        "states": states,
        "baseline": baselines,
        "regime": regime,
        "launch_metrics": metrics,
        "mismatch_jump": jumps,
        "shelf_profiles": profiles,
        "pilots": pilots,
        "arms": ARMS,
        "baseline_feature_names": BASELINE_FEATURE_NAMES,
        "regime_feature_names": REGIME_FEATURE_NAMES,
        "launch_metric_names": LAUNCH_METRIC_NAMES,
    }
    _atomic_dump(registry, spec.atlas_path)
    _atomic_dump(design, spec.design_path)
    sidecar = {
        **design["metadata"],
        "format": design["format"],
        "design_hash": joblib.hash(design),
    }
    temporary = spec.metadata_path.with_name(spec.metadata_path.name + f".{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(sidecar, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(spec.metadata_path)
    return spec.design_path


def _strict8_details(traced: list[TracedFission]) -> dict[str, Any] | None:
    outcome = evaluate_regime([item.record for item in traced])
    if not outcome.primary_all8:
        return None
    onset = int(outcome.primary_all8_onset)
    window = traced[onset : onset + 8]
    first_break = int(outcome.first_break_index)
    return {
        "start": window[-1].record.daughter.copy(),
        "centroid": np.mean(
            np.stack([item.record.daughter for item in window]).astype(float), axis=0
        ),
        "anchor": traced[first_break].record.parent.copy(),
        "daughters": np.stack([item.record.daughter for item in window]),
        "onset": onset,
    }


def _durable(
    traced: list[TracedFission], centroid: np.ndarray, anchor: np.ndarray
) -> bool:
    if len(traced) < 8:
        return False
    daughters = [item.record.daughter for item in traced[-8:]]
    for left in range(8):
        if cosine_similarity(daughters[left], centroid) <= 0.90:
            return False
        if cosine_similarity(daughters[left], anchor) > 0.85:
            return False
        for right in range(left + 1, 8):
            if cosine_similarity(daughters[left], daughters[right]) <= 0.90:
                return False
    return True


def run_futures(spec: Cell25Spec, config: Campaign25Config) -> Path:
    if spec.future_path.exists() and not spec.force:
        return spec.future_path
    design = load_design(spec.design_path)
    registry = load_atlases(spec.atlas_path)
    if joblib.hash(registry) != design["metadata"]["atlas_hash"]:
        raise ValueError("atlas artifact differs from frozen design")
    scale = config.confirmation
    gard = GardConfig(generations=max(scale.landmarks))
    beta = np.asarray(design["beta"])
    order = np.asarray(design["order"])
    shape = (len(scale.landmarks), len(ARMS), scale.branches)
    strict8 = np.zeros(shape, dtype=np.int8)
    departed = np.zeros(shape, dtype=np.int8)
    first_break = np.full(shape, -1, dtype=np.int16)
    complete = np.zeros(shape, dtype=np.int8)
    lengths = np.zeros(shape, dtype=np.int16)
    destination = np.full(shape, -1, dtype=np.int16)
    durability_followed = np.zeros(shape, dtype=np.int8)
    durable16 = np.zeros(shape, dtype=np.int8)
    durability_complete = np.zeros(shape, dtype=np.int8)
    durable_destination = np.full(shape, -1, dtype=np.int8)
    digest = hashlib.sha256()
    digest.update(design["metadata"]["scientific_digest"].encode("ascii"))
    candidates: dict[tuple[int, int, int], dict[str, Any]] = {}
    contract = SIMULATOR_CONTRACTS[spec.candidate]
    for landmark_index, landmark in enumerate(scale.landmarks):
        state = np.asarray(design["states"][landmark_index])
        launches = arm_launches25(beta, state, order)
        for branch in range(scale.branches):
            native_trace: list[TracedFission] | None = None
            native_complete = False
            for arm_index, arm in enumerate(ARMS):
                launch = launches[arm]
                if arm == "ISOMORPHIC_BOTH_100":
                    if native_trace is None:
                        raise AssertionError("native future must precede isomorphism")
                    traced, completed = native_trace, native_complete
                    _update_trace_digest(digest, traced, completed, order)
                else:
                    traced, completed = trace_future(
                        launch.composition,
                        launch.beta,
                        gard,
                        contract,
                        scale.horizon,
                        _rng(
                            config.master_seed,
                            "experiment25.confirmation.main.future",
                            spec.matrix_id,
                            spec.candidate,
                            landmark,
                            branch,
                        ),
                        config.phase_grid,
                    )
                    _update_trace_digest(digest, traced, completed)
                    if arm == "ALIGNED_NATIVE":
                        native_trace, native_complete = traced, completed
                outcome = evaluate_regime([item.record for item in traced])
                strict8[landmark_index, arm_index, branch] = int(outcome.primary_all8)
                departed[landmark_index, arm_index, branch] = int(
                    outcome.first_break_index >= 0
                )
                first_break[landmark_index, arm_index, branch] = int(
                    outcome.first_break_index
                )
                complete[landmark_index, arm_index, branch] = int(completed)
                lengths[landmark_index, arm_index, branch] = len(traced)
                details = _strict8_details(traced)
                profile = design["shelf_profiles"][landmark_index][arm_index]
                if details is not None:
                    candidates[(landmark_index, arm_index, branch)] = details
                    if profile["eligible"]:
                        daughters = details["daughters"]
                        if arm == "ISOMORPHIC_BOTH_100":
                            daughters = daughters[:, order]
                        destination[landmark_index, arm_index, branch] = destination_label(
                            daughters, profile["centers"]
                        )

    continuation_cache: dict[tuple[int, int], tuple[list[TracedFission], bool]] = {}
    for landmark_index, landmark in enumerate(scale.landmarks):
        state = np.asarray(design["states"][landmark_index])
        launches = arm_launches25(beta, state, order)
        for arm_index, arm in enumerate(ARMS):
            priority_arm = "ALIGNED_NATIVE" if arm == "ISOMORPHIC_BOTH_100" else arm
            priority = _rng(
                config.master_seed,
                "experiment25.confirmation.durability.priority",
                spec.matrix_id,
                spec.candidate,
                landmark,
                priority_arm,
            ).permutation(scale.branches)
            selected = [
                int(branch)
                for branch in priority
                if (landmark_index, arm_index, int(branch)) in candidates
            ][: scale.durability_events]
            for branch in selected:
                details = candidates[(landmark_index, arm_index, branch)]
                durability_followed[landmark_index, arm_index, branch] = 1
                if arm == "ISOMORPHIC_BOTH_100":
                    traced, completed = continuation_cache[(landmark_index, branch)]
                    _update_trace_digest(digest, traced, completed, order)
                else:
                    traced, completed = trace_future(
                        details["start"],
                        launches[arm].beta,
                        gard,
                        contract,
                        scale.durability_horizon,
                        _rng(
                            config.master_seed,
                            "experiment25.confirmation.durability.future",
                            spec.matrix_id,
                            spec.candidate,
                            landmark,
                            priority_arm,
                            branch,
                        ),
                        config.phase_grid,
                    )
                    _update_trace_digest(digest, traced, completed)
                    if arm == "ALIGNED_NATIVE":
                        continuation_cache[(landmark_index, branch)] = (traced, completed)
                durability_complete[landmark_index, arm_index, branch] = int(completed)
                durable16[landmark_index, arm_index, branch] = int(
                    _durable(traced, details["centroid"], details["anchor"])
                )
                original_destination = destination[landmark_index, arm_index, branch]
                profile = design["shelf_profiles"][landmark_index][arm_index]
                if len(traced) >= 8 and original_destination >= 0 and profile["eligible"]:
                    daughters = np.stack([item.record.daughter for item in traced[-8:]])
                    if arm == "ISOMORPHIC_BOTH_100":
                        daughters = daughters[:, order]
                    final_destination = destination_label(daughters, profile["centers"])
                    durable_destination[landmark_index, arm_index, branch] = int(
                        final_destination == original_destination
                    )
    payload = {
        "format": "fep-surprise-25-futures-cell-v1",
        "metadata": {
            "profile": config.profile,
            "matrix_id": spec.matrix_id,
            "candidate": spec.candidate,
            "stratum": spec.stratum,
            "design_hash": joblib.hash(design),
            "atlas_hash": joblib.hash(registry),
            "scientific_digest": digest.hexdigest(),
        },
        "strict8": strict8,
        "departed": departed,
        "first_break": first_break,
        "complete": complete,
        "trace_lengths": lengths,
        "destination": destination,
        "durability_followed": durability_followed,
        "durable16": durable16,
        "durability_complete": durability_complete,
        "durable_destination": durable_destination,
        "arms": ARMS,
        "landmarks": np.asarray(scale.landmarks, dtype=np.int16),
    }
    _atomic_dump(payload, spec.future_path)
    return spec.future_path


def load_design(path: Path) -> dict[str, Any]:
    payload = joblib.load(path)
    if payload.get("format") != "fep-surprise-25-design-cell-v1":
        raise ValueError(f"unsupported Experiment 2.5 design cell: {path}")
    return payload


def load_atlases(path: Path) -> Atlas25Registry:
    payload = joblib.load(path)
    if not isinstance(payload, Atlas25Registry):
        raise ValueError(f"unsupported Experiment 2.5 atlas bundle: {path}")
    return payload


def load_futures(path: Path) -> dict[str, Any]:
    payload = joblib.load(path)
    if payload.get("format") != "fep-surprise-25-futures-cell-v1":
        raise ValueError(f"unsupported Experiment 2.5 future cell: {path}")
    return payload
