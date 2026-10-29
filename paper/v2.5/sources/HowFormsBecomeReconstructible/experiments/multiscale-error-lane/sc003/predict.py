"""SC003's registered statements and their scoring, written before any development outcome.

python -m sc003.predict   (writes sc003/frozen/predictions.json)

Thresholds were set from engineering probe P26 (32 cases on blocks
900660-900663 under tag mse-p26; probes/results/p26b_sc003_margins.json) under BE002's rule. For each quantity,
SD_block = max(the item's own SD over P26's four blocks, the RMS of those SDs over the part's items). An every-item part
sits >= 3 x sqrt(1/4 + 1/16) = 1.68 SD_block inside P26's worst item; a pooled part (the mean over its items) uses the
SD over blocks of the pooled per-block value. An item is one unit and body (and arm or rate where a part names several).
Margins at the registered thresholds are in each statement's inputs. The lead's review (28 October 2026) approved the
design and the thresholds as drafted, and narrowed the wording of claims B1, B3, B7 and B9 and of B5's label and rule text
to what each rule tests.

Scored by sc003.analyze on the unrounded block means over the 16 development blocks, at t = 4,000 unless a statement
names another instant. r_in: the record's agreement with the correct target over the patch's occupied sites (for change,
the new target); r_out: outside the patch; r_all: over the sheet. Runs are named situation + patch side @ mu.
The extra loss of an arm under scattered corruption at mu: (none8 - cue8) in r_all of the arm, minus the cue arm's.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from sc003 import design as D  # noqa: E402

ALL = tuple((u, b) for u in D.UNITS for b in D.BODIES)
HI, LO = "@0.001", "@0.00025"

MUS = (HI, LO)
PACE_T = tuple(range(200, 1001, 100))     # B5: mu t = 0.2 ... 1 at the faster rate

TH = {"B1_lo": 0.95, "B1_hi": 1.05, "B1_inst": 0.01,
      "B2_item_hi": 0.01, "B2_mean_hi": 0.15, "B2_item_lo": 0.005, "B2_mean_lo": 0.06,
      "B3_item": 0.001, "B3_s4": 0.015,
      "B4_hi": 0.04, "B4_lo": 0.02, "B4_rate": 0.02,
      "B5_pace": 0.01,
      "B6_emt_t200": 0.15, "B6_growth": 0.10,
      "B7_change4": 0.03, "B7_extra_loss": 0.005, "B7_none8": 0.001,
      "B8_sub": -0.08,
      "B9_s4": 0.04, "B9_f0": 0.01, "B9_mat": 0.045,
      "B10_shrink": 0.03, "B10_out": 0.002}

STATEMENTS = [
    {"id": "B1", "kind": "the population's birth checks are first-update checks",
     "claim": "Under turnover the population's newborns commit on their first update as often as (within 5 per cent) "
              "newborns isolated for one update and then coupled at full strength, at either maturation time; newborns "
              "joined at once almost never do (at most 1 per cent as often)",
     "rule": "HOLDS if, with no event and under scattered cue damage at both turnover rates, mat-300's and mat-1000's new "
             "commitments by cells of age 0 are between 0.95 and 1.05 times iso-3's, and inst-3's at most 0.01 times "
             "iso-3's, in every unit for both bodies, else FAILS",
     "inputs": "P26: ratio 0.973 to 1.000 (margin 1.78 SD_block); inst-3 / iso-3 0 to 0.0027 (2.12)"},
    {"id": "B2", "kind": "the birth check alone re-specifies small groups",
     "claim": "Isolating each newborn for its first update, on a sheet otherwise joined at full strength (lam 3), adopts a "
              "legitimate change of a 4 x 4 group that the same sheet with no isolation refuses",
     "rule": "HOLDS if iso-3's r_in minus inst-3's for change4 is >= 0.01 in every unit for both bodies and >= 0.15 on "
             "average over the four items at mu = 1e-3, and >= 0.005 in every item and >= 0.06 on average at "
             "mu = 2.5e-4, else FAILS",
     "inputs": "P26: 1e-3 +0.149 to +0.344 (1.69), mean +0.222 (SD 0.039, 1.85); 2.5e-4 +0.068 to +0.143 (1.78), mean "
               "+0.119 (SD 0.032, 1.86)"},
    {"id": "B3", "kind": "the birth check alone repairs inherited errors",
     "claim": "With no event, the same first-update isolation keeps more of the record than none, and by at least 0.015 on "
              "stripes (S4)",
     "rule": "HOLDS if with no event at mu = 1e-3 iso-3's r_all minus inst-3's is >= 0.001 in every unit for both bodies "
             "and >= 0.015 for S4, else FAILS",
     "inputs": "P26: +0.006 to +0.026 (1.84); S4 +0.022 to +0.026 (1.96)"},
    {"id": "B4", "kind": "the birth check alone pays in false alarms, more with faster renewal",
     "claim": "Under scattered cue corruption the first-update isolation loses more of the record than none, beyond what "
              "turnover itself costs, and more at the faster turnover",
     "rule": "HOLDS if iso-3's extra loss (none8 minus cue8 in r_all, minus the cue arm's) exceeds inst-3's by >= 0.04 at "
             "mu = 1e-3 and by >= 0.02 at mu = 2.5e-4, and iso-3's extra loss at 1e-3 exceeds its own at 2.5e-4 by "
             ">= 0.02, in every unit for both bodies, else FAILS",
     "inputs": "P26: +0.052 to +0.120 (3.08); +0.025 to +0.047 (2.84); +0.027 to +0.076 (2.30)"},
    {"id": "B5", "kind": "aligned by births, the two rates are nearer than aligned by time",
     "claim": "At the same elapsed time the faster-renewing sheet's birth check has adopted more of a 4 x 4 change than the "
              "slower's; at the same number of births per site the two are nearer",
     "rule": "HOLDS if (the mean over t = 200, 300, ..., 1,000 and over the four unit-body items of the equal-time gap) "
             "minus (the absolute value of the mean over t and items of the equal-births gap) is >= 0.01, else FAILS; "
             "the equal-time gap is (iso-3 - inst-3 in the change4 r_in trace at mu = 1e-3 and t) minus (the same at "
             "mu = 2.5e-4 and t), the equal-births gap the former minus (the same at mu = 2.5e-4 and 4t)",
     "inputs": "P26: equal time +0.083 (SD 0.038), equal births +0.033 (SD 0.020); the rule's statistic +0.050 (SD 0.022, "
               "1.83); fast / slow 3.5 at equal time and 1.4 at equal births (reported)"},
    {"id": "B6", "kind": "the pooled coupling acts at once, the birth check over time",
     "claim": "Through the pooled coupling alone a sheet adopts its share of a 4 x 4 change within the first 200 updates; "
              "through the birth check alone its adoption keeps growing with births",
     "rule": "HOLDS if at mu = 1e-3 emt-1000's r_in minus inst-3's for change4 at t = 200 is >= 0.15 on average over the "
             "four items, and iso-3's growth in r_in minus inst-3's from t = 200 to t = 2,000 exceeds emt-300's and "
             "emt-1000's by >= 0.10 on average, else FAILS",
     "inputs": "P26: +0.242 (SD 0.038, 2.42); growth difference +0.167 (SD 0.034, 1.96) and +0.188 (SD 0.039, 2.27)"},
    {"id": "B7", "kind": "the two named scales reproduce the population",
     "claim": "The population's own junctions behave as their effective-medium coupling plus each newborn's first-update "
              "isolation: at t = 4,000 they adopt a small change, pay under scattered corruption and keep the record with "
              "no event as that two-scale sheet does",
     "rule": "HOLDS if at both turnover rates mat-300 minus iso-emt-300 and mat-1000 minus iso-emt-1000 are within 0.03 in "
             "r_in for change4, within 0.005 in extra loss, and within 0.001 in r_all with no event, in every unit for "
             "both bodies, else FAILS",
     "inputs": "P26: change4 -0.004 to +0.006 (1.74); extra loss -0.001 to +0.002 (1.76); none8 within 0.0001 (5.06)"},
    {"id": "B8", "kind": "the two scales overlap",
     "claim": "Where the pooled coupling already re-specifies a group, the birth check adds less",
     "rule": "HOLDS if at mu = 1e-3, (iso-emt-1000 - emt-1000) minus (iso-3 - inst-3) in r_in for change4 is <= -0.08 on "
             "average over the four items, else FAILS",
     "inputs": "P26: -0.152 (SD 0.039, 1.87); items -0.221 to -0.100"},
    {"id": "B9", "kind": "a regrowing wound's window is the birth check",
     "claim": "In a wound regrown by division, isolating each newborn for its first update repairs the regrown cells' "
              "inherited records beyond instant junctions, and junctions that keep maturing afterwards add at most 0.045",
     "rule": "HOLDS if in regrow8 iso-3's r_in minus inst-3's is >= 0.04 for S4 in both bodies and >= 0.01 on average over "
             "F0's two items, and mat-300's and mat-1000's r_in minus iso-3's is <= 0.045 in every unit for both bodies, "
             "else FAILS",
     "inputs": "P26: S4 +0.064 to +0.081 (1.81); F0 mean +0.025 (SD 0.007, 2.12); mat - iso-3 +0.004 to +0.015 (1.79)"},
    {"id": "B10", "kind": "the wound's check reads corrupted cues; outside, nothing",
     "claim": "The first-update check's advantage in the regrowing wound shrinks when the cue is corrupted, and it changes "
              "nothing outside the wound",
     "rule": "HOLDS if (iso-3 - inst-3) in r_in, regrow8 minus regrow+cue8, is >= 0.03 on average over the four items, and "
             "in regrow+cue8 iso-3's r_out is within 0.002 of inst-3's in every unit for both bodies, else FAILS",
     "inputs": "P26: shrink +0.056 (SD 0.012, 2.08); r_out within 0.0001 (5.59)"},
]


def blk(B, u, b, rn, arm, e="r_in", ti=-1):
    """Per-block values of an endpoint at read index ti."""
    run = D.RUNS[D.RUNNAMES.index(rn)]
    return B[(u, b)][f"{rn}/{e}"][:, ti, D.arms_of(run).index(arm)]


def trc(B, u, b, rn, arm, t, e="trace"):
    """Per-block values of a trace (r_in: 'trace'; r_all: 'trace_all') at update t."""
    run = D.RUNS[D.RUNNAMES.index(rn)]
    return B[(u, b)][f"{rn}/{e}"][:, t // D.TRACE - 1, D.arms_of(run).index(arm)]


def newc(B, u, b, rn, arm, q):
    """Per-block new commitments per case over the window by cells in age bin q."""
    run = D.RUNS[D.RUNNAMES.index(rn)]
    return B[(u, b)][f"{rn}/newc"][:, q, D.arms_of(run).index(arm)] * D.SIDE * D.SIDE


def loss(B, u, b, mu, arm):
    g = lambda a: blk(B, u, b, f"none8{mu}", a, "r_all") - blk(B, u, b, f"cue8{mu}", a, "r_all")
    return g(arm) - g("cue")


def m(x):
    return float(np.mean(x))


def r4(x):
    return round(float(x), 4)


def items(f):
    return {f"{u}/{b}": f(u, b) for u, b in ALL}


def every(d, test):
    return all(test(float(np.mean(v))) for v in d.values())


def means(d):
    return {k: r4(np.mean(v)) for k, v in d.items()}


def pooled(d):
    return float(np.mean([np.mean(v) for v in d.values()]))


def score(B):
    """Every statement's verdict and the values it read (unrounded inputs; rounded once here)."""
    S = {}
    rat, inst = {}, {}
    for mu in MUS:
        for s in ("none8", "cue8"):
            iso0 = {k: m(v) for k, v in items(lambda u, b: newc(B, u, b, f"{s}{mu}", "iso-3", 0)).items()}
            for tau in ("300", "1000"):
                rat[f"{s}{mu}/mat-{tau}"] = {k: m(v) / max(iso0[k], 1e-12)
                                             for k, v in items(lambda u, b: newc(B, u, b, f"{s}{mu}", f"mat-{tau}", 0)).items()}
            inst[f"{s}{mu}"] = {k: m(v) / max(iso0[k], 1e-12)
                                for k, v in items(lambda u, b: newc(B, u, b, f"{s}{mu}", "inst-3", 0)).items()}
    ok = all(TH["B1_lo"] <= x <= TH["B1_hi"] for d in rat.values() for x in d.values()) \
        and all(x <= TH["B1_inst"] for d in inst.values() for x in d.values())
    S["B1"] = {"verdict": "HOLDS" if ok else "FAILS",
               "ratio_mat_to_iso3_age0": {k: {i: r4(x) for i, x in d.items()} for k, d in rat.items()},
               "ratio_inst3_to_iso3_age0": {k: {i: round(x, 5) for i, x in d.items()} for k, d in inst.items()}}

    v = {mu: items(lambda u, b: blk(B, u, b, f"change4{mu}", "iso-3") - blk(B, u, b, f"change4{mu}", "inst-3")) for mu in MUS}
    ok = every(v[HI], lambda x: x >= TH["B2_item_hi"]) and pooled(v[HI]) >= TH["B2_mean_hi"] \
        and every(v[LO], lambda x: x >= TH["B2_item_lo"]) and pooled(v[LO]) >= TH["B2_mean_lo"]
    S["B2"] = {"verdict": "HOLDS" if ok else "FAILS", "iso3_minus_inst3_change4": {mu: means(d) for mu, d in v.items()},
               "mean": {mu: r4(pooled(d)) for mu, d in v.items()}}

    v = items(lambda u, b: blk(B, u, b, f"none8{HI}", "iso-3", "r_all") - blk(B, u, b, f"none8{HI}", "inst-3", "r_all"))
    ok = every(v, lambda x: x >= TH["B3_item"]) and every({k: x for k, x in v.items() if k.startswith("S4")},
                                                           lambda x: x >= TH["B3_s4"])
    S["B3"] = {"verdict": "HOLDS" if ok else "FAILS", "iso3_minus_inst3_none8_r_all": means(v)}

    e = {mu: items(lambda u, b: loss(B, u, b, mu, "iso-3") - loss(B, u, b, mu, "inst-3")) for mu in MUS}
    rate = items(lambda u, b: loss(B, u, b, HI, "iso-3") - loss(B, u, b, LO, "iso-3"))
    ok = every(e[HI], lambda x: x >= TH["B4_hi"]) and every(e[LO], lambda x: x >= TH["B4_lo"]) \
        and every(rate, lambda x: x >= TH["B4_rate"])
    S["B4"] = {"verdict": "HOLDS" if ok else "FAILS", "iso3_minus_inst3_extra_loss": {mu: means(d) for mu, d in e.items()},
               "iso3_extra_loss_1e-3_minus_2.5e-4": means(rate)}

    def d_iso(mu, t):
        return items(lambda u, b: trc(B, u, b, f"change4{mu}", "iso-3", t) - trc(B, u, b, f"change4{mu}", "inst-3", t))
    et = np.mean([pooled(d_iso(HI, t)) - pooled(d_iso(LO, t)) for t in PACE_T])
    eb = np.mean([pooled(d_iso(HI, t)) - pooled(d_iso(LO, 4 * t)) for t in PACE_T])
    ok = et - abs(eb) >= TH["B5_pace"]
    rf = np.mean([pooled(d_iso(HI, t)) for t in PACE_T])
    S["B5"] = {"verdict": "HOLDS" if ok else "FAILS", "equal_time": r4(et), "equal_births": r4(eb), "statistic": r4(et - abs(eb)),
               "reported_ratio_fast_to_slow": {"equal_time": r4(rf / np.mean([pooled(d_iso(LO, t)) for t in PACE_T])),
                                               "equal_births": r4(rf / np.mean([pooled(d_iso(LO, 4 * t)) for t in PACE_T]))}}

    lvl = pooled(items(lambda u, b: trc(B, u, b, f"change4{HI}", "emt-1000", 200) - trc(B, u, b, f"change4{HI}", "inst-3", 200)))
    grow = {}
    for tau in ("300", "1000"):
        grow[tau] = pooled(items(lambda u, b: (trc(B, u, b, f"change4{HI}", "iso-3", 2000) - trc(B, u, b, f"change4{HI}", "iso-3", 200))
                                 - (trc(B, u, b, f"change4{HI}", f"emt-{tau}", 2000) - trc(B, u, b, f"change4{HI}", f"emt-{tau}", 200))))
    ok = lvl >= TH["B6_emt_t200"] and all(g_ >= TH["B6_growth"] for g_ in grow.values())
    S["B6"] = {"verdict": "HOLDS" if ok else "FAILS", "emt1000_minus_inst3_t200": r4(lvl),
               "growth_iso3_minus_emt": {tau: r4(g_) for tau, g_ in grow.items()}}

    g = {}
    for mu in MUS:
        for tau in ("300", "1000"):
            g[f"change4{mu}/{tau}"] = items(lambda u, b: blk(B, u, b, f"change4{mu}", f"mat-{tau}") - blk(B, u, b, f"change4{mu}", f"iso-emt-{tau}"))
            g[f"extra_loss{mu}/{tau}"] = items(lambda u, b: loss(B, u, b, mu, f"mat-{tau}") - loss(B, u, b, mu, f"iso-emt-{tau}"))
            g[f"none8_r_all{mu}/{tau}"] = items(lambda u, b: blk(B, u, b, f"none8{mu}", f"mat-{tau}", "r_all")
                                                - blk(B, u, b, f"none8{mu}", f"iso-emt-{tau}", "r_all"))
    lim = {"change4": TH["B7_change4"], "extra_loss": TH["B7_extra_loss"], "none8_r_all": TH["B7_none8"]}
    ok = all(every(d, lambda x, q=k.split("@")[0]: abs(x) <= lim[q]) for k, d in g.items())
    S["B7"] = {"verdict": "HOLDS" if ok else "FAILS", "mat_minus_iso_emt": {k: means(d) for k, d in g.items()}}

    v = items(lambda u, b: (blk(B, u, b, f"change4{HI}", "iso-emt-1000") - blk(B, u, b, f"change4{HI}", "emt-1000"))
              - (blk(B, u, b, f"change4{HI}", "iso-3") - blk(B, u, b, f"change4{HI}", "inst-3")))
    S["B8"] = {"verdict": "HOLDS" if pooled(v) <= TH["B8_sub"] else "FAILS", "items": means(v), "mean": r4(pooled(v))}

    w = items(lambda u, b: blk(B, u, b, "regrow8@0", "iso-3") - blk(B, u, b, "regrow8@0", "inst-3"))
    mm = {tau: items(lambda u, b: blk(B, u, b, "regrow8@0", f"mat-{tau}") - blk(B, u, b, "regrow8@0", "iso-3")) for tau in ("300", "1000")}
    f0 = pooled({k: x for k, x in w.items() if k.startswith("F0")})
    ok = every({k: x for k, x in w.items() if k.startswith("S4")}, lambda x: x >= TH["B9_s4"]) and f0 >= TH["B9_f0"] \
        and all(every(d, lambda x: x <= TH["B9_mat"]) for d in mm.values())
    S["B9"] = {"verdict": "HOLDS" if ok else "FAILS", "iso3_minus_inst3": means(w), "F0_mean": r4(f0),
               "mat_minus_iso3": {tau: means(d) for tau, d in mm.items()}}

    sh = items(lambda u, b: (blk(B, u, b, "regrow8@0", "iso-3") - blk(B, u, b, "regrow8@0", "inst-3"))
               - (blk(B, u, b, "regrow+cue8@0", "iso-3") - blk(B, u, b, "regrow+cue8@0", "inst-3")))
    out = items(lambda u, b: blk(B, u, b, "regrow+cue8@0", "iso-3", "r_out") - blk(B, u, b, "regrow+cue8@0", "inst-3", "r_out"))
    ok = pooled(sh) >= TH["B10_shrink"] and every(out, lambda x: abs(x) <= TH["B10_out"])
    S["B10"] = {"verdict": "HOLDS" if ok else "FAILS", "shrink": means(sh), "shrink_mean": r4(pooled(sh)),
                "r_out_iso3_minus_inst3": {k: round(float(np.mean(x)), 5) for k, x in out.items()}}
    return S


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "statements": STATEMENTS}, indent=1) + "\n")
    print(f"wrote {out}")
