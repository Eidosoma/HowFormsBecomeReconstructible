"""E2E006's unit tests (engineering records only: AR006's debug block 900948 and P57's 900917, packets only; short
generations of 300 updates; no outcome value is read)."""
import inspect
import sys
from pathlib import Path

import numpy as np
import pytest

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

from ar001 import design as A  # noqa: E402
from ar001 import sim as A1S  # noqa: E402
from ar006 import sim as S6  # noqa: E402
from e2e002 import sim as E2  # noqa: E402
from e2e003 import sim as E3  # noqa: E402
from e2e006 import design as D  # noqa: E402
from e2e006 import sim  # noqa: E402
from e2e006 import worker as W  # noqa: E402
from gc001 import sim as GCS  # noqa: E402
from lr005 import sim as L5S  # noqa: E402
import msefield  # noqa: E402
from msefield import core as MF  # noqa: E402
from sr001 import sim as SRS  # noqa: E402

TG = 300                                          # a short generation: the windows' late half never opens


def _task(body="dw", unit="F0_t1", block=900948, source="ar006/debug"):
    raw, meta, _rf = W.load(source, body, unit, block)
    pattern, theta = A.parse_unit(unit)
    cases, V0, ema0, R0, th, T = A1S.prepare(pattern, block, D.SOURCES[source]["purpose"])
    Tf = SRS.foreign(T, pattern, cases)
    _pk, m0 = sim.post_damage("memory@0", cases, V0, ema0, R0, T, meta["tag"])
    am, normals = L5S.anchor_mask(cases, meta["tag"]), GCS.unit_normals(cases, meta["tag"])
    return dict(raw=raw, meta=meta, cases=cases, V0=V0, ema0=ema0, R0=R0, thf=th * theta, T=T, Tf=Tf, m0=m0, am=am,
                normals=normals, body=body)


def _rows(t, labels, stop=2):
    lins = [dict(x, stop=stop) for x in D.ALL if x["label"] in labels]
    rows, lab, _al, _src = sim.packets(t["raw"], t["meta"], t["cases"], t["V0"], t["ema0"], t["R0"], t["T"], lins)
    return rows, lab


def _run(t, rows, field, sched=True, kappa=0.5, T=None, gens=2, scored=True):
    sch = sim.schedule(t["cases"], t["m0"], D.TAG, gens)[0] if sched else None
    return sim.lineage(t["body"], rows, t["cases"], t["thf"], t["T"] if T is None else T, t["Tf"], t["m0"], t["am"],
                       t["normals"], D.TAG, sim.GEN_NAMES(0), sim.BIRTH_NAMES(0), sched=sch, t_gen=TG, keep=(1, gens),
                       field=field, kappa_override=kappa, scored=scored)


def _same(k1, i1, k2, i2, g):
    """Row i1's kept state in run 1 equals row i2's in run 2 at generation g (V, r, H, W over the row's eight cases)."""
    a, b = k1[g], k2[g]
    j1, j2 = a["rows"].index(i1), b["rows"].index(i2)
    k = a["V"].shape[0] // len(a["rows"])
    return all(np.array_equal(a[x][j1 * k:(j1 + 1) * k], b[x][j2 * k:(j2 + 1) * k]) for x in ("V", "r", "H", "W"))


def test_isolated_blocks_equal_one_sheet_media():
    """The lead's ruling 3: the isolated Medium (eight sheets at non-adjacent cells) is eight disconnected blocks, each
    bit for bit a one-sheet Medium of the same parameters (the field on its block and its exposure, every update)."""
    f = D.FIELD
    iso = MF.Medium(f["isolated_positions"], f["D"], f["gamma"], f["leakage"], dt=f["dt"], m=f["m"], margin=f["margin"])
    one = [MF.Medium([(0, 0)], f["D"], f["gamma"], f["leakage"], dt=f["dt"], m=f["m"], margin=f["margin"])
           for _ in range(8)]
    assert iso.nsub == one[0].nsub and len(iso.blocks) == 8
    rng = np.random.default_rng(6)
    for _ in range(300):
        e = rng.uniform(0.0, 2.0, 8)
        x = iso.step(e)
        y = np.array([one[j].step(e[j:j + 1])[0] for j in range(8)])
        assert np.array_equal(x, y)
        assert all(np.array_equal(iso.c[sl], one[j].c) for j, sl in enumerate(iso.blocks))


