"""Exercise the automatic reporting pipeline on synthetic paired outcomes."""
import copy
import json

import numpy as np

from analyze import analyze, paired_table
from evidence import ROOT, save_npz
from verify import verify_tables
from run import merge_controls
import pytest


def test_rescues_and_harms_are_counted_separately():
    candidate = np.array([True, True, False, False])
    baseline = np.array([True, False, True, False])
    assert paired_table(candidate, baseline) == dict(both_pass=1, rescued=1, harmed=1, both_fail=1)


def test_automatic_summary_and_independent_verification(tmp_path):
    cfg = copy.deepcopy(json.loads((ROOT/'config.json').read_text()))
    cfg['blocks'] = [34000, 34001]
    for block in cfg['blocks']:
        endpoint = np.zeros((6, 4, 4, 3), dtype=bool)
        endpoint[0] = True
        endpoint[1, :1] = True
        endpoint[2, :2] = True
        endpoint[3, :2] = True
        endpoint[4, :3] = True
        save_npz(tmp_path/f'cases_{block:06d}.npz', dict(block=np.array(block), generations=np.array([3]),
            assay_both_pass=endpoint, assay_min_margin=np.where(endpoint, .6, .1),
            body_both_pass=np.ones((1, 5, 4, 4), bool), body_min_margin=np.full((1, 5, 4, 4), .6),
            newly_substituted_fraction=np.zeros((1, 5, 4, 4)), sign_flip_fraction=np.zeros((1, 5, 4, 4)),
            simulated_magnitude_sign_fallback_fraction=np.zeros((1, 3, 4, 4))))
    result = analyze(tmp_path, cfg)
    assert result['primaries'][0]['mean_block_success_difference'] == .25
    assert result['primaries'][0]['paired_counts'] == dict(both_pass=8, rescued=8, harmed=0, both_fail=16)
    assert result['primaries'][1]['mean_block_success_difference'] == .5
    assert result['factorial'][1]['mean_block_interaction'] == .25
    receipt = verify_tables(tmp_path, cfg)
    assert receipt['terminal_rows'] == 2*6*4*4*3


def test_old_controls_are_merged_by_declared_policy_order():
    new = np.array([1., 4., 5., 0.])
    old = np.array([1., 2., 3., 0.])
    np.testing.assert_array_equal(merge_controls(new, old, 0, True), [1., 2., 3., 4., 5., 0.])
    np.testing.assert_array_equal(merge_controls(new[:3][None], old[:3][None], 1), [[1., 2., 3., 4., 5.]])
    old[0] = -1.
    with pytest.raises(AssertionError):
        merge_controls(new, old, 0, True)
