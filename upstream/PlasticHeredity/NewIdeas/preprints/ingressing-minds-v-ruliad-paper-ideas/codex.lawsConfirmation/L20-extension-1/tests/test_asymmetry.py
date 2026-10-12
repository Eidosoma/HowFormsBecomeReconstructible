"""Synthetic qualification only: no tissue dynamics, fitting or real scoring."""
import ast
from copy import deepcopy
import json
import os
from pathlib import Path
import time
import numpy as np
import pytest
from l20_extension1 import asymmetry as a, asymmetry_check as c, asymmetry_run as run


@pytest.fixture(scope='module')
def small():return a.fixture(4)


def test_full64_panel(record_property):
    begin=time.monotonic();data,models,p,raw,y,ids=a.fixture(64)
    s=a.cohort(p,raw,y,ids);m,v=a.model_accounting(data,models,p,raw,y,ids)
    assert c.check_cohort(s,p,raw,y,ids)['passes']
    assert c.check_models(m,v,data,models,p,raw,y,ids)['passes']
    record_property('full_panel_seconds',time.monotonic()-begin)
    record_property('founders',64);record_property('comparisons',277);record_property('saved_forecasts',52224)


@pytest.mark.parametrize('candidate,reference,target,alignment,cost,gain',[
    (.2,0.,.5,.2,.04,.16),(0.,.2,.5,-.12,.04,-.16),
    (.2,.2,.5,0.,0.,0.),(.5,0.,.5,.5,.25,.25),(-.2,0.,.5,-.2,.04,-.24)])
def test_scalar_identity(candidate,reference,target,alignment,cost,gain):
    y=np.full((2,4,4,4),target);p=np.full((2,4,4),candidate);r=np.full_like(p,reference)
    c.close(a.pair_cells(p,r,y),np.broadcast_to([alignment,cost,gain],y.shape+(3,)))


def test_bias_centering(small):
    _,_,p,_,y,ids=small;row=a.pair_record(p,y,ids,a.specifications()[0])
    d=p[row['candidate']][0]-p[row['reference']][0];res=y-p[row['reference']][0,...,None]
    for k in range(len(ids)):
        keep=np.arange(len(ids))!=k
        bias=2*d[keep].mean()*res[keep].mean()
        c.close(row['omit_founder'][k][1],bias)
    for k in range(4):
        keep=np.arange(4)!=k
        c.close(row['omit_future'][k][1],2*d.mean()*res[...,keep].mean())


def test_virtual_mean_is_loss_not_forecast(small):
    _,_,source,_,y,ids=small;p={k:np.zeros_like(v) for k,v in source.items()}
    p['tied:sham_plus'][:]=.4;p['tied:sham_minus'][:]=-.4
    spec=dict(candidate='tied:mean_sham_loss',reference='tied:passive',candidate_alpha=.01,reference_alpha=.01)
    row=a.pair_record(p,y,ids,spec)
    c.close(row['overall'][-1],-.16)
    ensemble=(p['tied:sham_plus'][1]+p['tied:sham_minus'][1])/2
    c.close(((ensemble[...,None]-y)**2-(p['tied:passive'][1,...,None]-y)**2).mean(),0.)


def test_sign_reversal(small):
    _,_,p,_,y,_=small
    args=[p['tied:'+k][1] for k in ('sham_plus','sham_minus','passive')]
    z=a.sign_cells(*args,y);r=a.sign_cells(args[1],args[0],args[2],y)
    c.close(z[...,0],r[...,0]);c.close(z[...,1],-r[...,1]);c.close(z[...,2],r[...,3]);c.close(z[...,4],-r[...,4])


