from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from fep_surprise.dynamics import expected_flux
from plastic_heredity.config import GardConfig, SimulationContract

from .config import ARMS, MORPH_LEVELS, PERMUTATION_COUNTS


EPS = 1e-15


@dataclass(frozen=True)
class ArmLaunch:
    name: str
    beta: np.ndarray
    composition: np.ndarray
    atlas_key: str
    alignment_order: np.ndarray | None


def nested_swap_orders(n_types: int, seed: int) -> dict[int, np.ndarray]:
    """Return nested involutions made from one frozen random perfect matching."""

    if n_types % 2:
        raise ValueError("nested disjoint swaps require an even type count")
    rng = np.random.default_rng(seed)
    matching = rng.permutation(n_types).reshape(-1, 2)
    output: dict[int, np.ndarray] = {}
    for count in PERMUTATION_COUNTS:
        if count > n_types or count % 2:
            raise ValueError("invalid nested permutation dose")
        order = np.arange(n_types, dtype=np.int64)
        for left, right in matching[: count // 2]:
            order[left], order[right] = order[right], order[left]
        if not np.array_equal(order[order], np.arange(n_types)):
            raise AssertionError("nested swap order must be an involution")
        output[count] = order
    return output


def permute_beta(beta: np.ndarray, order: np.ndarray) -> np.ndarray:
    values = np.asarray(beta, dtype=np.float64)
    permutation = np.asarray(order, dtype=np.int64)
    return values[np.ix_(permutation, permutation)].copy()


def permute_composition(composition: np.ndarray, order: np.ndarray) -> np.ndarray:
    return np.asarray(composition)[np.asarray(order, dtype=np.int64)].copy()


def log_morph(beta: np.ndarray, endpoint: np.ndarray, level: float) -> np.ndarray:
    if not 0.0 <= level <= 1.0:
        raise ValueError("morph level must lie in [0,1]")
    left = np.asarray(beta, dtype=np.float64)
    right = np.asarray(endpoint, dtype=np.float64)
    if left.shape != right.shape or np.any(left <= 0.0) or np.any(right <= 0.0):
        raise ValueError("log morph requires aligned positive beta matrices")
    return np.exp((1.0 - level) * np.log(left) + level * np.log(right))


def beta_variants(beta: np.ndarray, orders: dict[int, np.ndarray]) -> dict[str, np.ndarray]:
    values = np.asarray(beta, dtype=np.float64)
    output = {"native": values.copy()}
    for count, order in orders.items():
        output[f"perm_{count}"] = permute_beta(values, order)
    endpoint = output["perm_100"]
    for level in MORPH_LEVELS:
        output[f"morph_{int(round(100 * level)):03d}"] = log_morph(
            values, endpoint, level
        )
    return output


def arm_launches(
    beta: np.ndarray,
    composition: np.ndarray,
    orders: dict[int, np.ndarray],
) -> dict[str, ArmLaunch]:
    variants = beta_variants(beta, orders)
    state = np.asarray(composition, dtype=np.int64)
    full = orders[100]
    output: dict[str, ArmLaunch] = {
        "NOOP": ArmLaunch("NOOP", variants["native"], state.copy(), "native", None),
        "COMPOSITION_ONLY_100": ArmLaunch(
            "COMPOSITION_ONLY_100",
            variants["native"],
            permute_composition(state, full),
            "native",
            None,
        ),
        "ISOMORPHIC_BOTH_100": ArmLaunch(
            "ISOMORPHIC_BOTH_100",
            variants["perm_100"],
            permute_composition(state, full),
            "perm_100",
            full,
        ),
    }
    for count in PERMUTATION_COUNTS:
        name = f"PERM_BETA_{count}"
        output[name] = ArmLaunch(
            name, variants[f"perm_{count}"], state.copy(), f"perm_{count}", None
        )
    for level in MORPH_LEVELS:
        suffix = int(round(100 * level))
        name = f"MORPH_BETA_{suffix:03d}"
        output[name] = ArmLaunch(
            name, variants[f"morph_{suffix:03d}"], state.copy(), f"morph_{suffix:03d}", None
        )
    if tuple(output) != ARMS:
        output = {name: output[name] for name in ARMS}
    return output


def _proposal_rates(
    beta: np.ndarray,
    composition: np.ndarray,
    gard: GardConfig,
    contract: SimulationContract,
) -> np.ndarray:
    state = np.asarray(composition, dtype=np.float64)
    mass = max(float(state.sum()), 1.0)
    boost = 1.0 + np.asarray(beta, dtype=np.float64) @ state / mass
    join = gard.k_join * (1.0 / gard.n_types) * mass * boost
    leave = gard.k_leave * state * boost
    return contract.poisson_exposure * np.concatenate([join, leave])


def product_poisson_hellinger(
    beta_from: np.ndarray,
    composition_from: np.ndarray,
    beta_to: np.ndarray,
    composition_to: np.ndarray,
    gard: GardConfig,
    contract: SimulationContract,
    *,
    align_to_order: np.ndarray | None = None,
) -> float:
    left = _proposal_rates(beta_from, composition_from, gard, contract)
    right = _proposal_rates(beta_to, composition_to, gard, contract)
    if align_to_order is not None:
        order = np.asarray(align_to_order, dtype=np.int64)
        size = len(order)
        inverse = np.argsort(order)
        right = np.concatenate([right[:size][inverse], right[size:][inverse]])
    exponent = -0.5 * float(np.sum((np.sqrt(left) - np.sqrt(right)) ** 2))
    return float(1.0 - np.exp(exponent))


def launch_metrics(
    beta: np.ndarray,
    composition: np.ndarray,
    launch: ArmLaunch,
    gard: GardConfig,
    contract: SimulationContract,
) -> np.ndarray:
    source_beta = np.asarray(beta, dtype=np.float64)
    source_state = np.asarray(composition, dtype=np.float64)
    target_state = np.asarray(launch.composition, dtype=np.float64)
    beta_delta = np.asarray(launch.beta, dtype=np.float64) - source_beta
    log_delta = np.log(np.asarray(launch.beta, dtype=np.float64)) - np.log(source_beta)
    source_flux = expected_flux(source_state, source_beta, gard)
    target_flux = expected_flux(target_state, launch.beta, gard)
    source_throughput = max(float(source_state @ source_beta @ source_state), EPS)
    target_throughput = max(float(target_state @ launch.beta @ target_state), EPS)
    source_norm = max(float(np.linalg.norm(source_state)), EPS)
    target_norm = max(float(np.linalg.norm(target_state)), EPS)
    composition_distance = 1.0 - float(
        source_state @ target_state / (source_norm * target_norm)
    )
    mismatch = product_poisson_hellinger(
        source_beta,
        source_state,
        launch.beta,
        target_state,
        gard,
        contract,
        align_to_order=launch.alignment_order,
    )
    name = launch.name
    permutation_fraction = (
        float(name.rsplit("_", 1)[1]) / gard.n_types
        if name.startswith("PERM_BETA_")
        else 0.0
    )
    morph_level = (
        float(name.rsplit("_", 1)[1]) / 100.0
        if name.startswith("MORPH_BETA_")
        else 0.0
    )
    return np.asarray(
        [
            permutation_fraction,
            morph_level,
            float(name.startswith("PERM_BETA_")),
            float(name.startswith("MORPH_BETA_")),
            float(name == "COMPOSITION_ONLY_100"),
            float(name == "ISOMORPHIC_BOTH_100"),
            float(np.linalg.norm(beta_delta)),
            float(np.linalg.norm(log_delta)),
            composition_distance,
            float(np.log(target_throughput / source_throughput)),
            float(np.linalg.norm(target_flux - source_flux)),
            mismatch,
        ],
        dtype=np.float64,
    )


LAUNCH_METRIC_NAMES = (
    "permutation_fraction",
    "morph_level",
    "is_permutation_series",
    "is_morph_series",
    "is_composition_only",
    "is_isomorphism",
    "beta_frobenius_edit",
    "beta_log_frobenius_edit",
    "composition_cosine_distance",
    "log_throughput_ratio",
    "expected_flux_l2_edit",
    "local_poisson_hellinger",
)
