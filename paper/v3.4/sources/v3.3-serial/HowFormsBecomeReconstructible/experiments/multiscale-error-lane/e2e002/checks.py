"""E2E002's qualification Q1-Q10 (DRAFT): python -m e2e002.checks --root STAGE_ROOT [--receipt PATH] [--cpus LIST]

Fixed in PLAN_E2E002.md before their results; in phase B they run on the preflight (AR005's 900779-900789).
  Q1  complete and finite: every task's endpoints and diagnostics at their shapes (rows alive at each horizon = rows
      whose stop reaches it; later futures the SECOND_FUTURE rows), finite; generation 0 for every row
  Q2  serial equals parallel: one task rerun in-process gives bit-identical endpoints, diagnostics and states
  Q3  the bridges: every restored raw file equals its manifest's sha256 (rehashed); the generation-0 replay
      (e2e002.sim.replay0, P58s's) of one task under memory@0 and none@0 reproduces every arm's saved final state bit for
      bit; every task's acquisition and generation-0 packets equal their sources (the workers' records)
  Q4  an independent replay: the first generation of protected and protected+vms-every (packet R0 with its bonds) for one
      task through ar003.sim.run_vd's own source, compiled with its event line replaced by the successor's birth state and
      its two stream lines by the future's names (each substitution asserted to apply once): equal to the lineage's saved
      generation-1 V, r, H and W bit for bit
  Q5  aliases: the alias table is complete (every label has a row; a row's labels share one packet); a row listed twice
      gives the same lineage bit for bit (500 updates)
  Q6  reanalysis: the endpoints recomputed from the saved states equal the shards'
  Q7  efficacy: the vote rows' detectors never fire; at sigma 0 every birth-cue row's anchors equal its incoming record's
      signs at birth (0 disagreeing), in every generation; at birth the second record equals the incoming record and the
      cue is built by the row's rule; post-damage differs from protected exactly in the patch; every task is a saved
      record of its stage
  Q8  pairing: reordering the rows changes no row's output (500 updates)
  Q9  resources: the development forecast structurally: this stage's CPU per vote-equivalent branch-generation (a vms
      branch-generation weighs W_VMS, P58s's measured ratio) times the development's own row-generations (its rows built
      at generation 0: packets compared, no successor run), within the lead's cap of 42 CPU-hours and 12 h of wall on
      12 workers; worker memory within 2 GB
  Q10 the reader's dry run: predict and tables complete, every part scored or marked unavailable, every output <= 256 KiB
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
from pathlib import Path
import sys
import tempfile
import time

import numpy as np

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from ar001 import design as A  # noqa: E402
from ar001 import sim as A1S  # noqa: E402
from ar003 import sim as S3  # noqa: E402
from ar005 import design as A5  # noqa: E402
from e2e002 import design as D  # noqa: E402
from e2e002 import sim  # noqa: E402
from e2e002 import worker as WK  # noqa: E402
from gc001 import sim as GCS  # noqa: E402
from lr005 import sim as L5S  # noqa: E402
from msegrid.core import birth  # noqa: E402
from sm005 import checks as K5  # noqa: E402  (the lane's parallel check runner, unchanged)
from sr001 import sim as SRS  # noqa: E402

CAP = 42.0                               # the lead's cap for phase B (ruling 4, about 11:10Z on 4 November)
W_VMS = 2.5                              # a vms branch-generation in vote branch-generations (P58s, the timing probes)


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}, json.loads(str(f["__meta__"]))


def tasks_of(root):
    M = json.loads((Path(root) / "manifest.json").read_text())
    out = []
    for name, t in sorted(M["tasks"].items()):
        src1, src2, body, unit, block = name.split("/")
        out.append((f"{src1}/{src2}", body, unit, int(block), t))
    return M, out


def alive_rows(meta, f, g):
    rows = meta["rows"]
    return [i for i, r in enumerate(rows) if r["stop"] >= g and (f == 0 or set(r["labels"]) & set(meta["second_future"]))]


def q1(root):
    M, tasks = tasks_of(root)
    bad = []
    for src, body, unit, block, t in tasks:
        ends, meta = npz(Path(root) / t["files"]["shards"]["path"])
        k = len(meta["cases"])
        nr = len(meta["rows"])
        for e in sim.E1.ENDPOINTS:
            if ends[f"g0/{e}"].shape != (nr, k) or not np.isfinite(ends[f"g0/{e}"]).all():
                bad.append(f"{src}/{body}/{unit}/{block} g0/{e}")
        for f in range(meta["futures"]):
            for g in range(1, max(r["stop"] for r in meta["rows"]) + 1):
                alive = alive_rows(meta, f, g)
                if not alive:
                    continue
                kinds = (("d", sim.DIAG + ("cue_dis_birth",)),) + ((("g", sim.E1.ENDPOINTS),)
                                                                   if g in D.HORIZONS else ())
                for kind, names in kinds:
                    if list(ends.get(f"f{f}/{kind}{g}/rows", [])) != alive:
                        bad.append(f"{src}/{body}/{unit}/{block} f{f}/{kind}{g} rows")
                        continue
                    for e in names:
                        v = ends[f"f{f}/{kind}{g}/{e}"]
                        if v.shape != (len(alive), k) or not np.isfinite(v).all():
                            bad.append(f"{src}/{body}/{unit}/{block} f{f}/{kind}{g}/{e}")
    want = set(map(tuple, D.stage_tasks(M["stage"])))
    have = {(s, b, u, blk) for s, b, u, blk, _ in tasks}
    return {"pass": not bad and have == want, "tasks": len(tasks), "bad": bad[:10], "missing": sorted(map(str, want - have))[:5]}


def q2(root):
    M, tasks = tasks_of(root)
    src, body, unit, block, t = tasks[0]
    ends, states, meta, bridge = WK.task(src, body, unit, block, M["stage"])
    e0, _ = npz(Path(root) / t["files"]["shards"]["path"])
    s0, _ = npz(Path(root) / t["files"]["raw"]["path"])
    differ = [k for k in e0 if not np.array_equal(e0[k], ends[k])] + [k for k in s0 if not np.array_equal(s0[k], states[k])]
    return {"pass": not differ and set(e0) == set(ends) and set(s0) == set(states), "task": [src, body, unit, block],
            "arrays": len(e0) + len(s0), "differ": differ[:10]}


def replay_bridge(src, body, unit, block, situations=("memory@0", "none@0")):
    """Generation 0 replayed by e2e002.sim.generation against the restored raw file's saved final states."""
    raw, meta, _ = WK.load(src, body, unit, block)
    pattern, theta = A.parse_unit(unit)
    cases, V0, ema0, R0, th, T = A1S.prepare(pattern, block, D.SOURCES[src]["purpose"])
    arms_of = {nm: list(a) for nm, a in meta["runs"]}
    k = len(cases)
    out = {}
    for sit in situations:
        arms = arms_of.get(sit)
        if not arms:
            continue
        V, E, A_, B_, dg = sim.replay0(body, sit, arms, cases, V0, ema0, R0, th, T, theta, meta["tag"],
                                       size=meta["sizes"][sit], configs=A5.VD_DETECTORS)
        mine = {"V": V, "r": A_[4], "H": A_[0], "W": A_[1], "rB": B_[4], "HB": B_[0], "WB": B_[1]}
        for j, arm in enumerate(arms):
            sl = slice(j * k, (j + 1) * k)
            out[f"{sit}/{arm}"] = all(np.array_equal(v[sl], raw[f"{sit}/{x}"][j]) for x, v in mine.items())
    return out