def test_field_values_as_ruled():
    f = D.FIELD
    assert (f["D"], f["gamma"], f["leakage"], f["m"], f["margin"]) == (0.25, 0.0625, 1.0, 4, 0)
    assert f["positions"] == msefield.rectangle(2, 4) and f["commit"] == "fb934f1f10"
    assert f["isolated_positions"] == [(0, 2 * j) for j in range(8)]
    med = sim.field_adapter().medium(8)
    assert med.decay_length == 2.0 and med.shape == (8, 16)


def test_routed_generation_two_substitutions():
    src = inspect.getsource(E2.generation)
    assert src.count(sim.DETECT_CALL) == 1 and src.count(sim.BODY_CALL) == 1
    assert sim.generation.__globals__["detect_vt"] is S6.detect
    assert sim._COUPLING is None


def test_adapter_reads_own_state_only():
    """The stress reads the sheet's own record and body (no target, no patch); the response reads the exposure only."""
    ad = sim.field_adapter()
    assert list(inspect.signature(ad.stress).parameters) == ["V", "Vt", "drift", "d", "r"]
    assert list(inspect.signature(ad.respond).parameters) == ["c", "active", "kappa", "gain", "thb", "p"]
    r, Vt = np.ones((2, 3, 3)), np.zeros((2, 3, 3))
    Vt[1] = 0.5
    assert np.array_equal(ad.stress(V=None, Vt=Vt, drift=None, d=None, r=r), np.array([1.0, 0.5]))
    g, _thb, _p = ad.respond(np.full((2, 1, 1), 0.5), np.array([True, False])[:, None, None], np.full((2, 1, 1), 2.0),
                             gain=1.5, thb=0, p=0)
    assert np.array_equal(g[:, 0, 0], np.array([1.5 * 2.0, 1.5]))


def test_kappas_from_p63k():
    """kappa as fixed by P63k (engineering only): kappa x the shared reference's mean exposure = 1 to four significant
    figures, each window's likewise, and the matched isolated row's on the isolated reference."""
    import json
    assert sim.kappas(0.0) == {"full": 0.0, "early": 0.0, "late": 0.0, "isolated": 0.0}
    k = sim.kappas()
    assert k == {"full": D.FIELD["kappa"], "early": D.FIELD["kappa_early"], "late": D.FIELD["kappa_late"],
                 "isolated": D.FIELD["kappa_isolated"]}
    r = json.loads((LANE / "probes" / "results" / "p63k_e2e006_kappa.json").read_text())
    s, i = r["vote/shared@k0"]["mean"], r["vote/isolated@k0"]["mean"]
    assert r["kappa"] == {"kappa": D.FIELD["kappa"], "kappa_early": D.FIELD["kappa_early"],
                          "kappa_late": D.FIELD["kappa_late"]}
    assert float(f"{1 / i['exp_full']:.4g}") == D.FIELD["kappa_isolated"]
    for kap, e in ((k["full"], s["exp_full"]), (k["early"], s["exp_early"]), (k["late"], s["exp_late"]),
                   (k["isolated"], i["exp_full"])):
        assert abs(kap * e - 1) < 5e-4
    assert r["kexp_all_zero"] and r["bridge_all_equal"]


def test_packets_rows_and_copy():
    t = _task("li4", "F0_t0", 900917, "ar006/p57")
    rows, lab, al, _s = sim.packets(t["raw"], t["meta"], t["cases"], t["V0"], t["ema0"], t["R0"], t["T"], D.CORE)
    assert len(rows) == len(D.CORE) and al == {}
    assert [r["copy"] for r in rows] == [x["label"] == "protected" for x in D.CORE]
    ar, alab, aal, _s = sim.packets(t["raw"], t["meta"], t["cases"], t["V0"], t["ema0"], t["R0"], t["T"], D.ALL)
    assert len(ar) == len(D.ALL) and aal == {}                      # the matched isolated row is its own row
    assert ar[alab["vote/isolated-matched"]]["kappa_key"] == "isolated" and ar[alab["vote/isolated"]]["kappa_key"] is None
    assert rows[lab["protected"]]["source"] == "protected" and rows[lab["protected"]]["injured"] is True
    kr, kl, _a, _s = sim.packets(t["raw"], t["meta"], t["cases"], t["V0"], t["ema0"], t["R0"], t["T"], D.KAPPA_ROWS)
    assert sorted(kl) == ["vote/isolated@k0", "vote/shared@k0"] and len(kr) == 2


