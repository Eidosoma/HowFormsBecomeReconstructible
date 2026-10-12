"""D159 synthetic qualification; no actual component results before the freeze."""
from copy import deepcopy
import inspect
import os
from types import SimpleNamespace
import numpy as np
import pytest
from l20_extension1 import reading_parts as model,reading_parts_check as check,reading_parts_run as run


@pytest.fixture(scope='module')
def bundle():return model.fixture(5)


@pytest.fixture(scope='module')
def parts(bundle):return model.extract(*bundle)


@pytest.fixture(scope='module')
def arrays(bundle,parts):
    data,b,br,p,raw,bf,rf=bundle
    return model.accounting(parts,b,p,data)


@pytest.fixture(scope='module')
def summary(bundle,parts,arrays):
    data,b,br,p,raw,bf,rf=bundle
    return model.summarize(parts,arrays,b,br,p,raw,data)


def test_small_audit():
    bundle=model.fixture(5);data,b,br,p,raw,bf,rf=bundle
    parts=model.extract(*bundle);arrays=model.accounting(parts,b,p,data)
    s=model.summarize(parts,arrays,b,br,p,raw,data)
    assert check.check_parts(parts,*bundle)['saved_models_replayed']==900
    assert check.check_accounting(arrays,parts,b,p,data)['case_arrays']==248
    assert check.check_summary(s,parts,arrays,b,br,p,raw,data)['observer_comparison_records']==1815
    source=model.prior.summarize(p,raw,b,br,data)
    assert check.source_bridge(s,source)['training_effect_records']==210


def simple_record(dim):
    return dict(alpha=.001,means=np.zeros((4,dim)).tolist(),scale=np.ones(dim).tolist(),
        coefficients=np.zeros((4,dim)).tolist(),offsets=[.1,.2,.3,.4],model_class=model.prior.ridge.CLASS)


def test_mean_difference_coordinates():
    m=simple_record(19);m['coefficients'][0][7]=2;m['coefficients'][0][13]=6
    m['means']=np.full((4,19),.25).tolist();x=np.full((4,4,19),.25)
    x[...,7]=1.25;x[...,13]=3.25;z=model.model_parts(m,x)
    np.testing.assert_array_equal(z[...,2],np.full((4,4),16.))
    np.testing.assert_array_equal(z[...,3],np.full((4,4),4.))
    np.testing.assert_allclose(z.sum(-1),np.tile(20+np.asarray(m['offsets']),(4,1)),atol=1e-14)
    # Difference is (second-first)/2, not first-second or the undivided difference.
    x[...,7],x[...,13]=x[...,13].copy(),x[...,7].copy();z=model.model_parts(m,x)
    np.testing.assert_array_equal(z[...,3],np.full((4,4),-4.))


def test_group_coordinates():
    m=simple_record(7);m['scale']=[2]*7
    m['coefficients'][0][0]=2;m['coefficients'][1][0]=4
    x=np.ones((4,4,7));z=model.model_parts(m,x)
    np.testing.assert_array_equal(z[...,1],np.tile([0,0,2,2],(4,1)))


@pytest.mark.parametrize('dim',[7,13,19])
def test_structural_zeros(dim):
    m=simple_record(dim);x=np.ones((4,4,dim))
    m['coefficients'][0]=[1]*dim
    z=model.model_parts(m,x)
    if dim==7:np.testing.assert_array_equal(z[...,2:4],0)
    if dim==13:np.testing.assert_array_equal(z[...,3],0)
    np.testing.assert_array_equal(z[...,4],0)


def test_clipping(bundle,parts):
    assert any(np.any(v[...,4]!=0) for v in parts.values())
    check.check_parts(parts,*bundle)
    for key,z in parts.items():
        q=bundle[1 if key.startswith('baseline') else 3][key.split('__',1)[1]]
        np.testing.assert_allclose(z.sum(-1),q,atol=1e-13,rtol=0)


@pytest.mark.parametrize('source,index,affected',[
 ('endpoint',0,('one_copy',)+tuple(prefix+k for prefix in ('separate:','mean:') for k in model.prior.old.EDITED)),
 ('endpoint',1,('separate:passive','mean:passive')),('endpoint',2,('separate:shuffle','mean:shuffle')),
 ('targeted',0,('separate:attenuate','mean:attenuate')),('targeted',1,('separate:sham_plus','mean:sham_plus')),
 ('targeted',2,('separate:sham_minus','mean:sham_minus'))])
