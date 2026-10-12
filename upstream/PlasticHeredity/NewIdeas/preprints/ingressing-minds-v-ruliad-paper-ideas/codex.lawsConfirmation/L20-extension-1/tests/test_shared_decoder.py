"""D164 synthetic qualification: fitting is allowed; no actual tissue runs."""
import ast
from copy import deepcopy
import inspect
import json
import time
import xml.etree.ElementTree as ET
import numpy as np
import pytest
from l20_extension1 import shared_decoder as m, shared_decoder_check as c, shared_decoder_run as run


def fixture(n=4,nt=5):
    df,_,dp,dr,dy,di=m.a.fixture(n,16420260922)
    pf,_,pp,pr,py,pi=m.a.fixture(nt,16420260923)
    di+=90000;pi+=100000
    sources=dict(development=(dp,dr,dy,di),pilot=(pp,pr,py,pi))
    prior={k:m.a.cohort(*v) for k,v in sources.items()}
    return dict(training_features=df,training_futures=dy,training_ids=di,features=pf,
                prior_summary=prior,**sources)


def calculate(d):
    records=m.train(d['training_features'],d['training_futures'],d['training_ids'])
    panels={}
    for co,f,ids in [('development',d['training_features'],d['training_ids']),('pilot',d['features'],None)]:
        p,r=m.forecast(records,f,ids);panels[co]=m.with_baselines(p,r,*d[co][:2])
    return records,panels,m.summarize(panels,{k:d[k] for k in ('development','pilot')})


def source_bridge_fixture(d):
    def legacy(r):
        return dict(candidate=r['candidate'],reference=r['reference'],candidate_alpha=r['candidate_alpha'],reference_alpha=r['reference_alpha'],
            candidate_mse=r['candidate_mse'],reference_mse=r['reference_mse'],mse_reduction=r['overall'][-1],
            block_differences=np.asarray(r['blocks'])[:,-1].tolist(),group_differences=np.asarray(r['groups'])[:,-1].tolist(),
            future_differences=np.asarray(r['futures'])[:,-1].tolist())
    p=d['prior_summary']['pilot'];dev=d['prior_summary']['development']
    d['pilot_source']=dict(prediction=dict(label='PREDICTIVE_DIFFERENCE_UNRESOLVED',founder_ids=p['ids'],absolute_scores=p['absolute'],
        comparisons=[legacy(r) for r in p['comparisons'][:264]],selected_cheap_baseline_comparisons=[legacy(r) for r in p['comparisons'][264:268]]))
    d['planning']=dict(source_founders=dev['ids'],comparisons=[dict(candidate=r['candidate'],reference=r['reference'],alpha=r['candidate_alpha'],
        mean_gain=r['overall'][-1],reference_mse=r['reference_mse'],block_gains=np.asarray(r['blocks'])[:,-1].tolist()) for r in dev['comparisons'][:69]])


@pytest.fixture(scope='module')
def small():
    d=fixture();records,panels,summary=calculate(d)
    return d,records,panels,summary


def test_full_panel_roundtrip(tmp_path,record_property):
    assert run.ROOT in tmp_path.parents;start=time.monotonic()
    d=fixture(16,64);source_bridge_fixture(d);records,panels,summary=calculate(d)
    proof=run.verify(records,panels,summary,d)
    assert proof['models']['fitted_models']==153 and summary['new_forecasts']==57600
    run.io.write_json(tmp_path/'models.json',records,run.ROOT);run.io.write_json(tmp_path/'summary.json',summary,run.ROOT)
    for co,(p,r) in panels.items():
        run.io.write_npz(tmp_path/(co+'_predictions.npz'),p,run.ROOT);run.io.write_npz(tmp_path/(co+'_raw.npz'),r,run.ROOT)
    assert run.verify(run.io.read_json(tmp_path/'models.json'),run.load_panels(tmp_path),run.io.read_json(tmp_path/'summary.json'),d)==proof
    with pytest.raises(FileExistsError):run.io.write_json(tmp_path/'summary.json',summary,run.ROOT)
    record_property('full_panel_seconds',time.monotonic()-start)
    record_property('fitted_models',153);record_property('new_forecasts',57600)


def test_whole_founder_exclusion(small):
    d,records,_,_=deepcopy(small)
    for v in d['training_features'].values():v[0]*=3.;v[0]+=.5
    d['training_futures'][0]*=-1
    changed=m.train(d['training_features'],d['training_futures'],d['training_ids'])
    for e in m.a.ENCODINGS:
        assert changed['models'][e]['folds'][0]==records['models'][e]['folds'][0]
        assert changed['models'][e]['models']!=records['models'][e]['models']


