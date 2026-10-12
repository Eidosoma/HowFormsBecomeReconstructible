"""Independent component selection, derived state, retention and renewal audit."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_commitment_window import audit_checkpoint
from analyze_group_transfer import arrays
from analyze_pulse_spacing import check_phase, comparison
from analyze_renewal import audit_round
from memory_metrics import REGULATORS, classify
from run_memory_probe import write_json
from run_onward_transfer import file_hash

FLAGS = ("all_array_checks_pass", "input_hashes_valid", "original_inputs_hashes_valid",
    "frozen_hashes_valid", "execution_files_hashes_valid", "predecessor_audit_hash_valid")


def canonical_state(state):
    """Independently implement pinned non-iterative RNA algebra, x0=40."""
    value = state.copy()
    value[8] = value[5]
    ratio = value[5] / 40.
    for n in range(7):
        value[9 + n] = value[6] * ratio ** n / (1 + ratio) ** 6
    return value


def audit_sources(inputs, config, case, indices):
    packets, records, ledgers, checks = {}, {}, [], {}
    for n in (6, 8):
        _, groups, _, _, seen, source, sc = audit_checkpoint(inputs, config, dict(case, stop_count=n), indices)
        packets[n] = np.concatenate([g[:, 0:1] for g in groups], axis=1)
        records[str(n)] = source
        ledgers.append(seen)
        checks.update({f"source_{n}/" + k: v for k, v in sc.items()})
        checks[f"source_{n}/M_pair_and_fixed_background"] = classify(packets[n], indices).tolist() == ["M", "M"] and np.all(packets[n][4] == 72) and np.all(packets[n][16] == 0)
    # Independent construction: choose the origin for every primary row.
    levels = dict(ions=8 if case["mask"] & 4 else 6, rna=8 if case["mask"] & 2 else 6,
        protein=8 if case["mask"] & 1 else 6)
    hybrid = packets[levels["ions"]].copy()
    for row in (5, 6):
        hybrid[row, :] = packets[levels["rna"]][row, :]
    hybrid[7, :] = packets[levels["protein"]][7, :]
    ids = [case["id"] + f":intervened:carrier_{i}" for i in (1, 2)]
    seen = set.union(*ledgers) | set(ids)
    checks.update(dict(fixed_mask_and_components=case["components"] == levels and case["mask"] in range(8),
        shared_historical_ledger=ledgers[0] == ledgers[1] and len(ledgers[0]) == 30,
        distinct_intervention_forks=len(seen) == 32 and len(set(ids)) == 2 and not (set(ids) & ledgers[0]),
        no_extra_polarity_or_transport=case["state"] == "M" and case["old_state"] == "E" and case["history"] == "learned",
        entry_labels_remain_M=classify(hybrid, indices).tolist() == ["M", "M"]))
    record = dict(checkpoints=records, historical_ages={"6": 110, "8": 150}, components=levels,
        intervention_ids=ids, excluded_ids=sorted(seen), artificial_counterfactual=True,
        new_cue_instances=0, assay_time_origin="intervention")
    return packets, hybrid, ids, seen, record, {k: bool(v) for k, v in checks.items()}


def audit_retention(folder, inputs, config, case, indices):
    packets, hybrid, ids, seen, source, checks = audit_sources(inputs, config, case, indices)
    saved, result = arrays(folder / "endpoints.npz"), json.loads((folder / "result.json").read_text())
    expected_canonical = canonical_state(hybrid)
    checks.update(dict(complete_sources_saved=all(np.array_equal(saved[f"source_{n}"], packets[n]) for n in (6, 8)),
        exact_primary_component_mix=np.array_equal(saved["hybrid_before_refresh"], hybrid),
        native_derived_refresh_matches_formula=np.allclose(saved["canonical_entry"], expected_canonical, rtol=1e-12, atol=1e-14),
        no_primary_change_during_refresh=np.array_equal(saved["canonical_entry"][:8], hybrid[:8]),
        ids_preserved=result["incoming_ids"] == result["outgoing_ids"] == ids,
        no_contacts_or_new_cues=result["new_contacts"] == result["new_cue_instances"] == 0,
        explicit_fork_placements=result["intervention_receiver_placements"] == 2 and result["primary_components"] == case["components"],
        fixed_hold_counts=len(result["audits"]) == 4 and len(result["setups"]) == 2 and len(result["carriers"]) == 2))
    rows, continuing = [], []
    for j in range(2):
        tag = f"carrier_{j + 1}"
        state, holds = hybrid[:, j:j + 1].copy(), []
        for k in range(2):
            phase = tag + f"_hold_{k + 1}"
            state, row, pc = check_phase(folder, phase, 10000, indices, state, 1, False, 2e-15,
                result["audits"][2 * j + k], result["setups"][j] if k == 0 else None)
            checks.update({phase + "/" + key: v for key, v in pc.items()})
            phase_saved = arrays(folder / (phase + ".npz"))
            checks[phase + "/canonical_initial_and_final"] = all(np.allclose(phase_saved[key], canonical_state(phase_saved[key]), rtol=1e-12, atol=1e-14) for key in ("initial", "final"))
            holds.append(row)
            if k == 0:
                first = state.copy()
                checks[tag + "/first_hold_saved"] = np.array_equal(first, saved[tag + "_held_first"])
                checks[tag + "/actual_canonical_entry"] = np.array_equal(phase_saved["initial"], saved["canonical_entry"][:, j:j + 1])
        checks[tag + "/actual_held_receiver_forwarded"] = np.array_equal(state, saved["continuing_packet"][:, j:j + 1])
        retained = all(h["recipient_label"] == "M" and h["late_label_fractions"]["M"] >= .95 for h in holds)
        row = dict(id=ids[j], entry_label=str(classify(hybrid[:, j:j + 1], indices)[0]), holds=holds,
            M_retained=retained, ion_hold_drift=float(np.max(np.abs(state[:4] - first[:4]))))
        checks[tag + "/carrier_record_recomputed"] = all(result["carriers"][j][k] == v for k, v in row.items() if k != "holds")
        checks[tag + "/hold_records_match"] = result["carriers"][j]["holds"] == result["audits"][2 * j:2 * j + 2]
        rows.append(row)
        continuing.append(state)
    retained = all(c["M_retained"] for c in rows)
    checks["pair_retention_recomputed"] = result["M_retained"] == retained
    packet = np.concatenate(continuing, axis=1)
    endpoints = dict(source_6=packets[6], source_8=packets[8], hybrid=hybrid,
        canonical_entry=saved["canonical_entry"], after_holds=packet)
    return packet, ids, seen, source, dict(carriers=rows, M_retained=retained), {k: bool(v) for k, v in checks.items()}, result["audits"], endpoints


def audit_branch(folder, inputs, config, case, indices, refs):
    packet, ids, seen, source, retention, rc, audits, endpoints = audit_retention(folder / "retention", inputs, config, case, indices)
    start, initial_seen = packet.copy(), len(seen)
    fresh = refs["prepared"][:, :1].copy()
    checks, rounds = {case["id"] + "/retention": rc}, []
    for n in (4, 5):
        end, row, sc, pa = audit_round(folder / f"round_{n:02}", config, case, n, packet, ids, seen, fresh, refs["later"], indices)
        packet, ids = end["outgoing_packet"], [c["id"] for c in row["children"]]
        seen.update(ids)
        rounds.append(row)
        audits.extend(pa)
        endpoints[str(n)] = packet
        checks[case["id"] + f"/round_{n:02}"] = sc
    outcomes = dict(M_retained=retention["M_retained"], M_renewed=all(r["round_success"] for r in rounds))
    outcomes["durable_M"] = outcomes["M_retained"] and outcomes["M_renewed"]
    saved, result = arrays(folder / "endpoints.npz"), json.loads((folder / "result.json").read_text())
    checks[case["id"]] = dict(case_record_correct=result["case"] == case and result["execution_pass"] and result["ion_indices"] == indices,
        source_record_recomputed=result["source"] == source == json.loads((folder / "source.json").read_text()),
        actual_held_pair_starts_relay=np.array_equal(saved["continuing_start"], start),
        fresh_E_target=np.array_equal(saved["fresh_target"], fresh) and classify(fresh, indices).tolist() == ["E"],
        actual_final_packet=np.array_equal(saved["final_packet"], packet),
        final_ids_correct=result["final_ids"] == ids and not (set(ids) & set(source["excluded_ids"])),
        four_fresh_recipients=result["distinct_fresh_targets"] == len(seen) - initial_seen == 4,
        retention_record_matches=result["retention"] == json.loads((folder / "retention/result.json").read_text()),
        outcomes_recomputed=all(result[k] == v for k, v in outcomes.items()),
        common_assay_clock=result["nominal_schedule"] == [dict(round=4, start=20000, end=42000), dict(round=5, start=42000, end=64000)],
        exactly_26_integrations=len(audits) == 26)
    checks = {group: {k: bool(v) for k, v in items.items()} for group, items in checks.items()}
    return dict(case=case, retention=retention, rounds=rounds, outcomes=outcomes), endpoints, checks, audits


def factorial_contrasts(branches):
    """Report background-specific contrasts; never infer a universal minimum."""
    panels = {}
    for fine in (False, True):
        by = {b["case"]["mask"]: b["outcomes"] for b in branches if b["case"]["fine"] == fine}
        rows = []
        for name, bit in (("ions", 4), ("rna", 2), ("protein", 1)):
            for low in range(8):
                if low & bit:
                    continue
                high = low | bit
                rows.append(dict(block=name, low_mask=f"{low:03b}", high_mask=f"{high:03b}",
                    low_outcomes=by[low], high_outcomes=by[high],
                    durable_difference=int(by[high]["durable_M"]) - int(by[low]["durable_M"])))
        panels["fine" if fine else "baseline"] = dict(contrasts=rows,
            controls_expected=(not by[0]["durable_M"]) and by[7]["durable_M"],
            add_to_six={k: dict(baseline=by[0], with_eight_block=by[b]) for k, b in (("ions", 4), ("rna", 2), ("protein", 1))},
            remove_from_eight={k: dict(baseline=by[7], with_six_block=by[7 ^ b]) for k, b in (("ions", 4), ("rna", 2), ("protein", 1))},
            global_necessity_or_sufficiency_established=False)
    return panels


def analyze(run):
    summary = json.loads((run / "summary.json").read_text())
    if not summary.get("all_execution_valid"):
        raise ValueError("Require a completed valid suite")
    config, inputs = summary["config"], run / "inputs"
    refs = arrays(inputs / "references.npz")
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    reg = [indices[n] for n in REGULATORS]
    scales = np.abs(refs["later"][reg, 0] - refs["later"][reg, 1])
    checks, branches, endpoints, audits = {}, [], {}, []
    for case in config["cases"]:
        branch, end, bc, pa = audit_branch(run / case["id"], inputs, config, case, indices, refs)
        branches.append(branch)
        endpoints[case["id"]] = end
        checks.update(bc)
        audits.extend(pa)
    prior = json.loads((run / "predecessor_audit.json").read_text())
    old_summary = json.loads((inputs / "commitment_summary.json").read_text())
    checks["panel"] = dict(fixed_sixteen_cases=len(branches) == 16 and len({b["case"]["id"] for b in branches}) == 16 and
        {(b["case"]["mask"], b["case"]["fine"]) for b in branches} == {(m, f) for m in range(8) for f in (False, True)},
        fixed_source_and_scopes=config["input_run"] == "runs/commitment-window-20260906T154216Z-6k4vdcff" and config["source_stops"] == [6, 8] and
        config["component_blocks"] == dict(ions=[0, 1, 2, 3], rna=[5, 6], protein=[7]) and config["assay_time_origin"] == "intervention",
        complete_predecessor=all(prior[k] for k in FLAGS) and prior["array_check_count"] == 5949 and len(prior["branches"]) == 30 and
        all(all(c.values()) for c in prior["array_checks"].values()),
        predecessor_identity=old_summary["all_execution_valid"] and old_summary["started_utc"] == "20260906T154216Z",
        fixed_input_and_new_integration_counts=len(summary["inputs"]) == 31 and len(audits) == 416)
    fine_comparisons, controls = {}, {}
    for branch in branches:
        case = branch["case"]
        if case["fine"]:
            name = case["id"].removesuffix("_fine")
            base = next(b for b in branches if b["case"]["id"] == name)
            fine_comparisons[name] = dict(same_outcomes=base["outcomes"] == branch["outcomes"],
                fine_prefix_included=True, older_lineage_refined=False,
                endpoints={k: comparison(v, endpoints[case["id"]][k], indices, reg, scales) for k, v in endpoints[name].items()})
        if case["mask"] in (0, 7):
            n = 6 if case["mask"] == 0 else 8
            suffix = "_fine" if case["fine"] else ""
            old = next(b for b in prior["branches"] if b["case"]["id"] == f"m_to_e_to_m_stop_{n:02}_pulse" + suffix)
            stem = f"benchmark_stop_{n:02}" + suffix
            benchmarks = {"after_holds": arrays(inputs / (stem + "_held.npz"))["continuing_packet"]}
            benchmarks.update({str(r): arrays(inputs / (stem + f"_round_{r:02}.npz"))["outgoing_packet"] for r in (4, 5)})
            outcomes = dict(M_retained=old["outcomes"]["postcue_state_written"], M_renewed=old["outcomes"]["new_state_transmitted"], durable_M=old["outcomes"]["durable_rewrite"])
            controls[case["id"]] = dict(source_stop=n, same_outcomes=outcomes == branch["outcomes"],
                expected_durable_M=n == 8, historical_outcomes=outcomes,
                endpoints={k: dict(bitwise_same=np.array_equal(v, endpoints[case["id"]][k]),
                    **comparison(v, endpoints[case["id"]][k], indices, reg, scales)) for k, v in benchmarks.items()})
    # These are scientific/replication gates, separate from data validity.
    control_gate = len(controls) == 4 and all(c["same_outcomes"] and c["historical_outcomes"]["durable_M"] == c["expected_durable_M"] and
        all(v["bitwise_same"] for v in c["endpoints"].values()) for c in controls.values())
    fine_gate = len(fine_comparisons) == 8 and all(c["same_outcomes"] and all(v["same_labels"] for v in c["endpoints"].values()) for c in fine_comparisons.values())
    children = [c for b in branches for r in b["rounds"] for c in r["children"]]
    report = dict(run=str(run), all_array_checks_pass=all(all(c.values()) for c in checks.values()),
        array_checks=checks, array_check_count=sum(len(c) for c in checks.values()),
        input_hashes_valid=all(file_hash(inputs / n) == v["sha256"] for n, v in summary["inputs"].items()),
        original_inputs_hashes_valid=all(file_hash(Path(v["source"])) == v["sha256"] for v in summary["inputs"].values()),
        frozen_hashes_valid=all(file_hash(run / "frozen" / n) == h for n, h in summary["frozen_hashes_sha256"].items()),
        execution_files_hashes_valid=all(file_hash(run.parents[1] / n) == h for n, h in summary["hashes_sha256"].items()),
        predecessor_audit_hash_valid=file_hash(run / "predecessor_audit.json") == summary["predecessor_audit_sha256"],
        branches=branches, controls=controls, fine_comparisons=fine_comparisons, factorial=factorial_contrasts(branches),
        unchanged_controls_reproduced=control_gate, all_fine_outcomes_and_labels_agree=fine_gate,
        new_integrations=len(audits), new_snapshots=sum(a["samples"] for a in audits),
        fresh_recipients=len(children), complete_pair_replacements=2 * len(branches),
        intervention_receiver_placements=2 * len(branches), new_cue_instances=0,
        all_recipients_locally_recovered=all(c["recovery"]["recovered"] for c in children),
        maximum_recovery_distance=max(c["recovery"]["final_distance"] for c in children),
        maximum_ion_hold_drift=max(c["ion_hold_drift"] for c in children + [c for b in branches for c in b["retention"]["carriers"]]),
        elapsed_seconds=summary["elapsed_seconds"], integration_cpu_seconds=sum(a["cpu_seconds"] for a in audits))
    report["eligible_for_stage2_design"] = all(report[k] for k in FLAGS) and control_gate and fine_gate
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--save", action="store_true", help="Atomically save full independent_audit.json")
    args = parser.parse_args()
    run = args.run.resolve()
    report = analyze(run)
    if args.save:
        write_json(run / "independent_audit.json", report)
    if args.compact:
        report["failed_checks"] = {k: [n for n, v in c.items() if not v] for k, c in report.pop("array_checks").items() if not all(c.values())}
        report["branches"] = [dict(id=b["case"]["id"], components=b["case"]["components"], **b["outcomes"]) for b in report["branches"]]
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if all(report[k] for k in FLAGS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
