"""Engineering probe P16b (python probes/p16b_dl003_front_speed.py CPUS): P16's panel B with further fronts, for DL003.
ENGINEERING_PROBE_NOT_EVIDENCE.

P16's tissue, cases and draws (tag mse-p16, blocks 900720-900723), building the stripes from newborn noise, with arms:
  scatter, perp/f100       P16's, repeated as paired references;
  perp/f200                a slower front across the stripes (reaches the far side at t = 3,000);
  par/f50                  a front along the stripes between P16's two speeds;
  none/perp-f100           a front spreading from the perp boundary's position without anchors (layout without
                           registration).
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p16_dl003_design_inputs as P  # noqa: E402

import numpy as np  # noqa: E402

from dl001 import design as DL  # noqa: E402
from dl001 import sim as S  # noqa: E402
from mse.native import NATIVE  # noqa: E402
from msegrid.core import Stream, birth  # noqa: E402

ARMS = [("scatter", "scatter", 0, ""), ("perp/f100", "perp", 100, ""), ("perp/f200", "perp", 200, ""),
        ("par/f50", "par", 50, ""), ("none/perp-f100", "none", 100, "perp")]
OUT = P.LANE / "probes" / "results" / "p16b_dl003_front_speed.json"


def run(body, theta, cpu):
    os.sched_setaffinity(0, [cpu])
    t0 = time.time()
    V0, ema0, R0, th, T = P.acquisition()
    cs = P.cases()
    k, n = len(cs), P.SIDE
    masks, dist = P.geometry(cs)
    alpha, L = DL.BODIES[body]
    G = S.ghat(n, L) if alpha else None
    p = replace(NATIVE, sigma=0.1)
    nb = len(ARMS)
    idx = np.tile(np.arange(k), nb)
    newb = birth(P.TAG, cs, "newborn-sheet", side=n)
    newbb = np.tile(newb, (nb, 1, 1))
    V, E = newbb.copy(), newbb.copy()
    r = np.tile(R0, (nb, 1, 1))
    gain = np.zeros((nb * k, n, n))
    fdist = np.full((nb * k, n, n), -1)
    every = np.zeros(nb * k)
    for i, (name, geo, front, origin) in enumerate(ARMS):
        sl = slice(i * k, (i + 1) * k)
        if geo in masks:
            gain[sl] = P.G_ANCHOR * masks[geo]
        if front:
            fdist[sl] = dist[origin or geo]
            every[sl] = front
    frontal = fdist >= 0
    live = ~frontal | (fdist == 0)
    V, E = np.where(live, V, 0.0), np.where(live, E, 0.0)
    Tb, thb = np.tile(T, (nb, 1, 1)), (th * theta)[idx]
    st = Stream(P.TAG, cs, "future", "B", side=n)
    out, buf = {a[0]: {} for a in ARMS}, None
    for t in range(1, P.WINDOW + 1):
        i = (t - 1) % P.CHUNK
        if i == 0:
            buf = st.take(P.CHUNK)
        V, E, Vt, drift, d = S.body(V, E, r, thb, buf[i][idx], p, gain, alpha, G)
        now = ~frontal | (fdist * every[:, None, None] <= t)
        born = now & ~live
        V = np.where(born, newbb, np.where(now, V, 0.0))
        E = np.where(born, newbb, np.where(now, E, 0.0))
        live = now
        if t in P.SNAPS:
            sg = S.sign(V, Tb).reshape(nb, k)
            for a, arm in enumerate(ARMS):
                out[arm[0]][f"sign@{t}"] = round(float(sg[a].mean()), 4)
    ok = (V > 0) == (Tb > 0)
    sg = S.sign(V, Tb).reshape(nb, k)
    sh = S.best_shift(V, Tb).reshape(nb, k)
    sp = S.spacing(V).reshape(nb, k)
    prof = {g: P.profile(ok, np.tile(dist[g], (nb, 1, 1)), 15).reshape(nb, k, -1) for g in ("par", "perp")}
    for a, arm in enumerate(ARMS):
        e = out[arm[0]]
        e["sign_blocks@4000"] = [round(float(x), 4) for x in sg[a].reshape(len(P.BLOCKS), -1).mean(1)]
        e["shift@4000"] = round(float(sh[a].mean()), 4)
        e["spacing@4000"] = round(float(sp[a].mean()), 3)
        e["prof"] = [round(float(x), 3) for x in prof["par" if arm[1] == "par" else "perp"][a].mean(0)]
    return {"panel": "B", "body": body, "theta": theta, "res": out, "wall_s": round(time.time() - t0, 1)}


def task(a):
    return run(*a)


def main():
    cpus = [int(c) for c in sys.argv[1].split(",")]
    t0 = time.time()
    jobs = [(b, th) for b in ("li4", "dw") for th in P.THETAS]
    with ProcessPoolExecutor(max_workers=len(cpus)) as ex:
        rows = list(ex.map(task, [(*j, cpus[i % len(cpus)]) for i, j in enumerate(jobs)]))
    out = {"probe": "P16b", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "tag": P.TAG, "blocks": list(P.BLOCKS),
           "arms": [a[0] for a in ARMS], "rows": rows, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "wall_s": round(time.time() - t0, 1), "cpu_s": round(sum(r["wall_s"] for r in rows), 1)}
    OUT.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    print("wrote", OUT, OUT.stat().st_size, "bytes;", len(rows), "tasks;", out["wall_s"], "s wall")


if __name__ == "__main__":
    main()
