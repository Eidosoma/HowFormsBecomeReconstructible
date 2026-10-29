"""P31c (python probes/p31c_np001_lead_check.py ROOT): the lead's check of NP001's development numbers.
LEAD_CHECK_NOT_REGISTERED; a read of the development shards, written by the lead while development ran (tried on the
preflight blocks first) and run after it, 29 October 2026; no simulation.

Checks the sha256 of every shard and raw file against the run's manifest, recomputes block means from the shards, and
recomputes every statement part and every number quoted in REPORT_NP001.md from the registration's words (not from
np001.predict / np001.analyze), unrounded, printed at 4-6 decimals and rounded once in the report. Array layouts come
from each shard's own metadata (conds, branches2); nothing is imported from the lane. ROOT is the stage root
(/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/np001/development). Output: probes/results/p31c_np001_lead_check.txt.
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

BODIES = ["dw", "li2", "li4", "li16"]
IMP, PER = ["li2", "li4"], ["dw", "li16"]
S4X = ["S4", "S4s1", "S4s2", "S4s3"]
CON = {"C4s1": 1, "C4s2": 2, "C4s3": 3}
UNITS = S4X + ["S8", "F0"] + list(CON)
BLOCKS = list(range(*M["blocks"]))
assert len(M["tasks"]) == len(BODIES) * len(UNITS) * len(BLOCKS), len(M["tasks"])
Z, C1, C2 = {}, None, None
for b in BODIES:
    for u in UNITS:
        for k in BLOCKS:
            with np.load(ROOT / "shards" / b / u / f"{k}.npz") as z:
                meta = json.loads(str(z["__meta__"]))
                Z[(b, u, k)] = {key: z[key] for key in z.files if key != "__meta__"}
            C1 = C1 or meta["conds"]
            C2 = C2 or meta["branches2"]
            assert meta["conds"] == C1 and meta["branches2"] == C2 and len(meta["cases"]) == 8, (b, u, k)
print("stage-1 conditions", C1, "| stage-2 branches", C2, "| blocks", BLOCKS[0], "to", BLOCKS[-1], f"({len(BLOCKS)})")
H1 = len(BLOCKS) // 2


def s1(b, u, cond, e, read=-1):
    """Block means (over the 8 cases) of a stage-1 endpoint; read -1 is t = 4,000."""
    return np.array([Z[(b, u, k)][f"s1/{e}"][read, C1.index(cond)].mean() for k in BLOCKS])


def s2(b, u, succ, rec, e, read=-1):
    """Block means of a successor endpoint: successor `succ` reading stage-1 body b's record `rec`; read -1 is t = 2,000."""
    return np.array([Z[(b, u, k)][f"s2/{succ}/{e}"][read, C2.index(rec)].mean() for k in BLOCKS])


def q1(b, u, cond, rec=False, read=-1):
    a, ab = ("r_align", "r_align_b") if rec else ("align", "align_b")
    return (s1(b, u, cond, a, read) - s1(b, u, cond, ab, read)) / (CON[u] / 4)


def q2(b, u, succ, rec, read=-1):
    return (s2(b, u, succ, rec, "align", read) - s2(b, u, succ, rec, "align_b", read)) / (CON[u] / 4)


def ci(x):
    m, se = x.mean(), x.std(ddof=1) / np.sqrt(len(x))
    h = stats.t.ppf(0.975, len(x) - 1) * se
    return "%+.6f [%+.6f, %+.6f]" % (m, m - h, m + h)


print("\n== aliases on these blocks (the registration's 'by construction'; Q5 checked them on the preflight blocks)")
al = []
for u in UNITS:
    for k in BLOCKS:
        for c in ("intact", "record1"):
            ref = Z[("dw", u, k)]["s1/r_align"][:, C1.index(c)]
            al.append(all(np.array_equal(ref, Z[(b, u, k)]["s1/r_align"][:, C1.index(c)]) for b in BODIES))
        for s in BODIES:
            for c in ("intact", "record1", "none"):
                ref = Z[("dw", u, k)][f"s2/{s}/align"][:, C2.index(c)]
                al.append(all(np.array_equal(ref, Z[(b, u, k)][f"s2/{s}/align"][:, C2.index(c)]) for b in BODIES))
        ref = Z[("dw", u, k)]["s1/r_align"][:, C1.index("alone")]
        al.append(all(np.array_equal(Z[(b, u, k)]["s1/r_align"][:, C1.index("alone")], Z[(b, u, k)]["s1/r_align"][:, C1.index("intact")]) for b in BODIES))
