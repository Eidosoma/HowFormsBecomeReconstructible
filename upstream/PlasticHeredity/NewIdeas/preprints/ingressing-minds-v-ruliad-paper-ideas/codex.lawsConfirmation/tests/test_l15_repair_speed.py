"""D097 synthetic and short-disposable validation; no main-cohort futures."""
from copy import deepcopy
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from laws_confirmation import l15_repair_speed as p
from laws_confirmation import l15_repair_speed_run as run
from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT as ROOT, canonical_digest, require_beneath

SHORT = replace(p.CONFIG, settle=4, recovery=8, times=(0,1,4,8), primary_time=4)


@pytest.fixture(scope='module')
def block():
    return p.execute_block(p.DISPOSABLE,SHORT)


@pytest.fixture
def piece(block):
    raw, meta = deepcopy(block)
    return ({k:np.asarray(v[0]) for k,v in raw.items()},meta['lives'][0])


def test_frozen_design():
    assert p.TISSUES == tuple(range(43000,43008)) and p.DISPOSABLE not in p.TISSUES
    assert p.CONFIG == p.Config() and p.CONFIG.primary_time == 80 and p.CONFIG.recovery == 500
    assert p.RATES == (.002,.01,.05) and p.GAINS == (.2,0.)
    assert len(set(p.CASES)) == 12 and p.contract()['main_futures'] == 192
    assert run.contract()['output_hash_count'] == len(run.output_names()) == 19
    assert len(run.SOURCE_UNITS) == 36


@pytest.mark.parametrize('changes',[
    dict(lives=0),dict(lives=True),dict(lives=1.5),dict(settle=-1),dict(recovery=0),
    dict(times=()),dict(times=(0,)),dict(times=[0,1,80,500]),dict(times=(0,1,1,80,500)),
    dict(times=(0,1,500,80)),dict(times=(0,80,500)),dict(times=(0,1,80,501)),
    dict(primary_time=3),dict(primary_time=True),dict(distance=2),dict(distance=12),
    dict(strip_width=0),dict(magnitude=0),dict(magnitude=float('nan')),dict(magnitude=float('inf'))])
def test_config_rejects_invalid(changes):
    with pytest.raises(ValueError):
        replace(p.CONFIG,**changes)


@pytest.mark.parametrize('identity',[-1,True,1.5,'43000'])
def test_identity_validation(identity):
    with pytest.raises(ValueError):
        p.context(identity)


def test_rng_address_is_explicit_pcg64():
    a = p.rng(p.DISPOSABLE,0,'settle'); b = p.rng(p.DISPOSABLE,0,'settle')
    assert type(a.bit_generator) is np.random.PCG64
    np.testing.assert_array_equal(a.standard_normal(10),b.standard_normal(10))
    hashes = {canonical_digest(p.rng(i,l,phase).bit_generator.state)
        for i in (p.DISPOSABLE,p.DISPOSABLE+1) for l in (0,1) for phase in ('settle','recover','bootstrap')}
    assert len(hashes) == 12


def test_displacement_keeps_reference_and_mean():
    v = np.arange(256,dtype=float).reshape(1,16,16)/100
    old = v.copy(); shifted = p.displaced(v)
    np.testing.assert_array_equal(v,old)
    expected = np.zeros_like(v); expected[:,:,2:5] = -.8; expected[:,:,10:13] = .8
    np.testing.assert_allclose(shifted-v,expected,rtol=0,atol=5e-16)
    assert abs((shifted-v).mean()) < 1e-16
    assert abs(abs(shifted.mean(axis=1)-v.mean(axis=1)).mean()-.3) < 1e-15


def test_fresh_process_import():
    command = [sys.executable,'-c',
        'from laws_confirmation.l15_repair_speed import api; '
        'a=api(); assert a["original"].__name__ == "triangle_final.pipeline"; print("imports only")']
    result = subprocess.run(command,cwd=p.WS,env=os.environ.copy(),check=True,capture_output=True,text=True)
    assert result.stdout.strip() == 'imports only'


