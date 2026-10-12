"""D150 qualification: disposable sources and synthetic labels only."""
import copy
import inspect
import json
import os
from types import SimpleNamespace
import numpy as np
import pytest
from l20_extension1 import recovery_features as f,recovery_models as m,recovery_check as c,recovery_run as run


def forbidden(*args,**kwargs):raise AssertionError('forbidden production/dynamics call')


@pytest.fixture(scope='module')
def block():
    raw,meta=f.diagnostic(run.DISPOSABLE,True)
    return raw,meta,f.extract(raw)


@pytest.fixture(scope='module')
def small():
    data,y=m.fixture(4);ids=np.arange(4,dtype=np.int64)
    p,models=m.fit_all(f.assemble(data),y,ids)
    return data,y,ids,p,models


@pytest.fixture(scope='module')
def panel():
    data=run.synthetic_panel();y=data['labels'];rng=np.random.default_rng(123)
    p={k:np.clip(y+rng.normal(scale=.08,size=y.shape),-1,1) for k in m.MODELS}
    fits={k:dict(folds=[dict(model=dict(alpha=m.ALPHAS[i%6])) for i in range(32)]) for k in m.MODELS}
    s=m.summarize(p,fits,y,data['futures'],f.SPECS)
    return data,p,fits,s


def test_feature_block():
    value,y,proof=run.checked_feature(run.DISPOSABLE,True)
    assert proof==dict(passes=True,cases=16,diagnostic_copies=48,recovery_values=288,new_dynamics=0)
    assert y.shape==(4,4) and value['start'].shape==(4,4,7)


def test_other_disposable_schema():
    value,y,proof=run.checked_feature(('disposable_test',514240),True)
    assert proof['passes'] and y.shape==(4,4) and value['start'].shape==(4,4,7)


def test_small_models():
    data,y=m.fixture(4);ids=np.arange(4,dtype=np.int64)
    p,models=m.fit_all(f.assemble(data),y,ids)
    proof=c.check_fits(p,models,data,y,ids)
    assert proof['models']==5 and proof['outer_folds']==20 and proof['inner_folds']==60


@pytest.mark.parametrize('role',[0,1])
@pytest.mark.parametrize('kind',['zero','constant','A','B','random'])
def test_shapes_axes(role,kind):
    value={'zero':np.zeros((16,16)),'constant':np.ones((16,16)),
        'A':f.TARGETS[0],'B':f.TARGETS[1],'random':np.random.default_rng(150).normal(size=(16,16))}[kind]
    np.testing.assert_allclose(f.best(value,role),c.shape(value,role),atol=1e-13,rtol=0)
    np.testing.assert_allclose(f.axis_rms(value,role),c.axes(value,role),atol=1e-13,rtol=0)
    for shift in ((3,5),(8,8)):
        z=np.roll(value,shift,(0,1))
        np.testing.assert_allclose(f.best(z,role),f.best(value,role),atol=1e-13,rtol=0)
        np.testing.assert_allclose(f.axis_rms(z,role),f.axis_rms(value,role),atol=1e-13,rtol=0)
    assert abs(np.sum(f.axis_rms(value,role)**2)-np.var(value))<1e-12


def test_recovery_telescopes(block):
    value=block[2];r=value['recovery'].reshape(4,4,3,3,2)
    np.testing.assert_array_equal(r,np.diff(value['stages'],axis=-2))
    np.testing.assert_allclose(r.sum(axis=-2),value['stages'][...,-1,:]-value['stages'][...,0,:],atol=1e-15,rtol=0)


@pytest.mark.parametrize('key',['start','endpoint','recovery','stages'])
def test_feature_corruption(block,key):
    value={k:v.copy() for k,v in block[2].items()};value[key].flat[-1]+=.01
    with pytest.raises(AssertionError):c.check_features(value,block[0])


@pytest.mark.parametrize('key',['initial_features','diagnostic_features','routed','read_states','write_states'])
def test_source_corruption(block,key):
    raw=dict(block[0]);raw[key]=raw[key].copy()
    if key=='routed':raw[key][0,0,0,:8]=np.frombuffer(np.float64(3).tobytes(),np.uint8)
    elif key=='read_states':raw[key][0,0,0,-1,2,0,0]+=.1
    elif key=='write_states':raw[key][0,0,0,2,2,0,0]+=.1
    else:raw[key].flat[0]+=.1
    with pytest.raises(AssertionError):c.check_features(block[2],raw)


