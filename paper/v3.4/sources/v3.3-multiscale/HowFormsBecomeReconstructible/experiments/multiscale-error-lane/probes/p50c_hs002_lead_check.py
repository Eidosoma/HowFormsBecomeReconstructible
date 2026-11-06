"""P50c (python probes/p50c_hs002_lead_check.py ROOT): the lead's check of HS002, a plateau or a slow drift.
LEAD_CHECK_NOT_REGISTERED; a read of HS002's shards and raw packets and of the HS001 source shards they continue, written
by the lead in reviewing HS002's phase A and committed before the freeze, dry-run first on P50 (engineering blocks
950010-950017, tag mse-p50, continued from HS001's P49); 1 November 2026; no simulation.

0. Integrity: the sha256 of every HS002 file against its manifest; each block's HS001 source files against the sha256
   HS001's run recorded (the raw one also against the one HS002's shard names); the stage, tag, blocks, budgets and
   checkpoints; at the development and e014 stages the run's digest against hs002/frozen/design.json and the sources'
   against HS001's frozen digest.
1. The registered statements from REGISTRATION_HS002.md's words, not from hs002.analyze, hs002.predict or hs002.fit:
   Q per lineage (founder x recipient) the own-founder qualified score in points; a block's value the mean over its 8
   lineages; SD_block the larger of the SD over the block values and the SD over every lineage value / sqrt 8; the 95%
   t interval; on the probe the margins (>= 3 sqrt(1/4 + 1/16)) and both halves. H1 the floors Q(rewrite) - Q(erased)
   and Q(foreign) - Q(erased) at 1,024; H2 at 128 bytes D(1024) - D(256) in [-0.3, +0.3] (D(256) from HS001's shards);
   H3 Q(rewrite) at 1,024 less the protected copy (HS001's protected reads, constant).
2. The prespecified measurements: the curve over all 24 checkpoints (HS001's 16 from its shards, HS002's 8), block
   means; intervals over E014's generator's 10,000 whole-block resamples (percentiles); the fits coded here
   independently:
   - M1 c + a 2^(-(n-1)/h) and M0 (c = 0) by profile least squares on 400 half-lives log-spaced 0.25-1e5, M1 refined by
     a bounded scalar search in log h (as P49c, on 24 checkpoints); identified if h's 95% upper bound <= 256;
   - M2 c + a1 2^(-(n-1)/h1) + a2 2^(-(n-1)/h2), h1 < h2: a 60 x 60 log grid of pairs over 0.25-1e5, (c, a1, a2)
     linear, then two vectorised local passes of 21 x 21 points over +-1 grid step and +-0.1 step;
   - the model-free changes D(1024) - D(512), D(1024) - D(256) and the late mean over 768, 896, 1,024;
   - the readings, in order (a slow drift; a plateau within 1,024 rewrites; decay to zero or below; neither resolved),
     by the rule as frozen (RULE below: the declared rule with the lead's ruling on Q7, from P50q: M2's c counts only
     where M2's slow timescale is identified, h2's upper bound <= 256, and a plateau also needs the level to hold
     through the horizon, the drift bound at least 1,024) and, beside it, by the rule as first declared
     (PLAN_HS002.md); the drift bound: the shortest half-life of a decay toward zero that D(1024) - D(512)'s 95% lower
     bound leaves possible, 512 ln 2 / ln(D(512) / (D(512) + lower bound));
   - R_H(n) (HS001's reference, the ratio only if its lower bound is at least half its estimate), the floor
     Q(rewrite) - Q(erased), each budget, and the basins: the concordance excess at 1,024 against the founder-free null.
3. From the raw packets, decoded with E001's own unpack: the concordance at the eight new checkpoints against the
   shards, and the final packets against the 1,024 checkpoint's; reported (added by the lead after P50's dry run showed
   the 128-byte record's sign pattern fixed): the turnover, the fraction of decoded sign cells differing from the record
   after rewrite 256 (HS001's final packets), at each new checkpoint, by budget and lineage arm.
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy import optimize, stats

LANE = Path(__file__).resolve().parents[1]
EXP = LANE.parent
sys.path.insert(0, str(EXP))
from common import rng                                            # noqa: E402  (E-series seeds, read-only)
from E014_long_renewal import run as e014                          # noqa: E402  (read-only; main() never called)

tissue = e014.tissue
RULE = "AH"       # the lead's ruling on Q7 (P50q): M2's c counts only where M2's slow timescale is identified (h2's
                  # upper bound <= 256), and the level must hold through the horizon (the drift bound >= 1,024)
ROOT = Path(sys.argv[1])
out = []
say = lambda s="": (out.append(s), print(s, flush=True))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
HS1 = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/hs001")
SRC = {"probe": HS1 / "p49", "development": HS1 / "development", "e014": HS1 / "e014"}
WANT = {"probe": ("mse-p50", list(range(950010, 950018))), "development": ("mse-hs002", list(range(951000, 951128))),
        "e014": ("mse-hs002", list(range(12000, 12064)))}
HS001_FROZEN = json.load(open(LANE / "hs001" / "frozen" / "design.json"))["digest"]

# ---------- 0. integrity ----------
M = json.load(open(ROOT / "manifest.json"))
STAGE = M["stage"]
assert STAGE in WANT and M["tag"] == WANT[STAGE][0], (STAGE, M["tag"])
bad = [f["path"] for t in M["tasks"].values() for f in t["files"].values() if sha(ROOT / f["path"]) != f["sha256"]]
assert not bad, bad[:5]
BLOCKS = list(M["blocks"])
assert BLOCKS == WANT[STAGE][1], BLOCKS
NB = len(BLOCKS)
MS = json.load(open(SRC[STAGE] / "manifest.json"))
if STAGE in ("development", "e014"):
    fz = json.load(open(LANE / "hs002" / "frozen" / "design.json"))
    assert fz["digest"] == M["design_digest"], "the draw is not under the frozen design"
    assert MS["design_digest"] == HS001_FROZEN, "the sources are not HS001's frozen draw"
Z2 = {b: np.load(ROOT / "shards" / f"{b}.npz") for b in BLOCKS}
Z1 = {b: np.load(SRC[STAGE] / "shards" / f"{b}.npz") for b in BLOCKS}
m2 = json.loads(str(Z2[BLOCKS[0]]["__meta__"]))
m1 = json.loads(str(Z1[BLOCKS[0]]["__meta__"]))
FACT = [int(f) for f in m2["factors"]]
LIN = list(m2["lineage"])
CK1, CK2 = [int(n) for n in m1["checkpoints"]], [int(n) for n in m2["checkpoints"]]
CK = CK1 + CK2
assert LIN == ["rewrite", "foreign", "erased", "background"] and CK1 == [1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256]
assert CK2 == [320, 384, 448, 512, 640, 768, 896, 1024] and int(m2["start"]) == 256 and int(m2["horizon"]) == 1024
assert list(m1["probes"]) == ["copy", "copy_foreign", "copy_erased", "copy_background"] and list(m1["lineage"]) == LIN
nsrc = 0
for b in BLOCKS:
    m = json.loads(str(Z2[b]["__meta__"]))
    assert int(m["block"]) == b and m["design_digest"] == M["design_digest"] and m["tag"] == M["tag"] and m["stage"] == STAGE
    rec = MS["tasks"][str(b)]["files"]
    for kind in ("shards", "raw"):
        assert sha(SRC[STAGE] / rec[kind]["path"]) == rec[kind]["sha256"], (b, kind)
    assert m["source"]["sha256"] == rec["raw"]["sha256"] and m["source"]["hs001_digest"] == MS["design_digest"]
    assert int(json.loads(str(Z1[b]["__meta__"]))["block"]) == b
    nsrc += 2
say(f"P50c on {ROOT} ({STAGE}{', DRY RUN on engineering blocks' if STAGE == 'probe' else ''}): {len(M['tasks'])} tasks, "
    f"{sum(len(t['files']) for t in M['tasks'].values())} files, every sha256 equal to the manifest's; digest "
    f"{M['design_digest'][:12]}; {M['started_utc']} - {M['finished_utc']}, {M['cpu_s_total'] / 3600:.2f} CPU-h; "
    f"HS001's sources ({SRC[STAGE].name}, digest {MS['design_digest'][:12]}): {nsrc} files, every sha256 equal to HS001's "
    f"recorded one and the raw ones to those HS002's shards name; budgets {FACT}; the plateau rule as frozen: {RULE}")


def own_ck(f):
    """(blocks, 24 checkpoints, founders, recipients, lineage arms): own-founder qualified scores, in points."""
    x = np.concatenate([np.stack([Z1[b][f"f{f}/ck_scores"] for b in BLOCKS]),
                        np.stack([Z2[b][f"f{f}/ck_scores"] for b in BLOCKS])], 1)    # (B, C, F, R, A, T)
    return 100 * np.stack([x[:, :, fo, :, :, fo] for fo in range(4)], 2)


def own_pr(f):
    x = np.stack([Z1[b][f"f{f}/probe_scores"] for b in BLOCKS])                       # (B, F, R, P, T)
    return 100 * np.stack([x[:, fo, :, :, fo] for fo in range(4)], 1)                # (B, F, R, P)


def est(x):
    x = x.reshape(NB, -1)
    blk = x.mean(1)
    v = float(blk.mean())
    sd4, sdc = blk.std(ddof=1), x.ravel().std(ddof=1) / math.sqrt(x.shape[1])
    sd = max(sd4, sdc)
    h = stats.t.ppf(0.975, NB - 1) * sd / math.sqrt(NB)
    return {"v": v, "lo": v - h, "hi": v + h, "sd": sd, "sd4": sd4, "sdc": sdc,
            "halves": (float(blk[: NB // 2].mean()), float(blk[NB // 2:].mean()))}


KR = 3 * math.sqrt(1 / 4 + 1 / 16)
A = {a: i for i, a in enumerate(LIN)}
I1024, I512, I256 = CK.index(1024), CK.index(512), CK.index(256)
Q = {f: own_ck(f) for f in FACT}
P = {f: own_pr(f) for f in FACT}
D = {f: Q[f][..., A["rewrite"]] - Q[f][..., A["foreign"]] for f in FACT}       # (B, C, F, R)
at = lambda f, arm, i=I1024: Q[f][:, i, :, :, A[arm]]
PARTS = []
for f, lab, t1, t2, t3 in ((1, "2,048 B", 8, 8, -8), (4, "128 B", 9, 7, -1)):
    if f not in FACT:
        continue
    PARTS += [("H1", f"{lab}: Q(rewrite) - Q(erased) at 1,024", at(f, "rewrite") - at(f, "erased"), "ge", t1),
              ("H1", f"{lab}: Q(foreign) - Q(erased) at 1,024", at(f, "foreign") - at(f, "erased"), "ge", t2)]
    if f == 4:
        PARTS += [("H2", "128 B: D(1024) - D(256), lower side", D[4][:, I1024] - D[4][:, I256], "ge", -0.3),
                  ("H2", "128 B: D(1024) - D(256), upper side", D[4][:, I1024] - D[4][:, I256], "le", 0.3)]
    PARTS += [("H3", f"{lab}: Q(rewrite) at 1,024 - Q(copy)", at(f, "rewrite") - P[f][..., 0], "le", t3)]
PARTS.sort(key=lambda p: p[0])
say(f"\nREGISTERED STATEMENTS ({NB} blocks x 8 lineages; points; [95% t interval], t(0.975, {NB - 1}) = "
    f"{stats.t.ppf(0.975, NB - 1):.4f}; SD_block the larger of the block SD and the lineage SD / sqrt 8"
    + (f"; the rule: margin >= {KR:.4f} and both halves" if STAGE == "probe" else "") + ")")
res = {}
for sid, words, x, sense, th in PARTS:
    q = est(x)
    ok = q["v"] >= th if sense == "ge" else q["v"] <= th
    res.setdefault(sid, []).append(ok)
    say(f"  {sid} {words}: {q['v']:+.6f} [{q['lo']:+.6f}, {q['hi']:+.6f}]  SD {q['sd']:.6f} (block {q['sd4']:.6f}, "
        f"lineage/sqrt8 {q['sdc']:.6f})  {'>=' if sense == 'ge' else '<='} {th:+}: {'holds' if ok else 'FAILS'}")
    if STAGE == "probe":
        marg = ((q["v"] - th) if sense == "ge" else (th - q["v"])) / q["sd"]
        hok = all((h >= th) if sense == "ge" else (h <= th) for h in q["halves"])
        say(f"       margin {marg:.4f}; halves {q['halves'][0]:+.6f} {q['halves'][1]:+.6f}; rule "
            f"{'ok' if marg >= KR and hok else 'NOT MET'}")
say("  VERDICTS: " + ", ".join(f"{k} {'HOLDS' if all(v) else 'FAILS'}" for k, v in res.items())
    + {"probe": "  [a dry run on engineering blocks: not a development result]",
       "e014": "  [reported only: E014's published lineages, continued]"}.get(STAGE, ""))

# ---------- 2. the prespecified measurements ----------
idx = rng("E014", "bootstrap").integers(0, NB, (10000, NB))
NCK = np.array(CK, float)
K = NCK.size
HG = np.logspace(np.log10(0.25), 5, 400)
HG2 = np.logspace(np.log10(0.25), 5, 60)
q2 = lambda x: [float(v) for v in np.quantile(np.asarray(x)[1:], [0.025, 0.975])]    # over the resamples only


def fit_ca(y, x):
    xc = x - x.mean()
    a = ((y - y.mean(-1, keepdims=True)) * xc).sum(-1) / (xc ** 2).sum()
    c = y.mean(-1) - a * x.mean()
    return c, a, ((y - c[..., None] - a[..., None] * x) ** 2).sum(-1)


def fit_m1(Y):
    """Y (k, 24): c, a, h, sse, at the grid's end."""
    S = np.stack([fit_ca(Y, 2.0 ** (-(NCK - 1) / h))[2] for h in HG], 1)
    i = S.argmin(1)
    C, A_, H, E, end = (np.zeros(len(Y)) for _ in range(5))
    for k in range(len(Y)):
        lo, hi = np.log(HG[max(i[k] - 1, 0)]), np.log(HG[min(i[k] + 1, len(HG) - 1)])
        g = lambda lh: float(fit_ca(Y[k][None], 2.0 ** (-(NCK - 1) / math.exp(lh)))[2][0])
        r = optimize.minimize_scalar(g, bounds=(lo, hi), method="bounded", options={"xatol": 1e-9})
        lh = r.x if r.fun <= S[k, i[k]] else math.log(HG[i[k]])
        c, a, e = fit_ca(Y[k][None], 2.0 ** (-(NCK - 1) / math.exp(lh)))
        C[k], A_[k], H[k], E[k], end[k] = c[0], a[0], math.exp(lh), e[0], i[k] in (0, len(HG) - 1)
    return C, A_, H, E, end


