"""Independent source, isolation, renewal and sampled-commitment audit."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_cue_duration import reconstruct_writing
from analyze_group_transfer import arrays
from analyze_lineage_return import source_inputs
from analyze_pulse_spacing import check_phase, comparison, expected_timeline
from analyze_renewal import audit_round
from memory_metrics import REGULATORS, classify, opposite
from run_onward_transfer import file_hash


def audit_checkpoint(inputs, config, case, indices):
    original, old_ids, seen, lineage, checks = source_inputs(inputs, config, case, indices)
    o, n = case["origin_state"], case["stop_count"]
    name = o.lower() + "_to_" + opposite(o).lower() + "_to_" + o.lower() + "_train_g0010_" + case["condition"] + ("_fine" if case["fine"] else "")
    stem = "checkpoint_" + name
    meta = json.loads((inputs / (stem + ".json")).read_text())
    previous = json.loads((inputs / "spacing_summary.json").read_text())
    historical = next(c for c in previous["config"]["cases"] if c["id"] == name)
    ids = [name + "::" + i for i in old_ids]
    cues = [f"{name}:cue:carrier_{i}:donor_{j}" for i in (1, 2) for j in range(1, 6)]
    plan = expected_timeline(dict(mode="train", gap=10))
    checks.update({
        "correct_source_refinement_condition_and_schedule": historical["fine"] == case["fine"] and historical["condition"] == case["condition"] and historical["mode"] == "train" and historical["gap"] == 10,
        "historical_ids_and_no_edits": meta["incoming_ids"] == meta["outgoing_ids"] == old_ids and meta["cue_ids"] == cues and meta["cue_refresh_count"] == meta["new_reference_edits"] == 0,
        "fixed_prefix_and_contact_end_age": meta["timeline"] == plan and plan[2 * n - 2] == dict(name=f"pulse_{n:02}", kind="contact", horizon=10, start=20 * n - 20, end=20 * n - 10),
        "historical_phase_and_setup_counts": len(meta["audits"]) == 42 and len(meta["setups"]) == 40 and len(meta["carriers"]) == 2,
        "history_ids_exclude_older_lineage": len(set(ids + cues)) == 12 and not (set(ids + cues) & seen),
    })
    seen.update(ids + cues)
    groups, provenance = [], []
    for i in (1, 2):
        filename = stem + f"_carrier_{i}_pulse_{n:02}.npz"
        phase = arrays(inputs / filename)
        state = phase["final"]
        record = meta["audits"][(i - 1) * 21 + 2 * n - 2]
        episode = meta["carriers"][i - 1]["episodes"][2 * n - 2]
        setup = meta["setups"][(i - 1) * 20 + 2 * n - 2]
        active = case["condition"] == "pulse"
        labels = "".join(classify(state, indices))
        checks.update({
            filename + "/complete_checkpoint": all(phase[k].shape == (17, 6) for k in ("initial", "raw_final", "final")) and phase["concentrations"].shape == (len(phase["times"]), 17, 6),
            filename + "/finite_nonnegative": all(np.isfinite(v).all() and (v >= 0).all() for v in phase.values()),
            filename + "/contact_not_gap_or_later_hold": record["phase"] == f"carrier_{i}_pulse_{n:02}" and record["requested_horizon"] == 10 and record["samples"] == len(phase["times"]),
            filename + "/historical_labels_reconstructed": record["all_labels"] == labels and record["recipient_label"] == episode["recipient_label"] == labels[0] and episode["cue_labels"] == labels[1:],
            filename + "/historical_episode_matches_prefix": all(episode[k] == v for k, v in plan[2 * n - 2].items()),
            filename + "/selected_history_transport": setup["active"] == active and setup["miRNA_kd"] == (2e-15 if active else 0) and setup["all_gj_transport_zero"] == (not active) and record["miRNA_kd"] == (2e-15 if active else 0),
            filename + "/primary_refresh_and_snail": np.array_equal(phase["raw_final"][:8], state[:8]) and np.all(state[indices["snail"]] == 72),
        })
        groups.append(state.copy())
        provenance.append(dict(file=filename, key="final", receiver_column=0, removed_cue_columns=[1, 2, 3, 4, 5],
            original_id=old_ids[i - 1], fork_id=ids[i - 1], cue_ids=cues[(i - 1) * 5:i * 5]))
    checks["thirty_excluded_instances"] = len(seen) == 30
    checkpoint = dict(historical_reuse=True, historical_case=name, source_settings="fine" if case["fine"] else "baseline",
        source_phase=f"pulse_{n:02}", stop_count=n, history_age=20 * n - 10, nominal_removal=89000 + 20 * n - 10,
        groups=provenance, excluded_ids=sorted(seen))
    return original, groups, ids, cues, seen, dict(lineage=lineage, checkpoint=checkpoint), {k: bool(v) for k, v in checks.items()}


def audit_exposure(folder, inputs, config, case, indices):
    original, groups, ids, cues, seen, source, checks = audit_checkpoint(inputs, config, case, indices)
    saved = arrays(folder / "endpoints.npz")
    result = json.loads((folder / "result.json").read_text())
    checks.update({
        "historical_receivers_retained_cues_removed": result["incoming_ids"] == result["outgoing_ids"] == ids and result["removed_cue_ids"] == cues,
        "no_new_cue_contact_or_reference_edit": result["new_reference_edits"] == result["new_contacts"] == result["new_cue_instances"] == 0,
        "historical_placements_not_new_cells": result["reused_receiver_placements"] == 2 and result["removed_historical_cue_placements"] == 10,
        "only_two_isolated_holds_per_receiver": len(result["audits"]) == 4 and len(result["setups"]) == 2,
        "all_onward_relays_active_even_after_blocked_history": case["history"] == "learned",
    })
    rows, packets = [], []
    for j, group in enumerate(groups):
        tag = f"carrier_{j + 1}"
        checks[tag + "/full_checkpoint_saved"] = np.array_equal(group, saved[tag + "_checkpoint"])
        state = group[:, :1].copy()
        holds = []
        for k in range(2):
            state, row, pc = check_phase(folder, tag + f"_hold_{k + 1}", 10000, indices, state, 1, False, 2e-15,
                result["audits"][2 * j + k], result["setups"][j] if k == 0 else None)
            checks.update({tag + f"/hold_{k + 1}/" + key: v for key, v in pc.items()})
            holds.append(row)
            if k == 0:
                first = state.copy()
                checks[tag + "/first_hold_saved"] = np.array_equal(first, saved[tag + "_held_first"])
        checks[tag + "/actual_receiver_not_cue_forwarded"] = np.array_equal(state, saved["continuing_packet"][:, j:j + 1])
        labels = classify(group, indices)
        retained = labels[0] == case["state"] and all(h["recipient_label"] == case["state"] and h["late_label_fractions"][case["state"]] >= .95 for h in holds)
        row = dict(id=ids[j], contact_label=str(labels[0]), cue_end_labels="".join(labels[1:]),
            holds=holds, retained_switch=bool(retained), ion_hold_drift=float(np.max(np.abs(state[:4] - first[:4]))))
        checks[tag + "/carrier_record_reconstructed"] = all(result["carriers"][j][k] == v for k, v in row.items() if k != "holds")
        checks[tag + "/hold_records_match"] = result["carriers"][j]["holds"] == result["audits"][2 * j:2 * j + 2]
        rows.append(row)
        packets.append(state)
    retained = all(c["retained_switch"] for c in rows)
    checks["strict_retention_endpoint_recomputed"] = result["retained_switch"] == retained
    exposure = dict(carriers=rows, retained_switch=retained)
    endpoints = dict(checkpoint_receivers=np.concatenate([g[:, :1] for g in groups], axis=1),
        checkpoint_groups=np.concatenate(groups, axis=1))
    return np.concatenate(packets, axis=1), ids, seen, source, exposure, {k: bool(v) for k, v in checks.items()}, result["audits"], endpoints, original


def audit_branch(folder, inputs, config, case, indices, refs):
    packet, ids, seen, source, exposure, ec, audits, endpoints, original = audit_exposure(folder / "exposure", inputs, config, case, indices)
    start, initial_seen = packet.copy(), len(seen)
    endpoints["after_holds"] = start
    checks = {case["id"] + "/exposure": ec}
    fresh = refs["prepared"][:, {"E": 0, "M": 1}[case["old_state"]], None]
    rounds = []
    for n in (4, 5):
        end, row, rc, pa = audit_round(folder / f"round_{n:02}", config, case, n, packet, ids, seen, fresh, refs["later"], indices)
        packet, ids = end["outgoing_packet"], [c["id"] for c in row["children"]]
        seen.update(ids)
        rounds.append(row)
        audits.extend(pa)
        checks[f"{case['id']}/round_{n:02}"] = rc
        endpoints[str(n)] = packet
    outcomes = reconstruct_writing(exposure, rounds, case["state"], .95)
    saved, result = arrays(folder / "endpoints.npz"), json.loads((folder / "result.json").read_text())
    age = 20 * case["stop_count"] - 10
    checks[case["id"]] = {
        "case_record_correct": result["case"] == case and result["execution_pass"] and result["ion_indices"] == indices,
        "source_provenance_reconstructed": result["source"] == source == json.loads((folder / "source.json").read_text()),
        "older_source_pair_saved": np.array_equal(saved["source_packet"], original),
        "actual_held_pair_seeds_relay": np.array_equal(saved["continuing_start"], start),
        "fresh_recipient_opposes_target": np.array_equal(saved["fresh_target"], fresh) and classify(fresh, indices).tolist() == [opposite(case["state"])] == [case["old_state"]],
        "actual_final_pair_saved": np.array_equal(saved["final_packet"], packet),
        "final_ids_correct_and_disjoint": result["final_ids"] == ids and not (set(ids) & set(source["checkpoint"]["excluded_ids"])),
        "four_new_recipients": result["distinct_fresh_targets"] == len(seen) - initial_seen == 4,
        "reused_receiver_counts_correct": result["reused_receiver_placements"] == 2 and result["removed_historical_cue_placements"] == 10 and result["new_cue_instances"] == 0,
        "exposure_record_matches": result["exposure"] == json.loads((folder / "exposure/result.json").read_text()),
        "six_outcomes_recomputed": all(result[k] == v for k, v in outcomes.items()),
        "strict_legacy_endpoint_preserved": result["retained_switch"] == exposure["retained_switch"] and outcomes["prompt_rewrite"] == (exposure["retained_switch"] and outcomes["new_state_transmitted"]),
        "nominal_clock_correct": result["nominal_schedule"] == [dict(round=4, start=109000 + age, end=131000 + age), dict(round=5, start=131000 + age, end=153000 + age)],
        "twenty_six_new_integrations": len(audits) == 26,
    }
    branch = dict(case=case, exposure=exposure, rounds=rounds, outcomes=outcomes, historical_reuse=False)
    return branch, endpoints, checks, audits


def historical_benchmarks(prior):
    rows = []
    for origin in ("E", "M"):
        stem = origin.lower() + "_to_" + opposite(origin).lower() + "_to_" + origin.lower()
        selections = [(5, prior["history"], stem + "_r1c1_pulse")]
        selections.extend((10, prior["spacing"], stem + "_train_g0010_" + c + ("_fine" if f else ""))
            for c, f in (("pulse", False), ("blocked", False), ("pulse", True)))
        for count, report, name in selections:
            b = next(b for b in report["branches"] if b["case"]["id"] == name)
            rows.append(dict(case=dict(b["case"], stop_count=count), historical_reuse=True, source_run=report["run"],
                exposure=b["exposure"], rounds=b["rounds"], outcomes=b["outcomes"]))
    return rows


def panel_summary(branches, historical):
    panel = {}
    for origin in ("E", "M"):
        by = {(b["case"]["stop_count"], b["case"]["condition"], b["case"]["fine"]): b
            for b in branches + historical if b["case"]["origin_state"] == origin}
        rows = []
        for n in sorted({k[0] for k in by}):
            b = by[(n, "pulse", False)]
            f, blocked = by.get((n, "pulse", True)), by.get((n, "blocked", False))
            carriers = b["exposure"]["carriers"]
            rows.append(dict(stop_count=n, removal_age=20 * n - 10, historical_reuse=b["historical_reuse"],
                removal_labels="".join(c["contact_label"] for c in carriers),
                held_labels=["".join(c["holds"][j]["recipient_label"] for c in carriers) for j in (0, 1)],
                onward_labels=[r["outgoing_labels"] for r in b["rounds"]],
                outcomes=b["outcomes"], blocked_outcomes=blocked["outcomes"] if blocked else None,
                fine_outcomes=f["outcomes"] if f else None, fine_agrees=f["outcomes"] == b["outcomes"] if f else None))
        successes = [r["stop_count"] for r in rows if r["outcomes"]["durable_rewrite"]]
        first = min(successes) if successes else None
        failures_before = [r["stop_count"] for r in rows if first is not None and r["stop_count"] < first and not r["outcomes"]["durable_rewrite"]]
        reversals = [[a["stop_count"], b["stop_count"]] for a, b in zip(rows, rows[1:])
            if a["outcomes"]["durable_rewrite"] and not b["outcomes"]["durable_rewrite"]]
        panel[origin] = dict(rows=rows, earliest_successful_sampled_stop=first,
            last_sampled_failure_before_first_success=max(failures_before) if failures_before else None,
            sampled_success_to_failure_reversals=reversals, untested_counts=[1, 7, 9],
            exact_threshold_established=False)
    return panel


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
        branch, endpoint, bc, pa = audit_branch(run / case["id"], inputs, config, case, indices, refs)
        checks.update(bc)
        branches.append(branch)
        endpoints[case["id"]] = endpoint
        audits.extend(pa)
    prior = json.loads((run / "predecessor_audit.json").read_text())
    spacing = json.loads((inputs / "spacing_summary.json").read_text())
    history = json.loads((inputs / "history_summary.json").read_text())
    checks["historical_reuse"] = {
        "both_predecessor_audits_valid": all(p["all_array_checks_pass"] and all(all(c.values()) for c in p["array_checks"].values()) for p in prior.values()),
        "22565_historical_checks_not_new_work": prior["spacing"]["array_check_count"] == 16296 and prior["history"]["array_check_count"] == 6269,
        "correct_complete_historical_panels": spacing["all_execution_valid"] and history["all_execution_valid"] and len(prior["spacing"]["branches"]) == 32 and len(prior["history"]["branches"]) == 24,
        "historical_timestamps": spacing["started_utc"] == "20260906T130210Z" and history["started_utc"] == "20260906T144633Z",
        "crossover_uses_same_spacing_run": file_hash(inputs / "spacing_summary.json") == history["inputs"]["previous_summary.json"]["sha256"],
        "fifth_contact_benchmarks_exact": len(prior["history"]["historical_pulse5_comparisons"]) == 2 and all(c["bitwise_same"] for c in prior["history"]["historical_pulse5_comparisons"].values()),
        "fixed_eighty_source_files": len(summary["inputs"]) == 80,
        "new_costs_exclude_historical_priming": len(branches) == 30 and len(audits) == 780,
    }
    historical = historical_benchmarks(prior)
    fine = {}
    for b in branches:
        c = b["case"]
        if c["fine"]:
            name = c["id"].removesuffix("_fine")
            base = next(v for v in branches if v["case"]["id"] == name)
            fine[name] = dict(same_outcomes=b["outcomes"] == base["outcomes"],
                source_prefix_refinement=True, older_lineage_refinement=False,
                endpoints={s: comparison(a, endpoints[c["id"]][s], indices, reg, scales)
                    for s, a in endpoints[name].items()})
    checks["historical_reuse"]["eight_benchmarks_and_ten_fine_comparisons"] = len(historical) == 8 and len(fine) == 10
    children = [c for b in branches for r in b["rounds"] for c in r["children"]]
    carriers = [c for b in branches for c in b["exposure"]["carriers"]]
    return dict(run=str(run), all_array_checks_pass=all(all(c.values()) for c in checks.values()),
        array_checks=checks, array_check_count=sum(len(c) for c in checks.values()),
        input_hashes_valid=all(file_hash(inputs / n) == v["sha256"] for n, v in summary["inputs"].items()),
        original_inputs_hashes_valid=all(file_hash(Path(v["source"])) == v["sha256"] for v in summary["inputs"].values()),
        frozen_hashes_valid=all(file_hash(run / "frozen" / n) == h for n, h in summary["frozen_hashes_sha256"].items()),
        execution_files_hashes_valid=all(file_hash(run.parents[1] / n) == h for n, h in summary["hashes_sha256"].items()),
        predecessor_audit_hash_valid=file_hash(run / "predecessor_audit.json") == summary["predecessor_audit_sha256"],
        branches=branches, historical_benchmarks=historical, commitment_panel=panel_summary(branches, historical),
        fine_comparisons=fine, new_fresh_targets=len(children), complete_pair_replacements=2 * len(branches),
        reused_receiver_placements=2 * len(branches), removed_historical_cue_placements=10 * len(branches),
        new_cue_instances=0, new_integrations=len(audits), new_snapshots=sum(a["samples"] for a in audits),
        all_new_recipients_locally_recovered=all(c["recovery"]["recovered"] for c in children),
        maximum_new_recovery_distance=max(c["recovery"]["final_distance"] for c in children),
        maximum_new_ion_hold_drift=max(c["ion_hold_drift"] for c in children + carriers),
        elapsed_seconds=summary["elapsed_seconds"], new_integration_cpu_seconds=sum(a["cpu_seconds"] for a in audits))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    report = analyze(args.run.resolve())
    if args.compact:
        report["failed_checks"] = {k: [n for n, v in c.items() if not v] for k, c in report.pop("array_checks").items() if not all(c.values())}
        for key in ("branches", "historical_benchmarks"):
            report[key] = [dict(id=b["case"]["id"], stop_count=b["case"]["stop_count"], historical_reuse=b["historical_reuse"], **b["outcomes"]) for b in report[key]]
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if all(report[k] for k in ("all_array_checks_pass", "input_hashes_valid", "original_inputs_hashes_valid",
        "frozen_hashes_valid", "execution_files_hashes_valid", "predecessor_audit_hash_valid")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
