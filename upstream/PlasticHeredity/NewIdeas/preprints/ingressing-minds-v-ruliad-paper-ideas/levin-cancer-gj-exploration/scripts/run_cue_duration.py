"""Fixed cue-duration panel with prompt and delayed durable rewriting."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_group_transfer import arrays
from bounded_extension import run_bounded
from memory_metrics import classify, opposite
from run_exposure_rehoming import exposure_worker
from run_lineage_return import load_descendants, clock_offset
from run_memory_probe import write_json
from run_onward_transfer import file_hash
from run_pilot import ROOT, REVISION
from run_rehoming import fresh_recipient, verify_source_run
from run_renewal import round_worker


def validate_config(config):
    if not 1 <= config["workers"] <= 2 or not 0 < config["worker_timeout_seconds"] <= 900 or not 0 < config["total_budget_seconds"] <= 3600:
        raise ValueError("Exceeds execution bounds")
    fixed = dict(revision=REVISION, packet_size=2, source_round=3, source_nominal_time=89000,
        continuing_rounds=[4, 5], cue_donors=5, cue_durations=[10, 100], benchmark_cue_duration=1000,
        cue_holds=[10000, 10000], write_kd=2e-15, contact_horizon=1000, retention_horizons=[10000, 10000],
        recovery_horizon=5000, perturbation_fraction=.2, late_label_fraction=.95, minimum_challenge_distance=.1,
        recovery_absolute_tolerance=.02, recovery_distance_ratio=.2)
    if any(config[k] != v for k, v in fixed.items()) or "cue_horizon" in config:
        raise ValueError("Changed fixed duration panel or ambiguous global cue horizon")
    expected = {}
    for origin in ("E", "M"):
        current = opposite(origin)
        stem = origin.lower() + "_to_" + current.lower() + "_to_" + origin.lower()
        source = origin.lower() + "_to_" + current.lower() + "_pulse"
        for duration in (10, 100):
            for condition in ("pulse", "blocked", "same", "alone"):
                expected[f"{stem}_t{duration:04}_{condition}"] = (origin, current, origin, source, condition, "learned", duration, False)
            expected[f"{stem}_t{duration:04}_pulse_fine"] = (origin, current, origin, source, "pulse", "learned", duration, True)
    if len(config["cases"]) != 20 or {c["id"] for c in config["cases"]} != set(expected):
        raise ValueError("Require twenty new cases; historical 1000-unit cases are not rerun")
    for c in config["cases"]:
        if (c["origin_state"], c["old_state"], c["state"], c["source_case"], c["condition"], c["history"], c["cue_duration"], c.get("fine", False)) != expected[c["id"]]:
            raise ValueError("Wrong duration, source, direction or onward transport")


def effective_config(config, case):
    return dict(config, cue_horizon=case["cue_duration"])


def writing_outcomes(exposure, rounds, case, config):
    carriers = exposure["carriers"]
    if len(carriers) != 2 or any(len(c["holds"]) != 2 for c in carriers) or len(rounds) != 2:
        raise ValueError("Writing requires two carriers, two holds each and two relay rounds")
    acquired = all(c["contact_label"] == case["state"] for c in carriers)
    written = all(h["recipient_label"] == case["state"] and h["late_label_fractions"][case["state"]] >= config["late_label_fraction"]
                  for c in carriers for h in c["holds"])
    transmitted = all(r["round_success"] for r in rounds)
    durable = written and transmitted
    return dict(contact_acquired=bool(acquired), postcue_state_written=bool(written), new_state_transmitted=bool(transmitted),
                durable_rewrite=bool(durable), prompt_rewrite=bool(durable and acquired), delayed_rewrite=bool(durable and not acquired))


def branch_worker(folder, config, case, inputs):
    validate_config(config)
    config = effective_config(config, case)
    refs = arrays(inputs / "references.npz")
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    original, ids, seen, source_record = load_descendants(inputs, config, case, indices)
    write_json(folder / "source.json", source_record)
    packet, exposure = exposure_worker(folder / "exposure", config, case, original, ids, refs["prepared"], indices)
    cue_ids = exposure["cue_ids"]
    if len(set(cue_ids)) != len(cue_ids) or set(cue_ids) & seen:
        raise RuntimeError("Cue and historical lineage identities overlap")
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
        print(f"DURATION_ROUND {number}: {''.join(classify(packet, indices))}; restored-state transfer={result['round_success']}", flush=True)
    outcomes = writing_outcomes(exposure, rounds, case, config)
    np.savez_compressed(folder / "endpoints.npz", source_packet=original, continuing_start=start, fresh_target=fresh, final_packet=packet)
    offset = clock_offset(config)
    write_json(folder / "result.json", {"case": case, "execution_pass": True, "ion_indices": indices,
        "source": source_record, "exposure": exposure, "rounds": rounds, "final_ids": ids,
        "distinct_fresh_targets": len(seen) - initial_seen, "cue_instances": len(cue_ids),
        "retained_switch": exposure["retained_switch"], "effective_cue_horizon": config["cue_horizon"], **outcomes,
        "nominal_schedule": [{"round": r["round"], "start": r["nominal_round_start"] + offset,
                              "end": r["nominal_round_end"] + offset} for r in rounds]})
    return 0


def freeze_inputs(run, config):
    from analyze_lineage_return import analyze
    previous = (ROOT / config["input_run"]).resolve()
    if not previous.is_relative_to(ROOT / "runs"):
        raise ValueError("Source must be an exploration run")
    summary, audit = verify_source_run(previous, config, analyze)
    shared = ("source_round", "source_nominal_time", "continuing_rounds", "cue_donors", "cue_holds")
    if any(config[k] != summary["config"][k] for k in shared) or summary["config"]["cue_horizon"] != config["benchmark_cue_duration"]:
        raise RuntimeError("Different source bank, relay timing or benchmark cue protocol")
    for name in ("run_exposure_rehoming.py", "analyze_exposure_rehoming.py", "run_lineage_return.py", "analyze_lineage_return.py"):
        if file_hash(ROOT / "scripts" / name) != summary["hashes_sha256"]["scripts/" + name]:
            raise RuntimeError("Historical source/exposure helper changed")
    if len(audit["branches"]) != 10:
        raise RuntimeError("Incomplete historical benchmark panel")
    write_json(run / "predecessor_audit.json", audit)
    paths = {"previous_summary.json": previous / "summary.json"}
    for name in summary["inputs"]:
        if name != "previous_summary.json":
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
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    for case in config["cases"]:
        load_descendants(inputs, effective_config(config, case), case, indices)
    write_json(inputs / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/cue_duration_v1.json")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        spec = json.loads(args.worker.read_text())
        return branch_worker(args.worker.parent, spec["config"], spec["case"], Path(spec["inputs"]))
    validate_config(json.loads(args.config.read_text()))
    helpers = ["bounded_extension.py", "run_exposure_rehoming.py", "run_rehoming.py", "run_renewal.py",
        "run_group_transfer.py", "run_onward_transfer.py", "run_memory_probe.py", "memory_metrics.py", "run_pilot.py",
        "analyze_renewal.py", "analyze_group_transfer.py", "analyze_erasure_rescue.py", "analyze_rehoming.py",
        "analyze_exposure_rehoming.py", "analyze_lineage_return.py", "run_lineage_return.py", "analyze_cue_duration.py",
        "test_cue_duration.py", "test_lineage_return.py", "test_exposure_rehoming.py"]
    return run_bounded(args.config.resolve(), Path(__file__).resolve(), ROOT / "CUE_DURATION_PROTOCOL.md",
        helpers, freeze_inputs, "cue-duration", "Fixed brief-cue panel against audited historical 1000-unit benchmarks")


if __name__ == "__main__":
    raise SystemExit(main())
