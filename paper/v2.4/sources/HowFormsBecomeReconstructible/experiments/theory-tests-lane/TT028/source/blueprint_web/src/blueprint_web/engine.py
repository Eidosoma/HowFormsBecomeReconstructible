"""The blueprint substrates.

Rung T: R is a per-lineage full-field reference, updated as a slow EMA of
V (rho per sweep); identity drift gains a conserved comparator c_m(R - V);
R is INHERITED WHOLE at fission even though the body is halved. Rung S:
staged growth from a seed, R written once per newborn ring. Rung Y:
coarse organizer blend + fine self-EMA. Rung TM: T + the frozen Wave-10
Kawasaki motility reading sign(R). Identity layer = the bare conserved
sheet (`ladder_web.engine.ladder_step` rung "A", verbatim); the c_m = 0
lesion consumes nothing and is stream-exact."""

from __future__ import annotations

import numpy as np

from growing_web.config import GrowConfig
from growing_web.engine import motility_phase
from ladder_web.config import LadderConfig
from ladder_web.engine import ladder_step
from voltage_web.engine import fission as sheet_fission

from .config import BlueprintConfig


def blueprint_step(V, ema, Rf, theta, tissue, ladder: LadderConfig,
                   bp: BlueprintConfig, rung: str, rng, mrng=None,
                   clamp=None, c_m=None, alive=None):
    """One sweep. Rf is the reference field (B,H,W) or None (rung A).
    `alive` (H,W bool) restricts dynamics for rung S growth phases."""
    c_m = bp.c_m if c_m is None else c_m
    V, ema, _ = ladder_step(V, ema, theta, tissue, ladder, "A", rng, None, clamp)
    if rung != "A" and Rf is not None and c_m > 0:
        drift = c_m * (Rf - V)
        if alive is not None:
            drift = np.where(alive[None], drift, 0.0)
        drift = drift - drift.mean(axis=(-2, -1), keepdims=True)
        V = np.clip(V + tissue.dt * drift, -2.0, 2.0)
    if rung == "TM" and mrng is not None and Rf is not None:
        grow = GrowConfig()
        for _ in range(grow.phases_per_sweep):
            V = motility_phase(V, np.sign(Rf.mean(axis=0)) if Rf.ndim == 3 else np.sign(Rf),
                               grow, "H", mrng)
    if rung in ("T", "Y", "TM") and Rf is not None:
        Rf = Rf + bp.rho * (V - Rf)
    if alive is not None:
        V = np.where(alive[None], V, tissue.resting)
    return V, ema, Rf


def blueprint_fission(V, Rf, tissue, rng):
    """Body halved; blueprint inherited WHOLE."""
    kids = sheet_fission(V, tissue, rng)
    return kids, (Rf.copy() if Rf is not None else None)


def settle_with_blueprint(tissue, bp: BlueprintConfig, rung: str, rng,
                          mrng, futures: int, sweeps: int = 60,
                          seed_index: int = 0, c_m=None):
    from voltage_web.engine import launch_pattern, make_thresholds

    ladder = LadderConfig()
    theta = make_thresholds(tissue)
    V = np.tile(launch_pattern(seed_index, tissue), (futures, 1, 1))
    V = V + tissue.copy_jitter * rng.standard_normal(V.shape)
    ema = V.copy()
    Rf = V.copy() if rung != "A" else None
    if rung == "Y":
        from ladder_web.engine import tissue_fields

        fields = tissue_fields(tissue, ladder, "C")
        E = fields[3]
        Rf = bp.coarse_weight * E[None] + (1 - bp.coarse_weight) * Rf
    for _ in range(sweeps):
        V, ema, Rf = blueprint_step(V, ema, Rf, theta, tissue, ladder, bp,
                                    rung, rng, mrng, c_m=c_m)
    return V, ema, Rf, theta, ladder
