"""Independent H4 reconstruction and declared task scoring; no simulator calls."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_commitment_components import FLAGS, canonical_state
from analyze_group_transfer import arrays
from analyze_pulse_spacing import check_phase, comparison
from analyze_reliability import audit_source, audit_round
from memory_metrics import REGULATORS, classify
from run_memory_probe import array_hash, write_json
from run_onward_transfer import file_hash


def read(path):
    return json.loads(path.read_text())


def expected_cases():
    policies = [("rewritable", True, True), ("fixed", True, False), ("reactive", False, True), ("neither", False, False)]
    cases = []
    groups = [(r, s, a, False) for r in ("constant", "slow", "rapid", "misleading")
        for s in (2026090801, 2026090811) for a in ("M", "E")]
    groups += [("misleading", 2026090811, a, True) for a in ("M", "E")]
    for regime, seed, anchor, fine in groups:
        for p, parent, cue in policies:
            cases.append(dict(id=f"{p}__{regime}__{seed}__{anchor}"+("_fine" if fine else ""),
                kind="main", policy=p, regime=regime, seed=seed, state=anchor,
                parent_enabled=parent, cue_enabled=cue, fine=fine))
    cases.extend(dict(id="benchmark__"+a+("_fine" if f else ""), kind="benchmark", state=a, fine=f)
        for a in ("M", "E") for f in (False, True))
    return cases


def expected_schedule(case):
    gen = np.random.Generator(np.random.PCG64(case["seed"]))
    order = list(map(int, gen.permutation([2, 3, 4, 5, 6])))
    incorrect = list(map(int, gen.permutation(order[:3])))
    available = [1]+sorted(order[:3])
    wrong = sorted(incorrect[:2]) if case["regime"] == "misleading" else []
    other = {"E": "M", "M": "E"}
    relative = {"constant": [0]*6, "slow": [0, 0, 0, 1, 1, 1],
        "rapid": [0, 1, 0, 1, 0, 1], "misleading": [0, 0, 0, 1, 1, 1]}[case["regime"]]
    truth = [other[case["state"]] if v else case["state"] for v in relative]
    visible = [None if n not in available else other[s] if n in wrong else s for n, s in enumerate(truth, 1)]
    return dict(generator="PCG64", seed=case["seed"], availability_order=order, corruption_order=incorrect,
        available_epochs=available, corrupted_epochs=wrong, hidden_truth=truth, visible_cues=visible, bootstrap_epoch=1)


def expected_handover(epoch, active, benchmark=False):
    start = (epoch-1)*42100 if not benchmark else 0
    return dict(round=epoch, contacts=[1000, 1000], active_columns=[0, 1], write_kd=2e-15,
        connected=active, nominal_start=start, nominal_end=start+22000,
        shock_factors=[[[1., 1.], [1., 1.], [1., 1.]], [[1., 1.], [1., 1.], [1., 1.]]])


def audit_cue(folder, config, case, epoch, incoming, ids, seen, prepared, indices, visible):
    result, saved = read(folder / "result.json"), arrays(folder / "endpoints.npz")
    active = bool(case["cue_enabled"] and visible is not None)
    cues = np.repeat(prepared[:, {"E": 0, "M": 1}[visible], None], 5, axis=1) if visible else np.empty((17, 0))
    cue_ids = [f"{case['id']}:epoch_{epoch:02}:recipient_{i}:cue_{j}" for i in (1, 2) for j in range(1, cues.shape[1]+1)]
    names = [f"child_{i}_"+p for i in (1, 2) for p in ("cue", "hold_1", "hold_2")]
    setups = {r["phase"]: r for r in result["setups"]}
    records = {r["phase"]: r for r in result["audits"]}
    checks = dict(execution=result["execution_pass"], phase_order=[r["phase"] for r in result["audits"]] == names,
        exact_builds=len(result["setups"]) == 4 and set(setups) == {n for n in names if not n.endswith("hold_2")},
        exact_incoming=np.array_equal(saved["incoming_packet"], incoming),
        exact_visible_cue=np.array_equal(saved["cue_template"], cues) and result["visible_cue"] == visible,
        same_actual_recipients=result["incoming_ids"] == result["outgoing_ids"] == ids,
        cue_ids_fresh_removed=result["removed_cue_ids"] == cue_ids and len(cue_ids) == len(set(cue_ids)) and not set(cue_ids) & seen,
        fixed_channel_control=result["connected"] == active and result["cue_enabled"] == case["cue_enabled"],
        cue_opportunity_and_cost=result["cue_cells_supplied"] == len(cue_ids) and result["active_cue_edge_time"] == (len(cue_ids)*100 if active else 0),
        epoch_identity=result["epoch"] == epoch)
    contacts, firsts, finals, fractions, trace = [], [], [], [], {}
    for i in (1, 2):
        state = np.concatenate((incoming[:, i-1:i], cues), axis=1)
        fr = []
        for suffix, duration in (("cue", 100), ("hold_1", 10000), ("hold_2", 10000)):
            name = f"child_{i}_{suffix}"
            state, row, pc = check_phase(folder, name, duration, indices, state, state.shape[1],
                active if suffix == "cue" else False, 2e-15, records[name], setups.get(name))
            checks.update({name+"/"+k: v for k, v in pc.items()})
            raw = arrays(folder / (name+".npz"))
            checks[name+"/canonical_RNA"] = all(np.allclose(raw[k], canonical_state(raw[k]), rtol=1e-12, atol=1e-14) for k in ("initial", "final"))
            trace[name] = state.copy()
            if suffix == "cue":
                contacts.append(state[:, :1])
                state = state[:, :1].copy()  # Remove EVERY cue cell; retain the actual recipient.
            elif suffix == "hold_1":
                firsts.append(state)
                fr.append(row["late_label_fractions"])
            else:
                finals.append(state)
                fr.append(row["late_label_fractions"])
        fractions.append(fr)
    checkpoints = [np.concatenate(parts, axis=1) for parts in (contacts, firsts, finals)]
    checks.update(exact_saved_checkpoints=all(np.array_equal(saved[k], a) for k, a in zip(("contact_packet", "held_first", "outgoing_packet"), checkpoints)),
        exact_final_label=result["final_labels"] == "".join(classify(checkpoints[-1], indices)),
        final_hash=result["outgoing_packet_hash"] == array_hash(checkpoints[-1]))
    return checkpoints, cue_ids, fractions, trace, {k: bool(v) for k, v in checks.items()}, result["audits"]


def score_epoch(epoch, truth, previous_truth, visible, labels, parent_on, cue_on):
    fractions = [sum(c == truth for c in pair)/2 for pair in labels]
    # Persistence is checked only at these four observations, not continuously.
    earliest = next((t for j, t in enumerate((22000, 22100, 32100, 42100)) if all(v == 1 for v in fractions[j:])), None)
    return dict(epoch=epoch, truth=truth, visible_cue=visible, cue_present=visible is not None,
        misleading=visible is not None and visible != truth, switched=previous_truth is not None and previous_truth != truth,
        checkpoint_labels=labels, checkpoint_match_fractions=fractions,
        inherited_match=fractions[0], final_match=fractions[-1], both_final_correct=fractions[-1] == 1,
        earliest_sustained_correct_checkpoint=earliest,
        active_parent_edge_time=4000 if parent_on else 0,
        active_cue_edge_time=1000 if cue_on and visible is not None else 0)


def summarize_scores(rows):
    selected = rows[1:]  # Bootstrap excluded from primary scoring and costs.
    mean = lambda seq, key: float(np.mean([r[key] for r in seq])) if seq else None
    subsets = dict(all_scored=selected, cue_missing=[r for r in selected if not r["cue_present"]],
        cue_present=[r for r in selected if r["cue_present"]], misleading=[r for r in selected if r["misleading"]],
        truthful=[r for r in selected if r["cue_present"] and not r["misleading"]],
        switching=[r for r in selected if r["switched"]], stable=[r for r in selected if not r["switched"]])
    outcome = {k: dict(epochs=len(rs), inherited_match=mean(rs, "inherited_match"), final_match=mean(rs, "final_match"),
        both_final_correct=mean(rs, "both_final_correct")) for k, rs in subsets.items()}
    parent = mean(selected, "active_parent_edge_time")/4000
    cue = mean(selected, "active_cue_edge_time")/1000
    utility = [dict(parent_cost=p, cue_cost=c, value=mean(selected, "final_match")-p*parent-c*cue)
        for p in (0, .1, .3) for c in (0, .1, .3)]
    return dict(subsets=outcome, all_six_final_match=mean(rows, "final_match"),
        mean_normalized_parent_contact=parent, mean_normalized_cue_contact=cue, utility_sensitivity=utility)


def audit_branch(folder, inputs, config, case, indices, refs):
    source_spec = dict(id=case["id"]+":source", state=case["state"],
        family="protein_m_pair" if case["state"] == "M" else "pooled_rewritten_e_pair",
        fine=case["fine"] and case["kind"] == "benchmark")
    source, ids, seen, provenance, sc = audit_source(inputs, config, source_spec, indices)
    saved = arrays(folder / "endpoints.npz")
    result = read(folder / "result.json")
    checks = {"source": sc}
    trace, phases, scored = {"source": source}, [], []
    packet = source.copy()
    if case["kind"] == "benchmark":
        fresh = np.repeat(refs["prepared"][:, 0 if case["state"] == "M" else 1, None], 2, axis=1)
        packet, ids, row, rc, pa = audit_round(folder / "round_01", config, case, 1, packet, ids, seen,
            fresh, refs["later"], indices, expected_handover(1, True, True))
        checks["benchmark"] = rc
        phases.extend(pa)
        historical = arrays(inputs / ("benchmark_"+case["state"]+("_fine" if case["fine"] else "")+".npz"))
        new = arrays(folder / "round_01/endpoints.npz")
        benchmark_pass = set(historical) == set(new) and all(np.array_equal(v, new[k]) for k, v in historical.items()) and row["round_success"]
        checks["benchmark_record"] = dict(same_result=result["benchmark"] == read(folder / "round_01/result.json"))
        fresh_count, cue_count = 2, 0
    else:
        plan = expected_schedule(case)
        checks["schedule"] = dict(complete_visible_and_hidden_schedule=result["design"] == read(folder / "design.json") == plan,
            six_epochs=len(result["epochs"]) == 6)
        cue_count = 0
        for epoch, visible in enumerate(plan["visible_cues"], 1):
            parent_ids = ids.copy()
            fresh = refs["prepared"][:, [0, 1] if epoch % 2 else [1, 0]].copy()
            stage = folder / f"epoch_{epoch:02}_inheritance"
            dyn_case = dict(id=case["id"], state=case["state"], fine=case["fine"])
            packet, ids, row, rc, pa = audit_round(stage, config, dyn_case, epoch, packet, ids, seen,
                fresh, refs["later"], indices, expected_handover(epoch, case["parent_enabled"]))
            # Explicit assay change: replace exactly ONE old opposite-target check.
            # All other old physics/continuity/identity/diagnostic checks remain.
            if "exact_fresh_targets" not in rc:
                raise ValueError("Legacy audit contract changed")
            relay_arrays = arrays(stage / "endpoints.npz")
            rc["exact_fresh_targets"] = bool(np.array_equal(relay_arrays["fresh_targets"], fresh)
                and classify(fresh, indices).tolist() == (["E", "M"] if epoch % 2 else ["M", "E"]))
            checks[f"epoch_{epoch}/inheritance"] = rc
            phases.extend(pa)
            seen.update(ids)
            pre = packet.copy()
            cue_folder = folder / f"epoch_{epoch:02}_cue"
            cp, removed_cues, late, cue_trace, cc, pa = audit_cue(cue_folder, config, case, epoch,
                packet, ids, seen, refs["prepared"], indices, visible)
            checks[f"epoch_{epoch}/cue"] = cc
            phases.extend(pa)
            seen.update(removed_cues)
            cue_count += len(removed_cues)
            packet = cp[-1]
            labels = ["".join(classify(a, indices)) for a in [pre]+cp]
            scores = score_epoch(epoch, plan["hidden_truth"][epoch-1], plan["hidden_truth"][epoch-2] if epoch > 1 else None,
                visible, labels, case["parent_enabled"], case["cue_enabled"])
            scored.append(dict(scores, post_hold_late_fractions=late,
                inherited_local_recoveries=[c["recovery"] for c in row["children"]]))
            actual = result["epochs"][epoch-1]
            checks[f"epoch_{epoch}/record"] = dict(actual_parent_ids_removed=actual["removed_parent_ids"] == parent_ids,
                exact_phase_records=actual["inheritance"] == read(stage / "result.json") and actual["cue"] == read(cue_folder / "result.json"),
                equal_clock=actual["nominal_start"] == 42100*(epoch-1) and actual["nominal_end"] == 42100*epoch,
                resource_accounting=actual["fresh_recipients"] == 2 and actual["active_parent_edge_time"] == scores["active_parent_edge_time"],
                epoch_identity=actual["epoch"] == epoch)
            trace.update({f"{epoch}/relay/"+k: v for k, v in relay_arrays.items() if v.ndim == 2 and v.shape[0] == 17})
            trace.update({f"{epoch}/cue/"+k: v for k, v in cue_trace.items()})
        fresh_count, benchmark_pass = 12, None
    checks["branch"] = dict(exact_case=result["case"] == case and result["execution_pass"] and result["ion_indices"] == indices,
        source_provenance=result["source"] == read(folder / "source.json") == provenance,
        source_unchanged=np.array_equal(saved["source_packet"], source),
        final_actual_packet=np.array_equal(saved["final_packet"], packet),
        exact_final_ids=result["final_ids"] == ids and len(set(ids)) == 2 and not set(ids) & set(provenance["excluded_ids"]),
        declared_counts=result["fresh_recipients"] == fresh_count and result["cue_cells_supplied"] == cue_count,
        integration_count=len(phases) == (11 if case["kind"] == "benchmark" else 102),
        no_ecological_fitness_claim=result["ecological_fitness_measured"] is False)
    branch = dict(case=case, source=provenance, epochs=scored, historical_benchmark_pass=bool(benchmark_pass) if benchmark_pass is not None else None,
        outcomes=summarize_scores(scored) if scored else None, fresh_recipients=fresh_count, cue_cells_supplied=cue_count)
    return branch, trace, {group: {k: bool(v) for k, v in cs.items()} for group, cs in checks.items()}, phases


def paired_contrasts(branches):
    main = [b for b in branches if b["case"]["kind"] == "main" and not b["case"]["fine"]]
    result = []
    for r in ("constant", "slow", "rapid", "misleading"):
        for s in (2026090801, 2026090811):
            for a in ("M", "E"):
                group = {b["case"]["policy"]: b for b in main if (b["case"]["regime"], b["case"]["seed"], b["case"]["state"]) == (r, s, a)}
                subsets = {}
                for sub in next(iter(group.values()))["outcomes"]["subsets"]:
                    d = {p: b["outcomes"]["subsets"][sub]["final_match"] for p, b in group.items()}
                    subsets[sub] = dict(scores=d, rewritable_minus_fixed=None if d["rewritable"] is None else d["rewritable"]-d["fixed"],
                        rewritable_minus_reactive=None if d["rewritable"] is None else d["rewritable"]-d["reactive"],
                        interaction=None if d["rewritable"] is None else d["rewritable"]-d["fixed"]-d["reactive"]+d["neither"])
                costs = []
                for j in range(9):
                    d = {p: b["outcomes"]["utility_sensitivity"][j]["value"] for p, b in group.items()}
                    row = group["rewritable"]["outcomes"]["utility_sensitivity"][j]
                    best = max(d.values())
                    costs.append(dict(parent_cost=row["parent_cost"], cue_cost=row["cue_cost"], scores=d,
                        best_policies=[p for p, value in d.items() if abs(value-best) < 1e-12]))
                result.append(dict(regime=r, seed=s, founder=a, contrasts=subsets, cost_sensitivity=costs))
    return result


def analyze(run):
    summary = read(run / "summary.json")
    if not summary.get("all_execution_valid"):
        raise ValueError("Require a complete H4 execution-valid panel")
    config, inputs = summary["config"], run / "inputs"
    cases = expected_cases()
    if config["cases"] != cases:
        raise ValueError("Unexpected H4 case grid")
    refs, indices = arrays(inputs / "references.npz"), read(inputs / "reference.json")["ion_indices"]
    reg = [indices[k] for k in REGULATORS]
    scales = np.abs(refs["later"][reg, 0]-refs["later"][reg, 1])
    branches, traces, checks, phases = [], {}, {}, []
    for case in cases:
        b, trace, bc, pa = audit_branch(run / case["id"], inputs, config, case, indices, refs)
        branches.append(b)
        traces[case["id"]] = trace
        checks.update({case["id"]+"/"+g: c for g, c in bc.items()})
        phases.extend(pa)
    records = {r["id"]: r for r in summary["cases"]}
    prior = read(run / "predecessor_audit.json")
    old = prior["h3_audit"]
    fixed = dict(epochs=6, workers=2, worker_timeout_seconds=1800, total_budget_seconds=28800,
        packet_size=2, write_kd=2e-15, contact_horizon=1000, retention_horizons=[10000, 10000],
        recovery_horizon=5000, perturbation_fraction=.2, late_label_fraction=.95,
        minimum_challenge_distance=.1, recovery_absolute_tolerance=.02, recovery_distance_ratio=.2,
        cue_count=5, cue_horizon=100, cue_holds=[10000, 10000], seeds=[2026090801, 2026090811],
        nominal_epoch_duration=42100, costs=[0, .1, .3], minimum_free_bytes=5*1024**3,
        revision="b2cb370aaecbc8299f259bc4251d5396c81f19a6",
        input_run="runs/reliability-confirmation-recovery-20260907T173445Z-a4rd3ibl")
    checks["panel"] = dict(fixed_parameters=all(config.get(k) == v for k, v in fixed.items()) and set(config) == set(fixed)|{"cases"},
        exactly_76_records=len(records) == len(summary["cases"]) == 76 and set(records) == {c["id"] for c in cases},
        summary_records_match=all(records[c["id"]]["execution_pass"] and records[c["id"]]["returncode"] == 0
            and records[c["id"]]["result"] == read(run / c["id"] / "result.json") for c in cases),
        immutable_predecessor_audited=all(old[k] for k in FLAGS) and old["quality_gate"] and old["ready_for_benefit_design"]
            and old["array_check_count"] == 79113 and all(all(c.values()) for c in old["array_checks"].values())
            and prior["recovery_provenance_pass"] and prior["original_artifacts_unchanged"] and prior["historical_audit_not_rewritten"],
        prior_audit_copy=file_hash(inputs / "h3_audit") == prior["stored_audit_sha256"],
        exact_manifest=read(inputs / "manifest.json") == summary["inputs"] and len(summary["inputs"]) == 72,
        exact_integration_count=len(phases) == 7388,
        exact_recipient_count=sum(b["fresh_recipients"] for b in branches) == 872,
        exact_cue_count=sum(b["cue_cells_supplied"] for b in branches) == 2880,
        pinned_revision=summary["revision"] == config["revision"] == fixed["revision"])
    fine = {}
    for b in branches:
        case = b["case"]
        if case["kind"] != "main" or not case["fine"]:
            continue
        base_id = case["id"].removesuffix("_fine")
        base = next(x for x in branches if x["case"]["id"] == base_id)
        fine[case["id"]] = dict(same_task_scores=base["outcomes"] == b["outcomes"],
            identical_source=np.array_equal(traces[base_id]["source"], traces[case["id"]]["source"]),
            endpoints={k: comparison(v, traces[case["id"]][k], indices, reg, scales) for k, v in traces[base_id].items()},
            old_source_history_refined=False)
    controls = {b["case"]["id"]: b["historical_benchmark_pass"] for b in branches if b["case"]["kind"] == "benchmark"}
    report = dict(run=str(run), all_array_checks_pass=all(all(c.values()) for c in checks.values()),
        array_checks=checks, array_check_count=sum(len(c) for c in checks.values()),
        input_hashes_valid=all(file_hash(inputs / n) == v["sha256"] for n, v in summary["inputs"].items()),
        original_inputs_hashes_valid=all(file_hash(Path(v["source"])) == v["sha256"] for v in summary["inputs"].values()),
        frozen_hashes_valid=all(file_hash(run / "frozen" / n) == h for n, h in summary["frozen_hashes_sha256"].items()),
        execution_files_hashes_valid=all(file_hash(run.parents[1] / n) == h for n, h in summary["hashes_sha256"].items()),
        predecessor_audit_hash_valid=file_hash(run / "predecessor_audit.json") == summary["predecessor_audit_sha256"],
        branches=branches, fine_comparisons=fine, historical_benchmarks=controls,
        historical_benchmarks_pass=len(controls) == 4 and all(controls.values()),
        selected_fine_agreement=len(fine) == 8 and all(x["same_task_scores"] and x["identical_source"]
            and all(v["same_labels"] for v in x["endpoints"].values()) for x in fine.values()),
        paired_contrasts=paired_contrasts(branches), new_integrations=len(phases),
        new_snapshots=sum(p["samples"] for p in phases), fresh_recipients=sum(b["fresh_recipients"] for b in branches),
        cue_cells_supplied=sum(b["cue_cells_supplied"] for b in branches),
        elapsed_seconds=summary["elapsed_seconds"], integration_cpu_seconds=sum(p["cpu_seconds"] for p in phases),
        ecological_fitness_measured=False, autonomous_reproduction=False, hidden_truth_used_for_dynamics=False,
        outcome_dependent_selection=False, costs_are_declared_assumptions=True)
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
        report.pop("branches")
        report.pop("fine_comparisons")
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if all(report[k] for k in FLAGS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
