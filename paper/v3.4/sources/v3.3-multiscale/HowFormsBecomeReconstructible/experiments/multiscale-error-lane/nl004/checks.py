"""NL004's qualification checks, fixed before their results: python -m nl004.checks --root RUN_ROOT --stage
{preflight,debug} [--receipt PATH]. Run on the preflight blocks (900133-900134) at the full shape; on the debug blocks
(900135-900136) in phase A.

Q1  complete and finite at the declared shapes: every endpoint finite except k_spec_reg, anc_A_kd and anc_B_kd, where
    NaN falls exactly on the cases whose killed square holds no region in which A and B differ (NL002's Amendment 1,
    from nl002.sim.masks on the case's templates and kill square), and nowhere else.
Q2  serial equals parallel: one task (the store-only unit, the first block) rerun in this process equals its saved
    shards and raw states bit for bit.
Q3  the bridges, bit for bit, on the first block: (a) with the arbiter off, every branch under none, R and K (the
    saved shard's float64 endpoints and dose, the saved final states against nl002's cast to their saved types)
    equals nl002.sim.run's, and the record-only and coded recipients of those labels equal nl002.sim.successor's;
    (b) with the given anchors (A) under none, R and K, every branch equals nl003.sim.run's (its arbiter endpoints and
    anchors too), and the recipient gated by the parent's anchors equals nl003.sim.successor's; (c) the record's
    commitment at the branch (sign(r) at the sites, K's square removed) equals the given anchors in every case and
    event, and so do Me's anchors under none and K; a slow copy at eta = 0 equals A bit for bit (300 updates); the
    frozen sources of nl002 and nl003 unchanged.
Q4  the replay: four gated branches (foreign+S1e-2/none, copy+S1e-2/R, copy+Mt250/R, copy+Me/change; dw; one case
    each) rerun alone for 300 updates with the gate, the slow copy's learning and the late commitment computed by
    explicit per-cell loops (an independent implementation of the declared rules) equal the batched run's states at
    update 300 within 1e-12, the gate's refusals exactly.
Q5  aliases: (a) a gated branch whose gate never refused equals its ungated twin bit for bit in every tissue
    endpoint; (b) a gated recipient (parent's or successor-made anchors) that never refused equals the coded recipient;
    (c) off's coded recipient equals its record-only one; (d) the information-limit pair: in every change branch, spec
    scored against B (from the final record) is exactly minus the stored spec; (e) a late commitment's branch equals its
    ungated twin at every read up to and including t_c.
Q6  reanalysis: the last read's endpoints recomputed from the saved final records equal the shards'; the saved
    anchors of the codes made at or before the branch (A, Mv, Me, Mpre, Mmid, Mmidc) equal the ones regenerated from
    their rules; the slow copies' saved anchors equal sign(a); the anchors' endpoints recomputed from the saved
    anchors equal the shards'.
Q7  efficacy on synthetic states: the gate (n 1, q 0.75); every commitment rule (the record at the branch, the body,
    after the event, early in the acquisition with and without the confidence rule, late); the slow copy's update,
    its flip time and eta = 0; the change event's start state; the anchors' shares; k2 x G = k2 where G = 1.
Q8  pairing: a label listed twice gives identical branches, and a gated label run alone equals its run in the full
    batch (300 updates, both units; a slow copy and a late commitment).
Q9  resources: the development forecast from this run's CPU per task, within 30 CPU-hours and 12 h of wall on 12
    workers; worker memory within 2 GB; disk headroom.
Q10 the reader dry run (analyze, tables), every part computed, every output file at 256 KB or less.
"""
from __future__ import annotations

import os

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"

import argparse  # noqa: E402
from dataclasses import replace  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
from pathlib import Path  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import tempfile  # noqa: E402
import time  # noqa: E402

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import numpy as np  # noqa: E402

from mse.native import NATIVE  # noqa: E402
from msegrid.core import acquire, bonds  # noqa: E402
from lr001.sim import edges_from  # noqa: E402
from nl001 import sim as N1S  # noqa: E402
from nl002 import design as D2  # noqa: E402
from nl002 import sim as S2  # noqa: E402
from nl003 import design as D3  # noqa: E402
from nl003 import sim as S3  # noqa: E402
from nl004 import design as D  # noqa: E402
from nl004 import sim  # noqa: E402
from nl004 import worker  # noqa: E402

K = f"k{D.KSTAR:g}"
NAN_KEYS = ("k_spec_reg", "anc_A_kd", "anc_B_kd")


def shard(root, unit, block):
    with np.load(root / "shards" / unit / f"{block}.npz") as z:
        return {k: z[k] for k in z.files}


def rawfile(root, unit, block):
    with np.load(root / "raw" / unit / f"{block}.npz") as z:
        return {k: z[k] for k in z.files}


def names_of(s):
    m = json.loads(str(s["__meta__"]))
    return [f"{a}/{e}" for a, e in m["labels"]], m


