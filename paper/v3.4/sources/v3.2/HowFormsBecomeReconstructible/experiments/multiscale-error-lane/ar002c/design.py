"""AR002C: AR002's confirmation, on fresh confirmation blocks 920128-920147.

AR002 (frozen 14:17:47Z on 31 October 2026, digest 1d13005e4ee3) found in development that the controller driven by the
tissue's own detector, det (BE006's dial-SL opened over det's footprint), beats the best fixed policy (the vote) and
keeps more than half of the declared signal's worth at AR001C's confirmed point, within the harm bound. AR002C tests
those two contrasts and the harm bound on blocks no study has drawn, as REGISTRATION_AR002.md declared before AR002's
development ran (its AR002C section); the lead set the count from the development under the declared rule.

The draws: AR002's tissue, tag (mse-ar002) and code path, through ar002.worker.task (and through it ar002.sim.run_det and
ar001.sim.run) imported unchanged, on the eight unit-body pairs, pooled exactly as in AR002 (per case the mean over the
pairs, a block's value the mean over its eight cases, a criterion's value the mean over the blocks), with equal weights
over AR001's eight scorings, BEST = the vote and det's detector as frozen in ar002.design.DETECTORS.
The purpose: mse.assay.RANGES assigns 920000-929999 to 'confirmation'. It is a range check in enrol only; Case.key() is
(block, message, parent), so the purpose enters no stream's address.

The arms: vote, rest and dial (ar001.sim.run) and det (ar002.sim.run_det) in AR001's seven sigma-0 situations (none,
body, memory, correlated, shared, cue, change; change scored new and old), all that (a), (b) and the harm bound need:
28 arm-runs a task. The checks' bridge (Q3) shows a reduced task equals AR002's full task's corresponding branches bit
for bit on AR002's engineering blocks 900356-900359 (its preflight and debug outputs, drawn under the frozen digest).

The intervals (every criterion and reported contrast): over the n blocks, mean +- t(0.975, n - 1) x SD / sqrt(n), with
SD = max(the SD of the n block values, the SD of the n x 8 per-case values / sqrt(8)); n = 20 here, t(0.975, 19).
"""
from __future__ import annotations

import hashlib
import json

from ar002 import design as A2

STUDY = "AR002C"
TAG = A2.TAG                                                   # the same tissue, tag and code path as AR002
IDENTITIES = {"confirmation": tuple(range(920128, 920148))}    # 20 blocks (the lead's count); AR001 holds 920000-920127
BRIDGE_BLOCKS = (900356, 900357, 900358, 900359)               # AR002's preflight (900356-57) and debug (900358-59)
BRIDGE_ROOTS = {900356: "preflight", 900357: "preflight", 900358: "debug", 900359: "debug"}
PURPOSE = {"debug": "engineering", "confirmation": "confirmation"}

A1_ARMS = ("vote", "rest", "dial")
DET_ARMS = ("det",)
ARMS = A1_ARMS + DET_ARMS
RUNS = tuple((s, 0.0, A1_ARMS, DET_ARMS, A2.SIZE) for s in A2.SITUATIONS)
UNITS, BODIES, SITUATIONS, SCORINGS = A2.UNITS, A2.BODIES, A2.SITUATIONS, A2.SCORINGS
NCASE, WINDOW, READS, T_READ, TRACE, SIDE = A2.NCASE, A2.WINDOW, A2.READS, A2.T_READ, A2.TRACE, A2.SIDE
BEST = "vote"
POINT = (0.9, 0.1)                                             # AR001C's confirmed point (h, f), for (b)
DETECTOR = A2.DETECTORS["det"]                                 # frozen in AR002; no retuning

# the development (AR002, 910646-910650 + 910664-910674, 16 blocks) and the declared rule: both 95% half-widths at most a
# third of their development values, SD = max(block SD, case SD / sqrt 8); the lead set 20 blocks
DEV = {"a": {"value": 0.060921, "sd": 0.027287, "sd_block": 0.023785, "sd_case8": 0.027287},
       "b": {"value": 0.041825, "sd": 0.009567, "sd_block": 0.008487, "sd_case8": 0.009567}}
TARGET = {k: v["value"] / 3 for k, v in DEV.items()}
SD_UPPER = 1.5477                                              # the development SD estimate's upper 95% limit (15 df), a factor
N_RULE = {"a": 10, "b": 5}                                     # the rule's minimum at the development SD
N_UPPER = {"a": 20, "b": 7}                                    # at the SD's upper 95% limit
CRITERIA = {"C1": "the 95% lower bound of (a) U(det) - U(vote) is above 0",
            "C2": "the 95% lower bound of (b) (U(det) - U(rest)) - (U_ctrl(0.9, 0.1) - U(rest)) / 2 is above 0",
            "C3": "the 95% upper bounds of r_all(rest) - r_all(det) at t = 8,000 are at most 0.01 under scattered cue damage "
                  "(cue@0) and at most 0.002 with no event (none@0)"}
HARM = {"cue@0": 0.01, "none@0": 0.002}
INTERVAL = "mean +- t(0.975, n - 1) x max(block SD, case SD / sqrt 8) / sqrt(n) over the n blocks"


def run_name(situation, sigma, *_):
    return A2.run_name(situation, sigma)


RUNNAMES = tuple(run_name(*x) for x in RUNS)


def stage_blocks(stage, override=None):
    if stage == "debug":
        blocks = list(BRIDGE_BLOCKS) if override is None else list(override)
        if not set(blocks) <= set(BRIDGE_BLOCKS):
            raise ValueError("the debug stage runs on AR002's engineering blocks 900356-900359 only")
        return blocks
    if override is not None:
        raise ValueError("block overrides are for the debug stage only")
    return list(IDENTITIES[stage])


def tasks():
    return A2.tasks()


def design_dict():
    return {"study": STUDY, "tag": TAG, "identities": IDENTITIES, "bridge_blocks": BRIDGE_BLOCKS,
            "bridge_roots": BRIDGE_ROOTS, "purpose": PURPOSE, "ar002_digest": A2.digest(), "detector": DETECTOR,
            "a1_arms": A1_ARMS, "det_arms": DET_ARMS, "runs": RUNS, "units": UNITS, "bodies": BODIES, "best": BEST,
            "point": POINT, "dev": DEV, "target": TARGET, "sd_upper": SD_UPPER, "n_rule": N_RULE, "n_upper": N_UPPER,
            "criteria": CRITERIA, "harm": HARM, "interval": INTERVAL, "weights": A2.WEIGHTS, "scorings": SCORINGS,
            "right": A2.RIGHT, "wrong": A2.WRONG, "t_read": T_READ, "reads": READS, "window": WINDOW}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    out = dict(A2.sources(lane))
    out.update({str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest()
                for f in sorted((lane / "ar002c").glob("*.py"))})
    return out


if __name__ == "__main__":      # python -m ar002c.design  ->  ar002c/frozen/design.json (phase B, on the lead's word)
    from pathlib import Path

    lane = Path(__file__).resolve().parents[1]
    out = lane / "ar002c" / "frozen" / "design.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"digest": digest(), "design": design_dict(), "sources": sources(lane)}, indent=1,
                              default=list) + "\n")
    print(out, digest()[:12])
