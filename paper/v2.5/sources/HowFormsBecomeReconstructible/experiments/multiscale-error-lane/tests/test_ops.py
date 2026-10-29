"""Batched operators against the single-field design fixtures, and exact alias classes."""
from itertools import product
from pathlib import Path
import sys

import numpy as np

LANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LANE))

import operators as fixture  # noqa: E402  the design-record fixtures in ../operators.py
from mse.engine import Channel, _permute  # noqa: E402
from mse.native import LEVELS  # noqa: E402
from mse.ops import Op, bands, canonical, project  # noqa: E402

X = np.random.default_rng(20261024).normal(size=(5, 16, 16)) + 0.4


def test_projections_match_fixture():
    for level in LEVELS:
        for x in X:
            np.testing.assert_allclose(project(x, level), fixture.spatial_operator(x, level),
                                       atol=1e-15, rtol=0)
        for x in X:
            np.testing.assert_allclose(Op(level, (1, 1))(x), fixture.shifted_operator(x, level),
                                       atol=1e-15, rtol=0)


def test_bands_match_fixture_and_sum():
    for x in X:
        ours, theirs = bands(x), fixture.error_bands(x)
        for k in ours:
            np.testing.assert_allclose(ours[k], theirs[k], atol=1e-15, rtol=0)
    np.testing.assert_allclose(sum(bands(X).values()), X, atol=1e-12, rtol=0)


def test_nine_aligned_pairs_are_three_exact_maps():
    outputs = {}
    for s, a in product(LEVELS, repeat=2):
        outputs[(s, a)] = Channel(Op(s), Op(a))(X)
        np.testing.assert_allclose(outputs[(s, a)], Op(a)(Op(s)(X)), atol=1e-14, rtol=0)
    classes = []
    for key, out in outputs.items():
        for c in classes:
            if np.array_equal(out, outputs[c[0]]):
                c.append(key)
                break
        else:
            classes.append([key])
    assert len(classes) == 3
    assert canonical(Op("region", (1, 1)), Op("site")) is None


def test_displaced_action_does_not_commute_and_half_shift_annihilates():
    for level in ("region", "sheet"):
        aligned = Channel(Op(level), Op(level))(X)
        displaced = Channel(Op(level), Op(level, (1, 1)))(X)
        assert np.abs(aligned - displaced).max() > 1e-6
    np.testing.assert_allclose(Channel(Op("sheet"), Op("sheet", (4, 4)))(X), 0, atol=1e-12)


def test_permutation_moves_whole_messages():
    perm = tuple(np.random.default_rng(1).permutation(16))
    s = project(X, "region")
    moved = _permute(s, "region", np.asarray(perm))
    assert sorted(np.unique(moved[0]).round(12)) == sorted(np.unique(s[0]).round(12))
    assert np.array_equal(project(moved, "region"), moved)


def test_sign_decision_separates_sensing_from_action():
    """With a nonlinear decision the aligned pairs are no longer aliases."""
    a = Channel(Op("site"), Op("region"), decision="sign")(X)
    b = Channel(Op("region"), Op("site"), decision="sign")(X)
    assert np.abs(a - b).max() > 0.1
