"""Synthetic D157 qualification; no actual-case fitting before the freeze."""
from copy import deepcopy
import inspect
import json
import os
import numpy as np
import pytest
from l20_extension1 import target_models as model,target_check as check,target_run as run


@pytest.fixture(scope='module')
def small():return model.fixture(4)


@pytest.fixture(scope='module')
def fitted(small):return model.fit_all(small)


@pytest.fixture(scope='module')
def summary(small,fitted):return model.summarize(fitted[0],fitted[1],small)


def test_small_comparison():
    data=model.fixture(4);p,raw,m=model.fit_all(data);s=model.summarize(p,raw,data)
    assert check.check_all(p,raw,m,data)['outer_fits']==864
    assert check.check_summary(s,p,raw,data)['target_contrasts']==294
    assert check.check_errors(model.case_errors(p,data),p,data)['case_arrays']==108


def test_outer_isolation(small):
    ys=model.targets(small);x=small['start'];ids=small['block_ids'];p,r,m=model.outer(x,ys,ids,0)
    ys[:,0]=.875;q,s,n=model.outer(x,ys,ids,0)
    np.testing.assert_array_equal(p,q);np.testing.assert_array_equal(r,s);assert m==n
    assert int(ids[0]) not in m['training_blocks']


def test_feature_isolation(small):
    ys=model.targets(small);x=small['start'].copy();ids=small['block_ids'];_,_,m=model.outer(x,ys,ids,0)
    x[0]+=100;_,_,n=model.outer(x,ys,ids,0);assert m==n


@pytest.mark.parametrize('arm',['original','future0','future3'])
def test_target_isolation(small,arm):
    data=deepcopy(small);ys=model.targets(data);x=data['start'];ids=data['block_ids'];p,_,m=model.outer(x,ys,ids,0)
    if arm=='original':data['labels'][1]=.9;affected={0}
    else:data['futures'][1,...,int(arm[-1])]=.9;affected={1+int(arm[-1]),5}
    q,_,n=model.outer(x,model.targets(data),ids,0)
    for i in range(6):
        if i not in affected:np.testing.assert_array_equal(p[i],q[i]);assert m['models'][i]==n['models'][i]
        else:assert not np.array_equal(p[i],q[i])


@pytest.mark.parametrize('source,index,affected',[
    ('endpoint',0,('one_copy',)+tuple(prefix+k for prefix in ('separate:','mean:') for k in model.EDITED)),
    ('endpoint',1,('separate:passive','mean:passive')),('endpoint',2,('separate:shuffle','mean:shuffle')),
    ('targeted',0,('separate:attenuate','mean:attenuate')),('targeted',1,('separate:sham_plus','mean:sham_plus')),
    ('targeted',2,('separate:sham_minus','mean:sham_minus'))])
def test_feature_boundary(small,source,index,affected):
    data=deepcopy(small);data[source][...,index,:]+=99;a=model.features(small);b=model.features(data)
    independent=check.matrices(data)
    for name in model.OBSERVERS:
        np.testing.assert_array_equal(b[name],independent[name]);assert np.array_equal(a[name],b[name])==(name not in affected)


def test_no_hidden_features(small,fitted):
    data=deepcopy(small);data['hidden_response']=np.ones((4,4,4))*999
    p,raw,m=model.fit_all(data)
    for k in p:np.testing.assert_array_equal(p[k],fitted[0][k]);np.testing.assert_array_equal(raw[k],fitted[1][k])
    assert m==fitted[2]


def test_averaging_identity(small,fitted):
    p,raw,m=fitted;proof=check.check_all(p,raw,m,small);assert proof['linear_averaging_identity']
    for k in raw:np.testing.assert_allclose(raw[k][5],raw[k][1:5].mean(axis=0),atol=1e-12,rtol=0)


def test_equal_targets(small):
    data=deepcopy(small);data['futures'][...]=data['labels'][...,None];p,raw,m=model.fit_all(data)
    for k in p:
        for j in range(1,6):np.testing.assert_array_equal(p[k][j],p[k][0]);np.testing.assert_array_equal(raw[k][j],raw[k][0])
    assert check.check_all(p,raw,m,data)['passes']


def test_repeat_permutation(small,fitted):
    data=deepcopy(small);perm=[3,1,0,2];data['futures']=data['futures'][...,perm];p,raw,m=model.fit_all(data)
    for k in p:
        np.testing.assert_allclose(p[k][5],fitted[0][k][5],atol=1e-12,rtol=0)
        for j,old in enumerate(perm):np.testing.assert_array_equal(p[k][j+1],fitted[0][k][old+1])


def test_clipping(small):
    x=small['start'].copy();x[0]*=1e4;p,raw,m=model.outer(x,model.targets(small),small['block_ids'],0)
    assert np.max(abs(p))==1 and np.max(abs(raw))>1
    np.testing.assert_array_equal(p,np.clip(raw,-1,1));np.testing.assert_allclose(raw[5],raw[1:5].mean(axis=0),atol=1e-9,rtol=0)
    assert np.max(abs(p[5]-p[1:5].mean(axis=0)))>0


