"""Bounded reproduction of E123's stopped development fit; no test scoring."""
from __future__ import annotations
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import sys
import time
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from E123_history_identity_audit import decoder_design as design
from E123_history_identity_audit import decoder_models as models
from E123_history_identity_audit.decoder_pipeline import checked_dataset
from E123_history_identity_audit.export import sha, dump


def main():
    allowed = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {5 if 5 in allowed else allowed[-1]})
    output = HERE / "analysis" / "optimizer_amendment_v2"
    output.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    run = HERE / "runs" / "retained_v1"
    dataset = run / "dataset"
    manifest = checked_dataset(dataset)
    preserved = {str(p.relative_to(ROOT)): sha(p)
                 for parent in (run, HERE / "jobs" / "retained_v1")
                 for p in sorted(parent.rglob("*")) if p.is_file()}
    dump(output / "PRESERVED_V1.json", preserved)
    assert not (run / "predictions" / "PREDICTIONS_SEALED.json").exists()
    assert not (run / "predictions" / "SCORES.json").exists()
    with gzip.open(dataset / "metadata_factor_1.json.gz", "rt") as f:
        rows = json.load(f)["checkpoint"]
    groups = np.array([r["source_block_id"] for r in rows])
    eligible = np.array([r["horizon"] in design.TRAIN_HORIZONS and
                         r["condition"] in ("own", "foreign") for r in rows])
    outer = design.fold_map(manifest["source_blocks"])
    development = eligible & np.array([outer[int(g)] != 0 for g in groups])
    held_out = sorted(g for g in outer if outer[g] == 0)
    with np.load(dataset / "features_factor_1.npz", allow_pickle=False) as z:
        x = z["checkpoint__body__features"][development]
    # Only development labels enter the reproduction or amended fit.
    y = np.array([r["true_label"] for r, keep in zip(rows, development) if keep])
    groups = groups[development]
    inner = design.fold_map(set(groups), 0)
    failures = []
    fits = []
    for fold in range(4):
        training = np.array([inner[int(g)] != fold for g in groups])
        train_groups = sorted(set(groups[training].tolist()))
        assert len(train_groups) == 42 and not set(train_groups) & set(held_out)
        receipts = {}
        for cap in (300, 2000):
            try:
                model, receipt = models.fit_ridge(x[training], y[training], .001, maxiter=cap)
            except models.FitFailure as exc:
                assert cap == 300, "Amended cap failed; preserve failure, do not retry"
                receipt = json.loads(str(exc))
                assert receipt["iterations"] == 300 and not receipt["success"]
                failures.append(fold)
                receipt["accepted"] = False
            else:
                receipt.update(accepted=True, model_sha256=models.canonical_hash(model))
            receipts[str(cap)] = receipt
        assert receipts["2000"]["success"]
        assert receipts["2000"]["gradient_inf"] <= design.GRADIENT_LIMIT
        assert receipts["2000"]["objective"] <= receipts["300"]["objective"] + 1e-12
        fits.append(dict(inner_fold=fold, training_groups=train_groups, receipts=receipts))
    assert failures, "Expected original cap exhaustion was not reproduced"
    failure = json.loads((run / "FAILED.json").read_text())
    expected = json.loads(failure["error"].split("FitFailure: ", 1)[1])
    first = fits[failures[0]]["receipts"]["300"]
    assert abs(first["objective"] - expected["objective"]) < 1e-12
    assert abs(first["gradient_inf"] - expected["gradient_inf"]) < 1e-12
    for rel, digest in preserved.items():
        assert sha(ROOT / rel) == digest, rel
    result = dict(status="PASS", utc=datetime.now(timezone.utc).isoformat(),
                  seconds=time.perf_counter()-start, evidence="NUMERICAL_DEVELOPMENT_CHECK",
                  factor=1, view="body", outer_fold=0, ridge=.001, fixed_caps=[300,2000],
                  outer_held_out_groups=held_out, reproduced_failed_inner_folds=failures,
                  fits=fits, outer_predictions_or_scores_computed=False,
                  original_files_preserved=len(preserved),
                  amendment_sha256=sha(HERE / "DECODER_AMENDMENT_V2.md"),
                  script_sha256=sha(Path(__file__)),
                  source_dataset_sha256=sha(dataset / "COMPLETE.json"))
    dump(output / "RESULT.json", result)
    print(json.dumps({k:result[k] for k in ("status","seconds","reproduced_failed_inner_folds",
                                          "outer_predictions_or_scores_computed","original_files_preserved")}))


if __name__ == "__main__":
    main()
