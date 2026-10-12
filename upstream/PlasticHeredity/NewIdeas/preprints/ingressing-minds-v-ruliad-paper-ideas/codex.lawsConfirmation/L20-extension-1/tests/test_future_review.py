"""D156 qualification on synthetic predictions; actual outcomes are not reviewed."""
from copy import deepcopy
import inspect
import json
import os
import numpy as np
import pytest
from l20_extension1 import future_review as review,future_review_check as check,future_review_run as run


@pytest.fixture(scope='module')
def full():
    data,p,refs,nested,old=review.fixture();panel=review.extract(data,p,refs,nested)
    return data,p,refs,nested,old,panel,review.summarize(panel)


def test_full_review():
    data,p,refs,nested,old=review.fixture();panel=review.extract(data,p,refs,nested);s=review.summarize(panel)
    assert check.check_panel(panel,data,p,refs,nested)['contrasts']==201
    assert check.check_summary(s,panel)['series']==42
    assert check.source_bridge(s,old)['source_contrasts']==201


def test_complete_specs():
    assert review.series()==check.names() and len(set(review.series()))==42
    assert review.specs()==check.specifications() and len(review.specs())==201
    assert len({(s['candidate'],s['reference']) for s in review.specs()})==201
    assert sum(s['origin']=='D155' for s in review.specs())==90
    assert all(len(review.components(s[k])) in (1,2) for s in review.specs() for k in ('candidate','reference'))


def test_known_reversal(full):
    data,p,refs,nested=deepcopy(full[:4]);data['labels'][:]=0;data['futures'][:]=.5
    p['passive'][:]=0;refs['passive'][:]=.5;panel=review.extract(data,p,refs,nested)
    j=next(i for i,s in enumerate(review.specs()) if s['candidate']=='0.001/mean:passive' and s['reference']=='0.001/separate:passive')
    np.testing.assert_array_equal(panel['contrast_original'][j],np.full((32,4,4),.25))
    np.testing.assert_array_equal(panel['contrast_mean'][j],np.full((16,4,4),-.25))
    np.testing.assert_array_equal(panel['contrast_shift'][j],np.full((16,4,4),-.5))
    assert check.check_panel(panel,data,p,refs,nested)['passes']


def test_future_identity(full):
    panel=full[-2]
    np.testing.assert_allclose(panel['future_squared'].mean(axis=-1),panel['mean_squared']+panel['future_variance'],atol=1e-14,rtol=0)
    np.testing.assert_allclose(panel['contrast_futures'].mean(axis=-1),panel['contrast_mean'],atol=1e-14,rtol=0)
    np.testing.assert_allclose(panel['contrast_mean']-panel['contrast_original'][:,16:],panel['contrast_shift'],atol=1e-14,rtol=0)


def test_zero_variance(full):
    data,p,refs,nested=deepcopy(full[:4]);data['futures'][...]=data['labels'][16:,...,None]
    panel=review.extract(data,p,refs,nested)
    for k in ('future_variance','target_shift','contrast_shift'):assert not np.any(panel[k])
    np.testing.assert_array_equal(panel['contrast_mean'],panel['contrast_original'][:,16:])
    assert check.check_panel(panel,data,p,refs,nested)['passes']


def test_zero_errors(full):
    data,p,refs,nested=deepcopy(full[:4]);data['labels'][:]=0;data['futures'][:]=0
    for bundle in (p,refs,nested):
        for value in bundle.values():value[:]=0
    panel=review.extract(data,p,refs,nested);s=review.summarize(panel)
    assert check.check_summary(s,panel)['passes']
    for row in s['comparisons']:
        assert row['individual_futures']['relative_reduction_percent'] is None
        assert row['individual_futures']['zero_cases']==256
        assert row['individual_futures']['zero_blocks']==16
    for row in s['models'].values():assert row['within_variance_share_of_mse'] is None


def test_mean_sham(full):
    data,p,refs,nested=deepcopy(full[:4]);data['labels'][:]=0;data['futures'][:]=0
    p['sham_plus'][:]=1;p['sham_minus'][:]=-1;p['passive'][:]=0
    panel=review.extract(data,p,refs,nested)
    j=next(i for i,s in enumerate(review.specs()) if s['candidate']=='0.001/mean:mean_sham_loss' and s['reference']=='0.001/mean:passive')
    np.testing.assert_array_equal(panel['contrast_original'][j],-np.ones((32,4,4)))
    assert not np.any(panel['contrast_prediction_delta'][j])
    assert not np.any((p['sham_plus']+p['sham_minus'])/2)
    assert check.check_panel(panel,data,p,refs,nested)['passes']


def test_repeat_permutation(full):
    data,p,refs,nested=deepcopy(full[:4]);perm=[3,1,0,2];data['futures']=data['futures'][...,perm]
    panel=review.extract(data,p,refs,nested);original=full[-2]
    np.testing.assert_allclose(panel['future_mean'],original['future_mean'],atol=1e-14,rtol=0)
    np.testing.assert_allclose(panel['contrast_shift'],original['contrast_shift'],atol=1e-14,rtol=0)
    np.testing.assert_array_equal(panel['contrast_futures'],original['contrast_futures'][...,perm])
    assert check.check_panel(panel,data,p,refs,nested)['passes']


def test_group_axis():
    value=np.broadcast_to(np.array([1.,2.,3.,4.]),(16,4,4)).copy();result=review.contributions(value,review.IDS[16:])
    check.same(result,check.contributions(value,review.IDS[16:]))
    assert result['group_means']==[1.,2.,3.,4.] and result['group_contributions']==[.25,.5,.75,1.]
    assert result['mean']==2.5 and sum(result['block_contributions'])==2.5