def q1(root, blocks, stage):
    bad, undefined = [], []
    for u in D.UNITS:
        for b in blocks:
            s = shard(root, u, b)
            cases = sim.cases_for(b, D.PURPOSE[stage])
            P = S2.prepare(cases, D.STAGE_TAG[stage])
            kd_empty = S2.masks(P["TA"], P["TB"], N1S.event_units(cases, D.STAGE_TAG[stage]))["kdreg"].sum((-2, -1)) == 0
            for key, v in s.items():
                if key == "__meta__" or not np.issubdtype(v.dtype, np.floating):
                    continue
                nan = np.isnan(v)
                if np.isinf(v).any():
                    bad.append((u, b, key, "inf"))
                if nan.any() or key.endswith(NAN_KEYS):
                    if not key.endswith(NAN_KEYS):
                        bad.append((u, b, key, "NaN outside the declared keys"))
                        continue
                    if not np.array_equal(nan, np.broadcast_to(kd_empty, v.shape)):
                        bad.append((u, b, key, "NaN not exactly on the undefined cases"))
            undefined += [(u, b, int(j)) for j in np.flatnonzero(kd_empty)]
            for key in ("t/r/spec_reg", "t/a/ref_all", "t/a/anc_A", "s/spec_reg", "c/spec_reg", "g/spec_reg", "m/spec_reg"):
                if key not in s:
                    bad.append((u, b, key, "missing"))
    return {"pass": not bad, "bad": bad[:20], "undefined_cases": sorted(set(undefined))}


def q2(root, blocks, stage):
    u, b = "none", blocks[0]
    with tempfile.TemporaryDirectory(dir=root) as td:
        worker.run_task(u, b, stage, td)
        new_s, new_r = shard(Path(td), u, b), rawfile(Path(td), u, b)
    old_s, old_r = shard(root, u, b), rawfile(root, u, b)
    differ = [k for k in old_s if k != "__meta__" and not np.array_equal(old_s[k], new_s[k], equal_nan=True)]
    differ += [k for k in old_r if k != "__meta__" and not np.array_equal(old_r[k], new_r[k])]
    return {"pass": not differ, "task": [u, b], "differ": differ}


def static_identities(cases, P, tag):
    """Q3c's anchor identities on a preparation: the record's commitment at the branch, and Me's under none and K."""
    units = N1S.event_units(cases, tag)
    H0, W0 = edges_from(bonds(P["R0"], True))
    dcell = sim.rep(S2.masks(P["TA"], P["TB"], units)["dreg"])
    out = {"R0_has_no_zero": bool((P["R0"] != 0).all())}
    for event in ("none", "R", "K"):
        same_branch, same_me = True, True
        for j in range(len(cases)):
            r, *_ = sim.start_state(event, j, cases[j], P, units, H0, W0, False, dcell, tag)
            amA, avA = sim.branch_anchors("A", event, j, P, units, r)
            # the record's commitment at the branch, before the event: sign(R0_A) at the sites, K's square removed
            amR, avR = sim.commit(P["R0"][j], P["sites"][j])
            if event == "K":
                amR = amR & ~N1S.kill_mask(units[j], P["TA"][j])
                avR = np.where(amR, avR, 0.0)
            same_branch &= bool(np.array_equal(amA, amR) and np.array_equal(avA, avR))
            if event in ("none", "K"):
                amE, avE = sim.branch_anchors("Me", event, j, P, units, r)
                same_me &= bool(np.array_equal(amA, amE) and np.array_equal(avA, avE))
        out[f"branch_commitment_equals_given_{event}"] = same_branch
        if event in ("none", "K"):
            out[f"Me_equals_given_{event}"] = same_me
    return out


