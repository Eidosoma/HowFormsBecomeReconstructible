"""One-time single-regulator rescue followed by two complete carrier replacements."""

import argparse
import json
from pathlib import Path

import numpy as np

from bounded_extension import run_bounded
from memory_metrics import REGULATORS, classify, opposite
from run_memory_probe import Experiment, write_json
from run_onward_transfer import file_hash
from run_pilot import ROOT, REVISION
from run_renewal import round_worker


def target_names(target):
    if target == "none":
        return ()
    if target == "all":
        return REGULATORS
    if target not in REGULATORS:
        raise ValueError("Unknown regulator target")
    return (target,)


def rescue_edit(packet, later, indices, desired, target):
    opposite(desired)
    if packet.shape != (17, 2) or later.shape != (17, 2):
        raise ValueError("Expected a pair and two reference states")
    if not all(np.isfinite(a).all() and (a >= 0).all() for a in (packet, later)):
        raise ValueError("Invalid concentrations")
    edited = packet.copy()
    for name in target_names(target):
        edited[indices[name], :] = later[indices[name], {"E": 0, "M": 1}[desired]]
    return edited


def validate_config(config):
    if not 1 <= config["workers"] <= 2 or not 0 < config["worker_timeout_seconds"] <= 900 or not 0 < config["total_budget_seconds"] <= 3600:
        raise ValueError("Exceeds concurrency/runtime limits")
    if config["revision"] != REVISION or config["packet_size"] != 2 or config["continuing_rounds"] != [2, 3]:
        raise ValueError("Unexpected revision, width or rounds")
    if config["intervention_horizon"] != 1000 or config["inherited_wait"] != 1000:
        raise ValueError("Unexpected intervention timing")
    expected = {(s, t, fine) for s in ("E", "M") for t in ("none", "all", *REGULATORS)
                for fine in ((False, True) if t in REGULATORS else (False,))}
    observed = {(c["state"], c["target"], c.get("fine", False)) for c in config["cases"]}
    ids = [c["id"] for c in config["cases"]]
    if len(ids) != 16 or len(set(ids)) != 16 or expected != observed:
        raise ValueError("Require the fixed sixteen-branch grid")
    for c in config["cases"]:
        if Path(c["id"]).name != c["id"] or c["id"] in (".", "..") or c["history"] != "learned":
            raise ValueError("Invalid case ID/history")
        suffix = {"none": "none", "all": "all", "miR200_total": "mir", "Zeb_mRNA_total": "mrna", "ZEB_prot": "prot"}[c["target"]]
        if c["id"] != c["state"].lower() + "_" + suffix + ("_fine" if c.get("fine") else ""):
            raise ValueError("Case ID must match its fixed condition")


def branch_worker(folder, config, case, inputs):
    with np.load(inputs / "references.npz", allow_pickle=False) as refs:
        prepared, later = refs["prepared"], refs["later"]
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    stem = case["state"].lower()
    metadata = json.loads((inputs / f"{stem}_prefix.json").read_text())
    ids = metadata["outgoing_ids"].copy()
    seen = set(metadata["incoming_ids"] + ids)
    with np.load(inputs / f"{stem}_erased.npz", allow_pickle=False) as saved:
        before = saved["after_1"].copy()
    if classify(before, indices).tolist() != [opposite(case["state"])] * 2:
        raise RuntimeError("Input must be the overwritten post-wait pair")
    edited = rescue_edit(before, later, indices, case["state"], case["target"])
    intervention_dir = folder / "intervention"
    intervention_dir.mkdir()
    exp = Experiment(intervention_dir, config, fine=case.get("fine", False))
    children, setups = [], []
    for cell in (1, 2):
        setups.append(exp.build(1, edited[:, cell - 1:cell], active=False))
        if exp.indices != indices:
            raise RuntimeError("Ion indices changed")
        final, _ = exp.phase(f"cell_{cell}_wait", config["intervention_horizon"])
        children.append(final)
    packet = np.concatenate(children, axis=1)
    carrier_rescued = all(a["recipient_label"] == case["state"] and a["late_label_fractions"][case["state"]] >= config["late_label_fraction"]
                          for a in exp.audits)
    intervention = {"incoming_ids": ids.copy(), "outgoing_ids": ids.copy(), "target_names": list(target_names(case["target"])),
        "before_labels": "".join(classify(before, indices)), "immediate_labels": "".join(classify(edited, indices)),
        "after_wait_labels": "".join(classify(packet, indices)), "carrier_rescued": carrier_rescued,
        "setups": setups, "audits": exp.audits, "sustained_forcing": False}
    np.savez_compressed(intervention_dir / "endpoints.npz", before=before, edited=edited, after_wait=packet)
    write_json(intervention_dir / "result.json", intervention)
    fresh = prepared[:, {"E": 0, "M": 1}[opposite(case["state"])], None].copy()
    start, rounds = packet.copy(), []
    for number in config["continuing_rounds"]:
        round_dir = folder / f"round_{number:02}"
        round_dir.mkdir()
        packet, ids, result = round_worker(round_dir, config, case, packet, ids, seen, fresh, later, indices, number)
        seen.update(ids)
        rounds.append(result)
        write_json(folder / "progress.json", rounds)
        print(f"SINGLE_ROUND {number}: {''.join(classify(packet, indices))}; success={result['round_success']}", flush=True)
    transmitted = all(r["round_success"] for r in rounds)
    offset = config["inherited_wait"] + config["intervention_horizon"]
    np.savez_compressed(folder / "endpoints.npz", erased_input=before, continuing_start=start, final_packet=packet, fresh_target=fresh)
    write_json(folder / "result.json", {"case": case, "execution_pass": True, "ion_indices": indices,
        "intervention": intervention, "rounds": rounds, "final_ids": ids, "distinct_fresh_targets": len(seen) - 4,
        "all_rounds_transmitted": transmitted, "relay_rescued": carrier_rescued and transmitted,
        "nominal_schedule": [{"round": r["round"], "start": r["nominal_round_start"] + offset,
                              "end": r["nominal_round_end"] + offset} for r in rounds]})
    return 0


