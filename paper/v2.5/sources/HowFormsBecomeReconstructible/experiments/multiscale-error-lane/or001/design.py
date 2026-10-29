"""OR001: the single source of truth for selection, evaluation, the reader and the checks.

Genome: x in R^6, decoded to maintenance body gains at site, region and sheet resolution
(0..G_MAX), an early-life multiplier on those gains for a newborn's first T_DEV updates (0..M_MAX;
a developmental programme), a record write rate from the body (0..RHO_MAX) and a packet mixture w
(packet = w R + (1 - w) Q).
Selection: antithetic evolution strategies from a near-zero genome (no setpoint), fitness = mean
body qualified agreement over generations 1..G_SEL of a chain, minus LAMBDA x body dose. Every
selection generation k draws new founders, theta, noise and injuries through its own tag
(mse-or001-s{seed}-sel{k}) on engineering blocks; the reading uses tag mse-or001 on fresh
development blocks, never seen by selection.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

import numpy as np

from me002.families import templates

TAG = "mse-or001"
STUDY = "OR001"
IDENTITIES = {
    "selection": (900970, 900972),     # engineering: 2 blocks x 4 messages (parent 0), new tag per generation
    "preflight": (900972, 900974),     # engineering: full-shape qualification of the reading
    "development": (910200, 910216),   # the OR001 reading cohort: 16 fresh blocks x 4 messages x 2 parents
}
PURPOSE = {"selection": "engineering", "preflight": "engineering", "development": "development"}
MESSAGES, PARENTS, SEL_PARENTS = (0, 1, 2, 3), (0, 1), (0,)
SETTLE, TEACH, AMPLITUDE, RELEASE = 120, 1000, 1.2, 200
LIFE, ONSET, G_SEL, G_READ = 1500, (700, 1101), 3, 6
INJURY_RMS = 2.0
MIX = (("body", 0.4), ("reference", 0.4), ("both", 0.2))
BANDS = ("fine", "regional", "collective")
G_MAX, M_MAX, RHO_MAX, T_DEV = 1.0, 5.0, 0.02, 300
X0 = (-3.8918, -3.8918, -3.8918, -1.3863, -4.5951, 0.0)   # gains 0.02, multiplier 1, write rate 0.0002, w = 0.5
POP, SIGMA_ES, ALPHA, K_GEN, SEEDS = 16, 0.5, 0.2, 40, (0, 1)
DOSE_SCALE = 1e4

SIGMAS = (0.05, 0.15, 0.3)
FAMILIES = ("F0", "BL")
INJURIES = ("none", "body", "record", "mixed")
LAMBDAS = (0.0, 0.05)
TEMPLATES = {f: templates(f, "mse-me002", AMPLITUDE) for f in FAMILIES}   # ME002's families, unchanged


@dataclass(frozen=True)
class Env:
    family: str
    sigma: float
    injuries: str
    cost: float

    @property
    def name(self):
        return f"{self.family}_s{self.sigma:g}_{self.injuries}_c{self.cost:g}"


ENVS = tuple(Env(f, s, i, c) for f in FAMILIES for s in SIGMAS for i in INJURIES for c in LAMBDAS)
ENV = {e.name: e for e in ENVS}
PRIMARY = Env("F0", 0.3, "mixed", 0.0).name


GENES = ("g_site", "g_region", "g_sheet", "m_dev", "rho_w", "w")
SCALE = {"g_site": G_MAX, "g_region": G_MAX, "g_sheet": G_MAX, "m_dev": M_MAX, "rho_w": RHO_MAX, "w": 1.0}


def decode(x):
    """x (..., 6) -> dict of gene arrays (...,)."""
    s = 1.0 / (1.0 + np.exp(-np.asarray(x, dtype=float)))
    return {g: SCALE[g] * s[..., i] for i, g in enumerate(GENES)}


# Fixed reference genomes for the reading (exact gene values; 'none' is the zero-gain floor).
REFERENCES = {
    "none": dict(g_site=0.0, g_region=0.0, g_sheet=0.0, m_dev=1.0, rho_w=0.0, w=0.0),
    "native_hold": dict(g_site=0.2, g_region=0.0, g_sheet=0.0, m_dev=1.0, rho_w=0.0, w=0.0),
    "native_copy": dict(g_site=0.2, g_region=0.0, g_sheet=0.0, m_dev=1.0, rho_w=0.0, w=1.0),
    "native_reciprocal": dict(g_site=0.2, g_region=0.0, g_sheet=0.0, m_dev=1.0, rho_w=0.002, w=0.0),
}
MARGIN = 0.02


def design_dict():
    return {"study": STUDY, "tag": TAG, "identities": IDENTITIES, "purpose": PURPOSE, "messages": MESSAGES,
            "parents": PARENTS, "selection_parents": SEL_PARENTS, "settle": SETTLE, "teach": TEACH,
            "amplitude": AMPLITUDE, "release": RELEASE, "life": LIFE, "onset": ONSET, "g_sel": G_SEL,
            "g_read": G_READ, "injury_rms": INJURY_RMS, "mix": MIX, "bands": BANDS, "genes": GENES, "scale": SCALE,
            "t_dev": T_DEV, "x0": X0, "es": {"population": POP, "sigma": SIGMA_ES, "alpha": ALPHA,
                                                  "generations": K_GEN, "seeds": SEEDS},
            "dose_scale": DOSE_SCALE, "envs": [asdict(e) for e in ENVS], "primary": PRIMARY,
            "references": REFERENCES, "margin": MARGIN,
            "template_sha256": hashlib.sha256(b"".join(np.ascontiguousarray(TEMPLATES[f]).tobytes() for f in FAMILIES)).hexdigest()}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted([*(lane / "mse").glob("*.py"), *(lane / "me002").glob("*.py"), *(lane / "or001").glob("*.py")])
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m or001.design  ->  or001/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "or001" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