def fit_m0(Y):
    return np.stack([(lambda x: ((Y - ((Y * x).sum(-1) / (x * x).sum())[:, None] * x) ** 2).sum(-1))(2.0 ** (-(NCK - 1) / h))
                     for h in HG], 1).min(1)


def lsq(Y, X):
    XtX = np.einsum("kni,knj->kij", X, X)
    coef = np.linalg.solve(XtX + 1e-12 * np.eye(X.shape[-1]), np.einsum("kni,kn->ki", X, Y)[..., None])[..., 0]
    return coef, ((Y - np.einsum("kni,ki->kn", X, coef)) ** 2).sum(1)


def x2(l1, l2):
    return np.stack([np.ones((len(l1), K)), 2.0 ** (-(NCK - 1) / np.exp(l1)[:, None]),
                     2.0 ** (-(NCK - 1) / np.exp(l2)[:, None])], -1)


def fit_m2(Y):
    """Y (k, 24): c, a1, h1, a2, h2, sse of c + a1 2^(-(n-1)/h1) + a2 2^(-(n-1)/h2), h1 < h2."""
    lg = np.log(HG2)
    best, b1, b2 = np.full(len(Y), np.inf), np.zeros(len(Y)), np.zeros(len(Y))
    for i in range(lg.size):
        for j in range(i + 1, lg.size):
            X = np.c_[np.ones(K), 2.0 ** (-(NCK - 1) / HG2[i]), 2.0 ** (-(NCK - 1) / HG2[j])]
            e = ((Y - (Y @ np.linalg.pinv(X).T) @ X.T) ** 2).sum(1)
            better = e < best
            best, b1, b2 = np.where(better, e, best), np.where(better, lg[i], b1), np.where(better, lg[j], b2)
    for span in (lg[1] - lg[0], (lg[1] - lg[0]) / 10):
        offs = np.linspace(-span, span, 21)
        nb_, n1, n2 = best.copy(), b1.copy(), b2.copy()
        for d1 in offs:
            for d2 in offs:
                t1, t2 = b1 + d1, b2 + d2
                ok = t1 < t2
                e = np.where(ok, lsq(Y, x2(np.where(ok, t1, b1), np.where(ok, t2, b2)))[1], np.inf)
                better = e < nb_
                nb_, n1, n2 = np.where(better, e, nb_), np.where(better, t1, n1), np.where(better, t2, n2)
        best, b1, b2 = nb_, n1, n2
    coef, e = lsq(Y, x2(b1, b2))
    return coef[:, 0], coef[:, 1], np.exp(b1), coef[:, 2], np.exp(b2), e


