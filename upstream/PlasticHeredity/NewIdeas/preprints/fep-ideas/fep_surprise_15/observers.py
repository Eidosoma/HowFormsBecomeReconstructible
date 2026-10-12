from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy.special import gammaln, logsumexp
from sklearn.decomposition import PCA
from sklearn.neighbors import NearestNeighbors


EPS = 1e-12
LEGACY_KNN = "legacy_knn"
INVARIANT_KNN = "invariant_knn"
SHELF = "shelf"
FIXED_SHELF = "fixed_shelf"
PRIMARY_OBSERVERS = (INVARIANT_KNN, SHELF)
ALL_OBSERVERS = (LEGACY_KNN, INVARIANT_KNN, SHELF, FIXED_SHELF)


def _as_rows(counts: np.ndarray) -> np.ndarray:
    values = np.asarray(counts, dtype=np.float64)
    if values.ndim == 1:
        values = values[None, :]
    if values.ndim != 2:
        raise ValueError("counts must be a vector or two-dimensional array")
    if np.any(values < 0):
        raise ValueError("compositions cannot be negative")
    if np.any(values.sum(axis=1) <= 0):
        raise ValueError("compositions must be nonempty")
    return values


def legacy_clr(counts: np.ndarray, pseudocount: float = 0.5) -> np.ndarray:
    """Experiment 1 count-smoothed CLR, retained only for diagnosis."""

    values = _as_rows(counts)
    logs = np.log(values + pseudocount)
    return logs - logs.mean(axis=1, keepdims=True)


def invariant_clr(
    counts: np.ndarray,
    pseudocount: float = 0.5,
    reference_mass: float = 80.0,
) -> np.ndarray:
    """Scale-invariant CLR that matches legacy CLR at reference mass."""

    values = _as_rows(counts)
    standardized = reference_mass * values / values.sum(axis=1, keepdims=True)
    logs = np.log(standardized + pseudocount)
    return logs - logs.mean(axis=1, keepdims=True)


@dataclass
class DeterministicProjection:
    clr_mean: np.ndarray
    components: np.ndarray
    coordinate_mean: np.ndarray
    coordinate_sd: np.ndarray
    pseudocount: float
    reference_mass: float
    explained_variance_ratio: np.ndarray

    def transform(self, counts: np.ndarray, *, invariant: bool) -> np.ndarray:
        if invariant:
            clr = invariant_clr(counts, self.pseudocount, self.reference_mass)
        else:
            clr = legacy_clr(counts, self.pseudocount)
        coordinates = (clr - self.clr_mean) @ self.components.T
        return (coordinates - self.coordinate_mean) / self.coordinate_sd


def fit_deterministic_projection(
    training_counts: np.ndarray,
    *,
    pseudocount: float,
    reference_mass: float,
    variance_target: float,
    min_components: int,
    max_components: int,
) -> tuple[DeterministicProjection, np.ndarray]:
    values = _as_rows(training_counts)
    if not np.allclose(values.sum(axis=1), reference_mass, atol=1e-12, rtol=0.0):
        raise ValueError("projection training states must have the reference mass")
    legacy = legacy_clr(values, pseudocount)
    invariant = invariant_clr(values, pseudocount, reference_mass)
    if not np.allclose(legacy, invariant, atol=1e-12, rtol=0.0):
        raise AssertionError("reference-mass legacy and invariant CLR must agree")
    available = min(max_components, legacy.shape[0] - 1, legacy.shape[1] - 1)
    if available < 1:
        raise ValueError("not enough states or species for PCA")
    # Full SVD is explicit: sklearn's auto branch selected randomized PCA in
    # Experiment 1 at 800 x 100 and made derived payloads non-replayable.
    full = PCA(n_components=available, svd_solver="full")
    raw = full.fit_transform(legacy)
    cumulative = np.cumsum(full.explained_variance_ratio_)
    dimension = int(np.searchsorted(cumulative, variance_target) + 1)
    dimension = max(min_components, min(dimension, available))
    coordinates = raw[:, :dimension]
    coordinate_mean = coordinates.mean(axis=0)
    coordinate_sd = coordinates.std(axis=0, ddof=1)
    coordinate_sd = np.where(coordinate_sd < 1e-8, 1.0, coordinate_sd)
    standardized = (coordinates - coordinate_mean) / coordinate_sd
    return (
        DeterministicProjection(
            clr_mean=full.mean_.copy(),
            components=full.components_[:dimension].copy(),
            coordinate_mean=coordinate_mean,
            coordinate_sd=coordinate_sd,
            pseudocount=pseudocount,
            reference_mass=reference_mass,
            explained_variance_ratio=full.explained_variance_ratio_[:dimension].copy(),
        ),
        standardized,
    )


