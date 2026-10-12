"""Fixed equal-fraction pair edits followed by the unchanged replacement relay."""

import argparse
import json
from pathlib import Path

import numpy as np

from bounded_extension import run_bounded
from memory_metrics import REGULATORS, classify
from run_memory_probe import Experiment, write_json
from run_onward_transfer import file_hash
from run_pair_regulator import SHARED_PARAMETERS
from run_pilot import ROOT, REVISION
from run_renewal import round_worker

PAIRS = {"e_mir_prot": (REGULATORS[0], REGULATORS[2]), "e_mrna_prot": REGULATORS[1:]}


def edit_fraction(packet, later, indices, names, fraction):
    if isinstance(fraction, bool) or not isinstance(fraction, (int, float)) or not np.isfinite(fraction) or not 0 <= fraction <= 1:
        raise ValueError("Fraction must be finite and between zero and one")
    if not ((not names and fraction == 0) or tuple(names) in PAIRS.values()):
        raise ValueError("Require a specified protein-containing pair or shared zero control")
    if packet.shape != (17, 2) or later.shape != (17, 2):
        raise ValueError("Expected two carriers and E/M references")
    if not all(np.isfinite(a).all() and (a >= 0).all() for a in (packet, later)):
        raise ValueError("Invalid state")
    edited = packet.copy()
    for name in names:
        row = indices[name]
        if fraction == 1:
            edited[row] = later[row, 0]
        elif fraction != 0:
            edited[row] = (1 - fraction) * packet[row] + fraction * later[row, 0]
    return edited


def validate_config(config):
    if not 1 <= config["workers"] <= 2 or not 0 < config["worker_timeout_seconds"] <= 900 or not 0 < config["total_budget_seconds"] <= 3600:
        raise ValueError("Exceeds runtime/concurrency bounds")
    if config["revision"] != REVISION or config["packet_size"] != 2 or config["continuing_rounds"] != [2, 3]:
        raise ValueError("Wrong revision, width or rounds")
    if config["intervention_horizon"] != 1000 or config["inherited_wait"] != 1000:
        raise ValueError("Wrong intervention timing")
    expected = {"e_none": ((), 0, False)}
    for pair, names in PAIRS.items():
        for fraction in (.25, .5, .75, 1.):
            key = f"{pair}_{round(fraction * 100):03}"
            expected[key] = (names, fraction, False)
            if fraction < 1:
                expected[key + "_fine"] = (names, fraction, True)
    cases = config["cases"]
    if len(cases) != 15 or {c["id"] for c in cases} != set(expected):
        raise ValueError("Require fixed 15-case grid")
    for c in cases:
        if c["state"] != "E" or c["history"] != "learned" or isinstance(c["fraction"], bool):
            raise ValueError("Wrong direction, history or fraction")
        if (tuple(c["targets"]), c["fraction"], c.get("fine", False)) != expected[c["id"]]:
            raise ValueError("Case differs from fixed grid")


