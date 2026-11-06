"""NL003: the single source of truth for the runner, the reader and the checks.

A level that can tell (the open item of SYNTHESIS.md, "Scale that emerges"; the lead's recommendation, the PI's "lets
go as you recommendation", 31 October 2026). NL001 and NL002 found that across levels gain decides, not truth: at the
gain where the faithful copy repairs coherent region damage, another history's reference overwrites the intact tissue,
and no gain does one without the other (THEORY 8.24). AR002 and AR002C found that a tissue can make a regime signal from
an independent reference (THEORY 8.28). NL003 asks whether such a signal lets the descending pathway repair from a
faithful reference and refuse a wrong one, at one gain.

The tissue is NL002's, imported unchanged (nl002.sim: the 64 x 64 nested stores L1, L2, L3, the units 'none' and 'dw',
histories A and B acquired, the references, the events none, R and K, the cap, the successors, the endpoints). New:
  anchors   a declared positional cue, independent of the descending code: a random 1/DENSITY of the cells per case
            (lr004.sim.anchors' rule, addressed by (case, 'anchors', density) under NL003's tag), holding history A's
            acquired record signs sign(R0_A) (as AR001's anchors hold the acquired record's signs)
  arbiter   per region and update, AR002's coherence rule moved from 'the anchors against the record' to 'the anchors
            against the code': the code's target at a cell is sign(sigma Bg) (the direction of NL002's descending
            increment); a live anchor is present, sits where the record is confident (lr005.sim.vote_sign) and where
            the code has a target (sigma != 0); with n_l the region's live anchors and n_d those whose cue disagrees
            with the target, the region's L2 increment is refused while n_d >= n and n_d >= q n_l (and, for a rule with
            a surround, while at most ring_max disagreeing live anchors lie within ring sites around the region);
            otherwise admitted (a veto: no evidence admits). L3 is not gated (every reference's L3 is A's).
            nl002.sim.step is called unchanged with k2 replaced per site by k2 x G (G in {0, 1}); arbiter off: G = 1.
Events: NL002's none, R and K (K also removes the anchors in the killed square), and 'change', the information-limit
pair: the anchors in the regions where A and B differ respecified to B's acquired record signs (one run, scored
against A as a coherent corruption and against B as a legitimate change).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

from nl002 import design as N2

TAG = "mse-nl003"
PROBE_TAG = "mse-p46"
STUDY = "NL003"
DEVELOPMENT_BLOCKS = tuple(range(910746, 910752)) + tuple(range(910753, 910759)) + tuple(range(910762, 910766))
IDENTITIES = {"tuning": tuple(range(900430, 900434)), "probe": tuple(range(900488, 900492)),
              "preflight": (900492, 900493), "debug": (900494, 900495), "development": DEVELOPMENT_BLOCKS}
SMOKE_BLOCKS = (900496, 900497)                            # the smoke and the tests
SPARE_BLOCKS = (900498, 900499)
RESERVE_BLOCKS = tuple(range(910867, 910872))              # held for the lead, not drawn
PURPOSE = {"tuning": "engineering", "probe": "engineering", "preflight": "engineering", "debug": "engineering",
           "smoke": "engineering", "development": "development"}
STAGE_TAG = {"tuning": PROBE_TAG, "probe": PROBE_TAG, "preflight": TAG, "debug": TAG, "smoke": TAG, "development": TAG}


def stage_blocks(stage):
    return list(IDENTITIES[stage]) if stage in IDENTITIES else list(SMOKE_BLOCKS[:1])


# NL002's tissue, unchanged
SIDE, REGION, BLOCK, KC, CAP = N2.SIDE, N2.REGION, N2.BLOCK, N2.KC, N2.CAP
UNITS = N2.UNITS
WINDOW, READS, WINDOW2, READS2 = N2.WINDOW, N2.READS, N2.WINDOW2, N2.READS2

# the anchors and the arbiter
DENSITY = 4                                                # AR001's and AR002's: a quarter of the cells
DENSITY_SIDE = 16                                          # the side arm: one anchor a region on average
MISREAD_SIGMA = 1.0                                        # GC001's quenched misread, as AR002's side arm
VMIN = 0.2                                                 # a confident record (lr005.design.VMIN)
GAINS = (0.5, 0.75, 1.0)                                   # k2 in units of KC (NL002's 0.25 and 2 dropped)
KSTAR = 0.75                                               # the gain of the registered statements (NL002's switch)
REFS = ("copy", "foreign", "corrupt")
SURROUND = {"ring": 2, "ring_max": 0}                      # AR002's: no disagreeing live anchor within 2 sites

# the tuning rule (PLAN_NL003.md, fixed before any tuning ran): candidates and the choice
CANDIDATES = tuple({"n": n, "q": q, "ring": s["ring"], "ring_max": s["ring_max"]}
                   for n in (1, 2, 3) for q in (0.75, 1.0) for s in ({"ring": 0, "ring_max": 0}, SURROUND))
FALSE_REFUSAL_MAX, ALIGN_COST_MAX, TIE = 0.02, 0.01, 0.005
# the rule: P46a's choice under Amendment 2 (the lead's ruling, 31 October 2026, before P46): T1q0.75r0
RULE = {"n": 1, "q": 0.75, "ring": 0, "ring_max": 0}
# the reported arms (the lead's ruling): the first rule's choice (the surround) and AR002's n 2
SIDE_RULES = {"A2": {"n": 2, "q": 0.75, "ring": 0, "ring_max": 0},      # T2q0.75r0
              "Asur": {"n": 3, "q": 0.75, "ring": 2, "ring_max": 0}}    # T3q0.75r2
SIDE_ARBS = ("A2", "Asur", "As1", "A2s1", "A16", "A2d16")


def cand_name(c):
    return f"T{c['n']}q{c['q']:g}r{c['ring']}"


@dataclass(frozen=True)
class Arm:
    name: str
    ref: str           # copy | foreign | corrupt | off
    k2: float          # in units of KC
    k3: float          # in units of KC
    arb: str           # '' (off); 'A' the rule (density 1/4); reported: 'A2' (n 2), 'Asur' (the surround), 'As1' and
                       # 'A2s1' (misread anchors), 'A16' and 'A2d16' (density 1/16); or a tuning candidate's name


def gate_config(arb, rule=None):
    """The gate's parameters for an arm's arbiter code: (n, q, ring, ring_max, density, sigma), or None (off)."""
    rule = RULE if rule is None else rule
    if not arb:
        return None
    if arb.startswith("T"):
        c = next(x for x in CANDIDATES if cand_name(x) == arb)
        return {**c, "density": DENSITY, "sigma": 0.0}
    table = {"A": (rule, DENSITY, 0.0), "A2": (SIDE_RULES["A2"], DENSITY, 0.0), "Asur": (SIDE_RULES["Asur"], DENSITY, 0.0),
             "As1": (rule, DENSITY, MISREAD_SIGMA), "A2s1": (SIDE_RULES["A2"], DENSITY, MISREAD_SIGMA),
             "A16": (rule, DENSITY_SIDE, 0.0), "A2d16": (SIDE_RULES["A2"], DENSITY_SIDE, 0.0)}
    base, density, sigma = table[arb]
    return {**dict(base), "density": density, "sigma": sigma}


def arm_name(ref, k2, arb=""):
    return "off" if ref == "off" else f"{ref}-k{k2:g}" + (f"+{arb}" if arb else "")


def _arms_labels(stage):
    """The stage's arms and labels [(arm name, event)], event-major as NL002's."""
    arms, labels = {}, []

    def add(ref, k2, arb, events):
        a = Arm(arm_name(ref, k2, arb), ref, 0.0 if ref == "off" else k2, 0.0 if ref == "off" else 1.0, arb)
        arms[a.name] = a
        for e in events:
            labels.append((a.name, e))
    if stage == "tuning":
        add("off", 0.0, "", ("none",))
        add("copy", KSTAR, "", ("none", "R"))
        for ref in ("foreign", "corrupt"):
            add(ref, KSTAR, "", ("none",))
        for c in CANDIDATES:
            add("copy", KSTAR, cand_name(c), ("none", "R"))
            for ref in ("foreign", "corrupt"):
                add(ref, KSTAR, cand_name(c), ("none",))
    else:
        add("off", 0.0, "", ("none", "R", "K"))
        for ref in REFS:
            for g in GAINS:
                add(ref, g, "", ("none", "R", "K"))
        for ref in REFS:
            for g in GAINS:
                add(ref, g, "A", ("none", "R", "K", "change"))
        for side in SIDE_ARBS:                                  # reported, tissue only (no recipients)
            add("copy", KSTAR, side, ("none", "R"))
            for ref in ("foreign", "corrupt"):
                add(ref, KSTAR, side, ("none",))
    order = {e: i for i, e in enumerate(("none", "R", "K", "change"))}
    labels = sorted(labels, key=lambda x: order[x[1]])          # event-major, arms in insertion order within an event
    return arms, tuple(labels)


def arms_labels(stage):
    return _arms_labels("tuning" if stage == "tuning" else "main")


def recipient_labels(arms, labels):
    """The labels whose final records the recipients read: the arbiter off and the rule 'A' (the reported side arms and
    the tuning run in the tissue only)."""
    return tuple(l for l in labels if arms[l[0]].arb in ("", "A"))


def tasks():
    return [(u,) for u in UNITS]


def design_dict():
    arms, labels = arms_labels("main")
    tarms, tlabels = arms_labels("tuning")
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "identities": IDENTITIES, "smoke_blocks": SMOKE_BLOCKS,
            "spare_blocks": SPARE_BLOCKS, "reserve_blocks": RESERVE_BLOCKS, "purpose": PURPOSE, "stage_tag": STAGE_TAG,
            "nl002_digest": N2.digest(), "density": DENSITY, "density_side": DENSITY_SIDE, "misread_sigma": MISREAD_SIGMA,
            "vmin": VMIN, "gains": GAINS, "kstar": KSTAR, "refs": REFS, "surround": SURROUND, "candidates": CANDIDATES,
            "false_refusal_max": FALSE_REFUSAL_MAX, "align_cost_max": ALIGN_COST_MAX, "tie": TIE, "rule": RULE,
            "rule_from": "P46a under Amendment 2 (the lead's ruling, before P46): one-sided constraints, refusals reported",
            "side_rules": SIDE_RULES, "side_arbs": SIDE_ARBS, "recipients": "the arbiter off and the rule A only",
            "arms": [asdict(a) for a in arms.values()], "labels": labels,
            "tuning_arms": [asdict(a) for a in tarms.values()], "tuning_labels": tlabels,
            "anchors": "a random 1/density of the cells per case, (case, 'anchors', density); values sign(R0_A)",
            "gate": "per region and update: refuse L2 while n_d >= n and n_d >= q n_l (and the surround); else admit",
            "events": ("none", "R", "K", "change"), "window": WINDOW, "reads": READS, "window2": WINDOW2, "reads2": READS2}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    out = dict(N2.sources(lane))
    out.update({str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest()
                for f in sorted((lane / "nl003").glob("*.py"))})
    return out


if __name__ == "__main__":      # python -m nl003.design  ->  nl003/frozen/design.json (phase B, on the lead's word)
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "nl003" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
