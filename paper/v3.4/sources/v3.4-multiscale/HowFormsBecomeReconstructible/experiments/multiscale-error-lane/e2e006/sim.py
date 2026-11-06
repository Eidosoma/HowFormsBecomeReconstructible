"""E2E006's successors: E2E003's renewal under repeated injury, with groups of sheets sharing SM007's field.

generation  e2e002.sim.generation's own source compiled with two substitutions, each asserted to apply once: its detector
            call routed to ar006.sim.detect (E2E003's routing: vtol's split guard), and its one body call
            (dl001.sim.body) routed through field_body(). With no coupling set, field_body is dl001.sim.body itself, so
            the generation is E2E003's bit for bit (P63s, Q3). With a coupling, field_body applies the declared response
            to the declared parameter of each branch (from the field sampled at the previous update, inside the row's
            window), calls dl001.sim.body, then computes each branch's stress, emission and the medium's step (every
            update), as SM007 declares them.
lineage     e2e003.sim's lineage loop (births, the second record, the birth cue, the injury at update 0, the reads of every
            generation, the handoff), with each row's medium: none; isolated (the eight sheets in one Medium as
            disconnected blocks) or shared (the eight sheets in rectangle(2, 4)); reset at every replacement or retained
            across it; protected copying for the protected row (its incoming packet, copied before the injury, is what
            it passes on); and, after the generations in FRESH_AT, the fresh-successor test: a field-free newborn
            reading each row's outgoing record for one generation under its own names (the vote, no injury, no medium),
            scored, never entering the lineage.
packets     e2e003.sim.packets with the field, medium, window and copying in a row's identity.
"""
from __future__ import annotations

import inspect

import numpy as np

from ar006 import sim as S6
from dl001 import sim as S
from e2e001 import sim as E1
from e2e002 import sim as E2
from e2e003 import sim as E3
from msegrid.core import birth
from sr001 import sim as SRS

from . import design as D

DETECT_CALL = "A5S.detect(sta, Vs, rs, Pg[gi], cfg, t, mg[gi])"
BODY_CALL = "V, E, Vt, drift, d = S.body(V, E, r, thb, buf[i][idx], p, gain, alpha, G)"
_COUPLING = None                          # the coupling of the generation now running (None: no field)


def field_body(t, V, E, r, thb, z, p, gain, alpha, G):
    """dl001.sim.body, through the current coupling when one is set."""
    if _COUPLING is None:
        return S.body(V, E, r, thb, z, p, gain, alpha, G)
    return _COUPLING.body(t, V, E, r, thb, z, p, gain, alpha, G)


def _derive(fn, namespace, subs):
    src = inspect.getsource(fn)
    for old, new in subs:
        if src.count(old) != 1:
            raise RuntimeError(f"{fn.__module__}.{fn.__name__}: '{old}' occurs {src.count(old)} times, not once")
        src = src.replace(old, new)
    exec(compile(src, f"<{fn.__module__}.{fn.__name__}, routed by e2e006>", "exec"), namespace)
    return namespace[fn.__name__]


_NS = dict(vars(E2), detect_vt=S6.detect, field_body=lambda *a: field_body(*a))
generation = _derive(E2.generation, _NS, ((DETECT_CALL, "detect_vt(sta, Vs, rs, Pg[gi], cfg, t, mg[gi])"),
                                          (BODY_CALL, "V, E, Vt, drift, d = field_body(t, V, E, r, thb, buf[i][idx], p, gain, alpha, G)")))
DIAG = E2.DIAG
BIRTH_NAMES, GEN_NAMES = E2.BIRTH_NAMES, E2.GEN_NAMES
FRESH_BIRTH = lambda f: (lambda g: (*D.FRESH["names"], "fut", f, "gen", g, "birth"))
FRESH_GEN = lambda f: (lambda g: tuple((*D.FRESH["names"], "fut", f, "gen", g, *s) for s in
                                       (("future",), ("record-noise",), ("bond-noise",), ("record-noise", "B"),
                                        ("bond-noise", "B"))))
score, post_damage, birth_cue, groups_of = E1.score, E2.post_damage, E2.birth_cue, E2.groups_of
schedule, injure, injury_ok, packet_of = E3.schedule, E3.injure, E3.injury_ok, E2.packet_of
READS, UNION_READS = E3.READS, E3.UNION_READS


