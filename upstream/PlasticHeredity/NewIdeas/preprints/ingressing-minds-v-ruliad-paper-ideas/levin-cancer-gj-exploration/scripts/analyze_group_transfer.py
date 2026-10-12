"""Read-only saved-array audit of donor preparation and group onward transfer."""

import argparse
import json
from pathlib import Path

import numpy as np

from memory_metrics import REGULATORS, classify, opposite, perturb_recipient, regulatory_distance, recovery_decision
from run_group_transfer import assemble_group, donor_ids, donor_qualified
from run_onward_transfer import file_hash, retained_label


def arrays(path):
    with np.load(path, allow_pickle=False) as saved:
        return {key: saved[key] for key in saved.files}


def audit_phases(folder, indices, config, later, exposure):
    end = arrays(folder / "endpoints.npz")
    phases = {name: arrays(folder / f"{name}.npz") for name in (exposure, "retention_1", "retention_2", "shadow", "challenge")}
    result = json.loads((folder / "result.json").read_text())
    endpoint_key = "written" if exposure == "write" else "contact"
    reg = [indices[name] for name in REGULATORS]
    scales = np.abs(later[reg, 0] - later[reg, 1])
    contact_label = str(classify(end[endpoint_key], indices)[0])
    original = str(classify(end["initial"], indices)[0])
    before = str(classify(end["checkpoint"], indices)[0])
    shadow_label, challenge_label = (str(classify(end[key], indices)[0]) for key in ("shadow", "challenged"))
    target = opposite(before if before in ("E", "M") else original)
    expected_impulse = perturb_recipient(end["checkpoint"], later[:, {"E": 0, "M": 1}[target]], reg, config["perturbation_fraction"])
    d0 = regulatory_distance(end["perturbed"][reg, 0], end["checkpoint"][reg, 0], scales)
    dfinal = regulatory_distance(end["challenged"][reg, 0], end["shadow"][reg, 0], scales)
    recovery = recovery_decision(d0, dfinal, before, shadow_label, challenge_label, config)
    holds = []
    for phase, duration in zip(("retention_1", "retention_2"), config["retention_horizons"]):
        data = phases[phase]
        sampled = classify(data["concentrations"], indices)[:, 0]
        late = sampled[data["times"] >= .75 * duration]
        holds.append({"recipient_label": str(classify(data["final"], indices)[0]),
                      "late_label_fractions": {label: float(np.mean(late == label)) for label in ("E", "M", "X")}})
    retained = retained_label(contact_label, holds, shadow_label, config["late_label_fraction"])
    checks = {
        "indices_match": result["ion_indices"] == indices,
        "finite_nonnegative_saved_states": all(np.isfinite(value).all() and (value >= 0).all()
            for phase in phases.values() for value in phase.values()),
        "chronological_samples": all(np.all(np.diff(phase["times"]) > 0) for phase in phases.values()),
        "primary_exposure_initialization_preserved": np.array_equal(phases[exposure]["initial"][:8], end["initial"][:8]),
        "contact_final_matches": np.array_equal(phases[exposure]["final"], end[endpoint_key]),
        "removal_preserves_target_primary_state": np.array_equal(phases["retention_1"]["initial"][:8], end[endpoint_key][:8, :1]),
        "holds_chained": np.array_equal(phases["retention_2"]["initial"][:8], end["retained_1"][:8]),
        "shadow_starts_at_checkpoint": np.array_equal(phases["shadow"]["initial"][:8], end["checkpoint"][:8]),
        "challenge_starts_at_impulse": np.array_equal(phases["challenge"]["initial"][:8], end["perturbed"][:8]),
        "saved_hold_endpoints_match": np.array_equal(phases["retention_1"]["final"], end["retained_1"])
            and np.array_equal(phases["retention_2"]["final"], end["checkpoint"]),
        "saved_fork_endpoints_match": np.array_equal(phases["shadow"]["final"], end["shadow"])
            and np.array_equal(phases["challenge"]["final"], end["challenged"]),
        "only_declared_impulse_applied": np.array_equal(end["perturbed"], expected_impulse),
        "reference_scales_match": np.array_equal(end["regulator_scales"], scales),
        "recovery_recomputed": recovery == result["recovery"],
        "one_target_after_removal": all(phase["initial"].shape == (17, 1) and phase["final"].shape == (17, 1)
                                        for name, phase in phases.items() if name != exposure),
        "zero_edges_and_miRNA_transport_after_removal": all(audit["cells"] == 1 and audit["graph_edges"] == 0 and audit["miRNA_kd"] == 0
                                                           for audit in result["audits"][1:]),
        "recorded_labels_match_arrays": all(audit["all_labels"] == "".join(classify(phases[audit["phase"]]["final"], indices))
                                             for audit in result["audits"]),
    }
    details = {"initial_label": original, "contact_labels": "".join(classify(end[endpoint_key], indices)),
               "retained_label": before, "challenge_label": challenge_label, "retained_contact_label": retained,
               "recovery": recovery, "holds": holds,
               "maximum_primary_ion_hold_drift": float(np.max(np.abs(end["checkpoint"][:4] - end["retained_1"][:4]))),
               "contact_recipient_regulators": dict(zip(REGULATORS, end[endpoint_key][reg, 0].tolist()))}
    return end, result, checks, details