def read(Yb, name):
    """Yb (10001, 24): the point curve then the resamples. The report and both readings."""
    c, a, h, e1, end = fit_m1(Yb)
    e0 = fit_m0(Yb)
    c2, a1, h1, a2, h2, e2 = fit_m2(Yb)
    r = {"c": c, "a": a, "h": h, "c2": c2, "h1": h1, "h2": h2, "a1": a1, "a2": a2}
    I = {k: q2(v) for k, v in r.items()}
    d2nd, dtot = Yb[:, I1024] - Yb[:, I512], Yb[:, I1024] - Yb[:, I256]
    late = Yb[:, [CK.index(768), CK.index(896), I1024]].mean(1)
    rem = a * 2.0 ** (-(1024 - 1) / h)
    ident = I["h"][1] <= 256
    lb, d512 = q2(d2nd)[0], float(Yb[0, I512])
    hmin = math.inf if lb >= 0 else 512 * math.log(2) / math.log(d512 / (d512 + lb)) if d512 > 0 and d512 + lb > 0 else 0.0
    bound = ("none needed: the lower bound is not below zero" if lb >= 0 else
             f"a decay toward zero needs a half-life of at least {hmin:.0f} rewrites" if hmin > 0
             else "a decay to zero within the second half is not excluded")
    out_ = {}
    for rule in ("declared", RULE):
        m2ok = I["c2"][0] > 0 or (rule in ("A256", "AH") and I["h2"][1] > 256)
        held = hmin >= 1024 or rule != "AH"
        if q2(d2nd)[1] < 0:
            out_[rule] = "a slow drift"
        elif ident and I["c"][0] > 0 and m2ok and held:
            out_[rule] = "a plateau within 1,024 rewrites"
        elif ident and I["c"][0] <= 0:
            out_[rule] = "decay to zero or below within 1,024 rewrites"
        else:
            why = [w for w, bad in (("M1 not identified", not ident), ("M1's c not above zero", ident and I["c"][0] <= 0),
                                    ("M2's c not above zero", not m2ok), ("the level not shown to hold (drift bound < 1,024)", not held)) if bad]
            out_[rule] = "neither resolved (" + "; ".join(why) + ")"
    say(f"  {name}:")
    say(f"    M1 c {c[0]:+.4f} [{I['c'][0]:+.4f}, {I['c'][1]:+.4f}], a {a[0]:+.4f} [{I['a'][0]:+.4f}, {I['a'][1]:+.4f}], h "
        f"{h[0]:.3f} [{I['h'][0]:.3f}, {I['h'][1]:.3f}]{' (grid end)' if end[0] else ''}; resamples at the grid's ends "
        f"{int(end[1:].sum())}; {'identified' if ident else 'NOT identified'} (h's upper bound <= 256); remaining at 1,024 "
        f"{rem[0]:+.4f} [{q2(rem)[0]:+.4f}, {q2(rem)[1]:+.4f}]")
    say(f"    M2 c {c2[0]:+.4f} [{I['c2'][0]:+.4f}, {I['c2'][1]:+.4f}], h1 {h1[0]:.2f} [{I['h1'][0]:.2f}, {I['h1'][1]:.2f}], "
        f"h2 {h2[0]:.1f} [{I['h2'][0]:.1f}, {I['h2'][1]:.1f}], a1 {a1[0]:+.3f}, a2 {a2[0]:+.3f}; SSE(M0) - SSE(M1) "
        f"{e0[0] - e1[0]:.4f} [{q2(e0 - e1)[0]:.4f}, {q2(e0 - e1)[1]:.4f}]; SSE(M1) - SSE(M2) {e1[0] - e2[0]:.4f} "
        f"[{q2(e1 - e2)[0]:.4f}, {q2(e1 - e2)[1]:.4f}]")
    say(f"    D(1024) - D(512) {d2nd[0]:+.4f} [{q2(d2nd)[0]:+.4f}, {q2(d2nd)[1]:+.4f}]; D(1024) - D(256) {dtot[0]:+.4f} "
        f"[{q2(dtot)[0]:+.4f}, {q2(dtot)[1]:+.4f}]; the late mean (768, 896, 1,024) {late[0]:+.4f} [{q2(late)[0]:+.4f}, "
        f"{q2(late)[1]:+.4f}]; the drift bound: {bound}")
    say(f"    READING (as frozen, {RULE}): {out_[RULE]}; by the rule as first declared: {out_['declared']}")
    return out_


