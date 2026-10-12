"""Synthetic D153 qualification; actual data only for source-identity checks."""
from copy import deepcopy
import inspect
import json
import os
import numpy as np
import pytest
from l20_extension1 import matched_models as model, matched_check as check, matched_run as run


@pytest.fixture(scope='module')
def small():return model.group.fixture(4)


@pytest.fixture(scope='module')
def small_fits(small):return model.fit_all(small)


@pytest.fixture(scope='module')
def full():
    data,p,m,old,records=model.fixture()
    return data,p,m,old,records,model.summarize(p,old,data)


def test_full_comparison():
    data,p,m,old,records=model.fixture();s=model.summarize(p,old,data)
    assert check.check_all(p,m,data)['outer_fits']==576
    assert check.bridge(p,m,old,records,data)['selected_outer_models']==192
    assert check.check_summary(s,p,old,data)['observer_contrasts']==72
    assert check.check_errors(model.case_errors(p,old,data),p,old,data)['case_arrays']==72


def test_outer_isolation(small):
    x=small['start'];y=small['labels'];ids=small['block_ids'];p,m=model.outer(x,y,ids,0)
    changed=y.copy();changed[0]=.999;q,n=model.outer(x,changed,ids,0)
    np.testing.assert_array_equal(p,q);assert m==n and 0 not in m['training_blocks']
    changed_x=x.copy();changed_x[0]+=100;_,n=model.outer(changed_x,y,ids,0);assert m==n


def test_future_not_training(small,small_fits):
    changed=deepcopy(small);changed['futures'][:]=999;p,m=model.fit_all(changed);a,b=small_fits
    for name in p:np.testing.assert_array_equal(p[name],a[name])
    assert m==b


@pytest.mark.parametrize('source,index,affected',[
    ('endpoint',0,('passive','shuffle','attenuate','sham_plus','sham_minus')),
    ('endpoint',1,('passive',)),('endpoint',2,('shuffle',)),
    ('targeted',0,('attenuate',)),('targeted',1,('sham_plus',)),('targeted',2,('sham_minus',))])
def test_two_copy_boundary(small,source,index,affected):
    changed=deepcopy(small);changed[source][...,index,:]+=999
    a=model.group.matrices(small);b=model.group.matrices(changed)
    for name in model.MODELS:
        assert a[name].shape[-1]==(7 if name=='starting' else 19)
        assert np.array_equal(a[name],b[name])==(name not in affected)
        np.testing.assert_array_equal(b[name],check.group.matrices(changed)[name])


def test_no_hidden_features(small,small_fits):
    changed=deepcopy(small);changed['recovery']=np.ones((4,4,4,3,6));changed['hidden_contrast']=np.ones((4,4,4,6))
    p,m=model.fit_all(changed)
    for k in p:np.testing.assert_array_equal(p[k],small_fits[0][k])
    assert m==small_fits[1]


def test_group_permutation(small):
    perm=[2,0,3,1];x=small['start'];y=small['labels'];ids=small['block_ids']
    p,_=model.outer(x,y,ids,0);q,_=model.outer(x[:,:,perm],y[:,:,perm],ids,0)
    np.testing.assert_allclose(q,p[:,:,perm],atol=1e-12,rtol=0)


def test_constants(small):
    data=deepcopy(small)
    for k in ('start','endpoint','targeted'):data[k][:]=0
    data['labels'][:]=.125;p,m=model.fit_all(data)
    for name in p:
        np.testing.assert_array_equal(p[name],np.full((3,4,4,4),.125))
        for fold in m[name]['folds']:
            assert [a['alpha'] for a in fold['models']]==list(model.ALPHAS)
            for a in fold['models']:assert min(a['scale'])==1
    assert check.check_all(p,m,data)['passes']


def test_clipping(small):
    x=small['start'].copy();x[0]*=1e9;p,_=model.outer(x,small['labels'],small['block_ids'],0)
    assert np.max(abs(p))==1 and np.isfinite(p).all()


def test_rank_deficient(small):
    data=deepcopy(small)
    for k in ('start','endpoint','targeted'):data[k][...]=data[k][...,:1]
    p,m=model.fit_all(data);assert check.check_all(p,m,data)['passes']


@pytest.mark.parametrize('kind',['nan','label','duplicate','groups','shape'])
def test_invalid_panel(small,kind):
    x=small['start'].copy();y=small['labels'].copy();ids=small['block_ids'].copy()
    if kind=='nan':x[0,0,0,0]=np.nan
    elif kind=='label':y[0,0,0]=2
    elif kind=='duplicate':ids[1]=ids[0]
    elif kind=='groups':x=x[:,:,:3];y=y[:,:,:3]
    else:x=x[:3];y=y[:3];ids=ids[:3]
    with pytest.raises(ValueError):model.outer(x,y,ids,0)


def test_bridge(full):
    data,p,m,old,records,_=full;assert check.bridge(p,m,old,records,data)['selected_outer_predictions']==3072