print(f"{len(al)} alias groups (records no body writes, their successors, the controls; alone's record = intact's): "
      f"{sum(al)} identical across the four stage-1 bodies")

res = {}


def part(stmt, name, items, thr, sense):
    """An every-item part (a dict of per-block arrays) or a pooled part (one array): every item's block mean passes."""
    if isinstance(items, np.ndarray):
        items = {"pooled": items}
    passes = lambda m: {"ge": m >= thr, "le": m <= thr, "abs": abs(m) <= thr}[sense]
    dist = lambda m: {"ge": m - thr, "le": thr - m, "abs": thr - abs(m)}[sense]
    ms = {key: x.mean() for key, x in items.items()}
    ok = all(passes(m) for m in ms.values())
    halves = [all(passes(x[sl].mean()) for x in items.values()) for sl in (slice(0, H1), slice(H1, None))]
    rms = np.sqrt(np.mean([x.std(ddof=1) ** 2 for x in items.values()]))
    wk = min(ms, key=lambda key: dist(ms[key]))
    sd = items[wk].std(ddof=1)
    mg = dist(ms[wk]) / max(sd, rms) if max(sd, rms) > 0 else float("inf")
    blk = sum(passes(v) for v in items[wk])
    res.setdefault(stmt, []).append(ok)
    print(f"{stmt} {name:58s} n={len(ms):2d} {min(ms.values()):+.6f} to {max(ms.values()):+.6f}; worst {wk} "
          f"{ms[wk]:+.6f} (SD {sd:.4f}, {mg:.2f} SD from the bound, {blk}/{len(BLOCKS)} blocks pass); "
          f"halves {['ok' if h else 'MISS' for h in halves]}; rule {sense} {thr}: {'ok' if ok else 'MISS'}")
    return ms


