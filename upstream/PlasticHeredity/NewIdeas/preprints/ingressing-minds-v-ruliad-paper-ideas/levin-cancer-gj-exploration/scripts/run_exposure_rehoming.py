"""Temporary cue contact, cue removal, and relay from intact incumbent cells."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_group_transfer import arrays
from bounded_extension import run_bounded
from memory_metrics import classify, opposite
from run_memory_probe import Experiment, write_json
from run_onward_transfer import file_hash
from run_pilot import ROOT, REVISION
from run_rehoming import fresh_recipient, load_source, verify_source_run
from run_renewal import round_worker


def validate_config(config):
    if not 1 <= config["workers"] <= 2 or not 0 < config["worker_timeout_seconds"] <= 900 or not 0 < config["total_budget_seconds"] <= 3600:
        raise ValueError("Exceeds execution bounds")
    fixed = dict(revision=REVISION, packet_size=2, continuing_rounds=[2, 3], inherited_wait=2000,
        cue_donors=5, cue_horizon=1000, cue_holds=[10000, 10000], write_kd=2e-15,
        contact_horizon=1000, retention_horizons=[10000, 10000], recovery_horizon=5000,
        perturbation_fraction=.2, late_label_fraction=.95, minimum_challenge_distance=.1,
        recovery_absolute_tolerance=.02, recovery_distance_ratio=.2)
    if any(config[k] != v for k, v in fixed.items()):
        raise ValueError("Changed fixed experimental parameters")
    expected = {}
    for old in ("E", "M"):
        state = opposite(old)
        stem = old.lower() + "_to_" + state.lower()
        for condition in ("pulse", "blocked", "same", "alone"):
            expected[stem + "_" + condition] = (old, state, condition, "learned", False)
        expected[stem + "_pulse_fine"] = (old, state, "pulse", "learned", True)
    if len(config["cases"]) != 10 or {c["id"] for c in config["cases"]} != set(expected):
        raise ValueError("Require the fixed ten-case grid")
    for c in config["cases"]:
        if (c["old_state"], c["state"], c["condition"], c["history"], c.get("fine", False)) != expected[c["id"]]:
            raise ValueError("Wrong cue condition or blocked onward relay")


def cue_group(carrier, prepared, case, count):
    if case["condition"] not in ("pulse", "blocked", "same", "alone") or count != 5:
        raise ValueError("Unknown cue condition or count")
    if carrier.shape != (17, 1) or prepared.shape != (17, 2) or not all(np.isfinite(a).all() and (a >= 0).all() for a in (carrier, prepared)):
        raise ValueError("Invalid carrier or reference")
    if case["condition"] == "alone":
        return carrier.copy(), False
    label = case["old_state"] if case["condition"] == "same" else case["state"]
    cue = prepared[:, {"E": 0, "M": 1}[label], None]
    return np.concatenate([carrier, np.repeat(cue, count, axis=1)], axis=1), case["condition"] != "blocked"


def cue_names(case, count):
    return [] if case["condition"] == "alone" else [
        f"{case['id']}:cue:carrier_{i}:donor_{j}" for i in (1, 2) for j in range(1, count + 1)]


def exposure_worker(folder, config, case, source, ids, prepared, indices):
    folder.mkdir()
    exp = Experiment(folder, config, fine=case.get("fine", False))
    saved, cells, setups, rows = {"source_packet": source.copy()}, [], [], []

    def build(state, active=False):
        setup = exp.build(state.shape[1], state, active)
        if exp.indices != indices:
            raise RuntimeError("Changed ion indices")
        setup["edges_list"] = [[int(e["from"]), int(e["to"])] for e in exp.sim.GJ_connects]
        setups.append(setup)

    for i in (1, 2):
        initial, active = cue_group(source[:, i - 1:i], prepared, case, config["cue_donors"])
        saved[f"carrier_{i}_initial"] = initial.copy()
        build(initial, active)
        contact, record = exp.phase(f"carrier_{i}_cue", config["cue_horizon"])
        saved[f"carrier_{i}_contact"] = contact.copy()
        # ONLY the original index-zero incumbent survives cue removal.
        build(contact[:, :1].copy())
        held, hold_1 = exp.phase(f"carrier_{i}_hold_1", config["cue_holds"][0])
        checkpoint, hold_2 = exp.phase(f"carrier_{i}_hold_2", config["cue_holds"][1])
        saved[f"carrier_{i}_held_first"] = held.copy()
        cells.append(checkpoint)
        switched = record["recipient_label"] == case["state"] and all(
            h["recipient_label"] == case["state"] and h["late_label_fractions"][case["state"]] >= config["late_label_fraction"]
            for h in (hold_1, hold_2))
        rows.append({"id": ids[i - 1], "contact_label": record["recipient_label"],
            "cue_end_labels": record["all_labels"][1:], "holds": [hold_1, hold_2], "retained_switch": bool(switched),
            "ion_hold_drift": float(np.max(np.abs(checkpoint[:4] - held[:4])))})
    packet = np.concatenate(cells, axis=1)
    saved["continuing_packet"] = packet
    np.savez_compressed(folder / "endpoints.npz", **saved)
    result = {"incoming_ids": ids, "outgoing_ids": ids, "cue_ids": cue_names(case, config["cue_donors"]),
        "carriers": rows, "retained_switch": all(c["retained_switch"] for c in rows),
        "setups": setups, "audits": exp.audits, "new_reference_edits": 0}
    write_json(folder / "result.json", result)
    return packet, result


def branch_worker(folder, config, case, inputs):
    validate_config(config)
    refs = arrays(inputs / "references.npz")
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    # Reuse only the established intact-sham checkpoint loader, never overwrite.
    original, ids, seen, spec = load_source(inputs, dict(case, condition="sham"), indices)
    source_record = dict(spec, incoming_ids=ids, outgoing_ids=ids, source_labels="".join(classify(original, indices)))
    write_json(folder / "source.json", source_record)
    packet, exposure = exposure_worker(folder / "exposure", config, case, original, ids, refs["prepared"], indices)
    cue_ids = exposure["cue_ids"]
    if len(set(cue_ids)) != len(cue_ids) or set(cue_ids) & seen:
        raise RuntimeError("Cue and lineage identity overlap")
    seen.update(cue_ids)
    initial_seen = len(seen)
    start = packet.copy()
    fresh = fresh_recipient(refs["prepared"], case, indices)
    rounds = []
    for number in config["continuing_rounds"]:
        stage = folder / f"round_{number:02}"
        stage.mkdir()
        packet, ids, result = round_worker(stage, config, case, packet, ids, seen, fresh, refs["later"], indices, number)
        seen.update(ids)
        rounds.append(result)
        write_json(folder / "progress.json", rounds)
        print(f"EXPOSURE_ROUND {number}: {''.join(classify(packet, indices))}; new-state transfer={result['round_success']}", flush=True)
    transmitted = all(r["round_success"] for r in rounds)
    np.savez_compressed(folder / "endpoints.npz", source_packet=original, continuing_start=start, fresh_target=fresh, final_packet=packet)
    offset = config["inherited_wait"] + config["cue_horizon"] + sum(config["cue_holds"])
    write_json(folder / "result.json", {"case": case, "execution_pass": True, "ion_indices": indices,
        "source": source_record, "exposure": exposure, "rounds": rounds, "final_ids": ids,
        "distinct_fresh_targets": len(seen) - initial_seen, "cue_instances": len(cue_ids),
        "retained_switch": exposure["retained_switch"], "new_state_transmitted": transmitted,
        "exposure_rehomed": exposure["retained_switch"] and transmitted,
        "nominal_schedule": [{"round": r["round"], "start": r["nominal_round_start"] + offset,
                              "end": r["nominal_round_end"] + offset} for r in rounds]})
    return 0


def freeze_inputs(run, config):
    from analyze_rehoming import analyze
    previous = (ROOT / config["input_run"]).resolve()
    if not previous.is_relative_to(ROOT / "runs"):
        raise ValueError("Source must be an exploration run")
    summary, audit = verify_source_run(previous, config, analyze)
    if config["inherited_wait"] != 2 * summary["config"]["intervention_horizon"] or config["continuing_rounds"] != summary["config"]["continuing_rounds"]:
        raise RuntimeError("Changed historical timing")
    old_audit = json.loads((previous / "predecessor_audit.json").read_text())["erasure"]
    write_json(run / "predecessor_audit.json", {"rehoming": audit, "old_state_lineages": old_audit})
    paths = {"previous_summary.json": previous / "summary.json"}
    for name in ("references.npz", "reference.json", "e_prefix.json", "m_prefix.json"):
        paths[name] = previous / "inputs" / name
    for old in ("e", "m"):
        key = old + "_sham"
        record = json.loads((previous / "inputs" / ("historical_" + key + ".json")).read_text())
        row = next(b for b in old_audit["branches"] if b["case"]["id"] == key)
        packet = arrays(previous / "inputs" / (key + ".npz"))["after_2"]
        historical = arrays(previous / "inputs" / ("historical_" + key + ".npz"))["continuing_start"]
        if not record["all_rounds_transmitted"] or not row["all_rounds_transmitted"] or not np.array_equal(packet, historical):
            raise RuntimeError("Source was not an intact transmitting old-state carrier pair")
        for prefix in ("", "historical_"):
            for ext in ("npz", "json"):
                name = prefix + key + "." + ext
                paths[name] = previous / "inputs" / name
    inputs = run / "inputs"
    inputs.mkdir()
    manifest = {}
    for name, source in paths.items():
        digest = file_hash(source)
        (inputs / name).write_bytes(source.read_bytes())
        if file_hash(source) != digest or file_hash(inputs / name) != digest:
            raise RuntimeError("Input changed during copy")
        manifest[name] = {"source": str(source), "sha256": digest}
    write_json(inputs / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/exposure_rehoming_v1.json")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        spec = json.loads(args.worker.read_text())
        return branch_worker(args.worker.parent, spec["config"], spec["case"], Path(spec["inputs"]))
    validate_config(json.loads(args.config.read_text()))
    helpers = ["bounded_extension.py", "run_rehoming.py", "run_renewal.py", "run_group_transfer.py", "run_onward_transfer.py",
        "run_memory_probe.py", "memory_metrics.py", "run_pilot.py", "analyze_renewal.py", "analyze_group_transfer.py",
        "analyze_erasure_rescue.py", "analyze_rehoming.py", "analyze_exposure_rehoming.py", "test_exposure_rehoming.py"]
    return run_bounded(args.config.resolve(), Path(__file__).resolve(), ROOT / "EXPOSURE_REHOMING_PROTOCOL.md",
        helpers, freeze_inputs, "exposure-rehoming", "Temporary contact rehoming without direct incumbent regulator edits")


if __name__ == "__main__":
    raise SystemExit(main())
