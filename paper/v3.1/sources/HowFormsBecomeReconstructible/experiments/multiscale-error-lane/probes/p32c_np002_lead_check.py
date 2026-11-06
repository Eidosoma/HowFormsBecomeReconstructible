"""P32c (python probes/p32c_np002_lead_check.py ROOT): the lead's check of NP002's development numbers.
LEAD_CHECK_NOT_REGISTERED; a read of the development shards, written by the lead while NP002's preflight ran (tried on
the preflight blocks first) and run after development, 29 October 2026; no simulation.

Checks the sha256 of every shard and raw file against the run's manifest, recomputes block means from the shards, and
recomputes every statement part and every number quoted in REPORT_NP002.md from the frozen registration's words (not
from np002.predict / np002.analyze), unrounded, printed at 4-6 decimals and rounded once in the report. Array layouts
come from each shard's own metadata (conds, branches2); the templates' agreements a0 (signs) and b0 (relations) are the
registration's table. ROOT is the stage root (/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/np002/development).
Output: probes/results/p32c_np002_lead_check.txt.
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

BODIES, IMP, PER = ["dw", "li2", "li4", "li16"], ["li2", "li4"], ["dw", "li16"]
PHASE, SPACING = ["C4s1", "C4s2", "C4s3"], ["C84", "C48"]
A0 = {"C4s1": 0.75, "C4s2": 0.5, "C4s3": 0.25, "C84": 0.5, "C48": 0.5}
B0 = {"C4s1": 0.75, "C4s2": 0.75, "C4s3": 0.75, "C84": 0.9375, "C48": 0.9375}
GAINS = ["0.2", "0.1", "0.05", "0.02", "0.01", "0.005"]
BLOCKS = list(range(*M["blocks"]))
assert len(M["tasks"]) == len(BODIES) * 5 * len(BLOCKS), len(M["tasks"])
Z, C1, C2 = {}, None, None
for b in BODIES:
    for u in PHASE + SPACING:
        for k in BLOCKS:
            with np.load(ROOT / "shards" / b / u / f"{k}.npz") as z:
                meta = json.loads(str(z["__meta__"]))
                Z[(b, u, k)] = {key: z[key] for key in z.files if key != "__meta__"}
            C1 = C1 or meta["conds"]
            if u in SPACING:
                C2 = C2 or meta["branches2"]
                assert meta["branches2"] == C2
            assert meta["conds"] == C1 and len(meta["cases"]) == 8, (b, u, k)
print("stage-1 conditions", C1, "| stage-2 branches", C2, "| blocks", BLOCKS[0], "to", BLOCKS[-1], f"({len(BLOCKS)})")
H1 = len(BLOCKS) // 2


def cname(c, g):
    return c if g == "0.2" else f"{c}@{g}"


def s1(b, u, c, e, read=-1):
    return np.array([Z[(b, u, k)][f"s1/{e}"][read, C1.index(c)].mean() for k in BLOCKS])


def s2(b, u, s, c, e, read=-1):
    return np.array([Z[(b, u, k)][f"s2/{s}/{e}"][read, C2.index(c)].mean() for k in BLOCKS])


def q(b, u, c, read=-1):
    """The body's signed preference: +1 at the record's pattern, -1 at the body's initial one."""
    return (s1(b, u, c, "align", read) - s1(b, u, c, "align_b", read)) / (1 - A0[u])


def qabs(b, u, c, read=-1):
    """The body's inversion-invariant preference (reported only)."""
    return (s1(b, u, c, "abs", read) - s1(b, u, c, "abs_b", read)) / (1 - abs(2 * A0[u] - 1))


def qrel(b, u, c, read=-1):
    """The record's inversion-invariant preference, from the per-case |2a - 1| (r_abs, r_abs_b)."""
    return (s1(b, u, c, "r_abs", read) - s1(b, u, c, "r_abs_b", read)) / (1 - abs(2 * A0[u] - 1))


def qbond(b, u, c):
    """The record's bonds at the last read: (bond_b - bond_err) / (1 - b0) (reported only)."""
    return (s1(b, u, c, "bond_b", 0) - s1(b, u, c, "bond_err")) / (1 - B0[u])


def q2(b, u, s, c, read=-1):
    return (s2(b, u, s, c, "align", read) - s2(b, u, s, c, "align_b", read)) / (1 - A0[u])


def ci(x):
    m, se = x.mean(), x.std(ddof=1) / np.sqrt(len(x))
    h = stats.t.ppf(0.975, len(x) - 1) * se
    return "%+.6f [%+.6f, %+.6f]" % (m, m - h, m + h)


print("\n== aliases on these blocks (the registration's 'by construction'; Q5 checked them on the preflight blocks)")
al = []
for u in PHASE + SPACING:
    for k in BLOCKS:
        for c in ["alone", "intact", "record1"] + [f"intact@{g}" for g in GAINS[1:]]:
            ref = Z[("dw", u, k)]["s1/r_align"][:, C1.index(c)]
            al.append(all(np.array_equal(ref, Z[(b, u, k)]["s1/r_align"][:, C1.index(c)]) for b in BODIES))
        if u in SPACING:
            for s in BODIES:
                for c in ("intact", "record1", "none"):
                    ref = Z[("dw", u, k)][f"s2/{s}/align"][:, C2.index(c)]
                    al.append(all(np.array_equal(ref, Z[(b, u, k)][f"s2/{s}/align"][:, C2.index(c)]) for b in BODIES))
