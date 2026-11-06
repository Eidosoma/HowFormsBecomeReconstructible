"""E2E006: collective rescue through renewal. DRAFT for the lead's review (phase A). See PLAN_E2E006.md.

Groups of newborn tissue sheets, each carrying its own independently acquired pattern (a task's eight restored cases), share
a diffusible field (SM007's msefield: a 2D reaction-diffusion medium; each sheet emits from its own stress variable and
its local field modulates one declared parameter of its dynamics), through renewal under repeated injury (E2E003's
design: a fresh disjoint 4 x 4 memory injury in every generation, each newborn's cue from its incoming record, the
outgoing records carried through actual replacement). Does collective support preserve the lineage's acquired history,
or merely help bodies return to their preferred organization?

The field's quantities (FIELD) are SM007's, as committed in msefield; until that commit they are None and the package
runs only with the field off (the bridge to E2E003).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ar001 import design as A
from ar006 import design as A6
from e2e002 import design as E2D
from e2e003 import design as E3D

STUDY = "E2E006"
TAG = "mse-e2e006"                      # the successors', the injuries' and the fresh successors' tag
PROBE_TAG = "mse-p63"                   # the pilot P63's
RUNS = E2D.RUNS

CLOCK, SIDE, GAIN, STRENGTH0, SIZE, T_GEN = E3D.CLOCK, E3D.SIDE, E3D.GAIN, E3D.STRENGTH0, E3D.SIZE, E3D.T_GEN
HORIZONS = (1, 3, 8)
G_MAIN = 8
G_DEBUG = 3
POLICIES = E3D.POLICIES                  # vote, vms, vtol (E2E003's, as frozen)
INJURY = E3D.INJURY                      # E2E003's repeated injury, its schedule drawn under E2E006's tag

# the field (SM007's msefield; the lead relays its commit). Interface: Medium(positions, D, gamma, leakage, dt);
# .step(emissions); .sample(positions). The emission (from each sheet's own stress variable) and the response (the local
# field modulating one declared parameter of each sheet's dynamics) are SM007's, declared.
# the lead's rulings (sent 12:26:39Z on 5 November, for both field studies): the field's quantities, frozen with the design
FIELD = {"module": "msefield", "commit": "fb934f1f10",          # SM007's fork F3, 12:14:45Z on 5 November (unchanged)
         "D": 0.25, "gamma": 0.0625, "leakage": 1.0, "dt": 1.0, "m": 4, "margin": 0,   # lambda = sqrt(D / gamma) = 2 sheets
         "positions": [(r, c) for r in range(2) for c in range(4)],                   # msefield.rectangle(2, 4)
         "isolated_positions": [(0, 2 * j) for j in range(8)],   # one Medium, 8 disconnected blocks (each its own boundary)
         "stress": "a sheet's mean |r - V-tilde| over its cells (the record's pull on its body): its own state only",
         "emission": "equal to the stress",
         "response": "the body's reading gain x (1 + kappa x exposure), inside the row's window",
         # fixed by P63k (engineering only, nothing scored; 12:40:47-12:44:11Z on 5 November, probes/results/
         # p63k_e2e006_kappa.json) before any outcome value: the shared reference's mean exposure 0.51451 (early
         # 0.51354, late 0.51548); the isolated reference's 0.12693 (0.247 of the shared)
         "kappa": 1.944, "kappa_early": 1.947, "kappa_late": 1.94,
         "kappa_isolated": 7.878,      # the optional matched isolated row's: the same rule on the isolated reference
         "kappa_rule": "kappa x the shared group's mean exposure in the reference configuration (shared, full window, "
                       "kappa 0: the field computed, no response; the debug record's 8 tasks, generations 1-8, tag "
                       "mse-p63k) = 1, the exposure x(t) being what the response reads at update t; kappa_early, "
                       "kappa_late: the same with the mean over updates 1-4,000 and 4,001-8,000, so the two windows "
                       "carry equal integrated kappa x exposure (4,000 a generation in the reference); kappa_isolated: "
                       "the same rule on the isolated reference; each rounded to four significant figures"}
GROUP = ("shared: the task's eight cases, one sheet each, at FIELD['positions'] (rectangle(2, 4)) in one Medium; "
         "isolated: the same eight sheets in one Medium at FIELD['isolated_positions'], non-adjacent cells, so eight "
         "disconnected blocks, each with its own absorbing boundary and no diffusion between them")

# how a lineage meets the field
#   field   "none": no medium (E2E003's lineage exactly); "isolated": each sheet alone in its own medium, at its own group
#           position, with the same emission and response; "shared": the task's eight sheets of the row in one medium
#   medium  "reset": a fresh medium at every replacement; "retain": the medium carried across replacement (a second
#           heritable channel, labelled so)
#   window  the updates of each generation in which the response acts: "full" (1-8,000), "early" (1-4,000), "late"
#           (4,001-8,000); emission and diffusion run in every update
WINDOWS = {"full": (1, T_GEN), "early": (1, T_GEN // 2), "late": (T_GEN // 2 + 1, T_GEN)}
L = lambda *x: dict(zip(("label", "packet", "policy", "sigma", "stop", "injured", "field", "medium", "window"), x))
# a row's kappa is its window's (FIELD's kappa, kappa_early, kappa_late) unless it names another ("kappa_key")
# protected copying (the lead's ruling 4): the packet each generation passes on is its incoming packet, copied before that
# generation's injury; the injury hits only the working record, on which the body develops and is scored
PROTECTED_COPY = ("protected",)
# the rows as built in phase A (P63 ran its five field rows; the debug run all eleven). Kept as run: the stages that ran
# them are re-read and re-checked under these definitions
ROWS_A = (L("vote/none", "vote/memory@0", "vote", 0.0, G_MAIN, True, "none", "-", "-"),
          L("vote/isolated", "vote/memory@0", "vote", 0.0, G_MAIN, True, "isolated", "reset", "full"),
          L("vote/shared", "vote/memory@0", "vote", 0.0, G_MAIN, True, "shared", "reset", "full"),
          L("vote/shared-retained", "vote/memory@0", "vote", 0.0, G_MAIN, True, "shared", "retain", "full"),
          L("vote/shared-early", "vote/memory@0", "vote", 0.0, G_MAIN, True, "shared", "reset", "early"),
          L("vote/shared-late", "vote/memory@0", "vote", 0.0, G_MAIN, True, "shared", "reset", "late"),
          L("protected", "protected", "vote", 0.0, G_MAIN, True, "none", "-", "-"),
          L("vtol-every", "vtol/memory@0", "vtol", 0.0, G_MAIN, True, "none", "-", "-"),
          L("uninjured", "vote/none@0", "vote", 0.0, G_MAIN, False, "none", "-", "-"),          # E2E003's ceiling
          L("vtol-every/shared", "vtol/memory@0", "vtol", 0.0, G_MAIN, True, "shared", "reset", "full"),
          # proposed after P63k: an isolated row at the shared row's mean response (kappa_isolated), so shared against it
          # differs in the neighbours' signal only, not in the response's size (the main control, Amendment 2)
          dict(L("vote/isolated-matched", "vote/memory@0", "vote", 0.0, G_MAIN, True, "isolated", "reset", "full"),
               kappa_key="isolated"))
ALL = ROWS_A
_A = {x["label"]: x for x in ROWS_A}
P63_ROWS = tuple(_A[x] for x in ("vote/isolated", "vote/shared", "vote/shared-retained", "vote/shared-early",
                                 "vote/shared-late"))            # P63 as run: the five field rows
# Amendment 2 (the lead's rulings of 13:46:59Z): P63x, the matched row and the field-free baseline on P63's two blocks,
# under P63's tag (so paired with P63's rows: the same births, injuries and noise), fresh states saved
P63X_ROWS = (_A["vote/isolated-matched"], _A["vote/none"])
# phase B's rows (Amendment 2): no retained, uninjured or vtol/shared rows; early and late to g 3
G_EARLY_LATE = 3
CORE = tuple(dict(_A[x], stop=G_EARLY_LATE) if x in ("vote/shared-early", "vote/shared-late") else _A[x]
             for x in ("vote/none", "vote/isolated", "vote/shared", "vote/isolated-matched", "vote/shared-early",
                       "vote/shared-late", "protected", "vtol-every"))
OPTIONAL = {}

# the fresh-successor test: after generation g in FRESH_AT, a field-free newborn reads the outgoing record for one
# generation (the vote, no injury, no medium) and is scored; nothing of it enters the lineage
FRESH_AT = HORIZONS
FRESH = {"policy": "vote", "injured": False, "field": "none", "names": ("e2e006", "fresh")}
STAGE_FRESH_AT = {"preflight": (G_MAIN,), "development": (G_MAIN,)}   # Amendment 2: phase B tests after g 8 only
# Amendment 2 (the lead's item 8): the fresh successors' final V, r, H and W are saved in raw/ (f0/x{g}/V, ... and
# f0/x{g}/rows), output only; the stages run before it (probe, kappa, debug) are kept as run, without them
SAVE_FRESH_STAGES = ("probe_x", "preflight", "development")

# the restored sources (AR006's raw final states: E2E003's cohort) and the stages
SOURCES = E3D.SOURCES
AR006_DEV = E3D.AR006_DEV
STAGES = E3D.STAGES
KAPPA_TAG = "mse-p63k"                  # P63k's: the engineering run that fixes kappa (its noise used nowhere else)
STAGE_TAG = {"probe": PROBE_TAG, "probe_x": PROBE_TAG, "kappa": KAPPA_TAG, "debug": TAG, "preflight": TAG,
             "development": TAG}
# P63k, the reference configuration (engineering only, nothing scored): the shared row with the response off (kappa 0:
# the field computed, no response; the tissue is then the field-free one, P63m), on the debug record's eight tasks,
# generations 1-8; the isolated row beside it for the exposure ratio (reported, not used for kappa)
KAPPA_ROWS = tuple(dict(x, label=x["label"] + "@k0") for x in ROWS_A if x["label"] in ("vote/shared", "vote/isolated"))
STAGE_LINEAGES = {"probe": P63_ROWS, "probe_x": P63X_ROWS, "kappa": KAPPA_ROWS, "debug": ROWS_A, "preflight": CORE,
                  "development": CORE}
FUTURES = {"probe": 1, "probe_x": 1, "kappa": 1, "debug": 1, "preflight": 1, "development": 1}
STAGE_KAPPA = {"kappa": 0.0}             # the reference configuration's kappa (every other stage: FIELD's)
STAGE_SCORED = {"kappa": False}          # P63k computes no read
STAGE_PARENTS = {}                       # every stage reads all eight cases: a group is the task's eight sheets
STAGE_STOP_CAP = {"debug": G_DEBUG}
PROBE_BLOCKS = (A6.PROBE_BLOCKS[0], A6.PROBE_BLOCKS[2])           # two of P57's four blocks (phase A's cap): 900917, 900919
STAGES = dict(STAGES, probe={"ar006/p57": PROBE_BLOCKS}, probe_x={"ar006/p57": PROBE_BLOCKS}, kappa=dict(STAGES["debug"]),
              preflight={"ar006/preflight": (E3D.STAGES["preflight"]["ar006/preflight"][0],)})   # Amendment 2: 900929
HALVES = {"probe": ((PROBE_BLOCKS[0],), (PROBE_BLOCKS[1],)), "probe_x": ((PROBE_BLOCKS[0],), (PROBE_BLOCKS[1],)),
          "development": (AR006_DEV[:8], AR006_DEV[8:])}
BODIES, UNITS = A.BODIES, A.UNITS
ITEM_SETS = E2D.ITEM_SETS                # native (li4 S4), particular (li4 F0: read first), permissive (dw)
K_RULE, STEP, STEP_NEAR0, AT_MOST_MAX, C_Q = E2D.K_RULE, E2D.STEP, E2D.STEP_NEAR0, E2D.AT_MOST_MAX, E2D.C_Q


def lineages(stage):
    return STAGE_LINEAGES[stage]


def stage_tasks(stage):
    return [(src, b, u, blk) for src, blocks in STAGES[stage].items() for blk in blocks for b in BODIES for u in UNITS]


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "clock": CLOCK, "t_gen": T_GEN, "horizons": HORIZONS,
            "g_main": G_MAIN, "g_debug": G_DEBUG, "policies": POLICIES, "injury": INJURY, "field": FIELD, "group": GROUP,
            "windows": WINDOWS, "core": CORE, "optional": OPTIONAL, "protected_copy": PROTECTED_COPY,
            "rows_a": ROWS_A, "p63_rows": [x["label"] for x in P63_ROWS], "p63x_rows": [x["label"] for x in P63X_ROWS],
            "g_early_late": G_EARLY_LATE, "fresh_at": FRESH_AT, "fresh": FRESH, "stage_fresh_at": STAGE_FRESH_AT,
            "save_fresh_stages": SAVE_FRESH_STAGES,
            "sources": SOURCES, "stages": STAGES, "stage_tag": STAGE_TAG,
            "stage_lineages": {k: [x["label"] for x in v] for k, v in STAGE_LINEAGES.items()}, "futures": FUTURES,
            "stage_parents": STAGE_PARENTS, "stage_stop_cap": STAGE_STOP_CAP, "stage_kappa": STAGE_KAPPA,
            "stage_scored": STAGE_SCORED, "kappa_tag": KAPPA_TAG, "halves": HALVES, "bodies": BODIES,
            "units": UNITS, "item_sets": ITEM_SETS, "k_rule": K_RULE, "step": STEP, "step_near0": STEP_NEAR0,
            "at_most_max": AT_MOST_MAX, "c_q": C_Q, "size": SIZE, "side": SIDE, "ar001_digest": A.digest(),
            "ar006_digest": A6.digest(), "e2e002_digest": E2D.digest(), "e2e003_digest": E3D.digest()}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane):
    lane = Path(lane)
    dirs = ("mse", "msegrid", "dl001", "dl002", "lr001", "lr002", "lr003", "lr004", "lr005", "be001", "be002", "be005",
            "be006", "gc001", "np001", "ar001", "ar002", "ar003", "ar004", "ar005", "ar006", "sr001", "e2e001", "e2e002",
            "e2e003", "msefield", "e2e006")
    files = sorted(f for d in dirs for f in (lane / d).glob("*.py"))
    return {str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}


if __name__ == "__main__":      # python -m e2e006.design  ->  e2e006/frozen/design.json (phase B, on the lead's word)
    import time
    lane = Path(__file__).resolve().parents[1]
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(lane), "design": design_dict()}
    path = lane / "e2e006" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
