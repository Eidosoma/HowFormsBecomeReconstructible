"""Disposable/synthetic qualification; no extension development or held-out futures."""
import copy
import inspect
import os
from pathlib import Path
import subprocess
import sys
import numpy as np
import pytest
from l20_extension1 import diagnostics as p, predictor as model, audit, development_run as run

CACHE = {}


def forbidden(*a,**kw):
    raise RuntimeError('forbidden production/shared/leaked path')


@pytest.fixture(scope='module')
def source():
    run.preflight()
    return p.source_inputs(*p.DISPOSABLE)


def test_full_disposable_life(source):
    founders,guides,y,meta = source
    before = founders.copy(),guides.copy()
    raw,entry = p.simulate_life(*p.DISPOSABLE,0,founders[0],guides[0])
    proof = audit.check_life(raw,entry,founders[0],guides[0],True)
    assert proof['diagnostic_cycles'] == 12 and proof['reader_paths'] == proof['selectors'] == 24
    assert proof['reader_max_abs'] == proof['writer_max_abs'] == proof['terminal_max_abs'] == 0.
    entry['replay'] = proof; CACHE.update(raw=raw,meta=entry)
    np.testing.assert_array_equal(founders,before[0]); np.testing.assert_array_equal(guides,before[1])


@pytest.fixture(scope='module')
def panel(source):
    if not CACHE: test_full_disposable_life(source)
    return CACHE['raw'],CACHE['meta']


def test_source_records():
    for spec in p.DEVELOPMENT+(p.DISPOSABLE,):
        founders,guides,y,meta = p.source_inputs(*spec)
        assert founders.shape == (4,2,2048) and guides.shape == (4,2,16,16) and y.shape == (4,4)
        assert np.isfinite(y).all() and np.all(abs(y)<=1)
        assert meta['host_index'] == (spec[1]-2000 if spec[0]=='d135' else spec[1])
    assert len(p.DEVELOPMENT) == len(set(p.DEVELOPMENT)) == 16


def test_shuffle_preserves_values(panel):
    raw,_ = panel
    for ci,(role,mode) in enumerate(p.CASES):
        before = p.old.decode(raw['founder_packets'][role].tobytes()).ravel()
        after = p.old.decode(raw['input'][ci,2].tobytes()).ravel()
        np.testing.assert_array_equal(np.sort(before),np.sort(after))
        untouched = np.setdiff1d(np.arange(256),raw['sites'])
        np.testing.assert_array_equal(before[untouched],after[untouched])
        assert 0 <= raw['changed_sites'][ci] <= 64
        assert abs(np.linalg.norm(before)-np.linalg.norm(after)) < 1e-14
    # Identity shuffle remains identity; no resampling to force an effect.
    identity = p.partial_shuffle(raw['founder_packets'][0].tobytes(),raw['sites'],np.arange(64,dtype=np.int64))
    assert identity == raw['founder_packets'][0].tobytes()


@pytest.mark.parametrize('kind',['duplicate','range','permutation','size','dtype'])
def test_shuffle_invalid(kind,panel):
    raw,_ = panel; sites = raw['sites'].copy(); permutation = raw['permutation'].copy()
    if kind == 'duplicate': sites[0]=sites[1]
    elif kind == 'range': sites[0]=256
    elif kind == 'permutation': permutation[0]=permutation[1]
    elif kind == 'size': sites=sites[:63]
    else: sites=sites.astype(float)
    with pytest.raises(ValueError): p.partial_shuffle(raw['founder_packets'][0].tobytes(),sites,permutation)


def test_noise_pairing(panel):
    raw,meta = panel
    for ci in range(4):
        u0,u1,c1 = meta['cycles'][ci]
        for field in ('birth_rng','read_rng'):
            assert u1['reader'][field] == c1['reader'][field] != u0['reader'][field]
            assert u1['terminal_reader'][field] == c1['terminal_reader'][field] != u1['reader'][field]
        assert u1['writer']['noise_rng'] == c1['writer']['noise_rng'] != u0['writer']['noise_rng']
    draw = p.rng(*p.DISPOSABLE,0,'trial1:birth').normal(size=20)
    for phase in ('g1:birth','g2:birth','g3:birth','terminal:birth'):
        assert not np.array_equal(draw,p.d140.rng(p.DISPOSABLE[1],0,phase).normal(size=20))
        assert not np.array_equal(draw,p.old.rng(p.DISPOSABLE[1],0,phase).normal(size=20))


