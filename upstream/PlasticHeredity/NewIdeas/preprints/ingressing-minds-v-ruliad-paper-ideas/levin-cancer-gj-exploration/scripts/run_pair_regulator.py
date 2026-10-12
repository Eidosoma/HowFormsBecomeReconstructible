"""Fixed E-directed pair-reference resets followed by two full replacements."""

import argparse
import json
from pathlib import Path

import numpy as np

from bounded_extension import run_bounded
from memory_metrics import REGULATORS, classify
from run_memory_probe import Experiment, write_json
from run_onward_transfer import file_hash
from run_pilot import ROOT, REVISION
from run_renewal import round_worker

SHARED_PARAMETERS = ("revision", "packet_size", "continuing_rounds", "intervention_horizon", "inherited_wait", "write_kd",
    "contact_horizon", "retention_horizons", "recovery_horizon", "perturbation_fraction", "late_label_fraction",
    "minimum_challenge_distance", "recovery_absolute_tolerance", "recovery_distance_ratio")


def edit_subset(packet, later, indices, names):
    if len(names) not in (0, 2, 3) or len(set(names)) != len(names) or any(n not in REGULATORS for n in names):
        raise ValueError("Require a pair, full reset, or no edit")
    if packet.shape != (17, 2) or later.shape != (17, 2):
        raise ValueError("Expected two-cell packet and E/M references")
    if not all(np.isfinite(a).all() and (a >= 0).all() for a in (packet, later)):
        raise ValueError("Invalid concentrations")
    edited = packet.copy()
    for name in names:
        edited[indices[name]] = later[indices[name], 0]
    return edited


def validate_config(config):
    if not 1 <= config["workers"] <= 2 or not 0 < config["worker_timeout_seconds"] <= 900 or not 0 < config["total_budget_seconds"] <= 3600:
        raise ValueError("Exceeds concurrency/runtime bounds")
    if config["revision"] != REVISION or config["packet_size"] != 2 or config["continuing_rounds"] != [2, 3]:
        raise ValueError("Unexpected revision, width or rounds")
    if config["intervention_horizon"] != 1000 or config["inherited_wait"] != 1000:
        raise ValueError("Unexpected intervention timing")
    expected = {"e_none": (), "e_all": REGULATORS, "e_mir_mrna": REGULATORS[:2],
                "e_mir_prot": (REGULATORS[0], REGULATORS[2]), "e_mrna_prot": REGULATORS[1:]}
    expected.update({name + "_fine": names for name, names in list(expected.items()) if len(names) == 2})
    cases = config["cases"]
    if len(cases) != 8 or {c["id"] for c in cases} != set(expected):
        raise ValueError("Require the fixed eight-case grid")
    for case in cases:
        if case["state"] != "E" or case["history"] != "learned" or tuple(case["targets"]) != expected[case["id"]]:
            raise ValueError("Unexpected targets, direction or history")
        if case.get("fine", False) != case["id"].endswith("_fine"):
            raise ValueError("Fine flag must match condition")


