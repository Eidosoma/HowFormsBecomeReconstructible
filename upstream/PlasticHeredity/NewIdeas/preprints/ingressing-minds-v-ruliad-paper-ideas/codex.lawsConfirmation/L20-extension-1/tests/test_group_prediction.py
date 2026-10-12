"""D152 synthetic qualification: no actual-case fits or tissue simulations."""
from copy import deepcopy
import inspect
import json
import os
from pathlib import Path
import numpy as np
import pytest
from l20_extension1 import group_models as model,group_check as check,group_run as run


@pytest.fixture(scope='module')
def small():return model.fixture(4)


@pytest.fixture(scope='module')
def nested(small):
    p,m=model.fit_all(small);return p,m


@pytest.fixture(scope='module')
def scores():
    data=model.fixture();rng=np.random.default_rng(152440)
    old={name:np.clip(data['labels']+rng.normal(scale=.1,size=(32,4,4)),-1,1) for name in model.MODELS}
    p={name:np.clip(data['labels']+rng.normal(scale=.09,size=(32,4,4)),-1,1) for name in model.MODELS}
    fits={name:dict(folds=[dict(model=dict(alpha=model.ALPHAS[i%6])) for i in range(32)]) for name in model.MODELS}
    s=model.summarize(p,fits,old,fits,data);return data,p,old,fits,s


def test_small_fold(small):
    p,m=model.fold_all(small);proof=check.check_fold_all(p,m,small)
    assert proof['models']==6 and proof['inner_folds']==18


def test_nested(small,nested):
    p,m=nested;assert check.check_all(p,m,small)['outer_folds']==24


@pytest.mark.parametrize('dimensions',[7,19])
def test_svd(small,dimensions):
    name='starting' if dimensions==7 else 'passive';x=model.matrices(small)[name].reshape(64,dimensions)
    y=small['labels'].ravel();g=np.tile(np.arange(4,dtype=np.int64),16)
    p,records=check.svd_path(x,y,g,x,g)
    for i,alpha in enumerate(model.ALPHAS):
        m=model.fit(x,y,g,alpha);check.old.same(m,records[i])
        np.testing.assert_allclose(model.predict(m,x,g),p[:,i],atol=2e-10,rtol=0)


def test_penalty_identity():
    rng=np.random.default_rng(1521);b=rng.normal(size=(4,19));delta=model.Q@b[1:];slopes=b[0]+delta
    np.testing.assert_allclose(model.Q.T@model.Q,np.eye(3),atol=0,rtol=0)
    np.testing.assert_allclose(delta.sum(axis=0),0,atol=1e-15,rtol=0)
    penalty=np.sum(b*b)
    np.testing.assert_allclose(penalty,np.sum(slopes*slopes)-3/16*np.sum(slopes.sum(axis=0)**2),atol=1e-12,rtol=0)
    z=rng.normal(size=(20,19));g=np.tile(np.arange(4,dtype=np.int64),5)
    np.testing.assert_allclose(model.design(z,g)@b.ravel(),np.sum(z*slopes[g],axis=1),atol=1e-12,rtol=0)


def test_group_permutation(small):
    x=small['start'].reshape(64,7);y=small['labels'].ravel();g=np.tile(np.arange(4,dtype=np.int64),16)
    permutation=np.array([2,0,3,1],np.int64);h=permutation[g]
    a=model.fit(x,y,g,.1);b=model.fit(x,y,h,.1)
    np.testing.assert_allclose(model.predict(a,x,g),model.predict(b,x,h),atol=1e-12,rtol=0)


def test_outer_isolation(small):
    x=small['start'];y=small['labels'];ids=small['block_ids'];p,m=model.outer_fold(x,y,ids,0)
    changed=y.copy();changed[0]=.999
    q,n=model.outer_fold(x,changed,ids,0);np.testing.assert_array_equal(p,q);assert m==n
    changed_x=x.copy();changed_x[0]+=100
    _,n=model.outer_fold(changed_x,y,ids,0);assert m==n
    assert 0 not in m['training_blocks'] and 0 not in m['inner_validation_blocks']


def test_inner_isolation(small,monkeypatch):
    calls=[];original=model.path
    def observed(x,y,g,test,h):
        result=original(x,y,g,test,h);calls.append((x.copy(),y.copy(),result.copy()));return result
    monkeypatch.setattr(model,'path',observed)
    x=small['start'];y=small['labels'];ids=small['block_ids'];model.outer_fold(x,y,ids,0);before=calls[0];calls.clear()
    changed=y.copy();changed[1]=-.999;model.outer_fold(x,changed,ids,0);after=calls[0]
    for a,b in zip(before,after):np.testing.assert_array_equal(a,b)


def test_future_not_training(small,nested):
    changed=deepcopy(small);changed['futures'][:]=999
    p,m=model.fit_all(changed);a,b=nested
    for name in p:np.testing.assert_array_equal(p[name],a[name])
    assert m==b


