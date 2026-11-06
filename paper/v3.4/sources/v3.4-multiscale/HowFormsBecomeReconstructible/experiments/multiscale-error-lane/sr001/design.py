"""SR001: the single source of truth for the runner, the reader and the checks.

Serial renewal against the body's preference (the v2.5 review's experiment 5; NP001's next step 3). Does an acquired
pattern, or an acquired phase, survive repeated renewal by fresh bodies that would make something else, and where along
the bond-noise axis does each way of maintaining the record stop working?

The tissue: NP001's. LR002's record of relations is read at gain 0.2 with no coarse code by DL001's bodies, after DL002's
acquisition (np001.sim.prepare, unchanged and imported), on the 32-site sheet in quiet tissue. The relations' update is
lr004.sim.relations, unchanged, which carries every route here (no repair, record+parity, body and LR004's three-copy
vote); the body's update is dl001.sim.body, unchanged.

A lineage. G0 is DL002's acquisition of the unit's pattern (the record R0 and its bonds). Renewal g = 1..GENS: a newborn
body of the lineage's kind, born from noise (msegrid.core.birth), reads the incoming record at its route's gain for one
generation of T_GEN updates under bond noise and its route's maintenance; the record it leaves is the next packet;
everything else is erased (the body, its moving average and the bonds' continuous strengths, which restart at
STRENGTH0 x sign as in NP001's handoff).

The packet, declared: the record's cell values r and its bond signs H, W (NP001's handoff to a successor: 1,024 values
and 2,048 signs). The vote route's packet holds two such records (counted as twice the content). Nothing of the body
crosses. A record of relations holds a pattern only up to its global sign (NP001's dated note), so every alignment is
scored inversion-invariant as well.

Routes (branches of one lineage, paired: every route shares the case's births and noise in every generation):
  protected  no bond noise, no relearning, no parity: the record steps through its bonds (the upper bound; also 'no
             write', since the record is never rewritten)
  exposed@p  bond noise p and no repair: a copy exposed to the same corruption (at 1e-3 only: it randomises within one
             generation even there, P39's timing smoke)
  body@p     bond noise p, the bonds relearned from the body's co-activity (LR002's 'body')
  parity@p   bond noise p, the bonds relearned from the record's co-activity with plaquette parity (LR001's two layers;
             LR002's 'record+parity')
  vote@p     bond noise p and a second record with its own noise streams; both records relearn each bond toward the
             majority of the body's and the two records' relations (LR004's 'vote'); the body reads the first record
  noread     body@1e-3 with the record never read (gain 0): the body's own dynamics write the record
with p = 1e-3, 3e-3 and 1e-2 for body, parity and vote (matched across routes).

Bodies (BODY_KINDS): DL001's dw (permissive), li2 and li4 (imposing period 8), li16 (permissive on this sheet), and
li16n, li16 with a notch inhibitor at period 8 (the body search, probes/p39s_sr001_body_search.py); BODIES are the ones
the study runs.
Patterns: S4 at two phases (S4 and S4s2, NP001's units; the history is the phase), S8 (period-16 stripes) and F0 (two
domains). S4s1 and S4s3 were dropped for cost (P39's timing smoke): with the foreign placements below, one phase already
measures phase specificity, and the second checks that nothing depends on the absolute phase.
Scoring: each read compares the record r and the body V with the unit's own template T and with three foreign
placements of it, T rolled across its stripes by 1/8, 1/4 and 3/8 of its period (S4: 1, 2, 3 sites; S8: 2, 4, 6; F0: 4,
8, 12). The history specificity q = (a - max_f a_f) / (1 - c), with a = max(align, 1 - align) the inversion-invariant
agreement and c the largest inversion-invariant agreement between T and a foreign placement (0.75 for every unit).
Fresh recipients: after G16 a newborn of each kind in BODIES, born from noise, reads each route's G16 record at gain 0.2
with the record protected (np001.sim.successor's arithmetic), beside the same newborn reading nothing (gain 0).
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from dl001 import design as DL
from lr004 import design as L4
from np001 import design as N1

TAG = "mse-sr001"
PROBE_TAG = "mse-p39"
STUDY = "SR001"
IDENTITIES = {
    "preflight": (900940, 900942),     # engineering: full-shape qualification, timing, reader dry run
    "development": (910560, 910576),   # the SR001 cohort: 16 fresh source blocks
}
PURPOSE = {"preflight": "engineering", "development": "development"}
DEBUG_BLOCKS = (900942, 900944)       # the engine reserves 900000-900999 for engineering; 900936-900943 scanned free (the lead)
PROBE_BLOCKS = (900936, 900940)       # engineering probe P39 (tag mse-p39) and the body search, before the freeze


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
assert (EPS, KR, SIGMA_R, KC, GAIN, STRENGTH0, ETA, SIDE, SIGMA, CHUNK) == (
    L4.EPS, L4.KR, L4.SIGMA_R, L4.KC, L4.GAIN, L4.STRENGTH0, L4.ETA, L4.SIDE, L4.SIGMA, L4.CHUNK)
SOURCES = L4.SOURCES
THETA = 0.0                                                    # quiet tissue only

# li16n: li16 plus a notch inhibitor at period 8, beta exp(-(k - K8)^2 / (2 w^2)) on the lattice Laplacian's eigenvalue
NOTCH = {"li16n": ("li16", 0.5, 0.1)}                          # body: (base body, beta, w): the body search P39s chose
# the smallest beta (then the narrower w) that, alone, holds S8 (1.000), erases S4 (0.494) and forms spacing 14.3
BODY_KINDS = ("dw", "li2", "li4", "li16") + tuple(NOTCH)
BODIES = ("dw", "li4", "li16n")                                # permissive, imposing period 8, imposing period 16
IMPOSES = {"dw": None, "li2": 8, "li4": 8, "li16": None, "li16n": 16}
PATTERNS = ("S4", "S4s2", "S8", "F0")
PERIOD = {"S4": 8, "S4s2": 8, "S8": 16, "F0": 32}
RATES = (0.001, 0.003, 0.01)


@dataclass(frozen=True)
class Route:
    name: str
    rate: float
    source: str        # '' (no relearning) | record | body | vote
    parity: bool
    gain: float

    @property
    def two(self):
        return self.source == "vote"


ROUTES = (Route("protected", 0.0, "", False, GAIN),
          Route("exposed@0.001", 0.001, "", False, GAIN),
          *(Route(f"body@{p:g}", p, "body", False, GAIN) for p in RATES),
          *(Route(f"parity@{p:g}", p, "record", True, GAIN) for p in RATES),
          *(Route(f"vote@{p:g}", p, "vote", False, GAIN) for p in RATES),
          Route("noread", 0.001, "body", False, 0.0))
ROUTENAMES = tuple(r.name for r in ROUTES)
GENS, T_GEN = 16, 2000                                         # 16 renewals of 2,000 updates each
GEN_READS = tuple(range(1, GENS + 1))                          # every generation's last update
WINDOW2, READS2 = N1.WINDOW2, N1.READS2                        # the fresh recipients: 2,000 updates, reads 500/1,000/2,000
RECIPIENTS = BODIES
NFOREIGN = 3


def foreign_rolls(unit):
    """The foreign placements: rolls by 1/8, 1/4 and 3/8 of the unit's period across its stripes."""
    p = PERIOD[unit]
    return (p // 8, p // 4, 3 * p // 8)


def unit_name(pattern):
    return pattern


def parse_unit(name):
    return name, THETA


UNITS = PATTERNS


def tasks():
    return [(b, u) for b in BODIES for u in UNITS]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "identities": IDENTITIES, "purpose": PURPOSE,
            "debug_blocks": DEBUG_BLOCKS, "probe_blocks": PROBE_BLOCKS, "messages": MESSAGES, "parents": PARENTS,
            "preparation": "np001.sim.prepare (DL002's tag, acquisition and templates; S4sX the same acquisition with "
                           "the S4 template rolled across its stripes), unchanged",
            "relations": "lr004.sim.relations, unchanged; the body dl001.sim.body, unchanged",
            "side": SIDE, "sigma": SIGMA, "chunk": CHUNK, "eps": EPS, "kr": KR, "sigma_r": SIGMA_R, "kc": KC,
            "gain": GAIN, "strength0": STRENGTH0, "eta": ETA, "sources": SOURCES, "theta": THETA,
            "body_kinds": {b: (list(DL.BODIES[b]) if b in DL.BODIES else list(NOTCH[b])) for b in BODY_KINDS},
            "bodies": BODIES, "imposes": IMPOSES, "patterns": PATTERNS, "period": PERIOD, "rates": RATES,
            "routes": [[r.name, r.rate, r.source, r.parity, r.gain] for r in ROUTES], "gens": GENS, "t_gen": T_GEN,
            "gen_reads": GEN_READS, "window2": WINDOW2, "reads2": READS2, "recipients": RECIPIENTS,
            "foreign_rolls": {u: foreign_rolls(u) for u in UNITS},
            "packet": "the record's cell values r and bond signs H, W (two records for vote); bond strengths restart at "
                      "STRENGTH0 x sign; nothing of the body"}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted(f for d in ("mse", "br001", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "np001",
                               "sr001") for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m sr001.design  ->  sr001/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "sr001" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
