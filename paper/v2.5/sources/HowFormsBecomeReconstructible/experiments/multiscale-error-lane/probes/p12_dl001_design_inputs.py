"""Engineering probe P12 (python probes/p12_dl001_design_inputs.py CPUS): design inputs for DL001, the design
ledger. ENGINEERING_PROBE_NOT_EVIDENCE.

The body: br001.sim.body_step's double well plus lateral inhibition, drift -= alpha * (G_L * V), where
G_L = (1 - L^2 Lap)^-1 on the periodic lattice (applied by FFT). alpha = 0 is br001.sim.body_step bit for bit
(checked first). With coupling c, the linear growth rate at V = 0 is g(k) = 1 - c k / 4 - alpha / (1 + L^2 k),
k = 4 - 2 cos qx - 2 cos qy, so a body prefers stripes of period 8 (k* = 2 - sqrt 2) when
alpha = c (1 + L^2 k*)^2 / (4 L^2). For alpha > 1 the double well has no uniform state left.

Cases: engineering blocks 900864-900867 (32 cases), tag mse-p12, side 32. Records and bodies are acquired as in
GW001 (msegrid.acquire, conserved body, sigma 0.1); the acquired state is shared by every body (paired). After
acquisition the environmental field theta is kept (x1, spread 0.2) or removed (x0): a first look on 26 Oct showed
that theta alone turns the stripe body's native stripes into a labyrinth of the same spacing.
Panels (open body unless stated), each at theta x0 and x1:
  S  spontaneous pattern from newborn noise, no record: preferred wavelength and amplitude;
  F  free memory: the acquired body, no record, open and conserved; t = 500, 2,000, 8,000: sign agreement
     (registration) and best-shift agreement (form);
  U  upkeep: the taught record held unchanged (protected) at gains 0.02-0.2: agreement and correction work;
  W  repair: an 8 x 8 body wound in S4 (reset to newborn noise, or flipped), no record or the held record;
  B  build: from newborn noise, with the held record.
With --control (run after the main probe, 26 Oct): a body tuned to stripes of period 16 (alpha 1.56, L = 16) on a
few tasks, to see whether the advantage follows the match between pattern and body; written to
p12_dl001_control.json.
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

from br001.sim import body_step  # noqa: E402
from mse.assay import enrol  # noqa: E402
from mse.native import NATIVE, address, moving_average, neighbours  # noqa: E402
from msegrid.core import Stream, acquire, base, birth  # noqa: E402

TAG = "mse-p12"
SIDE = 32
BLOCKS = tuple(range(900864, 900868))
MESSAGES, PARENTS = (0, 1, 2, 3), (0, 1)
SETTLE, TEACH, RELEASE, AMPLITUDE, SIGMA_ACQ = 120, 1000, 200, 1.2, 0.1
KSTAR = 2.0 - np.sqrt(2.0)                      # stripes of period 8 along one axis


def alpha_for(L, coupling=1.0):
    return coupling * (1.0 + L * L * KSTAR) ** 2 / (4.0 * L * L)


BODIES = {"dw": (0.0, 0.0), "li2": (alpha_for(2), 2.0), "li3": (alpha_for(3), 3.0), "li4": (alpha_for(4), 4.0)}
PATTERNS = ("S4", "S8", "F0", "BL")
THETAS = (0.0, 1.0)                              # theta kept (x1) or removed (x0) after acquisition
GAINS = (0.005, 0.02, 0.05, 0.1, 0.2)
ROOT = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/probes/p12")
OUT = LANE / "probes" / "results" / "p12_dl001_design_inputs.json"


def template(family, kind, block):
    if family == "S4":
        f = np.tile(np.where((np.arange(SIDE) // 4) % 2 == 0, 1.0, -1.0), (SIDE, 1))
        if kind % 2 == 1:
            f = f.T.copy()
        return f if kind < 2 else -f
    return base(family, kind, SIDE, TAG, block)


def ghat(L):
    q, qr = 2 * np.pi * np.fft.fftfreq(SIDE), 2 * np.pi * np.fft.rfftfreq(SIDE)
    k = (2 - 2 * np.cos(q))[:, None] + (2 - 2 * np.cos(qr))[None, :]
    return 1.0 / (1.0 + L * L * k)


def step(V, ema, r, th, z, p, conserved, gain, alpha, G):
    """br001.sim.body_step with lateral inhibition; also returns the drift and the correction."""
    drift = V - V ** 3 + p.well_asym + th + p.coupling * (neighbours(V) - V)
    if alpha:
        drift = drift - alpha * np.fft.irfft2(np.fft.rfft2(V) * G, s=(SIDE, SIDE))
    noise = p.sigma * z
    if conserved:
        drift = drift - drift.mean(axis=(-2, -1), keepdims=True)
        noise = noise - noise.mean(axis=(-2, -1), keepdims=True)
    Vt = np.clip(V + p.dt * drift + noise, -p.bound, p.bound)
    ema = moving_average(ema, Vt, p)
    d = gain * (r - Vt)
    if conserved:
        d = d - d.mean(axis=(-2, -1), keepdims=True)
    return np.clip(Vt + p.dt * d, -p.bound, p.bound), ema, Vt, drift, d


def sign_agree(V, T):
    return ((V > 0) == (T > 0)).mean((-2, -1))


def best_shift(V, T):
    a, b = np.sign(V), np.sign(T)
    c = np.fft.irfft2(np.fft.rfft2(a) * np.conj(np.fft.rfft2(b)), s=(SIDE, SIDE))
    return (1.0 + c.reshape(len(c), -1).max(-1) / (SIDE * SIDE)) / 2.0


def peak_wavelength(V):
    S = np.abs(np.fft.fft2(V - V.mean((-2, -1), keepdims=True))) ** 2
    q = 2 * np.pi * np.fft.fftfreq(SIDE)
    qq = np.hypot(q[:, None], q[None, :])
    S[:, 0, 0] = 0.0
    idx = S.reshape(len(S), -1).argmax(-1)
    return 2 * np.pi / qq.ravel()[idx]


def cases():
    return enrol(list(BLOCKS), MESSAGES, PARENTS, "engineering")


def acquisition(pattern):
    path = ROOT / f"acq_{pattern}.npz"
    if path.exists():
        z = np.load(path)
        return z["V"], z["ema"], z["R"], z["th"], z["T"]
    cs = cases()
    T = np.stack([AMPLITUDE * template(pattern, c.message, c.block) for c in cs])
    V, ema, R, th = acquire(TAG, cs, T, replace(NATIVE, sigma=SIGMA_ACQ), SIDE, settle=SETTLE, teach=TEACH, release=RELEASE)
    ROOT.mkdir(parents=True, exist_ok=True)
    tmp = ROOT / f".acq_{pattern}.{os.getpid()}.npz"
    np.savez(tmp, V=V, ema=ema, R=R, th=th, T=T)
    os.replace(tmp, path)
    return V, ema, R, th, T


def run(V, ema, r, th, p, conserved, gain, body, updates, stream, snaps, T, mask=None):
    alpha, L = BODIES[body]
    G = ghat(L) if alpha else None
    st = Stream(TAG, cases(), "p12", stream, side=SIDE)
    out = {"sign": {}, "shift": {}, "patch": {}}
    wc = wd = 0.0
    nwork = 0
    buf = None
    for t in range(1, updates + 1):
        i = (t - 1) % 250
        if i == 0:
            buf = st.take(250)
        V, ema, Vt, drift, d = step(V, ema, r, th, buf[i], p, conserved, gain, alpha, G)
        if t > updates // 2:
            wc += np.abs(p.dt * d).mean((-2, -1))
            wd += np.abs(p.dt * drift).mean((-2, -1))
            nwork += 1
        if t in snaps:
            out["sign"][t] = sign_agree(V, T)
            out["shift"][t] = best_shift(V, T)
            if mask is not None:
                out["patch"][t] = ((((V > 0) == (T > 0)) & mask).sum((-2, -1)) / mask.sum((-2, -1)))
    out["w_corr"], out["w_drift"] = wc / nwork, wd / nwork
    out["final"] = V
    return out


def summarise(x):
    """[mean over the 32 cases, SD of the 4 block means]."""
    a = np.asarray(x, float).reshape(len(BLOCKS), -1)
    return [round(float(a.mean()), 4), round(float(a.mean(1).std(ddof=1)), 4)]


def task(args):
    panel, body, pattern, sigma, conserved, gain, wound, ths, cpu = args
    os.sched_setaffinity(0, [cpu])
    t0 = time.time()
    p = replace(NATIVE, sigma=sigma)
    V0, ema0, R0, th, T = acquisition(pattern)
    th = th * ths
    cs = cases()
    res = {}
    if panel == "S":
        Vb = birth(TAG, cs, "p12-birth", side=SIDE)
        o = run(Vb, Vb.copy(), np.zeros_like(Vb), th, p, conserved, 0.0, body, 2000, "S", {2000}, T)
        V = o["final"]
        res = {"lambda": summarise(peak_wavelength(V)), "mean_abs_v": summarise(np.abs(V).mean((-2, -1))),
               "frac_abs_gt_0.5": summarise((np.abs(V) > 0.5).mean((-2, -1)))}
    elif panel == "F":
        o = run(V0.copy(), ema0.copy(), np.zeros_like(V0), th, p, conserved, 0.0, body, 8000, "F", {500, 2000, 8000}, T)
        res = {f"{k}@{t}": summarise(o[k][t]) for k in ("sign", "shift") for t in (500, 2000, 8000)}
        res["lambda@8000"] = summarise(peak_wavelength(o["final"]))
    elif panel == "U":
        o = run(V0.copy(), ema0.copy(), R0, th, p, conserved, gain, body, 2000, "U", {2000}, T)
        res = {"sign@2000": summarise(o["sign"][2000]), "shift@2000": summarise(o["shift"][2000]),
               "qual@2000": summarise((((o["final"] > 0) == (T > 0)) & (np.abs(o["final"]) > 0.2)).mean((-2, -1))),
               "w_corr": summarise(o["w_corr"]), "w_drift": summarise(o["w_drift"])}
    elif panel == "W":
        mask = np.zeros((len(cs), SIDE, SIDE), bool)
        for j, c in enumerate(cs):
            a, b = address(TAG, *c.key(), "p12-wound").integers(0, SIDE, 2)
            mask[j][np.ix_(np.arange(a, a + 8) % SIDE, np.arange(b, b + 8) % SIDE)] = True
        V, ema = V0.copy(), ema0.copy()
        if wound == "flip":
            V = np.where(mask, -V, V)
        else:
            nb = np.stack([0.2 * address(TAG, *c.key(), "p12-newborn").standard_normal((SIDE, SIDE)) for c in cs])
            V, ema = np.where(mask, nb, V), np.where(mask, nb, ema)
        r = R0 if gain > 0 else np.zeros_like(R0)
        o = run(V, ema, r, th, p, conserved, gain, body, 2000, "W", {250, 500, 2000}, T, mask)
        res = {f"patch@{t}": summarise(o["patch"][t]) for t in (250, 500, 2000)}
        res["sign@2000"] = summarise(o["sign"][2000])
    elif panel == "B":
        Vb = birth(TAG, cs, "p12-birth", side=SIDE)
        o = run(Vb, Vb.copy(), R0, th, p, conserved, gain, body, 2000, "B", {500, 2000}, T)
        res = {f"sign@{t}": summarise(o["sign"][t]) for t in (500, 2000)}
        res["shift@2000"] = summarise(o["shift"][2000])
        res["w_corr"] = summarise(o["w_corr"])
    return {"panel": panel, "body": body, "pattern": pattern, "sigma": sigma, "conserved": conserved, "gain": gain,
            "wound": wound, "theta_scale": ths, "res": res, "wall_s": round(time.time() - t0, 1)}


def check_equal():
    """alpha = 0 equals br001.sim.body_step bit for bit, open and conserved."""
    g = np.random.default_rng(0)
    V, ema, r, th = (g.standard_normal((4, SIDE, SIDE)) for _ in range(4))
    for conserved in (False, True):
        a, b = (V.copy(), ema.copy()), (V.copy(), ema.copy())
        for _ in range(50):
            z = g.standard_normal((4, SIDE, SIDE))
            a = step(a[0], a[1], r, th, z, NATIVE, conserved, 0.2, 0.0, None)[:2]
            b = body_step(b[0], b[1], r, th, z, NATIVE, conserved, 0.2)[:2]
        assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1]), conserved
    return True


def control(cpus):
    k16 = 2.0 - 2.0 * np.cos(2 * np.pi / 16)
    BODIES["li16"] = ((1.0 + 256.0 * k16) ** 2 / (4.0 * 256.0), 16.0)
    jobs = [("S", "li16", "S4", 0.1, False, 0.0, "", ths) for ths in THETAS]
    jobs += [("F", "li16", pat, 0.1, False, 0.0, "", 0.0) for pat in PATTERNS]
    jobs += [("U", "li16", pat, 0.1, False, g, "", 0.0) for pat in ("S4", "S8", "F0") for g in (0.05, 0.2)]
    jobs += [("W", "li16", "S4", 0.1, False, 0.0, "reset", 0.0)]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=len(cpus)) as ex:
        rows = list(ex.map(task, [(*j, cpus[i % len(cpus)]) for i, j in enumerate(jobs)]))
    out = {"probe": "P12 control", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "tag": TAG, "blocks": list(BLOCKS),
           "side": SIDE, "body": {"li16": {"alpha": round(float(BODIES["li16"][0]), 4), "L": 16.0}}, "rows": rows,
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1)}
    path = OUT.with_name("p12_dl001_control.json")
    path.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    print("wrote", path, path.stat().st_size, "bytes")


def main():
    cpus = [int(c) for c in sys.argv[1].split(",")]
    if "--control" in sys.argv:
        BODIES.clear()
        control(cpus)
        return
    t0 = time.time()
    eq = check_equal()
    with ProcessPoolExecutor(max_workers=min(len(cpus), len(PATTERNS))) as ex:
        list(ex.map(acquisition, PATTERNS))
    jobs = []
    for ths in THETAS:
        for b in BODIES:
            for s in (0.1, 0.3):
                jobs.append(("S", b, "S4", s, False, 0.0, "", ths))
                for pat in PATTERNS:
                    for cons in (False, True):
                        jobs.append(("F", b, pat, s, cons, 0.0, "", ths))
                    for gn in GAINS:
                        jobs.append(("U", b, pat, s, False, gn, "", ths))
                for w in ("reset", "flip"):
                    for gn in (0.0, 0.2):
                        jobs.append(("W", b, "S4", s, False, gn, w, ths))
            for pat in ("S4", "F0", "BL"):
                for gn in (0.05, 0.2):
                    jobs.append(("B", b, pat, 0.1, False, gn, "", ths))
    jobs.sort(key=lambda j: {"F": 0, "U": 1, "W": 2, "B": 3, "S": 4}[j[0]])
    with ProcessPoolExecutor(max_workers=len(cpus)) as ex:
        rows = list(ex.map(task, [(*j, cpus[i % len(cpus)]) for i, j in enumerate(jobs)]))
    out = {"probe": "P12", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "tag": TAG, "blocks": list(BLOCKS), "side": SIDE,
           "bodies": {k: {"alpha": round(float(a), 4), "L": L} for k, (a, L) in BODIES.items()},
           "alpha0_equals_br001_body_step": eq, "rows": rows,
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
           "cpu_s": round(sum(r["wall_s"] for r in rows), 1)}
    OUT.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    print("wrote", OUT, OUT.stat().st_size, "bytes;", len(rows), "tasks;", out["wall_s"], "s wall")


if __name__ == "__main__":
    main()
