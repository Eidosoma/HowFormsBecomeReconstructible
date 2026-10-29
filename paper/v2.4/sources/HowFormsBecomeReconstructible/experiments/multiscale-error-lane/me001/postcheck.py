"""Independent checks of the development run itself, on one development block (written after the run).

python -m me001.postcheck --root DEV_ROOT --cpus LIST   (writes results/me001_v2/postcheck_receipt.json)

Reuses the qualification checks' independent models (checks.py) on development block 910000:
the legacy blueprint_step replay (identity routes and the fresh reader, bit for bit), the
per-site loop replay built on the design fixtures (acquisition, twelve linear arms, a fresh
reading, within 1e-9), the exact aliases, and endpoints recomputed from the saved states.
checks.py enrols engineering identities; here its enrolment is pointed at the development
range, which is the only change.
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

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from me001 import checks as C  # noqa: E402
from me001 import design as D  # noqa: E402
from me001 import worker as W  # noqa: E402
from mse.assay import enrol  # noqa: E402
from mse.native import half_plane  # noqa: E402

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
    out = {}
    legacy = {}
    for r in (D.PRIMARY, "F4_s0.1"):
        legacy.update({f"{r}/{k}": v for k, v in C.legacy_replay(r, C.npz(root / "raw" / r / f"{BLOCK}.npz")).items()})
    out["legacy_bit_exact"] = {"pass": all(legacy.values()), "items": len(legacy)}
    worst = 0.0
    for r, ci in ((D.PRIMARY, 0), ("F2_s0.1", 6)):
        sc = C.scalar_case(r, ci)
        raw = C.npz(root / "raw" / r / f"{BLOCK}.npz")
        names = [D.condition_name(i) for i in D.FULL]
        for k in ("s0/V", "s0/R"):
            worst = max(worst, float(np.abs(sc[k] - raw[k][ci]).max()))
        for (arm, cond), (V, R, Q) in sc["arms"].items():
            k = D.arm_conditions(D.ARM[arm]).index(names.index(cond))
            worst = max(worst, *(float(np.abs(x - raw[f"{arm}/{f}"][k, ci]).max()) for x, f in ((V, "V"), (R, "R"), (Q, "Q"))))
        arm, cond, Vr = sc["fresh"]
        k = D.arm_conditions(D.ARM[arm]).index(names.index(cond))
        worst = max(worst, float(np.abs(Vr - raw[f"{arm}/fresh"][k, ci, 0]).max()))
    out["independent_replay"] = {"pass": worst <= 1e-9, "max_abs_difference": worst}
    alias, bad = {}, []
    for r in D.REGIMES:
        raw, e = C.npz(root / "raw" / r / f"{BLOCK}.npz"), C.npz(root / "shards" / r / f"{BLOCK}.npz")
        for lvl in ("site", "region", "sheet"):
            alias[f"{r}/reference_{lvl}"] = all(np.array_equal(raw[f"reference_{lvl}/{f}"], raw[f"inactive/{f}"]) for f in ("V", "Q", "fresh"))
        alias[f"{r}/snapshot_V"] = bool(np.array_equal(raw["snapshot/V"], raw["body_site/V"]))
        shift, _ = W.params(r)
        T = raw["targets"]
        templ = np.stack([np.roll(half_plane(k, D.AMPLITUDE), shift, axis=(0, 1)) for k in range(4)])
        own = np.array([c.message for c in enrol([BLOCK], D.MESSAGES, D.PARENTS, "development")])
        for arm in D.ARMS:
            nc = len(D.arm_conditions(arm))
            Tb = np.tile(T, (nc, 1, 1))
            got = W.body_endpoints(raw[f"{arm.name}/V"].reshape(-1, 16, 16), Tb, np.tile(W.edges(T), (nc, 1, 1)), "v1000")
            got.update(W.fresh_endpoints(raw[f"{arm.name}/fresh"].reshape(nc * 8, -1, 16, 16), Tb, templ, np.tile(own, nc)))
            bad += [f"{r}/{arm.name}/{k}" for k, v in got.items() if not np.array_equal(v.reshape(nc, 8), e[f"{arm.name}/{k}"])]
    out["aliases_exact"] = {"pass": all(alias.values()), "items": len(alias)}
    out["reanalysis_exact"] = {"pass": not bad, "mismatched": bad[:10]}
    manifest = json.loads((root / "manifest.json").read_text())
    receipt = {"status": "PASS" if all(v["pass"] for v in out.values()) else "FAIL", "block": BLOCK,
               "design_digest": D.digest(), "run_design_digest": manifest["design_digest"],
               "run_sources_equal_frozen": manifest["sources"] == json.loads((LANE / "me001/frozen/design.json").read_text())["sources"],
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "run": {k: manifest[k] for k in ("started_utc", "finished_utc", "wall_s", "cpu_s_total", "worker_maxrss_mb_peak",
                                                "bytes_written", "cpus", "host")},
               "checks": out}
    path = LANE / "results" / "me001_v2" / "postcheck_receipt.json"
    path.write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps({"status": receipt["status"], **{k: v["pass"] for k, v in out.items()},
                      "sources_equal_frozen": receipt["run_sources_equal_frozen"]}, indent=1))


if __name__ == "__main__":
    main()
