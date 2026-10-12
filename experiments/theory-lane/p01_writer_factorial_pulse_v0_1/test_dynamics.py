"""Independent small-system and intervention checks before native branching."""
import numpy as np
import pytest
import json
from pathlib import Path

import dynamics as d


def test_magnitude_control_preserves_original_weights_with_explicit_zero_rule():
    original = np.array([2., -3., 4., -5., 0., 1e-310])
    tolerance = np.array([-7., 8., 0., 0., 0., -1e-320])
    control, completed = d.restore_magnitudes(original, tolerance)
    np.testing.assert_array_equal(control, np.array([-2., 3., 4., -5., 0., -1e-310]))
    np.testing.assert_array_equal(completed, [False, False, True, True, False, False])


def test_invalid_tolerance_only_edge_is_rejected():
    with pytest.raises(AssertionError):
        d.restore_magnitudes(np.array([0.]), np.array([1.]))


def test_single_pulse_schedule_has_exactly_one_tolerance_write():
    cfg = json.loads((Path(__file__).parent/'config.json').read_text())
    pulse = cfg['simulated_writers'].index('single_tolerance_rewrite')
    schedules = [d.policies_at(g, cfg)[pulse] for g in range(3, 33)]
    assert schedules == ['tolerance_rewrite']+['exact_rewrite']*29
    assert d.policies_at(3, cfg) == ['exact_rewrite', 'magnitude_restored', 'tolerance_rewrite']
    assert d.policies_at(4, cfg) == ['exact_rewrite', 'magnitude_restored', 'exact_rewrite']
    with pytest.raises(ValueError):
        d.policies_at(2, cfg)


@pytest.mark.parametrize('amplification', [True, False])
def test_signed_normalized_step_against_explicit_dense_edges(amplification):
    random = np.random.default_rng(5104)
    side = 4
    weights = random.normal(size=(2, side, side))
    weights[:, 0, 0] = weights[0, 0, -1] = weights[1, -1, 0] = 0.
    matrix = np.zeros((side*side, side*side))
    for row in range(side):
        for col in range(side):
            a = row*side+col
            for edge, (r, c) in enumerate(((row, (col+1) % side), ((row+1) % side, col))):
                b = r*side+c
                matrix[a, b] += weights[edge, row, col]
                matrix[b, a] += weights[edge, row, col]
    value = random.normal(size=(side, side))
    noise = random.normal(size=(side, side))
    denominator = abs(matrix).sum(axis=1)
    expected_local = np.divide(matrix @ value.ravel(), denominator,
        out=np.zeros(side*side), where=denominator > 0).reshape(side, side)
    cfg = dict(dt=.2, noise=.02)
    drift = (value-value**3 if amplification else -value**3)+2*(expected_local-value)
    expected = np.clip(value+.2*drift+.02*noise, -2., 2.)
    got = d.step(value, weights, d.incident(abs(weights)), noise, cfg, amplification)
    np.testing.assert_allclose(got, expected, rtol=0, atol=2e-15)


def test_sign_control_changes_signs_preserves_magnitudes_and_support():
    # Adjacent cells have agreeing weak contrast and disagreeing common response.
    difference = np.full((16, 16), .5)
    common = np.full((16, 16), .2)
    difference[0, 1] = 1e-5
    common[0, 1] = -.2
    x = np.stack((common+difference, common-difference))
    body = np.broadcast_to(np.arctanh(x)/3, (3, 4, 4, 2, 16, 16)).copy()
    masks = np.zeros((4, 4, 16, 16), dtype=bool)
    masks[:, :, 5, 5] = True
    parts, _ = d.writer_components(body, masks, 3., 1e-4)
    old, tol, control = (parts[n] for n in ('exact_rewrite', 'tolerance_rewrite', 'sign_restored'))
    assert old[0, 0, 0, 0, 0, 0] > 0 and tol[0, 0, 0, 0, 0, 0] < 0
    assert control[0, 0, 0, 0, 0, 0] > 0
    np.testing.assert_array_equal(abs(control), abs(tol))
    np.testing.assert_array_equal(control != 0, tol != 0)
    assert np.all(control[..., 0, 5, 5] == 0)


def test_zero_and_subnormal_edges_do_not_change_control_support():
    body = np.zeros((3, 4, 4, 2, 16, 16))
    body[..., 0, 0, 0] = 1e-150
    body[..., 0, 0, 1] = 1e-160
    parts, _ = d.writer_components(body, np.zeros((4, 4, 16, 16), bool), 3., 1e-4)
    np.testing.assert_array_equal(abs(parts['sign_restored']), abs(parts['tolerance_rewrite']))
    np.testing.assert_array_equal(parts['sign_restored'] != 0, parts['tolerance_rewrite'] != 0)
    for value in parts.values():
        np.testing.assert_array_equal(d.decode(d.encode(value)), value)


def test_damage_excludes_ports_and_pairs_founders():
    masks = d.damage_masks(34000, 'E022_renewal_g4', 4)
    assert not (masks & d.PORTS.any(axis=0)).any()
    assert (masks[:, :, 1].sum(axis=(-1, -2)) == 24).all()
    assert (masks[:, :, 2].sum(axis=(-1, -2)) == 9).all()
    np.testing.assert_array_equal(masks[0], masks[1])
    np.testing.assert_array_equal(masks[2], masks[3])


def test_both_cue_scoring_is_strict_and_separate_from_writer():
    values = np.empty((3, 4, 4, 2, 3, 2))
    desired = d.RULES[None, :, None, None, None]*d.CUES[None, None, None, :, None]
    values[..., 0] = desired*.5
    values[..., 1] = -desired*.5
    values[0, 0, 0, 1, 1, 0] = -.25
    scores = d.score(values, .25)
    assert not scores['both_pass'][0, 0, 0, 1]
    assert scores['both_pass'].sum() == 3*4*4*3-1