@dataclass
class KNNRawObserver:
    training_coordinates: np.ndarray
    k: int
    query_batch_size: int = 512

    def score(self, coordinates: np.ndarray) -> np.ndarray:
        query = np.asarray(coordinates, dtype=np.float64)
        k = min(self.k, len(self.training_coordinates))
        model = NearestNeighbors(
            n_neighbors=k,
            metric="euclidean",
            algorithm="brute",
            n_jobs=1,
        ).fit(self.training_coordinates)
        radii = []
        for start in range(0, len(query), self.query_batch_size):
            batch = query[start : start + self.query_batch_size]
            radii.append(model.kneighbors(batch, return_distance=True)[0][:, -1])
        radius = np.concatenate(radii) if radii else np.empty(0, dtype=np.float64)
        dimension = self.training_coordinates.shape[1]
        log_volume = (dimension / 2.0) * np.log(np.pi) - gammaln(
            dimension / 2.0 + 1.0
        )
        log_density = (
            np.log(k)
            - np.log(len(self.training_coordinates))
            - log_volume
            - dimension * np.log(np.maximum(radius, 1e-9))
        )
        return -log_density


@dataclass
class CosineShelfObserver:
    weights: np.ndarray
    centers: np.ndarray
    gamma_shape: np.ndarray
    gamma_scale: np.ndarray

    def score(self, counts: np.ndarray) -> np.ndarray:
        values = _as_rows(counts).copy()
        values /= np.maximum(np.linalg.norm(values, axis=1, keepdims=True), EPS)
        distance = np.maximum(1.0 - values @ self.centers.T, 1e-9)
        shape = self.gamma_shape[None, :]
        scale = self.gamma_scale[None, :]
        log_residual = (
            (shape - 1.0) * np.log(distance)
            - distance / scale
            - gammaln(shape)
            - shape * np.log(scale)
        )
        log_score = logsumexp(
            np.log(self.weights + EPS)[None, :] + log_residual, axis=1
        )
        return -log_score


def _spherical_kmeans(
    counts: np.ndarray,
    k: int,
    seed: int,
    *,
    n_init: int = 8,
    iterations: int = 100,
) -> tuple[np.ndarray, np.ndarray]:
    values = _as_rows(counts).copy()
    values /= np.maximum(np.linalg.norm(values, axis=1, keepdims=True), EPS)
    rng = np.random.default_rng(seed)
    best: tuple[float, np.ndarray, np.ndarray] | None = None
    for _ in range(n_init):
        centers = values[rng.choice(len(values), size=k, replace=False)].copy()
        for _ in range(iterations):
            labels = np.argmax(values @ centers.T, axis=1)
            updated = np.empty_like(centers)
            for component in range(k):
                selected = values[labels == component]
                if len(selected):
                    center = selected.mean(axis=0)
                    updated[component] = center / max(float(np.linalg.norm(center)), EPS)
                else:
                    updated[component] = values[int(rng.integers(len(values)))]
            if np.allclose(updated, centers, atol=1e-10, rtol=0.0):
                centers = updated
                break
            centers = updated
        labels = np.argmax(values @ centers.T, axis=1)
        loss = float(np.sum(1.0 - np.max(values @ centers.T, axis=1)))
        if best is None or loss < best[0]:
            best = (loss, centers.copy(), labels.copy())
    if best is None:
        raise RuntimeError("spherical k-means failed")
    return best[1], best[2]


