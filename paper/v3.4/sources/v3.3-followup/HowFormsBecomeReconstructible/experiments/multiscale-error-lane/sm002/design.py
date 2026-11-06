"""SM002: does the reader's size explain the scale loss? (item 1 of REPORT_SM001.md's Next). DRAFT for the lead's review
(phase A).

SM001 doubled every declared length of BE006's tissue (lam_rest and lam_sig, the stripes' width w, the patch L, the
footprint's dilation) at a fixed 64 x 64 sheet and scored each refined condition against its half-scale twin (the
transfer condition at half every length, on the same blocks, cases, streams, anchors and patch corner): a late signal
lost 0.156 of the fresh successor's reconstruction (S4), in the reading, not the episode (S5, S6). The named
candidate: the reader's own lengths (dw's nearest-neighbour coupling and interface, its record's bond step, the bonds'
grain) do not double.

SM002 reruns SM001's six refinement and twin units unchanged (sm001.sim.run, imported; sm001/ is frozen) on fresh
blocks and reads every final record with two readers:
  u    the unscaled reader: sm001.sim.successor as SM001's worker calls it (the S3/S4 replication)
  cg   the half-scale reader seen at twice the grain: the record coarse-grained 2 x 2 by a declared rule
       (sm002.coarse), read by sm001.sim.successor unchanged on the half-side lattice, the final body lifted back and
       scored on the full grid exactly as u is
The main contrast: E(refined, cg) - E(twin, u), under the late signal (m 2) and the prompt one (m 0). The control:
E(twin, cg) - E(twin, u) (is cg simply a better reader?). See REGISTRATION_SM002.md.
"""
from __future__ import annotations

import hashlib
import json

from sm001 import design as S1D

TAG = "mse-sm002"
PROBE_TAG = "mse-p43"
STUDY = "SM002"
# the lead's assignment (31 October 2026; scanned free at about 11:15Z by date -u and again by fork M2; inside
# mse.assay.RANGES): engineering 900330-900345, development 910653-910662 and 910676-910681, reserve 910737-910743
# and 910745
IDENTITIES = {"preflight": (900334, 900335), "dev": tuple(range(910653, 910663)) + tuple(range(910676, 910682))}
RESERVE = tuple(range(910737, 910744)) + (910745,)
PROBE_BLOCKS = (900330, 900334)            # P43: 900330-900333
DEBUG_BLOCKS = (900336, 900338)            # preflight debugging: 900336-900337
SMOKE_BLOCK = 900338
PURPOSE = {"probe": "engineering", "preflight": "engineering", "dev": "development"}

REFINE = ("W8_x64_r2", "W16_x64_r2", "W32_x64_r2")
TWINS = ("W4_x64", "W8_x64", "W16_x64")
UNITS = TWINS + REFINE
READERS = ("u", "cg")
CG_STREAM = "dw-cg"                        # the coarse reader's own birth and noise addresses (independent of u's)
GRAIN = 2                                  # the coarse reader's cell: 2 x 2 sites

GAIN, WINDOW2, READS2 = S1D.GAIN, S1D.WINDOW2, S1D.READS2
WINDOW, READS = S1D.WINDOW, S1D.READS


def unit(name):
    return S1D.UNIT[name]


def unit_arms(name):
    return S1D.unit_arms(name)


def twin_unit(name):
    """The twin of a refined unit: the transfer unit at half the width, on the same side."""
    u = S1D.UNIT[name]
    return S1D.unit_name(u["w"] // 2, u["side"])


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "identities": IDENTITIES, "reserve": RESERVE,
            "probe_blocks": PROBE_BLOCKS, "debug_blocks": DEBUG_BLOCKS, "purpose": PURPOSE, "units": UNITS,
            "refine": REFINE, "twins": TWINS, "readers": READERS, "cg_stream": CG_STREAM, "grain": GRAIN,
            "gain": GAIN, "window2": WINDOW2, "reads2": READS2, "window": WINDOW, "reads": READS,
            "sm001_units": {u: S1D.UNIT[u] for u in UNITS}, "arms": {u: [a["name"] for a in unit_arms(u)] for u in UNITS},
            "sm001_digest": S1D.digest()}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def stage_blocks(stage, override=None):
    if override is not None:
        lo, hi = override
        if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
            raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
        return list(range(lo, hi))
    if stage == "probe":
        return list(range(*PROBE_BLOCKS))
    return list(IDENTITIES[stage])


def sources(lane):
    files = sorted(f for d in ("mse", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005", "be001",
                               "be002", "be004", "be005", "be006", "np001", "sm001", "sm002")
                   for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m sm002.design  ->  sm002/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "sm002" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
