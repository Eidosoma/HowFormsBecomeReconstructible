import copy
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from laws_confirmation import l16_body_content as p
from laws_confirmation import l16_body_content_run as run
from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT


@pytest.fixture(scope='module')
def source():
    return p.source_control(0)


def test_e53_exact_source_bridge(source):
    raw, meta = source
    assert meta['result'] == run.source_expected()[0]
    assert p.api()['original'].knife_run(p.api()['KnifeConfig'](), 0) == meta['result']
    assert meta['replay']['full_source_replay'] and meta['replay']['max_abs'] == 0
    assert raw['finals'].shape == (20, 8, 16, 16)
    assert meta['replay']['old_region_disagreement'] == [4, 3, 7, 6, 9, 5, 5, 6]
    assert meta['replay']['centred_region_disagreement'] == [28, 26, 31, 34, 26, 26, 28, 29]


@pytest.fixture(scope='module')
def full_block():
    return p.execute_block(p.DISPOSABLE)


def test_full_disposable_replay(full_block):
    raw, meta = full_block
    assert meta['index'] == p.DISPOSABLE and p.DISPOSABLE not in p.TISSUES
    assert p.checker().check_block(raw, meta, p.CONFIG, replay=False)
    assert all(m['replay']['dynamics_max_abs'] == 0 for m in meta['lives'])
    assert all(m['replay']['metric_max_abs'] <= 1e-12 for m in meta['lives'])
    assert sum(m['replay']['exact_sham_aliases'] for m in meta['lives']) == 8


@pytest.mark.parametrize('case', p.CASES)
def test_birth_histograms(full_block, case):
    raw, _ = full_block
    sources = raw['sources'][0]; role, _, kind = case
    initial = raw['states'][0, p.CASES.index(case), 0]
    if kind.startswith('full_'):
        np.testing.assert_array_equal(np.sort(initial[0].ravel()), np.sort(sources[role, 0].ravel()))
    else:
        mask = p.injury_mask()
        np.testing.assert_array_equal(np.sort(initial[0, ~mask]), np.sort(sources[role, 0, ~mask]))
        assert np.all(initial[0, mask] == p.context(p.DISPOSABLE)['tissue'].resting)
    np.testing.assert_array_equal(initial[0], initial[1])
    np.testing.assert_array_equal(initial[2], sources[role, 2])


@pytest.mark.parametrize('role', (0, 1))
@pytest.mark.parametrize('kind', p.KINDS)
def test_no_donor_reference_or_ema(full_block, role, kind):
    raw, _ = full_block; sources = raw['sources'][0].copy()
    perm = raw['permutations'][0, role]
    expected = p.birth(sources, role, kind, perm, 0.)
    sources[1-role, 1:] += 1.1
    sources[role, 1] -= .7
    np.testing.assert_array_equal(expected, p.birth(sources, role, kind, perm, 0.))


def test_rank_stable_ties():
    values = np.array([4., 3., 2., 1.]); guide = np.array([1., 0., 1., 0.])
    np.testing.assert_array_equal(p.rank_match(values, guide), [3., 1., 4., 2.])
    np.testing.assert_array_equal(p.rank_match(values, values), values)
    np.testing.assert_array_equal(p.rank_match(values, guide), p.checker().ranked(values, guide))


@pytest.mark.parametrize('values,guide', [([], []), ([1.], [1., 2.]), ([float('nan')], [1.]),
    ([1.], [float('inf')]), ([[1.]], [[1.]])])
def test_rank_rejects_invalid(values, guide):
    with pytest.raises(ValueError): p.rank_match(np.array(values), np.array(guide))


@pytest.mark.parametrize('kw', [dict(lives=0), dict(lives=True), dict(settle=-1), dict(recovery=2),
    dict(times=(0, 2, 240)), dict(times=(0, 1, 240, 240)), dict(times=[0, 1, 240]),
    dict(amp_threshold=0), dict(amp_threshold=np.nan), dict(amp_threshold=2)])
