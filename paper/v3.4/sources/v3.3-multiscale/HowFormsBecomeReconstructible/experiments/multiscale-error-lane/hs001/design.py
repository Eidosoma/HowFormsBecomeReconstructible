"""HS001's design: historical specificity, a reference and an asymptote (PLAN_HS001.md).

E014's machinery (E001's tissue and observer, E006's compact lifecycle) is imported read-only from the E-series tree and
never edited; its sources are pinned here by sha256. HS001 adds a generation over a declared subset of arms (line for
line E006's), the protected-foreign probe, sixteen log-spaced checkpoints to 256 rewrites, and the reader: the
reference-normalised specificity R_H(n) and the asymptote's fit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

STUDY = "HS001"
TAG = "mse-hs001"                 # bookkeeping only: the E-series engine keeps its own seeds
PROBE_TAG = "mse-p49"
LANE = Path(__file__).resolve().parents[1]
EXP = LANE.parent                 # HowFormsBecomeReconstructible/experiments
E_SOURCES = ("common.py", "E001_unprescribed_capture/model.py", "E001_unprescribed_capture/analyze.py",
             "E006_compact_renewal/run.py", "E014_long_renewal/run.py")

FACTORS = (1, 4)                  # 2,048 and 128 bytes (E014's budgets)
BYTES = {1: 2048, 4: 128}
HORIZON = 256
CHECKPOINTS = (1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256)
E014_CHECKPOINTS = (1, 3, 8, 16)
LINEAGE = ("rewrite", "foreign", "erased", "background")          # renewed for HORIZON generations
PROBES = ("copy", "copy_foreign", "copy_erased", "copy_background")  # reads of protected initial bytes
PROBE_SOURCE = {"copy": "copy", "copy_foreign": "foreign", "copy_erased": "erased", "copy_background": "background"}
LATE = (128, 192, 256)            # the model-free late mean

# The fit rule (PLAN_HS001.md, fixed before any long-horizon value)
H_GRID = (0.25, 1.0e5, 400)       # M1/M0: half-lives log-spaced, (c, a) linear, refined by a bounded scalar search
H2_GRID = (0.25, 1.0e5, 60)       # M2: a 60 x 60 grid of half-life pairs h1 < h2, (c, a1, a2) linear, then refined
IDENTIFIED_H_MAX = HORIZON / 4    # the plateau is identified only if M1's 95% upper bound of h is at most 64
BOOT = 10000                      # whole-block resamples, E014's generator rng("E014", "bootstrap")
DENOM_MIN_FRACTION = 0.5          # R_H as a ratio only if the reference's 95% lower bound >= half its estimate

IDENTITIES = {
    "smoke": [950000, 950001], "tests": [950002, 950003],
    "probe": list(range(950010, 950018)),
    "preflight": [950020, 950021], "debug": [950022, 950023], "spare": list(range(950024, 950032)),
    "development": list(range(951000, 951128)), "reserve": list(range(951128, 951192)),
    "e014": list(range(12000, 12064)),      # the bridge, the post hoc reference, and phase B's reported continuation
}
E014_BENCHMARKS = tuple(range(900014, 900030))  # E-series benchmarks: never used

# The information audit's founder-identification schema (INFORMATION_AUDIT_HANDOFF.md, the Forms lane; the lead's
# scope addition of about 14:10Z, 1 November 2026). Outputs only: no endpoint, arm or simulation changes, and no
# decoder is fitted in HS001.
IDENTITY_EXPORT = {
    "file": "ROOT/export/<block>.npz, one per block, every stage but 'e014'",
    "candidate_dictionary": "evaluator/prototypes: the block's four founders' late-formation prototypes (E001), "
                            "evaluator resources only, never an input of any reader or writer; one set for the own, "
                            "foreign and protected records",
    "target": "which of the block's four founders' acquired records a lineage or protected read started from "
              "(k = 4, uniform prior 1/4 within the block); erased and background lineages have none (-1)",
    "coordinate_tolerance": "none: the native reader, the writer and E014's observer act cell by cell at the shared "
                            "coordinates of the 16 x 16 torus; no translation, rotation, reflection or sign "
                            "tolerance; a decoder that allows any must declare it as a different task",
    "native_dtypes": "packets uint8 (the record bytes), recipients' fields float64 (v, ema, ref), prototypes float64; "
                     "no lossy conversion",
    "inclusion": "every block of the stage, all four founders (formation failures included, flagged), both recipient "
                 "lineages, every arm and checkpoint; no exclusion",
    "outcomes_kept_separate": "E014's qualified (Q), sign-only (S) and amplitude (|v| > 0.2) outcomes are in the shards, "
                              "not in the export",
    "decoder": "none fitted in HS001; identity decoding is a separate post hoc audit, frozen and reviewed on its own",
    "e014_cohort": "no identity export: its raw lineage fields are on the producing host only "
                   "(/home/robert/Random-Replications/WhereDoFormsComeFrom/experiments/E014_long_renewal/runs/"
                   "confirmation_v2/; hashes in E014's runs/confirmation_v2/COMPLETE.json, sha256 80f52dfbeb0f851d...)",
}
STAGE_TAG = {"smoke": TAG, "tests": TAG, "probe": PROBE_TAG, "preflight": TAG, "debug": TAG, "development": TAG,
             "e014": TAG}


def stage_blocks(stage):
    return list(IDENTITIES[stage])


def e_sources():
    return {f"experiments/{s}": hashlib.sha256((EXP / s).read_bytes()).hexdigest() for s in E_SOURCES}


def design_dict():
    return {"study": STUDY, "tag": TAG, "probe_tag": PROBE_TAG, "identities": IDENTITIES, "stage_tag": STAGE_TAG,
            "e014_benchmarks_avoided": list(E014_BENCHMARKS), "factors": FACTORS, "bytes": BYTES, "horizon": HORIZON,
            "checkpoints": CHECKPOINTS, "lineage": LINEAGE, "probes": PROBES, "probe_source": PROBE_SOURCE,
            "late": LATE, "h_grid": H_GRID, "h2_grid": H2_GRID, "identified_h_max": IDENTIFIED_H_MAX, "boot": BOOT,
            "denom_min_fraction": DENOM_MIN_FRACTION, "e_sources": e_sources(),
            "machinery": "E014's (E001 heterogeneous formation 1,000, capture 1,000, 16 x 16 torus; E006 initial "
                         "packets and generation, 300 read + 1,000 write; stream block + 1,000,000; checkpoint "
                         "reader on the 'terminal' stream), imported read-only",
            "observer": "E001 analyze.score: share of all 256 cells with |v| > 0.2 and the own founder's sign",
            "identity_export": IDENTITY_EXPORT}


def digest():
    return hashlib.sha256(json.dumps(design_dict(), sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def sources(lane=LANE):
    out = e_sources()
    out.update({str(f.relative_to(lane)): hashlib.sha256(f.read_bytes()).hexdigest()
                for f in sorted((lane / "hs001").glob("*.py"))})
    return out


if __name__ == "__main__":      # python -m hs001.design  ->  hs001/frozen/design.json (phase B, on the lead's word)
    import time
    out = {"study": STUDY, "digest": digest(), "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": sources(), "design": design_dict()}
    path = LANE / "hs001" / "frozen" / "design.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=list) + "\n")
    print(out["digest"])
