"""HS002's founder-identification export manifest: python -m hs002.export ROOT  ->  ROOT/EXPORT_MANIFEST.json.

HS001's schema (hs001.export; INFORMATION_AUDIT_HANDOFF.md, the Forms lane) at HS002's eight new checkpoints: the
candidate dictionary, the checkpoint packets and the recipients' full states in native dtypes, the label table, IDs
and inclusion. HS001's export files hold rewrites 1-256 of the same lineages. No decoder is fitted, no prediction made
and no estimate formed here.
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

from hs001 import design as H1, export as X1  # noqa: E402
from hs002 import design as D  # noqa: E402


def manifest(root):
    root = Path(root)
    M = json.loads((root / "manifest.json").read_text())
    blocks = list(M["blocks"])
    files = {str(b): json.loads((root / "done" / f"{b}.json").read_text())["files"] for b in blocks}
    first = np.load(root / "export" / f"{blocks[0]}.npz")
    sizes = {k: {"shape": list(first[k].shape), "native_dtype": str(first[k].dtype), "exported_dtype": str(first[k].dtype),
                 "bytes": int(first[k].nbytes), "lossy_transformation": "none"} for k in first.files if k != "__meta__"}
    keep = {k: v for k, v in X1.ARRAYS.items() if k in ("evaluator/prototypes", "evaluator/prototype_halves",
            "f<F>/packets_checkpoint", "f<F>/recipient_checkpoint", "labels/lineage_source_founder",
            "labels/formation_qualified", "ids/block", "ids/background_id", "ids/stream", "ids/founder", "ids/recipient",
            "ids/checkpoint")}
    return {"study": D.STUDY, "schema": "HS001's (hs001.export) at the new checkpoints 320-1,024",
            "provenance": {"stage": M["stage"], "run_root": str(root), "design_digest": M["design_digest"],
                           "code_and_e_series_hashes": M["sources"], "blocks": blocks, "files_sha256": files,
                           "hs001_source_root": str(D.SOURCE_ROOT[M["stage"]]),
                           "inclusion": H1.IDENTITY_EXPORT["inclusion"],
                           "missing": "none at the new checkpoints; rewrites 1-256 are in HS001's export files"},
            "boundaries": X1.BOUNDARIES, "arrays": {k: {"axes": v[0].replace("checkpoint 16", "checkpoint 8"), "meaning": v[1]}
                                                    for k, v in keep.items()},
            "array_sizes_first_block": sizes,
            "target": {"definition": H1.IDENTITY_EXPORT["target"], "candidate_count": 4, "prior": "uniform 1/4 within the block",
                       "coordinate_tolerance": H1.IDENTITY_EXPORT["coordinate_tolerance"]},
            "decoder": H1.IDENTITY_EXPORT["decoder"], "predictions": "none", "estimates": "none",
            "e014_cohort": "no identity export (" + H1.IDENTITY_EXPORT["e014_cohort"] + ")"}


def main(root):
    out = manifest(root)
    path = Path(root) / "EXPORT_MANIFEST.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    print(f"-> {path} ({hashlib.sha256(path.read_bytes()).hexdigest()[:12]})")


if __name__ == "__main__":
    main(sys.argv[1])