def test_score_omissions():
    values=np.broadcast_to(np.arange(16,dtype=float)[:,None,None],(16,4,4)).copy()
    row=review.contributions(values,review.IDS[16:]);check.same(row,check.contributions(values,review.IDS[16:]))
    for j,value in enumerate(row['leave_one_score_block_out']):assert value==np.delete(values,j,axis=0).mean()
    assert row['block_order_descending']==review.IDS[16:][::-1].tolist()


def test_repeat_omissions(full):
    panel,s=full[-2:];j=3;row=s['comparisons'][j]
    for k in range(4):
        expected=np.delete(panel['contrast_futures'][j],k,axis=-1).mean()
        np.testing.assert_allclose(row['leave_one_repeat_out'][k]['mean'],expected,atol=1e-14,rtol=0)
    error=panel['future_signed'][0];score=s['models'][review.series()[0]]
    for k in range(4):
        future=np.delete(error,k,axis=-1)
        np.testing.assert_allclose(score['leave_one_repeat_out'][k]['mse'],np.mean(future**2),atol=1e-14,rtol=0)
        assert score['leave_one_repeat_out'][k]['mse']!=np.mean(future.mean(axis=-1)**2)


def test_source_bridge(full):assert check.source_bridge(full[-1],full[4])['exact_source_series']==42


@pytest.mark.parametrize('field',['block_ids','labels','futures','predictions','signed','absolute','squared',
    'future_signed','future_absolute','future_squared','mean_signed','mean_squared','future_mean','future_variance',
    'target_shift','contrast_original','contrast_futures','contrast_mean','contrast_prediction_delta','contrast_shift'])
def test_panel_corruption(full,field):
    data,p,refs,nested=full[:4];panel=deepcopy(full[-2]);panel[field].flat[0]+=.1 if panel[field].dtype==np.float64 else 1
    with pytest.raises(AssertionError):check.check_panel(panel,data,p,refs,nested)


@pytest.mark.parametrize('kind',['model','bias','repeat','omission','group','block','shift','mean','target','metadata','ensemble'])
def test_summary_corruption(full,kind):
    panel,original=full[-2:];s=deepcopy(original);model=s['models']['0.001/mean:passive'];pair=s['comparisons'][0]
    if kind=='model':model['full_original']['mse']+=.1
    elif kind=='bias':model['mean_future']['bias_points']+=.1
    elif kind=='repeat':pair['by_repeat'][0]['mean']+=.1
    elif kind=='omission':pair['leave_one_repeat_out'][0]['mean']+=.1
    elif kind=='group':pair['shift']['group_contributions'][2]+=.1
    elif kind=='block':pair['individual_futures']['leave_one_score_block_out'][0]+=.1
    elif kind=='shift':pair['shift']['mean']+=.1
    elif kind=='mean':model['mean_future_error_mse']+=.1
    elif kind=='target':s['targets']['within_future_variance']['mean']+=.1
    elif kind=='ensemble':s['mean_sham_is_loss_not_ensemble']=False
    else:s['new_fits']=1
    with pytest.raises(AssertionError):check.check_summary(s,panel)


@pytest.mark.parametrize('kind',['nan','labels','future','predictions','missing','shape','ids','dtype'])
def test_invalid_input(full,kind):
    data,p,refs,nested=deepcopy(full[:4])
    if kind=='nan':p['passive'][0,0,0,0]=np.nan
    elif kind=='labels':data['labels'][0,0,0]=2
    elif kind=='future':data['futures'][0,0,0,0]=-2
    elif kind=='predictions':p['passive'][0,0,0,0]=1.001
    elif kind=='missing':del nested['starting']
    elif kind=='shape':data['futures']=data['futures'][...,:3]
    elif kind=='ids':data['block_ids'][0]=0
    else:data['labels']=data['labels'].astype(np.float32)
    with pytest.raises(AssertionError):review.extract(data,p,refs,nested)


def test_roundtrip(full,tmp_path):
    assert run.ROOT in tmp_path.resolve().parents
    run.io.write_npz(tmp_path/'panel.npz',full[-2],run.ROOT);run.io.write_json(tmp_path/'summary.json',full[-1],run.ROOT)
    data,p,refs,nested=full[:4];panel=run.io.load_npz(tmp_path/'panel.npz')
    assert check.check_panel(panel,data,p,refs,nested)['passes']
    assert check.check_summary(run.io.read_json(tmp_path/'summary.json'),panel)['passes']


def test_no_fits_or_dynamics(monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('new fitting or dynamics forbidden')
    for name in ('solve','lstsq','svd','eigh','inv','pinv'):monkeypatch.setattr(np.linalg,name,forbidden)
    for module in (run.source.models,run.source.models.prior,run.source.models.prior.prior):
        monkeypatch.setattr(module,'fit_all',forbidden)
    monkeypatch.setattr(run.source.models.prior.prior.group,'fit',forbidden)
    monkeypatch.setattr(run.source,'saved_audit',forbidden)
    data,p,refs,nested,old=review.fixture();panel=review.extract(data,p,refs,nested);s=review.summarize(panel)
    assert check.check_panel(panel,data,p,refs,nested)['new_fits']==0
    assert check.check_summary(s,panel)['new_dynamics']==0 and check.source_bridge(s,old)['passes']
    for module in (review,check,run):
        for term in ('simulate(','.read_cycle(','.write_cycle(','.fit(','.nested(','.solve(','.svd('):
            assert term not in inspect.getsource(module)


def test_source_closure():
    files=set(run.source_files());assert len(files)>2100 and run.AUDIT in files
    assert all(run.WS/name in files for name in run.SCIENCE)
    assert run.source.paths()[1]/'reference_nested_predictions.npz' in files
    assert run.source.paths()[1]/'fits.json' in files


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
