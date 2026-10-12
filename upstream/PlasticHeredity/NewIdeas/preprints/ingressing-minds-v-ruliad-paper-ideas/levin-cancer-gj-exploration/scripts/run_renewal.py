"""Three-round two-cell relay with complete donor replacement and no reseeding."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import numpy as np

from memory_metrics import REGULATORS, classify, opposite, perturb_recipient, regulatory_distance, recovery_decision
from run_group_transfer import assemble_group, donor_qualified
from run_memory_probe import Experiment, array_hash, write_json
from run_onward_transfer import file_hash, retained_label
from run_pilot import ROOT, SOURCE, REVISION, source_check


def founder_names(case):
    if case["history"] == "ordinary":
        stem = case["state"].lower() + "_naive"
    elif case["history"] in ("learned", "blocked"):
        stem = opposite(case["state"]).lower() + "_pulse"
    else:
        raise ValueError("Unknown founder history")
    return [f"{stem}_{i:02}" for i in (1, 2)]


def carry_donors(contact):
    if contact.ndim != 2 or contact.shape[1] != 3:
        raise ValueError("Expected one target and two donors")
    return contact[:, 1:].copy()


def replace_packet(seen_ids, new_ids, children):
    if len(new_ids) != 2 or len(set(new_ids)) != 2 or set(new_ids) & set(seen_ids):
        raise ValueError("Replacement must use two entirely new cell IDs")
    if len(children) != 2 or any(child.ndim != 2 or child.shape[1] != 1 for child in children):
        raise ValueError("Replacement needs two separate one-cell checkpoints")
    return np.concatenate(children, axis=1)


def round_worker(folder, config, case, incoming, incoming_ids, seen_ids, fresh, later, indices, number):
    exp = Experiment(folder, config, fine=case.get("fine", False))
    active = case["history"] != "blocked"
    setup = []

    def build(state, connected=False):
        record = exp.build(state.shape[1], state, connected)
        if exp.indices != indices:
            raise RuntimeError("Ion indexing changed")
        record["edges_list"] = [[int(edge["from"]), int(edge["to"])] for edge in exp.sim.GJ_connects]
        setup.append(record)
        return record

    first_initial = assemble_group(fresh, [incoming[:, :1], incoming[:, 1:]])
    build(first_initial, active)
    contact_1, write_1 = exp.phase("write_1", config["contact_horizon"])
    used_donors = carry_donors(contact_1)
    second_initial = assemble_group(fresh, [used_donors[:, :1], used_donors[:, 1:]])
    if not np.array_equal(second_initial[:, 1:], contact_1[:, 1:]):
        raise RuntimeError("Donors were reset between the two writes")
    build(second_initial, active)
    contact_2, write_2 = exp.phase("write_2", config["contact_horizon"])
    build(contact_1[:, :1])
    waited, wait_record = exp.phase("wait_1", config["contact_horizon"])
    children = [waited, contact_2[:, :1].copy()]
    holds, held_first, checkpoints = [], [], []
    for index, child in enumerate(children, 1):
        build(child)
        held, hold_1 = exp.phase(f"child_{index}_hold_1", config["retention_horizons"][0])
        checkpoint, hold_2 = exp.phase(f"child_{index}_hold_2", config["retention_horizons"][1])
        holds.append((hold_1, hold_2))
        held_first.append(held)
        checkpoints.append(checkpoint)
    new_ids = [f"{case['id']}:round_{number:02}:child_{i}" for i in (1, 2)]
    outgoing = replace_packet(seen_ids, new_ids, checkpoints)
    outgoing_hash = array_hash(outgoing)
    scales = np.abs(later[exp.reg, 0] - later[exp.reg, 1])
    diagnostic_arrays, outcomes = [], []
    for index, (checkpoint, hold_records, write_record) in enumerate(zip(checkpoints, holds, (write_1, write_2)), 1):
        before = hold_records[-1]["recipient_label"]
        challenge_label = opposite(before if before in ("E", "M") else opposite(case["state"]))
        changed = perturb_recipient(checkpoint, later[:, {"E": 0, "M": 1}[challenge_label]], exp.reg, config["perturbation_fraction"])
        shadow_setup = build(checkpoint)
        shadow, shadow_record = exp.phase(f"child_{index}_shadow", config["recovery_horizon"])
        challenge_setup = build(changed)
        challenged, challenge_record = exp.phase(f"child_{index}_challenge", config["recovery_horizon"])
        if shadow_setup["environment_hash"] != challenge_setup["environment_hash"]:
            raise RuntimeError("Diagnostic environments differ")
        d0 = regulatory_distance(changed[exp.reg, 0], checkpoint[exp.reg, 0], scales)
        dfinal = regulatory_distance(challenged[exp.reg, 0], shadow[exp.reg, 0], scales)
        recovery = recovery_decision(d0, dfinal, before, shadow_record["recipient_label"], challenge_record["recipient_label"], config)
        written_label = write_record["recipient_label"]
        retained = retained_label(written_label, hold_records, shadow_record["recipient_label"], config["late_label_fraction"])
        wait_ok = index == 2 or (written_label in ("E", "M") and wait_record["recipient_label"] == written_label
                                  and wait_record["late_label_fractions"][written_label] >= config["late_label_fraction"])
        acquired = written_label == case["state"]
        outcomes.append({"id": new_ids[index - 1], "contact_label": written_label, "retained_label": before,
                         "acquired_desired_state": acquired, "wait_preserved_label": bool(wait_ok),
                         "retained_contact_label": retained, "recovery": recovery,
                         "durable_transfer": bool(acquired and wait_ok and retained and recovery["recovered"]),
                         "ion_hold_drift": float(np.max(np.abs(checkpoint[:4] - held_first[index - 1][:4])))})
        diagnostic_arrays.append((changed, shadow, challenged))
    if outgoing_hash != array_hash(outgoing):
        raise RuntimeError("Diagnostic branch modified the continuing packet")
    np.savez_compressed(folder / "endpoints.npz", incoming_packet=incoming, fresh_target=fresh,
                        first_initial=first_initial, second_initial=second_initial,
                        contact_1=contact_1, contact_2=contact_2, child_1_waited=waited,
                        held_first=np.concatenate(held_first, axis=1), outgoing_packet=outgoing,
                        perturbed_packet=np.concatenate([items[0] for items in diagnostic_arrays], axis=1),
                        shadow_packet=np.concatenate([items[1] for items in diagnostic_arrays], axis=1),
                        challenged_packet=np.concatenate([items[2] for items in diagnostic_arrays], axis=1), regulator_scales=scales)
    nominal_duration = 2 * config["contact_horizon"] + sum(config["retention_horizons"])
    result = {"round": number, "execution_pass": True, "ion_indices": indices,
              "incoming_ids": incoming_ids, "outgoing_ids": new_ids, "incoming_packet_hash": array_hash(incoming),
              "outgoing_packet_hash": outgoing_hash, "all_old_ids_removed": not bool(set(incoming_ids) & set(new_ids)),
              "target_start_hash": array_hash(fresh), "children": outcomes,
              "round_success": all(child["durable_transfer"] for child in outcomes),
              "write_1_donor_labels": write_1["all_labels"][1:], "write_2_donor_labels": write_2["all_labels"][1:],
              "nominal_round_start": (number - 1) * nominal_duration, "nominal_round_end": number * nominal_duration,
              "diagnostic_branches_enter_lineage": False, "setups": setup, "audits": exp.audits}
    write_json(folder / "result.json", result)
    return outgoing, new_ids, result


def lineage_worker(folder, config, case, inputs):
    with np.load(inputs / "references.npz", allow_pickle=False) as refs:
        prepared, later = refs["prepared"], refs["later"]
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    founders = []
    for name in founder_names(case):
        metadata = json.loads((inputs / f"{name}.json").read_text())
        if not donor_qualified(metadata) or metadata["ion_indices"] != indices:
            raise RuntimeError("Unqualified founder")
        with np.load(inputs / f"{name}.npz", allow_pickle=False) as saved:
            cell = saved["checkpoint"].copy()
        if classify(cell, indices).tolist() != [case["state"]]:
            raise RuntimeError("Founder label mismatch")
        founders.append(cell)
    packet = np.concatenate(founders, axis=1)
    ids = [f"{case['id']}:founder:{name}" for name in founder_names(case)]
    founder_ids = ids.copy()
    seen = set(ids)
    original = opposite(case["state"])
    fresh = prepared[:, {"E": 0, "M": 1}[original], None].copy()
    initial_packet = packet.copy()
    rounds = []
    for number in range(1, config["rounds"] + 1):
        round_dir = folder / f"round_{number:02}"
        round_dir.mkdir()
        packet, ids, result = round_worker(round_dir, config, case, packet, ids, seen, fresh, later, indices, number)
        seen.update(ids)
        if set(ids) & set(founder_ids):
            raise RuntimeError("An original founder survived replacement")
        rounds.append(result)
        write_json(folder / "progress.json", rounds)
        print(f"RELAY_ROUND {number}: {''.join(classify(packet, indices))}; success={result['round_success']}", flush=True)
    np.savez_compressed(folder / "endpoints.npz", founders=initial_packet, final_packet=packet, fresh_target=fresh)
    result = {"case": case, "execution_pass": True, "ion_indices": indices, "founder_ids": founder_ids,
              "final_ids": ids, "distinct_fresh_targets": len(seen) - len(founder_ids),
              "all_rounds_transmitted": all(row["round_success"] for row in rounds),
              "first_failed_round": next((row["round"] for row in rounds if not row["round_success"]), None),
              "rounds": rounds, "scope": "Finite externally scheduled carrier-state replacement; no autonomous cell reproduction"}
    write_json(folder / "result.json", result)
    return 0


def freeze_relay_inputs(run_dir, config):
    previous = (ROOT / config["input_run"]).resolve()
    if not previous.is_relative_to(ROOT / "runs"):
        raise ValueError("Input run must be inside the exploration runs directory")
    summary = json.loads((previous / "summary.json").read_text())
    if summary["revision"] != REVISION or not all(summary.get(key, False) for key in
        ("all_execution_valid", "bank_qualified", "source_clean_after", "inputs_unchanged", "files_unchanged", "bank_unchanged")):
        raise RuntimeError("Previous donor-group run is not valid")
    manifest = json.loads((previous / "bank_manifest.json").read_text())
    if file_hash(previous / "bank_manifest.json") != summary["bank_manifest_sha256"]:
        raise RuntimeError("Previous bank manifest changed")
    paths = {"previous_summary.json": previous / "summary.json", "previous_bank_manifest.json": previous / "bank_manifest.json",
             "references.npz": previous / "inputs" / "references.npz", "reference.json": previous / "inputs" / "reference.json"}
    for name in ("references.npz", "reference.json"):
        if file_hash(paths[name]) != summary["inputs"][name]["sha256"]:
            raise RuntimeError("Previous reference input changed")
    for case in config["cases"]:
        for name in founder_names(case):
            for filename, digest in manifest[name].items():
                if file_hash(previous / "bank" / name / filename) != digest:
                    raise RuntimeError("Previous bank donor changed")
            paths[f"{name}.npz"] = previous / "bank" / name / "endpoints.npz"
            paths[f"{name}.json"] = previous / "bank" / name / "result.json"
    inputs = run_dir / "inputs"
    inputs.mkdir()
    copied = {}
    for name, path in paths.items():
        (inputs / name).write_bytes(path.read_bytes())
        digest = file_hash(inputs / name)
        if digest != file_hash(path):
            raise RuntimeError("Input changed while copied")
        copied[name] = {"source": str(path), "sha256": digest}
    write_json(inputs / "manifest.json", copied)
    return copied


def run_worker(case, config, run_dir, deadline, env):
    record = {"id": case["id"], "execution_pass": False}
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return dict(record, status="not_launched_budget")
    folder = run_dir / case["id"]
    folder.mkdir()
    write_json(folder / "spec.json", {"case": case, "config": config, "inputs": str(run_dir / "inputs")})
    began = time.monotonic()
    print(f"Starting {case['id']}", flush=True)
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", str(folder / "spec.json")]
    with (folder / "stdout.log").open("x") as log:
        try:
            completed = subprocess.run(command, cwd=folder, env=env, stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=subprocess.STDOUT,
                                       timeout=min(remaining, config["worker_timeout_seconds"]))
            record.update(status="finished", returncode=completed.returncode)
        except subprocess.TimeoutExpired:
            record.update(status="timeout", returncode=None)
    record["elapsed_seconds"] = time.monotonic() - began
    if (folder / "result.json").exists():
        record["result"] = json.loads((folder / "result.json").read_text())
        record["execution_pass"] = record["returncode"] == 0 and record["result"]["execution_pass"]
    print(f"{case['id']}: {'VALID' if record['execution_pass'] else 'INVALID'} ({record['elapsed_seconds']:.1f}s)", flush=True)
    return record


def run_suite(config_path):
    config = json.loads(config_path.read_text())
    if config["revision"] != REVISION or config["packet_size"] != 2 or not 1 <= config["rounds"] <= 3:
        raise ValueError("Unexpected source, packet width, or round count")
    if not 1 <= config["workers"] <= 2 or not 0 < config["worker_timeout_seconds"] <= 900 or not 0 < config["total_budget_seconds"] <= 3600:
        raise ValueError("Exceeds concurrency/runtime bounds")
    names = [case["id"] for case in config["cases"]]
    if not names or len(names) != len(set(names)) or any(Path(name).name != name or name in (".", "..") for name in names):
        raise ValueError("Empty, duplicate or invalid case IDs")
    for case in config["cases"]:
        opposite(case["state"])
        founder_names(case)
    source_check()
    began = time.monotonic()
    deadline = began + config["total_budget_seconds"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (ROOT / "runs").mkdir(exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix=f"renewal-{stamp}-", dir=ROOT / "runs"))
    inputs = freeze_relay_inputs(run_dir, config)
    frozen = run_dir / "frozen"
    frozen.mkdir()
    files = [Path(__file__).resolve(), config_path, ROOT / "RENEWAL_PROTOCOL.md", ROOT / "requirements-smoke.txt"]
    files += [ROOT / "scripts" / name for name in ("run_group_transfer.py", "run_onward_transfer.py", "run_memory_probe.py", "memory_metrics.py", "run_pilot.py")]
    for path in files:
        (frozen / path.name).write_bytes(path.read_bytes())
    native = subprocess.check_output(["git", "-C", str(SOURCE), "ls-files", "*.py"], text=True).splitlines()
    files += [SOURCE / name for name in native]
    hashes = {str(path.relative_to(ROOT)): file_hash(path) for path in files}
    summary = {"started_utc": stamp, "revision": REVISION, "python": sys.version,
               "packages": {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "matplotlib")},
               "config": config, "inputs": inputs, "hashes_sha256": hashes, "cases": [],
               "scope": "Three externally scheduled full carrier-state replacements, not autonomous cell reproduction"}
    write_json(run_dir / "summary.json", summary)
    env = os.environ.copy()
    env.update(MPLBACKEND="Agg", MPLCONFIGDIR=str(ROOT / ".cache" / "matplotlib"), XDG_CACHE_HOME=str(ROOT / ".cache"),
               PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1",
               MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    print(f"Run artifacts: {run_dir}", flush=True)
    with ThreadPoolExecutor(max_workers=config["workers"]) as pool:
        pending = [pool.submit(run_worker, case, config, run_dir, deadline, env) for case in config["cases"]]
        for future in as_completed(pending):
            summary["cases"].append(future.result())
            write_json(run_dir / "summary.json", summary)
    source_check()
    input_ok = all(file_hash(Path(entry["source"])) == entry["sha256"] == file_hash(run_dir / "inputs" / name)
                   for name, entry in inputs.items())
    files_ok = all(file_hash(ROOT / path) == digest for path, digest in hashes.items())
    frozen_ok = all(file_hash(path) == hashes[next(name for name in hashes if not name.startswith("upstream/") and Path(name).name == path.name)]
                    for path in frozen.iterdir())
    summary.update(elapsed_seconds=time.monotonic() - began, source_clean_after=True,
                   inputs_unchanged=input_ok, files_unchanged=files_ok, frozen_files_unchanged=frozen_ok,
                   all_execution_valid=input_ok and files_ok and frozen_ok and len(summary["cases"]) == len(config["cases"])
                       and all(record["execution_pass"] for record in summary["cases"]))
    write_json(run_dir / "summary.json", summary)
    print(f"Summary: {run_dir / 'summary.json'}", flush=True)
    return 0 if summary["all_execution_valid"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "renewal_v1.json")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        spec = json.loads(args.worker.read_text())
        return lineage_worker(args.worker.parent, spec["config"], spec["case"], Path(spec["inputs"]))
    return run_suite(args.config.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
