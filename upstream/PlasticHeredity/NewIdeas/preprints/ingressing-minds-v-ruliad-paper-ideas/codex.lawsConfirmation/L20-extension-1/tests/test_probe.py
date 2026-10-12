"""D151 qualification: disposable cycles, synthetic models, no main probe outcomes."""
import copy
import inspect
import json
import os
from types import SimpleNamespace
import numpy as np
import pytest
from l20_extension1 import probe_system as p,probe_audit as a,probe_models as m,probe_model_check as c,probe_run as run


def forbidden(*args,**kwargs):raise AssertionError('forbidden production/future/state call')


@pytest.fixture(scope='module')
def panel(tmp_path_factory):
    run.resources(False);source,sm=p.load_source(p.DISPOSABLE);spec=p.DISPOSABLE
    src={k:v[0] for k,v in source.items()};plan=p.block_plan(spec)
    raw,meta=p.simulate_life(spec,0,src['founder_packets'],src['guide'],plan['lives'][0])
    meta['replay']=a.check_life(raw,meta,src,sm['lives'][0],True)
    directory=tmp_path_factory.mktemp('d151_disposable')
    run.io.write_npz(directory/'raw.npz',raw,run.ROOT);run.io.write_json(directory/'meta.json',meta,run.ROOT)
    return dict(raw=raw,meta=meta,source=src,source_meta=sm['lives'][0],plan=plan,directory=directory)


@pytest.fixture(scope='module')
def small():
    data,bp,bm=m.fixture(4);pred,fit=m.fit_new(data,bp,bm)
    return data,bp,bm,pred,fit


@pytest.fixture(scope='module')
def scores():
    rng=np.random.default_rng(151);y=rng.uniform(-.5,.5,(32,4,4))
    data=dict(labels=y,futures=np.clip(y[16:,...,None]+rng.normal(scale=.1,size=(16,4,4,4)),-1,1))
    pred={k:np.clip(y+rng.normal(scale=.1,size=y.shape),-1,1) for k in m.MODELS}
    fits={k:dict(folds=[dict(model=dict(alpha=m.ridge.ALPHAS[i%6])) for i in range(32)]) for k in m.MODELS}
    return data,pred,fits,m.summarize(pred,fits,data)


def check(panel,raw=None,meta=None,replay=False):
    return a.check_life(panel['raw'] if raw is None else raw,panel['meta'] if meta is None else meta,panel['source'],panel['source_meta'],replay)


def test_full_disposable_life(panel):
    proof=panel['meta']['replay']
    assert proof['passes'] and proof['cycles']==proof['replayed_cycles']==12
    assert proof['readers']==24 and proof['writers']==12 and proof['max_abs']<=1e-10
    assert proof['new_actual_lineages']==0 and proof['prospective_evidence'] is False


def test_small_models():
    data,bp,bm=m.fixture(4);pred,fit=m.fit_new(data,bp,bm)
    proof=c.check_fits(pred,fit,data,bp,bm)
    assert proof['models']==6 and proof['exact_saved_baselines']==3 and proof['inner_folds']==72


@pytest.mark.parametrize('role',[0,1])
@pytest.mark.parametrize('seed',[0,1,37])
def test_algebra(role,seed):
    f=np.random.default_rng(seed).normal(size=(16,16))*.3+.02;packet=p.old.encode(f)
    edited,detail=p.edit.edit_packets(packet,role)
    for name in p.EDITS:
        expected,d=a.algebra.expected_edit(packet,role,name)
        np.testing.assert_allclose(p.old.decode(edited[name]),expected,atol=1e-12,rtol=0)
        a.physics.nested(detail,d);a.algebra.invariants(packet,edited[name],role,name,d)


@pytest.mark.parametrize('role',[0,1])
@pytest.mark.parametrize('kind',['zero','constant','own','competing','residual','near_zero'])
def test_degenerate(role,kind):
    targets=p.original.targets();h=np.where(np.arange(16)<8,1.,-1.);res=np.outer(h,h)
    field={'zero':np.zeros((16,16)),'constant':np.full((16,16),.3),'own':targets[role]*.3,
        'competing':targets[1-role]*.3,'residual':res*.3,'near_zero':targets[1-role]*.3+res*1e-14}[kind]
    packet=p.old.encode(field);edited,d=p.edit.edit_packets(packet,role)
    assert d['degenerate'] and d['dose_rms']==0 and all(v==packet for v in edited.values())


def test_independent_replay(panel,monkeypatch):
    monkeypatch.setattr(p,'simulate_life',forbidden);monkeypatch.setattr(p,'cycle',forbidden)
    monkeypatch.setattr(p.edit,'edit_packets',forbidden)
    for name in ('read_selected','write_streams','route'):monkeypatch.setattr(p.old,name,forbidden)
    assert check(panel,replay=True)['replayed_cycles']==12