def _fit_shelf(
    counts: np.ndarray,
    k: int,
    seed: int,
) -> tuple[CosineShelfObserver, np.ndarray]:
    centers, labels = _spherical_kmeans(counts, k, seed)
    values = _as_rows(counts).copy()
    values /= np.maximum(np.linalg.norm(values, axis=1, keepdims=True), EPS)
    residuals = np.maximum(
        1.0 - np.sum(values * centers[labels], axis=1), 1e-9
    )
    global_mean = max(float(np.mean(residuals)), 1e-6)
    global_variance = max(float(np.var(residuals, ddof=1)), 1e-8)
    weights = []
    shapes = []
    scales = []
    for component in range(k):
        residual = residuals[labels == component]
        mean = max(float(np.mean(residual)) if len(residual) else global_mean, 1e-6)
        variance = (
            max(float(np.var(residual, ddof=1)), 1e-8)
            if len(residual) >= 3
            else global_variance
        )
        shapes.append(float(np.clip(mean * mean / variance, 0.2, 200.0)))
        scales.append(float(np.clip(variance / mean, 1e-7, 1.0)))
        weights.append(max(int(np.count_nonzero(labels == component)), 1))
    weight_array = np.asarray(weights, dtype=np.float64)
    weight_array /= weight_array.sum()
    return (
        CosineShelfObserver(
            weights=weight_array,
            centers=centers,
            gamma_shape=np.asarray(shapes),
            gamma_scale=np.asarray(scales),
        ),
        labels,
    )


def _trajectory_folds(
    lineage_ids: np.ndarray, folds: int
) -> list[tuple[np.ndarray, np.ndarray]]:
    unique = np.unique(lineage_ids)
    folds = max(2, min(folds, len(unique)))
    output = []
    for fold in range(folds):
        valid_ids = unique[np.arange(len(unique)) % folds == fold]
        valid = np.isin(lineage_ids, valid_ids)
        if valid.any() and (~valid).any():
            output.append((~valid, valid))
    return output


