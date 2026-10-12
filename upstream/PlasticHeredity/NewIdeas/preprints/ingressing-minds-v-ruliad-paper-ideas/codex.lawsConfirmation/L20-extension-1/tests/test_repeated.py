"""D142 qualification: disposable dynamics only; synthetic uncertainty fixtures."""
import copy
import inspect
import json
import os
from pathlib import Path
import numpy as np
import pytest
from l20_extension1 import repeated_system as system, repeated_audit as audit
from l20_extension1 import repeated_analysis as analysis, repeated_analysis_check as independent
from l20_extension1 import repeated_run as run, heldout_system, predictor


def forbidden(*args, **kwargs):
    raise AssertionError('forbidden production/dynamic/fit access')


@pytest.fixture(scope='module')
def panel(tmp_path_factory):
    founders, guides = system.load_source(system.DISPOSABLE)
    raw, meta = system.simulate(system.DISPOSABLE, 0, 0, founders[0], guides[0])
    meta['replay'] = audit.check(raw, meta, founders[0], guides[0], True)
    directory = tmp_path_factory.mktemp('repeated_disposable_future')
    run.io.write_npz(directory/'raw.npz', raw, run.ROOT)
    run.io.write_json(directory/'meta.json', meta, run.ROOT)
    return dict(raw=raw, meta=meta, founders=founders[0], guide=guides[0], directory=directory)


def test_full_disposable_future(panel):
    assert panel['meta']['replay']['full_dynamics_replayed']
    assert panel['meta']['replay']['generation_paths'] == 12
    assert panel['meta']['replay']['terminal_paths'] == 4
    assert panel['meta']['replay']['new_founders'] == 0


def test_original_namespace_parity(panel, monkeypatch):
    monkeypatch.setattr(system, 'rng', lambda index, life, future, phase: heldout_system.rng(index, life, phase))
    raw, _ = system.simulate(system.DISPOSABLE, 0, 0, panel['founders'], panel['guide'])
    arrays, meta = system.source_paths(system.DISPOSABLE)
    saved_meta = run.io.read_json(meta)['lives'][0]
    with np.load(arrays, allow_pickle=False) as saved:
        for ci, case in enumerate(system.CASES):
            a = saved_meta['cases'].index(list(case)); b = saved_meta['probes'].index(list(case))
            for new, old in (('incoming','incoming'),('routed','routed'),('outgoing','outgoing'),
                ('read_states','generation_read_states'),('write_states','generation_write_states'),('values','values')):
                np.testing.assert_array_equal(raw[new][ci], saved[old][0,a])
            np.testing.assert_array_equal(raw['scores'][ci], saved['generation_scores'][0,a,:,0])
            for new, old in (('terminal_input','terminal_inputs'),('terminal_packet','terminal_packets'),
                ('terminal_scores','terminal_scores'),('terminal_states','terminal_states'),('terminal_values','terminal_values')):
                np.testing.assert_array_equal(raw[new][ci], saved[old][0,b])


def test_source_host_json_roundtrip():
    for index in (514240,90000):
        packets,guides=system.load_source(index)
        assert packets.shape==(4,2,2048) and guides.shape==(4,2,16,16)
        assert not packets.flags.writeable and not guides.flags.writeable
        saved=run.io.read_json(system.source_paths(index)[1])['lives'][0]['host']
        assert isinstance(saved['tissue']['strict_band'],list)
        assert isinstance(saved['ladder']['displacement_ladder'],list)


def test_noise_separation(panel):
    phases = [f'g{g}:{name}' for g in (1,2,3) for name in ('birth','read','source_shift','source_write')]+['terminal:birth','terminal:read']
    seen = set()
    for index in (90000,90001,514240):
        for life in range(4):
            for future in range(4):
                for phase in phases:
                    values = system.rng(index, life, future, phase).standard_normal(16).tobytes()
                    assert values not in seen; seen.add(values)
                    assert values != heldout_system.rng(index, life, phase).standard_normal(16).tobytes()
    for g in range(3):
        first = panel['meta']['paths'][0]['generations'][g]
        for row in panel['meta']['paths'][1:]:
            other = row['generations'][g]
            assert other['reader']['birth_rng'] == first['reader']['birth_rng']
            assert other['reader']['read_rng'] == first['reader']['read_rng']
            assert other['writer_details']['noise_rng'] == first['writer_details']['noise_rng']


