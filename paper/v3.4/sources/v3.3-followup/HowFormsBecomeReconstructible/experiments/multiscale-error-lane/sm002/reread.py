"""SM002's two declared rereads (reported, not registered; the lead's review of 31 October 2026, rulings 3 and 4), run on
a stage's saved final records after the stage:

python -m sm002.reread run --root STAGE_ROOT --cpus LIST   ->  STAGE_ROOT/reread/{shards,done}/UNIT/BLOCK, manifest.json
python -m sm002.reread read --root STAGE_ROOT --out DIR    ->  DIR/reread.json, DIR/REREAD.md

Every reread reads the raw shard's float32 final records (r, H, W), cast to float64, with the stage's case set (enrolled
as the stage enrolled it, its keys checked against the shard's), patches and templates, and theta's thresholds zero
(exact: SM001's THETA is 0, so the successor adds th x THETA = +-0 after the well's asymmetry 0.0, which changes no sum).
Four readers, each branch with its paired no-record control (gain 0):
  u32    the unscaled reader (sm001.sim.successor at the full side, u's stream name) on the float32 record: avgu's base
  avgu   the declared coarse record (sm002.coarse.coarse_grain) upsampled back to the full side (sm002.coarse.upsample),
         read by the unscaled reader at the full side with u's stream name, so paired with u's draws, and scored as u is:
         the record's coarse-graining alone
  cg32   the cg reader with the declared tie rule on the float32 record (read_coarse: sm002.coarse.read_cg's read and
         scoring on a given coarse record): cg+1's base
  cg+1   the cg reader with every tie set to +1 (P43t's method), with cg's stream name
A control reads no record, so each reader's control must equal the saved one bit for bit (u32's and avgu's u's, cg32's
and cg+1's cg's): the pairing check, recorded per task. The float32 rounding's effect is reported (u32 - u, cg32 - cg).

The reported contrasts (read), with E the patch agreement at the reader's last read, the twin as in sm002.analyze, late
m 2 and prompt m 0, each over the refined conditions r and their twins t, against u32 (all from the same float32 records):
  the +1 rule   T2 X(r) - u32(t); T3 X(r) - u32(r); T4 (X - u32)(r) - (X - u32)(t); T5 X(t) - u32(t); for X = cg+1 and
                X = cg32 (the declared rule, reread), overall and per patch size; the rule's effect cg+1 - cg32 on r and t
  avg-u         avgu - u32 (the coarse-graining alone) and cg32 - avgu (the reader's doubled lengths, given the coarse
                record), each on r, on t and their difference in differences, overall and per patch size
  float32       u32 - u and cg32 - cg, on r and t
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
import socket  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from dl002 import design as D2  # noqa: E402
from lr005 import sim as L5S  # noqa: E402
from mse.assay import enrol  # noqa: E402
from sm001 import design as S1D  # noqa: E402
from sm001 import sim as S1  # noqa: E402
from sm002 import analyze as A  # noqa: E402
from sm002 import coarse as C  # noqa: E402
from sm002 import design as D  # noqa: E402
from sm002 import predict as P  # noqa: E402

FROZEN = LANE / "sm002" / "frozen"
READERS = ("u32", "avgu", "cg32", "cgp1")
ENDS = ("in", "in_gen")


def coarse_grain_plus_one(r, H, W):
    """The declared coarse values; a coarse bond the majority of the two crossing fine bonds, every tie +1."""
    rc = C.coarse_values(r)
    hs = H[..., 0::2, 1::2] + H[..., 1::2, 1::2]
    ws = W[..., 1::2, 0::2] + W[..., 1::2, 1::2]
    return rc, np.where(hs != 0, np.sign(hs), 1.0), np.where(ws != 0, np.sign(ws), 1.0)


def read_coarse(rc, Hc, Wc, cases, th, T, m, side, w, gains, tag, window=D.WINDOW2, stream=D.CG_STREAM):
    """sm002.coarse.read_cg after its coarse-graining: the given coarse record read by sm001.sim.successor at side / 2,
    the final body lifted back and scored on the full grid (the last read's endpoints only)."""
    k, nb = len(cases), len(gains)
    o = S1.successor(rc, Hc, Wc, cases, C.coarse_values(th), C.coarse_template(T), C.coarse_mask(m), side // 2, w // 2,
                     gains, tag=tag, window=window, reads=(window,), stream=stream)
    idx = np.tile(np.arange(k), nb)
    Vf = C.lift(o["V"])
    return {"in": L5S.inside(Vf, T[idx], m[idx]), "in_gen": S1.in_generic(Vf, T[idx], m[idx], w), "V": o["V"]}


def read_full(r, H, W, cases, th, T, m, side, w, gains, tag, window=D.WINDOW2):
    """The unscaled reader (sm001.sim.successor at the full side, u's stream name): the last read's endpoints."""
    o = S1.successor(r, H, W, cases, th, T, m, side, w, gains, tag=tag, window=window, reads=(window,))
    return {"in": o["in"][-1], "in_gen": o["in_gen"][-1], "V": o["V"]}


def readers(r, H, W, cases, th, T, m, side, w, gains, tag, window=D.WINDOW2):
    """The four rereads of one patch size's records (r, H, W: (nb x k, side, side), branch-major)."""
    rc, Hc, Wc = C.coarse_grain(r, H, W)
    return {"u32": read_full(r, H, W, cases, th, T, m, side, w, gains, tag, window),
            "avgu": read_full(*C.upsample(rc, Hc, Wc), cases, th, T, m, side, w, gains, tag, window),
            "cg32": read_coarse(rc, Hc, Wc, cases, th, T, m, side, w, gains, tag, window),
            "cgp1": read_coarse(*coarse_grain_plus_one(r, H, W), cases, th, T, m, side, w, gains, tag, window)}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def task(root, unit, block, stage, tag, files):
    """One (unit, block): the stage's raw and endpoint shards checked against its manifest, then the four rereads of every
    patch size, the controls checked against the saved ones, the float32 differences recorded."""
    root = Path(root)
    for f in files.values():
        if sha(root / f["path"]) != f["sha256"]:
            raise ValueError(f"{f['path']}: sha256 differs from the stage manifest")
    cfg = S1D.UNIT[unit]
    side, w = cfg["side"], cfg["w"]
    na = len(D.unit_arms(unit))
    raw, z = np.load(root / "raw" / unit / f"{block}.npz"), np.load(root / "shards" / unit / f"{block}.npz")
    cases = enrol([block], D2.MESSAGES, D2.PARENTS, D.PURPOSE[stage])
    if [list(c.key()) for c in cases] != [list(x) for x in json.loads(str(z["__meta__"]))["cases"]]:
        raise ValueError(f"{unit} {block}: the case set differs from the shard's")
    k = len(cases)
    T = raw["T"].astype(np.float64)
    th = np.zeros_like(T)
    gains = [D.GAIN] * na + [0.0]
    ends, checks, timing = {}, {}, {}
    for L in cfg["sizes"]:
        rn = f"L{L}"
        m = raw[f"{rn}/m"]
        pick = lambda x: np.concatenate([x, x[:k]])          # every arm's final record, then the control's (unread)
        r, H, W = (pick(raw[f"{rn}/{x}"].astype(np.float64).reshape(na * k, side, side)) for x in ("r", "H", "W"))
        t1 = time.time()
        out = readers(r, H, W, cases, th, T, m, side, w, gains, tag)
        timing[rn] = round(time.time() - t1, 3)
        for name, o in out.items():
            for e in ENDS:
                ends[f"{rn}/{name}/{e}"] = o[e].reshape(na + 1, k)
        su, sc = z[f"{rn}/u/in"][-1], z[f"{rn}/cg/in"]
        sug, scg = z[f"{rn}/u/in_gen"][-1], z[f"{rn}/cg/in_gen"]
        checks[rn] = {
            "controls_equal": bool(all(np.array_equal(ends[f"{rn}/{x}/in"][na], (su if x in ("u32", "avgu") else sc)[na])
                                       and np.array_equal(ends[f"{rn}/{x}/in_gen"][na], (sug if x in ("u32", "avgu") else scg)[na])
                                       for x in READERS)),
            "max_abs_u32_minus_u": float(np.abs(ends[f"{rn}/u32/in"][:na] - su[:na]).max()),
            "max_abs_cg32_minus_cg": float(np.abs(ends[f"{rn}/cg32/in"][:na] - sc[:na]).max()),
            "cases_u32_differ": int((ends[f"{rn}/u32/in"][:na] != su[:na]).sum()),
            "cases_cg32_differ": int((ends[f"{rn}/cg32/in"][:na] != sc[:na]).sum())}
    return ends, checks, timing


def run_task(root, unit, block, stage, tag, files):
    t_wall, t_cpu = time.time(), time.process_time()
    root = Path(root)
    ends, checks, timing = task(root, unit, block, stage, tag, files)
    meta = {"unit": unit, "block": block, "stage": stage, "tag": tag, "design_digest": D.digest(), "readers": READERS,
            "numpy": np.__version__, "timing_s": timing}
    folder = root / "reread" / "shards" / unit
    folder.mkdir(parents=True, exist_ok=True)
    final = folder / f"{block}.npz"
    tmp = folder / f".{block}.{os.getpid()}.tmp.npz"
    np.savez(tmp, __meta__=np.array(json.dumps(meta)), **ends)
    os.replace(tmp, final)
    rec = {"unit": unit, "block": block, "stage": stage, "tag": tag, "design_digest": D.digest(),
           "file": {"path": str(final.relative_to(root)), "sha256": sha(final), "bytes": final.stat().st_size},
           "checks": checks, "wall_s": round(time.time() - t_wall, 2), "cpu_s": round(time.process_time() - t_cpu, 2),
           "maxrss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
           "cpu": sorted(os.sched_getaffinity(0)), "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    done = root / "reread" / "done" / unit / f"{block}.json"
    done.parent.mkdir(parents=True, exist_ok=True)
    tmpd = done.with_suffix(f".{os.getpid()}.tmp")
    tmpd.write_text(json.dumps(rec, indent=1) + "\n")
    os.replace(tmpd, done)
    return rec


def _pin(queue):
    os.sched_setaffinity(0, {queue.get()})


def refuse_unless_frozen(stage):
    """A development stage's rereads run the frozen module only."""
    if stage != "dev":
        return
    frozen = json.loads((FROZEN / "design.json").read_text())
    now = D.sources(LANE)
    changed = sorted(k for k in set(frozen["sources"]) | set(now) if frozen["sources"].get(k) != now.get(k))
    if frozen["digest"] != D.digest() or changed:
        sys.exit(f"the design or sources differ from the frozen ones ({changed}): refusing the development's rereads")


def cmd_run(a):
    root = a.root.resolve()
    M = json.loads((root / "manifest.json").read_text())
    stage, tag = M["stage"], M["tag"]
    refuse_unless_frozen(stage)
    cpus = [int(c) for c in a.cpus.split(",")]
    os.sched_setaffinity(0, cpus)
    pairs = [tuple(p) for p in M["pairs"]]
    out = root / "reread"
    out.mkdir(exist_ok=True)
    lock = out / "LOCK"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        sys.exit(f"reread lock held: {lock.read_text().strip()}")
    os.write(fd, f"{socket.gethostname()} pid {os.getpid()} since {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n".encode())
    os.close(fd)
    try:
        start = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        load = float(open("/proc/loadavg").read().split()[0])
        records, todo = {}, []
        for u, b in pairs:
            done = out / "done" / u / f"{b}.json"
            rec = json.loads(done.read_text()) if done.exists() else None
            if rec is not None and (out / "shards" / u / f"{b}.npz").exists() and sha(out / "shards" / u / f"{b}.npz") == rec["file"]["sha256"]:
                records[(u, b)] = dict(rec, resumed=True)
            else:
                todo.append((u, b))
        print(f"{start} reread {stage}: {len(pairs)} tasks, {len(records)} resumed, {len(todo)} to run on cpus {cpus} "
              f"(1-min load {load})", flush=True)
        t0 = time.time()
        queue = mp.get_context("fork").Queue()
        for c in cpus:
            queue.put(c)
        with ProcessPoolExecutor(len(cpus), mp_context=mp.get_context("fork"), initializer=_pin, initargs=(queue,)) as pool:
            futures = {pool.submit(run_task, str(root), u, b, stage, tag, M["tasks"][f"{u}/{b}"]["files"]): (u, b)
                       for u, b in todo}
            for i, fut in enumerate(as_completed(futures), 1):
                u, b = futures[fut]
                rec = fut.result()
                records[(u, b)] = rec
                print(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} reread {i}/{len(todo)} {u} {b} "
                      f"cpu {rec['cpu_s']} s rss {rec['maxrss_mb']} MB", flush=True)
        recs = list(records.values())
        man = {"stage": stage, "tag": tag, "design_digest": D.digest(), "sources": D.sources(LANE), "started_utc": start,
               "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "cpus": cpus, "load_1min_start": load,
               "wall_s": round(time.time() - t0, 1), "cpu_s_total": round(sum(r["cpu_s"] for r in recs), 1),
               "worker_maxrss_mb_peak": max(r["maxrss_mb"] for r in recs),
               "stage_manifest_sha256": sha(root / "manifest.json"),
               "tasks": {f"{r['unit']}/{r['block']}": {"file": r["file"], "checks": r["checks"], "cpu_s": r["cpu_s"]}
                         for r in recs}}
        (out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
        print(f"{man['finished_utc']} reread finished: wall {man['wall_s']} s, cpu {man['cpu_s_total']} s", flush=True)
    finally:
        lock.unlink(missing_ok=True)


# the reported contrasts -------------------------------------------------------------------------------------------

def rows_of(root):
    """sm002.analyze's rows with each reread's E (keys E_u32, E_avgu, E_cg32, E_cgp1), twins attached."""
    root = Path(root)
    M = json.loads((root / "manifest.json").read_text())
    RM = json.loads((root / "reread" / "manifest.json").read_text())
    if RM["stage_manifest_sha256"] != sha(root / "manifest.json"):
        raise ValueError("the rereads were made from another stage manifest")
    pairs = [tuple(p) for p in M["pairs"]]
    Z, _ = A.load(root, pairs)
    ZR = {}
    for u, b in pairs:
        f = RM["tasks"][f"{u}/{b}"]["file"]
        if sha(root / f["path"]) != f["sha256"]:
            raise ValueError(f"{f['path']}: sha256 differs from the reread manifest")
        ZR[(u, b)] = dict(np.load(root / f["path"]))
    rows = A.conditions(Z, pairs)
    for r in rows:
        ai = [a["name"] for a in D.unit_arms(r["unit"])].index(r["arm"])
        for x in READERS:
            r[f"E_{x}"] = np.array([ZR[(r["unit"], b)][f"L{r['L']}/{x}/in"][ai] for b in r["blocks"]])
    return A.attach_twins(rows), RM


def _refined(R, m, L=None):
    out = [r for r in R if r["kind"] == "refine" and r["m"] == m and (L is None or r["L"] == L)]
    if not out:
        raise ValueError(f"no refined rows at m {m} L {L}")
    return out


def over(R, m, f, L=None):
    """Per case, the mean over the refined conditions at m (and patch size L) of f(row, its twin)."""
    return np.mean([f(r, r["twin"]) for r in _refined(R, m, L)], axis=0)


def contrasts():
    out = {}
    for m, s in ((2, "late"), (0, "prompt")):
        for L in (None, 4, 8, 16):
            at = "" if L is None else f", L {L}"
            for x, lab in (("E_cgp1", "cg+1"), ("E_cg32", "cg32")):
                out[f"{lab} {s}{at}: T2 {lab} - u32(twin)"] = lambda R, m=m, L=L, x=x: over(R, m, lambda r, t: r[x] - t["E_u32"], L)
                out[f"{lab} {s}{at}: T3 {lab} - u32 (refined)"] = lambda R, m=m, L=L, x=x: over(R, m, lambda r, t: r[x] - r["E_u32"], L)
                out[f"{lab} {s}{at}: T4 ({lab} - u32) - ({lab} - u32)(twin)"] = (
                    lambda R, m=m, L=L, x=x: over(R, m, lambda r, t: (r[x] - r["E_u32"]) - (t[x] - t["E_u32"]), L))
                out[f"{lab} {s}{at}: T5 {lab}(twin) - u32(twin)"] = lambda R, m=m, L=L, x=x: over(R, m, lambda r, t: t[x] - t["E_u32"], L)
            out[f"rule {s}{at}: cg+1 - cg32 (refined)"] = lambda R, m=m, L=L: over(R, m, lambda r, t: r["E_cgp1"] - r["E_cg32"], L)
            out[f"rule {s}{at}: cg+1 - cg32 (twin)"] = lambda R, m=m, L=L: over(R, m, lambda r, t: t["E_cgp1"] - t["E_cg32"], L)
            for a, b, lab in (("E_avgu", "E_u32", "avgu - u32"), ("E_cg32", "E_avgu", "cg32 - avgu")):
                out[f"avg-u {s}{at}: {lab} (refined)"] = lambda R, m=m, L=L, a=a, b=b: over(R, m, lambda r, t: r[a] - r[b], L)
                out[f"avg-u {s}{at}: {lab} (twin)"] = lambda R, m=m, L=L, a=a, b=b: over(R, m, lambda r, t: t[a] - t[b], L)
                out[f"avg-u {s}{at}: {lab}, difference in differences"] = (
                    lambda R, m=m, L=L, a=a, b=b: over(R, m, lambda r, t: (r[a] - r[b]) - (t[a] - t[b]), L))
        for a, b, lab in (("E_u32", "E_u", "u32 - u"), ("E_cg32", "E_cg", "cg32 - cg")):
            out[f"float32 {s}: {lab} (refined)"] = lambda R, m=m, a=a, b=b: over(R, m, lambda r, t: r[a] - r[b])
            out[f"float32 {s}: {lab} (twin)"] = lambda R, m=m, a=a, b=b: over(R, m, lambda r, t: t[a] - t[b])
    return out


def cmd_read(a):
    rows, RM = rows_of(a.root)
    res = {name: P.part_record(f(rows)) for name, f in contrasts().items()}
    ck = [c for t in RM["tasks"].values() for c in t["checks"].values()]
    checks = {"tasks": len(RM["tasks"]), "controls_equal": all(c["controls_equal"] for c in ck),
              "max_abs_u32_minus_u": max(c["max_abs_u32_minus_u"] for c in ck),
              "max_abs_cg32_minus_cg": max(c["max_abs_cg32_minus_cg"] for c in ck),
              "cases_u32_differ": sum(c["cases_u32_differ"] for c in ck),
              "cases_cg32_differ": sum(c["cases_cg32_differ"] for c in ck),
              "reread_cpu_s": RM["cpu_s_total"], "reread_manifest": "reread/manifest.json"}
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "reread.json").write_text(json.dumps({"stage": RM["stage"], "tag": RM["tag"], "checks": checks,
                                                   "contrasts": res}, indent=1) + "\n")
    Lm = [f"# SM002 rereads ({RM['stage']}, {checks['tasks']} tasks; reported, not registered)", "",
          f"Checks: every control equal to the saved one bit for bit: {checks['controls_equal']}. Float32 rereading: "
          f"max |u32 - u| {checks['max_abs_u32_minus_u']:.4f} ({checks['cases_u32_differ']} case values differ), max |cg32 - cg| "
          f"{checks['max_abs_cg32_minus_cg']:.4f} ({checks['cases_cg32_differ']} differ).", "",
          "| Contrast | Value [95%] | SD (block, case) | Halves |", "|---|---|---|---|"]
    for name, p in res.items():
        Lm.append(f"| {name} | {p['value']:+.4f} [{p['ci95'][0]:+.4f}, {p['ci95'][1]:+.4f}] | {p['sd']:.4f} "
                  f"({p['sd4']:.4f}, {p['sdc']:.4f}) | {', '.join(f'{h:+.4f}' for h in p['halves'])} |")
    (a.out / "REREAD.md").write_text("\n".join(Lm) + "\n")
    print(json.dumps(checks))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--root", type=Path, required=True)
    r.add_argument("--cpus", required=True)
    q = sub.add_parser("read")
    q.add_argument("--root", type=Path, required=True)
    q.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    cmd_run(a) if a.cmd == "run" else cmd_read(a)


if __name__ == "__main__":
    main()
