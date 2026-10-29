"""BE005's registered statements and their scoring, written before any development outcome.

python -m be005.predict   (writes be005/frozen/predictions.json)

Thresholds were set from engineering probe P30 (32 cases on blocks 900620-900623 under tag mse-p30, disclosed in
REGISTRATION_BE005.md) under BE002's rule; probes/p30b_be005_margins.py prints every part, its SD over P30's four blocks
and the margin at these thresholds. Every part is pooled over the twelve unit-body pairs (the mean over them, scored on
unrounded block means), and its margin uses the SD over P30's four blocks of the pooled per-block value; M5's part is every
item (a pair of arms, pooled over the twelve pairs). A part needs >= 3 x sqrt(1/4 + 1/16) = 1.68 SDs between P30's value
and its threshold; where P30's SD is 0, or the registered static/relaxation map disagrees with P30, the bound follows the
map. Every part reads t = 4,000. Scored by be005.analyze on the 16 development blocks; a statement HOLDS when every one
of its parts passes.

Quantities (r_in: the patch's record against the target, the new one in a change):
  prompt(eta)    the dial-e{eta}'s r_in in memory4@0 (the signal at 1-1,000)
  late(eta, m)   the dial-e{eta}'s r_in in memory4@D, D = round(m T*(eta)), T*(eta) = ln(1.8) / -ln(1 - eta)
  none(eta)      never-e{eta}'s r_in in memory4@0 (the same tissue, the signal never on)
  loss(eta, m)   prompt(eta) - late(eta, m)
  sensors(eta,m) the share of the patch's anchored cells whose record is right at the delayed signal's first update
                 (per block: right over all)
  adopt(arm)     the arm's r_in in change4@0
  cost(tau)      never-tv{tau}'s r_all less dial-tv{tau}'s in cue4@0 (a prompt sham's cost to the sheet)
  repair(tau)    dial-tv{tau}'s r_in in memory4@0 (dial-tv1 is dial-e0.01)
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from be005 import design as D  # noqa: E402

ALL = tuple((u, b) for u in D.UNITS for b in D.BODIES)
STATIC = Path(__file__).resolve().parent / "frozen" / "static_map.json"
E5, E1_, E2 = "0.005", "0.01", "0.02"
THR = {"D1": {"early": 0.02},
       "D2": {"late": 0.05},
       "D3": {"raw": 0.05},
       "D4": {"extent": 0.02},
       "D5": {"intact": 0.05, "repaired": 0.15, "faster": 0.1},
       "D6": {"gain": 0.2},
       "M1": {"brief": 0.1, "same": 0.005},
       "M2": {"flick": 0.05, "same": 0.005},
       "M3": {"t10_t1": 0.05, "t100_t10": 0.05, "t100_t10_slow": 0.03},
       "M4": {"steady": 0.1, "race": 0.03},
       "M5": {"gap": 0.15, "order": 0.0},
       "M6": {"sham": 0.0005}}


def lv(L, u, b, rn, arm, e="r_in"):
    return L[u][b][rn][D.EQUIV.get(arm, arm) if arm not in L[u][b][rn] else arm][e][-1][0]


def sc(L, u, b, rn, arm, e):
    return L[u][b][rn][arm][e][0]


MEM0 = D.run_name("memory", 4, 0)
CHG = D.run_name("change", 4, 0)
CUE = D.run_name("cue", 4, 0)


def prompt(L, u, b, eta):
    return lv(L, u, b, MEM0, f"dial-e{eta}")


def late(L, u, b, eta, m):
    rn, arm = D.where(float(eta), m)
    return lv(L, u, b, rn, arm)


def none(L, u, b, eta):
    return lv(L, u, b, MEM0, f"never-e{eta}")


def loss(L, u, b, eta, m):
    return prompt(L, u, b, eta) - late(L, u, b, eta, m)


def sensors(L, u, b, eta, m):
    rn, arm = D.where(float(eta), m)
    return sc(L, u, b, rn, arm, "anc_on_share")


def adopt(L, u, b, arm):
    return lv(L, u, b, CHG, arm)


def cost(L, u, b, tau):
    return lv(L, u, b, CUE, f"never-tv{tau}", "r_all") - lv(L, u, b, CUE, f"dial-tv{tau}", "r_all")


def repair(L, u, b, tau):
    return lv(L, u, b, MEM0, f"dial-tv{tau}")


def part(stmt, name, items, threshold, sense, pooled, value):
    return {"stmt": stmt, "name": name, "items": tuple(items), "threshold": threshold, "sense": sense, "pooled": pooled,
            "value": value}


def relax_pairs():
    """M5's arm pairs: within tau_v 1 or 10, panel-M arms whose registered relaxation share is at least THR gap apart
    (at tau_v 100 the map omits the commitment's feedback and overstates the steady signal; P30 put that order's worst margin
    below the rule, so those pairs are reported, not registered)."""
    s = json.loads(STATIC.read_text())["relaxation"]
    out = []
    for tau in D.TAUS[:2]:
        st = s[str(tau)]
        names = {"dial": f"dial-tv{tau}", "never": f"never-tv{tau}",
                 **{f"t{d}": f"dial-t{d}-tv{tau}" for d in D.DURS}, **{f"f{D.fmt(p)}": f"dial-f{D.fmt(p)}-tv{tau}" for p in D.FLICKS}}
        for k1 in st:
            for k2 in st:
                if st[k1] - st[k2] >= THR["M5"]["gap"]:
                    out.append((names[k1], names[k2]))
    return tuple(out)


T = THR
E_ = (E5, E1_, E2)
PARTS = [
    *[part("D1", f"D1 late(e{e}, {m}) - prompt(e{e}) (pooled)", ALL, T["D1"]["early"], "abs", True,
           (lambda e_, m_: lambda L, u, b: -loss(L, u, b, e_, m_))(e, m)) for e in E_ for m in (0.5, 1)],
    *[part("D2", f"D2 late(e{e}, {m}) - prompt(e{e}) (pooled)", ALL, -T["D2"]["late"], "le", True,
           (lambda e_, m_: lambda L, u, b: -loss(L, u, b, e_, m_))(e, m)) for e in E_ for m in (2, 16)],
    part("D3", "D3 loss(e0.02, 2) - loss(e0.005, 0.5): delays 58 and 59 (pooled)", ALL, T["D3"]["raw"], "ge", True,
         lambda L, u, b: loss(L, u, b, E2, 2) - loss(L, u, b, E5, 0.5)),
    *[part("D4", f"D4 loss(e0.02, {m}) - loss(e0.005, {m}) (pooled)", ALL, T["D4"]["extent"], "ge", True,
           (lambda m_: lambda L, u, b: loss(L, u, b, E2, m_) - loss(L, u, b, E5, m_))(m)) for m in (2, 4, 16)],
    *[part("D5", f"D5 sensors(e{e}, {m}) (pooled)", ALL, T["D5"]["intact"], "le", True,
           (lambda e_, m_: lambda L, u, b: sensors(L, u, b, e_, m_))(e, m)) for e in E_ for m in (0.5, 1)],
    *[part("D5", f"D5 sensors(e{e}, 2) (pooled)", ALL, T["D5"]["repaired"], "ge", True,
           (lambda e_: lambda L, u, b: sensors(L, u, b, e_, 2))(e)) for e in E_],
    part("D5", "D5 sensors(e0.02, 4) - sensors(e0.005, 4) (pooled)", ALL, T["D5"]["faster"], "ge", True,
         lambda L, u, b: sensors(L, u, b, E2, 4) - sensors(L, u, b, E5, 4)),
    *[part("D6", f"D6 prompt(e{e}) - none(e{e}) (pooled)", ALL, T["D6"]["gain"], "ge", True,
           (lambda e_: lambda L, u, b: prompt(L, u, b, e_) - none(L, u, b, e_))(e)) for e in E_],
    *[part("M1", f"M1 adopt(dial-tv100) - adopt(dial-t{d}-tv100) (pooled)", ALL, T["M1"]["brief"], "ge", True,
           (lambda d_: lambda L, u, b: adopt(L, u, b, "dial-tv100") - adopt(L, u, b, f"dial-t{d_}-tv100"))(d)) for d in (1, 10)],
    part("M1", "M1 adopt(dial-t1-tv1) - adopt(dial-tv1) (pooled)", ALL, T["M1"]["same"], "abs", True,
         lambda L, u, b: adopt(L, u, b, "dial-t1-tv1") - adopt(L, u, b, "dial-tv1")),
    part("M2", "M2 adopt(dial-tv100) - adopt(dial-f0.25-tv100) (pooled)", ALL, T["M2"]["flick"], "ge", True,
         lambda L, u, b: adopt(L, u, b, "dial-tv100") - adopt(L, u, b, "dial-f0.25-tv100")),
    part("M2", "M2 adopt(dial-f0.25-tv1) - adopt(dial-tv1) (pooled)", ALL, T["M2"]["same"], "abs", True,
         lambda L, u, b: adopt(L, u, b, "dial-f0.25-tv1") - adopt(L, u, b, "dial-tv1")),
    part("M3", "M3 adopt(dial-t10-tv10) - adopt(dial-t1-tv10) (pooled)", ALL, T["M3"]["t10_t1"], "ge", True,
         lambda L, u, b: adopt(L, u, b, "dial-t10-tv10") - adopt(L, u, b, "dial-t1-tv10")),
    part("M3", "M3 adopt(dial-t100-tv10) - adopt(dial-t10-tv10) (pooled)", ALL, T["M3"]["t100_t10"], "ge", True,
         lambda L, u, b: adopt(L, u, b, "dial-t100-tv10") - adopt(L, u, b, "dial-t10-tv10")),
    part("M3", "M3 adopt(dial-t100-tv100) - adopt(dial-t10-tv100) (pooled)", ALL, T["M3"]["t100_t10_slow"], "ge", True,
         lambda L, u, b: adopt(L, u, b, "dial-t100-tv100") - adopt(L, u, b, "dial-t10-tv100")),
    part("M4", "M4 adopt(dial-tv1) - adopt(dial-tv100), change4@0 (pooled)", ALL, T["M4"]["steady"], "ge", True,
         lambda L, u, b: adopt(L, u, b, "dial-tv1") - adopt(L, u, b, "dial-tv100")),
    part("M4", "M4 repair(1) - repair(100), memory4@0 (pooled)", ALL, T["M4"]["steady"], "ge", True,
         lambda L, u, b: repair(L, u, b, 1) - repair(L, u, b, 100)),
    part("M4", "M4 (repair(1) - repair(100)) - (adopt(dial-tv1) - adopt(dial-tv100)) (pooled)", ALL, T["M4"]["race"], "abs", True,
         lambda L, u, b: (repair(L, u, b, 1) - repair(L, u, b, 100)) - (adopt(L, u, b, "dial-tv1") - adopt(L, u, b, "dial-tv100"))),
    part("M5", "M5 run adoption follows the relaxation map's order (pairs within tau_v 1 or 10 at least 0.15 apart)",
         relax_pairs(), T["M5"]["order"], "ge", False,
         lambda L, a1, a2: sum(adopt(L, u, b, a1) - adopt(L, u, b, a2) for u, b in ALL) / len(ALL)),
    *[part("M6", f"M6 cost({t}) - cost(1) (pooled)", ALL, T["M6"]["sham"], "le", True,
           (lambda t_: lambda L, u, b: cost(L, u, b, t_) - cost(L, u, b, 1))(t)) for t in (10, 100)],
]

CLAIM = {
    "D1": ("before the arbiter's clock runs out, a late signal repairs as a prompt one",
           "At each of the arbiter's three relearning rates, a signal that arrives half of T*(eta), or T*(eta), after a 4 x 4 "
           "memory damage repairs it within 0.02 of a prompt signal, on average",
           "HOLDS if for each eta in {{0.005, 0.01, 0.02}} and m in {{0.5, 1}}, on average over the twelve unit-body pairs at "
           "t = 4,000, the dial-e{{eta}}'s r_in in memory4@round(m T*(eta)) is within {early} of its r_in in memory4@0, else "
           "FAILS"),
    "D2": ("after it, a late signal repairs less",
           "At each of the three rates, a signal that arrives 2 or 16 times T*(eta) after the damage repairs it less than a "
           "prompt signal, by at least 0.05 on average",
           "HOLDS if for each eta in {{0.005, 0.01, 0.02}} and m in {{2, 16}}, on average over the twelve unit-body pairs at "
           "t = 4,000, the dial-e{{eta}}'s r_in in memory4@round(m T*(eta)) is below its r_in in memory4@0 by >= {late}, else "
           "FAILS"),
    "D3": ("measured in updates, the deadline differs with the rate",
           "A signal 58 updates late after the fastest arbiter (2 T*) loses more of its repair than one 59 updates late after "
           "the slowest (0.5 T*), by at least 0.05 on average",
           "HOLDS if on average over the twelve unit-body pairs at t = 4,000, loss(0.02, 2) exceeds loss(0.005, 0.5) by "
           ">= {raw}, where loss(eta, m) is the dial-e{{eta}}'s r_in in memory4@0 less its r_in in memory4@round(m T*(eta)), "
           "else FAILS"),
    "D4": ("past the deadline, a faster arbiter costs more",
           "At the same multiple of T*(eta) past the deadline (2, 4 and 16 times), the fastest arbiter costs a late signal "
           "more of its repair than the slowest, by at least 0.02 on average",
           "HOLDS if for each m in {{2, 4, 16}}, on average over the twelve unit-body pairs at t = 4,000, loss(0.02, m) "
           "exceeds loss(0.005, m) by >= {extent}, else FAILS"),
    "D5": ("the sensors keep the arbiter's clock",
           "When a delayed signal arrives, at most 5 per cent of the damaged patch's anchored cells have been repaired at "
           "half of T*(eta) or at T*(eta), and at least 15 per cent at twice T*(eta), at every rate; at four times T*(eta) "
           "the fastest arbiter has repaired at least 0.1 more of them than the slowest",
           "HOLDS if on average over the twelve unit-body pairs, the share of the patch's anchored cells whose record is "
           "right at the delayed signal's first update is <= {intact} at m = 0.5 and at m = 1 and >= {repaired} at m = 2 "
           "for every eta, and at m = 4 is larger for eta 0.02 than for 0.005 by >= {faster}, else FAILS"),
    "D6": ("a prompt signal still pays at every rate",
           "At each of the three rates, a prompt signal repairs at least 0.2 more of a 4 x 4 memory damage than the same "
           "tissue with no signal, on average",
           "HOLDS if for each eta in {{0.005, 0.01, 0.02}}, on average over the twelve unit-body pairs at t = 4,000, the "
           "dial-e{{eta}}'s r_in in memory4@0 exceeds never-e{{eta}}'s by >= {gain}, else FAILS"),
    "M1": ("under a slow membrane a brief signal fails",
           "With a membrane time constant of 100 updates, a signal on for only 1 or 10 updates adopts a 4 x 4 change less "
           "than a steady 1,000-update signal, by at least 0.1 on average; with potentials that settle at once, a 1-update "
           "signal adopts it within 0.005 of the steady one",
           "HOLDS if on average over the twelve unit-body pairs at t = 4,000 in change4@0, dial-tv100's r_in exceeds "
           "dial-t1-tv100's and dial-t10-tv100's by >= {brief} each, and dial-t1-tv1's is within {same} of dial-tv1's, "
           "else FAILS"),
    "M2": ("under a slow membrane a flickering signal adopts less",
           "With a membrane time constant of 100 updates, a signal on at a quarter of the updates adopts a 4 x 4 change "
           "less than a steady one, by at least 0.05 on average; with potentials that settle at once, within 0.005",
           "HOLDS if on average over the twelve unit-body pairs at t = 4,000 in change4@0, dial-tv100's r_in exceeds "
           "dial-f0.25-tv100's by >= {flick}, and dial-f0.25-tv1's is within {same} of dial-tv1's, else FAILS"),
    "M3": ("with a membrane, duration orders adoption",
           "With a membrane time constant of 10 updates, a signal on for 10 updates adopts a 4 x 4 change more than one on "
           "for 1, and one on for 100 more than one on for 10; with 100, one on for 100 updates more than one on for 10",
           "HOLDS if on average over the twelve unit-body pairs at t = 4,000 in change4@0, dial-t10-tv10's r_in exceeds "
           "dial-t1-tv10's by >= {t10_t1}, dial-t100-tv10's exceeds dial-t10-tv10's by >= {t100_t10}, and "
           "dial-t100-tv100's exceeds dial-t10-tv100's by >= {t100_t10_slow}, else FAILS"),
    "M4": ("a slow membrane makes a steady signal do less, against a change and a memory damage alike",
           "With a membrane time constant of 100 updates, a steady prompt signal adopts a 4 x 4 change and repairs a 4 x 4 "
           "memory damage less than with potentials that settle at once, by at least 0.1 each on average, and the two "
           "shortfalls differ by at most 0.03",
           "HOLDS if on average over the twelve unit-body pairs at t = 4,000, dial-tv1's r_in in change4@0 exceeds "
           "dial-tv100's by >= {steady}, dial-tv1's r_in in memory4@0 exceeds dial-tv100's by >= {steady}, and the two "
           "differences differ by at most {race}, else FAILS"),
    "M5": ("the relaxation map orders the signals",
           "With a membrane time constant of 1 or 10 updates, wherever the relaxation map registered before the run gives "
           "one signal a share of a 4 x 4 change below threshold at least 0.15 above another's under the same time constant, "
           "the run adopts the change at least as much with the first",
           "HOLDS if for every pair of panel-M arms with tau_v 1 or with tau_v 10 whose registered relaxation share "
           "differs by >= {gap}, the first's pooled r_in in change4@0 at t = 4,000 (over the twelve unit-body pairs) is >= "
           "the second's, else FAILS"),
    "M6": ("a slow membrane does not raise a steady sham's cost",
           "Under scattered cue corruption, a steady prompt sham costs the sheet's record no more, beyond 0.0005, with a "
           "membrane time constant of 10 or 100 updates than with potentials that settle at once, on average",
           "HOLDS if on average over the twelve unit-body pairs at t = 4,000 in cue4@0, cost(10) - cost(1) and cost(100) - "
           "cost(1) are each <= {sham}, where cost(tau) is never-tv{{tau}}'s r_all less dial-tv{{tau}}'s, else FAILS"),
}
STATEMENTS = [{"id": k, "kind": v[0], "claim": v[1], "rule": v[2].format(**THR[k]), "thresholds": THR[k]} for k, v in CLAIM.items()]


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs)


def passes(x, threshold, sense):
    return {"ge": x >= threshold, "le": x <= threshold, "abs": abs(x) <= threshold}[sense]


def score(L):
    S = {}
    for s in STATEMENTS:
        out, ok = {}, True
        for p in (q for q in PARTS if q["stmt"] == s["id"]):
            vals = {"/".join(map(str, it)): p["value"](L, *it) for it in p["items"]}
            if p["pooled"]:
                x = mean(vals.values())
                good = passes(x, p["threshold"], p["sense"])
                out[p["name"]] = {"pooled": x, "pass": good, "items": vals}
            else:
                good = all(passes(x, p["threshold"], p["sense"]) for x in vals.values())
                out[p["name"]] = {"pass": good, "items": vals}
            ok &= good
        S[s["id"]] = {"verdict": "HOLDS" if ok else "FAILS", "parts": out}
    return S


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "frozen" / "predictions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"status": "FROZEN_BEFORE_DEVELOPMENT_OUTCOMES", "design_digest": D.digest(),
                               "computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "static_map": json.loads(STATIC.read_text()), "thresholds": THR,
                               "parts": [{k: v for k, v in p.items() if k != "value"} for p in PARTS],
                               "statements": STATEMENTS}, indent=1, default=list) + "\n")
    print(f"wrote {out}")
