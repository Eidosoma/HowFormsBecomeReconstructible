"""One learned BITSEY cell contacting one independently initialized recipient."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
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
from run_memory_probe import Experiment, array_hash, write_json
from run_pilot import ROOT, SOURCE, REVISION, source_check


def donor_source(learned_state, history):
    origin = opposite(learned_state).lower()
    if history == "alone":
        return None
    if history in ("learned", "blocked"):
        return origin + "_pulse"
    if history == "origin":
        return origin + "_naive"
    if history == "same_state":
        return learned_state.lower() + "_naive"
    raise ValueError(f"Unknown history: {history}")


def assemble_contact(recipient, donor=None):
    recipient = np.asarray(recipient)
    if recipient.ndim != 2 or recipient.shape[1] != 1:
        raise ValueError("Expected exactly one fresh recipient")
    if donor is None:
        return recipient.copy()
    donor = np.asarray(donor)
    if donor.shape != recipient.shape:
        raise ValueError("Expected exactly one full-state donor")
    return np.concatenate((recipient, donor), axis=1)


def retained_label(written_label, holds, shadow_label, fraction):
    return written_label in ("E", "M") and shadow_label == written_label and all(
        hold["recipient_label"] == written_label
        and hold["late_label_fractions"][written_label] >= fraction for hold in holds
    )


def experiment_worker(folder, config, case, inputs):
    with np.load(inputs / "references.npz", allow_pickle=False) as refs:
        prepared, later = refs["prepared"], refs["later"]
    expected_indices = json.loads((inputs / "reference.json").read_text())["ion_indices"]
    learned, history = case["learned_state"], case["history"]
    initial_label = opposite(learned)
    label_index = {"E": 0, "M": 1}
    recipient = prepared[:, label_index[initial_label], None].copy()
    origin = donor_source(learned, history)
    donor = None
    if origin is not None:
        with np.load(inputs / f"{origin}.npz", allow_pickle=False) as saved:
            donor = saved["checkpoint"].copy()
        metadata = json.loads((inputs / f"{origin}.json").read_text())
        if not metadata["execution_pass"] or metadata["ion_indices"] != expected_indices:
            raise RuntimeError("Invalid donor provenance")
        if history in ("learned", "blocked") and not metadata["donor_independent_acquired_recoverable_state"]:
            raise RuntimeError("Donor did not pass the original acquired-memory test")
        expected_donor = initial_label if history == "origin" else learned
        if classify(donor, expected_indices).tolist() != [expected_donor]:
            raise RuntimeError("Donor input has unexpected label")
    initial = assemble_contact(recipient, donor)
    active = history not in ("alone", "blocked")
    exp = Experiment(folder, config, fine=case.get("fine", False))
    setup = exp.build(initial.shape[1], initial, active)
    if exp.indices != expected_indices or classify(recipient, exp.indices).tolist() != [initial_label]:
        raise RuntimeError("Invalid fresh recipient/index mapping")
    scales = np.abs(later[exp.reg, 0] - later[exp.reg, 1])
    contact, contact_record = exp.phase("contact", config["contact_horizon"])
    removal_setup = exp.build(1, contact[:, :1].copy(), False)
    held, hold_1 = exp.phase("retention_1", config["retention_horizons"][0])
    checkpoint, hold_2 = exp.phase("retention_2", config["retention_horizons"][1])
    before = hold_2["recipient_label"]
    target_label = opposite(before if before in ("E", "M") else initial_label)
    perturbed = perturb_recipient(checkpoint, later[:, label_index[target_label]], exp.reg,
                                  config["perturbation_fraction"])
    shadow_setup = exp.build(1, checkpoint, False)
    shadow, shadow_record = exp.phase("shadow", config["recovery_horizon"])
    challenge_setup = exp.build(1, perturbed, False)
    challenged, challenge_record = exp.phase("challenge", config["recovery_horizon"])
    if shadow_setup["environment_hash"] != challenge_setup["environment_hash"]:
        raise RuntimeError("Fork environments differ")
    d0 = regulatory_distance(perturbed[exp.reg, 0], checkpoint[exp.reg, 0], scales)
    dfinal = regulatory_distance(challenged[exp.reg, 0], shadow[exp.reg, 0], scales)
    recovery = recovery_decision(d0, dfinal, before, shadow_record["recipient_label"],
                                 challenge_record["recipient_label"], config)
    written_label = contact_record["recipient_label"]
    switched = written_label == learned
    retained = retained_label(written_label, (hold_1, hold_2), shadow_record["recipient_label"],
                              config["late_label_fraction"])
    np.savez_compressed(folder / "endpoints.npz", initial=initial, contact=contact, retained_1=held,
                        checkpoint=checkpoint, perturbed=perturbed, shadow=shadow, challenged=challenged,
                        regulator_scales=scales)
    drift = np.abs(checkpoint[:, 0] - held[:, 0])
    result = {
        "case": case, "execution_pass": True, "ion_indices": exp.indices,
        "initial_label": initial_label, "donor_source": origin,
        "recipient_start_hash": array_hash(recipient),
        "donor_start_hash": None if donor is None else array_hash(donor),
        "contact_setup": setup, "removal_setup": removal_setup,
        "shadow_setup": shadow_setup, "challenge_setup": challenge_setup,
        "donor_contact_label": None if donor is None else contact_record["all_labels"][1],
        "donor_kept_initial_label": None if donor is None else bool(
            contact_record["all_labels"][1] == classify(donor, exp.indices)[0]),
        "contact_label": written_label, "recipient_switched_to_learned_state": bool(switched),
        "retained_contact_label": bool(retained), "recovery": recovery,
        "one_hop_acquired_state_propagation": bool(history == "learned" and switched and retained and recovery["recovered"]),
        "control_kept_initial_label": all(record["recipient_label"] == initial_label for record in exp.audits)
            if history in ("alone", "blocked", "origin") else None,
        "retention_drift": {name: float(drift[index]) for name, index in exp.indices.items()},
        "integrator": {key: getattr(exp.p, key) for key in ("time_step", "sim_integ_max_delt_cc", "sim_integ_max_delt_Vm", "use_implicit")},
        "audits": exp.audits,
        "scope": "One additional contact, finite-horizon regulatory retention/recovery; no renewal or PH",
    }
    write_json(folder / "result.json", result)
    return 0  # Scientifically negative results are not execution failures.


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze_inputs(run_dir, config):
    previous = (ROOT / config["input_run"]).resolve()
    if not previous.is_relative_to(ROOT / "runs"):
        raise ValueError("Input run must be inside this exploration's runs directory")
    summary = json.loads((previous / "summary.json").read_text())
    if not summary["all_execution_valid"] or not summary["source_clean_after"] or summary["revision"] != REVISION:
        raise RuntimeError("Prior experiment did not finish validly at the pinned revision")
    inputs = run_dir / "inputs"
    inputs.mkdir()
    paths = {"previous_summary.json": previous / "summary.json",
             "references.npz": previous / "reference" / "references.npz",
             "reference.json": previous / "reference" / "result.json"}
    for name in ("e_naive", "m_naive", "e_pulse", "m_pulse"):
        paths[f"{name}.npz"] = previous / name / "endpoints.npz"
        paths[f"{name}.json"] = previous / name / "result.json"
    manifest = {}
    for name, path in paths.items():
        (inputs / name).write_bytes(path.read_bytes())
        digest = file_hash(inputs / name)
        if digest != file_hash(path):
            raise RuntimeError("Input changed during copy")
        manifest[name] = {"source": str(path), "sha256": digest}
    write_json(inputs / "manifest.json", manifest)
    return manifest


def run_worker(case, run_dir, config, deadline, env):
    record = {"id": case["id"], "execution_pass": False}
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return dict(record, status="not_launched_budget")
    folder = run_dir / case["id"]
    folder.mkdir()
    write_json(folder / "spec.json", {"case": case, "config": config, "inputs": str(run_dir / "inputs")})
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", str(folder / "spec.json")]
    began = time.monotonic()
    print(f"Starting {case['id']}", flush=True)
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
    if config["revision"] != REVISION or not 1 <= config["workers"] <= 2:
        raise ValueError("Unexpected revision/concurrency")
    if not 0 < config["worker_timeout_seconds"] <= 900 or not 0 < config["total_budget_seconds"] <= 3600:
        raise ValueError("Exceeds runtime limits")
    names = [case["id"] for case in config["cases"]]
    if len(names) != len(set(names)) or any(Path(name).name != name or name in (".", "..") for name in names):
        raise ValueError("Invalid/duplicate case IDs")
    source_check()
    (ROOT / "runs").mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = Path(tempfile.mkdtemp(prefix=f"onward-transfer-{stamp}-", dir=ROOT / "runs"))
    inputs = freeze_inputs(run_dir, config)
    frozen = run_dir / "frozen"
    frozen.mkdir()
    files = [Path(__file__).resolve(), config_path, ROOT / "ONWARD_TRANSFER_PROTOCOL.md", ROOT / "requirements-smoke.txt"]
    files += [ROOT / "scripts" / name for name in ("run_memory_probe.py", "memory_metrics.py", "run_pilot.py")]
    for path in files:
        (frozen / path.name).write_bytes(path.read_bytes())
    native = subprocess.check_output(["git", "-C", str(SOURCE), "ls-files", "*.py"], text=True).splitlines()
    files += [SOURCE / name for name in native]
    hashes = {str(path.relative_to(ROOT)): file_hash(path) for path in files}
    summary = {"started_utc": stamp, "revision": REVISION, "python": sys.version,
               "packages": {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "matplotlib")},
               "hashes_sha256": hashes, "inputs": inputs, "config": config, "cases": [],
               "scope": "New one-hop transfer experiment, not paper reproduction or PH"}
    write_json(run_dir / "summary.json", summary)
    env = os.environ.copy()
    env.update(MPLBACKEND="Agg", MPLCONFIGDIR=str(ROOT / ".cache" / "matplotlib"), XDG_CACHE_HOME=str(ROOT / ".cache"),
               PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1",
               MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    began = time.monotonic()
    deadline = began + config["total_budget_seconds"]
    print(f"Run artifacts: {run_dir}", flush=True)
    with ThreadPoolExecutor(max_workers=config["workers"]) as pool:
        pending = [pool.submit(run_worker, case, run_dir, config, deadline, env) for case in config["cases"]]
        for future in as_completed(pending):
            summary["cases"].append(future.result())
            write_json(run_dir / "summary.json", summary)
    source_check()
    inputs_unchanged = all(file_hash(Path(item["source"])) == item["sha256"] == file_hash(run_dir / "inputs" / name)
                           for name, item in inputs.items())
    files_unchanged = all(file_hash(ROOT / path) == digest for path, digest in hashes.items())
    summary.update(elapsed_seconds=time.monotonic() - began, source_clean_after=True,
                   inputs_unchanged=inputs_unchanged, files_unchanged=files_unchanged,
                   all_execution_valid=inputs_unchanged and files_unchanged
                       and all(record["execution_pass"] for record in summary["cases"]))
    write_json(run_dir / "summary.json", summary)
    print(f"Summary: {run_dir / 'summary.json'}", flush=True)
    return 0 if summary["all_execution_valid"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "onward_transfer_v1.json")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        spec = json.loads(args.worker.read_text())
        return experiment_worker(args.worker.parent, spec["config"], spec["case"], Path(spec["inputs"]))
    return run_suite(args.config.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
