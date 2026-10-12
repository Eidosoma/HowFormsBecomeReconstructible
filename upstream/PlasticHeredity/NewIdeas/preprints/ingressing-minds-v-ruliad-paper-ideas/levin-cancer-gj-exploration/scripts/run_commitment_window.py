"""Fixed prefix stopping points; cue-free commitment and fresh-pair renewal."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_group_transfer import arrays
from bounded_extension import run_bounded
from memory_metrics import classify, opposite
from run_cue_duration import writing_outcomes
from run_lineage_return import load_descendants
from run_memory_probe import Experiment, write_json
from run_onward_transfer import file_hash
from run_pilot import ROOT, REVISION
from run_rehoming import fresh_recipient, verify_source_run
from run_renewal import round_worker


def validate_config(config):
    if not 1 <= config["workers"] <= 2 or not 0 < config["worker_timeout_seconds"] <= 900 or not 0 < config["total_budget_seconds"] <= 3600:
        raise ValueError("Exceeds fixed execution bounds")
    fixed = dict(revision=REVISION, input_run="runs/pulse-spacing-20260906T130210Z-8pyjjxct",
        benchmark_run="runs/history-crossover-20260906T144633Z-gkc7ryjt",
        packet_size=2, source_round=3, source_nominal_time=89000, continuing_rounds=[4, 5],
        cue_donors=5, history_gap=10, pulse_horizon=10, stop_counts=[2, 3, 4, 6, 8],
        cue_holds=[10000, 10000], write_kd=2e-15, contact_horizon=1000,
        retention_horizons=[10000, 10000], recovery_horizon=5000, perturbation_fraction=.2,
        late_label_fraction=.95, minimum_challenge_distance=.1,
        recovery_absolute_tolerance=.02, recovery_distance_ratio=.2)
    if any(config[k] != v for k, v in fixed.items()) or "cue_horizon" in config:
        raise ValueError("Changed fixed stopping-point parameters")
    expected = {}
    for n in (2, 3, 4, 6, 8):
        for origin in ("E", "M"):
            old = opposite(origin)
            stem = origin.lower() + "_to_" + old.lower() + "_to_" + origin.lower()
            for condition, fine in (("pulse", False), ("blocked", False), ("pulse", True)):
                name = f"{stem}_stop_{n:02}_{condition}" + ("_fine" if fine else "")
                expected[name] = (origin, old, origin, origin.lower() + "_to_" + old.lower() + "_pulse",
                    n, condition, "learned", fine)
    if len(config["cases"]) != 30 or {c["id"] for c in config["cases"]} != set(expected):
        raise ValueError("Require the fixed thirty-case grid")
    for c in config["cases"]:
        if tuple(c[k] for k in ("origin_state", "old_state", "state", "source_case", "stop_count", "condition", "history", "fine")) != expected[c["id"]]:
            raise ValueError("Changed stop, source, polarity, numerics or onward transport")


def history_name(case):
    origin = case["origin_state"].lower()
    return origin + "_to_" + opposite(case["origin_state"]).lower() + "_to_" + origin + "_train_g0010_" + case["condition"] + ("_fine" if case["fine"] else "")


def checkpoint_file(case, carrier=None):
    stem = "checkpoint_" + history_name(case)
    return stem + (".json" if carrier is None else f"_carrier_{carrier}_pulse_{case['stop_count']:02}.npz")


def load_checkpoint(inputs, config, case, indices):
    original, old_ids, seen, lineage = load_descendants(inputs, config, case, indices)
    name, n = history_name(case), case["stop_count"]
    meta = json.loads((inputs / checkpoint_file(case)).read_text())
    previous = json.loads((inputs / "spacing_summary.json").read_text())
    historical = next(c for c in previous["config"]["cases"] if c["id"] == name)
    if historical["fine"] != case["fine"] or historical["condition"] != case["condition"] or historical["mode"] != "train" or historical["gap"] != 10:
        raise ValueError("Wrong prefix refinement or history")
    expected = []
    for j in range(1, n + 1):
        start = 20 * (j - 1)
        expected.append(dict(name=f"pulse_{j:02}", kind="contact", horizon=10, start=start, end=start + 10))
        if j < n:
            expected.append(dict(name=f"gap_{j:02}", kind="gap", horizon=10, start=start + 10, end=start + 20))
    if meta["timeline"][:2 * n - 1] != expected:
        raise ValueError("Wrong prefix age or removal phase")
    cue_ids = [f"{name}:cue:carrier_{i}:donor_{j}" for i in (1, 2) for j in range(1, 6)]
    ids = [name + "::" + old_id for old_id in old_ids]
    if meta["incoming_ids"] != old_ids or meta["outgoing_ids"] != old_ids or meta["cue_ids"] != cue_ids or meta["cue_refresh_count"] != 0 or meta["new_reference_edits"] != 0:
        raise ValueError("Historical IDs, cue continuity or edits changed")
    if set(ids + cue_ids) & seen or len(set(ids + cue_ids)) != 12:
        raise ValueError("Historical identity collision")
    seen.update(ids + cue_ids)
    groups, provenance = [], []
    for i in (1, 2):
        filename = checkpoint_file(case, i)
        phase = arrays(inputs / filename)
        state = phase["final"].copy()
        record = meta["audits"][(i - 1) * 21 + 2 * n - 2]
        if state.shape != (17, 6) or not np.isfinite(state).all() or (state < 0).any() or not np.all(state[indices["snail"]] == 72):
            raise ValueError("Invalid complete checkpoint")
        if record["phase"] != f"carrier_{i}_pulse_{n:02}" or record["requested_horizon"] != 10 or not np.array_equal(phase["raw_final"][:8], state[:8]):
            raise ValueError("Wrong contact endpoint or primary-state refresh")
        groups.append(state)
        provenance.append(dict(file=filename, key="final", receiver_column=0, removed_cue_columns=[1, 2, 3, 4, 5],
            original_id=old_ids[i - 1], fork_id=ids[i - 1], cue_ids=cue_ids[(i - 1) * 5:i * 5]))
    if len(seen) != 30:
        raise ValueError("Incomplete source exclusion ledger")
    checkpoint = dict(historical_reuse=True, historical_case=name, source_settings="fine" if case["fine"] else "baseline",
        source_phase=f"pulse_{n:02}", stop_count=n, history_age=20 * n - 10,
        nominal_removal=89000 + 20 * n - 10, groups=provenance, excluded_ids=sorted(seen))
    return original, groups, ids, cue_ids, seen, dict(lineage=lineage, checkpoint=checkpoint)


def exposure_worker(folder, config, case, groups, ids, cue_ids, indices):
    folder.mkdir()
    exp = Experiment(folder, config, fine=case["fine"])
    saved, setups, rows, packets = {}, [], [], []
    for j, group in enumerate(groups):
        tag = f"carrier_{j + 1}"
        saved[tag + "_checkpoint"] = group.copy()
        receiver = group[:, :1].copy()
        setup = exp.build(1, receiver, False)
        if exp.indices != indices:
            raise RuntimeError("Changed ion indices")
        setup.update(phase=tag + "_hold_1", edges_list=[[int(e["from"]), int(e["to"])] for e in exp.sim.GJ_connects],
            all_gj_transport_zero=bool(not np.any(exp.sim.GJ_diffusion)))
        setups.append(setup)
        first, h1 = exp.phase(tag + "_hold_1", config["cue_holds"][0])
        final, h2 = exp.phase(tag + "_hold_2", config["cue_holds"][1])
        saved[tag + "_held_first"] = first
        packets.append(final)
        labels = classify(group, indices)
        retained = labels[0] == case["state"] and all(h["recipient_label"] == case["state"] and
            h["late_label_fractions"][case["state"]] >= config["late_label_fraction"] for h in (h1, h2))
        rows.append(dict(id=ids[j], contact_label=str(labels[0]), cue_end_labels="".join(labels[1:]),
            holds=[h1, h2], retained_switch=bool(retained),
            ion_hold_drift=float(np.max(np.abs(final[:4] - first[:4])))))
    packet = np.concatenate(packets, axis=1)
    saved["continuing_packet"] = packet
    np.savez_compressed(folder / "endpoints.npz", **saved)
    result = dict(incoming_ids=ids, outgoing_ids=ids, removed_cue_ids=cue_ids, carriers=rows,
        retained_switch=all(c["retained_switch"] for c in rows),
        setups=setups, audits=exp.audits, new_reference_edits=0, new_contacts=0,
        new_cue_instances=0, reused_receiver_placements=2, removed_historical_cue_placements=10)
    write_json(folder / "result.json", result)
    return packet, result


def branch_worker(folder, config, case, inputs):
    validate_config(config)
    refs = arrays(inputs / "references.npz")
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    original, groups, ids, cue_ids, seen, source = load_checkpoint(inputs, config, case, indices)
    write_json(folder / "source.json", source)
    packet, exposure = exposure_worker(folder / "exposure", config, case, groups, ids, cue_ids, indices)
    start, initial_seen = packet.copy(), len(seen)
    fresh, rounds = fresh_recipient(refs["prepared"], case, indices), []
    for n in config["continuing_rounds"]:
        stage = folder / f"round_{n:02}"
        stage.mkdir()
        packet, ids, row = round_worker(stage, config, case, packet, ids, seen, fresh, refs["later"], indices, n)
        seen.update(ids)
        rounds.append(row)
        write_json(folder / "progress.json", rounds)
        print(f"COMMITMENT_ROUND {n}: {''.join(classify(packet, indices))}; target transfer={row['round_success']}", flush=True)
    outcomes = writing_outcomes(exposure, rounds, case, config)
    np.savez_compressed(folder / "endpoints.npz", source_packet=original, continuing_start=start, fresh_target=fresh, final_packet=packet)
    begin = config["source_nominal_time"] + source["checkpoint"]["history_age"] + sum(config["cue_holds"])
    duration = 2 * config["contact_horizon"] + sum(config["retention_horizons"])
    write_json(folder / "result.json", dict(case=case, execution_pass=True, ion_indices=indices, source=source,
        exposure=exposure, rounds=rounds, final_ids=ids, distinct_fresh_targets=len(seen) - initial_seen,
        reused_receiver_placements=2, new_cue_instances=0, removed_historical_cue_placements=10,
        retained_switch=exposure["retained_switch"], **outcomes,
        nominal_schedule=[dict(round=n, start=begin + j * duration, end=begin + (j + 1) * duration)
            for j, n in enumerate(config["continuing_rounds"])]))
    return 0


def freeze_inputs(run, config):
    from analyze_history_crossover import analyze as analyze_history
    from analyze_pulse_spacing import analyze as analyze_spacing
    previous, benchmark = [(ROOT / config[k]).resolve() for k in ("input_run", "benchmark_run")]
    if not all(p.is_relative_to(ROOT / "runs") for p in (previous, benchmark)):
        raise ValueError("Sources must be exploration runs")
    reports, summaries = {}, {}
    for name, path, analyzer, count, size in (("spacing", previous, analyze_spacing, 16296, 32),
            ("history", benchmark, analyze_history, 6269, 24)):
        summary, audit = verify_source_run(path, config, analyzer)
        audit["original_inputs_hashes_valid"] = all(file_hash(Path(v["source"])) == v["sha256"] for v in summary["inputs"].values())
        audit["execution_files_hashes_valid"] = all(file_hash(ROOT / n) == h for n, h in summary["hashes_sha256"].items())
        flags = ("all_array_checks_pass", "input_hashes_valid", "original_inputs_hashes_valid",
            "frozen_hashes_valid", "execution_files_hashes_valid", "predecessor_audit_hash_valid")
        if audit["array_check_count"] != count or len(audit["branches"]) != size or not all(audit[k] for k in flags):
            raise RuntimeError("Historical audit or provenance failed")
        reports[name], summaries[name] = audit, summary
    if file_hash(previous / "summary.json") != summaries["history"]["inputs"]["previous_summary.json"]["sha256"]:
        raise RuntimeError("Crossover benchmarks use a different spacing run")
    if not all(c["bitwise_same"] for c in reports["history"]["historical_pulse5_comparisons"].values()):
        raise RuntimeError("Historical fifth-contact continuation is not exact")
    write_json(run / "predecessor_audit.json", reports)
    paths = dict(spacing_summary=previous / "summary.json", history_summary=benchmark / "summary.json")
    paths = {k + ".json": v for k, v in paths.items()}
    for name in ("references.npz", "reference.json", "e_prefix.json", "m_prefix.json"):
        paths[name] = previous / "inputs" / name
    for origin in ("E", "M"):
        stem = origin.lower() + "_to_" + opposite(origin).lower() + "_pulse"
        for suffix in ("", "_round_03"):
            for ext in ("json", "npz"):
                name = stem + suffix + "." + ext
                paths[name] = previous / "inputs" / name
    for case in config["cases"]:
        name = history_name(case)
        paths[checkpoint_file(case)] = previous / name / "exposure/result.json"
        for i in (1, 2):
            paths[checkpoint_file(case, i)] = previous / name / f"exposure/carrier_{i}_pulse_{case['stop_count']:02}.npz"
    if len(paths) != 80:
        raise RuntimeError("Incomplete fixed checkpoint manifest")
    inputs = run / "inputs"
    inputs.mkdir()
    manifest = {}
    for name, source in paths.items():
        digest = file_hash(source)
        (inputs / name).write_bytes(source.read_bytes())
        if file_hash(source) != digest or file_hash(inputs / name) != digest:
            raise RuntimeError("Input changed while copying")
        manifest[name] = dict(source=str(source), sha256=digest)
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    for case in config["cases"]:
        load_checkpoint(inputs, config, case, indices)
    write_json(inputs / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/commitment_window_v1.json")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        spec = json.loads(args.worker.read_text())
        return branch_worker(args.worker.parent, spec["config"], spec["case"], Path(spec["inputs"]))
    validate_config(json.loads(args.config.read_text()))
    helpers = ["bounded_extension.py", "run_memory_probe.py", "run_pilot.py", "run_onward_transfer.py",
        "run_group_transfer.py", "run_renewal.py", "run_rehoming.py", "run_exposure_rehoming.py",
        "run_lineage_return.py", "run_cue_duration.py", "run_pulse_spacing.py", "run_history_crossover.py",
        "history_delivery.py", "memory_metrics.py", "analyze_group_transfer.py", "analyze_renewal.py",
        "analyze_erasure_rescue.py", "analyze_rehoming.py", "analyze_exposure_rehoming.py",
        "analyze_lineage_return.py", "analyze_cue_duration.py", "analyze_pulse_spacing.py",
        "analyze_history_crossover.py", "analyze_commitment_window.py", "test_commitment_window.py",
        "test_history_crossover.py", "test_lineage_return.py", "test_exposure_rehoming.py"]
    return run_bounded(args.config.resolve(), Path(__file__).resolve(), ROOT / "COMMITMENT_WINDOW_PROTOCOL.md",
        helpers, freeze_inputs, "commitment-window", "Fixed prefix stopping points; no new cues; two fresh replacements")


if __name__ == "__main__":
    raise SystemExit(main())
