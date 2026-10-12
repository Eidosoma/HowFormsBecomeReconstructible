"""Independent H4b schedule/lineage reconstruction and complete cost reporting."""

import argparse
from pathlib import Path

import numpy as np

from analyze_changing_environment import (read, audit_cue, expected_handover, score_epoch,
    summarize_scores as h4_scores)
from analyze_commitment_components import FLAGS
from analyze_group_transfer import arrays
from analyze_pulse_spacing import comparison
from analyze_reliability import audit_source, audit_round
from changing_environment_design import FIXED as H4_FIXED
from memory_metrics import REGULATORS, classify
from recover_reliability import snapshot
from run_memory_probe import write_json
from run_onward_transfer import file_hash

SEEDS = (20260908101, 20260908102, 20260908103, 20260908104)
PROFILES = {"slow_reliable": (.15, .60, 0.), "fast_reliable": (.75, .60, 0.),
    "slow_sparse": (.15, .25, 0.), "slow_noisy": (.15, .60, .25)}
POLICIES = [("rewritable", True, True), ("fixed", True, False), ("reactive", False, True), ("neither", False, False)]
COSTS = (0., .025, .05, .075, .1, .15, .2, .3)


def expected_cases():
    result = [dict(id=f"prefix__{p}__{a}", kind="prefix", policy=p, state=a, fine=False,
        parent_enabled=parent, cue_enabled=cue, legacy_case_id=f"{p}__misleading__2026090811__{a}")
        for a in ("M", "E") for p, parent, cue in POLICIES]
    settings = [(r, s, a, False) for r in PROFILES for s in SEEDS for a in ("M", "E")]
    settings += [("slow_noisy", SEEDS[-1], a, True) for a in ("M", "E")]
    for profile, seed, state, fine in settings:
        for policy, parent, cue in POLICIES:
            result.append(dict(id=f"holdout__{policy}__{profile}__{seed}__{state}"+("_fine" if fine else ""),
                kind="main", policy=policy, profile=profile, seed=seed, state=state,
                parent_enabled=parent, cue_enabled=cue, fine=fine))
    return result


def expected_config():
    return dict(H4_FIXED, input_run="runs/changing-environment-20260907T191331Z-bvq74cne",
        epochs=12, prefix_epochs=2, prefix_cases=8, seeds=list(SEEDS),
        profiles={k: list(v) for k, v in PROFILES.items()}, costs=list(COSTS),
        worker_timeout_seconds=3600, total_budget_seconds=86400, planned_cases=144,
        planned_integrations=28016, planned_fresh_recipients=3296,
        prefix_gate_required=True, binary_reference_rule=True, cases=expected_cases())


def expected_schedule(case):
    if case["kind"] == "prefix":
        # The registered H4 seed 2026090811 has first two cues [A, absent],
        # with both world states A. Independently checked against frozen H4 metadata.
        return dict(generator="historical_H4_prefix", legacy_case_id=case["legacy_case_id"],
            hidden_truth=[case["state"]]*2, visible_cues=[case["state"], None], bootstrap_epoch=1)
    draws = np.random.Generator(np.random.PCG64(case["seed"])).random(size=(11, 3))
    flip_p, available_p, wrong_p = PROFILES[case["profile"]]
    hidden, visible, state = [case["state"]], [case["state"]], case["state"]
    for k in range(11):
        if draws[k, 0] < flip_p:
            state = "E" if state == "M" else "M"
        hidden.append(state)
        cue = None
        if draws[k, 1] < available_p:
            cue = ("E" if state == "M" else "M") if draws[k, 2] < wrong_p else state
        visible.append(cue)
    return dict(generator="PCG64", seed=case["seed"], raw_uniform=draws.tolist(),
        columns=["world_flip", "cue_available", "cue_incorrect"],
        probabilities=dict(flip=flip_p, available=available_p, incorrect=wrong_p),
        hidden_truth=hidden, visible_cues=visible, bootstrap_epoch=1,
        resampling=False, forced_post_bootstrap_events=False)