def test_feature_boundary(bundle,source,index,affected):
    data=deepcopy(bundle[0]);data[source][...,index,:]+=9
    a=model.prior.old.features(bundle[0]);b=model.prior.old.features(data);c=check.old.matrices(data)
    for k in model.OBSERVERS:
        np.testing.assert_array_equal(b[k],c[k]);assert np.array_equal(a[k],b[k])==(k not in affected)


def test_outcomes_not_parts(bundle,parts):
    values=list(deepcopy(bundle));values[0]['labels'][:]=-.9;values[0]['futures'][:]=.9
    changed=model.extract(*values)
    for k in parts:np.testing.assert_array_equal(parts[k],changed[k])


def test_repeat_permutation(bundle,parts,arrays):
    data,b,br,p,raw,bf,rf=deepcopy(bundle);order=[3,0,2,1]
    data['futures']=data['futures'][...,order]
    changed=model.accounting(parts,b,p,data)
    for k in arrays:
        np.testing.assert_allclose(changed[k],arrays[k][...,order,:] if k.endswith('futures') else arrays[k],atol=1e-13,rtol=0)


def test_synthetic_permutation():
    # A fresh fabricated bundle respects arbitrary founder identities/order.
    data,b,br,p,raw,bf,rf=model.fixture(5)
    mapped={90000:90103,90001:90100,90002:90104,90003:90101,90004:90102}
    data['block_ids']=np.array([mapped[int(k)] for k in data['block_ids']],dtype=np.int64)
    for name in model.OBSERVERS:
        for header in (bf[name],rf[name]):header['blocks']=data['block_ids'].tolist()
        for fold in bf[name]['folds']:
            fold['validation_block']=mapped[fold['validation_block']]
            fold['training_blocks']=[mapped[k] for k in fold['training_blocks']]
        for deletion in rf[name]['deletions']:
            deletion['deleted_block']=mapped[deletion['deleted_block']]
            deletion['remaining_blocks']=[mapped[k] for k in deletion['remaining_blocks']]
            for fold in deletion['folds']:
                fold['validation_block']=mapped[fold['validation_block']]
                fold['training_blocks']=[mapped[k] for k in fold['training_blocks']]
    z=model.extract(data,b,br,p,raw,bf,rf)
    assert check.check_parts(z,data,b,br,p,raw,bf,rf)['passes']


def test_mean_loss_not_ensemble():
    cp={k:np.zeros((1,4,4,5)) for k in model.OBSERVERS};q={k:np.zeros((1,4,4)) for k in model.OBSERVERS}
    for prefix in ('separate:','mean:'):
        for suffix,value in (('sham_plus',1.),('sham_minus',-1.)):
            cp[prefix+suffix][...,2]=value;q[prefix+suffix][:]=value
    y=np.zeros((1,4,4))
    z=model.gap('separate:mean_sham_loss','starting',cp,cp,q,q,y)
    np.testing.assert_array_equal(z.sum(-1),-np.ones_like(y))
    np.testing.assert_array_equal(z,check.independent_gap('separate:mean_sham_loss','starting',cp,cp,q,q,y,False))
    both=model.gap('separate:mean_sham_loss','mean:mean_sham_loss',cp,cp,q,q,y)
    np.testing.assert_array_equal(both,0)


def test_gap_symmetry(bundle,parts):
    data,b,br,p,raw,bf,rf=bundle;z={k:parts['baseline__'+k] for k in model.OBSERVERS}
    for c,r in model.PAIRS:
        a=model.gap(c,r,z,z,b,b,data['labels']);other=model.gap(r,c,z,z,b,b,data['labels'])
        np.testing.assert_allclose(a,-other,atol=1e-13,rtol=0)


