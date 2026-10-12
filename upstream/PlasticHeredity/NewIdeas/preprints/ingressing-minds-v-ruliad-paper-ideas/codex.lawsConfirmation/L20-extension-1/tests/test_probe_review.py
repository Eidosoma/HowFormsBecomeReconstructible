"""Disposable/synthetic qualification for the D151 saved-case audit."""
import copy
import inspect
import json
import os
import numpy as np
import pytest
from l20_extension1 import probe_review as p,probe_review_check as c,probe_review_run as run


def forbidden(*args,**kwargs):raise AssertionError('simulation or fit forbidden')


@pytest.fixture(scope='module')
def raw():return run.raw_block(run.source.system.DISPOSABLE)


@pytest.fixture(scope='module')
def value(raw):return p.extract(*raw)


@pytest.fixture(scope='module')
def panel(value):return p.fixture(value)


def test_full_block(raw,tmp_path):
    value=p.extract(*raw);assert c.check_block(value,*raw)['field_checkpoints']==1920
    run.io.write_npz(tmp_path/'block.npz',value,run.ROOT)
    assert c.check_block(run.io.load_npz(tmp_path/'block.npz'),*raw)['passes']
    assert tmp_path.is_relative_to(run.ROOT/'tmp')


def test_summary(panel,tmp_path):
    data,arch=panel;summary=p.summarize(data,arch,True)
    run.io.write_json(tmp_path/'summary.json',summary,run.ROOT)
    run.io.write_npz(tmp_path/'panel.npz',data,run.ROOT)
    proof=c.check_summary(run.io.read_json(tmp_path/'summary.json'),run.io.load_npz(tmp_path/'panel.npz'),arch,True)
    assert proof['associations']==100 and proof['secondary_associations']==40
    assert proof['new_models']==proof['new_dynamics']==0


def test_independent_check(raw,value,panel,monkeypatch):
    data,arch=panel;s=p.summarize(data,arch,True)
    for name in ('extract','summarize','correlation','error_stats','loss_terms'):monkeypatch.setattr(p,name,forbidden)
    monkeypatch.setattr(p.field,'measure',forbidden)
    assert c.check_block(value,*raw)['passes']
    assert c.check_summary(s,data,arch,True)['passes']


@pytest.mark.parametrize('role',[0,1])
@pytest.mark.parametrize('amplitude',[0.,.2,np.nextafter(.2,np.inf),1.])
def test_threshold(role,amplitude):
    v=p.field.TARGETS[role]*amplitude;codes=p.field.codes(v,role)
    assert np.all(codes==(1 if amplitude>.2 else 0))
    np.testing.assert_array_equal(codes,c.fields.states(v,role))


def test_roles():
    v=np.random.default_rng(5).normal(size=(4,16,16));a=p.field.measure(v,0);b=p.field.measure(v,1)
    for x,y in ((3,4),(6,7),(9,10),(13,14)):np.testing.assert_array_equal(a[...,x],b[...,y])
    for role in (0,1):np.testing.assert_allclose(p.field.measure(v,role),c.fields.measure(v,role),atol=1e-12,rtol=0)


@pytest.mark.parametrize('left,right',[(np.ones(32),np.arange(32)),(np.arange(32),np.ones(32)),(np.zeros(32),np.zeros(32))])
def test_constant(left,right):
    assert p.correlation(left,right) is None and c.pearson(left,right) is None


@pytest.mark.parametrize('sign',[-1,1])
def test_correlation(sign):
    x=np.arange(128).reshape(32,4);y=sign*x
    a=p.association(x,y);b=c.association(x,y);assert a['cases']==128 and a['blocks']==32
    assert a['case_r']==a['block_mean_r']==b['case_r']==b['block_mean_r']==sign


