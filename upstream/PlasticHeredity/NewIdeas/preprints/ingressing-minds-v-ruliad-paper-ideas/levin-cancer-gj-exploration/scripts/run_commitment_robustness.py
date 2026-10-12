"""Fixed robustness stresses selected from the audited commitment factorial."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_group_transfer import arrays
from bounded_extension import run_bounded
from memory_metrics import classify
from robust_relay import hold_pair, round_worker
from run_memory_probe import write_json
from run_onward_transfer import file_hash
from run_pilot import ROOT, REVISION
from run_rehoming import verify_source_run

SOURCE_MASKS = dict(transient=0, protein=1, rna=2, committed=7)


def validate_config(config):
    fixed = dict(revision=REVISION, input_run="runs/commitment-components-20260906T171654Z-17g1l8yg",
        packet_size=2, continuing_rounds=[4, 5], cue_holds=[10000, 10000], write_kd=2e-15,
        contact_horizon=1000, retention_horizons=[10000, 10000], recovery_horizon=5000,
        perturbation_fraction=.2, late_label_fraction=.95, minimum_challenge_distance=.1,
        recovery_absolute_tolerance=.02, recovery_distance_ratio=.2, jitter_fraction=.1, jitter_indices=[5, 6, 7],
        seeds=dict(screen=2026090601, validation=2026090602), irregular_contacts=[500, 1500],
        profiles=["none", "jitter", "timing", "loss", "combined", "validation"],
        backgrounds=["transient", "protein", "rna", "committed", "ordinary"])
    if any(config.get(k) != v for k, v in fixed.items()):
        raise ValueError("Changed fixed robustness parameters")
    if not 1 <= config["workers"] <= 2 or not 0 < config["worker_timeout_seconds"] <= 900 or not 0 < config["total_budget_seconds"] <= 3600:
        raise ValueError("Exceeds execution bounds")
    expected = []
    for fine, profiles, backgrounds in ((False, fixed["profiles"], fixed["backgrounds"]),
            (True, ["none", "combined", "validation"], ["protein", "rna"])):
        for profile in profiles:
            for background in backgrounds:
                expected.append(dict(id=background + "_" + profile + ("_fine" if fine else ""), background=background,
                    profile=profile, state="M", old_state="E", fine=fine, seed=2026090602 if profile == "validation" else 2026090601))
    if config["cases"] != expected:
        raise ValueError("Require fixed 36-case grid, seeds and order")


def design(case):
    rng = np.random.Generator(np.random.PCG64(case["seed"]))
    raw = 1 + rng.uniform(-.1, .1, size=(3, 6))
    timing = rng.integers(0, 2, size=2).tolist()
    survivors = rng.integers(0, 2, size=2).tolist()
    profile = case["profile"]
    jitter = profile in ("jitter", "combined", "validation")
    irregular = profile in ("timing", "combined", "validation")
    loss = profile in ("loss", "combined", "validation")
    plans = [dict(round=4 + j, contacts=([500, 1500] if timing[j] == 0 else [1500, 500]) if irregular else [1000, 1000],
        active_columns=[survivors[j]] if loss else [0, 1]) for j in range(2)]
    return dict(seed=case["seed"], generator="PCG64", raw_multipliers=raw.tolist(),
        multipliers=(raw if jitter else np.ones((3, 6))).tolist(), timing_choices=timing, survivor_choices=survivors, rounds=plans)


def perturb_state(state, factors):
    if state.shape[0] != 17 or factors.shape != (3, state.shape[1]) or not np.isfinite(factors).all() or np.any(factors < .9) or np.any(factors > 1.1):
        raise ValueError("Invalid bounded regulator variation")
    changed = state.copy()
    changed[5:8] *= factors
    return changed


def source_name(case):
    if case["background"] == "ordinary":
        return None
    return f"m_components_{SOURCE_MASKS[case['background']]:03b}" + ("_fine" if case["fine"] else "")


def load_source(inputs, case, indices, refs):
    name = source_name(case)
    ids = [f"{case['id']}:placed:carrier_{i}" for i in (1, 2)]
    if name is None:
        packet, seen = np.repeat(refs["prepared"][:, 1:2], 2, axis=1), set()
        record = dict(background="ordinary", previous_case=None, file="references.npz", key="prepared", column=1,
            source_ids=[], excluded_predecessor_assay_ids=[], ordinary_not_age_matched=True)
    else:
        meta = json.loads((inputs / (name + ".json")).read_text())
        packet = arrays(inputs / (name + "_entry.npz"))["canonical_entry"].copy()
        expected_success = case["background"] != "transient"
        if meta["case"]["id"] != name or meta["case"]["mask"] != SOURCE_MASKS[case["background"]] or meta["case"]["fine"] != case["fine"]:
            raise ValueError("Wrong source mask/refinement")
        if not meta["execution_pass"] or meta["durable_M"] != expected_success:
            raise ValueError("Required source phenotype not audited")
        source_ids = meta["source"]["intervention_ids"]
        future = [i for r in meta["rounds"] for i in r["outgoing_ids"]]
        seen = set(meta["source"]["excluded_ids"]) | set(future)
        if len(seen) != 36 or len(source_ids) != 2 or not set(source_ids).issubset(seen):
            raise ValueError("Invalid predecessor identity exclusion ledger")
        record = dict(background=case["background"], previous_case=name, file=name + "_entry.npz", key="canonical_entry",
            source_ids=source_ids, excluded_predecessor_assay_ids=future, ordinary_not_age_matched=False)
    if packet.shape != (17, 2) or not np.isfinite(packet).all() or np.any(packet < 0) or not np.all(packet[4] == 72) or not np.all(packet[16] == 0) or classify(packet, indices).tolist() != ["M", "M"]:
        raise ValueError("Invalid full M-labelled source entry")
    if set(ids) & seen:
        raise ValueError("New placement IDs collide with source ledger")
    seen.update(ids)
    record.update(placement_ids=ids, excluded_ids=sorted(seen), source_before_holds=True, artificial_placements=True)
    return packet, ids, seen, record


def branch_worker(folder, config, case, inputs):
    validate_config(config)
    refs = arrays(inputs / "references.npz")
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    source, ids, seen, provenance = load_source(inputs, case, indices, refs)
    plan = design(case)
    factors = np.array(plan["multipliers"])
    initial = perturb_state(source, factors[:, :2])
    targets = perturb_state(np.repeat(refs["prepared"][:, :1], 4, axis=1), factors[:, 2:])
    if classify(targets, indices).tolist() != ["E"] * 4:
        raise ValueError("Perturbed fresh recipients no longer start E; no resampling")
    write_json(folder / "source.json", provenance)
    write_json(folder / "design.json", plan)
    packet, retention = hold_pair(folder / "retention", config, case, initial, ids, indices)
    start, initial_seen, rounds = packet.copy(), len(seen), []
    for j, n in enumerate((4, 5)):
        stage = folder / f"round_{n:02}"
        stage.mkdir()
        packet, ids, row = round_worker(stage, config, case, packet, ids, seen,
            targets[:, 2 * j:2 * j + 2], refs["later"], indices, n, plan["rounds"][j])
        seen.update(ids)
        rounds.append(row)
        write_json(folder / "progress.json", rounds)
        print(f"ROBUSTNESS_ROUND {n}: {''.join(classify(packet, indices))}; transfer={row['round_success']}", flush=True)
    renewed = all(r["round_success"] for r in rounds)
    np.savez_compressed(folder / "endpoints.npz", source_packet=source, perturbed_entry=initial,
        fresh_targets=targets, continuing_start=start, final_packet=packet)
    result = dict(case=case, execution_pass=True, ion_indices=indices, source=provenance, design=plan,
        retention=retention, rounds=rounds, final_ids=ids, distinct_fresh_targets=len(seen) - initial_seen,
        lost_carriers=sum(len(r["lost_ids"]) for r in rounds), M_retained=retention["M_retained"],
        M_renewed=renewed, durable_M=retention["M_retained"] and renewed,
        first_failed_stage="retention" if not retention["M_retained"] else next((f"round_{r['round']}" for r in rounds if not r["round_success"]), None))
    write_json(folder / "result.json", result)
    return 0


def freeze_inputs(run, config):
    from analyze_commitment_components import analyze, FLAGS
    previous = (ROOT / config["input_run"]).resolve()
    if previous.parent != ROOT / "runs":
        raise ValueError("Source must be an exploration run")
    summary, report = verify_source_run(previous, config, analyze)
    if report["array_check_count"] != 3893 or len(report["branches"]) != 16 or not all(report[k] for k in FLAGS) or not report["eligible_for_stage2_design"]:
        raise RuntimeError("Component-source gate or re-audit failed")
    write_json(run / "predecessor_audit.json", report)
    paths = {n: previous / "inputs" / n for n in ("references.npz", "reference.json")}
    paths["components_summary.json"] = previous / "summary.json"
    for case in config["cases"]:
        name = source_name(case)
        if name:
            paths[name + ".json"] = previous / name / "result.json"
            paths[name + "_entry.npz"] = previous / name / "retention/endpoints.npz"
            for n in (4, 5):
                paths[name + f"_round_{n:02}.npz"] = previous / name / f"round_{n:02}/endpoints.npz"
    if len(paths) != 27:
        raise RuntimeError("Incomplete fixed source/control manifest")
    inputs = run / "inputs"
    inputs.mkdir()
    manifest = {}
    for name, path in paths.items():
        h = file_hash(path)
        (inputs / name).write_bytes(path.read_bytes())
        if file_hash(path) != h or file_hash(inputs / name) != h:
            raise RuntimeError("Source changed while copying")
        manifest[name] = dict(source=str(path), sha256=h)
    refs = arrays(inputs / "references.npz")
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    for case in config["cases"]:
        source, *_ = load_source(inputs, case, indices, refs)
        factors = np.array(design(case)["multipliers"])
        perturb_state(source, factors[:, :2])
        targets = perturb_state(np.repeat(refs["prepared"][:, :1], 4, axis=1), factors[:, 2:])
        if classify(targets, indices).tolist() != ["E"] * 4:
            raise ValueError("Frozen recipient perturbations violate E-start control")
    write_json(inputs / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/commitment_robustness_v1.json")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        spec = json.loads(args.worker.read_text())
        return branch_worker(args.worker.parent, spec["config"], spec["case"], Path(spec["inputs"]))
    config = json.loads(args.config.read_text())
    validate_config(config)
    previous = json.loads((ROOT / config["input_run"] / "summary.json").read_text())
    helpers = {Path(n).name for n in previous["hashes_sha256"] if n.startswith("scripts/")}
    helpers.update(("robust_relay.py", "analyze_commitment_robustness.py", "test_commitment_robustness.py",
        "run_commitment_robustness_detached.py", "test_detached_robustness.py"))
    return run_bounded(args.config.resolve(), Path(__file__).resolve(), ROOT / "COMMITMENT_ROBUSTNESS_PROTOCOL.md",
        sorted(helpers), freeze_inputs, "commitment-robustness", "Fixed regulator variation, unequal writes and carrier loss; no ecological fitness")


if __name__ == "__main__":
    raise SystemExit(main())
