"""Test alternative-state relay from exact prior overwritten carrier pairs."""

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
from run_renewal import round_worker

SHARED = ("revision", "packet_size", "write_kd", "contact_horizon", "retention_horizons",
    "recovery_horizon", "perturbation_fraction", "late_label_fraction",
    "minimum_challenge_distance", "recovery_absolute_tolerance", "recovery_distance_ratio")


def validate_config(config):
    if not 1 <= config["workers"] <= 2 or not 0 < config["worker_timeout_seconds"] <= 900 or not 0 < config["total_budget_seconds"] <= 3600:
        raise ValueError("Exceeds execution bounds")
    if config["revision"] != REVISION or config["packet_size"] != 2 or config["continuing_rounds"] != [2, 3] or config["intervention_horizon"] != 1000:
        raise ValueError("Wrong revision, width, rounds or timing")
    expected = {}
    for old in ("E", "M"):
        state = opposite(old)
        stem = old.lower() + "_to_" + state.lower()
        for condition in ("rehomed", "blocked", "sham", "ordinary"):
            history = "blocked" if condition == "blocked" else "ordinary" if condition == "ordinary" else "learned"
            expected[stem + "_" + condition] = (old, state, condition, history, False)
        expected[stem + "_rehomed_fine"] = (old, state, "rehomed", "learned", True)
    cases = config["cases"]
    if len(cases) != 10 or {c["id"] for c in cases} != set(expected):
        raise ValueError("Require the fixed ten-case grid")
    for c in cases:
        if (c["old_state"], c["state"], c["condition"], c["history"], c.get("fine", False)) != expected[c["id"]]:
            raise ValueError("Case differs from fixed grid")


def source_spec(case):
    if case["condition"] == "ordinary":
        stem = case["state"].lower() + "_ordinary"
        return {"packet_file": stem + ".npz", "metadata_file": stem + ".json", "key": "outgoing_packet"}
    if case["condition"] not in ("rehomed", "blocked", "sham"):
        raise ValueError("Unknown source condition")
    kind = "sham" if case["condition"] == "sham" else "overwrite"
    stem = case["old_state"].lower() + "_" + kind
    return {"packet_file": stem + ".npz", "metadata_file": stem + ".json", "key": "after_2"}


def load_source(inputs, case, indices):
    spec = source_spec(case)
    packet = arrays(inputs / spec["packet_file"])[spec["key"]].copy()
    meta = json.loads((inputs / spec["metadata_file"]).read_text())
    ids = meta["outgoing_ids"].copy()
    if case["condition"] == "ordinary":
        seen = set(meta["incoming_ids"] + ids)
    else:
        prefix = json.loads((inputs / (case["old_state"].lower() + "_prefix.json")).read_text())
        if ids != prefix["outgoing_ids"]:
            raise ValueError("Changed carriers do not match the original prefix")
        seen = set(prefix["incoming_ids"] + ids)
    expected = case["old_state"] if case["condition"] == "sham" else case["state"]
    if packet.shape != (17, 2) or not np.isfinite(packet).all() or (packet < 0).any() or classify(packet, indices).tolist() != [expected] * 2:
        raise ValueError("Invalid source pair or polarity")
    if len(ids) != 2 or len(set(ids)) != 2 or len(seen) != 4:
        raise ValueError("Invalid source identity ledger")
    return packet, ids, seen, spec


def age_ordinary(folder, config, packet, ids, indices):
    """Two sham wait stages, in the existing intervention-audit format."""
    folder.mkdir()
    exp = Experiment(folder, config)
    saved = {"prefix_packet": packet.copy()}
    stages, setups = [], []
    for stage in (1, 2):
        saved[f"before_{stage}"] = packet.copy()
        saved[f"edited_{stage}"] = packet.copy()  # Explicit no-op, no reference use.
        cells, records = [], []
        for cell in (1, 2):
            setups.append(exp.build(1, packet[:, cell - 1:cell], active=False))
            if exp.indices != indices:
                raise ValueError("Ion indices changed")
            final, record = exp.phase(f"stage_{stage}_cell_{cell}", config["intervention_horizon"])
            cells.append(final)
            records.append(record)
        packet = np.concatenate(cells, axis=1)
        saved[f"after_{stage}"] = packet.copy()
        stages.append({"stage": stage, "anchor": None, "labels_after_wait": "".join(classify(packet, indices)), "phases": records})
    np.savez_compressed(folder / "endpoints.npz", **saved)
    write_json(folder / "result.json", {"stages": stages, "audits": exp.audits, "setups": setups,
        "incoming_ids": ids, "outgoing_ids": ids, "nominal_extra_duration": 2 * config["intervention_horizon"]})
    return packet


