"""D165 fabricated coefficients only: no fitting or tissue dynamics."""
import ast
from copy import deepcopy
import inspect
import time
import numpy as np
import pytest
from l20_extension1 import decoder_transport as m, decoder_transport_check as c, decoder_transport_run as run


def sources(n=4,nt=5):
    df,_,_,_,dy,di=m.a.fixture(n,16520260922)
    pf,_,_,_,py,pi=m.a.fixture(nt,16520260923);di+=90000;pi+=100000
    shared=dict(schema='d164_shared_models_v1',training_blocks=di.tolist(),calibration=list(m.CALIBRATION),
        encodings=list(m.a.ENCODINGS),alphas=list(m.a.ALPHAS),new_fits=9*(n+1),models={},target='four_future_mean',
        pilot_outcomes_used=False,condition_indicator=False,inner_selection=False)
    cheap={k:dict(alphas=list(m.a.ALPHAS),blocks=di.tolist(),inner_selection=False,model_class=m.CHEAP_CLASS,
        observer=k,preprocessing='training-only within each whole-founder fold',prospective_evidence=False,
        training_targets=list(m.TARGETS),folds=[]) for k in ('starting','one_copy')}
    for e in m.a.ENCODINGS:shared['models'][e]=dict(training_blocks=di.tolist(),folds=[])
    for b in range(n):
        _,models,_,_,_,_=m.a.fixture(1,16500+b)
        train=di[di!=di[b]].tolist()
        for e in m.a.ENCODINGS:
            records=deepcopy(models[e+':passive'])
            for model in records:model.update(encoding=e,model_class=m.CLASS,calibration=list(m.CALIBRATION),
                training_rows=48*(n-1),unique_training_cases=16*(n-1))
            shared['models'][e]['folds'].append(dict(validation_block=int(di[b]),training_blocks=train,models=records))
        for name in ('starting','one_copy'):
            records=[]
            for target in range(6):
                row=deepcopy(models[name])
                for model in row:
                    model.update(model_class=m.CHEAP_CLASS)
                    model['offsets']=(np.asarray(model['offsets'])+.007*target).tolist()
                records.append(row)
            cheap[name]['folds'].append(dict(validation_block=int(di[b]),training_blocks=train,models=records))
    rules=m.registry(shared,cheap);dp,dr=m.forecasts(rules,df,di)
    # A separate fabricated reference; qualification makes no full-16 fitting claim.
    fp,fr=m.forecasts(rules[:1],pf);fp={k:v[0] for k,v in fp.items()};fr={k:v[0] for k,v in fr.items()}
    dev=(dp,dr,dy,di);full=(fp,fr,py,pi)
    prior=dict(cohorts={k:dict(scores=m.a.cohort(*v)) for k,v in [('development',dev),('pilot',full)]})
    d=dict(rules=rules,development_features=df,development_ids=di,pilot_features=pf,dp=dp,dr=dr)
    return shared,cheap,d,dict(dev=dev,full=full,prior=prior)


def calculate(d,scored):
    p,r=m.forecasts(d['rules'],d['pilot_features'])
    s=m.summarize(p,r,scored['dev'],scored['full'],d['development_ids'])
    return p,r,s


@pytest.fixture(scope='module')
def small():
    shared,cheap,d,scored=sources();p,r,s=calculate(d,scored)
    return shared,cheap,d,scored,p,r,s


def forbid(*args,**kwargs):raise AssertionError('no fitting allowed')


