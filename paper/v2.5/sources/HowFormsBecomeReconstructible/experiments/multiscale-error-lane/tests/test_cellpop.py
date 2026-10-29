"""cellpop's tests: python -m pytest tests/test_cellpop.py"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cellpop import core as C  # noqa: E402
from cellpop.loop import Branches, evolve  # noqa: E402
from dl001 import design as DL1  # noqa: E402
from dl001 import sim as S1  # noqa: E402
from dl003 import design as D3  # noqa: E402
from dl003 import sim as S3  # noqa: E402
from lr001.sim import edges_from  # noqa: E402
from lr004 import design as L4D  # noqa: E402
from lr004 import sim as L4S  # noqa: E402
from msegrid.core import bonds  # noqa: E402

BLOCK = 900786
N = 32


def full(x):
    return np.ones(x.shape, bool)


def test_full_sheet_body_equals_dl001():
    cases, V0, ema0, R0, th, T = S1.prepare("S4", N, BLOCK, "engineering")
    k = len(cases)
    V, E, r = np.tile(V0, (2, 1, 1)), np.tile(ema0, (2, 1, 1)), np.tile(R0, (2, 1, 1))
    gains = np.repeat([0.0, 0.2], k)
    o = S1.run("li4", V.copy(), E.copy(), r, gains, th, np.tile(T, (2, 1, 1)), cases, 0.1, 300, {300})
    idx = np.tile(np.arange(k), 2)
    st = {"occ": full(V), "V": V.copy(), "E": E.copy()}
    br = Branches(gain=np.broadcast_to(gains[:, None, None], V.shape).copy(), read=r)
    out, _ = evolve("li4", st, br, cases, th[idx], DL1.TAG, ("future",), 300)
    assert np.array_equal(out["V"], o["final"])


def test_full_sheet_record_equals_lr004():
    cases, V0, ema0, R0, th, T = L4S.prepare("S4", BLOCK, "engineering")
    k = len(cases)
    conds = (L4D.Cond(0.003, "record+parity"), L4D.Cond(0.003, "body"))
    o = L4S.run("li4", conds, cases, V0, ema0, R0, th, T, 1.0, {300}, tag=L4D.TAG, window=300)
    idx = np.tile(np.arange(k), 2)
    H0, W0 = edges_from(bonds(R0, True))
    st = {"occ": full(V0[idx]), "V": V0[idx].copy(), "E": ema0[idx].copy(), "r": R0[idx].copy(),
          "H": H0[idx].copy(), "W": W0[idx].copy(), "Hb": L4D.STRENGTH0 * H0[idx], "Wb": L4D.STRENGTH0 * W0[idx]}
    first = np.repeat([True, False], k)[:, None, None]
    br = Branches(gain=np.full(V0[idx].shape, L4D.GAIN), learn_record=first, learn_body=~first, parity=first)
    out, _ = evolve("li4", st, br, cases, (th * 1.0)[idx], L4D.TAG, ("future",), 300, rate=0.003, eps=L4D.EPS,
                    kr=L4D.KR, sigma_r=L4D.SIGMA_R, kc=L4D.KC, eta=L4D.ETA, sigma=L4D.SIGMA)
    for key in ("V", "r", "H", "W"):
        assert np.array_equal(out[key], o[key])


def test_prescribed_front_equals_dl003():
    cases, V0, ema0, R0, th, T = S3.prepare(BLOCK, "engineering")
    arms = (D3.Arm("perp/f25", "perp", 25), D3.Arm("par/f50", "par", 50), D3.Arm("full", "full"))
    o = S3.run("li4", arms, cases, V0, ema0, R0, th, T, 0.0, "B", {300}, window=300)
    V, E, gain, fdist, every, masks, dist = S3.branches(arms, cases, V0, ema0, "B")
    k = len(cases)
    idx = np.tile(np.arange(k), len(arms))
    nbv = np.tile(S3.newborn(cases), (len(arms), 1, 1))
    st = {"occ": (fdist < 0) | (fdist == 0), "V": V, "E": E}
    br = Branches(gain=gain, read=np.tile(R0, (len(arms), 1, 1)), fdist=fdist, every=every, newborn=nbv)
    out, _ = evolve("li4", st, br, cases, (th * 0.0)[idx], D3.TAG, ("future", "B"), 300)
    assert np.array_equal(out["V"], o["final"]) and np.array_equal(out["E"], o["final_ema"])


def toy(side=8, n=1):
    occ = np.zeros((n, side, side), bool)
    V = np.zeros((n, side, side))
    return {"occ": occ, "V": V, "E": V.copy(), "r": V.copy(), "H": V.copy(), "W": V.copy(), "Hb": V.copy(), "Wb": V.copy()}


def test_division_inheritance_and_contacts():
    st = toy()
    st["occ"][0, 3, 3] = st["occ"][0, 3, 4] = True
    st["V"][0, 3, 3], st["E"][0, 3, 3], st["r"][0, 3, 3] = 0.7, 0.5, -1.1
    st["V"][0, 3, 4], st["r"][0, 3, 4] = -0.4, 0.9
    st["H"][0, 3, 3], st["Hb"][0, 3, 3] = -1.0, -0.8                   # the contact (3,3)-(3,4)
    u = np.ones((1, 8, 8))
    u[0, 3, 3] = 0.0                                                   # only (3,3) divides
    w = np.zeros((1, 8, 8))                                            # its first empty neighbour in order: up
    one = np.ones((1, 1, 1), bool)
    out, born = C.divide(st, np.full((1, 1, 1), 0.5), u, w, one)
    assert born[0, 2, 3] and born.sum() == 1 and out["occ"][0, 2, 3]
    assert (out["V"][0, 2, 3], out["E"][0, 2, 3], out["r"][0, 2, 3]) == (0.7, 0.5, -1.1)
    assert out["W"][0, 2, 3] == 0 and out["Wb"][0, 2, 3] == 0          # the daughter-parent contact is untrained
    assert out["H"][0, 3, 3] == -1.0 and out["Hb"][0, 3, 3] == -0.8    # other contacts keep their training
    nb = np.full((1, 8, 8), 0.05)
    out2, born2 = C.divide(st, np.full((1, 1, 1), 0.5), u, w, ~one, nb)
    assert out2["V"][0, 2, 3] == 0.05 and out2["E"][0, 2, 3] == 0.05 and out2["r"][0, 2, 3] == 0.0


def test_death_swap_and_bookkeeping():
    rng = np.random.default_rng(1)
    n, side = 3, 16
    st = toy(side, n)
    st["occ"][:] = rng.random((n, side, side)) < 0.7
    for f in ("V", "E", "r"):
        st[f] = np.where(st["occ"], rng.standard_normal((n, side, side)), 0.0)
    ch, cw = C.contacts(st["occ"])
    for b, c in (("H", ch), ("W", cw)):
        st[b] = np.where(c, np.sign(rng.standard_normal((n, side, side))), 0.0)
        st[b + "b"] = 0.8 * st[b]
    prot = np.zeros_like(st["occ"])
    prot[:, 0, :] = True
    prot &= st["occ"]                                                  # the occupied cells of row 0 are protected
    V0 = st["V"].copy()
    for t in range(1, 60):
        u = rng.random((4, n, side, side))
        st, dead = C.die(st, np.full((n, 1, 1), 0.02), u[0], prot)
        st, moved = C.swap(st, np.full((n, 1, 1), 0.05), u[1], t, prot)
        st, born = C.divide(st, np.full((n, 1, 1), 0.05), u[2], u[3], np.ones((n, 1, 1), bool))
        assert not (dead & prot).any() and not (moved & prot).any()
        occ = st["occ"]
        for f in ("V", "E", "r"):
            assert (st[f][~occ] == 0).all()
        ch, cw = C.contacts(occ)
        assert (st["H"][~ch] == 0).all() and (st["W"][~cw] == 0).all()
        assert (st["Hb"][~ch] == 0).all() and (st["Wb"][~cw] == 0).all()
        parents = sum(C.at(occ & ~born, d) for d in range(4)) > 0
        assert (parents[born]).all()                                   # every daughter has a parent next to it
    assert st["occ"][prot].all() and (st["V"][prot] == V0[prot]).all()
    a = toy(4, 1)
    a["occ"][:] = True
    a["V"][0] = np.arange(16.0).reshape(4, 4)
    a["H"][:] = a["W"][:] = 1.0
    a["Hb"][:] = a["Wb"][:] = 0.8
    u = np.ones((1, 4, 4))
    u[0, 1, 0] = 0.0                                                   # t = 4: horizontal pairs with even first column
    out, moved = C.swap(a, np.full((1, 1, 1), 0.5), u, 4, np.zeros((1, 4, 4), bool))
    assert out["V"][0, 1, 0] == 5.0 and out["V"][0, 1, 1] == 4.0 and moved.sum() == 2
    assert out["H"][0, 1, 0] == 0 and out["W"][0, 0, 0] == 0 and out["H"][0, 1, 3] == 0 and out["H"][0, 2, 2] == 1.0


def test_determinism_and_serial_equals_parallel():
    cases, V0, ema0, R0, th, T = S3.prepare(BLOCK, "engineering")
    k = len(cases)

    def go(sel):
        cs = [cases[j] for j in sel]
        occ = np.zeros((len(cs), N, N), bool)
        occ[:, 14:18, :] = True
        st = {"occ": occ, "V": np.where(occ, V0[sel], 0.0), "E": np.where(occ, ema0[sel], 0.0)}
        br = Branches(gain=np.zeros(occ.shape), read=R0[sel], p_div=np.full((len(cs), 1, 1), 0.04),
                      inherit=np.ones((len(cs), 1, 1), bool), newborn=np.zeros(occ.shape),
                      p_die=np.full((len(cs), 1, 1), 0.002), p_swap=np.full((len(cs), 1, 1), 0.002),
                      protected=np.broadcast_to(occ, occ.shape).copy())
        return evolve("li4", st, br, cs, th[sel], "mse-sc001-test", ("future",), 250)[0]
    a, b = go(list(range(k))), go(list(range(k)))
    lo, hi = go(list(range(k // 2))), go(list(range(k // 2, k)))
    for f in ("occ", "V", "E"):
        assert np.array_equal(a[f], b[f])
        assert np.array_equal(a[f], np.concatenate([lo[f], hi[f]]))
    assert a["occ"].mean() > 0.5                                       # the sheet grew


def test_diffusion_decay_length_and_walls():
    kappa, decay = 0.2, 0.02
    occ = np.ones((1, 8, 64), bool)
    x = np.zeros(occ.shape)
    src = np.zeros(occ.shape, bool)
    src[..., 0] = True
    for _ in range(6000):
        x = C.diffuse(x, occ, kappa, decay, 0.0)
        x = np.where(src, 1.0, x)
    lam = C.decay_length(kappa, decay)
    ratio = x[0, 0, 6] / x[0, 0, 5]
    assert abs(ratio - np.exp(-1.0 / lam)) < 1e-3
    occ[..., 20] = occ[..., 40] = False                               # empty columns enclose 21-39 on the ring
    x = np.zeros(occ.shape)
    for _ in range(3000):
        x = np.where(src, 1.0, C.diffuse(x, occ, kappa, decay, 0.0))
    assert (x[..., 20] == 0).all() and (x[..., 21:40] == 0).all() and (x[..., 19] > 0).all()


def test_scheduled_fill():
    st = toy()
    st["occ"][0, 3, 3] = True
    st["V"][0, 3, 3], st["E"][0, 3, 3], st["r"][0, 3, 3] = 0.6, 0.4, 1.2
    due = np.zeros((1, 8, 8), bool)
    due[0, 3, 4] = due[0, 5, 5] = True
    pdir = np.full((1, 8, 8), C.LEFT, np.int8)                       # each site's parent is on its left
    one = np.ones((1, 1, 1), bool)
    out, born = C.fill(st, due, pdir, one)
    assert born[0, 3, 4] and not born[0, 5, 5] and born.sum() == 1      # (5,5) has no parent, so it stays empty
    assert (out["V"][0, 3, 4], out["E"][0, 3, 4], out["r"][0, 3, 4]) == (0.6, 0.4, 1.2)
    assert out["H"][0, 3, 3] == 0 and out["occ"][0, 3, 4]
    out2, _ = C.fill(st, due, pdir, ~one, np.full((1, 8, 8), -0.1))
    assert out2["V"][0, 3, 4] == -0.1 and out2["r"][0, 3, 4] == 0.0