def _select_shelf_k(
    counts: np.ndarray,
    lineage_ids: np.ndarray,
    k_max: int,
    seed: int,
) -> tuple[int, float]:
    best: tuple[float, int] | None = None
    folds = _trajectory_folds(lineage_ids, min(4, len(np.unique(lineage_ids))))
    maximum = min(k_max, max(1, len(counts) // 10))
    for k in range(1, maximum + 1):
        scores = []
        for fold, (training, validation) in enumerate(folds):
            model, _ = _fit_shelf(counts[training], k, seed + fold)
            scores.append(float(np.mean(-model.score(counts[validation]))))
        score = float(np.mean(scores)) if scores else float("-inf")
        if best is None or score > best[0] + 1e-10 or (
            abs(score - best[0]) <= 1e-10 and k < best[1]
        ):
            best = (score, k)
    if best is None:
        raise RuntimeError("shelf selection failed")
    return best[1], best[0]


@dataclass
class EmpiricalPhaseCalibrator:
    sorted_scores: tuple[np.ndarray, ...]
    quantization_decimals: int = 10

    @classmethod
    def fit(cls, scores: np.ndarray) -> "EmpiricalPhaseCalibrator":
        values = np.asarray(scores, dtype=np.float64)
        if values.ndim != 2:
            raise ValueError("phase calibration scores must be state x phase")
        if not np.isfinite(values).all():
            raise ValueError("phase calibration scores must be finite")
        decimals = 10
        quantized = np.round(values, decimals=decimals)
        return cls(
            tuple(np.sort(quantized[:, phase]) for phase in range(values.shape[1])),
            quantization_decimals=decimals,
        )

    def transform(self, scores: np.ndarray, phase: int) -> np.ndarray:
        values = np.round(
            np.asarray(scores, dtype=np.float64), decimals=self.quantization_decimals
        )
        calibration = self.sorted_scores[phase]
        # Smoothed upper-tail empirical probability.  Higher raw
        # nonconformity therefore gives a larger anomaly value.
        left = np.searchsorted(calibration, values, side="left")
        tail = (len(calibration) - left + 1.0) / (len(calibration) + 1.0)
        return -np.log(tail)

    def transform_grid(self, scores: np.ndarray) -> np.ndarray:
        values = np.asarray(scores, dtype=np.float64)
        if values.ndim != 2 or values.shape[1] != len(self.sorted_scores):
            raise ValueError("grid scores must be state x registered phase")
        return np.column_stack(
            [self.transform(values[:, phase], phase) for phase in range(values.shape[1])]
        )


@dataclass
class HalfObserverBundle:
    projection: DeterministicProjection
    knn: KNNRawObserver
    shelf: CosineShelfObserver
    fixed_shelf: CosineShelfObserver
    calibrators: dict[str, EmpiricalPhaseCalibrator]
    selected_k: int
    shelf_validation_score: float

    def raw(self, counts: np.ndarray, observer: str) -> np.ndarray:
        if observer == LEGACY_KNN:
            return self.knn.score(self.projection.transform(counts, invariant=False))
        if observer == INVARIANT_KNN:
            return self.knn.score(self.projection.transform(counts, invariant=True))
        if observer == SHELF:
            return self.shelf.score(counts)
        if observer == FIXED_SHELF:
            return self.fixed_shelf.score(counts)
        raise ValueError(observer)

    def anomaly(self, counts: np.ndarray, phase: int, observer: str) -> np.ndarray:
        return self.calibrators[observer].transform(self.raw(counts, observer), phase)

    def anomaly_grid(self, phase_counts: np.ndarray, observer: str) -> np.ndarray:
        values = np.asarray(phase_counts)
        if values.ndim != 3:
            raise ValueError("phase counts must have state x phase x species shape")
        flat = values.reshape(-1, values.shape[-1])
        raw = self.raw(flat, observer).reshape(values.shape[:2])
        return self.calibrators[observer].transform_grid(raw)


@dataclass
class ObserverEnsemble:
    halves: tuple[HalfObserverBundle, HalfObserverBundle]

    def raw_halves(self, counts: np.ndarray, observer: str) -> np.ndarray:
        return np.column_stack([half.raw(counts, observer) for half in self.halves])

    def raw(self, counts: np.ndarray, observer: str) -> np.ndarray:
        return self.raw_halves(counts, observer).mean(axis=1)

    def anomaly_halves(
        self, counts: np.ndarray, phase: int, observer: str
    ) -> np.ndarray:
        return np.column_stack(
            [half.anomaly(counts, phase, observer) for half in self.halves]
        )

    def anomaly(self, counts: np.ndarray, phase: int, observer: str) -> np.ndarray:
        return self.anomaly_halves(counts, phase, observer).mean(axis=1)

    def anomaly_grid_halves(self, phase_counts: np.ndarray, observer: str) -> np.ndarray:
        return np.stack(
            [half.anomaly_grid(phase_counts, observer) for half in self.halves], axis=-1
        )

    def anomaly_grid(self, phase_counts: np.ndarray, observer: str) -> np.ndarray:
        return self.anomaly_grid_halves(phase_counts, observer).mean(axis=-1)

    @property
    def atlas_centers(self) -> np.ndarray:
        centers = np.vstack([half.shelf.centers for half in self.halves])
        return centers / np.maximum(np.linalg.norm(centers, axis=1, keepdims=True), EPS)


def _subsample_training(
    counts: np.ndarray,
    lineage_ids: np.ndarray,
    maximum: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    if len(counts) <= maximum:
        return counts, lineage_ids
    rng = np.random.default_rng(seed)
    chosen = np.sort(rng.choice(len(counts), maximum, replace=False))
    return counts[chosen], lineage_ids[chosen]


def _fit_half(
    training_counts: np.ndarray,
    training_lineages: np.ndarray,
    calibration_phase_counts: np.ndarray,
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
) -> HalfObserverBundle:
    training_counts, training_lineages = _subsample_training(
        np.asarray(training_counts),
        np.asarray(training_lineages),
        training_subsample,
        seed,
    )
    projection, coordinates = fit_deterministic_projection(
        training_counts,
        pseudocount=pseudocount,
        reference_mass=reference_mass,
        variance_target=pca_variance,
        min_components=pca_min,
        max_components=pca_max,
    )
    knn = KNNRawObserver(coordinates.copy(), min(knn_k, len(coordinates)))
    selected_k, validation = _select_shelf_k(
        training_counts, training_lineages, mixture_k_max, seed
    )
    shelf, _ = _fit_shelf(training_counts, selected_k, seed)
    fixed, _ = _fit_shelf(training_counts, 1, seed=0)
    provisional = HalfObserverBundle(
        projection=projection,
        knn=knn,
        shelf=shelf,
        fixed_shelf=fixed,
        calibrators={},
        selected_k=selected_k,
        shelf_validation_score=validation,
    )
    phases = np.asarray(calibration_phase_counts)
    flattened = phases.reshape(-1, phases.shape[-1])
    calibrators: dict[str, EmpiricalPhaseCalibrator] = {}
    for observer in ALL_OBSERVERS:
        raw = provisional.raw(flattened, observer).reshape(phases.shape[:2])
        calibrators[observer] = EmpiricalPhaseCalibrator.fit(raw)
    provisional.calibrators = calibrators
    return provisional


def fit_observer_ensemble(
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
) -> ObserverEnsemble:
    parents = np.asarray(parent_counts)
    phases = np.asarray(phase_counts)
    lineages = np.asarray(lineage_ids)
    if len(parents) != len(phases) or len(parents) != len(lineages):
        raise ValueError("reference arrays do not align")
    unique = np.unique(lineages)
    if len(unique) < 4:
        raise ValueError("at least four reference lineages are required")
    split_ids = (unique[::2], unique[1::2])
    halves = []
    for index, training_ids in enumerate(split_ids):
        training = np.isin(lineages, training_ids)
        calibration = np.isin(lineages, split_ids[1 - index])
        halves.append(
            _fit_half(
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
                seed=seed + index,
            )
        )
    return ObserverEnsemble((halves[0], halves[1]))


def proportional_state(parent: np.ndarray, target_mass: float) -> np.ndarray:
    values = np.asarray(parent, dtype=np.float64)
    total = float(values.sum())
    if total <= 0 or target_mass <= 0:
        raise ValueError("proportional state requires positive masses")
    return values * (target_mass / total)


def scale_invariance_error(
    ensemble: ObserverEnsemble,
    states: np.ndarray,
    observer: str,
    scales: tuple[float, ...] = (0.5, 0.75, 1.25, 2.0),
) -> float:
    values = _as_rows(states)
    baseline = ensemble.raw(values, observer)
    maximum = 0.0
    for scale in scales:
        shifted = ensemble.raw(values * scale, observer)
        maximum = max(maximum, float(np.max(np.abs(shifted - baseline))))
    return maximum


def nearest_shelf_distance(counts: np.ndarray, centers: np.ndarray) -> np.ndarray:
    values = _as_rows(counts).copy()
    values /= np.maximum(np.linalg.norm(values, axis=1, keepdims=True), EPS)
    return 1.0 - np.max(values @ centers.T, axis=1)
