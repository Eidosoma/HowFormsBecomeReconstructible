"""P55c (python probes/p55c_sm006_lead_check.py [ROOT]): the lead's check of SM006, the reader's erasure size in the
scaling model. LEAD_CHECK_NOT_REGISTERED; a read of the FIT rereads, the stage's shards and the source records, written
by the lead in reviewing SM006's phase A and committed before the freeze, dry-run first on P55 (SM003's P45 records,
engineering blocks 900476-900479, reread); 2 November 2026; no simulation. Without ROOT it checks the FIT side only.

It checks, from PLAN_SM006.md's words (with its Amendment 1) and not from sm006.analyze, sm006.predict or sm006.checks:
0. the erasure sizes: recomputed from the island tests by the declared rule (the largest island read with the
   background, agreement >= 0.5) and compared with sm006/design.py's EPS; the censored ones named;
1. FIT: the sha256 of every FIT file (SM003's g 1 and 2 rereads, SM004's g 4 rereads, SM006's gain rereads, SM001's FIT
   shards) against its manifest; the 1,836 condition means rebuilt from the shards;
2. the family J0-J6 rebuilt from the plan's words; the identification (full rank, condition number <= 1,000 on the
   centred and scaled columns, the constant kept); every candidate refitted by the lead's own solver (trust-region
   reflective, analytic Jacobian, logistic on the condition means); the leave-one-block-out errors over the 16 FIT
   blocks; the selection (within 0.002 of the best admissible, the fewest terms, then the smaller error); against the
   frozen model blob (sm006/frozen/model.json) when it exists: the choice, and its predictions within 1e-6;
3. with ROOT, the stage: every sha256 against its manifest and every source record against its own study's manifest;
   the rows (the base reads from the source shards, E(4) and E(8) from the stage, E(6) from the stage on the transfer
   units and from SM005 on the refined); the parts S1-S11 by the plan's words, SD = sqrt(SD_T^2 + SD_F^2) with SD_T the
   max rule and SD_F from the lead's own 16 single-FIT-block refits and jackknife (the model on that set's FIT means;
   SM004's H1 on its own 864 FIT rows, by SM004's procedure); on the probe the margins (>= 3 sqrt(1/4 + 1/16)), both
   halves and the narrowest round thresholds (0.01 steps); S2 and S7 register only if the rule allows a bound above 0.
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy import stats
from scipy.optimize import least_squares

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
from sm001 import design as S1D  # noqa: E402   (constants only: the units, their arms, T*, lam_rest = 3 c)
from sm006 import design as D6   # noqa: E402   (constants only, each checked below against the plan or the island tests)

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else None
RUNS = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane")
FITR, FIT4, FITG, SM1FIT = RUNS / "sm003" / "fit_reread", RUNS / "sm004" / "fit_g4", RUNS / "sm006" / "fit_gain", RUNS / "sm001" / "fit"
H1_SHA = "d3cb24ccf9f72f665a311580679aecfbce2085e772f71208957e7a3a950f92ff"       # sm004/frozen/model.json, committed
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
out = []
say = lambda s="": (out.append(s), print(s, flush=True))

# ------------------------------------------------------------------------------------------- 0. the erasure sizes
EPS, CENS = {}, []
for side in (32, 64):
    d = json.load(open(LANE / "probes" / "results" / f"p55s_sm006_erasure_{side}.json"))
    for k, xs in d.items():
        if isinstance(xs, list) and k.count("/") == 2:
            EPS[k] = max([l for l, x in zip(d["sizes"], xs) if x >= 0.5], default=0)
            if EPS[k] == max(d["sizes"]):
                CENS.append(k)
assert EPS == D6.EPS, ({k: (EPS.get(k), D6.EPS.get(k)) for k in set(EPS) | set(D6.EPS) if EPS.get(k) != D6.EPS.get(k)})
FN = {1.0: "f1", 0.5: "f2", 1 / (2 * math.sqrt(2)): "f2r2", 0.25: "f4"}
assert tuple(D6.F_GRID) == (0.5, 1 / (2 * math.sqrt(2)), 0.25)
say("0. the erasure sizes recomputed from the island tests by the declared rule (agreement >= 0.5): equal to "
    "sm006/design.py's EPS in all " + str(len(EPS)) + " entries; censored at the largest island tested: " + ", ".join(CENS))
say("   " + "; ".join(f"{k} {v}" for k, v in sorted(EPS.items(), key=lambda kv: (int(kv[0].split('/')[0]), int(kv[0].split('/')[1]), kv[0]))))

# ------------------------------------------------------------------------------------------------ 1. FIT
RM, R4, FM, GM = (json.load(open(d / "manifest.json")) for d in (FITR, FIT4, SM1FIT, FITG))
bad = [t["file"]["path"] for t in RM["tasks"].values() if sha(FITR / t["file"]["path"]) != t["file"]["sha256"]]
bad += [t["file"]["path"] for t in R4["tasks"].values() if sha(FIT4 / t["file"]["path"]) != t["file"]["sha256"]]
bad += [t["file"]["path"] for t in GM["tasks"].values() if sha(FITG / t["file"]["path"]) != t["file"]["sha256"]]
bad += [t["files"]["shards"]["path"] for t in FM["tasks"].values()
        if sha(SM1FIT / t["files"]["shards"]["path"]) != t["files"]["shards"]["sha256"]]
assert not bad, bad[:5]
assert RM["sm001_fit_manifest_sha256"] == R4["sm001_fit_manifest_sha256"] == sha(SM1FIT / "manifest.json")
assert len(GM["tasks"]) == 48 and all(t.get("bridge_all_equal", True) for t in GM["tasks"].values())
LAM0, TSTAR = S1D.LAM0, S1D.T_STAR
assert LAM0 == 3
UNITS_F = ("W4_x32", "W8_x32", "W16_x32")


def parse(name):
    bits = name.split("-")
    if bits[0] == "never":
        return None
    return {"c": float(bits[1][1:]), "m": float(bits[2][1:]), "tau": float(bits[3][1:])}


def row(kind, side, w, L, arm, g, f, E):
    lam, eps = LAM0 * arm["c"], EPS[f"{side}/{g}/{FN[f]}"]
    return {"kind": kind, "w": w, "L": L, "c": arm["c"], "m": arm["m"], "tau": arm["tau"], "lam": lam, "g": g, "f": f,
            "eps": eps, "E": E,
            "x": {"a": math.log2(lam / w), "b": math.log2(L / lam), "c": arm["m"], "d": math.log2(arm["tau"] / TSTAR),
                  "e": math.log2(L / g), "G": math.log2(g), "z": math.log2(eps / g), "E": math.log2(L / eps)}}


FIT = []
for u in UNITS_F:
    cfg = S1D.UNIT[u]
    bl = sorted(b for uu, b in FM["pairs"] if uu == u)
    assert len(bl) == 16
    Z = {b: np.load(FITR / "shards" / u / f"{b}.npz") for b in bl}
    Z4 = {b: np.load(FIT4 / "shards" / u / f"{b}.npz") for b in bl} if cfg["w"] >= 8 else None
    ZG = {b: np.load(FITG / "shards" / u / f"{b}.npz") for b in bl}
    names = json.loads(str(Z[bl[0]]["__meta__"]))["arms"]
    gnames = json.loads(str(ZG[bl[0]]["__meta__"]))["arms"]
    assert all(json.loads(str(ZG[b]["__meta__"]))["arms"] == gnames for b in bl)
    assert gnames == [n for n in names if parse(n) is not None and parse(n)["m"] in (0.0, 2.0)], (u, gnames)
    for L in cfg["sizes"]:
        for ai, nm in enumerate(names):
            arm = parse(nm)
            if arm is None:
                continue
            for g in (1, 2, 4):
                if g == 4 and not Z4:
                    continue
                src = Z4 if g == 4 else Z
                FIT.append(dict(row("fit", 32, cfg["w"], L, arm, g, 1.0, np.array([src[b][f"L{L}/g{g}/in"][ai] for b in bl])),
                                block_list=bl))
            if nm in gnames:
                j = gnames.index(nm)
                for f in D6.F_GRID:
                    for g in (1, 2):
                        FIT.append(dict(row("fit", 32, cfg["w"], L, arm, g, f,
                                            np.array([ZG[b][f"L{L}/g{g}/{FN[f]}/in"][j] for b in bl])), block_list=bl))
assert len(FIT) == 1836 and all(r["E"].shape == (16, 8) for r in FIT), len(FIT)
FIT0 = [r for r in FIT if r["f"] == 1.0]                               # SM004's 864 (H1's own FIT rows)
assert len(FIT0) == 864
say(f"\n1. FIT: {len(RM['tasks'])} rereads at g 1 and 2 (SM003), {len(R4['tasks'])} at g 4 (SM004), {len(GM['tasks'])} gain "
    f"rereads (SM006, reread digest {GM.get('reread_digest', '?')[:12]}, design digest {GM.get('design_digest', '?')[:12]}), {len(FM['tasks'])} SM001 FIT shards: every sha256 "
    f"equal to its manifest's; {len(FIT)} condition means ({len(FIT0)} at the base gain, {len(FIT) - len(FIT0)} gain variants)")

# ------------------------------------------------------------------------------------------------ 2. the family
F4T = ("1", "a", "b", "c", "d", "a*b", "b^2", "a^2", "c*b", "c*a", "c^2", "e", "e*c", "e^2", "e*a", "e*b")
H1T = F4T + ("G",)
F4E = tuple({"e": "E", "e*c": "E*c", "e^2": "E^2", "e*a": "E*a", "e*b": "E*b"}.get(t, t) for t in F4T)
FORMS = {"J0": H1T, "J1": H1T + ("z",), "J2": H1T + ("z", "z*c"), "J3": H1T + ("z", "z*c", "z*e"),
         "J4": F4E + ("G",), "J5": F4E + ("G", "z"), "J6": F4E + ("G", "z", "z*c")}
assert {k: tuple(v) for k, v in D6.CANDIDATES.items()} == FORMS, "sm006/design.py's family is not the plan's"


def term(v, t):
    if "^" in t:
        s, p = t.split("^")
        return v[s] ** int(p)
    if "*" in t:
        s1, s2 = t.split("*")
        return v[s1] * v[s2]
    return v[t]


X = lambda rows, terms: np.array([[term(dict(r["x"], **{"1": 1.0}), t) for t in terms] for r in rows])
sig = lambda z: 1.0 / (1.0 + np.exp(-z))


def fit(Xm, y):
    f = lambda b: sig(Xm @ b) - y
    jac = lambda b: (lambda s: (s * (1 - s))[:, None] * Xm)(sig(Xm @ b))
    return least_squares(f, np.zeros(Xm.shape[1]), jac=jac, method="trf", xtol=1e-15, ftol=1e-15, gtol=1e-15,
                         max_nfev=20000).x


ymean = lambda rows, bl=None: np.array([(r["E"] if bl is None else r["E"][bl]).mean() for r in rows])
XF = {k: X(FIT, t) for k, t in FORMS.items()}
ident = {}
for k, Xm in XF.items():
    Xs = Xm.copy()
    for j, t in enumerate(FORMS[k]):
        if t != "1":
            Xs[:, j] = (Xs[:, j] - Xs[:, j].mean()) / Xs[:, j].std()
    ident[k] = (int(np.linalg.matrix_rank(Xs)), float(np.linalg.cond(Xs)))
adm = [k for k in FORMS if ident[k][0] == len(FORMS[k]) and ident[k][1] <= 1000.0]
lobo = {}
for k in FORMS:
    errs = [np.abs(ymean(FIT, [b]) - sig(XF[k] @ fit(XF[k], ymean(FIT, [i for i in range(16) if i != b])))) for b in range(16)]
    lobo[k] = float(np.mean(errs))
best = min(lobo[k] for k in adm)
near = [k for k in adm if lobo[k] <= best + 0.002]
chosen = min(near, key=lambda k: (len(FORMS[k]), lobo[k]))
say(f"\n2. THE FAMILY (the plan's words): " + "; ".join(f"{k} {len(t)} terms, rank {ident[k][0]}, cond {ident[k][1]:.1f}, LOBO "
                                                        f"{lobo[k]:.6f}{'' if k in adm else ' (NOT admissible)'}" for k, t in FORMS.items()))
say(f"   the best admissible {best:.6f}; within 0.002: {near}; CHOSEN by the rule: {chosen} ({len(FORMS[chosen])} terms)")
beta = fit(XF[chosen], ymean(FIT))
r2 = 1 - ((sig(XF[chosen] @ beta) - ymean(FIT)) ** 2).sum() / ((ymean(FIT) - ymean(FIT).mean()) ** 2).sum()
say(f"   the lead's fit of {chosen} on the {len(FIT)} means: R2 {r2:.6f}; FIT bias (E - the model) by grain and factor: "
    + "; ".join(f"g {g} {FN[f]} {np.mean([r['E'].mean() for r in FIT if r['g'] == g and r['f'] == f]) - np.mean(sig(X([r for r in FIT if r['g'] == g and r['f'] == f], FORMS[chosen]) @ beta)):+.4f}"
                for g in (1, 2, 4) for f in (1.0,) + tuple(D6.F_GRID) if any(r["g"] == g and r["f"] == f for r in FIT)))
H1P = LANE / "sm004" / "frozen" / "model.json"
assert sha(H1P) == H1_SHA
H1B = json.load(open(H1P))
assert tuple(H1B["model"]["terms"]) == H1T
FZP = LANE / "sm006" / "frozen" / "model.json"
BLOB = json.load(open(FZP)) if FZP.exists() else None
if BLOB:
    assert BLOB["chosen"] == chosen and tuple(BLOB["model"]["terms"]) == FORMS[chosen], (BLOB["chosen"], chosen)
    pf = sig(XF[chosen] @ np.array(BLOB["model"]["beta"]))
    say(f"   the frozen blob (sha256 {sha(FZP)[:16]}): chosen {BLOB['chosen']}; its predictions at the FIT means against the "
        f"lead's fit: largest |difference| {np.abs(pf - sig(XF[chosen] @ beta)).max():.1e}")
    assert np.abs(pf - sig(XF[chosen] @ beta)).max() < 1e-6
else:
    say("   no frozen model blob yet (sm006/frozen/model.json)")
TERMS = FORMS[chosen]
# the reported sensitivity U (the lead's ruling at phase A, after P55's values were read; never computed on P55): the chosen
# form refitted on the FIT rows whose erasure size is not censored (dropping g 4 at side 32 and g 2 x 1/4 at side 32)
FITU = [r for r in FIT if f"32/{r['g']}/{FN[r['f']]}" not in CENS]
beta_u = fit(X(FITU, TERMS), ymean(FITU))
say(f"   the sensitivity U: {chosen} on the {len(FITU)} FIT means whose erasure size is not censored (dropped: "
    f"{', '.join(c for c in CENS if c.startswith('32/'))}; {len(FIT) - len(FITU)} means)")

# ------------------------------------------------------------------------------------------------ 3. the stage
if ROOT is not None:
    M = json.load(open(ROOT / "manifest.json"))
    STAGE = M["stage"]
    assert STAGE in D6.STAGES
    WANT = {"probe": {"sm003/p45": [900476, 900477, 900478, 900479]}, "debug": {"sm004/debug": [900472]},
            "preflight": {"sm004/preflight": [900470, 900471]},
            "development": {"sm003/test": list(range(910879, 910889)) + list(range(910894, 910900)),
                            "sm004/test": list(range(910617, 910628)) + [910859, 910860, 910861, 910890, 910891]}}[STAGE]
    SRC = {s: RUNS / s for s in WANT}
    S5R = {"sm003/p45": RUNS / "sm005" / "probe", "sm004/debug": RUNS / "sm005" / "debug",
           "sm004/preflight": RUNS / "sm005" / "preflight", "sm003/test": RUNS / "sm005" / "development",
           "sm004/test": RUNS / "sm005" / "development"}
    UNITS_T = ("W4_x64", "W8_x64", "W16_x64", "W8_x64_r2", "W16_x64_r2", "W32_x64_r2")
    bad = [f["path"] for t in M["tasks"].values() for f in t["files"].values() if sha(ROOT / f["path"]) != f["sha256"]]
    assert not bad, bad[:5]
    if STAGE == "development":
        fz = json.load(open(LANE / "sm006" / "frozen" / "design.json"))
        assert fz["digest"] == M["design_digest"], "the run is not under the frozen design"
    nsrc = 0
    for s, bl in WANT.items():
        sm = json.load(open(SRC[s] / "manifest.json"))
        s5 = json.load(open(S5R[s] / "manifest.json"))
        for u in UNITS_T:
            for b in bl:
                for f in sm["tasks"][f"{u}/{b}"]["files"].values():
                    assert sha(SRC[s] / f["path"]) == f["sha256"], (s, u, b)
                    nsrc += 1
                if u.endswith("_r2"):
                    t5 = s5["tasks"][f"{s}/{u}/{b}"]
                    assert sha(S5R[s] / t5["files"]["shards"]["path"]) == t5["files"]["shards"]["sha256"]
                    nsrc += 1
    BLOCKS = [(s, b) for s, bl in WANT.items() for b in bl]
    NB = len(BLOCKS)
    say(f"\n3. P55c on {ROOT} ({STAGE}{', DRY RUN on engineering records' if STAGE != 'development' else ''}): "
        f"{len(M['tasks'])} tasks, every sha256 equal to the manifest's; digest {M['design_digest'][:12]}; the source records "
        f"and SM005's refined E(6) shards: {nsrc} files, every sha256 equal to its study's manifest")
    key = lambda s: s.replace("/", "_")
    TEST = []
    for u in UNITS_T:
        cfg = S1D.UNIT[u]
        Zs = {(s, b): np.load(SRC[s] / "shards" / u / f"{b}.npz") for s, b in BLOCKS}
        Z6 = {(s, b): np.load(ROOT / "shards" / key(s) / u / f"{b}.npz") for s, b in BLOCKS}
        Z5 = {(s, b): np.load(S5R[s] / "shards" / key(s) / u / f"{b}.npz") for s, b in BLOCKS} if u.endswith("_r2") else None
        names = json.loads(str(Zs[BLOCKS[0]]["__meta__"]))["arms"]
        g4 = cfg["w"] >= 8 and cfg["w"] % 4 == 0
        for L in cfg["sizes"]:
            for ai, nm in enumerate(names):
                arm = parse(nm)
                if arm is None:
                    continue
                get = lambda fn: np.array([fn(sb) for sb in BLOCKS])
                TEST.append(row(cfg["kind"], 64, cfg["w"], L, arm, 1, 1.0, get(lambda sb: Zs[sb][f"L{L}/u/in"][-1, ai])))
                TEST.append(row(cfg["kind"], 64, cfg["w"], L, arm, 2, 1.0, get(lambda sb: Zs[sb][f"L{L}/cg/in"][ai])))
                if g4:
                    TEST.append(row(cfg["kind"], 64, cfg["w"], L, arm, 4, 1.0, get(lambda sb: Zs[sb][f"L{L}/g4/in"][ai])))
                for f in D6.F_GRID:
                    if FN[f] == "f2r2" and Z5 is not None:
                        E_ = get(lambda sb: Z5[sb][f"L{L}/E/in"][ai])
                    else:
                        E_ = get(lambda sb: Z6[sb][f"L{L}/g1/{FN[f]}/in"][ai])
                    TEST.append(row(cfg["kind"], 64, cfg["w"], L, arm, 1, f, E_))
    by = {(r["kind"], r["w"], r["L"], r["c"], r["m"], r["tau"], r["g"], r["f"]): r for r in TEST}
    for r in TEST:
        if r["kind"] == "refine":
            r["twin"] = by.get(("transfer", r["w"] // 2, r["L"] // 2, r["c"] / 2, r["m"], r["tau"], r["g"], r["f"]))
            r["base"] = by[("refine", r["w"], r["L"], r["c"], r["m"], r["tau"], r["g"], 1.0)]
    ID = {id(r): i for i, r in enumerate(TEST)}
    XT = X(TEST, TERMS)
    XH = X(TEST, H1T)                    # H1 does not know eps: for a gain variant it predicts the base reader's value
    PRED = {"new": sig(XT @ beta), "h1": sig(XH @ np.array(H1B["model"]["beta"]))}
    if BLOB:
        assert np.abs(sig(XT @ np.array(BLOB["model"]["beta"])) - PRED["new"]).max() < 1e-6
    REF = {}
    for nm_, sets in (("S", [[b] for b in range(16)]), ("J", [[i for i in range(16) if i != b] for b in range(16)])):
        REF[nm_] = [{"new": sig(XT @ fit(XF[chosen], ymean(FIT, s))), "h1": sig(XH @ fit(X(FIT0, H1T), ymean(FIT0, s)))}
                    for s in sets]
    say(f"   rows: {len(TEST)} stage conditions; the lead's predictions equal the frozen blob's" if BLOB else
        f"   rows: {len(TEST)} stage conditions")

    K = 3 * math.sqrt(1 / 4 + 1 / 16)
    # the registration's bands as the lead ruled on phase A (REGISTRATION_SM006.md); S2 and S7 reported
    TH = {"S1": (-0.16, 0.08), "S3": (-0.05, 0.11), "S4": (-0.02, 0.15), "S5": (-0.01, 0.28), "S6": (0.01, 0.17),
          "S8": (-0.10, 0.02), "S9": (0.00, 0.14), "S10": (-0.08, 0.09), "S11": (-0.05, 0.08)}
    if STAGE == "development":
        PRZ = json.load(open(LANE / "sm006" / "frozen" / "predictions.json"))
        got = {x["id"]: tuple(x["threshold"]) for x in PRZ["registered"]}
        assert got == TH and PRZ["design_digest"] == M["design_digest"], ("the frozen thresholds differ", got)
        SU = LANE / "sm006" / "frozen" / "sensitivity_U.json"
        sb = json.load(open(SU))
        assert tuple(sb["model"]["terms"]) == TERMS
        PRED["U"] = sig(XT @ np.array(sb["model"]["beta"]))
        assert np.abs(PRED["U"] - sig(XT @ beta_u)).max() < 1e-6, "the sensitivity file is not the lead's refit"
    sel = lambda kind, g, f, m=None, need=None: [r for r in TEST if (kind is None or r["kind"] == kind) and r["g"] == g
                                                 and abs(r["f"] - f) < 1e-12 and (m is None or r["m"] == m)
                                                 and (need is None or r.get(need) is not None)]
    Pv = lambda k, r, P: P[k][ID[id(r)]]
    err = lambda k: (lambda r, P: r["E"] - Pv(k, r, P))
    loss = lambda k: (lambda r, P: (r["E"] - r["twin"]["E"]) - (Pv(k, r, P) - Pv(k, r["twin"], P)))
    lossabs = lambda r, P: np.abs(loss("h1")(r, P)) - np.abs(loss("new")(r, P))
    rec = lambda k: (lambda r, P: (r["E"] - r["base"]["E"]) - (Pv(k, r, P) - Pv(k, r["base"], P)))
    aerr = lambda r, P: np.abs(r["E"] - Pv("h1", r, P)) - np.abs(r["E"] - Pv("new", r, P))
    PARTS = [
        ("S1", "the late loss from FIT alone: refined, base g 1, late, (E - E twin) - (the model - the model at the twin)",
         sel("refine", 1, 1.0, 2, "twin"), loss("new"), ("new",), "band"),
        ("S2", "the late loss against H1: |H1's loss error| - |the model's loss error|", sel("refine", 1, 1.0, 2, "twin"),
         lossabs, ("new", "h1"), "least"),
        ("S3", "E(4), blind: every unit, g 1, eps 4, E - the model", sel(None, 1, 0.5), err("new"), ("new",), "band"),
        ("S4", "E(8), blind: every unit, g 1, gain x 1/4, E - the model", sel(None, 1, 0.25), err("new"), ("new",), "band"),
        ("S5", "the erasure's recovery at gain x 1/4, blind: refined, late, (E(8) - E base) - (the model at eps 8 - at the base)",
         sel("refine", 1, 0.25, 2), rec("new"), ("new",), "band"),
        ("S6", "the same at eps 4", sel("refine", 1, 0.5, 2), rec("new"), ("new",), "band"),
        ("S7", "closer than H1 at the blind targets: every unit, g 1, eps 4 and 8, |E - H1| - |E - the model|",
         sel(None, 1, 0.5) + sel(None, 1, 0.25), aerr, ("new", "h1"), "least"),
        ("S8", "the g-2 offset kept: refined, g 2, E - the model", sel("refine", 2, 1.0), err("new"), ("new",), "band"),
        ("S9", "the g-4 shortfall kept: refined, g 4, E - the model", sel("refine", 4, 1.0), err("new"), ("new",), "band"),
        ("S10", "the prompt loss kept: refined, base g 1, prompt, as S1", sel("refine", 1, 1.0, 0, "twin"), loss("new"),
         ("new",), "band"),
        ("S11", "the larger sheet kept: transfer, g 1, 2 and 4, E - the model",
         sel("transfer", 1, 1.0) + sel("transfer", 2, 1.0) + sel("transfer", 4, 1.0), err("new"), ("new",), "band")]
    NCOND = {"S1": 27, "S2": 27, "S3": 162, "S4": 162, "S5": 27, "S6": 27, "S7": 324, "S8": 81, "S9": 81, "S10": 54, "S11": 216}

    def value(rows, f, uses, P=PRED):
        x = np.mean([f(r, P) for r in rows], axis=0)
        blk = x.mean(1)
        sdT = max(blk.std(ddof=1), x.ravel().std(ddof=1) / math.sqrt(x.shape[1])) if NB > 1 else \
            x.ravel().std(ddof=1) / math.sqrt(x.shape[1])
        vs = np.array([np.mean([f(r, dict(P, **{k: rf[k] for k in uses})) for r in rows]) for rf in REF["S"]])
        vj = np.array([np.mean([f(r, dict(P, **{k: rf[k] for k in uses})) for r in rows]) for rf in REF["J"]])
        sds, sdj = vs.std(ddof=1), math.sqrt((len(vj) - 1) * ((vj - vj.mean()) ** 2).sum())
        sdF = max(sds, sdj)
        sd = math.sqrt(sdT ** 2 + sdF ** 2)
        v = float(blk.mean())
        h = stats.t.ppf(0.975, NB - 1) * sd / math.sqrt(NB) if NB > 1 else float("nan")
        return {"v": v, "lo": v - h, "hi": v + h, "sd": sd, "sdT": sdT, "sdF": sdF, "sds": sds, "sdj": sdj,
                "halves": (float(blk[: NB // 2].mean()), float(blk[NB // 2:].mean())) if NB > 1 else (v, v)}

    def narrowest(q, kind):
        lo = math.floor(round(min(q["v"] - K * q["sd"], *q["halves"]) / 0.01, 9)) * 0.01
        hi = math.ceil(round(max(q["v"] + K * q["sd"], *q["halves"]) / 0.01, 9)) * 0.01
        return (round(lo, 2), round(hi, 2)) if kind == "band" else round(lo, 2)

    say(f"\n   THE PARTS ({NB} blocks x 8 cases; SD = sqrt(SD_T^2 + SD_F^2); [95% t interval]"
        + (f"; the rule: each margin >= {K:.4f}, both halves" if STAGE == "probe" else "") + ")")
    for sid, words, rows, f, uses, kind in PARTS:
        assert len(rows) == NCOND[sid], (sid, len(rows), NCOND[sid])
        q = value(rows, f, uses)
        line = (f"   {sid:3s} {words} ({len(rows)} conditions)\n        {q['v']:+.6f} [{q['lo']:+.6f}, {q['hi']:+.6f}] SD "
                f"{q['sd']:.6f} (SD_T {q['sdT']:.6f}, SD_F {q['sdF']:.6f}: single {q['sds']:.6f}, jackknife {q['sdj']:.6f}); "
                f"halves {q['halves'][0]:+.6f} {q['halves'][1]:+.6f}")
        if STAGE == "probe":
            nb = narrowest(q, kind)
            if kind == "band":
                line += f"; the narrowest band [{nb[0]:+.2f}, {nb[1]:+.2f}]"
                assert nb == TH[sid], (sid, nb, TH[sid])
            else:
                line += f"; the narrowest bound >= {nb:+.2f}: " + ("registers" if nb > 0 else "NOT above 0: reported")
                assert nb <= 0 and sid not in TH
        if sid in TH:
            line += f"; registered band [{TH[sid][0]:+.2f}, {TH[sid][1]:+.2f}]: " + (
                "HOLDS" if TH[sid][0] <= q["v"] <= TH[sid][1] else "FAILS")
        else:
            line += "; reported"
        if STAGE == "development":
            line += f"; the sensitivity U {value(rows, f, (), dict(PRED, new=PRED['U']))['v']:+.6f}"
        say(line)
    for m, nm in ((2, "late"), (0, "prompt")):
        rr = sel("refine", 1, 1.0, m, "twin")
        o = np.mean([(r["E"] - r["twin"]["E"]).mean() for r in rr])
        say(f"   the refinement loss at g 1, {nm}: observed {o:+.6f}; predicted from FIT by the model "
            f"{np.mean([Pv('new', r, PRED) - Pv('new', r['twin'], PRED) for r in rr]):+.6f}, by H1 "
            f"{np.mean([Pv('h1', r, PRED) - Pv('h1', r['twin'], PRED) for r in rr]):+.6f}")

name = "p55c_sm006_lead_check" + ("_fit" if ROOT is None else ("" if STAGE == "development" else f"_{STAGE}")) + ".txt"
(LANE / "probes" / "results" / name).write_text("\n".join(out) + "\n")
print(f"-> probes/results/{name}")
