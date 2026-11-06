"""Coordinator: python -m be005.run --stage {preflight,development} --root RUN_ROOT --cpus LIST

Parallelises independent (body, unit, source block) tasks over one worker per allocated CPU, each with one numerical
thread, longest tasks first (estimated arm-updates). Workers write immutable shards and completion records; the
coordinator holds an exclusive run lock, resumes from valid completion records, and writes the manifest (sources, design
digest, CPU set, wall and CPU time, peak RAM, disk headroom). Development work is refused unless the design digest and
sources equal the frozen ones and the qualification receipt passes.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
from concurrent.futures import ProcessPoolExecutor, as_completed  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import multiprocessing as mp  # noqa: E402
from pathlib import Path  # noqa: E402
import shutil  # noqa: E402
import socket  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from be005 import design as D  # noqa: E402
from be005.worker import run_task  # noqa: E402

FROZEN = LANE / "be005" / "frozen"


def cost(body, unit):
    """Estimated work of one task: arm-updates over every run, li4's inhibitor a little dearer (every task is alike)."""
    w = sum(D.WINDOW * len(x[3]) for x in D.RUNS)
    return D.SIDE * D.SIDE * w * (1.05 if body == "li4" else 1.0)


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _pin(queue):
    os.sched_setaffinity(0, {queue.get()})


def valid(root, body, name, block):
    done = root / "done" / body / name / f"{block}.json"
    if not done.exists():
        return None
    rec = json.loads(done.read_text())
    for f in rec["files"].values():
        path = root / f["path"]
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != f["sha256"]:
            return None
    return rec if rec["design_digest"] == D.digest() else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("preflight", "development"), required=True)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--cpus", required=True, help="comma-separated allocated CPU ids")
    ap.add_argument("--bodies", default="all")
    ap.add_argument("--blocks", default=None, help="LO,HI: preflight debugging on design.DEBUG_BLOCKS only")
    a = ap.parse_args()
    cpus = [int(c) for c in a.cpus.split(",")]
    os.sched_setaffinity(0, cpus)
    root = a.root.resolve()
    blocks = D.stage_blocks(a.stage, None if a.blocks is None else tuple(map(int, a.blocks.split(","))))
    bodies = list(D.BODIES) if a.bodies == "all" else a.bodies.split(",")
    if a.stage == "development":
        frozen = json.loads((FROZEN / "design.json").read_text())
        receipt = json.loads((FROZEN / "qualification_receipt.json").read_text())
        if frozen["digest"] != D.digest() or receipt.get("design_digest") != D.digest():
            sys.exit("design digest differs from the frozen registration: refusing development work")
        now = D.sources(LANE)
        changed = sorted(k for k in set(frozen["sources"]) | set(now) if frozen["sources"].get(k) != now.get(k))
        if changed:
            sys.exit(f"sources changed since the freeze: {changed}: refusing development work")
        if receipt.get("status") not in ("PASS", "PASS_WITH_FLAGS"):
            sys.exit("qualification receipt is not PASS: refusing development work")
    root.mkdir(parents=True, exist_ok=True)
    lock = root / "LOCK"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        sys.exit(f"run lock held: {lock.read_text().strip()}")
    os.write(fd, f"{socket.gethostname()} pid {os.getpid()} since {utc()}\n".encode())
    os.close(fd)
    (root / "coordinator.pid").write_text(f"{os.getpid()}\n")
    try:
        start = {"stage": a.stage, "started_utc": utc(), "host": socket.gethostname(), "pid": os.getpid(),
                 "cpus": cpus, "workers": len(cpus), "bodies": bodies, "blocks": [blocks[0], blocks[-1] + 1],
                 "design_digest": D.digest(), "sources": D.sources(LANE), "numpy": np.__version__,
                 "python": sys.version.split()[0], "load_1min_start": float(open("/proc/loadavg").read().split()[0]),
                 "disk_free_bytes_start": shutil.disk_usage(root).free}
        (root / "manifest_start.json").write_text(json.dumps(start, indent=1) + "\n")
        tasks = sorted(((p, r, b) for p, r in D.tasks() if p in bodies for b in blocks), key=lambda x: -cost(x[0], x[1]))
        records, todo = {}, []
        for p, r, b in tasks:
            rec = valid(root, p, r, b)
            if rec is not None:
                records[(p, r, b)] = dict(rec, resumed=True)
            else:
                todo.append((p, r, b))
        print(f"{utc()} {a.stage}: {len(tasks)} tasks, {len(records)} resumed, {len(todo)} to run on cpus {cpus} "
              f"(1-min load {start['load_1min_start']})", flush=True)
        t0 = time.time()
        queue = mp.get_context("fork").Queue()
        for c in cpus:
            queue.put(c)
        with ProcessPoolExecutor(len(cpus), mp_context=mp.get_context("fork"), initializer=_pin,
                                 initargs=(queue,)) as pool:
            futures = {pool.submit(run_task, p, r, b, D.PURPOSE[a.stage], str(root)): (p, r, b)
                       for p, r, b in todo}
            for i, fut in enumerate(as_completed(futures), 1):
                p, r, b = futures[fut]
                rec = fut.result()
                records[(p, r, b)] = rec
                print(f"{utc()} done {i}/{len(todo)} {p} {r} {b} wall {rec['wall_s']} s cpu {rec['cpu_s']} s "
                      f"rss {rec['maxrss_mb']} MB on cpu {rec['cpu']}", flush=True)
        wall = time.time() - t0
        recs = list(records.values())
        manifest = dict(start, finished_utc=utc(), wall_s=round(wall, 1),
                        cpu_s_total=round(sum(r["cpu_s"] for r in recs), 1),
                        worker_maxrss_mb_peak=max(r["maxrss_mb"] for r in recs),
                        bytes_written=sum(f["bytes"] for r in recs for f in r["files"].values()),
                        disk_free_bytes_end=shutil.disk_usage(root).free,
                        tasks={f"{r['body']}/{r['unit']}/{r['block']}": {k: r[k] for k in ("files", "wall_s", "cpu_s", "maxrss_mb")}
                               | {"resumed": r.get("resumed", False)} for r in recs})
        (root / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
        print(f"{utc()} finished: wall {wall:.0f} s, cpu {manifest['cpu_s_total']:.0f} s, "
              f"peak worker RSS {manifest['worker_maxrss_mb_peak']} MB", flush=True)
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
