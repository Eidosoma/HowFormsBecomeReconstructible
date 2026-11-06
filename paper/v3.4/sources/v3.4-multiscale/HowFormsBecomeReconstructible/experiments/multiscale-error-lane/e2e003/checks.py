"""E2E003's qualification Q1-Q10 (DRAFT): python -m e2e003.checks --root STAGE_ROOT --cpus LIST [--debug]
  (with --debug: ROOT/debug_qualification_receipt.json; otherwise e2e003/frozen/qualification_receipt.json)

Fixed in PLAN_E2E003.md before their results; in phase B they run on the preflight (AR006's 900929, 900947).
  Q1  complete and finite: every task's endpoints and diagnostics at their shapes (rows alive at each generation = rows
      whose stop reaches it), generation 0 for every row, the schedule's corners and attempts; every value finite
  Q2  serial equals parallel: one task rerun in-process gives bit-identical endpoints, diagnostics and states
  Q3  the bridges: every restored raw file equals its manifest's sha256 (rehashed); the generation-0 replay
      (e2e003.sim.replay0) of one task under memory@0, memory@1 and none@0 reproduces every arm's saved final state bit
      for bit, vtol included; with the injury disabled, e2e003.sim.lineage equals e2e002.sim.lineage (unchanged) bit for
      bit on the vote and vms rows (two generations, 2,000 updates); the routed generation is e2e002.sim.generation's
      source with its one detector call routed to ar006.sim.detect; every task's acquisition and generation-0 packets
      equal their sources (the workers' records)
  Q4  the vote-default identity through renewal: wherever vtol-every never fired in generations 1..g, its saved state at
      g equals vtol-once's (the same packet and injuries) bit for bit (V, r, H, W)
  Q5  aliases: the alias table is complete (every label has a row; vote/memory@1 is vote/memory@0's row; a row's labels
      share one packet); a row listed twice gives the same lineage bit for bit (two generations, 500 updates)
  Q6  reanalysis: the endpoints recomputed from the saved states, with the union and own patches rebuilt from the saved
      corners, equal the shards'
  Q7  efficacy and the injury: the vote rows never fire, in any generation; at sigma 0 every birth cue equals its
      incoming record's signs at birth; every injury flips exactly its patch of the incoming record, 16 cells, every
      injured branch in every generation, and nothing on the uninjured row (the lineage's own check); the patches are
      disjoint from each other and from generation 0's and recompute from their addresses; the injury rule at generation
      0 equals be001.sim.event's memory rule bit for bit; the second record and the cue are taken before the injury (the
      lineage's order); every task is a saved record of its stage
  Q8  pairing: reordering the rows changes no row's output (two generations, 500 updates)
  Q9  resources: the development forecast structurally: this stage's CPU a task, per vote-equivalent row-generation at 8
      cases (a detector row-generation weighs W_DET, P59s's measured ratio), times the development's own row-generations
      (its core rows to g 8, 8 cases, 128 tasks), within the lead's target of 35 CPU-hours and 12 h of wall on 12
      workers; worker memory within 2 GB
  Q10 the reader's dry run: predict and tables complete, every part scored or marked unavailable, every output and every
      E2E003 git file 256 KiB or less
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
from ar006 import design as A6  # noqa: E402
from ar006 import sim as S6  # noqa: E402
from be001 import sim as B1S  # noqa: E402
from e2e002 import sim as E2  # noqa: E402
from e2e003 import design as D  # noqa: E402
from e2e003 import sim  # noqa: E402
from e2e003 import worker as W  # noqa: E402
from gc001 import sim as GCS  # noqa: E402
from lr001.sim import edges_from  # noqa: E402
from lr005 import sim as L5S  # noqa: E402
from msegrid.core import bonds  # noqa: E402
from sr001 import sim as SRS  # noqa: E402

FROZEN = LANE / "e2e003" / "frozen"
W_DET = 2.0                    # P59s: a vtol or vms row-generation 18.8-24.6 CPU-s against a vote row's 10.9-11.0
REPLAY_SITUATIONS = ("memory@0", "memory@1", "none@0")


def npz(path):
    with np.load(path) as f:
        return {k: f[k] for k in f.files if k != "__meta__"}


def meta_of(path):
    return json.loads(str(np.load(path)["__meta__"]))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def setup(source, body, unit, block, stage):
    """The task's restored inputs as the worker builds them (the pilot's parent subset included)."""
    raw, meta, _rf = W.load(source, body, unit, block)
    pattern, theta = A.parse_unit(unit)
    cases, V0, ema0, R0, th, T = A1S.prepare(pattern, block, D.SOURCES[source]["purpose"])
    parents = D.STAGE_PARENTS.get(stage)
    if parents is not None:
        sel = [j for j, c in enumerate(cases) if c.parent in parents]
        cases = [cases[j] for j in sel]
        V0, ema0, R0, th, T = (x[sel] for x in (V0, ema0, R0, th, T))
        raw = {k: (v[sel] if k in ("V0", "R0", "T") else v[:, sel]) for k, v in raw.items()}
    Tf = SRS.foreign(T, pattern, cases)
    _pk, m0 = sim.post_damage("memory@0", cases, V0, ema0, R0, T, meta["tag"])
    am, normals = L5S.anchor_mask(cases, meta["tag"]), GCS.unit_normals(cases, meta["tag"])
    return dict(raw=raw, meta=meta, cases=cases, V0=V0, ema0=ema0, R0=R0, th=th, theta=theta, T=T, Tf=Tf, m0=m0, am=am,
                normals=normals, thf=th * theta, pattern=pattern)


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--cpus", default=None)
    ap.add_argument("--debug", action="store_true")
    a = ap.parse_args()
    if a.cpus:
        os.sched_setaffinity(0, [int(c) for c in a.cpus.split(",")])
    root, t0 = a.root.resolve(), time.time()
    M = json.loads((root / "manifest.json").read_text())
    stage = M["stage"]
    receipt_path = root / "debug_qualification_receipt.json" if a.debug else FROZEN / "qualification_receipt.json"
    tasks = [tuple(t) for t in M["tasks_planned"]]
    paths = {t: (root / "shards" / W.key(t[0]) / t[1] / t[2] / f"{t[3]}.npz", root / "raw" / W.key(t[0]) / t[1] / t[2] / f"{t[3]}.npz")
             for t in tasks}
    done = {t: json.loads((root / "done" / W.key(t[0]) / t[1] / t[2] / f"{t[3]}.json").read_text()) for t in tasks
            if (root / "done" / W.key(t[0]) / t[1] / t[2] / f"{t[3]}.json").exists()}
    checks = {}

    # Q1
    bad = []
    for t in tasks:
        sp, rp = paths[t]
        if not sp.exists() or not rp.exists():
            bad.append(f"{t}: missing")
            continue
        e, meta = npz(sp), meta_of(sp)
        rows = meta["rows"]
        k = len(meta["cases"])
        gmax = max(r["stop"] for r in rows)
        for key in [x for x in e if x.startswith("g0/")]:
            bad += [] if e[key].shape == (len(rows), k) else [f"{t}: {key} shape"]
        if e["schedule/corners"].shape != (k, gmax, 2) or e["schedule/attempts"].shape != (k, gmax):
            bad.append(f"{t}: schedule shape")
        for g in range(1, gmax + 1):
            alive = [i for i, r in enumerate(rows) if r["stop"] >= g]
            for kind, ends in (("g", tuple(sim.READS) + tuple(sim.UNION_READS)),
                               ("d", tuple(sim.DIAG) + ("cue_dis_birth", "injury_ok"))):
                if list(e[f"f0/{kind}{g}/rows"]) != alive:
                    bad.append(f"{t}: f0/{kind}{g}/rows")
                for x in ends:
                    key = f"f0/{kind}{g}/{x}"
                    bad += [] if key in e and e[key].shape == (len(alive), k) else [f"{t}: {key}"]
        bad += [f"{t}: {x} not finite" for x, v in e.items() if np.issubdtype(v.dtype, np.floating) and not np.isfinite(v).all()]
    checks["Q1_complete_finite"] = {"pass": not bad, "tasks": len(tasks), "bad": bad[:10]}

    # Q2
    t2 = sorted(tasks)[0]
    ends, states, meta2, _b = W.task(*t2, stage)
    e, r = npz(paths[t2][0]), npz(paths[t2][1])
    same_e = set(ends) == set(e) and all(np.array_equal(np.asarray(ends[x]), e[x]) for x in e)
    same_r = set(states) == set(r) and all(np.array_equal(np.asarray(states[x]), r[x]) for x in r)
    checks["Q2_serial_equals_parallel"] = {"pass": bool(same_e and same_r), "task": list(t2)}

    # Q3
    q3 = {}
    shas = []
    for t in tasks:
        src = Path(D.SOURCES[t[0]]["root"])
        Mf = json.loads((src / "manifest.json").read_text())
        f = Mf["tasks"][f"{t[1]}/{t[2]}/{t[3]}"]["files"]["raw"]
        shas.append(sha(src / f["path"]) == f["sha256"])
    q3["every_raw_file_equals_its_manifests_sha256"] = all(shas) and len(shas) == len(tasks)
    tr = sorted(tasks)[0]
    S0 = setup(*tr, "debug")                     # the replay runs on all eight cases of the raw file
    arms_of = {nm: list(x) for nm, x in S0["meta"]["runs"]}
    k = len(S0["cases"])
    rep_ok = True
    for sit in REPLAY_SITUATIONS:
        arms = arms_of[sit]
        V, E, A_, B_, dg = sim.replay0(tr[1], sit, arms, S0["cases"], S0["V0"], S0["ema0"], S0["R0"], S0["th"], S0["T"],
                                       S0["theta"], S0["meta"]["tag"], size=S0["meta"]["sizes"][sit], configs=A6.VD_DETECTORS)
        raw = S0["raw"]
        vd = [x for x in arms if x != "vote"]
        arrays = {"V": V, "r": A_[4], "H": A_[0], "W": A_[1], "rB": B_[4], "HB": B_[0], "WB": B_[1], "zone": dg["zone_map"],
                  "fp": dg["fp_map"]}
        for j, arm in enumerate(arms):
            sl = slice(j * k, (j + 1) * k)
            for x, mine in arrays.items():
                key = f"{sit}/{x}"
                if key not in raw:
                    continue
                if x in ("zone", "fp"):
                    ok = (not mine[sl].any()) if arm == "vote" else np.array_equal(mine[sl], raw[key][vd.index(arm)])
                elif x in ("rB", "HB", "WB"):
                    ok = np.array_equal(mine[sl], raw[key][((["vote"] if "vote" in arms else []) + vd).index(arm)])
                else:
                    ok = np.array_equal(mine[sl], raw[key][j])
                rep_ok &= bool(ok)
    q3["the_generation0_replay_reproduces_every_arms_saved_state"] = bool(rep_ok)
    lins = (dict(label="vms-every/memory@0", packet="vms/memory@0", policy="vms", sigma=0.0, stop=2, injured=False),
            dict(label="vote/memory@0", packet="vote/memory@0", policy="vote", sigma=0.0, stop=2, injured=False),
            dict(label="vms-every/memory@1", packet="vms/memory@1", policy="vms", sigma=1.0, stop=2, injured=False))
    rows_b, *_ = sim.packets(S0["raw"], S0["meta"], S0["cases"], S0["V0"], S0["ema0"], S0["R0"], S0["T"], lins)
    exact0 = np.where(S0["R0"] > 0, 1.0, -1.0)
    cue0 = {s: (GCS.read_at(exact0, S0["normals"], s) if s else exact0) for s in (0.0, 1.0)}
    r2, a2, d2, k2 = E2.lineage(tr[1], [dict(x, cue="birth") for x in rows_b], S0["cases"], S0["thf"], S0["T"], S0["Tf"],
                                S0["m0"], S0["am"], S0["normals"], cue0, D.TAG, E2.GEN_NAMES(0), E2.BIRTH_NAMES(0),
                                t_gen=2000, horizons=(1, 2), keep=(1, 2))
    r3, a3, d3, k3 = sim.lineage(tr[1], rows_b, S0["cases"], S0["thf"], S0["T"], S0["Tf"], S0["m0"], S0["am"], S0["normals"],
                                 D.TAG, sim.GEN_NAMES(0), sim.BIRTH_NAMES(0), sched=None, t_gen=2000, keep=(1, 2))
    q3["without_injury_the_lineage_is_e2e002s"] = bool(all(
        all(np.array_equal(r2[g][x], r3[g][x]) for x in r2[g]) and all(np.array_equal(d2[g][x], d3[g][x]) for x in d2[g])
        and all(np.array_equal(k2[g][x], k3[g][x]) for x in ("V", "r", "H", "W")) for g in (1, 2)))
    q3["the_routed_generation_is_e2e002s_with_one_call_routed"] = bool(
        inspect.getsource(E2.generation).count(sim.DETECT_CALL) == 1 and sim.generation.__globals__["detect_vt"] is S6.detect
        and sim.replay0.__globals__["generation"] is sim.generation)
    q3["every_tasks_acquisition_and_generation0_packets_equal_their_sources"] = bool(
        len(done) == len(tasks) and all(rec["bridge_all_equal"] for rec in done.values()))
    checks["Q3_bridges"] = {"pass": all(q3.values()), "items": q3, "replay_task": list(tr)}

    # Q4
    q4 = {"pairs": 0, "cases_compared": 0, "bad": []}
    for t in tasks:
        e, rr, meta = npz(paths[t][0]), npz(paths[t][1]), meta_of(paths[t][0])
        lab = meta["labels"]
        for ev, on in (("vtol-every/memory@0", "vtol-once/memory@0"), ("vtol-every/memory@1", "vtol-once/memory@1")):
            if ev not in lab or on not in lab:
                continue
            ie, io = lab[ev], lab[on]
            for g in D.HORIZONS:
                if f"f0/g{g}/rows" not in rr:
                    continue
                kr = list(rr[f"f0/g{g}/rows"])
                if ie not in kr or io not in kr:
                    continue
                q4["pairs"] += 1
                never = np.ones(len(meta["cases"]), bool)
                for h in range(1, g + 1):
                    dr = list(e[f"f0/d{h}/rows"])
                    never &= ~e[f"f0/d{h}/fired"][dr.index(ie)].astype(bool)
                for c in np.flatnonzero(never):
                    q4["cases_compared"] += 1
                    if not all(np.array_equal(rr[f"f0/g{g}/{x}"][kr.index(ie) * len(meta["cases"]) + c],
                                              rr[f"f0/g{g}/{x}"][kr.index(io) * len(meta["cases"]) + c]) for x in ("V", "r", "H", "W")):
                        q4["bad"].append(f"{t} {ev} g{g} case {c}")
    checks["Q4_vote_default_identity"] = {"pass": not q4["bad"], **q4, "bad": q4["bad"][:10]}

    # Q5
    q5 = {}
    ok_tab = True
    for t in tasks:
        meta = meta_of(paths[t][0])
        lab, rows = meta["labels"], meta["rows"]
        want = [x["label"] for x in D.lineages(stage)]
        ok_tab &= set(want) <= set(lab) and lab["vote/memory@1"] == lab["vote/memory@0"]
        ok_tab &= all(sorted(rows[i]["labels"]) == sorted(x for x, j in lab.items() if j == i) for i in range(len(rows)))
    q5["the_alias_table_is_complete"] = bool(ok_tab)
    rows_s, *_ = sim.packets(S0["raw"], S0["meta"], S0["cases"], S0["V0"], S0["ema0"], S0["R0"], S0["T"],
                             (dict(D.CORE[0], stop=2),))
    sched_s, _c, _a = sim.schedule(S0["cases"], S0["m0"], D.TAG, 2)
    twice = [rows_s[0], dict(rows_s[0])]
    r5, a5, d5, k5 = sim.lineage(tr[1], twice, S0["cases"], S0["thf"], S0["T"], S0["Tf"], S0["m0"], S0["am"], S0["normals"],
                                 D.TAG, sim.GEN_NAMES(0), sim.BIRTH_NAMES(0), sched=sched_s, t_gen=500, keep=(1, 2))
    q5["a_row_listed_twice_gives_the_same_lineage"] = bool(all(
        all(np.array_equal(v[0], v[1]) for v in r5[g].values()) and all(np.array_equal(v[0], v[1]) for v in d5[g].values())
        and all(np.array_equal(k5[g][x][:k], k5[g][x][k:]) for x in ("V", "r", "H", "W")) for g in (1, 2)))
    checks["Q5_aliases"] = {"pass": all(q5.values()), "items": q5}

    # Q6
    bad6 = []
    for t in tasks:
        e, rr, meta = npz(paths[t][0]), npz(paths[t][1]), meta_of(paths[t][0])
        S = setup(*t, stage)
        sched = masks_from(e["schedule/corners"])
        k = len(S["cases"])
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
    checks["Q6_reanalysis"] = {"pass": not bad6, "bad": bad6[:10]}

    # Q7
    q7 = {}
    vote_fired, cue_bad, inj_bad, sched_bad, own = 0, 0, 0, [], []
    for t in tasks:
        e, meta = npz(paths[t][0]), meta_of(paths[t][0])
        rows = meta["rows"]
        gmax = max(r["stop"] for r in rows)
        for g in range(1, gmax + 1):
            dr = list(e[f"f0/d{g}/rows"])
            for j, i in enumerate(dr):
                if rows[i]["policy"] == "vote":
                    vote_fired += int(e[f"f0/d{g}/fired"][j].astype(bool).sum())
                if rows[i]["sigma"] == 0.0:
                    cue_bad += int((e[f"f0/d{g}/cue_dis_birth"][j] != 0).sum())
                inj_bad += int((~e[f"f0/d{g}/injury_ok"][j].astype(bool)).sum())
        S = setup(*t, stage)
        sched = masks_from(e["schedule/corners"])
        stack = np.stack([S["m0"]] + [sched[g] for g in range(1, gmax + 1)])
        if not (stack.sum((-2, -1)) == D.SIZE * D.SIZE).all() or stack.sum(0).max() > 1:
            sched_bad.append(f"{t}: not disjoint")
        _s, corners, attempts = sim.schedule(S["cases"], S["m0"], D.STAGE_TAG[stage], gmax)
        if not (np.array_equal(corners, e["schedule/corners"]) and np.array_equal(attempts, e["schedule/attempts"])):
            sched_bad.append(f"{t}: does not recompute from its addresses")
        own.append(t[0] in D.STAGES[stage] and t[3] in D.STAGES[stage][t[0]])
    q7["the_vote_rows_never_fire"] = vote_fired == 0
    q7["every_sigma0_birth_cue_equals_its_incoming_records_signs"] = cue_bad == 0
    q7["every_injury_flips_exactly_its_patch_and_none_on_the_uninjured_row"] = inj_bad == 0
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
    checks["Q7_efficacy_and_the_injury"] = {"pass": all(q7.values()), "items": q7, "vote_fired": vote_fired,
                                           "cue_disagreements": cue_bad, "injury_failures": inj_bad, "schedule": sched_bad[:5]}

    # Q8
    rows_p, *_ = sim.packets(S0["raw"], S0["meta"], S0["cases"], S0["V0"], S0["ema0"], S0["R0"], S0["T"],
                             tuple(dict(x, stop=2) for x in D.CORE[:4]))
    outs = []
    for order in (list(range(len(rows_p))), list(reversed(range(len(rows_p))))):
        rp = [rows_p[i] for i in order]
        rd, al, dg, kp = sim.lineage(tr[1], rp, S0["cases"], S0["thf"], S0["T"], S0["Tf"], S0["m0"], S0["am"], S0["normals"],
                                     D.TAG, sim.GEN_NAMES(0), sim.BIRTH_NAMES(0), sched=sched_s, t_gen=500, keep=(2,))
        outs.append((order, rd, dg, kp))
    (o1, rd1, dg1, kp1), (o2, rd2, dg2, kp2) = outs
    ok8 = True
    k = len(S0["cases"])
    for i in range(len(rows_p)):
        j1, j2 = o1.index(i), o2.index(i)
        for g in (1, 2):
            ok8 &= all(np.array_equal(rd1[g][x][j1], rd2[g][x][j2]) for x in rd1[g])
            ok8 &= all(np.array_equal(dg1[g][x][j1], dg2[g][x][j2]) for x in dg1[g])
        ok8 &= all(np.array_equal(kp1[2][x][j1 * k:(j1 + 1) * k], kp2[2][x][j2 * k:(j2 + 1) * k]) for x in ("V", "r", "H", "W"))
    checks["Q8_pairing"] = {"pass": bool(ok8), "rows": len(rows_p)}

    # Q9
    units = lambda rows, gens, k: sum((W_DET if r["policy"] != "vote" else 1.0) * min(r["stop"], gens) for r in rows) * k / 8
    per_unit = []
    for t in tasks:
        meta = meta_of(paths[t][0])
        rec = done.get(t)
        if rec:
            per_unit.append(rec["cpu_s"] / units(meta["rows"], 99, len(meta["cases"])))
    dev_rows = [dict(r, stop=D.G_MAIN) for r in meta_of(paths[tr][0])["rows"] if set(r["labels"]) & {x["label"] for x in D.CORE}]
    dev_units = units(dev_rows, D.G_MAIN, 8)
    n_dev = len(D.stage_tasks("development"))
    cpu_h = float(np.mean(per_unit)) * dev_units * n_dev / 3600
    wall_h = cpu_h / 12 * 1.15 + max(rec["wall_s"] for rec in done.values()) / 3600 * dev_units / max(
        units(meta_of(paths[t][0])["rows"], 99, len(meta_of(paths[t][0])["cases"])) for t in tasks)
    rss = max(rec["maxrss_mb"] for rec in done.values())
    checks["Q9_resources"] = {"pass": bool(cpu_h <= 35 and wall_h <= 12 and rss <= 2048), "forecast_cpu_h": round(cpu_h, 2),
                              "forecast_wall_h_12": round(float(wall_h), 2), "cpu_s_per_vote_row_generation_8_cases":
                              round(float(np.mean(per_unit)), 2), "development_units_a_task": dev_units,
                              "worker_rss_mb": rss, "w_det": W_DET}

    # Q10
    out = root / "analysis_dry_run"
    out.mkdir(exist_ok=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    procs = [subprocess.run([sys.executable, "-m", f"e2e003.{mod}"] + args_, cwd=LANE, capture_output=True, text=True, env=env)
             for mod, args_ in (("predict", ["--root", str(root), "--out", str(out)]),
                                ("tables", ["--scored", str(out / "predictions_scored.json"), "--out", str(out / "TABLES.md")]))]
    got = json.loads((out / "predictions_scored.json").read_text()) if (out / "predictions_scored.json").exists() else {}
    from e2e003 import predict as PR
    ids = sorted(p for p, _w, _f, _k in PR.parts())
    scored = sorted(p["id"] for p in got.get("parts", []))
    sizes = {q.name: q.stat().st_size for q in out.iterdir() if q.is_file()}
    git_files = [f for f in list((LANE / "e2e003").rglob("*")) + list((LANE / "probes").rglob("*p59*"))
                 + [LANE / "tests" / "test_e2e003.py", LANE / "PLAN_E2E003.md", LANE / "REGISTRATION_E2E003.md"] if f.is_file()]
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
               "checks": checks}
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=1, default=str) + "\n")
    print(json.dumps({"status": receipt["status"], "failed": failed}, indent=1))


if __name__ == "__main__":
    main()
