"""AR006C: AR006's confirmation, on fresh confirmation blocks 920387-920410.

AR006 (frozen 14:27:04Z on 3 November 2026, digest 963f47e2cf71) found in development that vtol (DET_STAR's windows
unguarded, united with DET_POOL's further windows confirmed by g-body-f05; the vote as the default) keeps the confirmed
controller vms's repair of correlated damage and most of the pooled detector's misread recovery: its six registered
statements held (results commit 5564de9beb). AR006C tests, on blocks no study has drawn, the criteria AR006's plan and
registration declared for it (PLAN_AR006.md, "A confirmation, AR006C, is declared now"), with the lead's rulings of
4 November 2026 (about 09:54Z, on the PI's "lets go on both"): K1, the harm bound under scattered cue damage, with the
no-event part as AR003C's C3; K3 (a), the misread recovery over vms; K5 (a), vtol against vms in correlated damage at
sigma 0. The lead set 24 blocks with a reserve of 6, not drawn (for K1's power).

The draws: AR006's tissue, tag (mse-ar006) and code path, through ar006.worker.task (ar003.worker's one and task from
their own source, the vote-default call routed to ar006.sim.run_vt) imported unchanged, on the eight unit-body pairs,
pooled as AR006 (per case the mean over the pairs, a block's value the mean over its eight cases, a criterion's value the
mean over the blocks). vms and vtol are AR006's frozen detectors, the vote (BEST) the default; no retuning. The purpose:
mse.assay.RANGES assigns 920000-929999 to 'confirmation'; it is a range check in enrol only, and Case.key() is (block,
message, parent), so the purpose enters no stream's address.

The arms: the vote, vms and vtol, in only the runs the criteria need, with vms beside K1 (12 arm-runs a task, against
AR006's development task's 32):
  4 x 4  none@0 and cue@0: vote, vms, vtol    K1 (vms's cost reported beside it)
  4 x 4  memory@1: vms, vtol                   K3 (a)
  8 x 8  memory@1: vms, vtol                   K3 (a)
  4 x 4  correlated@0: vms, vtol               K5 (a)
vpool and vguard are left out, and with them K3 (b) and K5 (b)-(d); memory@0, none@1 and correlated@1 are not run. The
bridge (Q3): every reduced branch equals AR006's full development task's corresponding branch bit for bit on the
engineering blocks where AR006 ran that task under its frozen digest: its debug block 900948 and its preflight block
900929 (AR006's own outputs there are the reference; no reference stage is needed).

The intervals (every criterion and reported contrast): over the n blocks, mean +- t(0.975, n - 1) x SD / sqrt(n), with
SD = max(the SD of the n block values, the SD of the n x 8 per-case values / sqrt 8) (ar006.analyze.ci, unchanged);
n = 24 here, t(0.975, 23).
"""
from __future__ import annotations

import hashlib
import json

from ar006 import design as A6

STUDY = "AR006C"
TAG = A6.TAG                                                   # the same tissue, tag and code path as AR006
CONFIRMATION_BLOCKS = tuple(range(920387, 920411))             # 24 blocks (the lead's count; fork A3's scan, 4 Nov ~10:06Z)
RESERVE = tuple(range(920411, 920417))                         # 6, held for the lead, not drawn
HALVES = (CONFIRMATION_BLOCKS[:12], CONFIRMATION_BLOCKS[12:])  # reported: the first and the last twelve
IDENTITIES = {"confirmation": CONFIRMATION_BLOCKS}
DEBUG_BLOCKS = (900948, 900929)                                # AR006's debug block and first preflight block (the bridge)
REFERENCE_ROOTS = {900948: "ar006/debug", 900929: "ar006/preflight"}   # AR006's full task there, under its frozen digest
PREFLIGHT_BLOCKS = (900969, 900989)                            # AR006's spare engineering blocks, never drawn
TEST_BLOCK = 900948                                            # the tests' short bridge (one run of one pair)
PURPOSE = {"debug": "engineering", "preflight": "engineering", "confirmation": "confirmation"}
TAKEN = {"ar001c_ar002c": (920000, 920147), "ar003c": (920365, 920380), "ar003c_reserve": (920381, 920386)}

SIZE, NCASE, WINDOW, READS, T_READ, TRACE, SIDE = A6.SIZE, A6.NCASE, A6.WINDOW, A6.READS, A6.T_READ, A6.TRACE, A6.SIDE
UNITS, BODIES, CLOCK, SIG = A6.UNITS, A6.BODIES, A6.CLOCK, A6.SIG
S1 = A6.MISREAD_SIGMA
BEST, CONTROLLER = A6.BEST, A6.CONTROLLER                      # the vote; vtol
VD_DETECTORS = {a: A6.VD_DETECTORS[a] for a in ("vms", "vtol")}  # AR006's frozen ones (a lookup by arm in run_vt)
STATEMENT_SIZES = A6.STATEMENT_SIZES                           # 4 and 8

