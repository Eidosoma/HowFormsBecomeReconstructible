"""ME002: the single source of truth for the runner, the reader and the checks.

A wide development screen, not a confirmation (PROTOCOL section 8). Every panel, regime,
condition, arm, constant and identity range is fixed here before any development outcome;
REGISTRATION_ME002.md and frozen/design.json record DESIGN's digest, and the runner refuses
development work when the digest or the sources differ from the frozen ones.

Time convention: a window runs updates t = 1..L. An event at onset tau is applied to the state
before update tau ("start" onset: tau = 1, ME001's injured start). A sentinel k reads the body
after k updates since the onset (after update tau + k - 1).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

import numpy as np

from mse.native import LEVELS
from mse.ops import bands

from .families import blobs, templates

TAG = "mse-me002"
STUDY = "ME002"

# Reserved before sampling; half-open block ranges, disjoint from every earlier probe and study.
IDENTITIES = {
    "calibration": (900930, 900946),   # engineering: thresholds, equal-dose gains, theory points
    "preflight": (900950, 900952),     # engineering: full-shape qualification, timing, reader dry run
    "development": (910100, 910116),   # the ME002 cohort: 16 fresh source blocks
}
PURPOSE = {"calibration": "engineering", "preflight": "engineering", "development": "development"}
DEBUG_BLOCKS = (900993, 900995)          # unreserved engineering blocks for debugging the tools


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


MESSAGES, PARENTS = (0, 1, 2, 3), (0, 1)
NCASE = len(MESSAGES) * len(PARENTS)
FOREIGN = {0: 1, 1: 0, 2: 3, 3: 2}        # the orthogonal message, same block and parent
SETTLE, TEACH, AMPLITUDE, RELEASE = 120, 1000, 1.2, 200
READ_UPDATES, RECIPIENTS = 1000, 4
PER_TISSUE_THETA = True

# P4b's burst constants, unchanged from ME001.
BURST_UPDATES, BURST_RATE, LATCH, REFRACTORY, QUANTILE = 20, 0.1, 1000, 200, 0.995
PERIOD = 450                              # periodic refresh: a 20-update write every 450 updates
ONSET = (100, 501)                        # panel A: onset uniform on the integers 100..500
EARLY = (20, 100)
LIFE, GEN_ONSET, GENERATIONS = 2500, (1300, 1701), 8
MIX = (("body", 0.4), ("reference", 0.4), ("both", 0.2))
BANDS = ("fine", "regional", "collective")
FAMILIES = ("F0", "F2", "F4", "S4", "BL", "IS")
CAL_FAMILIES = ("F0", "F2", "F4")         # pooled thresholds are calibrated on these only
TEMPLATES = {f: templates(f, TAG, AMPLITUDE) for f in FAMILIES}
BLOB_INDEX = blobs(TAG)[2]


def regime(family, sigma, g=1.0):
    return f"{family}_s{sigma:g}_g{g:g}"


def parse(name):
    family, s, g = name.split("_")
    return family, float(s[1:]), float(g[1:])


def pool_key(name):
    _, s, g = parse(name)
    return f"s{s:g}_g{g:g}"


PRIMARY = regime("F0", 0.3)


@dataclass(frozen=True)
class Event:
    kind: str                 # damage | impose
    target: str = ""          # damage: body | reference | both | reference2 (both records of a
                              # two-record arm, independent fields; the first record only otherwise)
    band: str = ""
    rms: float = 0.0
    delay: int = 0            # updates after the onset
    duration: int = 0         # impose: updates; 0 = until the window ends


@dataclass(frozen=True)
class Condition:
    name: str
    events: tuple = ()


def damage(target, band, rms, delay=0):
    return Event("damage", target, band, float(rms), delay)


def single(target, band, rms):
    return Condition(f"{target}-{band}-{rms:g}", (damage(target, band, rms),))


SHAM = Condition("sham")
COND_A = (SHAM, *(single(t, b, r) for t in ("body", "reference", "both") for b in BANDS for r in (1, 2)),
          Condition("ref-then-body-10", (damage("reference", "collective", 2), damage("body", "collective", 2, 10))),
          Condition("ref-then-body-300", (damage("reference", "collective", 2), damage("body", "collective", 2, 300))),
          Condition("body-then-ref-10", (damage("body", "collective", 2), damage("reference", "collective", 2, 10))),
          Condition("body-then-ref-300", (damage("body", "collective", 2), damage("reference", "collective", 2, 300))),
          Condition("impose-50", (Event("impose", duration=50),)),
          Condition("impose-300", (Event("impose", duration=300),)),
          Condition("impose-inf", (Event("impose", duration=0),)))
COND_B = (SHAM, *(single("reference", b, r) for b in BANDS for r in (1, 2)), *(single("body", b, 2) for b in BANDS))
COND_C = (SHAM, *(single("reference", b, 2) for b in BANDS), *(single("body", b, 2) for b in BANDS),
          single("both", "collective", 2))
COND_D = (SHAM, *(single("reference", b, r) for b in BANDS for r in (1, 2)), single("body", "collective", 2),
          single("both", "regional", 2), single("both", "collective", 2),
          single("reference2", "regional", 2), single("reference2", "collective", 2))
COND_E = (SHAM, *(single("body", b, 2) for b in BANDS), *(single("reference", b, r) for b in BANDS for r in (1, 2)))
ENVIRONMENTS = ("none", "reference", "mixed")


def ch(sensor, so=(0, 0), actuator=None, ao=(0, 0), decision="linear"):
    """Channel spec: (sensor level, sensor offset, actuator level, actuator offset, decision)."""
    return (sensor, so, actuator or sensor, ao, decision)


SITE = ch("site")


@dataclass(frozen=True)
class Arm:
    name: str
    body: tuple | None = None          # None: comparison into V off
    reference: tuple | None = None     # None: working R held (events aside)
    control: str = "hold"              # inactive | hold | native | burst0 | periodic | arbiter | oracle | matched
    trigger: str = "region"            # arbiter: pooling of the mismatch feature
    latch: int = LATCH                 # arbiter: surprise latch W; 0 = none (change-point)
    surprise: str = "trajectory"       # arbiter latch threshold: trajectory (v2) | update (ME001's rule)
    mismatch_window: int = 0           # mismatch calibration window; 0 = the panel's window
    thresholds: str = "regime"         # regime | pooled (calibrated on CAL_FAMILIES only)
    abort: bool = False                # stop a burst when surprise appears during it
    clamp: str | None = None           # protected backup restoring R's content at this resolution
    germline: str | None = None        # panel F: incoming R is the protected founder record
    copies: int = 1                    # 2: two unprotected working records voted with the body
    packets: tuple = ("Q",)            # outgoing packets read by fresh recipients (F: the one passed on)
    privileged: bool = False


QR = ("Q", "R")
FULL = dict(body=SITE, reference=SITE)


def arbiter(name, **k):
    return Arm(name, **FULL, control="arbiter", **k)


ARMS_A = (
    Arm("inactive", control="inactive", packets=QR),
    Arm("hold_site", body=SITE, packets=QR),
    Arm("reciprocal", **FULL, control="native", packets=QR),
    Arm("write20_t0", **FULL, control="burst0", packets=QR),
    Arm("periodic20", **FULL, control="periodic", packets=QR),
    arbiter("changepoint", latch=0, packets=QR),
    arbiter("arbiter_me001", surprise="update", mismatch_window=1000, packets=QR),
    arbiter("arbiter", packets=QR),
    arbiter("arbiter_W300", latch=300, packets=QR),
    arbiter("arbiter_W100", latch=100, packets=QR),
    arbiter("arbiter_abort", abort=True, packets=QR),
    arbiter("arbiter_pooled", thresholds="pooled", packets=QR),
    arbiter("arbiter_site", trigger="site", packets=QR),
    Arm("oracle", **FULL, control="oracle", packets=QR, privileged=True),
)
ARMS_B = (
    Arm("inactive", control="inactive"),
    *(Arm(f"hold_{r}", body=ch(r)) for r in LEVELS),
    arbiter("arbiter_site", trigger="site", packets=QR),
    arbiter("arbiter", packets=QR),
    arbiter("arbiter_sheet", trigger="sheet", packets=QR),
    arbiter("changepoint", latch=0, packets=QR),
    Arm("oracle", **FULL, control="oracle", packets=QR, privileged=True),
)
ARMS_C = (
    Arm("inactive", control="inactive"),
    *(Arm(f"hold_{r}", body=ch(r)) for r in LEVELS),
    Arm("reciprocal", **FULL, control="native", packets=QR),
    Arm("write20_t0", **FULL, control="burst0", packets=QR),
    arbiter("arbiter_me001", surprise="update", mismatch_window=1000, packets=QR),
    arbiter("arbiter", packets=QR),
    arbiter("arbiter_pooled", thresholds="pooled", packets=QR),
    Arm("oracle", **FULL, control="oracle", packets=QR, privileged=True),
)
ARMS_D = (
    Arm("hold_site", body=SITE, packets=QR),
    *(Arm(f"clamp_{r}", body=SITE, clamp=r, packets=QR, privileged=True) for r in LEVELS),
    arbiter("arbiter", packets=QR),
    Arm("dual_vote", body=SITE, copies=2, packets=QR),
)
ARMS_E = (
    *(Arm(f"hold_{r}", body=ch(r)) for r in LEVELS),
    *(Arm(f"sign_{s}_{a}", body=ch(s, actuator=a, decision="sign")) for s in LEVELS for a in LEVELS),
    *(Arm(f"sign_{s}_{a}_eq", body=ch(s, actuator=a, decision="sign"), control="matched") for s in LEVELS for a in LEVELS),
)
ARMS_F = (
    Arm("inactive_Q", control="inactive"),
    Arm("hold_Q", body=SITE),
    Arm("hold_R", body=SITE, packets=("R",)),
    Arm("reciprocal_Q", **FULL, control="native"),
    Arm("reciprocal_R", **FULL, control="native", packets=("R",)),
    arbiter("arbiter_Q"),
    arbiter("arbiter_R", packets=("R",)),
    arbiter("arbiterW300_R", latch=300, packets=("R",)),
    Arm("germline_region", body=SITE, germline="region", packets=("germline",), privileged=True),
    Arm("germline_site", body=SITE, germline="site", packets=("germline",), privileged=True),
)

R1 = lambda fams, sigmas, gs=(1.0,): tuple(regime(f, s, g) for f in fams for s in sigmas for g in gs)
PANELS = {
    "A": {"title": "time: random onset, repeated injuries, sustained change", "window": 1800, "onset": "random",
          "regimes": R1(("F0",), (0.3, 0.1)) + R1(("F4", "BL"), (0.3,)), "conditions": COND_A, "arms": ARMS_A,
          "packets": ("protected", "target", "foreign_target", "zero")},
    "B": {"title": "coupling: does the useful trigger scale follow the body's correction scale?", "window": 1000,
          "onset": "start", "regimes": R1(("F0", "F4"), (0.3, 0.1), (0.25, 1.0, 2.5)), "conditions": COND_B,
          "arms": ARMS_B, "packets": ("protected", "target", "zero")},
    "C": {"title": "breadth: noise x pattern families, pooled thresholds on untouched families", "window": 1000,
          "onset": "start", "regimes": R1(("F0", "F4", "S4", "BL", "IS"), (0.05, 0.1, 0.2, 0.3, 0.4)),
          "conditions": COND_C, "arms": ARMS_C, "packets": ("copy_post", "protected", "target", "zero")},
    "D": {"title": "storage: protected backups at three resolutions", "window": 1000, "onset": "start",
          "regimes": R1(("F0", "F4", "BL", "IS"), (0.3,)) + R1(("F0",), (0.1,)), "conditions": COND_D,
          "arms": ARMS_D, "packets": ("protected", "backup_region", "backup_sheet", "target", "zero")},
    "E": {"title": "equal-dose majority voting", "window": 1000, "onset": "start",
          "regimes": R1(("F0", "F4"), (0.3, 0.1)), "conditions": COND_E, "arms": ARMS_E,
          "packets": ("target", "zero")},
    "F": {"title": "heredity over generations", "window": LIFE, "onset": "generation",
          "regimes": R1(("F0", "F4", "BL"), (0.3,)) + R1(("F0",), (0.1,)), "environments": ENVIRONMENTS,
          "arms": ARMS_F, "generations": GENERATIONS},
}
ARM = {p: {a.name: a for a in v["arms"]} for p, v in PANELS.items()}
PACKET_ONCE = ("protected", "backup_region", "backup_sheet", "target", "foreign_target", "zero")


def tasks():
    return [(p, r) for p, v in PANELS.items() for r in v["regimes"]]


def calibration_regimes():
    """Every regime an arbiter runs in, plus the calibration families at each (sigma, g) where a
    pooled-threshold arm runs."""
    out = {r for v in PANELS.values() if any(a.control == "arbiter" for a in v["arms"]) for r in v["regimes"]}
    for v in PANELS.values():
        if any(a.thresholds == "pooled" for a in v["arms"]):
            for r in v["regimes"]:
                _, s, g = parse(r)
                out.update(regime(f, s, g) for f in CAL_FAMILIES)
    return sorted(out)


def gain_regimes():
    return sorted({r for v in PANELS.values() if any(a.control == "matched" for a in v["arms"]) for r in v["regimes"]})


def coarser(s, a):
    return max(s, a, key=LEVELS.index)


# Registered contrasts: (panel, family, arm or packet, reference arm or packet). Positive = better
# for the first. Generational (panel F) contrasts are read at generation 8 and as the mean over
# generations 1-8, per environment.
MARGIN = 0.02
PRIMARY_ENDPOINTS = {"A": ("v_qual", "fQ_qual", "fR_qual"), "B": ("v_qual", "fQ_qual"), "C": ("v_qual", "fQ_qual"),
                     "D": ("v_qual", "fQ_qual", "fR_qual"), "E": ("v_qual", "fQ_qual"), "F": ("v_qual", "p_sign")}
SECONDARY_ENDPOINTS = {"A": ("e20_qual", "e100_qual", "vg_qual", "gQ_qual", "gR_qual", "r_sign", "rg_sign"),
                       "B": ("fR_qual", "v_sign", "e20_qual"), "C": ("fR_qual", "v_sign", "e20_qual"),
                       "D": ("v_sign",), "E": ("v_sign", "d_body_l1"), "F": ("v_sign",)}


def _contrasts():
    out = []
    add = lambda p, fam, a, b: out.append((p, fam, a, b))
    for a, b in (("hold_site", "inactive"), ("reciprocal", "hold_site"), ("write20_t0", "hold_site"),
                 ("periodic20", "hold_site")):
        add("A", "A1 fixed routes and schedules", a, b)
    for a, b in (("arbiter", "hold_site"), ("arbiter_me001", "hold_site"), ("arbiter", "arbiter_me001"),
                 ("arbiter", "oracle"), ("arbiter", "changepoint"), ("changepoint", "hold_site"), ("oracle", "hold_site")):
        add("A", "A2 arbitration under random onset", a, b)
    for a in ("arbiter_W300", "arbiter_W100", "arbiter_abort", "arbiter_pooled", "arbiter_site"):
        add("A", "A3 arbiter variants", a, "arbiter")
    add("A", "A4 storage", "protected", "hold_site")
    for a in ("arbiter_site", "arbiter", "arbiter_sheet", "changepoint", "oracle"):
        add("B", "B1 trigger scale vs hold", a, "hold_site")
    for a, b in (("arbiter_site", "arbiter"), ("arbiter_sheet", "arbiter"), ("arbiter", "oracle"),
                 ("arbiter_site", "oracle"), ("arbiter_sheet", "oracle")):
        add("B", "B2 trigger scale vs trigger scale", a, b)
    for a, b in (("hold_region", "hold_site"), ("hold_sheet", "hold_site"), ("hold_site", "inactive")):
        add("B", "B3 resolution and setpoint value", a, b)
    for a, b in (("hold_site", "inactive"), ("hold_region", "hold_site"), ("hold_sheet", "hold_site")):
        add("C", "C1 setpoint value and resolution", a, b)
    for a, b in (("arbiter", "hold_site"), ("arbiter_me001", "hold_site"), ("arbiter_pooled", "arbiter"),
                 ("arbiter", "oracle"), ("oracle", "hold_site"), ("reciprocal", "hold_site"), ("write20_t0", "hold_site")):
        add("C", "C2 arbitration across noise and families", a, b)
    for a, b in (("copy_post", "hold_site"), ("protected", "copy_post")):
        add("C", "C3 copy and storage", a, b)
    for r in LEVELS:
        add("D", "D1 protected backup vs hold", f"clamp_{r}", "hold_site")
    for r in ("region", "sheet"):
        add("D", "D2 coarse backup vs full backup", f"clamp_{r}", "clamp_site")
    add("D", "D3 live arbitration vs storage", "arbiter", "hold_site")
    add("D", "D3 live arbitration vs storage", "arbiter", "clamp_region")
    for k in ("backup_region", "backup_sheet"):
        add("D", "D4 coarse packets", k, "protected")
    for b in ("hold_site", "clamp_site", "arbiter"):
        add("D", "D5 redundant records", "dual_vote", b)
    for s in LEVELS:
        for a in LEVELS:
            add("E", "E1 equal-dose vote vs linear", f"sign_{s}_{a}_eq", f"hold_{coarser(s, a)}")
            add("E", "E2 equal-dose vote vs full-dose vote", f"sign_{s}_{a}_eq", f"sign_{s}_{a}")
    for a in LEVELS:
        for s in ("region", "sheet"):
            add("E", "E3 sensing at fixed actuator, equal dose", f"sign_{s}_{a}_eq", f"sign_site_{a}_eq")
    for a, b in (("hold_R", "hold_Q"), ("arbiter_R", "hold_R"), ("arbiter_R", "hold_Q"), ("arbiter_Q", "hold_Q"),
                 ("arbiterW300_R", "arbiter_R"), ("reciprocal_R", "hold_R"), ("reciprocal_Q", "hold_Q"),
                 ("hold_Q", "inactive_Q"), ("germline_region", "germline_site"), ("arbiter_R", "germline_site"),
                 ("hold_R", "germline_site")):
        add("F", "F1 heredity", a, b)
    return tuple(out)


CONTRASTS = _contrasts()


def template_hash():
    h = hashlib.sha256()
    for f in FAMILIES:
        h.update(f.encode())
        h.update(np.ascontiguousarray(TEMPLATES[f]).tobytes())
    return h.hexdigest()


def band_content():
    out = {}
    for f in FAMILIES:
        e = {k: float((v ** 2).sum()) for k, v in bands(TEMPLATES[f][0]).items()}
        tot = sum(e.values())
        out[f] = {k: round(v / tot, 4) for k, v in e.items()}
    return out


def design_dict():
    panels = {p: {k: ([asdict(x) for x in v] if k in ("conditions", "arms") else v) for k, v in spec.items()}
              for p, spec in PANELS.items()}
    return {
        "study": STUDY, "tag": TAG, "identities": IDENTITIES, "purpose": PURPOSE, "debug_blocks": DEBUG_BLOCKS,
        "messages": MESSAGES, "parents": PARENTS, "foreign": FOREIGN, "settle": SETTLE, "teach": TEACH,
        "amplitude": AMPLITUDE, "release": RELEASE, "read_updates": READ_UPDATES, "recipients": RECIPIENTS,
        "per_tissue_theta": PER_TISSUE_THETA,
        "arbiter": {"burst_updates": BURST_UPDATES, "burst_rate": BURST_RATE, "latch": LATCH,
                    "refractory": REFRACTORY, "quantile": QUANTILE},
        "period": PERIOD, "onset": ONSET, "early": EARLY, "life": LIFE, "generation_onset": GEN_ONSET,
        "generations": GENERATIONS, "mix": MIX, "bands": BANDS, "families": FAMILIES,
        "calibration_families": CAL_FAMILIES, "template_sha256": template_hash(), "blob_index": BLOB_INDEX,
        "band_content": band_content(), "panels": panels, "packet_once": PACKET_ONCE, "margin": MARGIN,
        "primary": PRIMARY, "primary_endpoints": PRIMARY_ENDPOINTS, "secondary_endpoints": SECONDARY_ENDPOINTS,
        "contrasts": CONTRASTS, "calibration_regimes": calibration_regimes(),
    }


def digest():
    payload = json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list)
    return hashlib.sha256(payload.encode()).hexdigest()


def sources(lane):
    files = sorted([*(lane / "mse").glob("*.py"), *(lane / "me001").glob("*.py"), *(lane / "me002").glob("*.py"),
                    lane / "operators.py"])
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m me002.design  ->  me002/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "me002" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
