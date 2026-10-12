"""Independent saved-array history selection, delivery and fresh-relay audit."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_cue_duration import reconstruct_writing
from analyze_group_transfer import arrays
from analyze_lineage_return import source_inputs
from analyze_pulse_spacing import check_phase, comparison
from analyze_renewal import audit_round
from history_delivery import inward_edge_rates
from memory_metrics import REGULATORS, classify, opposite
from run_onward_transfer import file_hash


def audit_histories(inputs, config, case, indices):
    original, old_ids, seen, lineage, checks = source_inputs(inputs, config, case, indices)
    o = case["origin_state"]
    banks, receiver_ids, cue_ids, files, names = {}, {}, {}, {}, {}
    for h in (0, 1):
        name = o.lower() + "_to_" + opposite(o).lower() + "_to_" + o.lower() + "_train_g0010_" + ("pulse" if h else "blocked")
        names[h] = name
        stem = f"history_{o.lower()}_{h}"
        meta = json.loads((inputs / (stem + ".json")).read_text())
        receiver_ids[h] = [name + "::" + old_id for old_id in old_ids]
        cue_ids[h] = [f"{name}:cue:carrier_{i}:donor_{j}" for i in (1, 2) for j in range(1, 6)]
        seen.update(receiver_ids[h] + cue_ids[h])
        checks[stem + "/historical_ids"] = meta["incoming_ids"] == meta["outgoing_ids"] == old_ids and meta["cue_ids"] == cue_ids[h]
        checks[stem + "/history_not_refreshed"] = meta["cue_refresh_count"] == meta["new_reference_edits"] == 0
        expected_steps = [dict(name=f"{kind}_{i:02}", kind="contact" if kind == "pulse" else "gap", horizon=10,
            start=20 * (i - 1) + (0 if kind == "pulse" else 10), end=20 * (i - 1) + (10 if kind == "pulse" else 20))
            for i in range(1, 5) for kind in ("pulse", "gap")]
        checks[stem + "/four_contacts_four_gaps_age80"] = meta["timeline"][:8] == expected_steps
        banks[h], files[h] = [], []
        for i in (1, 2):
            filename = stem + f"_carrier_{i}_gap_04.npz"
            phase = arrays(inputs / filename)
            state = phase["final"]
            banks[h].append(state)
            files[h].append(filename)
            episode = meta["carriers"][i - 1]["episodes"][7]
            pa = meta["audits"][(i - 1) * 21 + 7]
            checks[filename + "/valid_full_checkpoint"] = state.shape == (17, 6) and np.isfinite(state).all() and (state >= 0).all()
            checks[filename + "/gap_not_later_or_earlier_phase"] = pa["phase"] == f"carrier_{i}_gap_04" and pa["requested_horizon"] == 10 and pa["samples"] == len(phase["times"])
            checks[filename + "/historical_labels_match"] = episode["recipient_label"] == str(classify(state, indices)[0]) and episode["cue_labels"] == "".join(classify(state, indices)[1:]) == pa["all_labels"][1:]
            checks[filename + "/native_primary_and_snail_preserved"] = np.array_equal(phase["raw_final"][:8], state[:8]) and np.all(state[indices["snail"]] == 72)
    rh, ch = case["receiver_history"], case["cue_history"]
    groups, provenance = [], []
    for j in range(2):
        group = np.empty((17, 6))
        group[:, 0] = banks[rh][j][:, 0]
        group[:, 1:] = banks[ch][j][:, 1:]
        groups.append(group)
        provenance.append(dict(carrier=j + 1,
            receiver=dict(file=files[rh][j], key="final", column=0, historical_case=names[rh], original_id=old_ids[j], fork_id=receiver_ids[rh][j]),
            cues=dict(file=files[ch][j], key="final", columns=[1, 2, 3, 4, 5], historical_case=names[ch], ids=cue_ids[ch][j * 5:(j + 1) * 5])))
    checks["42_excluded_lineage_and_history_instances"] = len(seen) == 42 and not (set(receiver_ids[rh]) & set(cue_ids[ch]))
    history = dict(historical_reuse=True, source_settings="baseline", source_phase="gap_04", history_age=80,
        nominal_probe_start=89080, receiver_history=rh, cue_history=ch, groups=provenance, excluded_ids=sorted(seen))
    return original, groups, receiver_ids[rh], cue_ids[ch], seen, dict(lineage=lineage, history=history), {k: bool(v) for k, v in checks.items()}


def audit_delivery(folder, tag, case, indices, record):
    phase = arrays(folder / (tag + "_probe.npz"))
    saved = arrays(folder / (tag + "_delivery.npz"))
    p = record["parameters"]
    active = case["condition"] == "pulse"
    expected_d = np.zeros((17, 5))
    if active:
        expected_d[:3] = 1e-18
    constants = dict(miRNA_valence=-1, F=96485, cell_vol=5.235987755982989e-16,
        cell_sa=3.1415926535897934e-10, cm=.05, kb=1.3806e-23, T=310, q=1.602e-19, GJ_len=1e-7)
    checks = {
        "fixed_native_transport_parameters": all(p[k] == v for k, v in constants.items()) and p["indices"] == indices and p["valences"] == [1., 1., -1., -1.] + [0.] * 13,
        "active_or_all_off_transport": p["miRNA_kd"] == (2e-15 if active else 0) and np.array_equal(p["diffusion"], expected_d),
        "declared_readonly_native_agreement": record["integrator_calls"] == 0 and record["live_state_unchanged"] and record["native_formula_agreement"],
    }
    raw_t = np.r_[0., phase["times"]]
    raw_s = np.concatenate((phase["initial"][None], phase["concentrations"]), axis=0)
    t = np.r_[raw_t[raw_t < 9], 9.]
    state = np.empty((len(t), 17, 6))
    for ion in range(17):
        for cell in range(6):
            state[:, ion, cell] = np.interp(t, raw_t, raw_s[:, ion, cell])
    trace = [inward_edge_rates(s, p) for s in state]
    rates, vm = np.asarray([v[0] for v in trace]), np.asarray([v[1] for v in trace])
    terminal, terminal_vm = inward_edge_rates(phase["final"], p)
    checks.update({
        "common_window_bracketed_by_saved_samples": raw_t[-1] >= 9 and np.all(np.diff(raw_t) > 0),
        "sample_grid_reconstructed": np.array_equal(t, saved["times"]) and record["exchange"]["window"] == [0., 9.] and record["exchange"]["samples"] == len(t),
        "native_trace_independently_recomputed": rates.shape == saved["inward_edge_rates"].shape and np.allclose(rates, saved["inward_edge_rates"], rtol=1e-10, atol=1e-20),
        "voltages_independently_recomputed": np.allclose(vm, saved["voltages"], rtol=1e-12, atol=1e-15) and np.allclose(terminal_vm, saved["terminal_voltages"], rtol=1e-12, atol=1e-15),
        "terminal_rate_recomputed_not_used_as_t10": np.allclose(terminal, saved["terminal_inward_edge_rates"], rtol=1e-10, atol=1e-20),
        "signed_traces_finite": all(np.isfinite(v).all() for v in saved.values()),
        "blocked_transport_exactly_zero": active or not (np.any(saved["inward_edge_rates"]) or np.any(saved["terminal_inward_edge_rates"])),
    })
    net = rates.sum(axis=2)
    integrals = dict(signed_net=np.trapezoid(net, t, axis=0),
        gross_inward=np.trapezoid(np.maximum(rates, 0).sum(axis=2), t, axis=0),
        gross_outward=np.trapezoid(np.maximum(-rates, 0).sum(axis=2), t, axis=0))
    thin = sorted(set(list(range(0, len(t), 2)) + [len(t) - 1]))
    integrals["thinned_signed_net"] = np.trapezoid(net[thin], t[thin], axis=0)
    for k, v in integrals.items():
        checks[k + "_independently_integrated"] = np.allclose(v, record["exchange"][k], rtol=1e-10, atol=1e-18)
    error = float(np.max(np.abs(integrals["signed_net"] - integrals["thinned_signed_net"])))
    checks["quadrature_difference_recomputed"] = np.isclose(error, record["exchange"]["quadrature_max_abs_difference"], rtol=1e-9, atol=1e-16)
    checks["initial_and_terminal_net_rates_recomputed"] = np.allclose(net[0], record["initial_net_rate"], rtol=1e-10, atol=1e-20) and np.allclose(terminal.sum(axis=1), record["terminal_net_rate"], rtol=1e-10, atol=1e-20)
    checks["in_minus_out_equals_net"] = np.allclose(integrals["gross_inward"] - integrals["gross_outward"], integrals["signed_net"], rtol=1e-10, atol=1e-18)
    mir = indices["miR200_total"]
    row = dict(miRNA_signed_net=float(integrals["signed_net"][mir]), miRNA_gross_inward=float(integrals["gross_inward"][mir]),
        miRNA_gross_outward=float(integrals["gross_outward"][mir]), initial_miRNA_net_rate=float(net[0, mir]),
        terminal_miRNA_net_rate=float(terminal[mir].sum()), initial_receiver_vm=float(vm[0, 0]),
        initial_cue_vm=vm[0, 1:].tolist(), quadrature_max_abs_difference=error,
        maximum_native_formula_abs_difference=record["maximum_native_formula_abs_difference"],
        signed_net_by_species={n: float(integrals["signed_net"][i]) for n, i in indices.items()})
    return row, {k: bool(v) for k, v in checks.items()}


def audit_exposure(folder, inputs, config, case, indices):
    original, groups, ids, cue_ids, seen, source, checks = audit_histories(inputs, config, case, indices)
    saved, result = arrays(folder / "endpoints.npz"), json.loads((folder / "result.json").read_text())
    checks.update({
        "selected_history_ids_preserved": result["incoming_ids"] == result["outgoing_ids"] == ids and result["cue_ids"] == cue_ids,
        "no_new_prepared_cells_or_selective_edits": result["new_reference_edits"] == result["cue_refresh_count"] == 0,
        "reused_cell_counts": result["reused_receiver_instances"] == 2 and result["reused_cue_instances"] == 10,
        "one_probe_two_holds_per_receiver": len(result["audits"]) == 6 and len(result["setups"]) == 4 and len(result["deliveries"]) == 2,
        "onward_transport_unaffected_by_probe_block": case["history"] == "learned",
    })
    rows, packets, contact_groups, deliveries = [], [], [], []
    for j, group in enumerate(groups):
        tag = f"carrier_{j + 1}"
        checks[tag + "/whole_cell_crossover_exact"] = np.array_equal(saved[tag + "_initial"], group)
        offset = 3 * j
        state, row, pc = check_phase(folder, tag + "_probe", 10, indices, group, 6, case["condition"] == "pulse", 2e-15,
            result["audits"][offset], result["setups"][2 * j])
        checks.update({tag + "/probe/" + k: v for k, v in pc.items()})
        checks[tag + "/probe_saved"] = np.array_equal(state, saved[tag + "_contact"])
        contact_groups.append(state.copy())
        contact_label = row["recipient_label"]
        cue_labels = "".join(classify(state, indices)[1:])
        delivery, dc = audit_delivery(folder, tag, case, indices, result["deliveries"][j])
        checks.update({tag + "/delivery/" + k: v for k, v in dc.items()})
        deliveries.append(delivery)
        state = state[:, :1].copy()
        holds = []
        for k in range(2):
            state, row, pc = check_phase(folder, tag + f"_hold_{k + 1}", 10000, indices, state, 1, False, 2e-15,
                result["audits"][offset + k + 1], result["setups"][2 * j + 1] if k == 0 else None)
            checks.update({tag + f"/hold_{k + 1}/" + key: v for key, v in pc.items()})
            holds.append(row)
            if k == 0:
                first = state.copy()
                checks[tag + "/first_hold_saved"] = np.array_equal(first, saved[tag + "_held_first"])
        checks[tag + "/actual_receiver_not_cue_forwarded"] = np.array_equal(state, saved["continuing_packet"][:, j:j + 1])
        retained = contact_label == case["state"] and all(h["recipient_label"] == case["state"] and h["late_label_fractions"][case["state"]] >= .95 for h in holds)
        record = dict(id=ids[j], initial_label=str(classify(group, indices)[0]), contact_label=contact_label,
            cue_end_labels=cue_labels, holds=holds, retained_switch=bool(retained), ion_hold_drift=float(np.max(np.abs(state[:4] - first[:4]))))
        checks[tag + "/carrier_record_reconstructed"] = all(result["carriers"][j][k] == v for k, v in record.items() if k != "holds")
        checks[tag + "/hold_records_match"] = result["carriers"][j]["holds"] == result["audits"][offset + 1:offset + 3]
        rows.append(record)
        packets.append(state)
    retained = all(r["retained_switch"] for r in rows)
    initial = all(r["initial_label"] == case["state"] for r in rows)
    checks["starting_and_strict_target_endpoints_recomputed"] = result["retained_switch"] == retained and result["target_pair_at_start"] == initial
    exposure = dict(carriers=rows, deliveries=deliveries, retained_switch=retained, target_pair_at_start=initial)
    return np.concatenate(packets, axis=1), ids, seen, source, exposure, {k: bool(v) for k, v in checks.items()}, result["audits"], np.concatenate(contact_groups, axis=1), original


def panel_summary(branches):
    panel = {}
    for origin in ("E", "M"):
        by = {(b["case"]["receiver_history"], b["case"]["cue_history"], b["case"]["condition"], b["case"]["fine"]): b
            for b in branches if b["case"]["origin_state"] == origin}
        rows = []
        for rh in (1, 0):
            for ch in (1, 0):
                a, b, f = (by[(rh, ch, c, n)] for c, n in (("pulse", False), ("blocked", False), ("pulse", True)))
                rows.append(dict(combination=f"R{rh}C{ch}", starting_labels="".join(c["initial_label"] for c in a["exposure"]["carriers"]),
                    active_outcomes=a["outcomes"], blocked_outcomes=b["outcomes"], fine_outcomes_agree=a["outcomes"] == f["outcomes"],
                    target_persists_without_final_contact=b["outcomes"]["durable_rewrite"],
                    active_succeeds_blocked_fails=a["outcomes"]["durable_rewrite"] and not b["outcomes"]["durable_rewrite"],
                    active_probe_delivery=a["exposure"]["deliveries"]))
        panel[origin + "_to_" + opposite(origin) + "_to_" + origin] = rows
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
        folder = run / case["id"]
        packet, ids, seen, source, exposure, ec, ea, contact, original = audit_exposure(folder / "exposure", inputs, config, case, indices)
        checks[case["id"] + "/exposure"] = ec
        audits.extend(ea)
        start, old_ids, initial_seen = packet.copy(), ids.copy(), len(seen)
        endpoints[case["id"]] = dict(contact_groups=contact, after_holds=start)
        fresh = refs["prepared"][:, {"E": 0, "M": 1}[case["old_state"]], None]
        rounds = []
        for n in (4, 5):
            end, row, rc, pa = audit_round(folder / f"round_{n:02}", config, case, n, packet, ids, seen, fresh, refs["later"], indices)
            packet, ids = end["outgoing_packet"], [c["id"] for c in row["children"]]
            seen.update(ids)
            rounds.append(row)
            audits.extend(pa)
            checks[f"{case['id']}/round_{n:02}"] = rc
            endpoints[case["id"]][str(n)] = packet
        outcomes = reconstruct_writing(exposure, rounds, case["state"], .95)
        saved, result = arrays(folder / "endpoints.npz"), json.loads((folder / "result.json").read_text())
        checks[case["id"]] = {
            "case_record_correct": result["case"] == case and result["execution_pass"] and result["ion_indices"] == indices,
            "source_and_counterfactual_provenance_correct": result["source"] == source == json.loads((folder / "source.json").read_text()),
            "older_lineage_source_saved": np.array_equal(saved["source_packet"], original),
            "actual_held_pair_seeds_relay": np.array_equal(saved["continuing_start"], start),
            "fresh_target_saved": np.array_equal(saved["fresh_target"], fresh),
            "recipient_opposes_target": classify(fresh, indices).tolist() == [opposite(case["state"])] == [case["old_state"]],
            "actual_final_packet_saved": np.array_equal(saved["final_packet"], packet),
            "final_ids_match_and_exclude_history": result["final_ids"] == ids and not (set(ids) & set(source["history"]["excluded_ids"])),
            "four_fresh_recipients": result["distinct_fresh_targets"] == len(seen) - initial_seen == 4,
            "historical_cues_and_receivers_reused": result["reused_cue_instances"] == 10 and result["reused_receiver_instances"] == 2,
            "exposure_record_matches": result["exposure"] == json.loads((folder / "exposure/result.json").read_text()),
            "six_outcomes_recomputed": all(result[k] == v for k, v in outcomes.items()),
            "legacy_strict_endpoint_preserved": result["retained_switch"] == exposure["retained_switch"] and outcomes["prompt_rewrite"] == (exposure["retained_switch"] and outcomes["new_state_transmitted"]),
            "nominal_clock_correct": result["nominal_schedule"] == [dict(round=4, start=109090, end=131090), dict(round=5, start=131090, end=153090)],
        }
        branches.append(dict(case=case, exposure=exposure, rounds=rounds, outcomes=outcomes))
    prior = json.loads((run / "predecessor_audit.json").read_text())
    old_summary = json.loads((inputs / "previous_summary.json").read_text())
    checks["historical_reuse"] = {
        "prior_16296_checks_pass": prior["array_check_count"] == 16296 and prior["all_array_checks_pass"] and all(all(c.values()) for c in prior["array_checks"].values()),
        "correct_complete_predecessor": len(prior["branches"]) == 32 and old_summary["all_execution_valid"] and old_summary["started_utc"] == "20260906T130210Z",
        "29_fixed_inputs": len(summary["inputs"]) == 29,
        "all_checkpoints_baseline_same_age": all(c["history_age"] == 80 and c["source_settings"] == "baseline" for c in [json.loads((run / b["case"]["id"] / "source.json").read_text())["history"] for b in branches]),
        "new_costs_exclude_reused_priming": len(branches) == 24 and len(audits) == 672,
    }
    fine, historical = {}, {}
    for b in branches:
        c = b["case"]
        if c["fine"]:
            name = c["id"].removesuffix("_fine")
            base = next(v for v in branches if v["case"]["id"] == name)
            fine[name] = dict(same_outcomes=b["outcomes"] == base["outcomes"], source_refinement=False,
                endpoints={s: comparison(a, endpoints[c["id"]][s], indices, reg, scales) for s, a in endpoints[name].items()},
                delivery_net_miRNA_absolute_differences=[abs(a["miRNA_signed_net"] - d["miRNA_signed_net"]) for a, d in zip(base["exposure"]["deliveries"], b["exposure"]["deliveries"])])
        if c["receiver_history"] == c["cue_history"] == 1 and c["condition"] == "pulse" and not c["fine"]:
            previous = np.concatenate([arrays(inputs / f"benchmark_{c['origin_state'].lower()}_carrier_{i}_pulse_05.npz")["final"] for i in (1, 2)], axis=1)
            historical[c["id"]] = dict(historical_reuse=True, comparison=comparison(previous, endpoints[c["id"]]["contact_groups"], indices, reg, scales),
                bitwise_same=bool(np.array_equal(previous, endpoints[c["id"]]["contact_groups"])))
    children = [c for b in branches for r in b["rounds"] for c in r["children"]]
    carriers = [c for b in branches for c in b["exposure"]["carriers"]]
    deliveries = [d for b in branches for d in b["exposure"]["deliveries"]]
    return dict(run=str(run), all_array_checks_pass=all(all(c.values()) for c in checks.values()), array_checks=checks,
        array_check_count=sum(len(c) for c in checks.values()),
        input_hashes_valid=all(file_hash(inputs / n) == v["sha256"] for n, v in summary["inputs"].items()),
        original_inputs_hashes_valid=all(file_hash(Path(v["source"])) == v["sha256"] for v in summary["inputs"].values()),
        frozen_hashes_valid=all(file_hash(run / "frozen" / n) == h for n, h in summary["frozen_hashes_sha256"].items()),
        execution_files_hashes_valid=all(file_hash(run.parents[1] / n) == h for n, h in summary["hashes_sha256"].items()),
        predecessor_audit_hash_valid=file_hash(run / "predecessor_audit.json") == summary["predecessor_audit_sha256"],
        branches=branches, history_panel=panel_summary(branches), fine_comparisons=fine, historical_pulse5_comparisons=historical,
        new_fresh_targets=len(children), complete_pair_replacements=2 * len(branches),
        reused_receiver_placements=2 * len(branches), reused_cue_placements=10 * len(branches),
        new_integrations=len(audits), new_snapshots=sum(a["samples"] for a in audits),
        all_new_recipients_locally_recovered=all(c["recovery"]["recovered"] for c in children),
        maximum_new_recovery_distance=max(c["recovery"]["final_distance"] for c in children),
        maximum_new_ion_hold_drift=max(c["ion_hold_drift"] for c in children + carriers),
        maximum_native_flux_formula_abs_difference=max(d["maximum_native_formula_abs_difference"] for d in deliveries),
        maximum_delivery_quadrature_difference=max(d["quadrature_max_abs_difference"] for d in deliveries),
        elapsed_seconds=summary["elapsed_seconds"], new_integration_cpu_seconds=sum(a["cpu_seconds"] for a in audits))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    report = analyze(args.run.resolve())
    if args.compact:
        report["failed_checks"] = {k: [n for n, v in c.items() if not v] for k, c in report.pop("array_checks").items() if not all(c.values())}
        report["branches"] = [dict(id=b["case"]["id"], **b["outcomes"], target_pair_at_start=b["exposure"]["target_pair_at_start"],
            outgoing=[r["outgoing_labels"] for r in b["rounds"]]) for b in report["branches"]]
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if all(report[k] for k in ("all_array_checks_pass", "input_hashes_valid", "original_inputs_hashes_valid", "frozen_hashes_valid", "execution_files_hashes_valid", "predecessor_audit_hash_valid")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
