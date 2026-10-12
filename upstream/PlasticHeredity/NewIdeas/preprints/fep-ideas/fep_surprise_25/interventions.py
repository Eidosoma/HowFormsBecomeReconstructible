from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from fep_surprise.dynamics import expected_flux
from fep_surprise_2.interventions import (
    log_morph,
    nested_swap_orders,
    permute_beta,
    permute_composition,
    product_poisson_hellinger,
)
from plastic_heredity.config import GardConfig, SimulationContract

from .config import ARMS


EPS = 1e-15


def log_beta_sigma(beta: np.ndarray) -> float:
    values = np.log(np.asarray(beta, dtype=np.float64))
    return float(np.std(values, ddof=0))


def sigma_variant(beta: np.ndarray, sigma: float) -> np.ndarray:
    """Set log-beta spread while preserving the original arithmetic mean."""

    values = np.asarray(beta, dtype=np.float64)
    if np.any(values <= 0) or sigma <= 0:
        raise ValueError("sigma transform requires positive beta and sigma")
    logs = np.log(values)
    centered = logs - float(np.mean(logs))
    spread = float(np.std(centered, ddof=0))
    if spread <= 0:
        raise ValueError("cannot rescale a constant log-beta matrix")
    transformed = np.exp(centered * (float(sigma) / spread))
    transformed *= float(np.mean(values)) / float(np.mean(transformed))
    return transformed


def variance_preserved_morph(
    beta: np.ndarray, endpoint: np.ndarray, level: float
) -> np.ndarray:
    """Log-morph, then restore native log spread and arithmetic mean."""

    native = np.asarray(beta, dtype=np.float64)
    raw = log_morph(native, endpoint, level)
    transformed = sigma_variant(raw, log_beta_sigma(native))
    transformed *= float(np.mean(native)) / float(np.mean(transformed))
    return transformed


def beta_variants25(beta: np.ndarray, order: np.ndarray) -> dict[str, np.ndarray]:
    native = np.asarray(beta, dtype=np.float64).copy()
    permuted = permute_beta(native, order)
    return {
        "native": native,
        "sigma_250": sigma_variant(native, 2.50),
        "sigma_325": sigma_variant(native, 3.25),
        "sigma_500": sigma_variant(native, 5.00),
        "raw_morph_050": log_morph(native, permuted, 0.50),
        "normalized_morph_050": variance_preserved_morph(native, permuted, 0.50),
    }


@dataclass(frozen=True)
class Arm25Launch:
    name: str
    beta: np.ndarray
    composition: np.ndarray
    atlas_key: str
    alignment_order: np.ndarray | None = None


def arm_launches25(
    beta: np.ndarray, composition: np.ndarray, order: np.ndarray
) -> dict[str, Arm25Launch]:
    variants = beta_variants25(beta, order)
    state = np.asarray(composition, dtype=np.int64)
    output = {
        "ALIGNED_NATIVE": Arm25Launch(
            "ALIGNED_NATIVE", variants["native"], state.copy(), "native"
        ),
        "ALIGNED_SIGMA_250": Arm25Launch(
            "ALIGNED_SIGMA_250", variants["sigma_250"], state.copy(), "sigma_250"
        ),
        "PERM_SIGMA_250": Arm25Launch(
            "PERM_SIGMA_250", permute_beta(variants["sigma_250"], order),
            state.copy(), "perm_sigma_250"
        ),
        "ALIGNED_SIGMA_325": Arm25Launch(
            "ALIGNED_SIGMA_325", variants["sigma_325"], state.copy(), "sigma_325"
        ),
        "PERM_SIGMA_325": Arm25Launch(
            "PERM_SIGMA_325", permute_beta(variants["sigma_325"], order),
            state.copy(), "perm_sigma_325"
        ),
        "PERM_NATIVE": Arm25Launch(
            "PERM_NATIVE", permute_beta(variants["native"], order),
            state.copy(), "perm_native"
        ),
        "ALIGNED_SIGMA_500": Arm25Launch(
            "ALIGNED_SIGMA_500", variants["sigma_500"], state.copy(), "sigma_500"
        ),
        "PERM_SIGMA_500": Arm25Launch(
            "PERM_SIGMA_500", permute_beta(variants["sigma_500"], order),
            state.copy(), "perm_sigma_500"
        ),
        "RAW_MORPH_050": Arm25Launch(
            "RAW_MORPH_050", variants["raw_morph_050"], state.copy(), "raw_morph_050"
        ),
        "NORMALIZED_MORPH_050": Arm25Launch(
            "NORMALIZED_MORPH_050", variants["normalized_morph_050"],
            state.copy(), "normalized_morph_050"
        ),
        "COMPOSITION_ONLY_100": Arm25Launch(
            "COMPOSITION_ONLY_100", variants["native"],
            permute_composition(state, order), "native"
        ),
        "ISOMORPHIC_BOTH_100": Arm25Launch(
            "ISOMORPHIC_BOTH_100", permute_beta(variants["native"], order),
            permute_composition(state, order), "perm_native", order
        ),
    }
    return {name: output[name] for name in ARMS}


LAUNCH_METRIC_NAMES = (
    "target_log_beta_sigma",
    "is_permuted",
    "is_sigma_scaled",
    "is_raw_morph",
    "is_normalized_morph",
    "is_composition_only",
    "is_isomorphism",
    "beta_frobenius_edit",
    "beta_log_frobenius_edit",
    "composition_cosine_distance",
    "log_throughput_ratio",
    "expected_flux_l2_edit",
    "local_poisson_hellinger",
)


def launch_metrics25(
    beta: np.ndarray,
    composition: np.ndarray,
    launch: Arm25Launch,
    gard: GardConfig,
    contract: SimulationContract,
) -> np.ndarray:
    source_beta = np.asarray(beta, dtype=np.float64)
    source_state = np.asarray(composition, dtype=np.float64)
    target_state = np.asarray(launch.composition, dtype=np.float64)
    beta_delta = np.asarray(launch.beta) - source_beta
    log_delta = np.log(np.asarray(launch.beta)) - np.log(source_beta)
    source_flux = expected_flux(source_state, source_beta, gard)
    target_flux = expected_flux(target_state, launch.beta, gard)
    source_throughput = max(float(source_state @ source_beta @ source_state), EPS)
    target_throughput = max(float(target_state @ launch.beta @ target_state), EPS)
    denominator = max(
        float(np.linalg.norm(source_state) * np.linalg.norm(target_state)), EPS
    )
    mismatch = product_poisson_hellinger(
        source_beta, source_state, launch.beta, target_state, gard, contract,
        align_to_order=launch.alignment_order,
    )
    name = launch.name
    return np.asarray(
        [
            log_beta_sigma(launch.beta),
            float(name.startswith("PERM_") or name == "ISOMORPHIC_BOTH_100"),
            float("SIGMA" in name),
            float(name == "RAW_MORPH_050"),
            float(name == "NORMALIZED_MORPH_050"),
            float(name == "COMPOSITION_ONLY_100"),
            float(name == "ISOMORPHIC_BOTH_100"),
            float(np.linalg.norm(beta_delta)),
            float(np.linalg.norm(log_delta)),
            1.0 - float(source_state @ target_state / denominator),
            float(np.log(target_throughput / source_throughput)),
            float(np.linalg.norm(target_flux - source_flux)),
            mismatch,
        ],
        dtype=np.float64,
    )