def utility_grid(match, parent, cue):
    return [dict(parent_cost=p, cue_cost=c, value=match-p*parent-c*cue) for p in COSTS for c in COSTS]


def summarize_scores(rows):
    result = h4_scores(rows)
    result["all_epochs_final_match"] = result.pop("all_six_final_match")
    result["utility_sensitivity"] = utility_grid(result["subsets"]["all_scored"]["final_match"],
        result["mean_normalized_parent_contact"], result["mean_normalized_cue_contact"])
    result["all_epochs_utility_sensitivity"] = utility_grid(result["all_epochs_final_match"],
        float(np.mean([r["active_parent_edge_time"]/4000 for r in rows])),
        float(np.mean([r["active_cue_edge_time"]/1000 for r in rows])))
    result["late_epochs_final_match"] = float(np.mean([r["final_match"] for r in rows if r["epoch"] >= 7])) if len(rows) >= 7 else None
    return result


def binary_reference(case, visible_cues):
    """A declared perfect-copy/instant-cue reference, not another native replicate.

    No hidden truth or fitted parameter enters this algorithm. No claim that
    these ideal operations have the same physical costs as native cells.
    """
    memory = case["state"]*2
    result = []
    for epoch, visible in enumerate(visible_cues, 1):
        before = memory if case["parent_enabled"] else ("EM" if epoch % 2 else "ME")
        after = visible*2 if case["cue_enabled"] and visible is not None else before
        result.append([before, after, after, after])
        memory = after
    return result


