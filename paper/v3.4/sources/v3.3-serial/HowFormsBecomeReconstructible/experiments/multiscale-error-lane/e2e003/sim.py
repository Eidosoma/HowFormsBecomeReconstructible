"""E2E003's successors under repeated injury: E2E002's machinery with a fresh injury in every generation.

generation  e2e002.sim.generation's own source, compiled in a copy of e2e002.sim's namespace with its one detector call
            (A5S.detect, AR005's) routed to ar006.sim.detect, which carries vtol's split guard (ar005.sim.guarded_windows
            refuses a split guard). For every configuration without the split (the vote, vms) ar006.sim.detect is AR005's,
            so this generation is E2E002's bit for bit there (Q3's bridge). The substitution is asserted to apply once.
replay0     e2e002.sim.replay0's own source compiled with this generation: generation 0 re-run from the event's state, the
            bridge to AR006's saved records (vtol included)
schedule    the injury patches: per case and generation g = 1..G, a size x size patch at a corner drawn from an addressed
            stream under the stage's tag, address(tag, block, message, parent, "e2e003", "injury", g, attempt), taking the
            first attempt whose patch is disjoint from generation 0's patch and from every earlier generation's (rejection
            sampling on the periodic sheet)
injure      memory damage on a patch of an incoming record: the record flipped on the patch with its bonds kept consistent
            (H and W, and their strengths Hb and Wb, flipped on every edge with exactly one end in the patch: H[i, j] is the
            edge (i, j)-(i, j+1), W[i, j] the edge (i, j)-(i+1, j)); nothing else changes. On generation 0's record and its
            consistent bonds (be001.sim.event's own construction) this is be001.sim.event's memory rule exactly (Q7)
lineage     e2e002.sim.lineage's generation loop with the injury: each generation g a newborn body (E2E002's birth under the
            future's names), the second record a copy of the incoming record (the injury hits the first record only), the
            cue from the incoming record's signs (e2e002.sim.birth_cue at the row's sigma: the pre-injury signs), then for
            an injured row the injury on its generation-g patch at update 0, then the routed generation; reads in every
            generation (E2E001's score: on the union of generation 0's patch and every patch injured so far, on the
            generation's own patch, and whole-sheet), the detectors' diagnostics and the injury's own check; the handoff
            (sr001.sim.handoff). Without a schedule (sched None) it is E2E002's lineage bit for bit (Q3)
packets     the task's rows from the restored raw file (e2e002.sim.packet_of, unchanged); identical rows (packet, policy,
            injury and, for a detector, sigma: the vote never reads its cue) run once, every label they stand for named
"""
from __future__ import annotations

import numpy as np

from ar005 import sim as S5
from ar006 import sim as S6
from e2e001 import sim as E1
from e2e002 import sim as E2
from mse.native import address
from msegrid.core import birth
from sr001 import sim as SRS

from . import design as D

DETECT_CALL = "A5S.detect(sta, Vs, rs, Pg[gi], cfg, t, mg[gi])"
generation = S5.derive(E2.generation, dict(vars(E2), detect_vt=S6.detect), DETECT_CALL,
                       "detect_vt(sta, Vs, rs, Pg[gi], cfg, t, mg[gi])")
replay0 = S5.derive(E2.replay0, dict(vars(E2), generation=generation))
DIAG = E2.DIAG
BIRTH_NAMES, GEN_NAMES = E2.BIRTH_NAMES, E2.GEN_NAMES
score, post_damage, packet_of, birth_cue, groups_of = E1.score, E2.post_damage, E2.packet_of, E2.birth_cue, E2.groups_of
READS = {"u_r": "u_r", "u_v": "u_v", "u_r_raw": "u_r_raw", "agree_in": "agree_in", "a_r": "a_r", "a_v": "a_v",
         "q_r": "q_r", "q_v": "q_v"}          # the own patch's score; whole-sheet a and q
UNION_READS = {"U": "u_r", "U_v": "u_v", "U_raw": "u_r_raw", "agree_U": "agree_in"}   # the union's score


def schedule(cases, m0, tag, gens, size=D.SIZE, side=D.SIDE):
    """{g: (k, side, side) bool} for g = 1..gens, the corners (k, gens, 2) and the attempts (k, gens)."""
    k = len(cases)
    sched = {g: np.zeros((k, side, side), bool) for g in range(1, gens + 1)}
    corners, attempts = np.zeros((k, gens, 2), np.int64), np.zeros((k, gens), np.int64)
    rows, cols = np.arange(size), np.arange(size)
    for j, c in enumerate(cases):
        used = m0[j].copy()
        for g in range(1, gens + 1):
            for att in range(D.MAX_ATTEMPTS):
                a, b = address(tag, *c.key(), *D.INJURY["stream"], g, att).integers(0, side, 2)
                p = np.zeros((side, side), bool)
                p[np.ix_((a + rows) % side, (b + cols) % side)] = True
                if not (p & used).any():
                    break
            else:
                raise RuntimeError(f"no disjoint patch for case {c.key()} at generation {g}")
            sched[g][j], corners[j, g - 1], attempts[j, g - 1] = p, (a, b), att
            used |= p
    return sched, corners, attempts


def edges(M):
    """The edges with exactly one end in M: (horizontal, vertical), each (n, side, side) bool."""
    return M ^ np.roll(M, -1, -1), M ^ np.roll(M, -1, -2)


def injure(A_, M):
    """Memory damage on the branches' patches M (n, side, side) bool, applied to the first record A = (H, W, Hb, Wb, r)."""
    H, W, Hb, Wb, r = A_
    xh, xw = edges(M)
    return (np.where(xh, -H, H), np.where(xw, -W, W), np.where(xh, -Hb, Hb), np.where(xw, -Wb, Wb), np.where(M, -r, r))


