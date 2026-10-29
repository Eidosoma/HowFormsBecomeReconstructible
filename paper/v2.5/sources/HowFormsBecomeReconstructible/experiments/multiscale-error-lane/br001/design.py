"""BR001: the single source of truth for the runner, the reader and the checks.

The record lives in the tissue: every cell carries a slow record value r beside its state v, the body
reads its own record with the native gain, and the record has its own optional dynamics:
    self-correction:  r <- r + EPS [ r (1 - (r / R_STAR)^2) + kr (N(r) - r) ] + sigma_r xi
    coarse code:      r <- r + kc (B - P4(r)), B = the taught record's 16 region means (protected)
    writing:          r <- r + RHO_W gate (v - r), gated by a rule (panel P)
Bodies: 'c' is the native conserved body (mean removed from drift, noise and correction), 'o' an open
body with no mean removal. Time convention as ME002: an event at onset tau is applied before update tau.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

from me002.families import templates

TAG = "mse-br001"
STUDY = "BR001"
IDENTITIES = {
    "calibration": (900953, 900959),   # engineering: panel P write thresholds
    "preflight": (900975, 900977),     # engineering: full-shape qualification, timing, reader dry run
    "development": (910300, 910316),   # the BR001 cohort: 16 fresh source blocks
}
PURPOSE = {"calibration": "engineering", "preflight": "engineering", "development": "development"}
DEBUG_BLOCKS = (900977, 900979)


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


MESSAGES, PARENTS = (0, 1, 2, 3), (0, 1)
NCASE = len(MESSAGES) * len(PARENTS)
FOREIGN = {0: 1, 1: 0, 2: 3, 3: 2}
SETTLE, TEACH, AMPLITUDE, RELEASE = 120, 1000, 1.2, 200
WINDOW, READ_UPDATES, RECIPIENTS = 2000, 1000, 4
PER_TISSUE_THETA = True
FAMILIES = ("F0", "F4", "BL")
TEMPLATES = {f: templates(f, "mse-me002", AMPLITUDE) for f in FAMILIES}   # ME002's families, unchanged

R_STAR, EPS, KR, SIGMA_R, KC = 1.2, 0.05, 1.0, 0.02, 0.02
RHO_W, TAG_DECAY, TAG_GATE, LATCH_W, WINDOW_P, QUANTILE = 0.05, 1.0 / 300, 0.05, 500, 500, 0.995
ONSET = (100, 501)
SIZES = (2, 4, 6, 8)
P_SIZE = 6
TURNOVER = (0.0, 3e-4, 1e-3, 3e-3)


def regime(family, sigma, body="c"):
    return f"{family}_s{sigma:g}_{body}"


def parse(name):
    family, s, body = name.split("_")
    return family, float(s[1:]), body


PRIMARY = regime("F0", 0.3)


@dataclass(frozen=True)
class Cond:
    name: str
    kind: str = "sham"        # sham | lesion | wound | scar | record | impose | turnover
    target: str = ""          # lesion: both | record | body
    size: int = 0
    duration: int = 0         # impose: 0 = to the window's end
    cue: bool = False         # impose: an instruction cue opens the plastic window at onset
    rate: float = 0.0         # turnover: replacement probability per cell per update


COND_L = (Cond("sham"), *(Cond(f"{t}-{s}x{s}", "lesion", t, s) for t in ("both", "record", "body") for s in SIZES))
COND_P = (Cond("sham"), Cond("wound-6x6", "wound", size=P_SIZE), Cond("scar-6x6", "scar", size=P_SIZE),
          Cond("record-6x6", "record", size=P_SIZE), Cond("impose-inf-cued", "impose", duration=0, cue=True),
          Cond("impose-inf", "impose", duration=0), Cond("impose-300", "impose", duration=300))
COND_T = tuple(Cond(f"turnover-{r:g}", "turnover", rate=r) for r in TURNOVER)


@dataclass(frozen=True)
class Arm:
    name: str
    reads: bool = True        # False: the body ignores its record (gain 0)
    eps: float = 0.0          # self-correction rate (0 = off)
    kr: float = KR
    sigma_r: float = SIGMA_R
    kc: float = 0.0           # coarse-code pull (0 = off)
    clamp: bool = False       # privileged protected copy restored every update
    separate: bool = False    # the record sits outside the cells: turnover does not reset it
    write: str = "none"       # none | always | duration | tags | phase
    privileged: bool = False


ARMS_L = (
    Arm("static"),
    Arm("self", eps=EPS),
    Arm("code", kc=KC),
    Arm("multi", eps=EPS, kc=KC),
    Arm("protected", clamp=True, privileged=True),
    Arm("multi_kr0.5", eps=EPS, kr=0.5, kc=KC),
    Arm("multi_kr2", eps=EPS, kr=2.0, kc=KC),
    Arm("multi_kc0.005", eps=EPS, kc=0.005),
    Arm("multi_kc0.08", eps=EPS, kc=0.08),
    Arm("multi_sr0.05", eps=EPS, sigma_r=0.05, kc=KC),
)
ARMS_P = tuple(Arm(f"write_{w}", eps=EPS, write=w) for w in ("none", "always", "duration", "tags", "phase"))
ARMS_T = (
    Arm("inactive", reads=False),
    Arm("static"),
    Arm("self", eps=EPS),
    Arm("multi", eps=EPS, kc=KC),
    Arm("separate", separate=True),
    Arm("protected", clamp=True, separate=True, privileged=True),
)

PANELS = {
    "L": {"title": "multi-scale self-repair of local lesions in a tissue-held record", "onset": "start",
          "regimes": (regime("F0", 0.1), regime("F0", 0.3), regime("F0", 0.1, "o"), regime("F0", 0.3, "o"),
                      regime("BL", 0.1), regime("BL", 0.3), regime("F4", 0.3)),
          "conditions": COND_L, "arms": ARMS_L},
    "P": {"title": "which writing rule adopts lasting change but not damage", "onset": "random",
          "regimes": (regime("F0", 0.1), regime("F0", 0.3), regime("F0", 0.1, "o"), regime("F0", 0.3, "o")),
          "conditions": COND_P, "arms": ARMS_P},
    "T": {"title": "cell turnover as the source of forgetting", "onset": "start",
          "regimes": (regime("F0", 0.05), regime("F0", 0.1), regime("F0", 0.3), regime("F0", 0.1, "o"), regime("BL", 0.1)),
          "conditions": COND_T, "arms": ARMS_T},
}
ARM = {p: {a.name: a for a in v["arms"]} for p, v in PANELS.items()}


def tasks():
    return [(p, r) for p, v in PANELS.items() for r in v["regimes"]]


MARGIN = 0.02
PRIMARY_ENDPOINTS = {"L": ("v_qual", "les_r", "fR_qual"), "P": ("v_qual", "r_sign", "rg_sign", "les_r"),
                     "T": ("v_qual", "r_sign", "fR_qual")}


def _contrasts():
    out = []
    add = lambda p, fam, a, b: out.append((p, fam, a, b))
    for a, b in (("self", "static"), ("code", "static"), ("multi", "static"), ("multi", "self"), ("multi", "code"),
                 ("multi", "protected"), ("protected", "static")):
        add("L", "L1 record designs", a, b)
    for a in ("multi_kr0.5", "multi_kr2", "multi_kc0.005", "multi_kc0.08", "multi_sr0.05"):
        add("L", "L2 parameters", a, "multi")
    for a, b in (("write_tags", "write_duration"), ("write_phase", "write_duration"), ("write_phase", "write_tags"),
                 ("write_always", "write_none"), ("write_duration", "write_none"), ("write_tags", "write_none"),
                 ("write_phase", "write_none")):
        add("P", "P1 writing rules", a, b)
    for a, b in (("static", "inactive"), ("self", "static"), ("multi", "static"), ("separate", "static"),
                 ("protected", "static"), ("self", "inactive")):
        add("T", "T1 turnover", a, b)
    return tuple(out)


CONTRASTS = _contrasts()


def design_dict():
    panels = {p: {k: ([asdict(x) for x in v] if k in ("conditions", "arms") else v) for k, v in spec.items()}
              for p, spec in PANELS.items()}
    import numpy as np
    th = hashlib.sha256(b"".join(np.ascontiguousarray(TEMPLATES[f]).tobytes() for f in FAMILIES)).hexdigest()
    return {"study": STUDY, "tag": TAG, "identities": IDENTITIES, "purpose": PURPOSE, "debug_blocks": DEBUG_BLOCKS,
            "messages": MESSAGES, "parents": PARENTS, "foreign": FOREIGN, "settle": SETTLE, "teach": TEACH,
            "amplitude": AMPLITUDE, "release": RELEASE, "window": WINDOW, "read_updates": READ_UPDATES,
            "recipients": RECIPIENTS, "per_tissue_theta": PER_TISSUE_THETA, "families": FAMILIES,
            "template_sha256": th,
            "record": {"r_star": R_STAR, "eps": EPS, "kr": KR, "sigma_r": SIGMA_R, "kc": KC},
            "writing": {"rho_w": RHO_W, "tag_decay": TAG_DECAY, "tag_gate": TAG_GATE, "latch_w": LATCH_W,
                        "window_p": WINDOW_P, "quantile": QUANTILE},
            "onset": ONSET, "sizes": SIZES, "p_size": P_SIZE, "turnover": TURNOVER, "panels": panels,
            "primary": PRIMARY, "margin": MARGIN, "primary_endpoints": PRIMARY_ENDPOINTS, "contrasts": CONTRASTS}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted([*(lane / "mse").glob("*.py"), *(lane / "me002").glob("*.py"), *(lane / "br001").glob("*.py")])
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m br001.design  ->  br001/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "br001" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
