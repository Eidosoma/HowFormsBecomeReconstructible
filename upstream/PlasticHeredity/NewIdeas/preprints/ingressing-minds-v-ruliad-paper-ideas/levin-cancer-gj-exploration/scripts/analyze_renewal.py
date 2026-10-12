"""Read-only lineage audit, including physical-state continuity and full replacement."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_group_transfer import arrays
from memory_metrics import REGULATORS, classify, opposite, perturb_recipient, regulatory_distance, recovery_decision
from run_onward_transfer import file_hash, retained_label
from run_renewal import founder_names


def audit_round(folder, config, case, number, incoming, ids, seen, fresh, later, indices):
    end = arrays(folder / "endpoints.npz")
    result = json.loads((folder / "result.json").read_text())
    names = ["write_1", "write_2", "wait_1"] + [f"child_{i}_{stage}" for i in (1, 2)
                                                for stage in ("hold_1", "hold_2", "shadow", "challenge")]
    phases = {name: arrays(folder / f"{name}.npz") for name in names}
    reg = [indices[name] for name in REGULATORS]
    scales = np.abs(later[reg, 0] - later[reg, 1])
    new_ids = [f"{case['id']}:round_{number:02}:child_{i}" for i in (1, 2)]
    duration = 2 * config["contact_horizon"] + sum(config["retention_horizons"])
    checks = {
        "valid_execution_and_indices": result["execution_pass"] and result["ion_indices"] == indices,
        "exact_previous_packet_continuity": np.array_equal(end["incoming_packet"], incoming),
        "fresh_targets_independent_and_fixed": all(np.array_equal(end[key][:, :1], fresh) for key in ("first_initial", "second_initial"))
            and np.array_equal(end["fresh_target"], fresh),
        "first_write_uses_current_packet": np.array_equal(end["first_initial"][:, 1:], incoming),
        "first_write_primary_start_matches": np.array_equal(phases["write_1"]["initial"][:8], end["first_initial"][:8]),
        "evolved_donors_not_reset_before_second_write": np.array_equal(end["second_initial"][:, 1:], end["contact_1"][:, 1:]),
        "second_write_primary_start_matches": np.array_equal(phases["write_2"]["initial"][:8], end["second_initial"][:8]),
        "contact_endpoints_match": all(np.array_equal(phases[f"write_{i}"]["final"], end[f"contact_{i}"]) for i in (1, 2)),
        "first_child_waits_from_actual_contact_state": np.array_equal(phases["wait_1"]["initial"][:8], end["contact_1"][:8, :1]),
        "first_child_wait_endpoint_matches": np.array_equal(phases["wait_1"]["final"], end["child_1_waited"]),
        "incoming_ids_match_previous_packet": result["incoming_ids"] == ids,
        "all_new_ids_unique_and_old_ids_excluded": result["outgoing_ids"] == new_ids and len(set(new_ids)) == 2 and not (set(new_ids) & seen),
        "nominal_schedule_matches": result["nominal_round_start"] == (number - 1) * duration and result["nominal_round_end"] == number * duration,
        "saved_states_finite_nonnegative": all(np.isfinite(value).all() and (value >= 0).all() for phase in phases.values() for value in phase.values()),
        "sample_times_increase": all(np.all(np.diff(phase["times"]) > 0) for phase in phases.values()),
        "reference_scales_match": np.array_equal(end["regulator_scales"], scales),
        "diagnostics_declared_outside_lineage": result["diagnostic_branches_enter_lineage"] is False,
        "correct_contact_graphs": all(setup["cells"] == 3 and setup["edges_list"] == [[0, 1], [0, 2]] for setup in result["setups"][:2]),
        "remaining_setups_isolated": all(setup["cells"] == 1 and setup["edges_list"] == [] and setup["miRNA_kd"] == 0 for setup in result["setups"][2:]),
        "phase_transport_matches_protocol": all(audit["miRNA_kd"] == (config["write_kd"] if case["history"] != "blocked" and audit["phase"].startswith("write_") else 0)
                                                for audit in result["audits"]),
        "audit_labels_match_saved_arrays": all(audit["all_labels"] == "".join(classify(phases[audit["phase"]]["final"], indices)) for audit in result["audits"]),
    }
    outcomes = []
    for i in (1, 2):
        column = slice(i - 1, i)
        prefix = f"child_{i}_"
        contact_label = str(classify(end[f"contact_{i}"], indices)[0])
        checkpoint = end["outgoing_packet"][:, column]
        held = end["held_first"][:, column]
        held_start = end["child_1_waited"] if i == 1 else end["contact_2"][:, :1]
        shadow, challenged = end["shadow_packet"][:, column], end["challenged_packet"][:, column]
        changed = end["perturbed_packet"][:, column]
        before = str(classify(checkpoint, indices)[0])
        target = opposite(before if before in ("E", "M") else opposite(case["state"]))
        expected_impulse = perturb_recipient(checkpoint, later[:, {"E": 0, "M": 1}[target]], reg, config["perturbation_fraction"])
        checks.update({
            prefix + "hold_starts_from_new_child": np.array_equal(phases[prefix + "hold_1"]["initial"][:8], held_start[:8]),
            prefix + "holds_are_contiguous": np.array_equal(phases[prefix + "hold_2"]["initial"][:8], held[:8]),
            prefix + "first_hold_endpoint_matches": np.array_equal(phases[prefix + "hold_1"]["final"], held),
            prefix + "only_unchallenged_new_child_enters_packet": np.array_equal(phases[prefix + "hold_2"]["final"], checkpoint),
            prefix + "shadow_starts_at_checkpoint": np.array_equal(phases[prefix + "shadow"]["initial"][:8], checkpoint[:8]),
            prefix + "exact_regulatory_impulse": np.array_equal(changed, expected_impulse),
            prefix + "challenge_starts_at_impulse": np.array_equal(phases[prefix + "challenge"]["initial"][:8], changed[:8]),
            prefix + "diagnostic_endpoints_match": np.array_equal(phases[prefix + "shadow"]["final"], shadow) and np.array_equal(phases[prefix + "challenge"]["final"], challenged),
        })
        holds = []
        for stage, horizon in zip(("hold_1", "hold_2"), config["retention_horizons"]):
            phase = phases[prefix + stage]
            sampled = classify(phase["concentrations"], indices)[:, 0]
            late = sampled[phase["times"] >= horizon * .75]
            holds.append({"recipient_label": str(classify(phase["final"], indices)[0]),
                          "late_label_fractions": {label: float(np.mean(late == label)) for label in ("E", "M", "X")}})
        retained = retained_label(contact_label, holds, str(classify(shadow, indices)[0]), config["late_label_fraction"])
        wait_ok = True
        if i == 1:
            wait = phases["wait_1"]
            late = classify(wait["concentrations"], indices)[:, 0][wait["times"] >= config["contact_horizon"] * .75]
            wait_ok = contact_label in ("E", "M") and str(classify(wait["final"], indices)[0]) == contact_label and np.mean(late == contact_label) >= config["late_label_fraction"]
        d0 = regulatory_distance(changed[reg, 0], checkpoint[reg, 0], scales)
        dfinal = regulatory_distance(challenged[reg, 0], shadow[reg, 0], scales)
        recovery = recovery_decision(d0, dfinal, before, str(classify(shadow, indices)[0]), str(classify(challenged, indices)[0]), config)
        success = bool(contact_label == case["state"] and wait_ok and retained and recovery["recovered"])
        recorded = result["children"][i - 1]
        checks.update({prefix + "recovery_recomputed": recovery == recorded["recovery"],
                       prefix + "retention_recomputed": retained == recorded["retained_contact_label"],
                       prefix + "wait_recomputed": bool(wait_ok) == recorded["wait_preserved_label"],
                       prefix + "success_recomputed": success == recorded["durable_transfer"]})
        outcomes.append({"id": new_ids[i - 1], "contact_label": contact_label, "retained_label": before,
                         "durable_transfer": success, "recovery": recovery, "holds": holds,
                         "ion_hold_drift": float(np.max(np.abs(checkpoint[:4] - held[:4])))})
    round_success = all(child["durable_transfer"] for child in outcomes)
    checks["round_success_recomputed"] = round_success == result["round_success"]
    checks["correct_pair_shapes"] = all(end[key].shape == (17, 2) for key in ("incoming_packet", "outgoing_packet", "perturbed_packet", "shadow_packet", "challenged_packet"))
    row = {"round": number, "incoming_labels": "".join(classify(incoming, indices)),
           "outgoing_labels": "".join(classify(end["outgoing_packet"], indices)), "children": outcomes,
           "round_success": round_success, "old_donors_after_write_1": "".join(classify(end["contact_1"][:, 1:], indices)),
           "old_donors_after_write_2": "".join(classify(end["contact_2"][:, 1:], indices)),
           "donor_full_state_change_during_first_contact": float(np.max(np.abs(end["contact_1"][:, 1:] - incoming)))}
    return end, row, {key: bool(value) for key, value in checks.items()}, result["audits"]


def analyze(run):
    summary = json.loads((run / "summary.json").read_text())
    if not summary.get("all_execution_valid"):
        raise ValueError("A finished, numerically valid suite is required; inspect progress for incomplete runs")
    config = summary["config"]
    refs = arrays(run / "inputs" / "references.npz")
    indices = json.loads((run / "inputs" / "reference.json").read_text())["ion_indices"]
    reg = [indices[name] for name in REGULATORS]
    scales = np.abs(refs["later"][reg, 0] - refs["later"][reg, 1])
    rows, checks, audits, all_endpoints = [], {}, [], {}
    for case in config["cases"]:
        founders = [arrays(run / "inputs" / f"{name}.npz")["checkpoint"] for name in founder_names(case)]
        packet = np.concatenate(founders, axis=1)
        fresh = refs["prepared"][:, {"E": 0, "M": 1}[opposite(case["state"])], None]
        ids = [f"{case['id']}:founder:{name}" for name in founder_names(case)]
        seen = set(ids)
        line = []
        for number in range(1, config["rounds"] + 1):
            folder = run / case["id"] / f"round_{number:02}"
            end, row, round_checks, phase_audits = audit_round(folder, config, case, number, packet, ids, seen, fresh, refs["later"], indices)
            packet = end["outgoing_packet"]
            ids = [child["id"] for child in row["children"]]
            seen.update(ids)
            checks[f"{case['id']}/round_{number:02}"] = round_checks
            all_endpoints[(case["id"], number)] = end
            line.append(row)
            audits.extend(phase_audits)
        result = json.loads((run / case["id"] / "result.json").read_text())
        endpoints = arrays(run / case["id"] / "endpoints.npz")
        transmitted = all(row["round_success"] for row in line)
        checks[case["id"]] = {
            "lineage_outcome_recomputed": transmitted == result["all_rounds_transmitted"],
            "final_ids_match": ids == result["final_ids"],
            "exact_fresh_target_count": result["distinct_fresh_targets"] == 2 * config["rounds"] == len(seen) - 2,
            "saved_final_packet_matches_last_round": np.array_equal(endpoints["final_packet"], packet),
            "saved_founder_packet_matches_inputs": np.array_equal(endpoints["founders"], np.concatenate(founders, axis=1)),
        }
        rows.append({"case": case, "rounds": line, "all_rounds_transmitted": transmitted})
    comparisons = {}
    for state in ("e", "m"):
        for variant in ("ordinary", "learned_fine"):
            rounds = []
            for number in range(1, config["rounds"] + 1):
                a = all_endpoints[(state + "_learned", number)]
                b = all_endpoints[(state + "_" + variant, number)]
                rounds.append({"round": number,
                    "outgoing_regulatory_distance": float(np.max(np.abs(a["outgoing_packet"][reg] - b["outgoing_packet"][reg]) / scales[:, None])),
                    "outgoing_full_state_max_abs_difference": float(np.max(np.abs(a["outgoing_packet"] - b["outgoing_packet"]))),
                    "same_outgoing_labels": bool(np.array_equal(classify(a["outgoing_packet"], indices), classify(b["outgoing_packet"], indices)))})
            comparisons[f"{state}_learned_vs_{variant}"] = rounds
    children = [child for row in rows for round_row in row["rounds"] for child in round_row["children"]]
    hashes_ok = all(file_hash(run / "inputs" / name) == entry["sha256"] for name, entry in summary["inputs"].items())
    return {"run": str(run), "all_execution_valid": summary["all_execution_valid"],
            "all_array_checks_pass": all(all(value.values()) for value in checks.values()), "array_checks": checks,
            "input_hashes_valid": hashes_ok, "lineages": rows, "comparisons": comparisons,
            "maximum_recovery_distance": max(child["recovery"]["final_distance"] for child in children),
            "maximum_ion_hold_drift": max(child["ion_hold_drift"] for child in children),
            "minimum_retained_label_late_fraction": min(hold["late_label_fractions"][child["retained_label"]] for child in children for hold in child["holds"]),
            "fresh_targets": len(children), "integration_calls": len(audits), "snapshots": sum(audit["samples"] for audit in audits),
            "elapsed_seconds": summary["elapsed_seconds"], "total_cpu_seconds": sum(audit["cpu_seconds"] for audit in audits)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    try:
        report = analyze(args.run.resolve())
    except ValueError as error:
        parser.error(str(error))
    if args.compact:
        report["failed_checks"] = {name: [key for key, passed in checks.items() if not passed]
                                   for name, checks in report.pop("array_checks").items() if not all(checks.values())}
        report["lineages"] = [{"id": row["case"]["id"], "all_rounds_transmitted": row["all_rounds_transmitted"],
                               "rounds": [{"round": item["round"], "incoming": item["incoming_labels"], "outgoing": item["outgoing_labels"],
                                           "success": item["round_success"]} for item in row["rounds"]]} for row in report["lineages"]]
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report["all_array_checks_pass"] and report["input_hashes_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