@pytest.mark.parametrize('spec,ci',[(p.DISPOSABLE,0),(p.DISPOSABLE,3),(p.OTHER_DISPOSABLE,2)])
def test_source_parity(spec,ci):
    run.resources(False);source,sm=p.load_source(spec);src={k:v[0] for k,v in source.items()}
    packet=src['routed'][ci,1].tobytes();raw,meta=p.cycle(packet,spec,0,p.CASES[ci][1],src['guide'])
    for k in ('outgoing','terminal_packet','read_states','write_states','terminal_states'):
        np.testing.assert_array_equal(raw[k],src[k][ci,1])
    np.testing.assert_array_equal(raw['last_scores'],src['scores'][ci,1,1])
    for k in ('reader','writer','terminal_selector','terminal_reader'):assert meta[k]==sm['lives'][0]['cycles'][ci][1][k]
    assert meta['trial']==1


def test_condition_order(panel):
    raw,meta=p.simulate_life(p.DISPOSABLE,0,panel['source']['founder_packets'],panel['source']['guide'],
        panel['plan']['lives'][0],tuple(reversed(p.ORDER)))
    for k in raw:np.testing.assert_array_equal(raw[k],panel['raw'][k])
    assert meta=={k:v for k,v in panel['meta'].items() if k!='replay'}


def test_matching(panel):
    raw=panel['raw'];src=panel['source']
    for ci in range(4):
        for ei in range(3):
            np.testing.assert_array_equal(raw['read_states'][ci,ei,0],src['read_states'][ci,1,0])
            np.testing.assert_array_equal(raw['terminal_states'][ci,ei,0],src['terminal_states'][ci,1,0])
            assert not np.array_equal(raw['read_states'][ci,ei,0],src['read_states'][ci,0,0])


def test_saved_no_dynamics(panel,monkeypatch):
    monkeypatch.setattr(a.physics,'step',forbidden)
    assert check(panel)['replayed_cycles']==0


@pytest.mark.parametrize('key',['input','outgoing','terminal_packet','read_states','write_states','terminal_states','last_scores','shift','record_values','diagnostic_features','selected_packets'])
def test_raw_corruption(panel,key):
    raw=dict(panel['raw']);raw[key]=raw[key].copy()
    if raw[key].dtype==np.uint8:raw[key].reshape(-1,2048)[0,:8]=np.frombuffer(np.float64(3).tobytes(),np.uint8)
    else:raw[key].flat[0]+=.1 if raw[key].dtype==np.float64 else 1
    with pytest.raises((AssertionError,ValueError)):check(panel,raw=raw)


@pytest.mark.parametrize('key,value',[('tag','wrong'),('physics_namespace','wrong'),('life',1),('rerouted_after_edit',True),
    ('diagnostic_to_lineage',True),('source_state_given_to_reader',True),('prospective_evidence',True),('new_main_lineages',1)])
def test_metadata_corruption(panel,key,value):
    meta=copy.deepcopy(panel['meta']);meta[key]=value
    with pytest.raises((AssertionError,ValueError)):check(panel,meta=meta)


def test_plan_corruption(panel):
    plan=copy.deepcopy(panel['plan']['lives'][0]);plan[0][0]['edited_sha256']='bad'
    with pytest.raises(ValueError):p.simulate_life(p.DISPOSABLE,0,panel['source']['founder_packets'],panel['source']['guide'],plan)
    meta=copy.deepcopy(panel['meta']);meta['cells'][0][0]['plan']['dose_rms']+=1
    with pytest.raises(AssertionError):check(panel,meta=meta)


def test_no_reroute(panel,monkeypatch):
    packet=panel['raw']['input'][0,0].tobytes();original=p.old.route;seen=[]
    def guarded(value,*args):
        assert value!=packet;seen.append(value);return original(value,*args)
    monkeypatch.setattr(p.old,'route',guarded)
    raw,_=p.cycle(packet,p.DISPOSABLE,0,'translated',panel['source']['guide'])
    assert len(seen)==1 and seen[0]==raw['outgoing'].tobytes()
    np.testing.assert_array_equal(raw['terminal_states'],panel['raw']['terminal_states'][0,0])


def test_reader_isolation(panel,monkeypatch):
    monkeypatch.setattr(p.sources,'labels',forbidden);monkeypatch.setattr(p.sources,'futures',forbidden)
    monkeypatch.setattr(p.old,'generate_founders',forbidden)
    signature=list(inspect.signature(p.simulate_life).parameters)
    assert signature==['spec','life','founders','guide','plan','order']
    raw,_=p.cycle(panel['raw']['input'][0,0].tobytes(),p.DISPOSABLE,0,'translated',panel['source']['guide'])
    np.testing.assert_array_equal(raw['read_states'][0],panel['source']['read_states'][0,1,0])


