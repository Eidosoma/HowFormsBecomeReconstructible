import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from laws_confirmation import l16_theta_content as p
from laws_confirmation import l16_theta_content_run as run
from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT


@pytest.fixture(scope='module')
def source():
    return p.source_bridge()


def test_source_bridge_full_replay(source):
    raw, meta = source
    assert meta['result'] == run.source_expected()
    assert meta['replay']['max_abs'] == 0 and meta['replay']['exact_source_scalars']
    assert meta['replay']['paths'] == 12
    assert p.checker().check_source(raw, meta) == meta['replay']


def test_source_function_restored(source):
    original = p.api()['original']
    assert original.blueprint_step is p.api()['blueprint_step']
    assert original.capacity_gate(p.api()['LandlordConfig']()) == source[1]['result']


@pytest.fixture(scope='module')
def block():
    return p.execute_block(p.DISPOSABLE)


def test_full_disposable_replay(block):
    raw, meta = block
    assert meta['index'] == p.DISPOSABLE and p.DISPOSABLE not in p.TISSUES
    assert p.checker().check_block(raw, meta, p.CONFIG, replay=False)
    assert all(x['replay']['dynamics_max_abs'] == 0 for x in meta['lives'])
    assert sum(x['replay']['exact_aliases'] for x in meta['lives']) == 20


@pytest.mark.parametrize('role', (0, 1))
@pytest.mark.parametrize('kind', ('aligned', 'shuffled', 'sham'))
def test_exact_field_multisets(block, role, kind):
    raw, _ = block
    theta = raw['theta'][0, p.CASES.index((role, kind))]
    expected = raw['theta'][0, p.CASES.index((0, 'aligned'))]
    np.testing.assert_array_equal(np.sort(theta.ravel()), np.sort(expected.ravel()))
    assert theta.std() == pytest.approx(.3) and abs(theta.mean()) < 1e-15
    if kind == 'sham':
        np.testing.assert_array_equal(theta, raw['theta'][0, p.CASES.index((role, 'aligned'))])


@pytest.mark.parametrize('case', p.CASES)
def test_common_birth_and_reference(block, case):
    raw, _ = block; role, kind = case
    start = raw['states'][0, p.CASES.index(case), 0]
    np.testing.assert_array_equal(start[2], raw['common'][0])
    np.testing.assert_array_equal(start[1], start[0])
    target = raw['targets'][0, role] if kind == 'body_own' else raw['targets'][0, 1-role] if kind == 'body_alternative' else raw['common'][0]
    np.testing.assert_array_equal(start[0], target)
    if kind in ('off', 'body_own', 'body_alternative'):
        assert np.count_nonzero(raw['theta'][0, p.CASES.index(case)]) == 0


def test_arm_order_and_noise():
    cfg = p.Config(lives=1, steps=3, times=(0, 1, 3))
    first, a = p.simulate_life(p.DISPOSABLE, 0, cfg)
    second, b = p.simulate_life(p.DISPOSABLE, 0, cfg, tuple(reversed(p.CASES)))
    for k in first: np.testing.assert_array_equal(first[k], second[k])
    assert a == b and len(set(a['branch_rng'])) == 1
    assert p.checker().check_life(first, a, cfg)['dynamics_max_abs'] == 0


def test_reference_off_isolation(block):
    raw, _ = block; cfg = p.Config(lives=1, steps=3, times=(0, 1, 3))
    initial = raw['states'][0, 0, 0].copy(); altered = initial.copy()
    altered[2] = 1.7
    ctx = p.context(p.DISPOSABLE)
    a, ar = p.evolve(initial, raw['theta'][0, 0], ctx, p.rng(p.DISPOSABLE, 0, 'test'), cfg)
    b, br = p.evolve(altered, raw['theta'][0, 0], ctx, p.rng(p.DISPOSABLE, 0, 'test'), cfg)
    assert ar == br
    np.testing.assert_array_equal(a[:, :2], b[:, :2])
    assert not np.array_equal(a[:, 2], b[:, 2])


def test_independent_observer(block, monkeypatch):
    raw, _ = block; life = {k: a[0] for k, a in raw.items()}
    monkeypatch.setattr(p, 'measurements', lambda *a: (_ for _ in ()).throw(RuntimeError('production forbidden')))
    np.testing.assert_allclose(p.checker().observe(life, p.CONFIG), life['values'], rtol=0, atol=1e-12)


def test_observer_denominator(block):
    raw, _ = block; life = {k: a[0].copy() for k, a in raw.items()}
    for amplitude, own in ((.2, 0.), (np.nextafter(.2, 1.), 1.)):
        for i, (role, _) in enumerate(p.CASES):
            life['states'][i, :, 0] = amplitude*life['targets'][role]
        values = p.measurements(life['states'], life['targets'])
        assert np.all(values[:, :, 0] == own) and np.all(values[:, :, 2] == 1.)
        np.testing.assert_allclose(values, p.checker().observe(life, p.CONFIG), rtol=0, atol=1e-12)
    # Half the sheet below the amplitude floor still remains in the denominator.
    life['states'][:, :, 0, :8] = 0.
    assert np.all(p.measurements(life['states'], life['targets'])[:, :, 0] == .5)


