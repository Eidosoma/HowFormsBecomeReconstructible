"""Synthetic D158 qualification; actual data are identity checks only before freeze."""
from copy import deepcopy
import inspect
import json
import os
import numpy as np
import pytest
from l20_extension1 import influence_models as model,influence_check as check,influence_run as run


@pytest.fixture(scope='module')
def small():return model.fixture(5)


@pytest.fixture(scope='module')
def fitted(small):return model.fit_all(small)


@pytest.fixture(scope='module')
def baseline(small):return model.fixture_baseline(small)


@pytest.fixture(scope='module')
def summary(small,fitted,baseline):
    return model.summarize(fitted[0],fitted[1],baseline[0],baseline[1],small)


def test_small_audit():
    data=model.fixture(5);b,br=model.fixture_baseline(data);p,raw,m=model.fit_all(data)
    s=model.summarize(p,raw,b,br,data)
    assert check.check_all(p,raw,m,data)['outer_fits']==720
    assert check.check_summary(s,p,raw,b,br,data)['deletions']==5
    assert check.check_errors(model.case_errors(p,b,data),p,b,data)['case_arrays']==252


@pytest.mark.parametrize('boundary',['deleted_labels','validation_labels','deleted_features'])
def test_exclusion_isolation(small,boundary):
    x=small['start'].copy();y=small['futures'].mean(axis=-1);ids=small['block_ids']
    p,r,m=model.fold(x,y,ids,1,0)
    if boundary=='deleted_labels':y[0]=.875
    elif boundary=='validation_labels':y[1]=.875
    else:x[0]+=100
    q,s,n=model.fold(x,y,ids,1,0)
    np.testing.assert_array_equal(p,q);np.testing.assert_array_equal(r,s);assert m==n
    assert ids[0] not in m['training_blocks'] and ids[1] not in m['training_blocks']


def test_heldout_features(small):
    x=small['start'].copy();y=small['futures'].mean(axis=-1);ids=small['block_ids']
    p,r,m=model.fold(x,y,ids,1,0);x[1]+=100;q,s,n=model.fold(x,y,ids,1,0)
    assert m==n and not np.array_equal(r,s)


@pytest.mark.parametrize('source,index,affected',[
    ('endpoint',0,('one_copy',)+tuple(prefix+k for prefix in ('separate:','mean:') for k in model.old.EDITED)),
    ('endpoint',1,('separate:passive','mean:passive')),('endpoint',2,('separate:shuffle','mean:shuffle')),
    ('targeted',0,('separate:attenuate','mean:attenuate')),('targeted',1,('separate:sham_plus','mean:sham_plus')),
    ('targeted',2,('separate:sham_minus','mean:sham_minus'))])
def test_feature_boundary(small,source,index,affected):
    data=deepcopy(small);data[source][...,index,:]+=99;a=model.old.features(small);b=model.old.features(data)
    independent=check.old.matrices(data)
    for k in model.OBSERVERS:
        np.testing.assert_array_equal(b[k],independent[k]);assert np.array_equal(a[k],b[k])==(k not in affected)


def test_original_not_training(small,fitted):
    data=deepcopy(small);data['labels'][:]=-.9;p,r,m=model.fit_all(data)
    for k in p:np.testing.assert_array_equal(p[k],fitted[0][k]);np.testing.assert_array_equal(r[k],fitted[1][k])
    assert m==fitted[2]


def test_repeat_permutation(small,fitted):
    data=deepcopy(small);data['futures']=data['futures'][...,[3,0,2,1]];p,r,m=model.fit_all(data)
    for k in p:np.testing.assert_allclose(p[k],fitted[0][k],atol=1e-12,rtol=0)


def test_founder_permutation(small,fitted):
    perm=[3,0,4,2,1];data={k:v[perm].copy() for k,v in small.items()};p,r,m=model.fit_all(data)
    assert check.check_all(p,r,m,data)['passes']
    for k in p:
        for d,original_d in enumerate(perm):
            order=[v for v in perm if v!=original_d]
            oldorder=[v for v in range(5) if v!=original_d]
            for j,b in enumerate(order):
                np.testing.assert_allclose(p[k][d,:,j],fitted[0][k][original_d,:,oldorder.index(b)],atol=1e-12,rtol=0)


def test_group_permutation(small):
    perm=[2,0,3,1];x=small['start'];y=small['futures'].mean(axis=-1);ids=small['block_ids']
    p,_,_=model.fold(x,y,ids,1,0);q,_,_=model.fold(x[:,:,perm],y[:,:,perm],ids,1,0)
    np.testing.assert_allclose(q,p[:,:,perm],atol=1e-12,rtol=0)


def test_clipping(small):
    x=small['start'].copy();x[1]*=1e4;p,r,_=model.fold(x,small['futures'].mean(axis=-1),small['block_ids'],1,0)
    assert np.max(abs(r))>1 and np.max(abs(p))==1
    np.testing.assert_array_equal(p,np.clip(r,-1,1))


