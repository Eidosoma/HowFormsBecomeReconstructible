"""Independent pair-edit audit and fixed-reference E subset comparison."""

import argparse
from itertools import combinations
import json
from pathlib import Path

import numpy as np

from analyze_group_transfer import arrays
from analyze_renewal import audit_round
from memory_metrics import REGULATORS, classify
from run_onward_transfer import file_hash


def minimal_successes(records):
    """Inclusion-minimal successful subsets within a complete fixed comparison."""
    expected = {frozenset(c) for n in range(4) for c in combinations(REGULATORS, n)}
    subsets = [frozenset(r["targets"]) for r in records]
    if len(subsets) != 8 or set(subsets) != expected or any(len(r["targets"]) != len(s) for r, s in zip(records, subsets)):
        raise ValueError("Require all eight distinct regulator subsets")
    success = [s for s, r in zip(subsets, records) if r["relay_rescued"]]
    minimal = [s for s in success if not any(other < s for other in success)]
    return [list(n for n in REGULATORS if n in s) for s in sorted(minimal, key=lambda s: (len(s), sorted(s)))]


def audit_rescue(folder, config, case, erased, ids, later, indices):
    saved = arrays(folder / "endpoints.npz")
    result = json.loads((folder / "result.json").read_text())
    names = case["targets"]
    if len(names) not in (0, 2, 3) or len(set(names)) != len(names) or any(n not in REGULATORS for n in names):
        raise ValueError("Invalid targets")
    reg = [indices[n] for n in REGULATORS]
    selected = [indices[n] for n in names]
    untouched = [i for i in range(17) if i not in selected]
    # Independent reconstruction; do not call the runner's edit helper.
    expected = erased.copy()
    if selected:
        expected[selected, :] = later[selected, 0, None]
    before, edited, after = (saved[k] for k in ("before", "edited", "after_wait"))
    before_labels, immediate, final_labels = ["".join(classify(a, indices)) for a in (before, edited, after)]
    checks = {
        "actual_post_erasure_input": np.array_equal(before, erased),
        "exact_selected_E_reference_edit": np.array_equal(edited, expected),
        "all_unselected_rows_preserved": np.array_equal(edited[untouched], before[untouched]),
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
        labels = classify(phase["concentrations"], indices)[:, 0]
        late = labels[phase["times"] >= config["intervention_horizon"] * .75]
        frac = {label: float(np.mean(late == label)) for label in ("E", "M", "X")}
        fractions.append(frac)
        checks.update({
            name + "_primary_start_matches": np.array_equal(phase["initial"][:8], edited[:8, column]),
            name + "_final_matches_packet": np.array_equal(phase["final"], after[:, column]),
            name + "_finite_nonnegative": all(np.isfinite(a).all() and (a >= 0).all() for a in phase.values()),
            name + "_times_increase": bool(np.all(np.diff(phase["times"]) > 0)),
            name + "_late_fractions_match": frac == audit["late_label_fractions"],
            name + "_native_label_matches": audit["all_labels"] == "".join(classify(phase["final"], indices)),
            name + "_isolated_fixed_wait": audit["graph_edges"] == 0 and audit["miRNA_kd"] == 0 and audit["requested_horizon"] == config["intervention_horizon"]})
    rescued = final_labels == "EE" and all(f["E"] >= config["late_label_fraction"] for f in fractions)
    checks["carrier_rescue_recomputed"] = rescued == result["carrier_rescued"]
    scales = np.abs(later[reg, 0] - later[reg, 1])
    row = {"before_labels": before_labels, "immediate_labels": immediate, "after_wait_labels": final_labels,
        "carrier_rescued": rescued, "immediate_E_label_lost": immediate == "EE" and final_labels != "EE",
        "late_fractions": fractions, "regulators_before": before[reg].tolist(), "regulators_edited": edited[reg].tolist(),
        "regulators_after_wait": after[reg].tolist(), "ion_change_at_edit": float(np.max(np.abs(edited[:4] - before[:4]))),
        "after_wait_distances_to_anchors": {label: float(np.max(np.abs(after[reg] - later[reg, i, None]) / scales[:, None])) for label, i in (("E", 0), ("M", 1))}}
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
        packet, intervention, stage_checks, stage_audits = audit_rescue(folder / "intervention", config, case, erased, ids, refs["later"], indices)
        checks[case["id"] + "/intervention"] = stage_checks
        audits.extend(stage_audits)
        start, rounds = packet.copy(), []
        endpoints[(case["id"], "after_wait")] = start
        for number in config["continuing_rounds"]:
            end, row, round_checks, phase_audits = audit_round(folder / f"round_{number:02}", config, case, number,
                packet, ids, seen, fresh, refs["later"], indices)
            packet, ids = end["outgoing_packet"], [c["id"] for c in row["children"]]
            seen.update(ids)
            rounds.append(row)
            audits.extend(phase_audits)
            checks[f"{case['id']}/round_{number:02}"] = round_checks
            endpoints[(case["id"], number)] = packet
        saved, result = arrays(folder / "endpoints.npz"), json.loads((folder / "result.json").read_text())
        transmitted = all(r["round_success"] for r in rounds)
        rescued = intervention["carrier_rescued"] and transmitted
        duration = 2 * config["contact_horizon"] + sum(config["retention_horizons"])
        offset = config["inherited_wait"] + config["intervention_horizon"]
        schedule = [{"round": n, "start": (n - 1) * duration + offset, "end": n * duration + offset} for n in config["continuing_rounds"]]
        checks[case["id"]] = {
            "valid_case_record": result["execution_pass"] and result["case"] == case and result["ion_indices"] == indices,
            "erased_input_saved": np.array_equal(saved["erased_input"], erased),
            "actual_post_wait_start_saved": np.array_equal(saved["continuing_start"], start),
            "final_packet_saved": np.array_equal(saved["final_packet"], packet),
            "fresh_target_saved": np.array_equal(saved["fresh_target"], fresh),
            "transmission_recomputed": result["all_rounds_transmitted"] == transmitted,
            "combined_rescue_recomputed": result["relay_rescued"] == rescued,
            "new_target_count": result["distinct_fresh_targets"] == len(seen) - 4 == 4,
            "final_ids_match": result["final_ids"] == ids,
            "nominal_clock_correct": result["nominal_schedule"] == schedule}
        branches.append({"case": case, "intervention": intervention, "rounds": rounds,
                         "all_rounds_transmitted": transmitted, "relay_rescued": rescued})
    previous = json.loads((run / "inputs/previous_summary.json").read_text())
    predecessor = json.loads((run / "predecessor_audit.json").read_text())
    shared = ("revision", "packet_size", "continuing_rounds", "intervention_horizon", "inherited_wait", "write_kd",
        "contact_horizon", "retention_horizons", "recovery_horizon", "perturbation_fraction", "late_label_fraction",
        "minimum_challenge_distance", "recovery_absolute_tolerance", "recovery_distance_ratio")
    checks["historical_comparison"] = {"identical_shared_parameters": all(config[k] == previous["config"][k] for k in shared),
        "identical_references": file_hash(run / "inputs/references.npz") == previous["inputs"]["references.npz"]["sha256"]}
    subset_rows, historical = [], {}
    for kind, names in (("none", []), ("all", list(REGULATORS)), ("mir", [REGULATORS[0]]), ("mrna", [REGULATORS[1]]), ("prot", [REGULATORS[2]])):
        old = json.loads((run / "inputs" / f"previous_e_{kind}.json").read_text())
        old_end = arrays(run / "inputs" / f"previous_e_{kind}.npz")
        old_audit = next(b for b in predecessor["branches"] if b["case"]["id"] == "e_" + kind)
        checks["historical_comparison"][kind + "_identical_erased_input"] = np.array_equal(old_end["erased_input"], erased)
        checks["historical_comparison"][kind + "_outcome_matches_reaudit"] = old["relay_rescued"] == old_audit["relay_rescued"]
        if kind in ("none", "all"):
            new = endpoints[("e_" + kind, "after_wait")]
            historical[kind] = {"same_labels": bool(np.array_equal(classify(new, indices), classify(old_end["continuing_start"], indices))),
                "post_wait_full_state_max_abs_difference": float(np.max(np.abs(new - old_end["continuing_start"])))}
        else:
            subset_rows.append({"targets": names, "relay_rescued": old_audit["relay_rescued"], "source": "re-audited previous single-regulator run"})
    for b in branches:
        if not b["case"].get("fine"):
            subset_rows.append({"targets": b["case"]["targets"], "relay_rescued": b["relay_rescued"], "source": "current pair/control run"})
    minimal = minimal_successes(subset_rows)
    comparisons = {}
    for case in config["cases"]:
        if len(case["targets"]) != 2 or case.get("fine"):
            continue
        rows = []
        for stage in ("after_wait", 2, 3):
            a, b = [endpoints[(key, stage)] for key in (case["id"], case["id"] + "_fine")]
            rows.append({"stage": stage, "same_labels": bool(np.array_equal(classify(a, indices), classify(b, indices))),
                "regulatory_distance": float(np.max(np.abs(a[reg] - b[reg]) / scales[:, None])),
                "full_state_max_abs_difference": float(np.max(np.abs(a - b)))})
        comparisons[case["id"]] = rows
    children = [c for b in branches for r in b["rounds"] for c in r["children"]]
    return {"run": str(run), "all_execution_valid": True, "all_array_checks_pass": all(all(c.values()) for c in checks.values()),
        "array_checks": checks, "array_check_count": sum(len(c) for c in checks.values()),
        "input_hashes_valid": all(file_hash(run / "inputs" / n) == v["sha256"] for n, v in summary["inputs"].items()),
        "frozen_hashes_valid": all(file_hash(run / "frozen" / n) == v for n, v in summary["frozen_hashes_sha256"].items()),
        "predecessor_audit_hash_valid": file_hash(run / "predecessor_audit.json") == summary["predecessor_audit_sha256"],
        "branches": branches, "fine_comparisons": comparisons, "historical_controls": historical,
        "restricted_subset_outcomes": subset_rows, "restricted_minimal_successes": minimal,
        "restricted_minimum_successful_count": min((len(s) for s in minimal), default=None),
        "controls": {"no_edit_rescued": next(b["relay_rescued"] for b in branches if b["case"]["id"] == "e_none"),
                     "full_reset_rescued": next(b["relay_rescued"] for b in branches if b["case"]["id"] == "e_all")},
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
