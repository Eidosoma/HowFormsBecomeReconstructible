"""E2E006's qualification Q1-Q10 (DRAFT): python -m e2e006.checks --root STAGE_ROOT --cpus LIST [--debug]
  (with --debug: ROOT/debug_qualification_receipt.json; otherwise e2e006/frozen/qualification_receipt.json)

Fixed in PLAN_E2E006.md (Q1-Q10, E2E003's adapted) before their results; in phase A they run on the debug run (AR006's
900948, every row to g 3), in phase B on the preflight (AR006's 900929, 900947). In-process checks run short generations
(SHORT updates) of the stage's first task.
  Q1  complete and finite: every task's reads, fresh reads and diagnostics at their shapes (rows alive at each generation
      = rows whose stop reaches it; the fresh successors after the stage's fresh generations, and their saved final
      states where the stage saves them), generation 0 for every row, the exposures in every generation with a field
      row, the schedule's corners and attempts; every value finite
  Q2  serial equals parallel: one task rerun in-process gives bit-identical endpoints, diagnostics and states
  Q3  the bridges: every restored raw file equals its manifest's sha256 (rehashed); field-free, e2e006.sim.lineage equals
      e2e003.sim.lineage (unchanged) bit for bit on the vote and vtol rows under repeated injury (reads, diagnostics,
      states; two generations of 2,000 updates), and P63s's full-length bridge stands; the routed generation is
      e2e002.sim.generation's source with its detector call and its body call routed, each once; every task's
      acquisition and generation-0 packets equal their sources (the workers' records)
  Q4  an independent replay: generation 1 of vote/shared and vote/isolated for one task through ar003.sim.run_vd's own
      source (its event line replaced by the successors' birth state and injured incoming packet, its second-record line
      by the incoming packet before the injury, its two stream lines by the generation's names, and its body line by a
      coupling written here from the rulings: msefield's Media stepped directly, the stress, the response; each
      substitution asserted once), equal to the stage's saved generation-1 V, r, H and W bit for bit
  Q5  aliases: the alias table is complete (every label has a row; a row's labels share one packet and one way of
      meeting the field); a field row listed twice gives the same lineage bit for bit
  Q6  reanalysis: the reads recomputed from the saved states, with the union and own patches rebuilt from the saved
      corners, equal the shards'; the fresh successors re-run from the saved outgoing records (one task) equal the
      shards' (and their saved final states, where saved); every saved fresh state re-scores to the shards' fresh reads
  Q7  efficacy, the injury and the field: the vote rows never fire; at sigma 0 every birth cue equals its incoming record's
      signs; every injury flips exactly its patch, and nothing on an uninjured row; the patches are disjoint and
      recompute from their addresses; the injury rule at generation 0 equals be001.sim.event's memory rule; the second
      record, the cue and the protected copy are taken before the injury; every task is a saved record of its stage; the
      windows (kappa x the window's exposure, and nothing outside it, in every field row's integrated response); no
      exposure on a field-free row; a field-free row in a mixed call equals its field-free run; reset (a new medium at
      birth, zero) against retain (the same medium carried, non-zero at the second birth); protected copying (the
      packet handed on is the incoming packet in every generation); the information boundary: another target, or
      another patch mask given to the generation, leaves every state and every exposure unchanged
  Q8  pairing: reordering the rows changes no row's output
  Q9  resources: phase B forecast structurally from this stage's CPU per vote-equivalent row-generation (a detector
      row-generation weighs W_DET, a field row-generation W_FIELD more, a fresh test one): the development's and the
      preflight's own row-generations (phase B's rows, Amendment 2; on the preflight its measured CPU), plus Q1-Q10 and
      the reader, with HEADROOM for other users' load, within CAP CPU-hours and 12 h of wall on 10 workers; worker memory
      within 2 GB. --only Q9,Q10 re-runs those alone (the others stand from the earlier receipt)
  Q10 the reader's dry run: predict and tables complete, every part scored or marked unavailable, every output and every
      E2E006 git file 256 KiB or less
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
import hashlib  # noqa: E402
import inspect  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from ar001 import design as A  # noqa: E402
from ar001 import sim as A1S  # noqa: E402
from ar003 import sim as S3  # noqa: E402
from ar006 import sim as S6  # noqa: E402
from be001 import sim as B1S  # noqa: E402
from dl001 import sim as DS  # noqa: E402
from e2e002 import design as E2D  # noqa: E402
from e2e002 import sim as E2  # noqa: E402
from e2e003 import sim as E3  # noqa: E402
from e2e006 import design as D  # noqa: E402
from e2e006 import sim  # noqa: E402
from e2e006 import worker as W  # noqa: E402
from gc001 import sim as GCS  # noqa: E402
from lr001.sim import edges_from  # noqa: E402
from lr005 import sim as L5S  # noqa: E402
from msefield import core as MF  # noqa: E402
from msegrid.core import birth, bonds  # noqa: E402
from sr001 import sim as SRS  # noqa: E402

FROZEN = LANE / "e2e006" / "frozen"
W_DET = 2.0                    # E2E003's P59s: a vtol row-generation weighs about two vote row-generations
W_FIELD = 0.5                  # a medium's step (20 substeps) about half a vote row-generation's tissue (3.3 of 6.8 CPU-s)
SHORT = 500                    # the in-process checks' generations (updates)
CAP = 40.0                     # the lead's phase B cap (CPU-hours, with HEADROOM): 30, then 35 (Amendment 2), then 40 (the
                               # freeze word, 14:18:44Z: a resource bound only, raised before the preflight)
CHECKS_CPU_H = 0.6             # Q1-Q10 on the preflight and the reader
HEADROOM = 1.25
WORKERS = 10


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


def meta_of(path):
    return json.loads(str(np.load(path)["__meta__"]))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def setup(source, body, unit, block, stage):
    """The task's restored inputs as the worker builds them."""
    raw, meta, _rf = W.load(source, body, unit, block)
    pattern, theta = A.parse_unit(unit)
    cases, V0, ema0, R0, th, T = A1S.prepare(pattern, block, D.SOURCES[source]["purpose"])
    Tf = SRS.foreign(T, pattern, cases)
    _pk, m0 = sim.post_damage("memory@0", cases, V0, ema0, R0, T, meta["tag"])
    am, normals = L5S.anchor_mask(cases, meta["tag"]), GCS.unit_normals(cases, meta["tag"])
    return dict(raw=raw, meta=meta, cases=cases, V0=V0, ema0=ema0, R0=R0, th=th, theta=theta, T=T, Tf=Tf, m0=m0, am=am,
                normals=normals, thf=th * theta, pattern=pattern, body=body)