def audit_branch(folder, inputs, config, case, indices, refs):
    source_spec = dict(id=case["id"]+":source", state=case["state"], fine=False,
        family="protein_m_pair" if case["state"] == "M" else "pooled_rewritten_e_pair")
    source, ids, seen, provenance, source_checks = audit_source(inputs, config, source_spec, indices)
    saved, result = arrays(folder / "endpoints.npz"), read(folder / "result.json")
    plan = expected_schedule(case)
    n = 2 if case["kind"] == "prefix" else 12
    checks = dict(source=source_checks, schedule=dict(exact_design=result["design"] == read(folder / "design.json") == plan,
        exact_epoch_count=len(result["epochs"]) == len(plan["hidden_truth"]) == len(plan["visible_cues"]) == n))
    packet, scored, phases, cue_count, trace = source.copy(), [], [], 0, {"source": source}
    historical_checks = {}
    for epoch, cue in enumerate(plan["visible_cues"], 1):
        parents = ids.copy()
        fresh = refs["prepared"][:, [0, 1] if epoch % 2 else [1, 0]].copy()
        stage = folder / f"epoch_{epoch:02}_inheritance"
        dynamic_case = dict(id=case["id"], state=case["state"], fine=case["fine"])
        packet, ids, row, rc, pa = audit_round(stage, config, dynamic_case, epoch, packet, ids, seen,
            fresh, refs["later"], indices, expected_handover(epoch, case["parent_enabled"]))
        relay = arrays(stage / "endpoints.npz")
        if "exact_fresh_targets" not in rc:
            raise ValueError("Legacy fresh-target audit contract changed")
        # The same single, explicitly documented H4 mixed-fresh assay replacement.
        rc["exact_fresh_targets"] = bool(np.array_equal(relay["fresh_targets"], fresh)
            and classify(fresh, indices).tolist() == (["E", "M"] if epoch % 2 else ["M", "E"]))
        checks[f"epoch_{epoch}/inheritance"] = rc
        phases.extend(pa)
        seen.update(ids)
        before = packet.copy()
        exposure = folder / f"epoch_{epoch:02}_cue"
        cp, removed, late, cue_trace, cc, pa = audit_cue(exposure, config, case, epoch, packet, ids, seen,
            refs["prepared"], indices, cue)
        checks[f"epoch_{epoch}/cue"] = cc
        phases.extend(pa)
        seen.update(removed)
        cue_count += len(removed)
        packet = cp[-1]
        labels = ["".join(classify(a, indices)) for a in [before]+cp]
        score = score_epoch(epoch, plan["hidden_truth"][epoch-1], plan["hidden_truth"][epoch-2] if epoch > 1 else None,
            cue, labels, case["parent_enabled"], case["cue_enabled"])
        scored.append(dict(score, post_hold_late_fractions=late, inherited_local_recoveries=[c["recovery"] for c in row["children"]]))
        actual = result["epochs"][epoch-1]
        checks[f"epoch_{epoch}/record"] = dict(actual_parents_removed=actual["removed_parent_ids"] == parents,
            exact_phase_records=actual["inheritance"] == read(stage / "result.json") and actual["cue"] == read(exposure / "result.json"),
            equal_clock=actual["nominal_start"] == 42100*(epoch-1) and actual["nominal_end"] == 42100*epoch,
            equal_resources=actual["fresh_recipients"] == 2 and actual["active_parent_edge_time"] == score["active_parent_edge_time"],
            epoch_identity=actual["epoch"] == epoch)
        trace.update({f"{epoch}/relay/"+k: v for k, v in relay.items() if v.ndim == 2 and v.shape[0] == 17})
        trace.update({f"{epoch}/cue/"+k: v for k, v in cue_trace.items()})
        if case["kind"] == "prefix":
            for phase, current in (("inheritance", relay), ("cue", arrays(exposure / "endpoints.npz"))):
                old = arrays(inputs / (case["id"]+f"_epoch_{epoch:02}_{phase}.npz"))
                historical_checks[f"{epoch}/{phase}"] = set(old) == set(current) and all(np.array_equal(v, current[k]) for k, v in old.items())
    if case["kind"] == "prefix":
        old = read(inputs / (case["id"]+"_legacy_result.json"))
        historical_checks["legacy_identity"] = old["execution_pass"] and old["case"]["id"] == case["legacy_case_id"]
        historical_checks["legacy_numerics"] = old["case"]["fine"] is False
        historical_checks["historical_schedule"] = old["design"]["hidden_truth"][:2] == plan["hidden_truth"] and old["design"]["visible_cues"][:2] == plan["visible_cues"]
    checks["branch"] = dict(exact_case=result["case"] == case and result["execution_pass"] and result["ion_indices"] == indices,
        source_provenance=result["source"] == read(folder / "source.json") == provenance,
        unchanged_source=np.array_equal(saved["source_packet"], source), actual_final_packet=np.array_equal(saved["final_packet"], packet),
        exact_final_ids=result["final_ids"] == ids and len(set(ids)) == 2 and not set(ids) & set(provenance["excluded_ids"]),
        fresh_recipient_count=result["fresh_recipients"] == n*2,
        cue_count=result["cue_cells_supplied"] == cue_count == 10*sum(v is not None for v in plan["visible_cues"]),
        integration_count=len(phases) == 17*n, no_fitness_claim=result["ecological_fitness_measured"] is False)
    reference = binary_reference(case, plan["visible_cues"])
    ref_scores = [score_epoch(i, t, plan["hidden_truth"][i-2] if i > 1 else None, v, label,
        case["parent_enabled"], case["cue_enabled"]) for i, (t, v, label) in enumerate(zip(plan["hidden_truth"], plan["visible_cues"], reference), 1)]
    mismatches = [dict(epoch=i, native=r["checkpoint_labels"], binary=b,
        disagreeing_checkpoints=[j for j in range(4) if r["checkpoint_labels"][j] != b[j]])
        for i, (r, b) in enumerate(zip(scored, reference), 1) if r["checkpoint_labels"] != b]
    branch = dict(case=case, source=provenance, design=plan, epochs=scored,
        outcomes=summarize_scores(scored), fresh_recipients=2*n, cue_cells_supplied=cue_count,
        historical_checks=historical_checks,
        historical_prefix_pass=all(historical_checks.values()) if historical_checks else None,
        binary_reference=dict(checkpoint_labels=reference, outcomes=summarize_scores(ref_scores),
            native_mismatches=mismatches, all_checkpoints_agree=not mismatches,
            is_native_simulation=False, equivalence_of_underlying_mechanism_proven=False))
    return branch, trace, {g: {k: bool(v) for k, v in c.items()} for g, c in checks.items()}, phases