print(f"{len(al)} alias groups: {sum(al)} identical across the four stage-1 bodies")

res = {}


def part(stmt, name, items, thr, sense):
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
    print(f"{stmt} {name:60s} n={len(ms):2d} {min(ms.values()):+.6f} to {max(ms.values()):+.6f}; worst {wk} "
          f"{ms[wk]:+.6f} (SD {sd:.4f}, {mg:.2f} SD from the bound, {blk}/{len(BLOCKS)} blocks pass); "
          f"halves {['ok' if h else 'MISS' for h in halves]}; rule {sense} {thr}: {'ok' if ok else 'MISS'}")


print("\n== statements (t = 4,000 in stage 1, t = 2,000 in stage 2; block means over", len(BLOCKS), "blocks)")
part("R1", "q intact@0.02 >= 0.5, li2 li4", {(b, u): q(b, u, "intact@0.02") for b in IMP for u in PHASE}, 0.5, "ge")
part("R1", "q intact@0.05 >= 0.25, dw li16", {(b, u): q(b, u, "intact@0.05") for b in PER for u in PHASE}, 0.25, "ge")
part("R2", "q intact@0.005 <= -0.5, li2 li4", {(b, u): q(b, u, "intact@0.005") for b in IMP for u in PHASE}, -0.5, "le")
part("R2", "q intact@0.005 <= -0.25, dw li16", {(b, u): q(b, u, "intact@0.005") for b in PER for u in PHASE}, -0.25, "le")
part("R3", "q body (0.2) >= 0.5, every body", {(b, u): q(b, u, "body") for b in BODIES for u in PHASE}, 0.5, "ge")
part("R3", "q body@0.02 <= -0.5, li2 li4", {(b, u): q(b, u, "body@0.02") for b in IMP for u in PHASE}, -0.5, "le")
part("R3", "q body@0.02 <= -0.25, dw li16", {(b, u): q(b, u, "body@0.02") for b in PER for u in PHASE}, -0.25, "le")
part("R4", "q intact@0.02 - q body@0.02 >= 1.0, li2 li4", {(b, u): q(b, u, "intact@0.02") - q(b, u, "body@0.02") for b in IMP for u in PHASE}, 1.0, "ge")
part("R4", "q intact@0.05 - q body@0.05 >= 0.25, dw li16", {(b, u): q(b, u, "intact@0.05") - q(b, u, "body@0.05") for b in PER for u in PHASE}, 0.25, "ge")
part("R5", "record q_rel body (0.2) >= 0.5, every body", {(b, u): qrel(b, u, "body") for b in BODIES for u in PHASE}, 0.5, "ge")
part("R5", "record q_rel body@0.02 <= 0, every body", {(b, u): qrel(b, u, "body@0.02") for b in BODIES for u in PHASE}, 0.0, "le")
part("S1", "q alone <= -0.5, li2 li4 in C48, dw li16 in C84", {**{(b, "C48"): q(b, "C48", "alone") for b in IMP}, **{(b, "C84"): q(b, "C84", "alone") for b in PER}}, -0.5, "le")
part("S2", "align intact >= 0.95, every body in C84 and C48", {(b, u): s1(b, u, "intact", "align") for b in BODIES for u in SPACING}, 0.95, "ge")
part("S2", "newborn align reading intact >= 0.95 (dw's run; aliases)", {(s, u): s2("dw", u, s, "intact", "align") for s in BODIES for u in SPACING}, 0.95, "ge")
part("S2", "q record1 >= 0.5, every body in C84 and C48", {(b, u): q(b, u, "record1") for b in BODIES for u in SPACING}, 0.5, "ge")
held = {**{(b, "C48"): q(b, "C48", "body") for b in IMP}, **{(b, "C84"): q(b, "C84", "body") for b in PER}}
other = {**{(b, "C84"): q(b, "C84", "body") for b in IMP}, **{(b, "C48"): q(b, "C48", "body") for b in PER}}
part("S3", "q body <= 0.5, the held conflicts", held, 0.5, "le")
part("S3", "q body >= 0.5, the other conflicts", other, 0.5, "ge")
part("S3", "mean phase q(body) - held spacing q(body) >= 0.3", {k: np.mean([q(k[0], u, "body") for u in PHASE], 0) - v for k, v in held.items()}, 0.3, "ge")
part("S4", "newborn q reading the held conflicts' body records <= 0.5", {(b, u, s): q2(b, u, s, "body") for (b, u) in held for s in BODIES}, 0.5, "le")
part("S4", "newborn q reading the other conflicts' body records >= 0.5", {(b, u, s): q2(b, u, s, "body") for (b, u) in other for s in BODIES}, 0.5, "ge")
print("\nverdicts:", {k: ("HOLDS" if all(x) else "FAILS") for k, x in res.items()})