def masks_from(corners, side=D.SIDE, size=D.SIZE):
    """{g: (k, side, side)} from the saved corners (k, G, 2)."""
    k, G, _ = corners.shape
    out = {}
    for g in range(1, G + 1):
        m = np.zeros((k, side, side), bool)
        for j in range(k):
            a, b = corners[j, g - 1]
            m[j][np.ix_((a + np.arange(size)) % side, (b + np.arange(size)) % side)] = True
        out[g] = m
    return out


def rows_of(S, labels, stop=2):
    lins = [dict(x, stop=stop) for x in D.ALL if x["label"] in labels]
    rows, lab, al, _src = sim.packets(S["raw"], S["meta"], S["cases"], S["V0"], S["ema0"], S["R0"], S["T"], lins)
    return rows, lab, al


def short(S, rows, tag, field, gens=2, t_gen=SHORT, T=None, keep=(1, 2), kappa=None):
    sched = sim.schedule(S["cases"], S["m0"], tag, gens)[0]
    return sim.lineage(S["body"], rows, S["cases"], S["thf"], S["T"] if T is None else T, S["Tf"], S["m0"], S["am"],
                       S["normals"], tag, sim.GEN_NAMES(0), sim.BIRTH_NAMES(0), sched=sched, t_gen=t_gen, keep=keep,
                       field=field, kappa_override=kappa)


def same_row(k1, i1, k2, i2, gens=(1, 2)):
    """Row i1's kept states in run 1 equal row i2's in run 2 at every generation in gens (V, r, H, W)."""
    ok = True
    for g in gens:
        a, b = k1[g], k2[g]
        k = a["V"].shape[0] // len(a["rows"])
        j1, j2 = a["rows"].index(i1), b["rows"].index(i2)
        ok &= all(np.array_equal(a[x][j1 * k:(j1 + 1) * k], b[x][j2 * k:(j2 + 1) * k]) for x in ("V", "r", "H", "W"))
    return bool(ok)


# ------------------------------------------------------------------------------------------------ Q4's own route
class Indep:
    """Q4's coupling, written here from the rulings (not e2e006.sim.Coupling): branches 0..k-1 a shared row (one msefield
    Medium over FIELD['positions']), k..2k-1 an isolated row (one Medium over FIELD['isolated_positions']); every
    update: the gain on every branch times (1 + kappa x its exposure after the previous update's step, zero at the
    first), then dl001.sim.body, then each sheet's mean |r - V-tilde| emitted into its medium's step."""

    def __init__(self, k, kappa):
        f = D.FIELD
        kw = dict(dt=f["dt"], m=f["m"], margin=f["margin"])
        self.k, self.kappa = k, kappa
        self.shared = MF.Medium(f["positions"], f["D"], f["gamma"], f["leakage"], **kw)
        self.iso = MF.Medium(f["isolated_positions"], f["D"], f["gamma"], f["leakage"], **kw)
        self.x = np.zeros(2 * k)

    def __call__(self, t, V, E, r, thb, z, p, gain, alpha, G):
        out = DS.body(V, E, r, thb, z, p, gain * (1.0 + self.kappa * self.x[:, None, None]), alpha, G)
        s = np.abs(r - out[2]).mean((-2, -1))
        self.x = np.concatenate([self.shared.step(s[:self.k]), self.iso.step(s[self.k:])])
        return out


