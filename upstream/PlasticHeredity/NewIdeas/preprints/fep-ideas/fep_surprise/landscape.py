from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.special import gammaln, logsumexp
from sklearn.decomposition import PCA
from sklearn.neighbors import NearestNeighbors


EPS = 1e-12


def clr_transform(counts: np.ndarray, pseudocount: float = 0.5) -> np.ndarray:
    values = np.asarray(counts, dtype=np.float64)
    if values.ndim == 1:
        values = values[None, :]
    if np.any(values < 0):
        raise ValueError("compositions cannot be negative")
    adjusted = values + pseudocount
    proportions = adjusted / adjusted.sum(axis=1, keepdims=True)
    logs = np.log(proportions)
    return logs - logs.mean(axis=1, keepdims=True)


@dataclass
class Projection:
    clr_mean: np.ndarray
    components: np.ndarray
    scale_mean: np.ndarray
    scale_sd: np.ndarray
    pseudocount: float

    def transform(self, counts: np.ndarray) -> np.ndarray:
        clr = clr_transform(counts, self.pseudocount)
        coords = (clr - self.clr_mean) @ self.components.T
        return (coords - self.scale_mean) / self.scale_sd


@dataclass
class DiagonalMixture:
    weights: np.ndarray
    means: np.ndarray
    variances: np.ndarray

    def log_density(self, coordinates: np.ndarray) -> np.ndarray:
        x = np.asarray(coordinates, dtype=np.float64)
        diff = x[:, None, :] - self.means[None, :, :]
        log_component = -0.5 * (
            np.sum(np.log(2.0 * np.pi * self.variances), axis=1)[None, :]
            + np.sum(diff * diff / self.variances[None, :, :], axis=2)
        )
        return logsumexp(np.log(self.weights + EPS)[None, :] + log_component, axis=1)


@dataclass
class CosineShelfMixture:
    """Library occupancy times a within-shelf cosine-residual density."""

    weights: np.ndarray
    centers: np.ndarray
    gamma_shape: np.ndarray
    gamma_scale: np.ndarray

    def log_density(self, counts: np.ndarray) -> np.ndarray:
        values = np.asarray(counts, dtype=np.float64)
        if values.ndim == 1:
            values = values[None, :]
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
        return logsumexp(np.log(self.weights + EPS)[None, :] + log_residual, axis=1)


@dataclass
class KNNModel:
    training: np.ndarray
    k: int

    def log_density(self, coordinates: np.ndarray) -> np.ndarray:
        x = np.asarray(coordinates, dtype=np.float64)
        k = min(self.k, len(self.training))
        neighbors = NearestNeighbors(n_neighbors=k, metric="euclidean")
        neighbors.fit(self.training)
        distances = neighbors.kneighbors(x, return_distance=True)[0][:, -1]
        dimension = self.training.shape[1]
        # Unit-ball log volume in q dimensions.
        log_volume = (dimension / 2.0) * np.log(np.pi) - gammaln(
            dimension / 2.0 + 1.0
        )
        return (
            np.log(k)
            - np.log(len(self.training))
            - log_volume
            - dimension * np.log(np.maximum(distances, 1e-9))
        )


@dataclass
class HalfLandscape:
    projection: Projection
    mixture: CosineShelfMixture
    knn: KNNModel
    calibration_median: dict[str, float]
    calibration_mad: dict[str, float]
    atlas_centers: np.ndarray
    selected_k: int
    validation_log_likelihood: float
    training_counts: np.ndarray
    calibration_counts: np.ndarray

    def score(self, counts: np.ndarray, estimator: str) -> np.ndarray:
        if estimator == "mixture":
            raw = -self.mixture.log_density(counts)
        elif estimator == "knn":
            coordinates = self.projection.transform(counts)
            raw = -self.knn.log_density(coordinates)
        else:
            raise ValueError(estimator)
        return (raw - self.calibration_median[estimator]) / self.calibration_mad[
            estimator
        ]


@dataclass
class LandscapeEnsemble:
    halves: tuple[HalfLandscape, HalfLandscape]

    def score_halves(self, counts: np.ndarray, estimator: str) -> np.ndarray:
        return np.column_stack([half.score(counts, estimator) for half in self.halves])

    def score(self, counts: np.ndarray, estimator: str) -> np.ndarray:
        return self.score_halves(counts, estimator).mean(axis=1)

    @property
    def atlas_centers(self) -> np.ndarray:
        centers = np.vstack([half.atlas_centers for half in self.halves])
        # Keep independent-half shelves; duplicates are harmless baselines.
        return centers / np.maximum(np.linalg.norm(centers, axis=1, keepdims=True), EPS)


