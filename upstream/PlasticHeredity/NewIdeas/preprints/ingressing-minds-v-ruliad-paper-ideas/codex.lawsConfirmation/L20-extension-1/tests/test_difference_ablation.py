"""Synthetic qualification of the D160 constrained predictor, prior to study refits."""
from copy import deepcopy
import inspect
import os
from types import SimpleNamespace
import numpy as np
import pytest
from l20_extension1 import difference_ablation as model,difference_check as check,difference_run as run


@pytest.fixture(scope='module')
def sources():return model.fixture(5)


@pytest.fixture(scope='module')
def fitted(sources):return model.fit_all(*sources)


@pytest.fixture(scope='module')
def summary(sources,fitted):
    data,b,br,p,raw,bf,rf=sources;nb,nbr,npred,nraw,m=fitted
    return model.summarize(b,br,p,raw,nb,nbr,npred,nraw,data)


def test_small_audit():
    source=model.fixture(5);data,b,br,p,raw,bf,rf=source
    fit=model.fit_all(*source);nb,nbr,npred,nraw,m=fit
    s=model.summarize(b,br,p,raw,nb,nbr,npred,nraw,data)
    assert check.check_all(*fit,*source)['new_fits']==375
    assert check.check_summary(s,nb,nbr,npred,nraw,data,b,br,p,raw)['observer_comparison_records']==1089
    assert check.check_errors(model.case_errors(nb,npred,b,p,data),nb,npred,b,p,data)['case_arrays']==120
    old=model.prior.summarize(p,raw,b,br,data)
    assert check.source_bridge(s,old,data,b,br,p,raw)['absolute_source_score_records']==396


@pytest.mark.parametrize('scale',[np.ones(19),np.geomspace(.01,100,19),np.arange(1,20,dtype=float)])
def test_embedding(scale):
    t=model.embedding(scale);np.testing.assert_allclose(t.T@t,np.eye(13),atol=1e-14,rtol=0)
    eta=np.arange(52,dtype=float).reshape(4,13)/50;beta=eta@t.T
    np.testing.assert_allclose(beta[:,7:13]/scale[7:13],beta[:,13:]/scale[13:],atol=1e-14,rtol=0)
    np.testing.assert_allclose(np.sum(beta*beta),np.sum(eta*eta),atol=1e-13,rtol=0)


def test_full_metric():
    rng=np.random.default_rng(160);s=np.arange(1,20,dtype=float)
    beta=rng.normal(size=(4,19));mu=rng.normal(size=(4,19));x=rng.normal(size=(16,19));g=np.tile(np.arange(4,dtype=np.int64),4)
    record=dict(means=mu.tolist(),scale=s.tolist(),coefficients=beta.tolist())
    md,gamma,restored=model.coordinates(x,g,record)
    np.testing.assert_allclose(restored,beta,atol=1e-14,rtol=0)
    np.testing.assert_allclose(model.ridge.design(md,g)@gamma.ravel(),
        model.ridge.design((x-mu[g])/s,g)@beta.ravel(),atol=1e-13,rtol=0)
    m,d=gamma[:,7:13],gamma[:,13:]
    diag=np.sum((gamma[:,:7]*s[:7])**2)+np.sum(.25*(s[7:13]**2+s[13:]**2)*(m*m+d*d))
    cross=np.sum(.5*(s[13:]**2-s[7:13]**2)*m*d)
    assert abs(cross)>.1
    np.testing.assert_allclose(diag+cross,np.sum(beta**2),atol=1e-13,rtol=0)


def training_rows(sources):
    data=sources[0];x=model.prior.old.features(data)['separate:passive']
    return x.reshape(-1,19),data['futures'].mean(-1).ravel(),np.tile(np.arange(4,dtype=np.int64),len(x)*4)


def test_raw_not_standardized_tying(sources):
    x,y,g=training_rows(sources);x=x.copy();x[:,7:13]*=.1;x[:,13:]*=5
    m=model.fit(x,y,g,.01);s=np.asarray(m['scale']);beta=np.asarray(m['coefficients'])
    assert np.max(abs(beta[:,7:13]-beta[:,13:]))>1e-3
    np.testing.assert_allclose(beta[:,7:13]/s[7:13],beta[:,13:]/s[13:],atol=1e-12,rtol=0)


