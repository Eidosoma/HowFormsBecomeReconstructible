"""P49c (python probes/p49c_hs001_lead_check.py ROOT [--e014]): the lead's check of HS001, historical specificity,
a reference and an asymptote. LEAD_CHECK_NOT_REGISTERED; a read of HS001's shards and raw packets, written by the lead
in reviewing HS001's phase A and committed before the freeze, dry-run first on P49 (engineering blocks 950010-950017,
tag mse-p49); 1 November 2026. The only simulation is with E014's own functions, under --e014, on E014's published
cohort: formation, capture and the terminal reader on the initial records for 64 blocks, and E014's own `simulate`
for block 12000.

1. With --e014 (post hoc, descriptive; E014's published cohort 12000-12063), with E014's functions, not hs001's:
   - the protected reads: the terminal-stream reader on E014's initial packets (copy = the own record, the foreign
     arm's initial record = the protected-foreign reference), scored by E014's observer against the own founder;
   - the bridge: the copy read against E014's published copy scores (observations.csv, after_16, every founder and
     recipient), and block 12000's whole lifecycle by E014's own `simulate` against every published row of that block;
   - the reference, D and R_H at checkpoints 1, 3, 8 and 16, with E014's own 10,000 index sets, ratio and numerator
     over the same resampled blocks.
2. HS001's registered parts (H1-H3) and prespecified measurements from REGISTRATION_HS001.md's words, from the shards,
   not from hs001.analyze, hs001.predict or hs001.fit:
   - Q per lineage (founder x recipient) is the own-founder qualified score; a block's value the mean over its 8
     lineages, in points; SD_block the larger of the SD over the block values and the SD over every lineage value /
     sqrt 8; the 95% t interval; on the probe the margins and both halves;
   - the reference, D(n), R_H(n) with the declared denominator rule, D(16) - D(1), the late mean and slope;
   - the asymptote by the declared rule, coded here independently: M1 D = c + a rho^(n-1) by profile least squares on
     400 half-lives log-spaced 0.25-1e5, refined by a bounded search in log h; M0 with c = 0; E014's generator's
     10,000 whole-block resamples; identified if h's 95% upper bound <= 64; above zero if c's interval excludes 0;
3. from the raw packets, decoded with E001's own unpack: the replicate concordance (same-founder less cross-founder
   sign agreement) at every checkpoint, against the shards' values.

Extended 1 November 2026, after HS001's development and before the lead's report (git shows the diff): the stage
'e014' (the reported continuation of E014's 64 lineages, run after the freeze under the frozen digest) is accepted,
with the frozen-digest check; and two reported companions are added, the floor's M1 fit (Q(rewrite) - Q(erased),
measurement 5) and an approximate two-timescale fit M2 of D (a 60 x 60 grid of half-lives, (c, a1, a2) linear, no
refinement; its c interval over the same resamples). Nothing in the registered parts or the other measurements changed.
"""
import csv
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

ROOT = Path(sys.argv[1])
E014 = "--e014" in sys.argv
out = []
say = lambda s="": (out.append(s), print(s, flush=True))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
tissue, compact, CFG, ARMS = e014.tissue, e014.compact, e014.CFG, e014.ARMS


def boot_idx(nb):
    return rng("E014", "bootstrap").integers(0, nb, (10000, nb))