def test_dynamic_complete_block_replay(block):
    raw,meta = block
    assert p.checker().check_block(raw,meta,SHORT,replay=True)
    assert max(m['replay']['max_abs'] for m in meta['lives']) == 0.
    assert all(m['exact_alias_futures']==3 for m in meta['lives'])


def test_dynamic_matched_body_and_reference_controls(piece):
    raw,meta = piece; states = raw['states']
    for ci,case in enumerate(p.CASES):
        np.testing.assert_array_equal(states[ci,0,2],raw['settled'][2])
        expected = p.displaced(raw['settled'][0]) if case[2] else raw['settled'][0]
        np.testing.assert_array_equal(states[ci,0,0],expected)
        np.testing.assert_array_equal(states[ci,0,1],expected)
    for ci in range(4):
        for offset in (4,8):
            np.testing.assert_array_equal(states[ci,:2,:2],states[ci+offset,:2,:2])
            if ci >= 2:
                np.testing.assert_array_equal(states[ci,:,:2],states[ci+offset,:,:2])
    assert not np.array_equal(states[2,-1,2],states[10,-1,2]), 'off reader still permits reference updating'
    assert len(set(meta['recovery_rng'])) == 1


def test_dynamic_order_and_duplicate_aliases(piece):
    raw,meta = piece
    order = (p.CASES[8],p.CASES[0],p.CASES[1],p.CASES[0])
    shuffled, sm = p.simulate_life(p.DISPOSABLE,0,SHORT,cases=order)
    for i,j in enumerate((8,0,1,0)):
        np.testing.assert_array_equal(shuffled['states'][i],raw['states'][j])
        assert sm['recovery_rng'][i] == meta['recovery_rng'][j]


def test_dynamic_native_theta_has_no_projection_or_writes(piece):
    raw,meta = piece; ctx = p.context(p.DISPOSABLE)
    from voltage_web.engine import make_thresholds
    np.testing.assert_array_equal(raw['theta'],make_thresholds(ctx['tissue']))
    assert abs(raw['theta'].mean()) > 1e-6 and abs(raw['theta'].std()-.3) > 1e-6
    assert meta['theta_writable'] is False


@pytest.mark.parametrize('arm',['D','T','T_lesion'])
def test_dynamic_short_source_bridge(arm):
    a = p.api(); old = (a['original'].settle_with_blueprint,a['original'].blueprint_step)
    cfg = replace(a['TriangleConfig'](),futures=2,settle_sweeps=4,recovery_sweeps=5)
    raw,meta = p.source_control(arm,p.DISPOSABLE,cfg)
    assert meta['replay']['max_abs'] == 0 and p.checker().check_source(raw,meta)['full_source_replay']
    assert (a['original'].settle_with_blueprint,a['original'].blueprint_step) == old


def test_source_wrappers_restore_after_error(monkeypatch):
    a = p.api(); original = a['original']; old = (original.settle_with_blueprint,original.blueprint_step)
    def broken(*args,**kwargs):
        raise RuntimeError('injected source failure')
    monkeypatch.setattr(original,'transport',broken)
    with pytest.raises(RuntimeError,match='injected'):
        p.source_control('T',p.DISPOSABLE)
    assert (original.settle_with_blueprint,original.blueprint_step) == old


@pytest.mark.parametrize('field',['theta','settled','states','values','initial_error'])
def test_state_corruptions_rejected(piece,field):
    raw,meta = piece
    raw[field].flat[0] += .01
    with pytest.raises(AssertionError):
        p.checker().check_life(raw,meta,SHORT)


@pytest.mark.parametrize('field',['settle_rng','recovery_rng','index','life','theta_writable','cases','config'])
def test_metadata_corruptions_rejected(piece,field):
    raw,meta = piece
    if field == 'recovery_rng': meta[field][0] = 'bad'
    elif field == 'cases': meta[field].reverse()
    elif field == 'config': meta[field]['settle'] += 1
    elif field == 'index': meta[field] += 1
    elif field == 'life': meta[field] = True
    elif field == 'theta_writable': meta[field] = True
    else: meta[field] = 'bad'
    with pytest.raises(AssertionError):
        p.checker().check_life(raw,meta,SHORT)