def test_constants(small):
    data=deepcopy(small)
    for k in ('start','endpoint','targeted'):data[k][:]=0
    data['labels'][:]=.125;data['futures'][:]=.25;p,raw,m=model.fit_all(data)
    for k in p:
        np.testing.assert_array_equal(p[k][0],np.full((3,4,4,4),.125))
        np.testing.assert_array_equal(p[k][1:],np.full((5,3,4,4,4),.25))
    assert check.check_all(p,raw,m,data)['passes']


def test_rank_deficient(small):
    data=deepcopy(small)
    for k in ('start','endpoint','targeted'):data[k][...]=data[k][...,:1]
    p,raw,m=model.fit_all(data);assert check.check_all(p,raw,m,data)['passes']


def test_group_permutation(small):
    perm=[2,0,3,1];x=small['start'];ys=model.targets(small);ids=small['block_ids']
    p,_,_=model.outer(x,ys,ids,0);q,_,_=model.outer(x[:,:,perm],ys[:,:,:,perm],ids,0)
    np.testing.assert_allclose(q,p[:,:,:,perm],atol=1e-12,rtol=0)


@pytest.mark.parametrize('kind',['nan','label','future','ids','shape','dtype','missing_group'])
def test_invalid_input(small,kind):
    data=deepcopy(small)
    if kind=='nan':data['start'][0,0,0,0]=np.nan
    elif kind=='label':data['labels'][0,0,0]=2
    elif kind=='future':data['futures'][0,0,0,0]=-2
    elif kind=='ids':data['block_ids'][0]=data['block_ids'][1]
    elif kind=='shape':data['futures']=data['futures'][...,:3]
    elif kind=='dtype':data['labels']=data['labels'].astype(np.float32)
    else:data['start']=data['start'][:,:,:3]
    with pytest.raises(ValueError):model.fit_all(data)


@pytest.mark.parametrize('kind',['prediction','raw','coefficient','offset','scale','training','validation','target','alpha','header'])
def test_fit_corruption(small,fitted,kind):
    p,raw,m=deepcopy(fitted);fold=m['starting']['folds'][0]
    if kind=='prediction':p['starting'][0,0,0,0,0]+=.1
    elif kind=='raw':raw['starting'][0,0,0,0,0]+=.1
    elif kind=='coefficient':fold['models'][0][0]['coefficients'][0][0]+=.1
    elif kind=='offset':fold['models'][0][0]['offsets'][0]+=.1
    elif kind=='scale':fold['models'][0][0]['scale'][0]+=.1
    elif kind=='training':fold['training_blocks'].append(90000)
    elif kind=='validation':fold['validation_block']=-1
    elif kind=='target':fold['models'][1]=deepcopy(fold['models'][2])
    elif kind=='alpha':fold['models'][0][0]['alpha']=.01
    else:m['starting']['inner_selection']=True
    with pytest.raises(AssertionError):check.check_all(p,raw,m,small)


@pytest.mark.parametrize('kind',['model','group','repeat','omission','contrast','target','identity','clipping','metadata'])
def test_summary_corruption(small,fitted,summary,kind):
    p,raw,_=fitted;s=deepcopy(summary);part=s['scores']['0.01']
    if kind=='model':part['models']['original/starting']['original']['mse']+=.1
    elif kind=='group':part['models']['future_mean/starting']['individual_futures']['group_mse'][0]+=.1
    elif kind=='repeat':part['comparisons'][0]['by_repeat'][0]['mse_reduction']+=.1
    elif kind=='omission':part['comparisons'][0]['individual_futures']['leave_one_score_block_out'][0]+=.1
    elif kind=='contrast':part['comparisons'][0]['mean_target']['mse_reduction']+=.1
    elif kind=='target':part['comparisons'][-1]['reference_target']='future2'
    elif kind=='identity':part['averaging_identity']['starting']['max_abs_unclipped_mean_residual']+=.1
    elif kind=='clipping':part['models']['original/starting']['clipped_cases']+=1
    else:s['held_out_outcomes_used_for_training']=True
    with pytest.raises(AssertionError):check.check_summary(s,p,raw,small)


@pytest.mark.parametrize('scope',['original','futures','mean'])
def test_error_corruption(small,fitted,scope):
    p=fitted[0];errors=model.case_errors(p,small);errors['starting__'+scope+'__squared'].flat[0]+=.1
    with pytest.raises(AssertionError):check.check_errors(errors,p,small)


