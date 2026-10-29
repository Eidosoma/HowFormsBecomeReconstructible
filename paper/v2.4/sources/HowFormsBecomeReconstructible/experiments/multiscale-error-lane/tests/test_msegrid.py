"""msegrid at side 16 equals the lane's engine bit for bit; placements sit where declared at every side."""
from dataclasses import replace
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from br001 import design as D1
from br002 import design as D2
from br002 import sim as S2
from mse.assay import Noise, birth, enrol, theta
from mse.native import NATIVE, address
from mse.ops import block_projection
from msegrid import core as G

BLOCK = [900862]


def test_bproj_equals_block_projection():
    x = np.random.default_rng(0).standard_normal((3, 16, 16))
    for s in (1, 2, 4, 8, 16):
        assert np.array_equal(G.bproj(x, s), block_projection(x, s))


def test_stream_chunks_equal_one_draw_and_br002_draws():
    cases = enrol(BLOCK, D2.MESSAGES, D2.PARENTS, "engineering")
    big = S2.draws(cases, "record-noise", updates=2000)
    st = G.Stream(D2.TAG, cases, "record-noise", side=16)
    chunks = np.concatenate([st.take(250) for _ in range(8)])
    assert np.array_equal(big, chunks)
    assert np.array_equal(big, G.draws(D2.TAG, cases, "record-noise", updates=2000, side=16))
    nz = Noise(D2.TAG, cases, "settle")
    st = G.Stream(D2.TAG, cases, "settle", side=16)
    assert np.array_equal(np.stack([nz(t) for t in range(1, 101)]), st.take(100))


def test_birth_and_theta():
    cases = enrol(BLOCK, D2.MESSAGES, D2.PARENTS, "engineering")
    assert np.array_equal(G.birth(D2.TAG, cases, "birth", side=16), birth(D2.TAG, cases, "birth"))
    p = replace(NATIVE, sigma=0.3)
    assert np.array_equal(G.theta(D2.TAG, cases, p, side=16), theta(D2.TAG, cases, p, per_tissue=True))


def test_acquire_equals_br002_prepare():
    for name in (D2.regime("F0", 0.3), D2.regime("BL", 0.1)):
        cases, s0, th, p, conserved, T, Tf = S2.prepare(name, BLOCK, "engineering")
        V, ema, R, th2 = G.acquire(D2.TAG, cases, T, p, 16)
        assert np.array_equal(V, s0.V) and np.array_equal(ema, s0.ema) and np.array_equal(R, s0.R) and np.array_equal(th, th2)


def test_families_at_side_16():
    for k in range(4):
        assert np.array_equal(D1.AMPLITUDE * G.base("F0", k, 16), D1.TEMPLATES["F0"][k])
        assert np.array_equal(G.base("S8", k, 16), G.base("F0", k, 16))
    b = G.base("BLx2", 0, 32, "mse-test", 1)
    assert np.array_equal(b, np.repeat(np.repeat(G.base("BL", 0, 16, "mse-test", 1), 2, 0), 2, 1))
    for f, s in (("BL", 16), ("BL", 32), ("BLx4", 64)):
        x = G.base(f, 1, s, "mse-test", 3)
        assert x.shape == (s, s) and x.sum() == 0


def test_placements_sit_where_declared():
    g = lambda i: np.random.default_rng(i)
    for family, side in (("F0", 16), ("F0", 32), ("F0", 64), ("S8", 32)):
        D = G.domain(family, side)
        for size in (4, 6, 8, 12, 16):
            for place in ("d0", "d1", "d2", "mid", "cross"):
                if place != "cross" and size > D:
                    continue
                d = (D - size) // 2 if place == "mid" else (int(place[1:]) if place != "cross" else None)
                if d is not None and 2 * d + size > D:
                    continue
                for kind in range(4):
                    T = G.base(family, kind, side)
                    for i in range(6):
                        m = G.place_mask(family, kind, side, size, place, g(i))
                        assert m.sum() == size * size
                        assert G.wall_distance(T, m, family, kind) == (-1 if place == "cross" else d), (family, side, size, place)


def test_record_step_matches_bond_gauge():
    rng = np.random.default_rng(2)
    R0 = rng.standard_normal((2, 32, 32))
    r = rng.standard_normal((2, 32, 32))
    s = np.where(R0 >= 0, 1.0, -1.0)
    from mse.native import neighbours
    assert np.array_equal(G.bond_sum(G.bonds(R0, True), r), s * neighbours(s * r))
    assert np.array_equal(G.bond_sum(G.bonds(R0, False), r), neighbours(r))
