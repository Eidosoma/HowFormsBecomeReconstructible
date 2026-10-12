"""Synthetic qualification only; no main-cohort access or tissue dynamics."""
import ast
import copy
from pathlib import Path

import numpy as np
import pytest

from l20_extension1 import phase_budget_review as review
from l20_extension1 import phase_budget_review_audit as check


@pytest.fixture(scope='module')
def synthetic():
    shapes = dict(incoming=(2048,), routed=(2048,), outgoing=(2048,), terminal_packet=(2048,),
        read_states=(6, 3, 16, 16), write_states=(5, 4, 16, 16), terminal_states=(4, 3, 16, 16),
        shift=(2,), scores=(2, 2, 16, 16), read_values=(6, 2), write_values=(5, 2), terminal_values=(4, 2), record_values=(2,))
    raw = {k: np.zeros((4, 2, 24, 3, *shape), dtype=np.uint8 if k in ('incoming', 'routed', 'outgoing', 'terminal_packet') else np.int64 if k == 'shift' else np.float64)
           for k, shape in shapes.items()}
    raw['founder_packets'] = np.zeros((4, 2, 2048), np.uint8)
    for role in (0, 1):
        f0 = .3 * review.metrics.TARGETS[role]
        packet = np.frombuffer(f0.astype('<f8').tobytes(), np.uint8)
        raw['founder_packets'][:, role] = packet
        for kind in review.SELECTED:
            ci = review.CASES.index((role, kind))
            for k in ('incoming', 'routed', 'outgoing', 'terminal_packet'):
                raw[k][:, :, ci] = packet
            for phase in ('read', 'write', 'terminal'):
                raw[phase + '_states'][:, :, ci, :, :, :3] = np.stack([f0] * 3)
                raw[phase + '_values'][:, :, ci, :, :, 0] = .5
                raw[phase + '_values'][:, :, ci, :, :, 1] = 1.
            raw['record_values'][:, :, ci] = 1.
            raw['scores'][:, :, ci, :, :, role] = 1.
            raw['shift'][:, :, ci] = (0, 1) if role == 0 else (1, 0)
    lives = []
    for life in range(4):
        trials = []
        for noise in (0, 1):
            paths = []
            for role, kind in review.CASES:
                timing = kind.split('_')[0]
                selector = dict(inferred_family=role, family_maxima=[int(role == 0), int(role == 1)], chosen_forward_shift=[0, 0])
                paths.append(dict(generations=[dict(role=role, kind=kind, generation=g,
                    read_times=review.times(timing, 'read'), write_times=review.times(timing, 'write'),
                    assay_steps=300, assay_enters_lineage=False, selector=copy.deepcopy(selector), terminal_selector=copy.deepcopy(selector)) for g in (1, 2, 3)]))
            trials.append(dict(paths=paths))
        lives.append(dict(trials=trials))
    return raw, dict(index=93000, lives=lives)


@pytest.fixture(scope='module')
def extracted(synthetic):
    return review.extract(*synthetic)


@pytest.fixture(scope='module')
def cohort(extracted):
    rows = []
    for block in review.BLOCKS:
        for source in extracted:
            row = copy.deepcopy(source)
            row['block'] = block
            rows.append(row)
    return rows


def original_from(rows):
    def statistic(values):
        x = np.array(values).reshape(16, 4, 2)
        s = check.block_summary(x)
        return dict(mean=s['mean'], block_means=s['block_means'],
            pointwise_block_bootstrap_95=s['original_block_bootstrap_95'], life_noise_values=x.tolist())
    original = dict(groups=[], contrasts=[], copy_contrasts=[], allocation_contrasts=[], controls=[dict(passes=True)] * 54,
                    primary_interval_classification='B_ALLOCATION_UNRESOLVED')
    for role in (0, 1):
        rr = sorted((r for r in rows if r['role'] == role), key=review.identity)
        for kind in review.SELECTED:
            for gi in range(3):
                original['groups'].append(dict(role=role, condition=kind, generation=gi + 1,
                    metrics={k: statistic([r['paths'][kind][gi][k] for r in rr]) for k in
                        ('terminal_preference', 'outgoing_shape', 'write_end_shape', 'terminal_reference_shape')}))
        for kind in review.INTACT:
            original['copy_contrasts'].append(dict(role=role, condition=kind, generation=3,
                metrics=dict(terminal_preference=statistic([r['paths'][kind][2]['terminal_preference'] - r['paths']['base_copy'][2]['terminal_preference'] for r in rr]))))
            if kind != 'base':
                original['contrasts'].append(dict(role=role, condition=kind, generation=3,
                    metrics=dict(terminal_preference=statistic([r['paired'][kind + '_minus_base'][2]['terminal_preference'] for r in rr]))))
        original['allocation_contrasts'].append(dict(role=role, generation=3,
            metrics=dict(terminal_preference=statistic([r['paired']['read_minus_write'][2]['terminal_preference'] for r in rr]))))
    original['primary'] = original['allocation_contrasts'][1]['metrics']['terminal_preference']
    return original