def test_no_pilot_label_interface(small):
    assert list(inspect.signature(m.train).parameters)==['features','futures','ids']
    assert list(inspect.signature(m.forecast).parameters)==['records','features','ids']
    assert list(inspect.signature(m.forward).parameters)==['model','x']
    d,records,_,_=small;bad=dict(d['features']);bad['pilot_outcomes']=d['pilot'][2]
    with pytest.raises(ValueError):m.forecast(records,bad)
    source=inspect.getsource(run.execute)
    assert source.index("out/'models.json'")<source.index("out/'FORECAST_SEAL.json'")<source.index('d=scored_inputs()')


def test_two_copy_isolation(small):
    d,records,panels,_=small;features=deepcopy(d['features']);features['targeted'][...,2,:]+=1.5
    p,raw=m.forecast(records,features)
    for e in m.a.ENCODINGS:
        for kind in ('passive','shuffle','attenuate','sham_plus'):
            np.testing.assert_array_equal(p[e+':'+kind],panels['pilot'][0][e+':'+kind])
        assert not np.array_equal(raw[e+':sham_minus'],panels['pilot'][1][e+':sham_minus'])


def test_direction_swap(small):
    d,records,_,_=small;features=deepcopy(d['training_features'])
    features['targeted'][...,1:3,:]=features['targeted'][...,[2,1],:]
    swapped=m.train(features,d['training_futures'],d['training_ids'])
    for e in m.a.ENCODINGS:
        for got,want in zip(swapped['models'][e]['models'],records['models'][e]['models']):
            for key in ('means','offsets','scale','coefficients'):c.close(got[key],want[key])
    p,r=m.forecast(records,d['training_features']);q,rr=m.forecast(swapped,features)
    for e in m.a.ENCODINGS:
        c.close(p[e+':sham_plus'],q[e+':sham_minus']);c.close(p[e+':sham_minus'],q[e+':sham_plus'])
        c.close(p[e+':passive'],q[e+':passive'])


def test_identical_copies_equal_predictions(small):
    d,records,_,_=small;features=deepcopy(d['features'])
    features['targeted'][...,1,:]=features['endpoint'][...,1,:]
    features['targeted'][...,2,:]=features['endpoint'][...,1,:]
    p,raw=m.forecast(records,features)
    for e in m.a.ENCODINGS:
        for k in ('sham_plus','sham_minus'):np.testing.assert_array_equal(p[e+':'+k],p[e+':passive'])


@pytest.mark.parametrize('encoding',['separate','mean','tied'])
def test_row_replication_preserves_regularization(small,encoding):
    d,_,_,_=small;x=m.a.feature_matrices(d['training_features'])
    X,Y,g=m.pooled(x,d['training_futures'].mean(-1),encoding,np.arange(4,dtype=np.int64))
    first=m.path(X,Y,g,encoding);twice=m.path(np.repeat(X,2,0),np.repeat(Y,2),np.repeat(g,2),encoding)
    for a,b in zip(first,twice):
        for k in ('means','offsets','scale','coefficients'):c.close(a[k],b[k])
        assert a['training_rows']==192 and a['unique_training_cases']==64


def test_tied_raw_slopes(small):
    _,records,_,_=small
    for r in records['models']['tied']['models']:
        b=np.array(r['coefficients']);s=np.array(r['scale']);c.close(b[:,7:13]/s[7:13],b[:,13:]/s[13:])
        c.close(np.sum(b*b),np.sum(np.array(r['reduced_coefficients'])**2))


def test_founder_permutation(small):
    d,records,panels,_=small;order=np.array([2,0,3,1]);features={k:v[order] for k,v in d['training_features'].items()}
    ids=d['training_ids'][order];new=m.train(features,d['training_futures'][order],ids);p,r=m.forecast(new,features,ids)
    for name in p:c.close(p[name],panels['development'][0][name][:,order])


def test_constant_features_and_labels():
    f,_,_,_,y,ids=m.a.fixture(4)
    for v in f.values():v[:]=.7
    y[:]=.23;records=m.train(f,y,ids)
    assert c.check_models(records,f,y,ids)['passes']
    p,r=m.forecast(records,f,ids)
    for v in p.values():c.close(v,.23)


def test_mean_target_linearity(small):
    d,_,_,_=small;X,Y,g=m.pooled(m.a.feature_matrices(d['training_features']),d['training_futures'].mean(-1),'tied',np.arange(4,dtype=np.int64))
    mean=m.path(X,Y,g,'tied');single=[m.path(X,np.tile(d['training_futures'][...,j].ravel(),3),g,'tied') for j in range(4)]
    for ai in range(3):
        for key in ('coefficients','offsets'):c.close(mean[ai][key],sum(np.array(s[ai][key]) for s in single)/4)