def test_full_panel_roundtrip(tmp_path,record_property,monkeypatch):
    assert run.ROOT in tmp_path.parents
    for name in ('solve','svd','lstsq'):monkeypatch.setattr(np.linalg,name,forbid)
    start=time.monotonic();shared,cheap,d,scored=sources(16,64);p,r,s=calculate(d,scored)
    proof=run.verify(d,p,r,s,scored)
    run.io.write_json(tmp_path/'shared.json',shared,run.ROOT);run.io.write_json(tmp_path/'cheap.json',cheap,run.ROOT)
    assert m.registry(run.io.read_json(tmp_path/'shared.json'),run.io.read_json(tmp_path/'cheap.json'))==d['rules']
    run.io.write_npz(tmp_path/'pilot_predictions.npz',p,run.ROOT);run.io.write_npz(tmp_path/'pilot_raw.npz',r,run.ROOT)
    run.io.write_json(tmp_path/'summary.json',s,run.ROOT)
    assert run.verify(d,*run.load_forecasts(tmp_path),run.io.read_json(tmp_path/'summary.json'),scored)==proof
    assert s['saved_rules']==240 and s['new_forecasts']==835584 and s['new_fits']==0
    assert proof['scores']['score_panels']==35
    assert sum(f.stat().st_size for f in tmp_path.iterdir())<run.source.ALLOWANCE
    with pytest.raises(FileExistsError):run.io.write_json(tmp_path/'summary.json',s,run.ROOT)
    record_property('full_panel_seconds',time.monotonic()-start)
    record_property('saved_rules',240);record_property('new_forecasts',835584);record_property('new_fits',0)


def test_no_fit_or_outcome_interface(small,monkeypatch):
    assert list(inspect.signature(m.registry).parameters)==['shared','cheap']
    assert list(inspect.signature(m.forecasts).parameters)==['rules','features','heldout_ids']
    for module in (m,c,run):
        for node in ast.walk(ast.parse(inspect.getsource(module))):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
                assert node.func.attr not in ('train','fit','solve','svd','lstsq','eigh','simulate','rollout')
    for name in ('solve','svd','lstsq'):monkeypatch.setattr(np.linalg,name,forbid)
    _,_,d,scored,_,_,_=small;calculate(d,scored)
    bad=dict(d['pilot_features'],outcomes=scored['full'][2])
    with pytest.raises(ValueError):m.forecasts(d['rules'],bad)
    code=inspect.getsource(run.execute)
    assert code.index('rule_seal(out,freeze_sha)')<code.index('forecast_seal(out,freeze_sha)')<code.index('scored=scored_inputs(d)')
    assert "['futures']" not in inspect.getsource(run.forecasting_inputs)


@pytest.mark.parametrize('kind',['shared_training','validation','duplicate','folds','cheap_training','target','cheap_alpha',
    'shared_alpha','class','count','calibration','tied','scale','coefficient','prospective','preprocessing'])
def test_model_corruption(small,kind):
    shared,cheap,*_=deepcopy(small);one=shared['models']['tied']['folds'][0]['models'][0]
    if kind=='shared_training':shared['models']['mean']['folds'][0]['training_blocks'].append(90000)
    elif kind=='validation':shared['models']['separate']['folds'][0]['validation_block']=90001
    elif kind=='duplicate':shared['training_blocks'][1]=90000
    elif kind=='folds':shared['models']['mean']['folds'].pop()
    elif kind=='cheap_training':cheap['starting']['folds'][0]['training_blocks'].append(90000)
    elif kind=='target':cheap['one_copy']['training_targets'][5]='original'
    elif kind=='cheap_alpha':cheap['one_copy']['folds'][0]['models'][5][1]['alpha']=.2
    elif kind=='shared_alpha':one['alpha']=.2
    elif kind=='class':one['model_class']='specific'
    elif kind=='count':shared['new_fits']+=1
    elif kind=='calibration':one['calibration']=['sham_plus']
    elif kind=='tied':one['coefficients'][0][13]+=.1
    elif kind=='scale':one['scale'][0]=0
    elif kind=='coefficient':one['coefficients'][0][0]=np.nan
    elif kind=='prospective':cheap['starting']['prospective_evidence']=True
    elif kind=='preprocessing':cheap['starting']['preprocessing']='all founders'
    with pytest.raises((AssertionError,ValueError)):m.registry(shared,cheap)


def test_whole_founder_exclusion_and_exact_rule(small):
    shared,cheap,d,_,p,r,_=small
    for b,rule in enumerate(d['rules']):
        assert rule['validation_block'] not in rule['training_blocks']
        for e in m.a.ENCODINGS:
            for k in m.a.EDITS:assert rule['models'][e+':'+k] is shared['models'][e]['folds'][b]['models']
        for name in ('starting','one_copy'):assert rule['models'][name] is cheap[name]['folds'][b]['models'][5]
    c.forecasts(d['rules'],d['development_features'],d['dp'],d['dr'],d['development_ids'])
    c.forecasts(d['rules'],d['pilot_features'],p,r)