say("\nPRESPECIFIED MEASUREMENTS (block means, points; intervals: percentiles over E014's generator's 10,000 whole-block "
    "resamples; the fits coded here)")
for f in FACT:
    label = "2,048 bytes (the question)" if f == 1 else "128 bytes (reported)"
    Db = D[f].reshape(NB, K, -1).mean(2)                                                          # (B, 24)
    dpb = (P[f][..., 0] - P[f][..., 1]).reshape(NB, -1).mean(1)                                    # (B,)
    Yb = np.vstack([Db.mean(0)[None], Db[idx].mean(1)])
    bdp = np.r_[dpb.mean(), dpb[idx].mean(1)]
    lo, hi = q2(bdp)
    resolved = lo >= dpb.mean() / 2
    say(f"\n {label}: the reference {dpb.mean():+.3f} [{lo:+.3f}, {hi:+.3f}] "
        f"({'resolved' if resolved else 'NOT resolved: lower bound below half the estimate'})")
    say("    D(n): " + " ".join(f"{n}:{d:+.3f}" for n, d in zip(CK, Yb[0])))
    read(Yb, f"D(n), {label}")
    if resolved:
        read(Yb / bdp[:, None], f"R_H(n), {label}")
    fl = (Q[f][..., A["rewrite"]] - Q[f][..., A["erased"]]).reshape(NB, K, -1).mean(2)
    read(np.vstack([fl.mean(0)[None], fl[idx].mean(1)]), f"the floor Q(rewrite) - Q(erased), {label}")
    exc = {}
    for Zs, i in ((Z1, CK1.index(256)), (Z2, CK2.index(1024))):
        cs = np.stack([Zs[b][f"f{f}/conc_same"][i] for b in BLOCKS])
        cc = np.stack([Zs[b][f"f{f}/conc_cross"][i] for b in BLOCKS])
        exc[256 if Zs is Z1 else 1024] = 100 * (cs - cc).mean(1)                                    # (B, A)
    iv = {a: q2(np.r_[exc[1024][:, A[a]].mean(), exc[1024][idx, A[a]].mean(1)]) for a in LIN}
    kept = iv["rewrite"][0] > 0 and iv["foreign"][0] > 0 and iv["erased"][0] <= 0 <= iv["erased"][1] \
        and iv["background"][0] <= 0 <= iv["background"][1]
    mixed = iv["rewrite"][0] <= 0 or iv["foreign"][0] <= 0
    say("    basins, the concordance excess at 1,024 (256): " + "; ".join(
        f"{a} {exc[1024][:, A[a]].mean():+.3f} [{iv[a][0]:+.3f}, {iv[a][1]:+.3f}] ({exc[256][:, A[a]].mean():+.3f})" for a in LIN)
        + f"; READING: {'kept to 1,024' if kept else 'mixed by 1,024' if mixed else 'neither (the null arms not at zero)'}")

