"""HS001's coordinator: python -m hs001.run --stage {smoke,tests,probe,preflight,debug,development,e014} --root RUN_ROOT
--cpus LIST [--horizon N]

nl004.run's pattern: one worker per allocated CPU, one numerical thread each; immutable shards and completion records,
an exclusive run lock, resumption from valid completion records, and the manifest (sources, design digest, CPU set,
wall and CPU time, peak RAM, disk headroom). The probe runs under bookkeeping tag mse-p49, every other stage under
mse-hs001 (the E-series engine keeps its own seeds). Development and the reported continuation of E014's cohort (e014)
are refused unless the design digest and sources equal the frozen ones and the qualification receipt passes.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

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
sys.dont_write_bytecode = True

import numpy as np  # noqa: E402

from hs001 import design as D  # noqa: E402
from hs001.worker import run_task  # noqa: E402

FROZEN = LANE / "hs001" / "frozen"


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _pin(queue):
    os.sched_setaffinity(0, {queue.get()})


def valid(root, block):
    done = root / "done" / f"{block}.json"
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
    ap.add_argument("--stage", choices=tuple(D.STAGE_TAG), required=True)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--cpus", required=True, help="comma-separated allocated CPU ids")
    ap.add_argument("--horizon", type=int, default=D.HORIZON)
    ap.add_argument("--blocks", default="all", help="a comma-separated subset of the stage's blocks")
    a = ap.parse_args()
    cpus = [int(c) for c in a.cpus.split(",")]
    os.sched_setaffinity(0, cpus)
    root = a.root.resolve()
    blocks = D.stage_blocks(a.stage)
    if a.blocks != "all":
        sub = [int(b) for b in a.blocks.split(",")]
        assert set(sub) <= set(blocks), "blocks outside the stage's identities"
        blocks = sub
    if a.horizon != D.HORIZON and a.stage in ("probe", "preflight", "development", "e014"):
        sys.exit("a registered stage runs at the registered horizon")
    if a.stage in ("development", "e014"):
        frozen = json.loads((FROZEN / "design.json").read_text())
        receipt = json.loads((FROZEN / "qualification_receipt.json").read_text())
        if frozen["digest"] != D.digest() or receipt.get("design_digest") != D.digest():
            sys.exit("design digest differs from the frozen registration: refusing development work")
        now = D.sources(LANE)
        changed = sorted(k for k in set(frozen["sources"]) | set(now) if frozen["sources"].get(k) != now.get(k))
        if changed:
            sys.exit(f"sources changed since the freeze: {changed}: refusing development work")
        if receipt.get("status") != "PASS":
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
        start = {"stage": a.stage, "started_utc": utc(), "host": socket.gethostname(), "pid": os.getpid(), "cpus": cpus,
                 "workers": len(cpus), "blocks": blocks, "horizon": a.horizon, "tag": D.STAGE_TAG[a.stage],
                 "design_digest": D.digest(), "sources": D.sources(LANE), "numpy": np.__version__,
                 "python": sys.version.split()[0], "load_1min_start": float(open("/proc/loadavg").read().split()[0]),
                 "disk_free_bytes_start": shutil.disk_usage(root).free}
        (root / "manifest_start.json").write_text(json.dumps(start, indent=1) + "\n")
        records, todo = {}, []
        for b in blocks:
            rec = valid(root, b)
            if rec is not None:
                records[b] = dict(rec, resumed=True)
            else:
                todo.append(b)
        print(f"{utc()} {a.stage}: {len(blocks)} tasks, {len(records)} resumed, {len(todo)} to run on cpus {cpus} "
              f"(1-min load {start['load_1min_start']})", flush=True)
        t0 = time.time()
        queue = mp.get_context("fork").Queue()
        for c in cpus:
            queue.put(c)
        with ProcessPoolExecutor(len(cpus), mp_context=mp.get_context("fork"), initializer=_pin, initargs=(queue,)) as pool:
            futures = {pool.submit(run_task, b, a.stage, str(root), a.horizon): b for b in todo}
            for i, fut in enumerate(as_completed(futures), 1):
                b = futures[fut]
                rec = fut.result()
                records[b] = rec
                print(f"{utc()} done {i}/{len(todo)} {b} wall {rec['wall_s']} s cpu {rec['cpu_s']} s rss "
                      f"{rec['maxrss_mb']} MB on cpu {rec['cpu']}", flush=True)
        wall = time.time() - t0
        recs = [records[b] for b in blocks]
        manifest = dict(start, finished_utc=utc(), wall_s=round(wall, 1),
                        cpu_s_total=round(sum(r["cpu_s"] for r in recs), 1),
                        worker_maxrss_mb_peak=max(r["maxrss_mb"] for r in recs),
                        bytes_written=sum(f["bytes"] for r in recs for f in r["files"].values()),
                        disk_free_bytes_end=shutil.disk_usage(root).free,
                        tasks={str(r["block"]): {k: r[k] for k in ("files", "wall_s", "cpu_s", "maxrss_mb")}
                               | {"resumed": r.get("resumed", False)} for r in recs})
        (root / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
        print(f"{utc()} finished: wall {wall:.0f} s, cpu {manifest['cpu_s_total']:.0f} s, peak worker RSS "
              f"{manifest['worker_maxrss_mb_peak']} MB", flush=True)
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