def test_two_copy_isolation(small):
    _,_,d,_,p,r,_=small;f=deepcopy(d['pilot_features']);f['targeted'][...,2,:]+=1.2
    q,qr=m.forecasts(d['rules'],f)
    for name in p:
        if name.endswith(':sham_minus'):assert not np.array_equal(qr[name],r[name])
        else:np.testing.assert_array_equal(q[name],p[name])


def test_direction_swap(small):
    _,_,d,_,p,r,_=small;f=deepcopy(d['pilot_features']);f['targeted'][...,1:3,:]=f['targeted'][...,[2,1],:]
    q,qr=m.forecasts(d['rules'],f)
    for e in m.a.ENCODINGS:
        np.testing.assert_array_equal(q[e+':sham_plus'],p[e+':sham_minus'])
        np.testing.assert_array_equal(q[e+':sham_minus'],p[e+':sham_plus'])


def test_permutations(small):
    _,_,d,scored,p,r,s=small;order=np.array([2,0,3,1]);f={k:v[order] for k,v in d['development_features'].items()}
    rules=[d['rules'][j] for j in order];dp,dr=m.forecasts(rules,f,d['development_ids'][order])
    for name in dp:c.close(dp[name],d['dp'][name][:,order])
    q,qr=m.forecasts(rules,d['pilot_features'])
    for name in q:c.close(q[name],p[name][order])
    values,n=m.moments(q,qr,scored['full'][2],scored['full'][3]);base,bn=m.moments(p,r,scored['full'][2],scored['full'][3])
    for name in base:c.close(values[name]['loss'],base[name]['loss'])
    po=np.array([4,1,0,3,2]);f={k:v[po] for k,v in d['pilot_features'].items()};q,qr=m.forecasts(d['rules'],f)
    for name in q:c.close(q[name],p[name][:,:,po])


def test_loss_not_ensemble():
    p={k:np.empty((2,3,1,4,4)) for k in m.a.OBSERVERS}
    for v in p.values():v[0]=.3;v[1]=-.3
    y=np.zeros((1,4,4,4));ids=np.array([1],dtype=np.int64);values,n=m.moments(p,p,y,ids)
    s=m.panel(values,n,ids,y);c.panel(s,p,p,y,ids)
    c.close(s['absolute']['starting'][0]['mse'],.09)
    assert np.mean(p['starting'],axis=0).max()==0
    assert s['founders']==1 and s['calibrations']==2 and s['comparisons'][0]['omit_founder'] is None
    assert s['forecast_instances_per_observer_alpha']==32
    # The virtual plus/minus observer also averages errors, never readings.
    p={k:v[:1].copy() for k,v in p.items()}
    for e in m.a.ENCODINGS:p[e+':sham_minus'][:]=-.3
    values,_=m.moments(p,p,y,ids);c.close(m.loss(values,'tied:mean_sham_loss',0),.09)


def test_clipping_and_single_founder(small):
    _,_,d,scored,_,_,_=deepcopy(small)
    for rule in d['rules']:
        for model in rule['models']['starting']:model['offsets']=[3.]*4
    p,r=m.forecasts(d['rules'],d['pilot_features']);c.forecasts(d['rules'],d['pilot_features'],p,r)
    values,n=m.moments(p,r,scored['full'][2],scored['full'][3]);s=m.panel(values,n,scored['full'][3],scored['full'][2])
    c.panel(s,p,r,scored['full'][2],scored['full'][3])
    assert s['absolute']['starting'][0]['clipped']==4*5*16


@pytest.mark.parametrize('kind',['duplicate_ids','dtype','bound','nan','missing_future','missing_observer','clipping','empty_rules'])
def test_bad_scoring_input(small,kind):
    _,_,_,scored,p,r,_=deepcopy(small);y=scored['full'][2];ids=scored['full'][3]
    if kind=='duplicate_ids':ids[0]=ids[1]
    elif kind=='dtype':y=y.astype(np.float32)
    elif kind=='bound':y[0,0,0,0]=2
    elif kind=='nan':p['starting'][0,0,0,0,0]=np.nan
    elif kind=='missing_future':y=y[...,:3]
    elif kind=='missing_observer':p.pop('starting')
    elif kind=='clipping':p['starting'][0,0,0,0,0]+=.1
    elif kind=='empty_rules':p={k:v[:0] for k,v in p.items()};r={k:v[:0] for k,v in r.items()}
    with pytest.raises((AssertionError,KeyError)):m.moments(p,r,y,ids)


