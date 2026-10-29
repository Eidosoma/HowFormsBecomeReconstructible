#!/usr/bin/env python3
"""One explicitly post hoc E054 interaction from retained block summaries.

This performs new statistical reaggregation, not new simulations or a native
array audit. It imports no experiment modules, fits no model and retains the
original qualification. The four cells are paired before whole-block resampling.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = "experiments/E054_record_interventions/"
RUN = BASE + "runs/interventions_v1/"
ARCHIVE = ROOT / "paper_assets/data/e054-history-interaction-v0.20-source-records.zip"
SOURCES = ROOT / "reviews/V0.20_E054_SOURCES.json"
SPEC = ROOT / "reviews/V0.20_E054_ANALYSIS_SPEC.json"
OUTPUT = ROOT / "paper_assets/data/e054-history-interaction-v0.20.json"
TABLE = ROOT / "paper_assets/data/e054-history-interaction-v0.20.csv"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text(value):
    return json.dumps(value, indent=2, allow_nan=False) + "\n"


def analyze():
    sources = json.loads(SOURCES.read_text())
    specification = json.loads(SPEC.read_text())
    assert specification["status"] == "POST_HOC_NOT_PREREGISTERED"
    assert sha(ARCHIVE) == sources["archive_sha256"]
    with zipfile.ZipFile(ARCHIVE) as z:
        for source in sources["sources"]:
            assert hashlib.sha256(z.read(source["member"])).hexdigest() == source["sha256"]
        read = lambda name: json.loads(z.read(name))
        summary = read(RUN + "summary.json")
        manifest = read(RUN + "manifest.json")
        complete = read(RUN + "COMPLETE.json")
        audit = read(RUN + "INDEPENDENT_AUDIT.json")
        assert summary["status"] == "MECHANISTIC_FOLLOWUP" and summary["controls_pass"]
        assert summary["cohort_reused"] and summary["independent_blocks"] == 32
        assert audit["status"] == "PASS"
        assert hashlib.sha256(z.read(RUN + "COMPLETE.json")).hexdigest() == audit["complete_sha256"]
        for name in ("summary.json", "manifest.json"):
            assert hashlib.sha256(z.read(RUN + name)).hexdigest() == complete["outputs_sha256"][name]
        for name in ("common.py", "E054_record_interventions/inference.py", "E054_record_interventions/run.py", "E054_record_interventions/plan.py"):
            assert hashlib.sha256(z.read(BASE + "frozen_inputs/" + name)).hexdigest() == manifest["inputs_sha256"][name]
        assert hashlib.sha256(z.read(BASE + "model.py")).hexdigest() == manifest["inputs_sha256"]["E054_record_interventions/model.py"]

    blocks = manifest["contract"]["blocks"]
    assert blocks == list(range(34000, 34032))
    # Reproduce the original E054 bootstrap stream without importing common.py.
    key = json.dumps(["E054", "bootstrap", "record_interventions"], separators=(",", ":")).encode()
    seed = int.from_bytes(hashlib.sha256(key).digest()[:16], "little")
    draws = np.random.Generator(np.random.PCG64(seed)).integers(0, 32, (10000, 32))
    stats = summary["statistics"]

    def retained(name):
        row = stats[name]
        values = np.asarray(row["block_means"], dtype=np.float64)
        assert values.shape == (32,) and np.isfinite(values).all()
        assert float(values.mean()) == row["mean"]
        tails = [1/120, 1 - 1/120] if name.startswith("primary/") else [.025, .975]
        interval = np.quantile(values[draws].mean(axis=1), tails)
        assert np.array_equal(interval, row["interval"]), name
        return values

    keys = {
        "matched_untreated": "both/paired_rewrite/untouched/scattered",
        "matched_permuted": "both/paired_rewrite/magnitude_permute/scattered",
        "independent_untreated": "both/independent_rewrite/untouched/scattered",
        "independent_permuted": "both/independent_rewrite/magnitude_permute/scattered",
    }
    cells = {name: retained(key) for name, key in keys.items()}
    for values in cells.values():
        assert np.array_equal(values * 16, np.rint(values * 16))
    matched_loss = cells["matched_untreated"] - cells["matched_permuted"]
    independent_loss = cells["independent_untreated"] - cells["independent_permuted"]
    assert np.array_equal(-matched_loss, retained("primary/magnitude_permute"))
    assert np.array_equal(-independent_loss, retained("effect/both/independent_rewrite/magnitude_permute/scattered"))
    interaction = matched_loss - independent_loss
    bootstrap = interaction[draws].mean(axis=1)

    # Independently aggregate integer counts using resample multiplicities.
    count_difference = np.rint(interaction * 16).astype(np.int64)
    frequency = np.vstack([np.bincount(row, minlength=32) for row in draws])
    independent_bootstrap = frequency @ count_difference / (32 * 16)
    assert np.array_equal(bootstrap, independent_bootstrap)
    assert float(interaction.mean()) == float(count_difference.sum() / 512)
    ordered = sorted(map(float, independent_bootstrap))
    def scalar_quantile(p):
        index = p * (len(ordered) - 1)
        low = int(index); remainder = index - low
        return ordered[low] + remainder * (ordered[min(low + 1, len(ordered) - 1)] - ordered[low])
    interval = np.quantile(bootstrap, [.025, .975])
    assert np.allclose(interval, [scalar_quantile(.025), scalar_quantile(.975)], atol=1e-15, rtol=0)

    original_policy = {}
    for regime in ("paired", "independent"):
        name = f"policy_interaction/both/{regime}/magnitude_permute/scattered"
        retained(name)
        original_policy[regime] = dict(
            definition="(permuted - untreated) under full rewriting minus the same contrast under strong preservation",
            mean_pp=100 * stats[name]["mean"],
            interval95_pp=[100 * x for x in stats[name]["interval"]],
            status="Original prespecified secondary, pointwise; not the new history interaction.")

    rows = []
    for i, block in enumerate(blocks):
        row = {"block": block, "lineages_per_condition": 16}
        row.update({name + "_successes": int(values[i] * 16) for name, values in cells.items()})
        row.update(matched_loss_pp=100 * float(matched_loss[i]),
                   independent_loss_pp=100 * float(independent_loss[i]),
                   history_interaction_pp=100 * float(interaction[i]))
        rows.append(row)
    table = io.StringIO(newline="")
    writer = csv.DictWriter(table, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
    result = dict(
        study="E054", evidence_note="E76", status="POST_HOC_NOT_PREREGISTERED",
        source_cohort="All 32 original E051 blocks, full-rewrite horizon-32 records, fresh common E054 scattered-injury assay.",
        independent_blocks=32, lineages_per_condition=512,
        definition=specification["contrast"], direction=specification["direction"],
        condition_successes={name: int((values * 16).sum()) for name, values in cells.items()},
        condition_rates_percent={name: 100 * float(values.mean()) for name, values in cells.items()},
        matched_permutation_loss_pp=100 * float(matched_loss.mean()),
        independent_permutation_loss_pp=100 * float(independent_loss.mean()),
        interaction_pp=100 * float(interaction.mean()),
        interval95_pp=[100 * float(x) for x in interval],
        bootstrap_draws=10000, bootstrap_method="Paired whole-block percentile; linear quantile interpolation; original E054 stream.",
        bootstrap_seed=seed, adjustment="Pointwise 95%; no correction for post hoc selection.",
        original_policy_interactions=original_policy,
        source_archive_sha256=sha(ARCHIVE), source_manifest_sha256=sha(SOURCES),
        analysis_specification_sha256=sha(SPEC), analysis_script_sha256=sha(Path(__file__).resolve()),
        numerical_environment={"numpy": np.__version__},
        checks={"original_mean_intervals_reproduced": 8,
                "paired_integer_count_reaggregation": True,
                "independent_quantile_check": True,
                "new_simulations": False, "raw_array_audit": False,
                "new_statistical_analysis": True, "original_qualification_changed": False})
    return result, table.getvalue()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    result, table = analyze()
    if args.check:
        assert json.loads(OUTPUT.read_text()) == result
        assert TABLE.read_text() == table
        print("PASS: retained sources, eight original intervals, post hoc paired interaction and integer reaggregation.")
    else:
        OUTPUT.write_text(text(result)); TABLE.write_text(table)
        print(json.dumps({key: result[key] for key in ("status", "matched_permutation_loss_pp", "independent_permutation_loss_pp", "interaction_pp", "interval95_pp")}, indent=2))


if __name__ == "__main__":
    main()
