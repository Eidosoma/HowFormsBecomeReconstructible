"""E2E004's successors: AR001's fixed policies as routes, in every generation, started from restored generation-0 packets.

generation  ar001.sim.run's update, written for branches that start from their own states. Every branch (rows x cases,
            row-major) has its own first record A = (H, W, Hb, Wb, r) and body; the vote's branches also a second record
            B = (HB, WB, HbB, WbB, rB). Each route's branches are one group, and each group's targets run on all its
            branches at once (ar001.sim.run runs each arm on its own; the arithmetic is per branch):
              body    lr005.sim.targets("body"): the body's co-activity, clipped
              vote    lr005.sim.targets("vote2r") with the branch's second record; both records learn the same targets
              record  lr005.sim.targets("record+parity"), then lr001.sim.parity_repair, as ar001.sim.run's record arm
              vote1   lr005.sim.targets("vote2r") with a second record of zeros: lr005.sim.vote_sign(0) = 0, so the second
                      copy always abstains and vote2r's sum is the body's and the record's alone; where they disagree it is 0
                      and AR001's own learning mask (a target of 0 learns nothing) holds the bond
            The streams are named by the caller: ar001.sim.run's own names under the record's tag reproduce generation 0
            (replay0, the bridge), and a future's names under E2E004's tag give a successor.
lineage     rows run from their packets for generations of T_GEN updates: a newborn body (V = E = a birth under the
            future's names, as E2E001 and E2E002); the first record from the packet with the strengths at STRENGTH0 x sign
            (sr001.sim.handoff, as at every handoff); for the vote, the second record a copy of the incoming record (the
            vote's own rule when no event hits the first record, as in E2E002); the row's route. Nothing else crosses.
packets     a task's rows from its restored raw file (e2e002.sim.packet_of, unchanged); identical (packet, route) rows run
            once, every label they stand for named.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib

import numpy as np

from ar001 import design as A
from ar001 import sim as A1S
from ar003 import sim as S3
from dl001 import design as DL
from dl001 import sim as S
from e2e001 import sim as E1
from e2e002 import sim as E2
from lr001.sim import cut_for, halves, parity_repair
from lr005 import sim as L5S
from mse.native import NATIVE
from msegrid.core import Stream, birth, record_step
from sr001 import sim as SRS

from . import design as D

RUN_NAMES = (("future",), ("record-noise",), ("bond-noise",), ("record-noise", "B"), ("bond-noise", "B"))
BIRTH_NAMES = E1.BIRTH_NAMES            # ("e2e", "fut", f, "gen", g, "birth"), under E2E004's tag
GEN_NAMES = E1.GEN_NAMES                # the future's five streams, under E2E004's tag
score, protected, post_damage = E1.score, E1.protected, E1.post_damage
TARGET = {"body": "body", "vote": "vote2r", "record": "record+parity", "vote1": "vote2r"}


def groups_of(routes, k):
    """[(route, branch indices)] for rows' route names (row-major branches), in D.ROUTES' order."""
    out = []
    for name in D.ROUTES:
        rows = [j for j, p in enumerate(routes) if p == name]
        if rows:
            out.append((name, np.concatenate([np.arange(j * k, (j + 1) * k) for j in rows])))
    if sum(len(ix) for _r, ix in out) != len(routes) * k:
        raise ValueError(f"a route without a definition: {sorted(set(routes) - set(D.ROUTES))}")
    return out


def generation(body, groups, cases, V, E, A_, B_, thb, tag, names, window=D.T_GEN, gain=D.GAIN, clock=None):
    """One generation. groups: [(route, branch indices)] partitioning the branches; B_ the vote group's second records in
    that group's branch order (None without a vote group). Returns V, E, A and B."""
    clock = D.CLOCK if clock is None else clock
    eta = clock["eta"]
    alpha, L = DL.BODIES[body]
    G = S.ghat(A.SIDE, L) if alpha else None
    k = len(cases)
    n = V.shape[0]
    idx = np.tile(np.arange(k), n // k)
    H, W, Hb, Wb, r = (x.copy() for x in A_)
    vote_ix = dict(groups).get("vote")
    if vote_ix is not None:
        HB, WB, HbB, WbB, rB = (x.copy() for x in B_)
        idxB = idx[vote_ix]
    cut = cut_for(clock["rate"])
    p = replace(NATIVE, sigma=A.SIGMA)
    st, xs, zs = (Stream(tag, cases, *nm, side=A.SIDE) for nm in names[:3])
    if vote_ix is not None:
        xsB, zsB = (Stream(tag, cases, *nm, side=A.SIDE) for nm in names[3:5])
    for t in range(1, window + 1):
        i = (t - 1) % A.CHUNK
        if i == 0:
            buf, xbuf, zbuf = st.take(A.CHUNK), xs.take(A.CHUNK), zs.take(A.CHUNK)
            if vote_ix is not None:
                xbB, zbB = xsB.take(A.CHUNK), zsB.take(A.CHUNK)
        V, E, Vt, drift, d = S.body(V, E, r, thb, buf[i][idx], p, gain, alpha, G)
        z = zbuf[i][idx]
        hh, hw = z > cut, z < -cut
        H, W, Hb, Wb = np.where(hh, -H, H), np.where(hw, -W, W), np.where(hh, -Hb, Hb), np.where(hw, -Wb, Wb)
        r = record_step(r, xbuf[i][idx], A.EPS, A.KR, A.SIGMA_R, A.KC, None, halves(H, W))
        if vote_ix is not None:
            zB = zbB[i][idxB]
            h2, w2 = zB > cut, zB < -cut
            HB, WB, HbB, WbB = np.where(h2, -HB, HB), np.where(w2, -WB, WB), np.where(h2, -HbB, HbB), np.where(w2, -WbB, WbB)
            rB = record_step(rB, xbB[i][idxB], A.EPS, A.KR, A.SIGMA_R, A.KC, None, halves(HB, WB))
        for route, ix in groups:
            Vs, rs = V[ix], r[ix]
            second = rB if route == "vote" else (np.zeros_like(rs) if route == "vote1" else None)
            xh, xw, _extra = L5S.targets(TARGET[route], Vs, rs, second, None, None)
            lh, lw = xh != 0, xw != 0
            Hbs, Wbs = Hb[ix], Wb[ix]
            Hn, Wn = Hbs + eta * (xh - Hbs), Wbs + eta * (xw - Wbs)
            Hbs, Wbs = np.where(lh, Hn, Hbs), np.where(lw, Wn, Wbs)
            Hs = np.where(lh & (Hbs != 0), np.sign(Hbs), H[ix])
            Ws = np.where(lw & (Wbs != 0), np.sign(Wbs), W[ix])
            if route == "vote":
                HbB, WbB = np.where(lh, HbB + eta * (xh - HbB), HbB), np.where(lw, WbB + eta * (xw - WbB), WbB)
                HB = np.where(lh & (HbB != 0), np.sign(HbB), HB)
                WB = np.where(lw & (WbB != 0), np.sign(WbB), WB)
            if route == "record":
                H2, W2 = parity_repair(Hs, Ws)
                Hbs = np.where(np.sign(Hbs) * H2 < 0, -Hbs, Hbs)
                Wbs = np.where(np.sign(Wbs) * W2 < 0, -Wbs, Wbs)
                Hs, Ws = H2, W2
            Hb[ix], Wb[ix], H[ix], W[ix] = Hbs, Wbs, Hs, Ws
    B_out = (HB, WB, HbB, WbB, rB) if vote_ix is not None else None
    return V, E, (H, W, Hb, Wb, r), B_out


def replay0(body, situation, routes, cases, V0, ema0, R0, th, T, theta, tag, window=D.T_GEN, size=D.SIZE):
    """Generation 0 re-run by generation() from the event's state (ar001.sim.event under the record's tag; the vote's second
    record as ar001.sim.run builds it; ar001.sim.run's stream names): the bridge to ar001.sim.run itself."""
    base, sig = situation.split("@")
    ev = A1S.event(base, size, float(sig), cases, V0, ema0, R0, T, tag)
    k = len(cases)
    idx = np.tile(np.arange(k), len(routes))
    A_ = tuple(ev[x][idx].copy() for x in ("H", "W", "Hb", "Wb", "r"))
    groups = groups_of(routes, k)
    B_ = None
    if "vote" in routes:
        ixv = dict(groups)["vote"]
        rB, HB, WB, HbB, WbB = S3.second_record(base, ev, R0, idx[ixv])
        B_ = (HB, WB, HbB, WbB, rB)
    return generation(body, groups, cases, ev["V"][idx].copy(), ev["E"][idx].copy(), A_, B_, (th * theta)[idx], tag,
                      RUN_NAMES, window)


def lineage(body, rows, cases, thf, T, Tf, m, tag, gen_names, birth_names, t_gen=D.T_GEN, horizons=D.HORIZONS, keep=()):
    """rows: dicts {"packet": (H, W, r) each (cases, side, side), "route", "stop"}. Returns the reads at the horizons
    ({g: {endpoint: (rows alive, cases)}}), the rows alive at each, and the states kept at the generations in `keep`."""
    k = len(cases)
    alive = list(range(len(rows)))
    H, W, r = (np.concatenate([np.asarray(row["packet"][x], dtype=float) for row in rows]) for x in range(3))
    A_ = (H.copy(), W.copy(), D.STRENGTH0 * H, D.STRENGTH0 * W, r.copy())
    reads, alive_at, kept = {}, {}, {}
    for g in range(1, max(row["stop"] for row in rows) + 1):
        still = [i for i in alive if rows[i]["stop"] >= g]
        if still != alive:
            sel = np.concatenate([np.arange(alive.index(i) * k, (alive.index(i) + 1) * k) for i in still])
            A_ = tuple(x[sel] for x in A_)
            alive = still
        idx = np.tile(np.arange(k), len(alive))
        V = birth(tag, cases, *birth_names(g), side=D.SIDE)[idx].copy()
        E = V.copy()
        groups = groups_of([rows[i]["route"] for i in alive], k)
        ixv = dict(groups).get("vote")
        B_ = None if ixv is None else tuple(x[ixv].copy() for x in A_)
        V, E, A_, _B = generation(body, groups, cases, V, E, A_, B_, thf[idx], tag, gen_names(g), t_gen)
        if g in horizons:
            sc = score(V, A_[4], T[idx], Tf[:, idx], m[idx])
            reads[g] = {key: v.reshape(len(alive), k) for key, v in sc.items()}
        alive_at[g] = list(alive)
        if g in keep:
            kept[g] = {"rows": list(alive), "V": V.copy(), "r": A_[4].copy(), "H": A_[0].astype(np.int8),
                       "W": A_[1].astype(np.int8)}
        A_, _ = SRS.handoff(A_, None)
    return reads, alive_at, kept


def _digest(*xs):
    h = hashlib.sha256()
    for x in xs:
        h.update(np.ascontiguousarray(np.asarray(x, dtype=float)).tobytes())
    return h.hexdigest()


def packets(raw, meta, cases, V0, ema0, R0, T, lineages):
    """The task's distinct rows and, for each lineage label, the row it runs on; the alias table; the packets' sources."""
    rows, labels, aliases, sources, sig = [], {}, {}, {}, {}
    for ln in lineages:
        pk, src = E2.packet_of(ln["packet"], raw, meta, cases, V0, ema0, R0, T)
        if pk is None:
            continue
        pk = tuple(np.asarray(x, dtype=float) for x in pk)
        h = (_digest(*pk), ln["route"])
        if h in sig:
            i = sig[h]
            rows[i]["stop"] = max(rows[i]["stop"], ln["stop"])
            aliases.setdefault(rows[i]["labels"][0], []).append(ln["label"])
            rows[i]["labels"].append(ln["label"])
        else:
            sig[h] = len(rows)
            rows.append({"labels": [ln["label"]], "packet": pk, "route": ln["route"], "stop": ln["stop"], "source": src})
        labels[ln["label"]] = sig[h]
        sources[ln["label"]] = src
    return rows, labels, aliases, sources
