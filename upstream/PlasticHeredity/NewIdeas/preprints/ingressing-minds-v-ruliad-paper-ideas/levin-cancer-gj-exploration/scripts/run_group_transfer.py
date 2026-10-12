"""Bounded donor-count test using separately prepared acquired-state donors."""

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
from run_memory_probe import Experiment, array_hash, experiment_worker as prepare_donor, write_json
from run_onward_transfer import donor_source, file_hash, freeze_inputs, retained_label
from run_pilot import ROOT, SOURCE, REVISION, source_check


def make_cases(config):
    counts, fine = config["donor_counts"], config["fine_counts"]
    if not counts or len(set(counts)) != len(counts) or any(type(n) is not int or not 1 <= n <= config["bank_size"] for n in counts):
        raise ValueError("Invalid donor counts")
    if len(set(fine)) != len(fine) or not set(fine).issubset(counts) or config["control_count"] not in counts:
        raise ValueError("Fine/control counts must be sampled baseline counts")
    cases = []
    for state in ("E", "M"):
        for n in counts:
            for history in ("learned", "same_state"):
                cases.append({"id": f"{state.lower()}_{history}_n{n}", "learned_state": state, "history": history, "donors": n})
        for history in ("blocked", "origin", "alone"):
            n = 0 if history == "alone" else config["control_count"]
            cases.append({"id": f"{state.lower()}_{history}_n{n}", "learned_state": state, "history": history, "donors": n})
        for n in fine:
            cases.append({"id": f"{state.lower()}_learned_n{n}_fine", "learned_state": state, "history": "learned", "donors": n, "fine": True})
    return cases


def make_bank_cases(config):
    return [{"id": f"{state.lower()}_{history}_{i:02}", "initial": state, "history": history}
            for state in ("E", "M") for history in ("pulse", "naive") for i in range(1, config["bank_size"] + 1)]


def donor_ids(case):
    source = donor_source(case["learned_state"], case["history"])
    if (source is None) != (case["donors"] == 0):
        raise ValueError("Only the alone condition has no donors")
    return [] if source is None else [f"{source}_{i:02}" for i in range(1, case["donors"] + 1)]


def assemble_group(recipient, donors):
    recipient = np.asarray(recipient)
    if recipient.ndim != 2 or recipient.shape[1] != 1:
        raise ValueError("Expected one independently initialized target")
    if any(np.shape(donor) != recipient.shape for donor in donors):
        raise ValueError("Each donor must be a separate one-cell full-state checkpoint")
    return np.concatenate([recipient, *donors], axis=1)


