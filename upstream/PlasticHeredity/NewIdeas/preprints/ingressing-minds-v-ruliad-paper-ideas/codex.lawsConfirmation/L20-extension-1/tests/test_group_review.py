"""Synthetic saved-fit qualification; no actual-case extraction or fitting."""
from copy import deepcopy
import inspect
import json
import os
import numpy as np
import pytest
from l20_extension1 import group_review as review,group_review_check as check,group_review_run as run


@pytest.fixture(scope='module')
def synthetic():
    data,p,m=review.fixture();panel=review.extract(data,p,m);summary=review.summarize(panel)
    return data,p,m,panel,summary


def test_full_review():
    data,p,m=review.fixture();panel=review.extract(data,p,m);summary=review.summarize(panel)
    assert check.check_panel(panel,data,p,m)['contrasts']==42
    assert check.check_summary(summary,panel)['models']==12


@pytest.mark.parametrize('arch',['shared','group_sensitive'])
@pytest.mark.parametrize('name',['starting','passive'])
def test_forward(synthetic,arch,name):
    data,p,m,_,_=synthetic;ki=review.MODELS.index(name);x=review.matrices(data)[ki][0];record=m[arch][name]['folds'][0]['model']
    a,parts=review.forward(record,x,arch);b,terms=check.forward(record,x,arch)
    np.testing.assert_allclose(a,b,atol=1e-12,rtol=0);np.testing.assert_allclose(parts,terms,atol=1e-12,rtol=0)
    np.testing.assert_allclose(parts.sum(axis=-1),p[arch][name][0],atol=1e-12,rtol=0)
    if name=='starting':np.testing.assert_array_equal(parts[...,2:4],np.zeros((4,4,2)))


def test_clipping(synthetic):
    data,_,m,_,_=synthetic;x=review.matrices(data)[1][0]*1e6;record=m['group_sensitive']['passive']['folds'][0]['model']
    p,parts=review.forward(record,x,'group_sensitive');q,terms=check.forward(record,x,'group_sensitive')
    assert np.max(abs(p))==1 and np.max(abs(parts[...,4]))>100
    np.testing.assert_array_equal(p,q);np.testing.assert_allclose(parts,terms,atol=1e-8,rtol=0)
    np.testing.assert_allclose(parts.sum(axis=-1),p,atol=1e-8,rtol=0)


@pytest.mark.parametrize('gap,expected',[(0,5),(5e-13,5),(2e-12,0)])
def test_ties(gap,expected):
    x=np.full(6,1+gap);x[0]=1
    assert review.choose(x)==check.index(x)==expected


def test_empty_partition():
    terms=np.empty((0,4,4,3));x=np.empty((0,4,4));ids=np.empty(0,np.int64)
    a=review.stats(terms,x,x,ids);b=check.basic(terms,x,x,ids)
    assert a==b and a['blocks']==0 and a['mse_reduction'] is None and a['cases']==0


def test_error_identity():
    rng=np.random.default_rng(1525001);c=rng.uniform(-1,1,(1,8,4,4));r=rng.uniform(-1,1,c.shape);y=rng.uniform(-1,1,c.shape[1:])
    t=review.decompose(c,r,y);np.testing.assert_allclose(t[...,0],-t[...,1]-t[...,2],atol=1e-14,rtol=0)
    np.testing.assert_allclose(t,check.direct_terms(c,r,y),atol=1e-14,rtol=0)


def test_mean_sham():
    c=np.array([np.ones((8,4,4)),np.ones((8,4,4))*-1]);r=np.zeros((1,8,4,4));y=np.zeros((8,4,4))
    t=review.decompose(c,r,y);np.testing.assert_array_equal(t[...,0],-np.ones_like(y))
    np.testing.assert_array_equal((c.mean(axis=0)-y)**2,np.zeros_like(y))


def test_future_identity(synthetic):
    _,_,_,panel,_=synthetic
    for i,s in enumerate(review.specs()):
        c,r=(check.model_predictions(panel,s,which) for which in ('candidate','reference'))
        t=review.decompose(c[:,16:],r[:,16:],panel['futures'].mean(axis=-1))
        np.testing.assert_allclose(t,panel['future_terms'][i].mean(axis=-2),atol=1e-14,rtol=0)


def test_score_deletion(synthetic):
    _,_,_,panel,_=synthetic
    for ai in range(2):
        for ki in range(6):
            for b in range(32):
                losses=panel['inner_losses'][ai,ki,b]
                for row in range(31):
                    assert panel['drop_selected'][ai,ki,b,row]==check.index(np.delete(losses,row,axis=0).mean(axis=0))


def test_complete_pairs():
    actual={frozenset(pair) for pair in review.PAIRS if 'mean_sham_loss' not in pair}
    expected={frozenset((a,b)) for i,a in enumerate(review.MODELS) for b in review.MODELS[i+1:]}
    assert actual==expected and len(review.specs())==42 and review.specs()==check.specs()


def test_leave_one_scores():
    gain=np.arange(32,dtype=float)/100;t=np.zeros((32,4,4,3));t[...,0]=gain[:,None,None]
    c=np.zeros((32,4,4));r=t[...,0];ids=np.arange(32,dtype=np.int64)
    result=review.describe(t,c,r,ids);check.same(result,check.detailed(t,c,r,ids))
    np.testing.assert_allclose(result['leave_one_score_block_out'],[(gain.sum()-g)/31 for g in gain],atol=1e-14,rtol=0)
    assert result['block_order_best_first']==list(range(31,-1,-1))