def test_config_validation(kw):
    with pytest.raises(ValueError): p.Config(**kw)


def test_arm_order_and_noise():
    cfg = p.Config(lives=1, settle=4, recovery=3, times=(0, 1, 3))
    raw, meta = p.simulate_life(p.DISPOSABLE, 0, cfg)
    other, alternate = p.simulate_life(p.DISPOSABLE, 0, cfg, tuple(reversed(p.CASES)))
    for key in raw: np.testing.assert_array_equal(raw[key], other[key])
    assert meta == alternate and len(set(meta['branch_rng'])) == 1 and len(set(meta['source_rng'])) == 1
    for role in (0, 1):
        for kind in p.KINDS:
            np.testing.assert_array_equal(raw['states'][p.CASES.index((role, .2, kind)), 0],
                                          raw['states'][p.CASES.index((role, 0., kind)), 0])


def test_independent_observer(full_block, monkeypatch):
    raw, _ = full_block; life = {k: v[0] for k, v in raw.items()}
    expected = p.checker().observe(life, p.CONFIG)
    np.testing.assert_array_equal(expected[..., :3], life['values'][..., :3])
    np.testing.assert_allclose(expected, life['values'], rtol=0, atol=1e-12)
    monkeypatch.setattr(p, 'measurements', lambda *args: (_ for _ in ()).throw(RuntimeError('production forbidden')))
    np.testing.assert_array_equal(p.checker().observe(life, p.CONFIG), expected)


def test_reference_off_exact_alias(full_block):
    raw, _ = full_block
    initial = raw['states'][0, p.CASES.index((0, 0., 'intact')), 0].copy()
    changed = initial.copy(); changed[2] = 1.7
    cfg = p.Config(lives=1, settle=4, recovery=3, times=(0, 1, 3))
    ctx = p.context(p.DISPOSABLE)
    first, a = p.evolve(initial, raw['theta'][0], ctx, p.rng(p.DISPOSABLE, 0, 'test-off'), 0., cfg)
    second, b = p.evolve(changed, raw['theta'][0], ctx, p.rng(p.DISPOSABLE, 0, 'test-off'), 0., cfg)
    assert a == b
    np.testing.assert_array_equal(first[:, :2], second[:, :2])
    assert not np.array_equal(first[:, 2], second[:, 2])


def test_amplitude_floor_and_shape(full_block):
    raw, _ = full_block; life = {k: v[0].copy() for k, v in raw.items()}
    for value, expected in ((.2, 0.), (np.nextafter(.2, 1.), 1.)):
        life['states'][:, :, 0] = value
        life['sources'][:, 0] = 1.
        observed = p.measurements(life['states'], life['sources'])
        assert np.all(observed[:, :, 0] == expected)
        np.testing.assert_allclose(observed, p.checker().observe(life, p.CONFIG), atol=1e-15)
    with pytest.raises(ValueError): p.measurements(life['states'], life['sources'][:, :, :1])


@pytest.mark.parametrize('field', ('theta', 'sources', 'states', 'values', 'permutations'))
def test_raw_corruption(full_block, field):
    raw, meta = full_block; life = {k: v[0].copy() for k, v in raw.items()}
    life[field].flat[-1] += 1
    with pytest.raises(AssertionError): p.checker().check_life(life, meta['lives'][0], p.CONFIG, replay=True)


@pytest.mark.parametrize('field', ('donor_reference_transferred', 'theta_writable', 'ema_reset_to_birth_v', 'branch_rng', 'source_rng'))
def test_metadata_corruption(full_block, field):
    raw, meta = full_block; bad = copy.deepcopy(meta['lives'][0])
    if isinstance(bad[field], bool): bad[field] = not bad[field]
    else: bad[field][0] = 'bad'
    with pytest.raises(AssertionError): p.checker().check_life({k: v[0] for k, v in raw.items()}, bad, p.CONFIG, False)


def test_source_metadata_corruption(source):
    raw, meta = source; bad = copy.deepcopy(meta)
    bad['result']['floor']['R_on'] += .01
    with pytest.raises(AssertionError): p.checker().check_source(raw, bad)