def group_worker(folder, config, case, run_dir):
    inputs = run_dir / "inputs"
    with np.load(inputs / "references.npz", allow_pickle=False) as refs:
        prepared, later = refs["prepared"], refs["later"]
    indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    original = opposite(case["learned_state"])
    recipient = prepared[:, {"E": 0, "M": 1}[original], None].copy()
    manifest = json.loads((run_dir / "bank_manifest.json").read_text())
    donors, provenance = [], []
    for name in donor_ids(case):
        bank = run_dir / "bank" / name
        if any(file_hash(bank / filename) != digest for filename, digest in manifest[name].items()):
            raise RuntimeError("Prepared donor changed after bank sealing")
        metadata = json.loads((bank / "result.json").read_text())
        if not donor_qualified(metadata) or metadata["ion_indices"] != indices:
            raise RuntimeError("Unqualified or incompatible donor")
        with np.load(bank / "endpoints.npz", allow_pickle=False) as saved:
            donor = saved["checkpoint"].copy()
        expected = original if case["history"] == "origin" else case["learned_state"]
        if classify(donor, indices).tolist() != [expected]:
            raise RuntimeError("Donor label mismatch")
        donors.append(donor)
        provenance.append({"id": name, "checkpoint_hash": array_hash(donor)})
    initial = assemble_group(recipient, donors)
    active = case["history"] not in ("blocked", "alone")
    exp = Experiment(folder, config, fine=case.get("fine", False))
    setup = exp.build(initial.shape[1], initial, active)
    if exp.indices != indices or classify(recipient, indices).tolist() != [original]:
        raise RuntimeError("Invalid fresh target or indices")
    edges = [(int(edge["from"]), int(edge["to"])) for edge in exp.sim.GJ_connects]
    if edges != [(0, i) for i in range(1, len(donors) + 1)]:
        raise RuntimeError("Not the prescribed target-centered star")
    scales = np.abs(later[exp.reg, 0] - later[exp.reg, 1])
    contact, contact_record = exp.phase("contact", config["contact_horizon"])
    removal_setup = exp.build(1, contact[:, :1].copy(), False)
    held, hold_1 = exp.phase("retention_1", config["retention_horizons"][0])
    checkpoint, hold_2 = exp.phase("retention_2", config["retention_horizons"][1])
    before = hold_2["recipient_label"]
    target = opposite(before if before in ("E", "M") else original)
    perturbed = perturb_recipient(checkpoint, later[:, {"E": 0, "M": 1}[target]], exp.reg, config["perturbation_fraction"])
    shadow_setup = exp.build(1, checkpoint, False)
    shadow, shadow_record = exp.phase("shadow", config["recovery_horizon"])
    challenge_setup = exp.build(1, perturbed, False)
    challenged, challenge_record = exp.phase("challenge", config["recovery_horizon"])
    if shadow_setup["environment_hash"] != challenge_setup["environment_hash"]:
        raise RuntimeError("Fork environments differ")
    d0 = regulatory_distance(perturbed[exp.reg, 0], checkpoint[exp.reg, 0], scales)
    dfinal = regulatory_distance(challenged[exp.reg, 0], shadow[exp.reg, 0], scales)
    recovery = recovery_decision(d0, dfinal, before, shadow_record["recipient_label"], challenge_record["recipient_label"], config)
    written = contact_record["recipient_label"]
    retained = retained_label(written, (hold_1, hold_2), shadow_record["recipient_label"], config["late_label_fraction"])
    transfer = bool(written == case["learned_state"] and retained and recovery["recovered"])
    np.savez_compressed(folder / "endpoints.npz", initial=initial, contact=contact, retained_1=held,
                        checkpoint=checkpoint, perturbed=perturbed, shadow=shadow, challenged=challenged, regulator_scales=scales)
    drift = np.abs(checkpoint[:, 0] - held[:, 0])
    result = {
        "case": case, "execution_pass": True, "ion_indices": indices, "initial_label": original,
        "donor_provenance": provenance, "recipient_start_hash": array_hash(recipient),
        "contact_setup": setup, "contact_edges": edges, "removal_setup": removal_setup,
        "shadow_setup": shadow_setup, "challenge_setup": challenge_setup,
        "contact_label": written, "donor_contact_labels": contact_record["all_labels"][1:],
        "all_donors_kept_initial_label": bool(np.array_equal(classify(initial, indices)[1:], classify(contact, indices)[1:])),
        "recipient_switched": bool(written == case["learned_state"]), "retained_contact_label": retained,
        "recovery": recovery, "durable_state_transfer": transfer,
        "acquired_state_onward_propagation": bool(case["history"] == "learned" and transfer),
        "control_kept_initial_label": all(audit["recipient_label"] == original for audit in exp.audits)
            if case["history"] in ("blocked", "origin", "alone") else None,
        "retention_drift": {name: float(drift[index]) for name, index in indices.items()},
        "integrator": {key: getattr(exp.p, key) for key in ("time_step", "sim_integ_max_delt_cc", "sim_integ_max_delt_Vm", "use_implicit")},
        "audits": exp.audits, "scope": "Donor-number effect on one onward contact; no renewal or PH",
    }
    write_json(folder / "result.json", result)
    return 0


def donor_qualified(result):
    if not result.get("execution_pass") or not result.get("expected_label_sequence"):
        return False
    if result["case"]["history"] == "pulse":
        return bool(result["donor_independent_acquired_recoverable_state"])
    return result["case"]["history"] == "naive" and result["retained_written_label"] and result["recovery"]["recovered"]


def run_worker(stage, case, config, run_dir, deadline, env):
    record = {"id": case["id"], "stage": stage, "execution_pass": False}
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return dict(record, status="not_launched_budget")
    folder = run_dir / stage / case["id"]
    folder.mkdir()
    write_json(folder / "spec.json", {"stage": stage, "case": case, "config": config, "run_dir": str(run_dir)})
    began = time.monotonic()
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", str(folder / "spec.json")]
    print(f"Starting {stage}/{case['id']}", flush=True)
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
        if stage == "bank":
            record["donor_qualified"] = donor_qualified(record["result"])
    print(f"{stage}/{case['id']}: {'VALID' if record['execution_pass'] else 'INVALID'} ({record['elapsed_seconds']:.1f}s)", flush=True)
    return record


def run_stage(stage, cases, config, run_dir, deadline, env, summary):
    with ThreadPoolExecutor(max_workers=config["workers"]) as pool:
        pending = [pool.submit(run_worker, stage, case, config, run_dir, deadline, env) for case in cases]
        for future in as_completed(pending):
            summary[stage].append(future.result())
            write_json(run_dir / "summary.json", summary)