def test_error_identity(panel):
    data,_=panel;e,t=p.loss_terms(data['predictions'],data['labels']);ee,tt=c.reconstruct_terms(data['predictions'],data['labels'])
    np.testing.assert_array_equal(e,ee);np.testing.assert_allclose(t,tt,atol=1e-14,rtol=0)
    np.testing.assert_allclose(t[...,5,2],e[...,3]**2-(e[...,4]**2+e[...,5]**2)/2,atol=1e-14,rtol=0)
    for group in range(4):
        m=p.error_stats(e[:,:,group,3]);assert abs(m['mse']-(m['bias_points']/100)**2-m['centered_error_variance'])<1e-14


def test_future_identity(panel):
    data,arch=panel;s=p.summarize(data,arch,True)
    for row in s['repeated_future_accounting']:
        assert abs(row['individual_mse']-row['mean_target_mse']-row['within_future_population_variance'])<1e-14
    spreads=[r['within_future_population_variance'] for r in s['repeated_future_accounting']]
    assert max(spreads)==min(spreads)


@pytest.mark.parametrize('key',['fields','preference'])
def test_derived_corruption(raw,value,key):
    bad={k:v.copy() for k,v in value.items()};bad[key].flat[-1]+=.1
    with pytest.raises(AssertionError):c.check_block(bad,*raw)


@pytest.mark.parametrize('key',['input','read_states','write_states','terminal_states','outgoing','terminal_packet','diagnostic_features'])
def test_raw_corruption(raw,value,key):
    edited={k:v.copy() for k,v in raw[0].items()}
    if edited[key].dtype==np.uint8:edited[key].reshape(-1,2048)[0,:8]=np.frombuffer(np.float64(7.).tobytes(),np.uint8)
    else:edited[key].flat[0]+=.1
    with pytest.raises((AssertionError,ValueError)):c.check_block(value,edited,raw[1])


@pytest.mark.parametrize('section',['sections','responses','associations','repeated_future_associations','repeated_future_accounting','trajectories'])
def test_summary_corruption(panel,section):
    data,arch=panel;s=p.summarize(data,arch,True)
    if section=='sections':s[section]['all']['models'][0]['mse']+=.1
    elif section=='responses':s[section][0]['endpoint']['mean']+=.1
    elif section in ('associations','repeated_future_associations'):s[section][0]['cases']-=1
    elif section=='repeated_future_accounting':s[section][0]['individual_mse']+=.1
    else:s[section][0]['fields'][0][0]+=.1
    with pytest.raises(AssertionError):c.check_summary(s,data,arch,True)


def test_order_and_retention(panel):
    data,arch=panel;s=p.summarize(data,arch,True)
    assert len(s['responses'])==20 and len(s['trajectories'])==24 and s['all_cases_retained']
    assert all(row['matched_noise']==(row['branch']!='U0') for row in s['responses'])
    bad=dict(data,preference=data['preference'][:,:,::-1].copy())
    with pytest.raises(AssertionError):c.check_summary(s,bad,arch,True)


def test_normalization():
    x=np.zeros((32,4));x[-1]=1
    assert p.describe(x)['mean']==c.describe(x)['mean']==1/32
    assert p.describe(x)['positive']==4


@pytest.mark.parametrize('key',['block_field_means','block_preference_means','absolute_error','squared_error'])
def test_explicit_case_retention(panel,key):
    data,arch=panel;s=p.summarize(data,arch,True);bad={k:v.copy() for k,v in data.items()}
    bad[key].flat[-1]+=.1
    with pytest.raises(AssertionError):c.check_summary(s,bad,arch,True)


def test_zero_errors(panel):
    data,arch=panel;bad={k:v.copy() for k,v in data.items()}
    bad['predictions']=np.repeat(bad['labels'][...,None],6,axis=-1)
    bad['error'],bad['comparison_terms']=p.loss_terms(bad['predictions'],bad['labels'])
    bad['absolute_error']=abs(bad['error']);bad['squared_error']=bad['error']**2
    s=p.summarize(bad,arch,True);assert c.check_summary(s,bad,arch,True)['passes']
    assert s['sections']['all']['models'][0]['groups'][0]['squared_error_share_percent'] is None