def test_independent_replay(panel, monkeypatch):
    for name in ('simulate',): monkeypatch.setattr(system, name, forbidden)
    for name in ('read_selected','write_streams','route','record'):
        monkeypatch.setattr(system.old, name, forbidden)
    assert audit.check(panel['raw'], panel['meta'], panel['founders'], panel['guide'], True)['full_dynamics_replayed']


def test_saved_no_dynamics(panel, monkeypatch):
    monkeypatch.setattr(audit.physics, 'step', forbidden)
    proof = audit.check(panel['raw'], panel['meta'], panel['founders'], panel['guide'], False)
    assert not proof['full_dynamics_replayed'] and proof['generation_paths'] == 12


@pytest.mark.parametrize('key', ['incoming','routed','outgoing','scores','read_states','write_states',
    'terminal_input','terminal_packet','terminal_scores','terminal_states','values','terminal_values','shift'])
def test_corruption(panel, key):
    raw = {k: v.copy() for k,v in panel['raw'].items()}
    if raw[key].dtype == np.uint8: raw[key].flat[0] ^= 1
    else: raw[key].flat[0] += 1
    with pytest.raises((AssertionError,ValueError)):
        audit.check(raw, panel['meta'], panel['founders'], panel['guide'], False)


@pytest.mark.parametrize('key,value', [('namespace','l20-extension1-heldout-v1'),('future',1),
    ('old_lineage_states_reused',True),('parent_state_access',True),('source_records_reused',False),
    ('fresh_future_noise',False),('guide_refitted',True),('record_bytes',64)])
def test_metadata_corruption(panel, key, value):
    meta = copy.deepcopy(panel['meta']); meta[key] = value
    with pytest.raises((AssertionError,ValueError)):
        audit.check(panel['raw'], meta, panel['founders'], panel['guide'], False)


def test_condition_order(panel):
    raw, meta = system.simulate(system.DISPOSABLE,0,0,panel['founders'],panel['guide'],tuple(reversed(system.CASES)))
    for key in raw: np.testing.assert_array_equal(raw[key],panel['raw'][key])
    assert meta == {k:v for k,v in panel['meta'].items() if k!='replay'}


@pytest.mark.parametrize('index,life,future', [(78000,0,0),(90016,0,0),(90000,4,0),(90000,0,4),
    (True,0,0),(90000,0,False),(90000,-1,0)])
def test_namespace_guard(index, life, future):
    with pytest.raises(ValueError): system.rng(index,life,future,'g1:birth')


def test_variance_formula():
    y = np.arange(64)[:,None]/100 + np.array([-.3,-.1,.1,.3])
    result = analysis.components(y); expected = independent.moments(y)
    for k in result: np.testing.assert_allclose(result[k],expected[k],atol=1e-12,rtol=0)
    assert result['within_future_variance'] == pytest.approx(.2/3)
    assert result['between_record_host_variance'] == pytest.approx(np.var(np.arange(64)/100,ddof=1)-.2/12)


def test_negative_between():
    y = np.tile([-.3,-.1,.1,.3],(64,1)); values = analysis.components(y)
    assert values['between_record_host_variance'] < 0
    assert values['repeatability'] == pytest.approx(-1/3)


def test_zero_noise():
    y = np.repeat(np.arange(64)[:,None]/64,4,axis=1)
    value = analysis.components(y)
    assert value['within_future_variance'] == 0 and value['repeatability'] == 1


def test_constant_outcomes():
    draws = np.zeros((10000,16),dtype=int)
    result = analysis.group_statistics(np.full((16,4,4),.125),draws)
    assert result['repeatability'] == dict(estimate=None,pointwise_block_bootstrap_95=None,undefined_bootstrap_draws=10000)
    assert result['within_future_variance']['estimate'] == 0