def fold_values(sources,b=1,d=0):
    data,base,br,p,raw,bf,rf=sources;name='separate:passive'
    x=model.prior.old.features(data)[name];y=data['futures'].mean(-1);ids=data['block_ids']
    order=[i for i in range(len(ids)) if i!=d];j=order.index(b)
    return x,y,ids,rf[name]['deletions'][d]['folds'][j]['models'],raw[name][d,:,j]


@pytest.mark.parametrize('kind',['deleted_labels','validation_labels','deleted_features'])
def test_exclusion_isolation(sources,kind):
    x,y,ids,records,raw=fold_values(sources);old=model.fold(x,y,ids,1,records,raw,0)
    x=x.copy();y=y.copy()
    if kind=='deleted_labels':y[0]=.8
    elif kind=='validation_labels':y[1]=-.8
    else:x[0]+=99
    new=model.fold(x,y,ids,1,records,raw,0)
    np.testing.assert_array_equal(old[0],new[0]);np.testing.assert_array_equal(old[1],new[1]);assert old[2]==new[2]


def test_heldout_features(sources):
    x,y,ids,records,raw=fold_values(sources);original=model.fold(x,y,ids,1,records,raw,0)
    x=x.copy();x[1]+=9;g=np.tile(np.arange(4,dtype=np.int64),4)
    rr=np.stack([model.prior.old.raw_predict(m,x[1].reshape(16,19),g).reshape(4,4) for m in records])
    changed=model.fold(x,y,ids,1,records,rr,0)
    assert original[2]['models']==changed[2]['models']
    assert not np.array_equal(original[1],changed[1])


def test_original_not_training(sources,fitted):
    changed=deepcopy(sources);changed[0]['labels'][:]=.9;new=model.fit_all(*changed)
    for a,b in zip(new[:4],fitted[:4]):
        for k in a:np.testing.assert_array_equal(a[k],b[k])
    assert new[4]==fitted[4]


@pytest.mark.parametrize('source,index,affected',[
 ('endpoint',0,model.EDITED),('endpoint',1,('passive',)),('endpoint',2,('shuffle',)),
 ('targeted',0,('attenuate',)),('targeted',1,('sham_plus',)),('targeted',2,('sham_minus',))])
def test_feature_boundary(sources,source,index,affected):
    data=deepcopy(sources[0]);data[source][...,index,:]+=9
    a=model.prior.old.features(sources[0]);b=model.prior.old.features(data);c=check.old.matrices(data)
    for k in model.EDITED:
        name='separate:'+k
        np.testing.assert_array_equal(b[name],c[name]);assert np.array_equal(a[name],b[name])==(k not in affected)


def test_repeat_permutation(sources,fitted):
    altered=deepcopy(sources);altered[0]['futures']=altered[0]['futures'][...,[3,0,2,1]]
    result=model.fit_all(*altered)
    for a,b in zip(result[:4],fitted[:4]):
        for k in a:np.testing.assert_allclose(a[k],b[k],atol=1e-12,rtol=0)


def test_founder_permutation(sources):
    x,y,ids,records,raw=fold_values(sources);p,rr,m=model.fold(x,y,ids,1,records,raw,0)
    order=[3,0,4,2,1];q,ss,n=model.fold(x[order],y[order],ids[order],4,records,raw,1)
    np.testing.assert_allclose(p,q,atol=1e-12,rtol=0)
    assert set(m['training_blocks'])==set(n['training_blocks'])
    for a,b in zip(m['models'],n['models']):check.old.same(a,b)


def test_group_permutation(sources):
    x,y,g=training_rows(sources);perm=[2,0,3,1]
    xx=x.reshape(5,4,4,19)[:,:,perm].reshape(-1,19);yy=y.reshape(5,4,4)[:,:,perm].ravel()
    m=model.fit(x,y,g,.01);n=model.fit(xx,yy,g,.01)
    p=model.prior.old.raw_predict(m,x,g).reshape(5,4,4)
    q=model.prior.old.raw_predict(n,xx,g).reshape(5,4,4)
    np.testing.assert_allclose(q,p[:,:,perm],atol=1e-12,rtol=0)