def test_counts_and_contributions():
    t=np.zeros((8,4,4,3));t[...,0]=1;t[...,2]=-1;x=np.ones((8,4,4));z=np.zeros_like(x);ids=np.arange(8,dtype=np.int64)
    a=review.stats(t,z,x,ids);check.same(a,check.basic(t,z,x,ids))
    assert a['cases']==128 and a['mse_reduction']==1 and a['relative_reduction_percent']==100
    assert a['group_reductions']==[1]*4 and a['group_contributions']==[.25]*4
    assert a['change_cost']==0 and a['error_correction']==1


def test_alpha_relations(synthetic):
    _,_,_,panel,summary=synthetic
    for s in summary['comparisons']:
        a=s['alpha_relation']
        if a is None:assert 'mean_sham_loss' in (s['candidate'],s['reference']) or s['candidate_arch']!=s['reference_arch']
        else:
            assert a['partitions']['same']['blocks']+a['partitions']['different']['blocks']==32
            np.testing.assert_allclose(sum(v['contribution_to_full_mse_reduction'] for v in a['partitions'].values()),
                s['original']['mse_reduction'],atol=1e-14,rtol=0)
            assert a['causal_isolation'] is a['new_outer_forecasts'] is False


def test_source_bridge(synthetic):
    data,p,m,_,summary=synthetic
    source=run.source.models.summarize(p['group_sensitive'],m['group_sensitive'],p['shared'],m['shared'],data)
    assert check.source_bridge(summary,source)['source_observer_contrasts']==20


@pytest.mark.parametrize('field',['predictions','parts','selected','inner_losses','inner_means','drop_selected',
    'selection_gaps','signed','absolute','squared','contrast_terms','future_terms','labels','futures','block_ids'])
def test_panel_corruption(synthetic,field):
    data,p,m,original,_=synthetic;panel=deepcopy(original)
    panel[field].flat[0]+=1 if panel[field].dtype==np.int64 else .1
    with pytest.raises(AssertionError):check.check_panel(panel,data,p,m)


@pytest.mark.parametrize('kind',['model','selection','partition','influence','cohort','decomposition','future','metadata'])
def test_summary_corruption(synthetic,kind):
    _,_,_,panel,original=synthetic;s=deepcopy(original)
    if kind=='model':s['models']['shared']['starting']['original']['mse']+=.1
    elif kind=='selection':s['selection']['group_sensitive']['sham_minus']['score_row_deletion_changed_counts'][0]+=1
    elif kind=='partition':s['comparisons'][0]['alpha_relation']['partitions']['same']['blocks']+=1
    elif kind=='influence':s['comparisons'][0]['original']['leave_one_score_block_out'][0]+=.1
    elif kind=='cohort':s['comparisons'][0]['cohorts']['d135']['mse_reduction']+=.1
    elif kind=='decomposition':s['comparisons'][0]['original']['change_cost']+=.1
    elif kind=='future':s['comparisons'][0]['secondary']['mse_reduction']+=.1
    else:s['new_fits']=1
    with pytest.raises(AssertionError):check.check_summary(s,panel)


def test_saved_metadata_corruption(synthetic):
    data,p,original,panel,_=synthetic;m=deepcopy(original)
    m['group_sensitive']['sham_minus']['folds'][0]['inner_validation_blocks'][0]=0
    with pytest.raises(AssertionError):check.check_panel(panel,data,p,m)


def test_roundtrip(synthetic,tmp_path):
    assert run.ROOT in tmp_path.resolve().parents;data,p,m,panel,s=synthetic
    run.io.write_npz(tmp_path/'panel.npz',panel,run.ROOT);run.io.write_json(tmp_path/'summary.json',s,run.ROOT)
    value=run.io.load_npz(tmp_path/'panel.npz');assert check.check_panel(value,data,p,m)['passes']
    assert check.check_summary(run.io.read_json(tmp_path/'summary.json'),value)['passes']


def test_no_fits_or_dynamics(monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('new fit/solver/dynamics forbidden')
    for name in ('solve','lstsq','svd','eigh','inv','pinv'):monkeypatch.setattr(np.linalg,name,forbidden)
    for module in (run.source.models,run.source.models.ridge):
        for name in ('fit','nested','fit_all'):monkeypatch.setattr(module,name,forbidden)
    monkeypatch.setattr(run.source,'saved_audit',forbidden)
    data,p,m=review.fixture();panel=review.extract(data,p,m);s=review.summarize(panel)
    assert check.check_panel(panel,data,p,m)['new_fits']==0 and check.check_summary(s,panel)['new_dynamics']==0
    for module in (review,check,run):
        code=inspect.getsource(module)
        for term in ('simulate(','.read_cycle(','.write_cycle(','.fit(','.nested(','.solve(','.svd('):assert term not in code


def test_source_closure():
    files=set(run.source_files());assert len(files)>1990 and run.AUDIT in files
    assert all(run.WS/name in files for name in run.SCIENCE)
    assert run.source.paths()[1]/'fits.json' in files and run.source.paths()[1]/'shared_fits.json' in files


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
