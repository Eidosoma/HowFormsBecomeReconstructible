"""GC001: graded cues. Positional error and the coupling length.

BE001's tissue, detector and commitment, unchanged and imported (be001.sim), at read gain 0.2, with one change: an
anchored cell no longer reads its own site's cue exactly. It reads the cue field at a quenched, noisy position:
  cue(x) = field(x + round(sigma * g)),  g ~ N(0, I) per site and axis, drawn once per case (address(tag, case, 'gc-eps')),
  periodic, the same unit normals g at every sigma (so levels are paired). sigma = 0 reads the exact field and is BE001.
The field is the event's cue field (the acquired record's signs; for a change, flipped inside the patch). Misreads fall
where the field changes within a few sites of a cell: at the pattern's boundaries, and coherently along them.
A matched control (scatter) flips, in each case, as many anchors as the noisy read misreads with no event, chosen
uniformly at random among the anchors (one permutation per case, shared by every sigma): the same count of wrong
anchors without the boundary coherence.
Arms: the cue arbiter (LR004) and BE001's ungated, noiseless detector at lambda 1, 1.5, 2 and 3.
Runs: none8 at every sigma; scatter8 at every sigma > 0; change4 and memory4 at sigma 0, 1 and 2.
Endpoints add to BE001's: the record's agreement in the boundary band (sites adjacent to a site of the other target
sign) and in the interior (taxicab distance >= 2), and the record's domain walls relative to the target's.
"""
from __future__ import annotations

import hashlib
import json

from be001 import design as B1
from dl001 import design as DL

TAG = "mse-gc001"
PROBE_TAG = "mse-p29"
STUDY = "GC001"
PROBE_BLOCKS = (900690, 900694)
IDENTITIES = {"preflight": (900694, 900696), "development": (910260, 910276)}
DEBUG_BLOCKS = (900696, 900698)
STATIC_BLOCKS = (900690, 900698)       # the static map's cases: engineering blocks only (no dynamics, no development case)
PURPOSE = {"preflight": "engineering", "development": "development"}

SIDE, SIGMA, CHUNK = B1.SIDE, B1.SIGMA, B1.CHUNK
BODIES, PATTERNS, THETAS, UNITS = B1.BODIES, B1.PATTERNS, B1.THETAS, B1.UNITS
MESSAGES, PARENTS, NCASE = B1.MESSAGES, B1.PARENTS, B1.NCASE
GAIN, RATE, KAPPA, G_LEAK, TAU = B1.GAIN, B1.RATE, B1.KAPPA, B1.G_LEAK, B1.TAU
BIO = {a: B1.BIO[a] for a in ("bio-1", "bio-1.5", "bio-2", "bio-3")}      # BE001's ungated, noiseless ladder
ARMS = ("cue", *BIO)
SIGMAS = (0.0, 0.5, 1.0, 2.0, 3.0)
EVENT_SIGMAS = (0.0, 1.0, 2.0)          # change and memory runs
BAND = 1                                # the boundary band: taxicab distance 1 from a site of the other target sign
RUNS = (*(("none", 8, s) for s in SIGMAS), *(("scatter", 8, s) for s in SIGMAS if s > 0),
        *(("change", 4, s) for s in EVENT_SIGMAS), *(("memory", 4, s) for s in EVENT_SIGMAS))
WINDOW, READS, TRACE = B1.WINDOW, B1.READS, B1.TRACE
TRACE_READS = tuple(range(TRACE, WINDOW + 1, TRACE))
parse_unit, unit_name = B1.parse_unit, B1.unit_name


def run_name(situation, size, sigma):
    return f"{situation}{size}@{sigma:g}"


RUNNAMES = tuple(run_name(*r) for r in RUNS)


def stage_blocks(stage, override=None):
    if override is None:
        return list(range(*IDENTITIES[stage]))
    lo, hi = override
    if stage != "preflight" or not (DEBUG_BLOCKS[0] <= lo < hi <= DEBUG_BLOCKS[1]):
        raise ValueError("block overrides are for preflight debugging on DEBUG_BLOCKS only")
    return list(range(lo, hi))


def tasks():
    return [("G", u) for u in UNITS]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "identities": IDENTITIES, "purpose": PURPOSE,
            "debug_blocks": DEBUG_BLOCKS, "probe_blocks": PROBE_BLOCKS, "static_blocks": STATIC_BLOCKS,
            "base": "be001.sim (BE001's tissue, detector and commitment, unchanged), lr002.sim.prepare (unchanged)",
            "cue_model": "field(x + round(sigma * g)), g ~ N(0, I) per site and axis, quenched per case, periodic; "
                         "scatter: the same count of anchors flipped uniformly at random",
            "side": SIDE, "sigma_body": SIGMA, "chunk": CHUNK, "gain": GAIN, "rate": RATE, "kappa": KAPPA,
            "g_leak": G_LEAK, "tau": TAU, "bio": BIO, "arms": ARMS, "sigmas": SIGMAS, "event_sigmas": EVENT_SIGMAS,
            "band": BAND, "runs": RUNS, "bodies": {b: list(DL.BODIES[b]) for b in BODIES}, "patterns": PATTERNS,
            "thetas": THETAS, "units": UNITS, "window": WINDOW, "reads": READS, "trace": TRACE,
            "be001_digest": B1.digest()}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    files = sorted(f for d in ("mse", "br001", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005",
                               "be001", "gc001")
                   for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m gc001.design  ->  gc001/frozen/design.json
    from pathlib import Path
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "gc001" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