@pytest.mark.parametrize('kind',['pooled','fold','baseline','count','prospective','source','change','founders'])
def test_summary_corruption(small,kind):
    _,_,d,scored,p,r,s=deepcopy(small)
    if kind=='pooled':s['cohorts']['pilot']['comparisons'][0]['overall']+=.01
    elif kind=='fold':s['calibrations'][0]['pilot']['absolute']['starting'][0]['mse']+=.01
    elif kind=='baseline':s['cohorts']['development']['absolute']['one_copy'][0]['mae_points']+=.1
    elif kind=='count':s['new_forecasts']+=1
    elif kind=='prospective':s['prospective_evidence']=True
    elif kind=='source':scored['prior']['cohorts']['pilot']['scores']['absolute']['starting'][0]['mse']+=.1
    elif kind=='change':s['cohort_gain_changes'][0]['calibrations'][0]+=.01
    elif kind=='founders':s['cohorts']['pilot']['founders']*=4
    with pytest.raises(AssertionError):c.summary(s,p,r,**scored)


def test_forecast_corruption(small):
    _,_,d,_,p,r,_=deepcopy(small);r['mean:passive'][0,0,0,0,0]+=.01
    with pytest.raises(AssertionError):c.forecasts(d['rules'],d['pilot_features'],p,r)


@pytest.mark.parametrize('kind',['hash','time','prospective','target','count'])
def test_seal_corruption(tmp_path,monkeypatch,kind):
    models=[tmp_path/'shared.json',tmp_path/'cheap.json']
    for path in models:run.io.write_json(path,dict(fabricated=True),run.ROOT)
    monkeypatch.setattr(run,'model_paths',lambda:models)
    for name in ('pilot_predictions.npz','pilot_raw.npz'):run.io.write_npz(tmp_path/name,dict(x=np.zeros(1)),run.ROOT)
    run.rule_seal(tmp_path,'freeze');run.forecast_seal(tmp_path,'freeze')
    run.io.write_json(tmp_path/'SCORING_STARTED.json',dict(started_utc=run.source.utc_now(),
        forecast_seal_sha256=run.source.sha256_file(tmp_path/'FORECAST_SEAL.json'),prospective_evidence=False),run.ROOT)
    assert run.check_seals(tmp_path,'freeze')['passes']
    original=run.io.read_json
    def corrupted(path):
        data=original(path)
        if path.name=='FORECAST_SEAL.json':
            if kind=='hash':data['forecast_sha256'][str(tmp_path/'pilot_raw.npz')]='0'*64
            elif kind=='time':data['sealed_utc']='2099-01-01T00:00:00+00:00'
            elif kind=='prospective':data['prospective_evidence']=True
            elif kind=='count':data['new_forecasts']+=1
        if path.name=='RULE_SEAL.json' and kind=='target':data['cheap_target_index']=0
        return data
    monkeypatch.setattr(run.io,'read_json',corrupted)
    with pytest.raises(AssertionError):run.check_seals(tmp_path,'freeze')


def test_stage_guard(monkeypatch):
    monkeypatch.delenv(run.ENV,raising=False);run.stage_guard(dict(must_detach=False),'execute')
    with pytest.raises(AssertionError):run.stage_guard(dict(must_detach=True),'execute')
    monkeypatch.setenv(run.ENV,'execute');monkeypatch.setattr(run.os,'getsid',lambda _:11)
    monkeypatch.setattr(run.os,'getpid',lambda:12)
    with pytest.raises(AssertionError):run.stage_guard(dict(must_detach=True),'execute')


def test_source_hash_corruption(tmp_path):
    path=tmp_path/'source.json';run.io.write_json(path,dict(synthetic=True),run.ROOT)
    run.source.check_hashes(run.io.hashes([path]))
    with pytest.raises(AssertionError):run.source.check_hashes({str(path):'0'*64})
