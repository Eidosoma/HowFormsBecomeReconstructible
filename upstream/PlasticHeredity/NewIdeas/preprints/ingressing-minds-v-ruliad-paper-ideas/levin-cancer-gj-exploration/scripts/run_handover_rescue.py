"""Bounded M-handover duration/miRNA-coupling panel from audited held pairs."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_group_transfer import arrays
from bounded_extension import run_bounded
from handover_rescue_relay import round_worker
from memory_metrics import classify
from run_memory_probe import write_json
from run_onward_transfer import file_hash
from run_pilot import ROOT, REVISION
from run_rehoming import verify_source_run

PROFILES = [
    dict(id="pair", donors=2, contact_horizon=1000, kd_factor=1),
    dict(id="single", donors=1, contact_horizon=1000, kd_factor=1),
    dict(id="single_long", donors=1, contact_horizon=2000, kd_factor=1),
    dict(id="single_longer", donors=1, contact_horizon=4000, kd_factor=1),
    dict(id="single_strong", donors=1, contact_horizon=1000, kd_factor=2),
    dict(id="single_weak", donors=1, contact_horizon=1000, kd_factor=.5),
    dict(id="pair_weak", donors=2, contact_horizon=1000, kd_factor=.5),
]


def validate_config(config):
    fixed = dict(revision=REVISION,
        input_run="runs/commitment-robustness-20260906T193416Z-u7q1u4lo",
        packet_size=2, continuing_rounds=[4, 5], write_kd=2e-15, contact_horizon=1000,
        retention_horizons=[10000, 10000], recovery_horizon=5000,
        perturbation_fraction=.2, late_label_fraction=.95, minimum_challenge_distance=.1,
        recovery_absolute_tolerance=.02, recovery_distance_ratio=.2,
        starting_nominal_time=20000, survivor_columns=[0, 1],
        profiles=PROFILES, backgrounds=["protein", "rna", "ordinary"])
    if any(config.get(k) != v for k, v in fixed.items()):
        raise ValueError("Changed fixed handover-rescue parameters")
    if not 1 <= config["workers"] <= 2 or not 0 < config["worker_timeout_seconds"] <= 900 or not 0 < config["total_budget_seconds"] <= 3600:
        raise ValueError("Exceeds execution bounds")
    expected = []
    for fine in (False, True):
        for profile in PROFILES:
            for background in (["protein", "rna"] if fine else fixed["backgrounds"]):
                expected.append(dict(id=background + "_" + profile["id"] + ("_fine" if fine else ""),
                    background=background, profile=profile["id"], state="M", old_state="E", fine=fine))
    if config["cases"] != expected:
        raise ValueError("Require all 35 predeclared cases in fixed order")


def design(case):
    profile = next(p for p in PROFILES if p["id"] == case["profile"])
    clock, rounds = 20000, []
    for j, number in enumerate((4, 5)):
        duration = profile["contact_horizon"]
        end = clock + 2 * duration + 20000
        rounds.append(dict(round=number, contacts=[duration, duration],
            active_columns=[j] if profile["donors"] == 1 else [0, 1],
            write_kd=2e-15 * profile["kd_factor"], nominal_start=clock, nominal_end=end))
        clock = end
    return dict(profile=profile, rounds=rounds)


def source_name(case):
    return case["background"] + "_none" + ("_fine" if case["fine"] else "")


def benchmark_name(case):
    if case["profile"] == "pair":
        return source_name(case)
    if case["profile"] == "single" and not case["fine"]:
        return case["background"] + "_loss"
    return None


def load_source(inputs, case, indices):
    name = source_name(case)
    meta = json.loads((inputs / (name + ".json")).read_text())
    packet = arrays(inputs / (name + "_held.npz"))["continuing_packet"].copy()
    if (meta["case"]["id"], meta["case"]["background"], meta["case"]["profile"], meta["case"]["fine"]) != (name, case["background"], "none", case["fine"]):
        raise ValueError("Wrong source origin, condition or numerical setting")
    if not meta["execution_pass"] or not meta["M_retained"] or not meta["retention"]["M_retained"] or not meta["durable_M"]:
        raise ValueError("Source does not meet the audited memory gate")
    source_ids = meta["retention"]["outgoing_ids"]
    future_ids = [i for r in meta["rounds"] for i in r["outgoing_ids"]]
    seen = set(meta["source"]["excluded_ids"]) | set(future_ids)
    expected_count = 6 if case["background"] == "ordinary" else 42
    if len(source_ids) != 2 or len(set(source_ids)) != 2 or not set(source_ids).issubset(seen) or len(set(future_ids)) != 4 or len(seen) != expected_count:
        raise ValueError("Invalid predecessor identity ledger")
    if packet.shape != (17, 2) or not np.isfinite(packet).all() or np.any(packet < 0) or not np.all(packet[4] == 72) or not np.all(packet[16] == 0) or classify(packet, indices).tolist() != ["M", "M"]:
        raise ValueError("Invalid full settled M source")
    ids = [case["id"] + f":placed:carrier_{i}" for i in (1, 2)]
    if set(ids) & seen:
        raise ValueError("Placement IDs collide with predecessor")
    prior_ids = sorted(seen)
    seen.update(ids)
    record = dict(previous_case=name, file=name + "_held.npz", key="continuing_packet",
        source_ids=source_ids, excluded_predecessor_ids=prior_ids,
        excluded_predecessor_assay_ids=future_ids, placement_ids=ids, excluded_ids=sorted(seen),
        source_after_holds=True, artificial_placements=True, new_initial_holds=0,
        ordinary_not_age_matched=case["background"] == "ordinary")
    return packet, ids, seen, record


def branch_worker(folder, config, case, inputs):
    validate_config(config)
    refs = arrays(inputs / "references.npz")
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    packet, ids, seen, source = load_source(inputs, case, indices)
    start, initial_seen = packet.copy(), len(seen)
    fresh = np.repeat(refs["prepared"][:, :1], 4, axis=1)
    if classify(fresh, indices).tolist() != ["E"] * 4:
        raise ValueError("Fresh targets must start opposite M")
    plan = design(case)
    write_json(folder / "source.json", source)
    write_json(folder / "design.json", plan)
    rounds = []
    for j, n in enumerate((4, 5)):
        stage = folder / f"round_{n:02}"
        stage.mkdir()
        packet, ids, row = round_worker(stage, config, case, packet, ids, seen,
            fresh[:, 2*j:2*j+2], refs["later"], indices, n, plan["rounds"][j])
        seen.update(ids)
        rounds.append(row)
        write_json(folder / "progress.json", rounds)
        print(f"HANDOVER_ROUND {n}: {''.join(classify(packet, indices))}; prompt={row['round_success']}; settled={row['settled_round_success']}", flush=True)
    prompt = all(r["round_success"] for r in rounds)
    settled = all(r["settled_round_success"] for r in rounds)
    np.savez_compressed(folder / "endpoints.npz", source_packet=start,
        fresh_targets=fresh, final_packet=packet)
    result = dict(case=case, execution_pass=True, ion_indices=indices, source=source, design=plan,
        rounds=rounds, final_ids=ids, distinct_fresh_targets=len(seen)-initial_seen,
        lost_carriers=sum(len(r["lost_ids"]) for r in rounds), M_renewed=prompt,
        settled_M_renewed=settled, delayed_only_renewal=settled and not prompt,
        first_failed_stage=next((f"round_{r['round']}" for r in rounds if not r["round_success"]), None))
    write_json(folder / "result.json", result)
    return 0


def freeze_inputs(run, config):
    from analyze_commitment_components import FLAGS
    from analyze_commitment_robustness import analyze
    previous = (ROOT / config["input_run"]).resolve()
    if previous.parent != ROOT / "runs":
        raise ValueError("Source must be a local exploration run")
    summary, report = verify_source_run(previous, config, analyze)
    if report["array_check_count"] != 14567 or len(report["branches"]) != 36 or not all(report[k] for k in FLAGS) or not report["ready_for_stage3_design"]:
        raise RuntimeError("Robustness source gate failed")
    write_json(run / "predecessor_audit.json", report)
    paths = {n: previous / "inputs" / n for n in ("references.npz", "reference.json")}
    paths["robustness_summary.json"] = previous / "summary.json"
    names = {source_name(c) for c in config["cases"]} | {benchmark_name(c) for c in config["cases"]}
    names.discard(None)
    for name in sorted(names):
        paths[name + ".json"] = previous / name / "result.json"
        paths[name + "_held.npz"] = previous / name / "retention/endpoints.npz"
        for n in (4, 5):
            paths[name + f"_round_{n:02}.npz"] = previous / name / f"round_{n:02}/endpoints.npz"
    if len(paths) != 35:
        raise RuntimeError("Incomplete source/benchmark manifest")
    inputs = run / "inputs"
    inputs.mkdir()
    manifest = {}
    for name, path in paths.items():
        h = file_hash(path)
        (inputs / name).write_bytes(path.read_bytes())
        if file_hash(path) != h or file_hash(inputs / name) != h:
            raise RuntimeError("Source changed while copying")
        manifest[name] = dict(source=str(path), sha256=h)
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    for case in config["cases"]:
        packet, *_ = load_source(inputs, case, indices)
        benchmark = benchmark_name(case)
        if benchmark and not np.array_equal(packet, arrays(inputs / (benchmark + "_held.npz"))["continuing_packet"]):
            raise RuntimeError("Historical control starts from a different held pair")
    write_json(inputs / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/handover_rescue_v1.json")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        spec = json.loads(args.worker.read_text())
        return branch_worker(args.worker.parent, spec["config"], spec["case"], Path(spec["inputs"]))
    config = json.loads(args.config.read_text())
    validate_config(config)
    previous = json.loads((ROOT / config["input_run"] / "summary.json").read_text())
    helpers = {Path(n).name for n in previous["hashes_sha256"] if n.startswith("scripts/")}
    helpers.update(("handover_rescue_relay.py", "analyze_handover_rescue.py", "test_handover_rescue.py",
        "run_handover_rescue_detached.py", "test_detached_handover.py"))
    return run_bounded(args.config.resolve(), Path(__file__).resolve(), ROOT / "HANDOVER_RESCUE_PROTOCOL.md",
        sorted(helpers), freeze_inputs, "handover-rescue",
        "Fixed M-handover duration and miRNA coupling; ordinary controls; no adaptive benefit or autonomy")


if __name__ == "__main__":
    raise SystemExit(main())