class Coupling:
    """The field for one generation's branches. adapter: the bridge to SM007's msefield (FieldAdapter below), used
    unchanged; groups: [{"branches", "window", "medium", "kappa"}], one per field row (shared: the row's eight sheets in
    rectangle(2, 4); isolated: the same eight sheets in disconnected blocks). Branches in no group (field-free rows in the
    same call) neither emit nor respond. Every update t: the response acts on the branches whose window contains t, from
    the exposure x(t) (the field sampled after update t - 1's step; at t = 1 the medium's state at birth: zero when reset,
    the carried field when retained); then dl001.sim.body; then each branch's stress and emission, and each medium's
    step. x(t) is summed by window (the engineering quantities P63k fixes kappa from), and kappa x x(t) where the response
    acted (the realized integrated exposure)."""

    def __init__(self, adapter, groups, n):
        self.adapter, self.groups = adapter, groups
        self.lo, self.hi = np.full(n, np.inf), np.full(n, -np.inf)
        self.kappa = np.zeros((n, 1, 1))
        c = np.zeros(n)
        for g in groups:
            self.lo[g["branches"]], self.hi[g["branches"]] = g["window"]
            self.kappa[g["branches"]] = g["kappa"]
            c[g["branches"]] = g["medium"].sample()
        self.c = c[:, None, None]
        self.half = D.T_GEN // 2
        self.sums = {"full": np.zeros(n), "early": np.zeros(n), "late": np.zeros(n)}   # x(t) summed by window
        self.kc = np.zeros(n)              # kappa x x(t) summed over the updates where the response acted

    def body(self, t, V, E, r, thb, z, p, gain, alpha, G):
        x = self.c[:, 0, 0]
        self.sums["full"] += x
        self.sums["early" if t <= self.half else "late"] += x
        active = ((self.lo <= t) & (t <= self.hi))[:, None, None]
        if active.any():
            gain, thb, p = self.adapter.respond(self.c, active, self.kappa, gain=gain, thb=thb, p=p)
            self.kc += np.where(active, self.kappa * self.c, 0.0)[:, 0, 0]
        out = S.body(V, E, r, thb, z, p, gain, alpha, G)
        emissions = self.adapter.emission(self.adapter.stress(V=out[0], Vt=out[2], drift=out[3], d=out[4], r=r))
        c = np.zeros(V.shape[0])
        for g in self.groups:
            ix = g["branches"]
            c[ix] = g["medium"].step(emissions[ix])        # msefield.Medium.step: one tissue update; the exposures after it
        self.c = c[:, None, None]
        return out

    def summary(self, window):
        """Per branch: the mean exposure x(t) over the generation and over each half, and kappa x x(t) summed over the
        updates where the response acted, divided by the generation's length (0 for branches in no group)."""
        return {"exp_full": self.sums["full"] / window, "exp_early": self.sums["early"] / self.half,
                "exp_late": self.sums["late"] / (window - self.half), "kexp": self.kc / window}


class FieldAdapter:
    """The one place E2E006 touches SM007's msefield (fb934f1f10, imported unchanged). Interface used:
    medium(n): msefield.Medium(positions, D, gamma, leak, dt, m, margin) over FIELD["positions"] (rectangle(2, 4));
    medium_isolated(): the same over FIELD["isolated_positions"], eight disconnected blocks; step(emissions) advances one
    tissue update and returns each sheet's exposure (the mean of c over its block); sample() the exposures now.
    stress, emission and respond: the lead's rulings (12:26:39Z on 5 November), from each sheet's own state only."""

    def __init__(self, msefield, field=D.FIELD):
        self.m, self.field = msefield, field

    def medium(self, n):
        pos = list(self.field["positions"])[:n]
        f = self.field
        return self.m.Medium(pos, f["D"], f["gamma"], f["leakage"], dt=f["dt"], m=f.get("m", 4), margin=f.get("margin", 0))

    def medium_isolated(self):
        f = self.field
        return self.m.Medium(list(f["isolated_positions"]), f["D"], f["gamma"], f["leakage"], dt=f["dt"], m=f["m"],
                             margin=f["margin"])

    def stress(self, V, Vt, drift, d, r):
        """The lead's ruling: a sheet's mean |r - V-tilde| over its cells (the record's pull on its body)."""
        return np.abs(r - Vt).mean((-2, -1))

    def emission(self, stress):
        """The lead's ruling: emission = stress."""
        return stress

    def respond(self, c, active, kappa, gain, thb, p):
        """The lead's ruling: the body's reading gain x (1 + kappa x exposure), on the active branches only."""
        return np.where(active, gain * (1.0 + kappa * c), gain), thb, p


