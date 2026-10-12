"""Controlled write/disconnect/challenge extension of pinned BITSEY equations."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time

import numpy as np

from memory_metrics import REGULATORS, classify, opposite, perturb_recipient, regulatory_distance, recovery_decision
from run_pilot import ROOT, SOURCE, REVISION, source_check


def write_json(path, value):
    # Readers can safely inspect progress while a worker finishes a phase.
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def array_hash(value):
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


class Experiment:
    def __init__(self, folder, config, fine=False):
        self.folder, self.config, self.audits = folder, config, []
        sys.path[:0] = [str(SOURCE / "cancer_GJ_sims"), str(SOURCE)]
        import sim
        self.sim = sim
        saved_args = sys.argv
        sys.argv = ["zombie.py", "metas_cases", "1", "1", "25", "0", "0", "0"]
        try:
            spec = importlib.util.spec_from_file_location("bitsey_zombie", SOURCE / "cancer_GJ_sims" / "zombie.py")
            self.z = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.z)
        finally:
            sys.argv = saved_args
        self.p = sim.Params()
        self.p.no_dumps = True
        self.p.time_step = .00005 if fine else .0001
        self.p.sim_integ_max_delt_cc = .0005 if fine else .001
        self.p.sim_integ_max_delt_Vm = .00005 if fine else .0001
        if self.z.GRN.ITERATE or self.z.GRN.MIR200_TGT >= 0 or self.z.GRN.Snail_input_conc != 72:
            raise RuntimeError("Unexpected GRN approximation, forcing, or Snail parameter")

    def build(self, count, state=None, active=False):
        self.z.setup_basic_network(self.p, 0, 1, 1, count)
        self.z.GRN.seed3D_inputs(self.sim.cc_cells)
        if count > 1:
            self.sim.GJ_connects["from"] = 0
            self.sim.GJ_connects["to"] = range(1, count)
        self.z.GRN.set_GJdiff(self.config["write_kd"] if active else 0)
        if not active:
            self.sim.GJ_diffusion.fill(0)
        if state is not None:
            if state.shape != self.sim.cc_cells.shape:
                raise RuntimeError("Checkpoint shape mismatch")
            np.copyto(self.sim.cc_cells, state)
            if not np.array_equal(state, self.sim.cc_cells):
                raise RuntimeError("Rebuild changed the copied cell state")
        if len(self.sim.GJ_connects) != count - 1:
            raise RuntimeError("Unexpected star/isolated-cell topology")
        if self.sim.IC_gates or self.sim.GJ_scale_gates:
            raise RuntimeError("Unexpected voltage or expression gates")
        if count == 1 and (len(self.sim.GJ_connects) or self.z.GRN.miR200_free_GJ_diffusion_val != 0):
            raise RuntimeError("Donor-free phase still has a communication path")
        if not active and np.any(self.sim.GJ_diffusion):
            raise RuntimeError("Blocked transport is not fully zero")
        self.indices = dict(self.sim.ion_i)
        self.reg = [self.indices[name] for name in REGULATORS]
        return {"cells": count, "edges": len(self.sim.GJ_connects), "active": active,
                "miRNA_kd": self.z.GRN.miR200_free_GJ_diffusion_val,
                "state_hash_before_derived_refresh": array_hash(self.sim.cc_cells),
                "environment_hash": array_hash(self.sim.cc_env)}

    def refresh(self):
        # Source uses this same algebraic routine on every slope evaluation.
        # It recomputes derived species while preserving the primary totals.
        primary = self.sim.cc_cells[:8].copy()
        self.z.GRN.compute_bound_complex_concs_simple(self.sim.cc_cells, self.z.GRN.x0, 0)
        if not np.array_equal(primary, self.sim.cc_cells[:8]):
            raise RuntimeError("Derived-species refresh changed primary variables")

    def phase(self, name, horizon):
        self.refresh()
        initial = self.sim.cc_cells.copy()
        began, cpu = time.monotonic(), time.process_time()
        times, shots = self.sim.sim(horizon)
        elapsed, cpu = time.monotonic() - began, time.process_time() - cpu
        samples = np.asarray(shots)
        raw_final = self.sim.cc_cells.copy()
        self.refresh()
        final = self.sim.cc_cells.copy()
        finite = bool(all(np.isfinite(value).all() for value in (initial, samples, raw_final, final)))
        minimum = float(min(value.min() for value in (initial, samples, raw_final, final))) if finite else None
        if not finite or minimum < 0:
            raise RuntimeError(f"{name}: nonfinite/negative concentrations")
        if not np.all(final[self.indices["snail"]] == 72):
            raise RuntimeError("Snail changed unexpectedly")
        labels = classify(final, self.indices)
        native_labels = np.array([self.z.GRN.state_char(final[:, cell]) for cell in range(final.shape[1])])
        if not np.array_equal(labels, native_labels):
            raise RuntimeError("Independent and native label rules disagree")
        snapshot_labels = classify(samples, self.indices)[:, 0]
        late = snapshot_labels[np.asarray(times) >= horizon * .75]
        if not len(late):
            raise RuntimeError("No late-window samples")
        record = {
            "phase": name, "requested_horizon": horizon, "cells": final.shape[1],
            "wall_seconds": elapsed, "cpu_seconds": cpu, "samples": len(times),
            "last_sample_time": float(times[-1]), "finite": finite, "nonnegative": minimum >= 0,
            "minimum_concentration": minimum, "recipient_label": str(labels[0]),
            "all_labels": "".join(labels),
            "late_label_fractions": {label: float(np.mean(late == label)) for label in ("E", "M", "X")},
            "recipient_label_transitions_in_returned_samples": int(np.count_nonzero(snapshot_labels[1:] != snapshot_labels[:-1])),
            "last_snapshot_raw_final_max_abs": float(np.max(np.abs(samples[-1] - raw_final))),
            "derived_refresh_max_abs": float(np.max(np.abs(final - raw_final))),
            "recipient_regulators": {name: float(final[self.indices[name], 0]) for name in REGULATORS},
            "recipient_vm": float(self.sim.compute_Vm(final)[0]),
            "graph_edges": len(self.sim.GJ_connects),
            "miRNA_kd": self.z.GRN.miR200_free_GJ_diffusion_val,
        }
        np.savez_compressed(self.folder / f"{name}.npz", initial=initial, times=np.asarray(times),
                            concentrations=samples, raw_final=raw_final, final=final)
        self.audits.append(record)
        write_json(self.folder / "progress.json", self.audits)
        print("MEMORY_PHASE " + json.dumps(record), flush=True)
        return final, record


def reference_worker(folder, config):
    exp = Experiment(folder, config)
    exp.build(2)
    exp.z.GRN.set_cell_state(exp.sim.cc_cells, 0, False)
    exp.z.GRN.set_cell_state(exp.sim.cc_cells, 1, True)
    prepared, _ = exp.phase("reference_preparation", config["reference_preparation"])
    later, _ = exp.phase("reference_later", config["reference_continuation"])
    if list(classify(prepared, exp.indices)) != ["E", "M"] or list(classify(later, exp.indices)) != ["E", "M"]:
        raise RuntimeError("Reference preparation did not produce E/M anchors")
    np.savez_compressed(folder / "references.npz", prepared=prepared, later=later)
    write_json(folder / "result.json", {"execution_pass": True, "ion_indices": exp.indices,
               "audits": exp.audits, "prepared_hash": array_hash(prepared), "later_hash": array_hash(later)})
    return 0


def experiment_worker(folder, config, case, reference_dir):
    references = np.load(reference_dir / "references.npz", allow_pickle=False)
    prepared, later = references["prepared"], references["later"]
    reference_metadata = json.loads((reference_dir / "result.json").read_text())
    exp = Experiment(folder, config, fine=case.get("fine", False))
    initial_label, history = case["initial"], case["history"]
    donor_label = initial_label if history == "sham" else opposite(initial_label)
    label_index = {"E": 0, "M": 1}
    count = 1 if history == "naive" else config["donors"] + 1
    initial = np.repeat(prepared[:, label_index[donor_label], None], count, axis=1)
    initial[:, 0] = prepared[:, label_index[initial_label]]
    active = history not in ("naive", "blocked")
    setup = exp.build(count, initial, active)
    if exp.indices != reference_metadata["ion_indices"]:
        raise RuntimeError("Reference and experiment ion indices differ")
    regulator_scales = np.abs(later[exp.reg, 0] - later[exp.reg, 1])
    if np.any(regulator_scales <= 0):
        raise RuntimeError("Degenerate regulator reference separation")
    recipient_start_hash = array_hash(initial[:, 0])
    written, write_record = exp.phase("write", config["write_horizon"])

    continued = history == "continuous"
    retained_system = written.copy() if continued else written[:, :1].copy()
    handling = exp.build(retained_system.shape[1], retained_system, continued)
    retained_1, retention_1 = exp.phase("retention_1", config["retention_horizons"][0])
    checkpoint, retention_2 = exp.phase("retention_2", config["retention_horizons"][1])
    label_before = retention_2["recipient_label"]
    challenge_target = opposite(label_before if label_before in ("E", "M") else initial_label)
    changed = perturb_recipient(checkpoint, later[:, label_index[challenge_target]], exp.reg,
                                config["perturbation_fraction"])
    d0 = regulatory_distance(changed[exp.reg, 0], checkpoint[exp.reg, 0], regulator_scales)
    untouched = np.ones_like(checkpoint, dtype=bool)
    untouched[exp.reg, 0] = False
    if not np.array_equal(changed[untouched], checkpoint[untouched]):
        raise RuntimeError("Impulse changed donors or non-regulatory state")

    # Separate rebuilds avoid hidden simulator/context carryover between forks.
    shadow_setup = exp.build(checkpoint.shape[1], checkpoint, continued)
    shadow, shadow_record = exp.phase("shadow", config["recovery_horizon"])
    challenge_setup = exp.build(changed.shape[1], changed, continued)
    challenged, challenge_record = exp.phase("challenge", config["recovery_horizon"])
    if shadow_setup["environment_hash"] != challenge_setup["environment_hash"]:
        raise RuntimeError("Shadow and challenge environments differ")
    distance = regulatory_distance(challenged[exp.reg, 0], shadow[exp.reg, 0], regulator_scales)
    recovery = recovery_decision(d0, distance, label_before, shadow_record["recipient_label"],
                                 challenge_record["recipient_label"], config)
    drift = np.abs(checkpoint[:, 0] - retained_1[:, 0])
    shadow_difference = np.abs(challenged[:, 0] - shadow[:, 0])
    written_label = write_record["recipient_label"]
    retained = written_label in ("E", "M") and all(
        record["recipient_label"] == written_label
        and record["late_label_fractions"][written_label] >= config["late_label_fraction"]
        for record in (retention_1, retention_2)
    ) and shadow_record["recipient_label"] == written_label
    acquired = history in ("pulse", "continuous") and written_label == donor_label != initial_label
    expected = donor_label if history in ("pulse", "continuous") else initial_label
    expected_sequence = all(record["recipient_label"] == expected for record in exp.audits)
    # Descriptive distance trajectory; endpoint gate above uses live terminal
    # states at the same requested horizon, not these interpolated snapshots.
    with np.load(folder / "shadow.npz", allow_pickle=False) as shadow_file, np.load(folder / "challenge.npz", allow_pickle=False) as challenge_file:
        common_times = challenge_file["times"]
        valid = (common_times >= shadow_file["times"][0]) & (common_times <= shadow_file["times"][-1])
        common_times = common_times[valid]
        shadow_reg = np.stack([np.interp(common_times, shadow_file["times"], shadow_file["concentrations"][:, index, 0]) for index in exp.reg], axis=1)
        actual_reg = challenge_file["concentrations"][valid][:, exp.reg, 0]
        trajectory_distance = np.max(np.abs(actual_reg - shadow_reg) / regulator_scales, axis=1)
        np.savez_compressed(folder / "recovery_distance.npz", times=common_times, normalized_distance=trajectory_distance)
    np.savez_compressed(folder / "endpoints.npz", initial=initial, written=written, retained_1=retained_1,
                        checkpoint=checkpoint, perturbed=changed, shadow=shadow, challenged=challenged,
                        regulator_scales=regulator_scales)
    result = {
        "case": case, "execution_pass": True, "ion_indices": exp.indices,
        "recipient_start_hash": recipient_start_hash, "reference_prepared_hash": array_hash(prepared),
        "exposure_setup": setup, "post_exposure_setup": handling,
        "shadow_setup": shadow_setup, "challenge_setup": challenge_setup,
        "donor_initial_label": donor_label if count > 1 else None,
        "written_label": written_label, "acquired_opposite_state": bool(acquired),
        "retained_written_label": bool(retained), "recovery": recovery,
        "donor_independent_acquired_recoverable_state": bool(history == "pulse" and acquired and retained and recovery["recovered"]),
        "expected_label": expected, "expected_label_sequence": expected_sequence,
        "challenge_target": challenge_target, "regulator_scales": dict(zip(REGULATORS, regulator_scales.tolist())),
        "retention_recipient_drift": {name: float(drift[index]) for name, index in exp.indices.items()},
        "challenge_shadow_recipient_difference": {name: float(shadow_difference[index]) for name, index in exp.indices.items()},
        "audits": exp.audits,
        "integrator": {key: getattr(exp.p, key) for key in ("time_step", "sim_integ_max_delt_cc", "sim_integ_max_delt_Vm", "use_implicit")},
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "scope": "Finite-horizon regulatory memory/local recovery in the native approximation; no lineage or carrier-renewal test",
    }
    write_json(folder / "result.json", result)
    print("MEMORY_OUTCOME " + json.dumps({key: result[key] for key in (
        "case", "written_label", "acquired_opposite_state", "retained_written_label", "recovery", "expected_label_sequence")}), flush=True)
    # A scientifically negative result with valid execution still exits zero.
    return 0


def run_worker(case, run_dir, config, deadline, env):
    name = case["id"]
    record = {"id": name, "execution_pass": False}
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return dict(record, status="not_launched_budget")
    folder = run_dir / name
    folder.mkdir()
    write_json(folder / "spec.json", {"case": case, "config": config, "reference_dir": str(run_dir / "reference")})
    timeout = min(config["worker_timeout_seconds"], remaining)
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", str(folder / "spec.json")]
    print(f"Starting {name} (limit {timeout:.0f}s)", flush=True)
    began = time.monotonic()
    with (folder / "stdout.log").open("x") as log:
        try:
            process = subprocess.run(command, cwd=folder, env=env, stdin=subprocess.DEVNULL,
                                     stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
            record.update(status="finished", returncode=process.returncode)
        except subprocess.TimeoutExpired:
            record.update(status="timeout", returncode=None)
    record["elapsed_seconds"] = time.monotonic() - began
    if (folder / "result.json").exists():
        record["result"] = json.loads((folder / "result.json").read_text())
        record["execution_pass"] = record["returncode"] == 0 and record["result"]["execution_pass"]
    print(f"{name}: {'VALID' if record['execution_pass'] else 'INVALID'} / {record['status']} / {record['elapsed_seconds']:.1f}s", flush=True)
    return record


def run_suite(config_path):
    config = json.loads(config_path.read_text())
    if config["revision"] != REVISION or not 1 <= config["workers"] <= 2:
        raise ValueError("Unexpected revision/concurrency")
    if not 0 < config["worker_timeout_seconds"] <= 900 or not 0 < config["total_budget_seconds"] <= 3600:
        raise ValueError("Exceeds runtime bounds")
    source_check()
    (ROOT / "runs").mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = Path(tempfile.mkdtemp(prefix=f"memory-probe-{stamp}-", dir=ROOT / "runs"))
    frozen = run_dir / "frozen"
    frozen.mkdir()
    files = [Path(__file__).resolve(), ROOT / "scripts" / "memory_metrics.py", ROOT / "scripts" / "run_pilot.py",
             ROOT / "MEMORY_PROBE_PROTOCOL.md", config_path, ROOT / "requirements-smoke.txt"]
    for path in files:
        (frozen / path.name).write_bytes(path.read_bytes())
    source_files = subprocess.check_output(["git", "-C", str(SOURCE), "ls-files", "*.py"], text=True).splitlines()
    files.extend(SOURCE / name for name in source_files)
    summary = {"started_utc": stamp, "revision": REVISION, "python": sys.version,
               "packages": {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "matplotlib")},
               "hashes_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files},
               "config": config, "cases": [], "scope": "New memory probe, not paper reproduction or PH"}
    write_json(run_dir / "summary.json", summary)
    env = os.environ.copy()
    env.update(MPLBACKEND="Agg", MPLCONFIGDIR=str(ROOT / ".cache" / "matplotlib"), XDG_CACHE_HOME=str(ROOT / ".cache"),
               PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1",
               MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    began = time.monotonic()
    deadline = began + config["total_budget_seconds"]
    print(f"Run artifacts: {run_dir}", flush=True)
    summary["reference"] = run_worker({"id": "reference"}, run_dir, config, deadline, env)
    write_json(run_dir / "summary.json", summary)
    if not summary["reference"]["execution_pass"]:
        print("Reference failed; experiments not launched.", flush=True)
        return 1
    with ThreadPoolExecutor(max_workers=config["workers"]) as pool:
        futures = [pool.submit(run_worker, case, run_dir, config, deadline, env) for case in config["cases"]]
        for future in as_completed(futures):
            summary["cases"].append(future.result())
            write_json(run_dir / "summary.json", summary)
    source_check()
    summary.update(elapsed_seconds=time.monotonic() - began, source_clean_after=True,
                   all_execution_valid=all(record["execution_pass"] for record in summary["cases"]))
    write_json(run_dir / "summary.json", summary)
    print(f"Summary: {run_dir / 'summary.json'}", flush=True)
    return 0 if summary["all_execution_valid"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "memory_probe_v1.json")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        spec = json.loads(args.worker.read_text())
        folder = args.worker.parent
        if spec["case"]["id"] == "reference":
            return reference_worker(folder, spec["config"])
        return experiment_worker(folder, spec["config"], spec["case"], Path(spec["reference_dir"]))
    return run_suite(args.config.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