# ---------- 3. the raw packets ----------
dmaxc, fin_ok = 0.0, True
turn = {f: [] for f in FACT}
for b in BLOCKS:
    raw = np.load(ROOT / "raw" / f"{b}.npz")
    src = np.load(SRC[STAGE] / "raw" / f"{b}.npz")
    for f in FACT:
        fields = tissue.unpack(raw[f"f{f}/ck_packets"], f)                                         # (C, F, R, A, 16, 16)
        s = fields > 0
        s256 = tissue.unpack(src[f"f{f}/final_packets"][None], f)[0] > 0                           # (F, R, A, 16, 16)
        turn[f].append((s != s256[None]).mean((1, 2, 4, 5)))                                        # (C, A)
        same = np.stack([(s[:, i, 0] == s[:, i, 1]).mean((-2, -1)) for i in range(4)], 1)            # (C, F, A)
        cross = np.stack([np.mean([(s[:, i, r] == s[:, j, t]).mean((-2, -1)) for j in range(4) if j != i
                                   for r in (0, 1) for t in (0, 1)], 0) for i in range(4)], 1)
        dmaxc = max(dmaxc, float(np.abs(same - Z2[b][f"f{f}/conc_same"]).max()), float(np.abs(cross - Z2[b][f"f{f}/conc_cross"]).max()))
        fin_ok &= bool(np.array_equal(raw[f"f{f}/final_packets"], raw[f"f{f}/ck_packets"][-1]))
say(f"\nFROM THE RAW PACKETS (E001's unpack): the concordance at the eight new checkpoints, every arm, founder and block, "
    f"against the shards: largest difference {dmaxc:.1e}; the final packets equal to the 1,024 checkpoint's: "
    f"{'every block and budget' if fin_ok else 'NOT ALL'}")
for f in FACT:
    t = np.mean(turn[f], 0)                                                                         # (C, A)
    say(f"  the turnover at {'2,048' if f == 1 else '128'} bytes (decoded sign cells differing from rewrite 256's record, "
        f"mean over blocks, founders and recipients), rewrite / foreign / erased / background: "
        + "; ".join(f"{n}: " + "/".join(f"{x:.4f}" for x in t[i]) for i, n in enumerate(CK2)))
assert dmaxc <= 1e-12 and fin_ok

name = f"p50c_hs002_lead_check{'_' + STAGE if STAGE != 'development' else ''}.txt"
(LANE / "probes" / "results" / name).write_text("\n".join(out) + "\n")
print(f"-> probes/results/{name}")
