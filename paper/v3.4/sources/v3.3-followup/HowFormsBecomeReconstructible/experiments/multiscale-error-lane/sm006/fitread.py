"""SM006's FIT gain variants: SM001's FIT records reread at g 1 and g 2 with every branch's gain x f (no block drawn).

python -m sm006.fitread run --root RUN_ROOT/fit_gain --cpus LIST [--limit UNIT/BLOCK,...]    (48 tasks; resumable)

Each of SM001's 48 FIT tasks (W4_x32, W8_x32, W16_x32 on 910628-910643): its files checked by sha256 against SM001's
FIT manifest and its case set enrolled as SM001 enrolled it (sm004.fitread4.load_records); the dial arms with m in
design.FIT_MS (18 a unit) and the no-record control (the first arm's record at gain 0) read under SM001's tag at g 1
(sm001.sim.successor, stream dw) and g 2 (sm002.coarse.read_cg, stream dw-cg) with the gains x f for f in design.F_GRID.
The control's reads (gain 0, any f) must equal SM003's FIT reread's controls at every sign-based endpoint (a bridge).
Writes fit_gain/shards/UNIT/BLOCK.npz (L{L}/g{g}/{fname}/{e}, each (19, cases), at the last read), done records and a
manifest. Training data: new reads of records SM001, SM003 and SM004 read at the base gain.
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
import resource  # noqa: E402
import shutil  # noqa: E402
import socket  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from sm001 import design as S1D  # noqa: E402
from sm001 import sim as S1  # noqa: E402
from sm003 import readers as RD3  # noqa: E402
from sm004 import design as D4  # noqa: E402
from sm004 import fitread4 as F4R  # noqa: E402
from sm006 import design as D  # noqa: E402

ENDS = ("in", "in_gen", "align", "shape", "spacing")
SIGN = ("in", "in_gen", "align", "shape")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def arm_index(unit):
    return [i for i, a in enumerate(S1D.unit_arms(unit)) if not a["never"] and a["m"] in D.FIT_MS]


def task(unit, block, files):
    raw, meta, cases = F4R.load_records(unit, block, files)
    cfg = S1D.UNIT[unit]
    side, w, k = cfg["side"], cfg["w"], len(cases)
    na = len(S1D.unit_arms(unit))
    idx = arm_index(unit)
    T = raw["T"].astype(np.float64)
    th = np.zeros_like(T)
    z12 = np.load(Path(D4.FIT12_ROOT) / "shards" / unit / f"{block}.npz")
    ends, bridge, timing = {}, {}, {}
    for L in cfg["sizes"]:
        rn = f"L{L}"
        r, H, W = (raw[f"{rn}/{x}"].astype(np.float64).reshape(na, k, side, side) for x in ("r", "H", "W"))
        pick = lambda x: np.concatenate([x[idx].reshape(len(idx) * k, side, side), x[0]])   # the arms, then the control
        rr, HH, WW = pick(r), pick(H), pick(W)
        m = raw[f"{rn}/m"]
        for f in D.F_GRID:
            gains = [S1D.GAIN * f] * len(idx) + [0.0]
            fn = D.F_NAME[f]
            t1 = time.time()
            o1 = S1.successor(rr, HH, WW, cases, th, T, m, side, w, gains, tag=D4.FIT_TAG, reads=S1D.READS2)
            timing[f"{rn}/g1/{fn}"] = round(time.time() - t1, 3)
            t1 = time.time()
            o2 = RD3.read_g2(rr, HH, WW, cases, th, T, m, side, w, gains, D4.FIT_TAG)
            timing[f"{rn}/g2/{fn}"] = round(time.time() - t1, 3)
            for e in ENDS:
                ends[f"{rn}/g1/{fn}/{e}"] = o1[e][-1].reshape(len(idx) + 1, k)
                ends[f"{rn}/g2/{fn}/{e}"] = o2[e].reshape(len(idx) + 1, k)
            bridge[f"{rn}/{fn}"] = all(np.array_equal(ends[f"{rn}/g{g}/{fn}/{e}"][-1], z12[f"{rn}/g{g}/{e}"][na])
                                       for g in (1, 2) for e in SIGN)
    return ends, bridge, timing, meta, idx


def run_task(root, unit, block, files):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    ends, bridge, timing, smeta, idx = task(unit, block, files)
    if not all(np.isfinite(v).all() for v in ends.values()):
        raise FloatingPointError(f"non-finite FIT gain reads in {unit} {block}")
    meta = {"study": D.STUDY, "stage": "fit_gain", "unit": unit, "block": block, "tag": D4.FIT_TAG,
            "design_digest": D.reread_digest(), "arms": [S1D.unit_arms(unit)[i]["name"] for i in idx], "f_grid": list(D.F_GRID),
            "sizes": smeta["sizes"], "cases": smeta["cases"], "numpy": np.__version__, "timing_s": timing}
    folder = root / "shards" / unit
    folder.mkdir(parents=True, exist_ok=True)
    final = folder / f"{block}.npz"
    tmp = folder / f".{block}.{os.getpid()}.tmp.npz"
    np.savez(tmp, __meta__=np.array(json.dumps(meta)), **ends)
    os.replace(tmp, final)
    rec = {"unit": unit, "block": block, "design_digest": D.reread_digest(),
           "file": {"path": str(final.relative_to(root)), "sha256": sha(final), "bytes": final.stat().st_size},
           "bridge": bridge, "bridge_all_equal": all(bridge.values()),
           "wall_s": round(time.time() - t_wall, 2), "cpu_s": round(time.process_time() - t_cpu, 2),
           "maxrss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
           "cpu": sorted(os.sched_getaffinity(0)), "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    done = root / "done" / unit / f"{block}.json"
    done.parent.mkdir(parents=True, exist_ok=True)
    tmpd = done.with_suffix(f".{os.getpid()}.tmp")
    tmpd.write_text(json.dumps(rec, indent=1) + "\n")
    os.replace(tmpd, done)
    return rec


def _pin(queue):
    os.sched_setaffinity(0, {queue.get()})


def cmd_run(a):
    root = a.root.resolve()
    cpus = [int(c) for c in a.cpus.split(",")]
    os.sched_setaffinity(0, cpus)
    FM = F4R.fit_manifest()
    pairs = [tuple(p) for p in FM["pairs"]]
    if a.limit:
        pairs = [p for p in pairs if f"{p[0]}/{p[1]}" in set(a.limit.split(","))]
    root.mkdir(parents=True, exist_ok=True)
    lock = root / "LOCK"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        sys.exit(f"run lock held: {lock.read_text().strip()}")
    os.write(fd, f"{socket.gethostname()} pid {os.getpid()} since {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n".encode())
    os.close(fd)
    (root / "coordinator.pid").write_text(f"{os.getpid()}\n")
    try:
        start = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        load = float(open("/proc/loadavg").read().split()[0])
        records, todo = {}, []
        for u, b in pairs:
            done = root / "done" / u / f"{b}.json"
            rec = json.loads(done.read_text()) if done.exists() else None
            if (rec is not None and rec["design_digest"] == D.reread_digest() and (root / rec["file"]["path"]).exists()
                    and sha(root / rec["file"]["path"]) == rec["file"]["sha256"]):
                records[(u, b)] = dict(rec, resumed=True)
            else:
                todo.append((u, b))
        print(f"{start} fit gain: {len(pairs)} tasks, {len(records)} resumed, {len(todo)} to run on cpus {cpus} "
              f"(1-min load {load})", flush=True)
        t0 = time.time()
        queue = mp.get_context("fork").Queue()
        for c in cpus:
            queue.put(c)
        with ProcessPoolExecutor(len(cpus), mp_context=mp.get_context("fork"), initializer=_pin, initargs=(queue,)) as pool:
            futures = {pool.submit(run_task, str(root), u, b, FM["tasks"][f"{u}/{b}"]["files"]): (u, b) for u, b in todo}
            for i, fut in enumerate(as_completed(futures), 1):
                u, b = futures[fut]
                rec = fut.result()
                records[(u, b)] = rec
                print(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} done {i}/{len(todo)} {u} {b} wall {rec['wall_s']} s "
                      f"cpu {rec['cpu_s']} s rss {rec['maxrss_mb']} MB bridge {'ok' if rec['bridge_all_equal'] else 'DIFFERS'}",
                      flush=True)
        recs = list(records.values())
        man = {"study": D.STUDY, "stage": "fit_gain", "tag": D4.FIT_TAG, "design_digest": D.digest(),
               "reread_digest": D.reread_digest(), "resumed": sorted(f"{u}/{b}" for (u, b), r in records.items() if r.get("resumed")),
               "sources": D.sources(LANE), "sm001_fit_manifest_sha256": sha(Path(D4.FIT_ROOT) / "manifest.json"),
               "pairs": [list(p) for p in pairs], "started_utc": start,
               "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "cpus": cpus, "workers": len(cpus),
               "load_1min_start": load, "wall_s": round(time.time() - t0, 1),
               "cpu_s_total": round(sum(r["cpu_s"] for r in recs), 1),
               "worker_maxrss_mb_peak": max(r["maxrss_mb"] for r in recs),
               "bridge_all_equal": all(r["bridge_all_equal"] for r in recs), "disk_free_bytes_end": shutil.disk_usage(root).free,
               "tasks": {f"{r['unit']}/{r['block']}": {"file": r["file"], "cpu_s": r["cpu_s"], "bridge_all_equal": r["bridge_all_equal"]}
                         for r in recs}}
        (root / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
        print(f"{man['finished_utc']} finished: wall {man['wall_s']} s, cpu {man['cpu_s_total']} s, bridges "
              f"{'all equal' if man['bridge_all_equal'] else 'NOT ALL EQUAL'}", flush=True)
    finally:
        lock.unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--root", type=Path, required=True)
    r.add_argument("--cpus", required=True)
    r.add_argument("--limit", default=None)
    a = ap.parse_args()
    cmd_run(a)


if __name__ == "__main__":
    main()