@pytest.mark.parametrize('source,index,affected',[
    ('endpoint',0,('passive','shuffle','attenuate','sham_plus','sham_minus')),
    ('endpoint',1,('passive',)),('endpoint',2,('shuffle',)),
    ('targeted',0,('attenuate',)),('targeted',1,('sham_plus',)),('targeted',2,('sham_minus',))])
def test_two_copy_boundary(small,source,index,affected):
    changed=deepcopy(small);changed[source][...,index,:]+=999
    a,b=model.matrices(small),model.matrices(changed)
    for name in model.MODELS:
        assert a[name].shape[-1]==(7 if name=='starting' else 19)
        assert np.array_equal(a[name],b[name])==(name not in affected)
        np.testing.assert_array_equal(b[name],check.matrices(changed)[name])


def test_no_hidden_features(small):
    changed=deepcopy(small);changed['matched_u1_minus_edit']=np.ones((4,4,4,6))*100
    changed['recovery']=np.ones((4,4,4,3,6))*200
    for k,v in model.matrices(small).items():np.testing.assert_array_equal(v,model.matrices(changed)[k])


def test_constants_ties(small):
    x=np.zeros_like(small['start']);y=np.full_like(small['labels'],.125)
    p,m=model.nested(x,y,small['block_ids']);np.testing.assert_array_equal(p,y)
    assert all(f['model']['alpha']==100 for f in m['folds'])
    assert all(np.array(f['model']['scale']).min()==1 for f in m['folds'])
    check.check_fold(p[0],m['folds'][0],x,y,small['block_ids'],0)


def test_rank_deficient(small):
    x=np.repeat(small['start'][...,:1],19,axis=-1);p,m=model.outer_fold(x,small['labels'],small['block_ids'],0)
    assert check.check_fold(p,m,x,small['labels'],small['block_ids'],0)['passes']


def test_clipping(small):
    x=small['start'].reshape(64,7);g=np.tile(np.arange(4,dtype=np.int64),16)
    m=model.fit(x,small['labels'].ravel(),g,.001);p=model.predict(m,x*1e9,g)
    assert np.max(abs(p))==1 and np.isfinite(p).all()


@pytest.mark.parametrize('kind',['nan','label','duplicate','groups','shape'])
def test_invalid_panel(small,kind):
    x=small['start'].copy();y=small['labels'].copy();ids=small['block_ids'].copy()
    if kind=='nan':x[0,0,0,0]=np.nan
    elif kind=='label':y[0,0,0]=2
    elif kind=='duplicate':ids[1]=ids[0]
    elif kind=='groups':x=x[:,:,:3];y=y[:,:,:3]
    else:x=x[:3];y=y[:3];ids=ids[:3]
    with pytest.raises(ValueError):model.nested(x,y,ids)


def test_missing_group(small):
    x=small['start'].reshape(64,7);y=small['labels'].ravel();g=np.tile(np.arange(4,dtype=np.int64),16);keep=g<3
    with pytest.raises(ValueError):model.fit(x[keep],y[keep],g[keep],.1)


def test_grid(small):
    x=small['start'].reshape(64,7);g=np.tile(np.arange(4,dtype=np.int64),16)
    with pytest.raises(ValueError):model.fit(x,small['labels'].ravel(),g,.5)


@pytest.mark.parametrize('kind',['coefficients','alpha','training_blocks','inner_block_mse','prediction'])
def test_model_corruption(small,nested,kind):
    p,m=nested;record=deepcopy(m['passive']['folds'][0]);prediction=p['passive'][0].copy()
    if kind=='coefficients':record['model']['coefficients'][0][0]+=.2
    elif kind=='alpha':record['model']['alpha']=.5
    elif kind=='training_blocks':record['training_blocks'].append(0)
    elif kind=='inner_block_mse':record['inner_block_mse'][0][0]+=.1
    else:prediction[0,0]+=.1
    with pytest.raises(AssertionError):check.check_fold(prediction,record,model.matrices(small)['passive'],small['labels'],small['block_ids'],0)


def test_summary(scores):
    data,p,old,fits,s=scores;assert check.check_summary(s,p,fits,old,fits,data)['architecture_contrasts']==6
    assert check.check_errors(model.case_errors(p,old,data),p,old,data)['case_arrays']==36


@pytest.mark.parametrize('groups',[1,4])
def test_group_divisors(groups):
    y=np.zeros((32,4,groups));p=np.ones_like(y)
    actual=check.error_stats(p,y);assert actual['mse']==1 and actual['mae_points']==actual['rmse_points']==100
    assert actual['block_mse']==[1]*32 and actual['group_mse']==[1]*groups
    delta=check.reduction(y,p);assert delta['mse_reduction']==1 and delta['relative_reduction_percent']==100
    assert delta['block_differences']==[1]*32


