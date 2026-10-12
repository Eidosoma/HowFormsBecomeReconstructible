from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from fep_surprise.tracing import trace_future
from fep_surprise_25.interventions import beta_variants25
from fep_surprise_25.regime import load_screen
from plastic_heredity.config import CANDIDATES as SIMULATOR_CONTRACTS
from plastic_heredity.config import GardConfig
from plastic_heredity.seeds import derive_seed
from plastic_heredity.simulator import generate_initial_composition


def exposed_matrix189_reference_regression(
    source_run_root: Path,
    source_master_seed: str,
    profile: str,
    reference_burnin: int,
    reference_fissions: int,
    phase_grid: tuple[float, ...],
) -> dict[str, Any]:
    """Exercise the known endpoint at scientific scale in a non-scientific domain."""

    if profile != "full":
        return {
            "status": "NONSCIENTIFIC_PROFILE_SKIPPED",
            "all_parity_halves_at_least_600": True,
        }
    screen = load_screen(
        source_run_root.resolve() / profile / "screen" / "cells" / "screen_m0189.joblib"
    )
    beta = beta_variants25(
        np.asarray(screen["beta"], dtype=np.float64),
        np.asarray(screen["order"], dtype=np.int64),
    )["sigma_500"]
    gard = GardConfig(generations=80)
    candidates: dict[str, Any] = {}
    for candidate in ("02", "03"):
        retained = [0, 0]
        contributors = [set(), set()]
        completed = 0
        terminal = 0
        lengths = []
        for lineage in range(96):
            initial = generate_initial_composition(
                gard,
                np.random.default_rng(
                    derive_seed(
                        source_master_seed,
                        "experiment25.confirmation.reference.initial",
                        189,
                        candidate,
                        "sigma_500",
                        lineage,
                    )
                ),
            )
            traced, complete = trace_future(
                initial,
                beta,
                gard,
                SIMULATOR_CONTRACTS[candidate],
                reference_fissions,
                np.random.default_rng(
                    derive_seed(
                        source_master_seed,
                        "experiment25.confirmation.reference.dynamics",
                        189,
                        candidate,
                        "sigma_500",
                        lineage,
                    )
                ),
                phase_grid,
            )
            length = len(traced)
            lengths.append(length)
            completed += int(complete)
            terminal += int(not complete)
            retained[lineage % 2] += max(0, length - reference_burnin)
            if length > reference_burnin:
                contributors[lineage % 2].add(lineage)
        candidates[candidate] = {
            "lineages": 96,
            "complete_lineages": completed,
            "terminal_prefixes": terminal,
            "retained_by_parity_half": retained,
            "contributing_lineages_by_parity_half": [
                len(contributors[0]),
                len(contributors[1]),
            ],
            "minimum_trace_length": min(lengths),
            "maximum_trace_length": max(lengths),
            "both_halves_at_least_600": bool(
                min(retained) >= 600 and min(map(len, contributors)) >= 4
            ),
        }
    return {
        "status": "EXPOSED_DIAGNOSTIC_DOMAIN_NOT_AMENDMENT_DATA",
        "matrix_id": 189,
        "atlas": "sigma_500",
        "candidates": candidates,
        "all_parity_halves_at_least_600": bool(
            all(value["both_halves_at_least_600"] for value in candidates.values())
        ),
    }


__all__ = ["exposed_matrix189_reference_regression"]