@pytest.mark.parametrize('kind',['prediction','alpha','index','coefficients','training_blocks','validation_block'])
def test_bridge_corruption(full,kind):
    data,p,m,guesses,fits,_=full;old=deepcopy(guesses);records=deepcopy(fits);fold=records['passive']['folds'][0]
    if kind=='prediction':old['passive'][0,0,0]+=.1
    elif kind=='alpha':fold['model']['alpha']=100
    elif kind=='index':fold['selected_index']=5
    elif kind=='coefficients':fold['model']['coefficients'][0][0]+=.1
    elif kind=='training_blocks':fold['training_blocks'].append(0)
    else:fold['validation_block']=999
    with pytest.raises((AssertionError,ValueError)):check.bridge(p,m,old,records,data)


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


@pytest.mark.parametrize('kind',['model','cohort','contrast','influence','future','change','metadata'])
def test_summary_corruption(full,kind):
    data,p,_,old,_,original=full;s=deepcopy(original);part=s['scores']['0.01']
    if kind=='model':part['models']['passive']['original']['mse']+=.1
    elif kind=='cohort':part['models']['starting']['cohorts']['d135']['mse']+=.1
    elif kind=='contrast':part['comparisons'][0]['original']['mse_reduction']+=.1
    elif kind=='influence':part['comparisons'][0]['original']['leave_one_score_block_out'][0]+=.1
    elif kind=='future':part['models']['sham_minus']['individual_futures']['mse']+=.1
    elif kind=='change':s['fixed_vs_nested'][0]['original']['mse_reduction']+=.1
    else:s['no_best_alpha_selected']=False
    with pytest.raises(AssertionError):check.check_summary(s,p,old,data)


@pytest.mark.parametrize('kind',['signed','absolute','squared'])
def test_error_corruption(full,kind):
    data,p,_,old,_,_=full;e=model.case_errors(p,old,data);e['0.01__passive__'+kind].flat[0]+=.1
    with pytest.raises(AssertionError):check.check_errors(e,p,old,data)


def test_mean_sham():
    guesses={k:np.zeros((32,4,4)) for k in model.MODELS};guesses['sham_plus'][:]=1;guesses['sham_minus'][:]=-1
    value=model.loss_panel(guesses,np.zeros((32,4,4)))
    np.testing.assert_array_equal(value['mean_sham_loss'],np.ones((32,4,4)))
    data=dict(labels=np.zeros((32,4,4)),futures=np.zeros((16,4,4,4)))
    a,_=model.score(guesses,data);b,_=check.score(guesses,data);check.same(a,b)
    row=next(v for v in a['comparisons'] if v['candidate']=='mean_sham_loss' and v['reference']=='passive')
    assert row['original']['mse_reduction']==-1


def test_future_identity(full):
    data,p,_,old,_,s=full
    for bundle in s['scores'].values():
        for c in bundle['comparisons']:
            np.testing.assert_allclose(c['individual_futures']['block_differences'],c['mean_target']['block_differences'],atol=1e-14,rtol=0)
    changed=deepcopy(data);changed['futures'][:]=0;new=model.summarize(p,old,changed)
    for label in s['scores']:
        for name in model.MODELS:assert new['scores'][label]['models'][name]['original']==s['scores'][label]['models'][name]['original']


def test_complete_panel():
    assert model.PAIRS==check.PAIRS and model.ALPHAS==check.ALPHAS and model.MODELS==check.MODELS
    pairs={frozenset(v) for v in model.PAIRS if 'mean_sham_loss' not in v}
    assert len(pairs)==15 and len(model.PAIRS)==18


def test_roundtrip(full,tmp_path):
    assert run.ROOT in tmp_path.resolve().parents;data,p,m,old,records,s=full
    run.io.write_npz(tmp_path/'predictions.npz',p,run.ROOT);run.io.write_json(tmp_path/'fits.json',m,run.ROOT)
    run.io.write_json(tmp_path/'summary.json',s,run.ROOT)
    loaded=run.io.load_npz(tmp_path/'predictions.npz');saved=run.io.read_json(tmp_path/'fits.json')
    assert check.check_all(loaded,saved,data)['passes'] and check.bridge(loaded,saved,old,records,data)['passes']
    assert check.check_summary(run.io.read_json(tmp_path/'summary.json'),loaded,old,data)['passes']


def test_no_dynamics_or_selection(small,monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('nested selection/dynamics forbidden')
    for name in ('nested','outer_fold'):monkeypatch.setattr(model.group,name,forbidden)
    monkeypatch.setattr(model.group.ridge,'nested',forbidden);model.fit_all(small)
    for module in (model,check,run):
        code=inspect.getsource(module)
        for term in ('simulate(','.read_cycle(','.write_cycle(','.nested(','.outer_fold('):assert term not in code


def test_source_closure():
    files=set(run.source_files());assert len(files)>2020 and run.AUDIT in files
    assert all(run.WS/name in files for name in run.SCIENCE)
    assert run.previous.source.paths()[1]/'fits.json' in files


def test_source_identity():
    data,p,m=run.source_data();assert run.check_source_identity(data,p,m)['exact_nested_models']==6


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
