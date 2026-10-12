"""Targeted safeguards against join errors and future/test information leakage."""
import copy
import json
from pathlib import Path

import numpy as np
import pytest

from analyze import assemble, design, fit_predict, rate_predict

CFG = json.loads((Path(__file__).parent/'config.json').read_text())


def fixture():
    cfg = copy.deepcopy(CFG)
    cfg.update(blocks=[1, 2], pairings=['paired'], writers=['exact_rewrite'], founders=[0], recipients=[0])
    rows = []
    for b in cfg['blocks']:
        for g in cfg['probe_generations']:
            row = dict(block=b, pairing='paired', source_writer='exact_rewrite', founder=0,
                       recipient=0, generation=g, terminal_pass=b % 2)
            row.update({n: float(b+g) for n in cfg['expression_features']+cfg['mechanistic_features']})
            row['current_pass'] = 1.
            rows.append(row)
    return rows, cfg


def test_join_is_order_independent_and_one_target_per_lineage():
    rows, cfg = fixture()
    a, checks = assemble(rows, cfg)
    b, _ = assemble(rows[::-1], cfg)
    assert a == b and len(a) == 2 and checks['boundaries_joined'] == 6
    assert a[0]['g3_current_margin'] == 4


@pytest.mark.parametrize('problem', ['duplicate', 'missing', 'changing_target', 'nonfinite'])
def test_bad_histories_are_rejected(problem):
    rows, cfg = fixture()
    if problem == 'duplicate':
        rows.append(rows[0])
    elif problem == 'missing':
        rows.pop()
    elif problem == 'changing_target':
        rows[1]['terminal_pass'] = 1-rows[0]['terminal_pass']
    else:
        rows[1]['current_margin'] = float('nan')
    with pytest.raises(ValueError):
        assemble(rows, cfg)


def test_future_rows_and_forbidden_fields_cannot_enter_features():
    rows, cfg = fixture()
    records, _ = assemble(rows, cfg)
    changed = copy.deepcopy(rows)
    for r in changed:
        r.update(next_pass=-9e20, next_margin=1e30, terminal_margin=float('nan'))
    changed.append(dict(generation=32, terminal_pass='do not access', current_margin='do not access'))
    other, _ = assemble(changed, cfg)
    assert records == other
    for spec in CFG['models']:
        if spec['id'] != 'condition_rate':
            a, names = design(records, spec, CFG)
            b, _ = design(other, spec, CFG)
            np.testing.assert_array_equal(a, b)
            assert not any('next_' in c or 'terminal_' in c for c in names)


def test_training_fit_ignores_held_out_labels_and_preprocessing_ignores_their_features():
    rng = np.random.default_rng(5103)
    x = rng.normal(size=(32, 3))
    y = np.array([i % 2 for i in range(32)], dtype=float)
    test = np.arange(32) >= 24
    train = ~test
    _, _, a = fit_predict(x, y, train, test, CFG)
    other = x.copy()
    other[test] += 1000
    other_y = y.copy()
    other_y[test] = 1-other_y[test]
    _, _, b = fit_predict(other, other_y, train, test, CFG)
    assert a == b
    np.testing.assert_allclose(a['mean'], x[train].mean(axis=0), rtol=0, atol=0)


def test_condition_rate_uses_only_training_outcomes():
    cfg = copy.deepcopy(CFG)
    cfg.update(pairings=['paired'], writers=['exact_rewrite'])
    y = np.array([0., 1., 1., 0.])
    conditions = np.array(['paired/exact_rewrite']*4)
    train = np.array([True, True, True, False])
    p, _, _ = rate_predict(y, conditions, train, ~train, cfg)
    assert p[0] == 2.5/4
    y[-1] = 1.
    q, _, _ = rate_predict(y, conditions, train, ~train, cfg)
    np.testing.assert_array_equal(p, q)
