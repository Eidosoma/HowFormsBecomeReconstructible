"""Independent fractional-edit audit and descriptive fixed-grid outcomes."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_group_transfer import arrays
from analyze_renewal import audit_round
from memory_metrics import REGULATORS, classify
from run_onward_transfer import file_hash


def grid_summary(rows):
    """Describe sampled outcomes without asserting an unobserved threshold."""
    fractions = [r["fraction"] for r in rows]
    if sorted(fractions) != [0, .25, .5, .75, 1]:
        raise ValueError("Require all five distinct fixed fractions")
    ordered = sorted(rows, key=lambda r: r["fraction"])
    success = [r["fraction"] for r in ordered if r["relay_rescued"]]
    return {"smallest_tested_success": min(success, default=None), "successful_tested_fractions": success,
        "sampled_outcomes_monotone": all(not a["relay_rescued"] or b["relay_rescued"] for a, b in zip(ordered, ordered[1:])),
        "adjacent_failure_success_samples": [[a["fraction"], b["fraction"]] for a, b in zip(ordered, ordered[1:])
                                             if not a["relay_rescued"] and b["relay_rescued"]],
        "rows": ordered}


def audit_intervention(folder, config, case, erased, ids, later, indices):
    saved = arrays(folder / "endpoints.npz")
    result = json.loads((folder / "result.json").read_text())
    names, fraction = case["targets"], case["fraction"]
    allowed = ((REGULATORS[0], REGULATORS[2]), REGULATORS[1:])
    if isinstance(fraction, bool) or not np.isfinite(fraction) or not 0 <= fraction <= 1 or not ((not names and fraction == 0) or tuple(names) in allowed):
        raise ValueError("Invalid pair/fraction")
    selected = [indices[n] for n in names]
    untouched = [i for i in range(17) if i not in selected]
    reg = [indices[n] for n in REGULATORS]
    expected = erased.copy()
    # Reconstruct directly from frozen inputs, not via the runner's helper.
    if fraction == 1:
        expected[selected] = later[selected, 0, None]
    elif fraction != 0:
        expected[selected] = (1 - fraction) * erased[selected] + fraction * later[selected, 0, None]
    before, edited, after = (saved[k] for k in ("before", "edited", "after_wait"))
    before_labels, immediate, final_labels = ["".join(classify(a, indices)) for a in (before, edited, after)]
    checks = {
        "actual_post_erasure_input": np.array_equal(before, erased),
        "exact_fractional_edit": np.array_equal(edited, expected),
        "all_unselected_rows_preserved": np.array_equal(edited[untouched], before[untouched]),
        "fraction_matches": result["fraction"] == fraction,
        "same_carrier_ids": result["incoming_ids"] == ids == result["outgoing_ids"],
        "targets_match": result["target_names"] == names,
        "no_sustained_forcing_declared": result["sustained_forcing"] is False,
        "labels_recomputed": (result["before_labels"], result["immediate_labels"], result["after_wait_labels"]) == (before_labels, immediate, final_labels),
        "correct_pair_shapes": all(a.shape == (17, 2) for a in saved.values()),
        "packets_finite_nonnegative": all(np.isfinite(a).all() and (a >= 0).all() for a in saved.values()),
        "two_isolated_setups": len(result["setups"]) == 2 and all(s["cells"] == 1 and s["edges"] == 0 and s["miRNA_kd"] == 0 and not s["active"] for s in result["setups"])}
    fractions = []
    for cell in (1, 2):
        name = f"cell_{cell}_wait"
        phase = arrays(folder / f"{name}.npz")
        audit = next(a for a in result["audits"] if a["phase"] == name)
        column = slice(cell - 1, cell)
        sampled = classify(phase["concentrations"], indices)[:, 0]
        late = sampled[phase["times"] >= config["intervention_horizon"] * .75]
        frac = {label: float(np.mean(late == label)) for label in ("E", "M", "X")}
        fractions.append(frac)
        checks.update({name + "_primary_start_matches": np.array_equal(phase["initial"][:8], edited[:8, column]),
            name + "_final_matches_packet": np.array_equal(phase["final"], after[:, column]),
            name + "_finite_nonnegative": all(np.isfinite(a).all() and (a >= 0).all() for a in phase.values()),
            name + "_times_increase": bool(np.all(np.diff(phase["times"]) > 0)),
            name + "_late_fractions_match": frac == audit["late_label_fractions"],
            name + "_native_label_matches": audit["all_labels"] == "".join(classify(phase["final"], indices)),
            name + "_isolated_fixed_wait": audit["graph_edges"] == 0 and audit["miRNA_kd"] == 0 and audit["requested_horizon"] == config["intervention_horizon"]})
    rescued = final_labels == "EE" and all(f["E"] >= config["late_label_fraction"] for f in fractions)
    checks["carrier_rescue_recomputed"] = rescued == result["carrier_rescued"]
    row = {"before_labels": before_labels, "immediate_labels": immediate, "after_wait_labels": final_labels,
        "carrier_rescued": rescued, "immediate_E_label_lost": immediate == "EE" and final_labels != "EE", "late_fractions": fractions,
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
    meta = json.loads((run / "inputs/e_prefix.json").read_text())
    erased = arrays(run / "inputs/e_erased.npz")["after_1"]
    reg = [indices[n] for n in REGULATORS]
    scales = np.abs(refs["later"][reg, 0] - refs["later"][reg, 1])
    fresh = refs["prepared"][:, 1, None]
    checks, branches, audits, endpoints = {}, [], [], {}
    for case in config["cases"]:
        folder = run / case["id"]
        ids = meta["outgoing_ids"]
        seen = set(meta["incoming_ids"] + ids)
        packet, intervention, stage_checks, stage_audits = audit_intervention(folder / "intervention", config, case, erased, ids, refs["later"], indices)
        checks[case["id"] + "/intervention"] = stage_checks
        audits.extend(stage_audits)
        start, rounds = packet.copy(), []
        endpoints[(case["id"], "after_wait")] = start
        for number in config["continuing_rounds"]:
            end, row, rc, pa = audit_round(folder / f"round_{number:02}", config, case, number, packet, ids, seen, fresh, refs["later"], indices)
            packet, ids = end["outgoing_packet"], [c["id"] for c in row["children"]]
            seen.update(ids)
            rounds.append(row)
            audits.extend(pa)
            checks[f"{case['id']}/round_{number:02}"] = rc
            endpoints[(case["id"], number)] = packet
        saved, result = arrays(folder / "endpoints.npz"), json.loads((folder / "result.json").read_text())
        transmitted = all(r["round_success"] for r in rounds)
        rescued = intervention["carrier_rescued"] and transmitted
        duration = 2 * config["contact_horizon"] + sum(config["retention_horizons"])
        offset = config["inherited_wait"] + config["intervention_horizon"]
        schedule = [{"round": n, "start": (n - 1) * duration + offset, "end": n * duration + offset} for n in config["continuing_rounds"]]
        checks[case["id"]] = {"valid_case_record": result["execution_pass"] and result["case"] == case and result["ion_indices"] == indices,
            "erased_input_saved": np.array_equal(saved["erased_input"], erased),
            "actual_post_wait_start_saved": np.array_equal(saved["continuing_start"], start),
            "final_packet_saved": np.array_equal(saved["final_packet"], packet),
            "fresh_target_saved": np.array_equal(saved["fresh_target"], fresh),
            "transmission_recomputed": result["all_rounds_transmitted"] == transmitted,
            "combined_rescue_recomputed": result["relay_rescued"] == rescued,
            "new_target_count": result["distinct_fresh_targets"] == len(seen) - 4 == 4,
            "final_ids_match": result["final_ids"] == ids, "nominal_clock_correct": result["nominal_schedule"] == schedule}
        branches.append({"case": case, "intervention": intervention, "rounds": rounds,
                         "all_rounds_transmitted": transmitted, "relay_rescued": rescued})
    previous = json.loads((run / "inputs/previous_summary.json").read_text())
    predecessor = json.loads((run / "predecessor_audit.json").read_text())
    shared = ("revision", "packet_size", "continuing_rounds", "intervention_horizon", "inherited_wait", "write_kd", "contact_horizon",
        "retention_horizons", "recovery_horizon", "perturbation_fraction", "late_label_fraction", "minimum_challenge_distance",
        "recovery_absolute_tolerance", "recovery_distance_ratio")
    checks["historical_comparison"] = {"identical_shared_parameters": all(config[k] == previous["config"][k] for k in shared),
        "identical_references": file_hash(run / "inputs/references.npz") == previous["inputs"]["references.npz"]["sha256"]}
    by_id = {b["case"]["id"]: b for b in branches}
    historical = {}
    for old_key, new_key in (("e_none", "e_none"), ("e_mir_prot", "e_mir_prot_100"), ("e_mrna_prot", "e_mrna_prot_100")):
        old = json.loads((run / "inputs" / f"previous_{old_key}.json").read_text())
        old_end = arrays(run / "inputs" / f"previous_{old_key}.npz")
        old_audit = next(b for b in predecessor["branches"] if b["case"]["id"] == old_key)
        checks["historical_comparison"][old_key + "_identical_erased_input"] = np.array_equal(old_end["erased_input"], erased)
        checks["historical_comparison"][old_key + "_outcome_matches_reaudit"] = old["relay_rescued"] == old_audit["relay_rescued"]
        historical[old_key] = {"same_rescue_outcome": by_id[new_key]["relay_rescued"] == old_audit["relay_rescued"],
            "post_wait_full_state_max_abs_difference": float(np.max(np.abs(endpoints[(new_key, "after_wait")] - old_end["continuing_start"])))}
    grids = {}
    for pair in ("e_mir_prot", "e_mrna_prot"):
        members = [by_id["e_none"]] + [by_id[f"{pair}_{n:03}"] for n in (25, 50, 75, 100)]
        grids[pair] = grid_summary([{"fraction": b["case"]["fraction"], "id": b["case"]["id"],
            "immediate": b["intervention"]["immediate_labels"], "after_wait": b["intervention"]["after_wait_labels"],
            "carrier_rescued": b["intervention"]["carrier_rescued"], "relay_rescued": b["relay_rescued"]} for b in members])
    comparisons = {}
    for case in config["cases"]:
        if not case.get("fine"):
            continue
        base = case["id"].removesuffix("_fine")
        rows = []
        for stage in ("after_wait", 2, 3):
            a, b = [endpoints[(key, stage)] for key in (base, case["id"])]
            rows.append({"stage": stage, "same_labels": bool(np.array_equal(classify(a, indices), classify(b, indices))),
                "regulatory_distance": float(np.max(np.abs(a[reg] - b[reg]) / scales[:, None])),
                "full_state_max_abs_difference": float(np.max(np.abs(a - b)))})
        comparisons[base] = {"same_carrier_rescue": by_id[base]["intervention"]["carrier_rescued"] == by_id[case["id"]]["intervention"]["carrier_rescued"],
            "same_relay_rescue": by_id[base]["relay_rescued"] == by_id[case["id"]]["relay_rescued"], "endpoints": rows}
    children = [c for b in branches for r in b["rounds"] for c in r["children"]]
    return {"run": str(run), "all_execution_valid": True, "all_array_checks_pass": all(all(c.values()) for c in checks.values()),
        "array_checks": checks, "array_check_count": sum(len(c) for c in checks.values()),
        "input_hashes_valid": all(file_hash(run / "inputs" / n) == v["sha256"] for n, v in summary["inputs"].items()),
        "frozen_hashes_valid": all(file_hash(run / "frozen" / n) == v for n, v in summary["frozen_hashes_sha256"].items()),
        "predecessor_audit_hash_valid": file_hash(run / "predecessor_audit.json") == summary["predecessor_audit_sha256"],
        "branches": branches, "grids": grids, "fine_comparisons": comparisons, "historical_controls": historical,
        "fresh_targets": len(children), "integration_calls": len(audits), "snapshots": sum(a["samples"] for a in audits),
        "all_recipients_locally_recovered": all(c["recovery"]["recovered"] for c in children),
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
        report["branches"] = [{"id": b["case"]["id"], "fraction": b["case"]["fraction"], "immediate": b["intervention"]["immediate_labels"],
            "after_wait": b["intervention"]["after_wait_labels"], "carrier_rescued": b["intervention"]["carrier_rescued"],
            "relay_rescued": b["relay_rescued"], "round_outputs": [r["outgoing_labels"] for r in b["rounds"]]} for b in report["branches"]]
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if all(report[k] for k in ("all_array_checks_pass", "input_hashes_valid", "frozen_hashes_valid", "predecessor_audit_hash_valid")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
