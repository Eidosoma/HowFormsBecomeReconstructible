"""Return-cue switching from actual round-three contact-rehomed descendants."""

import argparse
import json
from pathlib import Path

import numpy as np

from analyze_group_transfer import arrays
from bounded_extension import run_bounded
from memory_metrics import classify, opposite
from run_exposure_rehoming import exposure_worker
from run_memory_probe import write_json
from run_onward_transfer import file_hash
from run_pilot import ROOT, REVISION
from run_rehoming import fresh_recipient, verify_source_run
from run_renewal import round_worker


def validate_config(config):
    if not 1 <= config["workers"] <= 2 or not 0 < config["worker_timeout_seconds"] <= 900 or not 0 < config["total_budget_seconds"] <= 3600:
        raise ValueError("Exceeds execution bounds")
    fixed = dict(revision=REVISION, packet_size=2, source_round=3, source_nominal_time=89000,
        continuing_rounds=[4, 5], cue_donors=5, cue_horizon=1000, cue_holds=[10000, 10000],
        write_kd=2e-15, contact_horizon=1000, retention_horizons=[10000, 10000], recovery_horizon=5000,
        perturbation_fraction=.2, late_label_fraction=.95, minimum_challenge_distance=.1,
        recovery_absolute_tolerance=.02, recovery_distance_ratio=.2)
    if any(config[k] != v for k, v in fixed.items()):
        raise ValueError("Changed fixed experimental parameters")
    expected = {}
    for origin in ("E", "M"):
        current = opposite(origin)
        stem = origin.lower() + "_to_" + current.lower()
        for condition in ("pulse", "blocked", "same", "alone"):
            expected[stem + "_to_" + origin.lower() + "_" + condition] = (origin, current, origin, stem + "_pulse", condition, "learned", False)
        expected[stem + "_to_" + origin.lower() + "_pulse_fine"] = (origin, current, origin, stem + "_pulse", "pulse", "learned", True)
    if len(config["cases"]) != 10 or {c["id"] for c in config["cases"]} != set(expected):
        raise ValueError("Require the fixed ten-case return grid")
    for c in config["cases"]:
        if (c["origin_state"], c["old_state"], c["state"], c["source_case"], c["condition"], c["history"], c.get("fine", False)) != expected[c["id"]]:
            raise ValueError("Wrong historical lineage, return target or onward transport")


def load_descendants(inputs, config, case, indices):
    stem = case["source_case"]
    metadata = json.loads((inputs / (stem + ".json")).read_text())
    prior = arrays(inputs / (stem + ".npz"))
    final_round = json.loads((inputs / (stem + "_round_03.json")).read_text())
    packet = arrays(inputs / (stem + "_round_03.npz"))["outgoing_packet"].copy()
    prefix = json.loads((inputs / (case["origin_state"].lower() + "_prefix.json")).read_text())
    c = metadata["case"]
    if (c["id"], c["old_state"], c["state"], c["condition"], c.get("fine", False)) != (stem, case["origin_state"], case["old_state"], "pulse", False):
        raise ValueError("Not the specified baseline rehomed lineage")
    if not metadata["exposure_rehomed"] or not metadata["retained_switch"] or not metadata["new_state_transmitted"]:
        raise ValueError("Previous lineage did not complete contact rehoming")
    if not np.array_equal(packet, prior["final_packet"]) or packet.shape != (17, 2) or not np.isfinite(packet).all() or (packet < 0).any() or classify(packet, indices).tolist() != [case["old_state"]] * 2:
        raise ValueError("Invalid actual descendant checkpoint or current polarity")
    if [r["round"] for r in metadata["rounds"]] != [2, 3] or final_round != metadata["rounds"][-1] or not all(r["round_success"] for r in metadata["rounds"]):
        raise ValueError("Invalid prior replacement records")
    ids = final_round["outgoing_ids"].copy()
    if ids != metadata["final_ids"] or final_round["round"] != config["source_round"] or metadata["nominal_schedule"][-1]["end"] != config["source_nominal_time"]:
        raise ValueError("Wrong source generation, IDs or clock")
    previous_ids = prefix["outgoing_ids"]
    if previous_ids != metadata["exposure"]["incoming_ids"] or previous_ids != metadata["exposure"]["outgoing_ids"]:
        raise ValueError("Historical exposure changed carrier identities")
    ledger = prefix["incoming_ids"] + previous_ids + metadata["exposure"]["cue_ids"]
    for row in metadata["rounds"]:
        if row["incoming_ids"] != previous_ids or len(row["outgoing_ids"]) != 2:
            raise ValueError("Discontinuous historical relay identities")
        previous_ids = row["outgoing_ids"]
        ledger += previous_ids
    if len(ledger) != 18 or len(set(ledger)) != 18 or len(ids) != 2 or previous_ids != ids:
        raise ValueError("Incomplete or reused historical cell ledger")
    source_record = {"packet_file": stem + "_round_03.npz", "metadata_file": stem + "_round_03.json",
        "key": "outgoing_packet", "source_case": stem, "source_round": config["source_round"],
        "incoming_ids": ids, "outgoing_ids": ids, "source_labels": case["old_state"] * 2,
        "origin_state": case["origin_state"], "nominal_source_end": config["source_nominal_time"], "excluded_ids": sorted(ledger)}
    return packet, ids, set(ledger), source_record


