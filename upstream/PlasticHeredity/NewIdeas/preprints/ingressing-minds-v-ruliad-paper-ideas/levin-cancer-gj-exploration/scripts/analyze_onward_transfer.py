"""Read-only checks and comparisons of an onward-transfer run's saved arrays."""

import argparse
import json
from pathlib import Path

import numpy as np

from memory_metrics import REGULATORS, classify, opposite, perturb_recipient, regulatory_distance, recovery_decision
from run_onward_transfer import donor_source, file_hash, retained_label


def analyze(run):
    summary = json.loads((run / "summary.json").read_text())
    config = summary["config"]
    with np.load(run / "inputs" / "references.npz", allow_pickle=False) as refs:
        prepared, later = refs["prepared"], refs["later"]
    indices = json.loads((run / "inputs" / "reference.json").read_text())["ion_indices"]
    reg = [indices[name] for name in REGULATORS]
    scales = np.abs(later[reg, 0] - later[reg, 1])
    records, arrays, checks, row_data = {}, {}, {}, []
    all_phases = []
    for case in config["cases"]:
        name = case["id"]
        folder = run / name
        result = json.loads((folder / "result.json").read_text())
        records[name] = result
        with np.load(folder / "endpoints.npz", allow_pickle=False) as saved:
            end = {key: saved[key] for key in saved.files}
        arrays[name] = end
        stages = {}
        for phase in ("contact", "retention_1", "retention_2", "shadow", "challenge"):
            with np.load(folder / f"{phase}.npz", allow_pickle=False) as saved:
                stages[phase] = {key: saved[key] for key in saved.files}
        original = opposite(case["learned_state"])
        fresh = prepared[:, {"E": 0, "M": 1}[original], None]
        origin = donor_source(case["learned_state"], case["history"])
        labels = classify(end["contact"], indices)
        expected_count = 1 if origin is None else 2
        check = {
            "execution_pass": result["execution_pass"],
            "recipient_from_independent_reference": np.array_equal(end["initial"][:, :1], fresh),
            "expected_cell_counts": end["initial"].shape == (17, expected_count)
                and all(end[key].shape == (17, 1) for key in ("retained_1", "checkpoint", "shadow", "challenged")),
            "contact_initialized_without_primary_change": np.array_equal(stages["contact"]["initial"][:8], end["initial"][:8]),
            "contact_endpoint_matches": np.array_equal(stages["contact"]["final"], end["contact"]),
            "donor_removal_preserves_recipient_primary_state": np.array_equal(stages["retention_1"]["initial"][:8], end["contact"][:8, :1]),
            "holds_connected_in_time": np.array_equal(stages["retention_2"]["initial"][:8], end["retained_1"][:8]),
            "shadow_starts_at_checkpoint": np.array_equal(stages["shadow"]["initial"][:8], end["checkpoint"][:8]),
            "challenge_starts_at_perturbed": np.array_equal(stages["challenge"]["initial"][:8], end["perturbed"][:8]),
            "isolated_after_contact": all(record["cells"] == 1 and record["graph_edges"] == 0 and record["miRNA_kd"] == 0
                                          for record in result["audits"][1:]),
            "all_saved_states_finite_nonnegative": all(np.isfinite(value).all() and (value >= 0).all()
                for stage in stages.values() for value in stage.values()),
            "recorded_contact_labels_agree": result["contact_label"] == labels[0]
                and (origin is None or result["donor_contact_label"] == labels[1]),
            "normalization_agrees": np.array_equal(end["regulator_scales"], scales),
        }
        if origin is not None:
            with np.load(run / "inputs" / f"{origin}.npz", allow_pickle=False) as saved:
                check["donor_from_original_unmodified_checkpoint"] = np.array_equal(end["initial"][:, 1:], saved["checkpoint"])
        before = str(classify(end["checkpoint"], indices)[0])
        target = opposite(before if before in ("E", "M") else original)
        expected_impulse = perturb_recipient(end["checkpoint"], later[:, {"E": 0, "M": 1}[target]], reg,
                                             config["perturbation_fraction"])
        check["exact_declared_impulse_only"] = np.array_equal(end["perturbed"], expected_impulse)
        d0 = regulatory_distance(end["perturbed"][reg, 0], end["checkpoint"][reg, 0], scales)
        dfinal = regulatory_distance(end["challenged"][reg, 0], end["shadow"][reg, 0], scales)
        shadow_label, challenged_label = (str(classify(end[key], indices)[0]) for key in ("shadow", "challenged"))
        recovery = recovery_decision(d0, dfinal, before, shadow_label, challenged_label, config)
        check["recovery_recomputed"] = recovery == result["recovery"]
        holds = []
        for phase, duration in zip(("retention_1", "retention_2"), config["retention_horizons"]):
            stage = stages[phase]
            sampled = classify(stage["concentrations"], indices)[:, 0]
            late = sampled[stage["times"] >= duration * .75]
            holds.append({"recipient_label": str(classify(stage["final"], indices)[0]),
                          "late_label_fractions": {label: float(np.mean(late == label)) for label in ("E", "M", "X")}})
        retained = retained_label(str(labels[0]), holds, shadow_label, config["late_label_fraction"])
        positive = case["history"] == "learned" and labels[0] == case["learned_state"] and retained and recovery["recovered"]
        check["propagation_recomputed"] = bool(positive) == result["one_hop_acquired_state_propagation"]
        check["retention_recomputed"] = retained == result["retained_contact_label"]
        checks[name] = {key: bool(value) for key, value in check.items()}
        all_phases.extend(result["audits"])
        row_data.append({"case": name, "recipient_initial": original, "contact_pair": "".join(labels),
                         "recipient_retained": before, "recipient_challenged": challenged_label,
                         "retained_contact_label": retained, "recovery": recovery,
                         "one_hop_propagation": bool(positive),
                         "maximum_primary_ion_hold_drift": float(np.max(np.abs(end["checkpoint"][:4] - end["retained_1"][:4]))),
                         "hold_late_label_fractions": [hold["late_label_fractions"] for hold in holds]})
    comparisons = {}
    for prefix in ("e", "m"):
        learned = arrays[f"{prefix}_learned"]
        blocked = arrays[f"{prefix}_blocked"]
        comparisons[f"{prefix}_active_vs_blocked"] = {
            "contact_recipient_regulatory_distance": regulatory_distance(learned["contact"][reg, 0], blocked["contact"][reg, 0], scales),
            "checkpoint_recipient_regulatory_distance": regulatory_distance(learned["checkpoint"][reg, 0], blocked["checkpoint"][reg, 0], scales),
            "active_contact_regulators": dict(zip(REGULATORS, learned["contact"][reg, 0].tolist())),
            "blocked_contact_regulators": dict(zip(REGULATORS, blocked["contact"][reg, 0].tolist())),
            "isolated_recipient_regulators": dict(zip(REGULATORS, learned["checkpoint"][reg, 0].tolist())),
        }
        for variant in ("same_state", "learned_fine"):
            other = arrays[f"{prefix}_{variant}"]
            comparisons[f"{prefix}_learned_vs_{variant}"] = {
                "initial_donor_max_abs_difference": float(np.max(np.abs(learned["initial"][:, 1] - other["initial"][:, 1]))),
                "initial_donor_regulatory_distance": regulatory_distance(learned["initial"][reg, 1], other["initial"][reg, 1], scales),
                "contact_recipient_regulatory_distance": regulatory_distance(learned["contact"][reg, 0], other["contact"][reg, 0], scales),
                "checkpoint_recipient_regulatory_distance": regulatory_distance(learned["checkpoint"][reg, 0], other["checkpoint"][reg, 0], scales),
                "checkpoint_full_vector_max_abs_difference": float(np.max(np.abs(learned["checkpoint"] - other["checkpoint"]))),
                "same_contact_pair_labels": records[f"{prefix}_learned"]["audits"][0]["all_labels"] == records[f"{prefix}_{variant}"]["audits"][0]["all_labels"],
            }
    input_hashes_valid = all(file_hash(run / "inputs" / name) == item["sha256"] for name, item in summary["inputs"].items())
    controls = {name: result["control_kept_initial_label"] for name, result in records.items()
                if result["control_kept_initial_label"] is not None}
    return {
        "run": str(run), "all_execution_valid": summary["all_execution_valid"],
        "all_array_checks_pass": all(all(check.values()) for check in checks.values()), "array_checks": checks,
        "input_hashes_valid": input_hashes_valid, "controls": controls,
        "all_controls_keep_initial_label": all(controls.values()), "cases": row_data, "comparisons": comparisons,
        "integration_calls": len(all_phases), "snapshots": sum(phase["samples"] for phase in all_phases),
        "elapsed_seconds": summary["elapsed_seconds"], "total_cpu_seconds": sum(phase["cpu_seconds"] for phase in all_phases),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    summary = json.loads((args.run / "summary.json").read_text())
    if "all_execution_valid" not in summary or not summary["all_execution_valid"]:
        parser.error("This analyzer requires a finished, numerically valid suite; inspect summary/progress files for incomplete runs.")
    report = analyze(args.run.resolve())
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report["all_execution_valid"] and report["all_array_checks_pass"] and report["input_hashes_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
