"""D162 synthetic/disposable-only qualification; no pilot-founder generation."""
import copy
import inspect
import json
import os
import time
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from l20_extension1 import pilot_run as r, pilot_models as m, pilot_analysis as a
from l20_extension1 import heldout_system, heldout_diagnostics, repeated_system, probe_system


@pytest.fixture(scope='module')
def life():
    tick=time.monotonic();i=r.system.DISPOSABLE;guide=r.system.load_guide(r.dev.BASE)
    source,sm=r.system.generate_founders(i,0)
    fp=r.lineage_check.prior.check_founders(source,sm,r.system.CONFIG,True,tag=r.system.TAG)
    packets=r.packets(source);d,dm=r.diagnostic.simulate_life('disposable',i,0,packets,guide)
    dp=r.diagnostic_check.check_life(d,dm,packets,guide,True)
    _,plan=r.probe.candidates(packets,guide)
    p,pm=r.probe.simulate_life(('disposable',i),0,packets,guide,plan)
    pp=r.probe_check.check_life(p,pm,d,dm,True)
    lineage,lm=r.system.simulate_life(i,0,guide,source,sm)
    lp=r.lineage_check.check_life(lineage,lm,r.system.CONFIG,guide,True)
    extra=[];metadata=[]
    for future in (0,1,2,3):
        e,em=r.repeated.simulate(i,0,future,packets,guide)
        proof=r.repeated_check.check(e,em,packets,guide,True)
        extra.append(e);metadata.append(em)
    return dict(source=source,sm=sm,packets=packets,guide=guide,d=d,dm=dm,p=p,pm=pm,
        lineage=lineage,lm=lm,extra=extra,em=metadata,founder_proof=fp,diagnostic_proof=dp,
        probe_proof=pp,lineage_proof=lp,seconds=time.monotonic()-tick)


def test_complete_disposable_life(life,record_property):
    record_property('complete_life_seconds',life['seconds'])
    assert life['diagnostic_proof']['diagnostic_cycles']==12
    assert life['probe_proof']['replayed_cycles']==12 and life['lineage_proof']['full_life_replay']
    assert life['source']['written_fields'].shape==(2,2,16,16)


def test_full_source_adapter_contract():
    for new,old,names in ((r.system,heldout_system,('generate_founders','descendant','simulate_life')),
        (r.diagnostic,heldout_diagnostics,('cycle','simulate_life')),
        (r.repeated,repeated_system,('simulate',)),(r.probe,probe_system,('candidates','cycle','simulate_life'))):
        for name in names:assert inspect.getsource(getattr(new,name))==inspect.getsource(getattr(old,name))
    assert r.system.TISSUES==tuple(range(100000,100064)) and heldout_system.TISSUES==tuple(range(90000,90016))
    assert r.system.TAG=='l20-extension1-pilot64-v1:future0' and heldout_system.TAG=='l20-extension1-heldout-v1'


def test_future0_bridge(life):
    old=life['lineage'];new=life['extra'][0]
    for ci,case in enumerate(r.repeated.CASES):
        idx=r.system.CASES.index(case);ti=r.system.PROBES.index(case)
        for k,w in (('incoming','incoming'),('outgoing','outgoing'),('routed','routed'),
                    ('read_states','generation_read_states'),('write_states','generation_write_states')):
            np.testing.assert_array_equal(new[k][ci],old[w][idx])
        np.testing.assert_array_equal(new['terminal_states'][ci],old['terminal_states'][ti])


@pytest.mark.parametrize('future',[1,2,3])
def test_phase_separation(life,future):
    assert not np.array_equal(life['extra'][0]['read_states'][0,0,0],life['extra'][future]['read_states'][0,0,0])
    assert not np.array_equal(life['d']['read_states'][0,0,0],life['extra'][future]['read_states'][0,0,0])
    assert not np.array_equal(life['d']['terminal_states'][0,1,0],life['extra'][future]['terminal_states'][0,0])


@pytest.mark.parametrize('name',['d','p','lineage','extra'])
def test_saved_physics_corruption(life,name):
    if name=='d':
        raw=copy.deepcopy(life['d']);raw['diagnostic_features'][0,0,0]+=.001
        fn=lambda:r.diagnostic_check.check_life(raw,life['dm'],life['packets'],life['guide'],False)
    elif name=='p':
        raw=copy.deepcopy(life['p']);raw['input'][0,0,10]^=1
        fn=lambda:r.probe_check.check_life(raw,life['pm'],life['d'],life['dm'],False)
    elif name=='lineage':
        raw=copy.deepcopy(life['lineage']);raw['incoming'][0,1,10]^=1
        fn=lambda:r.lineage_check.check_life(raw,life['lm'],r.system.CONFIG,life['guide'],False)
    else:
        raw=copy.deepcopy(life['extra'][1]);raw['terminal_values'][0,-1,0]+=.001
        fn=lambda:r.repeated_check.check(raw,life['em'][1],life['packets'],life['guide'],False)
    with pytest.raises((AssertionError,ValueError)):fn()