@dataclass
class PhaseConditionalHalf:
    projection: Projection
    means: np.ndarray
    variances: np.ndarray
    calibration_median: np.ndarray
    calibration_mad: np.ndarray

    def score(self, phase_counts: np.ndarray) -> np.ndarray:
        values = np.asarray(phase_counts)
        if values.ndim != 3 or values.shape[1] != len(self.means):
            raise ValueError("phase compositions must have shape (n, phase, species)")
        coordinates = self.projection.transform(values.reshape(-1, values.shape[-1])).reshape(
            values.shape[0], values.shape[1], -1
        )
        difference = coordinates - self.means[None, :, :]
        raw = 0.5 * (
            np.sum(np.log(2.0 * np.pi * self.variances), axis=1)[None, :]
            + np.sum(difference * difference / self.variances[None, :, :], axis=2)
        )
        return (raw - self.calibration_median[None, :]) / self.calibration_mad[None, :]


@dataclass
class PhaseConditionalEnsemble:
    halves: tuple[PhaseConditionalHalf, PhaseConditionalHalf]

    def score(self, phase_counts: np.ndarray) -> np.ndarray:
        return np.mean([half.score(phase_counts) for half in self.halves], axis=0)


def _fit_projection(
    training: np.ndarray,
    pseudocount: float,
    variance_target: float,
    min_components: int,
    max_components: int,
) -> tuple[Projection, np.ndarray]:
    clr = clr_transform(training, pseudocount)
    full = PCA(n_components=min(max_components, clr.shape[0] - 1, clr.shape[1] - 1))
    raw = full.fit_transform(clr)
    cumulative = np.cumsum(full.explained_variance_ratio_)
    q = int(np.searchsorted(cumulative, variance_target) + 1)
    q = max(min_components, min(q, max_components, raw.shape[1]))
    coords = raw[:, :q]
    mean = coords.mean(axis=0)
    sd = coords.std(axis=0, ddof=1)
    sd = np.where(sd < 1e-8, 1.0, sd)
    projection = Projection(
        clr_mean=full.mean_.copy(),
        components=full.components_[:q].copy(),
        scale_mean=mean,
        scale_sd=sd,
        pseudocount=pseudocount,
    )
    return projection, (coords - mean) / sd


def _trajectory_folds(lineage_ids: np.ndarray, folds: int) -> list[tuple[np.ndarray, np.ndarray]]:
    unique = np.unique(lineage_ids)
    folds = max(2, min(folds, len(unique)))
    result = []
    for fold in range(folds):
        valid_lineages = unique[np.arange(len(unique)) % folds == fold]
        valid = np.isin(lineage_ids, valid_lineages)
        if valid.any() and (~valid).any():
            result.append((~valid, valid))
    return result


def _spherical_kmeans(
    counts: np.ndarray,
    k: int,
    seed: int,
    n_init: int = 8,
    iterations: int = 100,
) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(counts, dtype=np.float64)
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
            if np.allclose(updated, centers, atol=1e-10):
                centers = updated
                break
            centers = updated
        labels = np.argmax(values @ centers.T, axis=1)
        loss = float(np.sum(1.0 - np.max(values @ centers.T, axis=1)))
        if best is None or loss < best[0]:
            best = (loss, centers.copy(), labels.copy())
    if best is None:
        raise ValueError("spherical k-means failed")
    return best[1], best[2]


