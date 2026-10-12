"""Independent source, variable-contact, donor-trajectory and renewal audit."""

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
    # Deliberately separate protocol reconstruction from the runner.
    settings = {
        "pair": (2, 1000, 2e-15), "single": (1, 1000, 2e-15),
        "single_long": (1, 2000, 2e-15), "single_longer": (1, 4000, 2e-15),
        "single_strong": (1, 1000, 4e-15), "single_weak": (1, 1000, 1e-15),
        "pair_weak": (2, 1000, 1e-15)}
    donors, duration, kd = settings[case["profile"]]
    profile = dict(id=case["profile"], donors=donors, contact_horizon=duration, kd_factor=kd/2e-15)
    rounds = [dict(round=n, contacts=[duration, duration], active_columns=[n-4] if donors == 1 else [0, 1],
        write_kd=kd, nominal_start=20000+(n-4)*(2*duration+20000),
        nominal_end=20000+(n-3)*(2*duration+20000)) for n in (4, 5)]
    return dict(profile=profile, rounds=rounds)


def audit_source(inputs, case, indices):
    name = case["background"] + "_none" + ("_fine" if case["fine"] else "")
    meta = json.loads((inputs / (name + ".json")).read_text())
    packet = arrays(inputs / (name + "_held.npz"))["continuing_packet"].copy()
    source_ids = meta["retention"]["outgoing_ids"]
    assay_ids = [i for r in meta["rounds"] for i in r["outgoing_ids"]]
    prior = set(meta["source"]["excluded_ids"]) | set(assay_ids)
    ids = [case["id"] + f":placed:carrier_{j}" for j in (1, 2)]
    seen = prior | set(ids)
    record = dict(previous_case=name, file=name + "_held.npz", key="continuing_packet",
        source_ids=source_ids, excluded_predecessor_ids=sorted(prior),
        excluded_predecessor_assay_ids=assay_ids, placement_ids=ids, excluded_ids=sorted(seen),
        source_after_holds=True, artificial_placements=True, new_initial_holds=0,
        ordinary_not_age_matched=case["background"] == "ordinary")
    checks = dict(
        correct_predecessor_identity=(meta["case"]["id"], meta["case"]["background"], meta["case"]["profile"], meta["case"]["fine"]) ==
            (name, case["background"], "none", case["fine"]),
        source_memory_verified=meta["execution_pass"] and meta["M_retained"] and meta["retention"]["M_retained"] and meta["durable_M"],
        predecessor_exclusion_count=len(prior) == (6 if case["background"] == "ordinary" else 42),
        correct_source_carriers=len(source_ids) == len(set(source_ids)) == 2 and set(source_ids).issubset(prior) and
            source_ids == meta["retention"]["incoming_ids"] == meta["source"]["placement_ids"],
        excluded_old_assay_descendants=len(assay_ids) == len(set(assay_ids)) == 4 and not set(assay_ids) & set(source_ids),
        fresh_fork_ids=len(set(ids)) == 2 and not (set(ids) & prior),
        full_M_pair=packet.shape == (17, 2) and classify(packet, indices).tolist() == ["M", "M"],
        finite_nonnegative=np.isfinite(packet).all() and np.all(packet >= 0),
        fixed_species=np.all(packet[4] == 72) and np.all(packet[16] == 0),
        canonical_RNA=np.allclose(packet, canonical_state(packet), rtol=1e-12, atol=1e-14),
        fine_only_for_routes=not case["fine"] or case["background"] in ("protein", "rna"))
    return packet, ids, seen, record, {k: bool(v) for k, v in checks.items()}

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
        exact_schedule=result["plan"] == plan,
        execution_and_indices=result["execution_pass"] and result["ion_indices"] == indices and result["round"] == number,
        incoming_hash=result["incoming_packet_hash"] == array_hash(incoming))

    def phase(name, initial, duration, connected=False):
        final, row, pc = check_phase(folder, name, duration, indices, initial, initial.shape[1], connected,
            plan["write_kd"], phase_records[name], setups.get(name))
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
            settled_transfer=bool(all(h["recipient_label"] == "M" and h["late_label_fractions"]["M"] >= .95 for h in holds)
                and sh["recipient_label"] == "M" and recovery["recovered"]),
            ion_hold_drift=float(np.max(np.abs(child[:4] - firsts[j][:4]))))
        checks.update({tag + "/diagnostic_endpoints": all(np.array_equal(end[k][:, j:j + 1], v) for k, v in
            (("perturbed_packet", changed), ("shadow_packet", shadow), ("challenged_packet", challenged))),
            tag + "/recovery_and_outcomes_recomputed": result["children"][j] == row,
            tag + "/matched_diagnostic_environment": setups[tag + "_shadow"]["environment_hash"] == setups[tag + "_challenge"]["environment_hash"]})
        rows.append(dict(row, holds=holds))
    success = all(c["durable_transfer"] for c in rows)
    settled = all(c["settled_transfer"] for c in rows)
    donor_history = []
    for name, contact in zip(("write_1", "write_2"), (contact1, contact2)):
        saved = arrays(folder / (name + ".npz"))
        labels = classify(saved["concentrations"], indices)
        late = labels[saved["times"] >= .75 * durations[0], 1:]
        donor_history.append(dict(phase=name, entry_labels="".join(classify(saved["initial"], indices)[1:]),
            end_labels="".join(classify(contact, indices)[1:]),
            late_M_fractions=[float(np.mean(late[:, j] == "M")) for j in range(active.shape[1])],
            end_regulators=contact[reg][:, 1:].tolist()))
    accounting = dict(active_donors=active.shape[1], total_contact_time=sum(durations),
        donor_contact_time=active.shape[1] * sum(durations),
        summed_miRNA_kd_time=active.shape[1] * plan["write_kd"] * sum(durations),
        actual_molecular_flux_measured=False, energetic_cost_measured=False)
    checks.update(dict(actual_held_pair_not_diagnostics=np.array_equal(end["outgoing_packet"], packet) and np.array_equal(end["held_first"], np.concatenate(firsts, axis=1)),
        fresh_unique_ids=result["outgoing_ids"] == new_ids and len(set(new_ids)) == 2 and not (set(new_ids) & seen),
        outgoing_hash=result["outgoing_packet_hash"] == array_hash(packet),
        scales_correct=np.array_equal(end["regulator_scales"], scales),
        diagnostics_excluded=result["diagnostic_branches_enter_lineage"] is False,
        round_success_recomputed=result["round_success"] == success and result["settled_round_success"] == settled,
        donor_history_reconstructed=result["donor_contact_history"] == donor_history,
        nominal_accounting_recomputed=result["nominal_accounting"] == accounting,
        correct_common_clock=result["nominal_round_start"] == plan["nominal_start"] and result["nominal_round_end"] == plan["nominal_end"]))
    row = dict(round=number, plan=plan, incoming_labels="".join(classify(incoming, indices)),
        active_labels="".join(classify(active, indices)), outgoing_labels="".join(classify(packet, indices)),
        lost_ids=result["lost_ids"], children=rows, round_success=success,
        settled_round_success=settled, donor_contact_history=donor_history, nominal_accounting=accounting)
    return packet, new_ids, row, {k: bool(v) for k, v in checks.items()}, result["audits"]