def q3(root, blocks, stage, units=D.UNITS):
    """The bridges on the first block (see the module's docstring)."""
    tag, b = D.STAGE_TAG[stage], blocks[0]
    cases = sim.cases_for(b, D.PURPOSE[stage])
    P = sim.prepare(cases, tag)
    k = len(cases)
    out = {}
    arms, labels = D.arms_labels(stage)
    S3.use_stage("main")
    for unit in units:
        s_, r_ = shard(root, unit, b), rawfile(root, unit, b)
        names, m = names_of(s_)
        assert [tuple(x) for x in m["labels"]] == list(labels)
        rlabels = [tuple(x) for x in m["rlabels"]]
        # (a) the arbiter off against nl002
        off = [l for l in labels if not arms[l[0]].arb and l[1] != "change"]
        li = [labels.index(l) for l in off]
        o2, d2, f2, _ = S2.run(cases, unit, labels=off, prep=P, tag=tag)
        a_t = all(np.array_equal(s_[f"t/{w}/{e}"][:, li], o2[(w, e)], equal_nan=True) for (w, e) in o2)
        a_t &= bool(np.array_equal(s_["dose"][li], d2))
        a_f = all(np.array_equal(r_[x][li], f2[x].astype(r_[x].dtype)) for x in f2)
        roff = [l for l in rlabels if not arms[l[0]].arb]
        lo = [rlabels.index(l) for l in roff]
        rec2, cod2 = S2.successor(cases, {x: f2[x][[off.index(l) for l in roff]] for x in f2}, P, labels=roff, tag=tag)
        nr = len(rlabels)
        a_s = all(np.array_equal(s_[f"s/{e}"][:, lo + [nr, nr + 1, nr + 2]], rec2[e], equal_nan=True) for e in rec2)
        a_c = all(np.array_equal(s_[f"c/{e}"][:, lo], cod2[e], equal_nan=True) for e in cod2)
        # (b) the given anchors against nl003
        gA = [l for l in labels if arms[l[0]].arb == "A" and l[1] != "change"]
        gi = [labels.index(l) for l in gA]
        o3, d3, f3, _, a3 = S3.run(cases, unit, gA, prep=P, tag=tag)
        b_t = all(np.array_equal(s_[f"t/{w}/{e}"][:, gi], o3[(w, e)], equal_nan=True) for (w, e) in o3)
        b_t &= bool(np.array_equal(s_["dose"][gi], d3))
        b_f = all(np.array_equal(r_[x][gi], f3[x].astype(r_[x].dtype)) for x in f3)
        gl = [i for i, (a_, _) in enumerate(labels) if arms[a_].arb]
        gpos = [gl.index(i) for i in gi]
        b_a = bool(np.array_equal(r_["am"][gpos], a3["am"].reshape(len(gi), k, D.SIDE, D.SIDE).astype(np.int8))
                   and np.array_equal(r_["aval"][gpos], a3["aval"].reshape(len(gi), k, D.SIDE, D.SIDE).astype(np.int8)))
        sub = [l for l in rlabels if arms[l[0]].arb in ("", "A")]
        fsub = {x: np.concatenate([f2[x][[off.index(l)]] if not arms[l[0]].arb else f3[x][[gA.index(l)]] for l in sub])
                for x in f3}
        arow = lambda l: np.arange(gA.index(l) * k, (gA.index(l) + 1) * k)
        asub = {x: np.concatenate([np.zeros((k, D.SIDE, D.SIDE), a3[x].dtype) if not arms[l[0]].arb else a3[x][arow(l)]
                                   for l in sub]) for x in ("am", "aval")}
        rec3, cod3, g3, gl3 = S3.successor(cases, fsub, P, sub, asub, tag=tag)
        pg = m["parent_gated"]
        b_g = all(np.array_equal(s_[f"g/{e}"][:, [pg.index(f"{sub[i][0]}/{sub[i][1]}") for i in gl3]], g3[e], equal_nan=True)
                  for e in g3)
        # (c) the static identities, and a slow copy at eta = 0
        c_st = static_identities(cases, P, tag)
        lab_s, lab_a = (f"foreign-{K}+S1e-2", "none"), (f"foreign-{K}+A", "none")
        eta0 = dict(D.ETA)
        try:
            D.ETA["S1e-2"] = 0.0
            o0, _, f0, _, _ = sim.run(cases, unit, [lab_s, lab_a], prep=P, tag=tag, window=300, reads=(300,))
        finally:
            D.ETA.clear()
            D.ETA.update(eta0)
        c_eta0 = bool(np.array_equal(f0["r"][0], f0["r"][1]) and all(np.array_equal(v[:, 0], v[:, 1], equal_nan=True)
                                                                     for v in o0.values()))
        out[unit] = {"a_tissue_and_dose": bool(a_t), "a_final_states": bool(a_f), "a_record_only": bool(a_s),
                     "a_coded": bool(a_c), "b_tissue_arbiter_and_dose": bool(b_t), "b_final_states": bool(b_f),
                     "b_anchors": b_a, "b_parent_gated": bool(b_g), "c_eta0_equals_A": c_eta0, **c_st,
                     "labels_off": len(off), "labels_A": len(gA)}
    unchanged = {}
    for name, mod in (("nl002", D2), ("nl003", D3)):
        frozen = json.loads((LANE / name / "frozen" / "design.json").read_text())["sources"]
        now = mod.sources(LANE)
        unchanged[name] = all(now.get(k_) == v for k_, v in frozen.items())
    ok = all(all(v for k_, v in x.items() if not k_.startswith("labels_")) for x in out.values()) and all(unchanged.values())
    return {"pass": ok, "units": out, "frozen_sources_unchanged": unchanged, "block": b}


def gate_loops(r, sig, Bg, am, aval, n_, q_):
    """The declared rule (no surround) by explicit loops, one sheet: refused (NR, NR) bool."""
    side, NR = D.SIDE, D.SIDE // D.REGION
    vs = lambda x: 1.0 if x >= D.VMIN else (-1.0 if x <= -D.VMIN else 0.0)
    ref = np.zeros((NR, NR), bool)
    for ri in range(NR):
        for rj in range(NR):
            nd = nl = 0
            for i in range(ri * D.REGION, (ri + 1) * D.REGION):
                for j in range(rj * D.REGION, (rj + 1) * D.REGION):
                    t = float(np.sign(sig[i, j] * Bg[i, j]))
                    if am[i, j] and vs(r[i, j]) != 0 and t != 0:
                        nl += 1
                        nd += int(aval[i, j] != t)
            ref[ri, rj] = nd >= n_ and nd >= q_ * nl
    return ref