def prefix_gate(run, config):
    if config != expected_config():
        raise ValueError("Unexpected H4b configuration at prefix gate")
    summary = read(run / "summary.json")
    records = {r["id"]: r for r in summary["cases"]}
    wanted = expected_cases()[:8]
    if not all(c["id"] in records and records[c["id"]]["execution_pass"] and records[c["id"]]["returncode"] == 0 for c in wanted):
        return dict(quality_gate=False, reason="Historical prefix execution failed or incomplete", controls={})
    inputs = run / "inputs"
    refs, indices = arrays(inputs / "references.npz"), read(inputs / "reference.json")["ion_indices"]
    controls = {}
    for case in wanted:
        b, _, checks, _ = audit_branch(run / case["id"], inputs, config, case, indices, refs)
        arrays_pass = all(all(c.values()) for c in checks.values())
        controls[case["id"]] = dict(array_checks_pass=arrays_pass, array_check_count=sum(len(c) for c in checks.values()),
            historical_prefix_pass=b["historical_prefix_pass"], historical_checks=b["historical_checks"],
            summary_matches=records[case["id"]]["result"] == read(run / case["id"] / "result.json"))
    integrity = dict(
        inputs=all(file_hash(inputs / n) == v["sha256"] == file_hash(Path(v["source"])) for n, v in summary["inputs"].items()),
        frozen=all(file_hash(run / "frozen" / n) == h for n, h in summary["frozen_hashes_sha256"].items()),
        execution=all(file_hash(run.parents[1] / n) == h for n, h in summary["hashes_sha256"].items()),
        predecessor=file_hash(run / "predecessor_audit.json") == summary["predecessor_audit_sha256"])
    gate = all(integrity.values()) and all(c["array_checks_pass"] and c["historical_prefix_pass"] and c["summary_matches"] for c in controls.values())
    return dict(quality_gate=gate, controls=controls, integrity=integrity, new_condition_outcomes_used=False)


def paired_contrasts(branches):
    main = [b for b in branches if b["case"]["kind"] == "main" and not b["case"]["fine"]]
    result = []
    for profile in PROFILES:
        for seed in SEEDS:
            for anchor in ("M", "E"):
                group = {b["case"]["policy"]: b for b in main if (b["case"]["profile"], b["case"]["seed"], b["case"]["state"]) == (profile, seed, anchor)}
                stats = {p: b["outcomes"] for p, b in group.items()}
                raw = {p: v["subsets"]["all_scored"]["final_match"] for p, v in stats.items()}
                pre = {p: v["subsets"]["all_scored"]["inherited_match"] for p, v in stats.items()}
                coefficients = {p: dict(match=raw[p], parent=stats[p]["mean_normalized_parent_contact"], cue=stats[p]["mean_normalized_cue_contact"]) for p in stats}
                pr = raw["rewritable"]-raw["reactive"]
                rf = raw["rewritable"]-raw["fixed"]
                availability = coefficients["rewritable"]["cue"]
                costs = []
                for j, (pc, cc) in enumerate((p, c) for p in COSTS for c in COSTS):
                    values = {p: v["utility_sensitivity"][j]["value"] for p, v in stats.items()}
                    best = max(values.values())
                    costs.append(dict(parent_cost=pc, cue_cost=cc, utilities=values,
                        best_policies=[p for p, v in values.items() if abs(v-best) < 1e-12]))
                subsets = {}
                for sub in stats["rewritable"]["subsets"]:
                    subsets[sub] = {p: v["subsets"][sub] for p, v in stats.items()}
                result.append(dict(profile=profile, seed=seed, founder=anchor, raw_final_match=raw, raw_inherited_match=pre,
                    rewritable_minus_fixed=rf, rewritable_minus_reactive=pr,
                    factorial_interaction=raw["rewritable"]-raw["fixed"]-raw["reactive"]+raw["neither"],
                    utility_coefficients=coefficients, cost_sensitivity=costs, subsets=subsets,
                    break_even=dict(parent_cost_vs_reactive=pr,
                        nonnegative_parent_cost_can_strictly_win=pr > 0,
                        cue_cost_vs_fixed=rf/availability if availability > 0 else None,
                        no_differential_scored_cue_use=availability == 0,
                        interpretation="U=match-parent_cost*parent-cue_cost*cue; negative thresholds are not beneficial nonnegative budgets")))
    return result


