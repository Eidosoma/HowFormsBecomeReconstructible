"""Fixed pulse-spacing experiment with continuously evolving, unreplaced cues."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_group_transfer import arrays
from bounded_extension import run_bounded
from memory_metrics import classify, opposite
from run_cue_duration import writing_outcomes
from run_exposure_rehoming import cue_group, cue_names
from run_lineage_return import load_descendants
from run_memory_probe import Experiment, write_json
from run_onward_transfer import file_hash
from run_pilot import ROOT, REVISION
from run_rehoming import fresh_recipient, verify_source_run
from run_renewal import round_worker


def validate_config(config):
    if not 1 <= config["workers"] <= 2 or not 0 < config["worker_timeout_seconds"] <= 900 or not 0 < config["total_budget_seconds"] <= 3600:
        raise ValueError("Exceeds fixed execution bounds")
    fixed = dict(revision=REVISION, packet_size=2, source_round=3, source_nominal_time=89000,
        continuing_rounds=[4, 5], cue_donors=5, pulse_count=10, pulse_horizon=10, gaps=[0, 10, 1000],
        cue_holds=[10000, 10000], write_kd=2e-15, contact_horizon=1000, retention_horizons=[10000, 10000],
        recovery_horizon=5000, perturbation_fraction=.2, late_label_fraction=.95,
        minimum_challenge_distance=.1, recovery_absolute_tolerance=.02, recovery_distance_ratio=.2)
    if any(config[k] != v for k, v in fixed.items()) or "cue_horizon" in config:
        raise ValueError("Changed fixed pulse-spacing parameters")
    expected = {}
    for origin in ("E", "M"):
        old = opposite(origin)
        stem = origin.lower() + "_to_" + old.lower() + "_to_" + origin.lower()
        for gap in (0, 10, 1000):
            variants = [("train", "pulse", False), ("train", "pulse", True)]
            if gap:
                variants += [("train", c, False) for c in ("blocked", "same", "alone")]
                variants += [(m, "pulse", False) for m in ("continuous", "single")]
            for mode, condition, fine in variants:
                name = f"{stem}_{mode}_g{gap:04}_{condition}" + ("_fine" if fine else "")
                expected[name] = (origin, old, origin, origin.lower() + "_to_" + old.lower() + "_pulse", condition, "learned", mode, gap, fine)
    if len(config["cases"]) != 32 or {c["id"] for c in config["cases"]} != set(expected):
        raise ValueError("Require the fixed thirty-two-case grid")
    for c in config["cases"]:
        if tuple(c[k] for k in ("origin_state", "old_state", "state", "source_case", "condition", "history", "mode", "gap", "fine")) != expected[c["id"]]:
            raise ValueError("Changed case schedule, history, polarity or transport")


def timeline(config, case):
    count, pulse, gap = config["pulse_count"], config["pulse_horizon"], case["gap"]
    window = count * pulse + (count - 1) * gap
    pieces = []
    if case["mode"] == "train":
        for i in range(1, count + 1):
            pieces.append((f"pulse_{i:02}", "contact", pulse))
            if i < count and gap:
                pieces.append((f"gap_{i:02}", "gap", gap))
    elif case["mode"] in ("continuous", "single"):
        contact = count * pulse if case["mode"] == "continuous" else pulse
        if window > contact:
            pieces.append(("wait", "wait", window - contact))
        pieces.append((case["mode"], "contact", contact))
    else:
        raise ValueError("Unknown schedule")
    rows, clock = [], 0
    for name, kind, horizon in pieces:
        rows.append(dict(name=name, kind=kind, horizon=horizon, start=clock, end=clock + horizon))
        clock += horizon
    if clock != window:
        raise RuntimeError("Incorrect cue-window clock")
    return rows


def exposure_worker(folder, config, case, source, ids, prepared, indices):
    folder.mkdir()
    exp = Experiment(folder, config, fine=case["fine"])
    plan = timeline(config, case)
    saved, setups, rows, packets = {"source_packet": source.copy()}, [], [], []

    def build(state, active, name):
        setup = exp.build(state.shape[1], state, active)
        if exp.indices != indices:
            raise RuntimeError("Changed ion indices")
        setup.update(phase=name, edges_list=[[int(e["from"]), int(e["to"])] for e in exp.sim.GJ_connects],
                     all_gj_transport_zero=bool(not np.any(exp.sim.GJ_diffusion)))
        setups.append(setup)

    for i in (1, 2):
        group, enabled = cue_group(source[:, i - 1:i], prepared, case, config["cue_donors"])
        saved[f"carrier_{i}_initial"] = group.copy()
        episodes = []
        for step in plan:
            name = f"carrier_{i}_{step['name']}"
            build(group, enabled and step["kind"] == "contact", name)
            group, audit = exp.phase(name, step["horizon"])
            episodes.append(dict(step, recipient_label=audit["recipient_label"], cue_labels=audit["all_labels"][1:]))
            # ALL incumbent and cue variables survive every episode, including gaps.
        saved[f"carrier_{i}_contact"] = group.copy()
        build(group[:, :1].copy(), False, f"carrier_{i}_hold_1")
        first, h1 = exp.phase(f"carrier_{i}_hold_1", config["cue_holds"][0])
        checkpoint, h2 = exp.phase(f"carrier_{i}_hold_2", config["cue_holds"][1])
        saved[f"carrier_{i}_held_first"] = first
        packets.append(checkpoint)
        retained = episodes[-1]["recipient_label"] == case["state"] and all(
            h["recipient_label"] == case["state"] and h["late_label_fractions"][case["state"]] >= config["late_label_fraction"] for h in (h1, h2))
        rows.append(dict(id=ids[i - 1], contact_label=episodes[-1]["recipient_label"], cue_end_labels=episodes[-1]["cue_labels"],
            episodes=episodes, holds=[h1, h2], retained_switch=bool(retained),
            ion_hold_drift=float(np.max(np.abs(checkpoint[:4] - first[:4])))))
    packet = np.concatenate(packets, axis=1)
    saved["continuing_packet"] = packet
    np.savez_compressed(folder / "endpoints.npz", **saved)
    result = dict(incoming_ids=ids, outgoing_ids=ids, cue_ids=cue_names(case, config["cue_donors"]),
        carriers=rows, retained_switch=all(c["retained_switch"] for c in rows), setups=setups,
        audits=exp.audits, timeline=plan, cue_window=plan[-1]["end"], new_reference_edits=0, cue_refresh_count=0)
    write_json(folder / "result.json", result)
    return packet, result


def branch_worker(folder, config, case, inputs):
    validate_config(config)
    refs = arrays(inputs / "references.npz")
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    original, ids, seen, source_record = load_descendants(inputs, config, case, indices)
    write_json(folder / "source.json", source_record)
    packet, exposure = exposure_worker(folder / "exposure", config, case, original, ids, refs["prepared"], indices)
    cue_ids = exposure["cue_ids"]
    if len(set(cue_ids)) != len(cue_ids) or set(cue_ids) & seen:
        raise RuntimeError("Cue and historical IDs overlap")
    seen.update(cue_ids)
    initial_seen, start = len(seen), packet.copy()
    fresh, rounds = fresh_recipient(refs["prepared"], case, indices), []
    for n in config["continuing_rounds"]:
        stage = folder / f"round_{n:02}"
        stage.mkdir()
        packet, ids, row = round_worker(stage, config, case, packet, ids, seen, fresh, refs["later"], indices, n)
        seen.update(ids)
        rounds.append(row)
        write_json(folder / "progress.json", rounds)
        print(f"SPACING_ROUND {n}: {''.join(classify(packet, indices))}; target transfer={row['round_success']}", flush=True)
    outcomes = writing_outcomes(exposure, rounds, case, config)
    np.savez_compressed(folder / "endpoints.npz", source_packet=original, continuing_start=start, fresh_target=fresh, final_packet=packet)
    duration = 2 * config["contact_horizon"] + sum(config["retention_horizons"])
    begin = config["source_nominal_time"] + exposure["cue_window"] + sum(config["cue_holds"])
    write_json(folder / "result.json", dict(case=case, execution_pass=True, ion_indices=indices, source=source_record,
        exposure=exposure, rounds=rounds, final_ids=ids, distinct_fresh_targets=len(seen) - initial_seen,
        cue_instances=len(cue_ids), retained_switch=exposure["retained_switch"], **outcomes,
        nominal_schedule=[dict(round=n, start=begin + j * duration, end=begin + (j + 1) * duration)
                          for j, n in enumerate(config["continuing_rounds"])]))
    return 0


def freeze_inputs(run, config):
    from analyze_cue_duration import analyze
    previous = (ROOT / config["input_run"]).resolve()
    if not previous.is_relative_to(ROOT / "runs"):
        raise ValueError("Source must be an exploration run")
    summary, audit = verify_source_run(previous, config, analyze)
    if any(summary["config"][k] != config[k] for k in ("source_round", "source_nominal_time", "continuing_rounds", "cue_donors", "cue_holds")):
        raise RuntimeError("Changed source bank or retention protocol")
    for name in ("run_exposure_rehoming.py", "run_lineage_return.py", "run_cue_duration.py", "analyze_lineage_return.py", "analyze_cue_duration.py"):
        if file_hash(ROOT / "scripts" / name) != summary["hashes_sha256"]["scripts/" + name]:
            raise RuntimeError("Prior execution/audit helper changed")
    if audit["array_check_count"] != 3976 or len(audit["new_branches"]) != 20:
        raise RuntimeError("Wrong predecessor panel")
    write_json(run / "predecessor_audit.json", audit)
    paths = {"previous_summary.json": previous / "summary.json"}
    paths.update({n: previous / "inputs" / n for n in summary["inputs"] if n != "previous_summary.json"})
    for b in audit["new_branches"]:
        c = b["case"]
        if c["condition"] == "pulse" and c["cue_duration"] == 100:
            for section in ("branch", "exposure"):
                paths[f"benchmark_{c['id']}_{section}.npz"] = previous / c["id"] / ("exposure" if section == "exposure" else "") / "endpoints.npz"
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
    for c in config["cases"]:
        load_descendants(inputs, config, c, indices)
    write_json(inputs / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/pulse_spacing_v1.json")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        spec = json.loads(args.worker.read_text())
        return branch_worker(args.worker.parent, spec["config"], spec["case"], Path(spec["inputs"]))
    validate_config(json.loads(args.config.read_text()))
    helpers = ["bounded_extension.py", "run_memory_probe.py", "run_pilot.py", "run_onward_transfer.py", "run_group_transfer.py",
        "run_renewal.py", "run_rehoming.py", "run_exposure_rehoming.py", "run_lineage_return.py", "run_cue_duration.py",
        "memory_metrics.py", "analyze_group_transfer.py", "analyze_renewal.py", "analyze_erasure_rescue.py", "analyze_rehoming.py",
        "analyze_exposure_rehoming.py", "analyze_lineage_return.py", "analyze_cue_duration.py", "analyze_pulse_spacing.py",
        "test_pulse_spacing.py", "test_lineage_return.py", "test_exposure_rehoming.py"]
    return run_bounded(args.config.resolve(), Path(__file__).resolve(), ROOT / "PULSE_SPACING_PROTOCOL.md", helpers,
        freeze_inputs, "pulse-spacing", "Fixed pulse-spacing panel with retained evolving cues and matched elapsed-time comparisons")


if __name__ == "__main__":
    raise SystemExit(main())
