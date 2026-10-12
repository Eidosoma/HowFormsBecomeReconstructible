"""Independent seeded-stress, loss, timing, state-continuity and relay audit."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_commitment_components import FLAGS, canonical_state
from analyze_group_transfer import arrays
from analyze_pulse_spacing import check_phase, comparison
from memory_metrics import REGULATORS, classify, opposite, perturb_recipient, regulatory_distance, recovery_decision
from run_memory_probe import array_hash, write_json
from run_onward_transfer import file_hash, retained_label


def expected_design(case):
    seed = 2026090602 if case["profile"] == "validation" else 2026090601
    generator = np.random.Generator(np.random.PCG64(seed))
    multipliers = 1 + generator.uniform(-.1, .1, (3, 6))
    timing = [int(v) for v in generator.integers(0, 2, 2)]
    keep = [int(v) for v in generator.integers(0, 2, 2)]
    p = case["profile"]
    applied = multipliers if p in ("jitter", "combined", "validation") else np.ones((3, 6))
    rounds = []
    for j in range(2):
        times = [1000, 1000]
        if p in ("timing", "combined", "validation"):
            times = [500, 1500] if timing[j] == 0 else [1500, 500]
        columns = [keep[j]] if p in ("loss", "combined", "validation") else [0, 1]
        rounds.append(dict(round=4 + j, contacts=times, active_columns=columns))
    return dict(seed=seed, generator="PCG64", raw_multipliers=multipliers.tolist(), multipliers=applied.tolist(),
        timing_choices=timing, survivor_choices=keep, rounds=rounds)


def audit_source(inputs, case, refs, indices):
    background = case["background"]
    source_case = None if background == "ordinary" else "m_components_" + {
        "transient": "000", "protein": "001", "rna": "010", "committed": "111"}[background] + ("_fine" if case["fine"] else "")
    ids = [case["id"] + f":placed:carrier_{i}" for i in (1, 2)]
    checks = {}
    if source_case is None:
        packet = np.column_stack((refs["prepared"][:, 1], refs["prepared"][:, 1]))
        seen = set()
        record = dict(background="ordinary", previous_case=None, file="references.npz", key="prepared", column=1,
            source_ids=[], excluded_predecessor_assay_ids=[], ordinary_not_age_matched=True)
        checks["ordinary_uses_prepared_baseline_not_fine_history"] = not case["fine"]
    else:
        meta = json.loads((inputs / (source_case + ".json")).read_text())
        saved = arrays(inputs / (source_case + "_entry.npz"))
        packet = saved["canonical_entry"].copy()
        prior_ids = [i for r in meta["rounds"] for i in r["outgoing_ids"]]
        seen = set(meta["source"]["excluded_ids"]) | set(prior_ids)
        checks.update(dict(source_identity=meta["case"]["id"] == source_case and meta["case"]["fine"] == case["fine"],
            source_phenotype=meta["execution_pass"] and meta["durable_M"] == (background != "transient"),
            complete_predecessor_exclusions=len(meta["source"]["excluded_ids"]) == 32 and len(set(prior_ids)) == 4 and len(seen) == 36,
            source_placements_named=meta["retention"]["incoming_ids"] == meta["source"]["intervention_ids"] and set(meta["source"]["intervention_ids"]).issubset(seen)))
        record = dict(background=background, previous_case=source_case, file=source_case + "_entry.npz", key="canonical_entry",
            source_ids=meta["source"]["intervention_ids"], excluded_predecessor_assay_ids=prior_ids, ordinary_not_age_matched=False)
    checks.update(dict(full_M_source=packet.shape == (17, 2) and classify(packet, indices).tolist() == ["M", "M"],
        source_finite_nonnegative=np.isfinite(packet).all() and np.all(packet >= 0),
        source_fixed_species=np.all(packet[4] == 72) and np.all(packet[16] == 0),
        source_is_canonical=np.allclose(packet, canonical_state(packet), rtol=1e-12, atol=1e-14),
        new_fork_ids=len(set(ids)) == 2 and not (set(ids) & seen)))
    seen.update(ids)
    record.update(placement_ids=ids, excluded_ids=sorted(seen), source_before_holds=True, artificial_placements=True)
    return packet, ids, seen, record, {k: bool(v) for k, v in checks.items()}


def audit_holds(folder, initial, ids, indices):
    result, end = json.loads((folder / "result.json").read_text()), arrays(folder / "endpoints.npz")
    checks = dict(initial_edited_packet_saved=np.array_equal(end["initial_before_refresh"], initial),
        exact_placement_ids=result["incoming_ids"] == result["outgoing_ids"] == ids,
        four_isolated_phases=len(result["audits"]) == 4 and len(result["setups"]) == 2 and len(result["carriers"]) == 2,
        no_cue_or_contact=result["new_cue_instances"] == result["new_contacts"] == 0,
        canonical_entry_matches_native_formula=np.allclose(end["canonical_entry"], canonical_state(initial), rtol=1e-12, atol=1e-14),
        canonical_entry_preserves_primaries=np.array_equal(end["canonical_entry"][:8], initial[:8]))
    rows, packets = [], []
    for j in range(2):
        tag, state, holds = f"carrier_{j + 1}", initial[:, j:j + 1], []
        for k in range(2):
            name = tag + f"_hold_{k + 1}"
            state, row, pc = check_phase(folder, name, 10000, indices, state, 1, False, 2e-15,
                result["audits"][2 * j + k], result["setups"][j] if k == 0 else None)
            checks.update({name + "/" + n: v for n, v in pc.items()})
            raw = arrays(folder / (name + ".npz"))
            checks[name + "/canonical_initial_final"] = all(np.allclose(raw[s], canonical_state(raw[s]), rtol=1e-12, atol=1e-14) for s in ("initial", "final"))
            holds.append(row)
            if k == 0:
                first = state.copy()
                checks[tag + "/first_hold_saved"] = np.array_equal(first, end["held_first"][:, j:j + 1])
                checks[tag + "/canonical_entry_is_phase_entry"] = np.array_equal(raw["initial"], end["canonical_entry"][:, j:j + 1])
        checks[tag + "/actual_held_carrier_forwarded"] = np.array_equal(state, end["continuing_packet"][:, j:j + 1])
        retained = all(h["recipient_label"] == "M" and h["late_label_fractions"]["M"] >= .95 for h in holds)
        row = dict(id=ids[j], entry_label=str(classify(initial[:, j:j + 1], indices)[0]), holds=holds,
            M_retained=retained, ion_hold_drift=float(np.max(np.abs(state[:4] - first[:4]))))
        checks[tag + "/carrier_outcome_recomputed"] = all(result["carriers"][j][k] == v for k, v in row.items() if k != "holds")
        checks[tag + "/hold_metadata_matches"] = result["carriers"][j]["holds"] == result["audits"][2 * j:2 * j + 2]
        rows.append(row)
        packets.append(state)
    retained = all(r["M_retained"] for r in rows)
    checks["pair_retention_recomputed"] = result["M_retained"] == retained
    return np.concatenate(packets, axis=1), dict(carriers=rows, M_retained=retained), {k: bool(v) for k, v in checks.items()}, result["audits"]


def audit_round(folder, config, case, number, incoming, ids, seen, fresh, later, indices, plan):
    result, end = json.loads((folder / "result.json").read_text()), arrays(folder / "endpoints.npz")
    columns, durations = plan["active_columns"], plan["contacts"]
    active = incoming[:, columns]
    phase_names = ["write_1", "write_2", "wait_1", "child_1_hold_1", "child_1_hold_2", "child_2_hold_1", "child_2_hold_2",
        "child_1_shadow", "child_1_challenge", "child_2_shadow", "child_2_challenge"]
    setups = {r["phase"]: r for r in result["setups"]}
    phase_records = {r["phase"]: r for r in result["audits"]}
    checks = dict(fixed_phase_order=[r["phase"] for r in result["audits"]] == phase_names,
        exact_builds=len(result["setups"]) == 9 and set(setups) == set(phase_names) - {"child_1_hold_2", "child_2_hold_2"},
        exact_incoming_pair=np.array_equal(end["incoming_packet"], incoming) and result["incoming_ids"] == ids,
        exact_active_selection=np.array_equal(end["active_packet"], active) and result["active_ids"] == [ids[j] for j in columns],
        exact_loss_no_dummy_or_rescue=result["lost_ids"] == [ids[j] for j in range(2) if j not in columns] and active.shape[1] == len(columns),
        exact_fresh_targets=np.array_equal(end["fresh_targets"], fresh) and classify(fresh, indices).tolist() == ["E", "E"],
        exact_schedule=result["plan"] == plan and sum(durations) == 2000,
        execution_and_indices=result["execution_pass"] and result["ion_indices"] == indices and result["round"] == number,
        incoming_hash=result["incoming_packet_hash"] == array_hash(incoming))

    def phase(name, initial, duration, connected=False):
        final, row, pc = check_phase(folder, name, duration, indices, initial, initial.shape[1], connected,
            2e-15, phase_records[name], setups.get(name))
        checks.update({name + "/" + k: v for k, v in pc.items()})
        raw = arrays(folder / (name + ".npz"))
        checks[name + "/canonical_initial_final"] = all(np.allclose(raw[s], canonical_state(raw[s]), rtol=1e-12, atol=1e-14) for s in ("initial", "final"))
        return final, row

    initial1 = np.concatenate((fresh[:, :1], active), axis=1)
    contact1, write1 = phase("write_1", initial1, durations[0], True)
    initial2 = np.concatenate((fresh[:, 1:2], contact1[:, 1:]), axis=1)
    contact2, write2 = phase("write_2", initial2, durations[1], True)
    waited, wait = phase("wait_1", contact1[:, :1], durations[1])
    checks.update(dict(first_write_exact=np.array_equal(end["first_initial"], initial1),
        second_write_uses_evolved_survivors=np.array_equal(end["second_initial"], initial2),
        exact_contact_endpoints=np.array_equal(end["contact_1"], contact1) and np.array_equal(end["contact_2"], contact2),
        exact_first_child_wait=np.array_equal(end["child_1_waited"], waited)))
    children, firsts, held = [], [], []
    for j, child in enumerate((waited, contact2[:, :1])):
        first, h1 = phase(f"child_{j + 1}_hold_1", child, 10000)
        checkpoint, h2 = phase(f"child_{j + 1}_hold_2", first, 10000)
        firsts.append(first)
        children.append(checkpoint)
        held.append([h1, h2])
    packet = np.concatenate(children, axis=1)
    reg = [indices[n] for n in REGULATORS]
    scales = np.abs(later[reg, 0] - later[reg, 1])
    new_ids = [case["id"] + f":round_{number:02}:child_{i}" for i in (1, 2)]
    rows = []
    for j, (child, holds, write) in enumerate(zip(children, held, (write1, write2))):
        tag = f"child_{j + 1}"
        before = str(classify(child, indices)[0])
        target = opposite(before if before in ("E", "M") else "E")
        changed = perturb_recipient(child, later[:, {"E": 0, "M": 1}[target]], reg, .2)
        shadow, sh = phase(tag + "_shadow", child, 5000)
        challenged, ch = phase(tag + "_challenge", changed, 5000)
        d0 = regulatory_distance(changed[reg, 0], child[reg, 0], scales)
        dfinal = regulatory_distance(challenged[reg, 0], shadow[reg, 0], scales)
        recovery = recovery_decision(d0, dfinal, before, sh["recipient_label"], ch["recipient_label"], config)
        written = write["recipient_label"]
        retained = retained_label(written, holds, sh["recipient_label"], .95)
        wait_ok = j == 1 or (written in ("E", "M") and wait["recipient_label"] == written and wait["late_label_fractions"][written] >= .95)
        row = dict(id=new_ids[j], contact_label=written, retained_label=before, wait_preserved_label=bool(wait_ok),
            retained_contact_label=retained, recovery=recovery, durable_transfer=bool(written == "M" and wait_ok and retained and recovery["recovered"]),
            ion_hold_drift=float(np.max(np.abs(child[:4] - firsts[j][:4]))))
        checks.update({tag + "/diagnostic_endpoints": all(np.array_equal(end[k][:, j:j + 1], v) for k, v in
            (("perturbed_packet", changed), ("shadow_packet", shadow), ("challenged_packet", challenged))),
            tag + "/recovery_and_outcomes_recomputed": result["children"][j] == row,
            tag + "/matched_diagnostic_environment": setups[tag + "_shadow"]["environment_hash"] == setups[tag + "_challenge"]["environment_hash"]})
        rows.append(dict(row, holds=holds))
    success = all(c["durable_transfer"] for c in rows)
    checks.update(dict(actual_held_pair_not_diagnostics=np.array_equal(end["outgoing_packet"], packet) and np.array_equal(end["held_first"], np.concatenate(firsts, axis=1)),
        fresh_unique_ids=result["outgoing_ids"] == new_ids and len(set(new_ids)) == 2 and not (set(new_ids) & seen),
        outgoing_hash=result["outgoing_packet_hash"] == array_hash(packet),
        scales_correct=np.array_equal(end["regulator_scales"], scales),
        diagnostics_excluded=result["diagnostic_branches_enter_lineage"] is False,
        round_success_recomputed=result["round_success"] == success,
        correct_common_clock=result["nominal_round_start"] == 20000 + (number - 4) * 22000 and result["nominal_round_end"] == 42000 + (number - 4) * 22000))
    row = dict(round=number, plan=plan, incoming_labels="".join(classify(incoming, indices)),
        active_labels="".join(classify(active, indices)), outgoing_labels="".join(classify(packet, indices)),
        lost_ids=result["lost_ids"], children=rows, round_success=success)
    return packet, new_ids, row, {k: bool(v) for k, v in checks.items()}, result["audits"]


def audit_branch(folder, inputs, config, case, indices, refs):
    source, ids, seen, provenance, sc = audit_source(inputs, case, refs, indices)
    plan = expected_design(case)
    factors = np.array(plan["multipliers"])
    initial = source.copy()
    initial[5:8] = source[5:8] * factors[:, :2]
    fresh = np.column_stack([refs["prepared"][:, 0]] * 4)
    fresh[5:8] *= factors[:, 2:]
    packet, retention, hc, audits = audit_holds(folder / "retention", initial, ids, indices)
    start, initial_seen, rounds = packet.copy(), len(seen), []
    checks = {case["id"] + "/source": sc, case["id"] + "/retention": hc}
    endpoints = dict(source=source, perturbed_entry=initial, fresh_targets=fresh, after_holds=packet)
    for j, n in enumerate((4, 5)):
        packet, ids, row, rc, pa = audit_round(folder / f"round_{n:02}", config, case, n, packet, ids, seen,
            fresh[:, 2 * j:2 * j + 2], refs["later"], indices, plan["rounds"][j])
        seen.update(ids)
        rounds.append(row)
        audits.extend(pa)
        endpoints[str(n)] = packet
        checks[case["id"] + f"/round_{n:02}"] = rc
    outcomes = dict(M_retained=retention["M_retained"], M_renewed=all(r["round_success"] for r in rounds))
    outcomes["durable_M"] = all(outcomes.values())
    failure = "retention" if not outcomes["M_retained"] else next((f"round_{r['round']}" for r in rounds if not r["round_success"]), None)
    result, end = json.loads((folder / "result.json").read_text()), arrays(folder / "endpoints.npz")
    checks[case["id"]] = dict(case_and_indices=result["case"] == case and result["execution_pass"] and result["ion_indices"] == indices,
        source_record_reconstructed=result["source"] == provenance == json.loads((folder / "source.json").read_text()),
        exact_seeded_design=result["design"] == plan == json.loads((folder / "design.json").read_text()) and case["seed"] == plan["seed"],
        exact_initial_source_and_perturbation=np.array_equal(end["source_packet"], source) and np.array_equal(end["perturbed_entry"], initial),
        exact_fresh_perturbations=np.array_equal(end["fresh_targets"], fresh) and classify(fresh, indices).tolist() == ["E"] * 4,
        actual_held_pair_starts_relay=np.array_equal(end["continuing_start"], start),
        actual_final_pair=np.array_equal(end["final_packet"], packet),
        final_ids_disjoint=result["final_ids"] == ids and not (set(ids) & set(provenance["excluded_ids"])),
        four_fresh_recipients=result["distinct_fresh_targets"] == len(seen) - initial_seen == 4,
        exact_loss_count=result["lost_carriers"] == sum(len(r["lost_ids"]) for r in rounds) == (2 if case["profile"] in ("loss", "combined", "validation") else 0),
        outcomes_recomputed=all(result[k] == v for k, v in outcomes.items()) and result["first_failed_stage"] == failure,
        retention_record_matches=result["retention"] == json.loads((folder / "retention/result.json").read_text()),
        exact_26_integrations=len(audits) == 26)
    return dict(case=case, source=provenance, retention=retention, rounds=rounds, outcomes=outcomes,
        first_failed_stage=failure), endpoints, checks, audits


def summarize_panel(branches):
    result = {}
    for background in ("transient", "protein", "rna", "committed", "ordinary"):
        by = {b["case"]["profile"]: b for b in branches if b["case"]["background"] == background and not b["case"]["fine"]}
        base = by["none"]["outcomes"]["durable_M"]
        rows = [dict(profile=p, **by[p]["outcomes"], first_failed_stage=by[p]["first_failed_stage"],
            durable_difference_from_unstressed=int(by[p]["outcomes"]["durable_M"]) - int(base))
            for p in ("none", "jitter", "timing", "loss", "combined", "validation")]
        result[background] = dict(rows=rows, both_combined_draws_durable=all(by[p]["outcomes"]["durable_M"] for p in ("combined", "validation")),
            seed_generalization_established=False, ecological_fitness_measured=False)
    return result


def analyze(run):
    summary = json.loads((run / "summary.json").read_text())
    if not summary.get("all_execution_valid"):
        raise ValueError("Require a completed valid robustness suite")
    config, inputs = summary["config"], run / "inputs"
    refs = arrays(inputs / "references.npz")
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    reg = [indices[n] for n in REGULATORS]
    scales = np.abs(refs["later"][reg, 0] - refs["later"][reg, 1])
    branches, endpoints, checks, audits = [], {}, {}, []
    for case in config["cases"]:
        b, e, bc, pa = audit_branch(run / case["id"], inputs, config, case, indices, refs)
        branches.append(b)
        endpoints[case["id"]] = e
        checks.update(bc)
        audits.extend(pa)
    prior = json.loads((run / "predecessor_audit.json").read_text())
    old_summary = json.loads((inputs / "components_summary.json").read_text())
    expected = {(b, p, False) for b in ("transient", "protein", "rna", "committed", "ordinary") for p in ("none", "jitter", "timing", "loss", "combined", "validation")}
    expected |= {(b, p, True) for b in ("protein", "rna") for p in ("none", "combined", "validation")}
    checks["panel"] = dict(fixed_36_cases=len(branches) == 36 and len({b["case"]["id"] for b in branches}) == 36 and
        {(b["case"]["background"], b["case"]["profile"], b["case"]["fine"]) for b in branches} == expected,
        source_qualified=prior["eligible_for_stage2_design"] and all(prior[k] for k in FLAGS) and prior["array_check_count"] == 3893 and
        all(all(c.values()) for c in prior["array_checks"].values()),
        source_run_correct=old_summary["started_utc"] == "20260906T171654Z" and old_summary["all_execution_valid"],
        input_and_integration_count=len(summary["inputs"]) == 27 and len(audits) == 936,
        predeclared_stress_values=config["jitter_fraction"] == .1 and config["jitter_indices"] == [5, 6, 7] and config["irregular_contacts"] == [500, 1500] and
        config["seeds"] == dict(screen=2026090601, validation=2026090602))
    controls, fine = {}, {}
    for b in branches:
        c, name = b["case"], b["case"]["id"]
        if c["profile"] == "none" and c["background"] != "ordinary":
            old = b["source"]["previous_case"]
            metadata = json.loads((inputs / (old + ".json")).read_text())
            bank = dict(after_holds=arrays(inputs / (old + "_entry.npz"))["continuing_packet"])
            bank.update({str(n): arrays(inputs / (old + f"_round_{n:02}.npz"))["outgoing_packet"] for n in (4, 5)})
            controls[name] = dict(same_outcomes=all(b["outcomes"][k] == metadata[k] for k in b["outcomes"]),
                endpoints={k: dict(bitwise_same=np.array_equal(v, endpoints[name][k]),
                    **comparison(v, endpoints[name][k], indices, reg, scales)) for k, v in bank.items()})
        if c["fine"]:
            base_name = name.removesuffix("_fine")
            base = next(v for v in branches if v["case"]["id"] == base_name)
            fine[name] = dict(same_outcomes=b["outcomes"] == base["outcomes"] and b["first_failed_stage"] == base["first_failed_stage"],
                fine_source_prefix=True, older_lineage_refined=False,
                endpoints={k: comparison(v, endpoints[name][k], indices, reg, scales) for k, v in endpoints[base_name].items()})
    control_gate = len(controls) == 6 and all(c["same_outcomes"] and all(e["bitwise_same"] for e in c["endpoints"].values()) for c in controls.values())
    fine_gate = len(fine) == 6 and all(c["same_outcomes"] and all(e["same_labels"] for e in c["endpoints"].values()) for c in fine.values())
    children = [c for b in branches for r in b["rounds"] for c in r["children"]]
    report = dict(run=str(run), all_array_checks_pass=all(all(c.values()) for c in checks.values()),
        array_checks=checks, array_check_count=sum(len(c) for c in checks.values()),
        input_hashes_valid=all(file_hash(inputs / n) == v["sha256"] for n, v in summary["inputs"].items()),
        original_inputs_hashes_valid=all(file_hash(Path(v["source"])) == v["sha256"] for v in summary["inputs"].values()),
        frozen_hashes_valid=all(file_hash(run / "frozen" / n) == h for n, h in summary["frozen_hashes_sha256"].items()),
        execution_files_hashes_valid=all(file_hash(run.parents[1] / n) == h for n, h in summary["hashes_sha256"].items()),
        predecessor_audit_hash_valid=file_hash(run / "predecessor_audit.json") == summary["predecessor_audit_sha256"],
        branches=branches, controls=controls, fine_comparisons=fine, panel=summarize_panel(branches),
        unchanged_controls_reproduced=control_gate, all_tested_fine_outcomes_and_labels_agree=fine_gate,
        new_integrations=len(audits), new_snapshots=sum(a["samples"] for a in audits),
        fresh_recipients=len(children), complete_pair_replacements=2 * len(branches), initial_placements=2 * len(branches),
        lost_carriers=sum(len(r["lost_ids"]) for b in branches for r in b["rounds"]), new_cue_instances=0,
        all_recipients_locally_recovered=all(c["recovery"]["recovered"] for c in children),
        maximum_recovery_distance=max(c["recovery"]["final_distance"] for c in children),
        elapsed_seconds=summary["elapsed_seconds"], integration_cpu_seconds=sum(a["cpu_seconds"] for a in audits))
    report["ready_for_stage3_design"] = all(report[k] for k in FLAGS) and control_gate and fine_gate
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()
    run = args.run.resolve()
    report = analyze(run)
    if args.save:
        write_json(run / "independent_audit.json", report)
    if args.compact:
        report["failed_checks"] = {k: [n for n, v in c.items() if not v] for k, c in report.pop("array_checks").items() if not all(c.values())}
        report["branches"] = [dict(id=b["case"]["id"], **b["outcomes"], first_failed_stage=b["first_failed_stage"]) for b in report["branches"]]
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if all(report[k] for k in FLAGS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
