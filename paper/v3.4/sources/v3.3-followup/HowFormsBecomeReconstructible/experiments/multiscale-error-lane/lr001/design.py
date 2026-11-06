"""LR001: the single source of truth for the runner, the reader and the checks.

Relations that learn and check themselves (PLAN_LR001.md). The record of BR002 held in the relations between
neighbours, on the 16 x 16 sheet with ME002's families, through msegrid/ (unchanged). Bonds are held as edges
(H joins (i, j)-(i, j+1), W joins (i, j)-(i+1, j)); a pattern's bonds have no flux around any plaquette, so a corrupted
bond shows as two frustrated plaquettes. Panels:
  A  acquisition: bonds learned from the body's co-activity while the teacher holds it at the template;
  E  relation errors: every bond's sign flips at rate p_b per update; repairs none, Hebbian relearning from the record,
     plaquette parity, or both; the record alone, no code;
  C  codes: none, BR002's plain code, the code in the relations' gauge frame, the hybrid (gauge frame where live bonds
     reach a cell, plain code where not), and the hybrid with trust flags (bonds re-formed by default kept out of the
     frame), on flipped, killed and killed-and-relinked patches;
  T  turnover under the hybrid code with trust flags: a newborn's bonds inherited by halves (BR002's assumption),
     relearned from the record by Hebbian learning, or re-formed as +1 by default;
  L  learning in life: bonds that keep learning from the record's or the body's co-activity while BR001's held 6 x 6
     body scar lasts 2,000 updates (br001.sim.body_step, conserved body, sigma 0.1).
Panels A, E, C and T are the record alone (writing off: the record never reads the body), so they need no regime.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

from br001 import design as B1

TAG = "mse-lr001"
STUDY = "LR001"
IDENTITIES = {
    "preflight": (900854, 900856),     # engineering: full-shape qualification, timing, reader dry run
    "development": (910800, 910816),   # the LR001 cohort: 16 fresh source blocks
}
PURPOSE = {"preflight": "engineering", "development": "development"}
DEBUG_BLOCKS = (900856, 900858)
PROBE_BLOCKS = (900868, 900872)       # engineering probes P13 and P13b (tag mse-p13), before the freeze


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


SIDE = 16
MESSAGES, PARENTS, NCASE = B1.MESSAGES, B1.PARENTS, B1.NCASE
SETTLE, TEACH, AMPLITUDE, RELEASE = B1.SETTLE, B1.TEACH, B1.AMPLITUDE, B1.RELEASE
EPS, KR, SIGMA_R, KC, R_STAR = B1.EPS, B1.KR, B1.SIGMA_R, B1.KC, B1.R_STAR
SIGMA_ACQ = 0.1                        # records (and panel L's bodies) acquired in the conserved body at sigma 0.1
FAMILIES = ("F0", "BL", "S4", "IS")    # ME002's templates, as BR002
STRENGTH0 = 0.8                        # a taught bond's strength
ETA = 0.01                             # Hebbian relearning rate
ETA_SLOW = 0.001                       # panel L's slow learner
ETA_TEACH = 0.002                      # panel A: the running average while the teacher holds the body (rho)
COUNT = 0.1                            # a relearned bond counts once |strength| >= COUNT
TRUST = 0.5                            # a relearned bond enters the gauge frame once |strength| >= TRUST
REGION = 4                             # the coarse code's regions (and the gauge frame's), as BR002

# Panel A: teaching-phase learning
A_UNITS = ("F0", "IS")
A_SIGMAS = (0.1, 0.3, 0.6)
A_READS = (20, 100, 1000)

# Panel E: relation errors
E_UNITS = ("F0", "BL", "IS")
E_RATES = (0.0001, 0.0003, 0.001, 0.002, 0.003)
E_REPAIRS = ("none", "hebb", "parity", "both")
E_WINDOW, E_READS = 8000, (1000, 2000, 4000, 8000)


@dataclass(frozen=True)
class Cond:
    name: str
    wound: str = "sham"       # sham | flip | kill | relink
    size: int = 0


# Panel C: codes against wounds
C_UNITS = FAMILIES
C_CODES = ("none", "plain", "gauge", "hybrid", "hybrid+trust")
C_SIZES = (2, 4, 6, 8)
C_CONDS = (Cond("sham"), *(Cond(f"{w}{s}", w, s) for w in ("flip", "kill", "relink") for s in C_SIZES))
C_WINDOW, C_READS = 4000, (1000, 2000, 4000)

# Panel T: turnover under the hybrid code with trust flags
T_UNITS = ("BL", "IS")
T_BRANCHES = ((0.0, "inherit"), *((r, m) for r in (0.001, 0.003) for m in ("inherit", "relearn", "default")))
T_WINDOW, T_READS = 8000, (2000, 4000, 8000)

# Panel L: learning in life with a held body scar
L_UNITS = ("F0", "IS")
L_LEARN = ("none", "record", "body", "body_slow")
L_SIGMA, L_SCAR, L_SCAR_UNTIL = 0.1, 6, 2000
L_WINDOW, L_READS = 4000, (2000, 4000)

PANELS = {
    "A": {"title": "acquisition: bonds learned during teaching", "units": A_UNITS},
    "E": {"title": "relation errors: bond flips and their repair", "units": E_UNITS},
    "C": {"title": "codes against flipped, killed and relinked patches", "units": C_UNITS},
    "T": {"title": "turnover: inherited, relearned or default bonds", "units": T_UNITS},
    "L": {"title": "learning in life with a held body scar", "units": L_UNITS},
}


def branches(panel):
    """The ordered branch labels of a panel (each run over the block's 8 cases)."""
    if panel == "A":
        return [f"s{s:g}" for s in A_SIGMAS]
    if panel == "E":
        return [f"{r:g}/{rep}" for r in E_RATES for rep in E_REPAIRS]
    if panel == "C":
        return [f"{code}/{c.name}" for code in C_CODES for c in C_CONDS]
    if panel == "T":
        return [f"{r:g}/{m}" for r, m in T_BRANCHES]
    return list(L_LEARN)


def tasks():
    return [(p, u) for p, v in PANELS.items() for u in v["units"]]


MARGIN = 0.02
CONTRASTS = (("C", "hybrid", "plain"), ("C", "gauge", "plain"), ("C", "hybrid+trust", "plain"), ("C", "hybrid+trust", "hybrid"),
             ("E", "both", "hebb"), ("E", "both", "parity"), ("E", "parity", "none"),
             ("T", "inherit", "relearn"), ("T", "inherit", "default"))


def design_dict():
    import numpy as np
    from me002.families import templates
    th = hashlib.sha256(b"".join(np.ascontiguousarray(templates(f, "mse-me002", AMPLITUDE)).tobytes()
                                 for f in FAMILIES)).hexdigest()
    return {"study": STUDY, "tag": TAG, "identities": IDENTITIES, "purpose": PURPOSE, "debug_blocks": DEBUG_BLOCKS,
            "probe_blocks": PROBE_BLOCKS, "side": SIDE, "messages": MESSAGES, "parents": PARENTS, "settle": SETTLE,
            "teach": TEACH, "amplitude": AMPLITUDE, "release": RELEASE, "eps": EPS, "kr": KR, "sigma_r": SIGMA_R, "kc": KC,
            "r_star": R_STAR, "sigma_acq": SIGMA_ACQ, "families": FAMILIES, "template_sha256": th, "strength0": STRENGTH0,
            "eta": ETA, "eta_slow": ETA_SLOW, "eta_teach": ETA_TEACH, "count": COUNT, "trust": TRUST, "region": REGION,
            "a": {"units": A_UNITS, "sigmas": A_SIGMAS, "reads": A_READS},
            "e": {"units": E_UNITS, "rates": E_RATES, "repairs": E_REPAIRS, "window": E_WINDOW, "reads": E_READS},
            "c": {"units": C_UNITS, "codes": C_CODES, "conditions": [asdict(c) for c in C_CONDS], "window": C_WINDOW,
                  "reads": C_READS},
            "t": {"units": T_UNITS, "branches": T_BRANCHES, "window": T_WINDOW, "reads": T_READS},
            "l": {"units": L_UNITS, "learn": L_LEARN, "sigma": L_SIGMA, "scar": L_SCAR, "scar_until": L_SCAR_UNTIL,
                  "window": L_WINDOW, "reads": L_READS},
            "margin": MARGIN, "contrasts": CONTRASTS}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted([*(lane / "mse").glob("*.py"), *(lane / "me002").glob("*.py"), *(lane / "br001").glob("*.py"),
                    *(lane / "msegrid").glob("*.py"), *(lane / "lr001").glob("*.py")])
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m lr001.design  ->  lr001/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "lr001" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