def test_constants(small):
    data=deepcopy(small)
    for k in ('start','endpoint','targeted'):data[k][:]=0
    data['futures'][:]=.25;p,r,m=model.fit_all(data)
    for k in p:np.testing.assert_array_equal(p[k],np.full((5,3,4,4,4),.25))
    assert check.check_all(p,r,m,data)['passes']


def test_rank_deficient(small):
    data=deepcopy(small)
    for k in ('start','endpoint','targeted'):data[k][...]=data[k][...,:1]
    p,r,m=model.fit_all(data);assert check.check_all(p,r,m,data)['passes']


@pytest.mark.parametrize('kind',['nan','label','future','ids','shape','dtype','too_few'])
def test_invalid_input(small,kind):
    data=deepcopy(small)
    if kind=='nan':data['start'][0,0,0,0]=np.nan
    elif kind=='label':data['labels'][0,0,0]=2
    elif kind=='future':data['futures'][0,0,0,0]=-2
    elif kind=='ids':data['block_ids'][0]=data['block_ids'][1]
    elif kind=='shape':data['futures']=data['futures'][...,:3]
    elif kind=='dtype':data['labels']=data['labels'].astype(np.float32)
    else:data={k:v[:4] for k,v in data.items()}
    with pytest.raises(ValueError):model.fit_all(data)


@pytest.mark.parametrize('b,d',[(0,0),(-1,0),(5,0),(0,-1),(0,5)])
def test_invalid_exclusions(small,b,d):
    with pytest.raises(ValueError):model.fold(small['start'],small['futures'].mean(axis=-1),small['block_ids'],b,d)


@pytest.mark.parametrize('kind',['prediction','raw','coefficient','offset','scale','training_deleted','training_validation',
    'validation','deleted','remaining','target','alpha','header'])
def test_fit_corruption(small,fitted,kind):
    p,r,m=deepcopy(fitted);deletion=m['starting']['deletions'][0];fold=deletion['folds'][0]
    if kind=='prediction':p['starting'][0,0,0,0,0]+=.1
    elif kind=='raw':r['starting'][0,0,0,0,0]+=.1
    elif kind=='coefficient':fold['models'][0]['coefficients'][0][0]+=.1
    elif kind=='offset':fold['models'][0]['offsets'][0]+=.1
    elif kind=='scale':fold['models'][0]['scale'][0]+=.1
    elif kind=='training_deleted':fold['training_blocks'].append(90000)
    elif kind=='training_validation':fold['training_blocks'].append(90001)
    elif kind=='validation':fold['validation_block']=-1
    elif kind=='deleted':deletion['deleted_block']=90001
    elif kind=='remaining':deletion['remaining_blocks'][0]=90000
    elif kind=='target':m['starting']['target']='original'
    elif kind=='alpha':fold['models'][0]['alpha']=.01
    else:m['starting']['inner_selection']=True
    with pytest.raises(AssertionError):check.check_all(p,r,m,small)


@pytest.mark.parametrize('kind',['full','refit','score','training','group','repeat','decomposition','signs','deleted','forecast','metadata'])
def test_summary_corruption(small,fitted,baseline,summary,kind):
    p,r,_=fitted;b,br=baseline;s=deepcopy(summary);part=s['scores']['0.01'];d=part['deletions'][0]
    if kind=='full':part['full']['models']['starting']['original']['mse']+=.1
    elif kind=='refit':d['refitted']['comparisons'][0]['original']['mse_reduction']+=.1
    elif kind=='score':d['score_only']['models']['starting']['mean_target']['mse']+=.1
    elif kind=='training':d['training_effect'][0]['individual_futures']['mse_reduction']+=.1
    elif kind=='group':d['refitted']['models']['starting']['individual_futures']['group_mse'][0]+=.1
    elif kind=='repeat':d['refitted']['comparisons'][0]['by_repeat'][0]['mse_reduction']+=.1
    elif kind=='decomposition':part['decomposition'][0]['scopes']['original']['training_change'][0]+=.1
    elif kind=='signs':part['decomposition'][0]['scopes']['original']['positive_refitted']+=1
    elif kind=='deleted':d['deleted_block']=-1
    elif kind=='forecast':d['forecast_change']['starting']['rms_points']+=1
    else:s['excluded_founder_in_training']=True
    with pytest.raises(AssertionError):check.check_summary(s,p,r,b,br,small)


@pytest.mark.parametrize('prefix',['baseline__starting__original','refit__starting__futures','forecast_change__starting'])
def test_error_corruption(small,fitted,baseline,prefix):
    errors=model.case_errors(fitted[0],baseline[0],small);errors[prefix+'__squared'].flat[0]+=.1
    with pytest.raises(AssertionError):check.check_errors(errors,fitted[0],baseline[0],small)


def test_mean_losses(small):
    data=deepcopy(small);data['labels'][:]=0;data['futures'][:]=0
    b={k:np.zeros((3,5,4,4)) for k in model.OBSERVERS}
    for prefix in ('separate:','mean:'):b[prefix+'sham_plus'][:]=1;b[prefix+'sham_minus'][:]=-1
    loss=model.losses(b,data,0);other,_=check.loss_panel(b,data,0)
    for prefix in ('separate:','mean:'):
        for x,y in zip(loss[prefix+'mean_sham_loss'],other[prefix+'mean_sham_loss']):
            np.testing.assert_array_equal(x,np.ones_like(x));np.testing.assert_array_equal(x,y)