def test_permutations(small):
    _,_,p,raw,y,ids=small;s=a.cohort(p,raw,y,ids)
    perm=np.array([2,0,3,1]);pp={k:v[:,perm] for k,v in p.items()};rr={k:v[:,perm] for k,v in raw.items()}
    z=a.cohort(pp,rr,y[perm],ids[perm])
    for first,last in zip(s['comparisons'],z['comparisons']):
        c.close(first['overall'],last['overall']);c.close(np.asarray(first['blocks'])[perm],last['blocks'])
    spec=a.specifications()[1];row=a.pair_record(p,y,ids,spec)
    by_group=a.pair_record({k:v[:,:,:,perm] for k,v in p.items()},y[:,:,perm],ids,spec)
    c.close(row['overall'],by_group['overall']);c.close(np.asarray(row['groups'])[perm],by_group['groups'])
    by_future=a.pair_record(p,y[...,perm],ids,spec)
    c.close(row['overall'],by_future['overall']);c.close(np.asarray(row['futures'])[perm],by_future['futures'])


@pytest.mark.parametrize('kind',['nan','dtype','shape','missing','duplicate_id','id_dtype','outcome_bound','clipping'])
def test_invalid_inputs(small,kind):
    _,_,p,raw,y,ids=deepcopy(small)
    if kind=='nan':p['starting'][0,0,0,0]=np.nan
    elif kind=='dtype':p['starting']=p['starting'].astype(np.float32)
    elif kind=='shape':y=y[...,:3]
    elif kind=='missing':del raw['starting']
    elif kind=='duplicate_id':ids[0]=ids[1]
    elif kind=='id_dtype':ids=ids.astype(np.float64)
    elif kind=='outcome_bound':y[0,0,0,0]=1.1
    elif kind=='clipping':p['starting'][0,0,0,0]+=.01
    with pytest.raises(ValueError):a.validate(p,raw,y,ids)


@pytest.mark.parametrize('field',['labels','outcomes','block_ids'])
def test_forbidden_features(small,field):
    data=deepcopy(small[0]);data[field]=np.zeros(4)
    with pytest.raises(ValueError):a.feature_matrices(data)


@pytest.mark.parametrize('kind',['scale','means','alpha','missing','coefficient'])
def test_bad_models(small,kind):
    data,models,p,raw,y,ids=deepcopy(small)
    if kind=='scale':models['starting'][0]['scale'][0]=0
    elif kind=='means':models['starting'][0]['means'].pop()
    elif kind=='alpha':models['starting'][0]['alpha']=.2
    elif kind=='missing':models.pop('one_copy')
    else:models['starting'][0]['coefficients'][0][0]+=.1
    with pytest.raises((ValueError,AssertionError)):a.model_accounting(data,models,p,raw,y,ids)


def test_clipping_accounting(small):
    data,models,p,raw,y,ids=deepcopy(small)
    for key,sign in [('tied:sham_plus',1),('tied:sham_minus',-1)]:
        models[key][1]['offsets']=[3.*sign]*4
        raw[key][1]=c.forward(models[key][1],c.matrix(data,key));p[key][1]=np.clip(raw[key][1],-1,1)
    summary,arrays=a.model_accounting(data,models,p,raw,y,ids)
    assert np.any(arrays['tied__1__forecast_parts'][...,2]!=0)
    assert c.check_models(summary,arrays,data,models,p,raw,y,ids)['passes']


@pytest.mark.parametrize('key',['overall','blocks','groups','futures','omit_founder','omit_future'])
def test_summary_corruption(small,key):
    _,_,p,raw,y,ids=small;s=a.cohort(p,raw,y,ids)
    v=np.asarray(s['comparisons'][0][key]);v.flat[-1]+=.001;s['comparisons'][0][key]=v.tolist()
    with pytest.raises(AssertionError):c.check_cohort(s,p,raw,y,ids)


def test_array_corruption(small):
    data,models,p,raw,y,ids=small;s,arrays=a.model_accounting(data,models,p,raw,y,ids)
    arrays['tied__1__forecast_parts'][0,0,0,0]+=.001
    with pytest.raises(AssertionError):c.check_models(s,arrays,data,models,p,raw,y,ids)