def test_no_third_copy(panel):
    raw,_ = panel; start=raw['initial_features']; probes=raw['diagnostic_features'].copy()
    passive = p.observer_features(start,probes[:,0],probes[:,1])
    challenge = p.observer_features(start,probes[:,0],probes[:,2])
    probes[:,1] += 999
    np.testing.assert_array_equal(challenge,p.observer_features(start,probes[:,0],probes[:,2]))
    probes=raw['diagnostic_features'].copy(); probes[:,2] += 999
    np.testing.assert_array_equal(passive,p.observer_features(start,probes[:,0],probes[:,1]))
    assert list(inspect.signature(p.observer_features).parameters) == ['initial','first','second']
    assert passive.shape == challenge.shape == (4,16)


def test_no_parent_or_future_access(panel,source,monkeypatch):
    assert list(inspect.signature(p.simulate_life).parameters) == ['cohort','index','life','founders','guide','order']
    assert list(inspect.signature(p.cycle).parameters) == ['packet','cohort','index','life','trial','mode','guide']
    monkeypatch.setattr(p,'source_inputs',forbidden)
    monkeypatch.setattr(p.d140,'generate_founders',forbidden)
    founders,guides,_,_ = source
    row,meta = p.cycle(founders[0,0].tobytes(),*p.DISPOSABLE,0,0,'translated',guides[0])
    for key in row: np.testing.assert_array_equal(row[key],panel[0][key][0,0])
    for name in ('incoming_packet_access','guide_access','target_labels'):
        assert meta['writer'][name] is False


def test_independent_checker(panel,source,monkeypatch):
    founders,guides,_,_ = source
    for name in ('record_features','terminal_features','partial_shuffle','cycle','simulate_life','rng'):
        monkeypatch.setattr(p,name,forbidden)
    for name in ('read_selected','write_streams','route','record'):
        monkeypatch.setattr(p.old,name,forbidden)
    proof = audit.check_life(*panel,founders[0],guides[0],True)
    assert proof['full_dynamics_replayed']


def test_condition_order(panel,source):
    founders,guides,_,_ = source
    raw,meta = p.simulate_life(*p.DISPOSABLE,0,founders[0],guides[0],tuple(reversed(p.CASES)))
    for key in raw: np.testing.assert_array_equal(raw[key],panel[0][key])
    audit.nested(meta,{k:v for k,v in panel[1].items() if k!='replay'})


@pytest.mark.parametrize('key',['founder_packets','guide','sites','permutation','input','routed','outgoing','terminal_packet',
                               'read_states','write_states','terminal_states','scores','shift','initial_features',
                               'diagnostic_features','input_strength','changed_sites'])
def test_raw_corruption(key,panel,source):
    raw={k:v.copy() for k,v in panel[0].items()}; value=raw[key]
    if value.dtype == np.uint8: value.flat[0] ^= 1
    elif value.dtype == np.int64: value.flat[0] += 1
    else: value.flat[0] += .01
    with pytest.raises((AssertionError,ValueError)):
        audit.check_life(raw,panel[1],source[0][0],source[1][0],False)


@pytest.mark.parametrize('key',['cohort','index','life','host','tag','config','cases','branches','cycles',
                               'guide_sha256','predictor_has_parent_state','diagnostic_to_lineage'])
def test_metadata_corruption(key,panel,source):
    meta=copy.deepcopy(panel[1])
    if key=='host': meta[key]['index']+=1
    elif key=='config': meta[key]['steps']+=1
    elif key=='cycles': meta[key][0][1]['reader']['read_rng']='bad'
    elif key in ('cases','branches'): meta[key]=meta[key][::-1]
    elif key in ('predictor_has_parent_state','diagnostic_to_lineage'): meta[key]=True
    elif key in ('index','life'): meta[key]+=1
    else: meta[key]='bad'
    with pytest.raises((AssertionError,ValueError)):
        audit.check_life(panel[0],meta,source[0][0],source[1][0],False)


def test_independent_features(panel):
    guide=panel[0]['guide']; random=np.random.default_rng(717)
    for field in (np.zeros((16,16)),p.targets()[0],p.targets()[1],random.normal(size=(16,16))):
        packet=p.old.encode(field)
        for role in (0,1):
            np.testing.assert_allclose(p.record_features(packet,role,guide),audit.record_features(packet,role,guide),atol=1e-12,rtol=0)
            np.testing.assert_array_equal(p.terminal_features(field,role),audit.terminal_features(field,role))
    boundary=np.full((16,16),.2)
    assert p.terminal_features(boundary,0)[0] == 0.


@pytest.fixture(scope='module')
def synthetic():
    random=np.random.default_rng(141)
    x=random.normal(size=(256,16)); x[:,-1]=4.
    groups=np.tile(np.arange(4,dtype=np.int64),64); ids=np.repeat(np.arange(16,dtype=np.int64),16)
    y=np.tanh(.2*x[:,0]-.3*x[:,3]+groups*.1+random.normal(0,.1,256))
    return x,y,groups,ids