def q3(root):
    M, tasks = tasks_of(root)
    raw_bad, rec_bad = [], []
    for src, body, unit, block, t in tasks:
        Mr = json.loads((Path(D.SOURCES[src]["root"]) / "manifest.json").read_text())
        f = Mr["tasks"][f"{body}/{unit}/{block}"]["files"]["raw"]
        if hashlib.sha256((Path(D.SOURCES[src]["root"]) / f["path"]).read_bytes()).hexdigest() != f["sha256"]:
            raw_bad.append(f"{src}/{body}/{unit}/{block}")
        rec = json.loads((Path(root) / "done" / WK.key(src) / body / unit / f"{block}.json").read_text())
        if not all(rec["bridge"].values()):
            rec_bad.append(f"{src}/{body}/{unit}/{block}")
    src, body, unit, block, _t = tasks[0]
    each = replay_bridge(src, body, unit, block)
    ok = bool(each) and all(each.values())
    return {"pass": not raw_bad and not rec_bad and ok, "raw_files": len(tasks), "raw_differ": raw_bad[:5],
            "task_bridges_differ": rec_bad[:5], "replay_task": [src, body, unit, block], "replay_bit_for_bit": each}


def run_vd_from_birth():
    """ar003.sim.run_vd's own source, its event line and two stream lines substituted (each asserted once)."""
    src = inspect.getsource(S3.run_vd)
    subs = (("    ev = A1S.event(situation, size, sigma, cases, V0, ema0, R0, T, tag)\n", "    ev = _BIRTH_EV\n"),
            ('    st, xs, zs = (Stream(tag, cases, s, side=A.SIDE) for s in ("future", "record-noise", "bond-noise"))\n',
             "    st, xs, zs = (Stream(tag, cases, *nm, side=A.SIDE) for nm in _NAMES[:3])\n"),
            ('    xsB, zsB = (Stream(tag, cases, s, "B", side=A.SIDE) for s in ("record-noise", "bond-noise"))\n',
             "    xsB, zsB = (Stream(tag, cases, *nm, side=A.SIDE) for nm in _NAMES[3:])\n"))
    for old, new in subs:
        if src.count(old) != 1:
            raise RuntimeError(f"run_vd: '{old.strip()}' occurs {src.count(old)} times, not once")
        src = src.replace(old, new)
    ns = dict(vars(S3))
    exec(compile(src, "<ar003.sim.run_vd from a successor's birth (e2e002 Q4)>", "exec"), ns)
    return ns


