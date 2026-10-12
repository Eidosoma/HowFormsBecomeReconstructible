"""D155 synthetic qualification; source checks never refit actual references."""
from copy import deepcopy
import inspect
import json
import os
import numpy as np
import pytest
from l20_extension1 import mean_models as model, mean_check as check, mean_run as run


@pytest.fixture(scope='module')
def small():return model.prior.prior.group.fixture(4)


@pytest.fixture(scope='module')
def small_fits(small):return model.fit_all(small)


@pytest.fixture(scope='module')
def full():
    data,refs,nested,source=model.fixture();p,m=model.fit_all(data)
    return data,p,m,refs,nested,source,model.summarize(p,refs,source,data)


def test_full_comparison():
    data,refs,nested,source=model.fixture();p,m=model.fit_all(data);s=model.summarize(p,refs,source,data)
    assert check.check_all(p,m,data)['outer_fits']==480
    assert check.check_summary(s,p,refs,nested,source,data)['new_contrasts']==90
    assert check.check_errors(model.case_errors(p,refs,nested,data),p,refs,nested,data)['retained_case_arrays']==75


def test_outer_isolation(small):
    x=model.features(small)['passive'];y=small['labels'];ids=small['block_ids'];p,m=model.prior.prior.outer(x,y,ids,0)
    changed=y.copy();changed[0]=.999;q,n=model.prior.prior.outer(x,changed,ids,0)
    np.testing.assert_array_equal(p,q);assert m==n and 0 not in m['training_blocks']
    altered=x.copy();altered[0]+=100;_,n=model.prior.prior.outer(altered,y,ids,0);assert m==n


def test_future_not_training(small,small_fits):
    changed=deepcopy(small);changed['futures'][:]=999;p,m=model.fit_all(changed)
    for name in p:np.testing.assert_array_equal(p[name],small_fits[0][name])
    assert m==small_fits[1]


@pytest.mark.parametrize('source,index,affected',[
    ('start',None,('passive','shuffle','attenuate','sham_plus','sham_minus')),
    ('endpoint',0,('passive','shuffle','attenuate','sham_plus','sham_minus')),
    ('endpoint',1,('passive',)),('endpoint',2,('shuffle',)),
    ('targeted',0,('attenuate',)),('targeted',1,('sham_plus',)),('targeted',2,('sham_minus',))])
def test_two_copy_boundary(small,source,index,affected):
    changed=deepcopy(small)
    if index is None:changed[source][...]+=8
    else:changed[source][...,index,:]+=8
    a=model.features(small);b=model.features(changed);c=check.features(changed)
    for name in model.MODELS:
        assert b[name].shape==(4,4,4,13) and np.array_equal(a[name],b[name])==(name not in affected)
        np.testing.assert_array_equal(b[name],c[name])
        if index is not None and name in affected:
            np.testing.assert_allclose(b[name][...,7:]-a[name][...,7:],4,atol=2e-15,rtol=0)


def test_raw_average(small):
    data=deepcopy(small);data['endpoint'][...,0,:]=12;data['endpoint'][...,1,:]=4
    x=model.features(data)['passive'];np.testing.assert_array_equal(x[...,7:],np.full((4,4,4,6),8))
    np.testing.assert_array_equal(x[...,:7],data['start'])


@pytest.mark.parametrize('name,source,index',[('passive','endpoint',1),('shuffle','endpoint',2),
    ('attenuate','targeted',0),('sham_plus','targeted',1),('sham_minus','targeted',2)])
def test_copy_exchange(small,small_fits,name,source,index):
    data=deepcopy(small);u=data['endpoint'][...,0,:].copy();v=data[source][...,index,:].copy()
    data['endpoint'][...,0,:]=v;data[source][...,index,:]=u
    np.testing.assert_array_equal(model.features(data)[name],model.features(small)[name])
    p,m=model.fit_all(data);np.testing.assert_array_equal(p[name],small_fits[0][name]);assert m[name]==small_fits[1][name]


def test_identical_copies(small):
    data=deepcopy(small);u=data['endpoint'][...,0,:].copy()
    for i in range(3):data['endpoint'][...,i,:]=u;data['targeted'][...,i,:]=u
    p,m=model.fit_all(data);one=model.prior.features(data)
    for name,x in model.features(data).items():
        np.testing.assert_array_equal(x,one);np.testing.assert_array_equal(p[name],p['passive'])
        assert m[name]['folds']==m['passive']['folds']
    assert check.check_all(p,m,data)['passes']


