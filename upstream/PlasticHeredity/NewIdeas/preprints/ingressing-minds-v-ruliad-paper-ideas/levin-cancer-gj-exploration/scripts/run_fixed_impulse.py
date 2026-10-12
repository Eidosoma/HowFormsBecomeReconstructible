"""Same absolute two-regulator impulse across a fixed starting-state panel."""

import argparse
import json
from pathlib import Path

import numpy as np

from bounded_extension import run_bounded
from memory_metrics import REGULATORS, classify
from run_heterogeneous_start import BACKGROUNDS, COPIED_INPUTS, vary_start
from run_memory_probe import Experiment, write_json
from run_onward_transfer import file_hash
from run_pair_regulator import SHARED_PARAMETERS
from run_pilot import ROOT, REVISION
from run_renewal import round_worker

TARGETS = (REGULATORS[0], REGULATORS[2])


def calibrated_delta(original, later, indices):
    """One calibration: original carrier column zero, never the varied start."""
    for state in (original, later):
        if state.shape != (17, 2) or not np.isfinite(state).all() or (state < 0).any():
            raise ValueError("Expected finite nonnegative two-column states")
    rows = [indices[name] for name in TARGETS]
    return .75 * (later[rows, 0] - original[rows, 0])


def edit_fixed(packet, later, original, indices, mode):
    delta = calibrated_delta(original, later, indices)
    if packet.shape != (17, 2) or not np.isfinite(packet).all() or (packet < 0).any():
        raise ValueError("Invalid starting pair")
    edited = packet.copy()
    rows = [indices[name] for name in TARGETS]
    if mode == "fixed":
        edited[rows] = packet[rows] + delta[:, None]
    elif mode == "reference":
        edited[rows] = later[rows, 0, None]
    elif mode != "none":
        raise ValueError("Unknown intervention mode")
    if not np.isfinite(edited).all() or (edited < 0).any():
        raise ValueError("Impulse leaves the valid state space; no clipping allowed")
    return edited


def validate_config(config):
    if not 1 <= config["workers"] <= 2 or not 0 < config["worker_timeout_seconds"] <= 900 or not 0 < config["total_budget_seconds"] <= 3600:
        raise ValueError("Exceeds runtime/concurrency bounds")
    if config["revision"] != REVISION or config["packet_size"] != 2 or config["continuing_rounds"] != [2, 3]:
        raise ValueError("Wrong revision, width or rounds")
    if config["intervention_horizon"] != 1000 or config["inherited_wait"] != 1000 or config["backgrounds"] != BACKGROUNDS:
        raise ValueError("Changed timing or background panel")
    if config["calibration_fraction"] != .75 or type(config["anchor_column"]) is not int or config["anchor_column"] != 0:
        raise ValueError("Calibration must be .75 from original column zero")
    expected = {}
    for background in BACKGROUNDS:
        for mode in ("none", "fixed", "reference"):
            expected[background + "_" + mode] = (background, mode, False)
        expected[background + "_fixed_fine"] = (background, "fixed", True)
    cases = config["cases"]
    if len(cases) != 16 or {c["id"] for c in cases} != set(expected):
        raise ValueError("Require the fixed sixteen-case panel")
    for c in cases:
        targets = [] if c["mode"] == "none" else list(TARGETS)
        if c["state"] != "E" or c["history"] != "learned" or c["targets"] != targets or "fraction" in c:
            raise ValueError("Invalid direction, history or target specification")
        if (c["background"], c["mode"], c.get("fine", False)) != expected[c["id"]]:
            raise ValueError("Case differs from fixed grid")