def q4(root):
    M, tasks = tasks_of(root)
    src, body, unit, block, t = tasks[0]
    _e, meta = npz(Path(root) / t["files"]["shards"]["path"])
    states, _ = npz(Path(root) / t["files"]["raw"]["path"])
    raw, rmeta, _ = WK.load(src, body, unit, block)
    pattern, theta = A.parse_unit(unit)
    cases, V0, ema0, R0, th, T = A1S.prepare(pattern, block, D.SOURCES[src]["purpose"])
    parents = D.STAGE_PARENTS.get(M["stage"])
    if parents is not None:
        sel = [j for j, c in enumerate(cases) if c.parent in parents]
        cases = [cases[j] for j in sel]
        V0, ema0, R0, th, T = (x[sel] for x in (V0, ema0, R0, th, T))
    k = len(cases)
    tag = D.STAGE_TAG[M["stage"]]
    H0, W0, r0 = sim.protected(R0)
    newborn = birth(tag, cases, *sim.BIRTH_NAMES(0)(1), side=D.SIDE)
    _pk, m = sim.post_damage("memory@0", cases, V0, ema0, R0, T, rmeta["tag"])
    am = L5S.anchor_mask(cases, rmeta["tag"])
    aval = np.where(r0 > 0, 1.0, -1.0)
    ns = run_vd_from_birth()
    ns["_BIRTH_EV"] = {"V": newborn, "E": newborn.copy(), "r": r0, "H": H0, "W": W0, "Hb": D.STRENGTH0 * H0,
                       "Wb": D.STRENGTH0 * W0, "aval": aval, "am": am, "m": m, "target": T, "old": None,
                       "mis": np.zeros_like(am)}
    ns["_NAMES"] = sim.GEN_NAMES(0)(1)
    res = ns["run_vd"](body, "none", 0.0, ["vote", "vms"], cases, newborn, newborn, r0, th, T, theta, set(), tag=tag,
                       window=D.T_GEN, size=D.SIZE, detectors={"vote": D.POLICIES["vote"], "vms": D.POLICIES["vms"]})
    rows1 = list(states["f0/g1/rows"])
    out = {}
    for j, lab in enumerate(("protected", "protected+vms-every")):
        i = meta["labels"][lab]
        pos = rows1.index(i)
        sl, sv = slice(j * k, (j + 1) * k), slice(pos * k, (pos + 1) * k)
        out[lab] = {x: bool(np.array_equal(res[x][sl], states[f"f0/g1/{x}"][sv].astype(res[x].dtype))) for x in ("V", "r", "H", "W")}
    return {"pass": all(all(v.values()) for v in out.values()), "task": [src, body, unit, block], "rows": out}