print("\n== statements (t = 4,000 in stage 1, t = 2,000 in stage 2; block means over", len(BLOCKS), "blocks)")
part("N1", "alone align, li2 and li4, S8 and F0 <= 0.7", {(b, u): s1(b, u, "alone", "align") for b in IMP for u in ("S8", "F0")}, 0.7, "le")
part("N1", "alone align, li2 and li4, S4x >= 0.95", {(b, u): s1(b, u, "alone", "align") for b in IMP for u in S4X}, 0.95, "ge")
part("N1", "alone align, dw and li16, S8 and F0 >= 0.95", {(b, u): s1(b, u, "alone", "align") for b in PER for u in ("S8", "F0")}, 0.95, "ge")
part("N2", "body r_align, li2 li4 dw, S4x >= 0.95", {(b, u): s1(b, u, "body", "r_align") for b in ("li2", "li4", "dw") for u in S4X}, 0.95, "ge")
part("N2", "align body - alone, li2 and li4, S4x, |x| <= 0.02", {(b, u): s1(b, u, "body", "align") - s1(b, u, "alone", "align") for b in IMP for u in S4X}, 0.02, "abs")
part("N3", "r_align body and body3, li2 and li4, S8 and F0 <= 0.7", {(b, c, u): s1(b, u, c, "r_align") for b in IMP for c in ("body", "body3") for u in ("S8", "F0")}, 0.7, "le")
part("N3", "r_align body, dw and li16, S8 and F0 >= 0.95", {(b, u): s1(b, u, "body", "r_align") for b in PER for u in ("S8", "F0")}, 0.95, "ge")
part("N4", "r_align intact and record1, S8 and F0 >= 0.97 (every body)", {(b, c, u): s1(b, u, c, "r_align") for b in BODIES for c in ("intact", "record1") for u in ("S8", "F0")}, 0.97, "ge")
part("N4", "align intact/record1 - alone, li2 and li4, S8 and F0 >= 0.2", {(b, c, u): s1(b, u, c, "align") - s1(b, u, "alone", "align") for b in IMP for c in ("intact", "record1") for u in ("S8", "F0")}, 0.2, "ge")
part("N5", "successors of the intact S4x records >= 0.95", {(b, s, u): s2(b, u, s, "intact", "align") for b in BODIES for s in BODIES for u in S4X}, 0.95, "ge")
ctrl = np.mean([s2(b, u, s, "none", "align") for b in BODIES for s in BODIES for u in S4X], 0)
part("N5", "no-record control align - 0.5, pooled over successors and S4x", ctrl - 0.5, 0.1, "abs")
part("N5", "successors of the body S4x records >= 0.85", {(b, s, u): s2(b, u, s, "body", "align") for b in BODIES for s in BODIES for u in S4X}, 0.85, "ge")
part("N6", "successors of li2's and li4's body S8 and F0 records <= 0.7", {(b, s, u): s2(b, u, s, "body", "align") for b in IMP for s in BODIES for u in ("S8", "F0")}, 0.7, "le")
part("N6", "dw successor of the intact and record1 S8 and F0 records >= 0.95", {(b, c, u): s2(b, u, "dw", c, "align") for b in BODIES for c in ("intact", "record1") for u in ("S8", "F0")}, 0.95, "ge")
part("N6", "dw successor of dw's and li16's body S8 and F0 records >= 0.9", {(b, u): s2(b, u, "dw", "body", "align") for b in PER for u in ("S8", "F0")}, 0.9, "ge")
part("N7", "dw - li4 successor, the intact F0 record >= 0.1", {b: s2(b, "F0", "dw", "intact", "align") - s2(b, "F0", "li4", "intact", "align") for b in BODIES}, 0.1, "ge")
part("N7", "dw - li4 successor, dw's and li16's body S8 and F0 >= 0.1", {(b, u): s2(b, u, "dw", "body", "align") - s2(b, u, "li4", "body", "align") for b in PER for u in ("S8", "F0")}, 0.1, "ge")
part("N7", "dw - li2 successor, dw's and li16's body S8 and F0 >= 0.05", {(b, u): s2(b, u, "dw", "body", "align") - s2(b, u, "li2", "body", "align") for b in PER for u in ("S8", "F0")}, 0.05, "ge")
part("N8", "q alone <= -0.5", {(b, u): q1(b, u, "alone") for b in BODIES for u in CON}, -0.5, "le")
part("N8", "q intact and body >= 0.5", {(b, c, u): q1(b, u, c) for b in BODIES for c in ("intact", "body") for u in CON}, 0.5, "ge")
part("N8", "the record's q under body >= 0.5", {(b, u): q1(b, u, "body", rec=True) for b in BODIES for u in CON}, 0.5, "ge")
part("N9", "successors of the intact conflict records, align >= 0.95", {(b, s, u): s2(b, u, s, "intact", "align") for b in BODIES for s in BODIES for u in CON}, 0.95, "ge")
part("N9", "successors of the body conflict records, q >= 0.5", {(b, s, u): q2(b, u, s, "body") for b in BODIES for s in BODIES for u in CON}, 0.5, "ge")
print("\nverdicts:", {k: ("HOLDS" if all(x) else "FAILS") for k, x in res.items()})

print("\n== reported, not registered")
part("rep", "q body3 (conflicts)", {(b, u): q1(b, u, "body3") for b in BODIES for u in CON}, 0.5, "ge")
part("rep", "the record's q under body3 (conflicts)", {(b, u): q1(b, u, "body3", rec=True) for b in BODIES for u in CON}, 0.5, "ge")
for s in ("li2", "li4"):
    print(f"   {s} successor reading the intact F0 record (dw's run): {s2('dw', 'F0', s, 'intact', 'align').mean():.6f}; "
          f"dw successor {s2('dw', 'F0', 'dw', 'intact', 'align').mean():.6f}")
for b in BODIES:
    print(f"   stage 1, {b} reading the intact F0 record: align {s1(b, 'F0', 'intact', 'align').mean():.6f}; alone {s1(b, 'F0', 'alone', 'align').mean():.6f}")

