"""Runtime-only subset adapter; see PILOT_FOLLOWUP_PROTOCOL.md."""

import argparse
from contextlib import redirect_stdout
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from run_pilot import ROOT, SOURCE, REVISION, Tee, compare_thresholds, source_check, write_json


def worker(folder, neighbours):
    sys.path[:0] = [str(SOURCE / "cancer_GJ_sims"), str(SOURCE)]
    import numpy as np
    import sim
    saved_args = sys.argv
    sys.argv = ["zombie.py", "metas_cases", "1", "1", "25", "0", "0", "0"]
    try:
        spec = importlib.util.spec_from_file_location("bitsey_zombie", SOURCE / "cancer_GJ_sims" / "zombie.py")
        z = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(z)
    finally:
        sys.argv = saved_args
    audits = []
    original_sim = sim.sim

    def audited_sim(*args, **kwargs):
        started, cpu = time.monotonic(), time.process_time()
        output = original_sim(*args, **kwargs)
        wall, cpu = time.monotonic() - started, time.process_time() - cpu
        times, shots = output
        samples = np.asarray(shots)
        finite = bool(np.isfinite(samples).all() and np.isfinite(sim.cc_cells).all())
        minimum = float(min(samples.min(), sim.cc_cells.min())) if finite else None
        audits.append({"requested_horizon": args[0], "wall_seconds": wall, "cpu_seconds": cpu,
                       "sample_count": len(times), "last_sample_time": float(times[-1]),
                       "finite": finite, "nonnegative": finite and minimum >= 0,
                       "minimum_concentration": minimum})
        write_json(folder / "progress.json", audits)
        print("PILOT_SIM " + json.dumps(audits[-1]), flush=True)
        if not finite or minimum < 0:
            raise RuntimeError("Invalid sampled concentration")
        return output

    sim.sim = audited_sim
    p = sim.Params()
    p.no_dumps = True
    p.time_step = .005
    tee = Tee(sys.stdout)
    started = time.monotonic()
    with redirect_stdout(tee):
        # Same statements as surround_flip_sims for one selected outer-loop
        # count. The plotting-free Thevenin diagnostic after each result is
        # omitted; it does not update the simulator state.
        z.setup_basic_network(p, 0, dimX=1, dimY=1, dimZ=neighbours + 1)
        sim.GJ_connects["from"] = 0
        sim.GJ_connects["to"] = range(1, neighbours + 1)
        z.GRN.seed3D_inputs(sim.cc_cells)
        for center_tumor in (False, True):
            z.GRN.set_cell_state(sim.cc_cells, 0, center_tumor)
            z.GRN.set_cell_state(sim.cc_cells, range(1, neighbours + 1), not center_tumor)
            z.GRN.set_GJdiff(0)
            _, shots = sim.sim(500)
            z.cc_discon = shots[-1].copy()
            center = "tumor" if center_tumor else "healthy"
            title = f"NR=0 center-{center}, surround={neighbours}"
            _, kd = z.binSearch(z.surround_flip_sim, 0, 1e-12, why=title)
            if kd == z.BAD_SEARCH:
                print(f"Result {title} final: BAD_SEARCH")
            else:
                print(f"Result {title}: final GJ_diff={kd:.4g}")
    rows, _ = compare_thresholds(tee.getvalue(), .02)
    passed = (len(rows) == 2 and all(row["pass"] for row in rows)
              and {(row["center_initial"], row["neighbours"]) for row in rows}
              == {("healthy", neighbours), ("tumor", neighbours)}
              and "BAD_SEARCH" not in tee.getvalue())
    result = {"neighbours": neighbours, "thresholds": rows, "audits": audits,
              "wall_seconds": time.monotonic() - started, "pass": passed,
              "scope": "Subset orchestration of original setup and native solver/predicate/search; not an independent implementation"}
    write_json(folder / "result.json", result)
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--neighbours", type=int, choices=(2, 3, 4, 5), required=True)
    parser.add_argument("--original-run", type=Path)
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        return worker(args.worker, args.neighbours)
    if args.original_run is None:
        parser.error("--original-run is required")
    original = json.loads((args.original_run / "summary.json").read_text())
    origin = datetime.strptime(original["started_utc"], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    remaining = 3600 - (datetime.now(timezone.utc) - origin).total_seconds()
    if remaining <= 0:
        raise RuntimeError("Original overall budget is exhausted")
    source_check()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    folder = Path(tempfile.mkdtemp(prefix=f"pilot-neighbour-followup-{stamp}-", dir=ROOT / "runs"))
    files = [Path(__file__).resolve(), ROOT / "scripts" / "run_pilot.py", ROOT / "PILOT_FOLLOWUP_PROTOCOL.md"]
    summary = {"revision": REVISION, "original_run": str(args.original_run.resolve()),
               "started_utc": stamp, "neighbours": args.neighbours, "timeout_seconds": min(900, remaining),
               "hashes_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    write_json(folder / "summary.json", summary)
    env = os.environ.copy()
    env.update(MPLBACKEND="Agg", MPLCONFIGDIR=str(ROOT / ".cache" / "matplotlib"),
               XDG_CACHE_HOME=str(ROOT / ".cache"), PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1",
               OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    print(f"Follow-up artifacts: {folder}", flush=True)
    started = time.monotonic()
    with (folder / "stdout.log").open("x") as log:
        try:
            proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--neighbours", str(args.neighbours),
                                   "--worker", str(folder)], cwd=folder, env=env, stdin=subprocess.DEVNULL,
                                  stdout=log, stderr=subprocess.STDOUT, timeout=summary["timeout_seconds"])
            summary.update(returncode=proc.returncode, status="finished")
        except subprocess.TimeoutExpired:
            summary.update(returncode=None, status="timeout")
    source_check()
    summary.update(elapsed_seconds=time.monotonic() - started, source_clean_after=True)
    if (folder / "result.json").exists():
        summary["result"] = json.loads((folder / "result.json").read_text())
    summary["pass"] = summary["returncode"] == 0 and summary.get("result", {}).get("pass", False)
    write_json(folder / "summary.json", summary)
    print(f"Follow-up {'PASS' if summary['pass'] else 'FAIL'}: {folder / 'summary.json'}", flush=True)
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