@pytest.mark.parametrize('kwargs', [dict(lives=0), dict(lives=True), dict(steps=-1),
    dict(times=(0, 2, 300)), dict(times=(0, 1, 300, 300)), dict(times=[0, 1, 300]),
    dict(norm=.4), dict(norm=np.nan), dict(amp_threshold=0.), dict(amp_threshold=.3)])
def test_config_rejects_drift(kwargs):
    with pytest.raises(ValueError): p.Config(**kwargs)


def algebra_blocks():
    targets = np.tile(p.checker().targets()[None], (4, 1, 1, 1))
    values = np.zeros((4, 12, len(p.CONFIG.times), 12))
    for role in (0, 1):
        values[:, p.CASES.index((role, 'aligned')), :, 0] = .2
        values[:, p.CASES.index((role, 'body_own')), :, 0] = 1.
        values[:, p.CASES.index((role, 'body_alternative')), :, 1] = 1.
    return [dict(targets=targets.copy(), values=values.copy()) for _ in range(8)]


def test_independent_summary(monkeypatch):
    blocks = algebra_blocks()
    for i, b in enumerate(blocks):
        for role in (0, 1):
            b['values'][0, p.CASES.index((role, 'aligned')), :, 0] += i/100
    summary = p.summarize(blocks)
    np.testing.assert_allclose(summary['primary']['block_means'], .2+np.arange(8)/400)
    assert summary['primary']['mean'] == pytest.approx(.20875)
    assert len(summary['contrasts']) == 120 and summary['label'] == 'QUALIFIED_THETA_CONTENT'
    monkeypatch.setattr(p, 'summarize', lambda *a: (_ for _ in ()).throw(RuntimeError('production forbidden')))
    assert p.checker().check_summary(summary, blocks, p.CONFIG)


@pytest.mark.parametrize('failure', ('readout', 'no_disagreement', 'zero', 'negative', 'direction'))
def test_gate_failure_not_absence(failure):
    blocks = algebra_blocks()
    for b in blocks:
        if failure == 'no_disagreement': b['targets'][:, 1] = b['targets'][:, 0]
        for role in (0, 1):
            if failure == 'readout':
                b['values'][:, p.CASES.index((role, 'body_own')), :, :2] = 0.
                b['values'][:, p.CASES.index((role, 'body_alternative')), :, :2] = 0.
            elif failure in ('zero', 'negative'):
                b['values'][:, p.CASES.index((role, 'aligned')), :, 0] = 0.
                if failure == 'negative': b['values'][:, p.CASES.index((role, 'aligned')), :, 1] = .1
            elif failure == 'direction' and role == 1:
                b['values'][:, p.CASES.index((role, 'aligned')), :, :2] = [.0, .1]
    summary = p.summarize(blocks)
    assert summary['label'] == ('READOUT_NOT_QUALIFIED' if failure in ('readout', 'no_disagreement')
                                else 'THETA_CONTENT_UNRESOLVED')
    assert p.checker().check_summary(summary, blocks, p.CONFIG)


@pytest.mark.parametrize('key', ('targets', 'common', 'permutations', 'theta', 'states', 'values'))
def test_raw_corruption(block, key):
    raw, meta = block; life = {k: a[0].copy() for k, a in raw.items()}
    life[key].flat[-1] += 1
    with pytest.raises(AssertionError): p.checker().check_life(life, meta['lives'][0], p.CONFIG)


@pytest.mark.parametrize('key', ('gain', 'theta_writable', 'target_reference_supplied',
    'primary_births_identical', 'birth_rng', 'branch_rng', 'tissue'))
def test_metadata_corruption(block, key):
    raw, meta = block; bad = copy.deepcopy(meta['lives'][0])
    if isinstance(bad[key], bool): bad[key] = not bad[key]
    elif key == 'gain': bad[key] = .2
    elif key == 'tissue': bad[key]['coupling'] += .1
    elif key == 'branch_rng': bad[key][0] = 'bad'
    else: bad[key] = 'bad'
    with pytest.raises(AssertionError): p.checker().check_life({k: a[0] for k, a in raw.items()}, bad, p.CONFIG, False)


@pytest.mark.parametrize('key', ('label', 'primary', 'readout_qualified', 'tissues', 'cell_means', 'contrasts'))
def test_summary_corruption(key):
    blocks = algebra_blocks(); summary = p.summarize(blocks)
    if key == 'label': summary[key] = 'wrong'
    elif key == 'primary': summary[key]['mean'] += .01
    elif key == 'readout_qualified': summary[key] = False
    elif key == 'tissues': summary[key][0] = 0
    elif key == 'cell_means': summary[key][0][0][0] += .01
    else: summary[key][-1]['block_means'][0] += .01
    with pytest.raises(AssertionError): p.checker().check_summary(summary, blocks, p.CONFIG)