def injury_ok(before, after, M):
    """(n,) bool: the record changed exactly on M (flipped there), the bonds and strengths exactly on M's boundary edges."""
    xh, xw = edges(M)
    ok = np.ones(M.shape[0], bool)
    for x, (b, a) in zip(("H", "W", "Hb", "Wb", "r"), zip(before, after)):
        mask = {"H": xh, "W": xw, "Hb": xh, "Wb": xw, "r": M}[x]
        ok &= np.all(np.where(mask, a == -b, a == b), axis=(-2, -1))
    return ok


def lineage(body, rows, cases, thf, T, Tf, m0, am, normals, tag, gen_names, birth_names, sched=None, t_gen=D.T_GEN,
            keep=(), configs=None):
    """rows: dicts {"packet": (H, W, r) each (cases, side, side), "policy", "sigma", "stop", "injured"}. sched: {g: (cases,
    side, side)} the injury patches (None: no injury, generation 0's patch read as E2E002 reads it). Returns the reads of
    every generation ({g: {endpoint: (rows alive, cases)}}), the rows alive at each, the diagnostics of every generation
    and the states kept at the generations in `keep`."""
    configs = D.POLICIES if configs is None else configs
    k = len(cases)
    alive = list(range(len(rows)))
    H, W, r = (np.concatenate([np.asarray(row["packet"][x], dtype=float) for row in rows]) for x in range(3))
    A_ = (H.copy(), W.copy(), D.STRENGTH0 * H, D.STRENGTH0 * W, r.copy())
    reads, alive_at, diags, kept = {}, {}, {}, {}
    union = m0.copy()
    for g in range(1, max(row["stop"] for row in rows) + 1):
        still = [i for i in alive if rows[i]["stop"] >= g]
        if still != alive:
            sel = np.concatenate([np.arange(alive.index(i) * k, (alive.index(i) + 1) * k) for i in still])
            A_ = tuple(x[sel] for x in A_)
            alive = still
        idx = np.tile(np.arange(k), len(alive))
        V = birth(tag, cases, *birth_names(g), side=D.SIDE)[idx].copy()
        E = V.copy()
        B_ = tuple(x.copy() for x in A_)
        aval = np.empty_like(A_[4])
        for j, i in enumerate(alive):
            sl = slice(j * k, (j + 1) * k)
            aval[sl] = birth_cue(A_[4][sl], normals, rows[i]["sigma"])
        P = {"am": am[idx], "aval": aval}
        exact = np.where(A_[4] > 0, 1.0, -1.0)
        cue_dis = ((aval != exact) & P["am"]).sum((-2, -1)).reshape(len(alive), k)
        mg = m0 if sched is None else sched[g]
        inj = None
        if sched is not None:
            union = union | mg
            hit = np.repeat(np.array([bool(rows[i]["injured"]) for i in alive]), k)
            M = mg[idx] & hit[:, None, None]
            before = A_
            A_ = injure(A_, M)
            inj = injury_ok(before, A_, M) & (M.sum((-2, -1)) == np.where(hit, D.SIZE * D.SIZE, 0))
        V, E, A_, B_, dg = generation(body, groups_of([rows[i]["policy"] for i in alive], k, configs), cases, V, E, A_, B_,
                                      P, mg[idx], thf[idx], tag, gen_names(g), t_gen)
        diags[g] = {key: dg[key].reshape(len(alive), k) for key in DIAG}
        diags[g]["cue_dis_birth"] = cue_dis
        if inj is not None:
            diags[g]["injury_ok"] = inj.reshape(len(alive), k)
        Tb, Tfb = T[idx], Tf[:, idx]
        so = score(V, A_[4], Tb, Tfb, mg[idx])
        su = score(V, A_[4], Tb, Tfb, union[idx])
        reads[g] = {key: so[e].reshape(len(alive), k) for key, e in READS.items()}
        reads[g].update({key: su[e].reshape(len(alive), k) for key, e in UNION_READS.items()})
        alive_at[g] = list(alive)
        if g in keep:
            kept[g] = {"rows": list(alive), "V": V.copy(), "r": A_[4].copy(), "H": A_[0].astype(np.int8),
                       "W": A_[1].astype(np.int8)}
        A_, _ = SRS.handoff(A_, None)
    return reads, alive_at, diags, kept


def _digest(*xs):
    return E2._digest(*xs)


def packets(raw, meta, cases, V0, ema0, R0, T, lineages):
    """The task's distinct rows and, for each lineage label, the row it runs on; the alias table; the packets' sources."""
    rows, labels, aliases, sources, sig = [], {}, {}, {}, {}
    for ln in lineages:
        pk, src = packet_of(ln["packet"], raw, meta, cases, V0, ema0, R0, T)
        if pk is None:
            continue
        pk = tuple(np.asarray(x, dtype=float) for x in pk)
        reads_cue = ln["policy"] != "vote"           # the vote never reads its cue: its lineage is the packet's alone
        h = (_digest(*pk), ln["policy"], bool(ln["injured"]), ln["sigma"] if reads_cue else "-")
        if h in sig:
            i = sig[h]
            rows[i]["stop"] = max(rows[i]["stop"], ln["stop"])
            aliases.setdefault(rows[i]["labels"][0], []).append(ln["label"])
            rows[i]["labels"].append(ln["label"])
        else:
            sig[h] = len(rows)
            rows.append({"labels": [ln["label"]], "packet": pk, "policy": ln["policy"], "sigma": ln["sigma"],
                         "stop": ln["stop"], "injured": bool(ln["injured"]), "source": src})
        labels[ln["label"]] = sig[h]
        sources[ln["label"]] = src
    return rows, labels, aliases, sources