# ---------- 1. E014's published cohort (post hoc) ----------
if E014:
    t0 = __import__("time").process_time()
    obs = {}
    with open(EXP / "E014_long_renewal" / "runs" / "confirmation_v2" / "observations.csv") as fh:
        for row in csv.DictReader(fh):
            obs[(int(row["block"]), int(row["factor"]), row["stage"], int(row["founder"]), int(row["recipient"]),
                 row["arm"])] = float(row["qualified_own"])
    blocks = list(e014.BLOCKS)
    say(f"P49c, part 1: E014's published cohort ({blocks[0]}-{blocks[-1]}, post hoc, descriptive), with E014's own "
        f"functions; {len(obs):,} published rows read")
    pc = {1: [], 4: []}
    dmax = 0.0
    src12000 = None
    for b in blocks:
        source = tissue.formation(b, "heterogeneous", CFG)
        acquired, end, first = tissue.capture(source["founder_state"], b, CFG)
        source.update(acquired=acquired, capture_end=end, capture_first=first)
        if b == 12000:
            src12000 = source
        for f in (1, 4):
            stream = b + 1000000
            packets, _ = compact.initial(source, stream, f)
            probe, _, _ = tissue.read_packets(packets, stream, "terminal", factor=f, cfg=CFG)
            own = compact.own_scores(compact.score(probe[None, :, :, :, 0], source["prototype"]))[0]
            cp, cf = own[:, :, ARMS.index("copy")], own[:, :, ARMS.index("foreign")]
            for fo in range(4):
                for r in range(2):
                    dmax = max(dmax, abs(cp[fo, r] - obs[(b, f, "after_16", fo, r, "copy")]))
            pc[f].append((cp, cf))
    say(f"  the bridge: the copy read against E014's published after_16 copy scores, {2 * 64 * 8} rows: largest "
        f"difference {dmax:.1e}")
    # block 12000's whole lifecycle by E014's own simulate, against every published row of the block
    rows = dmax2 = 0
    dmax2 = 0.0
    for f in (1, 4):
        raw = e014.simulate(src12000, 12000, f)
        v = np.concatenate((raw["generation_read"][:, :, :, :, 0], raw["checkpoint_read"][:, :, :, :, 0]))
        own = compact.own_scores(compact.score(v, raw["prototype"]))
        for s, stage in enumerate(e014.STAGES):
            for fo in range(4):
                for r in range(2):
                    for a, arm in enumerate(ARMS):
                        dmax2 = max(dmax2, abs(own[s, fo, r, a] - obs[(12000, f, stage, fo, r, arm)]))
                        rows += 1
    say(f"  block 12000's lifecycle by E014's own simulate against its published rows ({rows:,}, every stage, arm, "
        f"founder and recipient, both budgets): largest difference {dmax2:.1e}")
    idx = boot_idx(len(blocks))
    for f, label in ((1, "2,048 bytes"), (4, "128 bytes")):
        dp = np.array([100 * (cp - cf).mean() for cp, cf in pc[f]])
        qc = np.mean([100 * cp.mean() for cp, _ in pc[f]]); qf = np.mean([100 * cf.mean() for _, cf in pc[f]])
        bdp = dp[idx].mean(1)
        lo, hi = np.quantile(bdp, [.025, .975])
        say(f"  {label}: Q(copy) {qc:.3f}%, Q(copy_foreign) {qf:.3f}%; the reference {dp.mean():+.3f} [{lo:+.3f}, "
            f"{hi:+.3f}] (E014's index sets); positive in {(dp > 0).sum()} of {len(dp)} blocks; ratio reported "
            f"{bool(lo >= dp.mean() / 2)}")
        dser = {}
        for n in (1, 3, 8, 16):
            d = np.array([100 * np.mean([obs[(b, f, f"after_{n}", fo, r, "rewrite")] - obs[(b, f, f"after_{n}", fo, r, "foreign")]
                                         for fo in range(4) for r in range(2)]) for b in blocks])
            dser[n] = d
            rh = d[idx].mean(1) / bdp
            dl, dh = np.quantile(d[idx].mean(1), [.025, .975])
            rl, rhh = np.quantile(rh, [.025, .975])
            say(f"    after {n:2d}: D {d.mean():+.3f} [{dl:+.3f}, {dh:+.3f}]  R_H {d.mean() / dp.mean():.3f} [{rl:.3f}, {rhh:.3f}]")
        dd = dser[16] - dser[1]
        ql, qh = np.quantile(dd[idx].mean(1), [.025, .975])
        sl, sh_ = np.quantile(dd[idx].mean(1) / bdp, [.025, .975])
        say(f"    after 16 less after 1: D {dd.mean():+.3f} [{ql:+.3f}, {qh:+.3f}], as a share of the reference "
            f"{dd.mean() / dp.mean():+.3f} [{sl:+.3f}, {sh_:+.3f}]")
    say(f"  CPU {__import__('time').process_time() - t0:.1f} s")