def branch_worker(folder, config, case, inputs):
    with np.load(inputs / "references.npz", allow_pickle=False) as refs:
        prepared, later = refs["prepared"], refs["later"]
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    meta = json.loads((inputs / "e_prefix.json").read_text())
    ids, seen = meta["outgoing_ids"].copy(), set(meta["incoming_ids"] + meta["outgoing_ids"])
    with np.load(inputs / "e_erased.npz", allow_pickle=False) as saved:
        before = saved["after_1"].copy()
    if classify(before, indices).tolist() != ["M", "M"]:
        raise RuntimeError("Expected actual erased M pair")
    edited = edit_fraction(before, later, indices, case["targets"], case["fraction"])
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
    intervention = {"incoming_ids": ids.copy(), "outgoing_ids": ids.copy(), "target_names": case["targets"], "fraction": case["fraction"],
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
        print(f"FRACTION_ROUND {number}: {''.join(classify(packet, indices))}; success={result['round_success']}", flush=True)
    transmitted = all(r["round_success"] for r in rounds)
    offset = config["inherited_wait"] + config["intervention_horizon"]
    np.savez_compressed(folder / "endpoints.npz", erased_input=before, continuing_start=start, final_packet=packet, fresh_target=fresh)
    write_json(folder / "result.json", {"case": case, "execution_pass": True, "ion_indices": indices,
        "intervention": intervention, "rounds": rounds, "final_ids": ids, "distinct_fresh_targets": len(seen) - 4,
        "all_rounds_transmitted": transmitted, "relay_rescued": carrier_rescued and transmitted,
        "nominal_schedule": [{"round": r["round"], "start": r["nominal_round_start"] + offset, "end": r["nominal_round_end"] + offset} for r in rounds]})
    return 0


def freeze_inputs(run, config):
    from analyze_pair_regulator import analyze
    previous = (ROOT / config["input_run"]).resolve()
    if not previous.is_relative_to(ROOT / "runs"):
        raise ValueError("Input must be an exploration run")
    summary = json.loads((previous / "summary.json").read_text())
    required = ("all_execution_valid", "source_clean_after", "inputs_unchanged", "files_unchanged", "frozen_files_unchanged", "predecessor_audit_unchanged")
    if not all(summary.get(k) for k in required) or summary["revision"] != REVISION:
        raise RuntimeError("Invalid predecessor")
    if any(config[k] != summary["config"][k] for k in SHARED_PARAMETERS):
        raise RuntimeError("Fractional and full-reset parameters differ")
    for name in ("run_memory_probe.py", "run_renewal.py", "run_group_transfer.py", "run_onward_transfer.py", "memory_metrics.py"):
        relative = "scripts/" + name
        if file_hash(ROOT / relative) != summary["hashes_sha256"][relative]:
            raise RuntimeError("Shared simulation helper changed")
    audit = analyze(previous)
    if not all(audit[k] for k in ("all_array_checks_pass", "input_hashes_valid", "frozen_hashes_valid", "predecessor_audit_hash_valid")):
        raise RuntimeError("Predecessor audit failed")
    write_json(run / "predecessor_audit.json", audit)
    paths = {"previous_summary.json": previous / "summary.json"}
    for name in ("references.npz", "reference.json", "e_prefix.json", "e_erased.npz", "e_erased.json"):
        paths[name] = previous / "inputs" / name
    with np.load(paths["e_erased.npz"], allow_pickle=False) as data:
        erased = data["after_1"]
    for key, names in {"e_none": (), **PAIRS}.items():
        folder = previous / key
        result = json.loads((folder / "result.json").read_text())
        c = result["case"]
        if c["state"] != "E" or tuple(c["targets"]) != names or c.get("fine", False):
            raise RuntimeError("Wrong historical comparator")
        with np.load(folder / "endpoints.npz", allow_pickle=False) as data:
            if not np.array_equal(data["erased_input"], erased):
                raise RuntimeError("Historical comparator has different input")
        for suffix, source in (("json", "result.json"), ("npz", "endpoints.npz")):
            paths[f"previous_{key}.{suffix}"] = folder / source
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
    parser.add_argument("--config", type=Path, default=ROOT / "configs/fractional_rescue_v1.json")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        spec = json.loads(args.worker.read_text())
        return branch_worker(args.worker.parent, spec["config"], spec["case"], Path(spec["inputs"]))
    validate_config(json.loads(args.config.read_text()))
    helpers = ["bounded_extension.py", "run_renewal.py", "run_group_transfer.py", "run_onward_transfer.py", "run_memory_probe.py",
        "memory_metrics.py", "run_pilot.py", "run_erasure_rescue.py", "run_single_regulator.py", "run_pair_regulator.py",
        "analyze_renewal.py", "analyze_group_transfer.py", "analyze_erasure_rescue.py", "analyze_single_regulator.py", "analyze_pair_regulator.py",
        "analyze_fractional_rescue.py", "test_fractional_rescue.py"]
    return run_bounded(args.config.resolve(), Path(__file__).resolve(), ROOT / "FRACTIONAL_RESCUE_PROTOCOL.md", helpers,
        freeze_inputs, "fractional-rescue", "Fixed equal-fraction E pair resets in a finite externally scheduled relay")


if __name__ == "__main__":
    raise SystemExit(main())