print("\n== stage 1 at t = 4,000: align | r_align | shape | spacing, by unit and body (rows) and condition (columns)")
for u in UNITS:
    print(f"-- {u}")
    for b in BODIES:
        print(f"   {b:5s}", "  ".join(f"{c} {s1(b, u, c, 'align').mean():.4f}|{s1(b, u, c, 'r_align').mean():.4f}|"
                                    f"{s1(b, u, c, 'shape').mean():.4f}|{s1(b, u, c, 'spacing').mean():5.2f}" for c in C1))
print("\n== stage 2 at t = 2,000: successor align reading each record (columns), by unit, stage-1 body and successor")
for u in UNITS:
    print(f"-- {u}")
    for b in BODIES:
        for s in BODIES:
            print(f"   {b:5s}> {s:5s}", "  ".join(f"{c} {s2(b, u, s, c, 'align').mean():.4f}" for c in C2),
                  "| spacing none %.2f intact %.2f" % (s2(b, u, s, "none", "spacing").mean(), s2(b, u, s, "intact", "spacing").mean()))

print("\n== native preferences (alone at t = 4,000; newborns reading nothing at t = 2,000)")
for b in BODIES:
    s4 = [s1(b, u, "alone", "align").mean() for u in S4X]
    print(f"   {b:5s} S4x {min(s4):.4f} to {max(s4):.4f}; S8 {s1(b, 'S8', 'alone', 'align').mean():.4f}; F0 {s1(b, 'F0', 'alone', 'align').mean():.4f}"
          f" | shape S8 {s1(b, 'S8', 'alone', 'shape').mean():.4f} F0 {s1(b, 'F0', 'alone', 'shape').mean():.4f}; spacing S8 {s1(b, 'S8', 'alone', 'spacing').mean():.2f}"
          f" | newborn alone: align over S4x {np.mean([s2('dw', u, b, 'none', 'align').mean() for u in S4X]):.4f}, spacing {np.mean([s2('dw', u, b, 'none', 'spacing').mean() for u in UNITS]):.2f}")
print("   pooled no-record control (N5):", ci(ctrl))

print("\n== the pull (N4) and the 0.97 (N2), with 95% intervals over blocks")
for b in IMP:
    for u in ("S8", "F0"):
        print(f"   {b} {u}: alone {s1(b, u, 'alone', 'align').mean():.4f}; reading intact {ci(s1(b, u, 'intact', 'align') - s1(b, u, 'alone', 'align'))};"
              f" record1 {ci(s1(b, u, 'record1', 'align') - s1(b, u, 'alone', 'align'))}; body {ci(s1(b, u, 'body', 'align') - s1(b, u, 'alone', 'align'))}")
for b in BODIES:
    print(f"   {b} S4 under body: r_align {s1(b, 'S4', 'body', 'r_align').mean():.4f}, align {s1(b, 'S4', 'body', 'align').mean():.4f};"
          f" S4x r_align {min(s1(b, u, 'body', 'r_align').mean() for u in S4X):.4f} to {max(s1(b, u, 'body', 'r_align').mean() for u in S4X):.4f}")

print("\n== records by condition (r_align at t = 4,000; S8 and F0)")
for b in BODIES:
    print(f"   {b:5s}", "  ".join(f"{c} S8 {s1(b, 'S8', c, 'r_align').mean():.4f} F0 {s1(b, 'F0', c, 'r_align').mean():.4f}" for c in C1[1:]))

print("\n== phase conflicts: q by condition at t = 1,000 / 2,000 / 4,000 (body | record)")
for u in CON:
    for b in BODIES:
        print(f"   {u} {b:5s}", "  ".join(f"{c} " + "/".join("%+.3f" % q1(b, u, c, read=r).mean() for r in range(3))
                                       + " | " + "/".join("%+.3f" % q1(b, u, c, rec=True, read=r).mean() for r in range(3)) for c in C1))
for c in C1:
    qs = [q1(b, u, c).mean() for b in BODIES for u in CON]
    qr = [q1(b, u, c, rec=True).mean() for b in BODIES for u in CON]
    print(f"   {c:7s} body q {min(qs):+.4f} to {max(qs):+.4f}; record q {min(qr):+.4f} to {max(qr):+.4f}")
