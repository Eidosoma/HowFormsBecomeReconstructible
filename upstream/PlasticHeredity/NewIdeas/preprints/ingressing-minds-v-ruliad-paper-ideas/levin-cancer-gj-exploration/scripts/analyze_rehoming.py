"""Independent source/polarity audit and alternative-state renewal outcomes."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_erasure_rescue import audit_intervention
from analyze_group_transfer import arrays
from analyze_renewal import audit_round
from memory_metrics import REGULATORS, classify, opposite
from run_onward_transfer import file_hash


def audit_source(folder, inputs, config, case, later, indices):
    condition = case["condition"]
    # Independent source selection, not the runner's source_spec/load_source.
    if condition == "ordinary":
        stem, key = case["state"].lower() + "_ordinary", "outgoing_packet"
    else:
        stem = case["old_state"].lower() + ("_sham" if condition == "sham" else "_overwrite")
        key = "after_2"
    original = arrays(inputs / (stem + ".npz"))[key]
    meta = json.loads((inputs / (stem + ".json")).read_text())
    ids = meta["outgoing_ids"]
    prefix = meta if condition == "ordinary" else json.loads((inputs / (case["old_state"].lower() + "_prefix.json")).read_text())
    seen = set(prefix["incoming_ids"] + ids)
    saved = arrays(folder / "endpoints.npz")
    record = json.loads((folder / "source.json").read_text())
    expected_label = case["old_state"] if condition == "sham" else case["state"]
    checks = {
        "exact_source_checkpoint": np.array_equal(saved["source_packet"], original),
        "correct_source_selection": (record["packet_file"], record["metadata_file"], record["key"]) == (stem + ".npz", stem + ".json", key),
        "unchanged_carrier_ids": record["incoming_ids"] == record["outgoing_ids"] == ids == prefix["outgoing_ids"],
        "valid_source_identity_ledger": len(ids) == len(set(ids)) == 2 and len(seen) == 4,
        "source_polarity": "".join(classify(original, indices)) == record["source_labels"] == expected_label * 2,
        "no_new_reference_edits_declared": record["new_reference_edits"] == 0,
        "correct_wait_count": record["extra_waits"] == (2 if condition == "ordinary" else 0),
        "source_finite_nonnegative": original.shape == (17, 2) and np.isfinite(original).all() and (original >= 0).all(),
    }
    stages, audits = [], []
    if condition == "ordinary":
        packet, stages, wait_checks, audits = audit_intervention(folder / "ordinary_wait", config,
            dict(case, intervention="sham"), original, ids, later, indices)
        checks.update({"ordinary/" + k: v for k, v in wait_checks.items()})
    else:
        packet = original
        checks["no_new_wait_directory"] = not (folder / "ordinary_wait").exists()
    checks["exact_actual_start_enters_relay"] = np.array_equal(saved["continuing_start"], packet)
    checks["relay_start_label_recomputed"] = record["relay_start_labels"] == "".join(classify(packet, indices))
    row = {"source_labels": "".join(classify(original, indices)), "relay_start_labels": "".join(classify(packet, indices)),
           "ordinary_wait_stages": stages}
    return packet, ids, seen, row, {k: bool(v) for k, v in checks.items()}, audits


def analyze(run):
    summary = json.loads((run / "summary.json").read_text())
    if not summary.get("all_execution_valid"):
        raise ValueError("Require a completed, valid suite")
    config, inputs = summary["config"], run / "inputs"
    refs = arrays(inputs / "references.npz")
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    reg = [indices[n] for n in REGULATORS]
    scales = np.abs(refs["later"][reg, 0] - refs["later"][reg, 1])
    checks, branches, audits, endpoints = {}, [], [], {}
    for case in config["cases"]:
        folder = run / case["id"]
        packet, ids, seen, source, sc, sa = audit_source(folder, inputs, config, case, refs["later"], indices)
        checks[case["id"] + "/source"] = sc
        audits.extend(sa)
        start, start_ids = packet.copy(), ids.copy()
        fresh = refs["prepared"][:, {"E": 0, "M": 1}[case["old_state"]], None]
        rounds = []
        for number in config["continuing_rounds"]:
            end, row, rc, pa = audit_round(folder / f"round_{number:02}", config, case, number, packet, ids, seen,
                                           fresh, refs["later"], indices)
            packet, ids = end["outgoing_packet"], [c["id"] for c in row["children"]]
            seen.update(ids)
            rounds.append(row)
            audits.extend(pa)
            checks[f"{case['id']}/round_{number:02}"] = rc
            endpoints[(case["id"], number)] = packet
        result, saved = json.loads((folder / "result.json").read_text()), arrays(folder / "endpoints.npz")
        transmitted = all(r["round_success"] for r in rounds)
        duration = 2 * config["contact_horizon"] + sum(config["retention_horizons"])
        offset = 2 * config["intervention_horizon"]
        schedule = [{"round": n, "start": (n - 1) * duration + offset, "end": n * duration + offset} for n in config["continuing_rounds"]]
        checks[case["id"]] = {
            "valid_case_record": result["execution_pass"] and result["case"] == case and result["ion_indices"] == indices,
            "source_record_matches": result["source"] == json.loads((folder / "source.json").read_text()),
            "same_actual_start_saved": np.array_equal(saved["continuing_start"], start),
            "final_packet_saved": np.array_equal(saved["final_packet"], packet),
            "fresh_target_saved": np.array_equal(saved["fresh_target"], fresh),
            "recipient_opposes_new_target": classify(fresh, indices).tolist() == [opposite(case["state"])] == [case["old_state"]],
            "all_outcomes_recomputed": result["new_state_transmitted"] == transmitted,
            "four_fresh_targets": result["distinct_fresh_targets"] == len(seen) - 4 == 4,
            "final_ids_match": result["final_ids"] == ids and not (set(ids) & set(start_ids)),
            "nominal_clock_correct": result["nominal_schedule"] == schedule}
        branches.append({"case": case, "source": source, "rounds": rounds, "new_state_transmitted": transmitted})
    by_id = {b["case"]["id"]: b for b in branches}
    fine, contrasts, historical = {}, {}, {}
    prior = json.loads((run / "predecessor_audit.json").read_text())["erasure"]
    for old in ("E", "M"):
        direction = old.lower() + "_to_" + opposite(old).lower()
        base, precise = direction + "_rehomed", direction + "_rehomed_fine"
        distances = []
        for number in config["continuing_rounds"]:
            a, b = endpoints[(base, number)], endpoints[(precise, number)]
            distances.append({"round": number, "same_labels": bool(np.array_equal(classify(a, indices), classify(b, indices))),
                "regulatory_distance": float(np.max(np.abs(a[reg] - b[reg]) / scales[:, None])),
                "full_state_max_abs_difference": float(np.max(np.abs(a - b)))})
        fine[direction] = {"same_transfer_outcome": by_id[base]["new_state_transmitted"] == by_id[precise]["new_state_transmitted"],
                           "endpoints": distances}
        outcomes = {kind: by_id[direction + "_" + kind]["new_state_transmitted"] for kind in ("rehomed", "blocked", "sham", "ordinary")}
        contrasts[direction] = {"new_state": opposite(old), "outcomes": outcomes,
            "primary_active_vs_controls_contrast": outcomes["rehomed"] and not outcomes["blocked"] and not outcomes["sham"],
            "ordinary_benchmark_works": outcomes["ordinary"],
            "fine_outcome_agrees": fine[direction]["same_transfer_outcome"]}
        key = old.lower() + "_overwrite"
        old_top = json.loads((inputs / ("historical_" + key + ".json")).read_text())
        old_end = arrays(inputs / ("historical_" + key + ".npz"))
        old_audit = next(b for b in prior["branches"] if b["case"]["id"] == key)
        checks[direction + "/historical"] = {
            "same_overwritten_packet_in_old_assay": np.array_equal(old_end["continuing_start"], arrays(run / base / "endpoints.npz")["continuing_start"]),
            "old_outcome_matches_reaudit": old_top["all_rounds_transmitted"] == old_audit["all_rounds_transmitted"],
            "old_assay_target_was_original_state": old_top["case"]["state"] == old and old_top["case"]["intervention"] == "overwrite",
            "old_recipients_already_had_new_state": classify(old_end["fresh_target"], indices).tolist() == [opposite(old)]}
        historical[direction] = {"old_target_transmitted_in_previous_assay": old_audit["all_rounds_transmitted"],
            "new_target_transmitted_now": outcomes["rehomed"], "recipient_states_differ_between_assays": True}
    children = [c for b in branches for r in b["rounds"] for c in r["children"]]
    return {"run": str(run), "all_execution_valid": True, "all_array_checks_pass": all(all(c.values()) for c in checks.values()),
        "array_checks": checks, "array_check_count": sum(len(c) for c in checks.values()),
        "input_hashes_valid": all(file_hash(inputs / n) == v["sha256"] for n, v in summary["inputs"].items()),
        "frozen_hashes_valid": all(file_hash(run / "frozen" / n) == h for n, h in summary["frozen_hashes_sha256"].items()),
        "predecessor_audit_hash_valid": file_hash(run / "predecessor_audit.json") == summary["predecessor_audit_sha256"],
        "branches": branches, "contrasts": contrasts, "fine_comparisons": fine, "historical_comparisons": historical,
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
        report["failed_checks"] = {k: [n for n, v in c.items() if not v] for k, c in report.pop("array_checks").items() if not all(c.values())}
        report["branches"] = [{"id": b["case"]["id"], "source": b["source"]["relay_start_labels"],
            "new_state_transmitted": b["new_state_transmitted"], "outgoing": [r["outgoing_labels"] for r in b["rounds"]]} for b in report["branches"]]
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if all(report[k] for k in ("all_array_checks_pass", "input_hashes_valid", "frozen_hashes_valid", "predecessor_audit_hash_valid")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
