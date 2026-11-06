"""AR001C: AR001's confirmation (the lane's first), on fresh confirmation blocks 920000-920015.

AR001 (frozen 23:20:01Z on 30 October 2026, digest 051af4cc7450) found in development that the controller, BE006's dial-SL
with a regime signal of hit rate h and false-alarm rate f, beats the best fixed policy (the vote) and the located but
undiscriminating dial at the reliability the registration declared for its confirmation (h 0.9, f 0.1), within the
harm bound. AR001C tests those two contrasts and the harm bound on blocks no study has drawn.

The draws: AR001's tissue, tag (mse-ar001) and code path, through ar001.worker.task and ar001.sim.run imported
unchanged, on the eight unit-body pairs, pooled exactly as in AR001 (per case the mean over the pairs, a block's value the
mean over its eight cases), with equal weights over AR001's eight scorings and BEST = the vote, frozen.
The purpose: mse.assay.RANGES assigns 920000-929999 to 'confirmation'. It is a range check in enrol only; Case.key() is
(block, message, parent), so the purpose does not enter any stream's address.

The arms: the reduced set {vote, rest, dial} in AR001's seven sigma-0 situations (none, body, memory, correlated,
shared, cue, change), all that the contrasts, U_ctrl and the harm bound need. The checks' bridge (Q3) shows a reduced-arm
task equals the full AR001 task's corresponding branches bit for bit on AR001's engineering blocks 900029-900032 (every
saved endpoint, trace, scalar and final state).
"""
from __future__ import annotations

import hashlib
import json
import math

from ar001 import design as A

STUDY = "AR001C"
TAG = A.TAG                                                    # the same tissue, tag and code path as AR001
IDENTITIES = {"confirmation": (920000, 920016)}                # 16 blocks, the development's own size (the lead)
BRIDGE_BLOCKS = (900029, 900033)                               # AR001's preflight (900029-30) and debug (900031-32)
BRIDGE_ROOTS = {900029: "preflight", 900030: "preflight", 900031: "debug", 900032: "debug"}
PURPOSE = {"debug": "engineering", "confirmation": "confirmation"}

ARMS = ("vote", "rest", "dial")
RUNS = tuple((s, 0.0, ARMS) for s in A.SITUATIONS)
UNITS, BODIES = A.UNITS, A.BODIES
BEST = "vote"
POINT = (0.9, 0.1)                                             # the declared confirmation point (h, f)

DEV = {"a": {"value": 0.112325, "sd_block": 0.033218}, "b": {"value": 0.058133, "sd_block": 0.010411}}
TARGET = {k: v["value"] / 3 for k, v in DEV.items()}           # each 95% half-width at most a third of its development value
SD_UPPER = 1.548                                               # the development SD estimate's upper 95% limit (15 df), as a factor
N_RULE = {"a": 6, "b": 4}                                      # the rule's minimum at the development SD
N_UPPER = 10                                                   # (a) at the SD's upper 95% limit
CRITERIA = {"C1": "the lower bound of (a) U_ctrl(0.9, 0.1) - U(vote) is above 0",
            "C2": "the lower bound of (b) U_ctrl(0.9, 0.1) - U_ctrl(1, 1) is above 0",
            "C3": "the upper bound of a sham's sheet cost r_all(rest) - r_all(dial) is at most 0.01 under scattered cue "
                  "damage (cue@0) and at most 0.002 with no event (none@0)"}
HARM = {"cue@0": 0.01, "none@0": 0.002}


def run_name(situation, sigma, arms=None):
    return A.run_name(situation, sigma)


RUNNAMES = tuple(run_name(*x) for x in RUNS)


def stage_blocks(stage, override=None):
    if stage == "debug":
        lo, hi = override if override is not None else BRIDGE_BLOCKS
        if not (BRIDGE_BLOCKS[0] <= lo < hi <= BRIDGE_BLOCKS[1]):
            raise ValueError("the debug stage runs on AR001's engineering blocks 900029-900032 only")
        return list(range(lo, hi))
    if override is not None:
        raise ValueError("block overrides are for the debug stage only")
    return list(range(*IDENTITIES[stage]))


def tasks():
    return A.tasks()


def design_dict():
    return {"study": STUDY, "tag": TAG, "identities": IDENTITIES, "bridge_blocks": BRIDGE_BLOCKS,
            "bridge_roots": BRIDGE_ROOTS, "purpose": PURPOSE, "ar001_digest": A.digest(), "arms": ARMS, "runs": RUNS,
            "units": UNITS, "bodies": BODIES, "best": BEST, "point": POINT, "dev": DEV, "target": TARGET,
            "sd_upper": SD_UPPER, "n_rule": N_RULE, "n_upper": N_UPPER, "criteria": CRITERIA, "harm": HARM,
            "weights": A.WEIGHTS, "scorings": A.SCORINGS, "right": A.RIGHT, "wrong": A.WRONG, "t_read": A.T_READ,
            "reads": A.READS, "window": A.WINDOW}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    out = dict(A.sources(lane))
    out.update({str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest()
                for f in sorted((lane / "ar001c").glob("*.py"))})
    return out


if __name__ == "__main__":      # python -m ar001c.design  ->  ar001c/frozen/design.json
    from pathlib import Path

    lane = Path(__file__).resolve().parents[1]
    out = lane / "ar001c" / "frozen" / "design.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"digest": digest(), "design": design_dict(), "sources": sources(lane)}, indent=1,
                              default=list) + "\n")
    print(out, digest()[:12], math.isfinite(TARGET["a"]))
