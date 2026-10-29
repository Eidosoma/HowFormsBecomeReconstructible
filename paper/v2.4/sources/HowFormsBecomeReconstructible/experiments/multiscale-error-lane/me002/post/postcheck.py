"""Independent checks of the ME002 development run itself, on development block 910100 (written
during the run, outside the frozen source set; the frozen me002/checks.py is reused unchanged).

python me002/post/postcheck.py --root DEV_ROOT --cpus LIST   (writes results/me002/postcheck_receipt.json)

checks.py enrols engineering identities; here its enrolment and block are pointed at the
development block, which is the only change. Items: the independent per-site replay of the nine
qualification branches and a fresh reading (within 1e-9), the legacy blueprint_step replay (bit
for bit), the exact aliases (clamp, vote, oracle, quiet arbiter, cross-panel), and endpoints
recomputed from saved states and re-read packets.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from me002 import checks as C  # noqa: E402
from me002 import design as D  # noqa: E402
from me002 import sim  # noqa: E402
from mse.assay import enrol  # noqa: E402

BLOCK = D.IDENTITIES["development"][0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--cpus", required=True)
    a = ap.parse_args()
    os.sched_setaffinity(0, [int(c) for c in a.cpus.split(",")])
    root, t0 = a.root.resolve(), time.time()
    C.BLOCK = BLOCK
    C.enrol = lambda blocks, messages, parents, purpose: enrol(blocks, messages, parents, "development")
    calib = json.loads((LANE / "me002/frozen/calibration.json").read_text())
    rawf = lambda p, r: C.npz(root / "raw" / p / r / f"{BLOCK}.npz")
    shard = lambda p, r: C.npz(root / "shards" / p / r / f"{BLOCK}.npz")
    out = {}
    worst, items = 0.0, {}
    for p, r, arm, cond, ci in C.Q4_PICKS:
        (V, R, Q), start = C.scalar_window(p, r, arm, cond, ci, calib)
        raw, k = rawf(p, r), C.cidx(p, cond)
        d = max(float(np.abs(start[0] - raw["s0/V"][ci]).max()), float(np.abs(V - raw[f"{arm}/V"][k, ci]).max()),
                float(np.abs(R - raw[f"{arm}/R"][k, ci]).max()), float(np.abs(Q - raw[f"{arm}/Q"][k, ci]).max()))
        items[f"{p}/{r}/{arm}/{cond}/case{ci}"], worst = d, max(worst, d)
    raw = rawf("F", D.PRIMARY)
    e = D.ENVIRONMENTS.index("mixed")
    for g, (V, packet) in enumerate(C.scalar_chain(D.PRIMARY, "arbiter_R", "mixed", 7, calib, generations=1)):
        d = max(float(np.abs(V - raw["arbiter_R/V"][g, e, 7]).max()), float(np.abs(packet - raw["arbiter_R/packet"][g, e, 7]).max()))
        items[f"F/arbiter_R/mixed/gen{g}"], worst = d, max(worst, d)
    out["independent_replay"] = {"pass": worst <= 1e-9, "max_abs_difference": worst, "items": items}
    legacy = {}
    legacy.update(C.legacy_replay("C", D.PRIMARY, rawf("C", D.PRIMARY),
                                  {"inactive": (0.0, 0.0), "hold_site": (None, 0.0), "reciprocal": (None, None)}))
    r = D.regime("F4", 0.1, 2.5)
    legacy.update(C.legacy_replay("B", r, rawf("B", r), {"inactive": (0.0, 0.0), "hold_site": (None, 0.0)}))
    out["legacy_bit_exact"] = {"pass": all(legacy.values()), "items": len(legacy)}
    alias = {}
    for r in D.PANELS["D"]["regimes"]:
        raw, conds = rawf("D", r), [c.name for c in D.COND_D]
        alias[f"D/{r}/clamp_site(ref)=hold(sham)"] = all(np.array_equal(raw["clamp_site/V"][conds.index(c)], raw["hold_site/V"][0])
                                                         for c in conds if c.startswith("reference-"))
        alias[f"D/{r}/dual_vote=hold(records agree)"] = all(np.array_equal(raw["dual_vote/V"][conds.index(c)], raw["hold_site/V"][conds.index(c)])
                                                            for c in ("sham", "body-collective-2"))
    for p in ("A", "B", "C"):
        for r in D.PANELS[p]["regimes"]:
            raw, sh = rawf(p, r), shard(p, r)
            for arm in D.PANELS[p]["arms"]:
                if arm.control == "arbiter":
                    quiet = sh[f"{arm.name}/a_bursts"] == 0
                    alias[f"{p}/{r}/{arm.name}=hold(no burst)"] = bool(np.array_equal(raw[f"{arm.name}/V"][quiet], raw["hold_site/V"][quiet]))
    for p in ("B", "D", "E"):
        for r in D.PANELS[p]["regimes"]:
            if r not in D.PANELS["C"]["regimes"]:
                continue
            x, y = rawf(p, r), rawf("C", r)
            shared = [c.name for c in D.PANELS[p]["conditions"] if c.name in [d.name for d in D.COND_C]]
            alias[f"{p}=C/{r}/hold_site"] = all(np.array_equal(x["hold_site/V"][C.cidx(p, c)], y["hold_site/V"][C.cidx("C", c)]) for c in shared)
    out["aliases_exact"] = {"pass": all(alias.values()), "items": len(alias), "failed": [k for k, v in alias.items() if not v][:10]}
    bad = []
    cases = enrol([BLOCK], D.MESSAGES, D.PARENTS, "development")
    births, Zr = sim.recipients(cases)
    for p, r in D.tasks():
        raw, sh = rawf(p, r), shard(p, r)
        T = raw["targets"]
        if p == "F":
            for arm in D.PANELS["F"]["arms"]:
                V = raw[f"{arm.name}/V"]
                got = sim.body_endpoints(V.reshape(-1, 16, 16), np.broadcast_to(T, V.shape).reshape(-1, 16, 16), "v")
                bad += [f"{p}/{r}/{arm.name}/{k}" for k, v in got.items() if not np.array_equal(v.reshape(sh[f"{arm.name}/{k}"].shape), sh[f"{arm.name}/{k}"])]
            continue
        nc = len(D.PANELS[p]["conditions"])
        Tb, idx = np.tile(T, (nc, 1, 1)), np.tile(np.arange(D.NCASE), nc)
        for j, arm in enumerate(D.PANELS[p]["arms"]):
            got = sim.body_endpoints(raw[f"{arm.name}/V"].reshape(-1, 16, 16), Tb, "v")
            if j == len(D.PANELS[p]["arms"]) - 1:
                for pk in arm.packets:
                    P = raw[f"{arm.name}/{pk}"].reshape(-1, 16, 16)
                    got.update(sim.fresh_endpoints(sim.read_batch(P, idx, raw["theta"], births, Zr, sim.params(r)[1]), Tb, f"f{pk}"))
            bad += [f"{p}/{r}/{arm.name}/{k}" for k, v in got.items() if not np.array_equal(v.reshape(nc, D.NCASE), sh[f"{arm.name}/{k}"])]
    out["reanalysis_exact"] = {"pass": not bad, "mismatched": bad[:10]}
    manifest = json.loads((root / "manifest.json").read_text())
    frozen = json.loads((LANE / "me002/frozen/design.json").read_text())
    receipt = {"status": "PASS" if all(v["pass"] for v in out.values()) else "FAIL", "block": BLOCK,
               "design_digest": D.digest(), "run_design_digest": manifest["design_digest"],
               "run_sources_equal_frozen": manifest["sources"] == frozen["sources"],
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "run": {k: manifest[k] for k in ("started_utc", "finished_utc", "wall_s", "cpu_s_total", "worker_maxrss_mb_peak",
                                                "bytes_written", "cpus", "host")},
               "checks": out}
    path = LANE / "results" / "me002" / "postcheck_receipt.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps({"status": receipt["status"], **{k: v["pass"] for k, v in out.items()},
                      "sources_equal_frozen": receipt["run_sources_equal_frozen"]}, indent=1))


if __name__ == "__main__":
    main()
