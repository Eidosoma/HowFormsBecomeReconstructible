"""Read-only summary of pilot outcomes and paired endpoint sensitivity."""

import argparse
import json
from pathlib import Path

import numpy as np

from run_pilot import compare_thresholds


def analyze(folder):
    summary = json.loads((folder / "summary.json").read_text())
    records = {record["id"]: record for record in summary["cases"]}
    config = json.loads((folder / "config.json").read_text())
    partial_audits = []
    print(f"Run: {folder.name}; completed {len(records)}/{len(summary['selected_cases'])}")
    print("case | comparison pass | elapsed seconds | E/M/X counts or thresholds")
    for name in summary["selected_cases"]:
        if name not in records:
            continue
        record = records[name]
        result = record.get("result", {})
        counts = result.get("final_state_counts", result.get("thresholds", record["status"]))
        print(f"{name} | {record['pass']} | {record.get('elapsed_seconds', 0):.3f} | {counts}")
        if not result and (folder / name / "progress.json").exists():
            partial_audits.extend(json.loads((folder / name / "progress.json").read_text()))
            output = (folder / name / "stdout.log").read_text()
            rows, _ = compare_thresholds(output, config["threshold_relative_tolerance"])
            if rows:
                print("PARTIAL_THRESHOLDS " + json.dumps({"case": name, "completed_thresholds": rows,
                      "scope": "Partial completed searches; does not pass the eight-search gate"}))
    for base, variant in (
        ("isolation_voltage_high", "sensitivity_voltage_fine"),
        ("isolation_both_low", "sensitivity_both_fine"),
        ("isolation_both_low", "sensitivity_both_long"),
    ):
        if any(name not in records or "result" not in records[name] for name in (base, variant)):
            continue
        a = np.load(folder / base / "endpoints.npz", allow_pickle=False)["final"]
        b = np.load(folder / variant / "endpoints.npz", allow_pickle=False)["final"]
        ion_indices = records[base]["result"]["ion_indices"]
        differences = {
            ion: float(np.max(np.abs(a[index] - b[index])))
            for ion, index in ion_indices.items()
        }
        print(f"SENSITIVITY {base} -> {variant}: " + json.dumps({
            "same_labels": records[base]["result"]["final_state_labels"] == records[variant]["result"]["final_state_labels"],
            "maximum_absolute_concentration_difference": float(np.max(np.abs(a - b))),
            "per_ion_max_abs": differences,
        }))
    audits = partial_audits + [audit for record in records.values() for audit in record.get("result", {}).get("audits", [])]
    if audits:
        print("AUDIT " + json.dumps({
            "completed_simulations": len(audits),
            "simulations_from_partial_cases": len(partial_audits),
            "returned_snapshot_count": sum(audit["sample_count"] for audit in audits),
            "all_sampled_finite_nonnegative": all(audit["finite"] and audit["nonnegative"] for audit in audits),
            "largest_last_sample_vs_final_abs": max(audit["last_sample_vs_final_max_abs"] for audit in audits),
            "simulation_wall_seconds_sum": sum(audit["wall_seconds"] for audit in audits),
            "simulation_cpu_seconds_sum": sum(audit["cpu_seconds"] for audit in audits),
        }))
    if all(name in records and "result" in records[name] for name in ("isolation_none_high", "benchmark_625")):
        small, large = (records[name]["result"] for name in ("isolation_none_high", "benchmark_625"))
        print("SCALING " + json.dumps({
            "wall_time_ratio": large["wall_seconds"] / small["wall_seconds"],
            "small_wall_seconds": small["wall_seconds"], "large_wall_seconds": large["wall_seconds"],
            "large_cpu_seconds": large["cpu_seconds"], "large_peak_rss_mib": large["peak_rss_kib"] / 1024,
            "scope": "Single matched 25 vs 625 cell comparison, not a scaling law",
        }))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory", type=Path)
    analyze(parser.parse_args().run_directory)
