"""Independent two-stage preparation audit and finite-relay sensitivity panel."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_fractional_rescue import audit_intervention
from analyze_group_transfer import arrays
from analyze_renewal import audit_round
from memory_metrics import REGULATORS, classify
from run_onward_transfer import file_hash


def audit_background(folder, inputs, config, case, original, indices):
    saved = arrays(folder / "background.npz")
    record = json.loads((folder / "background.json").read_text())
    prepared = folder / "prepared_inputs"
    factors = np.asarray(config["backgrounds"][case["background"]])
    reg = [indices[n] for n in REGULATORS]
    other = [i for i in range(17) if i not in reg]
    expected = original.copy()
    # Deliberately independent of the preparation helper.
    for coordinate, row in enumerate(reg):
        for cell in (0, 1):
            expected[row, cell] = original[row, cell] * factors[coordinate, cell]
    varied = saved["varied_start"]
    before = arrays(prepared / "e_erased.npz")["after_1"]
    hashes = record["prepared_hashes_sha256"]
    checks = {"unmodified_original_source": np.array_equal(saved["original_erased"], original),
        "exact_background_preparation": np.array_equal(varied, expected),
        "exact_factors_saved": np.array_equal(saved["factors"], factors) and record["factors"] == factors.tolist(),
        "all_nonregulatory_rows_preserved": np.array_equal(varied[other], original[other]),
        "prepared_input_equals_varied_start": np.array_equal(before, varied),
        "correct_background_record": record["background"] == case["background"] and record["extra_relaxation_horizon"] == 0,
        "both_labels_still_M": "".join(classify(varied, indices)) == record["varied_labels"] == "MM",
        "original_labels_match": "".join(classify(original, indices)) == record["original_labels"],
        "background_shapes": varied.shape == original.shape == (17, 2) and saved["factors"].shape == (3, 2),
        "finite_nonnegative_preparation": all(np.isfinite(a).all() and (a >= 0).all() for a in saved.values()),
        "prepared_file_set": set(hashes) == {"references.npz", "reference.json", "e_prefix.json", "e_erased.npz"},
        "derived_inputs_unchanged": record["prepared_inputs_unchanged"] and all(file_hash(prepared / n) == h for n, h in hashes.items()),
        "background_file_unchanged": file_hash(folder / "background.npz") == record["background_sha256"],
        "references_and_ids_copied_exactly": all(file_hash(prepared / n) == file_hash(inputs / n) for n in ("references.npz", "reference.json", "e_prefix.json"))}
    row = {"name": case["background"], "factors": factors.tolist(), "original_regulators": original[reg].tolist(),
        "varied_regulators": varied[reg].tolist(), "carrier_regulators_differ": not np.array_equal(varied[reg, 0], varied[reg, 1]),
        "largest_relative_preparation_change": float(np.max(np.abs(varied[reg] / original[reg] - 1)))}
    return varied, row, {k: bool(v) for k, v in checks.items()}


def analyze(run):
    summary = json.loads((run / "summary.json").read_text())
    if not summary.get("all_execution_valid"):
        raise ValueError("Require a completed, numerically valid suite")
    config, inputs = summary["config"], run / "inputs"
    refs = arrays(inputs / "references.npz")
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    meta = json.loads((inputs / "e_prefix.json").read_text())
    original = arrays(inputs / "e_erased.npz")["after_1"]
    reg = [indices[n] for n in REGULATORS]
    scales = np.abs(refs["later"][reg, 0] - refs["later"][reg, 1])
    fresh = refs["prepared"][:, 1, None]
    checks, branches, audits, endpoints = {}, [], [], {}
    for case in config["cases"]:
        folder = run / case["id"]
        varied, background, bc = audit_background(folder, inputs, config, case, original, indices)
        checks[case["id"] + "/background"] = bc
        ids = meta["outgoing_ids"]
        seen = set(meta["incoming_ids"] + ids)
        packet, intervention, ic, ia = audit_intervention(folder / "intervention", config, case, varied, ids, refs["later"], indices)
        checks[case["id"] + "/intervention"] = ic
        audits.extend(ia)
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
            "varied_input_saved_in_legacy_field": np.array_equal(saved["erased_input"], varied),
            "actual_post_wait_start_saved": np.array_equal(saved["continuing_start"], start),
            "final_packet_saved": np.array_equal(saved["final_packet"], packet),
            "fresh_target_saved": np.array_equal(saved["fresh_target"], fresh),
            "transmission_recomputed": result["all_rounds_transmitted"] == transmitted,
            "combined_rescue_recomputed": result["relay_rescued"] == rescued,
            "new_target_count": result["distinct_fresh_targets"] == len(seen) - 4 == 4,
            "final_ids_match": result["final_ids"] == ids, "nominal_clock_correct": result["nominal_schedule"] == schedule}
        branches.append({"case": case, "background": background, "intervention": intervention, "rounds": rounds,
                         "all_rounds_transmitted": transmitted, "relay_rescued": rescued})
    previous = json.loads((inputs / "previous_summary.json").read_text())
    predecessor = json.loads((run / "predecessor_audit.json").read_text())
    shared = ("revision", "packet_size", "continuing_rounds", "intervention_horizon", "inherited_wait", "write_kd", "contact_horizon",
        "retention_horizons", "recovery_horizon", "perturbation_fraction", "late_label_fraction", "minimum_challenge_distance",
        "recovery_absolute_tolerance", "recovery_distance_ratio")
    checks["historical_comparison"] = {"identical_shared_parameters": all(config[k] == previous["config"][k] for k in shared),
        "identical_references": file_hash(inputs / "references.npz") == previous["inputs"]["references.npz"]["sha256"]}
    by_id = {b["case"]["id"]: b for b in branches}
    historical = {}
    for old_key, new_key in (("e_none", "original_000"), ("e_mir_prot_075", "original_075"), ("e_mir_prot_100", "original_100")):
        old = json.loads((inputs / f"previous_{old_key}.json").read_text())
        old_end = arrays(inputs / f"previous_{old_key}.npz")
        old_audit = next(b for b in predecessor["branches"] if b["case"]["id"] == old_key)
        checks["historical_comparison"][old_key + "_identical_erased_input"] = np.array_equal(old_end["erased_input"], original)
        checks["historical_comparison"][old_key + "_outcome_matches_reaudit"] = old["relay_rescued"] == old_audit["relay_rescued"]
        historical[old_key] = {"same_rescue_outcome": by_id[new_key]["relay_rescued"] == old_audit["relay_rescued"],
            "post_wait_full_state_max_abs_difference": float(np.max(np.abs(endpoints[(new_key, "after_wait")] - old_end["continuing_start"])))}
    comparisons, panel = {}, {}
    for background in config["backgrounds"]:
        rows = []
        for fraction, suffix in ((0, "000"), (.75, "075"), (1, "100")):
            b = by_id[background + "_" + suffix]
            rows.append({"fraction": fraction, "immediate": b["intervention"]["immediate_labels"],
                "after_wait": b["intervention"]["after_wait_labels"], "carrier_rescued": b["intervention"]["carrier_rescued"],
                "relay_rescued": b["relay_rescued"], "round_outputs": [r["outgoing_labels"] for r in b["rounds"]]})
        panel[background] = rows
        base, fine = background + "_075", background + "_075_fine"
        distances = []
        for stage in ("after_wait", 2, 3):
            a, b = endpoints[(base, stage)], endpoints[(fine, stage)]
            distances.append({"stage": stage, "same_labels": bool(np.array_equal(classify(a, indices), classify(b, indices))),
                "regulatory_distance": float(np.max(np.abs(a[reg] - b[reg]) / scales[:, None])),
                "full_state_max_abs_difference": float(np.max(np.abs(a - b)))})
        comparisons[background] = {"same_carrier_rescue": by_id[base]["intervention"]["carrier_rescued"] == by_id[fine]["intervention"]["carrier_rescued"],
            "same_relay_rescue": by_id[base]["relay_rescued"] == by_id[fine]["relay_rescued"], "endpoints": distances}
    children = [c for b in branches for r in b["rounds"] for c in r["children"]]
    return {"run": str(run), "all_execution_valid": True, "all_array_checks_pass": all(all(c.values()) for c in checks.values()),
        "array_checks": checks, "array_check_count": sum(len(c) for c in checks.values()),
        "input_hashes_valid": all(file_hash(inputs / n) == v["sha256"] for n, v in summary["inputs"].items()),
        "frozen_hashes_valid": all(file_hash(run / "frozen" / n) == v for n, v in summary["frozen_hashes_sha256"].items()),
        "predecessor_audit_hash_valid": file_hash(run / "predecessor_audit.json") == summary["predecessor_audit_sha256"],
        "branches": branches, "panel": panel, "fine_comparisons": comparisons, "historical_controls": historical,
        "all_tested_backgrounds_rescued_at_075": all(by_id[name + "_075"]["relay_rescued"] for name in config["backgrounds"]),
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
        report.pop("branches")
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if all(report[k] for k in ("all_array_checks_pass", "input_hashes_valid", "frozen_hashes_valid", "predecessor_audit_hash_valid")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