def test_source_only_packet_boundary(life):
    for future in range(4):
        for ci,(role,_) in enumerate(r.repeated.CASES):
            np.testing.assert_array_equal(life['extra'][future]['incoming'][ci,0],life['packets'][role])
    for ci in range(4):
        np.testing.assert_array_equal(life['p']['read_states'][ci,:,0],np.repeat(life['d']['read_states'][ci,1,None,0],3,axis=0))


@pytest.fixture(scope='module')
def fitted():
    data=m.fixture();return data,m.fit_all(data)


def test_independent_models(fitted):
    data,fit=fitted;assert m.check_models(fit,data)['models']==51
    x={k:data[k] for k in ('start','endpoint','targeted')};p,raw=m.predict(fit,x)
    assert m.check_predictions(p,raw,fit,x)['forecasts']==4*16*51


def test_original_label_isolation(fitted):
    data,fit=fitted;changed=copy.deepcopy(data);changed['labels']*=-1
    assert m.fit_all(changed)==fit


@pytest.mark.parametrize('forbidden',['labels','futures','block_ids','record_pixels'])
def test_feature_boundaries(fitted,forbidden):
    data,fit=fitted;x={k:data[k] for k in ('start','endpoint','targeted')};x[forbidden]=np.zeros(1)
    with pytest.raises(ValueError):m.predict(fit,x)


def test_diagnostic_feature_isolation(fitted):
    data,fit=fitted;x={k:data[k].copy() for k in ('start','endpoint','targeted')};p,_=m.predict(fit,x)
    x['targeted']+=10;new,_=m.predict(fit,x)
    for key in ('starting','one_copy','tied:passive','tied:shuffle','separate:passive','mean:passive'):
        np.testing.assert_array_equal(p[key],new[key])


def test_tied_raw_slope(fitted):
    _,fit=fitted
    for k in m.OBSERVERS:
        if not k.startswith('tied:'):continue
        for model in fit['models'][k]:
            w=np.array(model['coefficients'])/model['scale']
            np.testing.assert_allclose(w[:,7:13],w[:,13:],atol=2e-14,rtol=0)


@pytest.mark.parametrize('field',['coefficients','scale','offsets'])
def test_model_corruption(fitted,field):
    data,fit=fitted;copyfit=copy.deepcopy(fit);arr=np.array(copyfit['models']['tied:passive'][1][field]);arr.flat[0]+=.01
    copyfit['models']['tied:passive'][1][field]=arr.tolist()
    with pytest.raises(AssertionError):m.check_models(copyfit,data)


@pytest.mark.parametrize('n',[1,8,16,64])
def test_control_normalization(life,n):
    raw=life['lineage'];small={k:np.repeat(raw[k][None],4,axis=0) for k in ('values','terminal_values','targets')}
    blocks=[small]*n;ids=list(range(n));summary=r.system.summarize(blocks,ids=ids)
    assert r.lineage_check.check_summary(summary,blocks,r.system.CONFIG,ids=ids)
    assert summary['generation_paths']==n*4*48 and summary['blocks']==n
    constant=np.full((n,4),.125);draws=np.random.default_rng(1).integers(0,n,(20000,n))
    assert r.lineage_check.stats(constant,draws)['mean']==.125
    assert r.lineage_check.stats(constant,draws)['pointwise_block_bootstrap_95']==[.125,.125]


@pytest.fixture(scope='module')
def scored(fitted):
    data,fit=fitted;p,raw=m.predict(fit,{k:data[k] for k in ('start','endpoint','targeted')})
    return a.summarize(p,raw,data['futures'],data['block_ids']),p,raw,data


def test_independent_scoring(scored):
    s,p,raw,data=scored;assert a.check_summary(s,p,raw,data['futures'],data['block_ids'])['passes']
    assert len(s['comparisons'])==264
    assert all(r['reference_alpha']==(.001 if r['reference']=='starting' else .01) for r in s['selected_cheap_baseline_comparisons'])


@pytest.mark.parametrize('kind',['gain','interval','label','blockcount'])
def test_summary_corruption(scored,kind):
    old,p,raw,data=scored;s=copy.deepcopy(old)
    if kind=='gain':s['comparisons'][0]['mse_reduction']+=.01
    elif kind=='interval':s['comparisons'][0]['block_bootstrap_95'][0]+=.01
    elif kind=='label':s['label']='EQUIVALENT'
    else:s['blocks']=8
    with pytest.raises(AssertionError):a.check_summary(s,p,raw,data['futures'],data['block_ids'])