def test_independent_model(synthetic,monkeypatch):
    x,y,g,b=synthetic; result=model.select_and_fit(x,y,g,b)
    for name in ('fit','predict','select_and_fit'): monkeypatch.setattr(model,name,forbidden)
    assert audit.check_fit(result,x,y,g,b)


def test_model_artifact_and_summary(synthetic,monkeypatch):
    x,y,g,b=synthetic
    blocks=[]
    for block in range(16):
        rows=x[b==block].reshape(4,4,16)
        probes=np.stack((rows[:,:,4:10],rows[:,:,10:16],rows[:,:,4:10]+.1),axis=2)
        blocks.append(dict(initial_features=rows[:,:,:4],diagnostic_features=probes,outcomes=y[b==block].reshape(4,4)))
    models=run.fit_models(blocks); summary=run.summarize(models,blocks)
    assert audit.check_models(models,blocks) and audit.check_summary(summary,models,blocks)
    monkeypatch.setattr(run,'summarize',forbidden)
    assert audit.check_summary(summary,models,blocks)
    bad=copy.deepcopy(summary); bad['cv_mse_improvement']+=.01
    with pytest.raises(AssertionError): audit.check_summary(bad,models,blocks)
    bad=copy.deepcopy(models); bad['heldout_outcomes_seen']=1
    with pytest.raises(AssertionError): audit.check_models(bad,blocks)


def test_blocked_cv(synthetic,monkeypatch):
    x,y,g,b=synthetic; seen=[]; original=model.fit
    def checked(features,outcomes,groups,alpha):
        if len(features)==240:
            included=set(features[:,0].tolist())
            present=[sum(v in included for v in x[b==i,0]) for i in range(16)]
            assert present.count(0)==1 and present.count(16)==15
            seen.append(present.index(0))
        else: assert len(features)==256
        return original(features,outcomes,groups,alpha)
    monkeypatch.setattr(model,'fit',checked)
    model.select_and_fit(x,y,g,b)
    assert seen == list(range(16))*6


def test_training_only_preprocessing(synthetic):
    x,y,g,b=synthetic; train=b!=0
    fit=model.fit(x[train],y[train],g[train],.1)
    altered=x.copy(); altered[~train] += 1000
    assert fit == model.fit(altered[train],y[train],g[train],.1)
    np.testing.assert_array_equal(np.asarray(fit['scales'])[-1],1.)
    # Group-wise constant offsets affect intercepts, not residual slopes.
    offset=x+g[:,None]*123
    other=model.fit(offset[train],y[train],g[train],.1)
    np.testing.assert_allclose(fit['coefficients'],other['coefficients'],rtol=0,atol=1e-10)


def test_tie_prefers_regularization(synthetic):
    x,y,g,b=synthetic
    fit=model.select_and_fit(x,np.zeros_like(y),g,b)
    assert fit['model']['alpha']==100.


@pytest.mark.parametrize('key',['alpha','features','group_feature_means','group_outcome_means','scales','coefficients','clip'])
def test_model_corruption(key,synthetic):
    x,y,g,b=synthetic; result=model.select_and_fit(x,y,g,b); bad=copy.deepcopy(result)
    if key in ('alpha','features'): bad['model'][key]+=1
    elif key=='group_feature_means': bad['model'][key][0][0]+=.01
    else: bad['model'][key][0]+=.01
    with pytest.raises((AssertionError,ValueError)): audit.check_fit(bad,x,y,g,b)


@pytest.mark.parametrize('kind',['gain','harm','tie','zero'])
def test_primary_score(kind):
    y=np.zeros((16,4,4)); p1=np.full_like(y,.2); p2=np.zeros_like(y)
    if kind=='harm': p1,p2=p2,p1
    elif kind=='tie': p2=p1.copy()
    elif kind=='zero': p1[:]=0
    result=model.score(y,p1,p2)
    expected={'gain':'CHALLENGE_PREDICTIVE_GAIN','harm':'CHALLENGE_PREDICTIVE_HARM',
              'tie':'PREDICTIVE_DIFFERENCE_UNRESOLVED','zero':'PREDICTIVE_DIFFERENCE_UNRESOLVED'}[kind]
    assert result['label']==expected
    np.testing.assert_allclose(result['mse_improvement'],np.mean(p1*p1-p2*p2),atol=1e-14,rtol=0)
    assert result['independent_blocks']==16
    if kind=='zero': assert result['relative_reduction'] is None


