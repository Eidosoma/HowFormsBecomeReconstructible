"""Synthetic spatial operators only. No tissue dynamics or scientific runner.

Offline decomposition/score functions must remain outside any deployed
controller interface. Native centering and sequential updates are NOT here.
"""
from __future__ import annotations

import numpy as np

LEVELS = ("site", "region", "sheet")


def field(x):
    x = np.asarray(x, dtype=np.float64)
    if x.shape != (16, 16) or not np.isfinite(x).all():
        raise ValueError("Expected a finite 16 by 16 field")
    return x


def center(x):
    x = field(x)
    return x - x.mean()


def block_projection(x, size):
    x = field(x)
    if size not in (1, 4, 8, 16):
        raise ValueError("Declared block sizes are 1, 4, 8 and 16")
    means = x.reshape(16 // size, size, 16 // size, size).mean(axis=(1, 3))
    return means.repeat(size, axis=0).repeat(size, axis=1)


def spatial_operator(x, level):
    """Mathematical aggregate; this is not a distributed communication engine."""
    if level == "site":
        return field(x).copy()
    if level == "region":
        return block_projection(x, 4)
    if level == "sheet":
        return center(block_projection(x, 8))
    raise ValueError(f"Unknown level: {level}")


def sensing_then_action(discrepancy, sensor, actuator):
    return spatial_operator(spatial_operator(discrepancy, sensor), actuator)


def shifted_operator(x, level, offset=(1, 1)):
    """Translate the grid, not the resulting physical coordinates."""
    x = field(x)
    rolled = np.roll(x, tuple(-int(k) for k in offset), axis=(0, 1))
    return np.roll(spatial_operator(rolled, level), offset, axis=(0, 1))


def error_bands(x):
    """Offline orthogonal decomposition, retaining the constant component."""
    x = field(x)
    p4, p8 = block_projection(x, 4), block_projection(x, 8)
    dc = np.full_like(x, x.mean())
    return {"fine": x - p4, "regional": p4 - p8,
            "collective": p8 - dc, "constant": dc}


def offline_scores(body, target):
    """Evaluator-only percentages; qualification is an intersection, not a sum."""
    body, target = field(body), field(target)
    matching = (body > 0) == (target > 0)
    eligible = np.abs(body) > 0.2
    joint = np.array([[np.sum((matching == m) & (eligible == a))
                       for a in (False, True)] for m in (False, True)])
    return {"sign_percent": float(100 * matching.mean()),
            "amplitude_percent": float(100 * eligible.mean()),
            "qualified_percent": float(100 * (matching & eligible).mean()),
            "joint_counts_match_by_eligible": joint.tolist()}
