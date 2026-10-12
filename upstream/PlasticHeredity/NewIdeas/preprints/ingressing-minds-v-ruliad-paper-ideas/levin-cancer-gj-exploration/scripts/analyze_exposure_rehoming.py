"""Independent saved-state audit of cue-driven switching and subsequent relay."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_group_transfer import arrays
from analyze_renewal import audit_round
from memory_metrics import REGULATORS, classify, opposite
from run_memory_probe import array_hash
from run_onward_transfer import file_hash


def audit_exposure(folder, inputs, config, case, prepared, indices):
    stem = case["old_state"].lower() + "_sham"
    source = arrays(inputs / (stem + ".npz"))["after_2"]
    meta = json.loads((inputs / (stem + ".json")).read_text())
    prefix = json.loads((inputs / (case["old_state"].lower() + "_prefix.json")).read_text())
    ids = meta["outgoing_ids"]
    prior_ids = set(prefix["incoming_ids"] + ids)
    saved, record = arrays(folder / "endpoints.npz"), json.loads((folder / "result.json").read_text())
    expected_cues = [] if case["condition"] == "alone" else [
        f"{case['id']}:cue:carrier_{i}:donor_{j}" for i in (1, 2) for j in range(1, config["cue_donors"] + 1)]
    old_top = json.loads((inputs / ("historical_" + stem + ".json")).read_text())
    old_arrays = arrays(inputs / ("historical_" + stem + ".npz"))
    checks = {
        "exact_intact_source": np.array_equal(saved["source_packet"], source),
        "valid_source_pair": source.shape == (17, 2) and np.isfinite(source).all() and (source >= 0).all(),
        "old_source_polarity": classify(source, indices).tolist() == [case["old_state"]] * 2,
        "incumbent_ids_preserved": record["incoming_ids"] == record["outgoing_ids"] == ids == prefix["outgoing_ids"],
        "prior_ids_valid": len(ids) == len(set(ids)) == 2 and len(prior_ids) == 4,
        "cue_ids_distinct_and_fixed": record["cue_ids"] == expected_cues and len(set(expected_cues)) == len(expected_cues) and not (set(expected_cues) & prior_ids),
        "no_reference_edits_declared": record["new_reference_edits"] == 0,
        "historical_old_assay_used_exact_pair": np.array_equal(old_arrays["continuing_start"], source),
        "historical_old_state_transmitted": old_top["case"]["state"] == case["old_state"] and old_top["case"]["intervention"] == "sham" and old_top["all_rounds_transmitted"],
        "six_phases_four_setups": len(record["audits"]) == 6 and len(record["setups"]) == 4,
        "all_onward_relays_active": case["history"] == "learned",
    }
    rows, packets, contacts, audits = [], [], [], []
    for i in (1, 2):
        tag = f"carrier_{i}"
        col = slice(i - 1, i)
        # Assemble independently: never call the runner's cue_group helper.
        count = 1 if case["condition"] == "alone" else config["cue_donors"] + 1
        expected = np.empty((source.shape[0], count))
        expected[:, 0] = source[:, i - 1]
        if count > 1:
            cue_label = case["old_state"] if case["condition"] == "same" else case["state"]
            expected[:, 1:] = prepared[:, {"E": 0, "M": 1}[cue_label], None]
        active = case["condition"] in ("pulse", "same")
        initial, contact, held = [saved[tag + suffix] for suffix in ("_initial", "_contact", "_held_first")]
        checkpoint = saved["continuing_packet"][:, col]
        cue, h1, h2 = [arrays(folder / (tag + "_" + stage + ".npz")) for stage in ("cue", "hold_1", "hold_2")]
        cue_setup, hold_setup = record["setups"][2 * (i - 1):2 * i]
        local = {
            "full_initial_assembly": np.array_equal(initial, expected),
            "actual_carrier_is_target_zero": np.array_equal(initial[:, :1], source[:, col]),
            "pre_refresh_full_state_hash": cue_setup["state_hash_before_derived_refresh"] == array_hash(expected),
            "cue_initial_primary_unchanged": np.array_equal(cue["initial"][:8], expected[:8]),
            "cue_star_correct": cue_setup["cells"] == count and cue_setup["edges_list"] == [[0, j] for j in range(1, count)] and cue_setup["edges"] == count - 1,
            "cue_transport_correct": cue_setup["active"] == active and cue_setup["miRNA_kd"] == (config["write_kd"] if active else 0),
            "contact_endpoint_matches": np.array_equal(cue["final"], contact),
            "only_original_carrier_survives_removal": hold_setup["state_hash_before_derived_refresh"] == array_hash(contact[:, :1]),
            "post_removal_isolation": hold_setup["cells"] == 1 and hold_setup["edges"] == 0 and hold_setup["edges_list"] == [] and hold_setup["miRNA_kd"] == 0 and not hold_setup["active"],
            "actual_target_enters_hold": np.array_equal(h1["initial"][:8], contact[:8, :1]),
            "first_hold_endpoint": np.array_equal(h1["final"], held),
            "holds_contiguous": np.array_equal(h2["initial"][:8], held[:8]),
            "actual_incumbent_enters_forward_pair": np.array_equal(h2["final"], checkpoint),
            "one_cell_holds": all(p["final"].shape == (17, 1) and p["concentrations"].shape[2] == 1 for p in (h1, h2)),
        }
        phase_rows = []
        for stage, phase, horizon in zip(("cue", "hold_1", "hold_2"), (cue, h1, h2), [config["cue_horizon"]] + config["cue_holds"]):
            pa = record["audits"][3 * (i - 1) + len(phase_rows)]
            labels = classify(phase["final"], indices)
            late = classify(phase["concentrations"], indices)[:, 0][phase["times"] >= .75 * horizon]
            fractions = {label: float(np.mean(late == label)) for label in ("E", "M", "X")}
            local[stage + "_metadata"] = pa["phase"] == tag + "_" + stage and pa["requested_horizon"] == horizon and pa["samples"] == len(phase["times"])
            local[stage + "_labels"] = pa["all_labels"] == "".join(labels) and pa["recipient_label"] == str(labels[0]) and pa["late_label_fractions"] == fractions
            local[stage + "_transport"] = pa["miRNA_kd"] == (config["write_kd"] if stage == "cue" and active else 0) and pa["graph_edges"] == (count - 1 if stage == "cue" else 0)
            local[stage + "_finite_nonnegative"] = all(np.isfinite(v).all() and (v >= 0).all() for v in phase.values())
            local[stage + "_sampling"] = len(late) > 0 and np.all(np.diff(phase["times"]) > 0)
            local[stage + "_snail_and_refresh"] = np.all(phase["final"][indices["snail"]] == 72) and np.array_equal(phase["raw_final"][:8], phase["final"][:8])
            phase_rows.append({"recipient_label": str(labels[0]), "late_label_fractions": fractions})
            audits.append(pa)
        switched = bool(phase_rows[0]["recipient_label"] == case["state"] and all(
            p["recipient_label"] == case["state"] and p["late_label_fractions"][case["state"]] >= config["late_label_fraction"] for p in phase_rows[1:]))
        row = {"id": ids[i - 1], "contact_label": phase_rows[0]["recipient_label"],
            "cue_end_labels": "".join(classify(contact, indices)[1:]), "holds": phase_rows[1:], "retained_switch": switched,
            "ion_hold_drift": float(np.max(np.abs(checkpoint[:4] - held[:4])))}
        stored = record["carriers"][i - 1]
        local["carrier_outcome_recomputed"] = all(stored[k] == v for k, v in row.items() if k != "holds")
        local["hold_records_match"] = stored["holds"] == record["audits"][3 * (i - 1) + 1:3 * i]
        checks.update({tag + "/" + k: bool(v) for k, v in local.items()})
        rows.append(row)
        packets.append(checkpoint)
        contacts.append(contact[:, :1])
    retained = all(r["retained_switch"] for r in rows)
    checks["pair_switch_recomputed"] = record["retained_switch"] == retained
    return np.concatenate(packets, axis=1), ids, prior_ids | set(expected_cues), {
        "carriers": rows, "retained_switch": retained, "cue_instances": len(expected_cues)}, {k: bool(v) for k, v in checks.items()}, audits, np.concatenate(contacts, axis=1)


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
        folder = run / case["id"]
        packet, ids, seen, exposure, ec, ea, contact = audit_exposure(folder / "exposure", inputs, config, case, refs["prepared"], indices)
        checks[case["id"] + "/exposure"] = ec
        audits.extend(ea)
        start, old_ids, initial_seen = packet.copy(), ids.copy(), len(seen)
        endpoints[(case["id"], "contact")] = contact
        endpoints[(case["id"], "after_holds")] = packet
        fresh = refs["prepared"][:, {"E": 0, "M": 1}[case["old_state"]], None]
        rounds = []
        for n in config["continuing_rounds"]:
            end, row, rc, pa = audit_round(folder / f"round_{n:02}", config, case, n, packet, ids, seen, fresh, refs["later"], indices)
            packet, ids = end["outgoing_packet"], [c["id"] for c in row["children"]]
            seen.update(ids)
            rounds.append(row)
            audits.extend(pa)
            checks[f"{case['id']}/round_{n:02}"] = rc
            endpoints[(case["id"], str(n))] = packet
        saved, result = arrays(folder / "endpoints.npz"), json.loads((folder / "result.json").read_text())
        source = json.loads((folder / "source.json").read_text())
        stem = case["old_state"].lower() + "_sham"
        original = arrays(inputs / (stem + ".npz"))["after_2"]
        transmitted = all(r["round_success"] for r in rounds)
        rehomed = transmitted and exposure["retained_switch"]
        duration = 2 * config["contact_horizon"] + sum(config["retention_horizons"])
        offset = config["inherited_wait"] + config["cue_horizon"] + sum(config["cue_holds"])
        schedule = [{"round": n, "start": (n - 1) * duration + offset, "end": n * duration + offset} for n in config["continuing_rounds"]]
        checks[case["id"]] = {
            "case_record_correct": result["case"] == case and result["execution_pass"] and result["ion_indices"] == indices,
            "source_record_correct": source == dict(packet_file=stem + ".npz", metadata_file=stem + ".json", key="after_2", incoming_ids=old_ids, outgoing_ids=old_ids, source_labels=case["old_state"] * 2) == result["source"],
            "original_saved": np.array_equal(saved["source_packet"], original),
            "exact_held_incumbents_seed_relay": np.array_equal(saved["continuing_start"], start),
            "fresh_target_saved": np.array_equal(saved["fresh_target"], fresh),
            "recipient_opposes_new_target": classify(fresh, indices).tolist() == [opposite(case["state"])] == [case["old_state"]],
            "final_packet_saved": np.array_equal(saved["final_packet"], packet),
            "final_ids_match": result["final_ids"] == ids and not (set(ids) & set(old_ids)),
            "four_new_recipients_excludes_cue_count": result["distinct_fresh_targets"] == len(seen) - initial_seen == 4,
            "cue_count_matches": result["cue_instances"] == exposure["cue_instances"],
            "exposure_record_matches": result["exposure"] == json.loads((folder / "exposure/result.json").read_text()),
            "three_outcomes_recomputed": result["retained_switch"] == exposure["retained_switch"] and result["new_state_transmitted"] == transmitted and result["exposure_rehomed"] == rehomed,
            "nominal_schedule_matches": result["nominal_schedule"] == schedule,
        }
        branches.append({"case": case, "exposure": exposure, "rounds": rounds, "new_state_transmitted": transmitted, "exposure_rehomed": rehomed})
    by_id = {b["case"]["id"]: b for b in branches}
    fine, contrasts = {}, {}
    for old in ("E", "M"):
        direction = old.lower() + "_to_" + opposite(old).lower()
        base, precise = direction + "_pulse", direction + "_pulse_fine"
        fine[direction] = {"same_rehoming_outcome": by_id[base]["exposure_rehomed"] == by_id[precise]["exposure_rehomed"], "endpoints": []}
        for stage in ("contact", "after_holds", "2", "3"):
            a, b = endpoints[(base, stage)], endpoints[(precise, stage)]
            fine[direction]["endpoints"].append({"stage": stage, "same_labels": bool(np.array_equal(classify(a, indices), classify(b, indices))),
                "regulatory_distance": float(np.max(np.abs(a[reg] - b[reg]) / scales[:, None])),
                "full_state_max_abs_difference": float(np.max(np.abs(a - b)))})
        outcomes = {c: by_id[direction + "_" + c]["exposure_rehomed"] for c in ("pulse", "blocked", "same", "alone")}
        contrasts[direction] = {"outcomes": outcomes, "pulse_vs_controls": outcomes["pulse"] and not any(outcomes[c] for c in ("blocked", "same", "alone"))}
    children = [c for b in branches for r in b["rounds"] for c in r["children"]]
    carriers = [c for b in branches for c in b["exposure"]["carriers"]]
    return {"run": str(run), "all_array_checks_pass": all(all(c.values()) for c in checks.values()),
        "array_checks": checks, "array_check_count": sum(len(c) for c in checks.values()),
        "input_hashes_valid": all(file_hash(inputs / n) == v["sha256"] for n, v in summary["inputs"].items()),
        "frozen_hashes_valid": all(file_hash(run / "frozen" / n) == h for n, h in summary["frozen_hashes_sha256"].items()),
        "predecessor_audit_hash_valid": file_hash(run / "predecessor_audit.json") == summary["predecessor_audit_sha256"],
        "branches": branches, "contrasts": contrasts, "fine_comparisons": fine,
        "fresh_targets": len(children), "cue_instances": sum(b["exposure"]["cue_instances"] for b in branches),
        "integration_calls": len(audits), "snapshots": sum(a["samples"] for a in audits),
        "all_recipients_locally_recovered": all(c["recovery"]["recovered"] for c in children),
        "maximum_recovery_distance": max(c["recovery"]["final_distance"] for c in children),
        "maximum_ion_hold_drift": max(c["ion_hold_drift"] for c in children + carriers),
        "elapsed_seconds": summary["elapsed_seconds"], "total_cpu_seconds": sum(a["cpu_seconds"] for a in audits)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    report = analyze(args.run.resolve())
    if args.compact:
        report["failed_checks"] = {k: [n for n, v in c.items() if not v] for k, c in report.pop("array_checks").items() if not all(c.values())}
        report["branches"] = [{"id": b["case"]["id"], "switched": b["exposure"]["retained_switch"],
            "new_state_transmitted": b["new_state_transmitted"], "exposure_rehomed": b["exposure_rehomed"],
            "cue_end": [c["contact_label"] for c in b["exposure"]["carriers"]],
            "outgoing": [r["outgoing_labels"] for r in b["rounds"]]} for b in report["branches"]]
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if all(report[k] for k in ("all_array_checks_pass", "input_hashes_valid", "frozen_hashes_valid", "predecessor_audit_hash_valid")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