def test_primary_block_bootstrap():
    y=np.zeros((16,4,4)); p1=np.zeros_like(y); p2=np.zeros_like(y)
    p1[0]=.8; p2[1]=.4
    result=model.score(y,p1,p2)
    blocks=(p1**2-p2**2).sum(axis=(1,2))/16
    random=np.random.Generator(np.random.PCG64(14120260917))
    draws=random.integers(0,16,(10000,16))
    boot=np.sum(blocks[draws],axis=1)/16
    np.testing.assert_array_equal(result['ci95'],np.percentile(boot,[2.5,97.5]))


def test_external_roundtrip(panel,tmp_path):
    assert p.ROOT in tmp_path.resolve().parents
    saved=p.io.save_pair(tmp_path,'life',panel[0],panel[1],p.ROOT)
    for key in saved: np.testing.assert_array_equal(saved[key],panel[0][key])
    with pytest.raises(FileExistsError): p.io.save_pair(tmp_path,'life',panel[0],panel[1],p.ROOT)
    with pytest.raises(ValueError): p.io.write_json(p.WS/'forbidden.json',{},p.ROOT)


def test_fresh_process_saved_audit(panel,tmp_path):
    p.io.save_pair(tmp_path,'life',panel[0],panel[1],p.ROOT)
    script="""from pathlib import Path
from l20_extension1 import diagnostics as p, audit, development_run as run
import sys
run.preflight(False)
d=Path(sys.argv[1]); raw=p.io.load_npz(d/'life.npz'); meta=p.io.read_json(d/'life.json')
f,g,y,m=p.source_inputs(*p.DISPOSABLE)
proof=audit.check_life(raw,meta,f[0],g[0],False)
assert proof['diagnostic_cycles']==12
print('independent saved audit passed')
"""
    result=subprocess.run([sys.executable,'-c',script,str(tmp_path)],capture_output=True,text=True,check=True)
    assert 'independent saved audit passed' in result.stdout


@pytest.mark.parametrize('kind',['threads','cpus','tmp','bytecode'])
def test_resource_guards(kind,monkeypatch):
    if kind=='threads': monkeypatch.setenv('OMP_NUM_THREADS','2')
    elif kind=='cpus': monkeypatch.setattr(os,'sched_getaffinity',lambda pid:set(range(7)))
    elif kind=='tmp': monkeypatch.setenv('TMPDIR',str(p.WS))
    else: monkeypatch.setenv('PYTHONDONTWRITEBYTECODE','0')
    with pytest.raises((AssertionError,RuntimeError,ValueError)): run.preflight()


def test_detachment_guard(monkeypatch):
    monkeypatch.delenv(run.DETACHED_ENV,raising=False)
    with pytest.raises(AssertionError,match='detached'): run.detached_guard('development',True)
    run.detached_guard('development',False)
    monkeypatch.setenv(run.DETACHED_ENV,'benchmark')
    with pytest.raises(AssertionError): run.detached_guard('development',True)


def test_long_stage_guard(monkeypatch):
    monkeypatch.delenv(run.DETACHED_ENV,raising=False); monkeypatch.setattr(run,'preflight',lambda *a:None)
    monkeypatch.setattr(run,'frozen',lambda:dict(test_proof=dict(benchmark_forecast=601)))
    with pytest.raises(AssertionError,match='detached'): run.benchmark()
    monkeypatch.setattr(run,'prepared',lambda:dict(timing=dict(must_detach=True)))
    with pytest.raises(AssertionError,match='detached'): run.execute()


def test_reservation_guard(monkeypatch,tmp_path):
    marker=tmp_path/'freeze.json'; p.io.write_json(marker,{},p.ROOT)
    monkeypatch.setattr(run,'preflight',lambda *a:None); monkeypatch.setattr(run,'report_proof',lambda *a:{})
    monkeypatch.setattr(run,'freeze_path',lambda:marker)
    with pytest.raises(FileExistsError): run.freeze(marker)


@pytest.mark.parametrize('spec',[('heldout',90000),('d140',90000),('d135',73000),('disposable',True),('d140',78000.)])
def test_heldout_guard(spec):
    with pytest.raises(ValueError): p.validate_spec(*spec)


def test_no_automatic_successor():
    assert p.contract()['heldout_generation'] is False and p.contract()['automatic_successor'] is False
    assert 'heldout' not in inspect.getsource(run.main).replace('--test-report','')
    assert run.contract()['workers']==6 and run.contract()['detach_above_seconds']==600


def test_source_closure():
    paths=run.source_closure()
    assert len(paths)>=1080
    assert all(path.is_file() for path in paths)
    assert p.WS/'PROTOCOL_V1.md' in paths
    assert p.WS/'README.md' not in paths
