"""Independent H2 audit: original-cell rewriting, cue exclusion and E renewal."""

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


def expected_cases():
    rows = []
    for fine in (False, True):
        suffix = "_fine" if fine else ""
        for tag, width, active in (("single", 1, True), ("pair", 2, True), ("blocked_pair", 2, False)):
            rows.append(dict(id="reference_e_"+tag+suffix, background="reference",
                rewrite_width=width, condition="reference", readout_width=width,
                readout_active=active, state="E", old_state="E", fine=fine))
        for condition in (("active1", "active2") if fine else ("active1", "active2", "blocked", "same", "none")):
            for width in (1, 2):
                for background in (("protein", "rna") if fine else ("protein", "rna", "ordinary")):
                    rows.append(dict(id=f"{background}_g{width}_{condition}"+suffix, background=background,
                        rewrite_width=width, condition=condition, readout_width=1,
                        readout_active=True, state="E", old_state="M", fine=fine))
    return rows


def expected_design(case):
    condition = case["condition"]
    cue_mask = dict(active1=(True, False), active2=(True, True), blocked=(True, True),
        same=(True, True), none=(False, False), reference=(False, False))[condition]
    steps = [dict(name=f"step_{j+1}", duration=1000, cue=cue,
        cue_label=("M" if condition == "same" else "E") if cue else None,
        connected=cue and condition != "blocked") for j, cue in enumerate(cue_mask)]
    plans = [dict(round=n, contacts=[1000, 1000],
        active_columns=[n-1] if case["readout_width"] == 1 else [0, 1],
        connected=case["readout_active"], write_kd=2e-15,
        nominal_start=22000*n, nominal_end=22000*(n+1)) for n in (1, 2)]
    return dict(steps=steps, readout=plans)


def audit_source(inputs, case, refs, indices):
    reference = case["background"] == "reference"
    checks = {}
    if reference:
        name, filename, key = None, "references.npz", "prepared"
        packet = np.repeat(refs["prepared"][:, :1], case["rewrite_width"], axis=1)
        old_ids, assay_ids, prior = [], [], set()
    else:
        profile = "single" if case["rewrite_width"] == 1 else "pair"
        name = case["background"]+"_"+profile+("_fine" if case["fine"] else "")
        filename, key = name+"_source.npz", "source_packet"
        meta = json.loads((inputs / (name+".json")).read_text())
        packet = arrays(inputs / filename)[key].copy()
        old_ids = meta["source"]["placement_ids"]
        assay_ids = [i for r in meta["rounds"] for i in r["outgoing_ids"]]
        prior = set(meta["source"]["excluded_ids"]) | set(assay_ids)
        checks.update(correct_H1_identity=(meta["case"]["id"], meta["case"]["background"],
            meta["case"]["profile"], meta["case"]["fine"]) == (name, case["background"], profile, case["fine"]),
            execution_valid=meta["execution_pass"],
            prior_exclusion_count=len(prior) == (12 if case["background"] == "ordinary" else 48),
            two_original_placements=len(old_ids) == len(set(old_ids)) == 2 and set(old_ids).issubset(prior),
            exclude_all_old_children=len(assay_ids) == len(set(assay_ids)) == 4 and not set(assay_ids) & set(old_ids))
    ids = [case["id"]+f":placed:incumbent_{j+1}" for j in range(packet.shape[1])]
    seen = prior | set(ids)
    expected_label = "E" if reference else "M"
    checks.update(full_expected_source=packet.shape == (17, case["rewrite_width"] if reference else 2)
        and classify(packet, indices).tolist() == [expected_label]*packet.shape[1],
        no_reused_placement_ids=len(ids) == len(set(ids)) and not (set(ids) & prior),
        finite_nonnegative=np.isfinite(packet).all() and np.all(packet >= 0),
        fixed_species=np.all(packet[4] == 72) and np.all(packet[16] == 0),
        canonical_RNA=np.allclose(packet, canonical_state(packet), rtol=1e-12, atol=1e-14))
    record = dict(previous_case=name, file=filename, key=key, source_ids=old_ids,
        excluded_prior_ids=sorted(prior), excluded_assay_ids=assay_ids,
        placement_ids=ids, excluded_ids=sorted(seen), source_before_H1_handover=not reference,
        ordinary_reference_initialization=reference, artificial_placements=True,
        ordinary_not_age_matched=case["background"] in ("ordinary", "reference"))
    return packet, ids, seen, record, {k: bool(v) for k, v in checks.items()}