def audit_branch(folder, inputs, config, case, indices, refs):
    packet, ids, seen, source, sc = audit_source(inputs, case, indices)
    initial, initial_seen = packet.copy(), len(seen)
    fresh = np.column_stack([refs["prepared"][:, 0]] * 4)
    plan = expected_design(case)
    checks = {case["id"] + "/source": sc}
    rounds, audits, endpoints = [], [], dict(source=initial)
    for j, n in enumerate((4, 5)):
        stage = folder / f"round_{n:02}"
        packet, ids, row, rc, pa = audit_round(stage, config, case, n, packet, ids, seen,
            fresh[:, 2*j:2*j+2], refs["later"], indices, plan["rounds"][j])
        seen.update(ids)
        rounds.append(row)
        audits.extend(pa)
        endpoints[str(n)] = packet
        saved = arrays(stage / "endpoints.npz")
        for name in ("contact_1", "contact_2"):
            endpoints[f"{n}_{name}"] = saved[name]
        checks[case["id"] + f"/round_{n:02}"] = rc
    prompt, settled = all(r["round_success"] for r in rounds), all(r["settled_round_success"] for r in rounds)
    outcomes = dict(M_renewed=prompt, settled_M_renewed=settled, delayed_only_renewal=settled and not prompt)
    failure = next((f"round_{r['round']}" for r in rounds if not r["round_success"]), None)
    result = json.loads((folder / "result.json").read_text())
    saved = arrays(folder / "endpoints.npz")
    checks[case["id"]] = dict(
        exact_case_and_indices=result["case"] == case and result["execution_pass"] and result["ion_indices"] == indices,
        source_provenance_recomputed=result["source"] == source == json.loads((folder / "source.json").read_text()),
        fixed_design_recomputed=result["design"] == plan == json.loads((folder / "design.json").read_text()),
        no_state_edit_at_entry=np.array_equal(saved["source_packet"], initial),
        four_fresh_opposite_targets=np.array_equal(saved["fresh_targets"], fresh) and classify(fresh, indices).tolist() == ["E"]*4,
        actual_final_pair=np.array_equal(saved["final_packet"], packet),
        fresh_ids_and_count=result["final_ids"] == ids and result["distinct_fresh_targets"] == len(seen)-initial_seen == 4
            and not set(ids) & set(source["excluded_ids"]),
        removal_count=result["lost_carriers"] == sum(len(r["lost_ids"]) for r in rounds) ==
            (2 if plan["profile"]["donors"] == 1 else 0),
        outcomes_recomputed=all(result[k] == v for k, v in outcomes.items()) and result["first_failed_stage"] == failure,
        embedded_rounds_match=result["rounds"] == [json.loads((folder / f"round_{n:02}/result.json").read_text()) for n in (4, 5)],
        exact_integration_count=len(audits) == 22)
    return dict(case=case, source=source, design=plan, rounds=rounds,
        outcomes=outcomes, first_failed_stage=failure), endpoints, checks, audits