def test_checkpoint_continuity(block):
    raw=dict(block[0]);raw['write_states']=raw['write_states'].copy();raw['write_states'][0,0,0,0,2,0,0]+=.01
    with pytest.raises(AssertionError):f.extract(raw)


@pytest.mark.parametrize('key',['outcomes','lineage','future_labels','host_id'])
def test_feature_boundary(block,key):
    raw=dict(block[0]);raw[key]=np.zeros((4,4))
    with pytest.raises(ValueError):f.extract(raw)


def test_two_copy_boundary():
    data,_=m.fixture(4);original=f.assemble(data)
    assert [original[k].shape[-1] for k in m.MODELS]==[7,19,19,31,31]
    for forbidden_copy,observer in ((2,'passive'),(1,'challenge')):
        changed={k:v.copy() for k,v in data.items()}
        changed['endpoint'][...,forbidden_copy,:]+=500;changed['recovery'][...,forbidden_copy,:]-=400
        new=f.assemble(changed)
        for name in ('starting',observer+'_endpoint',observer+'_recovery'):np.testing.assert_array_equal(original[name],new[name])
    for name in m.MODELS:np.testing.assert_array_equal(original[name][...,:7],data['start'])


def test_outer_isolation(small):
    data,y,ids,p,models=small;changed=y.copy();changed[0]=np.clip(-changed[0]+.4,-1,1)
    q,fit=m.nested(f.assemble(data)['challenge_recovery'],changed,ids)
    np.testing.assert_array_equal(q[0],p['challenge_recovery'][0])
    assert fit['folds'][0]==models['challenge_recovery']['folds'][0]
    for outer,fold in enumerate(fit['folds']):
        assert fold['validation_block']==ids[outer] and ids[outer] not in fold['training_blocks']
        assert len(fold['training_blocks'])==3 and fold['training_blocks']==fold['inner_validation_blocks']


def test_inner_isolation(monkeypatch):
    data,y=m.fixture(4);x=data['start'];x[...,0]=np.arange(4)[:,None,None]
    original=m.path;seen=[]
    def spy(train,labels,groups,test,testgroups):
        trainblocks=set(train[:,0].astype(int));validation=set(test[:,0].astype(int))
        assert len(trainblocks)==2 and len(validation)==1 and not trainblocks&validation
        assert len(train)==32 and len(test)==16
        seen.append((trainblocks,validation))
        return original(train,labels,groups,test,testgroups)
    monkeypatch.setattr(m,'path',spy);m.nested(x,y,np.arange(4,dtype=np.int64))
    for outer in range(4):
        for a,b in seen[3*outer:3*outer+3]:assert outer not in a|b


def test_training_only_scaling():
    rng=np.random.default_rng(199);x=rng.normal(size=(64,7));x[:,-1]=3.;y=rng.uniform(-.5,.5,64);g=np.tile(np.arange(4,dtype=np.int64),16)
    model=m.fit(x,y,g,.1);assert model['scale'][-1]==1
    expected=m.predict(model,x,g);large=x+1e6;m.predict(model,large,g)
    assert model==m.fit(x,y,g,.1)
    other,models=c.svd_path(x,y,g,x,g)
    np.testing.assert_allclose(expected,other[:,2],atol=2e-10,rtol=0);c.same(model,models[2])


def test_intercepts_ties():
    x=np.zeros((4,4,4,7));y=np.broadcast_to(np.array([-.7,-.3,.3,.7]),(4,4,4)).copy()
    p,models=m.nested(x,y,np.arange(4,dtype=np.int64))
    np.testing.assert_allclose(p,y,atol=1e-15,rtol=0)
    assert all(fold['model']['alpha']==100 for fold in models['folds'])
    assert all(np.all(np.array(fold['model']['scale'])==1) for fold in models['folds'])


def test_clipping():
    model=dict(means=np.zeros((4,1)),offsets=np.zeros(4),scale=[1],beta=[10])
    np.testing.assert_array_equal(m.predict(model,np.array([[10.],[-10.]]),np.array([0,1])),[1,-1])