def kappas(override=None):
    """The response's kappa for each window (the full window's kappa, and the matched early and late ones) and the
    optional matched isolated row's ("isolated")."""
    if override is not None:
        return {"full": override, "early": override, "late": override, "isolated": override}
    k = {"full": D.FIELD["kappa"], "early": D.FIELD["kappa_early"], "late": D.FIELD["kappa_late"],
         "isolated": D.FIELD["kappa_isolated"]}
    if any(v is None for v in k.values()):
        raise RuntimeError("kappa is fixed by P63k (engineering only) before any outcome value: not yet set")
    return k


def field_adapter():
    """The study's FieldAdapter over msefield (fb934f1f10), with the lead's ruled emission and response."""
    import msefield
    return FieldAdapter(msefield.core, D.FIELD)


def lineage(body, rows, cases, thf, T, Tf, m0, am, normals, tag, gen_names, birth_names, sched=None, t_gen=D.T_GEN,
            keep=(), configs=None, field=None, fresh_names=None, fresh_birth=None, fresh_at=(), kappa_override=None,
            scored=True, save_fresh=False):
    """rows: dicts {"packet", "policy", "sigma", "stop", "injured", "field", "medium", "window", "copy"}. field: a
    FieldAdapter (None: every row runs field-free, E2E003's lineage exactly). A row with "copy" true passes on its
    incoming packet, copied before the generation's injury (protected copying). kappa_override: one kappa for every
    window (P63k's reference runs at 0). scored False: no read is computed (P63k). Returns the reads of every generation,
    the rows alive at each, the diagnostics (with each field row's exposures), the states kept, and the fresh successors'
    reads at the generations in fresh_at. save_fresh: the fresh successors' final states are kept too, under kept["x<g>"]
    (output only: nothing else changes)."""
    global _COUPLING
    configs = D.POLICIES if configs is None else configs
    k = len(cases)
    alive = list(range(len(rows)))
    H, W, r = (np.concatenate([np.asarray(row["packet"][x], dtype=float) for row in rows]) for x in range(3))
    A_ = (H.copy(), W.copy(), D.STRENGTH0 * H, D.STRENGTH0 * W, r.copy())
    reads, alive_at, diags, kept, fresh = {}, {}, {}, {}, {}
    union = m0.copy()
    retained = {}                         # row -> its media, for rows that retain the medium
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
        copy_rows = [j for j, i in enumerate(alive) if rows[i].get("copy", False)]
        A_in = tuple(x.copy() for x in A_) if copy_rows else None          # protected copying: the incoming packet
        inj = None
        if sched is not None:
            union = union | mg
            hit = np.repeat(np.array([bool(rows[i]["injured"]) for i in alive]), k)
            M = mg[idx] & hit[:, None, None]
            before = A_
            A_ = injure(A_, M)
            inj = injury_ok(before, A_, M) & (M.sum((-2, -1)) == np.where(hit, D.SIZE * D.SIZE, 0))
        _COUPLING = coupling_for(field, rows, alive, k, retained, kappa_override)
        coupling = _COUPLING
        try:
            V, E, A_, B_, dg = generation(body, groups_of([rows[i]["policy"] for i in alive], k, configs), cases, V, E, A_,
                                          B_, P, mg[idx], thf[idx], tag, gen_names(g), t_gen)
        finally:
            _COUPLING = None
        diags[g] = {key: dg[key].reshape(len(alive), k) for key in DIAG}
        diags[g]["cue_dis_birth"] = cue_dis
        if inj is not None:
            diags[g]["injury_ok"] = inj.reshape(len(alive), k)
        if coupling is not None:
            diags[g].update({key: v.reshape(len(alive), k) for key, v in coupling.summary(t_gen).items()})
        if scored:
            Tb, Tfb = T[idx], Tf[:, idx]
            so = score(V, A_[4], Tb, Tfb, mg[idx])
            su = score(V, A_[4], Tb, Tfb, union[idx])
            reads[g] = {key: so[e].reshape(len(alive), k) for key, e in READS.items()}
            reads[g].update({key: su[e].reshape(len(alive), k) for key, e in UNION_READS.items()})
        alive_at[g] = list(alive)
        if g in keep:
            kept[g] = {"rows": list(alive), "V": V.copy(), "r": A_[4].copy(), "H": A_[0].astype(np.int8),
                       "W": A_[1].astype(np.int8)}
        if copy_rows:                                                        # pass on the copy, not the working record
            sel = np.concatenate([np.arange(j * k, (j + 1) * k) for j in copy_rows])
            A_ = tuple(np.where(np.isin(np.arange(len(x)), sel)[:, None, None], xi, x) for x, xi in zip(A_, A_in))
        A_, _ = SRS.handoff(A_, None)
        if g in fresh_at:
            fresh[g], fst = fresh_test(body, A_, cases, alive, k, thf, T, Tf, union, normals, am, tag, fresh_names(g),
                                       fresh_birth(g), t_gen, configs)
            if save_fresh:
                kept[f"x{g}"] = dict(fst, rows=list(alive))
    return reads, alive_at, diags, kept, fresh


