"""NP002: spacing conflicts, and where the phase race turns. The single source of truth for the runner, the reader and the
checks.

NP001 (REPORT_NP001.md) found, in LR002's tissue (DL001's bodies reading a record of relations at gain 0.2, no coarse
code, bond-sign noise, relearning from the body or from the record with parity, a 32-site sheet, quiet tissue), that a
record wins every phase conflict at the same spacing, even when its bonds are relearned from the body, and that no body
in DL001's set imposes a spacing other than 8 on this sheet. NP002 asks two things NP001 left open.

Spacing conflicts (panel S). A body whose present pattern differs from the record's history in spacing, not phase:
  C84   the body, its moving average and theta from S8's acquisition (period-16 stripes), the record and the history
        from S4's (period 8)
  C48   the body from S4's acquisition, the record and the history from S8's
S4 and S8 agree in sign on exactly half the sheet in every case (checks Q7), so the preference
q = (align - align_b) / (1 - a0) with a0 = 1/2 is +1 at the record's pattern and -1 at the body's initial one, as NP001's
phase preference (a0 = 1 - K/4) is for C4sK. The engineering smokes (fork S, 29 October 2026, block 900520;
probes/p32s_np002_smoke_*.py) searched DL001's lateral-inhibition family for a body that imposes period 16
(alpha_for(L, K16) x 1-2, L 2-16): every setting holds S8, and none erases period-8 stripes (case means 0.75-0.84 after
16,000 updates; of eight sheets three keep the stripes exactly, three coarsen to spacing about 10, two convert toward
13-18). The lead accepted that no new body form be made. In this family no body erases period-8 stripes, so NP002's
spacing conflicts pit a body's present period, and li2's and li4's preference for 8, against a record of the other
period, on DL001's bodies:
  li2, li4   prefer period 8: in C48 the record's period opposes both the body's present period and its preference;
             in C84 the record's period is the body's preference
  li16       holds period-16 stripes and wears period-8 stripes down only part of the way
  dw         permissive
Each spacing conflict runs NP001's stage 1 (six conditions at gain 0.2) and stage 2 (newborns of each kind reading the
five handed records, protected, and the paired no-record control).

The phase race (panel R). NP001's phase conflicts C4s1-C4s3 (the body at S4's phase 0, the record at phase K) and the
two spacing conflicts, each under the record read at lower gains g in RACE_GAINS, protected ('intact@g': no bond noise,
no relearning) and relearned from the body ('body@g': bond noise 1e-2, LR002's body repair), beside NP001's six
conditions at gain 0.2. The protected arm gives the gain at which a record the body cannot write switches the body;
the relearned arm, the gain at which the record still wins the race against relearning. Stage 1 only for C4sK.

Every branch of one case shares its acquisition and its three noise streams (the body's, the record's and the bonds'),
so gains and conditions are paired within a case. Templates reach only the record's acquisition and the scoring.
"""
from __future__ import annotations

import hashlib
import json

from dl001 import design as DL
from np001 import design as N1

TAG = "mse-np002"
PROBE_TAG = "mse-p32"
STUDY = "NP002"
IDENTITIES = {
    "preflight": (900528, 900530),     # engineering: full-shape qualification, timing, reader dry run
    "development": (910340, 910356),   # the NP002 cohort: 16 fresh source blocks
}
PURPOSE = {"preflight": "engineering", "development": "development"}
DEBUG_BLOCKS = (900530, 900532)
PROBE_BLOCKS = (900520, 900524)       # engineering probe P32 (tag mse-p32), before the freeze; 900520 also the smokes'


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


MESSAGES, PARENTS, NCASE = N1.MESSAGES, N1.PARENTS, N1.NCASE
SIDE, SIGMA, CHUNK = N1.SIDE, N1.SIGMA, N1.CHUNK
EPS, KR, SIGMA_R, KC = N1.EPS, N1.KR, N1.SIGMA_R, N1.KC
GAIN, STRENGTH0, ETA = N1.GAIN, N1.STRENGTH0, N1.ETA
THETA = N1.THETA
BODIES = ("dw", "li2", "li4", "li16")
PHASE = ("C4s1", "C4s2", "C4s3")
SPACING = ("C84", "C48")
UNITS = PHASE + SPACING
PAIRS = {"C4s1": ("S4", "S4s1"), "C4s2": ("S4", "S4s2"), "C4s3": ("S4", "S4s3"),   # (the body's pattern, the record's)
         "C84": ("S8", "S4"), "C48": ("S4", "S8")}
A0 = {"C4s1": 0.75, "C4s2": 0.5, "C4s3": 0.25, "C84": 0.5, "C48": 0.5}               # sign agreement of the two templates
B0 = {"C4s1": 0.75, "C4s2": 0.75, "C4s3": 0.75, "C84": 0.9375, "C48": 0.9375}       # agreement of their relations (bonds)

Cond = N1.Cond
RACE_GAINS = (0.1, 0.05, 0.02, 0.01, 0.005)
RACE = tuple(c for g in RACE_GAINS for c in (Cond(f"intact@{g:g}", g, 0.0, "none"), Cond(f"body@{g:g}", g, 0.01, "body")))
CONDS = N1.CONDS + RACE                                     # NP001's six at gain 0.2, then the race pairs by gain
CONDNAMES = tuple(c.name for c in CONDS)
HANDED = N1.HANDED                                          # the records handed to successors (spacing conflicts only)
SUCC_BODIES = BODIES
WINDOW, READS = N1.WINDOW, N1.READS
WINDOW2, READS2 = N1.WINDOW2, N1.READS2


def gain_of(name):
    """The read gain of a stage-1 condition: 0.2 for NP001's, g for 'intact@g' and 'body@g' ('alone' reads nothing)."""
    return CONDS[CONDNAMES.index(name)].gain


def has_successors(unit):
    return unit in SPACING


def tasks():
    return [(b, u) for b in BODIES for u in UNITS]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "identities": IDENTITIES, "purpose": PURPOSE,
            "debug_blocks": DEBUG_BLOCKS, "probe_blocks": PROBE_BLOCKS, "messages": MESSAGES, "parents": PARENTS,
            "preparation": "np001.sim.prepare of each pattern (DL002's acquisition and templates; S4sX the same "
                           "acquisition teaching S4 rolled X sites): the body, moving average and theta of the first "
                           "pattern of PAIRS[unit], the record and the history of the second",
            "side": SIDE, "sigma": SIGMA, "chunk": CHUNK, "eps": EPS, "kr": KR, "sigma_r": SIGMA_R, "kc": KC,
            "gain": GAIN, "strength0": STRENGTH0, "eta": ETA, "theta": THETA,
            "bodies": {b: list(DL.BODIES[b]) for b in BODIES}, "units": UNITS, "pairs": PAIRS, "a0": A0, "b0": B0,
            "conds": [[c.name, c.gain, c.rate, c.repair] for c in CONDS], "race_gains": RACE_GAINS,
            "handed": [c.name for c in HANDED], "successor_bodies": SUCC_BODIES, "successor_units": SPACING,
            "window": WINDOW, "reads": READS, "window2": WINDOW2, "reads2": READS2}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted([*(lane / "mse").glob("*.py"), *(lane / "br001").glob("*.py"), *(lane / "msegrid").glob("*.py"),
                    *(lane / "dl001").glob("*.py"), *(lane / "dl002").glob("*.py"), *(lane / "lr001").glob("*.py"),
                    *(lane / "lr002").glob("*.py"), *(lane / "np001").glob("*.py"), *(lane / "np002").glob("*.py")])
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m np002.design  ->  np002/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "np002" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
