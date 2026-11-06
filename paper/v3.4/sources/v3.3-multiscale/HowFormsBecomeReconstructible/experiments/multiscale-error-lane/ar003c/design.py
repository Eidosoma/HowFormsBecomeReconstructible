"""AR003C: AR003's confirmation, on fresh confirmation blocks 920365-920380.

AR003 (frozen 13:25:00Z on 1 November 2026, digest d392002671e6) found in development that the controller vms (DET_STAR,
det's rule at every box from 2 to 12 with n 3, driving AR002's dial over its footprint, with the vote as the default)
beats the best fixed policy (the vote) over the size mix and AR002's controller (det with the rest default) at 8 x 8,
within the harm bound. AR003C tests those two contrasts and the harm bound on blocks no study has drawn, as
REGISTRATION_AR003.md declared before AR003's development ran (its AR003C section); the lead set the count, 16 blocks.

The draws: AR003's tissue, tag (mse-ar003) and code path, through ar003.worker.task (and through it ar001.sim.run,
ar002.sim.run_det and ar003.sim.run_vd) imported unchanged, on the eight unit-body pairs, pooled exactly as in AR003
(per case the mean over the pairs, a block's value the mean over its eight cases, a criterion's value the mean over the
blocks), with equal weights over AR001's eight scorings and over the three sizes, BEST = the vote, det and DET_STAR as
frozen in ar003.design. The purpose: mse.assay.RANGES assigns 920000-929999 to 'confirmation'; it is a range check in
enrol only, and Case.key() is (block, message, parent), so the purpose enters no stream's address.

The arms: the vote, det and vms, in only the runs C1-C3 need (36 arm-runs a task, AR003's development task 63):
  4 x 4    none and cue: vote, det, vms (scored on every size's patch; det for U_8(det))
           body, memory, correlated, shared, change: vote, vms (change gives U_4's information-limit pair, as AR003's
           development read it; the identity makes it 1/8 either way)
  2 x 2    memory, correlated, body, shared: vote, vms
  8 x 8    memory, correlated, body, shared: vote, det, vms
ms, vdial and the misread runs are left out. The bridge (Q3): every reduced branch equals AR003's full development task's
corresponding branch bit for bit on engineering block 900162 (the reference: AR003's frozen ar003.worker.run_task, all
63 arm-runs, run on that block by this package's reference stage).

The intervals (every criterion and reported contrast): over the n blocks, mean +- t(0.975, n - 1) x SD / sqrt(n), with
SD = max(the SD of the n block values, the SD of the n x 8 per-case values / sqrt(8)); n = 16 here, t(0.975, 15).
"""
from __future__ import annotations

import hashlib
import json

from ar003 import design as A3

STUDY = "AR003C"
TAG = A3.TAG                                                   # the same tissue, tag and code path as AR003
IDENTITIES = {"confirmation": tuple(range(920365, 920381))}    # 16 blocks (the lead's count; scanned free 17:15Z, 17:19Z)
RESERVE = tuple(range(920381, 920387))                         # held for the lead, not drawn
REFERENCE_BLOCKS = (900162,)                                   # the bridge's reference: AR003's full task (frozen code)
DEBUG_BLOCKS = (900162, 900163)                                # AR003's spare engineering blocks
SPARE = (900164, 900165, 900166, 900167)
PURPOSE = {"reference": "engineering", "debug": "engineering", "confirmation": "confirmation"}

SIZE, SIZES, SIZE_WEIGHTS = A3.SIZE, A3.SIZES, A3.SIZE_WEIGHTS
NCASE, WINDOW, READS, T_READ, TRACE, SIDE = A3.NCASE, A3.WINDOW, A3.READS, A3.T_READ, A3.TRACE, A3.SIDE
UNITS, BODIES, SITUATIONS, SCORINGS, WEIGHTS = A3.UNITS, A3.BODIES, A3.SITUATIONS, A3.SCORINGS, A3.WEIGHTS
BEST, CONTROLLER = A3.BEST, A3.CONTROLLER                      # the vote; vms
DETECTORS = {"det": A3.DETECTORS["det"]}                       # rest-default arm (frozen in AR003; no retuning)
VD_DETECTORS = {"vms": A3.VD_DETECTORS["vms"]}                 # DET_STAR with the vote default (frozen in AR003)


def R(situation, a1, det, vd, size=SIZE):
    return (situation, 0.0, tuple(a1), tuple(det), tuple(vd), size)


