"""P52c (python probes/p52c_sm004_lead_check.py ROOT): the lead's check of SM004, the reader's grain as itself.
LEAD_CHECK_NOT_REGISTERED; a read of the shards and a refit, written by the lead in reviewing SM004's phase A and committed
before the freeze and before any TEST block is drawn, dry-run first on P52 (SM003's P45 records, engineering blocks
900476-900479, tag mse-p45, as the lead ruled); 2 November 2026; no simulation. Adapted from the lead's P45c (SM003).

It checks, from REGISTRATION_SM004.md's words and not from sm004.analyze, sm004.predict, sm004.checks or sm003.analyze:
- integrity: the sha256 of every file of the stage, of every FIT reread at g 1 and 2 (SM003's), of every FIT reread at
  g 4 (SM004's), and of every SM001 FIT shard against their manifests; the frozen model file against its committed sha256,
  and its manifest hashes against the FIT manifests; at the TEST stage, the run's digest against the frozen design's, the
  model file written before the TEST stage started, and the two reported sensitivities against their declared sha256;
- the FIT rows: the 864 condition means (g 1 and 2 from SM003's rereads, g 4 from SM004's), equal to the blob's;
- the model: the candidates H0 (F4's 16 terms) to H6, each adding to the last (G, G*c, G*e, G^2, G*a and G*b, G*d),
  refitted on the 864 means with the lead's own solver (scipy's trust-region reflective method with an analytic Jacobian);
  the declared selection rule (the smallest leave-one-block-out error; a smaller candidate within 0.002 of it chosen); the
  refit's predictions against the frozen model's at every condition of the stage;
- the parts, from the shards: per case the mean over the part's conditions of its paired difference; a block's value the
  mean of its 8 cases; the part the mean over the blocks; SD = sqrt(SD_T^2 + SD_F^2), SD_T the max rule, SD_F the larger
  of the SD over the 16 single-FIT-block refits and sqrt(16 x the jackknife variance), every fitted predictor the part uses
  refitted on the same block set (the model on that set's 864 means, F4 on SM003's 648); the verdict; on the probe the
  margins (>= 3 sqrt(1/4 + 1/16)), both halves, and the narrowest round threshold (0.01 steps) the rule allows;
- registered N1-N8; reported N9, N10, F4's offsets (R7, R8), the observed losses and gains (R16-R18), the comparators
  (the parametric refitted on the 864 means; the 4-NN with exact ties); at the TEST stage the two sensitivities H2 and H5
  on N1-N10, as numbers.

Fixed 2 November 2026 at the TEST stage, before its output was written (git shows the diff): the sensitivity files hold
their terms and coefficients under "model", as the main model file does; the first version read them at the top level and
stopped with a KeyError. The check now also verifies each file's own model hash and digest.
"""
import datetime
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy import stats
from scipy.optimize import least_squares

ROOT = Path(sys.argv[1])
LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
from sm001 import design as S1D  # noqa: E402   (constants only: the units, T*, lam_rest = 3 c)

RUNS = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane")
FITR, FIT4, SM1FIT = RUNS / "sm003" / "fit_reread", RUNS / "sm004" / "fit_g4", RUNS / "sm001" / "fit"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
out = []
say = lambda s="": (out.append(s), print(s, flush=True))
TEST_BLOCKS = list(range(910617, 910628)) + [910859, 910860, 910861, 910890, 910891]
MODEL_SHA = "d3cb24ccf9f72f665a311580679aecfbce2085e772f71208957e7a3a950f92ff"
SENS_SHA = {"H2": "6268fcb6d56ccaad4dfb130245dd86961900f60df8aaa8948ca82cba32336bfc",
            "H5": "d645f17c4298c9a94a08a461ab11ae1f465280875c24b0591cd0f1aa0fb7b18c"}