def _rows_of(root):
    M, tasks = tasks_of(root)
    src, body, unit, block, t = tasks[0]
    raw, rmeta, _ = WK.load(src, body, unit, block)
    pattern, theta = A.parse_unit(unit)
    cases, V0, ema0, R0, th, T = A1S.prepare(pattern, block, D.SOURCES[src]["purpose"])
    parents = D.STAGE_PARENTS.get(M["stage"])
    if parents is not None:
        sel = [j for j, c in enumerate(cases) if c.parent in parents]
        cases = [cases[j] for j in sel]
        V0, ema0, R0, th, T = (x[sel] for x in (V0, ema0, R0, th, T))
        raw = {kk: (v[sel] if kk in ("V0", "R0", "T") else v[:, sel]) for kk, v in raw.items()}
    _e, meta = npz(Path(root) / t["files"]["shards"]["path"])
    lins = D.lineages(M["stage"])
    cap = D.STAGE_STOP_CAP.get(M["stage"])
    if cap is not None:
        lins = tuple(dict(ln, stop=min(ln["stop"], cap)) for ln in lins)
    rows, labels, aliases, sources = sim.packets(raw, rmeta, cases, V0, ema0, R0, T, lins)
    return (src, body, unit, block), raw, rmeta, cases, V0, ema0, R0, th * theta, T, rows, labels, aliases, meta


def _mini(body, rows, cases, thf, T, rtag, tag, t_gen=500):
    """A short first generation of the given rows (no reads): the states at its end."""
    m = np.ones_like(T, dtype=bool)
    am = L5S.anchor_mask(cases, rtag)
    normals = GCS.unit_normals(cases, rtag)
    _r, _a, _d, kept = sim.lineage(body, [dict(row, stop=1) for row in rows], cases, thf, T, np.stack([T] * 3), m, am,
                                   normals, {0.0: np.where(T > 0, 1.0, -1.0), 1.0: np.where(T > 0, 1.0, -1.0)}, tag,
                                   sim.GEN_NAMES(0), sim.BIRTH_NAMES(0), t_gen=t_gen, horizons=(), keep=(1,))
    return kept[1]


def q5(root):
    key, raw, rmeta, cases, V0, ema0, R0, thf, T, rows, labels, aliases, meta = _rows_of(root)
    complete = set(labels) == set(meta["labels"]) and all(labels[l] == meta["labels"][l] for l in labels)
    share = all(all(labels[l] == i for l in row["labels"]) for i, row in enumerate(rows))
    k = len(cases)
    i = labels["protected+vms-every"]
    kept = _mini(key[1], [rows[i], rows[i]], cases, thf, T, rmeta["tag"], meta["tag"])
    V, r = kept["V"].reshape(2, k, D.SIDE, D.SIDE), kept["r"].reshape(2, k, D.SIDE, D.SIDE)
    twice = bool(np.array_equal(V[0], V[1]) and np.array_equal(r[0], r[1]))
    return {"pass": bool(complete and share and twice), "complete": bool(complete), "rows_share_packets": bool(share),
            "listed_twice_identical": twice, "aliases": aliases}