@pytest.mark.parametrize('kind',['zero_scale','negative_scale','nan','wrong_beta','wrong_x','offset'])
def test_invalid_model(kind):
    m=simple_record(19);x=np.zeros((4,4,19))
    if kind=='zero_scale':m['scale'][0]=0
    elif kind=='negative_scale':m['scale'][0]=-1
    elif kind=='nan':m['means'][0][0]=np.nan
    elif kind=='wrong_beta':m['coefficients']=m['coefficients'][:2]
    elif kind=='wrong_x':x=x[...,:18]
    else:m['offsets']=[0,1]
    with pytest.raises(ValueError):model.model_parts(m,x)


@pytest.mark.parametrize('key,component',[('baseline__starting',0),('refit__mean:passive',2),
 ('baseline__separate:sham_minus',3),('refit__separate:passive',4)])
def test_parts_corruption(bundle,parts,key,component):
    bad={k:v.copy() for k,v in parts.items()};bad[key][...,component].flat[0]+=.1
    with pytest.raises(AssertionError):check.check_parts(bad,*bundle)


@pytest.mark.parametrize('kind',['coefficient','offset','scale','alpha','training_deleted','training_validation',
 'validation','deleted','remaining','target','header','baseline_training','baseline_target','prediction','raw'])
def test_fit_corruption(bundle,parts,kind):
    data,b,br,p,raw,bf,rf=deepcopy(bundle)
    fold=rf['starting']['deletions'][0]['folds'][0];m=fold['models'][0]
    if kind=='coefficient':m['coefficients'][0][0]+=.1
    elif kind=='offset':m['offsets'][0]+=.1
    elif kind=='scale':m['scale'][0]+=.1
    elif kind=='alpha':m['alpha']=.01
    elif kind=='training_deleted':fold['training_blocks'].append(90000)
    elif kind=='training_validation':fold['training_blocks'].append(90001)
    elif kind=='validation':fold['validation_block']=-1
    elif kind=='deleted':rf['starting']['deletions'][0]['deleted_block']=-1
    elif kind=='remaining':rf['starting']['deletions'][0]['remaining_blocks'][0]=-1
    elif kind=='target':rf['starting']['target']='original'
    elif kind=='header':rf['starting']['inner_selection']=True
    elif kind=='baseline_training':bf['starting']['folds'][0]['training_blocks'].append(90000)
    elif kind=='baseline_target':bf['starting']['training_targets'][5]='original'
    elif kind=='prediction':p['starting'].flat[0]+=.1
    else:br['starting'].flat[0]+=.1
    with pytest.raises(AssertionError):check.check_parts(parts,data,b,br,p,raw,bf,rf)


@pytest.mark.parametrize('key',['baseline__pair00__original','refit__pair03__futures','training__pair12__original'])
def test_case_corruption(bundle,parts,arrays,key):
    changed={k:v.copy() for k,v in arrays.items()};changed[key].flat[0]+=.1
    with pytest.raises(AssertionError):check.check_accounting(changed,parts,bundle[1],bundle[3],bundle[0])


@pytest.mark.parametrize('kind',['component','group','block','repeat','omit','refit','score','training','model','metadata'])
def test_summary_corruption(bundle,parts,arrays,summary,kind):
    s=deepcopy(summary);panel=s['scores']['0.01'];comparison=panel['full']['comparisons'][0]
    if kind=='component':comparison['original']['components'][1]+=.1
    elif kind=='group':comparison['original']['group_components'][0][1]+=.1
    elif kind=='block':comparison['individual_futures']['block_components'][0][2]+=.1
    elif kind=='repeat':comparison['by_repeat'][0]['components'][2]+=.1
    elif kind=='omit':comparison['leave_one_repeat_out'][0]['mse_reduction']+=.1
    elif kind=='refit':panel['deletions'][0]['refitted']['comparisons'][0]['original']['mse_reduction']+=.1
    elif kind=='score':panel['deletions'][0]['score_only']['comparisons'][0]['original']['mse_reduction']+=.1
    elif kind=='training':panel['deletions'][0]['training_effect'][0]['original']['mse_reduction']+=.1
    elif kind=='model':panel['full']['models']['starting']['original']['mse']+=.1
    else:s['causal_attribution']=True
    data,b,br,p,raw,bf,rf=bundle
    with pytest.raises(AssertionError):check.check_summary(s,parts,arrays,b,br,p,raw,data)