def test_source_score_bridge(panel):
    data,arch=panel;s=p.summarize(data,arch,True)
    old=dict(models={},comparisons=[],repeated_future_models={})
    for row in s['sections']['all']['models']:
        old['models'][row['model']]={k:row[k] for k in ('mse','mae_points','rmse_points')}
        old['models'][row['model']]['group_mse']=[g['mse'] for g in row['groups']]
    for row in s['sections']['all']['comparisons']:
        old['comparisons'].append(dict(candidate=row['candidate'],reference=row['reference'],mse_reduction=-row['terms'][-1]))
    for row in s['repeated_future_accounting']:
        old['repeated_future_models'][row['model']]=dict(individual_future_mse=row['individual_mse'],mean_target_mse=row['mean_target_mse'])
    assert c.source_scores(s,old)['original_primary_unchanged']
    old['comparisons'][0]['mse_reduction']+=.1
    with pytest.raises(AssertionError):c.source_scores(s,old)


def test_architecture():
    fits={}
    for mi,name in enumerate(p.MODELS):
        d=7 if mi==0 else 19
        fits[name]=dict(blocks=list(range(32)),folds=[dict(validation_block=i,model=dict(beta=[0]*d,
            means=np.zeros((4,d)).tolist(),offsets=[0]*4,scale=[1]*d)) for i in range(32)])
    assert len(p.architecture(fits))==6
    fits['passive']['folds'][0]['model']['beta']=np.zeros((4,19)).tolist()
    with pytest.raises(AssertionError):p.architecture(fits)


def test_source_closure():
    paths=run.source_files();assert len(paths)>=1909 and len(paths)==len(set(paths))
    assert all(run.WS/name in paths for name in run.SCIENCE)
    assert run.COMPLETE=='68742ebaa28c3594dcd72123e481561f7e51a6549a6c752f6e56196764e9a13f'


def test_no_dynamics(raw,monkeypatch):
    for name in ('read_selected','write_streams','generator'):monkeypatch.setattr(run.source.system.old,name,forbidden)
    monkeypatch.setattr(run.source.system,'simulate_life',forbidden)
    monkeypatch.setattr(run.source.models.ridge,'nested',forbidden)
    value=p.extract(*raw);assert c.check_block(value,*raw)['new_dynamics']==0
    data,arch=p.fixture(value);assert c.check_summary(p.summarize(data,arch,True),data,arch,True)['new_models']==0


def test_no_source_mutation(raw):
    copies=tuple({k:v.copy() for k,v in source.items()} for source in raw)
    for source in copies:
        for value in source.values():value.setflags(write=False)
    p.extract(*copies)
    for source,original in zip(copies,raw):
        for k,v in source.items():np.testing.assert_array_equal(v,original[k])


def test_resource_guard(monkeypatch):
    monkeypatch.setattr(run.source.previous,'resources',forbidden)
    with pytest.raises(AssertionError):run.resources()


def test_detach_guard(monkeypatch):
    monkeypatch.delenv(run.ENV,raising=False)
    with pytest.raises(RuntimeError):run.detached_guard(True,'execute')
    run.detached_guard(False,'execute')


def test_startup_handshake(monkeypatch):
    reader,writer=os.pipe();monkeypatch.setenv(run.READY,str(writer));run.ready('execute')
    value=json.loads(os.read(reader,4096));os.close(reader)
    assert value==dict(stage='execute',pid=os.getpid(),status='STARTED') and run.READY not in os.environ


def test_no_automatic_successor():
    contract=run.contract();assert contract['automatic_polling'] is contract['automatic_retry'] is contract['automatic_successor'] is False
    code=inspect.getsource(run.detach)
    assert 'start_new_session=True' in code and 'stdin=subprocess.DEVNULL' in code and 'select.select([reader],[],[],55)' in code
    assert '.poll(' not in code and '.wait(' not in code
    assert 'io.failure(run,error,ROOT)' in inspect.getsource(run.execute)