def q6(root):
    M, tasks = tasks_of(root)
    bad, n = [], 0
    for src, body, unit, block, t in tasks[:4]:
        ends, meta = npz(Path(root) / t["files"]["shards"]["path"])
        states, _ = npz(Path(root) / t["files"]["raw"]["path"])
        raw, rmeta, _ = WK.load(src, body, unit, block)
        pattern, theta = A.parse_unit(unit)
        cases, V0, ema0, R0, th, T = A1S.prepare(pattern, block, D.SOURCES[src]["purpose"])
        parents = D.STAGE_PARENTS.get(M["stage"])
        if parents is not None:
            sel = [j for j, c in enumerate(cases) if c.parent in parents]
            cases = [cases[j] for j in sel]
            V0, ema0, R0, th, T = (x[sel] for x in (V0, ema0, R0, th, T))
        k = len(cases)
        Tf = SRS.foreign(T, pattern, cases)
        _pk, m = sim.post_damage("memory@0", cases, V0, ema0, R0, T, rmeta["tag"])
        for f in range(meta["futures"]):
            for g in D.HORIZONS:
                if f"f{f}/g{g}/rows" not in ends:
                    continue
                alive = list(ends[f"f{f}/g{g}/rows"])
                idx = np.tile(np.arange(k), len(alive))
                sc = sim.score(states[f"f{f}/g{g}/V"], states[f"f{f}/g{g}/r"], T[idx], Tf[:, idx], m[idx])
                for e, v in sc.items():
                    n += 1
                    if not np.array_equal(v.reshape(len(alive), k), ends[f"f{f}/g{g}/{e}"]):
                        bad.append(f"{src}/{body}/{unit}/{block} f{f}/g{g}/{e}")
    return {"pass": not bad and n > 0, "compared": n, "differ": bad[:10]}


def q7(root):
    M, tasks = tasks_of(root)
    fired_vote, cue_bad = [], []
    for src, body, unit, block, t in tasks:
        ends, meta = npz(Path(root) / t["files"]["shards"]["path"])
        for f in range(meta["futures"]):
            for g in range(1, max(r["stop"] for r in meta["rows"]) + 1):
                key = f"f{f}/d{g}/rows"
                if key not in ends:
                    continue
                for j, i in enumerate(ends[key]):
                    row = meta["rows"][i]
                    if row["policy"] == "vote" and ends[f"f{f}/d{g}/fired"][j].any():
                        fired_vote.append(f"{src}/{body}/{unit}/{block} f{f} g{g} row {i}")
                    if row["cue"] == "birth" and row["sigma"] == 0 and ends[f"f{f}/d{g}/cue_dis_birth"][j].any():
                        cue_bad.append(f"{src}/{body}/{unit}/{block} f{f} g{g} row {i}")
    # at birth: the second record equals the incoming record, and the cue is built by the row's rule
    key, raw, rmeta, cases, V0, ema0, R0, thf, T, rows, labels, aliases, meta = _rows_of(root)
    k = len(cases)
    seen = {}
    real = sim.generation

    def spy(body, groups, cases_, V, E, A_, B_, P, m, thb, tag, names, window=D.T_GEN, gain=D.GAIN, clock=None):
        if "A" not in seen:
            seen.update(A=[x.copy() for x in A_], B=[x.copy() for x in B_], aval=P["aval"].copy(), am=P["am"].copy())
        return real(body, groups, cases_, V, E, A_, B_, P, m, thb, tag, names, 5, gain, clock)

    pick = [rows[labels[lab]] for lab in ("protected+vms-every", "vms-every/memory@0") if lab in labels]
    sim.generation = spy
    try:
        am = L5S.anchor_mask(cases, rmeta["tag"])
        normals = GCS.unit_normals(cases, rmeta["tag"])
        sim.lineage(key[1], [dict(r, stop=1) for r in pick], cases, thf, T, np.stack([T] * 3), np.ones_like(T, bool),
                    am, normals, {0.0: np.where(R0 > 0, 1.0, -1.0)}, meta["tag"], sim.GEN_NAMES(0), sim.BIRTH_NAMES(0),
                    t_gen=5, horizons=(), keep=())
    finally:
        sim.generation = real
    second_ok = all(np.array_equal(a, b) for a, b in zip(seen["A"], seen["B"]))
    signs = np.where(seen["A"][4] > 0, 1.0, -1.0)
    cue_ok = bool(np.array_equal(seen["aval"], signs) and np.array_equal(seen["am"], np.tile(am, (len(pick), 1, 1))))
    pattern, _ = A.parse_unit(key[2])
    (Hp, Wp, rp), m = sim.post_damage("memory@0", cases, V0, ema0, R0, T, rmeta["tag"])
    post_ok = bool(np.array_equal(rp[~m], R0[~m]) and np.array_equal(rp[m], -R0[m]))
    stage_ok = {(s, b, u, blk) for s, b, u, blk, _ in tasks} <= set(map(tuple, D.stage_tasks(M["stage"])))
    return {"pass": bool(not fired_vote and not cue_bad and second_ok and cue_ok and post_ok and stage_ok),
            "vote_never_fires": not fired_vote, "birth_cue_agrees_at_sigma0": not cue_bad,
            "second_record_is_incoming": bool(second_ok), "cue_built_by_rule": cue_ok, "post_damage_patch_only": post_ok,
            "tasks_are_saved_records": bool(stage_ok), "examples": (fired_vote + cue_bad)[:5]}