def learn_loops(a, r, site, eta):
    out = np.zeros_like(a)
    for m in range(a.shape[0]):
        e = float(eta[m].ravel()[0])
        for i in range(D.SIDE):
            for j in range(D.SIDE):
                if site[m, i, j]:
                    s = 1.0 if r[m, i, j] > 0 else (-1.0 if r[m, i, j] < 0 else 0.0)
                    out[m, i, j] = a[m, i, j] + e * (s - a[m, i, j])
    return out


def commit_loops(r, site):
    am = np.zeros(r.shape, bool)
    av = np.zeros(r.shape)
    for idx in np.ndindex(*r.shape):
        if site[idx] and r[idx] != 0:
            am[idx] = True
            av[idx] = 1.0 if r[idx] > 0 else -1.0
    return am, av


def q4(blocks, stage):
    tag, b = D.STAGE_TAG[stage], blocks[0]
    cases = sim.cases_for(b, D.PURPOSE[stage])[:1]
    P = sim.prepare(cases, tag)
    arms, labels = D.arms_labels(stage)
    picks = [(f"foreign-{K}+S1e-2", "none"), (f"copy-{K}+S1e-2", "R"), (f"copy-{K}+Mt250", "R"), (f"copy-{K}+Me", "change")]
    window = 300
    _, _, f_full, _, a_full = sim.run(cases, "dw", picks, prep=P, tag=tag, window=window, reads=(window,))
    real = (S3.gate, sim.learn, sim.commit)
    nref = [0, 0]

    def loop_gate(r, sig, Bg, am, aval, n, q, ring, ring_max):
        res = np.stack([gate_loops(r[m], sig[m], Bg[m], am[m], aval[m], float(n[m]), float(q[m])) for m in range(r.shape[0])])
        fast = real[0](r, sig, Bg, am, aval, n, q, ring, ring_max)
        nref[0] += int(res.sum())
        nref[1] += int((res != fast).sum())
        return res
    out = []
    S3.gate, sim.learn, sim.commit = loop_gate, learn_loops, commit_loops
    try:
        for bi, lab in enumerate(picks):
            _, _, f1, _, a1 = sim.run(cases, "dw", [lab], prep=P, tag=tag, window=window, reads=(window,))
            out.append({"label": "/".join(lab), "max_dr": float(np.abs(f1["r"][0] - f_full["r"][bi]).max()),
                        "max_dV": float(np.abs(f1["V"][0] - f_full["V"][bi]).max()),
                        "anchors_equal": bool(np.array_equal(a1["am"][0], a_full["am"][bi])
                                              and np.array_equal(a1["aval"][0], a_full["aval"][bi]))})
    finally:
        S3.gate, sim.learn, sim.commit = real
    return {"pass": all(x["max_dr"] <= 1e-12 and x["max_dV"] <= 1e-12 and x["anchors_equal"] for x in out) and nref[1] == 0,
            "branches": out, "loop_refusals": nref[0], "loop_vs_vectorised_differences": nref[1], "window": window}


def q5(root, blocks, stage):
    bad, n_alias, n_late = [], 0, 0
    for u in D.UNITS:
        for b in blocks:
            s = shard(root, u, b)
            names, m = names_of(s)
            pg, rnames = m["parent_gated"], [f"{a}/{e}" for a, e in m["rlabels"]]
            ever = s["t/a/ever"][-1]                                  # (branches, cases)
            tkeys = [x for x in s if x.startswith("t/r/") or x.startswith("t/v/")]
            for gi, br in enumerate(names):
                if "+" not in br:
                    continue
                twin = br.split("+")[0] + "/" + br.split("/")[-1]
                ti = names.index(twin)
                for j in np.flatnonzero(ever[gi] == 0):
                    n_alias += 1
                    for key in tkeys:
                        if not np.array_equal(s[key][:, gi, j], s[key][:, ti, j], equal_nan=True):
                            bad.append((u, b, br, int(j), key))
                arb = br.split("+")[1].split("/")[0]
                if arb in D.T_C:
                    upto = [i for i, t in enumerate(D.READS) if t <= D.T_C[arb]]
                    n_late += 1
                    for key in tkeys:
                        if not np.array_equal(s[key][upto, gi], s[key][upto, ti], equal_nan=True):
                            bad.append((u, b, br, key, "late commitment before t_c"))
            for fam, labs in (("g/", pg), ("m/", rnames)):
                gever = s[fam + "ever"][-1]
                for k_, br in enumerate(labs):
                    ci = rnames.index(br)
                    for j in np.flatnonzero(gever[k_] == 0):
                        for key in [x for x in s if x.startswith(fam) and x[2:] in S2.ENDS]:
                            if not np.array_equal(s[key][:, k_, j], s["c/" + key[2:]][:, ci, j], equal_nan=True):
                                bad.append((u, b, br, int(j), key, "gated vs coded"))
            oi = rnames.index("off/none")
            for key in [x for x in s if x.startswith("c/")]:
                if not np.array_equal(s[key][:, oi], s["s/" + key[2:]][:, oi], equal_nan=True):
                    bad.append((u, b, "off", key, "coded vs record-only"))
            r = rawfile(root, u, b)
            cases = sim.cases_for(b, D.PURPOSE[stage])
            mk = S2.masks(r["TA"].astype(float), r["TB"].astype(float), N1S.event_units(cases, D.STAGE_TAG[stage]))
            for br in [x for x in names if x.endswith("/change")]:
                bi = names.index(br)
                reg = N1S.unit_sign(r["r"][bi].astype(float), D.REGION)
                specB = N1S.frac(mk["dreg"], reg == mk["regB"], (-2, -1)) - N1S.frac(mk["dreg"], reg == mk["regA"], (-2, -1))
                if not np.array_equal(specB, -s["t/r/spec_reg"][-1, bi]):
                    bad.append((u, b, br, "the pair's identity"))
    return {"pass": not bad, "bad": bad[:20], "never_refused_case_aliases": n_alias, "late_branches_checked": n_late}