def artificial_blocks():
    # Pure algebra fixture, not a simulator future or observed qualification data.
    source = np.zeros((2, 2, 3, 16, 16), dtype=np.float64)
    source[:, 0, 0] = 1.; source[:, 1, 0] = -1.
    values = np.zeros((2, 24, len(p.CONFIG.times), 9), dtype=np.float64)
    for role in (0, 1):
        values[:, p.CASES.index((role, 0., 'full_own')), :, 0] = 1.
        values[:, p.CASES.index((role, 0., 'full_alternative')), :, 1] = 1.
        values[:, p.CASES.index((role, 0., 'alternative')), :, 1] = .1
    return [dict(sources=source.copy(), values=values.copy()) for _ in range(8)]


def test_summary_and_independent_unit():
    blocks = artificial_blocks()
    for index, block in enumerate(blocks):
        for role in (0, 1):
            block['values'][0, p.CASES.index((role, 0., 'alternative')), :, 1] += index/100
    summary = p.summarize(blocks)
    assert p.checker().check_summary(summary, blocks, p.CONFIG)
    assert summary['label'] == 'QUALIFIED_CONTEXT_STEERING'
    np.testing.assert_allclose(summary['primary']['block_means'], .1+np.arange(8)/200)
    assert len(summary['contrasts']) == 100 and len(summary['cell_means']) == 24
    assert summary['primary']['mean'] == pytest.approx(.1175)


@pytest.mark.parametrize('reason', ('empty_target', 'failed_readout', 'zero_primary', 'negative_direction'))
def test_gate_failure_not_no_memory(reason):
    blocks = artificial_blocks()
    for b in blocks:
        if reason == 'empty_target': b['sources'][0, 1, 0] = 1.
        elif reason == 'failed_readout':
            b['values'][:, p.CASES.index((1, 0., 'full_alternative')), :, 0] = 1.
            b['values'][:, p.CASES.index((1, 0., 'full_alternative')), :, 1] = 0.
        elif reason == 'zero_primary':
            for r in (0, 1): b['values'][:, p.CASES.index((r, 0., 'alternative')), :, 1] = 0.
        else:
            b['values'][:, p.CASES.index((1, 0., 'alternative')), :, 0] = .15
    result = p.summarize(blocks)
    assert result['label'] == ('READOUT_NOT_QUALIFIED' if reason in ('empty_target', 'failed_readout')
                              else 'CONTEXT_STEERING_UNRESOLVED')
    assert result['independent_main_confirmation_run'] is False and result['absolute_fidelity_gate'] is None
    assert p.checker().check_summary(result, blocks, p.CONFIG)


@pytest.mark.parametrize('field', ('primary', 'readout_qualified', 'label', 'contrasts', 'cell_means', 'target_disagreement_cells'))
def test_summary_corruption(field):
    blocks = artificial_blocks(); bad = copy.deepcopy(p.summarize(blocks))
    if field == 'primary': bad[field]['mean'] += .1
    elif field == 'readout_qualified': bad[field] = False
    elif field == 'label': bad[field] = 'no memory'
    elif field == 'contrasts': bad[field].pop()
    elif field == 'cell_means': bad[field][0][0][0] += .1
    else: bad[field][0][0] = 0
    with pytest.raises(AssertionError): p.checker().check_summary(bad, blocks, p.CONFIG)


def test_saved_roundtrip(full_block, tmp_path):
    assert DEFAULT_EXTERNAL_ROOT in tmp_path.resolve().parents
    raw, meta = full_block
    saved = run.u.save_pair(tmp_path, 'block', raw, meta, DEFAULT_EXTERNAL_ROOT)
    assert p.checker().check_block(saved, run.u.read_json(tmp_path/'block.json'), p.CONFIG)
    with pytest.raises(FileExistsError): run.u.save_pair(tmp_path, 'block', raw, meta, DEFAULT_EXTERNAL_ROOT)


