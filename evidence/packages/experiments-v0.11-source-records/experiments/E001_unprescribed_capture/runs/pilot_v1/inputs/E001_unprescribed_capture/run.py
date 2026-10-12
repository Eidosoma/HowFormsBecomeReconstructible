from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import ROOT, cap_cpus, dump, finish, new_run, utc
from model import ARMS, CFG, checks, simulate
import numpy as np


def worker(block, background, output):
    cap_cpus()
    started = time.monotonic()
    raw = simulate(block, background)
    audit = checks(raw)
    np.savez_compressed(output / f"block_{block:06d}_{background}.npz", **raw)
    dump(output / f"block_{block:06d}_{background}.json", dict(block=block, background=background,
         seconds=time.monotonic()-started, audit=audit, config=asdict(CFG)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--worker", type=int)
    parser.add_argument("--background", choices=("homogeneous", "heterogeneous"))
    args = parser.parse_args()
    if not 1 <= args.workers <= 12:
        parser.error("workers must be between 1 and 12")
    if args.worker is not None:
        if not args.output.resolve().is_relative_to(HERE):
            raise ValueError("Worker output must be local to E001")
        worker(args.worker, args.background, args.output)
        return
    ids = [900001] if args.benchmark else list(range(8))
    backgrounds = ["homogeneous"] if args.benchmark else ["homogeneous", "heterogeneous"]
    started = time.monotonic()
    inputs = [ROOT / "common.py", ROOT / "SOURCE_SNAPSHOT.json", ROOT / "run_python.sh"]
    inputs += [HERE / p for p in ("model.py", "run.py", "analyze.py", "tests.py", "PROTOCOL.md")]
    output = new_run(args.output, inputs, dict(experiment="E001", mode="technical" if args.benchmark else "development",
        blocks=ids, backgrounds=backgrounds, config=asdict(CFG), arms=ARMS, workers=args.workers))
    def launch(block, background):
        command = [sys.executable, "-B", str(HERE / "run.py"), "--output", str(output),
                   "--worker", str(block), "--background", background]
        remaining = 1200 - (time.monotonic()-started)
        if remaining <= 0:
            raise TimeoutError("E001 20-minute campaign budget exhausted")
        with (output / f"worker_{block}_{background}.log").open("x") as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=remaining)
        return block, background
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            tasks = [pool.submit(launch, b, k) for b in ids for k in backgrounds]
            for task in as_completed(tasks):
                block, background = task.result()
                print(f"Completed block {block} / {background}", flush=True)
        from analyze import analyze
        analyze(output, ids, backgrounds, technical=args.benchmark)
        finish(output, started, dict(experiment="E001", blocks_completed=len(ids)*len(backgrounds)))
        print(f"Complete: {output}", flush=True)
    except BaseException:
        dump(output / "FAILED.json", dict(time=utc(), traceback=traceback.format_exc()))
        raise


if __name__ == "__main__":
    main()
