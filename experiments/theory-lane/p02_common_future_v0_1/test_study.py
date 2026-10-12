"""Synthetic checks of selection, leakage barriers and fixed estimators."""
import copy
import itertools

import numpy as np
import pytest

from analyze import choice_weight, design, fit_fold, matching, rate_fold, validate
from extract import HERE, read


@pytest.fixture
def cfg():
    return read(HERE / 'config.json')


@pytest.fixture
def records(cfg):
    result = []
    for bi, block in enumerate(cfg['blocks']):
        for hi, history in enumerate(cfg['histories']):
            for founder, recipient in itertools.product(range(4), range(4)):
                value = .5 + .01*bi + .02*hi + .003*founder + .007*recipient
                y = int((bi+hi+founder+recipient) % 3 != 0)
                row = dict(block=block, history=history, founder=founder, recipient=recipient,
                           generation=14, task_rule=1 if founder % 2 == 0 else -1,
                           current_margin=value, current_pass=1, unsigned_access=.06+.001*recipient,
                           signed_transfer=.02+.002*founder-.001*hi,
                           terminal_success=y, terminal_margin=.7 if y else -.3)
                row.update({k: value+.01*i for i, k in enumerate(cfg['expression_features'][:4])})
                result.append(row)
    return result


def test_complete_unique_panel(cfg, records):
    validate(records, cfg)
    with pytest.raises(AssertionError):
        validate(records[:-1], cfg)
    with pytest.raises(AssertionError):
        validate(records + records[:1], cfg)


def test_strict_threshold_and_caliper(cfg, records):
    # Compare literal floating point distances to the literal protocol boundary.
    spaced = next(r for r in records if r['history'] == cfg['matched_pair'][0])
    cluster = next(r for r in records if r['history'] == cfg['matched_pair'][1])
    for r in (spaced, cluster):
        r.update({k: .5 for k in cfg['expression_features'][:4]})
        r['current_margin'] = .5
    spaced[cfg['expression_features'][0]] += cfg['match_caliper']
    measured = abs(spaced[cfg['expression_features'][0]]-cluster[cfg['expression_features'][0]])
    test_cfg = dict(cfg, match_caliper=measured)
    pairs, _ = matching(records, test_cfg)
    assert pairs[0]['strict_match'] == 1
    test_cfg['match_caliper'] = np.nextafter(measured, -np.inf)
    assert matching(records, test_cfg)[0][0]['strict_match'] == 0
    spaced['current_pass'] = 0
    assert matching(records, cfg)[0][0]['strict_match'] == 0


def test_no_endpoint_filtering_or_match_drift(cfg, records):
    pairs, _ = matching(records, cfg)
    changed = copy.deepcopy(records)
    for r in changed:
        r['terminal_success'] = 1-r['terminal_success']
    other, _ = matching(changed, cfg)
    for a, b in zip(pairs, other):
        for name in ('strict_match', 'current_both_pass', 'exact_expression',
                     'max_expression_difference', 'choose_spaced_margin', 'choose_spaced_signed'):
            assert a[name] == b[name]


def test_ties_and_decision_regret(cfg, records):
    assert [choice_weight(a, b) for a, b in ((1, 0), (0, 1), (1, 1))] == [1., 0., .5]
    for r in records:
        r.update({k: .8 for k in cfg['expression_features'][:4]})
        r.update(current_margin=.8, signed_transfer=.07,
                 terminal_success=int(r['history'] == cfg['matched_pair'][0]))
    _, result = matching(records, cfg)
    assert result['subsets']['strict']['n'] == 128
    choices = result['choices_on_strict_matches']
    assert choices['constant']['successes'] == 128
    for rule in ('margin', 'signed'):
        assert choices[rule]['successes'] == choices[rule]['regret'] == 64
        assert choices[rule]['discordant_accuracy'] == .5
        assert choices[rule]['discordant_ties'] == 128
        assert choices[rule]['discordant_nontie_coverage'] == 0


def test_empty_matches_are_reported(cfg, records):
    for r in records:
        r['current_pass'] = 0
    _, result = matching(records, cfg)
    assert result['subsets']['strict']['n'] == 0
    assert result['subsets']['strict']['difference'] is None
    assert result['choices_on_strict_matches']['signed']['success_rate'] is None


def test_design_excludes_future_and_identifiers(cfg, records):
    model = cfg['models'][-1]
    x, names = design(records, cfg, model)
    changed = copy.deepcopy(records)
    for r in changed:
        r.update(terminal_success=77, terminal_margin=-1e50, block=-999,
                 founder=1000, recipient=1000, future_magic=1e100)
    other, other_names = design(changed, cfg, model)
    np.testing.assert_array_equal(x, other)
    assert names == other_names and len(names) == 21
    assert sum('*' in name for name in names) == 10


def test_excluded_labels_never_change_fit_or_probability(cfg, records):
    x, _ = design(records, cfg, cfg['models'][-1])
    y = np.array([r['terminal_success'] for r in records], float)
    test = np.array([r['block'] == cfg['blocks'][0] for r in records])
    z, fit = fit_fold(x, y, ~test, test, cfg)
    changed = y.copy()
    changed[test] = 1-changed[test]
    z2, fit2 = fit_fold(x, changed, ~test, test, cfg)
    np.testing.assert_array_equal(z, z2)
    assert fit == fit2
    r1, rate1 = rate_fold(records, y, ~test, test, cfg)
    r2, rate2 = rate_fold(records, changed, ~test, test, cfg)
    np.testing.assert_array_equal(r1, r2)
    assert rate1 == rate2


def test_excluded_features_do_not_change_preprocessing_or_fit(cfg, records):
    x, _ = design(records, cfg, cfg['models'][-1])
    y = np.array([r['terminal_success'] for r in records], float)
    test = np.array([r['block'] == cfg['blocks'][0] for r in records])
    _, fit = fit_fold(x, y, ~test, test, cfg)
    changed = x.copy()
    changed[test] += 100
    _, fit2 = fit_fold(changed, y, ~test, test, cfg)
    assert fit == fit2