def test_mean_sham_not_ensemble(fitted,scored):
    data,fit=fitted;s,p,raw,_=scored
    row=next(r for r in s['comparisons'] if r['candidate']=='tied:mean_sham_loss' and r['reference']=='tied:passive' and r['alpha']==.01)
    y=data['futures'];real=((p['tied:sham_plus'][1,...,None]-y)**2+(p['tied:sham_minus'][1,...,None]-y)**2).mean()/2
    np.testing.assert_allclose(row['candidate_mse'],real,atol=1e-14)


def sealed_fixture(tmp_path,monkeypatch,fitted):
    data,fit=fitted
    mp=tmp_path/'models.json';fp=tmp_path/'freeze.json'
    r.io.write_json(mp,{'synthetic_only':True},r.ROOT);r.io.write_json(fp,{'synthetic_only':True},r.ROOT)
    monkeypatch.setattr(r,'model_path',lambda:mp);monkeypatch.setattr(r,'freeze_path',lambda:fp)
    monkeypatch.setattr(r,'fitted_models',lambda:fit)
    measured={k:data[k][0] for k in ('start','endpoint','targeted')}
    monkeypatch.setattr(r,'check_forecast_block',lambda directory,index:measured)
    for name in r.forecast_files([r.system.DISPOSABLE]):
        if name.endswith('.npz'):r.io.write_npz(tmp_path/name,dict(synthetic=np.zeros(1)),r.ROOT)
        else:r.io.write_json(tmp_path/name,dict(synthetic_only=True),r.ROOT)
    seal=r.seal_forecasts(tmp_path,[r.system.DISPOSABLE]);return seal


def test_forecast_barrier(tmp_path,monkeypatch,fitted):
    with pytest.raises(FileNotFoundError):r.barrier(tmp_path,'absent')
    seal=sealed_fixture(tmp_path,monkeypatch,fitted)
    assert r.barrier(tmp_path,seal)['forecasts']==816
    assert not (tmp_path/'OUTCOMES_STARTED.json').exists()


@pytest.mark.parametrize('kind',['seal','founder','forecasts','models'])
def test_barrier_tampering(tmp_path,monkeypatch,fitted,kind):
    seal=sealed_fixture(tmp_path,monkeypatch,fitted)
    name={'seal':'FORECAST_SEAL.json','founder':f'founder_{r.system.DISPOSABLE}.npz','forecasts':'forecasts.npz','models':'models.json'}[kind]
    # Corruption fixtures are numerical test outputs on the external drive.
    path=tmp_path/name
    with path.open('ab') as stream:stream.write(b'corruption')
    with pytest.raises((AssertionError,ValueError)):r.barrier(tmp_path,seal)


def test_roundtrip(life,tmp_path):
    size=r.save_block(tmp_path,'founder',r.system.DISPOSABLE,[life['source']]*4,[life['sm']]*4)
    raw,meta=r.load_block(tmp_path,'founder',r.system.DISPOSABLE)
    assert size>0 and len(meta['lives'])==4
    for k,v in life['source'].items():np.testing.assert_array_equal(raw[k][0],v)


@pytest.mark.parametrize('index',[90000,100064,True,-1])
def test_main_id_boundary(index):
    with pytest.raises(ValueError):r.system.validate_index(index)


def test_resource_guards(monkeypatch):
    monkeypatch.setattr(r.development_run,'preflight',lambda _:None)
    monkeypatch.setattr(r.shutil,'disk_usage',lambda _:SimpleNamespace(free=r.RESERVE-1))
    with pytest.raises(RuntimeError):r.resources(False)
    monkeypatch.delenv(r.ENV,raising=False)
    with pytest.raises(RuntimeError):r.detached_guard(True,'execute')
    r.detached_guard(False,'benchmark')


def test_no_successor():
    assert r.contract()['automatic_successor'] is False and r.contract()['workers']==6
    for fn in (r.benchmark,r.execute,r.audit):
        assert 'detach' not in fn.__code__.co_names
    assert 'execute' not in r.benchmark.__code__.co_names and 'prepare' not in r.benchmark.__code__.co_names
    assert len(r.output_names())==len(set(r.output_names()))==712


def test_startup_ack(monkeypatch):
    readfd,writefd=os.pipe();monkeypatch.setenv(r.READY,str(writefd));r.ready('benchmark')
    value=json.loads(os.read(readfd,4096));os.close(readfd)
    assert value==dict(stage='benchmark',pid=os.getpid(),status='STARTED') and r.READY not in os.environ
