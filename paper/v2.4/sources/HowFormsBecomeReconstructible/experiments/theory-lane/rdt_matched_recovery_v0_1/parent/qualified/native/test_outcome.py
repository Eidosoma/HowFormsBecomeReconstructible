"""Failure injection and reduced-step integration; no scientific future labels."""
import copy
import hashlib
from pathlib import Path
import time

import numpy as np
import pytest
from scipy.stats import t

from bridge import ROOT, P, e, ev, read
import execute
import futures
import ledger
import pipeline
import probes
import scoring
import verify_science


class Guard:
    def check(self):
        pass

    def account(self, folder):
        pass


@pytest.fixture
def short_reader(monkeypatch):
    for config in (P['reader'], e.DESIGN['reader']):
        for key, value in dict(read_steps=24, settling_steps=12, observe_steps=4).items():
            monkeypatch.setitem(config, key, value)


def artificial_scores():
    spec = pipeline.specification('native_qualification')
    forecasts, outcomes = [], []
    for index, key in enumerate(spec['keys']):
        for regime in scoring.REGIMES:
            forecasts.append(dict(key=key, block=key[0], history=key[1], current_pass=0,
                regime=regime, probabilities=dict(candidate=1. if index == 0 else .2,
                    direct_rival=.6, tt008=.7)))
            outcomes.append(dict(key=key, regime=regime, passed=index%2))
    return spec, forecasts, outcomes


def test_production_contract_and_unchanged_models():
    spec = pipeline.specification('outcome')
    assert spec['blocks'] == list(range(304))
    assert len(spec['keys']) == len({tuple(k) for k in spec['keys']}) == 19456
    assert spec['records_per_block'] == 64
    assert ev.sha(ROOT/'FROZEN_MODELS.json') == 'ba3b00ce745467d6eba9b4c098468f9e80c8858b689d4b6b2d93af045affc0ce'
    parent = read(ROOT/'context/previous_protocol.json')
    assert P['reader'] == parent['reader']
    assert P['writer'] == parent['writer']
    assert P['analysis']['margins'] == parent['analysis']['margins']
    assert P['outcome']['horizon_rebuilds'] == 18
    assert P['prediction']['probe_indices'] == list(range(32))
    assert P['prediction']['direct_probe_indices'] == list(range(8))
    assert P['resources']['outcome_wall_ceiling_seconds'] == 20*86400


def test_stream_separation_and_paired_noise(short_reader):
    key = pipeline.specification('native_qualification')['keys'][0]
    a = futures.environment('qualification', key, 15, 'writer', 'matched')
    b = futures.environment('qualification', key, 15, 'writer', 'independent')
    c = futures.environment('qualification', key, 16, 'writer', 'matched')
    d = probes.environment('qualification', key, 15, 'writer', 'matched')
    assert a[0].sum() == 24 and not (a[0] & e.PORTS.any(axis=0)).any()
    assert np.array_equal(a[0], b[0])
    assert np.array_equal(a[1][0], b[1][0]) and np.array_equal(a[2][:,0], b[2][:,0])
    assert np.array_equal(a[1][0], a[1][1]) and np.array_equal(a[2][:,0], a[2][:,1])
    assert not np.array_equal(b[1][0], b[1][1]) and not np.array_equal(b[2][:,0], b[2][:,1])
    assert not np.array_equal(a[2], c[2]) and not np.array_equal(a[2], d[2])
    assert a[2].tobytes() == futures.environment('qualification', key, 15, 'writer', 'matched')[2].tobytes()


@pytest.mark.parametrize('level,expected', [(.25,0), (np.nextafter(.25,1.),1), (np.nextafter(.25,0.),0)])
@pytest.mark.parametrize('rule', [-1,1])
def test_strict_task_threshold(short_reader, level, expected, rule):
    windows = np.broadcast_to(level*rule*np.array([[1.,-1.],[-1.,1.]]), (1,4,1,2,2)).copy()
    assert futures.terminal_scores(windows, [dict(rule=rule)])['terminal_passed'].tolist() == [expected]


