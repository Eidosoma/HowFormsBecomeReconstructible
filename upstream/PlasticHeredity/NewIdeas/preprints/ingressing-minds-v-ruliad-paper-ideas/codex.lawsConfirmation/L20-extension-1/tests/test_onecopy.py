"""D154 synthetic qualification and read-only source identity checks."""
from copy import deepcopy
import inspect
import json
import os
import numpy as np
import pytest
from l20_extension1 import onecopy_models as model, onecopy_check as check, onecopy_run as run


@pytest.fixture(scope='module')
def small():return model.prior.group.fixture(4)


@pytest.fixture(scope='module')
def small_fits(small):return model.fit_all(small)


@pytest.fixture(scope='module')
def full():
    data,refs,nested,source=model.fixture();p,m=model.fit_all(data)
    return data,p,m,refs,nested,source,model.summarize(p,refs,source,data)


def test_full_comparison():
    data,refs,nested,source=model.fixture();p,m=model.fit_all(data);s=model.summarize(p,refs,source,data)
    assert check.check_all(p,m,data)['outer_fits']==96
    assert check.check_summary(s,p,refs,nested,source,data)['retained_contrasts']==90
    assert check.check_errors(model.case_errors(p,refs,nested,data),p,refs,nested,data)['retained_case_arrays']==72


def test_outer_isolation(small):
    x=model.features(small);y=small['labels'];ids=small['block_ids'];p,m=model.prior.outer(x,y,ids,0)
    changed=y.copy();changed[0]=.999;q,n=model.prior.outer(x,changed,ids,0)
    np.testing.assert_array_equal(p,q);assert m==n and 0 not in m['training_blocks']
    altered=x.copy();altered[0]+=100;_,n=model.prior.outer(altered,y,ids,0);assert m==n


def test_future_not_training(small,small_fits):
    changed=deepcopy(small);changed['futures'][:]=999;p,m=model.fit_all(changed)
    np.testing.assert_array_equal(p['one_copy'],small_fits[0]['one_copy']);assert m==small_fits[1]


@pytest.mark.parametrize('source,index,affected',[
    ('start',None,True),('endpoint',0,True),('endpoint',1,False),('endpoint',2,False),
    ('targeted',0,False),('targeted',1,False),('targeted',2,False)])
def test_one_copy_boundary(small,small_fits,source,index,affected):
    changed=deepcopy(small)
    if index is None:changed[source][...]+=5
    else:changed[source][...,index,:]+=5
    a=model.features(small);b=model.features(changed)
    assert b.shape==(4,4,4,13) and np.array_equal(a,b)==(not affected)
    np.testing.assert_array_equal(b,check.features(changed))
    if not affected:
        p,m=model.fit_all(changed);np.testing.assert_array_equal(p['one_copy'],small_fits[0]['one_copy']);assert m==small_fits[1]


def test_no_hidden_features(small,small_fits):
    changed=deepcopy(small);changed['hidden_u1_minus_edit']=np.ones((4,4,4,6))*999
    changed['recovery']=np.ones((4,4,4,3,6))*999;changed['targeted'][:]=np.nan;changed['endpoint'][...,1:,:]=np.nan
    p,m=model.fit_all(changed);np.testing.assert_array_equal(p['one_copy'],small_fits[0]['one_copy']);assert m==small_fits[1]


def test_group_permutation(small):
    perm=[2,0,3,1];x=model.features(small);y=small['labels'];ids=small['block_ids']
    p,_=model.prior.outer(x,y,ids,0);q,_=model.prior.outer(x[:,:,perm],y[:,:,perm],ids,0)
    np.testing.assert_allclose(q,p[:,:,perm],atol=1e-12,rtol=0)


def test_constants(small):
    data=deepcopy(small);data['start'][:]=0;data['endpoint'][:]=0;data['labels'][:]=.125
    p,m=model.fit_all(data);np.testing.assert_array_equal(p['one_copy'],np.full((3,4,4,4),.125))
    assert all(min(v['scale'])==1 for fold in m['folds'] for v in fold['models'])
    assert check.check_all(p,m,data)['passes']


def test_clipping(small):
    data=deepcopy(small);data['start'][0]*=1e9;p,m=model.fit_all(data)
    assert np.max(abs(p['one_copy']))==1 and check.check_all(p,m,data)['passes']


def test_rank_deficient(small):
    data=deepcopy(small);data['start'][...]=data['start'][...,:1];data['endpoint'][...]=0
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
    p,m=deepcopy(small_fits);fold=m['folds'][0]
    if kind=='prediction':p['one_copy'][0,0,0,0]+=.1
    elif kind=='alpha':fold['models'][0]['alpha']=.1
    elif kind=='coefficient':fold['models'][0]['coefficients'][0][0]+=.1
    elif kind=='means':fold['models'][0]['means'][0][0]+=.1
    elif kind=='scale':fold['models'][0]['scale'][0]+=.1
    elif kind=='training_blocks':fold['training_blocks'].append(0)
    else:m['inner_selection']=True
    with pytest.raises(AssertionError):check.check_all(p,m,small)