def audit_exposure(folder, case, source, ids, seen, refs, indices):
    result = json.loads((folder / "result.json").read_text())
    end = arrays(folder / "endpoints.npz")
    width = case["rewrite_width"]
    group = source[:, :width].copy()
    original_group = group.copy()
    group_ids = ids[:width]
    selected_columns = list(range(width)) if case["background"] == "reference" else [0]
    selected_ids = [group_ids[j] for j in selected_columns]
    plan = expected_design(case)["steps"]
    names = ["step_1", "step_2"] + [f"incumbent_{j+1}_hold_{h}"
        for j in range(len(selected_columns)) for h in (1, 2)]
    setups = {r["phase"]: r for r in result["setups"]}
    records = {r["phase"]: r for r in result["audits"]}
    builds = [n for n in names if not n.endswith("_hold_2")]
    checks = dict(exact_source=np.array_equal(end["source_packet"], source),
        exact_initial_group=np.array_equal(end["group_start"], group),
        fixed_phase_order=[r["phase"] for r in result["audits"]] == names,
        exact_rebuilds=[r["phase"] for r in result["setups"]] == builds,
        original_id_selection=result["incoming_ids"] == ids and result["exposure_ids"] == group_ids
            and result["selected_ids"] == selected_ids and result["selected_columns"] == selected_columns,
        before_and_after_removal=result["removed_before"] == ids[width:]
            and result["removed_after"] == [i for j, i in enumerate(group_ids) if j not in selected_columns],
        no_cloning_or_reference_edit=result["source_clone_count"] == result["new_reference_edits"] == 0,
        source_labels_recomputed=result["source_labels"] == "".join(classify(source, indices))
            and result["exposure_start_labels"] == "".join(classify(original_group, indices)),
        nominal_clock=result["nominal_start"] == 0 and result["nominal_exposure_end"] == 2000
            and result["nominal_readout_start"] == 22000)

    def phase(name, initial, duration, connected=False):
        final, row, pc = check_phase(folder, name, duration, indices, initial, initial.shape[1],
            connected, 2e-15, records[name], setups.get(name))
        checks.update({name+"/"+k: v for k, v in pc.items()})
        raw = arrays(folder / (name+".npz"))
        checks[name+"/canonical_RNA_and_ST"] = all(np.allclose(raw[s], canonical_state(raw[s]),
            rtol=1e-12, atol=1e-14) and np.all(raw[s][16] == 0) for s in ("initial", "final"))
        return final, row

    cue_ids, steps, last_contact = [], [], None
    for step in plan:
        name, before = step["name"], group.copy()
        cue_id = case["id"]+":cue:"+name if step["cue"] else None
        if step["cue"]:
            cue_ids.append(cue_id)
            column = 0 if step["cue_label"] == "E" else 1
            initial = np.concatenate((refs["prepared"][:, column:column+1], group), axis=1)
        else:
            initial = group.copy()
        final, _ = phase(name, initial, 1000, step["connected"])
        group = final[:, 1:].copy() if step["cue"] else final.copy()
        checks[name+"/exact_cue_and_continuous_incumbents"] = np.array_equal(end[name+"_initial"], initial)
        checks[name+"/saved_full_and_incumbent_states"] = np.array_equal(end[name+"_full"], final) and np.array_equal(end[name+"_incumbents"], group)
        if step["cue"]:
            last_contact = "".join(classify(group, indices))
        steps.append(dict(step, incumbent_labels_before="".join(classify(before, indices)),
            incumbent_labels_after="".join(classify(group, indices)), cue_id=cue_id))
    checks["fresh_cues_excluded_from_lineage"] = result["removed_cue_ids"] == cue_ids and len(set(cue_ids)) == len(cue_ids) and not (set(cue_ids) & seen) and not (set(cue_ids) & set(selected_ids))
    seen.update(cue_ids)
    selected = group[:, selected_columns].copy()
    last_selected = None if last_contact is None else "".join(last_contact[j] for j in selected_columns)
    checks["exact_selected_incumbents_no_cues"] = np.array_equal(end["readout_entry"], selected)
    checks["steps_and_last_contact_recomputed"] = result["steps"] == steps and result["last_selected_contact_labels"] == last_selected
    checks["cue_count"] = result["cue_instances"] == len(cue_ids)
    firsts, held, carriers = [], [], []
    for j, cell_id in enumerate(selected_ids):
        tag = f"incumbent_{j+1}"
        first, h1 = phase(tag+"_hold_1", selected[:, j:j+1], 10000)
        final, h2 = phase(tag+"_hold_2", first, 10000)
        firsts.append(first)
        held.append(final)
        row = dict(id=cell_id, entry_label=str(classify(selected[:, j:j+1], indices)[0]),
            E_retained=all(h["recipient_label"] == "E" and h["late_label_fractions"]["E"] >= .95 for h in (h1, h2)),
            M_retained=all(h["recipient_label"] == "M" and h["late_label_fractions"]["M"] >= .95 for h in (h1, h2)))
        stored = result["carriers"][j]
        checks[tag+"/record_recomputed"] = all(stored[k] == v for k, v in row.items())
        checks[tag+"/holds_match_audits"] = stored["holds"] == [records[tag+"_hold_1"], records[tag+"_hold_2"]]
        carriers.append(dict(row, holds=[h1, h2]))
    packet = np.concatenate(held, axis=1)
    retained_e, retained_m = all(c["E_retained"] for c in carriers), all(c["M_retained"] for c in carriers)
    checks["held_endpoints_and_outcomes"] = np.array_equal(end["held_first"], np.concatenate(firsts, axis=1)) and np.array_equal(end["continuing_packet"], packet) and result["E_retained"] == retained_e and result["M_retained"] == retained_m
    checks["exact_carrier_record_count"] = len(result["carriers"]) == len(carriers)
    row = dict(steps=steps, selected_ids=selected_ids, removed_cue_ids=cue_ids,
        removed_before=ids[width:], removed_after=[i for j, i in enumerate(group_ids) if j not in selected_columns],
        E_retained=retained_e, M_retained=retained_m, last_selected_contact_labels=last_selected,
        carriers=carriers, cue_instances=len(cue_ids))
    return packet, selected_ids, row, {k: bool(v) for k, v in checks.items()}, result["audits"]


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
        exact_loss_no_dummy_or_rescue=result["lost_ids"] == [ids[j] for j in range(len(ids)) if j not in columns] and active.shape[1] == len(columns),
        exact_fresh_targets=np.array_equal(end["fresh_targets"], fresh) and classify(fresh, indices).tolist() == ["M", "M"],
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
    contact1, write1 = phase("write_1", initial1, durations[0], plan["connected"])
    initial2 = np.concatenate((fresh[:, 1:2], contact1[:, 1:]), axis=1)
    contact2, write2 = phase("write_2", initial2, durations[1], plan["connected"])
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
            retained_contact_label=retained, recovery=recovery, durable_transfer=bool(written == "E" and wait_ok and retained and recovery["recovered"]),
            settled_transfer=bool(all(h["recipient_label"] == "E" and h["late_label_fractions"]["E"] >= .95 for h in holds)
                and sh["recipient_label"] == "E" and recovery["recovered"]),
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
            late_E_fractions=[float(np.mean(late[:, j] == "E")) for j in range(active.shape[1])],
            end_regulators=contact[reg][:, 1:].tolist()))
    accounting = dict(active_donors=active.shape[1], total_contact_time=sum(durations),
        donor_contact_time=active.shape[1] * sum(durations),
        summed_miRNA_kd_time=active.shape[1] * (plan["write_kd"] if plan["connected"] else 0) * sum(durations),
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
    source, ids, seen, provenance, sc = audit_source(inputs, case, refs, indices)
    packet, ids, exposure, ec, audits = audit_exposure(folder / "exposure", case, source, ids, seen, refs, indices)
    held, initial_seen = packet.copy(), len(seen)
    fresh = np.repeat(refs["prepared"][:, 1:2], 4, axis=1)
    checks = {case["id"]+"/source": sc, case["id"]+"/exposure": ec}
    endpoints = {"exposure_"+k: v for k, v in arrays(folder / "exposure/endpoints.npz").items()}
    plans, rounds = expected_design(case)["readout"], []
    for j, n in enumerate((1, 2)):
        stage = folder / f"round_{n:02}"
        packet, ids, row, rc, pa = audit_round(stage, config, case, n, packet, ids, seen,
            fresh[:, 2*j:2*j+2], refs["later"], indices, plans[j])
        seen.update(ids)
        rounds.append(row)
        audits.extend(pa)
        checks[case["id"]+f"/round_{n:02}"] = rc
        saved = arrays(stage / "endpoints.npz")
        for key in ("contact_1", "contact_2", "outgoing_packet"):
            endpoints[f"{n}_"+key] = saved[key]
    regular = case["background"] != "reference"
    acquired = exposure["E_retained"] if regular else None
    strict, settled = all(r["round_success"] for r in rounds), all(r["settled_round_success"] for r in rounds)
    outcomes = dict(E_retained=exposure["E_retained"], M_retained=exposure["M_retained"],
        rewritten=acquired, prompt_rewrite=(acquired and exposure["last_selected_contact_labels"] == "E") if regular else None,
        E_renewed=strict, settled_E_renewed=settled,
        rewritten_and_renewed=(acquired and strict) if regular else None,
        rewritten_and_settled_renewed=(acquired and settled) if regular else None)
    failure = "retention" if not exposure["E_retained"] else next((f"round_{r['round']}" for r in rounds if not r["settled_round_success"]), None)
    result, saved = json.loads((folder / "result.json").read_text()), arrays(folder / "endpoints.npz")
    removed = len(exposure["removed_before"])+len(exposure["removed_after"])+sum(len(r["lost_ids"]) for r in rounds)
    checks[case["id"]] = dict(
        exact_case_and_indices=result["case"] == case and result["execution_pass"] and result["ion_indices"] == indices,
        source_provenance_recomputed=result["source"] == provenance == json.loads((folder / "source.json").read_text()),
        exact_readout_plans=result["readout_plans"] == plans,
        unedited_source=np.array_equal(saved["source_packet"], source),
        actual_original_held_incumbent_enters_readout=np.array_equal(saved["continuing_start"], held),
        four_fresh_M_targets=np.array_equal(saved["fresh_targets"], fresh) and classify(fresh, indices).tolist() == ["M"]*4,
        actual_final_pair=np.array_equal(saved["final_packet"], packet),
        fresh_ids_and_count=result["final_ids"] == ids and result["fresh_recipients"] == len(seen)-initial_seen == 4
            and not set(ids) & (set(provenance["excluded_ids"]) | set(exposure["removed_cue_ids"])),
        removal_count=result["removed_carriers"] == removed == (0 if case["readout_width"] == 2 else (1 if not regular else 2)),
        outcomes_recomputed=result["outcomes"] == outcomes and result["first_failed_stage"] == failure,
        embedded_exposure_matches=result["exposure"] == json.loads((folder / "exposure/result.json").read_text()),
        embedded_rounds_match=result["rounds"] == [json.loads((folder / f"round_{n:02}/result.json").read_text()) for n in (1, 2)],
        exact_integration_count=len(audits) == (28 if case["readout_width"] == 2 else 26))
    return dict(case=case, source=provenance, exposure=exposure, rounds=rounds, outcomes=outcomes,
        removed_carriers=removed, first_failed_stage=failure), endpoints, checks, audits


def panel_summary(branches):
    rows = {}
    for background in ("protein", "rna", "ordinary"):
        base = [b for b in branches if b["case"]["background"] == background and not b["case"]["fine"]]
        pairs = []
        for condition in ("active1", "active2", "blocked", "same", "none"):
            group = {b["case"]["rewrite_width"]: b for b in base if b["case"]["condition"] == condition}
            pairs.append(dict(condition=condition, outcomes_by_width={str(w): b["outcomes"] for w, b in group.items()},
                single_rewrites_pair_does_not=group[1]["outcomes"]["rewritten"] and not group[2]["outcomes"]["rewritten"],
                single_rewrite_and_renewal=group[1]["outcomes"]["rewritten_and_renewed"],
                common_readout_width=1))
        rows[background] = dict(contrasts=pairs, direction="M_to_E",
            equal_actual_molecular_dose_assumed=False, ecological_fitness_measured=False,
            autonomous_reproduction=False, independent_hypothesis_validation=False)
    return rows


def analyze(run):
    summary = json.loads((run / "summary.json").read_text())
    if not summary.get("all_execution_valid"):
        raise ValueError("Require a completed execution-valid H2 panel")
    config, inputs = summary["config"], run / "inputs"
    refs = arrays(inputs / "references.npz")
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    reg = [indices[n] for n in REGULATORS]
    scales = np.abs(refs["later"][reg, 0]-refs["later"][reg, 1])
    branches, ends, checks, audits = [], {}, {}, []
    for case in config["cases"]:
        branch, end, bc, pa = audit_branch(run / case["id"], inputs, config, case, indices, refs)
        branches.append(branch)
        ends[case["id"]] = end
        checks.update(bc)
        audits.extend(pa)
    prior = json.loads((run / "predecessor_audit.json").read_text())
    old_summary = json.loads((inputs / "handover_summary.json").read_text())
    fixed = dict(packet_size=2, continuing_rounds=[1, 2], write_kd=2e-15, contact_horizon=1000,
        retention_horizons=[10000, 10000], recovery_horizon=5000, perturbation_fraction=.2,
        late_label_fraction=.95, minimum_challenge_distance=.1, recovery_absolute_tolerance=.02,
        recovery_distance_ratio=.2, exposure_horizons=[1000, 1000], readout_start=22000,
        backgrounds=["protein", "rna", "ordinary"], rewrite_widths=[1, 2],
        conditions=["active1", "active2", "blocked", "same", "none"])
    records = {r["id"]: r for r in summary["cases"]}
    expected = expected_cases()
    checks["panel"] = dict(
        exact_44_cases=config["cases"] == expected and len(records) == len(summary["cases"]) == 44 and set(records) == {c["id"] for c in expected},
        all_summary_results_match=all(records[c["id"]]["execution_pass"] and records[c["id"]]["returncode"] == 0 and
            records[c["id"]]["result"] == json.loads((run / c["id"] / "result.json").read_text()) for c in config["cases"]),
        fixed_parameters=all(config.get(k) == v for k, v in fixed.items()),
        bounded_runtime=1 <= config["workers"] <= 2 and 0 < config["worker_timeout_seconds"] <= 900 and 0 < config["total_budget_seconds"] <= 3600,
        source_is_audited=all(prior[k] for k in FLAGS) and prior["ready_for_linked_design"] and prior["array_check_count"] == 12189
            and all(all(c.values()) for c in prior["array_checks"].values()),
        exact_source_run=config["input_run"] == "runs/handover-rescue-20260906T212435Z-du3ovank" and old_summary["started_utc"] == "20260906T212435Z",
        same_native_revision=summary["revision"] == config["revision"] == old_summary["revision"] == "b2cb370aaecbc8299f259bc4251d5396c81f19a6",
        manifest_and_integration_counts=len(summary["inputs"]) == 33 and len(audits) == 1152)
    matched_sources = {}
    for fine, backgrounds in ((False, ("protein", "rna", "ordinary")), (True, ("protein", "rna"))):
        for background in backgrounds:
            suffix = "_fine" if fine else ""
            a, b = [arrays(inputs / (background+"_"+p+suffix+"_source.npz"))["source_packet"] for p in ("single", "pair")]
            matched_sources[background+suffix] = bool(np.array_equal(a, b))
    controls, fine_comparisons = {}, {}
    for branch in branches:
        case, name = branch["case"], branch["case"]["id"]
        if case["condition"] in ("active1", "active2"):
            old = arrays(inputs / (branch["source"]["previous_case"]+"_contacts.npz"))
            end = ends[name]
            pairs = [("exposure_step_1_initial", "first_initial"), ("exposure_step_1_full", "contact_1")]
            if case["condition"] == "active2":
                pairs += [("exposure_step_2_initial", "second_initial"), ("exposure_step_2_full", "contact_2")]
            controls[name] = dict(bitwise_arrays={new: bool(np.array_equal(end[new], old[old_key])) for new, old_key in pairs},
                full_contact_comparisons=2 if case["condition"] == "active2" else 1,
                independent_replication=False)
        if case["fine"]:
            base_name = name.removesuffix("_fine")
            base = next(b for b in branches if b["case"]["id"] == base_name)
            fine_comparisons[name] = dict(same_outcomes=base["outcomes"] == branch["outcomes"] and base["first_failed_stage"] == branch["first_failed_stage"],
                endpoints={k: comparison(v, ends[name][k], indices, reg, scales) for k, v in ends[base_name].items()},
                older_lineage_refined=False)
    historical_gate = len(controls) == 20 and sum(c["full_contact_comparisons"] for c in controls.values()) == 30 and all(all(c["bitwise_arrays"].values()) for c in controls.values())
    fine_gate = len(fine_comparisons) == 11 and all(c["same_outcomes"] and all(e["same_labels"] for e in c["endpoints"].values()) for c in fine_comparisons.values())
    negative_controls = {b["case"]["id"]: bool(b["outcomes"]["M_retained"] and not b["outcomes"]["rewritten"]) for b in branches if b["case"]["condition"] in ("blocked", "same", "none")}
    reference_controls = {}
    for branch in branches:
        case, o = branch["case"], branch["outcomes"]
        if case["background"] == "reference" and case["readout_width"] == 2:
            reference_controls[case["id"]] = bool(o["E_retained"] and
                (o["E_renewed"] if case["readout_active"] else not o["settled_E_renewed"]))
    assay_gate = len(negative_controls) == 18 and all(negative_controls.values()) and len(reference_controls) == 4 and all(reference_controls.values())
    children = [c for b in branches for r in b["rounds"] for c in r["children"]]
    report = dict(run=str(run), all_array_checks_pass=all(all(c.values()) for c in checks.values()),
        array_checks=checks, array_check_count=sum(len(c) for c in checks.values()),
        input_hashes_valid=all(file_hash(inputs / n) == v["sha256"] for n, v in summary["inputs"].items()),
        original_inputs_hashes_valid=all(file_hash(Path(v["source"])) == v["sha256"] for v in summary["inputs"].values()),
        frozen_hashes_valid=all(file_hash(run / "frozen" / n) == h for n, h in summary["frozen_hashes_sha256"].items()),
        execution_files_hashes_valid=all(file_hash(run.parents[1] / n) == h for n, h in summary["hashes_sha256"].items()),
        predecessor_audit_hash_valid=file_hash(run / "predecessor_audit.json") == summary["predecessor_audit_sha256"],
        branches=branches, historical_prefix_controls=controls, fine_comparisons=fine_comparisons,
        matched_width_sources=matched_sources, same_sources_across_width=all(matched_sources.values()),
        negative_controls=negative_controls, reference_controls=reference_controls,
        unchanged_prefixes_reproduced=historical_gate, all_tested_fine_outcomes_and_labels_agree=fine_gate,
        assay_controls_pass=assay_gate, panel=panel_summary(branches),
        new_integrations=len(audits), new_snapshots=sum(a["samples"] for a in audits),
        fresh_recipients=len(children), fresh_pair_handovers=2*len(branches),
        initial_placements=sum(len(b["source"]["placement_ids"]) for b in branches),
        removed_carriers=sum(b["removed_carriers"] for b in branches),
        new_cue_instances=sum(b["exposure"]["cue_instances"] for b in branches),
        all_recipients_locally_recovered=all(c["recovery"]["recovered"] for c in children),
        maximum_recovery_distance=max(c["recovery"]["final_distance"] for c in children),
        elapsed_seconds=summary["elapsed_seconds"], integration_cpu_seconds=sum(a["cpu_seconds"] for a in audits))
    report["ready_for_reliability_design"] = all(report[k] for k in FLAGS) and historical_gate and fine_gate and assay_gate and report["same_sources_across_width"]
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

