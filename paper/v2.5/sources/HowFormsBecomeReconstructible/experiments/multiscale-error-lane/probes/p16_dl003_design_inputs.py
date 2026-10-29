"""Engineering probe P16 (python probes/p16_dl003_design_inputs.py CPUS): design inputs for DL003, whether a boundary
registers a self-organised pattern. ENGINEERING_PROBE_NOT_EVIDENCE.

DL001's bodies (dw, li4; dl001.sim.body, read-only) on a 32-site sheet, open body, sigma 0.1, the environmental field
theta at x0, x0.25, x0.5 and x1. Stripes of period 8 (S4; kinds 0 and 2 change sign across columns, 1 and 3 across
rows). Positional information at 64 cells (1/16 of the sheet), each holding the acquired record at gain 1.0:
  scatter  64 random cells;
  par      a boundary along the stripes: two adjacent lines straddling a wall of the template (a random wall);
  perp     a boundary across the stripes: two adjacent lines at a random offset;
  cluster  one 8 x 8 block at a random position;
and the references none and full (the held record at every cell, gain 0.2, DL001's).
Panels: H, holding the acquired pattern for 4,000 updates; B, building it from newborn noise for 4,000 updates with
the whole sheet active from the start, or with activation spreading from a boundary at one line per 25 or 100
updates ("f25", "f100"; cells ahead of the front are held at 0 and start from their newborn values when reached).
"none/par-f100" spreads from the par boundary's position without anchors.
Endpoints: sign over the sheet; the best cyclic-shift agreement (layout whatever the registration); spacing; sign by
distance from the par and perp boundaries (0 = on the boundary, 15 = farthest) and from the cluster (Chebyshev).
Cases: engineering blocks 900720-900723 (32 cases), tag mse-p16.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

from concurrent.futures import ProcessPoolExecutor  # noqa: E402
from dataclasses import replace  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from dl001 import design as DL  # noqa: E402
from dl001 import sim as S  # noqa: E402
from mse.assay import enrol  # noqa: E402
from mse.native import NATIVE, address  # noqa: E402
from msegrid.core import Stream, acquire, birth  # noqa: E402

TAG = "mse-p16"
SIDE = 32
BLOCKS = tuple(range(900720, 900724))
THETAS = (0.0, 0.25, 0.5, 1.0)
N_ANCHOR, G_ANCHOR, G_FULL = 64, 1.0, 0.2
ARMS = {"H": ["none", "scatter", "par", "perp", "cluster", "full"],
        "B": ["none", "scatter", "par", "perp", "cluster", "full", "par/f25", "par/f100", "perp/f25", "perp/f100",
              "none/par-f100"]}
WINDOW, SNAPS, CHUNK = 4000, (1000, 2000, 4000), 250
OUT = LANE / "probes" / "results" / "p16_dl003_design_inputs.json"
ROOT = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/probes/p16")


def cases():
    return enrol(list(BLOCKS), DL.MESSAGES, DL.PARENTS, "engineering")


def acquisition():
    path = ROOT / "acq_S4.npz"
    if path.exists():
        z = np.load(path)
        return z["V"], z["ema"], z["R"], z["th"], z["T"]
    cs = cases()
    T = np.stack([DL.AMPLITUDE * S.template("S4", c.message, SIDE, c.block) for c in cs])
    V, ema, R, th = acquire(TAG, cs, T, replace(NATIVE, sigma=DL.SIGMA_ACQ), SIDE, settle=DL.SETTLE, teach=DL.TEACH,
                            release=DL.RELEASE)
    ROOT.mkdir(parents=True, exist_ok=True)
    tmp = ROOT / f".acq_S4.{os.getpid()}.npz"
    np.savez(tmp, V=V, ema=ema, R=R, th=th, T=T)
    os.replace(tmp, path)
    return V, ema, R, th, T


def ring_dist(lines):
    """Distance of every index on the periodic ring from the nearest of the given lines."""
    ar = np.arange(SIDE)
    return (np.abs((ar[:, None] - np.asarray(lines)[None, :] + SIDE // 2) % SIDE - SIDE // 2)).min(1)


def geometry(cs):
    """Anchor masks per geometry, and distance maps from the par and perp boundaries and from the cluster."""
    k = len(cs)
    masks = {g: np.zeros((k, SIDE, SIDE), bool) for g in ("scatter", "par", "perp", "cluster")}
    dist = {g: np.zeros((k, SIDE, SIDE), int) for g in ("par", "perp", "cluster")}
    for j, c in enumerate(cs):
        g = address(TAG, *c.key(), "geometry")
        masks["scatter"][j].flat[g.permutation(SIDE * SIDE)[:N_ANCHOR]] = True
        w = int(g.integers(0, SIDE // 4))                       # the template's walls lie between 4w - 1 and 4w
        wall = [(4 * w - 1) % SIDE, (4 * w) % SIDE]
        o = int(g.integers(0, SIDE))
        across = [o, (o + 1) % SIDE]
        dw, da = ring_dist(wall), ring_dist(across)
        if c.message % 2 == 0:                                  # the sign changes across columns
            masks["par"][j][:, wall] = True
            dist["par"][j] = np.broadcast_to(dw[None, :], (SIDE, SIDE))
            masks["perp"][j][across, :] = True
            dist["perp"][j] = np.broadcast_to(da[:, None], (SIDE, SIDE))
        else:                                                   # the sign changes across rows
            masks["par"][j][wall, :] = True
            dist["par"][j] = np.broadcast_to(dw[:, None], (SIDE, SIDE))
            masks["perp"][j][:, across] = True
            dist["perp"][j] = np.broadcast_to(da[None, :], (SIDE, SIDE))
        a, b = (int(x) for x in g.integers(0, SIDE, 2))
        ri, ci = np.arange(a, a + 8) % SIDE, np.arange(b, b + 8) % SIDE
        masks["cluster"][j][np.ix_(ri, ci)] = True
        dist["cluster"][j] = np.maximum(ring_dist(ri)[:, None], ring_dist(ci)[None, :])
    return masks, dist


def profile(ok, dmap, dmax):
    """Mean agreement at each distance 0..dmax, per branch."""
    return np.stack([(ok & (dmap == d)).sum((-2, -1)) / np.maximum((dmap == d).sum((-2, -1)), 1)
                     for d in range(dmax + 1)], -1)


def run(panel, body, theta, cpu):
    os.sched_setaffinity(0, [cpu])
    t0 = time.time()
    V0, ema0, R0, th, T = acquisition()
    cs = cases()
    k = len(cs)
    masks, dist = geometry(cs)
    alpha, L = DL.BODIES[body]
    G = S.ghat(SIDE, L) if alpha else None
    p = replace(NATIVE, sigma=0.1)
    arms = ARMS[panel]
    nb = len(arms)
    idx = np.tile(np.arange(k), nb)
    newb = birth(TAG, cs, "newborn-sheet", side=SIDE)
    if panel == "H":
        V, E = np.tile(V0, (nb, 1, 1)), np.tile(ema0, (nb, 1, 1))
    else:
        V, E = np.tile(newb, (nb, 1, 1)), np.tile(newb, (nb, 1, 1))
    r = np.tile(R0, (nb, 1, 1))
    gain = np.zeros((nb * k, SIDE, SIDE))
    fdist = np.full((nb * k, SIDE, SIDE), -1)
    speed = np.zeros(nb * k)
    for i, arm in enumerate(arms):
        sl = slice(i * k, (i + 1) * k)
        geo, _, front = arm.partition("/")
        if geo == "full":
            gain[sl] = G_FULL
        elif geo in masks:
            gain[sl] = G_ANCHOR * masks[geo]
        if front:
            line, spd = (front[:-5], front[-4:]) if front.startswith("par-") else (geo, front)
            fdist[sl] = dist[line.rstrip("-")]
            speed[sl] = 1.0 / float(spd[1:])
    frontal = fdist >= 0
    newbb = np.tile(newb, (nb, 1, 1))
    active = ~frontal | (fdist == 0)
    V, E = np.where(active, V, 0.0), np.where(active, E, 0.0)
    Tb, thb = np.tile(T, (nb, 1, 1)), (th * theta)[idx]
    dmaps = {g: np.tile(dist[g], (nb, 1, 1)) for g in dist}
    st = Stream(TAG, cs, "future", panel, side=SIDE)
    out, buf = {arm: {} for arm in arms}, None
    wc, nwork = np.zeros(nb * k), 0
    for t in range(1, WINDOW + 1):
        i = (t - 1) % CHUNK
        if i == 0:
            buf = st.take(CHUNK)
        V, E, Vt, drift, d = S.body(V, E, r, thb, buf[i][idx], p, gain, alpha, G)
        if frontal.any():
            now = ~frontal | (fdist <= speed[:, None, None] * t)
            born = now & ~active
            V = np.where(born, newbb, np.where(now, V, 0.0))
            E = np.where(born, newbb, np.where(now, E, 0.0))
            active = now
        if t > WINDOW // 2:
            wc += np.abs(p.dt * d).mean((-2, -1))
            nwork += 1
        if t in SNAPS:
            sg = S.sign(V, Tb).reshape(nb, k)
            for a, arm in enumerate(arms):
                out[arm][f"sign@{t}"] = round(float(sg[a].mean()), 4)
            if t == WINDOW:
                ok = (V > 0) == (Tb > 0)
                sh = S.best_shift(V, Tb).reshape(nb, k)
                sp = S.spacing(V).reshape(nb, k)
                prof = {g: profile(ok, dmaps[g], 12 if g == "cluster" else 15).reshape(nb, k, -1) for g in dmaps}
                wk = (wc / nwork).reshape(nb, k)
                for a, arm in enumerate(arms):
                    e = out[arm]
                    e["sign_blocks@4000"] = [round(float(x), 4) for x in sg[a].reshape(len(BLOCKS), -1).mean(1)]
                    e["shift@4000"] = round(float(sh[a].mean()), 4)
                    e["spacing@4000"] = round(float(sp[a].mean()), 3)
                    e["w_corr"] = round(float(wk[a].mean()), 6)
                    for g in prof:
                        e[f"prof_{g}"] = [round(float(x), 3) for x in prof[g][a].mean(0)]
    return {"panel": panel, "body": body, "theta": theta, "res": out, "wall_s": round(time.time() - t0, 1)}


def task(a):
    return run(*a)


def main():
    cpus = [int(c) for c in sys.argv[1].split(",")]
    t0 = time.time()
    acquisition()
    jobs = [("B", b, th) for b in ("li4", "dw") for th in THETAS] + [("H", b, th) for b in ("li4", "dw") for th in THETAS]
    with ProcessPoolExecutor(max_workers=len(cpus)) as ex:
        rows = list(ex.map(task, [(*j, cpus[i % len(cpus)]) for i, j in enumerate(jobs)]))
    out = {"probe": "P16", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "tag": TAG, "blocks": list(BLOCKS), "side": SIDE,
           "arms": ARMS, "rows": rows, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "wall_s": round(time.time() - t0, 1), "cpu_s": round(sum(r["wall_s"] for r in rows), 1)}
    OUT.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    print("wrote", OUT, OUT.stat().st_size, "bytes;", len(rows), "tasks;", out["wall_s"], "s wall")


if __name__ == "__main__":
    main()
