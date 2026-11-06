"""HS001's founder-identification export: python -m hs001.export ROOT  ->  ROOT/EXPORT_MANIFEST.json.

The information audit's schema (INFORMATION_AUDIT_HANDOFF.md, "Instructions for the Forms lane", folded into HS001 on
the lead's word of about 14:10Z, 1 November 2026). It documents ROOT/export/<block>.npz, written by hs001.worker for
HS001's own cohort, in the handoff's manifest format: provenance, boundaries, arrays (name, shape, native dtype,
exported dtype, bytes, lossy transformation: none), the target and its candidate dictionary, the label table, the
coordinate tolerance, and the inclusion decisions. No decoder is fitted, no prediction made and no estimate formed
here: identity decoding is a separate post hoc audit, frozen and reviewed on its own.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))
sys.dont_write_bytecode = True

from hs001 import design as D  # noqa: E402

ARRAYS = {
    "evaluator/prototypes": ("(founder 4, row 16, col 16)", "the candidate dictionary: each founder's mean field over the "
                             "last 100 of its 1,000 formation steps (E001); an evaluator resource, never a reader or writer input"),
    "evaluator/prototype_halves": ("(half 2, founder 4, row 16, col 16)", "the same over each half of those 100 steps (E001's stability check)"),
    "f<F>/packets_initial_lineage": ("(founder 4, recipient 2, arm 4, byte B)", "the lineage arms' incoming records at "
                                     "acquisition (E006's initial packets; arms rewrite, foreign, erased, background)"),
    "f<F>/packets_initial_protected": ("(founder 4, recipient 2, probe 4, byte B)", "the protected records' exact bytes "
                                       "(copy, copy_foreign, copy_erased, copy_background), constant at every boundary"),
    "f<F>/packets_checkpoint": ("(checkpoint 16, founder 4, recipient 2, arm 4, byte B)", "each lineage's outgoing record "
                                "after n rewrites (the bytes a fresh checkpoint reader receives)"),
    "f<F>/recipient_checkpoint": ("(checkpoint 16, founder 4, recipient 2, arm 4, component 3, row 16, col 16)",
                                  "the fresh checkpoint reader's state after its 300 reading steps (terminal stream; "
                                  "components v, ema, ref); v is what E014's observer scores"),
    "f<F>/recipient_protected": ("(founder 4, recipient 2, probe 4, component 3, row 16, col 16)",
                                 "the same reader on the protected records (constant across horizons)"),
    "labels/lineage_source_founder": ("(founder 4, arm 4) int8", "the founder whose acquired record the lineage started "
                                      "from: own f, foreign (f + 1) mod 4, -1 for erased and background"),
    "labels/protected_source_founder": ("(founder 4, probe 4) int8", "the same for the protected records"),
    "labels/formation_qualified": ("(founder 4) bool", "E014's formation qualification per founder (all founders kept)"),
    "ids/block": ("() int64", "the independent source block"),
    "ids/background_id": ("() int64", "the shared formation background's ID (E001 draws it per block: the block number)"),
    "ids/stream": ("() int64", "the recipient stream, block + 1,000,000 (E006)"),
    "ids/founder": ("(4) int64", "founder indices within the block (positions only: no meaning across blocks)"),
    "ids/recipient": ("(2) int64", "the two recipient lineages per founder"),
    "ids/checkpoint": ("(16) int64", "completed rewrites at each checkpoint"),
}
BOUNDARIES = {
    "incoming": "packets_initial_*: the record bytes at acquisition (E001's generic capture, E006's codec at the budget)",
    "maintenance": "each generation reads the incoming record into a fresh body (300 steps, read_off off), erases, "
                   "and writes a new record (1,000 steps); only record bytes cross (E014); not exported per generation",
    "outgoing": "packets_checkpoint: the record after n rewrites",
    "recipient": "recipient_*: a fresh body that read the outgoing (or protected) record on the shared terminal stream; "
                 "it never feeds back into the lineage",
    "outside": "the prototypes, the labels and the founder order stay outside every native reader and writer; public "
               "coordinates, the dynamics and the codecs are shared apparatus outside the byte budget (E014)",
}


def manifest(root):
    root = Path(root)
    M = json.loads((root / "manifest.json").read_text())
    blocks = list(M["blocks"])
    files, shapes = {}, {}
    for b in blocks:
        rec = json.loads((root / "done" / f"{b}.json").read_text())
        files[str(b)] = rec["files"]
    first = np.load(root / "export" / f"{blocks[0]}.npz")
    for k in first.files:
        if k != "__meta__":
            shapes[k] = {"shape": list(first[k].shape), "native_dtype": str(first[k].dtype), "exported_dtype": str(first[k].dtype),
                         "bytes": int(first[k].nbytes), "lossy_transformation": "none"}
    status = {"smoke": "development (interface check)", "tests": "development (interface check)",
              "probe": "development: probe P49 (engineering blocks; exposed in phase A)",
              "preflight": "qualification (engineering blocks)", "debug": "development (interface check)",
              "development": "HS001's development cohort (post hoc for any identity analysis once HS001's results are read)"}
    out = {"study": D.STUDY, "schema": "INFORMATION_AUDIT_HANDOFF.md, Instructions for the Forms lane",
           "provenance": {"stage": M["stage"], "status": status.get(M["stage"], M["stage"]), "run_root": str(root),
                          "design_digest": M["design_digest"], "code_and_e_series_hashes": M["sources"],
                          "blocks": blocks, "files_sha256": files, "inclusion": D.IDENTITY_EXPORT["inclusion"],
                          "missing": "none: every exported array is written for every block; the per-generation "
                                     "maintenance states are not exported (they never cross a boundary)"},
           "boundaries": BOUNDARIES,
           "arrays": {k: {"axes": v[0], "meaning": v[1]} | ({"per_budget": "F in (1, 4): 2,048 or 128 bytes"} if "<F>" in k else {})
                      for k, v in ARRAYS.items()},
           "array_sizes_first_block": shapes,
           "target": {"definition": D.IDENTITY_EXPORT["target"], "candidate_count": 4, "prior": "uniform 1/4 within the block",
                      "candidate_dictionary": "evaluator/prototypes (the same set for own, foreign and protected records)",
                      "nuisance": "the block's shared background (ids/background_id); the budget; the horizon",
                      "coordinate_tolerance": D.IDENTITY_EXPORT["coordinate_tolerance"],
                      "distinct_tasks": "four-founder matching is the declared task; family, phase and fine-detail "
                                        "recovery are not interchangeable with it and are not declared here"},
           "decoder": D.IDENTITY_EXPORT["decoder"], "predictions": "none", "estimates": "none",
           "outcomes_kept_separate": D.IDENTITY_EXPORT["outcomes_kept_separate"],
           "e014_cohort": D.IDENTITY_EXPORT["e014_cohort"]}
    return out


def main(root):
    out = manifest(root)
    path = Path(root) / "EXPORT_MANIFEST.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    print(f"-> {path} ({hashlib.sha256(path.read_bytes()).hexdigest()[:12]})")


if __name__ == "__main__":
    main(sys.argv[1])
