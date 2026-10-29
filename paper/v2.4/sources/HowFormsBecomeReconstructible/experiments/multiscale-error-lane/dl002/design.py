"""DL002: the single source of truth for the runner, the reader and the checks.

Who supplies a pattern's relations: the body's physics, a record of relations, or positional anchors? DL001's
double well (dw) and its strong period-8 lateral-inhibition body (li4) (dl001.sim.body, unchanged), with records the
body reads through the pull g (r - V~):
  none;
  a16, a4  positional anchors: the held record at a random 1/16 or 1/4 of the sites (drawn per case), gain 1.0 there;
  full     the held record at every site, gain 0.2 (DL001's);
  rel      a tissue-held relational record (BR002's bonds and coarse code on msegrid.record_step), read at gain 0.2.
Patterns on a 32-site sheet: S4 (stripes of period 8, native to li4), LB (li4's own labyrinth: grown from newborn
noise in a clean sheet without a record for 2,000 updates, then its sign; two per block, kinds 2 and 3 reversed) and
F0 (two domains, native to dw). The environmental field theta at x0, x0.25, x0.5 and x1 (spreads 0 to 0.2); sigma 0.1;
records and bodies acquired as in GW001 and DL001 (msegrid.acquire), shared by every body and record of a case.
Panels: A, no wound, t = 2,000 and 4,000; R, an 8 x 8 wound at t = 1 (flipped or reset; the relational record is
wounded with the body, anchors inside the wound are lost, the full held record stays intact), t = 500, 2,000, 4,000.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

from dl001 import design as DL

TAG = "mse-dl002"
STUDY = "DL002"
IDENTITIES = {
    "preflight": (900896, 900898),     # engineering: full-shape qualification, timing, reader dry run
    "development": (910900, 910916),   # the DL002 cohort: 16 fresh source blocks
}
PURPOSE = {"preflight": "engineering", "development": "development"}
DEBUG_BLOCKS = (900898, 900900)
PROBE_BLOCKS = (900892, 900896)       # engineering probes P14 and P14b (tag mse-p14), before the freeze


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


MESSAGES, PARENTS, NCASE = DL.MESSAGES, DL.PARENTS, DL.NCASE
SETTLE, TEACH, AMPLITUDE, RELEASE, SIGMA_ACQ = DL.SETTLE, DL.TEACH, DL.AMPLITUDE, DL.RELEASE, DL.SIGMA_ACQ
SIDE, SIGMA, KILL_SD, CHUNK = 32, 0.1, 0.2, 250
LB_GROW = 2000                         # updates of li4 growing a labyrinth from newborn noise
EPS, KR, SIGMA_R, KC = 0.05, 1.0, 0.02, 0.02   # the relational record (BR001 and BR002)
BODIES = ("dw", "li4")
PATTERNS = ("S4", "LB", "F0")
THETAS = (0.0, 0.25, 0.5, 1.0)
WINDOW, SNAPS_A, SNAPS_R = 4000, (2000, 4000), (500, 2000, 4000)


@dataclass(frozen=True)
class Rec:
    name: str
    kind: str          # none | anchors | full | rel
    gain: float = 0.0
    density: int = 0   # anchors: one site in `density`


RECORDS = (Rec("none", "none"), Rec("a16", "anchors", 1.0, 16), Rec("a4", "anchors", 1.0, 4),
           Rec("full", "full", 0.2), Rec("rel", "rel", 0.2))
RECORDS_R = tuple(r for r in RECORDS if r.name != "a16")


def unit_name(pattern, theta, wound=""):
    return f"{pattern}_t{theta:g}" + (f"_{wound}" if wound else "")


def parse_unit(name):
    parts = name.split("_")
    return parts[0], float(parts[1][1:]), (parts[2] if len(parts) > 2 else "")


PANELS = {
    "A": {"title": "who holds the pattern: no wound", "records": RECORDS, "snaps": SNAPS_A,
          "units": tuple(unit_name(p, t) for p in PATTERNS for t in THETAS)},
    "R": {"title": "who repairs it: an 8 x 8 wound to body (and the relational record)", "records": RECORDS_R,
          "snaps": SNAPS_R, "units": tuple(unit_name(p, t, w) for p in ("S4", "LB") for t in (0.0, 1.0) for w in ("flip", "reset"))},
}


def tasks():
    return [(p, u) for p, v in PANELS.items() for u in v["units"]]


def design_dict():
    return {"study": STUDY, "tag": TAG, "identities": IDENTITIES, "purpose": PURPOSE, "debug_blocks": DEBUG_BLOCKS,
            "probe_blocks": PROBE_BLOCKS, "messages": MESSAGES, "parents": PARENTS, "settle": SETTLE, "teach": TEACH,
            "amplitude": AMPLITUDE, "release": RELEASE, "sigma_acq": SIGMA_ACQ, "side": SIDE, "sigma": SIGMA,
            "kill_sd": KILL_SD, "chunk": CHUNK, "lb_grow": LB_GROW, "eps": EPS, "kr": KR, "sigma_r": SIGMA_R, "kc": KC,
            "bodies": {b: list(DL.BODIES[b]) for b in BODIES}, "patterns": PATTERNS, "thetas": THETAS, "window": WINDOW,
            "panels": {p: {"title": v["title"], "records": [asdict(r) for r in v["records"]], "snaps": v["snaps"],
                           "units": v["units"]} for p, v in PANELS.items()}}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted([*(lane / "mse").glob("*.py"), *(lane / "br001").glob("*.py"), *(lane / "msegrid").glob("*.py"),
                    *(lane / "dl001").glob("*.py"), *(lane / "dl002").glob("*.py")])
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m dl002.design  ->  dl002/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "dl002" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