def test_equal_mean_invariance(sources):
    x,y,g=training_rows(sources);m=model.fit(x,y,g,.001);delta=np.arange(6)/5
    altered=x.copy();altered[:,7:13]+=delta;altered[:,13:]-=delta
    np.testing.assert_allclose(model.prior.old.raw_predict(m,x,g),
        model.prior.old.raw_predict(m,altered,g),atol=1e-12,rtol=0)
    swapped=x.copy();swapped[:,7:13]=x[:,13:];swapped[:,13:]=x[:,7:13]
    n=model.fit(swapped,y,g,.001)
    np.testing.assert_allclose(model.prior.old.raw_predict(m,x,g),
        model.prior.old.raw_predict(n,swapped,g),atol=1e-12,rtol=0)


def test_clipping(sources):
    x,y,g=training_rows(sources);m=model.fit(x,y,g,.001)
    raw=model.prior.old.raw_predict(m,x*1e4,g);assert np.max(abs(raw))>1
    p,r,models=check.svd_path(x,y,g,x*1e4,g)
    np.testing.assert_allclose(r[0],raw,atol=2e-9,rtol=0)
    np.testing.assert_array_equal(p,np.clip(r,-1,1))


@pytest.mark.parametrize('kind',['constants','rank_deficient'])
def test_constants(sources,kind):
    x,y,g=training_rows(sources);x=x.copy();y=y.copy()
    if kind=='constants':x[:]=.5;y[:]=.25
    else:x[:]=x[:,:1]
    m=model.fit(x,y,g,.01);p,raw,expected=check.svd_path(x,y,g,x,g)
    check.old.same(m,expected[1])
    if kind=='constants':np.testing.assert_array_equal(raw[1],.25)


def test_rank_deficient(sources):
    x,y,g=training_rows(sources);x=x.copy();x[:,7:13]=x[:,13:]
    m=model.fit(x,y,g,.1);source=model.ridge.fit(x,y,g,.1)
    rr=model.prior.old.raw_predict(source,x,g);geo=model.geometry(source,m,x,y,g,x,g,rr)
    assert abs(geo['objective_increase'])<1e-12


@pytest.mark.parametrize('kind',['negative_scale','nan_scale','shape','alpha','nan_features','outcome'])
def test_invalid_input(sources,kind):
    x,y,g=training_rows(sources);x=x.copy();y=y.copy();s=np.ones(19)
    if kind=='negative_scale':s[0]=-1
    elif kind=='nan_scale':s[0]=np.nan
    elif kind=='shape':s=s[:18]
    if kind in ('negative_scale','nan_scale','shape'):
        with pytest.raises(ValueError):model.embedding(s)
        return
    if kind=='nan_features':x[0,0]=np.nan
    elif kind=='outcome':y[0]=2
    with pytest.raises(ValueError):model.fit(x,y,g,1. if kind=='alpha' else .01)


@pytest.mark.parametrize('kind',['prediction','raw','coefficient','reduced','offset','scale','alpha','training_deleted',
 'training_validation','validation','deleted','remaining','target','header','geometry','full_training'])
def test_fit_corruption(sources,fitted,kind):
    nb,nbr,p,raw,m=deepcopy(fitted);fold=m['tied:passive']['deletions'][0]['folds'][0];rec=fold['models'][0]
    if kind=='prediction':nb['tied:passive'].flat[0]+=.1
    elif kind=='raw':raw['tied:passive'].flat[0]+=.1
    elif kind=='coefficient':rec['coefficients'][0][7]+=.1
    elif kind=='reduced':rec['reduced_coefficients'][0][7]+=.1
    elif kind=='offset':rec['offsets'][0]+=.1
    elif kind=='scale':rec['scale'][0]+=.1
    elif kind=='alpha':rec['alpha']=.01
    elif kind=='training_deleted':fold['training_blocks'].append(90000)
    elif kind=='training_validation':fold['training_blocks'].append(90001)
    elif kind=='validation':fold['validation_block']=-1
    elif kind=='deleted':m['tied:passive']['deletions'][0]['deleted_block']=-1
    elif kind=='remaining':m['tied:passive']['deletions'][0]['remaining_blocks'][0]=-1
    elif kind=='target':m['tied:passive']['target']='original'
    elif kind=='header':m['tied:passive']['inner_selection']=True
    elif kind=='geometry':fold['geometry'][0]['full_objective']+=.1
    else:m['tied:passive']['folds'][0]['training_blocks'].append(90000)
    with pytest.raises(AssertionError):check.check_all(nb,nbr,p,raw,m,*sources)


