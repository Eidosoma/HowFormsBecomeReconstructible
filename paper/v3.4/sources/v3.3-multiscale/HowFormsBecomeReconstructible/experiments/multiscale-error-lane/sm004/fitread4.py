"""SM004's third FIT grain: SM001's own FIT records reread at g = 4 where w >= 8 (no block drawn).

python -m sm004.fitread4 run --root RUN_ROOT/fit_g4 --cpus LIST [--limit UNIT/BLOCK,...]     (32 tasks; resumable)

Each task (unit, block) of SM001's FIT stage with w >= 8 (W8_x32, W16_x32; 910628-910643), as sm003.fitread reads g = 1
and 2:
- its raw and endpoint shards are checked against SM001's FIT manifest by sha256, and its case set is enrolled as SM001
  enrolled it (purpose development) and checked against the shard's;
- every patch size's saved float32 final records (r, H, W), cast to float64, are read with SM001's tag (mse-sm001) and
  the thresholds theta zero (SM001's THETA), every arm's record and the paired no-record control (gain 0), at g = 4 by
  sm003.readers.read_g4 (SM003's g-4 rule, unchanged: the declared 2 x 2 rule twice, read at side / 4 = 8 with stream
  dw-cg4, a stream no SM001 or SM003 run drew under mse-sm001; lifted x 4 and scored on the full grid);
- writes fit_g4/shards/UNIT/BLOCK.npz (L{L}/g4/{e}, each (arms + 1, cases), and L{L}/g4/V, the coarse final bodies in
  float32), fit_g4/done/UNIT/BLOCK.json, and a manifest.
These records are training data SM001 and SM003 saw at g = 1 and 2; the g = 4 values are new reads of them, not a test.
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

from dl002 import design as D2  # noqa: E402
from mse.assay import enrol  # noqa: E402
from sm001 import design as S1D  # noqa: E402
from sm003 import readers as RD  # noqa: E402
from sm004 import design as D  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fit_manifest():
    return json.loads((Path(D.FIT_ROOT) / "manifest.json").read_text())


def pairs():
    FM = fit_manifest()
    return [tuple(p) for p in FM["pairs"] if p[0] in D.FIT_G4_UNITS]


def load_records(unit, block, files, fit_root=D.FIT_ROOT):
    """SM001's FIT task's raw records, checked by sha256 and against SM001's frozen task and case set."""
    fit_root = Path(fit_root)
    for f in files.values():
        if sha(fit_root / f["path"]) != f["sha256"]:
            raise ValueError(f"{f['path']}: sha256 differs from SM001's FIT manifest")
    raw, z = np.load(fit_root / "raw" / unit / f"{block}.npz"), np.load(fit_root / "shards" / unit / f"{block}.npz")
    meta = json.loads(str(z["__meta__"]))
    if meta["tag"] != D.FIT_TAG or meta["design_digest"] != S1D.digest() or meta["arms"] != [a["name"] for a in S1D.unit_arms(unit)]:
        raise ValueError(f"{unit} {block}: the shard is not SM001's frozen FIT task")
    cases = enrol([block], D2.MESSAGES, D2.PARENTS, D.FIT_PURPOSE)
    if [list(c.key()) for c in cases] != [list(x) for x in meta["cases"]]:
        raise ValueError(f"{unit} {block}: the case set differs from the shard's")
    return raw, meta, cases


def branches(raw, rn, na, k, side):
    """Every arm's final record, then the control's (the first arm's record, read at gain 0), as float64."""
    pick = lambda x: np.concatenate([x, x[:k]])
    return tuple(pick(raw[f"{rn}/{x}"].astype(np.float64).reshape(na * k, side, side)) for x in ("r", "H", "W"))