# ------------------------------------------------------------------------------------------------------------ integrity
M = json.load(open(ROOT / "manifest.json"))
WANT = {"probe": ("mse-p45", [900476, 900477, 900478, 900479]), "test": ("mse-sm004", sorted(TEST_BLOCKS))}
STAGE = M["stage"]
assert STAGE in WANT and M["tag"] == WANT[STAGE][0], (STAGE, M["tag"])
bad = [f["path"] for t in M["tasks"].values() for f in t["files"].values() if sha(ROOT / f["path"]) != f["sha256"]]
RM, R4, FM = (json.load(open(d / "manifest.json")) for d in (FITR, FIT4, SM1FIT))
bad += [t["file"]["path"] for t in RM["tasks"].values() if sha(FITR / t["file"]["path"]) != t["file"]["sha256"]]
bad += [t["file"]["path"] for t in R4["tasks"].values() if sha(FIT4 / t["file"]["path"]) != t["file"]["sha256"]]
bad += [t["files"]["shards"]["path"] for t in FM["tasks"].values()
        if sha(SM1FIT / t["files"]["shards"]["path"]) != t["files"]["shards"]["sha256"]]
assert not bad, bad[:5]
assert RM["sm001_fit_manifest_sha256"] == R4["sm001_fit_manifest_sha256"] == sha(SM1FIT / "manifest.json")
MODEL_PATH = LANE / "sm004" / "frozen" / "model.json"
assert sha(MODEL_PATH) == MODEL_SHA, "the model file is not the committed one"
BLOB = json.load(open(MODEL_PATH))
assert BLOB["model_sha256"] == hashlib.sha256(json.dumps(BLOB["model"], sort_keys=True).encode()).hexdigest()
assert BLOB["fit12_manifest_sha256"] == sha(FITR / "manifest.json") and BLOB["fit_g4_manifest_sha256"] == sha(FIT4 / "manifest.json")
B3 = json.load(open(LANE / "sm003" / "frozen" / "model.json"))
assert BLOB["sm003_model_sha256"] == sha(LANE / "sm003" / "frozen" / "model.json")
if STAGE == "test":
    fz = json.load(open(LANE / "sm004" / "frozen" / "design.json"))
    assert fz["digest"] == M["design_digest"], "the draw is not under the frozen design"
    mt = datetime.datetime.fromtimestamp(MODEL_PATH.stat().st_mtime, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert mt < M["started_utc"], ("the frozen model was written after the TEST stage started", mt, M["started_utc"])
    for k, h in SENS_SHA.items():
        assert sha(LANE / "sm004" / "frozen" / f"sensitivity_{k}.json") == h, k
say(f"P52c on {ROOT} ({STAGE}{', DRY RUN: P52 = SM003 P45 records, engineering blocks' if STAGE != 'test' else ''}): "
    f"{len(M['tasks'])} tasks, every sha256 equal to the manifest's; digest {M['design_digest'][:12]}; "
    f"{M['started_utc']} - {M['finished_utc']}")
say(f"  FIT: {len(RM['tasks'])} rereads at g 1 and 2 (SM003), {len(R4['tasks'])} at g 4 (SM004, digest "
    f"{R4['design_digest'][:12]}), {len(FM['tasks'])} SM001 FIT shards, every sha256 equal to its manifest's; the model file "
    f"sha256 {MODEL_SHA[:16]} (the committed one), model sha256 {BLOB['model_sha256'][:12]}, chosen {BLOB['chosen']}")


def parse(name):
    bits = name.split("-")
    c = float(bits[1][1:])
    if bits[0] == "never":
        return {"c": c, "m": None, "tau": float(bits[2][1:]), "never": True}
    return {"c": c, "m": float(bits[2][1:]), "tau": float(bits[3][1:]), "never": False}


# ------------------------------------------------------------------------------------------------------------- the rows
LAM0, TSTAR = S1D.LAM0, S1D.T_STAR
assert LAM0 == 3
UNITS_T = ("W4_x64", "W8_x64", "W16_x64", "W8_x64_r2", "W16_x64_r2", "W32_x64_r2")
UNITS_F = ("W4_x32", "W8_x32", "W16_x32")


def grains(w):
    return [g for g in (1, 2, 4) if g == 1 or (g == 2 and w % 2 == 0) or (g == 4 and w >= 8 and w % 4 == 0)]


def row(kind, w, L, arm, g, E):
    lam = LAM0 * arm["c"]
    return {"kind": kind, "w": w, "L": L, "c": arm["c"], "m": arm["m"], "tau": arm["tau"], "lam": lam, "g": g, "E": E,
            "x": {"a": math.log2(lam / w), "b": math.log2(L / lam), "c": arm["m"], "d": math.log2(arm["tau"] / TSTAR),
                  "e": math.log2(L / g), "G": math.log2(g)}}


FIT = []
for u in UNITS_F:
    bl = sorted(b for uu, b in FM["pairs"] if uu == u)
    Z = {b: np.load(FITR / "shards" / u / f"{b}.npz") for b in bl}
    Z4 = {b: np.load(FIT4 / "shards" / u / f"{b}.npz") for b in bl} if S1D.UNIT[u]["w"] >= 8 else None
    names = json.loads(str(Z[bl[0]]["__meta__"]))["arms"]
    if Z4:
        assert json.loads(str(Z4[bl[0]]["__meta__"]))["arms"] == names
    for L in S1D.UNIT[u]["sizes"]:
        for ai, nm in enumerate(names):
            arm = parse(nm)
            if arm["never"]:
                continue
            for g in (1, 2, 4):
                if g == 4 and not Z4:
                    continue
                src = Z4 if g == 4 else Z
                FIT.append(dict(row("fit", S1D.UNIT[u]["w"], L, arm, g, np.array([src[b][f"L{L}/g{g}/in"][ai] for b in bl])),
                                key=(u, L, nm, g)))
assert len(FIT) == 864 and all(r["E"].shape == (16, 8) for r in FIT), len(FIT)
_byk = {r["key"]: r for r in FIT}
FIT = [_byk[tuple(k)] for k in BLOB["fit_conditions"]]               # the blob's FIT order (the 4-NN's ties go by it)
assert len(FIT) == 864 and len({id(r) for r in FIT}) == 864
fm = {(r["w"], r["L"], r["c"], r["m"], r["tau"], r["g"]): r["E"].mean() for r in FIT}
bm = {}
for uu, L, arm, g, v in BLOB["fit_means"]:
    a = parse(arm)
    bm[(S1D.UNIT[uu]["w"], L, a["c"], a["m"], a["tau"], g)] = v
assert set(bm) == set(fm) and max(abs(bm[k] - fm[k]) for k in fm) == 0.0
FIT12 = [r for r in FIT if r["g"] in (1, 2)]
assert len(FIT12) == 648

PAIRS = [tuple(p) for p in M["pairs"]]
BLOCKS = sorted({b for _u, b in PAIRS})
assert BLOCKS == WANT[STAGE][1] and sorted(PAIRS) == sorted((u, b) for u in UNITS_T for b in BLOCKS), PAIRS
NB = len(BLOCKS)
TEST = []
for u in UNITS_T:
    cfg = S1D.UNIT[u]
    Z = {b: np.load(ROOT / "shards" / u / f"{b}.npz") for b in BLOCKS}
    for b in BLOCKS:
        meta = json.loads(str(Z[b]["__meta__"]))
        assert meta["unit"] == u and meta["block"] == b and meta["tag"] == M["tag"]
    names = json.loads(str(Z[BLOCKS[0]]["__meta__"]))["arms"]
    for L in cfg["sizes"]:
        for ai, nm in enumerate(names):
            for g in grains(cfg["w"]):
                key = {1: "u/in", 2: "cg/in", 4: "g4/in"}[g]
                E = np.array([Z[b][f"L{L}/{key}"][-1, ai] if g == 1 else Z[b][f"L{L}/{key}"][ai] for b in BLOCKS])
                TEST.append(row(cfg["kind"], cfg["w"], L, parse(nm), g, E))
by = {(r["kind"], r["w"], r["L"], r["c"], r["m"], r["tau"], r["g"]): r for r in TEST}
for r in TEST:
    if r["kind"] == "refine":
        tw = lambda gg: by.get(("transfer", r["w"] // 2, r["L"] // 2, r["c"] / 2, r["m"], r["tau"], gg))
        r["twin"], r["twin_half"] = tw(r["g"]), (tw(r["g"] // 2) if r["g"] > 1 else None)
say(f"  rows: {len(FIT)} FIT condition means (equal to the frozen blob's fit_means exactly; {len(FIT12)} at g 1 and 2); "
    f"{len(TEST)} conditions in the stage")

# ----------------------------------------------------------------------------------------------------------- the models
F4T = ("1", "a", "b", "c", "d", "a*b", "b^2", "a^2", "c*b", "c*a", "c^2", "e", "e*c", "e^2", "e*a", "e*b")
ADD = [("H1", ("G",)), ("H2", ("G*c",)), ("H3", ("G*e",)), ("H4", ("G^2",)), ("H5", ("G*a", "G*b")), ("H6", ("G*d",))]
FORMS = {"H0": F4T}
for k, t in ADD:
    FORMS[k] = FORMS[list(FORMS)[-1]] + t
assert tuple(B3["model"]["terms"]) == F4T and tuple(BLOB["model"]["terms"]) == FORMS[BLOB["chosen"]]
assert all(tuple(BLOB["candidates"][k]["terms"]) == FORMS[k] for k in FORMS)
PV = ("A", "B", "C", "M", "G")
PAR = ("1",) + PV + tuple(f"{v}^2" for v in PV if v != "G") + tuple(f"{PV[i]}*{PV[j]}" for i in range(5) for j in range(i + 1, 5)) + ("T",)
assert tuple(BLOB["parametric"]["terms"]) == PAR


def term(v, t):
    if "^" in t:
        s, p = t.split("^")
        return v[s] ** int(p)
    if "*" in t:
        s1, s2 = t.split("*")
        return v[s1] * v[s2]
    return v[t]


def X(rows, terms, par=False):
    vv = lambda r: ({"1": 1.0, "A": math.log2(r["lam"]), "B": math.log2(r["w"]), "C": math.log2(r["L"]), "M": r["m"],
                     "G": math.log2(r["g"]), "T": math.log2(r["tau"])} if par else dict(r["x"], **{"1": 1.0}))
    return np.array([[term(vv(r), t) for t in terms] for r in rows])


sig = lambda z: 1.0 / (1.0 + np.exp(-z))


def fit(Xm, y):
    f = lambda b: sig(Xm @ b) - y
    jac = lambda b: (lambda s: (s * (1 - s))[:, None] * Xm)(sig(Xm @ b))
    sol = least_squares(f, np.zeros(Xm.shape[1]), jac=jac, method="trf", xtol=1e-15, ftol=1e-15, gtol=1e-15, max_nfev=20000)
    return sol.x


ymean = lambda rows, bl=None: np.array([(r["E"] if bl is None else r["E"][bl]).mean() for r in rows])
XF = {k: X(FIT, t) for k, t in FORMS.items()}
lobo = {}
for k in FORMS:
    errs = [np.abs(ymean(FIT, [b]) - sig(XF[k] @ fit(XF[k], ymean(FIT, [i for i in range(16) if i != b])))) for b in range(16)]
    lobo[k] = float(np.mean(errs))
best = min(lobo.values())
chosen = next(k for k in FORMS if lobo[k] <= best + 0.002)
say(f"  the model by the declared rule: LOBO " + ", ".join(f"{k} {v:.6f}" for k, v in lobo.items()) + f"; chosen {chosen} "
    f"(within the tolerance by {best + 0.002 - lobo[chosen]:.6f}); the frozen blob: {BLOB['chosen']}, LOBO "
    + ", ".join(f"{k} {v:.6f}" for k, v in BLOB["lobo"].items()))
assert chosen == BLOB["chosen"]
TERMS = FORMS[chosen]
beta_lead = fit(XF[chosen], ymean(FIT))
r2 = 1 - ((sig(XF[chosen] @ beta_lead) - ymean(FIT)) ** 2).sum() / ((ymean(FIT) - ymean(FIT).mean()) ** 2).sum()
XT = X(TEST, TERMS)
p_frozen = sig(XT @ np.array(BLOB["model"]["beta"]))
p_lead = sig(XT @ beta_lead)
say(f"  the lead's refit of {chosen}: FIT R2 {r2:.6f} (the blob's {BLOB['model']['r2']:.6f}); its predictions at the "
    f"{len(TEST)} conditions against the frozen model's: largest |difference| {np.abs(p_lead - p_frozen).max():.1e}")
assert np.abs(p_lead - p_frozen).max() < 1e-6
for g in (1, 2, 4):
    rr = [r for r in FIT if r["g"] == g]
    say(f"     FIT bias (E - the model) at g {g}: {np.mean([r['E'].mean() for r in rr]) - np.mean(sig(X(rr, TERMS) @ beta_lead)):+.6f}")
ID = {id(r): i for i, r in enumerate(TEST)}
F4P = sig(X(TEST, F4T) @ np.array(B3["model"]["beta"]))
bp = fit(X(FIT, PAR, True), ymean(FIT))
PARP = sig(X(TEST, PAR, True) @ bp)
say(f"  the parametric (21 terms) refitted on the 864 means by the lead: against the blob's at the stage's conditions, "
    f"largest |difference| {np.abs(PARP - sig(X(TEST, PAR, True) @ np.array(BLOB['parametric']['beta']))).max():.1e}")
nnf = lambda r: np.array([math.log2(r["lam"]), math.log2(r["w"]), math.log2(r["L"]), float(round(r["m"] * TSTAR)),
                          math.log2(r["tau"]), math.log2(r["g"])])
NX = np.array([nnf(r) for r in FIT])
nsd = np.where(NX.std(0) > 0, NX.std(0), 1.0)
ny = ymean(FIT)
assert np.allclose(nsd, BLOB["nn"]["sd"], rtol=0, atol=1e-12) and np.array_equal(ny, np.array(BLOB["nn"]["train_y"]))
NNP = np.array([ny[np.lexsort((np.arange(len(FIT)), np.round((((NX - nnf(r)) / nsd) ** 2).sum(1), 9)))[:4]].mean() for r in TEST])
PRED = {"new": p_frozen, "f4": F4P, "par": PARP, "nn": NNP}
if STAGE == "test":
    for k in SENS_SHA:
        sb = json.load(open(LANE / "sm004" / "frozen" / f"sensitivity_{k}.json"))
        assert sb["name"] == k and sb["reported_sensitivity"] and sb["design_digest"] == BLOB["design_digest"]
        assert sb["model_sha256"] == hashlib.sha256(json.dumps(sb["model"], sort_keys=True).encode()).hexdigest()
        assert tuple(sb["model"]["terms"]) == FORMS[k] and sb["fit_g4_manifest_sha256"] == BLOB["fit_g4_manifest_sha256"]
        PRED[k] = sig(X(TEST, FORMS[k]) @ np.array(sb["model"]["beta"]))
        lead_k = sig(X(TEST, FORMS[k]) @ fit(XF[k], ymean(FIT)))
        assert np.abs(lead_k - PRED[k]).max() < 1e-6, k

# the refits for SD_F: the model on single FIT blocks / leaving one out (864 means); F4 on SM003's 648 the same way
XF4 = X(FIT12, F4T)
REF = {}
for nm_, sets in (("S", [[b] for b in range(16)]), ("J", [[i for i in range(16) if i != b] for b in range(16)])):
    REF[nm_] = [{"new": sig(XT @ fit(XF[chosen], ymean(FIT, s))), "f4": sig(X(TEST, F4T) @ fit(XF4, ymean(FIT12, s)))}
                for s in sets]

# ------------------------------------------------------------------------------------------------------------ the parts
K = 3 * math.sqrt(1 / 4 + 1 / 16)
sel = lambda kind, g, m=None, need=None: [r for r in TEST if r["kind"] == kind and r["g"] == g and (m is None or r["m"] == m)
                                          and (need is None or r.get(need) is not None)]
Pv = lambda key, r, P: P[key][ID[id(r)]]
err = lambda key: (lambda r, P: r["E"] - Pv(key, r, P))
aerr = lambda k1, k2: (lambda r, P: np.abs(r["E"] - Pv(k1, r, P)) - np.abs(r["E"] - Pv(k2, r, P)))
loss = lambda key, tw: (lambda r, P: (r["E"] - r[tw]["E"]) - (Pv(key, r, P) - Pv(key, r[tw], P)))
lossabs = lambda r, P: np.abs(loss("f4", "twin")(r, P)) - np.abs(loss("new", "twin")(r, P))
obs = lambda tw: (lambda r, P: r["E"] - r[tw]["E"])
PARTS = [("N1", "the g-2 offset: refinement at g 2, E - the model", sel("refine", 2), err("new"), ("new",), (-0.10, 0.05)),
         ("N2", "the g-4 shortfall: refinement at g 4, E - the model", sel("refine", 4), err("new"), ("new",), (-0.05, 0.08)),
         ("N3", "the late loss: refinement at g 1, m 2, (E - E twin) - (the model - the model at the twin)",
          sel("refine", 1, 2, "twin"), loss("new", "twin"), ("new",), (-0.16, 0.01)),
         ("N4", "the prompt loss: the same at m 0", sel("refine", 1, 0, "twin"), loss("new", "twin"), ("new",), (-0.07, 0.06)),
         ("N5", "the larger sheet: transfer at g 1, 2 and 4, E - the model",
          sel("transfer", 1) + sel("transfer", 2) + sel("transfer", 4), err("new"), ("new",), (-0.07, 0.06)),
         ("N6", "the matched-reader gain at g 2: (E - E twin at g/2) - (the model - the model at the twin at g/2)",
          sel("refine", 2, None, "twin_half"), loss("new", "twin_half"), ("new",), (-0.10, 0.08)),
         ("N7", "the same at g 4", sel("refine", 4, None, "twin_half"), loss("new", "twin_half"), ("new",), (-0.05, 0.09)),
         ("N8", "closer than F4 at g 4: refinement, |E - F4| - |E - the model|", sel("refine", 4), aerr("f4", "new"),
          ("new", "f4"), 0.02)]
REPORTED = [("N9", "closer than F4 at g 2: refinement, |E - F4| - |E - the model|", sel("refine", 2), aerr("f4", "new"), ("new", "f4")),
            ("N10", "the late loss kept against F4: refinement at g 1, late, |F4's loss error| - |the model's loss error|",
             sel("refine", 1, 2, "twin"), lossabs, ("new", "f4")),
            ("R7", "refinement at g 2, E - F4 (SM003's R1)", sel("refine", 2), err("f4"), ("f4",)),
            ("R8", "refinement at g 4, E - F4 (SM003's M7)", sel("refine", 4), err("f4"), ("f4",)),
            ("R16", "the observed late loss at g 1, E - E twin", sel("refine", 1, 2, "twin"), obs("twin"), ()),
            ("R17", "E - E twin at g/2 at g 2 (SM003's M4)", sel("refine", 2, None, "twin_half"), obs("twin_half"), ()),
            ("R18", "the same at g 4 (SM003's M5)", sel("refine", 4, None, "twin_half"), obs("twin_half"), ()),
            ("R10", "refinement at g 2, |E - the parametric| - |E - the model|", sel("refine", 2), aerr("par", "new"), ("new",)),
            ("R11", "refinement at g 4, |E - the parametric| - |E - the model|", sel("refine", 4), aerr("par", "new"), ("new",)),
            ("R12", "refinement at g 2, |E - the 4-NN| - |E - the model|", sel("refine", 2), aerr("nn", "new"), ("new",)),
            ("R13", "refinement at g 4, |E - the 4-NN| - |E - the model|", sel("refine", 4), aerr("nn", "new"), ("new",))]


def value(rows, f, uses, P=PRED):
    assert rows
    x = np.mean([f(r, P) for r in rows], axis=0)                       # (blocks, cases)
    blk = x.mean(1)
    sdT = max(blk.std(ddof=1), x.ravel().std(ddof=1) / math.sqrt(x.shape[1])) if NB > 1 else float("nan")
    sdF = sds = sdj = 0.0
    if uses:
        vs = np.array([np.mean([f(r, dict(P, **{k: rf[k] for k in uses})) for r in rows]) for rf in REF["S"]])
        vj = np.array([np.mean([f(r, dict(P, **{k: rf[k] for k in uses})) for r in rows]) for rf in REF["J"]])
        sds, sdj = vs.std(ddof=1), math.sqrt((len(vj) - 1) * ((vj - vj.mean()) ** 2).sum())
        sdF = max(sds, sdj)
    sd = math.sqrt(sdT ** 2 + sdF ** 2)
    v = float(blk.mean())
    h = stats.t.ppf(0.975, NB - 1) * sd / math.sqrt(NB)
    return {"v": v, "lo": v - h, "hi": v + h, "sd": sd, "sdT": sdT, "sdF": sdF, "sds": sds, "sdj": sdj, "n": len(rows),
            "halves": (float(blk[: NB // 2].mean()), float(blk[NB // 2:].mean()))}


def narrowest(q, two):
    lo = math.floor(round(min(q["v"] - K * q["sd"], *q["halves"]) / 0.01, 9)) * 0.01
    hi = math.ceil(round(max(q["v"] + K * q["sd"], *q["halves"]) / 0.01, 9)) * 0.01
    return f"[{lo:+.2f}, {hi:+.2f}]" if two else f">= {lo:+.2f}"


say(f"\nREGISTERED PARTS ({NB} blocks x 8 cases; SD = sqrt(SD_T^2 + SD_F^2); [95% t interval], t(0.975, {NB - 1}) = "
    f"{stats.t.ppf(0.975, NB - 1):.4f}" + (f"; the rule: each margin >= {K:.4f}, both halves passing" if STAGE == "probe" else "") + ")")
verdict = {}
for sid, words, rows, f, uses, th in PARTS:
    q = value(rows, f, uses)
    two = isinstance(th, tuple)
    holds = (th[0] <= q["v"] <= th[1]) if two else (q["v"] >= th)
    verdict[sid] = holds
    say(f"  {sid} {words} ({q['n']} conditions)")
    say(f"     {q['v']:+.6f} [{q['lo']:+.6f}, {q['hi']:+.6f}]  SD {q['sd']:.6f} (SD_T {q['sdT']:.6f}, SD_F {q['sdF']:.6f}: "
        f"single {q['sds']:.6f}, jackknife {q['sdj']:.6f})  threshold {th}: {'HOLDS' if holds else 'FAILS'}")
    if STAGE == "probe":
        marg = ((q["v"] - th[0]) / q["sd"], (th[1] - q["v"]) / q["sd"]) if two else ((q["v"] - th) / q["sd"],)
        hok = all((th[0] <= h <= th[1]) if two else (h >= th) for h in q["halves"])
        say(f"     margins {', '.join(f'{m:.4f}' for m in marg)}; halves {q['halves'][0]:+.6f} {q['halves'][1]:+.6f}; "
            f"rule {'ok' if min(marg) >= K and hok else 'NOT MET'}; the narrowest the rule allows {narrowest(q, two)}")
say(f"  VERDICTS: " + ", ".join(f"{k} {'HOLDS' if v else 'FAILS'}" for k, v in verdict.items())
    + ("  [a dry run on engineering blocks: not a development result]" if STAGE != "test" else ""))

say("\nREPORTED (scored the same way)")
for sid, words, rows, f, uses in REPORTED:
    q = value(rows, f, uses)
    say(f"  {sid:3s} {words}: {q['v']:+.6f} [{q['lo']:+.6f}, {q['hi']:+.6f}] (SD_T {q['sdT']:.6f}, SD_F {q['sdF']:.6f}; "
        f"halves {q['halves'][0]:+.6f} {q['halves'][1]:+.6f})"
        + (f"; the narrowest bound the rule allows {narrowest(q, False)}" if STAGE == "probe" and sid in ("N9", "N10") else ""))
for m, nm in ((2, "late"), (0, "prompt")):
    rr = sel("refine", 1, m, "twin")
    say(f"  the predicted refinement loss at g 1, {nm}, from the FIT alone: the model "
        f"{np.mean([Pv('new', r, PRED) - Pv('new', r['twin'], PRED) for r in rr]):+.6f}, F4 "
        f"{np.mean([Pv('f4', r, PRED) - Pv('f4', r['twin'], PRED) for r in rr]):+.6f}; observed {value(rr, obs('twin'), ())['v']:+.6f}")
for g in (2, 4):
    for m, nm in ((2, "late"), (0, "prompt")):
        rr = sel("refine", g, m)
        say(f"  the model's bias at g {g}, {nm} (refinement, E - the model): {value(rr, err('new'), ())['v']:+.6f} "
            f"({len(rr)} conditions)")
if STAGE == "test":
    say("\nTHE REPORTED SENSITIVITIES ON TEST (Amendment 1; numbers, no thresholds)")
    for k in SENS_SHA:
        P = dict(PRED, new=PRED[k])
        say(f"  {k}: " + "; ".join(f"{sid} {value(rows, f, (), P)['v']:+.6f}" for sid, _w, rows, f, _u, _t in PARTS)
            + "; " + "; ".join(f"{sid} {value(rows, f, (), P)['v']:+.6f}" for sid, _w, rows, f, _u in REPORTED[:2]))

name = f"p52c_sm004_lead_check{'_' + STAGE if STAGE != 'test' else ''}.txt"
(LANE / "probes" / "results" / name).write_text("\n".join(out) + "\n")
print(f"-> probes/results/{name}")
