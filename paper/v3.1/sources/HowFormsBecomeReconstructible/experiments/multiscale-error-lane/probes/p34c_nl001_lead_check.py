"""P34c (python probes/p34c_nl001_lead_check.py ROOT): the lead's check of NL001's development numbers.
LEAD_CHECK_NOT_REGISTERED; a read of the development shards, written by the lead while NL001's debug run waited (tried on
the debug or preflight blocks first) and run after development, 29 October 2026; no simulation.

Checks the sha256 of every shard and raw file against the run's manifest, recomputes block means from the shards, and
recomputes every statement part and every number quoted in REPORT_NL001.md from the frozen registration's words (not
from nl001.predict / nl001.analyze), unrounded, printed at 4-6 decimals and rounded once in the report. Array layouts come
from each shard's own metadata (arms, reads, ends). ROOT is the stage root
(/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/nl001/development). Output: probes/results/p34c_nl001_lead_check.txt.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(sys.argv[1])
M = json.load(open(ROOT / "manifest.json"))
bad = []
for key, t in M["tasks"].items():
    for kind in ("shards", "raw"):
        f = t["files"][kind]
        if hashlib.sha256((ROOT / f["path"]).read_bytes()).hexdigest() != f["sha256"]:
            bad.append(f["path"])
print("tasks", len(M["tasks"]), "files checked", 2 * len(M["tasks"]), "sha256 mismatches", bad, "digest", M["design_digest"][:12])
print("run: %s to %s, wall %.0f s, cpu %.0f s (%.2f CPU-h), peak worker RSS %s MB, %d workers, 1-min load at start %s"
      % (M["started_utc"], M["finished_utc"], M["wall_s"], M["cpu_s_total"], M["cpu_s_total"] / 3600,
         M["worker_maxrss_mb_peak"], M["workers"], M["load_1min_start"]))

EVENTS = ("none", "F", "R", "B", "FRB", "C3", "C2", "K")
BLOCKS = list(range(*M["blocks"]))
Z, META = {}, {}
for e in EVENTS:
    for k in BLOCKS:
        with np.load(ROOT / "shards" / e / f"{k}.npz") as z:
            meta = json.loads(str(z["__meta__"]))
            Z[(e, k)] = {key.split("/", 1)[1]: z[key] for key in z.files if key != "__meta__"}
        META.setdefault(e, meta)
        assert meta["arms"] == META[e]["arms"] and len(meta["cases"]) == 8, (e, k)
        x = Z[(e, k)]["cell_err"]
        assert x.shape == (len(meta["reads"]), len(meta["arms"]), 8), (e, x.shape)
print("events", {e: len(META[e]["arms"]) for e in EVENTS}, "| reads", META["F"]["reads"], "| blocks", BLOCKS[0], "to", BLOCKS[-1], f"({len(BLOCKS)})")
H1 = len(BLOCKS) // 2


def x(arm, ev, end, read=-1):
    ai = META[ev]["arms"].index(arm)
    return np.array([Z[(ev, k)][end][read, ai].mean() for k in BLOCKS])


def ci(v):
    m, se = v.mean(), v.std(ddof=1) / np.sqrt(len(v))
    h = stats.t.ppf(0.975, len(v) - 1) * se
    return "%+.6f [%+.6f, %+.6f]" % (m, m - h, m + h)


res = {}


def part(stmt, name, items, thr, sense):
    passes = lambda m: {"ge": m >= thr, "le": m <= thr}[sense]
    dist = lambda m: {"ge": m - thr, "le": thr - m}[sense]
    ms = {key: v.mean() for key, v in items.items()}
    ok = all(passes(m) for m in ms.values())
    halves = [all(passes(v[sl].mean()) for v in items.values()) for sl in (slice(0, H1), slice(H1, None))]
    rms = np.sqrt(np.mean([v.std(ddof=1) ** 2 for v in items.values()]))
    wk = min(ms, key=lambda key: dist(ms[key]))
    sd = items[wk].std(ddof=1)
    mg = dist(ms[wk]) / max(sd, rms) if max(sd, rms) > 0 else float("inf")
    blk = sum(passes(v) for v in items[wk])
    res.setdefault(stmt, []).append(ok)
    print(f"{stmt} {name:62s} n={len(ms):2d} {min(ms.values()):+.6f} to {max(ms.values()):+.6f}; worst {wk} {ms[wk]:+.6f} "
          f"(SD {sd:.4f}, {mg:.2f} SD, {blk}/{len(BLOCKS)} blocks pass); halves {['ok' if h else 'MISS' for h in halves]}; "
          f"rule {sense} {thr}: {'ok' if ok else 'MISS'}")


BASE = ["L1", "L1L2", "L1L3", "L1L2L3", "L1L2rL3", "L1L2L3d"]
WEAK, STRONG = ["L1L2L3", "L1L2L3-k3x2", "L1L2L3-k3x3"], ["L1L2L3-k3x5", "L1L2L3-k3x6", "L1L2L3-k3x8"]
REL = ["L1L2rL3", "L1L2rL3-k3x0.25"]
print("\n== statements (t = 2,000; block means over", len(BLOCKS), "blocks)")
part("D1", "fine_ok under F >= 0.95, every base arm", {a: x(a, "F", "fine_ok") for a in BASE}, 0.95, "ge")
part("D1", "regions_ok under R >= 0.5, the arms with a region code", {a: x(a, "R", "regions_ok") for a in ["L1L2", "L1L2L3", "L1L2rL3", "L1L2L3d"]}, 0.5, "ge")
part("D1", "regions_ok under R <= 0.5, the arms without one", {a: x(a, "R", "regions_ok") for a in ["L1", "L1L3", "L1L3-k3x4", "L1L3-k3x8"]}, 0.5, "le")
part("D1", "block_ok under B <= 0.5, L1 and L1L2", {a: x(a, "B", "block_ok") for a in ["L1", "L1L2"]}, 0.5, "le")
part("D2", "cell_err under FRB <= 0.01, L1L2rL3", {"L1L2rL3": x("L1L2rL3", "FRB", "cell_err")}, 0.01, "le")
part("D2", "cell_err under FRB >= 0.05, L1 L1L3 L1L2 L1L2L3 L1L2L3d", {a: x(a, "FRB", "cell_err") for a in ["L1", "L1L3", "L1L2", "L1L2L3", "L1L2L3d"]}, 0.05, "ge")
part("C1", "cell_err under none <= 0.001, every arm run there", {a: x(a, "none", "cell_err") for a in META["none"]["arms"]}, 0.001, "le")
part("T1", "regions_ok under R >= 0.5, k2 0.75 and 1", {a: x(a, "R", "regions_ok") for a in ["L1L2-k2x0.75", "L1L2"]}, 0.5, "ge")
part("T1", "regions_ok under R <= 0.5, k2 0.25 and 0.5", {a: x(a, "R", "regions_ok") for a in ["L1L2-k2x0.25", "L1L2-k2x0.5"]}, 0.5, "le")
part("T1", "c2_ok under C2 <= 0.5, k2 0.75 and 1", {a: x(a, "C2", "c2_ok") for a in ["L1L2-k2x0.75", "L1L2"]}, 0.5, "le")
part("T1", "c2_ok under C2 >= 0.5, k2 0.25 and 0.5", {a: x(a, "C2", "c2_ok") for a in ["L1L2-k2x0.25", "L1L2-k2x0.5"]}, 0.5, "ge")
part("T2", "block_ok under B <= 0.5, block code at 1-3 KC", {a: x(a, "B", "block_ok") for a in WEAK}, 0.5, "le")
part("T2", "block_ok under B >= 0.5, block code at 5-8 KC", {a: x(a, "B", "block_ok") for a in STRONG}, 0.5, "ge")
part("T2", "block_ok under C3 >= 0.5, block code at 1-3 KC", {a: x(a, "C3", "block_ok") for a in WEAK}, 0.5, "ge")
part("T2", "block_ok under C3 <= 0.5, block code at 5-8 KC", {a: x(a, "C3", "block_ok") for a in STRONG}, 0.5, "le")
part("T3", "block_ok under B >= 0.5, strong or alone", {a: x(a, "B", "block_ok") for a in STRONG + ["L1L3-k3x4", "L1L3-k3x8"]}, 0.5, "ge")
part("T3", "bmin_ok under B <= 0.5, strong or alone", {a: x(a, "B", "bmin_ok") for a in STRONG + ["L1L3-k3x4", "L1L3-k3x8"]}, 0.5, "le")
part("T4", "block_ok and bmin_ok under B >= 0.5, relative", {(a, e): x(a, "B", e) for a in REL for e in ("block_ok", "bmin_ok")}, 0.5, "ge")
part("T4", "block_ok and bmin_ok under C3 <= 0.5, relative", {(a, e): x(a, "C3", e) for a in REL for e in ("block_ok", "bmin_ok")}, 0.5, "le")
part("T5", "derived block code: block_ok under B <= 0.5", {"L1L2L3d": x("L1L2L3d", "B", "block_ok")}, 0.5, "le")
part("T5", "derived block code: block_ok under C3 >= 0.5", {"L1L2L3d": x("L1L2L3d", "C3", "block_ok")}, 0.5, "ge")
part("K1", "kill_min_ok without minus with a block code >= 0.15", {
    "L1 - L1L3": x("L1", "K", "kill_min_ok") - x("L1L3", "K", "kill_min_ok"),
    "L1L2 - L1L2L3": x("L1L2", "K", "kill_min_ok") - x("L1L2L3", "K", "kill_min_ok"),
    "L1L2 - L1L2rL3": x("L1L2", "K", "kill_min_ok") - x("L1L2rL3", "K", "kill_min_ok")}, 0.15, "ge")
print("\nverdicts:", {k: ("HOLDS" if all(v) else "FAILS") for k, v in res.items()})

print("\n== reported, not registered")
print("   strong absolute hierarchy under FRB, cell_err:", " ".join(f"{a} {x(a, 'FRB', 'cell_err').mean():.6f}" for a in STRONG + ["L1L2L3-k3x4"]),
      "| relative", "%.6f" % x("L1L2rL3", "FRB", "cell_err").mean())
print("   ... and their region_err / block_err:", " ".join(f"{a} {x(a, 'FRB', 'region_err').mean():.4f}/{x(a, 'FRB', 'block_err').mean():.4f}" for a in STRONG))
print("   the block code at 4 KC: block_ok under B %s; under C3 %s" % (ci(x("L1L2L3-k3x4", "B", "block_ok")), ci(x("L1L2L3-k3x4", "C3", "block_ok"))))
print("   kill wound, by arm: kill_ok / kill_reg_ok / kill_min_ok:", " ".join(f"{a} {x(a, 'K', 'kill_ok').mean():.4f}/{x(a, 'K', 'kill_reg_ok').mean():.4f}/{x(a, 'K', 'kill_min_ok').mean():.4f}" for a in BASE))
print("   kill_ok with minus without a block code:", "L1L3 - L1", ci(x("L1L3", "K", "kill_ok") - x("L1", "K", "kill_ok")), "| L1L2L3 - L1L2", ci(x("L1L2L3", "K", "kill_ok") - x("L1L2", "K", "kill_ok")))
print("   K1 intervals:", "L1 - L1L3", ci(x("L1", "K", "kill_min_ok") - x("L1L3", "K", "kill_min_ok")), "| L1L2 - L1L2L3", ci(x("L1L2", "K", "kill_min_ok") - x("L1L2L3", "K", "kill_min_ok")),
      "| L1L2 - L1L2rL3", ci(x("L1L2", "K", "kill_min_ok") - x("L1L2rL3", "K", "kill_min_ok")))
print("   cell_err under FRB by base arm:", " ".join(f"{a} {x(a, 'FRB', 'cell_err').mean():.6f}" for a in BASE))
print("   the error's energy by band under FRB (fine / regional / block / sheet):")
for a in BASE + STRONG:
    print(f"     {a:14s}", " / ".join("%.6f" % x(a, "FRB", e).mean() for e in ("e_fine", "e_regional", "e_block", "e_sheet")))
print("   events one at a time, cell_err by base arm:")
for ev in ("F", "R", "B", "C2", "C3", "K"):
    print(f"     {ev:4s}", " ".join(f"{a} {x(a, ev, 'cell_err').mean():.4f}" for a in BASE if a in META[ev]["arms"]))
print("   minority cells and regions kept under none and F (min_cell_ok, min_region_ok):",
      " ".join(f"{a} {x(a, 'F', 'min_cell_ok').mean():.4f}/{x(a, 'F', 'min_region_ok').mean():.4f}" for a in BASE))
print("done")
