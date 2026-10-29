"""Engineering probe P12b (python probes/p12b_dl001_design_inputs.py CPUS): DL001's last design inputs, run after
P12 on its blocks and tag. ENGINEERING_PROBE_NOT_EVIDENCE.

  X  the reversed match on a 64-site sheet: the double well, the period-8 body li4 and a period-16 body li16
     (alpha 1.56, L = 16, a quarter of the sheet) on S4 (period 8), S8 (period 16) and F0 (period 64), theta
     removed, sigma 0.1: no record (t = 2,000 and 8,000) and the held record at gains 0.02-0.4;
  G  the held record at gain 0.4 on the 32-site sheet (P12's grid stopped at 0.2), every body and pattern,
     theta x0 and x1, sigma 0.1;
  C  a continuous spacing estimate for DL001's registered endpoint: P12's free-memory runs (32 sites, no record,
     t = 8,000) read with the power-weighted mean wavenumber over 0 < |q| <= pi/2 (wavelengths of 4 sites or
     more), beside P12's per-case 2-D argmax, whose discrete values gave block SDs up to 5.7.
P12's functions are reused with the module's SIDE and ROOT set per task.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

from concurrent.futures import ProcessPoolExecutor  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

import p12_dl001_design_inputs as P  # noqa: E402

OUT = P.LANE / "probes" / "results" / "p12b_dl001_design_inputs.json"
K16 = 2.0 - 2.0 * np.cos(2 * np.pi / 16)
EXTRA = {"li16": ((1.0 + 256.0 * K16) ** 2 / (4.0 * 256.0), 16.0)}


def configure(side):
    P.SIDE = side
    P.ROOT = Path(f"/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/probes/p12{'' if side == 32 else 'b64'}")
    P.BODIES.update(EXTRA)


def spacing_centroid(V, qmax=np.pi / 2):
    side = V.shape[-1]
    S = np.abs(np.fft.fft2(V - V.mean((-2, -1), keepdims=True))) ** 2
    q = 2 * np.pi * np.fft.fftfreq(side)
    qq = np.hypot(q[:, None], q[None, :])
    w = (qq > 0) & (qq <= qmax)
    return 2 * np.pi / ((S * qq * w).sum((-2, -1)) / (S * w).sum((-2, -1)))


def task(args):
    side = args[0]
    configure(side)
    if args[1] == "C":
        _, _, body, pattern, sigma, ths, cpu = args
        os.sched_setaffinity(0, [cpu])
        t0 = time.time()
        V0, ema0, R0, th, T = P.acquisition(pattern)
        p = P.replace(P.NATIVE, sigma=sigma)
        o = P.run(V0.copy(), ema0.copy(), np.zeros_like(V0), th * ths, p, False, 0.0, body, 8000, "F", {8000}, T)
        res = {"lam_centroid@8000": P.summarise(spacing_centroid(o["final"])),
               "lam_argmax@8000": P.summarise(P.peak_wavelength(o["final"])), "sign@8000": P.summarise(o["sign"][8000])}
        return {"side": side, "panel": "C", "body": body, "pattern": pattern, "sigma": sigma, "theta_scale": ths,
                "res": res, "wall_s": round(time.time() - t0, 1)}
    return {"side": side, **P.task(args[1:])}


def main():
    cpus = [int(c) for c in sys.argv[1].split(",")]
    t0 = time.time()
    configure(64)
    with ProcessPoolExecutor(max_workers=min(len(cpus), 3)) as ex:
        list(ex.map(lambda_acq, ("S4", "S8", "F0")))
    jobs = []
    for b in ("dw", "li4", "li16"):
        for pat in ("S4", "S8", "F0"):
            jobs.append((64, "F", b, pat, 0.1, False, 0.0, "", 0.0))
            for g in (0.02, 0.05, 0.2, 0.4):
                jobs.append((64, "U", b, pat, 0.1, False, g, "", 0.0))
    for b in ("dw", "li2", "li4"):
        for pat in P.PATTERNS:
            for ths in (0.0, 1.0):
                jobs.append((32, "U", b, pat, 0.1, False, 0.4, "", ths))
    jobs.sort(key=lambda j: (-j[0], j[1]))
    jobs += [(32, "C", b, pat, s, ths) for b in ("dw", "li2", "li4") for pat in P.PATTERNS for s in (0.1, 0.3)
             for ths in (0.0, 1.0)]
    with ProcessPoolExecutor(max_workers=len(cpus)) as ex:
        rows = list(ex.map(task, [(*j[:-1], j[-1], cpus[i % len(cpus)]) for i, j in enumerate(jobs)]))
    out = {"probe": "P12b", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "tag": P.TAG, "blocks": list(P.BLOCKS),
           "bodies": {"li16": {"alpha": round(float(EXTRA["li16"][0]), 4), "L": 16.0},
                      **{k: {"alpha": round(float(a), 4), "L": L} for k, (a, L) in P.BODIES.items() if k != "li16"}},
           "rows": rows, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
           "cpu_s": round(sum(r["wall_s"] for r in rows), 1)}
    OUT.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    print("wrote", OUT, OUT.stat().st_size, "bytes;", len(rows), "tasks;", out["wall_s"], "s wall")


def lambda_acq(pattern):
    configure(64)
    return P.acquisition(pattern)[0].shape


if __name__ == "__main__":
    main()