def q6(root, blocks, stage):
    bad = []
    tag = D.STAGE_TAG[stage]
    arms, labels = D.arms_labels(stage)
    for u in D.UNITS:
        for b in blocks:
            s, r = shard(root, u, b), rawfile(root, u, b)
            names, m = names_of(s)
            cases = sim.cases_for(b, D.PURPOSE[stage])
            units = N1S.event_units(cases, tag)
            mk1 = S2.masks(r["TA"].astype(float), r["TB"].astype(float), units)
            mk = {k_: np.concatenate([v] * len(names)) for k_, v in mk1.items()}
            rr = r["r"].astype(np.float64).reshape(-1, D.SIDE, D.SIDE)
            if not (np.sign(rr) == np.sign(r["r"].reshape(-1, D.SIDE, D.SIDE))).all():
                bad.append((u, b, "float32 sign"))
            for e, v in S2.score(rr, mk).items():
                if not np.array_equal(v.reshape(-1), s[f"t/r/{e}"][-1].reshape(-1), equal_nan=True):
                    bad.append((u, b, e))
            P = sim.prepare(cases, tag)
            H0, W0 = edges_from(bonds(P["R0"], True))
            dcell = sim.rep(mk1["dreg"])
            gl = [i for i, (a_, _) in enumerate(labels) if arms[a_].arb]
            k = len(cases)
            for k_, i in enumerate(gl):
                a_, ev = labels[i]
                code = arms[a_].arb
                if D.kind(code) in ("late", "slow"):
                    if D.kind(code) == "slow":
                        rows = worker.sim_slow_rows(labels, k)
                        pos = [list(rows).index(i * k + j) for j in range(k)]
                        a_s = r["a_slow"][pos].astype(np.float64)
                        if not (np.array_equal(r["am"][k_], (a_s != 0).astype(np.int8))
                                and np.array_equal(r["aval"][k_], np.sign(a_s).astype(np.int8))):
                            bad.append((u, b, f"{a_}/{ev}", "slow anchors vs a"))
                    continue
                for j in range(k):
                    r0, *_ = sim.start_state(ev, j, cases[j], P, units, H0, W0, False, dcell, tag)
                    am, av = sim.branch_anchors(code, ev, j, P, units, r0)
                    if not (np.array_equal(am.astype(np.int8), r["am"][k_, j]) and np.array_equal(av.astype(np.int8), r["aval"][k_, j])):
                        bad.append((u, b, f"{a_}/{ev}", int(j), "anchors"))
                        break
            AM = np.zeros((len(names) * k, D.SIDE, D.SIDE), bool)
            AV = np.zeros((len(names) * k, D.SIDE, D.SIDE))
            for k_, i in enumerate(gl):
                AM[i * k:(i + 1) * k] = r["am"][k_].astype(bool)
                AV[i * k:(i + 1) * k] = r["aval"][k_].astype(float)
            sites = np.concatenate([r["sites"].astype(bool)] * len(names))
            mk["evcell"], mk["dcellreg"] = sim.rep(mk["ev"]), sim.rep(mk["dreg"])
            for e, v in sim.anchor_shares(AM, AV, sites, mk).items():
                if not np.array_equal(v.reshape(-1), s[f"t/a/{e}"][-1].reshape(-1), equal_nan=True):
                    bad.append((u, b, e, "anchor shares"))
    return {"pass": not bad, "bad": bad[:20]}