def test_each_row_takes_its_kappa():
    t = _task()
    rows, lab = _rows(t, ("vote/isolated", "vote/isolated-matched", "vote/shared-early", "vote/shared-late"))
    c = sim.coupling_for(sim.field_adapter(), rows, list(range(len(rows))), 8, {})
    got = {g["row"]: g["kappa"] for g in c.groups}
    assert got == {lab["vote/isolated"]: D.FIELD["kappa"], lab["vote/isolated-matched"]: D.FIELD["kappa_isolated"],
                   lab["vote/shared-early"]: D.FIELD["kappa_early"], lab["vote/shared-late"]: D.FIELD["kappa_late"]}
    assert all(np.array_equal(c.kappa[g["branches"], 0, 0], np.full(8, g["kappa"])) for g in c.groups)


def test_field_free_lineage_is_e2e003s():
    t = _task()
    rows, _lab = _rows(t, ("vote/none", "vtol-every"))
    sch = sim.schedule(t["cases"], t["m0"], D.TAG, 2)[0]
    args = (t["body"], rows, t["cases"], t["thf"], t["T"], t["Tf"], t["m0"], t["am"], t["normals"], D.TAG,
            sim.GEN_NAMES(0), sim.BIRTH_NAMES(0))
    r3, _a3, d3, k3 = E3.lineage(*args, sched=sch, t_gen=TG, keep=(2,))
    r6, _a6, d6, k6, _f6 = sim.lineage(*args, sched=sch, t_gen=TG, keep=(2,), field=None)
    for g in (1, 2):
        assert all(np.array_equal(r3[g][x], r6[g][x]) for x in r3[g])
        assert set(d3[g]) == set(d6[g]) and all(np.array_equal(d3[g][x], d6[g][x]) for x in d3[g])
    assert all(np.array_equal(k3[2][x], k6[2][x]) for x in ("V", "r", "H", "W"))


def test_coupling_identity_windows_and_mixed_call():
    """kappa 0: the coupled tissue is the field-free one bit for bit; a response window outside the generation (the late
    half, at 300 updates) leaves a field row field-free; early = full under one kappa (both open throughout); a field-free
    row in a mixed call equals its solo run; the response changes the shared row; the group changes it again."""
    t = _task()
    labels = ("vote/none", "vote/isolated", "vote/shared", "vote/shared-early", "vote/shared-late")
    rows, lab = _rows(t, labels)
    ad = sim.field_adapter()
    _r0, _a0, _d0, k0, _f0 = _run(t, rows, ad, kappa=0.0)
    _r1, _a1, d1, k1, _f1 = _run(t, rows, ad, kappa=0.5)
    solo = [rows[lab["vote/none"]]]
    _rs, _as, _ds, ks, _fs = _run(t, solo, None, kappa=None)
    nn, iso, sh, ea, la = (lab[x] for x in labels)
    for g in (1, 2):
        assert all(_same(k0, i, k0, nn, g) for i in (iso, sh, ea, la))         # kappa 0: every field row = field-free
        assert _same(k1, la, k1, nn, g) and _same(k1, ea, k1, sh, g)          # the windows
        assert _same(k1, nn, ks, 0, g)                                        # the mixed call
        assert not _same(k1, sh, k1, nn, g) and not _same(k1, sh, k1, iso, g)
        j = _a1[g].index(la)
        assert (d1[g]["kexp"][j] == 0).all() and (d1[g]["kexp"][_a1[g].index(sh)] > 0).all()
        assert (d1[g]["exp_full"][_a1[g].index(nn)] == 0).all()


def test_reset_and_retain():
    """Reset: a new medium (zero) at every birth; retain: the same medium carried across replacement (non-zero at the
    second birth). Their first generations are equal bit for bit; the second differs."""
    t = _task()
    rows, lab = _rows(t, ("vote/shared", "vote/shared-retained"))
    ad = sim.field_adapter()
    retained = {}
    c1 = sim.coupling_for(ad, rows, [0, 1], 8, retained, kappa_override=0.5)
    m_keep = retained[lab["vote/shared-retained"]]
    for g in c1.groups:
        g["medium"].step(np.ones(8))
    c2 = sim.coupling_for(ad, rows, [0, 1], 8, retained, kappa_override=0.5)
    by = {g["row"]: g["medium"] for g in c2.groups}
    assert by[lab["vote/shared-retained"]] is m_keep and by[lab["vote/shared"]] is not c1.groups[0]["medium"]
    j = {g["row"]: g["branches"] for g in c2.groups}
    assert (c2.c[j[lab["vote/shared"]], 0, 0] == 0).all() and (c2.c[j[lab["vote/shared-retained"]], 0, 0] > 0).all()
    _r, al, _d, k, _f = _run(t, rows, ad, kappa=0.5)
    assert _same(k, lab["vote/shared"], k, lab["vote/shared-retained"], 1)
    assert not _same(k, lab["vote/shared"], k, lab["vote/shared-retained"], 2)


