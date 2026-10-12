"""Read-only analysis of the memory probe, including controls and fine repeats."""

import argparse
import json
from pathlib import Path

import numpy as np

from memory_metrics import REGULATORS, perturb_recipient, regulatory_distance


def analyze(folder):
    summary = json.loads((folder / "summary.json").read_text())
    records = {row["id"]: row for row in summary["cases"]}
    results = {name: row["result"] for name, row in records.items() if row["execution_pass"]}
    branch_checks = {}
    print(f"Run {folder.name}; {len(records)}/{len(summary['config']['cases'])} workers completed")
    print("case | seconds | phase labels: write/hold1/hold2/shadow/challenge | acquired | retained | recovered | D0 | Dfinal")
    for case in summary["config"]["cases"]:
        name = case["id"]
        if name not in records:
            continue
        if name not in results:
            print(f"{name} | INVALID {records[name]['status']}")
            continue
        result = results[name]
        labels = "/".join(phase["recipient_label"] for phase in result["audits"])
        recovery = result["recovery"]
        print(f"{name} | {records[name]['elapsed_seconds']:.3f} | {labels} | "
              f"{result['acquired_opposite_state']} | {result['retained_written_label']} | "
              f"{recovery['recovered']} | {recovery['initial_distance']:.6g} | {recovery['final_distance']:.6g}")
        # Audit persisted inputs, not merely the runner's reported flags.
        with np.load(folder / name / "endpoints.npz", allow_pickle=False) as points, \
             np.load(folder / name / "shadow.npz", allow_pickle=False) as shadow, \
             np.load(folder / name / "challenge.npz", allow_pickle=False) as challenged, \
             np.load(folder / name / "retention_1.npz", allow_pickle=False) as retained, \
             np.load(folder / "reference" / "references.npz", allow_pickle=False) as reference:
            reg = [result["ion_indices"][ion] for ion in REGULATORS]
            target = reference["later"][:, 0 if result["challenge_target"] == "E" else 1]
            expected_impulse = perturb_recipient(points["checkpoint"], target, reg, summary["config"]["perturbation_fraction"])
            expected_retained = points["written"] if case["history"] == "continuous" else points["written"][:, :1]
            checks = {
                "shadow_primary_equals_checkpoint": bool(np.array_equal(shadow["initial"][:8], points["checkpoint"][:8])),
                "challenge_primary_matches_registered_impulse": bool(np.array_equal(challenged["initial"][:8], expected_impulse[:8])),
                "donor_removal_preserves_retained_primary_state": bool(np.array_equal(retained["initial"][:8], expected_retained[:8])),
                "post_exposure_cell_count_correct": retained["initial"].shape[1] == (6 if case["history"] == "continuous" else 1),
            }
            branch_checks[name] = checks
            if not all(checks.values()):
                raise RuntimeError(f"Persisted-state audit failed for {name}: {checks}")
    print("PERSISTED_BRANCH_AUDIT " + json.dumps({"cases_checked": len(branch_checks), "all_passed": all(all(row.values()) for row in branch_checks.values())}))
    for initial in ("e", "m"):
        names = [f"{initial}_{mode}" for mode in ("naive", "pulse", "sham", "blocked", "continuous")]
        if not all(name in results for name in names):
            continue
        family = [results[name] for name in names]
        phase_labels = {name: [phase["recipient_label"] for phase in results[name]["audits"]] for name in names}
        print("FAMILY " + json.dumps({
            "initial": initial.upper(),
            "identical_recipient_start_hashes": len({row["recipient_start_hash"] for row in family}) == 1,
            "identical_post_exposure_external_environment": len({row["post_exposure_setup"]["environment_hash"] for row in family}) == 1,
            "control_label_sequences_as_expected": all(results[f"{initial}_{mode}"]["expected_label_sequence"] for mode in ("naive", "sham", "blocked", "continuous")),
            "pulse_donor_independent_acquired_recoverable_state": results[f"{initial}_pulse"]["donor_independent_acquired_recoverable_state"],
            "phase_labels": phase_labels,
        }))
        pulse = results[f"{initial}_pulse"]
        indices = [pulse["ion_indices"][name] for name in REGULATORS]
        scales = [pulse["regulator_scales"][name] for name in REGULATORS]
        a = np.load(folder / f"{initial}_pulse" / "endpoints.npz", allow_pickle=False)["shadow"]
        b = np.load(folder / f"{initial}_naive" / "endpoints.npz", allow_pickle=False)["shadow"]
        print("HISTORY_CONTRAST " + json.dumps({"initial": initial,
            "pulse_vs_naive_shadow_regulatory_distance": regulatory_distance(a[indices, 0], b[indices, 0], scales)}))
    for initial in ("e", "m"):
        base, fine = f"{initial}_pulse", f"{initial}_pulse_fine"
        if base not in results or fine not in results:
            continue
        a = np.load(folder / base / "endpoints.npz", allow_pickle=False)
        b = np.load(folder / fine / "endpoints.npz", allow_pickle=False)
        deltas = {}
        for phase in ("written", "checkpoint", "shadow", "challenged"):
            diff = np.abs(a[phase][:, 0] - b[phase][:, 0])
            deltas[phase] = {name: float(diff[index]) for name, index in results[base]["ion_indices"].items()}
        print("SENSITIVITY " + json.dumps({"initial": initial,
              "baseline_positive": results[base]["donor_independent_acquired_recoverable_state"],
              "fine_positive": results[fine]["donor_independent_acquired_recoverable_state"],
              "per_variable_endpoint_differences": deltas}))
    for name in ("e_pulse", "m_pulse"):
        if name in results:
            print("DRIFT " + json.dumps({"case": name,
                  "retention_recipient_drift": results[name]["retention_recipient_drift"],
                  "challenge_shadow_recipient_difference": results[name]["challenge_shadow_recipient_difference"]}))
    reference = summary.get("reference", {}).get("result", {}).get("audits", [])
    audits = reference + [phase for result in results.values() for phase in result["audits"]]
    if audits:
        print("AUDIT " + json.dumps({"completed_valid_phases": len(audits),
              "returned_snapshots": sum(phase["samples"] for phase in audits),
              "all_finite_nonnegative": all(phase["finite"] and phase["nonnegative"] for phase in audits),
              "largest_snapshot_raw_final_difference": max(phase["last_snapshot_raw_final_max_abs"] for phase in audits),
              "largest_derived_refresh_difference": max(phase["derived_refresh_max_abs"] for phase in audits),
              "simulation_cpu_seconds_sum": sum(phase["cpu_seconds"] for phase in audits),
              "suite_elapsed_seconds": summary.get("elapsed_seconds"),
              "all_execution_valid": summary.get("all_execution_valid"),
              "source_clean_after": summary.get("source_clean_after")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory", type=Path)
    analyze(parser.parse_args().run_directory)
