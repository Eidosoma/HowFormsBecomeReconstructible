"""Audit brief-cue rewriting and explicitly reused historical benchmarks."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_group_transfer import arrays
from analyze_lineage_return import audit_exposure, source_inputs
from analyze_renewal import audit_round
from memory_metrics import REGULATORS, classify, opposite
from run_onward_transfer import file_hash


def reconstruct_writing(exposure, rounds, state, threshold):
    """Compose endpoints from independently reconstructed per-cell records."""
    contacts = [c["contact_label"] for c in exposure["carriers"]]
    holds = [h for c in exposure["carriers"] for h in c["holds"]]
    acquired = contacts == [state, state]
    post = len(contacts) == 2 and all(len(c["holds"]) == 2 for c in exposure["carriers"]) and len(holds) == 4 and all(h["recipient_label"] == state and h["late_label_fractions"][state] >= threshold for h in holds)
    onward = len(rounds) == 2 and all(r["round_success"] for r in rounds)
    durable = post and onward
    return {"contact_acquired": bool(acquired), "postcue_state_written": bool(post), "new_state_transmitted": bool(onward),
        "durable_rewrite": bool(durable), "prompt_rewrite": bool(durable and acquired), "delayed_rewrite": bool(durable and not acquired)}


def panel_summary(branches, durations):
    result = {}
    for origin in ("E", "M"):
        rows = []
        for duration in durations:
            matching = [b for b in branches if b["case"]["origin_state"] == origin and b["cue_duration"] == duration]
            by_condition = {b["case"]["condition"]: b for b in matching if not b["case"].get("fine", False)}
            pulse = by_condition["pulse"]
            fine = next(b for b in matching if b["case"].get("fine", False))
            outcomes = {c: by_condition[c]["outcomes"]["durable_rewrite"] for c in ("pulse", "blocked", "same", "alone")}
            rows.append({"duration": duration, "historical_reuse": pulse["historical_reuse"],
                "contact_labels": [c["contact_label"] for c in pulse["exposure"]["carriers"]],
                "held_labels": [c["holds"][-1]["recipient_label"] for c in pulse["exposure"]["carriers"]],
                "outgoing_labels": [r["outgoing_labels"] for r in pulse["rounds"]],
                "pulse_outcomes": pulse["outcomes"], "durable_outcomes": outcomes,
                "all_controls_negative": not any(outcomes[c] for c in ("blocked", "same", "alone")),
                "fine_outcomes_agree": pulse["outcomes"] == fine["outcomes"]})
        successes = [r["duration"] for r in rows if r["pulse_outcomes"]["durable_rewrite"]]
        failures = [r["duration"] for r in rows if not r["pulse_outcomes"]["durable_rewrite"]]
        first = min(successes) if successes else None
        lower_failures = [t for t in failures if first is not None and t < first]
        result[origin + "_to_" + opposite(origin) + "_to_" + origin] = {
            "durations": rows, "tested_successes": successes, "tested_failures": failures,
            "smallest_tested_success": first, "largest_tested_failure_below_it": max(lower_failures) if lower_failures else None,
            "observed_nonmonotonicity": any(f > s for s in successes for f in failures),
            "exact_minimum_or_global_monotonicity_established": False}
    return result


def analyze(run):
    summary = json.loads((run / "summary.json").read_text())
    if not summary.get("all_execution_valid"):
        raise ValueError("Require a completed valid suite")
    config, inputs = summary["config"], run / "inputs"
    refs = arrays(inputs / "references.npz")
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    reg = [indices[n] for n in REGULATORS]
    scales = np.abs(refs["later"][reg, 0] - refs["later"][reg, 1])
    checks, branches, audits, endpoints = {}, [], [], {}
    for case in config["cases"]:
        effective = {**config, "cue_horizon": case["cue_duration"]}  # Independent of runner's effective_config.
        folder = run / case["id"]
        packet, ids, seen, exposure, ec, ea, contact = audit_exposure(folder / "exposure", inputs, effective, case, refs["prepared"], indices)
        checks[case["id"] + "/exposure"] = ec
        audits.extend(ea)
        start, old_ids, initial_seen = packet.copy(), ids.copy(), len(seen)
        endpoints[(case["id"], "contact")] = contact
        endpoints[(case["id"], "after_holds")] = packet
        fresh = refs["prepared"][:, {"E": 0, "M": 1}[case["old_state"]], None]
        rounds = []
        for n in config["continuing_rounds"]:
            end, row, rc, pa = audit_round(folder / f"round_{n:02}", effective, case, n, packet, ids, seen, fresh, refs["later"], indices)
            packet, ids = end["outgoing_packet"], [c["id"] for c in row["children"]]
            seen.update(ids)
            rounds.append(row)
            audits.extend(pa)
            checks[f"{case['id']}/round_{n:02}"] = rc
            endpoints[(case["id"], str(n))] = packet
        outcomes = reconstruct_writing(exposure, rounds, case["state"], config["late_label_fraction"])
        saved, result = arrays(folder / "endpoints.npz"), json.loads((folder / "result.json").read_text())
        original, _, _, expected_source, _ = source_inputs(inputs, effective, case, indices)
        duration = 2 * config["contact_horizon"] + sum(config["retention_horizons"])
        start_time = config["source_nominal_time"] + case["cue_duration"] + sum(config["cue_holds"])
        schedule = [{"round": n, "start": start_time + i * duration, "end": start_time + (i + 1) * duration} for i, n in enumerate(config["continuing_rounds"])]
        checks[case["id"]] = {
            "case_record_correct": result["case"] == case and result["execution_pass"] and result["ion_indices"] == indices,
            "source_record_correct": result["source"] == expected_source == json.loads((folder / "source.json").read_text()),
            "original_saved": np.array_equal(saved["source_packet"], original),
            "exact_held_incumbents_seed_relay": np.array_equal(saved["continuing_start"], start),
            "fresh_target_saved": np.array_equal(saved["fresh_target"], fresh),
            "recipient_opposes_target": classify(fresh, indices).tolist() == [opposite(case["state"])] == [case["old_state"]],
            "final_packet_saved": np.array_equal(saved["final_packet"], packet),
            "final_ids_match": result["final_ids"] == ids and not (set(ids) & set(old_ids)),
            "four_fresh_recipients_excludes_cues": result["distinct_fresh_targets"] == len(seen) - initial_seen == 4,
            "cue_count_matches": result["cue_instances"] == exposure["cue_instances"],
            "exposure_record_matches": result["exposure"] == json.loads((folder / "exposure/result.json").read_text()),
            "all_six_outcomes_recomputed": all(result[k] == v for k, v in outcomes.items()),
            "legacy_strict_switch_unchanged": result["retained_switch"] == exposure["retained_switch"] and outcomes["prompt_rewrite"] == (exposure["retained_switch"] and outcomes["new_state_transmitted"]),
            "effective_duration_correct": result["effective_cue_horizon"] == case["cue_duration"] and case["cue_duration"] in config["cue_durations"],
            "nominal_schedule_correct": result["nominal_schedule"] == schedule,
        }
        branches.append({"case": case, "cue_duration": case["cue_duration"], "historical_reuse": False,
                         "exposure": exposure, "rounds": rounds, "outcomes": outcomes})
    prior = json.loads((run / "predecessor_audit.json").read_text())
    old_summary = json.loads((inputs / "previous_summary.json").read_text())
    expected_ids = {origin.lower() + "_to_" + opposite(origin).lower() + "_to_" + origin.lower() + "_" + condition
                    for origin in ("E", "M") for condition in ("pulse", "blocked", "same", "alone", "pulse_fine")}
    checks["historical_benchmark"] = {
        "all_prior_checks_passed": prior["all_array_checks_pass"] and all(all(c.values()) for c in prior["array_checks"].values()),
        "exact_ten_case_benchmark": len(prior["branches"]) == 10 and {b["case"]["id"] for b in prior["branches"]} == expected_ids,
        "benchmark_duration_1000": old_summary["config"]["cue_horizon"] == config["benchmark_cue_duration"] == 1000,
        "same_source_bank_hashes": all(old_summary["inputs"][k]["sha256"] == v["sha256"] for k, v in summary["inputs"].items() if k != "previous_summary.json"),
        "same_source_generation_and_clock": all(old_summary["config"][k] == config[k] for k in ("source_round", "source_nominal_time", "continuing_rounds")),
        "benchmark_not_counted_as_new": len(branches) == 20 and all(not b["historical_reuse"] and b["cue_duration"] != 1000 for b in branches),
    }
    benchmarks = []
    for b in prior["branches"]:
        outcome = reconstruct_writing(b["exposure"], b["rounds"], b["case"]["state"], config["late_label_fraction"])
        checks["historical_benchmark"][b["case"]["id"] + "_strict_consistency"] = outcome["prompt_rewrite"] == b["renewed_return"]
        benchmarks.append(dict(b, cue_duration=1000, historical_reuse=True, outcomes=outcome))
    fine = {}
    for baseline in [b for b in branches if b["case"]["condition"] == "pulse" and not b["case"].get("fine", False)]:
        name = baseline["case"]["id"]
        precise = next(b for b in branches if b["case"]["id"] == name + "_fine")
        distances = []
        for stage in ("contact", "after_holds", "4", "5"):
            a, b = endpoints[(name, stage)], endpoints[(name + "_fine", stage)]
            distances.append({"stage": stage, "same_labels": bool(np.array_equal(classify(a, indices), classify(b, indices))),
                "regulatory_distance": float(np.max(np.abs(a[reg] - b[reg]) / scales[:, None])),
                "full_state_max_abs_difference": float(np.max(np.abs(a - b)))})
        fine[name] = {"same_outcomes": baseline["outcomes"] == precise["outcomes"], "endpoints": distances}
    children = [c for b in branches for r in b["rounds"] for c in r["children"]]
    carriers = [c for b in branches for c in b["exposure"]["carriers"]]
    return {"run": str(run), "all_array_checks_pass": all(all(c.values()) for c in checks.values()),
        "array_checks": checks, "array_check_count": sum(len(c) for c in checks.values()),
        "input_hashes_valid": all(file_hash(inputs / n) == v["sha256"] for n, v in summary["inputs"].items()),
        "frozen_hashes_valid": all(file_hash(run / "frozen" / n) == h for n, h in summary["frozen_hashes_sha256"].items()),
        "predecessor_audit_hash_valid": file_hash(run / "predecessor_audit.json") == summary["predecessor_audit_sha256"],
        "new_branches": branches, "historical_benchmarks": benchmarks,
        "duration_panel": panel_summary(branches + benchmarks, config["cue_durations"] + [config["benchmark_cue_duration"]]),
        "fine_comparisons": fine, "historical_fine_comparisons": prior["fine_comparisons"],
        "new_fresh_targets": len(children), "new_cue_instances": sum(b["exposure"]["cue_instances"] for b in branches),
        "new_integrations": len(audits), "new_snapshots": sum(a["samples"] for a in audits),
        "all_new_recipients_locally_recovered": all(c["recovery"]["recovered"] for c in children),
        "maximum_new_recovery_distance": max(c["recovery"]["final_distance"] for c in children),
        "maximum_new_ion_hold_drift": max(c["ion_hold_drift"] for c in children + carriers),
        "elapsed_seconds": summary["elapsed_seconds"], "new_integration_cpu_seconds": sum(a["cpu_seconds"] for a in audits)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    report = analyze(args.run.resolve())
    if args.compact:
        report["failed_checks"] = {k: [n for n, v in c.items() if not v] for k, c in report.pop("array_checks").items() if not all(c.values())}
        for key in ("new_branches", "historical_benchmarks"):
            report[key] = [{"id": b["case"]["id"], "duration": b["cue_duration"], "historical_reuse": b["historical_reuse"],
                **b["outcomes"], "outgoing": [r["outgoing_labels"] for r in b["rounds"]]} for b in report[key]]
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if all(report[k] for k in ("all_array_checks_pass", "input_hashes_valid", "frozen_hashes_valid", "predecessor_audit_hash_valid")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