V, M = ("vote",), ("vms", "vtol")
RUNS = (A6.R("memory", S1, (), M, 4), A6.R("memory", S1, (), M, 8), A6.R("none", 0.0, V, M), A6.R("cue", 0.0, V, M),
        A6.R("correlated", 0.0, (), M))                       # AR006's order; 12 arm-runs a task


def run_name(situation, sigma, a1=None, det=None, vd=None, size=SIZE):
    return A6.run_name(situation, sigma, size=size)


def arms_of(run):
    return A6.arms_of(run)


RUNNAMES = tuple(run_name(*x) for x in RUNS)
ARM_RUNS = sum(len(arms_of(x)) for x in RUNS)

# the development (AR006, 16 blocks 925614-925634; P57e from its shards with ar006.analyze, 6 decimals)
DEV = {"k1_cue": {"value": 0.00773, "sd": 0.002883, "sd_block": 0.002883, "sd_case8": 0.002764},
       "k1_none": {"value": -2.6e-05, "sd": 6.6e-05, "sd_block": 6.5e-05, "sd_case8": 6.6e-05},
       "k3a": {"value": 0.092422, "sd": 0.040717, "sd_block": 0.037036, "sd_case8": 0.040717},
       "k5a": {"value": 0.000366, "sd": 0.001465, "sd_block": 0.001465, "sd_case8": 0.001465},
       "vtol_less_vms_cue": {"value": 0.001022, "sd": 0.000965, "sd_block": 0.000965, "sd_case8": 0.000888}}
DEV_BLOCKS = 16
SD_UPPER = 1.5477                                              # the development SD's upper 95% limit (15 df), a factor
THRESHOLDS = {"k1_cue": ("le", 0.01), "k1_none": ("le", 0.002), "k3a": ("ge", 0.04), "k5a": ("ge", -0.005)}
CRITERIA = {"K1": "the 95% upper bounds of r_all(vote) - r_all(vtol) at t = 8,000 are at most 0.01 under scattered cue "
                  "damage (cue@0) and at most 0.002 with no event (none@0)",
            "K3a": "the 95% lower bound of R1 = (1/2) sum over sizes 4, 8 of u(vtol, memory@1) - u(vms, memory@1) is at "
                   "least 0.04",
            "K5a": "the 95% lower bound of u(vtol) - u(vms) in correlated damage at sigma 0, 4 x 4, is at least -0.005"}
PARTS = {"K1": ("k1_cue", "k1_none"), "K3a": ("k3a",), "K5a": ("k5a",)}
INTERVAL = "mean +- t(0.975, n - 1) x max(block SD, case SD / sqrt 8) / sqrt(n) over the n blocks"


def stage_blocks(stage, override=None):
    if stage == "debug":
        blocks = list(DEBUG_BLOCKS) if override is None else list(override)
        if not set(blocks) <= set(DEBUG_BLOCKS):
            raise ValueError(f"the debug stage runs on {DEBUG_BLOCKS} only")
        return blocks
    if override is not None:
        raise ValueError("block overrides are for the debug stage only")
    return list(PREFLIGHT_BLOCKS if stage == "preflight" else IDENTITIES[stage])


def tasks():
    return A6.tasks()


def design_dict():
    return {"study": STUDY, "tag": TAG, "identities": IDENTITIES, "reserve": RESERVE, "halves": HALVES,
            "debug_blocks": DEBUG_BLOCKS, "reference_roots": REFERENCE_ROOTS, "preflight_blocks": PREFLIGHT_BLOCKS,
            "test_block": TEST_BLOCK, "purpose": PURPOSE, "taken": TAKEN, "ar006_digest": A6.digest(),
            "vd_detectors": VD_DETECTORS, "runs": RUNS, "units": UNITS, "bodies": BODIES, "best": BEST,
            "controller": CONTROLLER, "statement_sizes": STATEMENT_SIZES, "misread_sigma": S1, "dev": DEV,
            "dev_blocks": DEV_BLOCKS, "sd_upper": SD_UPPER, "thresholds": THRESHOLDS, "criteria": CRITERIA,
            "parts": PARTS, "interval": INTERVAL, "t_read": T_READ, "reads": READS, "window": WINDOW, "clock": CLOCK,
            "sig": SIG}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    out = dict(A6.sources(lane))
    out.update({str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest()
                for f in sorted((lane / "ar006c").glob("*.py"))})
    return out


if __name__ == "__main__":      # python -m ar006c.design  ->  ar006c/frozen/design.json (phase B, on the lead's word)
    from pathlib import Path

    lane = Path(__file__).resolve().parents[1]
    out = lane / "ar006c" / "frozen" / "design.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"digest": digest(), "design": design_dict(), "sources": sources(lane)}, indent=1,
                              default=list) + "\n")
    print(out, digest()[:12])