def test_eighteen_rewrites_then_discard_terminal_output(short_reader, monkeypatch, tmp_path):
    initial = np.zeros((2,16,16))
    row = dict(key=[-2,P['acquisition']['histories'][0],0,0], rule=1,
               packet_sha256=hashlib.sha256(initial.tobytes()).hexdigest())
    calls = []
    def read_batch(incoming, environments):
        calls.append(incoming.copy())
        signal = .5 if len(calls) == 19 else -.5
        windows = np.broadcast_to(signal*np.array([[1.,-1.],[-1.,1.]]), (1,4,1,2,2)).copy()
        return dict(end=np.zeros((1,1,2,16,16)), windows=windows, outgoing=incoming+1.)
    monkeypatch.setattr(futures.fast_reader, 'read_batch', read_batch)
    seal = tmp_path/'seal.json'
    ledger.atomic_json(seal, {'fixture': True})
    receipt, outcomes = futures.batch([row], [initial], ['absent'], 'matched', 'qualification',
                                     tmp_path/'future', Guard(), seal, ev.sha(seal))
    raw = ev.load(tmp_path/'future.npz', receipt['raw_sha256'])
    assert len(calls) == 19
    assert [v[0,0,0,0,0] for v in calls] == list(range(19))
    assert np.all(raw['g32_packets'] == 18.) and np.all(raw['outgoing'][-1] == 19.)
    assert outcomes[0]['passed'] == 1  # Earlier expression failures never stopped the path.
    verify_science.continuation(tmp_path, [row], outcomes, P['reader'], ev.sha(seal), ['absent'])
    seal.write_text('{}')
    with pytest.raises(ValueError, match='seal'):
        futures.batch([row], [initial], ['absent'], 'matched', 'qualification',
                      tmp_path/'forbidden', Guard(), seal, receipt['forecast_seal_sha256'])
    assert len(calls) == 19


def test_block_inference_calibration_and_empty_strata():
    spec, forecasts, outcomes = artificial_scores()
    result = scoring.analyze(forecasts, outcomes, spec)
    verify_science.analysis(forecasts, outcomes, result, spec['blocks'])
    group = result['regimes']['matched']
    values = group['primary']['tt008']['block_values']
    assert len(values) == 2
    radius = t.ppf(.975,1)*np.std(values,ddof=1)/np.sqrt(2.)
    assert group['primary']['tt008']['lower'] == pytest.approx(np.mean(values)-radius)
    assert group['calibration']['candidate'][9]['records'] == 1
    assert group['calibration']['candidate'][9]['mean_prediction'] == 1.
    empty = group['strata']['current_pass']['1']
    assert empty['records'] == empty['contributing_blocks'] == 0
    assert all(v is None for v in empty['conditional_brier'].values())
    assert empty['additive_contrasts']['tt008']['block_values'] == [0.,0.]
    for strata in group['strata'].values():
        for rival in scoring.MARGINS:
            terms = [row['additive_contrasts'][rival]['block_values'] for row in strata.values()]
            np.testing.assert_allclose(np.sum(terms,axis=0), group['primary'][rival]['block_values'],atol=1e-15)
            assert all('decision' not in row['additive_contrasts'][rival] for row in strata.values())
    assert result['new_model_fits'] == 0


@pytest.mark.parametrize('mutation', ['duplicate_forecast','missing_outcome','extra_outcome','invalid_probability','wrong_metadata','nonbinary'])
def test_incomplete_or_invalid_cohort_cannot_score(mutation):
    spec, forecasts, outcomes = artificial_scores()
    if mutation == 'duplicate_forecast': forecasts.append(copy.deepcopy(forecasts[0]))
    elif mutation == 'missing_outcome': outcomes.pop()
    elif mutation == 'extra_outcome': outcomes.append(dict(key=[999,'bad',0,0],regime='matched',passed=1))
    elif mutation == 'invalid_probability': forecasts[0]['probabilities']['candidate'] = float('nan')
    elif mutation == 'wrong_metadata': forecasts[0]['block'] = 7
    else: outcomes[0]['passed'] = .5
    with pytest.raises(ValueError): scoring.analyze(forecasts,outcomes,spec)


def test_decision_boundaries_and_independent_disagreement():
    assert scoring.limits([.002,.002],.002)['decision'] == 'REJECTED'
    assert scoring.limits([.003,.003],.002)['decision'] == 'SUPPORTED'
    assert scoring.limits([-.1,.1],.002)['decision'] == 'UNRESOLVED'
    spec, forecasts, outcomes = artificial_scores()
    result = scoring.analyze(forecasts,outcomes,spec)
    result['regimes']['matched']['primary']['tt008']['mean_gain'] += .01
    with pytest.raises(ArithmeticError):
        verify_science.analysis(forecasts,outcomes,result,spec['blocks'])


def test_commit_tampering_partial_attempts_and_duplicate_rejection(tmp_path):
    partial = ledger.new_attempt(tmp_path/'unit')
    (partial/'partial.txt').write_text('preserved')
    assert ledger.existing(tmp_path/'unit', {'fixed':1}) is None
    complete = ledger.new_attempt(tmp_path/'unit')
    (complete/'raw.txt').write_text('evidence')
    ledger.commit(complete, {'fixed':1}, {'ok':True})
    assert partial.exists() and complete.name == 'attempt_0002'
    assert ledger.existing(tmp_path/'unit',{'fixed':1})[0] == complete
    with pytest.raises(ValueError, match='identity'):
        ledger.existing(tmp_path/'unit',{'fixed':2})
    (complete/'raw.txt').write_text('tampered')
    with pytest.raises(ValueError, match='changed'):
        ledger.existing(tmp_path/'unit',{'fixed':1})
    (complete/'raw.txt').write_text('evidence')
    duplicate = ledger.new_attempt(tmp_path/'unit')
    (duplicate/'raw.txt').write_text('duplicate')
    ledger.commit(duplicate,{'fixed':1},{'ok':True})
    with pytest.raises(ValueError, match='More than one'):
        ledger.existing(tmp_path/'unit',{'fixed':1})
    with pytest.raises(ValueError): ledger.child(tmp_path,'../outside')


