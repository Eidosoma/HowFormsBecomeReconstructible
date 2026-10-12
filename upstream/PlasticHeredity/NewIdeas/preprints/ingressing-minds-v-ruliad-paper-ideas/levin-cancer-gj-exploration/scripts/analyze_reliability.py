"""Independent H3 reconstruction; controls/gates do not require favorable new results."""

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

FAMILIES = [
    ("protein_m_pair", "M", 2, True), ("rna_m_pair", "M", 2, True),
    ("ordinary_m_pair", "M", 2, True), ("pooled_rewritten_e_pair", "E", 2, True),
    ("ordinary_e_pair", "E", 2, True), ("protein_m_single", "M", 1, True),
    ("protein_rewritten_e_single", "E", 1, True), ("rna_rewritten_e_single", "E", 1, True),
    ("ordinary_e_single", "E", 1, True), ("ordinary_e_pair_blocked", "E", 2, False)]


def expected_cases(stage):
    if stage not in ("screen", "confirmation"):
        raise ValueError("Unknown stage")
    seeds = (2026090701, 2026090702, 2026090703) if stage == "screen" else (2026090711, 2026090712, 2026090713)
    specs = [(f, "none", 0, 0, False) for f in FAMILIES[:10 if stage == "screen" else 5]]
    specs += [(f, profile+f"_s{j+1}", a, seed, False)
        for j, seed in enumerate(seeds) for profile, a in (("mild", .1), ("strong", .25)) for f in FAMILIES[:5]]
    if stage == "screen":
        specs += [(f, "strong_s1", .25, seeds[0], False) for f in FAMILIES[5:]]
        specs += [(f, "none", 0, 0, True) for f in FAMILIES]
        specs += [(f, "strong_s3", .25, seeds[2], True) for f in (FAMILIES[0], FAMILIES[3])]
    else:
        specs += [(f, p, a, s, True) for f in (FAMILIES[0], FAMILIES[3])
            for p, a, s in (("none", 0, 0), ("strong_s1", .25, seeds[0]))]
    return [dict(id=stage+"__"+f[0]+"_"+p+("_fine" if fine else ""),
        family=f[0], state=f[1], width=f[2], connected=f[3], profile=p,
        amplitude=a, seed=seed, fine=fine) for f, p, a, seed, fine in specs]


def expected_design(config, case):
    raw = np.random.Generator(np.random.PCG64(case["seed"])).uniform(-1, 1, (config["round_count"], 2, 3, 2))
    plans = []
    for index, draws in enumerate(raw):
        cols = [index % 2] if case["width"] == 1 else [0, 1]
        mult = [[[(1+case["amplitude"]*draws[k, r, col]) for col in cols] for r in range(3)] for k in range(2)]
        plans.append(dict(round=index+1, contacts=[1000, 1000], active_columns=cols,
            write_kd=2e-15, connected=case["connected"], nominal_start=22000*index,
            nominal_end=22000*(index+1), shock_factors=mult))
    return dict(generator="PCG64", seed=case["seed"], amplitude=case["amplitude"],
        raw_uniform=raw.tolist(), rounds=plans, shock_target="active_donor_primary_regulators_only", continuous_noise=False)


def expected_recipe(case):
    name, fine = case["family"], case["fine"]
    if name in ("protein_m_pair", "rna_m_pair", "ordinary_m_pair", "protein_m_single"):
        stem = name.replace("_m_", "_")
        stem += "_fine" if fine and not name.startswith("ordinary") else ""
        return [dict(kind="h1", name=stem, key="source_packet", columns=[0, 1])]
    mapping = {
        "pooled_rewritten_e_pair": ("protein_g1_active2", "rna_g1_active2"),
        "protein_rewritten_e_single": ("protein_g1_active2",),
        "rna_rewritten_e_single": ("rna_g1_active2",),
        "ordinary_e_pair": ("reference_e_pair",),
        "ordinary_e_single": ("reference_e_single",),
        "ordinary_e_pair_blocked": ("reference_e_blocked_pair",)}
    return [dict(kind="h2", name=n+("_fine" if fine else ""), key="continuing_packet",
        columns=[0, 1] if n in ("reference_e_pair", "reference_e_blocked_pair") else [0]) for n in mapping[name]]