def run_suite(config_path):
    config = json.loads(config_path.read_text())
    if config["revision"] != REVISION or not 1 <= config["workers"] <= 2 or not 1 <= config["bank_size"] <= 5:
        raise ValueError("Unexpected revision/concurrency/bank size")
    if not 0 < config["worker_timeout_seconds"] <= 900 or not 0 < config["total_budget_seconds"] <= 3600:
        raise ValueError("Exceeds runtime bounds")
    cases, bank_cases = make_cases(config), make_bank_cases(config)
    source_check()
    began = time.monotonic()
    deadline = began + config["total_budget_seconds"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (ROOT / "runs").mkdir(exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix=f"group-transfer-{stamp}-", dir=ROOT / "runs"))
    inputs = freeze_inputs(run_dir, config)
    # Existing memory adapter expects its reference metadata under this name.
    (run_dir / "inputs" / "result.json").write_bytes((run_dir / "inputs" / "reference.json").read_bytes())
    inputs["result.json"] = inputs["reference.json"].copy()
    write_json(run_dir / "inputs" / "manifest.json", inputs)
    previous = json.loads((run_dir / "inputs" / "previous_summary.json").read_text())
    bank_config = previous["config"].copy()
    for key in ("workers", "worker_timeout_seconds", "total_budget_seconds"):
        bank_config[key] = config[key]
    bank_config["cases"] = bank_cases
    frozen = run_dir / "frozen"
    frozen.mkdir()
    files = [Path(__file__).resolve(), config_path, ROOT / "GROUP_TRANSFER_PROTOCOL.md", ROOT / "requirements-smoke.txt"]
    files += [ROOT / "scripts" / name for name in ("run_onward_transfer.py", "run_memory_probe.py", "memory_metrics.py", "run_pilot.py")]
    for path in files:
        (frozen / path.name).write_bytes(path.read_bytes())
    write_json(frozen / "donor_preparation_config.json", bank_config)
    native = subprocess.check_output(["git", "-C", str(SOURCE), "ls-files", "*.py"], text=True).splitlines()
    files += [SOURCE / name for name in native]
    hashes = {str(path.relative_to(ROOT)): file_hash(path) for path in files}
    summary = {"started_utc": stamp, "revision": REVISION, "python": sys.version,
               "packages": {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "matplotlib")},
               "config": config, "bank_config": bank_config, "planned_bank": bank_cases, "planned_groups": cases,
               "hashes_sha256": hashes, "inputs": inputs, "bank": [], "groups": [],
               "scope": "New donor-number probe, not serial renewal or PH"}
    write_json(run_dir / "summary.json", summary)
    for stage in ("bank", "groups"):
        (run_dir / stage).mkdir()
    env = os.environ.copy()
    env.update(MPLBACKEND="Agg", MPLCONFIGDIR=str(ROOT / ".cache" / "matplotlib"), XDG_CACHE_HOME=str(ROOT / ".cache"),
               PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1",
               MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    print(f"Run artifacts: {run_dir}", flush=True)
    run_stage("bank", bank_cases, bank_config, run_dir, deadline, env, summary)
    summary["bank_qualified"] = len(summary["bank"]) == len(bank_cases) and all(
        record["execution_pass"] and record.get("donor_qualified", False) for record in summary["bank"])
    if not summary["bank_qualified"]:
        summary.update(all_execution_valid=False, groups_not_launched="donor preparation failed",
                       elapsed_seconds=time.monotonic() - began)
        write_json(run_dir / "summary.json", summary)
        print("Donor qualification failed; group tests not launched.", flush=True)
        return 1
    bank_manifest = {case["id"]: {name: file_hash(run_dir / "bank" / case["id"] / name)
                     for name in ("spec.json", "result.json", "endpoints.npz")} for case in bank_cases}
    write_json(run_dir / "bank_manifest.json", bank_manifest)
    summary["bank_manifest_sha256"] = file_hash(run_dir / "bank_manifest.json")
    write_json(run_dir / "summary.json", summary)
    run_stage("groups", cases, config, run_dir, deadline, env, summary)
    source_check()
    input_ok = all(file_hash(Path(item["source"])) == item["sha256"] == file_hash(run_dir / "inputs" / name)
                   for name, item in inputs.items())
    files_ok = all(file_hash(ROOT / path) == digest for path, digest in hashes.items())
    bank_ok = all(file_hash(run_dir / "bank" / case / name) == digest for case, entries in bank_manifest.items()
                  for name, digest in entries.items()) and file_hash(run_dir / "bank_manifest.json") == summary["bank_manifest_sha256"]
    summary.update(elapsed_seconds=time.monotonic() - began, source_clean_after=True,
                   inputs_unchanged=input_ok, files_unchanged=files_ok, bank_unchanged=bank_ok,
                   all_execution_valid=input_ok and files_ok and bank_ok and len(summary["groups"]) == len(cases)
                       and all(record["execution_pass"] for record in summary["groups"]))
    write_json(run_dir / "summary.json", summary)
    print(f"Summary: {run_dir / 'summary.json'}", flush=True)
    return 0 if summary["all_execution_valid"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "group_transfer_v1.json")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        spec = json.loads(args.worker.read_text())
        run_dir = Path(spec["run_dir"])
        if spec["stage"] == "bank":
            return prepare_donor(args.worker.parent, spec["config"], spec["case"], run_dir / "inputs")
        return group_worker(args.worker.parent, spec["config"], spec["case"], run_dir)
    return run_suite(args.config.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
