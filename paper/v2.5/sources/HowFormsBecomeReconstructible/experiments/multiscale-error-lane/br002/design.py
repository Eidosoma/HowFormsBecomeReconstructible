"""BR002: the single source of truth for the runner, the reader and the checks.

Commitment and relations, after BR001 and engineering probe P8. The record lives in the tissue as in BR001
(br001/design.py); three additions:
    committed writing:  a write gate with hysteresis opens as BR001's does and closes only when the region
                        mismatch falls below OFF x theta (panel C)
    relational record:  bonds J_ij = sign(R0_i) sign(R0_j) replace uniform consensus,
                        r <- r + EPS [ f(r) + kr (sum_j J_ij r_j / 4 - r) ] + sigma_r xi  (the Mattis gauge; J = 1 is
                        BR001's consensus rule exactly) (panel R)
    wall geometry:      lesions placed at declared distances from F0's own walls (panel G)
Bodies: 'c' conserved, 'o' open, as BR001. Time convention as BR001: an event at onset tau is applied before
update tau; window damage arrives at tau + WINDOW_DELAY inside a window the cue opened at tau.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

from br001 import design as B1
from me002.families import templates

TAG = "mse-br002"
STUDY = "BR002"
IDENTITIES = {
    "preflight": (900828, 900830),     # engineering: full-shape qualification, timing, reader dry run
    "development": (910400, 910416),   # the BR002 cohort: 16 fresh source blocks
}
PURPOSE = {"preflight": "engineering", "development": "development"}
DEBUG_BLOCKS = (900830, 900832)
PROBE_BLOCKS = (900824, 900828)       # engineering probe P9, before the freeze


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


# Unchanged from BR001 (imported, so the two studies cannot drift apart)
MESSAGES, PARENTS, NCASE, FOREIGN = B1.MESSAGES, B1.PARENTS, B1.NCASE, B1.FOREIGN
SETTLE, TEACH, AMPLITUDE, RELEASE = B1.SETTLE, B1.TEACH, B1.AMPLITUDE, B1.RELEASE
WINDOW, READ_UPDATES, RECIPIENTS, PER_TISSUE_THETA = B1.WINDOW, B1.READ_UPDATES, B1.RECIPIENTS, B1.PER_TISSUE_THETA
R_STAR, EPS, KR, SIGMA_R, KC = B1.R_STAR, B1.EPS, B1.KR, B1.SIGMA_R, B1.KC
RHO_W, TAG_DECAY, TAG_GATE, LATCH_W, WINDOW_P = B1.RHO_W, B1.TAG_DECAY, B1.TAG_GATE, B1.LATCH_W, B1.WINDOW_P
ONSET = B1.ONSET
FAMILIES = ("F0", "BL", "S4", "IS")
TEMPLATES = {f: templates(f, "mse-me002", AMPLITUDE) for f in FAMILIES}   # ME002's families, unchanged

# New in BR002
OFF = 0.05             # hysteresis: a committed gate closes when region mismatch < OFF x theta
WINDOW_DELAY = 100     # window damage arrives this many updates after the cue
DOMAIN = 8             # F0's domains are 8 sites thick on the 16-site torus (walls at 7|8 and 15|0)
KILL_SD = 0.2          # newborn body state of a killed cell, as turnover's newborns


def regime(family, sigma, body="c"):
    return f"{family}_s{sigma:g}_{body}"


def parse(name):
    family, s, body = name.split("_")
    return family, float(s[1:]), body


@dataclass(frozen=True)
class Cond:
    name: str
    kind: str = "sham"        # sham | lesion | kill | turnover | wound | scar | record | impose | window
    size: int = 0
    duration: int = 0         # impose: 0 = to the window's end
    cue: bool = False         # an instruction cue opens the plastic window at onset
    rate: float = 0.0         # turnover: replacement probability per cell per update
    place: str = "random"     # random | d0..d3 (distance from F0's nearest wall) | cross (straddles a wall)
    damage: str = ""          # window: scar | wound, arriving at tau + WINDOW_DELAY


@dataclass(frozen=True)
class Arm:
    name: str
    reads: bool = True
    eps: float = 0.0          # self-correction rate (0 = off)
    kc: float = 0.0           # coarse-code pull (0 = off)
    rel: bool = False         # bonds from the taught record's signs (False: J = 1, BR001's consensus)
    relink: bool = False      # bonds lost with dead cells re-form as +1 (consensus default) instead of 0
    clamp: bool = False       # privileged protected copy restored every update
    write: str = "none"       # none | always | duration | tags | phase | phase_tags
    hyst: bool = False        # committed gate (hysteresis)
    privileged: bool = False


COND_C = (Cond("sham"), Cond("wound-6x6", "wound", 6), Cond("scar-6x6", "scar", 6), Cond("record-6x6", "record", 6),
          Cond("impose-inf-cued", "impose", cue=True), Cond("impose-inf", "impose"),
          Cond("impose-300", "impose", duration=300),
          Cond("window-scar-6x6", "window", 6, cue=True, damage="scar"),
          Cond("window-wound-6x6", "window", 6, cue=True, damage="wound"))
ARMS_C = (Arm("none", eps=EPS),
          Arm("always", eps=EPS, write="always"), Arm("always+h", eps=EPS, write="always", hyst=True),
          Arm("duration", eps=EPS, write="duration"), Arm("duration+h", eps=EPS, write="duration", hyst=True),
          Arm("tags", eps=EPS, write="tags"), Arm("tags+h", eps=EPS, write="tags", hyst=True),
          Arm("phase", eps=EPS, write="phase"), Arm("phase+tags", eps=EPS, write="phase_tags"))

COND_R = (Cond("sham"), *(Cond(f"both-{s}x{s}", "lesion", s) for s in (2, 4, 6, 8)),
          Cond("kill-4x4", "kill", 4), Cond("kill-8x8", "kill", 8),
          Cond("turnover-0.001", "turnover", rate=1e-3), Cond("turnover-0.003", "turnover", rate=3e-3))
ARMS_R = (Arm("static"), Arm("self", eps=EPS), Arm("multi", eps=EPS, kc=KC), Arm("rel", eps=EPS, rel=True),
          Arm("rel+code", eps=EPS, kc=KC, rel=True), Arm("rel+code+relink", eps=EPS, kc=KC, rel=True, relink=True),
          Arm("protected", clamp=True, privileged=True))

PLACES = {2: ("d0", "d1", "d2", "d3", "cross"), 4: ("d0", "d1", "d2", "cross"), 6: ("d0", "d1", "cross"), 8: ("d0", "cross")}
COND_G = (Cond("sham"), *(Cond(f"w{s}-{pl}", "lesion", s, place=pl) for s, pls in PLACES.items() for pl in pls))
ARMS_G = (Arm("static"), Arm("self", eps=EPS), Arm("multi", eps=EPS, kc=KC), Arm("rel", eps=EPS, rel=True),
          Arm("rel+code", eps=EPS, kc=KC, rel=True))

PANELS = {
    "C": {"title": "committed writing, damage inside an open window, and a window that respects damage tags",
          "onset": "random",
          "regimes": (regime("F0", 0.1), regime("F0", 0.3), regime("F0", 0.1, "o"), regime("F0", 0.3, "o")),
          "conditions": COND_C, "arms": ARMS_C},
    "R": {"title": "a record held in the relations between neighbours", "onset": "start",
          "regimes": (regime("F0", 0.1), regime("F0", 0.1, "o"), regime("BL", 0.1), regime("BL", 0.1, "o"),
                      regime("BL", 0.3), regime("S4", 0.1), regime("IS", 0.1)),
          "conditions": COND_R, "arms": ARMS_R},
    "G": {"title": "what consensus cannot repair: wounds at declared distances from the pattern's walls",
          "onset": "start", "regimes": (regime("F0", 0.1), regime("F0", 0.3)),
          "conditions": COND_G, "arms": ARMS_G},
}
ARM = {p: {a.name: a for a in v["arms"]} for p, v in PANELS.items()}


def tasks():
    return [(p, r) for p, v in PANELS.items() for r in v["regimes"]]


MARGIN = 0.02
PRIMARY_ENDPOINTS = {"C": ("les_r", "adopt_flip", "rg_sign", "v_qual"), "R": ("les_r", "r_sign", "v_qual"),
                     "G": ("les_r",)}


def _contrasts():
    out = []
    add = lambda p, fam, a, b: out.append((p, fam, a, b))
    for a, b in (("always+h", "always"), ("duration+h", "duration"), ("tags+h", "tags"), ("phase+tags", "phase"),
                 ("tags+h", "duration+h"), ("phase", "duration+h"), ("phase+tags", "tags+h")):
        add("C", "C1 committed and windowed writing", a, b)
    for a, b in (("rel", "self"), ("rel", "multi"), ("rel+code", "rel"), ("rel+code", "multi"),
                 ("rel+code+relink", "rel+code"), ("rel", "protected"), ("rel+code", "protected")):
        add("R", "R1 relational record", a, b)
    for a, b in (("rel", "self"), ("multi", "self"), ("rel+code", "multi")):
        add("G", "G1 walls", a, b)
    return tuple(out)


CONTRASTS = _contrasts()


def design_dict():
    panels = {p: {k: ([asdict(x) for x in v] if k in ("conditions", "arms") else v) for k, v in spec.items()}
              for p, spec in PANELS.items()}
    import numpy as np
    th = hashlib.sha256(b"".join(np.ascontiguousarray(TEMPLATES[f]).tobytes() for f in FAMILIES)).hexdigest()
    return {"study": STUDY, "tag": TAG, "identities": IDENTITIES, "purpose": PURPOSE, "debug_blocks": DEBUG_BLOCKS,
            "probe_blocks": PROBE_BLOCKS, "messages": MESSAGES, "parents": PARENTS, "foreign": FOREIGN,
            "settle": SETTLE, "teach": TEACH, "amplitude": AMPLITUDE, "release": RELEASE, "window": WINDOW,
            "read_updates": READ_UPDATES, "recipients": RECIPIENTS, "per_tissue_theta": PER_TISSUE_THETA,
            "families": FAMILIES, "template_sha256": th,
            "record": {"r_star": R_STAR, "eps": EPS, "kr": KR, "sigma_r": SIGMA_R, "kc": KC},
            "writing": {"rho_w": RHO_W, "tag_decay": TAG_DECAY, "tag_gate": TAG_GATE, "latch_w": LATCH_W,
                        "window_p": WINDOW_P, "off": OFF, "window_delay": WINDOW_DELAY},
            "geometry": {"domain": DOMAIN, "places": PLACES}, "kill_sd": KILL_SD, "onset": ONSET,
            "panels": panels, "margin": MARGIN, "primary_endpoints": PRIMARY_ENDPOINTS, "contrasts": CONTRASTS}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted([*(lane / "mse").glob("*.py"), *(lane / "me002").glob("*.py"), *(lane / "br001").glob("*.py"),
                    *(lane / "br002").glob("*.py")])
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m br002.design  ->  br002/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "br002" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