def test_protected_copying(monkeypatch):
    """The lead's ruling 4: the protected row passes on its incoming packet (R0 with its bonds), copied before the
    injury, in every generation; the injury hits its working record (the body develops on it); vote/none passes on its
    working record."""
    t = _task()
    rows, lab = _rows(t, ("protected", "vote/none"), stop=3)
    seen = []
    real = sim.SRS.handoff

    def spy(A_, B_):
        seen.append(tuple(x.copy() for x in A_))
        return real(A_, B_)

    monkeypatch.setattr(sim.SRS, "handoff", spy)
    _r, al, _d, k, _f = _run(t, rows, None, kappa=None, gens=3)
    pr, vn = lab["protected"], lab["vote/none"]
    H, W, r = (np.asarray(x, dtype=float) for x in rows[pr]["packet"])
    want = (H, W, D.STRENGTH0 * H, D.STRENGTH0 * W, r)
    assert len(seen) == 3
    for A_ in seen:
        sl = slice(pr * 8, (pr + 1) * 8)
        assert all(np.array_equal(x[sl], y) for x, y in zip(A_, want))
        sv = slice(vn * 8, (vn + 1) * 8)
        assert not np.array_equal(A_[4][sv], np.asarray(rows[vn]["packet"][2], dtype=float))
    assert not np.array_equal(k[1]["r"][pr * 8:(pr + 1) * 8], r)                # the working record was injured


def test_target_never_reaches_the_field_or_the_tissue():
    """The information boundary: another target leaves every state and every exposure unchanged (the scoring reads it,
    nothing else does)."""
    t = _task()
    rows, _lab = _rows(t, ("vote/shared", "vote/isolated", "vtol-every"))
    ad = sim.field_adapter()
    r1, _a1, d1, k1, _f1 = _run(t, rows, ad, kappa=0.5)
    r2, _a2, d2, k2, _f2 = _run(t, rows, ad, kappa=0.5, T=np.roll(t["T"], 7, -1))
    assert not np.array_equal(r1[2]["a_v"], r2[2]["a_v"])                     # the target did reach the scoring
    for g in (1, 2):
        assert all(np.array_equal(k1[g][x], k2[g][x]) for x in ("V", "r", "H", "W"))
        assert all(np.array_equal(d1[g][x], d2[g][x]) for x in ("exp_full", "exp_early", "exp_late", "kexp"))


def test_reader_parts():
    from e2e006 import predict as PR
    ps = PR.parts()
    assert [p for p, _w, _f, _k in ps] == ["H1", "H2", "H3", "H5", "N1", "N2", "N3", "R1", "R2", "R3"]
    assert [k for _p, _w, _f, k in ps] == ["le", "le", "le", "in", "in", "in", "in", "le", "le", "le"]
    assert {p: v[4] for p, v in PR.PARTS.items()} == {"H1": 8, "H2": 8, "H3": 8, "H5": 3, "N1": 8, "N2": 8, "N3": 8,
                                                     "R1": 8, "R2": 8, "R3": 8}
    assert [PR.PARTS[p][3] for p in ("H3", "N3", "R3")] == ["x", "x", "x"]
    assert PR.TH["H1"] == -0.05 and PR.TH["H2"] == -0.04 and PR.TH["H3"] == -0.01 and PR.TH["H5"] == [-0.04, 0.02]
    assert {p: PR.TH[p] for p in ("N1", "N2", "N3", "R1", "R2", "R3")} == {
        "N1": [-0.01, 0.01], "N2": [-0.01, 0.02], "N3": [-0.01, 0.01], "R1": -0.09, "R2": -0.08, "R3": -0.02}
    assert all(PR.registers("in", PR.TH[p], p) for p in ("N1", "N2", "N3"))
    assert all(PR.registers("le", PR.TH[p], p) for p in ("H1", "H2", "H3", "R1", "R2", "R3"))
    assert set(PR.TH) == set(PR.PARTS)                              # every part registered (Amendment 2)
    assert PR.narrowest(-0.0687, 0.0101, [-0.0712, -0.0662], "le") == -0.05 and PR.registers("le", -0.05, "H1")
    assert PR.narrowest(-0.0687, 0.0101, [-0.0712, -0.0662], "ge") == -0.09 and not PR.registers("ge", -0.09)
    assert PR.registers("in", [-0.02, 0.03], "N1") and not PR.registers("in", [-0.04, 0.01], "N1")
    assert PR.registers("le", 0.05, "R1") and not PR.registers("le", 0.06, "R1")
    ids = [r for r, _w, _f in PR.reported()]
    assert len(ids) == len(set(ids))