def test_no_hidden_features(small,small_fits):
    changed=deepcopy(small);changed['hidden_u1_minus_edit']=np.ones((4,4,4,6))*999
    changed['recovery']=np.ones((4,4,4,3,6))*999;p,m=model.fit_all(changed)
    for name in p:np.testing.assert_array_equal(p[name],small_fits[0][name])
    assert m==small_fits[1]


def test_group_permutation(small):
    perm=[2,0,3,1];x=model.features(small)['passive'];y=small['labels'];ids=small['block_ids']
    p,_=model.prior.prior.outer(x,y,ids,0);q,_=model.prior.prior.outer(x[:,:,perm],y[:,:,perm],ids,0)
    np.testing.assert_allclose(q,p[:,:,perm],atol=1e-12,rtol=0)


def test_constants(small):
    data=deepcopy(small)
    for k in ('start','endpoint','targeted'):data[k][:]=0
    data['labels'][:]=.125;p,m=model.fit_all(data)
    for name in p:
        np.testing.assert_array_equal(p[name],np.full((3,4,4,4),.125))
        assert all(min(v['scale'])==1 for fold in m[name]['folds'] for v in fold['models'])
    assert check.check_all(p,m,data)['passes']


def test_clipping(small):
    data=deepcopy(small);data['start'][0]*=1e9;p,m=model.fit_all(data)
    for name in p:assert np.max(abs(p[name]))==1
    assert check.check_all(p,m,data)['passes']


def test_rank_deficient(small):
    data=deepcopy(small);data['start'][...]=data['start'][...,:1];data['endpoint'][...]=0;data['targeted'][...]=0
    p,m=model.fit_all(data);assert check.check_all(p,m,data)['passes']


@pytest.mark.parametrize('kind',['nan','label','duplicate','groups','endpoint_shape','blocks'])
def test_invalid_panel(small,kind):
    data=deepcopy(small)
    if kind=='nan':data['start'][0,0,0,0]=np.nan
    elif kind=='label':data['labels'][0,0,0]=2
    elif kind=='duplicate':data['block_ids'][1]=data['block_ids'][0]
    elif kind=='groups':data['start']=data['start'][:,:,:3]
    elif kind=='endpoint_shape':data['endpoint']=data['endpoint'][...,:5]
    else:
        for k in data:data[k]=data[k][:3]
    with pytest.raises(ValueError):model.fit_all(data)


@pytest.mark.parametrize('kind',['prediction','alpha','coefficient','means','scale','training_blocks','metadata'])
def test_model_corruption(small,small_fits,kind):
    p,m=deepcopy(small_fits);fold=m['passive']['folds'][0]
    if kind=='prediction':p['passive'][0,0,0,0]+=.1
    elif kind=='alpha':fold['models'][0]['alpha']=.1
    elif kind=='coefficient':fold['models'][0]['coefficients'][0][0]+=.1
    elif kind=='means':fold['models'][0]['means'][0][0]+=.1
    elif kind=='scale':fold['models'][0]['scale'][0]+=.1
    elif kind=='training_blocks':fold['training_blocks'].append(0)
    else:m['passive']['inner_selection']=True
    with pytest.raises(AssertionError):check.check_all(p,m,small)


@pytest.mark.parametrize('kind',['model','cohort','group','contrast','influence','future','retained','metadata'])
def test_summary_corruption(full,kind):
    data,p,_,refs,nested,source,original=full;s=deepcopy(original);part=s['scores']['0.01']
    if kind=='model':part['models']['passive']['original']['mse']+=.1
    elif kind=='cohort':part['models']['passive']['cohorts']['d135']['mse']+=.1
    elif kind=='group':part['models']['sham_minus']['original']['group_mse'][0]+=.1
    elif kind=='contrast':part['comparisons'][0]['original']['mse_reduction']+=.1
    elif kind=='influence':part['comparisons'][0]['original']['leave_one_score_block_out'][0]+=.1
    elif kind=='future':part['models']['sham_plus']['individual_futures']['mse']+=.1
    elif kind=='retained':s['retained_d154']['scores']['0.01']['one_copy']['original']['mse']+=.1
    else:s['discarded_between_copy_differences']=False
    with pytest.raises(AssertionError):check.check_summary(s,p,refs,nested,source,data)


@pytest.mark.parametrize('kind',['signed','absolute','squared','retained'])
def test_error_corruption(full,kind):
    data,p,_,refs,nested,_,_=full;e=model.case_errors(p,refs,nested,data)
    key='one_copy__squared' if kind=='retained' else 'mean_passive__'+kind;e[key].flat[0]+=.1
    with pytest.raises(AssertionError):check.check_errors(e,p,refs,nested,data)