def test_mean_losses(small):
    data=deepcopy(small);data['labels'][:]=0;data['futures'][:]=0
    p={k:np.zeros((6,3,4,4,4)) for k in model.OBSERVERS}
    for k in p:
        for j in range(1,5):p[k][j]=(-1.)**j
    p['mean:sham_plus'][5]=1;p['mean:sham_minus'][5]=-1
    loss=model.losses(p,data,0)
    for key in ('single_mean_loss/starting','future_mean/mean:mean_sham_loss'):
        for value in loss[key]:np.testing.assert_array_equal(value,np.ones_like(value))
    np.testing.assert_array_equal(p['starting'][1:5].mean(axis=0),np.zeros((3,4,4,4)))
    s=model.summarize(p,p,data);assert check.check_summary(s,p,p,data)['passes']


def test_future_identity(small,fitted,summary):
    p=fitted[0];f=small['futures'];variance=f.var(axis=-1)
    for k in p:np.testing.assert_allclose(((p[k][...,None]-f)**2).mean(axis=-1),(p[k]-f.mean(axis=-1))**2+variance,atol=1e-14,rtol=0)
    for row in summary['scores']['0.01']['comparisons']:
        np.testing.assert_allclose(row['individual_futures']['block_differences'],row['mean_target']['block_differences'],atol=1e-14,rtol=0)


def test_score_omissions():
    c=np.zeros((4,4,4));r=np.broadcast_to(np.arange(4)[:,None,None],c.shape).copy()
    a=model.paired(c,r);check.same(a,check.paired(c,r))
    for j,v in enumerate(a['leave_one_score_block_out']):assert v==np.delete(r,j,axis=0).mean()


def test_specs():
    assert len(model.observer_pairs())==55 and model.observer_pairs()==check.observer_pairs()
    assert model.specs()==check.specifications() and len(model.specs())==428
    assert len({tuple(s.values()) for s in model.specs()})==428
    assert model.metadata(16)['new_fits']==3456 and model.metadata(16)['new_predictions']==55296


def test_roundtrip(small,fitted,summary,tmp_path):
    assert run.ROOT in tmp_path.resolve().parents;p,raw,m=fitted
    run.io.write_npz(tmp_path/'p.npz',p,run.ROOT);run.io.write_npz(tmp_path/'raw.npz',raw,run.ROOT)
    run.io.write_json(tmp_path/'fits.json',m,run.ROOT);run.io.write_json(tmp_path/'summary.json',summary,run.ROOT)
    q=run.io.load_npz(tmp_path/'p.npz');r=run.io.load_npz(tmp_path/'raw.npz');records=run.io.read_json(tmp_path/'fits.json')
    assert check.check_all(q,r,records,small)['passes']
    assert check.check_summary(run.io.read_json(tmp_path/'summary.json'),q,r,small)['passes']


def test_source_identity():
    data=run.source_data();assert run.source_identity(data)['exact_arrays']==6
    data['labels'][0,0,0]+=.1
    with pytest.raises(AssertionError):run.source_identity(data)


def test_source_closure():
    files=set(run.source_files());assert len(files)>2130 and run.AUDIT in files
    assert all(run.WS/p in files for p in run.SCIENCE)
    assert run.previous.source.paths()[1]/'dataset.npz' in files


def test_no_dynamics_or_old_refits(small,monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('old reference refit or dynamics forbidden')
    monkeypatch.setattr(run.previous,'saved_audit',forbidden)
    for module in (model.old,model.old.prior,model.old.prior.prior):monkeypatch.setattr(module,'fit_all',forbidden)
    p,raw,m=model.fit_all(small);assert check.check_all(p,raw,m,small)['passes']
    for module in (model,check,run):
        for term in ('simulate(','.read_cycle(','.write_cycle(','.nested(','.outer_fold('):assert term not in inspect.getsource(module)


def test_resource_guard(monkeypatch):
    run.resources(False);monkeypatch.setattr(os,'sched_getaffinity',lambda _:set(range(7)))
    with pytest.raises(RuntimeError):run.resources(False)


def test_thread_guard(monkeypatch):
    monkeypatch.setenv('OPENBLAS_NUM_THREADS','2')
    with pytest.raises(RuntimeError):run.resources(False)


def test_detach_guard(monkeypatch):
    monkeypatch.delenv(run.ENV,raising=False);run.detached_guard(False,'execute')
    with pytest.raises(RuntimeError):run.detached_guard(True,'execute')


def test_startup_handshake(monkeypatch):
    reader,writer=os.pipe();monkeypatch.setenv(run.READY,str(writer));run.ready('benchmark')
    try:assert json.loads(os.read(reader,4096))==dict(stage='benchmark',pid=os.getpid(),status='STARTED')
    finally:os.close(reader)
    assert run.READY not in os.environ


def test_no_automatic_successor():
    code=inspect.getsource(run.detach)
    assert 'start_new_session=True' in code and 'stdin=subprocess.DEVNULL' in code
    assert 'select.select([reader],[],[],55)' in code
    assert '.poll(' not in code and '.wait(' not in code and 'sleep(' not in code
    assert 'execute(' not in inspect.getsource(run.benchmark) and 'detach(' not in inspect.getsource(run.execute)
    assert run.contract()['automatic_successor'] is False