def q7():
    items = {}
    n_ = D.SIDE
    rule = lambda m: tuple(np.full(m, D.RULE[x], float) for x in ("n", "q", "ring", "ring_max"))
    r = np.full((1, n_, n_), 1.0)
    sig = np.ones((1, n_, n_))
    Bg = np.full((1, n_, n_), 1.0)
    am = np.zeros((1, n_, n_), bool)
    aval = np.zeros((1, n_, n_))
    am[0, 0, 0:4] = True                                         # region (0, 0): four live anchors
    for nd, want in ((1, False), (2, False), (3, True), (4, True)):
        aval[0, 0, 0:4] = [-1.0] * nd + [1.0] * (4 - nd)
        items[f"gate_{nd}_of_4_contradicting_{'refused' if want else 'admitted'}"] = \
            bool(S3.gate(r, sig, Bg, am, aval, *rule(1))[0, 0, 0]) == want
    am1 = np.zeros_like(am)
    am1[0, 0, 0], aval[0, 0, 0] = True, -1.0
    items["gate_single_contradicting_anchor_refuses"] = bool(S3.gate(r, sig, Bg, am1, aval, *rule(1))[0, 0, 0])
    r4 = r.copy()
    r4[0, 0, 0] = 0.1
    items["gate_unconfident_record_not_live"] = not bool(S3.gate(r4, sig, Bg, am1, aval, *rule(1))[0, 0, 0])
    tag = D.TAG
    cases = sim.cases_for(D.SMOKE_BLOCKS[1], "engineering")
    P = sim.prepare(cases, tag)
    units = N1S.event_units(cases, tag)
    H0, W0 = edges_from(bonds(P["R0"], True))
    mk1 = S2.masks(P["TA"], P["TB"], units)
    dcell = sim.rep(mk1["dreg"])
    k = len(cases)
    st = static_identities(cases, P, tag)
    items.update({f"identity_{x}": v for x, v in st.items()})
    ok_v = ok_me = ok_pre = ok_c = ok_chg = True
    p = replace(NATIVE, sigma=D2.SIGMA_ACQ)
    Rk = {t: acquire(tag, cases, D2.AMPLITUDE * P["TA"], p, D.SIDE, settle=D2.SETTLE, teach=t, release=0)[2]
          for t in sorted(set(D.TEACH_K.values())) + [D2.TEACH]}
    items["acquisition_without_release_holds_R0"] = bool(np.array_equal(Rk[D2.TEACH], P["R0"]))
    for j in range(k):
        site = P["sites"][j]
        r0, *_ = sim.start_state("none", j, cases[j], P, units, H0, W0, False, dcell, tag)
        am_, av_ = sim.branch_anchors("Mv", "none", j, P, units, r0)
        ok_v &= bool(np.array_equal(am_, site & (P["V0"][j] != 0)) and np.array_equal(av_, np.where(am_, np.sign(P["V0"][j]), 0)))
        rR, *_ = sim.start_state("R", j, cases[j], P, units, H0, W0, False, dcell, tag)
        am_, av_ = sim.branch_anchors("Me", "R", j, P, units, rR)
        evm = sim.rep(mk1["ev"][j])
        ok_me &= bool(np.array_equal(av_[evm & site], -np.sign(P["R0"][j])[evm & site])
                      and np.array_equal(av_[~evm & site], np.sign(P["R0"][j])[~evm & site]))
        for code in ("Mpre", "Mmid"):
            am_, av_ = sim.branch_anchors(code, "none", j, P, units, r0)
            Rj = Rk[D.TEACH_K[code]][j]
            ok_pre &= bool(np.array_equal(am_, site & (Rj != 0)) and np.array_equal(av_, np.where(am_, np.sign(Rj), 0)))
        am_, av_ = sim.branch_anchors("Mmidc", "none", j, P, units, r0)
        Rj = Rk[D.TEACH_K["Mmidc"]][j]
        ok_c &= bool(np.array_equal(am_, site & (np.abs(Rj) >= D.VMIN)) and np.array_equal(av_, np.where(am_, np.sign(Rj), 0)))
        rC, HC, WC, VC, EC = sim.start_state("change", j, cases[j], P, units, H0, W0, True, dcell, tag)
        Hs, Ws = edges_from(bonds(rC, True))
        dc = dcell[j]
        ok_chg &= bool(np.array_equal(rC[dc], P["RB"][j][dc]) and np.array_equal(rC[~dc], P["R0"][j][~dc])
                       and np.array_equal(VC[dc], P["VB"][j][dc]) and np.array_equal(VC[~dc], P["V0"][j][~dc])
                       and np.array_equal(EC[dc], P["EB"][j][dc]) and np.array_equal(EC[~dc], P["E0"][j][~dc])
                       and np.array_equal(HC, Hs) and np.array_equal(WC, Ws))
    items.update({"Mv_is_the_acquired_body_sign": ok_v, "Me_under_R_holds_the_flip": ok_me,
                  "Mpre_Mmid_are_the_early_record": ok_pre, "Mmidc_only_confident": ok_c,
                  "change_start_state_spliced": ok_chg,
                  "B_acquisition_reproduces_RB": bool(np.array_equal(S2.acquire_history(cases, P["TB"], tag)[2], P["RB"]))})
    # the late commitment: no anchors at the branch, then sign(r) at the sites where r != 0
    rtest = np.random.default_rng(5).standard_normal((2, n_, n_))
    rtest[0, 0, 0] = 0.0
    site2 = np.stack([P["sites"][0]] * 2)
    am_, av_ = sim.commit(rtest, site2)
    items["commit_rule"] = bool(np.array_equal(am_, site2 & (rtest != 0)) and np.array_equal(av_, np.where(am_, np.sign(rtest), 0)))
    am0, _ = sim.branch_anchors("Mt250", "none", 0, P, units, P["R0"][0])
    items["late_commitment_empty_at_the_branch"] = not am0.any()
    # the slow copy: one update, eta 0, the flip time, a newborn anchor
    for code, eta in D.ETA.items():
        a = np.ones((1, 1, 1))
        rr = -np.ones((1, 1, 1))
        e_ = np.full((1, 1, 1), eta)
        one = sim.learn(a, rr, np.ones((1, 1, 1), bool), e_)
        items[f"{code}_one_update"] = bool(one[0, 0, 0] == 1.0 + eta * (-1.0 - 1.0))
        t, x = 0, a
        while x[0, 0, 0] > 0 and t < 10000:
            x = sim.learn(x, rr, np.ones((1, 1, 1), bool), e_)
            t += 1
        want = math.ceil(math.log(0.5) / math.log(1 - eta))
        items[f"{code}_flip_after_{want}"] = t == want
    a = np.array([[[1.0, -1.0, 0.0]]])
    items["eta0_leaves_a"] = bool(np.array_equal(sim.learn(a, -a, np.ones_like(a, bool), np.zeros((1, 1, 1))), a))
    nb_ = sim.learn(np.zeros((1, 1, 2)), np.array([[[0.3, -0.01]]]), np.ones((1, 1, 2), bool), np.full((1, 1, 1), 1e-3))
    items["newborn_takes_the_record_sign"] = bool(np.array_equal(np.sign(nb_), np.array([[[1.0, -1.0]]])))
    # the anchors' shares on synthetic anchors: anchors at A's sign at every site
    mk = {k_: v.copy() for k_, v in mk1.items()}
    mk["evcell"], mk["dcellreg"] = sim.rep(mk["ev"]), sim.rep(mk["dreg"])
    amT = P["sites"].copy()
    avT = np.where(amT, mk["TA"], 0.0)
    sh = sim.anchor_shares(amT, avT, P["sites"], mk)
    same = mk["TA"] == mk["TB"]
    want_B = (amT & same).sum((-2, -1)) / amT.sum((-2, -1))
    want_Bd = (amT & same & mk["dcellreg"]).sum((-2, -1)) / (amT & mk["dcellreg"]).sum((-2, -1))
    kd_def = mk["kdreg"].any((-2, -1))
    items["shares_all_at_A"] = bool(np.allclose(sh["anc_A"], 1) and np.allclose(sh["anc_A_min"], 1) and np.allclose(sh["anc_present"], 1)
                                    and np.allclose(sh["anc_A_dreg"], 1))
    items["shares_B_where_A_equals_B"] = bool(np.allclose(sh["anc_B"], want_B) and np.allclose(sh["anc_B_dreg"], want_Bd))
    items["kd_nan_exactly_where_undefined"] = bool(np.array_equal(np.isnan(sh["anc_A_kd"]), ~kd_def)
                                                   and np.array_equal(np.isnan(sh["anc_B_kd"]), ~kd_def))
    k2 = np.array([0.75, 1.0, 0.5])[:, None, None] * D.KC
    g = S3.gated_k2(k2, np.zeros(0, int), np.zeros((0, n_ // D.REGION, n_ // D.REGION), bool), 3)
    items["k2_times_one_exact"] = bool(np.array_equal(g, np.broadcast_to(k2, g.shape)))
    items["anchor_count_density_4"] = bool((P["sites"].sum((-2, -1)) == n_ * n_ // D.DENSITY).all())
    return {"pass": all(items.values()), "items": items}


def q8(blocks, stage):
    tag, b = D.STAGE_TAG[stage], blocks[0]
    cases = sim.cases_for(b, D.PURPOSE[stage])
    P = sim.prepare(cases, tag)
    arms, labels = D.arms_labels(stage)
    picks = [(f"foreign-{K}+S1e-2", "none"), (f"copy-{K}+Mt250", "R")]
    out = {}
    for unit in D.UNITS:
        o, _, f, _, _ = sim.run(cases, unit, labels, prep=P, tag=tag, window=300, reads=(300,))
        res = {}
        for lab in picks:
            o2, _, f2, _, _ = sim.run(cases, unit, [lab, lab], prep=P, tag=tag, window=300, reads=(300,))
            bi = labels.index(lab)
            res["/".join(lab)] = {"twice_identical": bool(np.array_equal(f2["r"][0], f2["r"][1])),
                                  "alone_equals_batch": bool(np.array_equal(f2["r"][0], f["r"][bi]))}
        out[unit] = res
    return {"pass": all(all(all(x.values()) for x in v.values()) for v in out.values()), "units": out}


def q9(root, blocks):
    M = json.loads((root / "manifest.json").read_text())
    cpu = {u: np.mean([t["cpu_s"] for k_, t in M["tasks"].items() if k_.startswith(u + "/")]) for u in D.UNITS}
    n_dev = len(D.IDENTITIES["development"])
    total = n_dev * sum(cpu.values()) / 3600
    wall = max(cpu.values()) / 3600 * int(np.ceil(n_dev * len(D.UNITS) / 12))
    rss = M["worker_maxrss_mb_peak"]
    disk = shutil.disk_usage(root).free > 50 * M["bytes_written"]
    return {"pass": total <= 30 and wall <= 12 and rss <= 2048 and disk, "forecast_dev_cpu_h": round(total, 2),
            "forecast_dev_wall_h_12": round(wall, 2), "cpu_s_per_task": {u: round(v, 1) for u, v in cpu.items()},
            "worker_rss_mb": rss, "disk_headroom": disk}


def q10(root, stage):
    with tempfile.TemporaryDirectory(dir=root) as td:
        env = dict(os.environ, PYTHONPATH=str(LANE), PYTHONDONTWRITEBYTECODE="1")
        r1 = subprocess.run([sys.executable, "-m", "nl004.analyze", "--root", str(root), "--stage", stage, "--out", td],
                            cwd=LANE, env=env, capture_output=True, text=True)
        r2 = subprocess.run([sys.executable, "-m", "nl004.tables", "--root", str(root), "--stage", stage, "--out", td],
                            cwd=LANE, env=env, capture_output=True, text=True)
        sizes = {p.name: p.stat().st_size for p in Path(td).iterdir()}
        S = json.loads((Path(td) / "predictions_scored.json").read_text()) if (Path(td) / "predictions_scored.json").exists() else {}
    computed = bool(S) and all(np.isfinite(p["value"]) for node in S.values() for p in node["parts"].values())
    return {"pass": r1.returncode == 0 and r2.returncode == 0 and computed and all(v <= 256_000 for v in sizes.values()),
            "stderr": (r1.stderr + r2.stderr)[-400:], "sizes": sizes, "parts": sum(len(n["parts"]) for n in S.values())}


CHECKS = ("Q1_complete_finite", "Q2_serial_equals_parallel", "Q3_bridge_none", "Q3_bridge_dw", "Q4_replay", "Q5_aliases",
          "Q6_reanalysis", "Q7_efficacy", "Q8_pairing", "Q9_resources", "Q10_reader_dry_run")


def run_check(name, root, blocks, stage):
    fn = {"Q1_complete_finite": lambda: q1(root, blocks, stage), "Q2_serial_equals_parallel": lambda: q2(root, blocks, stage),
          "Q3_bridge_none": lambda: q3(root, blocks, stage, ("none",)), "Q3_bridge_dw": lambda: q3(root, blocks, stage, ("dw",)),
          "Q4_replay": lambda: q4(blocks, stage), "Q5_aliases": lambda: q5(root, blocks, stage),
          "Q6_reanalysis": lambda: q6(root, blocks, stage), "Q7_efficacy": q7, "Q8_pairing": lambda: q8(blocks, stage),
          "Q9_resources": lambda: q9(root, blocks), "Q10_reader_dry_run": lambda: q10(root, stage)}[name]
    t1 = time.time()
    try:
        res = fn()
    except Exception as exc:                                      # a crash is a failure, recorded
        res = {"pass": False, "error": repr(exc)[:500]}
    res["seconds"] = round(time.time() - t1, 1)
    print(f"{time.strftime('%H:%M:%SZ', time.gmtime())} {name}: {'PASS' if res['pass'] else 'FAIL'} ({res['seconds']} s)", flush=True)
    return res


def main():
    """--only NAME[,NAME] writes the named checks' results to --part; --merge PART [PART ...] writes the receipt from
    parts (every check exactly once); with neither, every check runs here in turn."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--stage", choices=("preflight", "debug"), required=True)
    ap.add_argument("--receipt", type=Path, default=None)
    ap.add_argument("--only", default=None)
    ap.add_argument("--part", type=Path, default=None)
    ap.add_argument("--merge", type=Path, nargs="*", default=None)
    a = ap.parse_args()
    root = a.root.resolve()
    blocks = D.stage_blocks(a.stage)
    t0 = time.time()
    if a.only is not None:
        res = {n: run_check(n, root, blocks, a.stage) for n in a.only.split(",")}
        a.part.write_text(json.dumps(res, indent=1, default=str) + "\n")
        return
    if a.merge is not None:
        checks = {}
        for f in a.merge:
            for k_, v in json.loads(f.read_text()).items():
                assert k_ not in checks, k_
                checks[k_] = v
        assert sorted(checks) == sorted(CHECKS), sorted(set(CHECKS) ^ set(checks))
        wall = round(sum(v["seconds"] for v in checks.values()), 1)
    else:
        checks = {n: run_check(n, root, blocks, a.stage) for n in CHECKS}
        wall = round(time.time() - t0, 1)
    checks = {n: checks[n] for n in CHECKS}
    failed = [k_ for k_, v in checks.items() if not v["pass"]]
    receipt = {"status": "PASS" if not failed else "FAIL", "failed": failed, "design_digest": D.digest(), "rule": D.RULE,
               "root": str(root), "stage": a.stage, "blocks": blocks, "tag": D.STAGE_TAG[a.stage],
               "load_1min_at_check": float(open("/proc/loadavg").read().split()[0]),
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "check_seconds_sum": wall,
               "checks": checks}
    out = a.receipt or (root / "qualification_receipt.json")
    out.write_text(json.dumps(receipt, indent=1, default=str) + "\n")
    print(json.dumps({"status": receipt["status"], "failed": failed}))


if __name__ == "__main__":
    main()