@pytest.mark.parametrize('cpus', ({0, 1, 2, 3, 4, 5}, {0, 1}, {6}, set(), set(range(7))))
def test_external_and_cpu_guards(monkeypatch, cpus):
    monkeypatch.setattr(os, 'sched_getaffinity', lambda pid: cpus)
    if cpus and cpus <= set(range(6)):
        assert run.preflight(DEFAULT_EXTERNAL_ROOT) == sorted(cpus)
    else:
        with pytest.raises(RuntimeError): run.preflight(DEFAULT_EXTERNAL_ROOT)


@pytest.mark.parametrize('key', ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'PYTHONDONTWRITEBYTECODE', 'TMPDIR', 'XDG_CACHE_HOME'))
def test_environment_guards(monkeypatch, key):
    monkeypatch.setenv(key, '2' if key.endswith('THREADS') else '/tmp')
    with pytest.raises(RuntimeError): run.preflight(DEFAULT_EXTERNAL_ROOT)


def test_storage_guard(monkeypatch):
    current = run.shutil.disk_usage(DEFAULT_EXTERNAL_ROOT)
    monkeypatch.setattr(run.shutil, 'disk_usage', lambda root: current._replace(free=run.RESERVE-1))
    with pytest.raises(RuntimeError): run.preflight(DEFAULT_EXTERNAL_ROOT, False)
    monkeypatch.setattr(run.shutil, 'disk_usage', lambda root: current._replace(free=run.RESERVE))
    run.preflight(DEFAULT_EXTERNAL_ROOT, False)
    with pytest.raises(RuntimeError): run.preflight(DEFAULT_EXTERNAL_ROOT, True)


def test_output_escape_rejected(tmp_path):
    with pytest.raises(ValueError): run.u.write_json(p.WS/'forbidden_d111.json', {}, DEFAULT_EXTERNAL_ROOT)
    with pytest.raises(ValueError): run.u.write_npz(p.WS/'forbidden_d111.npz', {}, DEFAULT_EXTERNAL_ROOT)
    (tmp_path/'alias').symlink_to(p.WS, target_is_directory=True)
    with pytest.raises(ValueError): run.u.write_json(tmp_path/'alias/forbidden_d111.json', {}, DEFAULT_EXTERNAL_ROOT)
    assert not (p.WS/'forbidden_d111.json').exists()


def test_reservation_guards(tmp_path, monkeypatch):
    monkeypatch.setattr(run, 'preflight', lambda *a, **k: None)
    monkeypatch.setattr(run, 'main_inputs', lambda *a: {})
    monkeypatch.setattr(run, 'timing_checked', lambda *a: {})
    (tmp_path/'runs'/p.RUN_ID).mkdir(parents=True)
    with pytest.raises(FileExistsError): run.prepare(tmp_path)
    assert not (tmp_path/'outputs').exists()
    with pytest.raises(FileNotFoundError): run.detached_guard(tmp_path, True)


def test_fresh_process_import():
    script = 'from laws_confirmation import l16_body_content as p; c=p.context(p.DISPOSABLE); assert c["bp"].rho==.002; print("ok")'
    process = subprocess.run([sys.executable, '-c', script], env=os.environ.copy(), cwd=p.WS,
                             capture_output=True, text=True, check=True)
    assert process.stdout.strip() == 'ok'


def test_contract_scope():
    contract = run.contract()
    assert contract['workers'] == 6 and contract['cpu_affinity_max'] == list(range(6))
    assert contract['qualification_only'] is True and contract['main_confirmation'] is False
    assert contract['branch_paths'] == 384 and contract['exact_sham_aliases'] == 64
    assert len(run.output_names()) == 19 and len(set(p.CASES)) == 24
    assert not set(p.TISSUES) & (set(range(6)) | {p.DISPOSABLE})
    assert p.injury_mask().sum() == 64 and not p.injury_mask()[0, 0]
    assert 'no polling' in (p.WS/'protocols/L16_BODY_CONTENT_V1.md').read_text()
