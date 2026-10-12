import copy
import os
import subprocess
import sys

import numpy as np
import pytest

from laws_confirmation import l16_body_content as previous
from laws_confirmation import l16_body_content_run as previous_run
from laws_confirmation import l16_body_content_confirmation as p
from laws_confirmation import l16_body_content_confirmation_run as run
from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT


def test_d111_saved_anchor():
    directory = previous_run.benchmark_dir(DEFAULT_EXTERNAL_ROOT)
    saved = run.u.load_npz(directory/f'block_{previous.DISPOSABLE}.npz')
    metadata = run.u.read_json(directory/f'block_{previous.DISPOSABLE}.json')
    raw, meta = previous.execute_block(previous.DISPOSABLE)
    assert set(raw) == set(saved)
    for key in raw:
        np.testing.assert_array_equal(raw[key], saved[key])
    previous.checker().nested(meta, metadata)
    assert previous.checker().check_block(saved, metadata, previous.CONFIG)


@pytest.fixture(scope='module')
def full_block():
    # First requested by the next test, so its JUnit setup includes full timing.
    # Never execute a 57000-series main future in the technical suite.
    return p.execute_block(p.DISPOSABLE)


def test_confirmation_disposable_full_replay(full_block):
    raw, meta = full_block
    assert meta['index'] == p.DISPOSABLE and p.DISPOSABLE not in p.TISSUES
    assert meta['run_id'] == p.RUN_ID
    assert p.checker().check_block(raw, meta, p.CONFIG, replay=False)
    assert all(m['replay']['dynamics_max_abs'] == 0 for m in meta['lives'])
    assert all(m['replay']['metric_max_abs'] <= 1e-12 for m in meta['lives'])
    assert sum(m['replay']['exact_sham_aliases'] for m in meta['lives']) == 8


def test_confirmation_unchanged_raw():
    cfg = previous.Config(lives=1, settle=4, recovery=3, times=(0, 1, 3))
    old_raw, old_meta = previous.execute_block(p.DISPOSABLE, cfg)
    raw, meta = p.execute_block(p.DISPOSABLE, cfg)
    assert set(old_raw) == set(raw)
    for key in raw:
        np.testing.assert_array_equal(raw[key], old_raw[key])
    assert meta == old_meta | dict(run_id=p.RUN_ID)
    assert p.checker().check_block(raw, meta, cfg, replay=True)


@pytest.mark.parametrize('index', (True, False, 0, -1, 56000, 56007, 57008, 514211, 57000., '57000', None))
def test_old_cohort_rejected(index):
    with pytest.raises(ValueError):
        p.execute_block(index)


@pytest.mark.parametrize('field', ('old_run', 'old_index', 'float_index', 'extra', 'missing_run', 'life_index'))
def test_cohort_metadata_corruption(full_block, field):
    raw, meta = full_block
    bad = copy.deepcopy(meta)
    if field == 'old_run': bad['run_id'] = previous.RUN_ID
    elif field == 'old_index': bad['index'] = previous.DISPOSABLE
    elif field == 'float_index': bad['index'] = float(p.DISPOSABLE)
    elif field == 'extra': bad['pooled'] = True
    elif field == 'missing_run': bad.pop('run_id')
    else: bad['lives'][0]['index'] = previous.DISPOSABLE
    with pytest.raises(AssertionError):
        p.checker().check_block(raw, bad, p.CONFIG)


@pytest.mark.parametrize('field', ('theta', 'sources', 'states', 'values', 'permutations'))
def test_confirmation_raw_corruption(full_block, field):
    raw, meta = full_block
    bad = {k: v.copy() for k, v in raw.items()}
    bad[field].flat[-1] += 1
    with pytest.raises(AssertionError):
        p.checker().check_block(bad, meta, p.CONFIG, replay=True)