def freeze_inputs(run, config):
    from analyze_erasure_rescue import analyze
    previous = (ROOT / config["input_run"]).resolve()
    if not previous.is_relative_to(ROOT / "runs"):
        raise ValueError("Input run must be inside exploration runs")
    summary = json.loads((previous / "summary.json").read_text())
    required = ("all_execution_valid", "source_clean_after", "inputs_unchanged", "files_unchanged", "frozen_files_unchanged")
    if summary["revision"] != REVISION or not all(summary.get(k) for k in required):
        raise RuntimeError("Invalid predecessor")
    if summary["config"]["intervention_horizon"] != config["inherited_wait"]:
        raise RuntimeError("Inherited wait does not match predecessor")
    audit = analyze(previous)
    if not all(audit[k] for k in ("all_array_checks_pass", "input_hashes_valid", "frozen_hashes_valid", "predecessor_audit_hash_valid")):
        raise RuntimeError("Predecessor audit failed")
    write_json(run / "predecessor_audit.json", audit)
    paths = {"previous_summary.json": previous / "summary.json",
             "references.npz": previous / "inputs/references.npz", "reference.json": previous / "inputs/reference.json"}
    for stem, desired in (("e", "E"), ("m", "M")):
        paths[f"{stem}_prefix.json"] = previous / "inputs" / f"{stem}_prefix.json"
        paths[f"{stem}_erased.npz"] = previous / f"{stem}_overwrite/intervention/endpoints.npz"
        paths[f"{stem}_erased.json"] = previous / f"{stem}_overwrite/intervention/result.json"
        paths[f"{stem}_full.npz"] = previous / f"{stem}_rescue/intervention/endpoints.npz"
        meta = json.loads(paths[f"{stem}_erased.json"].read_text())
        prefix = json.loads(paths[f"{stem}_prefix.json"].read_text())
        if meta["stages"][0]["labels_after_wait"] != opposite(desired) * 2 or meta["incoming_ids"] != prefix["outgoing_ids"]:
            raise RuntimeError("Wrong erased state or carrier identities")
    inputs = run / "inputs"
    inputs.mkdir()
    manifest = {}
    for name, path in paths.items():
        digest = file_hash(path)
        (inputs / name).write_bytes(path.read_bytes())
        if file_hash(path) != digest or file_hash(inputs / name) != digest:
            raise RuntimeError("Input changed during copying")
        manifest[name] = {"source": str(path), "sha256": digest}
    write_json(inputs / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/single_regulator_v1.json")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        spec = json.loads(args.worker.read_text())
        return branch_worker(args.worker.parent, spec["config"], spec["case"], Path(spec["inputs"]))
    validate_config(json.loads(args.config.read_text()))
    helpers = ["bounded_extension.py", "run_renewal.py", "run_group_transfer.py", "run_onward_transfer.py",
        "run_memory_probe.py", "memory_metrics.py", "run_pilot.py", "run_erasure_rescue.py",
        "analyze_renewal.py", "analyze_group_transfer.py", "analyze_erasure_rescue.py", "analyze_single_regulator.py",
        "test_single_regulator.py"]
    return run_bounded(args.config.resolve(), Path(__file__).resolve(), ROOT / "SINGLE_REGULATOR_PROTOCOL.md", helpers,
        freeze_inputs, "single-regulator", "One-time regulatory edits in a finite externally scheduled replacement relay")


if __name__ == "__main__":
    raise SystemExit(main())
