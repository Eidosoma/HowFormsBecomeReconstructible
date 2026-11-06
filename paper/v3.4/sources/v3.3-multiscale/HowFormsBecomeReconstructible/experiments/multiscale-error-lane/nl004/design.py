"""NL004: the single source of truth for the runner, the reader and the checks.

Anchors the tissue makes (REPORT_NL003.md's Next item 1; the PI's "lets go on both in parallel", 1 November 2026).
NL003 gated the hierarchy's descending pathway with a veto computed from sparse anchors holding history A's acquired
record signs, sign(R0_A): at one gain the faithful copy repaired and another history no longer overwrote (THEORY 8.30).
Those anchors were given. NL004 lets the tissue make them from its own state and measures what they carry.

The tissue is NL003's, imported unchanged (nl003.sim: the anchor sites, the liveness test and the gate; nl003.design's
rule T1q0.75r0; through it NL002's nested stores, units, histories, references, events, cap, endpoints and
successors). New:
  anchors   the same sites (a random quarter of the cells per case, nl003.sim.anchors under NL004's tag) and the same
            rule; only the values, and when they are made, differ. No anchor reads the codes or a template:
              A       sign(R0_A), NL003's given anchors; equal to the record's commitment at the branch (before the
                      event) in both units, since both start the branch from R0_A (bridge, not an arm)
              Mv      sign(V0_A), the acquired body's sign, made at the branch (none where V0_A = 0)
              Me      the record's sign just after the event, before the first descending increment (none where r = 0)
              Mt250, Mt1000   the record's sign at the end of update t_c; no anchors (no gate) before
              Mpre, Mmid      the sign of A's record during its acquisition (msegrid.acquire stopped after settle and k
                      teaching steps, no release: k 0, before the history; k 100, mid-acquisition); Mmidc as Mmid only
                      where that record is confident (|R| >= VMIN)
              S1e-2, S1e-3    slow copies: a(0) = A's; after every record step a <- a + eta (sign(r) - a); cue sign(a),
                      present where a != 0
            K kills the anchors in the killed square for every arm made before the kill (Me has none there: r = 0).
  change    (NL004's; not NL003's anchor-only change) at the branch the record, body and moving average in the regions
            where A and B differ are B's acquired ones (nl002.sim.acquire_history of B, the call prepare makes), L1's
            bonds the record's sign relations: the tissue carries B there. One run scored against A (a coherent
            corruption carried) and against B (a legitimate change): spec_B = -spec_A.
  successor a coded recipient gated by anchors the successor makes at birth from the record it inherits (sign(r) where
            r != 0, at the case's sites, fixed), beside NL002's record-only and coded recipients and NL003's gated one
            (the parent's given anchors, for A only).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

from nl003 import design as N3

TAG = "mse-nl004"
PROBE_TAG = "mse-p48"
STUDY = "NL004"
DEVELOPMENT_BLOCKS = tuple(range(910517, 910522)) + tuple(range(910594, 910600)) + tuple(range(910873, 910878))
IDENTITIES = {"probe": tuple(range(900129, 900133)), "preflight": (900133, 900134), "debug": (900135, 900136),
              "development": DEVELOPMENT_BLOCKS}
TUNING_BLOCKS = tuple(range(900125, 900129))               # assigned by the lead; no tuning, not drawn
SMOKE_BLOCKS = (900137, 900138)                            # the smoke and the tests
SPARE_BLOCKS = tuple(range(900186, 900192))
RESERVE_BLOCKS = (910523, 910524, 910525, 910527, 910862, 910863, 910864, 910865)   # held for the lead, not drawn
PURPOSE = {"probe": "engineering", "preflight": "engineering", "debug": "engineering", "smoke": "engineering",
           "development": "development"}
STAGE_TAG = {"probe": PROBE_TAG, "preflight": TAG, "debug": TAG, "smoke": TAG, "development": TAG}


def stage_blocks(stage):
    return list(IDENTITIES[stage]) if stage in IDENTITIES else list(SMOKE_BLOCKS[:1])


# NL003's tissue and rule, unchanged
SIDE, REGION, BLOCK, KC, CAP = N3.SIDE, N3.REGION, N3.BLOCK, N3.KC, N3.CAP
UNITS = N3.UNITS
WINDOW, READS, WINDOW2, READS2 = N3.WINDOW, N3.READS, N3.WINDOW2, N3.READS2
DENSITY, VMIN, RULE = N3.DENSITY, N3.VMIN, N3.RULE
GAINS = N3.GAINS                                           # 0.5, 0.75, 1 x KC
KSTAR = N3.KSTAR                                           # 0.75 x KC, the gain of the statements

# the anchors the tissue makes (PLAN_NL004.md; the clocks declared there before any NL004 tissue value)
T_C = {"Mt250": 250, "Mt1000": 1000}                       # NL002's first two reads: part and nearly all of the overwrite
ETA = {"S1e-2": 1e-2, "S1e-3": 1e-3}                       # a held anchor flips after ln 2 / eta: 69 and 693 updates
TEACH_K = {"Mpre": 0, "Mmid": 100, "Mmidc": 100}           # teaching steps before the commitment (of 1,000)
CONFIDENT = ("Mmidc",)                                     # made only where the record is confident (|R| >= VMIN)
ANCHORS = {
    "A": "sign(R0_A) at the sites (NL003's given anchors; = the record's commitment at the branch); K kills the square's",
    "Mv": "sign(V0_A), the acquired body, at the sites, none where V0_A = 0; K kills the square's",
    "Me": "sign(r) just after the event, before the first descending increment, none where r = 0",
    "Mt250": "sign(r) at the end of update 250, none where r = 0; no anchors before",
    "Mt1000": "sign(r) at the end of update 1,000, none where r = 0; no anchors before",
    "Mpre": "sign of A's record at the end of settle (msegrid.acquire, teach 0, release 0); K kills the square's",
    "Mmid": "sign of A's record after 100 teaching steps (msegrid.acquire, release 0); K kills the square's",
    "Mmidc": "as Mmid, only where that record is confident (|R| >= 0.2); K kills the square's",
    "S1e-2": "a slow copy: a(0) = A's (K: 0 in the square); after each record step a <- a + 0.01 (sign(r) - a)",
    "S1e-3": "a slow copy: a(0) = A's (K: 0 in the square); after each record step a <- a + 0.001 (sign(r) - a)"}
CODES = tuple(ANCHORS)
EVENTS = ("none", "R", "K", "change")


def kind(arb):
    """'off', 'given', 'branch' (made at or before the branch, fixed), 'after_event', 'late' or 'slow'."""
    if not arb:
        return "off"
    if arb == "A":
        return "given"
    if arb == "Me":
        return "after_event"
    if arb in T_C:
        return "late"
    if arb in ETA:
        return "slow"
    return "branch"


@dataclass(frozen=True)
class Arm:
    name: str
    ref: str           # copy | foreign | corrupt | off
    k2: float          # in units of KC
    k3: float          # in units of KC
    arb: str           # '' (off) or an anchor code in ANCHORS


def arm_name(ref, k2, arb=""):
    return "off" if ref == "off" else f"{ref}-k{k2:g}" + (f"+{arb}" if arb else "")


# the labels (PLAN_NL004.md's table): at KSTAR unless stated; the gain sweep 0.5 and 1 for off, A, Mv and S1e-3
EV_FULL = {"copy": ("none", "R", "K", "change"), "foreign": ("none", "K", "change"), "corrupt": ("none",)}
EV_MADE = {"copy": ("none", "R", "K"), "foreign": ("none", "K"), "corrupt": ("none",)}
EV_MAIN = {"copy": ("none", "R"), "foreign": ("none",), "corrupt": ("none",)}
EV_ME = {"copy": ("R", "change"), "foreign": ("change",)}
SWEEP = ("", "A", "Mv", "S1e-3")
PER_ARB = {"": EV_FULL, "A": EV_FULL, "Mv": EV_MADE, "Me": EV_ME, "Mt250": EV_MAIN, "Mt1000": EV_MAIN,
           "Mpre": EV_MAIN, "Mmid": EV_MAIN, "Mmidc": EV_MAIN, "S1e-2": EV_MADE, "S1e-3": EV_MADE}


def _arms_labels():
    arms, labels = {}, []

    def add(ref, k2, arb, events):
        a = Arm(arm_name(ref, k2, arb), ref, 0.0 if ref == "off" else k2, 0.0 if ref == "off" else 1.0, arb)
        arms[a.name] = a
        labels.extend((a.name, e) for e in events)
    add("off", 0.0, "", EVENTS)
    for arb, evs in PER_ARB.items():
        for ref, e in evs.items():
            add(ref, KSTAR, arb, e)
    for g in GAINS:
        if g == KSTAR:
            continue
        for arb in SWEEP:
            for ref, e in EV_MAIN.items():
                add(ref, g, arb, e)
    order = {e: i for i, e in enumerate(EVENTS)}
    labels = sorted(labels, key=lambda x: order[x[1]])          # event-major, arms in insertion order within an event
    assert len(set(labels)) == len(labels)
    return arms, tuple(labels)


ARMS, LABELS = _arms_labels()


def arms_labels(stage=None):
    return ARMS, LABELS


def recipient_labels(arms=ARMS, labels=LABELS):
    """The labels whose final records the successors read: off under none, and the copy and foreign references at KSTAR
    under none for the arbiter off and every anchor code that has them (21)."""
    return tuple(l for l in labels if l[1] == "none" and (arms[l[0]].ref == "off" or
                 (arms[l[0]].ref in ("copy", "foreign") and arms[l[0]].k2 == KSTAR)))


def parent_gated(arms, rlabels):
    """The recipient labels whose successor is also gated by the parent's given anchors (NL003's gated recipient)."""
    return tuple(l for l in rlabels if arms[l[0]].arb == "A")


def tasks():
    return [(u,) for u in UNITS]


def design_dict():
    rl = recipient_labels()
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "identities": IDENTITIES, "tuning_blocks": TUNING_BLOCKS,
            "smoke_blocks": SMOKE_BLOCKS, "spare_blocks": SPARE_BLOCKS, "reserve_blocks": RESERVE_BLOCKS,
            "purpose": PURPOSE, "stage_tag": STAGE_TAG, "nl003_digest": N3.digest(), "density": DENSITY, "vmin": VMIN,
            "rule": RULE, "gains": GAINS, "kstar": KSTAR, "anchors": ANCHORS, "t_c": T_C, "eta": ETA,
            "teach_k": TEACH_K, "confident": CONFIDENT, "events": EVENTS,
            "change": "B's acquired record, body and moving average in the regions where A and B differ; bonds from the record",
            "arms": [asdict(a) for a in ARMS.values()], "labels": LABELS, "recipients": rl,
            "parent_gated": parent_gated(ARMS, rl),
            "successor_anchors": "made at birth from the inherited record: sign(r) where r != 0, the case's sites, fixed",
            "window": WINDOW, "reads": READS, "window2": WINDOW2, "reads2": READS2}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    out = dict(N3.sources(lane))
    out.update({str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest()
                for f in sorted((lane / "nl004").glob("*.py"))})
    return out


if __name__ == "__main__":      # python -m nl004.design  ->  nl004/frozen/design.json (phase B, on the lead's word)
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "nl004" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