def q8(root):
    key, raw, rmeta, cases, V0, ema0, R0, thf, T, rows, labels, aliases, meta = _rows_of(root)
    k = len(cases)
    pick = [rows[labels[lab]] for lab in ("protected+vms-every", "vms-once/memory@0", "protected")]
    a = _mini(key[1], pick, cases, thf, T, rmeta["tag"], meta["tag"])
    b = _mini(key[1], pick[::-1], cases, thf, T, rmeta["tag"], meta["tag"])
    ra, rb = a["r"].reshape(3, k, D.SIDE, D.SIDE), b["r"].reshape(3, k, D.SIDE, D.SIDE)[::-1]
    Va, Vb = a["V"].reshape(3, k, D.SIDE, D.SIDE), b["V"].reshape(3, k, D.SIDE, D.SIDE)[::-1]
    same = bool(np.array_equal(ra, rb) and np.array_equal(Va, Vb))
    return {"pass": same, "reordered_identical": same}


def row_generations(rows, nf, second=()):
    """Every future's (vote, vms) row-generations: all rows in the first future, the SECOND_FUTURE rows after."""
    vote = vms = 0
    for f in range(nf):
        for r in rows:
            if f > 0 and not set(r["labels"]) & set(second):
                continue
            if r["policy"] == "vote":
                vote += r["stop"]
            else:
                vms += r["stop"]
    return vote, vms


def q9(root):
    M, tasks = tasks_of(root)
    done, cpu = 0.0, 0.0
    for src, body, unit, block, t in tasks:
        _e, meta = npz(Path(root) / t["files"]["shards"]["path"])
        vote, vms = row_generations(meta["rows"], meta["futures"], meta["second_future"])
        done += len(meta["cases"]) * (vote + W_VMS * vms)
        cpu += t["cpu_s"]
    rate = cpu / done
    dev = 0.0
    for s, b, u, blk in D.stage_tasks("development"):
        raw, rmeta, _ = WK.load(s, b, u, blk)
        pattern, theta = A.parse_unit(u)
        cases, V0, ema0, R0, th, T = A1S.prepare(pattern, blk, D.SOURCES[s]["purpose"])
        rows, _labels, _al, _src = sim.packets(raw, rmeta, cases, V0, ema0, R0, T, D.lineages("development"))
        vote, vms = row_generations(rows, D.FUTURES["development"], D.SECOND_FUTURE)
        dev += len(cases) * (vote + W_VMS * vms)
    forecast = rate * dev / 3600
    wall12 = forecast / 12
    rss = max(t["maxrss_mb"] for *_x, t in tasks)
    return {"pass": bool(forecast <= CAP and wall12 <= 12 and rss <= 2048), "forecast_dev_cpu_h": round(forecast, 2),
            "forecast_dev_wall_h_12": round(wall12, 2), "cpu_s_per_vote_branch_generation": round(rate, 4),
            "w_vms": W_VMS, "dev_vote_equivalent_branch_generations": dev, "worker_rss_mb": rss, "cap": CAP}