@pytest.mark.parametrize('role', (0, 1))
def test_independent_shape_and_signed_canonical(role):
    rng = np.random.default_rng(8)
    for value in (np.zeros((16, 16)), -.3 * review.metrics.TARGETS[role], rng.normal(size=(16, 16))):
        assert check.shape(value, role) == pytest.approx(review.metrics.shape(value, role))
        assert check.shape(value, role, False) == pytest.approx(review.metrics.canonical(value, role))
    assert check.shape(-review.metrics.TARGETS[role], role) == pytest.approx(1)
    assert check.shape(-review.metrics.TARGETS[role], role, False) == pytest.approx(-1)


@pytest.mark.parametrize('role', (0, 1))
def test_exact_score_decomposition(role):
    rng = np.random.default_rng(146)
    for _ in range(10):
        a, b = rng.normal(0, .3, (2, 16, 16))
        assert review.parts(a, b, role) == check.decomposition(a, b, role)
        assert review.parts(a, b, role)['net_units'] / 256 == review.metrics.preference(a, role) - review.metrics.preference(b, role)


@pytest.mark.parametrize('role', (0, 1))
def test_original_strict_threshold_and_zero(role):
    t = review.metrics.TARGETS[role]
    assert review.metrics.preference(.2 * t, role) == 0
    assert review.metrics.preference(np.nextafter(.2, 1) * t, role) == .5
    assert review.metrics.preference(-.3 * t, role) == -.5
    assert check.decomposition(.3 * t, -.3 * t, role)['both_active_sign_net_units'] == 256


def test_phase_identity():
    result = review.phase_changes(.8, .6, .85, .82)
    assert result['packet_net'] == pytest.approx(.02)
    assert sum(result[k] for k in ('incoming_to_read_R', 'read_R_to_write_R', 'write_R_to_packet')) == pytest.approx(.02)
    with pytest.raises(ValueError):
        review.phase_changes(0, 1, np.nan, 1)


@pytest.mark.parametrize('kind,phase,a,b', [('read', 'read', 300, 600), ('write', 'write', 1000, 1300)])
def test_extended_window_uses_times(kind, phase, a, b):
    tt = review.times(kind, phase)
    p = dict(times=tt, **{k: [t / 100 for t in tt] for k in ('preference', 'reference_shape', 'reference_canonical', 'body_shape', 'body_canonical')})
    assert review.window(p, a, b)['reference_shape'] == 3.
    with pytest.raises(ValueError):
        review.window(p, a, a)
    with pytest.raises(ValueError):
        review.window(p, a, 999)


def test_timestamps_not_common_array_slots():
    assert review.times('base', 'read')[-2:] == [200, 300]
    assert review.times('read', 'read')[-2:] == [300, 600]
    assert review.times('write', 'write')[-2:] == [1000, 1300]
    with pytest.raises(ValueError):
        review.times('unregistered', 'read')


def test_full_synthetic_extract_and_independent_check(synthetic, extracted):
    assert len(extracted) == 16
    for row in extracted:
        check.row_check(row, *synthetic)


def test_prefix_corruption_rejected(synthetic):
    raw, meta = synthetic
    changed = dict(raw, write_states=raw['write_states'].copy())
    changed['write_states'][0, 0, 8, 0, 3, 2, 0, 0] += .1
    with pytest.raises(AssertionError):
        review.prefixes(changed, 0, 0, 0)


def test_later_history_not_forced_equal(synthetic):
    raw, meta = synthetic
    changed = dict(raw, write_states=raw['write_states'].copy())
    changed['write_states'][0, 0, 8, 1, 3, 2, 0, 0] += .1
    review.prefixes(changed, 0, 0, 0)


def test_metadata_timing_corruption(synthetic):
    raw, meta = synthetic
    corrupted = copy.deepcopy(meta)
    corrupted['lives'][0]['trials'][0]['paths'][4]['generations'][0]['read_times'][-2] = 200
    with pytest.raises(AssertionError):
        review.extract(raw, corrupted)


def test_saved_score_corruption(synthetic):
    raw, meta = synthetic
    corrupted = dict(raw, terminal_values=raw['terminal_values'].copy())
    corrupted['terminal_values'][0, 0, 0, 0, -1, 0] = -.5
    with pytest.raises(AssertionError):
        review.extract(corrupted, meta)


def test_guide_label_corruption(synthetic):
    raw, meta = synthetic
    corrupted = copy.deepcopy(meta)
    corrupted['lives'][0]['trials'][0]['paths'][0]['generations'][0]['terminal_selector']['inferred_family'] = 1
    with pytest.raises(AssertionError):
        review.extract(raw, corrupted)


def test_continuity_corruption(synthetic):
    raw, meta = synthetic
    corrupted = dict(raw, incoming=raw['incoming'].copy())
    corrupted['incoming'][0, 0, 0, 1, 0] ^= 1
    with pytest.raises(AssertionError):
        review.extract(corrupted, meta)