@pytest.mark.parametrize('kind',['absolute','group','architecture','future','metadata','mean_sham'])
def test_summary_corruption(scores,kind):
    data,p,old,fits,original=scores;s=deepcopy(original)
    if kind=='absolute':s['architectures']['shared']['models']['starting']['mse']+=.1
    elif kind=='group':s['architectures']['group_sensitive']['group_details']['passive'][2]['mse']+=.1
    elif kind=='architecture':s['architecture_comparisons'][0]['original']['mse_reduction']+=.1
    elif kind=='future':s['architecture_comparisons'][0]['individual_futures']['block_differences'][0]+=.1
    elif kind=='metadata':s['new_diagnostic_cycles']=1536
    else:s['architectures']['group_sensitive']['comparisons'][5]['mse_reduction']+=.1
    with pytest.raises(AssertionError):check.check_summary(s,p,fits,old,fits,data)


def test_mean_sham(scores):
    data,p,_,_,s=scores;a=(p['attenuate']-data['labels'])**2
    b=((p['sham_plus']-data['labels'])**2+(p['sham_minus']-data['labels'])**2)/2
    pair=s['architectures']['group_sensitive']['comparisons'][5]
    np.testing.assert_allclose(pair['mse_reduction'],(b-a).mean(),atol=1e-14,rtol=0)


def test_future_identity(scores):
    s=scores[-1]
    for row in s['architecture_comparisons']:
        np.testing.assert_allclose(row['individual_futures']['block_differences'],row['mean_target']['block_differences'],atol=1e-14,rtol=0)


def test_roundtrip(tmp_path,small,nested,scores):
    assert run.ROOT in tmp_path.resolve().parents;p,m=nested
    run.io.write_npz(tmp_path/'synthetic.npz',small,run.ROOT);run.io.write_npz(tmp_path/'predictions.npz',p,run.ROOT)
    run.io.write_json(tmp_path/'fits.json',m,run.ROOT)
    assert check.check_all(run.io.load_npz(tmp_path/'predictions.npz'),run.io.read_json(tmp_path/'fits.json'),
        run.io.load_npz(tmp_path/'synthetic.npz'))['passes']
    data,p,old,fits,s=scores;run.io.write_json(tmp_path/'summary.json',s,run.ROOT)
    assert check.check_summary(run.io.read_json(tmp_path/'summary.json'),p,fits,old,fits,data)['passes']


def test_source_closure():
    files=set(run.source_files());assert len(files)>1960
    assert all(run.WS/p in files for p in run.SCIENCE) and run.AUDIT in files
    assert run.previous.source.paths()[1]/'dataset.npz' in files
    assert run.previous.paths()[1]/'summary.json' in files


def test_exact_baselines():
    data,p,m=run.source_data();assert run.check_source_identity(data,p,m)['exact_shared_models']==6
    p['attenuate'][0,0,0]+=.1
    with pytest.raises(AssertionError):run.check_source_identity(data,p,m)


def test_resource_guard(monkeypatch):
    run.resources(False)
    monkeypatch.setattr(os,'sched_getaffinity',lambda _:set(range(7)))
    with pytest.raises(RuntimeError):run.resources(False)


def test_thread_guard(monkeypatch):
    monkeypatch.setenv('OPENBLAS_NUM_THREADS','2')
    with pytest.raises(RuntimeError):run.resources(False)


def test_disk_guard(monkeypatch):
    from collections import namedtuple
    usage=namedtuple('usage','total used free')
    monkeypatch.setattr(run.shutil,'disk_usage',lambda _:usage(100,99,1))
    with pytest.raises(RuntimeError):run.resources()


def test_detach_guard(monkeypatch):
    monkeypatch.delenv(run.ENV,raising=False);run.detached_guard(False,'execute')
    with pytest.raises(RuntimeError):run.detached_guard(True,'execute')


def test_startup_handshake(monkeypatch):
    reader,writer=os.pipe();monkeypatch.setenv(run.READY,str(writer));run.ready('benchmark')
    try:assert json.loads(os.read(reader,4096))==dict(stage='benchmark',pid=os.getpid(),status='STARTED')
    finally:os.close(reader)
    assert run.READY not in os.environ


def test_no_automatic_successor():
    source=inspect.getsource(run.detach)
    assert 'start_new_session=True' in source and 'stdin=subprocess.DEVNULL' in source
    assert 'select.select([reader],[],[],55)' in source
    assert '.poll(' not in source and '.wait(' not in source and 'sleep(' not in source
    assert 'execute(' not in inspect.getsource(run.benchmark)
    assert 'detach(' not in inspect.getsource(run.execute)
    assert run.contract()['automatic_successor'] is False


def test_no_dynamics():
    for module in (model,check,run):
        source=inspect.getsource(module)
        for forbidden in ('simulate(','.read_cycle(','.write_cycle(','.fresh_read(','.replay('):assert forbidden not in source
    assert run.contract()['new_dynamics']==0