print("\n== the race (phase conflicts): body q at t = 4,000, range over K = 1-3 [and the mean], by gain")
for b in BODIES:
    for c in ("intact", "body"):
        row = []
        for g in GAINS:
            v = [q(b, u, cname(c, g)).mean() for u in PHASE]
            row.append(f"{g}: {min(v):+.3f} to {max(v):+.3f}")
        print(f"   {b:5s} {c:6s}", " | ".join(row))
print("   the record's q_rel under body@g, range over K (and every body):")
for b in BODIES:
    print(f"   {b:5s}", " | ".join(f"{g}: " + "%+.3f to %+.3f" % (min(qrel(b, u, cname('body', g)).mean() for u in PHASE), max(qrel(b, u, cname('body', g)).mean() for u in PHASE)) for g in GAINS))
print("   the record's q_bond under body@g at 4,000 (reported):")
for b in BODIES:
    print(f"   {b:5s}", " | ".join(f"{g}: " + "%+.3f to %+.3f" % (min(qbond(b, u, cname('body', g)).mean() for u in PHASE), max(qbond(b, u, cname('body', g)).mean() for u in PHASE)) for g in GAINS))
print("   time course, body q at 1,000 / 2,000 / 4,000, every body and K:")
for c in ("intact@0.02", "intact@0.01", "body", "body@0.1", "body@0.05", "body@0.02"):
    print(f"   {c:12s}", " ".join(f"{b}:" + "/".join("%+.2f" % np.mean([q(b, u, c, r).mean() for u in PHASE]) for r in range(3)) for b in BODIES))

print("\n== the spacing conflicts: body q at t = 4,000 by condition, and the record's q_rel and q_bond under body")
for u in SPACING:
    for b in BODIES:
        print(f"   {u} {b:5s}", "  ".join(f"{c} {q(b, u, c).mean():+.3f}" for c in ("alone", "intact", "body1", "record1", "body", "body3")),
              f"| race intact@g: " + " ".join(f"{g}:{q(b, u, cname('intact', g)).mean():+.2f}" for g in GAINS[1:]),
              f"| body@g: " + " ".join(f"{g}:{q(b, u, cname('body', g)).mean():+.2f}" for g in GAINS[1:]),
              f"| record q_rel body {qrel(b, u, 'body').mean():+.3f}, q_bond body {qbond(b, u, 'body').mean():+.3f}")
print("   spacing (the body's wavelength) under alone / intact / body:")
for u in SPACING:
    print(f"   {u}", " ".join(f"{b} {s1(b, u, 'alone', 'spacing').mean():.1f}/{s1(b, u, 'intact', 'spacing').mean():.1f}/{s1(b, u, 'body', 'spacing').mean():.1f}" for b in BODIES))
print("   the record at low gain where the body kept its period (reported): q_rel and q_bond under body@0.02 and body@0.005")
for (b, u) in list(held) + [(b, u) for (b, u) in other]:
    print(f"   {b:5s} {u}: body q {q(b, u, 'body@0.02').mean():+.3f}/{q(b, u, 'body@0.005').mean():+.3f}; q_rel {qrel(b, u, 'body@0.02').mean():+.3f}/{qrel(b, u, 'body@0.005').mean():+.3f}; q_bond {qbond(b, u, 'body@0.02').mean():+.3f}/{qbond(b, u, 'body@0.005').mean():+.3f}")

print("\n== newborns (spacing conflicts) at t = 2,000: q reading each stage-1 body's record, range over the four kinds")
for u in SPACING:
    for b in BODIES:
        print(f"   {u} {b:5s}", "  ".join(f"{c} " + "%+.3f to %+.3f" % (min(q2(b, u, s, c).mean() for s in BODIES), max(q2(b, u, s, c).mean() for s in BODIES)) for c in C2))
print("   newborns reading nothing: align", " ".join(f"{u}/{s} {s2('dw', u, s, 'none', 'align').mean():.3f}" for u in SPACING for s in BODIES))

print("\n== checks on the measures")
inv, ncase = {}, 0
for (b, u, k), z in Z.items():
    al, ab = z["s1/align"][-1], z["s1/align_b"][-1]             # per case at t = 4,000
    for ci, c in enumerate(C1):
        ncase += al.shape[1]
        h = int(((al[ci] < 0.15) | (ab[ci] < 0.15)).sum())     # a body within 0.15 of a template's inverse
        if h:
            inv[(b, u, c)] = inv.get((b, u, c), 0) + h
print(f"   bodies within 0.15 of a template's inverse (align or align_b < 0.15, per case at 4,000): {sum(inv.values())} of {ncase}: {inv}")
print("   (|q - q_abs| at the block level is not an inversion test: the two differ for mixed bodies; largest %.3f)"
      % max(abs(q(b, u, c).mean() - qabs(b, u, c).mean()) for b in BODIES for u in PHASE + SPACING for c in C1))
print("   K = 2 under body@0.02, record q_rel by body:", " ".join(f"{b} {qrel(b, 'C4s2', 'body@0.02').mean():+.3f}" for b in BODIES))
print("done")