def fresh_recipient(prepared, case, indices):
    fresh = prepared[:, {"E": 0, "M": 1}[case["old_state"]], None].copy()
    if fresh.shape != (17, 1) or not np.isfinite(fresh).all() or (fresh < 0).any() or classify(fresh, indices).tolist() != [opposite(case["state"])]:
        raise ValueError("Recipient must start opposite the proposed new state")
    return fresh


def branch_worker(folder, config, case, inputs):
    refs = arrays(inputs / "references.npz")
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    packet, ids, seen, spec = load_source(inputs, case, indices)
    original, original_ids = packet.copy(), ids.copy()
    if case["condition"] == "ordinary":
        packet = age_ordinary(folder / "ordinary_wait", config, packet, ids, indices)
    start = packet.copy()
    fresh = fresh_recipient(refs["prepared"], case, indices)
    source_record = dict(spec, incoming_ids=original_ids, outgoing_ids=original_ids,
        source_labels="".join(classify(original, indices)), relay_start_labels="".join(classify(start, indices)),
        extra_waits=2 if case["condition"] == "ordinary" else 0, new_reference_edits=0)
    write_json(folder / "source.json", source_record)
    rounds = []
    for number in config["continuing_rounds"]:
        stage = folder / f"round_{number:02}"
        stage.mkdir()
        packet, ids, result = round_worker(stage, config, case, packet, ids, seen, fresh, refs["later"], indices, number)
        seen.update(ids)
        rounds.append(result)
        write_json(folder / "progress.json", rounds)
        print(f"REHOME_ROUND {number}: {''.join(classify(packet, indices))}; new-state transfer={result['round_success']}", flush=True)
    np.savez_compressed(folder / "endpoints.npz", source_packet=original, continuing_start=start,
                        fresh_target=fresh, final_packet=packet)
    offset = 2 * config["intervention_horizon"]
    write_json(folder / "result.json", {"case": case, "execution_pass": True, "ion_indices": indices,
        "source": source_record, "rounds": rounds, "final_ids": ids, "distinct_fresh_targets": len(seen) - 4,
        "new_state_transmitted": all(r["round_success"] for r in rounds),
        "nominal_schedule": [{"round": r["round"], "start": r["nominal_round_start"] + offset,
                              "end": r["nominal_round_end"] + offset} for r in rounds]})
    return 0


def frozen_manifest(summary):
    if "frozen_hashes_sha256" in summary:
        return summary["frozen_hashes_sha256"]
    # The original renewal harness used the primary manifest for frozen files.
    pairs = [(Path(name).name, digest) for name, digest in summary["hashes_sha256"].items()
             if not name.startswith("upstream/")]
    if not pairs or len({name for name, _ in pairs}) != len(pairs):
        raise ValueError("Ambiguous or empty legacy frozen manifest")
    return dict(pairs)


def verify_source_run(path, config, analyze):
    summary = json.loads((path / "summary.json").read_text())
    required = ("all_execution_valid", "source_clean_after", "inputs_unchanged", "files_unchanged", "frozen_files_unchanged")
    if not all(summary.get(k) for k in required) or any(config[k] != summary["config"][k] for k in SHARED):
        raise RuntimeError("Invalid source run or changed shared parameters")
    frozen = frozen_manifest(summary)
    if {p.name for p in (path / "frozen").iterdir()} != set(frozen) or not all(file_hash(path / "frozen" / name) == value for name, value in frozen.items()):
        raise RuntimeError("Source frozen files changed")
    for name in ("run_memory_probe.py", "run_renewal.py", "run_group_transfer.py", "run_onward_transfer.py", "memory_metrics.py"):
        key = "scripts/" + name
        if file_hash(ROOT / key) != summary["hashes_sha256"][key]:
            raise RuntimeError("Native simulation helper differs from source run")
    audit = analyze(path)
    if not audit["all_array_checks_pass"] or not audit["input_hashes_valid"]:
        raise RuntimeError("Source re-audit failed")
    if "predecessor_audit_sha256" in summary and file_hash(path / "predecessor_audit.json") != summary["predecessor_audit_sha256"]:
        raise RuntimeError("Source predecessor audit changed")
    return summary, audit