def audit_source(inputs, config, case, indices):
    parts, old_ids, prior, recipes, checks = [], [], set(), [], {}
    for number, spec in enumerate(expected_recipe(case)):
        kind, name = spec["kind"], spec["name"]
        stem = kind+"_"+name
        meta = json.loads((inputs / (stem+".json")).read_text())
        state = arrays(inputs / (stem+"_source.npz"))[spec["key"]]
        checks[f"{number}/identity_and_execution"] = meta["case"]["id"] == name and meta["case"]["fine"] == name.endswith("_fine") and meta["execution_pass"]
        assay_ids = [i for r in meta["rounds"] for i in r["outgoing_ids"]]
        if kind == "h1":
            source_ids = meta["source"]["placement_ids"]
            excluded = set(meta["source"]["excluded_ids"]) | set(assay_ids)
            expected_count = 12 if name.startswith("ordinary") else 48
        else:
            source_ids = meta["exposure"]["selected_ids"]
            excluded = set(meta["source"]["excluded_ids"]) | set(meta["exposure"]["removed_cue_ids"]) | set(assay_ids)
            expected_count = 56 if name.startswith(("protein", "rna")) else (5 if "reference_e_single" in name else 6)
            checks[f"{number}/held_E_source"] = meta["outcomes"]["E_retained"] and (meta["outcomes"]["rewritten"] if name.startswith(("protein", "rna")) else True)
            checks[f"{number}/cue_cells_excluded"] = not set(source_ids) & set(meta["exposure"]["removed_cue_ids"])
        checks[f"{number}/complete_prior_exclusion"] = len(excluded) == expected_count and len(set(assay_ids)) == len(assay_ids) == 4 and not set(assay_ids) & set(source_ids)
        checks[f"{number}/source_ids_match_columns"] = len(source_ids) == len(set(source_ids)) == state.shape[1] and set(source_ids).issubset(excluded)
        chosen = [source_ids[j] for j in spec["columns"]]
        old_ids.extend(chosen)
        prior.update(excluded)
        parts.append(state[:, spec["columns"]].copy())
        recipes.append(dict(spec, file=stem+"_source.npz", source_ids=chosen, excluded_ids=sorted(excluded)))
    packet = np.concatenate(parts, axis=1)
    ids = [case["id"]+f":placed:carrier_{j+1}" for j in range(packet.shape[1])]
    seen = prior | set(ids)
    checks.update(no_duplicate_pooled_cells=len(set(old_ids)) == len(old_ids),
        source_shape_and_label=packet.shape[0] == 17 and packet.shape[1] in (1, 2) and classify(packet, indices).tolist() == [case["state"]]*packet.shape[1],
        no_reused_placements=len(ids) == len(set(ids)) and not (set(ids) & prior),
        finite_nonnegative=np.isfinite(packet).all() and np.all(packet >= 0),
        canonical_RNA=np.allclose(packet, canonical_state(packet), rtol=1e-12, atol=1e-14),
        fixed_species=np.all(packet[4] == 72) and np.all(packet[16] == 0))
    provenance = dict(recipe=recipes, source_ids=old_ids, placement_ids=ids,
        excluded_prior_ids=sorted(prior), excluded_ids=sorted(seen), artificial_placements=True,
        pooled_across_routes=case["family"] == "pooled_rewritten_e_pair", cloned_source_cell=False,
        source_history_fully_refined=False, ordinary_not_age_matched=case["family"].startswith("ordinary"))
    return packet, ids, seen, provenance, {k: bool(v) for k, v in checks.items()}