def branch_worker(folder, config, case, inputs):
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    with np.load(inputs / "e_erased.npz", allow_pickle=False) as data:
        original = data["after_1"].copy()
    factors = np.asarray(config["backgrounds"][case["background"]])
    varied = vary_start(original, indices, factors)
    if classify(varied, indices).tolist() != ["M", "M"]:
        raise RuntimeError("Background preparation must retain both M labels")
    np.savez_compressed(folder / "background.npz", original_erased=original, varied_start=varied, factors=factors)
    derived = folder / "prepared_inputs"
    derived.mkdir()
    for name in COPIED_INPUTS:
        (derived / name).write_bytes((inputs / name).read_bytes())
    np.savez_compressed(derived / "e_erased.npz", after_1=varied)
    hashes = {p.name: file_hash(p) for p in derived.iterdir()}
    record = {"background": case["background"], "factors": factors.tolist(), "extra_relaxation_horizon": 0,
        "original_labels": "".join(classify(original, indices)), "varied_labels": "".join(classify(varied, indices)),
        "prepared_hashes_sha256": hashes, "background_sha256": file_hash(folder / "background.npz")}
    write_json(folder / "background.json", record)

    with np.load(inputs / "references.npz", allow_pickle=False) as refs:
        prepared, later = refs["prepared"], refs["later"]
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    meta = json.loads((inputs / "e_prefix.json").read_text())
    ids, seen = meta["outgoing_ids"].copy(), set(meta["incoming_ids"] + meta["outgoing_ids"])
    before = varied.copy()
    if classify(before, indices).tolist() != ["M", "M"]:
        raise RuntimeError("Expected actual erased M pair")
    edited = edit_fixed(before, later, original, indices, case["mode"])
    delta = calibrated_delta(original, later, indices)
    stage = folder / "intervention"
    stage.mkdir()
    exp = Experiment(stage, config, fine=case.get("fine", False))
    cells, setups = [], []
    for cell in (1, 2):
        setups.append(exp.build(1, edited[:, cell - 1:cell], active=False))
        if exp.indices != indices:
            raise RuntimeError("Ion indexing changed")
        final, _ = exp.phase(f"cell_{cell}_wait", config["intervention_horizon"])
        cells.append(final)
    packet = np.concatenate(cells, axis=1)
    carrier_rescued = all(a["recipient_label"] == "E" and a["late_label_fractions"]["E"] >= config["late_label_fraction"] for a in exp.audits)
    intervention = {"incoming_ids": ids.copy(), "outgoing_ids": ids.copy(), "target_names": case["targets"], "mode": case["mode"],
        "calibration_fraction": .75, "anchor_column": 0, "calibrated_delta": delta.tolist(),
        "before_labels": "".join(classify(before, indices)), "immediate_labels": "".join(classify(edited, indices)),
        "after_wait_labels": "".join(classify(packet, indices)), "carrier_rescued": carrier_rescued,
        "sustained_forcing": False, "setups": setups, "audits": exp.audits}
    np.savez_compressed(stage / "endpoints.npz", before=before, edited=edited, after_wait=packet)
    write_json(stage / "result.json", intervention)
    start, fresh, rounds = packet.copy(), prepared[:, 1, None].copy(), []
    for number in config["continuing_rounds"]:
        subdir = folder / f"round_{number:02}"
        subdir.mkdir()
        packet, ids, result = round_worker(subdir, config, case, packet, ids, seen, fresh, later, indices, number)
        seen.update(ids)
        rounds.append(result)
        write_json(folder / "progress.json", rounds)
        print(f"FIXED_IMPULSE_ROUND {number}: {''.join(classify(packet, indices))}; success={result['round_success']}", flush=True)
    transmitted = all(r["round_success"] for r in rounds)
    offset = config["inherited_wait"] + config["intervention_horizon"]
    np.savez_compressed(folder / "endpoints.npz", erased_input=before, continuing_start=start, final_packet=packet, fresh_target=fresh)
    write_json(folder / "result.json", {"case": case, "execution_pass": True, "ion_indices": indices,
        "intervention": intervention, "rounds": rounds, "final_ids": ids, "distinct_fresh_targets": len(seen) - 4,
        "all_rounds_transmitted": transmitted, "relay_rescued": carrier_rescued and transmitted,
        "nominal_schedule": [{"round": r["round"], "start": r["nominal_round_start"] + offset, "end": r["nominal_round_end"] + offset} for r in rounds]})
    if not all(file_hash(derived / name) == digest for name, digest in hashes.items()) or file_hash(folder / "background.npz") != record["background_sha256"]:
        raise RuntimeError("Prepared inputs changed during relay")
    record["prepared_inputs_unchanged"] = True
    write_json(folder / "background.json", record)
    return 0


