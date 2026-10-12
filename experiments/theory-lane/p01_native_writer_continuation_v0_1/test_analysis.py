"""Exercise the automatic reporting pipeline on synthetic paired outcomes."""
import copy
import json

import numpy as np

from analyze import analyze, paired_table
from evidence import ROOT, save_npz
from verify import verify_tables


def test_rescues_and_harms_are_counted_separately():
    candidate = np.array([True, True, False, False])
    baseline = np.array([True, False, True, False])
    assert paired_table(candidate, baseline) == dict(both_pass=1, rescued=1, harmed=1, both_fail=1)


def test_automatic_summary_and_independent_verification(tmp_path):
    cfg = copy.deepcopy(json.loads((ROOT/'config.json').read_text()))
    cfg['blocks'] = [34000, 34001]
    for block in cfg['blocks']:
        endpoint = np.zeros((4, 4, 4, 3), dtype=bool)
        endpoint[0] = True
        endpoint[1, :1] = True
        endpoint[2, :2] = True
        save_npz(tmp_path/f'cases_{block:06d}.npz', dict(block=np.array(block), generations=np.array([3]),
            assay_both_pass=endpoint, assay_min_margin=np.where(endpoint, .6, .1),
            body_both_pass=np.ones((1, 3, 4, 4), bool), body_min_margin=np.full((1, 3, 4, 4), .6),
            newly_substituted_fraction=np.zeros((1, 3, 4, 4)), sign_flip_fraction=np.zeros((1, 3, 4, 4))))
    result = analyze(tmp_path, cfg)
    assert result['primary']['mean_block_success_difference'] == .25
    assert result['primary']['paired_counts'] == dict(both_pass=8, rescued=8, harmed=0, both_fail=16)
    receipt = verify_tables(tmp_path, cfg)
    assert receipt['terminal_rows'] == 2*4*4*4*3