def q10(root):
    import os
    import subprocess
    out = Path(tempfile.mkdtemp())
    env = dict(os.environ, PYTHONPATH=str(LANE))
    p1 = subprocess.run([sys.executable, "-m", "e2e002.predict", "--root", str(root), "--out", str(out)], capture_output=True,
                        text=True, env=env, cwd=LANE)
    p2 = subprocess.run([sys.executable, "-m", "e2e002.tables", "--dir", str(out)], capture_output=True, text=True, env=env,
                        cwd=LANE)
    sizes = {f.name: f.stat().st_size for f in out.glob("*")}
    scored = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    from e2e002 import predict as PR
    ok = (p1.returncode == 0 and p2.returncode == 0 and len(scored.get("parts", [])) == len(PR.parts())
          and all(s <= 256 * 1024 for s in sizes.values()))
    return {"pass": bool(ok), "stderr": (p1.stderr + p2.stderr)[-600:], "sizes": sizes, "parts_scored": len(scored.get("parts", []))}


def main():
    from concurrent.futures import ProcessPoolExecutor
    import multiprocessing as mp
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--receipt", type=Path, default=None)
    ap.add_argument("--cpus", default=None)
    a = ap.parse_args()
    root = a.root.resolve()
    M = json.loads((root / "manifest.json").read_text())
    t0 = time.time()
    heavy = {"Q2_serial_equals_parallel": lambda: q2(root), "Q3_bridges": lambda: q3(root), "Q4_replay": lambda: q4(root),
             "Q7_efficacy": lambda: q7(root), "Q8_pairing": lambda: q8(root), "Q9_resources": lambda: q9(root)}
    light = {"Q1_complete_finite": lambda: q1(root), "Q5_aliases": lambda: q5(root), "Q6_reanalysis": lambda: q6(root),
             "Q10_reader_dry_run": lambda: q10(root)}
    checks = {}
    cpus = [int(c) for c in a.cpus.split(",")] if a.cpus else []
    if len(cpus) >= len(heavy):
        ctx = mp.get_context("fork")
        q = ctx.Queue()
        for c in cpus[: len(heavy)]:
            q.put(c)
        K5._HEAVY.clear()
        K5._HEAVY.update(heavy)
        with ProcessPoolExecutor(len(heavy), mp_context=ctx, initializer=K5._pin, initargs=(q,)) as pool:
            futs = [pool.submit(K5._run_named, name) for name in heavy]
            for name, fn in light.items():
                checks[name] = K5._run(name, fn)[1]
                print(name, "PASS" if checks[name]["pass"] else "FAIL", checks[name]["seconds"], "s", flush=True)
            for fu in futs:
                name, res = fu.result()
                checks[name] = res
                print(name, "PASS" if res["pass"] else "FAIL", res["seconds"], "s", flush=True)
    else:
        for name, fn in {**heavy, **light}.items():
            checks[name] = K5._run(name, fn)[1]
            print(name, "PASS" if checks[name]["pass"] else "FAIL", checks[name]["seconds"], "s", flush=True)
    order = ["Q1_complete_finite", "Q2_serial_equals_parallel", "Q3_bridges", "Q4_replay", "Q5_aliases", "Q6_reanalysis",
             "Q7_efficacy", "Q8_pairing", "Q9_resources", "Q10_reader_dry_run"]
    checks = {k: checks[k] for k in order}
    failed = [k for k, v in checks.items() if not v["pass"]]
    receipt = {"status": "PASS" if not failed else "FAIL", "failed": failed, "design_digest": D.digest(), "root": str(root),
               "stage": M["stage"], "tasks": len(M["tasks"]), "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "wall_s": round(time.time() - t0, 1), "checks": checks}
    path = a.receipt or (root / "qualification_receipt.json")
    path.write_text(json.dumps(receipt, indent=1, default=str) + "\n")
    print(receipt["status"], failed)


if __name__ == "__main__":
    main()