def freeze_inputs(run, config):
    from analyze_erasure_rescue import analyze as audit_erasure
    from analyze_renewal import analyze as audit_renewal
    previous, ordinary = [(ROOT / config[key]).resolve() for key in ("input_run", "ordinary_run")]
    if not all(p.is_relative_to(ROOT / "runs") for p in (previous, ordinary)):
        raise ValueError("Sources must be exploration runs")
    es, ea = verify_source_run(previous, config, audit_erasure)
    os, oa = verify_source_run(ordinary, config, audit_renewal)
    if any(config[k] != es["config"][k] for k in ("continuing_rounds", "intervention_horizon")):
        raise RuntimeError("Changed continuation timing")
    if file_hash(ordinary / "summary.json") != es["inputs"]["previous_summary.json"]["sha256"]:
        raise RuntimeError("Ordinary source is not the original renewal predecessor")
    if file_hash(previous / "inputs/references.npz") != file_hash(ordinary / "inputs/references.npz"):
        raise RuntimeError("Different reference preparations")
    write_json(run / "predecessor_audit.json", {"erasure": ea, "ordinary": oa})
    paths = {"erasure_summary.json": previous / "summary.json", "ordinary_summary.json": ordinary / "summary.json"}
    for name in ("references.npz", "reference.json", "e_prefix.json", "m_prefix.json"):
        paths[name] = previous / "inputs" / name
    for old in ("e", "m"):
        for kind in ("overwrite", "sham"):
            key = old + "_" + kind
            folder = previous / key
            result = json.loads((folder / "result.json").read_text())
            if result["case"]["state"] != old.upper() or result["case"]["intervention"] != kind or result["case"].get("fine", False):
                raise RuntimeError("Wrong old-state source case")
            changed = arrays(folder / "intervention/endpoints.npz")["after_2"]
            if not np.array_equal(changed, arrays(folder / "endpoints.npz")["continuing_start"]):
                raise RuntimeError("Historical assay did not use this exact packet")
            for ext in ("npz", "json"):
                paths[key + "." + ext] = folder / "intervention" / ("endpoints.npz" if ext == "npz" else "result.json")
                paths["historical_" + key + "." + ext] = folder / ("endpoints.npz" if ext == "npz" else "result.json")
        folder = ordinary / (old + "_ordinary") / "round_01"
        result = json.loads((folder / "result.json").read_text())
        if not result["round_success"] or set(result["incoming_ids"]) & set(result["outgoing_ids"]):
            raise RuntimeError("Ordinary first replacement was not successful")
        for ext in ("npz", "json"):
            paths[old + "_ordinary." + ext] = folder / ("endpoints.npz" if ext == "npz" else "result.json")
    inputs = run / "inputs"
    inputs.mkdir()
    manifest = {}
    for name, source in paths.items():
        digest = file_hash(source)
        (inputs / name).write_bytes(source.read_bytes())
        if file_hash(source) != digest or file_hash(inputs / name) != digest:
            raise RuntimeError("Input changed while copied")
        manifest[name] = {"source": str(source), "sha256": digest}
    write_json(inputs / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/rehoming_v1.json")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        spec = json.loads(args.worker.read_text())
        return branch_worker(args.worker.parent, spec["config"], spec["case"], Path(spec["inputs"]))
    validate_config(json.loads(args.config.read_text()))
    helpers = ["bounded_extension.py", "run_renewal.py", "run_group_transfer.py", "run_onward_transfer.py",
        "run_memory_probe.py", "memory_metrics.py", "run_pilot.py", "analyze_renewal.py",
        "analyze_group_transfer.py", "analyze_erasure_rescue.py", "analyze_rehoming.py", "test_rehoming.py"]
    return run_bounded(args.config.resolve(), Path(__file__).resolve(), ROOT / "REHOMING_PROTOCOL.md",
        helpers, freeze_inputs, "rehoming", "Alternative-state relay from exact prior overwritten checkpoints")


if __name__ == "__main__":
    raise SystemExit(main())