@pytest.mark.parametrize('kind',['coefficient','offset','scale','validation','training','target','prediction','raw'])
def test_source_corruption(sources,fitted,kind):
    data,b,br,p,raw,bf,rf=deepcopy(sources);fold=bf['separate:passive']['folds'][0];rec=fold['models'][5][0]
    if kind=='coefficient':rec['coefficients'][0][0]+=.1
    elif kind=='offset':rec['offsets'][0]+=.1
    elif kind=='scale':rec['scale'][0]+=.1
    elif kind=='validation':fold['validation_block']=-1
    elif kind=='training':fold['training_blocks'].append(90000)
    elif kind=='target':bf['separate:passive']['training_targets'][5]='original'
    elif kind=='prediction':b['separate:passive'].flat[0]+=.1
    else:br['separate:passive'].flat[0]+=.1
    with pytest.raises(AssertionError):check.check_all(*fitted,data,b,br,p,raw,bf,rf)


@pytest.mark.parametrize('kind',['full','refit','score','training','group','repeat','omit','model','metadata'])
def test_summary_corruption(sources,fitted,summary,kind):
    s=deepcopy(summary);panel=s['scores']['0.01'];d=panel['deletions'][0]
    if kind=='full':panel['full']['comparisons'][0]['original']['mse_reduction']+=.1
    elif kind=='refit':d['refitted']['comparisons'][0]['original']['mse_reduction']+=.1
    elif kind=='score':d['score_only']['comparisons'][0]['original']['mse_reduction']+=.1
    elif kind=='training':d['training_effect'][0]['individual_futures']['mse_reduction']+=.1
    elif kind=='group':panel['full']['models']['tied:passive']['individual_futures']['group_mse'][0]+=.1
    elif kind=='repeat':panel['full']['comparisons'][0]['by_repeat'][0]['mse_reduction']+=.1
    elif kind=='omit':panel['full']['comparisons'][0]['leave_one_repeat_out'][0]['mse_reduction']+=.1
    elif kind=='model':panel['full']['models']['starting']['original']['mse']+=.1
    else:s['penalty_geometry_matched']=False
    data,b,br,p,raw,bf,rf=sources
    with pytest.raises(AssertionError):check.check_summary(s,*fitted[:4],data,b,br,p,raw)


@pytest.mark.parametrize('key',['full__tied:passive__original__squared','deletion__tied:sham_minus__futures__signed',
 'full__tied:shuffle__change_from_separate__absolute'])
def test_error_corruption(sources,fitted,key):
    data,b,br,p,raw,bf,rf=sources;nb,nbr,npred,nraw,m=fitted
    arrays=model.case_errors(nb,npred,b,p,data);arrays[key].flat[0]+=.1
    with pytest.raises(AssertionError):check.check_errors(arrays,nb,npred,b,p,data)


def test_mean_losses(sources):
    data=deepcopy(sources[0]);data['labels'][:]=0;data['futures'][:]=0
    p={k:np.zeros((3,5,4,4)) for k in model.OBSERVERS}
    for prefix in ('separate:','mean:','tied:'):p[prefix+'sham_plus'][:]=1;p[prefix+'sham_minus'][:]=-1
    a=model.losses(p,data,0);b,_=check.loss_panel(p,data,0)
    for prefix in ('separate:','mean:','tied:'):
        for u,v in zip(a[prefix+'mean_sham_loss'],b[prefix+'mean_sham_loss']):
            np.testing.assert_array_equal(u,1);np.testing.assert_array_equal(v,1)