def freeze_inputs(run, config):
    from analyze_heterogeneous_start import analyze
    previous = (ROOT / config["input_run"]).resolve()
    if not previous.is_relative_to(ROOT / "runs"):
        raise ValueError("Input must be an exploration run")
    summary = json.loads((previous / "summary.json").read_text())
    required = ("all_execution_valid", "source_clean_after", "inputs_unchanged", "files_unchanged", "frozen_files_unchanged", "predecessor_audit_unchanged")
    if not all(summary.get(k) for k in required) or summary["revision"] != REVISION:
        raise RuntimeError("Invalid predecessor")
    if any(config[k] != summary["config"][k] for k in SHARED_PARAMETERS):
        raise RuntimeError("Shared parameters changed")
    for name in ("run_heterogeneous_start.py", "run_fractional_rescue.py", "run_memory_probe.py", "run_renewal.py", "run_group_transfer.py", "run_onward_transfer.py", "memory_metrics.py"):
        path = "scripts/" + name
        if file_hash(ROOT / path) != summary["hashes_sha256"][path]:
            raise RuntimeError("Shared simulation helper changed")
    audit = analyze(previous)
    if not all(audit[k] for k in ("all_array_checks_pass", "input_hashes_valid", "frozen_hashes_valid", "predecessor_audit_hash_valid")):
        raise RuntimeError("Predecessor audit failed")
    write_json(run / "predecessor_audit.json", audit)
    paths = {"previous_summary.json": previous / "summary.json"}
    for name in (*COPIED_INPUTS, "e_erased.npz", "e_erased.json"):
        paths[name] = previous / "inputs" / name
    with np.load(paths["e_erased.npz"], allow_pickle=False) as data:
        original = data["after_1"]
    for background in BACKGROUNDS:
        for suffix, fraction in (("000", 0), ("075", .75), ("100", 1)):
            key = background + "_" + suffix
            folder = previous / key
            c = json.loads((folder / "result.json").read_text())["case"]
            names = [] if fraction == 0 else list(TARGETS)
            if c["state"] != "E" or c["targets"] != names or c["fraction"] != fraction or c.get("fine", False) or c["background"] != background:
                raise RuntimeError("Wrong historical comparator")
            expected = vary_start(original, json.loads(paths["reference.json"].read_text())["ion_indices"], BACKGROUNDS[background])
            with np.load(folder / "endpoints.npz", allow_pickle=False) as data:
                if not np.array_equal(data["erased_input"], expected):
                    raise RuntimeError("Comparator used different varied input")
            for suffix, name in (("json", "result.json"), ("npz", "endpoints.npz")):
                paths[f"previous_{key}.{suffix}"] = folder / name
    inputs = run / "inputs"
    inputs.mkdir()
    manifest = {}
    for name, source in paths.items():
        digest = file_hash(source)
        (inputs / name).write_bytes(source.read_bytes())
        if file_hash(source) != digest or file_hash(inputs / name) != digest:
            raise RuntimeError("Input changed during copying")
        manifest[name] = {"source": str(source), "sha256": digest}
    write_json(inputs / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/fixed_impulse_v1.json")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        spec = json.loads(args.worker.read_text())
        return branch_worker(args.worker.parent, spec["config"], spec["case"], Path(spec["inputs"]))
    validate_config(json.loads(args.config.read_text()))
    helpers = ["bounded_extension.py", "run_fractional_rescue.py", "run_renewal.py", "run_group_transfer.py", "run_onward_transfer.py",
        "run_memory_probe.py", "memory_metrics.py", "run_pilot.py", "run_erasure_rescue.py", "run_single_regulator.py", "run_pair_regulator.py",
        "analyze_renewal.py", "analyze_group_transfer.py", "analyze_erasure_rescue.py", "analyze_single_regulator.py", "analyze_pair_regulator.py",
        "analyze_fractional_rescue.py", "analyze_heterogeneous_start.py", "test_heterogeneous_start.py", "run_heterogeneous_start.py", "analyze_fixed_impulse.py", "test_fixed_impulse.py"]
    return run_bounded(args.config.resolve(), Path(__file__).resolve(), ROOT / "FIXED_IMPULSE_PROTOCOL.md", helpers,
        freeze_inputs, "fixed-impulse", "Fixed absolute impulse, no state-tailored amount, followed by finite E carrier replacement")


if __name__ == "__main__":
    raise SystemExit(main())
