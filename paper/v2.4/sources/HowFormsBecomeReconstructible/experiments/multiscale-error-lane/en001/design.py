"""EN001: the single source of truth for the runner, the reader and the checks.

The energy budget. Slow the budget and watch the plan (the PI's question from the Levin thread; MODEL_LIMITS
section 3.1, pilot T7). BR002's tissue (br002/sim.py) runs a starvation phase of STARVE updates on a reduced budget,
then a recovery phase of RECOVER updates on the full budget. A budget multiplies the rates of the paid processes:
    body drift      the double well, coupling and theta (paid only when every drift is paid)
    body correction the body reading its record (always paid)
    record          the record's self-correction and coarse code (always paid)
and decides the noise: thermal (unchanged by the budget) or activity-driven (variance scaled with the paid rate).
Panel G: a global budget factor phi under three accountings (A: only correction paid, thermal noise; B: every
drift paid, thermal noise; C: every drift paid, activity noise). Panel P: what to protect, at phi = 0.25 (all
paid at phi, the record protected at full rate, or the body protected). Panel E: a per-cell energy store with
supply phi x S0; each cell's availability a = (E/Emax)(1 + K)/(E/Emax + K) multiplies its paid rates.
Wounds are flips (record and body inverted) or resets (cells die: record 0, newborn body; dead bonds re-form
as +1); turnover runs on an outside clock (never slowed by the budget).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

from br002 import design as B2

TAG = "mse-en001"
STUDY = "EN001"
IDENTITIES = {
    "calibration": (900876, 900880),   # engineering: the store's sham work per cell (panel E supply)
    "preflight": (900888, 900890),     # engineering: full-shape qualification, timing, reader dry run
    "development": (910600, 910616),   # the EN001 cohort: 16 fresh source blocks
}
PURPOSE = {"calibration": "engineering", "preflight": "engineering", "development": "development"}
PROBE_BLOCKS = (900880, 900884)       # engineering probe P11, before the freeze
DEBUG_BLOCKS = (900890, 900892)


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


# Unchanged from BR002 (imported, so the studies cannot drift apart)
MESSAGES, PARENTS, NCASE, FOREIGN = B2.MESSAGES, B2.PARENTS, B2.NCASE, B2.FOREIGN
SETTLE, TEACH, AMPLITUDE, RELEASE = B2.SETTLE, B2.TEACH, B2.AMPLITUDE, B2.RELEASE
PER_TISSUE_THETA = B2.PER_TISSUE_THETA
R_STAR, EPS, KR, SIGMA_R, KC, KILL_SD = B2.R_STAR, B2.EPS, B2.KR, B2.SIGMA_R, B2.KC, B2.KILL_SD
FAMILIES = ("F0", "BL")
TEMPLATES = {f: B2.TEMPLATES[f] for f in FAMILIES}

# New in EN001
STARVE, RECOVER = 2000, 1000
WINDOW = STARVE + RECOVER
SNAP = 100                       # snapshot interval for repair times
REPAIR = 500                     # the store's availability inside and outside a wound is compared over t <= REPAIR
PHIS = (0.5, 0.25, 0.1)
STORE_CAP = 100.0                # store capacity, in units of the calibrated sham work per cell per update
STORE_HEADROOM = 1.25            # full supply S0 = 1.25 x calibrated sham work per cell per update
STORE_K = 0.25                   # half-saturation, as a fraction of capacity
WOUND = 6
TURNOVER = 1e-3


def regime(family, sigma, body="c"):
    return f"{family}_s{sigma:g}_{body}"


def parse(name):
    family, s, body = name.split("_")
    return family, float(s[1:]), body


@dataclass(frozen=True)
class Cond:
    name: str
    kind: str = "sham"        # sham | lesion (flip: record and body inverted) | kill (reset) | turnover
    size: int = 0
    rate: float = 0.0


@dataclass(frozen=True)
class Arm:
    name: str
    eps: float = 0.0          # record self-correction rate
    kc: float = 0.0           # coarse-code pull
    rel: bool = False         # relational bonds (BR002)
    relink: bool = False      # bonds of dead cells re-form as +1


@dataclass(frozen=True)
class Budget:
    name: str
    scheme: str = "global"    # global | store
    paid: str = "all"         # all (body drift, correction and record) | corr (correction and record only)
    noise: str = "thermal"    # thermal | activity
    phi: float = 1.0          # global: rate factor; store: supply factor
    alloc: str = "uniform"    # uniform | record (record at full rate) | body (body at full rate)


CONDS = (Cond("sham"), Cond("flip-6x6", "lesion", WOUND), Cond("reset-6x6", "kill", WOUND),
         Cond("turnover-0.001", "turnover", rate=TURNOVER))
ARMS = {"hold": Arm("hold"), "self": Arm("self", eps=EPS), "multi": Arm("multi", eps=EPS, kc=KC),
        "relcode": Arm("relcode", eps=EPS, kc=KC, rel=True, relink=True)}
BASE = Budget("base")
B_G = (BASE, *(Budget(f"{a}{phi:g}", paid="corr" if a == "A" else "all", noise="activity" if a == "C" else "thermal", phi=phi)
               for a in ("A", "B", "C") for phi in PHIS))
B_P = (BASE, *(Budget(f"{n}-{al}", noise=n, phi=0.25, alloc=al)
               for n in ("thermal", "activity") for al in ("uniform", "record", "body")))
B_E = tuple(Budget(f"store-{n}{phi:g}", scheme="store", noise=n, phi=phi)
            for n in ("thermal", "activity") for phi in (1.0, *PHIS))

PANELS = {
    "G": {"title": "a global budget under three accountings: correction only, every drift with thermal noise, "
                   "every drift with activity-driven noise",
          "regimes": (regime("F0", 0.3), regime("F0", 0.1), regime("BL", 0.1)),
          "arms": ("hold", "self", "multi", "relcode"), "budgets": B_G},
    "P": {"title": "what to protect when the budget is a quarter: everything cut, the record protected, the body protected",
          "regimes": (regime("F0", 0.3), regime("BL", 0.1)), "arms": ("multi", "relcode"), "budgets": B_P},
    "E": {"title": "a per-cell energy store: wounds draw on local energy",
          "regimes": (regime("F0", 0.3), regime("BL", 0.1)), "arms": ("multi", "relcode"), "budgets": B_E},
}


def tasks():
    return [(p, r) for p, v in PANELS.items() for r in v["regimes"]]


def branches(panel):
    """(arm, budget) pairs of a panel, in the order the worker runs and stores them."""
    return [(a, b) for a in PANELS[panel]["arms"] for b in PANELS[panel]["budgets"]]


MARGIN = 0.02
ENDPOINTS = ("v_qual", "v_sign", "r_sign", "les_r", "les_v", "v_qual_rec", "r_sign_rec", "les_r_rec", "les_v_rec",
             "t95", "healed", "w_drift", "w_corr", "w_rec", "a_mean", "a_patch", "a_rest")


def design_dict():
    panels = {p: {"title": v["title"], "regimes": v["regimes"], "arms": v["arms"],
                  "budgets": [asdict(b) for b in v["budgets"]]} for p, v in PANELS.items()}
    import numpy as np
    th = hashlib.sha256(b"".join(np.ascontiguousarray(TEMPLATES[f]).tobytes() for f in FAMILIES)).hexdigest()
    return {"study": STUDY, "tag": TAG, "identities": IDENTITIES, "purpose": PURPOSE, "probe_blocks": PROBE_BLOCKS,
            "debug_blocks": DEBUG_BLOCKS, "messages": MESSAGES, "parents": PARENTS, "foreign": FOREIGN,
            "settle": SETTLE, "teach": TEACH, "amplitude": AMPLITUDE, "release": RELEASE,
            "per_tissue_theta": PER_TISSUE_THETA, "families": FAMILIES, "template_sha256": th,
            "record": {"r_star": R_STAR, "eps": EPS, "kr": KR, "sigma_r": SIGMA_R, "kc": KC, "kill_sd": KILL_SD},
            "phases": {"starve": STARVE, "recover": RECOVER, "snap": SNAP, "repair": REPAIR}, "phis": PHIS,
            "store": {"cap": STORE_CAP, "headroom": STORE_HEADROOM, "k": STORE_K},
            "conditions": [asdict(c) for c in CONDS], "arms": {k: asdict(v) for k, v in ARMS.items()},
            "panels": panels, "margin": MARGIN, "endpoints": ENDPOINTS}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted([*(lane / "mse").glob("*.py"), *(lane / "me002").glob("*.py"), *(lane / "br001").glob("*.py"),
                    *(lane / "br002").glob("*.py"), *(lane / "en001").glob("*.py")])
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m en001.design  ->  en001/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "en001" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
