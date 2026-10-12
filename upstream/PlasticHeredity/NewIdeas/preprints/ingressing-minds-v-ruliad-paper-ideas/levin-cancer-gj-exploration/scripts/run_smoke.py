"""Bounded execution checks of the unmodified, pinned BITSEY source.

Not a paper replication or an independent implementation. Each case runs in a
fresh process; raw logs and provenance are retained under ignored runs/.
"""

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream" / "bitsey"
REVISION = "b2cb370aaecbc8299f259bc4251d5396c81f19a6"
CASES = ("single_cell_e", "single_cell_m", "metas_case_0")
MARKER = "SMOKE_RESULT "


def single_cell_worker(case):
    # Upstream uses cwd-relative imports; provide explicit source paths without
    # editing their files. This module has no automatic experiment invocation.
    sys.path[:0] = [str(SOURCE / "cancer_GJ_sims"), str(SOURCE)]
    import numpy as np
    import GRN_miRNA as grn
    import sim

    grn.instantiate()
    expected = "E" if case == "single_cell_e" else "M"
    initial = (100, 0, 0) if expected == "E" else (0, 100, 100)
    # Upstream helper and its original 10000-unit simulation horizon.
    cc = grn.sim_me(72, *initial)
    finite = bool(np.isfinite(cc).all())
    nonnegative = bool((cc >= 0).all())
    observed = grn.state_char(cc[:, 0])
    result = {
        "case": case,
        "snail": 72,
        "initial_miR200_Zeb_ZEB": initial,
        "expected_state": expected,
        "observed_state": observed,
        "finite": finite,
        "nonnegative": nonnegative,
        "final_concentrations": {
            name: float(cc[index, 0]) for name, index in sim.ion_i.items()
        },
        "pass": finite and nonnegative and observed == expected,
        "scope": "Single-cell execution/state-retention smoke check only",
    }
    print(MARKER + json.dumps(result, allow_nan=False), flush=True)
    return 0 if result["pass"] else 1


def run_suite(selected, timeout_seconds):
    actual = subprocess.check_output(
        ["git", "-C", str(SOURCE), "rev-parse", "HEAD"], text=True
    ).strip()
    if actual != REVISION:
        raise RuntimeError(f"Expected {REVISION}, found {actual}")
    dirty = subprocess.check_output(
        ["git", "-C", str(SOURCE), "status", "--porcelain", "--untracked-files=no"],
        text=True,
    )
    if dirty:
        raise RuntimeError("Upstream has tracked modifications; use a clean checkout.")

    (ROOT / "runs").mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = Path(tempfile.mkdtemp(prefix=f"smoke-{timestamp}-", dir=ROOT / "runs"))
    env = os.environ.copy()
    env.update({
        "MPLBACKEND": "Agg",
        "MPLCONFIGDIR": str(ROOT / ".cache" / "matplotlib"),
        "XDG_CACHE_HOME": str(ROOT / ".cache"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
    })
    summary = {
        "started_utc": timestamp,
        "upstream_revision": actual,
        "python": sys.version,
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("numpy", "scipy", "matplotlib")
        },
        "case_timeout_seconds": timeout_seconds,
        "source_modified": False,
        "cases": [],
        "claim_boundary": "Execution smoke checks, not reproduction of paper tables or PH",
    }
    print(f"Run artifacts: {run_dir}", flush=True)

    for case in selected:
        if case.startswith("single_cell_"):
            command = [sys.executable, str(Path(__file__).resolve()), "--worker", case]
            cwd = run_dir
        else:
            # The upstream CLI range is [min,max): this runs ONLY case zero,
            # not the full 10800-configuration metastasis sweep.
            command = [sys.executable, "-u", "zombie.py", "metas_cases",
                       "1", "1", "21", "0", "0", "1"]
            cwd = SOURCE / "cancer_GJ_sims"
        log_path = run_dir / f"{case}.log"
        print(f"Starting {case} (timeout {timeout_seconds}s)", flush=True)
        started = time.monotonic()
        record = {"case": case, "command": command, "cwd": str(cwd), "log": log_path.name}
        with log_path.open("x") as log:
            try:
                proc = subprocess.run(
                    command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                    stdout=log, stderr=subprocess.STDOUT, timeout=timeout_seconds,
                )
                record["returncode"] = proc.returncode
                record["timed_out"] = False
            except subprocess.TimeoutExpired:
                record["returncode"] = None
                record["timed_out"] = True
        record["elapsed_seconds"] = round(time.monotonic() - started, 3)
        output = log_path.read_text()
        record["pass"] = False
        if case.startswith("single_cell_"):
            results = [line[len(MARKER):] for line in output.splitlines() if line.startswith(MARKER)]
            if results:
                record["result"] = json.loads(results[-1])
                record["pass"] = record["returncode"] == 0 and record["result"]["pass"]
        else:
            final_lines = re.findall(r"^0\. Final .* => .*$", output, flags=re.MULTILINE)
            record["final_lines"] = final_lines
            record["pass"] = (
                record["returncode"] == 0 and len(final_lines) == 1
                and not re.search(r"Traceback|stack dump|BAD_SEARCH|\b(?:nan|inf)\b", output)
            )
        summary["cases"].append(record)
        summary["all_passed"] = all(item["pass"] for item in summary["cases"])
        (run_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(f"{case}: {'PASS' if record['pass'] else 'FAIL'} ({record['elapsed_seconds']}s)", flush=True)
        if not record["pass"]:
            print("\n".join(output.splitlines()[-16:]), flush=True)

    print(f"Summary: {run_dir / 'summary.json'}", flush=True)
    return 0 if summary["all_passed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=("all",) + CASES, default="all")
    parser.add_argument("--timeout-seconds", type=float, default=120)
    parser.add_argument("--worker", choices=CASES[:2], help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        return single_cell_worker(args.worker)
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")
    selected = CASES if args.case == "all" else (args.case,)
    return run_suite(selected, args.timeout_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