def test_roundtrip(small,tmp_path):
    assert run.ROOT in tmp_path.parents
    data,models,p,raw,y,ids=small;s,arrays=a.model_accounting(data,models,p,raw,y,ids)
    run.io.write_json(tmp_path/'summary.json',s,run.ROOT);run.io.write_npz(tmp_path/'parts.npz',arrays,run.ROOT)
    assert c.check_models(run.io.read_json(tmp_path/'summary.json'),run.io.load_npz(tmp_path/'parts.npz'),data,models,p,raw,y,ids)['passes']
    with pytest.raises(FileExistsError):run.io.write_json(tmp_path/'summary.json',s,run.ROOT)
    with pytest.raises(ValueError):run.io.write_json(Path('/tmp/d163_disallowed.json'),s,run.ROOT)


def test_source_binding(tmp_path):
    path=tmp_path/'binding.json';run.io.write_json(path,dict(a=1),run.ROOT)
    hashes=run.io.hashes([path]);run.check_hashes(hashes)
    with pytest.raises(AssertionError):run.bind(path,'0'*64,{})
    with pytest.raises(AssertionError):run.check_hashes({str(tmp_path/'absent.json'):'0'*64})
    with pytest.raises(AssertionError):run.io.hashes([path,path])


def test_source_bridge_corruption():
    _,_,p,raw,y,ids=a.fixture(64);main=a.cohort(p,raw,y,ids+100000)
    _,_,p,raw,y,ids=a.fixture(16);dev=a.cohort(p,raw,y,ids+90000)
    def legacy(r):
        return dict(candidate=r['candidate'],reference=r['reference'],candidate_alpha=r['candidate_alpha'],
            reference_alpha=r['reference_alpha'],mse_reduction=r['overall'][-1],candidate_mse=r['candidate_mse'],
            reference_mse=r['reference_mse'],block_differences=np.asarray(r['blocks'])[:,-1].tolist(),
            group_differences=np.asarray(r['groups'])[:,-1].tolist(),future_differences=np.asarray(r['futures'])[:,-1].tolist())
    old=dict(label='PREDICTIVE_DIFFERENCE_UNRESOLVED',founder_ids=main['ids'],absolute_scores=main['absolute'],
             comparisons=[legacy(r) for r in main['comparisons'][:264]],
             selected_cheap_baseline_comparisons=[legacy(r) for r in main['comparisons'][264:268]])
    planning=dict(source_founders=dev['ids'],comparisons=[dict(candidate=r['candidate'],reference=r['reference'],
        alpha=r['candidate_alpha'],mean_gain=r['overall'][-1],reference_mse=r['reference_mse'],
        block_gains=np.asarray(r['blocks'])[:,-1].tolist()) for r in dev['comparisons'][:69]])
    assert c.source_bridge(main,dev,dict(prediction=old),planning)['passes']
    old['comparisons'][0]['mse_reduction']+=.001
    with pytest.raises(AssertionError):c.source_bridge(main,dev,dict(prediction=old),planning)


def test_stage_guard(monkeypatch):
    monkeypatch.delenv(run.ENV,raising=False);run.stage_guard(dict(must_detach=False),'execute')
    with pytest.raises(AssertionError):run.stage_guard(dict(must_detach=True),'execute')
    monkeypatch.setenv(run.ENV,'audit')
    with pytest.raises(AssertionError):run.stage_guard(dict(must_detach=True),'execute')


@pytest.mark.parametrize('key,value',[('OMP_NUM_THREADS','2'),('PYTHONDONTWRITEBYTECODE','0'),('TMPDIR','/tmp')])
def test_resource_guards(monkeypatch,key,value):
    monkeypatch.setenv(key,value)
    with pytest.raises(AssertionError):run.resources()


def test_no_fit_dynamics_or_search():
    forbidden={'fit','fit_models','minimize','optimize','bootstrap','simulate','rollout','run_life','future_worker'}
    for path in run.science():
        if path.suffix!='.py' or path.name.startswith('test_'):continue
        tree=ast.parse(path.read_text())
        names={node.func.id if isinstance(node.func,ast.Name) else node.func.attr
               for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,(ast.Name,ast.Attribute))}
        assert not names&forbidden
    assert len(a.specifications())==277
    assert len(run.PINS)==5 and all(len(v)==64 for v in run.PINS.values())