def run_vd_field():
    """ar003.sim.run_vd's own source with five substitutions (each asserted once)."""
    src = inspect.getsource(S3.run_vd)
    subs = (("    ev = A1S.event(situation, size, sigma, cases, V0, ema0, R0, T, tag)\n", "    ev = _BIRTH_EV\n"),
            ("    rB, HB, WB, HbB, WbB = second_record(situation, ev, R0, idx)\n",
             "    rB, HB, WB, HbB, WbB = (x[idx].copy() for x in _SECOND)\n"),
            ('    st, xs, zs = (Stream(tag, cases, s, side=A.SIDE) for s in ("future", "record-noise", "bond-noise"))\n',
             "    st, xs, zs = (Stream(tag, cases, *nm, side=A.SIDE) for nm in _NAMES[:3])\n"),
            ('    xsB, zsB = (Stream(tag, cases, s, "B", side=A.SIDE) for s in ("record-noise", "bond-noise"))\n',
             "    xsB, zsB = (Stream(tag, cases, *nm, side=A.SIDE) for nm in _NAMES[3:])\n"),
            ("        V, E, Vt, drift, d = S.body(V, E, r, thb, buf[i][idx], p, gain, alpha, G)\n",
             "        V, E, Vt, drift, d = _FIELD(t, V, E, r, thb, buf[i][idx], p, gain, alpha, G)\n"))
    for old, new in subs:
        if src.count(old) != 1:
            raise RuntimeError(f"run_vd: '{old.strip()}' occurs {src.count(old)} times, not once")
        src = src.replace(old, new)
    ns = dict(vars(S3))
    exec(compile(src, "<ar003.sim.run_vd with a field (e2e006 Q4)>", "exec"), ns)
    return ns


def q4(task, stage, shard, rawshard):
    S = setup(*task, stage)
    e, rr, meta = npz(shard), npz(rawshard), meta_of(shard)
    k = len(S["cases"])
    tag = D.STAGE_TAG[stage]
    rows, _lab, _al = rows_of(S, ("vote/shared",))
    H, Wm, r = (np.asarray(x, dtype=float) for x in rows[0]["packet"])
    A_ = (H.copy(), Wm.copy(), D.STRENGTH0 * H, D.STRENGTH0 * Wm, r.copy())
    m1 = masks_from(e["schedule/corners"])[1]
    inj = sim.injure(A_, m1)
    newborn = birth(tag, S["cases"], *sim.BIRTH_NAMES(0)(1), side=D.SIDE)
    ns = run_vd_field()
    ns["_BIRTH_EV"] = {"V": newborn, "E": newborn.copy(), "r": inj[4], "H": inj[0], "W": inj[1], "Hb": inj[2],
                       "Wb": inj[3], "aval": sim.birth_cue(r, S["normals"], 0.0), "am": S["am"], "m": m1,
                       "target": S["T"], "old": None, "mis": np.zeros_like(S["am"])}
    ns["_SECOND"] = (r, H, Wm, D.STRENGTH0 * H, D.STRENGTH0 * Wm)
    ns["_NAMES"] = sim.GEN_NAMES(0)(1)
    ns["_FIELD"] = Indep(k, D.FIELD["kappa"])
    res = ns["run_vd"](S["body"], "none", 0.0, ["vote", "vote"], S["cases"], newborn, newborn, r, S["th"], S["T"],
                       S["theta"], set(), gain=E2D.GAIN, tag=tag, window=D.T_GEN, size=D.SIZE, clock=E2D.CLOCK,
                       detectors={"vote": D.POLICIES["vote"]})
    lab = meta["labels"]
    kept = list(rr["f0/g1/rows"])
    out = {}
    for j, label in enumerate(("vote/shared", "vote/isolated")):
        pos = kept.index(lab[label])
        sl, sv = slice(j * k, (j + 1) * k), slice(pos * k, (pos + 1) * k)
        out[label] = {x: bool(np.array_equal(res[x][sl], rr[f"f0/g1/{x}"][sv].astype(res[x].dtype)))
                      for x in ("V", "r", "H", "W")}
    return {"pass": all(all(v.values()) for v in out.values()), "task": list(task), "rows": out}