def test_source_bridge(bundle,summary):
    data,b,br,p,raw,bf,rf=bundle;source=model.prior.summarize(p,raw,b,br,data)
    assert check.source_bridge(summary,source)['observer_comparison_records']==1815
    source['scores']['0.01']['deletions'][0]['training_effect'][0]['individual_futures']['mse_reduction']+=.1
    with pytest.raises(AssertionError):check.source_bridge(summary,source)


def test_roundtrip(bundle,parts,arrays,summary,tmp_path):
    assert run.ROOT in tmp_path.resolve().parents
    run.io.write_npz(tmp_path/'parts.npz',parts,run.ROOT);run.io.write_npz(tmp_path/'accounting.npz',arrays,run.ROOT)
    run.io.write_json(tmp_path/'summary.json',summary,run.ROOT)
    data,b,br,p,raw,bf,rf=bundle
    source=model.prior.summarize(p,raw,b,br,data)
    assert run.verify_accounting(tmp_path,*bundle,source)['source_bridge']['passes']


def test_constants():
    for dim in (7,13,19):
        m=simple_record(dim);m['coefficients']=(np.ones((4,dim))*9).tolist()
        m['means']=np.full((4,dim),.5).tolist();x=np.full((4,4,dim),.5)
        z=model.model_parts(m,x);np.testing.assert_array_equal(z[...,1:],0)


def test_complete_specs():
    assert model.PAIRS==check.PAIRS and len(model.PAIRS)==len(set(model.PAIRS))==55
    assert model.metadata(16)==check.metadata(16)
    assert model.metadata(16)['saved_models_replayed']==9216
    assert model.metadata(16)['saved_forecasts_replayed']==147456
    assert run.contract()['new_fits']==0 and run.contract()['new_predictions']==0


def test_no_fitting_or_dynamics(monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('fitting/solver forbidden')
    monkeypatch.setattr(model.prior.ridge,'fit',forbidden)
    monkeypatch.setattr(model.prior,'fit_all',forbidden)
    monkeypatch.setattr(model.prior.old,'fit_all',forbidden)
    for name in ('solve','lstsq','svd','pinv','inv'):monkeypatch.setattr(np.linalg,name,forbidden)
    bundle=model.fixture(5);z=model.extract(*bundle)
    assert check.check_parts(z,*bundle)['new_fits']==0
    assert 'fit_all(' not in inspect.getsource(model) and 'svd_path(' not in inspect.getsource(check)


def test_source_closure():
    files=run.source_files();assert len(files)==2203 and len(files)==len(set(files))
    for path in run.SCIENCE:assert run.WS/path in files
    assert run.previous.previous.paths()[1]/'fits.json' in files
    assert run.source_identity()['passes']


def test_resource_guard(monkeypatch):
    monkeypatch.setattr(run.previous,'resources',lambda starting:None)
    monkeypatch.setattr(run.shutil,'disk_usage',lambda path:SimpleNamespace(free=run.RESERVE+run.ALLOWANCE-1))
    with pytest.raises(RuntimeError):run.resources()
    run.resources(False)


def test_detach_guard(monkeypatch):
    monkeypatch.delenv(run.ENV,raising=False)
    with pytest.raises(RuntimeError):run.detached_guard(True,'execute')
    run.detached_guard(False,'execute')
    monkeypatch.setenv(run.ENV,'1')
    with pytest.raises(AssertionError):run.detached_guard(False,'execute')


def test_startup_handshake(monkeypatch):
    reader,writer=os.pipe();monkeypatch.setenv(run.READY,str(writer))
    run.ready('execute');message=os.read(reader,4096);os.close(reader)
    assert b'STARTED' in message and run.READY not in os.environ
    text=inspect.getsource(run.detach)
    for required in ('start_new_session=True','stdin=subprocess.DEVNULL','pass_fds=(writer,)','[],[],55'):
        assert required in text


def test_no_automatic_successor():
    text=inspect.getsource(run)
    for forbidden in ('time.sleep(','.poll(','.wait(','.terminate(','.kill('):assert forbidden not in text
    assert run.contract()['automatic_polling'] is False and run.contract()['automatic_retry'] is False
    assert run.contract()['automatic_successor'] is False
