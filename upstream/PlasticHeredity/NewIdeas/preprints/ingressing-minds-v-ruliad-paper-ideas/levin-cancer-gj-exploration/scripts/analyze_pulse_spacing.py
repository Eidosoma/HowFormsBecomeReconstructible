"""Independent trajectory, timing, cue-continuity and renewal audit."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_cue_duration import reconstruct_writing
from analyze_group_transfer import arrays
from analyze_lineage_return import source_inputs
from analyze_renewal import audit_round
from memory_metrics import REGULATORS, classify, opposite
from run_memory_probe import array_hash
from run_onward_transfer import file_hash


def expected_timeline(case):
    # Independent fixed-protocol construction, not the runner's schedule helper.
    gap = case["gap"]
    window = 100 + 9 * gap
    if case["mode"] == "train":
        raw = []
        for j in range(10):
            raw.append((f"pulse_{j + 1:02}", "contact", 10))
            if j < 9 and gap:
                raw.append((f"gap_{j + 1:02}", "gap", gap))
    else:
        length = {"continuous": 100, "single": 10}[case["mode"]]
        raw = [("wait", "wait", window - length)] if window > length else []
        raw.append((case["mode"], "contact", length))
    plan, clock = [], 0
    for name, kind, duration in raw:
        plan.append(dict(name=name, kind=kind, horizon=duration, start=clock, end=clock + duration))
        clock += duration
    return plan


def check_phase(folder, name, duration, indices, expected, count, active, kd, record, setup=None):
    phase = arrays(folder / (name + ".npz"))
    labels = classify(phase["final"], indices)
    late = classify(phase["concentrations"], indices)[:, 0][phase["times"] >= .75 * duration]
    fractions = {label: float(np.mean(late == label)) for label in ("E", "M", "X")}
    checks = {
        "primary_continuity_all_cells": np.array_equal(phase["initial"][:8], expected[:8]),
        "shape_and_cell_count": all(phase[k].shape == (17, count) for k in ("initial", "raw_final", "final")) and phase["concentrations"].shape == (len(phase["times"]), 17, count),
        "phase_metadata": record["phase"] == name and record["requested_horizon"] == duration and record["samples"] == len(phase["times"]),
        "labels_recomputed": record["all_labels"] == "".join(labels) and record["recipient_label"] == str(labels[0]) and record["late_label_fractions"] == fractions,
        "transport_metadata": record["miRNA_kd"] == (kd if active else 0) and record["graph_edges"] == count - 1,
        "finite_nonnegative": all(np.isfinite(v).all() and (v >= 0).all() for v in phase.values()),
        "sampling": len(late) > 0 and np.all(np.diff(phase["times"]) > 0),
        "snail_and_native_refresh": np.all(phase["initial"][indices["snail"]] == 72) and np.all(phase["final"][indices["snail"]] == 72) and np.array_equal(phase["raw_final"][:8], phase["final"][:8]),
    }
    if setup is not None:
        checks.update({
            "full_state_enters_rebuild": setup["state_hash_before_derived_refresh"] == array_hash(expected),
            "setup_phase_correct": setup["phase"] == name,
            "star_or_isolation_correct": setup["cells"] == count and setup["edges"] == count - 1 and setup["edges_list"] == [[0, j] for j in range(1, count)],
            "all_transport_off_in_gaps_and_waits": setup["active"] == active and setup["miRNA_kd"] == (kd if active else 0) and setup["all_gj_transport_zero"] == (not active),
        })
    return phase["final"], dict(recipient_label=str(labels[0]), late_label_fractions=fractions), {k: bool(v) for k, v in checks.items()}


def audit_exposure(folder, inputs, config, case, prepared, indices):
    source, ids, prior_ids, _, checks = source_inputs(inputs, config, case, indices)
    saved = arrays(folder / "endpoints.npz")
    record = json.loads((folder / "result.json").read_text())
    plan = expected_timeline(case)
    cues = [] if case["condition"] == "alone" else [f"{case['id']}:cue:carrier_{i}:donor_{j}" for i in (1, 2) for j in range(1, 6)]
    checks.update({
        "exact_source_enters_exposure": np.array_equal(source, saved["source_packet"]),
        "ids_preserved": record["incoming_ids"] == record["outgoing_ids"] == ids,
        "ten_cues_initialized_only_once": record["cue_ids"] == cues and len(cues) == len(set(cues)) and not (set(cues) & prior_ids),
        "no_declared_refresh_or_reset": record["cue_refresh_count"] == record["new_reference_edits"] == 0,
        "fixed_timeline_and_window": record["timeline"] == plan and record["cue_window"] == 100 + 9 * case["gap"],
        "phase_and_setup_counts": len(record["audits"]) == 2 * (len(plan) + 2) and len(record["setups"]) == 2 * (len(plan) + 1),
        "all_onward_relays_active": case["history"] == "learned",
    })
    rows, packets, contacts, audits, trace = [], [], [], [], {}
    for i in (1, 2):
        tag = f"carrier_{i}"
        count = 1 if case["condition"] == "alone" else 6
        state = np.empty((17, count))
        state[:, :1] = source[:, i - 1:i]
        if count > 1:
            label = case["old_state"] if case["condition"] == "same" else case["state"]
            state[:, 1:] = prepared[:, {"E": 0, "M": 1}[label], None]
        checks[tag + "/initial_assembly"] = np.array_equal(saved[tag + "_initial"], state)
        episodes = []
        offset = (i - 1) * (len(plan) + 2)
        setup_offset = (i - 1) * (len(plan) + 1)
        for j, step in enumerate(plan):
            name = tag + "_" + step["name"]
            active = case["condition"] in ("pulse", "same") and step["kind"] == "contact"
            pa, setup = record["audits"][offset + j], record["setups"][setup_offset + j]
            state, row, pc = check_phase(folder, name, step["horizon"], indices, state, count, active, config["write_kd"], pa, setup)
            checks.update({name + "/" + k: v for k, v in pc.items()})
            episodes.append(dict(step, recipient_label=row["recipient_label"], cue_labels="".join(classify(state, indices)[1:])))
            trace.setdefault(step["name"], []).append(state.copy())
            audits.append(pa)
        checks[tag + "/last_contact_saved"] = np.array_equal(saved[tag + "_contact"], state)
        contacts.append(state[:, :1])
        state = state[:, :1].copy()  # Only original target survives removal.
        holds = []
        for j, duration in enumerate(config["cue_holds"]):
            name = f"{tag}_hold_{j + 1}"
            pa = record["audits"][offset + len(plan) + j]
            setup = record["setups"][setup_offset + len(plan)] if j == 0 else None
            state, row, pc = check_phase(folder, name, duration, indices, state, 1, False, config["write_kd"], pa, setup)
            checks.update({name + "/" + k: v for k, v in pc.items()})
            holds.append(row)
            audits.append(pa)
            if j == 0:
                first = state.copy()
                checks[tag + "/first_hold_saved"] = np.array_equal(first, saved[tag + "_held_first"])
        checks[tag + "/actual_incumbent_forwarded"] = np.array_equal(state, saved["continuing_packet"][:, i - 1:i])
        retained = episodes[-1]["recipient_label"] == case["state"] and all(h["recipient_label"] == case["state"] and h["late_label_fractions"][case["state"]] >= config["late_label_fraction"] for h in holds)
        row = dict(id=ids[i - 1], contact_label=episodes[-1]["recipient_label"], cue_end_labels=episodes[-1]["cue_labels"],
            episodes=episodes, holds=holds, retained_switch=bool(retained), ion_hold_drift=float(np.max(np.abs(state[:4] - first[:4]))))
        stored = record["carriers"][i - 1]
        checks[tag + "/carrier_record_reconstructed"] = all(stored[k] == v for k, v in row.items() if k != "holds")
        checks[tag + "/hold_records_match"] = stored["holds"] == record["audits"][offset + len(plan):offset + len(plan) + 2]
        rows.append(row)
        packets.append(state)
    retained = all(r["retained_switch"] for r in rows)
    checks["pair_switch_recomputed"] = record["retained_switch"] == retained
    joint = [int(step["name"].split("_")[-1]) for j, step in enumerate(plan) if step["name"].startswith("pulse_") and all(r["episodes"][j]["recipient_label"] == case["state"] for r in rows)]
    exposure = dict(carriers=rows, retained_switch=retained, cue_instances=len(cues), cue_window=plan[-1]["end"], first_joint_target_pulse=min(joint) if joint else None)
    return np.concatenate(packets, axis=1), ids, prior_ids | set(cues), exposure, {k: bool(v) for k, v in checks.items()}, audits, np.concatenate(contacts, axis=1), {k: np.concatenate(v, axis=1) for k, v in trace.items()}


def comparison(a, b, indices, reg, scales):
    return dict(same_labels=bool(np.array_equal(classify(a, indices), classify(b, indices))),
        regulatory_distance=float(np.max(np.abs(a[reg] - b[reg]) / scales[:, None])),
        full_state_max_abs_difference=float(np.max(np.abs(a - b))))


def panel_summary(branches):
    panel = {}
    for origin in ("E", "M"):
        rows = [b for b in branches if b["case"]["origin_state"] == origin]
        contrasts = []
        for gap in (10, 1000):
            subset = [b for b in rows if b["case"]["gap"] == gap]
            base = {(b["case"]["mode"], b["case"]["condition"]): b for b in subset if not b["case"]["fine"]}
            fine = next(b for b in subset if b["case"]["fine"])
            pulse = base[("train", "pulse")]
            outcome = {"_".join(k): b["outcomes"]["durable_rewrite"] for k, b in base.items()}
            controls_negative = not any(outcome["train_" + c] for c in ("blocked", "same", "alone"))
            contrasts.append(dict(gap=gap, cue_window=100 + 9 * gap, durable_outcomes=outcome,
                all_controls_negative=controls_negative, fine_train_outcomes_agree=fine["outcomes"] == pulse["outcomes"],
                first_joint_target_pulse=pulse["exposure"]["first_joint_target_pulse"],
                train_succeeds_late_single_fails=outcome["train_pulse"] and not outcome["single_pulse"],
                train_fails_matched_continuous_succeeds=not outcome["train_pulse"] and outcome["continuous_pulse"],
                both_train_and_matched_continuous_fail=not outcome["train_pulse"] and not outcome["continuous_pulse"]))
        panel[origin + "_to_" + opposite(origin) + "_to_" + origin] = contrasts
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
    checks, branches, audits, endpoints, traces = {}, [], [], {}, {}
    for case in config["cases"]:
        folder = run / case["id"]
        packet, ids, seen, exposure, ec, ea, contact, trace = audit_exposure(folder / "exposure", inputs, config, case, refs["prepared"], indices)
        checks[case["id"] + "/exposure"] = ec
        audits.extend(ea)
        traces[case["id"]] = trace
        start, old_ids, initial_seen = packet.copy(), ids.copy(), len(seen)
        endpoints[case["id"]] = dict(contact=contact, after_holds=start)
        fresh = refs["prepared"][:, {"E": 0, "M": 1}[case["old_state"]], None]
        rounds = []
        for n in config["continuing_rounds"]:
            end, row, rc, pa = audit_round(folder / f"round_{n:02}", config, case, n, packet, ids, seen, fresh, refs["later"], indices)
            packet, ids = end["outgoing_packet"], [c["id"] for c in row["children"]]
            seen.update(ids)
            rounds.append(row)
            audits.extend(pa)
            checks[f"{case['id']}/round_{n:02}"] = rc
            endpoints[case["id"]][str(n)] = packet
        outcomes = reconstruct_writing(exposure, rounds, case["state"], config["late_label_fraction"])
        saved, result = arrays(folder / "endpoints.npz"), json.loads((folder / "result.json").read_text())
        original, _, _, expected_source, _ = source_inputs(inputs, config, case, indices)
        begin = 109000 + 100 + 9 * case["gap"]
        schedule = [dict(round=n, start=begin + j * 22000, end=begin + (j + 1) * 22000) for j, n in enumerate((4, 5))]
        checks[case["id"]] = {
            "case_record_correct": result["case"] == case and result["execution_pass"] and result["ion_indices"] == indices,
            "source_record_correct": result["source"] == expected_source == json.loads((folder / "source.json").read_text()),
            "original_saved": np.array_equal(saved["source_packet"], original),
            "actual_posthold_pair_seeds_relay": np.array_equal(saved["continuing_start"], start),
            "fresh_target_saved": np.array_equal(saved["fresh_target"], fresh),
            "recipient_opposes_target": classify(fresh, indices).tolist() == [opposite(case["state"])] == [case["old_state"]],
            "actual_final_packet_saved": np.array_equal(saved["final_packet"], packet),
            "final_ids_match": result["final_ids"] == ids and not (set(ids) & set(old_ids)),
            "four_fresh_recipients_excludes_cues": result["distinct_fresh_targets"] == len(seen) - initial_seen == 4,
            "cue_cells_counted_once": result["cue_instances"] == exposure["cue_instances"],
            "exposure_record_matches": result["exposure"] == json.loads((folder / "exposure/result.json").read_text()),
            "all_six_outcomes_recomputed": all(result[k] == v for k, v in outcomes.items()),
            "legacy_strict_endpoint_unchanged": result["retained_switch"] == exposure["retained_switch"] and outcomes["prompt_rewrite"] == (exposure["retained_switch"] and outcomes["new_state_transmitted"]),
            "nominal_clock_correct": result["nominal_schedule"] == schedule,
        }
        branches.append(dict(case=case, exposure=exposure, rounds=rounds, outcomes=outcomes))
    prior = json.loads((run / "predecessor_audit.json").read_text())
    old_summary = json.loads((inputs / "previous_summary.json").read_text())
    benchmarks = [b for b in prior["new_branches"] if b["case"]["condition"] == "pulse" and b["cue_duration"] == 100]
    checks["historical_benchmark"] = {
        "prior_full_audit_passes": prior["array_check_count"] == 3976 and prior["all_array_checks_pass"] and all(all(c.values()) for c in prior["array_checks"].values()),
        "four_correct_historical_cases": len(benchmarks) == 4 and {(b["case"]["origin_state"], b["case"].get("fine", False)) for b in benchmarks} == {(o, f) for o in ("E", "M") for f in (False, True)},
        "same_source_bank": all(summary["inputs"][n]["sha256"] == v["sha256"] for n, v in old_summary["inputs"].items() if n != "previous_summary.json"),
        "historical_costs_excluded": len(branches) == 32 and sum(b["exposure"]["cue_instances"] for b in branches) == 280 and len(audits) == 1704,
    }
    fine, segmentation = {}, {}
    for b in branches:
        c = b["case"]
        if c["fine"]:
            name = c["id"].removesuffix("_fine")
            base = next(v for v in branches if v["case"]["id"] == name)
            phases = {stage: comparison(a, traces[c["id"]][stage], indices, reg, scales) for stage, a in traces[name].items()}
            fine[name] = dict(same_outcomes=base["outcomes"] == b["outcomes"],
                endpoints={stage: comparison(a, endpoints[c["id"]][stage], indices, reg, scales) for stage, a in endpoints[name].items()},
                exposure_episode_comparisons=phases)
        if c["gap"] == 0:
            benchmark = next(v for v in benchmarks if v["case"]["origin_state"] == c["origin_state"] and v["case"].get("fine", False) == c["fine"])
            key = benchmark["case"]["id"]
            old_exp = arrays(inputs / ("benchmark_" + key + "_exposure.npz"))
            old_end = arrays(inputs / ("benchmark_" + key + "_branch.npz"))
            old_contact = np.concatenate([old_exp[f"carrier_{i}_contact"][:, :1] for i in (1, 2)], axis=1)
            old_stages = dict(contact=old_contact, after_holds=old_end["continuing_start"], **{"5": old_end["final_packet"]})
            checks["historical_benchmark"][key + "_source_matches"] = np.array_equal(old_end["source_packet"], arrays(run / c["id"] / "endpoints.npz")["source_packet"])
            segmentation[c["id"]] = dict(historical_case=key, historical_reuse=True, same_outcomes=b["outcomes"] == benchmark["outcomes"],
                endpoints={stage: comparison(endpoints[c["id"]][stage], a, indices, reg, scales) for stage, a in old_stages.items()})
    children = [c for b in branches for r in b["rounds"] for c in r["children"]]
    carriers = [c for b in branches for c in b["exposure"]["carriers"]]
    return dict(run=str(run), all_array_checks_pass=all(all(c.values()) for c in checks.values()), array_checks=checks,
        array_check_count=sum(len(c) for c in checks.values()),
        input_hashes_valid=all(file_hash(inputs / n) == v["sha256"] for n, v in summary["inputs"].items()),
        frozen_hashes_valid=all(file_hash(run / "frozen" / n) == h for n, h in summary["frozen_hashes_sha256"].items()),
        predecessor_audit_hash_valid=file_hash(run / "predecessor_audit.json") == summary["predecessor_audit_sha256"],
        branches=branches, spacing_panel=panel_summary(branches), fine_comparisons=fine, segmentation_comparisons=segmentation,
        new_fresh_targets=len(children), new_cue_instances=sum(b["exposure"]["cue_instances"] for b in branches),
        new_integrations=len(audits), new_snapshots=sum(a["samples"] for a in audits),
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
        report["branches"] = [dict(id=b["case"]["id"], **b["outcomes"], first_joint_target_pulse=b["exposure"]["first_joint_target_pulse"],
            outgoing=[r["outgoing_labels"] for r in b["rounds"]]) for b in report["branches"]]
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if all(report[k] for k in ("all_array_checks_pass", "input_hashes_valid", "frozen_hashes_valid", "predecessor_audit_hash_valid")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