def profile_summary(contrasts):
    result = {}
    for profile in PROFILES:
        rows = [g for g in contrasts if g["profile"] == profile]
        result[profile] = dict(schedules=4, polarities_per_schedule=2,
            mean_final_match={p: float(np.mean([g["raw_final_match"][p] for g in rows])) for p, _, _ in POLICIES},
            by_seed=[dict(seed=s, mean_rewritable_minus_reactive=float(np.mean([g["rewritable_minus_reactive"] for g in rows if g["seed"] == s])),
                mean_rewritable_minus_fixed=float(np.mean([g["rewritable_minus_fixed"] for g in rows if g["seed"] == s]))) for s in SEEDS],
            superiority_sign_counts={name: dict(positive=sum(g[name] > 1e-12 for g in rows),
                tie=sum(abs(g[name]) <= 1e-12 for g in rows), negative=sum(g[name] < -1e-12 for g in rows))
                for name in ("rewritable_minus_fixed", "rewritable_minus_reactive")},
            polarities_are_paired_not_independent_environment_replicates=True)
    return result


def analyze(run):
    summary = read(run / "summary.json")
    if not summary.get("all_execution_valid"):
        raise ValueError("Require a complete execution-valid H4b panel")
    config, inputs = summary["config"], run / "inputs"
    if config != expected_config():
        raise ValueError("Unexpected H4b protocol/configuration")
    refs, indices = arrays(inputs / "references.npz"), read(inputs / "reference.json")["ion_indices"]
    branches, traces, checks, phases = [], {}, {}, []
    for case in expected_cases():
        b, trace, bc, pa = audit_branch(run / case["id"], inputs, config, case, indices, refs)
        branches.append(b)
        traces[case["id"]] = trace
        checks.update({case["id"]+"/"+g: c for g, c in bc.items()})
        phases.extend(pa)
    records = {r["id"]: r for r in summary["cases"]}
    prior = read(run / "predecessor_audit.json")
    old = prior["h4_audit"]
    current_gate = prefix_gate(run, config)
    previous = run.parents[1] / config["input_run"]
    checks["panel"] = dict(exact_records=len(records) == len(summary["cases"]) == 144 and set(records) == {c["id"] for c in expected_cases()},
        source_audited=all(old[k] for k in FLAGS) and old["quality_gate"] and old["array_check_count"] == 112544
            and all(all(c.values()) for c in old["array_checks"].values()) and prior["historical_audit_not_rewritten"] and prior["original_artifacts_unchanged"],
        source_audit_copy=file_hash(inputs / "h4_audit.json") == prior["stored_audit_sha256"],
        summary_records=all(records[c["id"]]["execution_pass"] and records[c["id"]]["returncode"] == 0 and
            records[c["id"]]["result"] == read(run / c["id"] / "result.json") for c in expected_cases()),
        prefix_gate_reconstructed=current_gate == read(run / "prefix_gate.json") == summary["prefix_gate"] and current_gate["quality_gate"],
        prefix_gate_hash=file_hash(run / "prefix_gate.json") == summary["prefix_gate_sha256"],
        no_seed_overlap=not set(SEEDS) & set(read(inputs / "h4_summary.json")["config"]["seeds"]),
        exact_manifest=read(inputs / "manifest.json") == summary["inputs"] and len(summary["inputs"]) == 114,
        exact_integrations=len(phases) == 28016,
        exact_fresh_recipient_count=sum(b["fresh_recipients"] for b in branches) == 3296,
        exact_cue_cell_count=sum(b["cue_cells_supplied"] for b in branches) == 8720,
        pinned_revision=summary["revision"] == config["revision"] == H4_FIXED["revision"],
        predecessor_run_path=prior["run"] == str(previous),
        historical_run_unchanged=snapshot(previous) == prior["original_run_sha256"],
        historical_job_unchanged=snapshot(Path(prior["job"])) == prior["original_job_sha256"])
    reg = [indices[n] for n in REGULATORS]
    scales = np.abs(refs["later"][reg, 0]-refs["later"][reg, 1])
    fine = {}
    for branch in branches:
        case = branch["case"]
        if not case["fine"]:
            continue
        base_id = case["id"].removesuffix("_fine")
        base = next(b for b in branches if b["case"]["id"] == base_id)
        fine[case["id"]] = dict(same_task_scores=base["outcomes"] == branch["outcomes"],
            identical_source=np.array_equal(traces[base_id]["source"], traces[case["id"]]["source"]),
            endpoints={k: comparison(v, traces[case["id"]][k], indices, reg, scales) for k, v in traces[base_id].items()},
            old_source_history_refined=False)
    contrasts = paired_contrasts(branches)
    report = dict(run=str(run), array_checks=checks, array_check_count=sum(len(c) for c in checks.values()),
        all_array_checks_pass=all(all(c.values()) for c in checks.values()),
        input_hashes_valid=all(file_hash(inputs / n) == v["sha256"] for n, v in summary["inputs"].items()),
        original_inputs_hashes_valid=all(file_hash(Path(v["source"])) == v["sha256"] for v in summary["inputs"].values()),
        frozen_hashes_valid=all(file_hash(run / "frozen" / n) == h for n, h in summary["frozen_hashes_sha256"].items()),
        execution_files_hashes_valid=all(file_hash(run.parents[1] / n) == h for n, h in summary["hashes_sha256"].items()),
        predecessor_audit_hash_valid=file_hash(run / "predecessor_audit.json") == summary["predecessor_audit_sha256"],
        historical_benchmarks_pass=current_gate["quality_gate"], prefix_gate=current_gate, fine_comparisons=fine,
        selected_fine_agreement=len(fine) == 8 and all(x["same_task_scores"] and x["identical_source"] and
            all(v["same_labels"] for v in x["endpoints"].values()) for x in fine.values()),
        branches=branches, paired_contrasts=contrasts, profile_summary=profile_summary(contrasts),
        new_integrations=len(phases), new_snapshots=sum(p["samples"] for p in phases),
        fresh_recipients=sum(b["fresh_recipients"] for b in branches), cue_cells_supplied=sum(b["cue_cells_supplied"] for b in branches),
        elapsed_seconds=summary["elapsed_seconds"], integration_cpu_seconds=sum(p["cpu_seconds"] for p in phases),
        ecological_fitness_measured=False, autonomous_reproduction=False, hidden_truth_used_for_dynamics=False,
        costs_are_declared_assumptions=True, outcome_dependent_selection=False,
        binary_reference_must_agree_for_quality=False)
    report["quality_gate"] = all(report[k] for k in FLAGS) and report["historical_benchmarks_pass"] and report["selected_fine_agreement"]
    report["ready_for_interpretation"] = report["quality_gate"]
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
        report["failed_checks"] = {g: [k for k, v in c.items() if not v] for g, c in report.pop("array_checks").items() if not all(c.values())}
        for name in ("branches", "fine_comparisons", "paired_contrasts"):
            report.pop(name)
    import json
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if all(report[k] for k in FLAGS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
