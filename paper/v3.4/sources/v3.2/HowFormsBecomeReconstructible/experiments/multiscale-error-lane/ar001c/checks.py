"""Qualification of AR001C on its debug run (AR001's engineering blocks 900029-900032); criteria fixed in advance.

python -m ar001c.checks --root DEBUG_ROOT --cpus LIST   (writes ROOT/debug_qualification_receipt.json; with --receipt-to-frozen
                                                       the receipt goes to ar001c/frozen/qualification_receipt.json)

Q1  complete and finite: every task's shard holds every reduced run's endpoints at its declared shape (reads x 3 arms x 8
    cases; r_in_old exactly in change@0), its trace, scalars, n_anc and n_mis; every value finite
Q2  serial = parallel: one task rerun in-process gives bit-identical shards and raw states
Q3  the bridge: on every debug task, every reduced branch equals the full AR001 task's corresponding branch bit for bit,
    against AR001's own preflight (900029-900030) and debug (900031-900032) outputs: every endpoint at every read, the
    trace, opened, opened_out, onset, hit, n_anc and n_mis, and the final V, r, H, W (and the vote's second record rB, HB,
    WB), plus the acquisition V0, R0 and T
Q9  resources: the confirmation (16 blocks x 8 pairs) forecast within 12 h of wall on 12 workers, worker memory within
    2 GB, disk headroom; the full arm set priced from AR001's development manifest beside it
Q10 reader dry run: ar001c.analyze completes on the debug shards, scores C1, C2 and C3 and the verdict, and writes
    confirmation.json and TABLES.md, each 256 KB or less
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from ar001 import design as A  # noqa: E402
from ar001 import worker as AW  # noqa: E402
from ar001c import design as D  # noqa: E402
from ar001c import worker as W  # noqa: E402

FROZEN = LANE / "ar001c" / "frozen"
AR001_RUNS = Path("/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/ar001")
AR001_DEV_MANIFEST = AR001_RUNS / "development" / "manifest.json"
WORKERS = 12
FULL = {A.run_name(*x): list(x[2]) for x in A.RUNS}


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


def bridge_one(root, body, unit, block):
    """Every reduced branch of one task against the full AR001 task's, bit for bit; returns the list of mismatches."""
    ref_root = AR001_RUNS / D.BRIDGE_ROOTS[block]
    e, r = npz(root / "shards" / body / unit / f"{block}.npz"), npz(root / "raw" / body / unit / f"{block}.npz")
    E, Rr = npz(ref_root / "shards" / body / unit / f"{block}.npz"), npz(ref_root / "raw" / body / unit / f"{block}.npz")
    bad = []
    for x in ("V0", "R0", "T"):
        if not (r[x].dtype == Rr[x].dtype and np.array_equal(r[x], Rr[x])):
            bad.append(x)
    for situation, sigma, arms in D.RUNS:
        rn = D.run_name(situation, sigma)
        full = FULL[rn]
        for i, arm in enumerate(arms):
            j = full.index(arm)
            for ep in AW.ENDS + AW.SCALARS + ("trace",):
                key = f"{rn}/{ep}"
                if (key in e) != (key in E):
                    bad.append(f"{rn}/{ep}: present in one only")
                    continue
                if key not in e:
                    continue
                got, want = (e[key][:, i], E[key][:, j]) if e[key].ndim == 3 else (e[key][i], E[key][j])
                if not (got.dtype == want.dtype and np.array_equal(got, want)):
                    bad.append(f"{rn}/{ep}/{arm}")
            for x in ("V", "r", "H", "W"):
                got, want = r[f"{rn}/{x}"][i], Rr[f"{rn}/{x}"][j]
                if not (got.dtype == want.dtype and np.array_equal(got, want)):
                    bad.append(f"{rn}/{x}/{arm}")
        for x in ("n_anc", "n_mis"):
            if not np.array_equal(e[f"{rn}/{x}"], E[f"{rn}/{x}"]):
                bad.append(f"{rn}/{x}")
        if "vote" in arms:
            for x in ("rB", "HB", "WB"):
                got, want = r[f"{rn}/{x}"], Rr[f"{rn}/{x}"]
                if not (got.dtype == want.dtype and np.array_equal(got, want)):
                    bad.append(f"{rn}/{x}")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--cpus", required=True)
    ap.add_argument("--receipt-to-frozen", action="store_true")
    a = ap.parse_args()
    cpus = [int(c) for c in a.cpus.split(",")]
    os.sched_setaffinity(0, cpus)
    root, t0 = a.root.resolve(), time.time()
    blocks = D.stage_blocks("debug")
    manifest = json.loads((root / "manifest.json").read_text())
    receipt_path = FROZEN / "qualification_receipt.json" if a.receipt_to_frozen else root / "debug_qualification_receipt.json"
    checks = {}

    missing = []
    ntr = A.WINDOW // A.TRACE
    for body, u in D.tasks():
        for blk in blocks:
            path = root / "shards" / body / u / f"{blk}.npz"
            if not path.exists():
                missing.append(f"{body}/{u}/{blk}")
                continue
            e = npz(path)
            bad = [k for k, v in e.items() if not np.isfinite(v).all()]
            for situation, sigma, arms in D.RUNS:
                rn, na = D.run_name(situation, sigma), len(arms)
                for x in AW.ENDS:
                    if x == "r_in_old":
                        want = (len(A.READS), na, A.NCASE) if situation == "change" else None
                        got = e[f"{rn}/{x}"].shape if f"{rn}/{x}" in e else None
                        bad += [f"{rn}/{x}"] if got != want else []
                    elif e.get(f"{rn}/{x}", np.zeros(0)).shape != (len(A.READS), na, A.NCASE):
                        bad.append(f"{rn}/{x}")
                bad += [f"{rn}/{x}" for x in AW.SCALARS if e.get(f"{rn}/{x}", np.zeros(0)).shape != (na, A.NCASE)]
                bad += [f"{rn}/{x}" for x in ("n_anc", "n_mis") if e.get(f"{rn}/{x}", np.zeros(0)).shape != (A.NCASE,)]
                bad += [f"{rn}/trace"] if e.get(f"{rn}/trace", np.zeros(0)).shape != (ntr, na, A.NCASE) else []
            missing += [f"{body}/{u}/{blk}/{k}" for k in bad]
    checks["Q1_complete_finite"] = {"pass": not missing, "missing": missing[:10], "tasks": len(manifest["tasks"])}

    serial = root / "serial_check"
    shutil.rmtree(serial, ignore_errors=True)
    same = {}
    body, u = D.tasks()[0]
    W.run_task(body, u, blocks[0], "engineering", str(serial))
    for kind in ("shards", "raw"):
        x, y = npz(root / kind / body / u / f"{blocks[0]}.npz"), npz(serial / kind / body / u / f"{blocks[0]}.npz")
        same[f"{kind}/{body}/{u}/{blocks[0]}"] = bool(x.keys() == y.keys() and all(np.array_equal(x[k], y[k]) for k in x))
    checks["Q2_serial_equals_parallel"] = {"pass": all(same.values()), "tasks": same}

    mism, n = {}, 0
    for body, u in D.tasks():
        for blk in blocks:
            bad = bridge_one(root, body, u, blk)
            n += 1
            if bad:
                mism[f"{body}/{u}/{blk}"] = bad[:10]
    n_branches = n * sum(len(x[2]) for x in D.RUNS)
    checks["Q3_bridge_bit_for_bit"] = {"pass": not mism, "tasks_compared": n, "branches_compared": n_branches,
                                       "reference": "AR001's preflight (900029-900030) and debug (900031-900032) outputs",
                                       "mismatched": mism}

    cpu = [t["cpu_s"] for t in manifest["tasks"].values()]
    walls = [t["wall_s"] for t in manifest["tasks"].values()]
    n_conf = (D.IDENTITIES["confirmation"][1] - D.IDENTITIES["confirmation"][0]) * len(D.tasks())
    cpu_h = float(np.mean(cpu)) * n_conf / 3600
    wall_h = (float(np.mean(cpu)) * n_conf / WORKERS * 1.15 + max(walls)) / 3600
    dev = json.loads(AR001_DEV_MANIFEST.read_text())
    avail = int(next(l for l in open("/proc/meminfo") if l.startswith("MemAvailable")).split()[1]) * 1024
    per_task = manifest["bytes_written"] / len(manifest["tasks"])
    free = shutil.disk_usage(root).free
    checks["Q9_resources"] = {"pass": bool(wall_h <= 12 and manifest["worker_maxrss_mb_peak"] <= 2048
                                           and manifest["worker_maxrss_mb_peak"] * 2 ** 20 * WORKERS <= 0.8 * avail
                                           and per_task * n_conf <= 0.8 * free),
                              "reduced": {"cpu_s_per_task": round(float(np.mean(cpu)), 1), "forecast_cpu_h": round(cpu_h, 2),
                                          "forecast_wall_h_12": round(wall_h, 2), "tasks": n_conf,
                                          "worker_rss_mb": manifest["worker_maxrss_mb_peak"], "bytes_per_task": int(per_task)},
                              "full_from_ar001_development": {"cpu_s_per_task": round(dev["cpu_s_total"] / len(dev["tasks"]), 1),
                                                              "cpu_h": round(dev["cpu_s_total"] / 3600, 2),
                                                              "wall_h_12": round(dev["wall_s"] / 3600, 2),
                                                              "worker_rss_mb": dev["worker_maxrss_mb_peak"]}}

    out = root / "analysis_dry_run"
    out.mkdir(exist_ok=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.run([sys.executable, "-m", "ar001c.analyze", "--root", str(root), "--out", str(out)], cwd=LANE,
                          capture_output=True, text=True, env=env)
    files = [out / "confirmation.json", out / "TABLES.md"]
    got = json.loads(files[0].read_text()) if files[0].exists() else {}
    sizes = {q.name: q.stat().st_size for q in files if q.exists()}
    checks["Q10_reader_dry_run"] = {"pass": proc.returncode == 0 and all(q.exists() for q in files)
                                    and sorted(got.get("criteria", {})) == ["C1", "C2", "C3"] and "verdict" in got
                                    and max(sizes.values(), default=0) <= 262144,
                                    "stderr": proc.stderr[-600:], "sizes": sizes}

    failed = [k for k, v in checks.items() if not v["pass"]]
    receipt = {"status": "FAIL" if failed else "PASS", "failed": failed, "study": D.STUDY, "design_digest": D.digest(),
               "ar001_digest": A.digest(), "root": str(root), "blocks": [blocks[0], blocks[-1] + 1], "tag": D.TAG,
               "load_1min_at_check": float(open("/proc/loadavg").read().split()[0]),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "checks": checks}
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=1, default=float) + "\n")
    print(json.dumps({"status": receipt["status"], "failed": failed}, indent=1))


if __name__ == "__main__":
    main()