def audit_round(folder, config, case, number, incoming, ids, seen, fresh, later, indices, plan):
    result, end = json.loads((folder / "result.json").read_text()), arrays(folder / "endpoints.npz")
    columns, durations = plan["active_columns"], plan["contacts"]
    selected = incoming[:, columns].copy()
    factors = np.asarray(plan["shock_factors"])
    active = selected.copy()
    active[5:8] *= factors[0]
    phase_names = ["write_1", "write_2", "wait_1", "child_1_hold_1", "child_1_hold_2", "child_2_hold_1", "child_2_hold_2",
        "child_1_shadow", "child_1_challenge", "child_2_shadow", "child_2_challenge"]
    setups = {r["phase"]: r for r in result["setups"]}
    phase_records = {r["phase"]: r for r in result["audits"]}
    checks = dict(fixed_phase_order=[r["phase"] for r in result["audits"]] == phase_names,
        exact_builds=len(result["setups"]) == 9 and set(setups) == set(phase_names) - {"child_1_hold_2", "child_2_hold_2"},
        exact_incoming_pair=np.array_equal(end["incoming_packet"], incoming) and result["incoming_ids"] == ids,
        exact_active_selection=np.array_equal(end["active_packet"], active) and result["active_ids"] == [ids[j] for j in columns],
        exact_loss_no_dummy_or_rescue=result["lost_ids"] == [ids[j] for j in range(len(ids)) if j not in columns] and active.shape[1] == len(columns),
        exact_fresh_targets=np.array_equal(end["fresh_targets"], fresh) and classify(fresh, indices).tolist() == [opposite(case["state"])] * 2,
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
    after_second_shock = contact1[:, 1:].copy()
    after_second_shock[5:8] *= factors[1]
    initial2 = np.concatenate((fresh[:, 1:2], after_second_shock), axis=1)
    contact2, write2 = phase("write_2", initial2, durations[1], plan["connected"])
    waited, wait = phase("wait_1", contact1[:, :1], durations[1])
    checks.update(dict(
        selected_original_packet=np.array_equal(end["selected_packet"], selected),
        exact_second_shock=np.array_equal(end["after_second_shock"], after_second_shock),
        exact_fixed_shock_factors=np.array_equal(end["shock_factors"], factors) and factors.shape == (2, 3, len(columns))
            and np.isfinite(factors).all() and np.all((factors >= .75) & (factors <= 1.25)),
        shock_labels_recomputed=result["selected_labels"] == "".join(classify(selected, indices))
            and result["after_first_shock_labels"] == "".join(classify(active, indices))
            and result["after_second_shock_labels"] == "".join(classify(after_second_shock, indices)),
        first_write_exact=np.array_equal(end["first_initial"], initial1),
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
            retained_contact_label=retained, recovery=recovery, durable_transfer=bool(written == case["state"] and wait_ok and retained and recovery["recovered"]),
            settled_transfer=bool(all(h["recipient_label"] == case["state"] and h["late_label_fractions"][case["state"]] >= .95 for h in holds)
                and sh["recipient_label"] == case["state"] and recovery["recovered"]),
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
            late_target_fractions=[float(np.mean(late[:, j] == case["state"])) for j in range(active.shape[1])],
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
    source, ids, seen, provenance, sc = audit_source(inputs, config, case, indices)
    initial_seen = len(seen)
    fresh = np.repeat(refs["prepared"][:, 0 if case["state"] == "M" else 1, None], 2*config["round_count"], axis=1)
    plan = expected_design(config, case)
    packet, rounds, audits, endpoints = source.copy(), [], [], {"source": source}
    checks = {case["id"]+"/source": sc}
    for j, step in enumerate(plan["rounds"]):
        stage = folder / f"round_{j+1:02}"
        packet, ids, row, rc, pa = audit_round(stage, config, case, j+1, packet, ids, seen,
            fresh[:, 2*j:2*j+2], refs["later"], indices, step)
        seen.update(ids)
        rounds.append(row)
        audits.extend(pa)
        checks[case["id"]+f"/round_{j+1:02}"] = rc
        end = arrays(stage / "endpoints.npz")
        endpoints.update({f"{j+1}/"+k: end[k] for k in ("outgoing_packet", "contact_1", "contact_2", "active_packet", "after_second_shock")})
    first = next((r["round"] for r in rounds if not r["round_success"]), None)
    settled = next((r["round"] for r in rounds if not r["settled_round_success"]), None)
    outcomes = dict(strict_renewal=first is None, settled_renewal=settled is None,
        first_failed_round=first, first_settled_failed_round=settled,
        successful_prefix_rounds=config["round_count"] if first is None else first-1,
        censored=first is None, observation_rounds=config["round_count"],
        failure_round_end_nominal_time=None if first is None else 22000*first)
    result = json.loads((folder / "result.json").read_text())
    end = arrays(folder / "endpoints.npz")
    checks[case["id"]] = dict(
        exact_case=result["case"] == case and result["execution_pass"] and result["ion_indices"] == indices,
        source_provenance=result["source"] == provenance == json.loads((folder / "source.json").read_text()),
        full_seeded_schedule=result["design"] == plan == json.loads((folder / "design.json").read_text()),
        unedited_source=np.array_equal(end["source_packet"], source),
        unedited_fresh_opposite_targets=np.array_equal(end["fresh_targets"], fresh)
            and classify(fresh, indices).tolist() == [opposite(case["state"])]*(2*config["round_count"]),
        actual_final_packet=np.array_equal(end["final_packet"], packet),
        new_unique_final_ids=result["final_ids"] == ids and not set(ids) & set(provenance["excluded_ids"]),
        fresh_recipient_count=result["fresh_recipients"] == len(seen)-initial_seen == 2*config["round_count"],
        removal_count=result["removed_carriers"] == sum(len(r["lost_ids"]) for r in rounds),
        fixed_round_and_integration_counts=len(rounds) == config["round_count"] and len(audits) == 11*config["round_count"],
        shock_counts=result["scheduled_shocks"] == 2*config["round_count"] and result["nonzero_shocks"] == (2*config["round_count"] if case["amplitude"] else 0),
        outcomes_recomputed=result["outcomes"] == outcomes,
        embedded_rounds=result["rounds"] == [json.loads((folder / f"round_{j+1:02}/result.json").read_text()) for j in range(config["round_count"])])
    return dict(case=case, source=provenance, rounds=rounds, outcomes=outcomes,
        removed_carriers=result["removed_carriers"]), endpoints, checks, audits


def panel_summary(branches):
    table = {}
    for family, _, _, _ in FAMILIES:
        rows = [b for b in branches if b["case"]["family"] == family and not b["case"]["fine"]]
        if not rows:
            continue
        table[family] = {}
        for amplitude in (0, .1, .25):
            group = [b for b in rows if b["case"]["amplitude"] == amplitude]
            if not group:
                continue
            table[family][str(amplitude)] = dict(n=len(group), independent_stochastic_schedules=len(group) if amplitude else 0,
                seeds=[b["case"]["seed"] for b in group],
                strict_successes=sum(b["outcomes"]["strict_renewal"] for b in group),
                settled_successes=sum(b["outcomes"]["settled_renewal"] for b in group),
                first_failed_rounds=[b["outcomes"]["first_failed_round"] for b in group],
                successful_prefix_rounds=[b["outcomes"]["successful_prefix_rounds"] for b in group],
                censored=[b["outcomes"]["censored"] for b in group],
                observation_rounds=group[0]["outcomes"]["observation_rounds"])
    return table


def analyze(run):
    summary = json.loads((run / "summary.json").read_text())
    if not summary.get("all_execution_valid"):
        raise ValueError("Require a complete execution-valid reliability panel")
    config, inputs = summary["config"], run / "inputs"
    stage = config["stage"]
    expected = expected_cases(stage)
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
    old_summary = json.loads((inputs / "rewrite_summary.json").read_text())
    fixed = dict(round_count=8 if stage == "screen" else 12, workers=2, worker_timeout_seconds=1800,
        total_budget_seconds=14400, packet_size=2, write_kd=2e-15, contact_horizon=1000,
        retention_horizons=[10000, 10000], recovery_horizon=5000, perturbation_fraction=.2,
        late_label_fraction=.95, minimum_challenge_distance=.1, recovery_absolute_tolerance=.02,
        recovery_distance_ratio=.2, shock_indices=[5, 6, 7], shocks_per_round=2,
        seeds=[2026090701, 2026090702, 2026090703] if stage == "screen" else [2026090711, 2026090712, 2026090713])
    records = {r["id"]: r for r in summary["cases"]}
    checks["panel"] = dict(
        exact_case_grid=config["cases"] == expected and len(records) == len(summary["cases"]) == (57 if stage == "screen" else 39) and set(records) == {c["id"] for c in expected},
        fixed_parameters=all(config.get(k) == v for k, v in fixed.items()),
        source_audited=all(prior[k] for k in FLAGS) and prior["array_check_count"] == 18466 and prior["ready_for_reliability_design"]
            and all(all(c.values()) for c in prior["array_checks"].values()),
        exact_source=config["input_run"] == "runs/rewrite-tradeoff-20260906T233148Z-3fq2onfn" and old_summary["started_utc"] == "20260906T233148Z",
        pinned_revision=summary["revision"] == config["revision"] == old_summary["revision"] == "b2cb370aaecbc8299f259bc4251d5396c81f19a6",
        summary_matches=all(records[c["id"]]["execution_pass"] and records[c["id"]]["returncode"] == 0 and
            records[c["id"]]["result"] == json.loads((run / c["id"] / "result.json").read_text()) for c in expected),
        manifest_count=len(summary["inputs"]) == (64 if stage == "screen" else 65),
        integration_count=len(audits) == (5016 if stage == "screen" else 5148))
    controls, fine = {}, {}
    for branch in branches:
        case, name = branch["case"], branch["case"]["id"]
        if case["profile"] == "none" and case["family"] != "pooled_rewritten_e_pair" and not (case["fine"] and case["family"] == "ordinary_m_pair"):
            spec = expected_recipe(case)[0]
            prefix = spec["kind"]+"_"+spec["name"]
            comparisons = {}
            for n in ((1,) if spec["kind"] == "h1" else (1, 2)):
                path = inputs / (prefix+("_contacts.npz" if spec["kind"] == "h1" else f"_round_{n:02}.npz"))
                old = arrays(path)
                new = arrays(run / name / f"round_{n:02}/endpoints.npz")
                comparisons[str(n)] = set(old).issubset(new) and all(np.array_equal(v, new[k]) for k, v in old.items())
            expected_first_success = case["width"] == 2 and case["connected"]
            controls[name] = dict(round_arrays=comparisons, first_outcome_matches=branch["rounds"][0]["round_success"] == expected_first_success,
                independent_hypothesis_validation=False)
        if case["fine"]:
            base_name = name.removesuffix("_fine")
            base = next(b for b in branches if b["case"]["id"] == base_name)
            fine[name] = dict(same_outcomes=base["outcomes"] == branch["outcomes"],
                endpoints={k: comparison(v, ends[name][k], indices, reg, scales) for k, v in ends[base_name].items()},
                older_history_fully_refined=False)
    control_gate = len(controls) == (17 if stage == "screen" else 5) and all(c["first_outcome_matches"] and all(c["round_arrays"].values()) for c in controls.values())
    fine_gate = len(fine) == (12 if stage == "screen" else 4) and all(c["same_outcomes"] and all(v["same_labels"] for v in c["endpoints"].values()) for c in fine.values())
    confirmation_checks = {}
    if stage == "confirmation":
        gate = json.loads((inputs / "screening_gate.json").read_text())
        screen = Path(gate["run"])
        screen_summary = json.loads((screen / "summary.json").read_text())
        confirmation_checks.update(screen_valid=gate["audit"]["eligible_for_confirmation"] and all(gate["audit"][k] for k in FLAGS),
            screen_summary_unchanged=file_hash(screen / "summary.json") == gate["screen_summary_sha256"],
            frozen_confirmation_unchanged=file_hash(screen / "frozen/reliability_confirmation_v1.json") == gate["config_sha256"],
            exact_confirmation_config=json.loads((screen / "frozen/reliability_confirmation_v1.json").read_text()) == config,
            disjoint_seed_sets=not set(config["seeds"]) & set(screen_summary["config"]["seeds"]),
            gate_copy_unchanged=file_hash(inputs / "screening_gate.json") == file_hash(run / "screening_gate.json"),
            same_H2_source_states=all(summary["inputs"][k]["sha256"] == v["sha256"] for k, v in screen_summary["inputs"].items()))
        for case in config["cases"]:
            if case["profile"] != "none":
                continue
            baseline = case["id"].replace("confirmation__", "screen__", 1)
            identical = True
            for n in range(1, 9):
                old = arrays(screen / baseline / f"round_{n:02}/endpoints.npz")
                new = arrays(run / case["id"] / f"round_{n:02}/endpoints.npz")
                identical = identical and set(old) == set(new) and all(np.array_equal(v, new[k]) for k, v in old.items())
            confirmation_checks[case["id"]+"/same_eight_round_prefix"] = identical
    checks["confirmation_gate"] = {k: bool(v) for k, v in confirmation_checks.items()}
    children = [c for b in branches for r in b["rounds"] for c in r["children"]]
    report = dict(run=str(run), stage=stage, all_array_checks_pass=all(all(c.values()) for c in checks.values()),
        array_checks=checks, array_check_count=sum(len(c) for c in checks.values()),
        input_hashes_valid=all(file_hash(inputs / n) == v["sha256"] for n, v in summary["inputs"].items()),
        original_inputs_hashes_valid=all(file_hash(Path(v["source"])) == v["sha256"] for v in summary["inputs"].values()),
        frozen_hashes_valid=all(file_hash(run / "frozen" / n) == h for n, h in summary["frozen_hashes_sha256"].items()),
        execution_files_hashes_valid=all(file_hash(run.parents[1] / n) == h for n, h in summary["hashes_sha256"].items()),
        predecessor_audit_hash_valid=file_hash(run / "predecessor_audit.json") == summary["predecessor_audit_sha256"],
        branches=branches, historical_controls=controls, fine_comparisons=fine, panel=panel_summary(branches),
        historical_prefixes_pass=control_gate, selected_fine_outcomes_and_labels_agree=fine_gate,
        confirmation_checks=confirmation_checks,
        new_integrations=len(audits), new_snapshots=sum(a["samples"] for a in audits),
        fresh_recipients=len(children), fresh_pair_handovers=config["round_count"]*len(branches),
        initial_placements=sum(len(b["source"]["placement_ids"]) for b in branches),
        removed_carriers=sum(b["removed_carriers"] for b in branches),
        scheduled_shocks=2*config["round_count"]*len(branches),
        nonzero_shocks=2*config["round_count"]*sum(bool(b["case"]["amplitude"]) for b in branches),
        all_recipients_locally_recovered=all(c["recovery"]["recovered"] for c in children),
        maximum_recovery_distance=max(c["recovery"]["final_distance"] for c in children),
        elapsed_seconds=summary["elapsed_seconds"], integration_cpu_seconds=sum(a["cpu_seconds"] for a in audits),
        ecological_fitness_measured=False, autonomous_reproduction=False, continuous_noise=False,
        confirmation_survivors_selected_from_screen=False)
    quality = all(report[k] for k in FLAGS) and control_gate and fine_gate
    report["quality_gate"] = quality
    report["eligible_for_confirmation"] = stage == "screen" and quality
    report["ready_for_benefit_design"] = stage == "confirmation" and quality
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    report = analyze(args.run.resolve())
    if args.save:
        write_json(args.run.resolve() / "independent_audit.json", report)
    if args.compact:
        report["failed_checks"] = {k: [n for n, v in c.items() if not v] for k, c in report.pop("array_checks").items() if not all(c.values())}
        report["branches"] = [dict(id=b["case"]["id"], **b["outcomes"]) for b in report["branches"]]
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if all(report[k] for k in FLAGS) else 1


if __name__ == "__main__":
    raise SystemExit(main())

