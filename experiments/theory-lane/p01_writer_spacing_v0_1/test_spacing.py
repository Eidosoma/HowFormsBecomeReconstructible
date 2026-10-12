"""Schedule timing, reused-control identity, and automatic reporting checks."""
import copy
import json

import numpy as np
import pytest

import dynamics as d
import run
from analyze import analyze
from evidence import ROOT, save_npz
from schedules import codes, validate, verify_capture_and_measure
from verify import verify_tables

CFG = json.loads((ROOT/'config.json').read_text())


def test_actual_capture_follows_six_event_schedules():
    validate(CFG)
    difference = np.full((16, 16), .5)
    common = np.full((16, 16), .2)
    difference[0, 1] = 1e-5
    common[0, 1] = -.2
    activity = np.stack((common+difference, common-difference))
    body = np.broadcast_to(np.arctanh(activity)/3, (3, 4, 4, 2, 16, 16)).copy()
    masks = np.zeros((4, 4, 16, 16), bool)
    parts, _ = d.writer_components(body, masks, 3., 1e-4)
    assert parts['exact_rewrite'][0, 0, 0, 0, 0, 0] > 0
    assert parts['tolerance_rewrite'][0, 0, 0, 0, 0, 0] < 0
    actual_events = []
    for g in range(3, 33):
        packets, _ = d.capture(body, masks, d.policies_at(g, CFG), CFG['config'], 1e-4)
        weights = d.decode(packets)
        actual_events.append((weights[:, 0, 0, 0, 0, 0] < 0).astype(int))
        if g in (3, 5, 9, 13, 14):
            metrics = verify_capture_and_measure(dict(end=body, masks=masks, outgoing=packets, writer_codes=codes(g, CFG)), g, CFG)
            assert all(a.shape == (3, 4, 4) and np.isfinite(a).all() for a in metrics.values())
    actual = np.array(actual_events)
    assert actual.sum(axis=0).tolist() == [0, 6, 6]
    assert (np.flatnonzero(actual[:, 1])+3).tolist() == [3, 5, 7, 9, 11, 13]
    assert (np.flatnonzero(actual[:, 2])+3).tolist() == [3, 9, 10, 11, 12, 13]
    assert not actual[11:].any()


@pytest.mark.parametrize('replacement', [[3, 5, 7, 9, 11, 12], [3, 5, 7, 9, 13], [3, 5, 7, 9, 11, 13, 14]])
def test_event_count_endpoints_and_recovery_interval_are_binding(replacement):
    cfg = copy.deepcopy(CFG)
    cfg['tolerance_generations']['spaced_tolerance_rewrite'] = replacement
    with pytest.raises(AssertionError):
        validate(cfg)


def test_reused_single_pulse_is_selected_instead_of_sign_control():
    new = np.array([1., 8., 9., 0.])
    prior = np.array([1., 2., 3., 4., 5., 0.])
    np.testing.assert_array_equal(run.merge_controls(new, prior, 0, CFG, True), [1., 2., 5., 8., 9., 0.])
    np.testing.assert_array_equal(run.merge_controls(new[:3][None], prior[:5][None], 1, CFG), [[1., 2., 5., 8., 9.]])
    prior[0] = -1
    with pytest.raises(AssertionError):
        run.merge_controls(new, prior, 0, CFG, True)


def test_prefix_check_includes_first_extra_write_body_but_not_its_packet(monkeypatch):
    expected = dict(masks=np.zeros((4, 4, 16, 16), bool), end=np.ones((3, 4, 4, 2, 16, 16)),
        outgoing=np.zeros((3, 4, 4, 4096), np.uint8), mean_ports=np.ones((3, 4, 4, 2, 2)))
    monkeypatch.setattr(run, 'pilot_arrays', lambda *args: (expected, 'synthetic'))
    raw = {k: v.copy() for k, v in expected.items()}
    raw['outgoing'][1, 0, 0, 0] = 1
    assert run.check_pulse_prefix(raw, 5, 34000, CFG, ROOT, {}) > 0
    with pytest.raises(AssertionError):
        run.check_pulse_prefix(raw, 4, 34000, CFG, ROOT, {})
    raw['end'][1, 0, 0, 0, 0, 0] = 2
    with pytest.raises(AssertionError):
        run.check_pulse_prefix(raw, 5, 34000, CFG, ROOT, {})


@pytest.mark.parametrize('reverse', [False, True])
def test_reporting_and_independent_verification_preserve_both_directions(tmp_path, reverse):
    cfg = copy.deepcopy(CFG)
    cfg['blocks'] = [34000, 34001]
    for block in cfg['blocks']:
        endpoint = np.zeros((6, 4, 4, 3), bool)
        endpoint[0] = True
        endpoint[1, :1] = True
        endpoint[2, :3] = True
        endpoint[3, :3] = True
        endpoint[4, :2] = True
        endpoint[4, 3, 0] = True
        if reverse:
            endpoint[[3, 4]] = endpoint[[4, 3]]
        events = np.array([[int(g in cfg['tolerance_generations'][w]) for w in cfg['writers']] for g in range(3, 33)], np.uint8)
        body = np.ones((30, 5, 4, 4), bool)
        body[11, 3, 0, 0] = False
        save_npz(tmp_path/f'cases_{block:06d}.npz', dict(block=np.array(block), generations=np.arange(3, 33),
            writer_codes=events, assay_both_pass=endpoint, assay_min_margin=np.where(endpoint, .6, .25),
            body_both_pass=body, body_min_margin=np.where(body, .6, .25),
            newly_substituted_fraction=np.zeros((30, 5, 4, 4)), sign_flip_fraction=np.zeros((30, 5, 4, 4)),
            signed_transfer=np.full((30, 5, 4, 4), .05), unsigned_access=np.full((30, 5, 4, 4), .1)))
    result = analyze(tmp_path, cfg)
    assert result['primary']['mean_block_success_difference'] == (-1 if reverse else 1)*3/16
    assert result['primary']['paired_counts']['rescued'] == (2 if reverse else 8)
    assert result['primary']['paired_counts']['harmed'] == (8 if reverse else 2)
    assert result['post_pulse_body'][3]['successes'] == 30
    verification = verify_tables(tmp_path, cfg)
    assert verification['terminal_rows'] == 576 and verification['body_rows'] == 4800
    assert not result['reused_controls_are_new_replicates']