def panel_summary(branches):
    panel = {}
    for background in ("protein", "rna", "ordinary"):
        rows = [b for b in branches if b["case"]["background"] == background and not b["case"]["fine"]]
        panel[background] = dict(
            settings=[dict(profile=b["case"]["profile"], **b["outcomes"], first_failed_stage=b["first_failed_stage"],
                round4_donors=[d["end_labels"] for d in b["rounds"][0]["donor_contact_history"]],
                nominal_per_round=b["rounds"][0]["nominal_accounting"]) for b in rows],
            sampled_single_prompt_rescues=[b["case"]["profile"] for b in rows if b["design"]["profile"]["donors"] == 1 and b["outcomes"]["M_renewed"]],
            sampled_single_settled_rescues=[b["case"]["profile"] for b in rows if b["design"]["profile"]["donors"] == 1 and b["outcomes"]["settled_M_renewed"]],
            general_minimum_not_established=True, independent_seed_validation=False,
            ecological_fitness_measured=False, autonomous_reproduction=False)
    return panel


def analyze(run):
    summary = json.loads((run / "summary.json").read_text())
    if not summary.get("all_execution_valid"):
        raise ValueError("Require a complete execution-valid handover panel")
    config, inputs = summary["config"], run / "inputs"
    refs = arrays(inputs / "references.npz")
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    reg = [indices[n] for n in REGULATORS]
    scales = np.abs(refs["later"][reg, 0]-refs["later"][reg, 1])
    branches, ends, checks, audits = [], {}, {}, []
    for case in config["cases"]:
        b, e, bc, pa = audit_branch(run / case["id"], inputs, config, case, indices, refs)
        branches.append(b)
        ends[case["id"]] = e
        checks.update(bc)
        audits.extend(pa)
    prior = json.loads((run / "predecessor_audit.json").read_text())
    old_summary = json.loads((inputs / "robustness_summary.json").read_text())
    profiles = ["pair", "single", "single_long", "single_longer", "single_strong", "single_weak", "pair_weak"]
    expected_cases = [dict(id=b+"_"+p+("_fine" if f else ""), background=b, profile=p, state="M", old_state="E", fine=f)
        for f in (False, True) for p in profiles for b in (["protein", "rna"] if f else ["protein", "rna", "ordinary"])]
    fixed = dict(packet_size=2, continuing_rounds=[4, 5], write_kd=2e-15, contact_horizon=1000,
        retention_horizons=[10000, 10000], recovery_horizon=5000, perturbation_fraction=.2,
        late_label_fraction=.95, minimum_challenge_distance=.1, recovery_absolute_tolerance=.02,
        recovery_distance_ratio=.2, starting_nominal_time=20000, survivor_columns=[0, 1])
    records = {r["id"]: r for r in summary["cases"]}
    checks["panel"] = dict(
        exact_35_cases=config["cases"] == expected_cases and len(records) == len(summary["cases"]) == 35 and set(records) == {c["id"] for c in expected_cases},
        all_summary_results_match=all(records[c["id"]]["execution_pass"] and records[c["id"]]["returncode"] == 0 and
            records[c["id"]]["result"] == json.loads((run / c["id"] / "result.json").read_text()) for c in config["cases"]),
        fixed_parameters=all(config.get(k) == v for k, v in fixed.items()),
        fixed_profiles=config["profiles"] == [expected_design(dict(profile=p))["profile"] for p in profiles],
        bounded_runtime=1 <= config["workers"] <= 2 and 0 < config["worker_timeout_seconds"] <= 900 and 0 < config["total_budget_seconds"] <= 3600,
        source_is_audited=all(prior[k] for k in FLAGS) and prior["ready_for_stage3_design"] and prior["array_check_count"] == 14567 and
            all(all(v.values()) for v in prior["array_checks"].values()),
        exact_source_run=config["input_run"] == "runs/commitment-robustness-20260906T193416Z-u7q1u4lo" and old_summary["started_utc"] == "20260906T193416Z",
        same_native_revision=summary["revision"] == config["revision"] == old_summary["revision"] == "b2cb370aaecbc8299f259bc4251d5396c81f19a6",
        manifest_and_integration_counts=len(summary["inputs"]) == 35 and len(audits) == 770)
    controls, fine = {}, {}
    for branch in branches:
        case, name = branch["case"], branch["case"]["id"]
        benchmark = case["background"] + ("_none" + ("_fine" if case["fine"] else "") if case["profile"] == "pair" else "_loss")
        historical = case["profile"] == "pair" or (case["profile"] == "single" and not case["fine"])
        if historical:
            meta = json.loads((inputs / (benchmark + ".json")).read_text())
            exact = {}
            for n in (4, 5):
                old = arrays(inputs / (benchmark + f"_round_{n:02}.npz"))
                new = arrays(run / name / f"round_{n:02}/endpoints.npz")
                exact[str(n)] = set(old) == set(new) and all(np.array_equal(old[k], new[k]) for k in old)
            controls[name] = dict(same_source=np.array_equal(ends[name]["source"], arrays(inputs / (benchmark+"_held.npz"))["continuing_packet"]),
                same_prompt_outcome=branch["outcomes"]["M_renewed"] == meta["M_renewed"],
                bitwise_round_arrays=exact)
        if case["fine"]:
            base_name = name.removesuffix("_fine")
            base = next(b for b in branches if b["case"]["id"] == base_name)
            fine[name] = dict(same_outcomes=base["outcomes"] == branch["outcomes"] and base["first_failed_stage"] == branch["first_failed_stage"],
                fine_held_source=True, older_lineage_refined=False,
                endpoints={k: comparison(v, ends[name][k], indices, reg, scales) for k, v in ends[base_name].items()})
    control_gate = len(controls) == 8 and all(c["same_source"] and c["same_prompt_outcome"] and all(c["bitwise_round_arrays"].values()) for c in controls.values())
    fine_gate = len(fine) == 14 and all(c["same_outcomes"] and all(e["same_labels"] for e in c["endpoints"].values()) for c in fine.values())
    children = [c for b in branches for r in b["rounds"] for c in r["children"]]
    report = dict(run=str(run), all_array_checks_pass=all(all(c.values()) for c in checks.values()),
        array_checks=checks, array_check_count=sum(len(c) for c in checks.values()),
        input_hashes_valid=all(file_hash(inputs / n) == v["sha256"] for n, v in summary["inputs"].items()),
        original_inputs_hashes_valid=all(file_hash(Path(v["source"])) == v["sha256"] for v in summary["inputs"].values()),
        frozen_hashes_valid=all(file_hash(run / "frozen" / n) == h for n, h in summary["frozen_hashes_sha256"].items()),
        execution_files_hashes_valid=all(file_hash(run.parents[1] / n) == h for n, h in summary["hashes_sha256"].items()),
        predecessor_audit_hash_valid=file_hash(run / "predecessor_audit.json") == summary["predecessor_audit_sha256"],
        branches=branches, controls=controls, fine_comparisons=fine, panel=panel_summary(branches),
        unchanged_controls_reproduced=control_gate, all_tested_fine_outcomes_and_labels_agree=fine_gate,
        new_integrations=len(audits), new_snapshots=sum(a["samples"] for a in audits),
        fresh_recipients=len(children), complete_pair_replacements=2*len(branches), initial_placements=2*len(branches),
        lost_carriers=sum(len(r["lost_ids"]) for b in branches for r in b["rounds"]), new_cue_instances=0,
        new_initial_holds=0, all_recipients_locally_recovered=all(c["recovery"]["recovered"] for c in children),
        maximum_recovery_distance=max(c["recovery"]["final_distance"] for c in children),
        elapsed_seconds=summary["elapsed_seconds"], integration_cpu_seconds=sum(a["cpu_seconds"] for a in audits))
    report["ready_for_linked_design"] = all(report[k] for k in FLAGS) and control_gate and fine_gate
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
