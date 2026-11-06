"""SM003's FIT stage: SM001's own FIT records reread at g = 1 and g = 2 (no block drawn).

python -m sm003.fitread run --root RUN_ROOT/fit_reread --cpus LIST     (SM001's 48 FIT tasks; resumable)

Each task (unit, block) of SM001's FIT stage (sm001/fit, 910628-910643, the units W4_x32, W8_x32, W16_x32):
- its raw and endpoint shards are checked against SM001's FIT manifest by sha256, and its case set is enrolled as SM001
  enrolled it (purpose development) and checked against the shard's;
- every patch size's saved float32 final records (r, H, W), cast to float64, are read with SM001's tag (mse-sm001) and
  the thresholds theta zero (exact: SM001's THETA is 0), every arm's record and the paired no-record control (gain 0),
  at g = 1 (sm001.sim.successor, u's stream: it must reproduce SM001's saved successor endpoints at every read, bit for
  bit, the bridge) and g = 2 (sm002.coarse.read_cg, stream dw-cg: a stream SM001 never drew);
- writes fit_reread/shards/UNIT/BLOCK.npz (L{L}/g1/{e} and L{L}/g2/{e}, each (arms + 1, cases), at the last read),
  fit_reread/done/UNIT/BLOCK.json (with the bridge's result), and a manifest.
This is training data SM001 already saw: SM001's model was fitted on its g = 1 values. It is not a test.
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
from sm001 import sim as S1  # noqa: E402
from sm003 import design as D  # noqa: E402
from sm003 import readers as RD  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# the bridge: every successor endpoint at every read equal to SM001's saved one bit for bit, except the spacing. The reread
# reads the float32-stored records, SM001's successor read them in float64: that rounding moves the final body by at most
# about one float32 step at a few sites (the smoke: 6e-8 at 2 of 376,832 sites at L 8), which leaves every sign-based
# endpoint exact (as SM002's u32 reread found) and moves the spacing, a ratio of spectral sums, in its last bits. The
# body's largest difference and the spacing's largest relative difference are recorded, not gated.
FFT_ENDS = ("spacing",)


def fit_manifest():
    return json.loads((Path(D.FIT_ROOT) / "manifest.json").read_text())


def task(unit, block, files, fit_root=D.FIT_ROOT):
    fit_root = Path(fit_root)
    for f in files.values():
        if sha(fit_root / f["path"]) != f["sha256"]:
            raise ValueError(f"{f['path']}: sha256 differs from SM001's FIT manifest")
    cfg = S1D.UNIT[unit]
    side, w = cfg["side"], cfg["w"]
    na = len(S1D.unit_arms(unit))
    raw, z = np.load(fit_root / "raw" / unit / f"{block}.npz"), np.load(fit_root / "shards" / unit / f"{block}.npz")
    meta = json.loads(str(z["__meta__"]))
    if meta["tag"] != D.FIT_TAG or meta["design_digest"] != S1D.digest() or meta["arms"] != [a["name"] for a in S1D.unit_arms(unit)]:
        raise ValueError(f"{unit} {block}: the shard is not SM001's frozen FIT task")
    cases = enrol([block], D2.MESSAGES, D2.PARENTS, D.FIT_PURPOSE)
    if [list(c.key()) for c in cases] != [list(x) for x in meta["cases"]]:
        raise ValueError(f"{unit} {block}: the case set differs from the shard's")
    k = len(cases)
    T = raw["T"].astype(np.float64)
    th = np.zeros_like(T)
    gains = [S1D.GAIN] * na + [0.0]
    ends, bridge, timing = {}, {}, {}
    for L in cfg["sizes"]:
        rn = f"L{L}"
        m = raw[f"{rn}/m"]
        pick = lambda x: np.concatenate([x, x[:k]])          # every arm's final record, then the control's (unread)
        r, H, W = (pick(raw[f"{rn}/{x}"].astype(np.float64).reshape(na * k, side, side)) for x in ("r", "H", "W"))
        t1 = time.time()
        o1 = S1.successor(r, H, W, cases, th, T, m, side, w, gains, tag=D.FIT_TAG, reads=S1D.READS2)
        timing[f"{rn}/g1"] = round(time.time() - t1, 3)
        got = {e: o1[e].reshape(len(S1D.READS2), na + 1, k) for e in S1.ENDS2}
        same = {e: bool(np.array_equal(got[e], z[f"{rn}/s/{e}"])) for e in S1.ENDS2 if e not in FFT_ENDS}
        rel = {e: float((np.abs(got[e] - z[f"{rn}/s/{e}"]) / np.abs(z[f"{rn}/s/{e}"])).max()) for e in FFT_ENDS}
        dV = np.abs(o1["V"].reshape(na + 1, k, side, side) - raw[f"{rn}/sV"].astype(np.float64))
        bridge[rn] = {"all_equal": all(same.values()), "exact": same, "spacing_rel_max": rel["spacing"],
                      "V_max_abs_diff": float(dV.max()), "max_abs_in": float(np.abs(got["in"] - z[f"{rn}/s/in"]).max())}
        for e in RD.ENDS:
            ends[f"{rn}/g1/{e}"] = o1[e][-1].reshape(na + 1, k)
        t1 = time.time()
        o2 = RD.read_g2(r, H, W, cases, th, T, m, side, w, gains, D.FIT_TAG)
        timing[f"{rn}/g2"] = round(time.time() - t1, 3)
        for e in RD.ENDS:
            ends[f"{rn}/g2/{e}"] = o2[e].reshape(na + 1, k)
        ends[f"{rn}/g2/ties"] = o2["ties"][: na * k].reshape(na, k).astype(float)
    return ends, bridge, timing, meta


def run_task(root, unit, block, files):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    ends, bridge, timing, smeta = task(unit, block, files)
    meta = {"study": D.STUDY, "stage": "fit_reread", "unit": unit, "block": block, "tag": D.FIT_TAG,
            "design_digest": D.digest(), "sm001_digest": S1D.digest(), "grains": list(D.FIT_GRAINS),
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
           "bridge": bridge, "bridge_all_equal": all(b["all_equal"] for b in bridge.values()),
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
    try:
        start = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        load = float(open("/proc/loadavg").read().split()[0])
        records, todo = {}, []
        for u, b in pairs:
            done = root / "done" / u / f"{b}.json"
            rec = json.loads(done.read_text()) if done.exists() else None
            if (rec is not None and rec["design_digest"] == D.digest() and (root / rec["file"]["path"]).exists()
                    and sha(root / rec["file"]["path"]) == rec["file"]["sha256"]):
                records[(u, b)] = dict(rec, resumed=True)
            else:
                todo.append((u, b))
        print(f"{start} fit reread: {len(pairs)} tasks, {len(records)} resumed, {len(todo)} to run on cpus {cpus} "
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
                print(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} fit reread {i}/{len(todo)} {u} {b} cpu "
                      f"{rec['cpu_s']} s rss {rec['maxrss_mb']} MB bridge {'ok' if rec['bridge_all_equal'] else 'DIFFERS'}",
                      flush=True)
        recs = list(records.values())
        man = {"study": D.STUDY, "stage": "fit_reread", "tag": D.FIT_TAG, "design_digest": D.digest(),
               "sources": D.sources(LANE), "sm001_fit_manifest_sha256": sha(Path(D.FIT_ROOT) / "manifest.json"),
               "pairs": [list(p) for p in pairs], "started_utc": start,
               "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "cpus": cpus, "workers": len(cpus),
               "load_1min_start": load, "wall_s": round(time.time() - t0, 1),
               "cpu_s_total": round(sum(r["cpu_s"] for r in recs), 1),
               "worker_maxrss_mb_peak": max(r["maxrss_mb"] for r in recs),
               "bridge_all_equal": all(r["bridge_all_equal"] for r in recs), "disk_free_bytes_end": shutil.disk_usage(root).free,
               "tasks": {f"{r['unit']}/{r['block']}": {"file": r["file"], "bridge_all_equal": r["bridge_all_equal"],
                                                        "cpu_s": r["cpu_s"]} for r in recs}}
        (root / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
        print(f"{man['finished_utc']} fit reread finished: wall {man['wall_s']} s, cpu {man['cpu_s_total']} s, "
              f"bridge {'all equal' if man['bridge_all_equal'] else 'NOT ALL EQUAL'}", flush=True)
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