@pytest.mark.parametrize('key', ['profiles', 'preference_parts', 'guide'])
def test_independent_row_corruption_rejected(synthetic, extracted, key):
    row = copy.deepcopy(extracted[0])
    if key == 'profiles':
        row['paths']['read'][0]['profiles']['read']['reference_shape'][-1] -= .1
    elif key == 'guide':
        row['paths']['write'][2]['guide']['out']['family'] = 1
    else:
        row['paired']['read_minus_write'][0]['preference_parts']['net_units'] += 1
    with pytest.raises(AssertionError):
        check.row_check(row, *synthetic)


def test_complete_summary_and_empty_strata(cohort):
    original = original_from(cohort)
    summary = review.summarize(cohort, original)
    check.summary_check(cohort, summary, original)
    assert summary['families']['1']['strata']['any_negative'] == dict(count=0, ids=[], founder_blocks=0, record_host_pairs=0)
    assert summary['families']['1']['negative_patterns']['000'] == 128
    assert summary['families']['1']['strata']['tie']['count'] == 128
    bad = copy.deepcopy(summary)
    bad['families']['1']['strata']['tie']['count'] -= 1
    with pytest.raises(AssertionError):
        check.summary_check(cohort, bad, original)


def test_negative_outcomes_differ_from_negative_differences(cohort):
    rows = copy.deepcopy([r for r in cohort if r['role'] == 1])
    rows[0]['paths']['write'][2]['terminal_preference'] = -.1
    rows[0]['paired']['read_minus_write'][2]['terminal_preference'] = .6
    rows[1]['paths']['read'][2]['terminal_preference'] = 0
    rows[1]['paired']['read_minus_write'][2]['terminal_preference'] = -.5
    masks = review.masks(rows)
    assert masks['read_advantage'].sum() == masks['write_advantage'].sum() == 1
    assert masks['negative_write'].sum() == masks['any_negative'].sum() == 1
    assert masks['negative_read'].sum() == 0
    assert masks['tie'].sum() == 126
    assert {k: [review.identity(r) for r, yes in zip(rows, mask) if yes] for k, mask in masks.items()} == {k: [check.key(r) for r in rr] for k, rr in check.choose(rows).items()}


def test_block_bootstrap_and_adverse_tail():
    data = np.ones((16, 4, 2)) * .1
    data[0, 0, :] = [-.5, 0]
    result = review.block_stats(data)
    check.same(result, check.block_summary(data))
    assert result['mean'] > 0 and result['descriptive']['negative'] == result['descriptive']['zero'] == 1
    assert result['negative_contribution_to_full_mean'] < 0
    assert result['negative_contribution_to_full_mean'] + result['positive_contribution_to_full_mean'] == pytest.approx(result['mean'])
    with pytest.raises(ValueError):
        review.block_stats(data[:8])


def test_shape_disagreement_not_pref_rescue():
    role = 1
    v, r = -.3 * review.metrics.TARGETS[role], .3 * review.metrics.TARGETS[role]
    p = review.profile(np.stack([np.stack([v, v, r])]), role, [300])
    assert p['reference_shape'] == pytest.approx([1])
    assert p['preference'] == [-.5]


def test_original_statistic_corruption_rejected(cohort):
    original = original_from(cohort)
    original['groups'][0]['metrics']['terminal_preference']['mean'] += .1
    with pytest.raises(AssertionError):
        review.summarize(cohort, original)


def test_duplicate_or_missing_rows_rejected(cohort):
    original = original_from(cohort)
    with pytest.raises(AssertionError):
        review.summarize(cohort[:-1], original)
    with pytest.raises(AssertionError):
        review.summarize(cohort[:-1] + [cohort[0]], original)


def test_external_roundtrip_and_exclusive_output(tmp_path, extracted):
    dest = tmp_path / 'rows.json'
    review.metrics.write_json(dest, extracted)
    check.same(review.metrics.read_json(dest), extracted)
    with pytest.raises(FileExistsError):
        review.metrics.write_json(dest, [])


def test_resource_guards(monkeypatch):
    for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        monkeypatch.setenv(k, '1')
    monkeypatch.setattr(review.os, 'sched_getaffinity', lambda pid: set(range(7)))
    with pytest.raises(RuntimeError):
        review.resources()
    monkeypatch.setattr(review.os, 'sched_getaffinity', lambda pid: set(range(6)))
    review.resources()
    monkeypatch.setenv('OMP_NUM_THREADS', '2')
    with pytest.raises(RuntimeError):
        review.resources()


def test_no_simulator_imports_or_dynamic_calls():
    allowed = {'__future__', 'argparse', 'datetime', 'hashlib', 'json', 'math', 'os', 'pathlib', 'time', 'xml', 'numpy'}
    for module in (review, check, review.metrics):
        tree = ast.parse(Path(module.__file__).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(x.name.split('.')[0] in allowed for x in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    assert module is review and node.module is None and [x.name for x in node.names] == ['serial_compat_review']
                else:
                    assert node.module.split('.')[0] in allowed
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in ('simulate', 'simulate_life', 'read_trace', 'write_trace', 'fit')