def test_phase_b_rows_as_ruled():
    """Amendment 2: phase B's eight rows, early and late to g 3, fresh tests after g 8 only, the preflight on 900929;
    the stages already run keep their rows."""
    assert [x["label"] for x in D.CORE] == ["vote/none", "vote/isolated", "vote/shared", "vote/isolated-matched",
                                            "vote/shared-early", "vote/shared-late", "protected", "vtol-every"]
    assert {x["label"]: x["stop"] for x in D.CORE}["vote/shared-early"] == 3 and D.CORE[0]["stop"] == 8
    assert D.STAGE_FRESH_AT == {"preflight": (8,), "development": (8,)} and D.FRESH_AT == (1, 3, 8)
    assert D.STAGES["preflight"] == {"ar006/preflight": (900929,)} and len(D.stage_tasks("development")) == 128
    assert [x["label"] for x in D.lineages("probe")] == ["vote/isolated", "vote/shared", "vote/shared-retained",
                                                         "vote/shared-early", "vote/shared-late"]
    assert [x["label"] for x in D.lineages("probe_x")] == ["vote/isolated-matched", "vote/none"]
    assert D.STAGE_TAG["probe_x"] == D.STAGE_TAG["probe"] == "mse-p63" and len(D.lineages("debug")) == 11
    assert set(D.SAVE_FRESH_STAGES) == {"probe_x", "preflight", "development"}


def test_fresh_saving_is_output_only():
    """The lead's item 8: saving the fresh successors' final states changes no read, state or draw. A short task run
    with saving on equals the same run with saving off in every endpoint and every lineage state; the extra raw arrays
    are exactly the fresh successors' V, r, H, W and rows; and they re-score to the fresh reads bit for bit."""
    lins = [x for x in D.ALL if x["label"] in ("vote/shared", "protected")]
    on = W.task("ar006/debug", "dw", "F0_t1", 900948, "debug", lineages=lins, t_gen=TG, save_fresh=True)
    off = W.task("ar006/debug", "dw", "F0_t1", 900948, "debug", lineages=lins, t_gen=TG, save_fresh=False)
    (e1, s1, m1, _b1), (e0, s0, m0, _b0) = on, off
    assert set(e1) == set(e0) and all(np.array_equal(e1[x], e0[x]) for x in e0)
    assert set(s0) <= set(s1) and all(np.array_equal(s1[x], s0[x]) for x in s0)
    extra = set(s1) - set(s0)
    assert extra == {f"f0/x{g}/{x}" for g in (1, 3) for x in ("V", "r", "H", "W", "rows")}
    t = _task()
    sched = sim.schedule(t["cases"], t["m0"], D.TAG, 3)[0]
    for g in (1, 3):
        rows = list(s1[f"f0/x{g}/rows"])
        idx = np.tile(np.arange(8), len(rows))
        union = t["m0"].copy()
        for h in range(1, g + 1):
            union |= sched[h]
        su = sim.score(s1[f"f0/x{g}/V"], s1[f"f0/x{g}/r"], t["T"][idx], t["Tf"][:, idx], union[idx])
        assert all(np.array_equal(su[src].reshape(len(rows), 8), e1[f"f0/x{g}/{x}"]) for x, src in sim.UNION_READS.items())
        assert all(np.array_equal(su[x].reshape(len(rows), 8), e1[f"f0/x{g}/{x}"]) for x in ("a_v", "q_v", "a_r", "q_r"))
