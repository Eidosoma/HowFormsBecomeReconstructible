"""Bounded, instrumented calls to unmodified BITSEY; see PILOT_PROTOCOL.md."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import sys
import tempfile
import time
from contextlib import redirect_stdout

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream" / "bitsey"
REVISION = "b2cb370aaecbc8299f259bc4251d5396c81f19a6"
THRESHOLDS = {
    ("healthy", 2): 1.129e-15, ("tumor", 2): 1.005e-15,
    ("healthy", 3): 7.124e-16, ("tumor", 3): 6.442e-16,
    ("healthy", 4): 5.212e-16, ("tumor", 4): 4.740e-16,
    ("healthy", 5): 4.108e-16, ("tumor", 5): 3.748e-16,
}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def source_check():
    def git(*args):
        return subprocess.check_output(["git", "-C", str(SOURCE), *args], text=True).strip()
    if git("rev-parse", "HEAD") != REVISION:
        raise RuntimeError("Unexpected upstream revision")
    if git("status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("Upstream tracked files are modified")


def compare_thresholds(output, tolerance):
    matches = re.findall(
        r"^Result NR=0 center-(healthy|tumor), surround=(\d+): final GJ_diff=([\deE.+-]+)$",
        output, re.MULTILINE,
    )
    rows = []
    for center, count, value in matches:
        key = center, int(count)
        expected = THRESHOLDS.get(key)
        observed = float(value)
        error = abs(observed / expected - 1) if expected is not None else None
        rows.append({"center_initial": center, "neighbours": int(count),
                     "expected": expected, "observed_rounded": observed,
                     "relative_error": error,
                     "pass": error is not None and error <= tolerance})
    keys = {(row["center_initial"], row["neighbours"]) for row in rows}
    passed = (len(rows) == 8 and keys == set(THRESHOLDS)
              and all(row["pass"] for row in rows) and "BAD_SEARCH" not in output)
    return rows, passed


class Tee(io.StringIO):
    def __init__(self, stream):
        super().__init__()
        self.stream = stream

    def write(self, value):
        self.stream.write(value)
        self.stream.flush()
        return super().write(value)


def worker(spec_path):
    spec_data = json.loads(spec_path.read_text())
    case = spec_data["case"]
    folder = spec_path.parent
    sys.path[:0] = [str(SOURCE / "cancer_GJ_sims"), str(SOURCE)]
    import numpy as np
    import sim

    # The upstream module invokes main on import. Its supported empty CLI range
    # initializes infrastructure without running any time integration.
    args_before = sys.argv
    sys.argv = ["zombie.py", "metas_cases", "1", "1", "25", "0", "0", "0"]
    try:
        module_spec = importlib.util.spec_from_file_location(
            "bitsey_zombie", SOURCE / "cancer_GJ_sims" / "zombie.py")
        z = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(z)
    finally:
        sys.argv = args_before

    audits = []
    original_sim = sim.sim

    def audited_sim(*args, **kwargs):
        started, cpu_started = time.monotonic(), time.process_time()
        output = original_sim(*args, **kwargs)
        elapsed, cpu = time.monotonic() - started, time.process_time() - cpu_started
        times, shots = output
        samples = np.asarray(shots)
        finite = bool(np.isfinite(samples).all() and np.isfinite(sim.cc_cells).all())
        minimum = float(min(np.min(samples), np.min(sim.cc_cells))) if finite else None
        audit = {
            "index": len(audits), "requested_horizon": args[0] if args else kwargs,
            "wall_seconds": elapsed, "cpu_seconds": cpu,
            "sample_count": len(times), "last_sample_time": float(times[-1]),
            "cells": int(sim.cc_cells.shape[1]), "finite": finite,
            "minimum_concentration": minimum,
            "nonnegative": finite and minimum >= 0,
            "last_sample_vs_final_max_abs": float(np.max(np.abs(samples[-1] - sim.cc_cells))) if finite else None,
        }
        audits.append(audit)
        if case["kind"] == "isolation":
            name = f"trajectory-{audit['index']}.npz"
            np.savez_compressed(folder / name, times=np.asarray(times), concentrations=samples,
                                final=sim.cc_cells.copy())
            audit["trajectory"] = name
        write_json(folder / "progress.json", audits)
        print("PILOT_SIM " + json.dumps(audit), flush=True)
        if not finite or minimum < 0:
            raise RuntimeError("Nonfinite or negative concentration in audited output")
        return output

    sim.sim = audited_sim
    p = sim.Params()
    p.no_dumps = True
    p.time_step = .0001
    result = {"case": case, "audit_scope": "Returned snapshots and final state, not every integrator step"}
    started, cpu_started = time.monotonic(), time.process_time()
    if case["kind"] == "neighbours":
        tee = Tee(sys.stdout)
        with redirect_stdout(tee):
            z.surround_flip_sims(p, 0, 0, 0, 0, [0, 100000], "pilot", False)
        rows, passed = compare_thresholds(tee.getvalue(), spec_data["threshold_relative_tolerance"])
        result.update(thresholds=rows, pass_comparison=passed)
    else:
        dimensions = case.get("dimensions", [1, 1, 25])
        if case.get("fine"):
            p.time_step = .00005
            p.sim_integ_max_delt_cc = .0005
            p.sim_integ_max_delt_Vm = .00005
        z.setup_basic_network(p, 0, *dimensions)
        z.GRN.seed3D_inputs(z.cc3D)
        if case["strategy"] in ("under", "both"):
            z.tumor_isolate(.5)
        if case["strategy"] in ("voltage", "both"):
            z.set_Vmem_from_conc()
            gate = z.GJ_lib.GJ_gate()
            z.GRN.set_GJ_diffusions(gate)
        tumour_dimensions = z.set_corner_tumor(6)
        initial = sim.cc_cells.copy()
        disconnected = z.disconnected_sim(500, why=case["id"])
        fixed = bool(z.sim_is_fixed(disconnected, case["kd"], case.get("horizon", 20000), case["id"]))
        labels = [z.GRN.state_char(sim.cc_cells[:, index]) for index in range(sim.cc_cells.shape[1])]
        np.savez_compressed(folder / "endpoints.npz", initial=initial,
                            disconnected=disconnected, final=sim.cc_cells.copy())
        result.update(
            observed_fixed=fixed, pass_comparison=(fixed == case["expected_fixed"]),
            dimensions=dimensions, tumour_dimensions=tumour_dimensions,
            final_state_counts={label: labels.count(label) for label in ("E", "M", "X")},
            final_state_labels="".join(labels), ion_indices=sim.ion_i,
            miRNA_valence=z.GRN.miR200_valence,
            miRNA_medium_size=z.GRN.miR200_is_medium_size,
        )
    result.update(
        wall_seconds=time.monotonic() - started, cpu_seconds=time.process_time() - cpu_started,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        integrator={key: getattr(p, key) for key in (
            "time_step", "sim_integ_max_delt_cc", "sim_integ_max_delt_Vm", "use_implicit")},
        audits=audits,
    )
    result["pass"] = result["pass_comparison"] and bool(audits) and all(
        audit["finite"] and audit["nonnegative"] for audit in audits)
    write_json(folder / "result.json", result)
    print("PILOT_RESULT " + json.dumps(result), flush=True)
    return 0 if result["pass"] else 1


def run_case(case, folder, config, deadline, env):
    record = {"id": case["id"], "pass": False}
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return dict(record, status="not_launched_budget")
    folder.mkdir()
    write_json(folder / "spec.json", {"case": case,
               "threshold_relative_tolerance": config["threshold_relative_tolerance"]})
    timeout = min(config["case_timeout_seconds"], remaining)
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", str(folder / "spec.json")]
    print(f"Starting {case['id']} (limit {timeout:.0f}s)", flush=True)
    started = time.monotonic()
    with (folder / "stdout.log").open("x") as log:
        try:
            process = subprocess.run(command, cwd=folder, env=env, stdin=subprocess.DEVNULL,
                                     stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
            record.update(returncode=process.returncode, status="finished")
        except subprocess.TimeoutExpired:
            record.update(returncode=None, status="timeout")
    record.update(elapsed_seconds=time.monotonic() - started, timeout_seconds=timeout)
    if (folder / "result.json").exists():
        result = json.loads((folder / "result.json").read_text())
        record.update(result=result, **{"pass": record["returncode"] == 0 and result["pass"]})
    print(f"{case['id']}: {'PASS' if record['pass'] else 'FAIL'} / {record['status']} / {record['elapsed_seconds']:.1f}s", flush=True)
    return record


def run_suite(config_path, selected):
    config = json.loads(config_path.read_text())
    if config["revision"] != REVISION or not 1 <= config["workers"] <= 2:
        raise ValueError("Unregistered revision or concurrency")
    if not 0 < config["case_timeout_seconds"] <= 900 or not 0 < config["launch_budget_seconds"] <= 3600:
        raise ValueError("Exceeds protocol runtime bounds")
    cases = config["cases"]
    if selected:
        if set(selected) - {case["id"] for case in cases}:
            raise ValueError("Unknown selected case")
        cases = [case for case in cases if case["id"] in selected]
    if len({case["id"] for case in cases}) != len(cases):
        raise ValueError("Duplicate case IDs")
    for case in cases:
        if not re.fullmatch(r"[a-z0-9_]+", case["id"]):
            raise ValueError("Invalid case ID")
        if case["kind"] not in ("neighbours", "isolation"):
            raise ValueError("Unknown experiment kind")
        if case["kind"] == "isolation" and case["strategy"] not in ("none", "under", "voltage", "both"):
            raise ValueError("Unknown isolation strategy")
    source_check()
    (ROOT / "runs").mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    folder = Path(tempfile.mkdtemp(prefix=f"pilot-{stamp}-", dir=ROOT / "runs"))
    write_json(folder / "config.json", config)
    files = [Path(__file__).resolve(), config_path, ROOT / "PILOT_PROTOCOL.md", ROOT / "requirements-smoke.txt"]
    names = subprocess.check_output(["git", "-C", str(SOURCE), "ls-files", "*.py"], text=True).splitlines()
    files.extend(SOURCE / name for name in names)
    files.extend(SOURCE / "cancer_GJ_sims" / "results_miRNA" / name for name in (
        "surround_flip_72", "tumor_isolate_1D_V1M", "tumor_isolate_2D_V1M"))
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    summary = {"started_utc": stamp, "revision": REVISION, "python": sys.version,
               "packages": {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "matplotlib")},
               "hashes_sha256": hashes, "selected_cases": [case["id"] for case in cases], "cases": [],
               "scope": "Bounded source-output reproduction, not independent replication or PH validation"}
    write_json(folder / "summary.json", summary)
    env = os.environ.copy()
    env.update(MPLBACKEND="Agg", MPLCONFIGDIR=str(ROOT / ".cache" / "matplotlib"),
               XDG_CACHE_HOME=str(ROOT / ".cache"), PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1",
               OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    print(f"Run artifacts: {folder}", flush=True)
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=config["workers"]) as pool:
        futures = [pool.submit(run_case, case, folder / case["id"], config,
                               started + config["launch_budget_seconds"], env) for case in cases]
        for future in as_completed(futures):
            summary["cases"].append(future.result())
            write_json(folder / "summary.json", summary)
    source_check()
    summary.update(elapsed_seconds=time.monotonic() - started, source_clean_after=True,
                   all_passed=all(case["pass"] for case in summary["cases"]))
    write_json(folder / "summary.json", summary)
    print(f"Summary: {folder / 'summary.json'}", flush=True)
    return 0 if summary["all_passed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "pilot_v1.json")
    parser.add_argument("--case", action="append", help="Run only this registered case (repeatable)")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    return worker(args.worker) if args.worker else run_suite(args.config.resolve(), args.case)


if __name__ == "__main__":
    raise SystemExit(main())
