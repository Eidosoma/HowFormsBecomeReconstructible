"""Reconstruct overwrite/rescue edits and audit subsequent relay continuity."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_group_transfer import arrays
from analyze_renewal import audit_round
from memory_metrics import REGULATORS, classify, opposite
from run_onward_transfer import file_hash


def audit_intervention(folder, config, case, prefix, ids, later, indices):
    saved = arrays(folder / "endpoints.npz")
    result = json.loads((folder / "result.json").read_text())
    reg = [indices[name] for name in REGULATORS]
    nonreg = [i for i in range(17) if i not in reg]
    # Deliberately reconstruct interventions here without the runner's edit helper.
    kind, desired = case["intervention"], case["state"]
    anchors = [None if kind == "sham" else opposite(desired),
               desired if kind == "rescue" else opposite(desired) if kind == "wrong" else None]
    packet, checks, stages = prefix, {}, []
    checks["same_prefix_packet"] = np.array_equal(saved["prefix_packet"], prefix)
    checks["no_cell_replacement_during_intervention"] = result["incoming_ids"] == ids == result["outgoing_ids"]
    checks["nominal_wait_offset"] = result["nominal_extra_duration"] == 2 * config["intervention_horizon"]
    checks["all_intervention_setups_isolated"] = len(result["setups"]) == 4 and all(
        s["cells"] == 1 and s["edges"] == 0 and s["miRNA_kd"] == 0 and not s["active"] for s in result["setups"])
    for stage, anchor in enumerate(anchors, 1):
        before, edited, after = [saved[f"{name}_{stage}"] for name in ("before", "edited", "after")]
        expected = packet.copy()
        if anchor is not None:
            expected[reg] = later[reg, {"E": 0, "M": 1}[anchor], None]
        tag = f"stage_{stage}_"
        checks[tag + "actual_previous_state"] = np.array_equal(before, packet)
        checks[tag + "exact_reference_edit"] = np.array_equal(edited, expected)
        checks[tag + "no_nonregulatory_restoration"] = np.array_equal(edited[nonreg], before[nonreg])
        checks[tag + "recorded_anchor_correct"] = result["stages"][stage - 1]["anchor"] == anchor
        late_fractions = []
        for cell in (1, 2):
            phase_name = f"stage_{stage}_cell_{cell}"
            phase = arrays(folder / f"{phase_name}.npz")
            audit = next(row for row in result["audits"] if row["phase"] == phase_name)
            column = slice(cell - 1, cell)
            ptag = phase_name + "_"
            checks[ptag + "primary_start_matches_edit"] = np.array_equal(phase["initial"][:8], edited[:8, column])
            checks[ptag + "saved_final_matches"] = np.array_equal(phase["final"], after[:, column])
            checks[ptag + "finite_nonnegative"] = all(np.isfinite(a).all() and (a >= 0).all() for a in phase.values())
            checks[ptag + "sample_times_increase"] = bool(np.all(np.diff(phase["times"]) > 0))
            labels = classify(phase["concentrations"], indices)[:, 0]
            late = labels[phase["times"] >= config["intervention_horizon"] * .75]
            fractions = {label: float(np.mean(late == label)) for label in ("E", "M", "X")}
            checks[ptag + "late_fractions_recomputed"] = fractions == audit["late_label_fractions"]
            checks[ptag + "native_label_matches"] = audit["all_labels"] == "".join(classify(phase["final"], indices))
            checks[ptag + "isolated_fixed_wait"] = audit["graph_edges"] == 0 and audit["miRNA_kd"] == 0 and audit["requested_horizon"] == config["intervention_horizon"]
            late_fractions.append(fractions)
        labels_after = "".join(classify(after, indices))
        checks[tag + "post_wait_labels_recomputed"] = labels_after == result["stages"][stage - 1]["labels_after_wait"]
        stages.append({"anchor": anchor, "before_labels": "".join(classify(before, indices)),
                       "after_wait_labels": labels_after, "late_fractions": late_fractions,
                       "nonregulatory_change_during_wait": float(np.max(np.abs(after[nonreg] - before[nonreg])))})
        packet = after
    checks["saved_intervention_packet_shapes"] = all(a.shape == (17, 2) for a in saved.values())
    checks["saved_intervention_packets_valid"] = all(np.isfinite(a).all() and (a >= 0).all() for a in saved.values())
    return packet, stages, {k: bool(v) for k, v in checks.items()}, result["audits"]


def analyze(run):
    summary = json.loads((run / "summary.json").read_text())
    if not summary.get("all_execution_valid"):
        raise ValueError("Require a completed, numerically valid suite")
    config = summary["config"]
    refs = arrays(run / "inputs/references.npz")
    indices = json.loads((run / "inputs/reference.json").read_text())["ion_indices"]
    reg = [indices[name] for name in REGULATORS]
    scales = np.abs(refs["later"][reg, 0] - refs["later"][reg, 1])
    checks, branches, audits, endpoints = {}, [], [], {}
    for case in config["cases"]:
        stem, folder = case["state"].lower(), run / case["id"]
        prefix = arrays(run / "inputs" / f"{stem}_prefix.npz")["outgoing_packet"]
        metadata = json.loads((run / "inputs" / f"{stem}_prefix.json").read_text())
        ids = metadata["outgoing_ids"]
        seen = set(metadata["incoming_ids"] + ids)
        packet, stages, stage_checks, stage_audits = audit_intervention(
            folder / "intervention", config, case, prefix, ids, refs["later"], indices)
        start = packet.copy()
        checks[case["id"] + "/intervention"] = stage_checks
        audits.extend(stage_audits)
        rounds = []
        for number in config["continuing_rounds"]:
            end, row, round_checks, phase_audits = audit_round(folder / f"round_{number:02}", config, case,
                number, packet, ids, seen, refs["prepared"][:, {"E": 0, "M": 1}[opposite(case["state"])], None], refs["later"], indices)
            packet, ids = end["outgoing_packet"], [child["id"] for child in row["children"]]
            seen.update(ids)
            rounds.append(row)
            audits.extend(phase_audits)
            checks[f"{case['id']}/round_{number:02}"] = round_checks
            endpoints[(case["id"], number)] = end
        saved, result = arrays(folder / "endpoints.npz"), json.loads((folder / "result.json").read_text())
        success = all(row["round_success"] for row in rounds)
        duration = 2 * config["contact_horizon"] + sum(config["retention_horizons"])
        offset = 2 * config["intervention_horizon"]
        schedule = [{"round": n, "start": (n - 1) * duration + offset, "end": n * duration + offset} for n in config["continuing_rounds"]]
        checks[case["id"]] = {
            "valid_record": result["execution_pass"] and result["case"] == case and result["ion_indices"] == indices,
            "prefix_checkpoint_saved": np.array_equal(saved["prefix_packet"], prefix),
            "post_intervention_state_enters_lineage": np.array_equal(saved["continuing_start"], start),
            "final_packet_matches": np.array_equal(saved["final_packet"], packet),
            "fresh_target_matches": np.array_equal(saved["fresh_target"], refs["prepared"][:, {"E": 0, "M": 1}[opposite(case["state"])], None]),
            "all_round_outcomes_recomputed": result["all_rounds_transmitted"] == success,
            "new_targets_count": result["distinct_fresh_targets"] == len(seen) - 4 == 4,
            "final_ids_match": result["final_ids"] == ids,
            "nominal_clock_includes_waits": result["nominal_schedule_with_intervention"] == schedule}
        branches.append({"case": case, "prefix_labels": "".join(classify(prefix, indices)),
                         "stages": stages, "rounds": rounds, "all_rounds_transmitted": success})
    comparisons = {}
    for stem in ("e", "m"):
        for kind in ("overwrite", "rescue"):
            name = f"{stem}_{kind}"
            rows = []
            for number in config["continuing_rounds"]:
                a, b = [endpoints[(key, number)]["outgoing_packet"] for key in (name, name + "_fine")]
                rows.append({"round": number, "regulatory_distance": float(np.max(np.abs(a[reg] - b[reg]) / scales[:, None])),
                    "full_state_max_abs_difference": float(np.max(np.abs(a - b))),
                    "same_labels": bool(np.array_equal(classify(a, indices), classify(b, indices)))})
            comparisons[name] = rows
    children = [child for branch in branches for row in branch["rounds"] for child in row["children"]]
    return {"run": str(run), "all_execution_valid": True,
        "all_array_checks_pass": all(all(c.values()) for c in checks.values()), "array_checks": checks,
        "input_hashes_valid": all(file_hash(run / "inputs" / name) == entry["sha256"] for name, entry in summary["inputs"].items()),
        "frozen_hashes_valid": all(file_hash(run / "frozen" / name) == digest for name, digest in summary["frozen_hashes_sha256"].items()),
        "predecessor_audit_hash_valid": file_hash(run / "predecessor_audit.json") == summary["predecessor_audit_sha256"],
        "branches": branches, "fine_comparisons": comparisons,
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
    report["array_check_count"] = sum(len(c) for c in report["array_checks"].values())
    if args.compact:
        report["failed_checks"] = {name: [key for key, passed in checks.items() if not passed]
            for name, checks in report.pop("array_checks").items() if not all(checks.values())}
        report["branches"] = [{"id": row["case"]["id"], "prefix": row["prefix_labels"],
            "after_first_wait": row["stages"][0]["after_wait_labels"], "after_second_wait": row["stages"][1]["after_wait_labels"],
            "rounds": [{"round": r["round"], "outgoing": r["outgoing_labels"], "success": r["round_success"]} for r in row["rounds"]]}
            for row in report["branches"]]
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if all(report[key] for key in ("all_array_checks_pass", "input_hashes_valid", "frozen_hashes_valid", "predecessor_audit_hash_valid")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