@pytest.mark.parametrize('bad',[float('nan'),float('inf'),-float('inf')])
def test_nonfinite_state_rejected(piece,bad):
    raw,meta = piece; raw['states'].flat[7] = bad
    with pytest.raises(AssertionError):
        p.checker().check_life(raw,meta,SHORT)


def test_no_denominator_floor(block):
    raw,_ = deepcopy(block); raw['initial_error'][0] = 0
    with pytest.raises(ValueError):
        p.summarize([raw]*8,SHORT)


def test_metrics_distinguish_repair_from_agreement():
    settled = np.zeros((3,16,16)); settled[:,:, :8] = 1.; settled[:,:,8:] = -1.
    damaged = -settled[0]
    states = np.stack([np.stack([np.stack([damaged,damaged,damaged])])])
    values = p.measure(states,settled)
    assert values[0,0,6] == 0 and values[0,0,1] == 0 and values[0,0,4] == 0
    assert values[0,0,0] == 2 and values[0,0,5] == 2
    np.testing.assert_array_equal(values,p.checker().metrics(states,settled))


def test_hand_built_block_pooling():
    blocks = []
    for i in range(8):
        values = np.zeros((2,12,len(SHORT.times),10))
        values[:,8,:,0] = np.array([i/10,(i+2)/10])[:,None]
        blocks.append(dict(values=values,initial_error=np.ones(2)))
    result = p.summarize(blocks,SHORT); primary = result['primary']
    expected = [[i/10,(i+2)/10] for i in range(8)]
    np.testing.assert_allclose(primary['life_values'],expected,rtol=0,atol=1e-15)
    assert abs(primary['mean']-.45) < 1e-15 and primary['block_positive'] == 8
    draws = p.rng(0,0,'bootstrap').integers(0,8,(10000,8))
    b = np.mean(expected,axis=1)
    np.testing.assert_allclose(primary['pointwise_block_bootstrap_95'],np.quantile(b[draws].mean(1),(.025,.975)))
    assert primary['life_tied'] == 1 and result['main_futures'] == 192


def test_scores_are_not_clipped_probabilities():
    values = np.zeros((2,12,len(SHORT.times),10)); values[:,1,:,0] = .6
    result = p.summarize([dict(values=values,initial_error=np.full(2,.3))]*8,SHORT)
    assert result['adjusted_repair_means'][0][0] == 3.


def test_saved_summary_corruptions(block):
    raw,_ = block; blocks = [raw]*8; summary = p.summarize(blocks,SHORT)
    assert p.checker().check_summary(summary,blocks,SHORT)
    variants = []
    wrong = deepcopy(summary); wrong['primary']['mean'] += .01; variants.append(wrong)
    wrong = deepcopy(summary); wrong['primary']['pointwise_block_bootstrap_95'][0] += .01; variants.append(wrong)
    wrong = deepcopy(summary); wrong['contrasts'].reverse(); variants.append(wrong)
    wrong = deepcopy(summary); wrong['cell_means'][0][0][0] += .01; variants.append(wrong)
    wrong = deepcopy(summary); wrong['blocks'] = 16; variants.append(wrong)
    wrong = deepcopy(summary); wrong['main_futures'] = True; variants.append(wrong)
    wrong = deepcopy(summary); wrong['score_cases'].reverse(); variants.append(wrong)
    for wrong in variants:
        with pytest.raises(AssertionError):
            p.checker().check_summary(wrong,blocks,SHORT)


def test_complete_table_required(block):
    raw,_ = block
    with pytest.raises(ValueError): p.summarize([raw]*7,SHORT)
    wrong = deepcopy(raw); wrong['values'] = wrong['values'][:1]
    with pytest.raises(ValueError): p.summarize([wrong]*8,SHORT)


def test_source_retained_coverage():
    expected = run.source_expected()
    assert set(expected) == set(run.SOURCE_UNITS)
    assert p.api()['TriangleConfig']().digest() == p.SOURCE_DIGEST


def test_known_post_audit_case_revision_is_exactly_pinned():
    paths = run.science_paths(ROOT)
    assert len(paths) == len(set(paths)) and p.WS/'laws/L15_timescale.md' in paths
    assert run.contract()['historical_inputs_hash_match'] == 110
    assert run.sha256_file(Path(run.LEGACY_CASE['path'])) == run.LEGACY_CASE['current_sha256']