def coupling_for(adapter, rows, alive, k, retained, kappa_override=None):
    """The generation's coupling: None when no alive row meets the field; else one Medium per row (shared: the eight
    sheets in rectangle(2, 4); isolated: the eight sheets in disconnected blocks), a retaining row's medium carried over
    from its last generation. Each row's kappa is its window's."""
    if adapter is None or all(rows[i]["field"] == "none" for i in alive):
        return None
    kap = kappas(kappa_override)
    groups = []
    for j, i in enumerate(alive):
        row = rows[i]
        if row["field"] == "none":
            continue
        old = retained.get(i) if row["medium"] == "retain" else None
        med = old if old is not None else (adapter.medium(k) if row["field"] == "shared" else adapter.medium_isolated())
        if row["medium"] == "retain":
            retained[i] = med
        groups.append({"branches": np.arange(j * k, (j + 1) * k), "window": D.WINDOWS[row["window"]], "medium": med,
                       "kappa": kap[row.get("kappa_key") or row["window"]], "row": i})
    return Coupling(adapter, groups, len(alive) * k)


def fresh_test(body, A_out, cases, alive, k, thf, T, Tf, union, normals, am, tag, names, birth_names, t_gen, configs):
    """A field-free newborn reading each alive row's outgoing record A_out for one generation (the vote, no injury, no
    medium), under the fresh names; scored on the union of the injured patches and whole-sheet. Returns its reads and its
    final state (V, r, H and W after the generation's last update), the latter saved only where asked."""
    idx = np.tile(np.arange(k), len(alive))
    V = birth(tag, cases, *birth_names, side=D.SIDE)[idx].copy()
    E = V.copy()
    A_ = tuple(x.copy() for x in A_out)
    B_ = tuple(x.copy() for x in A_)
    P = {"am": am[idx], "aval": birth_cue(A_[4], normals, 0.0)}
    V, E, A_, B_, _dg = generation(body, groups_of([D.FRESH["policy"]] * len(alive), k, configs), cases, V, E, A_, B_, P,
                                   union[idx], thf[idx], tag, names, t_gen)
    su = score(V, A_[4], T[idx], Tf[:, idx], union[idx])
    out = {key: su[e].reshape(len(alive), k) for key, e in UNION_READS.items()}
    out.update({"a_v": su["a_v"].reshape(len(alive), k), "q_v": su["q_v"].reshape(len(alive), k),
                "a_r": su["a_r"].reshape(len(alive), k), "q_r": su["q_r"].reshape(len(alive), k)})
    return out, {"V": V.copy(), "r": A_[4].copy(), "H": A_[0].astype(np.int8), "W": A_[1].astype(np.int8)}


def packets(raw, meta, cases, V0, ema0, R0, T, lineages):
    """The task's distinct rows and, for each lineage label, the row it runs on; the alias table; the packets' sources.
    As e2e003.sim.packets, with the row's field, medium, window and copying in its identity: rows that differ only in how
    they meet the field, or in protected copying, run separately."""
    rows, labels, aliases, sources, sig = [], {}, {}, {}, {}
    for ln in lineages:
        pk, src = packet_of(ln["packet"], raw, meta, cases, V0, ema0, R0, T)
        if pk is None:
            continue
        pk = tuple(np.asarray(x, dtype=float) for x in pk)
        reads_cue = ln["policy"] != "vote"
        copy = ln["label"] in D.PROTECTED_COPY
        kk = ln.get("kappa_key")
        h = (E2._digest(*pk), ln["policy"], bool(ln["injured"]), ln["sigma"] if reads_cue else "-", ln["field"],
             ln["medium"], ln["window"], copy, kk)
        if h in sig:
            i = sig[h]
            rows[i]["stop"] = max(rows[i]["stop"], ln["stop"])
            aliases.setdefault(rows[i]["labels"][0], []).append(ln["label"])
            rows[i]["labels"].append(ln["label"])
        else:
            sig[h] = len(rows)
            rows.append({"labels": [ln["label"]], "packet": pk, "policy": ln["policy"], "sigma": ln["sigma"],
                         "stop": ln["stop"], "injured": bool(ln["injured"]), "field": ln["field"], "medium": ln["medium"],
                         "window": ln["window"], "copy": copy, "kappa_key": kk, "source": src})
        labels[ln["label"]] = sig[h]
        sources[ln["label"]] = src
    return rows, labels, aliases, sources