def clock_offset(config):
    duration = 2 * config["contact_horizon"] + sum(config["retention_horizons"])
    return config["source_nominal_time"] + config["cue_horizon"] + sum(config["cue_holds"]) - config["source_round"] * duration


def branch_worker(folder, config, case, inputs):
    validate_config(config)
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
        print(f"RETURN_ROUND {number}: {''.join(classify(packet, indices))}; restored-state transfer={result['round_success']}", flush=True)
    transmitted = all(r["round_success"] for r in rounds)
    np.savez_compressed(folder / "endpoints.npz", source_packet=original, continuing_start=start, fresh_target=fresh, final_packet=packet)
    offset = clock_offset(config)
    write_json(folder / "result.json", {"case": case, "execution_pass": True, "ion_indices": indices,
        "source": source_record, "exposure": exposure, "rounds": rounds, "final_ids": ids,
        "distinct_fresh_targets": len(seen) - initial_seen, "cue_instances": len(cue_ids),
        "retained_switch": exposure["retained_switch"], "new_state_transmitted": transmitted,
        "renewed_return": exposure["retained_switch"] and transmitted,
        "nominal_schedule": [{"round": r["round"], "start": r["nominal_round_start"] + offset,
                              "end": r["nominal_round_end"] + offset} for r in rounds]})
    return 0


def freeze_inputs(run, config):
    from analyze_exposure_rehoming import analyze
    previous = (ROOT / config["input_run"]).resolve()
    if not previous.is_relative_to(ROOT / "runs"):
        raise ValueError("Source must be an exploration run")
    summary, audit = verify_source_run(previous, config, analyze)
    for key in ("cue_donors", "cue_horizon", "cue_holds"):
        if config[key] != summary["config"][key]:
            raise RuntimeError("Changed cue protocol")
    for name in ("run_exposure_rehoming.py", "analyze_exposure_rehoming.py"):
        if file_hash(ROOT / "scripts" / name) != summary["hashes_sha256"]["scripts/" + name]:
            raise RuntimeError("Previous exposure helper/auditor changed")
    if config["source_round"] != summary["config"]["continuing_rounds"][-1]:
        raise RuntimeError("Not continuing after the previous final round")
    write_json(run / "predecessor_audit.json", audit)
    paths = {"previous_summary.json": previous / "summary.json"}
    for name in ("references.npz", "reference.json", "e_prefix.json", "m_prefix.json"):
        paths[name] = previous / "inputs" / name
    for stem in ("e_to_m_pulse", "m_to_e_pulse"):
        if not next(b for b in audit["branches"] if b["case"]["id"] == stem)["exposure_rehomed"]:
            raise RuntimeError("Audited source lineage did not rehome")
        for suffix, sub in (("", ""), ("_round_03", "round_03")):
            for ext, filename in (("npz", "endpoints.npz"), ("json", "result.json")):
                paths[stem + suffix + "." + ext] = previous / stem / sub / filename
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
        load_descendants(inputs, config, case, indices)
    write_json(inputs / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/lineage_return_v1.json")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        spec = json.loads(args.worker.read_text())
        return branch_worker(args.worker.parent, spec["config"], spec["case"], Path(spec["inputs"]))
    validate_config(json.loads(args.config.read_text()))
    helpers = ["bounded_extension.py", "run_exposure_rehoming.py", "run_rehoming.py", "run_renewal.py",
        "run_group_transfer.py", "run_onward_transfer.py", "run_memory_probe.py", "memory_metrics.py", "run_pilot.py",
        "analyze_renewal.py", "analyze_group_transfer.py", "analyze_erasure_rescue.py", "analyze_rehoming.py",
        "analyze_exposure_rehoming.py", "analyze_lineage_return.py", "test_lineage_return.py", "test_exposure_rehoming.py"]
    return run_bounded(args.config.resolve(), Path(__file__).resolve(), ROOT / "LINEAGE_RETURN_PROTOCOL.md",
        helpers, freeze_inputs, "lineage-return", "Return-state cue and renewed transmission from actual rehomed descendants")


if __name__ == "__main__":
    raise SystemExit(main())
