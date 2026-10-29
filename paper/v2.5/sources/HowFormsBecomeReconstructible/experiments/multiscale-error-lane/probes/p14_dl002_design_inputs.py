"""Engineering probe P14 (python probes/p14_dl002_design_inputs.py CPUS): design inputs for DL002, how little record a
self-organising body needs. ENGINEERING_PROBE_NOT_EVIDENCE.

DL001's bodies (dw, li2, li4; dl001.sim.body, read-only) on a 32-site sheet, open body, sigma 0.1, theta kept (x1) or
removed (x0). Records the body reads through the pull g (r - V~):
  none;
  full    the acquired record held unchanged at every site, gain 0.2 (DL001's held record);
  aF/gG   sparse anchors: the held record at a random fraction F of the sites (drawn per case), gain G there and 0
          elsewhere; F in 1/64, 1/16, 1/4 and G in 0.2, 1.0;
  rel     a tissue-held relational record (BR002's bonds with the coarse code, msegrid.record_step), read at gain 0.2.
Patterns: S4 (stripes of period 8, native to li2 and li4), LB (li4's own labyrinth: grown from newborn noise for
2,000 updates in a clean sheet without a record, then its sign; two per block, kinds 2 and 3 their reversals) and
F0 (two domains, native to dw).
Panels: A, no wound, t = 2,000 and 4,000; R, an 8 x 8 wound at t = 1 (flipped or reset; for rel the record is wounded
with the body, for anchors the anchors inside the wound are lost), agreement inside the wound at t = 500, 2,000, 4,000.
Cases: engineering blocks 900892-900895 (32 cases), tag mse-p14.
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
from mse.assay import BIRTH_SCALE, enrol  # noqa: E402
from mse.native import NATIVE, address, center  # noqa: E402
from msegrid.core import Stream, acquire, base, bonds, bproj, record_step  # noqa: E402

TAG = "mse-p14"
SIDE = 32
BLOCKS = tuple(range(900892, 900896))
EPS, KR, SIGMA_R, KC = 0.05, 1.0, 0.02, 0.02
RECORDS = ["none", "full"] + [f"a{f}/g{g:g}" for f in (64, 16, 4) for g in (0.2, 1.0)] + ["rel"]
OUT = LANE / "probes" / "results" / "p14_dl002_design_inputs.json"
ROOT = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/probes/p14")


def cases():
    return enrol(list(BLOCKS), DL.MESSAGES, DL.PARENTS, "engineering")


def labyrinth(block, j):
    """li4 grown from newborn noise without a record in a clean sheet for 2,000 updates; its sign."""
    alpha, L = DL.BODIES["li4"]
    G = S.ghat(SIDE, L)
    V = BIRTH_SCALE * center(address(TAG, "family", "LB", block, j).standard_normal((SIDE, SIDE)))[None]
    g = address(TAG, "family", "LB-noise", block, j)
    p = replace(NATIVE, sigma=0.1)
    zero = np.zeros_like(V)
    for _ in range(2000):
        V, _, _, _, _ = S.body(V, V, zero, zero, g.standard_normal((1, SIDE, SIDE)), p, 0.0, alpha, G)
    return np.where(V[0] >= 0, 1.0, -1.0)


def template(family, kind, block):
    if family == "S4":
        return S.template("S4", kind, SIDE, block)
    if family == "LB":
        f = labyrinth(block, kind % 2)
        return f if kind < 2 else -f
    return base(family, kind, SIDE, TAG, block)


def acquisition(pattern):
    path = ROOT / f"acq_{pattern}.npz"
    if path.exists():
        z = np.load(path)
        return z["V"], z["ema"], z["R"], z["th"], z["T"]
    cs = cases()
    T = np.stack([DL.AMPLITUDE * template(pattern, c.message, c.block) for c in cs])
    V, ema, R, th = acquire(TAG, cs, T, replace(NATIVE, sigma=DL.SIGMA_ACQ), SIDE, settle=DL.SETTLE, teach=DL.TEACH,
                            release=DL.RELEASE)
    ROOT.mkdir(parents=True, exist_ok=True)
    tmp = ROOT / f".acq_{pattern}.{os.getpid()}.npz"
    np.savez(tmp, V=V, ema=ema, R=R, th=th, T=T)
    os.replace(tmp, path)
    return V, ema, R, th, T


def anchors(cs, f):
    return np.stack([address(TAG, *c.key(), "anchors", f).random((SIDE, SIDE)) < 1.0 / f for c in cs])


def wound_mask(cs):
    m = np.zeros((len(cs), SIDE, SIDE), bool)
    for j, c in enumerate(cs):
        a, b = address(TAG, *c.key(), "wound").integers(0, SIDE, 2)
        m[j][np.ix_(np.arange(a, a + 8) % SIDE, np.arange(b, b + 8) % SIDE)] = True
    return m


def run(body, pattern, theta, wound, cpu):
    os.sched_setaffinity(0, [cpu])
    t0 = time.time()
    V0, ema0, R0, th, T = acquisition(pattern)
    cs = cases()
    k = len(cs)
    alpha, L = DL.BODIES[body]
    G = S.ghat(SIDE, L) if alpha else None
    p = replace(NATIVE, sigma=0.1)
    nb = len(RECORDS)
    idx = np.tile(np.arange(k), nb)
    V, E = np.tile(V0, (nb, 1, 1)), np.tile(ema0, (nb, 1, 1))
    r = np.tile(R0, (nb, 1, 1))
    gain = np.zeros((nb * k, SIDE, SIDE))
    for i, rec in enumerate(RECORDS):
        sl = slice(i * k, (i + 1) * k)
        if rec in ("full", "rel"):
            gain[sl] = 0.2
        elif rec.startswith("a"):
            f, g = rec[1:].split("/g")
            gain[sl] = float(g) * anchors(cs, int(f))
    m = None
    if wound:
        m1 = wound_mask(cs)
        m = np.tile(m1, (nb, 1, 1))
        if wound == "flip":
            V = np.where(m, -V, V)
        else:
            nbv = np.stack([0.2 * address(TAG, *c.key(), "newborn").standard_normal((SIDE, SIDE)) for c in cs])
            nbv = np.tile(nbv, (nb, 1, 1))
            V, E = np.where(m, nbv, V), np.where(m, nbv, E)
        gain = np.where(m, 0.0, gain)                     # wounded anchors and the held record inside are lost...
        for i, rec in enumerate(RECORDS):                 # ...except the full held record, which DL001 kept intact
            sl = slice(i * k, (i + 1) * k)
            if rec in ("full", "rel"):
                gain[sl] = 0.2
        rel = slice(RECORDS.index("rel") * k, (RECORDS.index("rel") + 1) * k)
        r[rel] = np.where(m1, -R0, R0) if wound == "flip" else np.where(m1, 0.0, R0)
    rel = slice(RECORDS.index("rel") * k, (RECORDS.index("rel") + 1) * k)
    J = bonds(R0, True)
    B = bproj(R0, 4)
    st = Stream(TAG, cs, "future", side=SIDE)
    xs = Stream(TAG, cs, "record-noise", side=SIDE)
    snaps = (500, 2000, 4000) if wound else (2000, 4000)
    out, buf, xbuf = {}, None, None
    Tb = np.tile(T, (nb, 1, 1))
    for t in range(1, 4001):
        i = (t - 1) % 250
        if i == 0:
            buf, xbuf = st.take(250), xs.take(250)
        V, E, Vt, drift, d = S.body(V, E, r, (th * theta)[idx], buf[i][idx], p, gain, alpha, G)
        r[rel] = record_step(r[rel], xbuf[i], EPS, KR, SIGMA_R, KC, B, J)
        if t in snaps:
            sg = S.sign(V, Tb).reshape(nb, k)
            for ri, rec in enumerate(RECORDS):
                out.setdefault(rec, {})[f"sign@{t}"] = round(float(sg[ri].mean()), 4)
                if wound:
                    pa = S.patch(V, Tb, m).reshape(nb, k)
                    out[rec][f"patch@{t}"] = round(float(pa[ri].mean()), 4)
            if t == 4000:
                sp = S.spacing(V).reshape(nb, k)
                for ri, rec in enumerate(RECORDS):
                    out[rec]["spacing@4000"] = round(float(sp[ri].mean()), 3)
    return {"body": body, "pattern": pattern, "theta": theta, "wound": wound, "res": out, "wall_s": round(time.time() - t0, 1)}


def task(a):
    return run(*a)


def main():
    cpus = [int(c) for c in sys.argv[1].split(",")]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=min(len(cpus), 3)) as ex:
        list(ex.map(acquisition, ("S4", "LB", "F0")))
    jobs = [(b, pat, th, "") for b in ("dw", "li2", "li4") for pat in ("S4", "LB", "F0") for th in (0.0, 1.0)]
    jobs += [(b, pat, th, w) for b in ("dw", "li4") for pat in ("S4", "LB") for th in (0.0, 1.0) for w in ("flip", "reset")]
    with ProcessPoolExecutor(max_workers=len(cpus)) as ex:
        rows = list(ex.map(task, [(*j, cpus[i % len(cpus)]) for i, j in enumerate(jobs)]))
    out = {"probe": "P14", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "tag": TAG, "blocks": list(BLOCKS), "side": SIDE,
           "records": RECORDS, "rows": rows, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "wall_s": round(time.time() - t0, 1), "cpu_s": round(sum(r["wall_s"] for r in rows), 1)}
    OUT.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    print("wrote", OUT, OUT.stat().st_size, "bytes;", len(rows), "tasks;", out["wall_s"], "s wall")


if __name__ == "__main__":
    main()