@pytest.mark.parametrize('kind',['ids_dtype','duplicate_ids','missing_founder','nan','feature_dtype','unknown_feature','future_bound','missing_future','future_dtype','future_nan'])
def test_invalid_training(small,kind):
    d,_,_,_=deepcopy(small);f,y,ids=d['training_features'],d['training_futures'],d['training_ids']
    if kind=='ids_dtype':ids=ids.astype(float)
    elif kind=='duplicate_ids':ids[0]=ids[1]
    elif kind=='missing_founder':ids=ids[:-1]
    elif kind=='nan':f['targeted'][0,0,0,0,0]=np.nan
    elif kind=='feature_dtype':f['start']=f['start'].astype(np.float32)
    elif kind=='unknown_feature':f['direction']=np.zeros(4)
    elif kind=='future_bound':y[0,0,0,0]=2
    elif kind=='missing_future':y=y[...,:3]
    elif kind=='future_dtype':y=y.astype(np.float32)
    elif kind=='future_nan':y[0,0,0,0]=np.nan
    with pytest.raises(ValueError):m.train(f,y,ids)


@pytest.mark.parametrize('kind',['coefficient','scale','means','alpha','calibration','training_ids','validation_ids','class','count'])
def test_model_corruption(small,kind):
    d,records,_,_=deepcopy(small);one=records['models']['mean']['models'][0]
    if kind=='coefficient':one['coefficients'][0][0]+=.01
    elif kind=='scale':one['scale'][0]*=2
    elif kind=='means':one['means'][0][0]+=.01
    elif kind=='alpha':one['alpha']=.02
    elif kind=='calibration':one['calibration']=['sham_plus']
    elif kind=='training_ids':records['models']['mean']['folds'][0]['training_blocks'].append(90000)
    elif kind=='validation_ids':records['models']['mean']['folds'][0]['validation_block']=90001
    elif kind=='class':one['model_class']='condition_specific'
    elif kind=='count':records['new_fits']+=1
    with pytest.raises(AssertionError):c.check_models(records,d['training_features'],d['training_futures'],d['training_ids'])


def test_clipped_forecast(small):
    d,records,_,_=deepcopy(small)
    for r in records['models']['mean']['models']:r['offsets']=[3.]*4
    p,raw=m.forecast(records,d['features']);assert np.any(p['mean:passive']!=raw['mean:passive'])
    assert c.check_forecasts(records,d['features'],p,raw)['passes']


def test_forecast_corruption(small):
    d,records,_,_=small;p,r=m.forecast(records,d['features']);r['mean:sham_minus'][0,0,0,0]+=.01
    with pytest.raises(AssertionError):c.check_forecasts(records,d['features'],p,r)


@pytest.mark.parametrize('kind',['gain','original','baseline','count','prospective'])
def test_summary_corruption(small,kind):
    d,_,panels,s=deepcopy(small)
    if kind=='gain':s['cohorts']['development']['decoder_changes'][10]['overall']+=.01
    elif kind=='original':d['prior_summary']['development']['comparisons'][0]['overall'][0]+=.01
    elif kind=='baseline':panels['development'][0]['starting'][0,0,0,0]+=.01
    elif kind=='count':s['new_forecasts']+=1
    elif kind=='prospective':s['prospective_evidence']=True
    with pytest.raises((ValueError,AssertionError)):c.check_summary(s,panels,{k:d[k] for k in ('development','pilot')},d['prior_summary'])


def test_virtual_loss_and_unchanged_baselines(small):
    d,_,panels,s=small;assert c.check_summary(s,panels,{k:d[k] for k in ('development','pilot')},d['prior_summary'])['passes']
    for co in ('development','pilot'):
        rows=s['cohorts'][co]['decoder_changes']
        for r in rows:
            if r['observer'] in ('starting','one_copy'):assert r['overall']==0
        for e in m.a.ENCODINGS:
            for alpha in m.a.ALPHAS:
                get=lambda k:next(r['overall'] for r in rows if r['observer']==e+':'+k and r['alpha']==alpha)
                c.close(get('mean_sham_loss'),(get('sham_plus')+get('sham_minus'))/2)