def test_influence_accounting(small):
    values=(1.,[-2.,2.,1.,-1.,0.],[3.,0.,1.,-2.,1.],small['block_ids'])
    a=model.influence(*values);check.old.same(a,check.influence(*values))
    assert a['training_change']==[5.,-2.,0.,-1.,1.]
    assert a['score_sign_reversals']==[90000,90003] and a['refit_sign_reversals']==[90003]


def test_score_only_bridge(summary):
    for part in summary['scores'].values():
        for j,full in enumerate(part['full']['comparisons']):
            for d,deleted in enumerate(part['deletions']):
                for scope in ('original','individual_futures','mean_target'):
                    a=full[scope]['leave_one_score_block_out'][d]
                    b=deleted['score_only']['comparisons'][j][scope]['mse_reduction']
                    assert abs(a-b)<1e-14


def test_source_bridge(small,baseline,summary):
    b,br=baseline;allp={k:np.repeat(v[None],6,axis=0) for k,v in b.items()}
    allraw={k:np.repeat(v[None],6,axis=0) for k,v in br.items()}
    reference=model.old.summarize(allp,allraw,small)
    assert check.source_bridge(summary,reference)['contrasts']==165
    reference['scores']['0.01']['models']['future_mean/starting']['original']['mse']+=.1
    with pytest.raises(AssertionError):check.source_bridge(summary,reference)


def test_complete_specs(small):
    assert model.PAIRS==check.PAIRS and len(model.PAIRS)==55 and len(set(model.PAIRS))==55
    m=model.metadata(16);assert m['new_fits']==8640 and m['new_predictions']==138240
    assert m['observer_comparison_records']==5445 and m['training_effect_records']==672
    data=model.fixture(16);_,_,fold=model.fold(data['start'],data['futures'].mean(axis=-1),data['block_ids'],1,0)
    assert len(fold['training_blocks'])==14


def test_roundtrip(small,fitted,baseline,summary,tmp_path):
    assert run.ROOT in tmp_path.resolve().parents;p,r,m=fitted;b,br=baseline
    for name,value in [('p',p),('raw',r),('baseline',b),('baseline_raw',br)]:
        run.io.write_npz(tmp_path/(name+'.npz'),value,run.ROOT)
    run.io.write_json(tmp_path/'fits.json',m,run.ROOT);run.io.write_json(tmp_path/'summary.json',summary,run.ROOT)
    q=run.io.load_npz(tmp_path/'p.npz');raw=run.io.load_npz(tmp_path/'raw.npz')
    baseline=run.io.load_npz(tmp_path/'baseline.npz');base_raw=run.io.load_npz(tmp_path/'baseline_raw.npz')
    assert check.check_all(q,raw,run.io.read_json(tmp_path/'fits.json'),small)['passes']
    assert check.check_summary(run.io.read_json(tmp_path/'summary.json'),q,raw,baseline,base_raw,small)['passes']


def test_source_identity():
    data,b,br=run.source_data();assert run.source_identity(data,b,br)['exact_arrays']==30
    b['starting'][0,0,0,0]+=.1
    with pytest.raises(AssertionError):run.source_identity(data,b,br)


def test_source_closure():
    files=set(run.source_files());assert len(files)>2160 and run.AUDIT in files
    assert all(run.WS/p in files for p in run.SCIENCE)
    assert run.previous.paths()[1]/'dataset.npz' in files


def test_no_dynamics_or_reference_fits(small,monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('old reference refit or dynamics forbidden')
    monkeypatch.setattr(run.previous,'saved_audit',forbidden)
    monkeypatch.setattr(model.old,'fit_all',forbidden);monkeypatch.setattr(model,'fixture_baseline',forbidden)
    p,r,m=model.fit_all(small);assert check.check_all(p,r,m,small)['passes']
    data,b,br=run.source_data();assert len(data['block_ids'])==16
    for module in (model,check,run):
        for term in ('simulate(','.read_cycle(','.write_cycle(','.nested(','.outer_fold('):assert term not in inspect.getsource(module)


def test_resource_guard(monkeypatch):
    run.resources(False);monkeypatch.setattr(os,'sched_getaffinity',lambda _:set(range(7)))
    with pytest.raises(RuntimeError):run.resources(False)


def test_thread_guard(monkeypatch):
    monkeypatch.setenv('OPENBLAS_NUM_THREADS','2')
    with pytest.raises(RuntimeError):run.resources(False)


def test_storage_guard(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(run.shutil,'disk_usage',lambda _:SimpleNamespace(free=0))
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
    code=inspect.getsource(run.detach)
    assert 'start_new_session=True' in code and 'stdin=subprocess.DEVNULL' in code
    assert 'select.select([reader],[],[],55)' in code
    assert '.poll(' not in code and '.wait(' not in code and 'sleep(' not in code
    assert 'execute(' not in inspect.getsource(run.benchmark) and 'detach(' not in inspect.getsource(run.execute)
    assert run.contract()['automatic_successor'] is False