# ------------------------------------------------------------------------------------------------ the checks
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--cpus", default=None)
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--only", default=None, help="comma-separated checks to run (e.g. Q9,Q10); the others stand from an "
                                                 "earlier receipt, and the receipt is written beside it under their names")
    a = ap.parse_args()
    only = None if a.only is None else [q.strip() for q in a.only.split(",")]
    chosen = lambda q: only is None or q in only     # which checks run (not 'want': Q5 and Q7 use that name)
    if a.cpus:
        os.sched_setaffinity(0, [int(c) for c in a.cpus.split(",")])
    root, t0 = a.root.resolve(), time.time()
    M = json.loads((root / "manifest.json").read_text())
    stage = M["stage"]
    tag = D.STAGE_TAG[stage]
    receipt_path = root / "debug_qualification_receipt.json" if a.debug else FROZEN / "qualification_receipt.json"
    if only is not None:
        receipt_path = receipt_path.with_name(receipt_path.stem + "_" + "_".join(only) + ".json")
    tasks = [tuple(t) for t in M["tasks_planned"]]
    paths = {t: (root / "shards" / W.key(t[0]) / t[1] / t[2] / f"{t[3]}.npz",
                 root / "raw" / W.key(t[0]) / t[1] / t[2] / f"{t[3]}.npz") for t in tasks}
    dpath = lambda t: root / "done" / W.key(t[0]) / t[1] / t[2] / f"{t[3]}.json"
    done = {t: json.loads(dpath(t).read_text()) for t in tasks if dpath(t).exists()}
    tr = sorted(tasks)[0]
    S0 = setup(*tr, stage)
    k = len(S0["cases"])
    ad = sim.field_adapter()
    checks = {}

    # Q1
    if chosen("Q1"):
        bad = []
        fresh_set = D.STAGE_FRESH_AT.get(stage, D.FRESH_AT)
        reads = tuple(sim.READS) + tuple(sim.UNION_READS)
        fresh_ends = tuple(sim.UNION_READS) + ("a_v", "q_v", "a_r", "q_r")
        for t in tasks:
            sp, rp = paths[t]
            if not sp.exists() or not rp.exists():
                bad.append(f"{t}: missing")
                continue
            e, meta = npz(sp), meta_of(sp)
            rows = meta["rows"]
            kk = len(meta["cases"])
            gmax = max(r["stop"] for r in rows)
            g0 = [x for x in e if x.startswith("g0/")]
            bad += [] if g0 else [f"{t}: no generation-0 endpoint"]
            for key in g0:
                bad += [] if e[key].shape == (len(rows), kk) else [f"{t}: {key} shape"]
            if e["schedule/corners"].shape != (kk, gmax, 2) or e["schedule/attempts"].shape != (kk, gmax):
                bad.append(f"{t}: schedule shape")
            for g in range(1, gmax + 1):
                alive = [i for i, r in enumerate(rows) if r["stop"] >= g]
                fieldy = any(rows[i]["field"] != "none" for i in alive)
                diag = tuple(sim.DIAG) + ("cue_dis_birth", "injury_ok") + (("exp_full", "exp_early", "exp_late", "kexp")
                                                                             if fieldy else ())
                for kind, ends in (("g", reads), ("d", diag)):
                    if list(e[f"f0/{kind}{g}/rows"]) != alive:
                        bad.append(f"{t}: f0/{kind}{g}/rows")
                    for x in ends:
                        key = f"f0/{kind}{g}/{x}"
                        bad += [] if key in e and e[key].shape == (len(alive), kk) else [f"{t}: {key}"]
                if g in fresh_set:
                    if list(e[f"f0/x{g}/rows"]) != alive:
                        bad.append(f"{t}: f0/x{g}/rows")
                    for x in fresh_ends:
                        key = f"f0/x{g}/{x}"
                        bad += [] if key in e and e[key].shape == (len(alive), kk) else [f"{t}: {key}"]
                    if meta.get("save_fresh"):
                        rr = npz(rp)
                        bad += [] if list(rr.get(f"f0/x{g}/rows", [])) == alive else [f"{t}: raw f0/x{g}/rows"]
                        for x in ("V", "r", "H", "W"):
                            key = f"f0/x{g}/{x}"
                            bad += [] if key in rr and rr[key].shape == (len(alive) * kk, D.SIDE, D.SIDE) else [f"{t}: raw {key}"]
            bad += [f"{t}: {x} not finite" for x, v in e.items() if np.issubdtype(v.dtype, np.floating) and not np.isfinite(v).all()]
        checks["Q1_complete_finite"] = {"pass": not bad, "tasks": len(tasks), "bad": bad[:10]}

    # Q2
    if chosen("Q2"):
        ends, states, _m2, _b = W.task(*tr, stage)
        e, r = npz(paths[tr][0]), npz(paths[tr][1])
        same_e = set(ends) == set(e) and all(np.array_equal(np.asarray(ends[x]), e[x]) for x in e)
        same_r = set(states) == set(r) and all(np.array_equal(np.asarray(states[x]), r[x]) for x in r)
        checks["Q2_serial_equals_parallel"] = {"pass": bool(same_e and same_r), "task": list(tr)}

    # Q3
    if chosen("Q3"):
        q3 = {}
        shas = []
        for t in tasks:
            src = Path(D.SOURCES[t[0]]["root"])
            Mf = json.loads((src / "manifest.json").read_text())
            f = Mf["tasks"][f"{t[1]}/{t[2]}/{t[3]}"]["files"]["raw"]
            shas.append(sha(src / f["path"]) == f["sha256"])
        q3["every_raw_file_equals_its_manifests_sha256"] = all(shas) and len(shas) == len(tasks)
        rows_b, _lb, _ab = rows_of(S0, ("vote/none", "vtol-every"))
        sched_b = sim.schedule(S0["cases"], S0["m0"], tag, 2)[0]
        args = (S0["body"], rows_b, S0["cases"], S0["thf"], S0["T"], S0["Tf"], S0["m0"], S0["am"], S0["normals"], tag,
                sim.GEN_NAMES(0), sim.BIRTH_NAMES(0))
        r3, _a3, d3, k3 = E3.lineage(*args, sched=sched_b, t_gen=2000, keep=(1, 2))
        r6, _a6, d6, k6, _f6 = sim.lineage(*args, sched=sched_b, t_gen=2000, keep=(1, 2), field=None)
        q3["field_free_the_lineage_is_e2e003s"] = bool(all(
            set(r3[g]) == set(r6[g]) and all(np.array_equal(r3[g][x], r6[g][x]) for x in r3[g])
            and set(d3[g]) == set(d6[g]) and all(np.array_equal(d3[g][x], d6[g][x]) for x in d3[g])
            and all(np.array_equal(k3[g][x], k6[g][x]) for x in ("V", "r", "H", "W")) for g in (1, 2)))
        p63s = json.loads((LANE / "probes" / "results" / "p63s_e2e006_bridge.json").read_text())
        q3["p63s_full_length_bridge_stands"] = bool(p63s.get("all_equal"))
        gsrc = inspect.getsource(E2.generation)
        q3["the_routed_generation_is_e2e002s_with_two_calls_routed"] = bool(
            gsrc.count(sim.DETECT_CALL) == 1 and gsrc.count(sim.BODY_CALL) == 1
            and sim.generation.__globals__["detect_vt"] is S6.detect and sim._COUPLING is None)
        q3["every_tasks_acquisition_and_generation0_packets_equal_their_sources"] = bool(
            len(done) == len(tasks) and all(rec["bridge_all_equal"] for rec in done.values()))
        checks["Q3_bridges"] = {"pass": all(q3.values()), "items": q3, "task": list(tr)}

    # Q4
    if chosen("Q4"):
        checks["Q4_independent_replay"] = q4(tr, stage, *paths[tr])

    # Q5
    if chosen("Q5"):
        q5 = {}
        ok_tab = True
        for t in tasks:
            meta = meta_of(paths[t][0])
            lab, rows = meta["labels"], meta["rows"]
            want = [x["label"] for x in D.lineages(stage)]
            ok_tab &= set(want) <= set(lab)
            ok_tab &= all(sorted(rows[i]["labels"]) == sorted(x for x, j in lab.items() if j == i) for i in range(len(rows)))
            ways = {x["label"]: (x["field"], x["medium"], x["window"], x["label"] in D.PROTECTED_COPY, x.get("kappa_key"))
                    for x in D.lineages(stage)}
            ok_tab &= all(len({ways[x] for x in rows[i]["labels"] if x in ways}) <= 1 for i in range(len(rows)))
        q5["the_alias_table_is_complete"] = bool(ok_tab)
        rs, _l5, _a5 = rows_of(S0, ("vote/shared",))
        r5, _a5r, d5, k5, _f5 = short(S0, [rs[0], dict(rs[0])], tag, ad)
        q5["a_field_row_listed_twice_gives_the_same_lineage"] = bool(all(
            all(np.array_equal(v[0], v[1]) for v in r5[g].values()) and all(np.array_equal(v[0], v[1]) for v in d5[g].values())
            and all(np.array_equal(k5[g][x][:k], k5[g][x][k:]) for x in ("V", "r", "H", "W")) for g in (1, 2)))
        checks["Q5_aliases"] = {"pass": all(q5.values()), "items": q5}

    # Q6
    if chosen("Q6"):
        bad6 = []
        for t in tasks:
            e, rr, meta = npz(paths[t][0]), npz(paths[t][1]), meta_of(paths[t][0])
            S = setup(*t, stage)
            sched = masks_from(e["schedule/corners"])
            for g in D.HORIZONS:
                if f"f0/g{g}/rows" not in rr:
                    continue
                kr = list(rr[f"f0/g{g}/rows"])
                idx = np.tile(np.arange(k), len(kr))
                union = S["m0"].copy()
                for h in range(1, g + 1):
                    union |= sched[h]
                so = sim.score(rr[f"f0/g{g}/V"], rr[f"f0/g{g}/r"], S["T"][idx], S["Tf"][:, idx], sched[g][idx])
                su = sim.score(rr[f"f0/g{g}/V"], rr[f"f0/g{g}/r"], S["T"][idx], S["Tf"][:, idx], union[idx])
                gr = list(e[f"f0/g{g}/rows"])
                sel = [gr.index(i) for i in kr]
                for key, src in sim.READS.items():
                    if not np.array_equal(so[src].reshape(len(kr), k), e[f"f0/g{g}/{key}"][sel]):
                        bad6.append(f"{t} g{g} {key}")
                for key, src in sim.UNION_READS.items():
                    if not np.array_equal(su[src].reshape(len(kr), k), e[f"f0/g{g}/{key}"][sel]):
                        bad6.append(f"{t} g{g} {key}")
        e, rr, meta = npz(paths[tr][0]), npz(paths[tr][1]), meta_of(paths[tr][0])
        sched = masks_from(e["schedule/corners"])
        fresh_bad, rescored = [], 0
        for t in tasks:                                   # the saved fresh states (where saved) re-score to the shards
            e_, rr_, meta_ = npz(paths[t][0]), npz(paths[t][1]), meta_of(paths[t][0])
            if not meta_.get("save_fresh"):
                continue
            S = setup(*t, stage)
            sched_ = masks_from(e_["schedule/corners"])
            for g in D.STAGE_FRESH_AT.get(stage, D.FRESH_AT):
                if f"f0/x{g}/rows" not in rr_:
                    continue
                kr = list(rr_[f"f0/x{g}/rows"])
                idx = np.tile(np.arange(k), len(kr))
                union = S["m0"].copy()
                for h in range(1, g + 1):
                    union |= sched_[h]
                su = sim.score(rr_[f"f0/x{g}/V"], rr_[f"f0/x{g}/r"], S["T"][idx], S["Tf"][:, idx], union[idx])
                xr = list(e_[f"f0/x{g}/rows"])
                sel = [xr.index(i) for i in kr]
                want_ = {x: su[src] for x, src in sim.UNION_READS.items()}
                want_.update({x: su[x] for x in ("a_v", "q_v", "a_r", "q_r")})
                fresh_bad += [f"{t} x{g} {x} (saved state)" for x, v in want_.items()
                              if not np.array_equal(v.reshape(len(kr), k), e_[f"f0/x{g}/{x}"][sel])]
                rescored += 1
        for g in D.STAGE_FRESH_AT.get(stage, D.FRESH_AT):
            if f"f0/x{g}/rows" not in e:
                continue
            kr = list(rr[f"f0/g{g}/rows"])
            H_, W_, r_ = (rr[f"f0/g{g}/{x}"].astype(float) for x in ("H", "W", "r"))
            for j, i in enumerate(kr):                            # a protected row hands on its incoming packet
                if meta["rows"][i]["copy"]:
                    pH, pW, pr = (np.asarray(x, dtype=float) for x in rows_of(S0, ("protected",))[0][0]["packet"])
                    sl = slice(j * k, (j + 1) * k)
                    H_[sl], W_[sl], r_[sl] = pH, pW, pr
            A_out = (H_, W_, D.STRENGTH0 * H_, D.STRENGTH0 * W_, r_)
            union = S0["m0"].copy()
            for h in range(1, g + 1):
                union |= sched[h]
            fx, fst = sim.fresh_test(S0["body"], A_out, S0["cases"], kr, k, S0["thf"], S0["T"], S0["Tf"], union,
                                     S0["normals"], S0["am"], tag, sim.FRESH_GEN(0)(g), sim.FRESH_BIRTH(0)(g), D.T_GEN,
                                     D.POLICIES)
            if meta.get("save_fresh"):                    # the re-run's final states equal the saved ones
                fresh_bad += [f"x{g} saved {x}" for x in ("V", "r", "H", "W")
                              if not np.array_equal(fst[x], rr[f"f0/x{g}/{x}"])]
            xr = list(e[f"f0/x{g}/rows"])
            sel = [xr.index(i) for i in kr]
            fresh_bad += [f"x{g} {x}" for x, v in fx.items() if not np.array_equal(v, e[f"f0/x{g}/{x}"][sel])]
        checks["Q6_reanalysis"] = {"pass": not bad6 and not fresh_bad, "bad": bad6[:10], "fresh_bad": fresh_bad[:10],
                                   "fresh_task": list(tr), "fresh_horizons_rescored_from_saved_states": rescored}

    # Q7
    if chosen("Q7"):
        q7 = {}
        vote_fired, cue_bad, inj_bad, sched_bad, own, win_bad, nofield_bad = 0, 0, 0, [], [], 0, 0
        kap = sim.kappas()
        lens = {w: hi - lo + 1 for w, (lo, hi) in D.WINDOWS.items()}
        for t in tasks:
            e, meta = npz(paths[t][0]), meta_of(paths[t][0])
            rows = meta["rows"]
            gmax = max(r["stop"] for r in rows)
            for g in range(1, gmax + 1):
                dr = list(e[f"f0/d{g}/rows"])
                for j, i in enumerate(dr):
                    row = rows[i]
                    if row["policy"] == "vote":
                        vote_fired += int(e[f"f0/d{g}/fired"][j].astype(bool).sum())
                    if row["sigma"] == 0.0:
                        cue_bad += int((e[f"f0/d{g}/cue_dis_birth"][j] != 0).sum())
                    inj_bad += int((~e[f"f0/d{g}/injury_ok"][j].astype(bool)).sum())
                    if f"f0/d{g}/kexp" not in e:
                        continue
                    if row["field"] == "none":
                        nofield_bad += int(sum((e[f"f0/d{g}/{x}"][j] != 0).sum() for x in ("exp_full", "kexp")))
                        continue
                    w = row["window"]
                    kw = kap[row["kappa_key"] or w]
                    xw = e[f"f0/d{g}/exp_{w}"][j]
                    want = kw * xw * lens[w] / D.T_GEN
                    win_bad += int((np.abs(e[f"f0/d{g}/kexp"][j] - want) > 1e-9 * np.maximum(1.0, np.abs(want))).sum())
            S = setup(*t, stage)
            sched = masks_from(e["schedule/corners"])
            stack = np.stack([S["m0"]] + [sched[g] for g in range(1, gmax + 1)])
            if not (stack.sum((-2, -1)) == D.SIZE * D.SIZE).all() or stack.sum(0).max() > 1:
                sched_bad.append(f"{t}: not disjoint")
            _s, corners, attempts = sim.schedule(S["cases"], S["m0"], tag, gmax)
            if not (np.array_equal(corners, e["schedule/corners"]) and np.array_equal(attempts, e["schedule/attempts"])):
                sched_bad.append(f"{t}: does not recompute from its addresses")
            own.append(t[0] in D.STAGES[stage] and t[3] in D.STAGES[stage][t[0]])
        q7["the_vote_rows_never_fire"] = vote_fired == 0
        q7["every_sigma0_birth_cue_equals_its_incoming_records_signs"] = cue_bad == 0
        q7["every_injury_flips_exactly_its_patch_and_none_on_an_uninjured_row"] = inj_bad == 0
        q7["the_patches_are_disjoint_and_recompute_from_their_addresses"] = not sched_bad
        ev = B1S.event("memory", D.SIZE, S0["cases"], S0["V0"], S0["ema0"], S0["R0"], S0["T"], S0["meta"]["tag"])
        H0, W0 = edges_from(bonds(S0["R0"], True))
        mine = sim.injure((H0, W0, A.STRENGTH0 * H0, A.STRENGTH0 * W0, S0["R0"].copy()), ev["m"])
        q7["the_injury_rule_at_generation0_is_be001s_memory_event"] = bool(
            all(np.array_equal(x, ev[y]) for x, y in zip(mine, ("H", "W", "Hb", "Wb", "r"))) and np.array_equal(ev["m"], S0["m0"]))
        src = inspect.getsource(sim.lineage)
        q7["the_second_record_the_cue_and_the_protected_copy_are_taken_before_the_injury"] = bool(
            src.index("B_ = tuple(x.copy() for x in A_)") < src.index("A_ = injure(A_, M)")
            and src.index("birth_cue(A_[4][sl]") < src.index("A_ = injure(A_, M)")
            and src.index("A_in = tuple(x.copy() for x in A_)") < src.index("A_ = injure(A_, M)"))
        q7["every_task_is_a_saved_record_of_its_stage"] = all(own) and len(tasks) == len(D.stage_tasks(stage))
        q7["the_windows_kappa_x_the_windows_exposure_and_nothing_outside"] = win_bad == 0
        q7["no_exposure_on_a_field_free_row"] = nofield_bad == 0
        free = ("vote/none", "protected", "vtol-every")
        rows_m, lab_m, _am = rows_of(S0, free + ("vote/isolated", "vote/shared", "vote/shared-late"))
        _r, _a, _d, km, _f = short(S0, rows_m, tag, ad)
        rows_f = [rows_m[lab_m[x]] for x in free]
        _r, _a, _d, kf, _f = short(S0, rows_f, tag, None)
        q7["a_field_free_row_in_a_mixed_call_equals_its_field_free_run"] = all(
            same_row(km, lab_m[x], kf, j) for j, x in enumerate(free))
        rows_rr, lab_rr, _ar = rows_of(S0, ("vote/shared", "vote/shared-retained"))
        retained = {}
        c1 = sim.coupling_for(ad, rows_rr, [0, 1], k, retained)
        keep_med = retained[lab_rr["vote/shared-retained"]]
        for g_ in c1.groups:
            g_["medium"].step(np.ones(k))
        c2 = sim.coupling_for(ad, rows_rr, [0, 1], k, retained)
        by = {g_["row"]: g_ for g_ in c2.groups}
        sh_, rt_ = by[lab_rr["vote/shared"]], by[lab_rr["vote/shared-retained"]]
        q7["reset_a_new_zero_medium_at_birth_retain_the_same_medium_carried"] = bool(
            rt_["medium"] is keep_med and sh_["medium"] is not c1.groups[0]["medium"]
            and (c2.c[sh_["branches"], 0, 0] == 0).all() and (c2.c[rt_["branches"], 0, 0] > 0).all())
        rows_p, lab_p, _ap = rows_of(S0, ("protected", "vote/none"))
        seen = []
        real = sim.SRS.handoff

        def spy(A_, B_):
            seen.append(tuple(x.copy() for x in A_))
            return real(A_, B_)

        sim.SRS.handoff = spy
        try:
            short(S0, rows_p, tag, None)
        finally:
            sim.SRS.handoff = real
        pH, pW, pr = (np.asarray(x, dtype=float) for x in rows_p[lab_p["protected"]]["packet"])
        want = (pH, pW, D.STRENGTH0 * pH, D.STRENGTH0 * pW, pr)
        sl = slice(lab_p["protected"] * k, (lab_p["protected"] + 1) * k)
        q7["protected_copying_hands_on_the_incoming_packet"] = bool(
            len(seen) == 2 and all(all(np.array_equal(x[sl], y) for x, y in zip(A_, want)) for A_ in seen))
        rows_i, _li, _ai = rows_of(S0, ("vote/shared", "vote/isolated", "vtol-every", "protected"))
        r1, _a1, d1, k1, _f1 = short(S0, rows_i, tag, ad)
        r2, _a2, d2, k2, _f2 = short(S0, rows_i, tag, ad, T=np.roll(S0["T"], 7, -1))
        fx = ("exp_full", "exp_early", "exp_late", "kexp")
        target_same = all(all(np.array_equal(k1[g][x], k2[g][x]) for x in ("V", "r", "H", "W"))
                          and all(np.array_equal(d1[g][x], d2[g][x]) for x in fx) for g in (1, 2))
        real_gen = sim.generation

        def other_mask(*args_, **kw):
            args_ = list(args_)
            args_[8] = np.roll(args_[8], 9, -1)
            return real_gen(*args_, **kw)

        sim.generation = other_mask
        try:
            r3m, _a3m, d3m, k3m, _f3m = short(S0, rows_i, tag, ad)
        finally:
            sim.generation = real_gen
        mask_same = all(all(np.array_equal(k1[g][x], k3m[g][x]) for x in ("V", "r", "H", "W"))
                        and all(np.array_equal(d1[g][x], d3m[g][x]) for x in fx) for g in (1, 2))
        q7["another_target_leaves_every_state_and_exposure_unchanged"] = bool(target_same)
        q7["another_patch_mask_given_to_the_generation_leaves_every_state_and_exposure_unchanged"] = bool(mask_same)
        checks["Q7_efficacy_injury_and_field"] = {"pass": all(q7.values()), "items": q7, "vote_fired": vote_fired,
                                                 "cue_disagreements": cue_bad, "injury_failures": inj_bad,
                                                 "window_mismatches": win_bad, "field_free_exposures": nofield_bad,
                                                 "schedule": sched_bad[:5]}

    # Q8
    if chosen("Q8"):
        rows_q, _lq, _aq = rows_of(S0, ("vote/none", "vote/isolated", "vote/shared", "vote/shared-early", "protected"))
        outs = []
        for order in (list(range(len(rows_q))), list(reversed(range(len(rows_q))))):
            rd, al, dg, kp, _fp = short(S0, [rows_q[i] for i in order], tag, ad, keep=(2,))
            outs.append((order, rd, dg, kp))
        (o1, rd1, dg1, kp1), (o2, rd2, dg2, kp2) = outs
        ok8 = True
        for i in range(len(rows_q)):
            j1, j2 = o1.index(i), o2.index(i)
            for g in (1, 2):
                ok8 &= all(np.array_equal(rd1[g][x][j1], rd2[g][x][j2]) for x in rd1[g])
                ok8 &= all(np.array_equal(dg1[g][x][j1], dg2[g][x][j2]) for x in dg1[g])
            ok8 &= all(np.array_equal(kp1[2][x][j1 * k:(j1 + 1) * k], kp2[2][x][j2 * k:(j2 + 1) * k]) for x in ("V", "r", "H", "W"))
        checks["Q8_pairing"] = {"pass": bool(ok8), "rows": len(rows_q)}

    # Q9
    if chosen("Q9"):
        def units(rows, fresh_at):
            u = 0.0
            for r_ in rows:
                n = r_["stop"]
                u += n * ((W_DET if r_["policy"] != "vote" else 1.0) + (W_FIELD if r_["field"] != "none" else 0.0))
                u += sum(1 for g in fresh_at if g <= n)
            return u
        stage_fresh = D.STAGE_FRESH_AT.get(stage, D.FRESH_AT)
        per_unit = [done[t]["cpu_s"] / units(meta_of(paths[t][0])["rows"], stage_fresh) for t in tasks if t in done]
        rate = float(np.mean(per_unit))
        dev_units = units(D.CORE, D.STAGE_FRESH_AT["development"])
        pre_units = units(D.CORE, D.STAGE_FRESH_AT["preflight"])
        n_dev, n_pre = len(D.stage_tasks("development")), len(D.stage_tasks("preflight"))
        dev_h = rate * dev_units * n_dev / 3600
        pre_h = (sum(rec["cpu_s"] for rec in done.values()) if stage == "preflight" else rate * pre_units * n_pre) / 3600
        cpu_h = dev_h + pre_h + CHECKS_CPU_H
        wall_h = dev_h / WORKERS * 1.15 + rate * dev_units / 3600
        rss = max(rec["maxrss_mb"] for rec in done.values())
        checks["Q9_resources"] = {"pass": bool(cpu_h * HEADROOM <= CAP and wall_h * HEADROOM <= 12 and rss <= 2048),
                                  "forecast_phase_b_cpu_h": round(cpu_h, 2),
                                  "forecast_phase_b_cpu_h_with_headroom": round(cpu_h * HEADROOM, 2),
                                  "development_cpu_h": round(dev_h, 2), "preflight_cpu_h": round(pre_h, 2),
                                  "preflight_measured": stage == "preflight", "checks_cpu_h": CHECKS_CPU_H,
                                  "forecast_wall_h_10": round(wall_h, 2), "cpu_s_per_vote_row_generation_8_cases":
                                  round(rate, 3), "development_units_a_task": dev_units, "preflight_units_a_task": pre_units,
                                  "development_tasks": n_dev, "preflight_tasks": n_pre, "worker_rss_mb": rss,
                                  "w_det": W_DET, "w_field": W_FIELD, "cap": CAP, "headroom": HEADROOM}

    # Q10
    if chosen("Q10"):
        out = root / "analysis_dry_run"
        out.mkdir(exist_ok=True)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        procs = [subprocess.run([sys.executable, "-m", f"e2e006.{mod}"] + args_, cwd=LANE, capture_output=True, text=True, env=env)
                 for mod, args_ in (("predict", ["--root", str(root), "--out", str(out)]), ("tables", ["--dir", str(out)]))]
        got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
        from e2e006 import predict as PR
        ids = sorted(p for p, _w, _f, _k in PR.parts())
        scored = sorted(p["id"] for p in got.get("parts", []))
        sizes = {q.name: q.stat().st_size for q in out.iterdir() if q.is_file()}
        git_files = [f for f in list((LANE / "e2e006").rglob("*")) + list((LANE / "probes").rglob("*p63*"))
                     + [LANE / "tests" / "test_e2e006.py", LANE / "PLAN_E2E006.md", LANE / "REGISTRATION_E2E006.md"]
                     if f.is_file() and "__pycache__" not in f.parts]
        big = [str(f.relative_to(LANE)) for f in git_files if f.stat().st_size > 262144]
        checks["Q10_reader_dry_run"] = {"pass": all(p.returncode == 0 for p in procs) and scored == ids
                                        and max(sizes.values(), default=0) <= 262144 and not big,
                                        "stderr": "".join(p.stderr for p in procs)[-600:], "sizes": sizes, "big_git_files": big,
                                        "parts_available": sum(1 for p in got.get("parts", []) if p.get("available"))}

    failed = [x for x, v in checks.items() if not v["pass"]]
    receipt = {"status": "FAIL" if failed else "PASS", "failed": failed, "study": D.STUDY, "design_digest": D.digest(),
               "stage": stage, "root": str(root), "tasks": len(tasks),
               "load_1min_at_check": float(open("/proc/loadavg").read().split()[0]),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1),
               "cpu_s": round(time.process_time(), 1), "only": only, "checks": checks}
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=1, default=str) + "\n")
    print(json.dumps({"status": receipt["status"], "failed": failed}, indent=1))


if __name__ == "__main__":
    main()