def test_external_roundtrip(block, tmp_path):
    assert DEFAULT_EXTERNAL_ROOT in tmp_path.resolve().parents
    raw, meta = block
    saved = run.u.save_pair(tmp_path, 'block', raw, meta, DEFAULT_EXTERNAL_ROOT)
    assert p.checker().check_block(saved, run.u.read_json(tmp_path/'block.json'), p.CONFIG, False)
    with pytest.raises(FileExistsError): run.u.save_pair(tmp_path, 'block', raw, meta, DEFAULT_EXTERNAL_ROOT)
    with pytest.raises(ValueError): run.u.write_json(p.WS/'forbidden.json', {}, DEFAULT_EXTERNAL_ROOT)


def test_cpu_and_external_guards(monkeypatch):
    assert run.preflight(DEFAULT_EXTERNAL_ROOT)
    monkeypatch.setattr(os, 'sched_getaffinity', lambda _: set(range(7)))
    with pytest.raises(RuntimeError): run.preflight(DEFAULT_EXTERNAL_ROOT)
    monkeypatch.setattr(os, 'sched_getaffinity', lambda _: {0})
    monkeypatch.setenv('OPENBLAS_NUM_THREADS', '2')
    with pytest.raises(RuntimeError): run.preflight(DEFAULT_EXTERNAL_ROOT)
    monkeypatch.setenv('OPENBLAS_NUM_THREADS', '1'); monkeypatch.setenv('TMPDIR', str(p.WS))
    with pytest.raises(RuntimeError): run.preflight(DEFAULT_EXTERNAL_ROOT)


def test_reservation_guards(tmp_path, monkeypatch):
    monkeypatch.setattr(run, 'preflight', lambda *a: [0])
    monkeypatch.setattr(run, 'main_inputs', lambda *a: {})
    monkeypatch.setattr(run, 'timing_checked', lambda *a: {})
    (tmp_path/'runs'/p.RUN_ID).mkdir(parents=True)
    with pytest.raises(FileExistsError): run.prepare(tmp_path)


def test_detachment_guard(tmp_path):
    run.detached_guard(tmp_path, False)
    with pytest.raises(FileNotFoundError): run.detached_guard(tmp_path, True)


def test_fresh_process_import():
    result = subprocess.run([sys.executable, '-c',
        'from laws_confirmation import l16_theta_content as p; p.api(); '
        'from laws_confirmation import l16_theta_content_run as r; '
        'assert p.CONFIG.norm == .3 and r.WORKERS == 6; print(p.RUN_ID)'],
        cwd=p.WS, env=os.environ.copy(), capture_output=True, text=True, check=True)
    assert result.stdout.strip() == p.RUN_ID


@pytest.mark.parametrize('bad', ('permutation', 'target_shape', 'nonfinite'))
def test_field_validation(bad):
    targets = p.checker().targets(); perm = np.tile(np.arange(256), (2, 1))
    if bad == 'permutation': perm[0, 0] = 1
    elif bad == 'target_shape': targets = targets[:, :1]
    else: targets[0, 0, 0] = np.nan
    with pytest.raises(ValueError): p.theta_fields(targets, perm)


def test_old_cohort_rejected(block):
    raw, meta = block; bad = copy.deepcopy(meta); bad['index'] = 57000
    with pytest.raises(AssertionError): p.checker().check_block(raw, bad, p.CONFIG, False)


def test_source_corruption(source):
    raw, meta = source; bad = copy.deepcopy(meta)
    bad['result']['rows'][0]['pin'] += .01
    with pytest.raises(AssertionError): p.checker().check_source(raw, bad)


def test_regression_inputs_pinned():
    paths = run.science_paths(DEFAULT_EXTERNAL_ROOT)
    assert len(paths) == len(set(paths)) and len(paths) >= 172
    assert p.WS/'src/laws_confirmation/artifact_audit.py' in paths
    assert p.ORIGIN/'hidden_genome/results/full/knife_summary.json' in paths
    assert not any(x.name in ('WORKLOG.md', 'DECISIONS.md', 'NEXT_WORK.md', 'LAW_LEDGER.md') for x in paths)


@pytest.mark.parametrize('level', ('block', 'life'))
def test_extra_metadata_rejected(block, level):
    raw, meta = block; bad = copy.deepcopy(meta)
    if level == 'block': bad['pooled'] = True
    else: bad['lives'][0]['pooled'] = True
    with pytest.raises(AssertionError): p.checker().check_block(raw, bad, p.CONFIG, False)


def test_freeze_reservation_guard(tmp_path, monkeypatch):
    monkeypatch.setattr(run, 'preflight', lambda *a: [0])
    monkeypatch.setattr(run, 'test_proof', lambda *a: {})
    (tmp_path/'tmp').mkdir()
    run.u.write_json(run.freeze_path(tmp_path), {}, DEFAULT_EXTERNAL_ROOT)
    with pytest.raises(FileExistsError): run.freeze(tmp_path, tmp_path/'report.xml')
