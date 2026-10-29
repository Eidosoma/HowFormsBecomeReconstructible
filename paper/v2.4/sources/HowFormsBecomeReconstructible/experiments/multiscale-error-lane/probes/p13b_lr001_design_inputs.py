"""Engineering probe P13b (python probes/p13b_lr001_design_inputs.py CPUS): the open questions in PLAN_LR001.md
before LR001's freeze. ENGINEERING_PROBE_NOT_EVIDENCE.

P13's tissue, tag, blocks and cached acquisitions (engineering blocks 900868-900871, tag mse-p13, 32 cases, side 16,
the record alone unless stated), with P13's helpers imported unchanged. Panels:
  D  a two-level decoder: after local parity, the frustrated plaquettes left in each 4 x 4 region of plaquettes are
     paired greedily (nearest first) and the bonds along an L-shaped dual path between each pair are flipped. Does it
     raise the threshold over Hebbian relearning + parity at bond flip rates 1e-3 to 5e-3?
  K  trust flags: bonds re-formed by default (+1 between dead cells) are kept out of the gauge frame (the consensus still
     uses them). Plain, hybrid and hybrid + trust codes on killed patches, relinked or not.
  T  turnover with the hybrid + trust code: a newborn cell's bonds are inherited (BR002's assumption), relearned from
     the record by Hebbian learning (strengths reset to 0, trusted again when |b| >= 0.5), or set to +1 by default
     (untrusted); a newborn's record starts at 0. Rates 0.001 and 0.003 per cell per update.
  L  learning in life: the relational record with bonds that keep learning from the record's or the body's
     co-activity while BR001's held 6 x 6 body scar lasts 2,000 updates (then released); br001.sim.body_step,
     conserved body, sigma 0.1, gain 0.2.
v2 (26 Oct, before LR001's freeze): adds panel D's arms both+hyb and both+dec+hyb (the hybrid code as a third,
regional layer of repair); written to p13b_lr001_design_inputs_v2.json, every other row identical to v1.
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

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

import p13_lr001_design_inputs as P  # noqa: E402
from br001.sim import body_step  # noqa: E402
from mse.native import NATIVE, address  # noqa: E402
from msegrid.core import Stream, acquire, bonds, bproj, kill_bonds, record_step  # noqa: E402

TAG, SIDE, BLOCKS = P.TAG, P.SIDE, P.BLOCKS
OUT = HERE / "results" / "p13b_lr001_design_inputs_v2.json"
ETA = 0.01


def decode(H, W, region=4):
    """Pair the frustrated plaquettes inside each region x region block of plaquettes (greedy, nearest first,
    Manhattan) and flip the bonds along an L-shaped dual path: along the first plaquette's row, then the column."""
    F = P.flux(H, W)
    idx = np.argwhere(F < 0)
    if len(idx) < 2:
        return H, W, 0
    key = idx[:, 0] * 10000 + (idx[:, 1] // region) * 100 + idx[:, 2] // region
    order = np.argsort(key, kind="stable")
    idx, key = idx[order], key[order]
    cut = np.flatnonzero(np.diff(key)) + 1
    H, W, n = H.copy(), W.copy(), 0
    for grp in np.split(idx, cut):
        if len(grp) < 2:
            continue
        c = int(grp[0, 0])
        pts = [(int(i), int(j)) for i, j in grp[:, 1:]]
        while len(pts) >= 2:
            best = None
            for a in range(len(pts)):
                for b in range(a + 1, len(pts)):
                    d = abs(pts[a][0] - pts[b][0]) + abs(pts[a][1] - pts[b][1])
                    if best is None or d < best[0]:
                        best = (d, a, b)
            _, a, b = best
            (i1, j1), (i2, j2) = pts[a], pts[b]
            step = 1 if j2 > j1 else -1
            for j in range(j1, j2, step):
                W[c, i1, j + 1 if step == 1 else j] *= -1     # the edge between plaquettes (i1, j) and (i1, j + step)
            step = 1 if i2 > i1 else -1
            for i in range(i1, i2, step):
                H[c, i + 1 if step == 1 else i, j2] *= -1     # the edge between plaquettes (i, j2) and (i + step, j2)
            pts = [q for k, q in enumerate(pts) if k not in (a, b)]
            n += 1
    return H, W, n


def turnover_events(cs, rate, updates):
    out = []
    for c in cs:
        g = address(TAG, *c.key(), "p13b-turnover", f"{rate:g}")
        n = int(g.poisson(rate * updates * SIDE * SIDE))
        t = g.integers(1, updates + 1, n)
        site = g.integers(0, SIDE * SIDE, n)
        o = np.argsort(t, kind="stable")
        out.append((t[o], site[o]))
    return out


def site_edges(i, j):
    """The four edges of cell (i, j): H[i, j], H[i, j-1], W[i, j], W[i-1, j]."""
    return [("H", i, j), ("H", i, (j - 1) % SIDE), ("W", i, j), ("W", (i - 1) % SIDE, j)]


def run(R0, T, updates, stream, code="none", trust=False, hebb=0.0, parity=False, decoder=False, p_b=0.0,
        wound=None, mask=None, turnover=None, snaps=(1000, 4000)):
    cs = P.cases()
    k = len(cs)
    st = Stream(TAG, cs, "p13", stream, side=SIDE)
    flip_st = Stream(TAG, cs, "p13-bondnoise", stream, side=SIDE) if p_b else None
    H, W = P.edges_from(bonds(R0, True))
    H0, W0 = H.copy(), W.copy()
    Hb, Wb = H * 0.8, W * 0.8
    tH, tW = np.ones(H.shape, bool), np.ones(W.shape, bool)
    B = bproj(R0, 4)
    Bg = bproj(P.gauge_frame(H0, W0) * R0, 4)
    r = R0.copy()
    if wound == "flip":
        r = np.where(mask, -r, r)
    elif wound in ("kill", "relink"):
        r = np.where(mask, 0.0, r)
        Jk = kill_bonds(P.halves(H, W), mask, wound == "relink")
        H, W = P.edges_from(Jk)
        tH, tW = ~(mask & np.roll(mask, -1, -1)), ~(mask & np.roll(mask, -1, -2))   # bonds between two dead cells
        Hb, Wb = H * 0.8, W * 0.8
    events = turnover_events(cs, turnover[0], updates) if turnover else None
    mn, mj = P.minority(T)
    cut = np.sqrt(2) * P.erfinv_1m(2 * p_b) if p_b else None
    out, ndec, buf, fbuf = {}, 0, None, None
    for t in range(1, updates + 1):
        i = (t - 1) % 100
        if i == 0:
            buf = st.take(100)
            if p_b:
                fbuf = flip_st.take(100)
        if p_b:
            hit_h, hit_w = fbuf[i] > cut, fbuf[i] < -cut
            H, W = np.where(hit_h, -H, H), np.where(hit_w, -W, W)
            Hb, Wb = np.where(hit_h, -Hb, Hb), np.where(hit_w, -Wb, Wb)
        r = record_step(r, buf[i], P.EPS, P.KR, P.SIGMA_R, 0.0, None, P.halves(H, W))
        if code != "none":
            if code == "plain":
                r = r + P.KC * (B - bproj(r, 4))
            else:
                sg = P.gauge_frame(np.where(tH, H, 0.0), np.where(tW, W, 0.0)) if trust else P.gauge_frame(H, W)
                live = sg != 0
                mean_u = bproj(sg * r, 4) * 16 / np.maximum(bproj(live * 1.0, 4) * 16, 1)
                inc = P.KC * sg * (Bg - mean_u)
                if code == "hybrid":
                    inc = np.where(live, inc, P.KC * (B - bproj(r, 4)))
                r = r + inc
            r = np.clip(r, -2.0, 2.0)
        if hebb:
            Hb = Hb + hebb * (np.clip(r * np.roll(r, -1, -1) / P.R2, -1, 1) - Hb)
            Wb = Wb + hebb * (np.clip(r * np.roll(r, -1, -2) / P.R2, -1, 1) - Wb)
            if turnover and turnover[1] == "relearn":                     # a relation counts once |b| >= 0.1
                H, W = np.where(np.abs(Hb) >= 0.1, np.sign(Hb), 0.0), np.where(np.abs(Wb) >= 0.1, np.sign(Wb), 0.0)
                tH, tW = np.abs(Hb) >= 0.5, np.abs(Wb) >= 0.5
            else:
                H, W = np.where(Hb != 0, np.sign(Hb), H), np.where(Wb != 0, np.sign(Wb), W)
        if parity:
            H, W, _ = P.parity_repair(H, W)
        if decoder:
            H, W, n = decode(H, W)
            ndec += n
        if parity or decoder:
            Hb, Wb = np.where(np.sign(Hb) * H < 0, -Hb, Hb), np.where(np.sign(Wb) * W < 0, -Wb, Wb)
        if events is not None:
            for j in range(k):
                tt, site = events[j]
                lo, hi = np.searchsorted(tt, t, "left"), np.searchsorted(tt, t, "right")
                for s in site[lo:hi]:
                    a, b = divmod(int(s), SIDE)
                    r[j, a, b] = 0.0
                    if turnover[1] == "inherit":
                        continue
                    for kind, x, y in site_edges(a, b):
                        arr, strength, tr = (H, Hb, tH) if kind == "H" else (W, Wb, tW)
                        if turnover[1] == "relearn":
                            arr[j, x, y], strength[j, x, y], tr[j, x, y] = 0.0, 0.0, False
                        else:                                       # default: re-formed as +1, untrusted
                            arr[j, x, y], strength[j, x, y], tr[j, x, y] = 1.0, 0.8, False
        if t in snaps:
            ok = (r > 0) == (T > 0)
            berr = ((H != H0).mean((-2, -1)) + (W != W0).mean((-2, -1))) / 2
            res = {"sign": P.summarise(ok.mean((-2, -1))), "bond_err": P.summarise(berr),
                   "minority": P.summarise(P.frac(mn, ok)), "majority": P.summarise(P.frac(mj, ok))}
            if mask is not None:
                res["kept"] = P.summarise(P.frac(mask, ok))
                res["kept_min"] = P.summarise(P.frac(mask & mn, ok))
                res["kept_maj"] = P.summarise(P.frac(mask & mj, ok))
            out[t] = res
    out["decoder_pairs_per_update"] = round(ndec / updates / k, 4)
    return out


def panel_L(family, learn):
    """Bonds keep learning in life (from the record or the body) while a held 6 x 6 body scar lasts 2,000 updates."""
    cs = P.cases()
    T = P.TPL[family][[c.message for c in cs]]
    V, ema, R0, th = acquire(TAG, cs, T, replace(NATIVE, sigma=P.SIGMA_ACQ), SIDE, settle=P.SETTLE, teach=P.TEACH,
                             release=P.RELEASE)
    p = replace(NATIVE, sigma=0.1)
    H, W = P.edges_from(bonds(R0, True))
    H0, W0 = H.copy(), W.copy()
    Hb, Wb = H * 0.8, W * 0.8
    mask = P.patch(cs, 6, "L")
    zs, xs = Stream(TAG, cs, "p13b-L", "body", side=SIDE), Stream(TAG, cs, "p13b-L", "record", side=SIDE)
    v, e, r = V.copy(), ema.copy(), R0.copy()
    eta = {"none": 0.0, "record": ETA, "body": ETA, "body_slow": 0.001}[learn]
    out, zb, xb = {}, None, None
    for t in range(1, 4001):
        i = (t - 1) % 100
        if i == 0:
            zb, xb = zs.take(100), xs.take(100)
        if t <= 2000:
            v = np.where(mask, -T, v)
        v, e, _ = body_step(v, e, r, th, zb[i], p, True, NATIVE.gain)
        r = record_step(r, xb[i], P.EPS, P.KR, P.SIGMA_R, 0.0, None, P.halves(H, W))
        if eta:
            x = r / 1.2 if learn == "record" else v
            Hb = Hb + eta * (np.clip(x * np.roll(x, -1, -1), -1, 1) - Hb)
            Wb = Wb + eta * (np.clip(x * np.roll(x, -1, -2), -1, 1) - Wb)
            H, W = np.where(Hb != 0, np.sign(Hb), H), np.where(Wb != 0, np.sign(Wb), W)
        if t in (2000, 4000):
            okr, okv = (r > 0) == (T > 0), (v > 0) == (T > 0)
            berr = ((H != H0).mean((-2, -1)) + (W != W0).mean((-2, -1))) / 2
            out[t] = {"record_kept": P.summarise(P.frac(mask, okr)), "body_kept": P.summarise(P.frac(mask, okv)),
                      "record_sign": P.summarise(okr.mean((-2, -1))), "bond_err": P.summarise(berr)}
    return out


def task(args):
    panel, family, a, b, c, cpu = args
    os.sched_setaffinity(0, [cpu])
    t0 = time.time()
    if panel == "L":
        res = panel_L(family, a)
    else:
        R0, T = P.acquisition(family)
        if panel == "D":
            p_b, repair = a, b
            res = run(R0, T, 8000, "D", code="hybrid" if repair.endswith("+hyb") else "none",
                      hebb=ETA if repair.startswith("both") else 0.0, parity=True, decoder="+dec" in repair, p_b=p_b,
                      snaps=(2000, 4000, 8000))
        elif panel == "K":
            code, wound, size = a, b, c
            m = P.patch(P.cases(), size, "G")
            res = run(R0, T, 4000, "G", code=code.replace("+trust", ""), trust=code.endswith("+trust"), wound=wound, mask=m)
        else:                                            # T: rate a, mode b, code c
            res = run(R0, T, 8000, "T", code=c.replace("+trust", ""), trust=c.endswith("+trust"),
                      hebb=ETA if b == "relearn" else 0.0, turnover=(a, b) if a else None, snaps=(2000, 8000))
    res = {str(k): v for k, v in res.items()}
    return {"panel": panel, "family": family, "a": a, "b": b, "c": c, "res": res, "wall_s": round(time.time() - t0, 1)}


def main():
    cpus = [int(x) for x in sys.argv[1].split(",")]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=min(len(cpus), len(P.FAMILIES))) as ex:
        list(ex.map(P.acquisition, P.FAMILIES))
    jobs = []
    for fam in ("F0", "BL", "IS"):
        for p_b in (0.001, 0.002, 0.003, 0.005):
            for rep in ("both", "both+dec", "parity+dec", "both+hyb", "both+dec+hyb"):
                jobs.append(("D", fam, p_b, rep, ""))
    for fam in P.FAMILIES:
        for code in ("plain", "hybrid", "hybrid+trust"):
            for wound in ("kill", "relink"):
                for size in (4, 8):
                    jobs.append(("K", fam, code, wound, size))
    for fam in ("BL", "IS"):
        jobs.append(("T", fam, 0.0, "inherit", "hybrid+trust"))
        for rate in (0.001, 0.003):
            for mode in ("inherit", "relearn", "default"):
                for code in ("plain", "hybrid+trust"):
                    jobs.append(("T", fam, rate, mode, code))
    for fam in ("F0", "IS"):
        for learn in ("none", "record", "body", "body_slow"):
            jobs.append(("L", fam, learn, "", ""))
    jobs.sort(key=lambda j: {"D": 0, "T": 1, "L": 2, "K": 3}[j[0]])
    with ProcessPoolExecutor(max_workers=len(cpus)) as ex:
        rows = list(ex.map(task, [(*j, cpus[i % len(cpus)]) for i, j in enumerate(jobs)]))
    out = {"probe": "P13b", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "tag": TAG, "blocks": list(BLOCKS), "side": SIDE,
           "rows": rows, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
           "cpu_s": round(sum(r["wall_s"] for r in rows), 1)}
    OUT.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    print("wrote", OUT, OUT.stat().st_size, "bytes;", len(rows), "tasks;", out["wall_s"], "s wall")


if __name__ == "__main__":
    main()
