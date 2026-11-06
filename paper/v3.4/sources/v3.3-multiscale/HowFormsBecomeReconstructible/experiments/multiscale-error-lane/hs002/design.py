"""HS002's design: a plateau or a slow drift (PLAN_HS002.md). HS001's lineages continued from their saved rewrite-256
records to 1,024 rewrites.

HS001 (frozen, imported unchanged) and through it E014's machinery (E001, E006, E014, common.py; pinned by sha256)
supply everything; HS002 adds only the continuation (generations 257-1,024 from each lineage's saved outgoing record
after rewrite 256), eight checkpoints past 256, the fit over all 24 checkpoints with the identification bound N/4 =
256, the model-free late changes, and the declared readings. Every source block's HS001 raw file is checked against
the sha256 its HS001 run recorded before it is continued.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from hs001 import design as H1

STUDY = "HS002"
TAG = "mse-hs002"                 # bookkeeping only (the E-series engine keeps its seeds)
PROBE_TAG = "mse-p50"
LANE = H1.LANE
EXP = H1.EXP
HS001_RUNS = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/hs001")

START = 256                       # the saved record: each lineage's outgoing packets after rewrite 256
HORIZON = 1024
NEW_CHECKPOINTS = (320, 384, 448, 512, 640, 768, 896, 1024)
CHECKPOINTS = tuple(H1.CHECKPOINTS) + NEW_CHECKPOINTS          # all 24, for the fit and the curves
FACTORS = {"development": (1, 4), "probe": (1, 4), "preflight": (1, 4), "debug": (1, 4), "smoke": (1, 4),
           "e014": (1,)}          # the 128-byte record is reported only; E014's continuation at 2,048 bytes only
LINEAGE = H1.LINEAGE
PROBES = H1.PROBES
LATE = (768, 896, 1024)           # the model-free late mean past 256

# The reading rules (PLAN_HS002.md, fixed before any value past rewrite 256)
H_GRID = H1.H_GRID
H2_GRID = H1.H2_GRID
IDENTIFIED_H_MAX = HORIZON / 4    # 256
BOOT = H1.BOOT
DENOM_MIN_FRACTION = H1.DENOM_MIN_FRACTION

SOURCE_ROOT = {"smoke": HS001_RUNS / "smoke", "probe": HS001_RUNS / "p49", "preflight": HS001_RUNS / "preflight",
               "debug": HS001_RUNS / "debug_v2", "development": HS001_RUNS / "development", "e014": HS001_RUNS / "e014"}
IDENTITIES = {"smoke": [950000, 950001], "probe": list(range(950010, 950018)), "preflight": [950020, 950021],
              "debug": [950022, 950023], "development": list(range(951000, 951128)), "e014": list(range(12000, 12064))}
TEST_BLOCKS = [950002, 950003]    # in-memory only: HS001's lifecycle to 256, then the continuation
STAGE_TAG = {"smoke": TAG, "probe": PROBE_TAG, "preflight": TAG, "debug": TAG, "development": TAG, "e014": TAG}
EXPORT_STAGES = ("smoke", "probe", "preflight", "debug", "development")   # no identity export for E014's cohort


def stage_blocks(stage):
    return list(IDENTITIES[stage])


def source_manifests():
    """sha256 of each source stage's HS001 manifest (provenance of the saved rewrite-256 records)."""
    out = {}
    for stage, root in SOURCE_ROOT.items():
        p = root / "manifest.json"
        out[stage] = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
    return out


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "hs001_digest": H1.digest(), "start": START,
            "horizon": HORIZON, "new_checkpoints": NEW_CHECKPOINTS, "checkpoints": CHECKPOINTS, "factors": FACTORS,
            "lineage": LINEAGE, "probes": PROBES, "late": LATE, "h_grid": H_GRID, "h2_grid": H2_GRID,
            "identified_h_max": IDENTIFIED_H_MAX, "boot": BOOT, "denom_min_fraction": DENOM_MIN_FRACTION,
            "identities": IDENTITIES, "test_blocks": TEST_BLOCKS, "stage_tag": STAGE_TAG, "export_stages": EXPORT_STAGES,
            "source_roots": {k: str(v) for k, v in SOURCE_ROOT.items()}, "source_manifests_sha256": source_manifests(),
            "e_sources": H1.e_sources(),
            "continuation": "each lineage's outgoing packets after rewrite 256 (HS001's saved raw f<F>/final_packets, "
                            "checked against HS001's recorded sha256) renewed by HS001's generation for rewrites 257-1,024; "
                            "the checkpoint reader on the shared terminal stream; the protected reads are HS001's (constant)"}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane=LANE):
    out = H1.sources(lane)
    out.update({str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest()
                for f in sorted((lane / "hs002").glob("*.py"))})
    return out


if __name__ == "__main__":      # python -m hs002.design  ->  hs002/frozen/design.json (phase B, on the lead's word)
    import time
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(), "design": design_dict()}
    path = LANE / "hs002" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