def task(unit, block, files, fit_root=D.FIT_ROOT):
    cfg = S1D.UNIT[unit]
    side, w = cfg["side"], cfg["w"]
    if unit not in D.FIT_G4_UNITS:
        raise ValueError(f"{unit}: g = 4 reads only w >= 8 (SM003's g-4 rule)")
    raw, meta, cases = load_records(unit, block, files, fit_root)
    na, k = len(S1D.unit_arms(unit)), len(cases)
    T = raw["T"].astype(np.float64)
    th = np.zeros_like(T)
    gains = [S1D.GAIN] * na + [0.0]
    ends, timing = {}, {}
    for L in cfg["sizes"]:
        rn = f"L{L}"
        r, H, W = branches(raw, rn, na, k, side)
        t1 = time.time()
        o4 = RD.read_g4(r, H, W, cases, th, T, raw[f"{rn}/m"], side, w, gains, D.FIT_TAG)
        timing[f"{rn}/g4"] = round(time.time() - t1, 3)
        for e in RD.ENDS:
            ends[f"{rn}/g4/{e}"] = o4[e].reshape(na + 1, k)
        ends[f"{rn}/g4/V"] = o4["V"].reshape(na + 1, k, side // 4, side // 4).astype(np.float32)
    return ends, timing, meta


def run_task(root, unit, block, files):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    ends, timing, smeta = task(unit, block, files)
    bad = [kk for kk, v in ends.items() if not np.isfinite(v).all()]
    if bad:
        raise FloatingPointError(f"non-finite g-4 FIT reads in {unit} {block}: {bad[:5]}")
    meta = {"study": D.STUDY, "stage": "fit_g4", "unit": unit, "block": block, "tag": D.FIT_TAG,
            "design_digest": D.digest(), "sm001_digest": S1D.digest(), "grain": 4, "stream": D.STREAMS[4],
            "arms": smeta["arms"], "sizes": smeta["sizes"], "cases": smeta["cases"], "numpy": np.__version__,
            "timing_s": timing}
    folder = root / "shards" / unit
    folder.mkdir(parents=True, exist_ok=True)
    final = folder / f"{block}.npz"
    tmp = folder / f".{block}.{os.getpid()}.tmp.npz"
    np.savez(tmp, __meta__=np.array(json.dumps(meta)), **ends)
    os.replace(tmp, final)
    rec = {"unit": unit, "block": block, "design_digest": D.digest(),
           "file": {"path": str(final.relative_to(root)), "sha256": sha(final), "bytes": final.stat().st_size},
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
    FM = fit_manifest()
    todo_pairs = pairs()
    if a.limit:
        todo_pairs = [p for p in todo_pairs if f"{p[0]}/{p[1]}" in set(a.limit.split(","))]
    root.mkdir(parents=True, exist_ok=True)
    lock = root / "LOCK"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        sys.exit(f"run lock held: {lock.read_text().strip()}")
    os.write(fd, f"{socket.gethostname()} pid {os.getpid()} since {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n".encode())
    os.close(fd)
    try:
        start = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        load = float(open("/proc/loadavg").read().split()[0])
        records, todo = {}, []
        for u, b in todo_pairs:
            done = root / "done" / u / f"{b}.json"
            rec = json.loads(done.read_text()) if done.exists() else None
            if (rec is not None and rec["design_digest"] == D.digest() and (root / rec["file"]["path"]).exists()
                    and sha(root / rec["file"]["path"]) == rec["file"]["sha256"]):
                records[(u, b)] = dict(rec, resumed=True)
            else:
                todo.append((u, b))
        print(f"{start} fit g4: {len(todo_pairs)} tasks, {len(records)} resumed, {len(todo)} to run on cpus {cpus} "
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
                print(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} fit g4 {i}/{len(todo)} {u} {b} cpu "
                      f"{rec['cpu_s']} s rss {rec['maxrss_mb']} MB", flush=True)
        recs = list(records.values())
        man = {"study": D.STUDY, "stage": "fit_g4", "tag": D.FIT_TAG, "design_digest": D.digest(),
               "sources": D.sources(LANE), "sm001_fit_manifest_sha256": sha(Path(D.FIT_ROOT) / "manifest.json"),
               "pairs": [list(p) for p in todo_pairs], "started_utc": start,
               "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "cpus": cpus, "workers": len(cpus),
               "load_1min_start": load, "wall_s": round(time.time() - t0, 1),
               "cpu_s_total": round(sum(r["cpu_s"] for r in recs), 1),
               "worker_maxrss_mb_peak": max(r["maxrss_mb"] for r in recs), "disk_free_bytes_end": shutil.disk_usage(root).free,
               "tasks": {f"{r['unit']}/{r['block']}": {"file": r["file"], "cpu_s": r["cpu_s"]} for r in recs}}
        (root / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
        print(f"{man['finished_utc']} fit g4 finished: wall {man['wall_s']} s, cpu {man['cpu_s_total']} s", flush=True)
    finally:
        lock.unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--root", type=Path, required=True)
    r.add_argument("--cpus", required=True)
    r.add_argument("--limit", default=None, help="UNIT/BLOCK,... (the smoke)")
    a = ap.parse_args()
    if a.cmd == "run":
        cmd_run(a)


if __name__ == "__main__":
    main()
