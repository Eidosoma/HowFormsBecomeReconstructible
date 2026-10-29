"""FN001's statements and their scoring (DRAFT, not frozen), written before any development outcome.

python -m fn001.predict   (at the freeze: writes fn001/frozen/predictions.json)

Thresholds were set from engineering probe P21b (32 cases on blocks 900770-900773 under tag mse-p21, disclosed in
REGISTRATION_FN001.md), with margins for 128 cases. Scored by fn001.analyze on block means over the 16 development
blocks. The first wound falls after t = 1,000 (the pre-wound baseline is the read at t = 1,000), the second after
t = 2,000; t = 2,000 reads the repair of the first wound, t = 3,000 the repair of the second. 'patch' is the body's
agreement with the template in the current wound; 'r_patch' the record's; 'intact' the share of sheets whose large
domains match the template's in number for each sign; 'defects' the count mismatch plus small islands. W12: wounded twice
at the same place; W2: naive tissue wounded once at that place.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fn001 import design as D  # noqa: E402

T0, T1, T2 = D.T_W1, D.T_W2, D.READS[-1]
NAMES = [c.name for c in D.CONDS]
RATES = tuple(f"{r:g}" for r in D.RATES)

STATEMENTS = [
    {"id": "F1", "kind": "appearance hides broken function",
     "claim": "Where the body does not make the pattern, a killed patch leaves the sheet looking whole while its stripes "
              "are broken or bridged",
     "rule": "HOLDS if for stripes on the double well (S4, dw) at theta x0 and p_b = 0, under every teacher, the pre-wound "
             "baseline is intact >= 0.95 and, after the first wound (t = 2,000), sign >= 0.96 while intact <= 0.55, "
             "else FAILS",
     "inputs": "P21b: baseline intact 1.000; sign 0.974-0.981; intact 0.156-0.375"},
    {"id": "F2", "kind": "function without full registration",
     "claim": "Where the body makes the pattern, it restores the wounded sheet's structure while part of the wound stays "
              "out of register",
     "rule": "HOLDS if for stripes on the stripe body (S4, li4) at theta x0 under body teaching at p_b = 0 and 1e-3, after "
             "the first wound (t = 2,000), intact >= 0.80 and defects <= 0.25 while patch <= 0.95, else FAILS",
     "inputs": "P21b: intact 0.906, 0.938; defects 0.094, 0.062; patch 0.906, 0.913"},
    {"id": "F3", "kind": "a re-injured labyrinth repairs worse",
     "claim": "On the labyrinth, a second wound at the place of the first repairs worse than the same wound in naive "
              "tissue",
     "rule": "HOLDS if for LB at theta x0 under body teaching, at t = 3,000, W12 - W2 in patch is <= -0.01 at every rate "
             "on both bodies and its mean over the six is <= -0.03, else FAILS",
     "inputs": "P21b: dw -0.053, -0.056, -0.085; li4 -0.036, -0.042, -0.025; mean -0.050"},
    {"id": "F4", "kind": "no scar where the body makes stripes",
     "claim": "On stripes the stripe body makes, a second wound at the same place repairs as well as in naive tissue",
     "rule": "HOLDS if for S4 on li4 at theta x0 under body teaching and the site gate, at t = 3,000, W12 - W2 in patch "
             "is >= -0.02 at every rate, else FAILS",
     "inputs": "P21b: body +0.009 to +0.012; site +0.000 to +0.013"},
    {"id": "F5", "kind": "shared damage defeats the vote",
     "claim": "When a wound kills both records, the two damaged records outvote the body inside it: the vote repairs the "
              "wound far worse than body teaching (LR005 tests shared damage in general)",
     "rule": "HOLDS if on li4 at theta x0, after the first wound (t = 2,000), the vote's patch is <= body teaching's "
             "- 0.10 for S4 and LB at every rate, and for S4 the vote's intact is <= body teaching's - 0.25 at every "
             "rate, else FAILS",
     "inputs": "P21b: S4 -0.210 to -0.222, LB -0.178 to -0.210; intact S4 -0.469 to -0.563"},
    {"id": "F6", "kind": "the memory stays lost under a restored body",
     "claim": "A record that relearns only from itself never recovers the killed patch, even where the body rebuilds "
              "it; a record taught by the stripe body does",
     "rule": "HOLDS if record+parity's r_patch at t = 2,000 is <= 0.56 in every unit, body and rate, while body teaching's "
             "on S4, li4, theta x0 is >= 0.85 at every rate, else FAILS",
     "inputs": "P21b: 0.501-0.526; 0.905-0.928"},
    {"id": "F7", "kind": "coarse domains heal in function",
     "claim": "Two domains on the double well, whose physics holds them, recover their structure after a kill under "
              "every teacher",
     "rule": "HOLDS if for F0 on dw at theta x0 the pre-wound baseline is intact >= 0.95 and intact at t = 2,000 is "
             ">= 0.85 under every teacher and rate, else FAILS",
     "inputs": "P21b: baseline 1.000; 0.938-1.000"},
    {"id": "F8", "kind": "under the field, a wound adds defects to a broken baseline",
     "claim": "Under the environmental field, where the sheet is already imperfect before any wound, a kill still adds "
              "lasting defects",
     "rule": "HOLDS if for S4 and LB at theta x1 on both bodies under body teaching at p_b = 0 and 1e-3, defects at "
             "t = 2,000 minus the pre-wound baseline at t = 1,000 is >= 0.15, else FAILS",
     "inputs": "P21b: S4 1.03-1.50, LB 0.34-0.62; baselines 0.09-1.69"},
]


def lv(L, unit, body, ep, t, cond):
    return L[unit][body][ep]["mean"][D.READS.index(t)][NAMES.index(cond)]


def score(L):
    S = {}
    reps = D.REPAIRS
    base = {rep: lv(L, "S4_t0", "dw", "intact", T0, f"0/{rep}/W12") for rep in reps}
    lev = {rep: {"sign": lv(L, "S4_t0", "dw", "sign", T1, f"0/{rep}/W12"),
                 "intact": lv(L, "S4_t0", "dw", "intact", T1, f"0/{rep}/W12")} for rep in reps}
    ok = all(base[r] >= 0.95 and lev[r]["sign"] >= 0.96 and lev[r]["intact"] <= 0.55 for r in reps)
    S["F1"] = {"verdict": "HOLDS" if ok else "FAILS", "baseline_intact": base, "after_first_wound": lev}

    v = {r: {ep: lv(L, "S4_t0", "li4", ep, T1, f"{r}/body/W12") for ep in ("intact", "defects", "patch")} for r in ("0", "0.001")}
    ok = all(x["intact"] >= 0.80 and x["defects"] <= 0.25 and x["patch"] <= 0.95 for x in v.values())
    S["F2"] = {"verdict": "HOLDS" if ok else "FAILS", "S4_t0/li4/body": v}

    d = {f"{b}/{r}": round(lv(L, "LB_t0", b, "patch", T2, f"{r}/body/W12") - lv(L, "LB_t0", b, "patch", T2, f"{r}/body/W2"), 4)
         for b in D.BODIES for r in RATES}
    mean = round(sum(d.values()) / len(d), 4)
    S["F3"] = {"verdict": "HOLDS" if max(d.values()) <= -0.01 and mean <= -0.03 else "FAILS", "W12_minus_W2": d, "mean": mean}

    d = {f"{rep}/{r}": round(lv(L, "S4_t0", "li4", "patch", T2, f"{r}/{rep}/W12") - lv(L, "S4_t0", "li4", "patch", T2, f"{r}/{rep}/W2"), 4)
         for rep in ("body", "site") for r in RATES}
    S["F4"] = {"verdict": "HOLDS" if min(d.values()) >= -0.02 else "FAILS", "W12_minus_W2": d}

    dp = {f"{p}/{r}": round(lv(L, f"{p}_t0", "li4", "patch", T1, f"{r}/vote/W12") - lv(L, f"{p}_t0", "li4", "patch", T1, f"{r}/body/W12"), 4)
          for p in ("S4", "LB") for r in RATES}
    di = {r: round(lv(L, "S4_t0", "li4", "intact", T1, f"{r}/vote/W12") - lv(L, "S4_t0", "li4", "intact", T1, f"{r}/body/W12"), 4)
          for r in RATES}
    S["F5"] = {"verdict": "HOLDS" if max(dp.values()) <= -0.10 and max(di.values()) <= -0.25 else "FAILS",
               "vote_minus_body_patch": dp, "S4_vote_minus_body_intact": di}

    rp = {f"{u}/{b}/{r}": lv(L, u, b, "r_patch", T1, f"{r}/record+parity/W12") for u in D.UNITS for b in D.BODIES for r in RATES}
    bt = {r: lv(L, "S4_t0", "li4", "r_patch", T1, f"{r}/body/W12") for r in RATES}
    S["F6"] = {"verdict": "HOLDS" if max(rp.values()) <= 0.56 and min(bt.values()) >= 0.85 else "FAILS",
               "record+parity_max": max(rp.values()), "record+parity_min": min(rp.values()), "body_S4_t0_li4": bt}

    base = {rep: lv(L, "F0_t0", "dw", "intact", T0, f"0/{rep}/W12") for rep in reps}
    after = {f"{rep}/{r}": lv(L, "F0_t0", "dw", "intact", T1, f"{r}/{rep}/W12") for rep in reps for r in RATES}
    S["F7"] = {"verdict": "HOLDS" if min(base.values()) >= 0.95 and min(after.values()) >= 0.85 else "FAILS",
               "baseline_intact": base, "intact_after_first_wound": after}

    d = {f"{p}/{b}/{r}": round(lv(L, f"{p}_t1", b, "defects", T1, f"{r}/body/W12") - lv(L, f"{p}_t1", b, "defects", T0, f"{r}/body/W12"), 4)
         for p in ("S4", "LB") for b in D.BODIES for r in ("0", "0.001")}
    bl = {f"{p}/{b}/{r}": lv(L, f"{p}_t1", b, "defects", T0, f"{r}/body/W12") for p in ("S4", "LB") for b in D.BODIES for r in ("0", "0.001")}
    S["F8"] = {"verdict": "HOLDS" if min(d.values()) >= 0.15 else "FAILS", "defects_added": d, "baseline_defects": bl}
    return S


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "statements": STATEMENTS}, indent=1) + "\n")
    print(f"wrote {out}")