def _fit_cosine_mixture(
    counts: np.ndarray,
    k: int,
    seed: int,
) -> tuple[CosineShelfMixture, np.ndarray]:
    centers, labels = _spherical_kmeans(counts, k, seed)
    values = np.asarray(counts, dtype=np.float64)
    values /= np.maximum(np.linalg.norm(values, axis=1, keepdims=True), EPS)
    assigned_distance = np.maximum(
        1.0 - np.sum(values * centers[labels], axis=1), 1e-9
    )
    global_mean = max(float(np.mean(assigned_distance)), 1e-6)
    global_variance = max(float(np.var(assigned_distance, ddof=1)), 1e-8)
    weights = []
    shapes = []
    scales = []
    for component in range(k):
        residual = assigned_distance[labels == component]
        mean = max(float(np.mean(residual)) if len(residual) else global_mean, 1e-6)
        variance = (
            max(float(np.var(residual, ddof=1)), 1e-8)
            if len(residual) >= 3
            else global_variance
        )
        shape = float(np.clip(mean * mean / variance, 0.2, 200.0))
        scale = float(np.clip(variance / mean, 1e-7, 1.0))
        weights.append(max(int(np.count_nonzero(labels == component)), 1))
        shapes.append(shape)
        scales.append(scale)
    weight_array = np.asarray(weights, dtype=np.float64)
    weight_array /= weight_array.sum()
    return (
        CosineShelfMixture(
            weights=weight_array,
            centers=centers,
            gamma_shape=np.asarray(shapes),
            gamma_scale=np.asarray(scales),
        ),
        labels,
    )