def test_block_bootstrap():
    y = np.arange(16*4*4,dtype=float).reshape(16,4,4)/256
    draws = np.zeros((10000,16),dtype=int)
    actual = analysis.group_statistics(y,draws)
    repeated = np.tile(y[0],(16,1)); expected = independent.moments(repeated)
    for k in expected:
        np.testing.assert_allclose(actual[k]['pointwise_block_bootstrap_95'],[expected[k]]*2,atol=1e-12,rtol=0)
    with pytest.raises(ValueError): analysis.group_statistics(y,np.zeros((10000,64),int))


def test_forecast_decomposition():
    y = np.random.default_rng(4).normal(0,.1,(64,4)); predictions = y.mean(axis=1)
    value = analysis.fixed_forecasts(y,predictions)
    assert value['noise_corrected_mean_target_mse'] < 0
    assert value['fresh_future_mse'] == pytest.approx(value['noise_corrected_mean_target_mse']+value['estimated_noise_variance'])


@pytest.fixture(scope='module')
def score_fixture(panel):
    base = {k:np.tile(v[None,None],(4,4)+(1,)*v.ndim) for k,v in panel['raw'].items()}
    meta = dict(index=514240,config=panel['meta']['config'],lives=[[panel['meta']]*4 for _ in range(4)])
    blocks = []
    for i in range(16):
        block = base.copy(); block['terminal_values'] = base['terminal_values'].copy()
        for life in range(4):
            for future in range(4):
                for ci in range(4):
                    block['terminal_values'][life,future,ci,-1,0] = .05*i+.03*life+.04*future+.03*ci-.2
                    block['terminal_values'][life,future,ci,-1,1] = 0
        blocks.append(block)
    forecasts=np.random.default_rng(17).uniform(0,.5,(16,4,4,3))
    original=np.random.default_rng(18).uniform(-.2,.5,(16,4,4))
    return blocks,[meta]*16,forecasts,original


def test_complete_summary(score_fixture, monkeypatch):
    summary = analysis.summarize(*score_fixture)
    monkeypatch.setattr(analysis,'components',forbidden)
    monkeypatch.setattr(analysis,'summarize',forbidden)
    assert independent.check(summary,*score_fixture)['passes']
    summary['groups']['B_translated']['primary']['within_future_variance']['estimate'] += .1
    with pytest.raises(AssertionError): independent.check(summary,*score_fixture)


def test_original_not_primary(score_fixture):
    a = analysis.summarize(*score_fixture)
    args=list(score_fixture); args[-1]=np.ones((16,4,4))*.1
    b = analysis.summarize(*args)
    for k in a['groups']:
        assert a['groups'][k]['primary'] == b['groups'][k]['primary']
        assert a['groups'][k]['fixed_predictors'] == b['groups'][k]['fixed_predictors']


def test_new_forecasts_not_fitted(monkeypatch):
    for name in ('fit','select_and_fit','predict'): monkeypatch.setattr(predictor,name,forbidden)
    forecasts,original=run.existing_labels()
    assert forecasts.shape==(16,4,4,3) and original.shape==(16,4,4)
    for i in range(3): assert np.isfinite(forecasts[...,i]).all()


def test_external_roundtrip(panel, tmp_path):
    run.io.write_npz(tmp_path/'raw.npz',panel['raw'],run.ROOT)
    run.io.write_json(tmp_path/'meta.json',panel['meta'],run.ROOT)
    raw=run.io.load_npz(tmp_path/'raw.npz'); meta=run.io.read_json(tmp_path/'meta.json')
    assert audit.check(raw,meta,panel['founders'],panel['guide'],False)['packet_lineage']
    with pytest.raises(FileExistsError): run.io.write_json(tmp_path/'meta.json',{},run.ROOT)
    with pytest.raises(ValueError): run.io.write_json(Path('/tmp/d142_forbidden.json'),{},run.ROOT)


