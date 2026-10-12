"""Synthetic, no-dynamics qualification of the exploratory saved-field review."""
import ast
from pathlib import Path

import numpy as np
import pytest

from l20_extension1 import serial_compat_review as review


@pytest.mark.parametrize('role', (0, 1))
def test_shape_translation_and_scale(role):
    for dy, dx in ((0, 0), (3, 5), (8, 8)):
        value = 2*np.roll(review.TARGETS[role], (dy, dx), (0, 1)) + .7
        assert review.shape(value, role) == pytest.approx(1)
        assert review.shape(value, 1-role) == pytest.approx(0)


def test_zero_field():
    x = np.zeros((16, 16))
    assert review.shape(x, 0) == review.canonical(x, 1) == review.self_overlap(x, (0, 1)) == 0
    assert review.preference(x, 1) == 0


def test_record_decode():
    value = np.arange(256, dtype='<f8').reshape(16, 16)
    np.testing.assert_array_equal(review.decode(np.frombuffer(value.tobytes(), np.uint8)), value)
    with pytest.raises(ValueError):
        review.decode(np.zeros(256))
    with pytest.raises(ValueError):
        review.field(np.zeros((8, 32)))


@pytest.mark.parametrize('role', (0, 1))
def test_original_threshold(role):
    assert review.preference(.2 * review.TARGETS[role], role) == 0
    assert review.preference(.20001 * review.TARGETS[role], role) == .5
    assert review.preference(-.3 * review.TARGETS[role], role) == -.5


@pytest.mark.parametrize('role', (0, 1))
def test_exact_preference_identity(role):
    rng = np.random.default_rng(45)
    for _ in range(20):
        q, z = rng.normal(0, .3, (2, 16, 16))
        parts = review.preference_parts(q, z, role)
        assert parts['net_units']/256 == review.preference(q, role)-review.preference(z, role)
        active = np.abs(q) > .2
        matches = [np.mean(((q > 0) == (t > 0)) & active) for t in review.TARGETS]
        assert review.preference(q, role) == matches[role]-matches[1-role]


def test_preference_components_not_all_threshold():
    q, z = .3*review.TARGETS[1], -.3*review.TARGETS[1]
    p = review.preference_parts(q, z, 1)
    assert p['both_active_sign_net_units'] == 256 and p['net_units'] == 256
    assert p['compatible_only_active_net_units'] == p['zero_only_active_net_units'] == 0
    p = review.preference_parts(q, np.zeros_like(z), 1)
    assert p['compatible_only_active_net_units'] == p['net_units'] == 128


def test_imperfect_record_not_ideal_invariant():
    x = review.TARGETS[1].copy()
    assert review.self_overlap(x, (3, 8)) == 1
    x[0, 0] += 5
    assert review.self_overlap(x, (3, 8)) < 1


def test_sibling_counts_preserve_zeros():
    x = np.ones((16, 4, 2))
    x[0, 0] = [-1, -2]
    x[0, 1] = [-1, 0]
    s = review.sibling_signs(x)
    assert (s['both_negative'], s['exactly_one_negative'], s['neither_negative']) == (1, 1, 62)
    assert review.signs(x)['zero'] == 1
    with pytest.raises(ValueError):
        review.sibling_signs(x[:8])


def test_block_not_pseudoreplicate_bootstrap():
    x = np.broadcast_to(np.arange(16.)[:, None, None], (16, 4, 2))
    s = review.block_stats(x)
    draws = np.random.default_rng(review.SEED).integers(0, 16, (10000, 16))
    assert s['mean'] == 7.5
    assert s['original_block_bootstrap_95'] == np.quantile(draws.mean(axis=1), [.025, .975]).tolist()
    assert s['leave_one_block_out_mean_range'] == [7, 8]
    with pytest.raises(ValueError):
        review.block_stats(x[:8])


def test_describe_retains_negative_tail():
    s = review.describe([-1, 0, 1, 1])
    assert s['mean'] == .25 and s['negative'] == 1 and s['zero'] == 1 and s['count'] == 4
    with pytest.raises(ValueError):
        review.describe([1, np.nan])


def test_no_simulator_imports():
    tree = ast.parse(Path(review.__file__).read_text())
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(a.name.split('.')[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.append(node.module.split('.')[0])
    assert set(modules) <= {'__future__', 'argparse', 'datetime', 'hashlib', 'json', 'os', 'pathlib', 'time', 'numpy'}


def test_output_exclusive(tmp_path):
    dest = tmp_path/'receipt.json'
    review.write_json(dest, {'all_cases_retained': True})
    with pytest.raises(FileExistsError):
        review.write_json(dest, {'overwrite': True})