def compare_endpoints(a, b, indices, scales):
    reg = [indices[name] for name in REGULATORS]
    return {"contact_regulatory_distance": regulatory_distance(a["contact"][reg, 0], b["contact"][reg, 0], scales),
            "checkpoint_regulatory_distance": regulatory_distance(a["checkpoint"][reg, 0], b["checkpoint"][reg, 0], scales),
            "checkpoint_full_vector_max_abs_difference": float(np.max(np.abs(a["checkpoint"] - b["checkpoint"]))),
            "same_contact_labels": bool(np.array_equal(classify(a["contact"], indices), classify(b["contact"], indices))),
            "same_retained_labels": bool(np.array_equal(classify(a["checkpoint"], indices), classify(b["checkpoint"], indices)))}


def analyze(run):
    summary = json.loads((run / "summary.json").read_text())
    if not summary.get("all_execution_valid"):
        raise ValueError("A finished, numerically valid suite is required; inspect summary/progress for incomplete runs")
    config = summary["config"]
    reference = arrays(run / "inputs" / "references.npz")
    prepared, later = reference["prepared"], reference["later"]
    indices = json.loads((run / "inputs" / "reference.json").read_text())["ion_indices"]
    reg = [indices[name] for name in REGULATORS]
    scales = np.abs(later[reg, 0] - later[reg, 1])
    bank, groups, all_checks, rows, audits = {}, {}, {}, [], []
    for case in summary["planned_bank"]:
        name = case["id"]
        end, result, checks, details = audit_phases(run / "bank" / name, indices, summary["bank_config"], later, "write")
        original = case["initial"]
        if case["history"] == "pulse":
            donors = [prepared[:, {"E": 0, "M": 1}[opposite(original)], None]] * summary["bank_config"]["donors"]
            expected = opposite(original)
        else:
            donors, expected = [], original
        expected_initial = assemble_group(prepared[:, {"E": 0, "M": 1}[original], None], donors)
        qualified = details["contact_labels"][0] == expected and details["retained_contact_label"] and details["recovery"]["recovered"]
        checks.update(fresh_donor_preparation_initialized_correctly=np.array_equal(end["initial"], expected_initial),
                      donor_qualification_recomputed=qualified and donor_qualified(result))
        bank[name] = end
        all_checks[f"bank/{name}"] = checks
        audits.extend(result["audits"])
    for case in summary["planned_groups"]:
        name = case["id"]
        end, result, checks, details = audit_phases(run / "groups" / name, indices, config, later, "contact")
        original = opposite(case["learned_state"])
        fresh = prepared[:, {"E": 0, "M": 1}[original], None]
        ids = donor_ids(case)
        expected_initial = assemble_group(fresh, [bank[donor]["checkpoint"] for donor in ids])
        positive = bool(details["contact_labels"][0] == case["learned_state"] and details["retained_contact_label"] and details["recovery"]["recovered"])
        checks.update(target_and_all_donors_from_correct_independent_inputs=np.array_equal(end["initial"], expected_initial),
                      donor_ids_match=[entry["id"] for entry in result["donor_provenance"]] == ids,
                      expected_star_edges=result["contact_edges"] == [[0, i] for i in range(1, case["donors"] + 1)],
                      correct_contact_cell_count=end["initial"].shape == (17, case["donors"] + 1),
                      transfer_recomputed=positive == result["durable_state_transfer"],
                      learned_transfer_recomputed=bool(case["history"] == "learned" and positive) == result["acquired_state_onward_propagation"],
                      retention_recomputed=details["retained_contact_label"] == result["retained_contact_label"],
                      expected_contact_transport=result["contact_setup"]["miRNA_kd"] == (0 if case["history"] in ("alone", "blocked") else config["write_kd"]))
        details.update(case=case, durable_state_transfer=positive, donor_ids=ids,
                       all_donors_kept_initial_label=bool(np.array_equal(classify(end["initial"], indices)[1:], classify(end["contact"], indices)[1:])),
                       control_kept_initial_label=result["control_kept_initial_label"])
        rows.append(details)
        all_checks[f"groups/{name}"] = checks
        groups[name] = end
        audits.extend(result["audits"])
    comparisons, minima, bank_variation = {}, {}, {}
    for state in ("e", "m"):
        for n in config["donor_counts"]:
            learned = groups[f"{state}_learned_n{n}"]
            comparisons[f"{state}_n{n}_learned_vs_naive"] = compare_endpoints(learned, groups[f"{state}_same_state_n{n}"], indices, scales)
            comparisons[f"{state}_n{n}_learned_vs_alone"] = compare_endpoints(learned, groups[f"{state}_alone_n0"], indices, scales)
            if n in config["fine_counts"]:
                comparisons[f"{state}_n{n}_baseline_vs_fine"] = compare_endpoints(learned, groups[f"{state}_learned_n{n}_fine"], indices, scales)
        for history in ("learned", "same_state"):
            success = [row["case"]["donors"] for row in rows if row["case"]["learned_state"] == state.upper()
                       and row["case"]["history"] == history and not row["case"].get("fine") and row["durable_state_transfer"]]
            minima[f"{state}_{history}"] = min(success) if success else None
        for history in ("pulse", "naive"):
            states = np.stack([bank[f"{state}_{history}_{i:02}"]["checkpoint"] for i in range(1, config["bank_size"] + 1)])
            bank_variation[f"{state}_{history}"] = float(np.max(np.abs(states - states[0])))
    bank_manifest = json.loads((run / "bank_manifest.json").read_text())
    provenance_checks = {
        "copied_input_hashes": all(file_hash(run / "inputs" / name) == entry["sha256"] for name, entry in summary["inputs"].items()),
        "bank_manifest_hash": file_hash(run / "bank_manifest.json") == summary["bank_manifest_sha256"],
        "bank_artifact_hashes": all(file_hash(run / "bank" / donor / name) == digest for donor, entries in bank_manifest.items()
                                    for name, digest in entries.items()),
    }
    all_checks = {name: {key: bool(value) for key, value in checks.items()} for name, checks in all_checks.items()}
    return {
        "run": str(run), "all_execution_valid": summary["all_execution_valid"],
        "all_array_checks_pass": all(all(checks.values()) for checks in all_checks.values()),
        "provenance_checks": provenance_checks, "array_checks": all_checks,
        "minimum_successful_tested_counts": minima, "cases": rows, "comparisons": comparisons,
        "bank_maximum_within_type_checkpoint_difference": bank_variation,
        "all_controls_kept_initial_label": all(row["control_kept_initial_label"] for row in rows if row["control_kept_initial_label"] is not None),
        "bank_conditions": len(bank), "group_conditions": len(groups), "integration_calls": len(audits),
        "snapshots": sum(audit["samples"] for audit in audits), "elapsed_seconds": summary["elapsed_seconds"],
        "total_cpu_seconds": sum(audit["cpu_seconds"] for audit in audits),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--compact", action="store_true", help="Omit individual passing checks and detailed comparisons")
    args = parser.parse_args()
    try:
        report = analyze(args.run.resolve())
    except ValueError as error:
        parser.error(str(error))
    if args.compact:
        report["failed_array_checks"] = {name: [key for key, passed in checks.items() if not passed]
                                         for name, checks in report.pop("array_checks").items() if not all(checks.values())}
        report.pop("comparisons")
        report["cases"] = [{"id": row["case"]["id"], "contact_labels": row["contact_labels"],
                            "retained_label": row["retained_label"], "recovery": row["recovery"]["recovered"],
                            "durable_state_transfer": row["durable_state_transfer"]} for row in report["cases"]]
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report["all_array_checks_pass"] and all(report["provenance_checks"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