def test_source_bridge(sources,summary):
    data,b,br,p,raw,bf,rf=sources;old=model.prior.summarize(p,raw,b,br,data)
    assert check.source_bridge(summary,old,data,b,br,p,raw)['reference_check']['observer_comparison_records']==1815
    old['scores']['0.01']['deletions'][0]['refitted']['comparisons'][0]['individual_futures']['mse_reduction']+=.1
    with pytest.raises(AssertionError):check.source_bridge(summary,old,data,b,br,p,raw)


def test_roundtrip(sources,summary,fitted,tmp_path):
    assert run.ROOT in tmp_path.resolve().parents
    data,b,br,p,raw,bf,rf=sources;nb,nbr,npred,nraw,m=fitted
    for name,value in (('tied_full',nb),('tied_full_raw',nbr),('tied_deletions',npred),('tied_deletions_raw',nraw),
        ('case_errors',model.case_errors(nb,npred,b,p,data))):run.io.write_npz(tmp_path/(name+'.npz'),value,run.ROOT)
    run.io.write_json(tmp_path/'tied_fits.json',m,run.ROOT);run.io.write_json(tmp_path/'summary.json',summary,run.ROOT)
    old=model.prior.summarize(p,raw,b,br,data)
    assert run.verify_experiment(tmp_path,*sources,old)['fits']['passes']


def test_complete_specs():
    assert model.PAIRS==check.specifications() and len(model.PAIRS)==len(set(model.PAIRS))==33
    assert model.metadata(16)==check.metadata(16)
    m=model.metadata(16);assert m['new_fits']==3840 and m['new_predictions']==61440
    assert m['observer_comparison_records']==3267 and m['training_effect_records']==288


def test_source_closure():
    files=run.source_files();assert len(files)==2234 and len(set(files))==len(files)
    for name in run.SCIENCE:assert run.WS/name in files
    assert run.source_identity()['passes']


def test_resource_guard(monkeypatch):
    monkeypatch.setattr(run.previous,'resources',lambda starting:None)
    monkeypatch.setattr(run.shutil,'disk_usage',lambda p:SimpleNamespace(free=run.RESERVE+run.ALLOWANCE-1))
    with pytest.raises(RuntimeError):run.resources()
    run.resources(False)


def test_detach_guard(monkeypatch):
    monkeypatch.delenv(run.ENV,raising=False)
    with pytest.raises(RuntimeError):run.detached_guard(True,'execute')
    run.detached_guard(False,'execute')
    monkeypatch.setenv(run.ENV,'1')
    with pytest.raises(AssertionError):run.detached_guard(False,'execute')


def test_startup_handshake(monkeypatch):
    reader,writer=os.pipe();monkeypatch.setenv(run.READY,str(writer));run.ready('execute')
    message=os.read(reader,4096);os.close(reader);assert b'STARTED' in message
    assert run.READY not in os.environ
    source=inspect.getsource(run.detach)
    for token in ('start_new_session=True','stdin=subprocess.DEVNULL','pass_fds=(writer,)','[],[],55'):assert token in source


def test_no_automatic_successor():
    source=inspect.getsource(run)
    for token in ('time.sleep(','.poll(','.wait(','.terminate(','.kill('):assert token not in source
    assert not run.contract()['automatic_polling'] and not run.contract()['automatic_retry']
    assert not run.contract()['automatic_successor']


def test_no_dynamics_or_reference_refits(sources,monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('reference refit forbidden')
    monkeypatch.setattr(model.ridge,'fit',forbidden);monkeypatch.setattr(model.prior,'fit_all',forbidden)
    monkeypatch.setattr(check.old.group,'svd_path',forbidden)
    result=model.fit_all(*sources)
    assert check.check_all(*result,*sources)['reference_fits_recomputed'] is False
    source=inspect.getsource(model.fit_all)+inspect.getsource(run.execute)
    assert 'simulate' not in source and 'fixture(' not in source
