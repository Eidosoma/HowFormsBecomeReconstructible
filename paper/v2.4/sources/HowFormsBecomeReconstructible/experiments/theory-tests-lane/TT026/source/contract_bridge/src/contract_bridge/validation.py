"""Pre-flight validation: pins, kernels, gauge exactness, isolation."""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np

from finite_gard_ruliad.combinatorics import RuleCodec
from finite_gard_ruliad.kernels import make_state_spaces, solve_absorption

from .artifacts import environment_manifest, sha256_file
from .config import (
    SEALED_BINOMIAL_CSV_SHA256,
    BridgeConfig,
    capsule_root,
    sibling_root,
)
from .physics import closed_kernel, expected_physical_time, gauge_beta

_FORBIDDEN_IMPORT_FRAGMENTS = ("fable", "plato")


def _isolation_scan() -> list[str]:
    violations = []
    for path in sorted((capsule_root() / "src").rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if any(fragment in name.lower() for fragment in _FORBIDDEN_IMPORT_FRAGMENTS):
                    violations.append(f"{path.name}: {name}")
    return violations


def validate_bridge(config: BridgeConfig) -> dict:
    config.validate()
    atlas = config.atlas()
    spaces = make_state_spaces(atlas)
    codec = RuleCodec(atlas)

    checks: dict[str, object] = {
        "config_digest": config.digest(),
        "e1_atlas_digest": atlas.digest(),
        "environment": environment_manifest(),
    }

    if config.mode == "full":
        sealed = (
            sibling_root("finite_gard_ruliad")
            / "results"
            / "full"
            / "binomial_strict_diagnostic.csv"
        )
        if not sealed.exists():
            raise RuntimeError(f"sealed E1 diagnostic missing: {sealed}")
        digest = sha256_file(sealed)
        if digest != SEALED_BINOMIAL_CSV_SHA256:
            raise RuntimeError(
                "sealed E1 binomial diagnostic hash changed; refusing to proceed"
            )
        checks["sealed_binomial_csv"] = "hash_ok"

    probe_rule = codec.rule_orbits()[len(codec.rule_orbits()) // 2].canonical_id
    beta = codec.matrix(probe_rule)
    tol = atlas.numeric_tolerance
    row_errors = {}
    for contract in ("equal", "binomial"):
        kernel = closed_kernel(probe_rule, beta, contract, atlas, spaces)
        row_errors[contract] = float(
            np.max(np.abs(kernel.transition.sum(axis=1) + kernel.death - 1.0))
        )
        if row_errors[contract] > tol:
            raise RuntimeError(f"{contract} kernel row sums out of tolerance")
    checks["kernel_row_errors"] = row_errors

    absorption = solve_absorption(probe_rule, beta, atlas, spaces)
    gauged = solve_absorption(
        probe_rule, gauge_beta(beta, config.gauge_factor), atlas, spaces
    )
    gauge_error = float(np.max(np.abs(gauged.probabilities - absorption.probabilities)))
    if gauge_error > tol:
        raise RuntimeError(f"clock gauge broke the embedded chain: {gauge_error:.3g}")
    checks["gauge_absorption_error"] = gauge_error

    base_time = expected_physical_time(beta, atlas, spaces)
    gauged_time = expected_physical_time(
        gauge_beta(beta, config.gauge_factor), atlas, spaces
    )
    positive = base_time > 0
    ratio_error = float(
        np.max(np.abs(gauged_time[positive] * config.gauge_factor - base_time[positive]))
    )
    if ratio_error > tol * float(np.max(base_time)):
        raise RuntimeError(f"physical time did not rescale by the gauge: {ratio_error:.3g}")
    checks["gauge_time_ratio_error"] = ratio_error

    violations = _isolation_scan()
    if violations:
        raise RuntimeError(f"isolation violations: {violations}")
    checks["isolation"] = "clean"
    return checks
