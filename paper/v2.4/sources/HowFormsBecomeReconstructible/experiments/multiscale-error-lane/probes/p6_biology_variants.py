"""Engineering probe P6 (python probes/p6_biology_variants.py CPU): are three ME002 results artifacts of the
apparatus or robust to biologically motivated variants? ENGINEERING_PROBE_NOT_EVIDENCE.

Engineering blocks 900980-900987 (64 cases), F0 at sigma 0.3, g = 1, ME002's machinery, thresholds and
acquisition; every injury at the window's start, window 1,800 updates (so a 1,000-update latch can expire).
1. The v2 arbiter's harm after a collective body injury: is it the clipping-induced shift of the conserved
   mean? Compare the standard injury with a mean-restored one (after clipping, the deficit is spread over
   the unclipped sites, so the conserved mean is unchanged).
2. The two-record vote under combined injury: independent fields for the body and the first record
   (ME002) against the SAME field for both (a wound that hits tissue and its local record together).
3. Coarse backups under a local lesion: a 6 x 6 patch (off the pooling grid) of the record, or of the
   body, has its sign flipped, instead of a band-limited field over the whole sheet.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import json  # noqa: E402
from pathlib import Path  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402
from scipy.stats import t as student  # noqa: E402

from me002 import design as D  # noqa: E402
from me002 import sim  # noqa: E402
from me002.policies import Arbiter2  # noqa: E402
from me002.worker import backup  # noqa: E402
from mse.engine import State  # noqa: E402

BLOCKS = list(range(900980, 900988))
L = 1800
NAME = D.regime("F0", 0.3)
PATCH = (slice(5, 11), slice(3, 9))


def interval(diff, k):
    b = diff.reshape(-1, k).mean(1)
    half = student.ppf(0.975, len(b) - 1) * b.std(ddof=1) / np.sqrt(len(b))
    return [round(float(b.mean()), 4), round(float(b.mean() - half), 4), round(float(b.mean() + half), 4)]


def main():
    os.sched_setaffinity(0, {int(sys.argv[1])} if len(sys.argv) > 1 else os.sched_getaffinity(0))
    t0 = time.time()
    calib = json.loads((LANE / "me002/frozen/calibration.json").read_text())
    thr = calib["regimes"][NAME]
    tm, ts = thr["mismatch_traj"]["region"][str(L)], thr["surprise_traj"][str(L)]
    cases, s0, th, p, T, Tf = sim.prepare(NAME, BLOCKS, "engineering")
    k = len(cases)
    fb = sim.band_field(cases, "body", "collective", 2.0)
    fr = sim.band_field(cases, "reference", "collective", 2.0)
    clip = lambda x: np.clip(x, -2.0, 2.0)
    V_inj = clip(s0.V + fb)
    V_mr = V_inj.copy()
    for i in range(k):                       # restore the conserved mean on the unclipped sites
        free = np.abs(V_mr[i]) < 2.0
        V_mr[i][free] += (s0.V[i].mean() - V_mr[i].mean()) * 256 / free.sum()
    V_mr = clip(V_mr)
    lesionR, lesionV = s0.R.copy(), s0.V.copy()
    lesionR[:, PATCH[0], PATCH[1]] *= -1
    lesionV[:, PATCH[0], PATCH[1]] *= -1
    starts = {  # name: (V, R, R2 for two-record arms)
        "sham": (s0.V, s0.R, s0.R),
        "body-collective-2": (V_inj, s0.R, s0.R),
        "body-collective-2 mean-restored": (V_mr, s0.R, s0.R),
        "both-collective-2 independent": (V_inj, clip(s0.R + fr), s0.R),
        "both-collective-2 correlated": (V_inj, clip(s0.R + fb), s0.R),
        "record lesion 6x6": (s0.V, lesionR, s0.R),
        "body lesion 6x6": (lesionV, s0.R, s0.R),
    }
    mean_shift = {"standard": round(float(np.abs((V_inj - s0.V).mean((-2, -1))).mean()), 4),
                  "mean-restored": round(float(np.abs((V_mr - s0.V).mean((-2, -1))).mean()), 4)}
    Z = sim.draws(cases, "future", updates=L)
    births, Zr = sim.recipients(cases)
    idx = np.arange(k)
    arms = {"hold_site": D.ARM["D"]["hold_site"], "arbiter": D.ARM["D"]["arbiter"], "dual_vote": D.ARM["D"]["dual_vote"],
            "clamp_site": D.ARM["D"]["clamp_site"], "clamp_region": D.ARM["D"]["clamp_region"]}
    res = {}
    for cname, (V, R, R2) in starts.items():
        row = {}
        for aname, arm in arms.items():
            ctl = Arbiter2(k, tm, ts) if arm.control == "arbiter" else None
            clamp = (arm.clamp, backup(s0.R, arm.clamp)) if arm.clamp else None
            st = State(V.copy(), s0.ema.copy(), R.copy(), np.zeros_like(V))
            end, _, _ = sim.simulate(st, th, Z, idx, p, L, sim.route(arm), ctl, None, clamp,
                                     copy2=R2.copy() if arm.copies == 2 else None)
            F = sim.read_batch(end.Q, idx, th, births, Zr, p)
            m, a = (end.V > 0) == (T > 0), np.abs(end.V) > 0.2
            row[aname] = {"v_qual": (m & a).mean((-2, -1)), "fQ_qual": sim.fresh_endpoints(F, T, "f")["f_qual"],
                          "bursts": None if ctl is None else ctl.bursts}
        res[cname] = row
    out = {"probe": "P6", "status": "ENGINEERING_PROBE_NOT_EVIDENCE", "blocks": [BLOCKS[0], BLOCKS[-1] + 1],
           "regime": NAME, "window": L, "mean_shift_abs": mean_shift, "contrasts": {}}
    for cname, row in res.items():
        c = {}
        for a, b in (("arbiter", "hold_site"), ("dual_vote", "hold_site"), ("dual_vote", "clamp_site"),
                     ("clamp_region", "clamp_site"), ("clamp_site", "hold_site")):
            for ep in ("v_qual", "fQ_qual"):
                c[f"{a} - {b} / {ep}"] = interval(row[a][ep] - row[b][ep], len(D.MESSAGES) * len(D.PARENTS))
        c["arbiter burst rate"] = round(float((res[cname]["arbiter"]["bursts"] > 0).mean()), 4)
        c["hold_site v_qual"] = round(float(row["hold_site"]["v_qual"].mean()), 4)
        out["contrasts"][cname] = c
    out["wall_s"] = round(time.time() - t0, 1)
    text = json.dumps(out, indent=1)
    (LANE / "probes" / "results" / "p6_biology_variants_v1.json").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