def _select_mixture_k(
    counts: np.ndarray,
    lineage_ids: np.ndarray,
    k_max: int,
    seed: int,
) -> tuple[int, float]:
    best: tuple[float, int] | None = None
    folds = _trajectory_folds(lineage_ids, min(4, len(np.unique(lineage_ids))))
    for k in range(1, min(k_max, len(counts) // 10) + 1):
        values = []
        for fold, (train, valid) in enumerate(folds):
            model, _ = _fit_cosine_mixture(counts[train], k, seed + fold)
            values.append(float(np.mean(model.log_density(counts[valid]))))
        score = float(np.mean(values)) if values else float("-inf")
        if best is None or score > best[0] + 1e-10 or (
            abs(score - best[0]) <= 1e-10 and k < best[1]
        ):
            best = (score, k)
    if best is None:
        raise ValueError("not enough reference states to fit mixture")
    return best[1], best[0]


def _robust_location_scale(values: np.ndarray) -> tuple[float, float]:
    median = float(np.median(values))
    mad = float(1.4826 * np.median(np.abs(values - median)))
    if mad < 1e-8:
        mad = float(np.std(values, ddof=1))
    return median, max(mad, 1e-8)


def _atlas_centers(training_counts: np.ndarray, labels: np.ndarray, k: int) -> np.ndarray:
    normalized = training_counts.astype(np.float64)
    normalized /= np.maximum(np.linalg.norm(normalized, axis=1, keepdims=True), EPS)
    centers = []
    for index in range(k):
        selected = normalized[labels == index]
        center = selected.mean(axis=0) if len(selected) else normalized[0]
        centers.append(center / max(float(np.linalg.norm(center)), EPS))
    return np.stack(centers)


def fit_half_landscape(
    training_counts: np.ndarray,
    training_lineages: np.ndarray,
    calibration_counts: np.ndarray,
    *,
    pseudocount: float,
    pca_variance: float,
    pca_min: int,
    pca_max: int,
    k_max: int,
    knn_k: int,
    subsample: int,
    seed: int,
) -> HalfLandscape:
    rng = np.random.default_rng(seed)
    if len(training_counts) > subsample:
        chosen = np.sort(rng.choice(len(training_counts), subsample, replace=False))
        training_counts = training_counts[chosen]
        training_lineages = training_lineages[chosen]
    projection, coordinates = _fit_projection(
        training_counts, pseudocount, pca_variance, pca_min, pca_max
    )
    selected_k, validation = _select_mixture_k(
        training_counts, training_lineages, k_max, seed
    )
    mixture, labels = _fit_cosine_mixture(training_counts, selected_k, seed)
    knn = KNNModel(training=coordinates.copy(), k=min(knn_k, len(coordinates)))
    calibration_coordinates = projection.transform(calibration_counts)
    raw = {
        "mixture": -mixture.log_density(calibration_counts),
        "knn": -knn.log_density(calibration_coordinates),
    }
    location: dict[str, float] = {}
    scale: dict[str, float] = {}
    for name, values in raw.items():
        location[name], scale[name] = _robust_location_scale(values)
    centers = mixture.centers.copy()
    return HalfLandscape(
        projection=projection,
        mixture=mixture,
        knn=knn,
        calibration_median=location,
        calibration_mad=scale,
        atlas_centers=centers,
        selected_k=selected_k,
        validation_log_likelihood=validation,
        training_counts=training_counts.copy(),
        calibration_counts=calibration_counts.copy(),
    )


def fit_landscape_ensemble(
    counts: np.ndarray,
    lineage_ids: np.ndarray,
    **kwargs: object,
) -> LandscapeEnsemble:
    lineages = np.unique(lineage_ids)
    if len(lineages) < 2:
        raise ValueError("at least two reference lineages are required")
    left_ids = lineages[::2]
    right_ids = lineages[1::2]
    left = np.isin(lineage_ids, left_ids)
    right = np.isin(lineage_ids, right_ids)
    if not left.any() or not right.any():
        raise ValueError("both reference halves must contain states")
    seed = int(kwargs.pop("seed"))
    first = fit_half_landscape(
        counts[left], lineage_ids[left], counts[right], seed=seed, **kwargs
    )
    second = fit_half_landscape(
        counts[right], lineage_ids[right], counts[left], seed=seed + 1, **kwargs
    )
    return LandscapeEnsemble((first, second))


def fit_phase_conditional_ensemble(
    phase_counts: np.ndarray,
    lineage_ids: np.ndarray,
    landscape: LandscapeEnsemble,
) -> PhaseConditionalEnsemble:
    """Fit the registered calibration-only p(c|phase) Gaussian family."""

    counts = np.asarray(phase_counts)
    lineages = np.unique(lineage_ids)
    split_ids = (lineages[::2], lineages[1::2])
    halves = []
    for index, training_ids in enumerate(split_ids):
        calibration_ids = split_ids[1 - index]
        training = np.isin(lineage_ids, training_ids)
        calibration = np.isin(lineage_ids, calibration_ids)
        projection = landscape.halves[index].projection
        train_coords = projection.transform(
            counts[training].reshape(-1, counts.shape[-1])
        ).reshape(int(training.sum()), counts.shape[1], -1)
        calibration_coords = projection.transform(
            counts[calibration].reshape(-1, counts.shape[-1])
        ).reshape(int(calibration.sum()), counts.shape[1], -1)
        means = train_coords.mean(axis=0)
        variances = np.maximum(train_coords.var(axis=0, ddof=1), 1e-4)
        difference = calibration_coords - means[None, :, :]
        raw = 0.5 * (
            np.sum(np.log(2.0 * np.pi * variances), axis=1)[None, :]
            + np.sum(difference * difference / variances[None, :, :], axis=2)
        )
        medians = np.median(raw, axis=0)
        mads = 1.4826 * np.median(np.abs(raw - medians[None, :]), axis=0)
        fallback = raw.std(axis=0, ddof=1)
        mads = np.where(mads < 1e-8, fallback, mads)
        mads = np.maximum(mads, 1e-8)
        halves.append(
            PhaseConditionalHalf(
                projection=projection,
                means=means,
                variances=variances,
                calibration_median=medians,
                calibration_mad=mads,
            )
        )
    return PhaseConditionalEnsemble(tuple(halves))  # type: ignore[arg-type]


def nearest_atlas_distance(counts: np.ndarray, centers: np.ndarray) -> np.ndarray:
    values = np.asarray(counts, dtype=np.float64)
    if values.ndim == 1:
        values = values[None, :]
    values /= np.maximum(np.linalg.norm(values, axis=1, keepdims=True), EPS)
    return 1.0 - np.max(values @ centers.T, axis=1)


def fit_fixed_target_landscape(model: LandscapeEnsemble) -> LandscapeEnsemble:
    """Return the registered K=1 comparator without refitting outcomes."""

    halves = []
    for half in model.halves:
        mixture, _ = _fit_cosine_mixture(half.training_counts, 1, seed=0)
        raw = -mixture.log_density(half.calibration_counts)
        med, mad = _robust_location_scale(raw)
        center = mixture.centers.copy()
        halves.append(
            HalfLandscape(
                projection=half.projection,
                mixture=mixture,
                knn=half.knn,
                calibration_median={"mixture": med, "knn": half.calibration_median["knn"]},
                calibration_mad={"mixture": mad, "knn": half.calibration_mad["knn"]},
                atlas_centers=center,
                selected_k=1,
                validation_log_likelihood=float(np.mean(-raw)),
                training_counts=half.training_counts.copy(),
                calibration_counts=half.calibration_counts.copy(),
            )
        )
    return LandscapeEnsemble(tuple(halves))  # type: ignore[arg-type]
