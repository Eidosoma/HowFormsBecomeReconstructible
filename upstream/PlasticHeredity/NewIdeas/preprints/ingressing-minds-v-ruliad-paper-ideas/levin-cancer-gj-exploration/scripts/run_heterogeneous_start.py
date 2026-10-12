"""Fixed regulatory starting-state panel; unchanged fractional-rescue worker."""

import argparse
import json
from pathlib import Path

import numpy as np

from bounded_extension import run_bounded
from memory_metrics import REGULATORS, classify
from run_fractional_rescue import branch_worker as relay_worker
from run_memory_probe import write_json
from run_onward_transfer import file_hash
from run_pair_regulator import SHARED_PARAMETERS
from run_pilot import ROOT, REVISION

BACKGROUNDS = {"original": [[1, 1], [1, 1], [1, 1]],
    "toward_e": [[1.1, 1.1], [.9, .9], [.9, .9]],
    "away_e": [[.9, .9], [1.1, 1.1], [1.1, 1.1]],
    "mixed": [[1.1, .9], [.9, 1.1], [.9, 1.1]]}
COPIED_INPUTS = ("references.npz", "reference.json", "e_prefix.json")


def vary_start(packet, indices, factors):
    factors = np.asarray(factors, dtype=float)
    if packet.shape != (17, 2) or factors.shape != (3, 2):
        raise ValueError("Expected two-cell state and three-by-two factors")
    if not np.isfinite(packet).all() or (packet < 0).any() or not np.isfinite(factors).all() or (factors < .9).any() or (factors > 1.1).any():
        raise ValueError("Invalid state or factors outside fixed ten-percent range")
    varied = packet.copy()
    rows = [indices[name] for name in REGULATORS]
    varied[rows] = packet[rows] * factors
    return varied


def validate_config(config):
    if not 1 <= config["workers"] <= 2 or not 0 < config["worker_timeout_seconds"] <= 900 or not 0 < config["total_budget_seconds"] <= 3600:
        raise ValueError("Exceeds runtime/concurrency bounds")
    if config["revision"] != REVISION or config["packet_size"] != 2 or config["continuing_rounds"] != [2, 3]:
        raise ValueError("Wrong revision, width or rounds")
    if config["intervention_horizon"] != 1000 or config["inherited_wait"] != 1000 or config["backgrounds"] != BACKGROUNDS:
        raise ValueError("Changed timing or background panel")
    expected = {}
    for name in BACKGROUNDS:
        for fraction in (0, .75, 1):
            expected[f"{name}_{round(fraction * 100):03}"] = (name, fraction, False)
        expected[name + "_075_fine"] = (name, .75, True)
    cases = config["cases"]
    if len(cases) != 16 or {c["id"] for c in cases} != set(expected):
        raise ValueError("Require fixed 16-case grid")
    for c in cases:
        names = [] if c["fraction"] == 0 else [REGULATORS[0], REGULATORS[2]]
        if c["state"] != "E" or c["history"] != "learned" or isinstance(c["fraction"], bool) or c["targets"] != names:
            raise ValueError("Wrong direction, history or target pair")
        if (c["background"], c["fraction"], c.get("fine", False)) != expected[c["id"]]:
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
    code = relay_worker(folder, config, case, derived)
    if not all(file_hash(derived / name) == digest for name, digest in hashes.items()) or file_hash(folder / "background.npz") != record["background_sha256"]:
        raise RuntimeError("Prepared inputs changed during relay")
    record["prepared_inputs_unchanged"] = True
    write_json(folder / "background.json", record)
    return code


def freeze_inputs(run, config):
    from analyze_fractional_rescue import analyze
    previous = (ROOT / config["input_run"]).resolve()
    if not previous.is_relative_to(ROOT / "runs"):
        raise ValueError("Input must be an exploration run")
    summary = json.loads((previous / "summary.json").read_text())
    required = ("all_execution_valid", "source_clean_after", "inputs_unchanged", "files_unchanged", "frozen_files_unchanged", "predecessor_audit_unchanged")
    if not all(summary.get(k) for k in required) or summary["revision"] != REVISION:
        raise RuntimeError("Invalid predecessor")
    if any(config[k] != summary["config"][k] for k in SHARED_PARAMETERS):
        raise RuntimeError("Shared parameters changed")
    for name in ("run_fractional_rescue.py", "run_memory_probe.py", "run_renewal.py", "run_group_transfer.py", "run_onward_transfer.py", "memory_metrics.py"):
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
    for key, fraction in (("e_none", 0), ("e_mir_prot_075", .75), ("e_mir_prot_100", 1)):
        folder = previous / key
        c = json.loads((folder / "result.json").read_text())["case"]
        names = [] if fraction == 0 else [REGULATORS[0], REGULATORS[2]]
        if c["state"] != "E" or c["targets"] != names or c["fraction"] != fraction or c.get("fine", False):
            raise RuntimeError("Wrong historical comparator")
        with np.load(folder / "endpoints.npz", allow_pickle=False) as data:
            if not np.array_equal(data["erased_input"], original):
                raise RuntimeError("Comparator used different input")
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
    parser.add_argument("--config", type=Path, default=ROOT / "configs/heterogeneous_start_v1.json")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        spec = json.loads(args.worker.read_text())
        return branch_worker(args.worker.parent, spec["config"], spec["case"], Path(spec["inputs"]))
    validate_config(json.loads(args.config.read_text()))
    helpers = ["bounded_extension.py", "run_fractional_rescue.py", "run_renewal.py", "run_group_transfer.py", "run_onward_transfer.py",
        "run_memory_probe.py", "memory_metrics.py", "run_pilot.py", "run_erasure_rescue.py", "run_single_regulator.py", "run_pair_regulator.py",
        "analyze_renewal.py", "analyze_group_transfer.py", "analyze_erasure_rescue.py", "analyze_single_regulator.py", "analyze_pair_regulator.py",
        "analyze_fractional_rescue.py", "analyze_heterogeneous_start.py", "test_heterogeneous_start.py"]
    return run_bounded(args.config.resolve(), Path(__file__).resolve(), ROOT / "HETEROGENEOUS_START_PROTOCOL.md", helpers,
        freeze_inputs, "heterogeneous-start", "Fixed initial-regulatory-state sensitivity of the 75-percent E rescue rule")


if __name__ == "__main__":
    raise SystemExit(main())