def test_roundtrip(panel,small,tmp_path):
    assert tmp_path.is_relative_to(run.ROOT/'tmp')
    raw=run.io.load_npz(panel['directory']/'raw.npz');meta=run.io.read_json(panel['directory']/'meta.json')
    assert check(panel,raw,meta)['passes']
    data,bp,bm,pred,fit=small;run.io.write_json(tmp_path/'fit.json',fit,run.ROOT)
    assert c.check_fits(pred,run.io.read_json(tmp_path/'fit.json'),data,bp,bm)['passes']
    with pytest.raises(FileExistsError):run.io.write_json(tmp_path/'fit.json',fit,run.ROOT)


def test_two_copy_boundary(small):
    data=small[0];a,e,t=data['start'],data['endpoint'],data['targeted'];x=m.matrices(a,e,t)
    assert [x[k].shape[-1] for k in m.MODELS]==[7,19,19,19,19,19]
    newe=e.copy();newe[...,1:,:]+=999
    q=m.matrices(a,newe,t)
    for k in ('starting',*m.NEW):np.testing.assert_array_equal(q[k],x[k])
    for i,name in enumerate(m.NEW):
        changed=t.copy()
        for j in range(3):
            if j!=i:changed[...,j,:]+=123
        np.testing.assert_array_equal(m.matrices(a,e,changed)[name],x[name])
    for k in m.MODELS:np.testing.assert_array_equal(x[k][...,:7],a)


def test_baseline_identity(small):
    data,bp,bm,pred,fit=small
    for name,source in m.BASELINES.items():
        np.testing.assert_array_equal(pred[name],bp[source]);assert fit[name]==bm[source]
    assert c.check_fits(pred,fit,data,bp,bm)['exact_saved_baselines']==3


def test_outer_isolation(small):
    data,bp,bm,pred,fit=small;changed=dict(data);changed['labels']=data['labels'].copy();changed['labels'][0]*=-1
    q,n=m.fit_new(changed,bp,bm)
    for k in m.NEW:
        np.testing.assert_array_equal(pred[k][0],q[k][0]);assert fit[k]['folds'][0]==n[k]['folds'][0]


def test_future_not_training(small):
    data,bp,bm,pred,fit=small;changed=dict(data);changed['futures']=-changed['futures']
    q,n=m.fit_new(changed,bp,bm)
    for k in m.MODELS:np.testing.assert_array_equal(q[k],pred[k]);assert n[k]==fit[k]


def test_independent_model(small,monkeypatch):
    data,bp,bm,pred,fit=small
    for name in ('matrices','fit_new','summarize'):monkeypatch.setattr(m,name,forbidden)
    for name in ('fit','nested','path','prepare'):monkeypatch.setattr(m.ridge,name,forbidden)
    assert c.check_fits(pred,fit,data,bp,bm)['passes']


@pytest.mark.parametrize('kind',['prediction','alpha','coefficient','inner_loss','training_id','baseline'])
def test_model_corruption(small,kind):
    data,bp,bm,pred,fit=small;pred={k:v.copy() for k,v in pred.items()};fit=copy.deepcopy(fit)
    if kind=='prediction':pred['attenuate'].flat[0]+=.1
    elif kind=='alpha':fit['attenuate']['folds'][0]['model']['alpha']=123
    elif kind=='coefficient':fit['attenuate']['folds'][0]['model']['beta'][0]+=.1
    elif kind=='inner_loss':fit['attenuate']['folds'][0]['inner_block_mse'][0][0]+=.1
    elif kind=='training_id':fit['attenuate']['folds'][0]['training_blocks'][0]=0
    else:pred['passive'].flat[0]+=.1
    with pytest.raises(AssertionError):c.check_fits(pred,fit,data,bp,bm)


def test_summary(scores):
    data,pred,fit,s=scores
    assert c.check_summary(s,pred,fit,data)['comparisons']==10
    assert s['confidence_intervals'] is s['prospective_evidence'] is s['model_selected_for_deployment'] is False
    assert s['central_comparison']['candidate']=='attenuate' and s['central_comparison']['reference']=='passive'