def test_source_closure():
    closure=run.source_closure()
    assert len(closure)>1200
    assert all(path in closure for path in system.source_paths(514240))
    assert all(system.dev.WS/p in closure for p in run.SCIENCE)


def test_resource_guards(monkeypatch):
    assert len(run.preflight(False))<=6
    monkeypatch.setenv('OMP_NUM_THREADS','2')
    with pytest.raises(RuntimeError): run.preflight(False)


def test_detached_guard(monkeypatch):
    monkeypatch.delenv(run.DETACHED_ENV,raising=False)
    with pytest.raises(RuntimeError): run.detached_guard(True)
    run.detached_guard(False)
    monkeypatch.setenv(run.DETACHED_ENV,'1')
    monkeypatch.setattr(os,'getsid',lambda _:os.getpid())
    monkeypatch.setattr(os,'readlink',lambda p:'/dev/null' if p.endswith('/0') else str(run.log_path()))
    run.detached_guard(True)


def test_long_stage_guard(tmp_path,monkeypatch):
    monkeypatch.setattr(run,'preflight',lambda:None)
    monkeypatch.setattr(run,'frozen',lambda:dict(test_proof=dict(benchmark_forecast=601)))
    monkeypatch.setattr(run,'benchmark_dir',lambda:tmp_path/'never_created')
    monkeypatch.delenv(run.DETACHED_ENV,raising=False)
    with pytest.raises(RuntimeError): run.benchmark()
    assert not (tmp_path/'never_created').exists()


def test_startup_handshake(monkeypatch):
    read,write=os.pipe(); monkeypatch.setenv('D142_READY_FD',str(write))
    run.signal_ready('execute')
    try: assert json.loads(os.read(read,4096))==dict(stage='execute',pid=os.getpid(),status='STARTED')
    finally: os.close(read)
    assert 'D142_READY_FD' not in os.environ


def test_no_automatic_successor():
    c=run.contract()
    assert not c['automatic_polling'] and not c['automatic_retry'] and not c['automatic_successor']
    assert 'detach(' not in inspect.getsource(run.execute)
    assert 'execute(' not in inspect.getsource(run.benchmark)
    assert 'child.poll' not in inspect.getsource(run.detach)
    assert 'select.select([ready_read], [], [], 55)' in inspect.getsource(run.detach)


def test_main_barrier(tmp_path,monkeypatch):
    monkeypatch.setattr(system,'simulate',forbidden)
    with pytest.raises(ValueError,match='barrier'): run.worker(tmp_path,90000)
    directory=tmp_path/'run'; directory.mkdir()
    run.io.write_json(directory/'MANIFEST.json',{'fixture':True},run.ROOT)
    digest=run.sha256_file(directory/'MANIFEST.json')
    with pytest.raises(FileNotFoundError): run.barrier(directory,tmp_path,digest)
    run.io.write_json(tmp_path/'NEW_FUTURES_STARTED.json',dict(manifest_sha256=digest,
        source_complete_sha256=system.SOURCE_COMPLETE_SHA,namespaces=[system.namespace(r) for r in range(4)]),run.ROOT)
    assert run.barrier(directory,tmp_path,digest)['manifest_sha256']==digest
    with pytest.raises(AssertionError): run.barrier(directory,tmp_path,'wrong hash')


def test_failure_receipt(tmp_path,monkeypatch):
    directory=tmp_path/'run'; directory.mkdir(); out=tmp_path/'out'; out.mkdir()
    monkeypatch.setattr(run,'paths',lambda:(directory,out))
    monkeypatch.setattr(run,'preflight',lambda:None)
    monkeypatch.setattr(run,'prepared',lambda:(_ for _ in ()).throw(RuntimeError('qualification failure fixture')))
    with pytest.raises(RuntimeError): run.execute()
    assert (directory/'FAILED.json').exists()
    assert run.io.read_json(directory/'STATUS.json')['status']=='FAILED'
    with pytest.raises(FileExistsError): run.execute()