@pytest.mark.parametrize('bad',['none','time','model_hash','prospective','forecast_hash'])
def test_seal_corruption(tmp_path,bad):
    freeze='a'*64
    run.io.write_json(tmp_path/'models.json',dict(synthetic=True),run.ROOT)
    for name in run.OUTPUTS[2:6]:run.io.write_npz(tmp_path/name,dict(synthetic=np.zeros(1)),run.ROOT)
    model_hash=run.source.sha256_file(tmp_path/'models.json')
    ms=dict(sealed_utc='2026-09-22T01:00:00+00:00',models_sha256=model_hash,freeze_sha256=freeze,new_fits=153,
        scoring_started=False,prospective_evidence=False,training_blocks=list(range(90000,90016)),calibration=list(m.CALIBRATION))
    ps=dict(sealed_utc='2026-09-22T01:00:01+00:00',models_sha256=model_hash,freeze_sha256=freeze,
        forecast_sha256=run.io.hashes(tmp_path/k for k in run.OUTPUTS[2:6]),new_forecasts=57600,reused_forecasts=7680,
        scoring_started=False,prospective_evidence=False,development_blocks=list(range(90000,90016)),pilot_blocks=list(range(100000,100064)))
    if bad=='time':ms['sealed_utc']='2026-09-22T01:00:03+00:00'
    elif bad=='model_hash':ps['models_sha256']='b'*64
    elif bad=='prospective':ps['prospective_evidence']=True
    elif bad=='forecast_hash':ps['forecast_sha256'][str(tmp_path/run.OUTPUTS[2])]='b'*64
    run.io.write_json(tmp_path/'MODEL_SEAL.json',ms,run.ROOT);run.io.write_json(tmp_path/'FORECAST_SEAL.json',ps,run.ROOT)
    run.io.write_json(tmp_path/'SCORING_STARTED.json',dict(started_utc='2026-09-22T01:00:02+00:00',prospective_evidence=False,
        forecast_seal_sha256=run.source.sha256_file(tmp_path/'FORECAST_SEAL.json')),run.ROOT)
    if bad=='none':assert run.check_seals(tmp_path,freeze)['passes']
    else:
        with pytest.raises(AssertionError):run.check_seals(tmp_path,freeze)


def test_stage_guard(monkeypatch):
    monkeypatch.delenv(run.ENV,raising=False);run.stage_guard(dict(must_detach=False),'execute')
    with pytest.raises(AssertionError):run.stage_guard(dict(must_detach=True),'execute')
    monkeypatch.setenv(run.ENV,'audit')
    with pytest.raises(AssertionError):run.stage_guard(dict(must_detach=True),'execute')


@pytest.mark.parametrize('failed',[False,True])
def test_qualification_receipt(tmp_path,monkeypatch,failed):
    # Parameterized case names must qualify by their stable test-function name.
    monkeypatch.setattr(run,'ROOT',tmp_path);logs=tmp_path/'logs';logs.mkdir()
    report=ET.Element('testsuite')
    required=['test_full_panel_roundtrip','test_whole_founder_exclusion','test_no_pilot_label_interface',
              'test_two_copy_isolation','test_direction_swap','test_seal_corruption[none]','test_stage_guard']
    for name in required+[f'extra_{i}' for i in range(40)]:
        case=ET.SubElement(report,'testcase',name=name,classname='test_shared_decoder')
        if name=='test_full_panel_roundtrip':
            props=ET.SubElement(case,'properties')
            for key,value in [('full_panel_seconds','5.0'),('fitted_models','153'),('new_forecasts','57600')]:
                ET.SubElement(props,'property',name=key,value=value)
    if failed:ET.SubElement(case,'failure')
    path=logs/'d164_synthetic_receipt.xml';ET.ElementTree(report).write(path)
    if failed:
        with pytest.raises(AssertionError):run.qualification(path)
    else:assert run.qualification(path)['tests']==47


@pytest.mark.parametrize('key,value',[('OMP_NUM_THREADS','2'),('PYTHONDONTWRITEBYTECODE','0'),('TMPDIR','/tmp')])
def test_resource_guard(monkeypatch,key,value):
    monkeypatch.setenv(key,value)
    with pytest.raises(AssertionError):run.source.resources()


def test_no_dynamics_or_model_selection():
    forbidden={'simulate','rollout','run_life','future_worker','bootstrap','outer_fold','nested','minimize','optimize'}
    for path in run.science():
        if path.suffix!='.py' or path.name.startswith('test_'):continue
        tree=ast.parse(path.read_text());calls={n.func.id if isinstance(n.func,ast.Name) else n.func.attr for n in ast.walk(tree)
            if isinstance(n,ast.Call) and isinstance(n.func,(ast.Name,ast.Attribute))}
        assert not calls&forbidden
    assert m.CALIBRATION==('passive','sham_plus','sham_minus')