print("   successors at t = 2,000, q reading each record (min to max over stage-1 bodies, successors and conflicts):")
for c in C2:
    qs = [q2(b, u, s, c).mean() for b in BODIES for s in BODIES for u in CON]
    al_ = [s2(b, u, s, c, "align").mean() for b in BODIES for s in BODIES for u in CON]
    print(f"   {c:7s} q {min(qs):+.4f} to {max(qs):+.4f} (mean {np.mean(qs):+.4f}); align {min(al_):.4f} to {max(al_):.4f}")

print("\n== further numbers quoted in the report")
for s in BODIES:
    print(f"   newborn {s:5s} reading nothing, S4x: align " + " ".join("%.4f" % s2('dw', u, s, 'none', 'align').mean() for u in S4X)
          + " | shape " + " ".join("%.4f" % s2('dw', u, s, 'none', 'shape').mean() for u in S4X)
          + " | spacing %.2f" % s2('dw', 'S4', s, 'none', 'spacing').mean())
for b in IMP:
    for u in ("S8", "F0"):
        print(f"   {b} {u} body1: r_align at 1,000/2,000/4,000 " + "/".join("%.4f" % s1(b, u, "body1", "r_align", r).mean() for r in range(3))
              + "; body align " + "/".join("%.4f" % s1(b, u, "body1", "align", r).mean() for r in range(3))
              + " | body: r_align " + "/".join("%.4f" % s1(b, u, "body", "r_align", r).mean() for r in range(3)))
for s in BODIES:
    v = [s2(b, u, s, "body", "align").mean() for b in PER for u in ("S8", "F0")]
    w = [s2(b, u, s, "body3", "align").mean() for b in BODIES for u in S4X]
    print(f"   newborn {s:5s}: reading dw's and li16's body S8/F0 records {min(v):.6f} to {max(v):.6f}; reading body3 S4x records {min(w):.6f} to {max(w):.6f};"
          f" reading the intact S8 record {s2('dw', 'S8', s, 'intact', 'align').mean():.6f}, F0 {s2('dw', 'F0', s, 'intact', 'align').mean():.6f}")
print("   N7 intervals: dw - li4, intact F0", ci(s2("dw", "F0", "dw", "intact", "align") - s2("dw", "F0", "li4", "intact", "align")))
for b in PER:
    for u in ("S8", "F0"):
        print(f"   N7 {b} body {u}: dw - li4 {ci(s2(b, u, 'dw', 'body', 'align') - s2(b, u, 'li4', 'body', 'align'))}; dw - li2 {ci(s2(b, u, 'dw', 'body', 'align') - s2(b, u, 'li2', 'body', 'align'))}")
for b in IMP:
    print(f"   {b} record under body1 vs body, S8: {s1(b, 'S8', 'body1', 'r_align').mean():.4f} / {s1(b, 'S8', 'body', 'r_align').mean():.4f}; "
          f"F0: {s1(b, 'F0', 'body1', 'r_align').mean():.4f} / {s1(b, 'F0', 'body', 'r_align').mean():.4f}")
print("   conflicts, the record's q under body at t = 1,000 (min to max):",
      "%+.6f to %+.6f" % (min(q1(b, u, "body", rec=True, read=0).mean() for b in BODIES for u in CON), max(q1(b, u, "body", rec=True, read=0).mean() for b in BODIES for u in CON)),
      "| the body's q under intact and body at t = 1,000: %+.6f to %+.6f" % (min(q1(b, u, c, read=0).mean() for b in BODIES for u in CON for c in ("intact", "body")),
                                                                         max(q1(b, u, c, read=0).mean() for b in BODIES for u in CON for c in ("intact", "body"))))
print("   conflicts under alone, li2 and li4: align (record's phase) and shape (any translation) at t = 4,000:",
      "; ".join(f"{b} {u} {s1(b, u, 'alone', 'align').mean():.4f}/{s1(b, u, 'alone', 'shape').mean():.4f}" for b in IMP for u in CON))
print("done")