def artificial_blocks():
    # Algebra only, without new main-cohort physics or observations.
    sources = np.zeros((2, 2, 3, 16, 16), dtype=np.float64)
    sources[:, 0, 0] = 1.; sources[:, 1, 0] = -1.
    values = np.zeros((2, 24, len(p.CONFIG.times), 9), dtype=np.float64)
    for role in (0, 1):
        values[:, p.CASES.index((role, 0., 'full_own')), :, 0] = 1.
        values[:, p.CASES.index((role, 0., 'full_alternative')), :, 1] = 1.
        values[:, p.CASES.index((role, 0., 'alternative')), :, 1] = .1
    return [dict(sources=sources.copy(), values=values.copy()) for _ in range(8)]


def test_summary_numeric_identity():
    blocks = artificial_blocks()
    for index, block in enumerate(blocks):
        for role in (0, 1):
            block['values'][0, p.CASES.index((role, 0., 'alternative')), :, 1] += index/100
    before = copy.deepcopy(blocks)
    old = previous.summarize(blocks)
    new = p.summarize(blocks)
    changed = {'schema', 'tissues', 'independent_main_confirmation_run', 'label'}
    assert set(new) == set(old)
    assert {k: v for k, v in new.items() if k not in changed} == {k: v for k, v in old.items() if k not in changed}
    assert new['label'] == 'CONFIRMED_CONTEXT_STEERING'
    assert new['primary']['mean'] == pytest.approx(.1175)
    assert len(new['contrasts']) == 100
    assert p.checker().check_summary(new, blocks, p.CONFIG)
    for a, b in zip(before, blocks):
        for key in a: np.testing.assert_array_equal(a[key], b[key])


@pytest.mark.parametrize('field', ('schema', 'tissues', 'independent_main_confirmation_run', 'label',
    'primary', 'contrasts', 'cell_means', 'readout_qualified', 'target_disagreement_cells', 'extra'))
def test_confirmation_summary_corruption(field):
    blocks = artificial_blocks()
    bad = copy.deepcopy(p.summarize(blocks))
    if field == 'schema': bad[field] = 'l16_body_content_qualification_v1'
    elif field == 'tissues': bad[field] = list(previous.TISSUES)
    elif field == 'independent_main_confirmation_run': bad[field] = False
    elif field == 'label': bad[field] = 'QUALIFIED_CONTEXT_STEERING'
    elif field == 'primary': bad[field]['mean'] += .1
    elif field == 'contrasts': bad[field].pop()
    elif field == 'cell_means': bad[field][0][0][0] += .1
    elif field == 'readout_qualified': bad[field] = False
    elif field == 'target_disagreement_cells': bad[field][0][0] = 0
    else: bad[field] = 'unreported adaptation'
    with pytest.raises(AssertionError):
        p.checker().check_summary(bad, blocks, p.CONFIG)


@pytest.mark.parametrize('reason', ('empty_target', 'failed_readout', 'zero_primary', 'negative_direction'))
def test_qualification_failures_preserved(reason):
    blocks = artificial_blocks()
    for b in blocks:
        if reason == 'empty_target': b['sources'][0, 1, 0] = 1.
        elif reason == 'failed_readout':
            b['values'][:, p.CASES.index((1, 0., 'full_alternative')), :, 0] = 1.
            b['values'][:, p.CASES.index((1, 0., 'full_alternative')), :, 1] = 0.
        elif reason == 'zero_primary':
            for r in (0, 1): b['values'][:, p.CASES.index((r, 0., 'alternative')), :, 1] = 0.
        else: b['values'][:, p.CASES.index((1, 0., 'alternative')), :, 0] = .15
    result = p.summarize(blocks)
    assert result['label'] == previous.summarize(blocks)['label']
    assert result['label'] == ('READOUT_NOT_QUALIFIED' if reason in ('empty_target', 'failed_readout')
                               else 'CONTEXT_STEERING_UNRESOLVED')
    assert result['absolute_fidelity_gate'] is None
    assert p.checker().check_summary(result, blocks, p.CONFIG)


def test_checker_does_not_call_production_summary(monkeypatch):
    blocks = artificial_blocks(); summary = p.summarize(blocks)
    def forbidden(*args, **kwargs): raise RuntimeError('production summary forbidden')
    monkeypatch.setattr(p, 'summarize', forbidden)
    monkeypatch.setattr(previous, 'summarize', forbidden)
    assert p.checker().check_summary(summary, blocks, p.CONFIG)