def test_independent_checker(block,small,monkeypatch):
    for name in ('extract','assemble','best','axis_rms'):monkeypatch.setattr(f,name,forbidden)
    for name in ('prepare','fit','path','nested','summarize'):monkeypatch.setattr(m,name,forbidden)
    assert c.check_features(block[2],block[0])['passes']
    data,y,ids,p,models=small;assert c.check_fits(p,models,data,y,ids)['passes']


@pytest.mark.parametrize('kind',['prediction','alpha','coefficient','inner_loss','training_id','scale'])
def test_model_corruption(small,kind):
    data,y,ids,original,models=small;p=original['starting'].copy();fit=copy.deepcopy(models['starting'])
    if kind=='prediction':p.flat[0]+=.1
    elif kind=='alpha':fit['folds'][0]['model']['alpha']=123
    elif kind=='coefficient':fit['folds'][0]['model']['beta'][0]+=.1
    elif kind=='inner_loss':fit['folds'][0]['inner_block_mse'][0][0]+=.1
    elif kind=='training_id':fit['folds'][0]['training_blocks'][0]=0
    elif kind=='scale':fit['folds'][0]['model']['scale'][0]+=.1
    with pytest.raises(AssertionError):c.check_nested(p,fit,data['start'],y,ids)


def test_summary(panel):
    data,p,models,s=panel
    assert c.check_summary(s,p,models,data['labels'],data['futures'],f.SPECS)['passes']
    assert s['prospective_evidence'] is s['confidence_intervals'] is s['new_challenge_selected'] is False
    assert s['former_test_is_now_development'] and len(s['comparisons'])==8
    for pair in s['repeated_future_comparisons']:
        np.testing.assert_allclose(pair['individual_futures']['block_differences'],pair['mean_target']['block_differences'],atol=1e-14,rtol=0)


def test_future_not_training(panel):
    data,p,models,s=panel
    changed=m.summarize(p,models,data['labels'],-data['futures'],f.SPECS)
    assert changed['models']==s['models'] and changed['comparisons']==s['comparisons']
    assert changed['repeated_future_models']!=s['repeated_future_models']
    for function in (m.nested,m.fit_all,m.fit,m.path):assert 'future' not in inspect.getsource(function)


@pytest.mark.parametrize('kind',['mse','normalization','primary','cohort','prospective','future'])
def test_summary_corruption(panel,kind):
    data,p,models,s=panel;s=copy.deepcopy(s)
    if kind=='mse':s['models']['starting']['mse']+=.1
    elif kind=='normalization':s['models']['starting']['group_mse'][0]*=2
    elif kind=='primary':s['central_comparison']['mse_reduction']+=.1
    elif kind=='cohort':s['models']['starting']['cohorts']['d135']['mse']+=.1
    elif kind=='prospective':s['prospective_evidence']=True
    elif kind=='future':s['repeated_future_models']['starting']['individual_future_mse']+=.1
    with pytest.raises(AssertionError):c.check_summary(s,p,models,data['labels'],data['futures'],f.SPECS)


def test_roundtrip(block,small,panel,tmp_path):
    assert tmp_path.is_relative_to(run.ROOT/'tmp')
    run.io.write_npz(tmp_path/'features.npz',block[2],run.ROOT)
    assert c.check_features(run.io.load_npz(tmp_path/'features.npz'),block[0])['passes']
    data,y,ids,p,models=small;run.io.write_json(tmp_path/'fits.json',models,run.ROOT)
    assert c.check_fits(p,run.io.read_json(tmp_path/'fits.json'),data,y,ids)['passes']
    data,p,models,s=panel
    reordered=json.loads(json.dumps(models,sort_keys=True))
    assert m.summarize(p,reordered,data['labels'],data['futures'],f.SPECS)==s
    with pytest.raises(FileExistsError):run.io.write_npz(tmp_path/'features.npz',block[2],run.ROOT)


@pytest.mark.parametrize('key',['OMP_NUM_THREADS','PYTHONDONTWRITEBYTECODE','TMPDIR'])
def test_resource_guards(monkeypatch,key):
    run.resources();monkeypatch.setenv(key,'99' if key!='TMPDIR' else '/tmp')
    with pytest.raises(RuntimeError):run.resources()