def branch_worker(folder, config, case, inputs):
    with np.load(inputs / "references.npz", allow_pickle=False) as refs:
        prepared, later = refs["prepared"], refs["later"]
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    meta = json.loads((inputs / "e_prefix.json").read_text())
    ids, seen = meta["outgoing_ids"].copy(), set(meta["incoming_ids"] + meta["outgoing_ids"])
    with np.load(inputs / "e_erased.npz", allow_pickle=False) as saved:
        before = saved["after_1"].copy()
    if classify(before, indices).tolist() != ["M", "M"]:
        raise RuntimeError("Require the actual overwritten M pair")
    edited = edit_subset(before, later, indices, case["targets"])
    subdir = folder / "intervention"
    subdir.mkdir()
    exp = Experiment(subdir, config, fine=case.get("fine", False))
    children, setups = [], []
    for cell in (1, 2):
        setups.append(exp.build(1, edited[:, cell - 1:cell], active=False))
        if exp.indices != indices:
            raise RuntimeError("Ion indexing changed")
        final, _ = exp.phase(f"cell_{cell}_wait", config["intervention_horizon"])
        children.append(final)
    packet = np.concatenate(children, axis=1)
    carrier_rescued = all(a["recipient_label"] == "E" and a["late_label_fractions"]["E"] >= config["late_label_fraction"] for a in exp.audits)
    intervention = {"incoming_ids": ids.copy(), "outgoing_ids": ids.copy(), "target_names": case["targets"],
        "before_labels": "".join(classify(before, indices)), "immediate_labels": "".join(classify(edited, indices)),
        "after_wait_labels": "".join(classify(packet, indices)), "carrier_rescued": carrier_rescued,
        "sustained_forcing": False, "setups": setups, "audits": exp.audits}
    np.savez_compressed(subdir / "endpoints.npz", before=before, edited=edited, after_wait=packet)
    write_json(subdir / "result.json", intervention)
    start, fresh, rounds = packet.copy(), prepared[:, 1, None].copy(), []
    for number in config["continuing_rounds"]:
        round_dir = folder / f"round_{number:02}"
        round_dir.mkdir()
        packet, ids, result = round_worker(round_dir, config, case, packet, ids, seen, fresh, later, indices, number)
        seen.update(ids)
        rounds.append(result)
        write_json(folder / "progress.json", rounds)
        print(f"PAIR_ROUND {number}: {''.join(classify(packet, indices))}; success={result['round_success']}", flush=True)
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
    from analyze_single_regulator import analyze
    previous = (ROOT / config["input_run"]).resolve()
    if not previous.is_relative_to(ROOT / "runs"):
        raise ValueError("Input run must be inside exploration runs")
    summary = json.loads((previous / "summary.json").read_text())
    required = ("all_execution_valid", "source_clean_after", "inputs_unchanged", "files_unchanged", "frozen_files_unchanged")
    if not all(summary.get(k) for k in required) or summary["revision"] != REVISION:
        raise RuntimeError("Invalid predecessor")
    if any(config[k] != summary["config"][k] for k in SHARED_PARAMETERS):
        raise RuntimeError("Pair and single comparison parameters differ")
    for name in ("run_memory_probe.py", "run_renewal.py", "run_group_transfer.py", "run_onward_transfer.py", "memory_metrics.py"):
        relative = "scripts/" + name
        if file_hash(ROOT / relative) != summary["hashes_sha256"][relative]:
            raise RuntimeError("Shared simulation helper changed since predecessor")
    audit = analyze(previous)
    if not all(audit[k] for k in ("all_array_checks_pass", "input_hashes_valid", "frozen_hashes_valid", "predecessor_audit_hash_valid")):
        raise RuntimeError("Predecessor audit failed")
    write_json(run / "predecessor_audit.json", audit)
    paths = {"previous_summary.json": previous / "summary.json"}
    for name in ("references.npz", "reference.json", "e_prefix.json", "e_erased.npz", "e_erased.json"):
        paths[name] = previous / "inputs" / name
    with np.load(paths["e_erased.npz"], allow_pickle=False) as saved:
        erased = saved["after_1"]
    for kind, target in (("none", "none"), ("all", "all"), ("mir", "miR200_total"), ("mrna", "Zeb_mRNA_total"), ("prot", "ZEB_prot")):
        folder = previous / ("e_" + kind)
        meta = json.loads((folder / "result.json").read_text())
        if meta["case"]["state"] != "E" or meta["case"]["target"] != target or meta["case"].get("fine", False):
            raise RuntimeError("Wrong historical comparator")
        with np.load(folder / "endpoints.npz", allow_pickle=False) as saved:
            if not np.array_equal(saved["erased_input"], erased):
                raise RuntimeError("Comparator started from different erased state")
        for suffix, source in (("json", "result.json"), ("npz", "endpoints.npz")):
            paths[f"previous_e_{kind}.{suffix}"] = folder / source
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
    parser.add_argument("--config", type=Path, default=ROOT / "configs/pair_regulator_v1.json")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        spec = json.loads(args.worker.read_text())
        return branch_worker(args.worker.parent, spec["config"], spec["case"], Path(spec["inputs"]))
    validate_config(json.loads(args.config.read_text()))
    helpers = ["bounded_extension.py", "run_renewal.py", "run_group_transfer.py", "run_onward_transfer.py",
        "run_memory_probe.py", "memory_metrics.py", "run_pilot.py", "run_erasure_rescue.py", "run_single_regulator.py",
        "analyze_renewal.py", "analyze_group_transfer.py", "analyze_erasure_rescue.py", "analyze_single_regulator.py",
        "analyze_pair_regulator.py", "test_pair_regulator.py"]
    return run_bounded(args.config.resolve(), Path(__file__).resolve(), ROOT / "PAIR_REGULATOR_PROTOCOL.md", helpers,
        freeze_inputs, "pair-regulator", "Fixed E-directed pair-reference resets in a finite externally scheduled relay")


if __name__ == "__main__":
    raise SystemExit(main())
