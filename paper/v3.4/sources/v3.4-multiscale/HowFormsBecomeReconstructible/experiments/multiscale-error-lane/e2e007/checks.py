"""E2E007's qualification Q1-Q10 (DRAFT): python -m e2e007.checks --root STAGE_ROOT --cpus LIST [--debug] [--only Q9,Q10]
  (with --debug: ROOT/debug_qualification_receipt.json; otherwise e2e007/frozen/qualification_receipt.json)

Fixed in PLAN_E2E007.md (Q1-Q10, E2E006's adapted) before their results; in phase A they run on the debug run (AR006's
900948, the six rows to g 3, the fresh successors after g 3), in phase B on the preflight (AR006's 900929). In-process
checks run short generations (SHORT updates) of the stage's first task.
  Q1  complete and finite: every task's reads, fresh reads and diagnostics at their shapes (the injury's checks, the
      observer, the exposures in every generation with a field row), generation 0 for every row, the fresh successors and
      their saved final states, the schedule's corners and attempts; every value finite
  Q2  serial equals parallel: one task rerun in-process gives bit-identical endpoints and states
  Q3  the bridges: every restored raw file equals its manifest's sha256 (rehashed); in-process, none/memory and
      raise/memory equal e2e006.sim.lineage's vote/none and vote/shared under the stage's tag (reads, E2E006's
      diagnostics, states; two generations of 2,000 updates); P66s stands (phase A's and Amendment 1's records); the
      routed generation is e2e002.sim.generation's
      source with its detector call and its body call routed, each once; every task's acquisition and generation-0 packets
      equal their sources (the workers' records)
  Q4  an independent replay: generation 1 of relax/memory, raise/body and (from Amendment 1) relax-matched/memory at its
      kappa' for one task, each through ar003.sim.run_vd's own
      source (its event line replaced by the newborn and the row's incoming packet, injured for the memory row and intact
      for the body row; its second-record line by the incoming packet before any injury; its two stream lines by the
      generation's names; its body line by a coupling written here from the rulings: one msefield Medium stepped directly,
      the stress, the signed response, the body flip at t_body; each substitution asserted once), equal to the stage's
      saved generation-1 V, r, H and W bit for bit
  Q5  aliases: the alias table is complete (every label has a row; a row's labels share one packet, one target and one
      response); a field row listed twice gives the same lineage bit for bit
  Q6  reanalysis: the reads recomputed from the saved states, with the union and own patches rebuilt from the saved corners,
      equal the shards'; every saved fresh state re-scores to the shards' fresh reads; one task's fresh successors re-run
      from the saved outgoing records equal the shards' reads and saved final states
  Q7  efficacy, the injuries and the field: the vote rows never fire; at sigma 0 every birth cue equals its incoming
      record's signs; every injury flips exactly its patch (memory: in the record at update 0; body: in V and E at
      t_body); the body flip is exactly the patch at t_body and nothing at any other update; a body row enters every
      generation with its record uninjured, a memory row with the patch flipped; the patches are disjoint and recompute from
      their addresses; the injury rule at generation 0 equals be001.sim.event's memory rule; the second record and the cue
      are taken before the injury; every task is a saved record of its stage; the realized response is kappa x the
      generation's exposure on every field row; no exposure on a field-free row; a field-free row in a mixed call equals its
      field-free run; relax and raise at kappa 0 equal none, and an empty body patch equals no injury; the information
      boundary: another target, or another patch mask given to the generation, leaves every state and exposure unchanged;
      the observer is output only (off equals on)
  Q8  pairing: reordering the rows changes no row's output
  Q9  resources: phase B forecast structurally from this stage's CPU per vote-equivalent row-generation (a field
      row-generation weighs W_FIELD more, a fresh test one): the development's and the preflight's row-generations, plus
      Q1-Q10 and the reader, with HEADROOM for other users' load, within CAP CPU-hours (35, the lead's) and 12 h
      of wall on 10 workers; worker memory within 2 GB
  Q10 the reader's dry run: predict and tables complete, every part scored or marked unavailable, every output and every
      E2E007 git file 256 KiB or less
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
from e2e006 import design as D6  # noqa: E402
from e2e006 import sim as S6E  # noqa: E402
from e2e007 import design as D  # noqa: E402
from e2e007 import sim  # noqa: E402
from e2e007 import worker as W  # noqa: E402
from gc001 import sim as GCS  # noqa: E402
from lr001.sim import edges_from  # noqa: E402
from lr005 import sim as L5S  # noqa: E402
from msefield import core as MF  # noqa: E402
from msegrid.core import birth, bonds  # noqa: E402
from sr001 import sim as SRS  # noqa: E402

FROZEN = LANE / "e2e007" / "frozen"
W_FIELD = 0.5                  # E2E006's: a medium's step about half a vote row-generation's tissue
SHORT = 500                    # the in-process checks' generations (updates)
CAP = 40.0                     # the lead's phase B cap (CPU-hours, with HEADROOM), ruled at 00:44:47Z (Amendment 2; 35 at
                               # Amendment 1); the development is refused unless the preflight's receipt passes, so Q9
                               # enforces it
CHECKS_CPU_H = 0.4             # Q1-Q10 on the preflight and the reader
HEADROOM = 1.25
WORKERS = 10
FX = ("exp_full", "exp_early", "exp_late", "kexp")


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


def rows_of(S, labels, stop=2, **over):
    lins = [dict(x, stop=stop, **over) for x in D.ALL if x["label"] in labels]
    rows, lab, al, _src = sim.packets(S["raw"], S["meta"], S["cases"], S["V0"], S["ema0"], S["R0"], S["T"], lins)
    return rows, lab, al


def short(S, rows, tag, field, gens=2, t_gen=SHORT, T=None, keep=(1, 2), **kw):
    sched = sim.schedule(S["cases"], S["m0"], tag, gens)[0]
    return sim.lineage(S["body"], rows, S["cases"], S["thf"], S["T"] if T is None else T, S["Tf"], S["m0"], S["am"],
                       S["normals"], tag, sim.GEN_NAMES(0), sim.BIRTH_NAMES(0), sched=sched, t_gen=t_gen, keep=keep,
                       field=field, **kw)


def same_row(k1, i1, k2, i2, gens=(1, 2)):
    """Row i1's kept states in run 1 equal row i2's in run 2 at every generation in gens (V, r, H, W)."""
    ok = True
    for g in gens:
        a, b = k1[g], k2[g]
        k = a["V"].shape[0] // len(a["rows"])
        j1, j2 = a["rows"].index(i1), b["rows"].index(i2)
        ok &= all(np.array_equal(a[x][j1 * k:(j1 + 1) * k], b[x][j2 * k:(j2 + 1) * k]) for x in ("V", "r", "H", "W"))
    return bool(ok)


def same_reads(o1, i1, o2, i2, gens=(1, 2)):
    ok = True
    for g in gens:
        a, b = o1[1][g].index(i1), o2[1][g].index(i2)
        ok &= all(np.array_equal(o1[0][g][x][a], o2[0][g][x][b]) for x in o1[0][g])
    return bool(ok)


# ------------------------------------------------------------------------------------------------ Q4's own route
class Indep:
    """Q4's coupling, written here from the rulings (not e2e007.sim.Coupling): one row's k branches, one msefield Medium
    over FIELD['positions']; every update: at t_body on the body row, the patch M flipped in V and E; the gain times
    (1 + kappa x) (raise) or divided by it (relax), x the exposure after the previous update's step (zero at the first);
    then dl001.sim.body; then each sheet's mean |r - V-tilde| emitted into the medium's step."""

    def __init__(self, k, kappa, sign, M=None, t_body=None):
        f = D.FIELD
        self.med = MF.Medium(f["positions"], f["D"], f["gamma"], f["leakage"], dt=f["dt"], m=f["m"], margin=f["margin"])
        self.kappa, self.sign, self.M, self.tb = kappa, sign, M, t_body
        self.x = np.zeros(k)

    def __call__(self, t, V, E, r, thb, z, p, gain, alpha, G):
        if self.M is not None and t == self.tb:
            V, E = np.where(self.M, -V, V), np.where(self.M, -E, E)
        f = 1.0 + self.kappa * self.x[:, None, None]
        out = DS.body(V, E, r, thb, z, p, gain * f if self.sign > 0 else gain / f, alpha, G)
        self.x = self.med.step(np.abs(r - out[2]).mean((-2, -1)))
        return out


def run_vd_field():
    """ar003.sim.run_vd's own source with five substitutions (each asserted once): e2e006.checks's, unchanged."""
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
    exec(compile(src, "<ar003.sim.run_vd with a field (e2e007 Q4)>", "exec"), ns)
    return ns


def q4(task, stage, shard, rawshard):
    S = setup(*task, stage)
    e, rr, meta = npz(shard), npz(rawshard), meta_of(shard)
    k = len(S["cases"])
    tag = D.STAGE_TAG[stage]
    rows, _lab, _al = rows_of(S, ("relax/memory",))
    H, Wm, r = (np.asarray(x, dtype=float) for x in rows[0]["packet"])
    clean = (H.copy(), Wm.copy(), D.STRENGTH0 * H, D.STRENGTH0 * Wm, r.copy())
    m1 = masks_from(e["schedule/corners"])[1]
    hurt = sim.injure(tuple(x.copy() for x in clean), m1)
    newborn = birth(tag, S["cases"], *sim.BIRTH_NAMES(0)(1), side=D.SIDE)
    kept = list(rr["f0/g1/rows"])
    out = {}
    replays = [("relax/memory", hurt, -1, None, D.FIELD["kappa"]), ("raise/body", clean, 1, m1, D.FIELD["kappa"])]
    if "relax-matched/memory" in meta["labels"]:                     # Amendment 1: the matched row at its kappa'
        replays.append(("relax-matched/memory", hurt, -1, None, D.KAPPA_MATCHED))
    for label, A_, sign, M, kap in replays:
        ns = run_vd_field()
        ns["_BIRTH_EV"] = {"V": newborn, "E": newborn.copy(), "r": A_[4], "H": A_[0], "W": A_[1], "Hb": A_[2],
                           "Wb": A_[3], "aval": sim.birth_cue(r, S["normals"], 0.0), "am": S["am"], "m": m1,
                           "target": S["T"], "old": None, "mis": np.zeros_like(S["am"])}
        ns["_SECOND"] = (r, H, Wm, D.STRENGTH0 * H, D.STRENGTH0 * Wm)
        ns["_NAMES"] = sim.GEN_NAMES(0)(1)
        ns["_FIELD"] = Indep(k, kap, sign, M, D.t_body())
        res = ns["run_vd"](S["body"], "none", 0.0, ["vote"], S["cases"], newborn, newborn, r, S["th"], S["T"],
                           S["theta"], set(), gain=E2D.GAIN, tag=tag, window=D.T_GEN, size=D.SIZE, clock=E2D.CLOCK,
                           detectors={"vote": D.POLICIES["vote"]})
        pos = kept.index(meta["labels"][label])
        sv = slice(pos * k, (pos + 1) * k)
        out[label] = {x: bool(np.array_equal(res[x], rr[f"f0/g1/{x}"][sv].astype(res[x].dtype)))
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
    labels = tuple(x["label"] for x in D.lineages(stage))
    fresh_set = D.STAGE_FRESH_AT.get(stage, D.FRESH_AT)
    checks = {}

    # Q1
    if chosen("Q1"):
        bad = []
        reads = tuple(sim.READS) + tuple(sim.UNION_READS)
        fresh_ends = tuple(sim.UNION_READS) + ("a_v", "q_v", "a_r", "q_r")
        for t in tasks:
            sp, rp = paths[t]
            if not sp.exists() or not rp.exists():
                bad.append(f"{t}: missing")
                continue
            e, rr, meta = npz(sp), npz(rp), meta_of(sp)
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
                diag = (tuple(sim.DIAG) + ("cue_dis_birth", "injury_ok", "body_injury_ok")
                        + tuple(f"agree_{o}" for o in D.OBS) + (FX if fieldy else ()))
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
                    bad += [] if list(rr.get(f"f0/x{g}/rows", [])) == alive else [f"{t}: raw f0/x{g}/rows"]
                    for x in ("V", "r", "H", "W"):
                        key = f"f0/x{g}/{x}"
                        bad += [] if key in rr and rr[key].shape == (len(alive) * kk, D.SIDE, D.SIDE) else [f"{t}: raw {key}"]
                if g in D.HORIZONS:
                    for x in ("V", "r", "H", "W"):
                        key = f"f0/g{g}/{x}"
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
        rows7, lab7, _a7 = rows_of(S0, ("none/memory", "raise/memory"))
        lins6 = [dict(x, stop=2) for x in D6.ALL if x["label"] in ("vote/none", "vote/shared")]
        rows6, lab6, _a6, _s6 = S6E.packets(S0["raw"], S0["meta"], S0["cases"], S0["V0"], S0["ema0"], S0["R0"], S0["T"],
                                            lins6)
        o7 = short(S0, rows7, tag, ad, t_gen=2000)
        sched_b = sim.schedule(S0["cases"], S0["m0"], tag, 2)[0]
        o6 = S6E.lineage(S0["body"], rows6, S0["cases"], S0["thf"], S0["T"], S0["Tf"], S0["m0"], S0["am"], S0["normals"],
                         tag, sim.GEN_NAMES(0), sim.BIRTH_NAMES(0), sched=sched_b, t_gen=2000, keep=(1, 2),
                         field=S6E.field_adapter())
        ok3 = True
        for mine, theirs in (("none/memory", "vote/none"), ("raise/memory", "vote/shared")):
            i7, i6 = lab7[mine], lab6[theirs]
            ok3 &= same_row(o7[3], i7, o6[3], i6) and same_reads(o7, i7, o6, i6)
            for g in (1, 2):
                a_, b_ = o7[1][g].index(i7), o6[1][g].index(i6)
                ok3 &= all(np.array_equal(o7[2][g][x][a_], o6[2][g][x][b_]) for x in o6[2][g])
        q3["none_and_raise_under_memory_injury_equal_e2e006s_vote_none_and_vote_shared"] = bool(ok3)
        p66s = [json.loads((LANE / "probes" / "results" / f).read_text()) for f in ("p66s_e2e007_bridges.json",
                "p66s_e2e007_bridges_a1.json") if (LANE / "probes" / "results" / f).exists()]
        q3["p66s_bridges_stand_phase_a_and_amendment_1"] = bool(len(p66s) == 2 and all(r.get("all_equal") for r in p66s))
        gsrc = inspect.getsource(E2.generation)
        q3["the_routed_generation_is_e2e002s_with_two_calls_routed"] = bool(
            gsrc.count(sim.DETECT_CALL) == 1 and gsrc.count(sim.BODY_CALL) == 1
            and sim.generation.__globals__["detect_vt"] is S6.detect
            and sim._COUPLING is None and sim._BODY is None and sim._OBS is None)
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
        ways = {x["label"]: (x["field"], x["medium"], x["window"], x["target"], x["response"], x.get("kappa_key"))
                for x in D.lineages(stage)}
        for t in tasks:
            meta = meta_of(paths[t][0])
            lab, rows = meta["labels"], meta["rows"]
            ok_tab &= set(labels) <= set(lab)
            ok_tab &= all(sorted(rows[i]["labels"]) == sorted(x for x, j in lab.items() if j == i) for i in range(len(rows)))
            ok_tab &= all(len({ways[x] for x in rows[i]["labels"] if x in ways}) <= 1 for i in range(len(rows)))
        q5["the_alias_table_is_complete"] = bool(ok_tab)
        rs, _l5, _a5 = rows_of(S0, ("raise/body",))
        r5, _a5r, d5, k5, _f5 = short(S0, [rs[0], dict(rs[0])], tag, ad)
        q5["a_field_row_listed_twice_gives_the_same_lineage"] = bool(all(
            all(np.array_equal(v[0], v[1]) for v in r5[g].values()) and all(np.array_equal(v[0], v[1]) for v in d5[g].values())
            and all(np.array_equal(k5[g][x][:k], k5[g][x][k:]) for x in ("V", "r", "H", "W")) for g in (1, 2)))
        checks["Q5_aliases"] = {"pass": all(q5.values()), "items": q5}

    # Q6
    if chosen("Q6"):
        bad6, fresh_bad, rescored = [], [], 0
        for t in tasks:
            e, rr = npz(paths[t][0]), npz(paths[t][1])
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
            for g in fresh_set:                       # the saved fresh states re-score to the shards
                if f"f0/x{g}/rows" not in rr:
                    continue
                kr = list(rr[f"f0/x{g}/rows"])
                idx = np.tile(np.arange(k), len(kr))
                union = S["m0"].copy()
                for h in range(1, g + 1):
                    union |= sched[h]
                su = sim.score(rr[f"f0/x{g}/V"], rr[f"f0/x{g}/r"], S["T"][idx], S["Tf"][:, idx], union[idx])
                xr = list(e[f"f0/x{g}/rows"])
                sel = [xr.index(i) for i in kr]
                want_ = {x: su[src] for x, src in sim.UNION_READS.items()}
                want_.update({x: su[x] for x in ("a_v", "q_v", "a_r", "q_r")})
                fresh_bad += [f"{t} x{g} {x} (saved state)" for x, v in want_.items()
                              if not np.array_equal(v.reshape(len(kr), k), e[f"f0/x{g}/{x}"][sel])]
                rescored += 1
        e, rr = npz(paths[tr][0]), npz(paths[tr][1])
        sched = masks_from(e["schedule/corners"])
        for g in fresh_set:                           # one task's fresh successors re-run from the saved outgoing records
            if f"f0/x{g}/rows" not in e:
                continue
            kr = list(rr[f"f0/g{g}/rows"])
            H_, W_, r_ = (rr[f"f0/g{g}/{x}"].astype(float) for x in ("H", "W", "r"))
            A_out = (H_, W_, D.STRENGTH0 * H_, D.STRENGTH0 * W_, r_)
            union = S0["m0"].copy()
            for h in range(1, g + 1):
                union |= sched[h]
            fx, fst = sim.fresh_test(S0["body"], A_out, S0["cases"], kr, k, S0["thf"], S0["T"], S0["Tf"], union,
                                     S0["normals"], S0["am"], tag, sim.FRESH_GEN(0)(g), sim.FRESH_BIRTH(0)(g), D.T_GEN,
                                     D.POLICIES)
            fresh_bad += [f"x{g} saved {x}" for x in ("V", "r", "H", "W") if not np.array_equal(fst[x], rr[f"f0/x{g}/{x}"])]
            xr = list(e[f"f0/x{g}/rows"])
            sel = [xr.index(i) for i in kr]
            fresh_bad += [f"x{g} {x}" for x, v in fx.items() if not np.array_equal(v, e[f"f0/x{g}/{x}"][sel])]
        checks["Q6_reanalysis"] = {"pass": not bad6 and not fresh_bad, "bad": bad6[:10], "fresh_bad": fresh_bad[:10],
                                   "fresh_task": list(tr), "fresh_horizons_rescored_from_saved_states": rescored}

    # Q7
    if chosen("Q7"):
        q7 = {}
        vote_fired, cue_bad, inj_bad, sched_bad, own, resp_bad, nofield_bad = 0, 0, 0, [], [], 0, 0
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
                    inj_bad += int((~e[f"f0/d{g}/body_injury_ok"][j].astype(bool)).sum())
                    if f"f0/d{g}/kexp" not in e:
                        continue
                    if row["field"] == "none":
                        nofield_bad += int(sum((e[f"f0/d{g}/{x}"][j] != 0).sum() for x in ("exp_full", "kexp")))
                        continue
                    want = sim.row_kappa(row) * e[f"f0/d{g}/exp_full"][j]           # the row's own kappa
                    resp_bad += int((np.abs(e[f"f0/d{g}/kexp"][j] - want) > 1e-9 * np.maximum(1.0, np.abs(want))).sum())
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
        q7["every_injury_flips_exactly_its_patch_memory_in_the_record_body_in_V_and_E"] = inj_bad == 0
        q7["the_patches_are_disjoint_and_recompute_from_their_addresses"] = not sched_bad
        ev = B1S.event("memory", D.SIZE, S0["cases"], S0["V0"], S0["ema0"], S0["R0"], S0["T"], S0["meta"]["tag"])
        H0, W0 = edges_from(bonds(S0["R0"], True))
        mine = sim.injure((H0, W0, A.STRENGTH0 * H0, A.STRENGTH0 * W0, S0["R0"].copy()), ev["m"])
        q7["the_injury_rule_at_generation0_is_be001s_memory_event"] = bool(
            all(np.array_equal(x, ev[y]) for x, y in zip(mine, ("H", "W", "Hb", "Wb", "r"))) and np.array_equal(ev["m"], S0["m0"]))
        src = inspect.getsource(sim.lineage)
        q7["the_second_record_and_the_cue_are_taken_before_the_injury"] = bool(
            src.index("B_ = tuple(x.copy() for x in A_)") < src.index("A_ = injure(A_, M)")
            and src.index("birth_cue(A_[4][sl]") < src.index("A_ = injure(A_, M)"))
        q7["every_task_is_a_saved_record_of_its_stage"] = all(own) and len(tasks) == len(D.stage_tasks(stage))
        q7["the_realized_response_is_kappa_x_the_exposure_on_every_field_row"] = resp_bad == 0
        q7["no_exposure_on_a_field_free_row"] = nofield_bad == 0
        # the body flip, directly: exactly the patch at t_body, nothing at any other update, the record untouched
        seen = []
        real_body = sim.S.body

        def fake(V, E, r, thb, z, p, gain, alpha, G):
            seen.append((V.copy(), E.copy(), r.copy()))
            return V, E, V, None, None

        rng = np.random.default_rng(11)
        Vx, Ex, rx = rng.normal(size=(8, D.SIDE, D.SIDE)), rng.normal(size=(8, D.SIDE, D.SIDE)), np.sign(
            rng.normal(size=(8, D.SIDE, D.SIDE)))
        Mx = masks_from(npz(paths[tr][0])["schedule/corners"])[1]
        sim.S.body = fake
        sim._BODY = {"t": 7, "M": Mx, "ok": np.zeros(8, bool)}
        try:
            for tt in (6, 7, 8):
                sim.field_body(tt, Vx, Ex, rx, 0, None, 0, 1.0, 0.1, None)
            okx = sim._BODY["ok"].copy()
        finally:
            sim.S.body, sim._BODY = real_body, None
        (V6, E6, r6), (V7, E7, r7), (V8, E8, r8) = seen
        q7["the_body_flip_is_exactly_the_patch_at_t_body_and_nothing_at_other_updates"] = bool(
            np.array_equal(V6, Vx) and np.array_equal(E6, Ex) and np.array_equal(V8, Vx) and np.array_equal(E8, Ex)
            and np.array_equal(V7, np.where(Mx, -Vx, Vx)) and np.array_equal(E7, np.where(Mx, -Ex, Ex))
            and all(np.array_equal(x, rx) for x in (r6, r7, r8)) and okx.all())
        # the record entering each generation: body rows uninjured, memory rows with the patch flipped
        rows_t, lab_t, _at = rows_of(S0, labels)
        entering, handed = [], []
        real_gen, real_hand = sim.generation, sim.SRS.handoff

        def spy_gen(*a_, **kw):
            entering.append(tuple(x.copy() for x in a_[5]))
            return real_gen(*a_, **kw)

        def spy_hand(A_, B_):
            out_ = real_hand(A_, B_)
            handed.append(tuple(x.copy() for x in out_[0]))
            return out_

        sim.generation, sim.SRS.handoff = spy_gen, spy_hand
        try:
            short(S0, rows_t, tag, ad)
        finally:
            sim.generation, sim.SRS.handoff = real_gen, real_hand
        sch_t = sim.schedule(S0["cases"], S0["m0"], tag, 2)[0]
        H1, W1, r1 = (np.asarray(x, dtype=float) for x in rows_t[0]["packet"])
        incoming = {1: tuple(np.concatenate([x] * len(rows_t)) for x in (H1, W1, D.STRENGTH0 * H1, D.STRENGTH0 * W1, r1)),
                    2: handed[0]}
        ok_in = len(entering) == 2
        for g in (1, 2):
            hurt_g = sim.injure(tuple(x.copy() for x in incoming[g]), np.tile(sch_t[g], (len(rows_t), 1, 1)))
            for label, i in lab_t.items():
                sl = slice(i * k, (i + 1) * k)
                want_g = hurt_g if label.endswith("/memory") else incoming[g]
                ok_in &= all(np.array_equal(x[sl], y[sl]) for x, y in zip(entering[g - 1], want_g))
        q7["a_body_row_enters_each_generation_with_its_record_uninjured_a_memory_row_with_the_patch_flipped"] = bool(ok_in)
        # a field-free row in a mixed call equals its field-free run
        _r, _a, _d, km, _f = short(S0, rows_t, tag, ad)
        free = ("none/memory", "none/body")
        _r, _a, _d, kf, _f = short(S0, [rows_t[lab_t[x]] for x in free], tag, None)
        q7["a_field_free_row_in_a_mixed_call_equals_its_field_free_run"] = all(
            same_row(km, lab_t[x], kf, j) for j, x in enumerate(free))
        # kappa 0, the empty body patch
        o0 = short(S0, rows_t, tag, ad, kappa=0.0)
        fieldy_labels = [x["label"] for x in D.lineages(stage) if x["field"] != "none"]
        q7["every_field_row_at_kappa0_equals_none"] = all(
            same_row(o0[3], lab_t[x], o0[3], lab_t["none/" + D._A[x]["target"]])
            and same_reads(o0, lab_t[x], o0, lab_t["none/" + D._A[x]["target"]]) for x in fieldy_labels)
        empty = {g: np.zeros((len(rows_t) * k, D.SIDE, D.SIDE), bool) for g in (1, 2)}
        oe = short(S0, rows_t, tag, ad, body_masks=empty)
        body_labels = ("none/body", "raise/body", "relax/body")
        ru, lu, _au = rows_of(S0, body_labels, injured=False)
        ou = short(S0, ru, tag, ad)
        q7["an_empty_body_patch_equals_no_injury"] = all(
            same_row(oe[3], lab_t[x], ou[3], lu[x]) and same_reads(oe, lab_t[x], ou, lu[x]) for x in body_labels)
        # the information boundary
        r1_, _a1, d1, k1, _f1 = short(S0, rows_t, tag, ad)
        r2_, _a2, d2, k2, _f2 = short(S0, rows_t, tag, ad, T=np.roll(S0["T"], 7, -1))
        target_same = all(all(np.array_equal(k1[g][x], k2[g][x]) for x in ("V", "r", "H", "W"))
                          and all(np.array_equal(d1[g][x], d2[g][x]) for x in FX) for g in (1, 2))

        def other_mask(*args_, **kw):
            args_ = list(args_)
            args_[8] = np.roll(args_[8], 9, -1)
            return real_gen(*args_, **kw)

        sim.generation = other_mask
        try:
            _r3, _a3, d3, k3, _f3 = short(S0, rows_t, tag, ad)
        finally:
            sim.generation = real_gen
        mask_same = all(all(np.array_equal(k1[g][x], k3[g][x]) for x in ("V", "r", "H", "W"))
                        and all(np.array_equal(d1[g][x], d3[g][x]) for x in FX) for g in (1, 2))
        q7["another_target_leaves_every_state_and_exposure_unchanged"] = bool(target_same and not np.array_equal(
            r1_[2]["a_v"], r2_[2]["a_v"]))
        q7["another_patch_mask_given_to_the_generation_leaves_every_state_and_exposure_unchanged"] = bool(mask_same)
        # the observer is output only
        r_off, _ao, d_off, k_off, _fo = short(S0, rows_t, tag, ad, observe=False)
        q7["the_observer_is_output_only"] = bool(all(
            all(np.array_equal(k1[g][x], k_off[g][x]) for x in ("V", "r", "H", "W"))
            and all(np.array_equal(r1_[g][x], r_off[g][x]) for x in r1_[g])
            and all(np.array_equal(d1[g][x], d_off[g][x]) for x in d_off[g]) for g in (1, 2)))
        checks["Q7_efficacy_injuries_and_field"] = {"pass": all(q7.values()), "items": q7, "vote_fired": vote_fired,
                                                   "cue_disagreements": cue_bad, "injury_failures": inj_bad,
                                                   "response_mismatches": resp_bad,
                                                   "field_free_exposures": nofield_bad, "schedule": sched_bad[:5]}

    # Q8
    if chosen("Q8"):
        rows_q, _lq, _aq = rows_of(S0, labels)
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
                u += n * (1.0 + (W_FIELD if r_["field"] != "none" else 0.0))
                u += sum(1 for g in fresh_at if g <= n)
            return u
        per_unit = [done[t]["cpu_s"] / units(meta_of(paths[t][0])["rows"], fresh_set) for t in tasks if t in done]
        rate = float(np.mean(per_unit))
        main_rows = D.lineages("development")
        dev_units = units(main_rows, D.STAGE_FRESH_AT.get("development", D.FRESH_AT))
        pre_units = units(main_rows, D.STAGE_FRESH_AT.get("preflight", D.FRESH_AT))
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
                                  "w_field": W_FIELD, "cap": CAP, "cap_status": "the lead's, 00:44:47Z (Amendment 2; 35 at Amendment 1)",
                                  "headroom": HEADROOM}

    # Q10
    if chosen("Q10"):
        out = root / "analysis_dry_run"
        out.mkdir(exist_ok=True)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        procs = [subprocess.run([sys.executable, "-m", f"e2e007.{mod}"] + args_, cwd=LANE, capture_output=True, text=True, env=env)
                 for mod, args_ in (("predict", ["--root", str(root), "--out", str(out)]), ("tables", ["--dir", str(out)]))]
        got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
        from e2e007 import predict as PR
        ids = sorted(p for p, _w, _f, _k in PR.parts())
        scored = sorted(p["id"] for p in got.get("parts", []))
        sizes = {q.name: q.stat().st_size for q in out.iterdir() if q.is_file()}
        git_files = [f for f in list((LANE / "e2e007").rglob("*")) + list((LANE / "probes").rglob("*p66*"))
                     + [LANE / "tests" / "test_e2e007.py", LANE / "PLAN_E2E007.md", LANE / "REGISTRATION_E2E007.md"]
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