def test_mean_sham_is_loss(scores):
    data,pred,fit,s=scores;y=data['labels'];loss=m.squared(pred,y)
    np.testing.assert_array_equal(loss['mean_sham_loss'],((pred['sham_plus']-y)**2+(pred['sham_minus']-y)**2)/2)
    ensemble=((pred['sham_plus']+pred['sham_minus'])/2-y)**2
    assert not np.allclose(loss['mean_sham_loss'],ensemble)
    for v in s['repeated_future_comparisons']:
        np.testing.assert_allclose(v['individual_futures']['block_differences'],v['mean_target']['block_differences'],atol=1e-14,rtol=0)


@pytest.mark.parametrize('kind',['mse','group','central','cohort','future','mean_sham','prospective'])
def test_summary_corruption(scores,kind):
    data,pred,fit,summary=scores;s=copy.deepcopy(summary)
    if kind=='mse':s['models']['attenuate']['mse']+=.1
    elif kind=='group':s['models']['attenuate']['group_mse'][0]*=2
    elif kind=='central':s['central_comparison']['mse_reduction']+=.1
    elif kind=='cohort':s['models']['attenuate']['cohorts']['d135']['mse']+=.1
    elif kind=='future':s['repeated_future_models']['attenuate']['per_future_mse'][0]*=2
    elif kind=='mean_sham':s['comparisons'][5]['mse_reduction']+=.1
    else:s['prospective_evidence']=True
    with pytest.raises(AssertionError):c.check_summary(s,pred,fit,data)


def test_diagnostic_summary(panel):
    raw={k:np.stack([v]*4) for k,v in panel['raw'].items()}
    source=panel['source'];end=np.stack([source['diagnostic_features']]*4)
    plan=copy.deepcopy(panel['plan']);plan['lives']=[plan['lives'][0]]*4
    value=m.diagnostic_summary([raw]*32,np.stack([end]*32),[plan]*32)
    assert c.check_diagnostic_summary(value,[raw]*32,np.stack([end]*32),[plan]*32)['passes']
    value['matched_change_means'][0][0][0]+=.1
    with pytest.raises(AssertionError):c.check_diagnostic_summary(value,[raw]*32,np.stack([end]*32),[plan]*32)


def test_source_closure():
    files=run.source_files();assert len(files)>1800 and len(files)==len(set(files))
    assert all(run.WS/name in files for name in run.SCIENCE)


def test_resource_guards(monkeypatch):
    assert len(run.resources(False))<=6 and run.WORKERS==6
    monkeypatch.setenv('OMP_NUM_THREADS','2')
    with pytest.raises(RuntimeError):run.resources(False)


def test_disk_guard(monkeypatch):
    monkeypatch.setattr(run.shutil,'disk_usage',lambda _:SimpleNamespace(free=run.RESERVE+1024**3))
    with pytest.raises(RuntimeError):run.resources()


def test_detach_guard(monkeypatch):
    monkeypatch.delenv(run.ENV,raising=False)
    with pytest.raises(RuntimeError):run.detached_guard(True,'execute')
    run.detached_guard(False,'execute')


def test_startup_handshake(monkeypatch):
    reader,writer=os.pipe();monkeypatch.setenv(run.READY,str(writer));run.ready('benchmark')
    value=json.loads(os.read(reader,4096));os.close(reader)
    assert value==dict(stage='benchmark',pid=os.getpid(),status='STARTED') and run.READY not in os.environ


def test_no_automatic_successor():
    x=run.contract();assert x['automatic_polling'] is x['automatic_retry'] is x['automatic_successor'] is False
    code=inspect.getsource(run.detach)
    assert 'start_new_session=True' in code and 'stdin=subprocess.DEVNULL' in code and 'select.select([reader],[],[],55)' in code
    assert '.poll(' not in code and '.wait(' not in code
    assert 'io.failure(run,error,ROOT)' in inspect.getsource(run.execute)
    assert 'max_workers=WORKERS' in inspect.getsource(run.execute)


def test_main_barrier(monkeypatch):
    monkeypatch.setattr(run,'resources',lambda *a:None);monkeypatch.setattr(run,'inputs',forbidden)
    with pytest.raises(AssertionError):run.execute()
    code=inspect.getsource(run.execute)
    assert code.index("io.write_json(run/'MANIFEST.json'")<code.index('pool.submit(checked_block')
    assert 'plan_path()' in inspect.getsource(run.freeze)


@pytest.mark.parametrize('spec,life',[(('former_test',90016),0),(('d135',73000),0),(('fresh',100000),0),(p.DISPOSABLE,True),(p.DISPOSABLE,4)])
def test_namespace(spec,life):
    with pytest.raises(ValueError):p.validate(spec,life)


def test_no_source_mutation(panel):
    assert all(not v.flags.writeable for v in panel['source'].values())
    assert len(inspect.signature(p.cycle).parameters)==5
    assert set(p.EDITS)=={'attenuate','sham_plus','sham_minus'}