# ---------- 2. HS001's shards ----------
M = json.load(open(ROOT / "manifest.json"))
DEV = list(range(951000, 951128))
WANT = {"probe": ("mse-p49", list(range(950010, 950018))), "development": ("mse-hs001", DEV),
        "e014": ("mse-hs001", list(range(12000, 12064)))}
STAGE = M["stage"]
assert STAGE in WANT and M["tag"] == WANT[STAGE][0], (STAGE, M["tag"])
bad = [f["path"] for t in M["tasks"].values() for f in t["files"].values() if sha(ROOT / f["path"]) != f["sha256"]]
assert not bad, bad[:5]
BLOCKS = list(M["blocks"])
assert BLOCKS == WANT[STAGE][1], BLOCKS
NB = len(BLOCKS)
frozen = LANE / "hs001" / "frozen" / "design.json"
if STAGE in ("development", "e014"):
    assert frozen.exists() and json.load(open(frozen))["digest"] == M["design_digest"], "the draw is not under the frozen design"
LABEL = {"probe": ", DRY RUN on engineering blocks", "development": "", "e014": ", the reported continuation of E014's published lineages (post hoc; not a test)"}
say(f"\nP49c, part 2, on {ROOT} ({STAGE}{LABEL[STAGE]}): "
    f"{len(M['tasks'])} tasks, {sum(len(t['files']) for t in M['tasks'].values())} files, every sha256 equal to the "
    f"manifest's; digest {M['design_digest'][:12]}; {M['started_utc']} - {M['finished_utc']}, "
    f"{M['cpu_s_total'] / 3600:.2f} CPU-h")
Z = {b: np.load(ROOT / "shards" / f"{b}.npz") for b in BLOCKS}
m0 = json.loads(str(Z[BLOCKS[0]]["__meta__"]))
LIN, PRB = list(m0["lineage"]), list(m0["probes"])
CK = [int(n) for n in m0["checkpoints"]]
assert LIN == ["rewrite", "foreign", "erased", "background"] and PRB == ["copy", "copy_foreign", "copy_erased", "copy_background"]
assert CK == [1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256] and int(m0["horizon"]) == 256
for b in BLOCKS:
    m = json.loads(str(Z[b]["__meta__"]))
    assert int(m["block"]) == b and m["design_digest"] == M["design_digest"] and m["tag"] == M["tag"]


def own_ck(f):
    """(blocks, checkpoints, founders, recipients, lineage arms) own-founder qualified scores, in points."""
    x = np.stack([Z[b][f"f{f}/ck_scores"] for b in BLOCKS])             # (B, C, F, R, A, T)
    return 100 * np.stack([x[:, :, fo, :, :, fo] for fo in range(4)], 2)


def own_pr(f):
    x = np.stack([Z[b][f"f{f}/probe_scores"] for b in BLOCKS])           # (B, F, R, P, T)
    return 100 * np.stack([x[:, fo, :, :, fo] for fo in range(4)], 1)    # (B, F, R, P)


lin = lambda x: x.reshape(NB, -1)                                        # (B, 8 lineages)


