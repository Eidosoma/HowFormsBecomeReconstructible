"""Independent intervention reconstruction and saved-array relay audit."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_group_transfer import arrays
from analyze_renewal import audit_round
from memory_metrics import REGULATORS, classify, opposite
from run_onward_transfer import file_hash


def audit_rescue(folder, config, case, erased, ids, later, indices):
    saved = arrays(folder / "endpoints.npz")
    result = json.loads((folder / "result.json").read_text())
    reg = [indices[n] for n in REGULATORS]
    # Do not use the runner's selector or edit function to reconstruct the edit.
    names = [] if case["target"] == "none" else list(REGULATORS) if case["target"] == "all" else [case["target"]]
    if any(n not in REGULATORS for n in names):
        raise ValueError("Unknown intervention")
    selected = [indices[n] for n in names]
    untouched = [i for i in range(17) if i not in selected]
    expected = erased.copy()
    for index in selected:
        expected[index] = later[index, {"E": 0, "M": 1}[case["state"]]]
    before, edited, after = (saved[k] for k in ("before", "edited", "after_wait"))
    before_labels, immediate, after_labels = ["".join(classify(a, indices)) for a in (before, edited, after)]
    checks = {
        "actual_post_erasure_input": np.array_equal(before, erased),
        "exact_selected_reference_edit": np.array_equal(edited, expected),
        "every_untouched_row_preserved": np.array_equal(edited[untouched], before[untouched]),
        "same_carrier_ids": result["incoming_ids"] == ids == result["outgoing_ids"],
        "correct_target_record": result["target_names"] == names,
        "no_sustained_forcing_declared": result["sustained_forcing"] is False,
        "labels_recomputed": (result["before_labels"], result["immediate_labels"], result["after_wait_labels"]) == (before_labels, immediate, after_labels),
        "pair_shapes": all(a.shape == (17, 2) for a in saved.values()),
        "packets_finite_nonnegative": all(np.isfinite(a).all() and (a >= 0).all() for a in saved.values()),
        "two_isolated_setups": len(result["setups"]) == 2 and all(s["cells"] == 1 and s["edges"] == 0 and s["miRNA_kd"] == 0 and not s["active"] for s in result["setups"])}
    fractions = []
    for cell in (1, 2):
        phase_name = f"cell_{cell}_wait"
        phase = arrays(folder / f"{phase_name}.npz")
        audit = next(a for a in result["audits"] if a["phase"] == phase_name)
        column = slice(cell - 1, cell)
        tag = phase_name + "_"
        labels = classify(phase["concentrations"], indices)[:, 0]
        late = labels[phase["times"] >= config["intervention_horizon"] * .75]
        frac = {label: float(np.mean(late == label)) for label in ("E", "M", "X")}
        fractions.append(frac)
        checks.update({
            tag + "primary_start_matches_edit": np.array_equal(phase["initial"][:8], edited[:8, column]),
            tag + "final_matches_packet": np.array_equal(phase["final"], after[:, column]),
            tag + "finite_nonnegative": all(np.isfinite(a).all() and (a >= 0).all() for a in phase.values()),
            tag + "times_increase": bool(np.all(np.diff(phase["times"]) > 0)),
            tag + "late_fractions_recomputed": frac == audit["late_label_fractions"],
            tag + "native_label_matches": audit["all_labels"] == "".join(classify(phase["final"], indices)),
            tag + "isolated_fixed_wait": audit["graph_edges"] == 0 and audit["miRNA_kd"] == 0 and audit["requested_horizon"] == config["intervention_horizon"]})
    recovered = after_labels == case["state"] * 2 and all(f[case["state"]] >= config["late_label_fraction"] for f in fractions)
    checks["carrier_recovery_recomputed"] = recovered == result["carrier_rescued"]
    scales = np.abs(later[reg, 0] - later[reg, 1])
    distances = {label: float(np.max(np.abs(after[reg] - later[reg, col, None]) / scales[:, None])) for label, col in (("E", 0), ("M", 1))}
    row = {"before_labels": before_labels, "immediate_labels": immediate, "after_wait_labels": after_labels,
        "carrier_rescued": recovered, "immediate_desired_label_lost": immediate == case["state"] * 2 and after_labels != immediate,
        "late_fractions": fractions, "after_wait_distances_to_anchors": distances,
        "regulators_before": before[reg].tolist(), "regulators_edited": edited[reg].tolist(), "regulators_after_wait": after[reg].tolist(),
        "ion_change_at_edit": float(np.max(np.abs(edited[:4] - before[:4])))}
    return after, row, {k: bool(v) for k, v in checks.items()}, result["audits"]


def analyze(run):
    summary = json.loads((run / "summary.json").read_text())
    if not summary.get("all_execution_valid"):
        raise ValueError("Require a completed, numerically valid suite")
    config = summary["config"]
    refs = arrays(run / "inputs/references.npz")
    indices = json.loads((run / "inputs/reference.json").read_text())["ion_indices"]
    reg = [indices[n] for n in REGULATORS]
    scales = np.abs(refs["later"][reg, 0] - refs["later"][reg, 1])
    checks, branches, audits, endpoints = {}, [], [], {}
    for case in config["cases"]:
        stem, folder = case["state"].lower(), run / case["id"]
        erased = arrays(run / "inputs" / f"{stem}_erased.npz")["after_1"]
        meta = json.loads((run / "inputs" / f"{stem}_prefix.json").read_text())
        ids = meta["outgoing_ids"]
        seen = set(meta["incoming_ids"] + ids)
        packet, intervention, stage_checks, stage_audits = audit_rescue(folder / "intervention", config, case, erased, ids, refs["later"], indices)
        checks[case["id"] + "/intervention"] = stage_checks
        audits.extend(stage_audits)
        start, rounds = packet.copy(), []
        endpoints[(case["id"], "after_wait")] = start
        fresh = refs["prepared"][:, {"E": 0, "M": 1}[opposite(case["state"])], None]
        for number in config["continuing_rounds"]:
            end, row, round_checks, phase_audits = audit_round(folder / f"round_{number:02}", config, case, number,
                packet, ids, seen, fresh, refs["later"], indices)
            packet, ids = end["outgoing_packet"], [c["id"] for c in row["children"]]
            seen.update(ids)
            rounds.append(row)
            audits.extend(phase_audits)
            checks[f"{case['id']}/round_{number:02}"] = round_checks
            endpoints[(case["id"], number)] = packet
        saved = arrays(folder / "endpoints.npz")
        result = json.loads((folder / "result.json").read_text())
        transmitted = all(r["round_success"] for r in rounds)
        rescued = intervention["carrier_rescued"] and transmitted
        duration = 2 * config["contact_horizon"] + sum(config["retention_horizons"])
        offset = config["inherited_wait"] + config["intervention_horizon"]
        schedule = [{"round": n, "start": (n - 1) * duration + offset, "end": n * duration + offset} for n in config["continuing_rounds"]]
        checks[case["id"]] = {
            "valid_record": result["execution_pass"] and result["case"] == case and result["ion_indices"] == indices,
            "erased_input_saved": np.array_equal(saved["erased_input"], erased),
            "post_wait_start_saved": np.array_equal(saved["continuing_start"], start),
            "final_packet_saved": np.array_equal(saved["final_packet"], packet),
            "fresh_target_saved": np.array_equal(saved["fresh_target"], fresh),
            "transmission_recomputed": result["all_rounds_transmitted"] == transmitted,
            "combined_rescue_recomputed": result["relay_rescued"] == rescued,
            "new_target_count": result["distinct_fresh_targets"] == len(seen) - 4 == 4,
            "final_ids_match": result["final_ids"] == ids,
            "nominal_clock_correct": result["nominal_schedule"] == schedule}
        branches.append({"case": case, "intervention": intervention, "rounds": rounds,
                         "all_rounds_transmitted": transmitted, "relay_rescued": rescued})
    fine_comparisons, historical = {}, {}
    for case in config["cases"]:
        name, target = case["id"], case["target"]
        if case.get("fine"):
            continue
        if target in REGULATORS:
            records = []
            for stage in ("after_wait", 2, 3):
                a, b = [endpoints[(key, stage)] for key in (name, name + "_fine")]
                records.append({"stage": stage, "same_labels": bool(np.array_equal(classify(a, indices), classify(b, indices))),
                    "regulatory_distance": float(np.max(np.abs(a[reg] - b[reg]) / scales[:, None])),
                    "full_state_max_abs_difference": float(np.max(np.abs(a - b)))})
            fine_comparisons[name] = records
        else:
            source = "erased" if target == "none" else "full"
            old = arrays(run / "inputs" / f"{case['state'].lower()}_{source}.npz")["after_2"]
            new = endpoints[(name, "after_wait")]
            historical[name] = {"same_labels": bool(np.array_equal(classify(old, indices), classify(new, indices))),
                                "post_wait_full_state_max_abs_difference": float(np.max(np.abs(old - new)))}
    children = [c for b in branches for r in b["rounds"] for c in r["children"]]
    controls = {s: {"no_edit_rescued": next(b["relay_rescued"] for b in branches if b["case"]["state"] == s and b["case"]["target"] == "none"),
                    "full_reset_rescued": next(b["relay_rescued"] for b in branches if b["case"]["state"] == s and b["case"]["target"] == "all")} for s in ("E", "M")}
    return {"run": str(run), "all_execution_valid": True, "all_array_checks_pass": all(all(c.values()) for c in checks.values()),
        "array_checks": checks, "array_check_count": sum(len(c) for c in checks.values()),
        "input_hashes_valid": all(file_hash(run / "inputs" / name) == entry["sha256"] for name, entry in summary["inputs"].items()),
        "frozen_hashes_valid": all(file_hash(run / "frozen" / name) == digest for name, digest in summary["frozen_hashes_sha256"].items()),
        "predecessor_audit_hash_valid": file_hash(run / "predecessor_audit.json") == summary["predecessor_audit_sha256"],
        "branches": branches, "controls": controls, "fine_comparisons": fine_comparisons, "historical_controls": historical,
        "fresh_targets": len(children), "integration_calls": len(audits), "snapshots": sum(a["samples"] for a in audits),
        "maximum_recovery_distance": max(c["recovery"]["final_distance"] for c in children),
        "maximum_ion_hold_drift": max(c["ion_hold_drift"] for c in children),
        "minimum_retained_label_late_fraction": min(h["late_label_fractions"][c["retained_label"]] for c in children for h in c["holds"]),
        "elapsed_seconds": summary["elapsed_seconds"], "total_cpu_seconds": sum(a["cpu_seconds"] for a in audits)}


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
        report["failed_checks"] = {name: [k for k, v in c.items() if not v] for name, c in report.pop("array_checks").items() if not all(c.values())}
        report["branches"] = [{"id": b["case"]["id"], "immediate": b["intervention"]["immediate_labels"],
            "after_wait": b["intervention"]["after_wait_labels"], "carrier_rescued": b["intervention"]["carrier_rescued"],
            "relay_rescued": b["relay_rescued"], "round_outputs": [r["outgoing_labels"] for r in b["rounds"]]} for b in report["branches"]]
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if all(report[k] for k in ("all_array_checks_pass", "input_hashes_valid", "frozen_hashes_valid", "predecessor_audit_hash_valid")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