V, D_, M = ("vote",), ("det",), ("vms",)
RUNS = (R("none", V, D_, M), R("body", V, (), M), R("memory", V, (), M), R("correlated", V, (), M), R("shared", V, (), M),
        R("cue", V, D_, M), R("change", V, (), M),
        R("memory", V, (), M, 2), R("correlated", V, (), M, 2), R("body", V, (), M, 2), R("shared", V, (), M, 2),
        R("memory", V, D_, M, 8), R("correlated", V, D_, M, 8), R("body", V, D_, M, 8), R("shared", V, D_, M, 8))


def run_name(situation, sigma, a1=None, det=None, vd=None, size=SIZE):
    return A3.run_name(situation, sigma, size=size)


def arms_of(run):
    return A3.arms_of(run)


RUNNAMES = tuple(run_name(*x) for x in RUNS)
ARM_RUNS = sum(len(arms_of(x)) for x in RUNS)

# the development (AR003, 910548-910552 + 910554-910559 + 910587-910591, 16 blocks) and the declared rule: both 95%
# half-widths at most a third of their development values, SD = max(block SD, case SD / sqrt 8); the lead set 16 blocks
DEV = {"c1": {"value": 0.108527, "sd": 0.011201, "sd_block": 0.011201, "sd_case8": 0.009193},
       "c2": {"value": 0.149961, "sd": 0.021990, "sd_block": 0.021990, "sd_case8": 0.020597},
       "sham_cue": {"value": 0.005635, "sd": 0.002433, "sd_block": 0.002433, "sd_case8": 0.002311},
       "sham_none": {"value": -0.000035, "sd": 0.000102, "sd_block": 0.000094, "sd_case8": 0.000102}}
TARGET = {k: DEV[k]["value"] / 3 for k in ("c1", "c2")}
SD_UPPER = 1.5477                                              # the development SD estimate's upper 95% limit (15 df), a factor
N_RULE = {"c1": 3, "c2": 4}                                    # the rule's minimum at the development SD
N_UPPER = {"c1": 4, "c2": 5}                                   # at the SD's upper 95% limit
CRITERIA = {"C1": "the 95% lower bound of U_mix(vms) - U_mix(vote) is above 0",
            "C2": "the 95% lower bound of U_8(vms) - U_8(det) is above 0",
            "C3": "the 95% upper bounds of r_all(vote) - r_all(vms) at t = 8,000 are at most 0.01 under scattered cue damage "
                  "(cue@0) and at most 0.002 with no event (none@0)"}
HARM = {"cue@0": 0.01, "none@0": 0.002}
INTERVAL = "mean +- t(0.975, n - 1) x max(block SD, case SD / sqrt 8) / sqrt(n) over the n blocks"


def stage_blocks(stage, override=None):
    if stage in ("reference", "debug"):
        allowed = REFERENCE_BLOCKS if stage == "reference" else DEBUG_BLOCKS
        blocks = list(allowed) if override is None else list(override)
        if not set(blocks) <= set(allowed):
            raise ValueError(f"the {stage} stage runs on {allowed} only")
        return blocks
    if override is not None:
        raise ValueError("block overrides are for the reference and debug stages only")
    return list(IDENTITIES[stage])


def tasks():
    return A3.tasks()


def design_dict():
    return {"study": STUDY, "tag": TAG, "identities": IDENTITIES, "reserve": RESERVE, "reference_blocks": REFERENCE_BLOCKS,
            "debug_blocks": DEBUG_BLOCKS, "spare": SPARE, "purpose": PURPOSE, "ar003_digest": A3.digest(),
            "detectors": DETECTORS, "vd_detectors": VD_DETECTORS, "det_star_name": A3.DET_STAR_NAME, "runs": RUNS,
            "units": UNITS, "bodies": BODIES, "best": BEST, "controller": CONTROLLER, "sizes": SIZES,
            "size_weights": SIZE_WEIGHTS, "dev": DEV, "target": TARGET, "sd_upper": SD_UPPER, "n_rule": N_RULE,
            "n_upper": N_UPPER, "criteria": CRITERIA, "harm": HARM, "interval": INTERVAL, "weights": WEIGHTS,
            "scorings": SCORINGS, "t_read": T_READ, "reads": READS, "window": WINDOW}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    out = dict(A3.sources(lane))
    out.update({str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest()
                for f in sorted((lane / "ar003c").glob("*.py"))})
    return out


if __name__ == "__main__":      # python -m ar003c.design  ->  ar003c/frozen/design.json (phase B, on the lead's word)
    from pathlib import Path

    lane = Path(__file__).resolve().parents[1]
    out = lane / "ar003c" / "frozen" / "design.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"digest": digest(), "design": design_dict(), "sources": sources(lane)}, indent=1,
                              default=list) + "\n")
    print(out, digest()[:12])