def est(x):
    x = lin(x)
    blk = x.mean(1)
    v = float(blk.mean())
    sd4, sdc = blk.std(ddof=1), x.ravel().std(ddof=1) / math.sqrt(x.shape[1])
    sd = max(sd4, sdc)
    h = stats.t.ppf(0.975, NB - 1) * sd / math.sqrt(NB)
    return {"v": v, "lo": v - h, "hi": v + h, "sd": sd, "sd4": sd4, "sdc": sdc,
            "halves": (float(blk[: NB // 2].mean()), float(blk[NB // 2:].mean()))}


KR = 3 * math.sqrt(1 / 4 + 1 / 16)
I256, I16, I1 = CK.index(256), CK.index(16), CK.index(1)
Q = {f: own_ck(f) for f in (1, 4)}
P = {f: own_pr(f) for f in (1, 4)}
A = {a: i for i, a in enumerate(LIN)}
PI = {p: i for i, p in enumerate(PRB)}
D = {f: Q[f][..., A["rewrite"]] - Q[f][..., A["foreign"]] for f in (1, 4)}   # (B, C, F, R)
PARTS = [
    ("H1", "2,048 B: Q(rewrite) - Q(erased) at 256", Q[1][:, I256, :, :, A["rewrite"]] - Q[1][:, I256, :, :, A["erased"]], "ge", 8),
    ("H1", "2,048 B: Q(foreign) - Q(erased) at 256", Q[1][:, I256, :, :, A["foreign"]] - Q[1][:, I256, :, :, A["erased"]], "ge", 8),
    ("H1", "128 B: Q(rewrite) - Q(erased) at 256", Q[4][:, I256, :, :, A["rewrite"]] - Q[4][:, I256, :, :, A["erased"]], "ge", 9),
    ("H1", "128 B: Q(foreign) - Q(erased) at 256", Q[4][:, I256, :, :, A["foreign"]] - Q[4][:, I256, :, :, A["erased"]], "ge", 7),
    ("H2", "128 B: D(256) - D(16), lower side", D[4][:, I256] - D[4][:, I16], "ge", -0.5),
    ("H2", "128 B: D(256) - D(16), upper side", D[4][:, I256] - D[4][:, I16], "le", 0.2),
    ("H3", "2,048 B: Q(rewrite) at 256 - Q(copy)", Q[1][:, I256, :, :, A["rewrite"]] - P[1][..., PI["copy"]], "le", -8),
    ("H3", "128 B: Q(rewrite) at 256 - Q(copy)", Q[4][:, I256, :, :, A["rewrite"]] - P[4][..., PI["copy"]], "le", -1),
]
say(f"\nREGISTERED PARTS ({NB} blocks x 8 lineages; points; [95% t interval], t(0.975, {NB - 1}) = "
    f"{stats.t.ppf(0.975, NB - 1):.4f}; SD_block the larger of the block SD and the lineage SD / sqrt 8; the rule: "
    f"margin >= {KR:.4f} and both halves)")
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
    + ({"probe": "  [a dry run on engineering blocks: not a development result]", "e014": "  [reported only: the continuation's first 16 rewrites are published]"}.get(STAGE, "")))

# ---------- the prespecified measurements ----------
say("\nPRESPECIFIED MEASUREMENTS (block means, points; intervals: E014's generator, 10,000 whole-block resamples)")
idx = boot_idx(NB)
NCK = np.array(CK, float)
HG = np.logspace(np.log10(0.25), 5, 400)


def fit_ca(y, x):
    xc = x - x.mean()
    a = ((y - y.mean(-1, keepdims=True)) * xc).sum(-1) / (xc ** 2).sum()
    c = y.mean(-1) - a * x.mean()
    return c, a, ((y - c[..., None] - a[..., None] * x) ** 2).sum(-1)


def sse_m0(y, x):
    a = (y * x).sum(-1) / (x * x).sum()
    return a, ((y - a[..., None] * x) ** 2).sum(-1)


def fit_m1(Y):
    """Y (k, 16): the decay-plus-plateau fit by the declared rule; returns c, a, h, sse (each (k,)), at grid end flag."""
    Y = np.atleast_2d(Y)
    S = np.stack([fit_ca(Y, 2.0 ** (-(NCK - 1) / h))[2] for h in HG], 1)       # (k, 400)
    i = S.argmin(1)
    C, A_, H, E, end = (np.zeros(len(Y)) for _ in range(5))
    for k in range(len(Y)):
        lo, hi = np.log(HG[max(i[k] - 1, 0)]), np.log(HG[min(i[k] + 1, len(HG) - 1)])
        g = lambda lh: float(fit_ca(Y[k][None], 2.0 ** (-(NCK - 1) / math.exp(lh)))[2][0])
        r = optimize.minimize_scalar(g, bounds=(lo, hi), method="bounded", options={"xatol": 1e-9})
        lh = r.x if r.fun <= S[k, i[k]] else math.log(HG[i[k]])
        c, a, e = fit_ca(Y[k][None], 2.0 ** (-(NCK - 1) / math.exp(lh)))
        C[k], A_[k], H[k], E[k], end[k] = c[0], a[0], math.exp(lh), e[0], i[k] == len(HG) - 1
    return C, A_, H, E, end


def fit_m0(Y):
    Y = np.atleast_2d(Y)
    S = np.stack([sse_m0(Y, 2.0 ** (-(NCK - 1) / h))[1] for h in HG], 1)
    return S.min(1)


HG2 = np.logspace(np.log10(0.25), 5, 60)


def fit_m2(Y):
    """The two-timescale fit, approximate: c at the best (h1 < h2) pair of a 60 x 60 grid, (c, a1, a2) linear; (k,)."""
    Y = np.atleast_2d(Y)
    best, cbest = np.full(len(Y), np.inf), np.zeros(len(Y))
    for i in range(len(HG2)):
        for j in range(i + 1, len(HG2)):
            X = np.c_[np.ones(len(NCK)), 2.0 ** (-(NCK - 1) / HG2[i]), 2.0 ** (-(NCK - 1) / HG2[j])]
            coef = Y @ np.linalg.pinv(X).T
            e = ((Y - coef @ X.T) ** 2).sum(1)
            better = e < best
            best, cbest = np.where(better, e, best), np.where(better, coef[:, 0], cbest)
    return cbest


q2 = lambda x: np.quantile(x, [.025, .975])
for f, label in ((1, "2,048 bytes"), (4, "128 bytes")):
    dpb = (P[f][..., PI["copy"]] - P[f][..., PI["copy_foreign"]]).reshape(NB, -1).mean(1)       # (B,)
    Db = D[f].reshape(NB, len(CK), -1).mean(2)                                                     # (B, C)
    bdp, bD = dpb[idx].mean(1), Db[idx].mean(1)                                                    # (10000,), (10000, C)
    lo, hi = q2(bdp)
    resolved = lo >= dpb.mean() / 2
    say(f"  {label}: the reference {dpb.mean():+.3f} [{lo:+.3f}, {hi:+.3f}] ({(dpb > 0).sum()} of {NB} blocks "
        f"positive; {'resolved' if resolved else 'NOT resolved: lower bound below half the estimate'})")
    Dm = Db.mean(0)
    rh = Dm / dpb.mean()
    say("    D(n): " + " ".join(f"{n}:{d:+.3f}" for n, d in zip(CK, Dm)))
    say("    R_H(n) point values: " + " ".join(f"{n}:{r:.3f}" for n, r in zip(CK, rh))
        + ("" if resolved else "  [not reported as a ratio: the reference is not resolved]"))
    for name, x in (("D(16) - D(1)", Db[:, I16] - Db[:, I1]),
                    ("late mean of D over 128, 192, 256", Db[:, [CK.index(128), CK.index(192), I256]].mean(1)),
                    ("late slope D(256) - D(128)", Db[:, I256] - Db[:, CK.index(128)])):
        l2, h2 = q2(x[idx].mean(1))
        say(f"    {name}: {x.mean():+.3f} [{l2:+.3f}, {h2:+.3f}]")
    for target, Y0, YB in (("D", Dm, bD), ("R_H", rh, bD / bdp[:, None])):
        c, a, h, e, end = fit_m1(Y0)
        cb, ab, hb, eb, endb = fit_m1(YB)
        e0, e0b = fit_m0(Y0)[0], fit_m0(YB)
        hl, hh = q2(hb)
        cl, ch = q2(cb)
        ident = hh <= 64
        reading = ("a plateau above zero" if ident and (cl > 0) else "a plateau below zero" if ident and ch < 0
                   else "decay to a plateau indistinguishable from zero" if ident else "a plateau is not identified within 256 rewrites")
        say(f"    M1 on {target}: c {c[0]:+.4f} [{cl:+.4f}, {ch:+.4f}], a {a[0]:+.4f} [{q2(ab)[0]:+.4f}, {q2(ab)[1]:+.4f}], "
            f"h {h[0]:.3f} [{hl:.3f}, {hh:.3f}]{' (grid end)' if end[0] else ''}; resamples at the grid end "
            f"{int(endb.sum())}; SSE(M0) - SSE(M1) {e0 - e[0]:.4f}; reading: {reading}")
    # reported companions, added after the development (see the docstring): the floor's M1, and an approximate M2 of D
    floor = (Q[f][..., A["rewrite"]] - Q[f][..., A["erased"]]).reshape(NB, len(CK), -1).mean(2)     # (B, C)
    fm, fb = floor.mean(0), floor[idx].mean(1)
    c_, a_, h_, e_, end_ = fit_m1(fm)
    cb_, ab_, hb_, eb_, endb_ = fit_m1(fb)
    sl = fb[:, I256] - fb[:, CK.index(128)]
    say(f"    the floor Q(rewrite) - Q(erased), M1: c {c_[0]:+.3f} [{q2(cb_)[0]:+.3f}, {q2(cb_)[1]:+.3f}], h {h_[0]:.2f} "
        f"[{q2(hb_)[0]:.2f}, {q2(hb_)[1]:.2f}]; its late slope {fm[I256] - fm[CK.index(128)]:+.3f} [{q2(sl)[0]:+.3f}, {q2(sl)[1]:+.3f}]")
    c2, c2b = fit_m2(Dm), fit_m2(bD)
    say(f"    M2 on D (approximate, grid only): c {c2[0]:+.3f} [{q2(c2b)[0]:+.3f}, {q2(c2b)[1]:+.3f}]")
    cs = np.stack([Z[b][f"f{f}/conc_same"] for b in BLOCKS]); cc = np.stack([Z[b][f"f{f}/conc_cross"] for b in BLOCKS])
    exc = 100 * (cs - cc).mean(2)                                                                  # (B, C, A)
    say("    the replicate-concordance excess at 256 (shards), " + ", ".join(f"{a} {exc[:, I256, i].mean():+.3f}" for i, a in enumerate(LIN))
        + f"; Q(rewrite) - Q(background) at 256 {(Q[f][:, I256, :, :, A['rewrite']] - Q[f][:, I256, :, :, A['background']]).mean():+.3f}")

# ---------- 3. the concordance from the raw packets, decoded with E001's own unpack ----------
dmaxc = 0.0
for b in BLOCKS:
    raw = np.load(ROOT / "raw" / f"{b}.npz")
    for f in (1, 4):
        fields = tissue.unpack(raw[f"f{f}/ck_packets"], f)                                       # (C, F, R, A, 16, 16)
        s = fields > 0
        same = np.stack([(s[:, i, 0] == s[:, i, 1]).mean((-2, -1)) for i in range(4)], 1)          # (C, F, A)
        cross = np.stack([np.mean([(s[:, i, r] == s[:, j, t]).mean((-2, -1)) for j in range(4) if j != i
                                   for r in (0, 1) for t in (0, 1)], 0) for i in range(4)], 1)
        dmaxc = max(dmaxc, float(np.abs(same - Z[b][f"f{f}/conc_same"]).max()), float(np.abs(cross - Z[b][f"f{f}/conc_cross"]).max()))
say(f"\nFROM THE RAW PACKETS (E001's unpack): the replicate concordance recomputed at every checkpoint, arm, founder "
    f"and block, against the shards: largest difference {dmaxc:.1e}")

name = f"p49c_hs001_lead_check{'_' + STAGE if STAGE != 'development' else ''}{'_e014' if E014 else ''}.txt"
(LANE / "probes" / "results" / name).write_text("\n".join(out) + "\n")
print(f"-> probes/results/{name}")