@pytest.mark.parametrize('target',['laws/L15_timescale.md','../blueprint_web/src/blueprint_web/engine.py'])
def test_unrecognized_baseline_drift_is_not_waived(monkeypatch,target):
    original = run.sha256_file; path = (p.WS/target).resolve()
    monkeypatch.setattr(run,'sha256_file',lambda x: 'bad' if Path(x).resolve()==path else original(x))
    with pytest.raises(AssertionError):
        run.science_paths(ROOT)


def test_write_once_roundtrip(tmp_path,block):
    require_beneath(tmp_path,ROOT)
    raw,meta = block
    loaded = run.save_pair(tmp_path,'fixture',raw,meta,ROOT)
    assert p.checker().check_block(loaded,run.read_json(tmp_path/'fixture.json'),SHORT,replay=False)
    with pytest.raises(FileExistsError): run.write_json(tmp_path/'fixture.json',{},ROOT)
    with pytest.raises(FileExistsError): run.write_npz(tmp_path/'fixture.npz',raw,ROOT)
    assert len(run.hashes([tmp_path/'fixture.json',tmp_path/'fixture.npz'])) == 2


@pytest.mark.parametrize('payload',['{"a":1,"a":2}','{"x":NaN}','{"x":Infinity}','{"x":-Infinity}'])
def test_strict_json_read(tmp_path,payload):
    require_beneath(tmp_path,ROOT)
    path = tmp_path/'bad.json'; path.write_text(payload)
    with pytest.raises(ValueError): run.read_json(path)


def test_paths_and_duplicate_hashes(tmp_path):
    require_beneath(tmp_path,ROOT)
    path = tmp_path/'ok.json'; run.write_json(path,{},ROOT)
    with pytest.raises(AssertionError): run.hashes([path,path])
    link = tmp_path/'link.json'; link.symlink_to(path)
    with pytest.raises(AssertionError): run.hashes([link])
    with pytest.raises(ValueError): run.write_json(link,{},ROOT)
    with pytest.raises(ValueError): run.write_json(p.WS/'forbidden_test_output.json',{},ROOT)


def test_preflight_and_storage_gate(monkeypatch):
    assert 1 <= len(run.preflight(ROOT)) <= 4
    usage = run.shutil.disk_usage(ROOT)
    monkeypatch.setattr(run.shutil,'disk_usage',lambda root: usage._replace(free=run.RESERVE+run.ALLOWANCE-1))
    with pytest.raises(RuntimeError,match='reserve'): run.preflight(ROOT)
    assert run.preflight(ROOT,starting=False)


@pytest.mark.parametrize('variable',['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS',
                                    'NUMEXPR_NUM_THREADS','PYTHONDONTWRITEBYTECODE','TMPDIR','XDG_CACHE_HOME'])
def test_environment_gates(monkeypatch,variable):
    monkeypatch.setenv(variable,'0')
    with pytest.raises(RuntimeError): run.preflight(ROOT)


def test_failure_marker_is_not_retryable(tmp_path):
    require_beneath(tmp_path,ROOT)
    try:
        raise RuntimeError('synthetic failure')
    except RuntimeError as error:
        run.failure(tmp_path,error,ROOT)
    saved = run.read_json(tmp_path/'FAILED.json')
    assert saved['automatic_retry'] is False and 'synthetic failure' in saved['traceback']
    with pytest.raises(FileExistsError): run.failure(tmp_path,RuntimeError('retry'),ROOT)


def test_test_proof_rejects_wrong_path(tmp_path):
    with pytest.raises(ValueError): run.test_proof(tmp_path/'proof.xml',ROOT)


def test_detach_guard_requires_real_detached_identity(tmp_path):
    with pytest.raises(FileNotFoundError): run.detached_guard(tmp_path,True)


def test_benchmark_threshold_is_ten_minutes():
    assert run.contract()['detach_above_seconds'] == 600
    assert run.RESERVE == 4*1024**3 and run.ALLOWANCE == 512*1024**2