def test_forecast_barrier_and_deterministic_restart(short_reader, monkeypatch, tmp_path):
    spec = pipeline.specification('native_qualification')
    root = tmp_path/'interrupted'; root.mkdir()
    binding = 'synthetic-test-only'
    calls = []
    original = pipeline.measurement.measure
    def measured(*args, **kwargs):
        calls.append((args[2],args[3]))
        return original(*args, **kwargs)
    monkeypatch.setattr(pipeline.measurement,'measure',measured)
    def interruption(stage, details):
        if stage == 'measurement_committed':
            raise RuntimeError('Injected process interruption after durable measurement')
    with pytest.raises(RuntimeError, match='Injected'):
        pipeline.run(root,spec,binding,Guard(),interruption)
    assert len(calls) == 1
    assert not (root/'units/future').exists()
    with pytest.raises(ValueError, match='barrier'):
        pipeline.seal_forecasts(root,spec,binding,Guard())
    retained = next((root/'units/measurement').rglob('probe.npz'))
    saved_hash = ev.sha(retained)
    result = pipeline.run(root,spec,binding,Guard())
    assert len(calls) == 8  # First completed measurement was reused, seven were computed.
    assert ev.sha(retained) == saved_hash
    assert result['case_regimes'] == 8 and result['new_model_fits'] == 0
    assert (root/'units/forecast_blocks/block_-00002/attempt_0001').exists()
    assert (root/'units/forecast_blocks/block_-00002/attempt_0002/COMMIT.json').exists()
    fresh = tmp_path/'fresh'; fresh.mkdir()
    other = pipeline.run(fresh,spec,binding,Guard())
    for directory in ('measurement','future'):
        left = sorted((root/'units'/directory).rglob('*.npz'))
        right = sorted((fresh/'units'/directory).rglob('*.npz'))
        assert len(left) == len(right)
        for a,b in zip(left,right,strict=True):
            ra,rb = ev.load(a,ev.sha(a)),ev.load(b,ev.sha(b))
            assert ra.keys() == rb.keys()
            assert all(ra[k].tobytes() == rb[k].tobytes() for k in ra)
    left,_ = ledger.referenced(root,result['final_reference'])
    right,_ = ledger.referenced(fresh,other['final_reference'])
    assert read(left/'ANALYSIS.json') == read(right/'ANALYSIS.json')
    # Complete checkpoints prevent every native read on another invocation.
    count = len(calls)
    assert pipeline.run(root,spec,binding,Guard()) == result
    assert len(calls) == count


def test_run_lock_and_fixed_resume_deadline(tmp_path):
    spec = pipeline.specification('native_qualification')
    with execute.exclusive_run(tmp_path):
        with pytest.raises(RuntimeError, match='owns'):
            with execute.exclusive_run(tmp_path): pass
        saved = execute.initialize(tmp_path,'native_qualification','fixed',spec,now=100.)
        resumed = execute.initialize(tmp_path,'native_qualification','fixed',spec,resume=True,now=200.)
        assert resumed == saved and resumed['deadline_epoch'] == 1900.
        with pytest.raises(ValueError, match='identical'):
            execute.initialize(tmp_path,'native_qualification','changed',spec,resume=True,now=200.)
        with pytest.raises(TimeoutError):
            execute.initialize(tmp_path,'native_qualification','fixed',spec,resume=True,now=1900.)
        with pytest.raises(FileExistsError):
            execute.initialize(tmp_path,'native_qualification','fixed',spec,now=200.)


def test_resource_deadline_and_evidence_ceiling(tmp_path):
    guard = execute.Guard(tmp_path,dict(mode='native_qualification',deadline_epoch=time.time()+30))
    (tmp_path/'raw').write_bytes(b'12345')
    guard.account(tmp_path); guard.account(tmp_path)
    assert guard.saved_bytes == 5
    guard.maximum = 4
    with pytest.raises(OSError,match='saved-evidence'): guard.check()
    guard.maximum = 10
    guard.deadline = time.time()-1
    with pytest.raises(TimeoutError): guard.check()


def test_runner_records_failure_and_requires_explicit_resume(monkeypatch, tmp_path):
    def broken(mode):
        raise ValueError('Injected frozen-input mismatch')
    monkeypatch.setattr(execute,'verify_configuration',broken)
    target = tmp_path/'failed'
    with pytest.raises(ValueError,match='Injected'):
        execute.run('native_qualification',target)
    assert read(target/'STATUS.json')['status'] == 'FAILED'
    assert read(target/'invocations/attempt_0001/FAILED.json')['type'] == 'ValueError'
    with pytest.raises(FileExistsError): execute.run('native_qualification',target)
    assert not (target/'units').exists()