def test_confirmation_external_roundtrip(full_block, tmp_path):
    assert DEFAULT_EXTERNAL_ROOT in tmp_path.resolve().parents
    raw, meta = full_block
    saved = run.u.save_pair(tmp_path, 'block', raw, meta, DEFAULT_EXTERNAL_ROOT)
    assert p.checker().check_block(saved, run.u.read_json(tmp_path/'block.json'), p.CONFIG)
    with pytest.raises(FileExistsError): run.u.save_pair(tmp_path, 'block', raw, meta, DEFAULT_EXTERNAL_ROOT)


@pytest.mark.parametrize('cpus', ({0, 1, 2, 3, 4, 5}, {0, 1}, {6}, set(), set(range(7))))
def test_confirmation_resource_guards(monkeypatch, cpus):
    monkeypatch.setattr(os, 'sched_getaffinity', lambda pid: cpus)
    if cpus and cpus <= set(range(6)):
        assert run.preflight(DEFAULT_EXTERNAL_ROOT) == sorted(cpus)
    else:
        with pytest.raises(RuntimeError): run.preflight(DEFAULT_EXTERNAL_ROOT)


def test_confirmation_reservation_guards(tmp_path, monkeypatch):
    monkeypatch.setattr(run, 'preflight', lambda *a, **k: None)
    monkeypatch.setattr(run, 'main_inputs', lambda *a: {})
    monkeypatch.setattr(run, 'timing_checked', lambda *a: {})
    (tmp_path/'runs'/p.RUN_ID).mkdir(parents=True)
    with pytest.raises(FileExistsError): run.prepare(tmp_path)
    assert not (tmp_path/'outputs').exists()
    with pytest.raises(FileNotFoundError): run.detached_guard(tmp_path, True)


def test_prior_saved_audit():
    result = previous_run.audit(DEFAULT_EXTERNAL_ROOT)
    assert result['passes'] and result['input_hashes'] == 122
    assert result['output_hashes'] == 19 and result['label'] == 'QUALIFIED_CONTEXT_STEERING'


def test_confirmation_does_not_mutate_d111():
    old = copy.deepcopy(previous.contract())
    cfg = previous.Config(lives=1, settle=4, recovery=3, times=(0, 1, 3))
    p.execute_block(p.DISPOSABLE, cfg)
    p.summarize(artificial_blocks()); p.contract(); p.checker()
    assert previous.contract() == old
    assert previous.TISSUES == tuple(range(56000, 56008))
    assert previous.DISPOSABLE == 514211
    assert p.CONFIG is previous.CONFIG and p.TAG == previous.TAG


def test_fresh_confirmation_process_import():
    script = ('from laws_confirmation import l16_body_content_confirmation as p; '
              'assert p.TISSUES==tuple(range(57000,57008)); '
              'assert p.base.context(p.DISPOSABLE)["bp"].rho==.002; '
              'assert p.base.DISPOSABLE==514211; print("ok")')
    result = subprocess.run([sys.executable, '-c', script], env=os.environ.copy(), cwd=p.WS,
                            capture_output=True, text=True, check=True)
    assert result.stdout.strip() == 'ok'


def test_confirmation_contract_scope():
    contract = run.contract()
    assert contract['workers'] == 6 and contract['cpu_affinity_max'] == list(range(6))
    assert contract['qualification_only'] is False and contract['main_confirmation'] is True
    assert contract['prior_observations_pooled'] is False and contract['independent_implementation'] is False
    assert contract['branch_paths'] == 384 and contract['exact_sham_aliases'] == 64
    assert len(run.output_names()) == len(set(run.output_names())) == 19
    assert contract['source_jobs'] == contract['source_branches'] == 0
    assert not set(p.TISSUES) & {*previous.TISSUES, previous.DISPOSABLE, p.DISPOSABLE}
    assert contract['detach_above_seconds'] == 600
    assert contract['positive_label'] == 'CONFIRMED_CONTEXT_STEERING'
    assert 'without polling' in (p.WS/'protocols/L16_BODY_CONTENT_CONFIRMATION_V1.md').read_text()