def test_reference_scores(full):
    data,p,_,refs,nested,source,s=full
    assert s['retained_d154']==source and check.check_summary(s,p,refs,nested,source,data)['passes']
    damaged=deepcopy(refs);damaged['one_copy'][0,0,0,0]+=.1
    with pytest.raises(AssertionError):check.check_summary(s,p,damaged,nested,source,data)
    source=deepcopy(source);source['scores']['0.01']['one_copy']['original']['mse']+=.1
    s=deepcopy(s);s['retained_d154']=source
    with pytest.raises(AssertionError):check.check_summary(s,p,refs,nested,source,data)


def test_mean_sham():
    data,refs,nested,source=model.fixture();data['labels'][:]=0;data['futures'][:]=0
    for v in refs.values():v[:]=0
    for v in nested.values():v[:]=0
    old={k:refs[k] for k in model.prior.prior.MODELS}
    d153=model.prior.prior.summarize(old,nested,data)
    source=model.prior.summarize({'one_copy':refs['one_copy']},old,d153,data)
    p={k:np.zeros((3,32,4,4)) for k in model.MODELS};p['sham_plus'][:]=1;p['sham_minus'][:]=-1
    s=model.summarize(p,refs,source,data);assert check.check_summary(s,p,refs,nested,source,data)['passes']
    for part in s['scores'].values():
        row=next(v for v in part['comparisons'] if v['candidate']=='mean:mean_sham_loss' and v['reference']=='one_copy')
        assert row['original']['mse_reduction']==-1


def test_future_identity(full):
    _,_,_,_,_,_,s=full
    for part in s['scores'].values():
        for c in part['comparisons']:
            np.testing.assert_allclose(c['individual_futures']['block_differences'],c['mean_target']['block_differences'],atol=1e-14,rtol=0)


def test_complete_panel():
    assert model.specs()==check.specs() and model.ALPHAS==check.ALPHAS and len(model.specs())==30
    assert len(set(model.specs()))==30 and model.MODELS==check.MODELS
    pairs={frozenset((c,r)) for c,r in model.specs() if c.startswith('mean:') and r.startswith('mean:') and 'mean_sham_loss' not in c+r}
    assert len(pairs)==10


def test_roundtrip(full,tmp_path):
    assert run.ROOT in tmp_path.resolve().parents;data,p,m,refs,nested,source,s=full
    run.io.write_npz(tmp_path/'predictions.npz',p,run.ROOT);run.io.write_json(tmp_path/'fits.json',m,run.ROOT)
    run.io.write_json(tmp_path/'summary.json',s,run.ROOT);loaded=run.io.load_npz(tmp_path/'predictions.npz')
    assert check.check_all(loaded,run.io.read_json(tmp_path/'fits.json'),data)['passes']
    assert check.check_summary(run.io.read_json(tmp_path/'summary.json'),loaded,refs,nested,source,data)['passes']


def test_no_reference_fits(monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('reference refit/selection/dynamics forbidden')
    original=model.prior.prior.group.fit
    def only_thirteen(x,*args,**kwargs):
        assert x.shape[-1]==13
        return original(x,*args,**kwargs)
    monkeypatch.setattr(model.prior.prior.group,'fit',only_thirteen)
    for module in (model.prior,model.prior.prior,model.prior.prior.group):monkeypatch.setattr(module,'fit_all',forbidden)
    monkeypatch.setattr(model.prior.prior.group,'nested',forbidden);monkeypatch.setattr(model.prior.prior.group,'outer_fold',forbidden)
    monkeypatch.setattr(check.prior,'check_all',forbidden);monkeypatch.setattr(run.previous,'saved_audit',forbidden)
    data,refs,nested,source=model.fixture();p,m=model.fit_all(data);s=model.summarize(p,refs,source,data)
    assert check.check_all(p,m,data)['passes'] and check.check_summary(s,p,refs,nested,source,data)['passes']
    for module in (model,check,run):
        code=inspect.getsource(module)
        for term in ('simulate(','.read_cycle(','.write_cycle(','.nested(','.outer_fold('):assert term not in code


def test_source_closure():
    files=set(run.source_files());assert len(files)>2075 and run.AUDIT in files
    assert all(run.WS/name in files for name in run.SCIENCE)
    assert run.previous.paths()[1]/'fits.json' in files and run.previous.paths()[1]/'case_errors.npz' in files


def test_source_identity():
    data,refs,nested,source=run.source_data()
    assert run.check_source_identity(data,refs,nested,{'retained_d154':source})['exact_fixed_observers']==7
    changed=deepcopy(refs);changed['passive'].flat[0]+=.1
    with pytest.raises(AssertionError):run.check_source_identity(data,changed,nested,{'retained_d154':source})


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
