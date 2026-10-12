"""Fixed whole-cell receiver/cue history crossover, followed by fresh relays."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_group_transfer import arrays
from bounded_extension import run_bounded
from history_delivery import record_delivery
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
        packet_size=2, source_round=3, source_nominal_time=89000, continuing_rounds=[4, 5],
        cue_donors=5, history_gap=10, history_pulses=4, history_phase="gap_04", history_age=80,
        probe_horizon=10, delivery_window=9, cue_holds=[10000, 10000], write_kd=2e-15,
        contact_horizon=1000, retention_horizons=[10000, 10000], recovery_horizon=5000,
        perturbation_fraction=.2, late_label_fraction=.95, minimum_challenge_distance=.1,
        recovery_absolute_tolerance=.02, recovery_distance_ratio=.2)
    if any(config[k] != v for k, v in fixed.items()) or "cue_horizon" in config:
        raise ValueError("Changed fixed history crossover parameters")
    expected = {}
    for origin in ("E", "M"):
        old = opposite(origin)
        stem = origin.lower() + "_to_" + old.lower() + "_to_" + origin.lower()
        for rh in (1, 0):
            for ch in (1, 0):
                for condition, fine in (("pulse", False), ("blocked", False), ("pulse", True)):
                    name = f"{stem}_r{rh}c{ch}_{condition}" + ("_fine" if fine else "")
                    expected[name] = (origin, old, origin, origin.lower() + "_to_" + old.lower() + "_pulse",
                        rh, ch, condition, "learned", fine)
    if len(config["cases"]) != 24 or {c["id"] for c in config["cases"]} != set(expected):
        raise ValueError("Require the fixed twenty-four-case grid")
    for c in config["cases"]:
        if tuple(c[k] for k in ("origin_state", "old_state", "state", "source_case", "receiver_history", "cue_history", "condition", "history", "fine")) != expected[c["id"]]:
            raise ValueError("Changed histories, polarity, probe or onward transport")


def historical_case(origin, experienced):
    stem = origin.lower() + "_to_" + opposite(origin).lower() + "_to_" + origin.lower()
    return stem + "_train_g0010_" + ("pulse" if experienced else "blocked")


def history_file(origin, experienced, carrier=None):
    stem = f"history_{origin.lower()}_{experienced}"
    return stem + (".json" if carrier is None else f"_carrier_{carrier}_gap_04.npz")


def load_histories(inputs, config, case, indices):
    original, original_ids, seen, lineage = load_descendants(inputs, config, case, indices)
    banks, receiver_ids, cue_ids = {}, {}, {}
    for h in (1, 0):
        name = historical_case(case["origin_state"], h)
        meta = json.loads((inputs / history_file(case["origin_state"], h)).read_text())
        if meta["incoming_ids"] != original_ids or meta["outgoing_ids"] != original_ids or meta["cue_refresh_count"] != 0 or meta["new_reference_edits"] != 0:
            raise ValueError("History has changed source IDs or refreshed cells")
        step = dict(name="gap_04", kind="gap", horizon=10, start=70, end=80)
        if meta["timeline"][7] != step or len(meta["cue_ids"]) != 10:
            raise ValueError("Not the fixed age-matched history checkpoint")
        receiver_ids[h] = [name + "::" + v for v in original_ids]
        cue_ids[h] = meta["cue_ids"]
        expected_cues = [f"{name}:cue:carrier_{i}:donor_{j}" for i in (1, 2) for j in range(1, 6)]
        if cue_ids[h] != expected_cues:
            raise ValueError("Wrong cue provenance")
        seen.update(receiver_ids[h] + cue_ids[h])
        banks[h] = []
        for i in (1, 2):
            a = arrays(inputs / history_file(case["origin_state"], h, i))["final"].copy()
            if a.shape != (17, 6) or not np.isfinite(a).all() or (a < 0).any() or not np.all(a[indices["snail"]] == 72):
                raise ValueError("Invalid full-cell historical checkpoint")
            banks[h].append(a)
    if len(seen) != 42:
        raise ValueError("Incomplete 18-lineage plus 24-history-instance exclusion ledger")
    rh, ch = case["receiver_history"], case["cue_history"]
    groups, provenance = [], []
    for i in (1, 2):
        group = np.concatenate((banks[rh][i - 1][:, :1], banks[ch][i - 1][:, 1:]), axis=1)
        groups.append(group)
        provenance.append(dict(carrier=i,
            receiver=dict(file=history_file(case["origin_state"], rh, i), key="final", column=0,
                historical_case=historical_case(case["origin_state"], rh), original_id=original_ids[i - 1], fork_id=receiver_ids[rh][i - 1]),
            cues=dict(file=history_file(case["origin_state"], ch, i), key="final", columns=list(range(1, 6)),
                historical_case=historical_case(case["origin_state"], ch), ids=cue_ids[ch][(i - 1) * 5:i * 5])))
    history = dict(historical_reuse=True, source_settings="baseline", source_phase="gap_04", history_age=80,
        nominal_probe_start=89080, receiver_history=rh, cue_history=ch,
        groups=provenance, excluded_ids=sorted(seen))
    return original, groups, receiver_ids[rh], cue_ids[ch], seen, dict(lineage=lineage, history=history)


def exposure_worker(folder, config, case, groups, ids, cue_ids, indices):
    folder.mkdir()
    exp = Experiment(folder, config, fine=case["fine"])
    saved, setups, rows, packets, deliveries = {}, [], [], [], []

    def build(state, active, name):
        setup = exp.build(state.shape[1], state, active)
        if exp.indices != indices:
            raise RuntimeError("Changed ion indices")
        setup.update(phase=name, edges_list=[[int(e["from"]), int(e["to"])] for e in exp.sim.GJ_connects],
            all_gj_transport_zero=bool(not np.any(exp.sim.GJ_diffusion)))
        setups.append(setup)

    for i, group in enumerate(groups, 1):
        tag = f"carrier_{i}"
        saved[tag + "_initial"] = group.copy()
        build(group, case["condition"] == "pulse", tag + "_probe")
        contact, contact_audit = exp.phase(tag + "_probe", config["probe_horizon"])
        saved[tag + "_contact"] = contact.copy()
        delivery = record_delivery(exp, arrays(folder / (tag + "_probe.npz")),
            folder / (tag + "_delivery.npz"), config["delivery_window"])
        if not np.array_equal(exp.sim.cc_cells, contact):
            raise RuntimeError("Delivery diagnostic altered continuation")
        deliveries.append(delivery)
        build(contact[:, :1].copy(), False, tag + "_hold_1")
        first, h1 = exp.phase(tag + "_hold_1", config["cue_holds"][0])
        final, h2 = exp.phase(tag + "_hold_2", config["cue_holds"][1])
        saved[tag + "_held_first"] = first
        packets.append(final)
        retained = contact_audit["recipient_label"] == case["state"] and all(
            h["recipient_label"] == case["state"] and h["late_label_fractions"][case["state"]] >= config["late_label_fraction"] for h in (h1, h2))
        rows.append(dict(id=ids[i - 1], initial_label=str(classify(group, indices)[0]),
            contact_label=contact_audit["recipient_label"], cue_end_labels=contact_audit["all_labels"][1:],
            holds=[h1, h2], retained_switch=bool(retained), ion_hold_drift=float(np.max(np.abs(final[:4] - first[:4])))))
    packet = np.concatenate(packets, axis=1)
    saved["continuing_packet"] = packet
    np.savez_compressed(folder / "endpoints.npz", **saved)
    result = dict(incoming_ids=ids, outgoing_ids=ids, cue_ids=cue_ids, carriers=rows, deliveries=deliveries,
        retained_switch=all(c["retained_switch"] for c in rows), target_pair_at_start=all(c["initial_label"] == case["state"] for c in rows),
        setups=setups, audits=exp.audits, new_reference_edits=0, cue_refresh_count=0,
        reused_receiver_instances=2, reused_cue_instances=10)
    write_json(folder / "result.json", result)
    return packet, result


def branch_worker(folder, config, case, inputs):
    validate_config(config)
    refs = arrays(inputs / "references.npz")
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    original, groups, ids, cue_ids, seen, source = load_histories(inputs, config, case, indices)
    write_json(folder / "source.json", source)
    packet, exposure = exposure_worker(folder / "exposure", config, case, groups, ids, cue_ids, indices)
    start, initial_seen = packet.copy(), len(seen)
    fresh = fresh_recipient(refs["prepared"], case, indices)
    rounds = []
    for n in config["continuing_rounds"]:
        stage = folder / f"round_{n:02}"
        stage.mkdir()
        packet, ids, row = round_worker(stage, config, case, packet, ids, seen, fresh, refs["later"], indices, n)
        seen.update(ids)
        rounds.append(row)
        write_json(folder / "progress.json", rounds)
        print(f"CROSSOVER_ROUND {n}: {''.join(classify(packet, indices))}; target transfer={row['round_success']}", flush=True)
    outcomes = writing_outcomes(exposure, rounds, case, config)
    np.savez_compressed(folder / "endpoints.npz", source_packet=original, continuing_start=start, fresh_target=fresh, final_packet=packet)
    begin = config["source_nominal_time"] + config["history_age"] + config["probe_horizon"] + sum(config["cue_holds"])
    duration = 2 * config["contact_horizon"] + sum(config["retention_horizons"])
    write_json(folder / "result.json", dict(case=case, execution_pass=True, ion_indices=indices, source=source,
        exposure=exposure, rounds=rounds, final_ids=ids, distinct_fresh_targets=len(seen) - initial_seen,
        reused_receiver_instances=2, reused_cue_instances=10, retained_switch=exposure["retained_switch"], **outcomes,
        nominal_schedule=[dict(round=n, start=begin + j * duration, end=begin + (j + 1) * duration)
                          for j, n in enumerate(config["continuing_rounds"])]))
    return 0


def freeze_inputs(run, config):
    from analyze_pulse_spacing import analyze
    previous = (ROOT / config["input_run"]).resolve()
    if not previous.is_relative_to(ROOT / "runs"):
        raise ValueError("Source must be an exploration run")
    summary, audit = verify_source_run(previous, config, analyze)
    if audit["array_check_count"] != 16296 or len(audit["branches"]) != 32 or not audit["frozen_hashes_valid"] or not audit["predecessor_audit_hash_valid"]:
        raise RuntimeError("Not the completed spacing panel")
    for name in ("run_pulse_spacing.py", "analyze_pulse_spacing.py", "run_lineage_return.py", "analyze_lineage_return.py", "run_cue_duration.py", "analyze_cue_duration.py"):
        if file_hash(ROOT / "scripts" / name) != summary["hashes_sha256"]["scripts/" + name]:
            raise RuntimeError("Previous helper or auditor changed")
    write_json(run / "predecessor_audit.json", audit)
    paths = {"previous_summary.json": previous / "summary.json"}
    for name in ("references.npz", "reference.json", "e_prefix.json", "m_prefix.json"):
        paths[name] = previous / "inputs" / name
    for origin in ("E", "M"):
        stem = origin.lower() + "_to_" + opposite(origin).lower() + "_pulse"
        for suffix in ("", "_round_03"):
            for ext in ("json", "npz"):
                name = stem + suffix + "." + ext
                paths[name] = previous / "inputs" / name
        for h in (1, 0):
            name = historical_case(origin, h)
            c = next(c for c in summary["config"]["cases"] if c["id"] == name)
            if c["fine"] or c["gap"] != 10 or c["mode"] != "train":
                raise RuntimeError("Wrong historical settings")
            paths[history_file(origin, h)] = previous / name / "exposure/result.json"
            for i in (1, 2):
                paths[history_file(origin, h, i)] = previous / name / f"exposure/carrier_{i}_gap_04.npz"
                if h:
                    paths[f"benchmark_{origin.lower()}_carrier_{i}_pulse_05.npz"] = previous / name / f"exposure/carrier_{i}_pulse_05.npz"
    if len(paths) != 29:
        raise RuntimeError("Incomplete fixed source manifest")
    inputs = run / "inputs"
    inputs.mkdir()
    manifest = {}
    for name, source in paths.items():
        digest = file_hash(source)
        (inputs / name).write_bytes(source.read_bytes())
        if file_hash(source) != digest or file_hash(inputs / name) != digest:
            raise RuntimeError("Historical input changed during copy")
        manifest[name] = dict(source=str(source), sha256=digest)
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    for c in config["cases"]:
        load_histories(inputs, config, c, indices)
    write_json(inputs / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/history_crossover_v1.json")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        spec = json.loads(args.worker.read_text())
        return branch_worker(args.worker.parent, spec["config"], spec["case"], Path(spec["inputs"]))
    validate_config(json.loads(args.config.read_text()))
    helpers = ["bounded_extension.py", "run_memory_probe.py", "run_pilot.py", "run_onward_transfer.py", "run_group_transfer.py",
        "run_renewal.py", "run_rehoming.py", "run_exposure_rehoming.py", "run_lineage_return.py", "run_cue_duration.py",
        "run_pulse_spacing.py", "memory_metrics.py", "analyze_group_transfer.py", "analyze_renewal.py", "analyze_erasure_rescue.py",
        "analyze_rehoming.py", "analyze_exposure_rehoming.py", "analyze_lineage_return.py", "analyze_cue_duration.py",
        "analyze_pulse_spacing.py", "history_delivery.py", "analyze_history_crossover.py", "test_history_crossover.py",
        "test_pulse_spacing.py", "test_lineage_return.py", "test_exposure_rehoming.py"]
    return run_bounded(args.config.resolve(), Path(__file__).resolve(), ROOT / "HISTORY_CROSSOVER_PROTOCOL.md", helpers,
        freeze_inputs, "history-crossover", "Fixed complete-cell history crossover at nominal 89080; one probe then two fresh replacements")


if __name__ == "__main__":
    raise SystemExit(main())
