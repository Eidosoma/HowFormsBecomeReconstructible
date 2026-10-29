"""ME001 v2: the single source of truth for the runner, the reader and the checks.

A development study, not a confirmation (PROTOCOL section 8). Every regime, condition,
arm, constant and identity range is fixed here before any development outcome, and the
registration (REGISTRATION.md, frozen/design.json) records DESIGN's digest. The runner
refuses development work when the digest differs from the frozen one.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

import numpy as np

from mse.native import LEVELS, address
from mse.ops import PATCH

TAG = "mse-me001-v2"
STUDY = "ME001 v2"

# Reserved before sampling; half-open block ranges. Engineering identities never enter the
# development analysis; development identities are touched only by the frozen runner.
IDENTITIES = {
    "calibration": (900900, 900916),   # engineering: arbiter thresholds, theory linearisation points
    "preflight": (900920, 900922),     # engineering: full-shape qualification, timing, reader dry run
    "development": (910000, 910016),   # the ME001 v2 cohort: 16 source blocks
}
PURPOSE = {"calibration": "engineering", "preflight": "engineering", "development": "development"}
DEBUG_BLOCKS = (900990, 900992)          # unreserved engineering blocks for debugging the tools


def stage_blocks(stage, override=None):
    """The stage's reserved blocks; an override is allowed only for preflight-style debugging
    on the unreserved engineering debug blocks."""
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))

# Target families (roll of the four half-planes) and noise levels; every block runs all six.
FAMILIES = {"F0": (0, 0), "F2": (2, 2), "F4": (4, 4)}
SIGMAS = (0.3, 0.1)
REGIMES = {f"{f}_s{s:.1f}": (f, s) for s in SIGMAS for f in FAMILIES}
PRIMARY = "F0_s0.3"

MESSAGES, PARENTS = (0, 1, 2, 3), (0, 1)
FOREIGN = {0: 1, 1: 0, 2: 3, 3: 2}        # the orthogonal message, same block and parent
SETTLE, TEACH, AMPLITUDE, RELEASE = 120, 1000, 1.2, 200
WINDOW, READ_UPDATES, RECIPIENTS = 1000, 1000, 4
EARLY = (20, 100)
TRACE_TIMES = (1, 2, 3, 5, 10, 20, 50, 100, 200, 500, 1000)
PER_TISSUE_THETA = True                   # theta spread U(0.15, 0.30) per block, as in L15/L17

# Provenance-gated arbiter: P4b's rule and constants, unchanged.
BURST_UPDATES, BURST_RATE, LATCH, REFRACTORY, QUANTILE = 20, 0.1, 1000, 200, 0.995

LOCATIONS = ("body", "reference", "both")
BANDS = ("fine", "regional", "collective")
RMS = (0.5, 1.0, 2.0)
CONDITIONS = (("sham", "none", 0.0),) + tuple((l, b, a) for l in LOCATIONS for b in BANDS for a in RMS)
FULL = tuple(range(len(CONDITIONS)))
SINGLE = tuple(i for i, c in enumerate(CONDITIONS) if c[0] != "both")


def condition_name(i):
    loc, band, rms = CONDITIONS[i]
    return "sham" if loc == "sham" else f"{loc}-{band}-{rms:g}"


def ch(sensor, so=(0, 0), actuator=None, ao=(0, 0), decision="linear"):
    """Channel spec: (sensor level, sensor offset, actuator level, actuator offset, decision)."""
    return (sensor, so, actuator or sensor, ao, decision)


@dataclass(frozen=True)
class Segment:
    updates: int
    body: tuple | None = None          # None: comparison into V off
    reference: tuple | None = None     # None: working R held
    policy: str | None = None          # None | burst | arbiter | changepoint | oracle


@dataclass(frozen=True)
class Arm:
    name: str
    panel: str
    segments: tuple
    conditions: str = "full"           # full (28) | single (19: sham, body, reference)
    capture: str = "body"              # body | snapshot (Q from the window-start body)
    privileged: bool = False
    traced: bool = False               # record sensor features at every update
    foreign: bool = False              # also read the matched foreign packet


def _arms():
    one = lambda **k: (Segment(WINDOW, **k),)
    arms = [Arm("inactive", "routes", one(), traced=True, foreign=True)]
    for r in LEVELS:
        arms.append(Arm(f"body_{r}", "routes", one(body=ch(r)), traced=r == "site", foreign=r == "site"))
    for r in LEVELS:
        arms.append(Arm(f"reference_{r}", "routes", one(reference=ch(r))))
    for r in LEVELS:
        arms.append(Arm(f"reciprocal_{r}", "routes", one(body=ch(r), reference=ch(r)),
                        traced=r == "site", foreign=r == "site"))
    for s in LEVELS:
        for a in LEVELS:
            arms.append(Arm(f"sign_{s}_{a}", "factorial", one(body=ch(s, actuator=a, decision="sign")), "single"))
    for lvl in ("region", "sheet"):
        arms.append(Arm(f"place_{lvl}_act", "placement", one(body=ch(lvl, ao=(1, 1))), "single"))
        arms.append(Arm(f"place_{lvl}_sense", "placement", one(body=ch(lvl, so=(1, 1))), "single"))
    for r in ("site", "region"):
        arms.append(Arm(f"write500_{r}", "timing", (Segment(500, reference=ch(r)), Segment(500, body=ch(r)))))
        arms.append(Arm(f"wait500_{r}", "timing", (Segment(500), Segment(500, body=ch(r)))))
        arms.append(Arm(f"write20_{r}", "timing", (Segment(BURST_UPDATES, reference=ch(r), policy="burst"),
                                                   Segment(WINDOW - BURST_UPDATES, body=ch(r)))))
        arms.append(Arm(f"wait20_{r}", "timing", (Segment(BURST_UPDATES), Segment(WINDOW - BURST_UPDATES, body=ch(r)))))
    for r in LEVELS:
        arms.append(Arm(f"permute_{r}", "lesions", one(body=ch(r, decision="permute")), "single"))
        arms.append(Arm(f"reverse_{r}", "lesions", one(body=ch(r, decision="reverse")), "single"))
    arms.append(Arm("snapshot", "capture", one(body=ch("site")), capture="snapshot"))
    full = dict(body=ch("site"), reference=ch("site"))
    arms.append(Arm("arbiter_region", "arbitration", one(**full, policy="arbiter"), traced=True, foreign=True))
    arms.append(Arm("changepoint_region", "arbitration", one(**full, policy="changepoint")))
    arms.append(Arm("oracle_location", "arbitration", one(**full, policy="oracle"), privileged=True))
    return tuple(arms)


ARMS = _arms()
ARM = {a.name: a for a in ARMS}
# Packets read without a correction window. protected = pre-damage R and target = clean
# template are privileged comparators; off_reader = recipients with comparison off.
PACKETS = ("copy_post", "protected", "target", "zero", "off_reader")
PACKET_CONDITIONS = {"copy_post": "full", "protected": "once", "target": "once", "zero": "once",
                     "off_reader": "once"}
PRIVILEGED_PACKETS = ("protected", "target")
FOREIGN_PACKETS = ("copy_post", "protected")


def arm_conditions(arm: Arm):
    return FULL if arm.conditions == "full" else SINGLE


def permutation(level):
    """The fixed placement permutation at a sensor's resolution: a derangement."""
    n = (16 // PATCH[level]) ** 2
    rng = address(TAG, "permutation", level)
    while True:
        p = rng.permutation(n)
        if not np.any(p == np.arange(n)):
            return tuple(int(i) for i in p)


PERMUTATIONS = {lvl: permutation(lvl) for lvl in LEVELS}

# Registered contrasts: (family, arm, reference). Positive = better for the arm.
MARGIN = 0.02
PRIMARY_ENDPOINTS = ("v1000_qual", "f_qual")
SECONDARY_ENDPOINTS = ("v1000_sign", "f_sign", "f_rec", "v20_qual", "v100_qual", "v1000_margin", "f_margin")


def _contrasts():
    out = []
    add = lambda fam, a, b: out.append((fam, a, b))
    for r in LEVELS:
        add("C1 route vs inactive", f"body_{r}", "inactive")
        add("C1 route vs inactive", f"reciprocal_{r}", "inactive")
        add("C3 reciprocal vs hold", f"reciprocal_{r}", f"body_{r}")
        add("C12 reference alias", f"reference_{r}", "inactive")
    for a in ("body_site", "body_region", "body_sheet", "reciprocal_site", "arbiter_region", "changepoint_region",
              "write20_site", "write20_region", "snapshot", "oracle_location"):
        add("C2 vs post-damage copy", a, "copy_post")
    add("C4 resolution", "body_region", "body_site")
    add("C4 resolution", "body_sheet", "body_site")
    add("C4 resolution", "body_sheet", "body_region")
    add("C5 arbitration", "arbiter_region", "body_site")
    add("C5 arbitration", "arbiter_region", "changepoint_region")
    add("C5 arbitration", "arbiter_region", "oracle_location")
    add("C5 arbitration", "changepoint_region", "body_site")
    add("C5 arbitration", "oracle_location", "body_site")
    for r in ("site", "region"):
        add("C6 timing", f"write500_{r}", f"wait500_{r}")
        add("C6 timing", f"write20_{r}", f"wait20_{r}")
        add("C6 timing", f"write20_{r}", f"body_{r}")
        add("C6 timing", f"wait500_{r}", f"body_{r}")
    coarser = lambda s, a: max(s, a, key=LEVELS.index)
    for s in LEVELS:
        for a in LEVELS:
            add("C7 sign vs linear", f"sign_{s}_{a}", f"body_{coarser(s, a)}")
    for a in LEVELS:
        for s in ("region", "sheet"):
            add("C7 sensing at fixed actuator", f"sign_{s}_{a}", f"sign_site_{a}")
    for s in LEVELS:
        for a in ("region", "sheet"):
            add("C7 actuation at fixed sensor", f"sign_{s}_{a}", f"sign_{s}_site")
    for lvl in ("region", "sheet"):
        add("C8 placement", f"place_{lvl}_act", f"body_{lvl}")
        add("C8 placement", f"place_{lvl}_sense", f"body_{lvl}")
    for r in LEVELS:
        add("C9 lesions", f"permute_{r}", f"body_{r}")
        add("C9 lesions", f"reverse_{r}", f"body_{r}")
    add("C10 capture", "snapshot", "body_site")
    add("C10 capture", "zero", "body_site")
    add("C11 storage", "protected", "copy_post")
    add("C11 storage", "target", "protected")
    add("C11 storage", "copy_post", "zero")
    add("C11 storage", "body_site", "protected")
    return tuple(out)


CONTRASTS = _contrasts()


def design_dict():
    return {
        "study": STUDY, "tag": TAG, "identities": IDENTITIES, "purpose": PURPOSE, "debug_blocks": DEBUG_BLOCKS,
        "families": FAMILIES, "sigmas": SIGMAS, "regimes": REGIMES, "primary": PRIMARY,
        "messages": MESSAGES, "parents": PARENTS, "foreign": FOREIGN,
        "settle": SETTLE, "teach": TEACH, "amplitude": AMPLITUDE, "release": RELEASE,
        "window": WINDOW, "read_updates": READ_UPDATES, "recipients": RECIPIENTS,
        "early": EARLY, "trace_times": TRACE_TIMES, "per_tissue_theta": PER_TISSUE_THETA,
        "arbiter": {"burst_updates": BURST_UPDATES, "burst_rate": BURST_RATE, "latch": LATCH,
                    "refractory": REFRACTORY, "quantile": QUANTILE},
        "conditions": CONDITIONS, "single": SINGLE,
        "arms": [asdict(a) for a in ARMS], "packets": PACKETS, "packet_conditions": PACKET_CONDITIONS,
        "privileged_packets": PRIVILEGED_PACKETS, "foreign_packets": FOREIGN_PACKETS,
        "permutations": PERMUTATIONS, "margin": MARGIN, "primary_endpoints": PRIMARY_ENDPOINTS,
        "secondary_endpoints": SECONDARY_ENDPOINTS, "contrasts": CONTRASTS,
    }


def digest():
    payload = json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list)
    return hashlib.sha256(payload.encode()).hexdigest()


def sources(lane):
    files = sorted([*(lane / "mse").glob("*.py"), *(lane / "me001").glob("*.py"), lane / "operators.py"])
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m me001.design  ->  me001/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "me001" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
