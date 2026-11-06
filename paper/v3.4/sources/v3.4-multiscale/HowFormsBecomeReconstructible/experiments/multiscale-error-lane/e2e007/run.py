"""E2E007's coordinator: python -m e2e007.run --stage {probe,debug,preflight,development} --root RUN_ROOT --cpus LIST

e2e001.run's coordinator (sm006.run's) for E2E007's tasks (e2e007.worker): independent (source, body, unit, block) tasks, one per
restored raw file, over one worker per allocated CPU, each with one numerical thread; workers write immutable shards and
completion records; the coordinator holds an exclusive run lock, resumes from valid completion records and writes the
manifest. No block is drawn: every task restores a saved record (e2e007.design.STAGES).
  development  refused unless the design digest and sources equal the frozen ones and the qualification receipt passes
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

from e2e007 import design as D  # noqa: E402
from e2e007.worker import key, run_task  # noqa: E402

FROZEN = LANE / "e2e007" / "frozen"


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _pin(queue):
    os.sched_setaffinity(0, {queue.get()})


def valid(root, source, body, unit, block):
    done = root / "done" / key(source) / body / unit / f"{block}.json"
    if not done.exists():
        return None
    rec = json.loads(done.read_text())
    for f in rec["files"].values():
        path = root / f["path"]
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != f["sha256"]:
            return None
    return rec if rec["design_digest"] == D.digest() else None


def refuse_unless_frozen():
    if not (FROZEN / "design.json").exists() or not (FROZEN / "qualification_receipt.json").exists():
        sys.exit("the design is not frozen or has no qualification receipt: refusing development work")
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=tuple(D.STAGES), required=True)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--cpus", required=True, help="comma-separated allocated CPU ids")
    a = ap.parse_args()
    cpus = [int(c) for c in a.cpus.split(",")]
    os.sched_setaffinity(0, cpus)
    if a.stage == "development":
        refuse_unless_frozen()
    root = a.root.resolve()
    tasks = D.stage_tasks(a.stage)
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
        start = {"study": D.STUDY, "stage": a.stage, "started_utc": utc(), "host": socket.gethostname(), "pid": os.getpid(),
                 "cpus": cpus, "workers": len(cpus), "tasks_planned": [list(t) for t in tasks],
                 "design_digest": D.digest(), "sources": D.sources(LANE), "numpy": np.__version__,
                 "python": sys.version.split()[0], "load_1min_start": float(open("/proc/loadavg").read().split()[0]),
                 "disk_free_bytes_start": shutil.disk_usage(root).free}
        (root / "manifest_start.json").write_text(json.dumps(start, indent=1) + "\n")
        records, todo = {}, []
        for t in sorted(tasks, key=lambda x: (x[1] != "li4", x)):
            rec = valid(root, *t)
            if rec is not None:
                records[t] = dict(rec, resumed=True)
            else:
                todo.append(t)
        print(f"{utc()} {a.stage}: {len(tasks)} tasks, {len(records)} resumed, {len(todo)} to run on cpus {cpus} "
              f"(1-min load {start['load_1min_start']})", flush=True)
        t0 = time.time()
        queue = mp.get_context("fork").Queue()
        for c in cpus:
            queue.put(c)
        with ProcessPoolExecutor(len(cpus), mp_context=mp.get_context("fork"), initializer=_pin, initargs=(queue,)) as pool:
            futures = {pool.submit(run_task, s, b, u, blk, a.stage, str(root)): (s, b, u, blk) for s, b, u, blk in todo}
            for i, fut in enumerate(as_completed(futures), 1):
                s, b, u, blk = futures[fut]
                rec = fut.result()
                records[(s, b, u, blk)] = rec
                print(f"{utc()} done {i}/{len(todo)} {s} {b} {u} {blk} rows {rec['n_rows']} wall {rec['wall_s']} s cpu "
                      f"{rec['cpu_s']} s rss {rec['maxrss_mb']} MB bridge {'ok' if rec['bridge_all_equal'] else 'DIFFERS'} "
                      f"on cpu {rec['cpu']}", flush=True)
        recs = list(records.values())
        manifest = dict(start, finished_utc=utc(), wall_s=round(time.time() - t0, 1),
                        cpu_s_total=round(sum(r["cpu_s"] for r in recs), 1),
                        worker_maxrss_mb_peak=max(r["maxrss_mb"] for r in recs),
                        bytes_written=sum(f["bytes"] for r in recs for f in r["files"].values()),
                        bridge_all_equal=all(r["bridge_all_equal"] for r in recs),
                        disk_free_bytes_end=shutil.disk_usage(root).free,
                        tasks={f"{r['source']}/{r['body']}/{r['unit']}/{r['block']}":
                               {k: r[k] for k in ("files", "wall_s", "cpu_s", "maxrss_mb", "bridge_all_equal", "n_rows")}
                               | {"resumed": r.get("resumed", False)} for r in recs})
        (root / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
        print(f"{utc()} finished: wall {manifest['wall_s']:.0f} s, cpu {manifest['cpu_s_total']:.0f} s, peak worker RSS "
              f"{manifest['worker_maxrss_mb_peak']} MB, bridges {'all equal' if manifest['bridge_all_equal'] else 'NOT ALL EQUAL'}",
              flush=True)
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