@pytest.mark.parametrize('kind',['model','cohort','group','contrast','influence','future','retained','metadata'])
def test_summary_corruption(full,kind):
    data,p,_,refs,nested,source,original=full;s=deepcopy(original);part=s['scores']['0.01']
    if kind=='model':part['one_copy']['original']['mse']+=.1
    elif kind=='cohort':part['one_copy']['cohorts']['d135']['mse']+=.1
    elif kind=='group':part['one_copy']['original']['group_mse'][0]+=.1
    elif kind=='contrast':part['comparisons'][0]['original']['mse_reduction']+=.1
    elif kind=='influence':part['comparisons'][0]['original']['leave_one_score_block_out'][0]+=.1
    elif kind=='future':part['one_copy']['individual_futures']['mse']+=.1
    elif kind=='retained':s['retained_d153']['scores']['0.01']['models']['starting']['original']['mse']+=.1
    else:s['equal_observation_budget']=True
    with pytest.raises(AssertionError):check.check_summary(s,p,refs,nested,source,data)


@pytest.mark.parametrize('kind',['signed','absolute','squared','retained'])
def test_error_corruption(full,kind):
    data,p,_,refs,nested,_,_=full;e=model.case_errors(p,refs,nested,data)
    key='0.01__passive__squared' if kind=='retained' else 'one_copy__'+kind;e[key].flat[0]+=.1
    with pytest.raises(AssertionError):check.check_errors(e,p,refs,nested,data)


def test_reference_scores(full):
    data,p,_,refs,nested,source,s=full
    assert s['retained_d153']==source and check.check_summary(s,p,refs,nested,source,data)['passes']
    damaged=deepcopy(refs);damaged['passive'][0,0,0,0]+=.1
    with pytest.raises(AssertionError):check.check_summary(s,p,damaged,nested,source,data)
    source=deepcopy(source);source['scores']['nested']['models']['starting']['original']['mse']+=.1
    s=deepcopy(s);s['retained_d153']=source
    with pytest.raises(AssertionError):check.check_summary(s,p,refs,nested,source,data)


def test_mean_sham():
    data=model.prior.group.fixture();data['labels'][:]=0;data['futures'][:]=0
    refs={k:np.zeros((3,32,4,4)) for k in model.prior.MODELS};refs['sham_plus'][:]=1;refs['sham_minus'][:]=-1
    nested={k:v[0] for k,v in refs.items()};source=model.prior.summarize(refs,nested,data);p={'one_copy':np.zeros((3,32,4,4))}
    s=model.summarize(p,refs,source,data);assert check.check_summary(s,p,refs,nested,source,data)['passes']
    for part in s['scores'].values():assert part['comparisons'][-1]['original']['mse_reduction']==-1


def test_future_identity(full):
    data,p,_,refs,nested,_,s=full
    for part in s['scores'].values():
        for c in part['comparisons']:
            np.testing.assert_allclose(c['individual_futures']['block_differences'],c['mean_target']['block_differences'],atol=1e-14,rtol=0)
    changed=deepcopy(data);changed['futures'][:]=0;source=model.prior.summarize(refs,nested,changed)
    t=model.summarize(p,refs,source,changed)
    for label in s['scores']:
        assert s['scores'][label]['one_copy']['original']==t['scores'][label]['one_copy']['original']


def test_complete_panel():
    assert model.PAIRS==check.PAIRS and model.ALPHAS==check.ALPHAS and len(model.PAIRS)==7
    assert len(model.MODELS)==7 and set(model.MODELS)-set(model.prior.MODELS)=={'one_copy'}


def test_roundtrip(full,tmp_path):
    assert run.ROOT in tmp_path.resolve().parents;data,p,m,refs,nested,source,s=full
    run.io.write_npz(tmp_path/'predictions.npz',p,run.ROOT);run.io.write_json(tmp_path/'fits.json',m,run.ROOT)
    run.io.write_json(tmp_path/'summary.json',s,run.ROOT);loaded=run.io.load_npz(tmp_path/'predictions.npz')
    assert check.check_all(loaded,run.io.read_json(tmp_path/'fits.json'),data)['passes']
    assert check.check_summary(run.io.read_json(tmp_path/'summary.json'),loaded,refs,nested,source,data)['passes']


def test_no_reference_fits(monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('reference refit/selection/dynamics forbidden')
    original=model.prior.group.fit
    def only_one_copy(x,*args,**kwargs):
        assert x.shape[-1]==13
        return original(x,*args,**kwargs)
    monkeypatch.setattr(model.prior.group,'fit',only_one_copy)
    for module in (model.prior,model.prior.group):monkeypatch.setattr(module,'fit_all',forbidden)
    monkeypatch.setattr(model.prior.group,'nested',forbidden);monkeypatch.setattr(model.prior.group,'outer_fold',forbidden)
    monkeypatch.setattr(check.prior,'check_all',forbidden);monkeypatch.setattr(run.previous,'saved_audit',forbidden)
    data,refs,nested,source=model.fixture();p,m=model.fit_all(data);s=model.summarize(p,refs,source,data)
    assert check.check_all(p,m,data)['passes'] and check.check_summary(s,p,refs,nested,source,data)['passes']
    for module in (model,check,run):
        code=inspect.getsource(module)
        for term in ('simulate(','.read_cycle(','.write_cycle(','.nested(','.outer_fold('):assert term not in code


def test_source_closure():
    files=set(run.source_files());assert len(files)>2045 and run.AUDIT in files
    assert all(run.WS/name in files for name in run.SCIENCE)
    assert run.previous.paths()[1]/'fits.json' in files and run.previous.paths()[1]/'case_errors.npz' in files


def test_source_identity():
    data,refs,nested,source=run.source_data()
    assert run.check_source_identity(data,refs,nested,{'retained_d153':source})['exact_reference_summary']
    changed=deepcopy(refs);changed['passive'].flat[0]+=.1
    with pytest.raises(AssertionError):run.check_source_identity(data,changed,nested,{'retained_d153':source})


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