def test_cpu_disk_guards(monkeypatch):
    monkeypatch.setattr(run.os,'sched_getaffinity',lambda _:set(range(7)))
    with pytest.raises(RuntimeError):run.resources()
    monkeypatch.setattr(run.os,'sched_getaffinity',lambda _:set(range(6)))
    monkeypatch.setattr(run.shutil,'disk_usage',lambda _:SimpleNamespace(free=0))
    with pytest.raises(RuntimeError):run.resources()


def test_detach_guard(monkeypatch):
    monkeypatch.delenv(run.ENV,raising=False)
    with pytest.raises(RuntimeError):run.detached_guard(True,'execute')
    run.detached_guard(False,'execute')


def test_startup_handshake(monkeypatch):
    reader,writer=os.pipe();monkeypatch.setenv(run.READY,str(writer))
    run.ready('execute');value=json.loads(os.read(reader,4096));os.close(reader)
    assert value==dict(stage='execute',pid=os.getpid(),status='STARTED') and run.READY not in os.environ


def test_no_automatic_successor():
    contract=run.contract();assert contract['automatic_polling'] is contract['automatic_retry'] is contract['automatic_successor'] is False
    code=inspect.getsource(run.detach)
    assert 'start_new_session=True' in code and 'stdin=subprocess.DEVNULL' in code
    assert 'select.select([reader],[],[],55)' in code and '.poll(' not in code and '.wait(' not in code
    for function in (run.execute,run.benchmark):assert 'detach(' not in inspect.getsource(function)
    assert 'io.failure(run,error,ROOT)' in inspect.getsource(run.execute)
    assert 'single-use' in inspect.getsource(run.execute)


def test_source_closure():
    files=run.source_files();assert len(files)>=1308 and len(files)==len(set(files))
    assert all(run.WS/name in files for name in run.SCIENCE)
    for name,digest in run.PREDECESSORS.items():assert run.sha256_file(run.ROOT/'runs'/name/'COMPLETE.json')==digest


def test_no_dynamics(block,monkeypatch):
    monkeypatch.setattr(c.old_audit.physics,'step',forbidden)
    for name in ('read_trace','write_trace'):monkeypatch.setattr(c.old_audit.prior,name,forbidden)
    assert c.check_features(f.extract(block[0]),block[0])['new_dynamics']==0
    assert c.check_labels(run.DISPOSABLE,f.labels(run.DISPOSABLE,True),True)


@pytest.mark.parametrize('spec',[('d135',75008),('former_test',90016),('disposable_dev',True),('fresh',100000)])
def test_namespace(spec):
    with pytest.raises(ValueError):f.paths(spec)


def test_bad_model_inputs():
    data,y=m.fixture(4);ids=np.arange(4,dtype=np.int64)
    with pytest.raises(ValueError):m.nested(data['start'],y,np.zeros(4,np.int64))
    with pytest.raises(ValueError):m.nested(data['start'][:3],y[:3],ids[:3])
    y[0,0,0]=np.nan
    with pytest.raises(ValueError):m.nested(data['start'],y,ids)


def test_nonfinite_and_byte_schema():
    z=np.zeros((16,16));z[0,0]=np.nan
    with pytest.raises(ValueError):f.best(z,0)
    with pytest.raises(ValueError):f.decode(np.zeros(2048))
    with pytest.raises(ValueError):f.decode(np.zeros(2047,np.uint8))


@pytest.mark.parametrize('amplitude',[0.,.2,np.nextafter(.2,np.inf),1.])
def test_target_threshold(amplitude):
    for role in (0,1):
        v=amplitude*f.TARGETS[role]
        assert f.preference(v,role)==c.body(v,role)==(.5 if amplitude>.2 else 0.)


def test_main_barrier(monkeypatch):
    monkeypatch.setattr(run,'resources',lambda *a:None)
    monkeypatch.setattr(run,'inputs',forbidden)
    with pytest.raises(AssertionError):run.execute()
    source=inspect.getsource(run.execute)
    assert source.index('manifest_inputs=inputs()')<source.index('features.diagnostic(spec)')
    assert source.index("io.write_json(run/'MANIFEST.json'")<source.index('features.diagnostic(spec)')


def test_no_source_mutation(block):
    assert all(not v.flags.writeable for v in block[0].values())
    again=f.extract(block[0])
    for k in again:np.testing.assert_array_equal(again[k],block[2][k])
