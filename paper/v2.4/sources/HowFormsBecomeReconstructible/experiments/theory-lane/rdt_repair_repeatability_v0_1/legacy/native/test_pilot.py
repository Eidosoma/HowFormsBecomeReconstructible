"""Cached evidence, unequal class sizes, and short synthetic continuation checks."""
import copy
import hashlib
import numpy as np
import pytest

from bridge import ROOT,P,e,ev,read
import audit_pilot
import ledger
import prepare_cache
import runner
import scoring_pilot as scoring


def fixture_panel():
    rows=[];forecasts=[];outcomes=[];packets=[]
    random=np.random.default_rng(2026101608)
    for block,classes in [(-2,[0,1,1]),(-1,[0,0,1,1])]:
        for i,current in enumerate(classes):
            history=P['acquisition']['histories'][i%4]
            key=[block,history,i,0]
            packet=random.uniform(-1,1,(2,16,16)) if i%2 else np.full((2,16,16),.6)
            row=dict(key=key,block=block,history=history,current_pass=current,rule=1 if i%2==0 else -1,
                     selection_hash=hashlib.sha256(str(key).encode()).hexdigest(),
                     packet_sha256=hashlib.sha256(packet.tobytes()).hexdigest())
            rows.append(row);packets.append(packet)
            probability=[1.,.5,.5][i] if block==-2 else [0.,.5,.75,1.][i]
            for regime in scoring.REGIMES:
                forecasts.append(dict(**row,regime=regime,probabilities=dict(candidate=probability,direct_rival=.6,tt008=.7)))
                outcomes.append(dict(key=key,regime=regime,passed=0))
    return rows,forecasts,outcomes,np.stack(packets)


def test_budget_and_all_cached_first_repeat_forecasts():
    assert P['resources']['pilot_wall_ceiling_seconds']==3600
    assert P['resources']['forecast_seconds']<3600
    assert P['resources']['automatic_extension'] is False
    assert P['resources']['user_general_ceiling_seconds']==21600
    rows,forecasts,packets=runner.check_cache()
    assert len(rows)==len(packets)==63 and len(forecasts)==126
    assert len({r['block'] for r in rows})==16
    assert sum(r['current_pass']==0 for r in rows)==31
    assert read(ROOT/'context/source_COMPLETE.json')['new_future_outcomes']==0


def test_first_repeat_is_fixed_and_never_averaged():
    raw=dict(packet=np.ones((2,16,16)),probes=np.arange(64),direct_probes=np.r_[0:8,32:40],
             writer_passed=np.r_[np.zeros(32),np.ones(32)][:,None],
             successor_passed=np.r_[np.zeros(32),np.ones(32)][:,None],
             direct_passed=np.r_[np.zeros(8),np.ones(8)][:,None])
    selected=prepare_cache.first_repeat(raw)
    assert selected['probes'].tolist()==list(range(32))
    assert selected['direct_probes'].tolist()==list(range(8))
    assert selected['successor_passed'].sum()==selected['direct_passed'].sum()==0
    assert selected['packet'].tobytes()==raw['packet'].tobytes()
    raw['probes']=np.arange(63)
    with pytest.raises(ValueError):prepare_cache.first_repeat(raw)


def test_unequal_class_sizes_receive_equal_class_and_block_weight():
    rows,forecasts,outcomes,_=fixture_panel()
    result=scoring.analyze(rows,forecasts,outcomes)
    audit_pilot.evaluate(rows,forecasts,outcomes,result)
    value=result['regimes']['matched']
    assert value['score_blocks']['candidate']==pytest.approx([.625,.453125])
    assert value['scores']['candidate']==pytest.approx(.5390625)
    calibration=value['calibration']['candidate']
    assert calibration[9]['records']==2 and calibration[9]['mean_prediction']==1.
    assert calibration[9]['panel_mass']==pytest.approx(.375)
    assert sum(v['panel_mass'] for v in calibration)==pytest.approx(1.)
    assert calibration[3]['records']==0 and calibration[3]['observed_fraction'] is None
    c=value['current_expression']
    assert .5*(c['0']['scores']['candidate']+c['1']['scores']['candidate'])==pytest.approx(value['scores']['candidate'])


@pytest.mark.parametrize('bad',['missing_forecast','duplicate_outcome','missing_class','bad_probability','wrong_metadata'])
def test_invalid_panel_cannot_produce_inference(bad):
    rows,forecasts,outcomes,_=fixture_panel()
    if bad=='missing_forecast':forecasts.pop()
    elif bad=='duplicate_outcome':outcomes.append(copy.deepcopy(outcomes[0]))
    elif bad=='missing_class':rows=[r for r in rows if r['current_pass']==1]
    elif bad=='bad_probability':forecasts[0]['probabilities']['candidate']=float('nan')
    else:forecasts[0]['current_pass']=1-forecasts[0]['current_pass']
    with pytest.raises(ValueError):scoring.analyze(rows,forecasts,outcomes)


def test_independent_audit_detects_changed_contrast():
    rows,forecasts,outcomes,_=fixture_panel()
    result=scoring.analyze(rows,forecasts,outcomes)
    result['regimes']['independent']['primary']['tt008']['lower']+=.1
    with pytest.raises(ArithmeticError):audit_pilot.evaluate(rows,forecasts,outcomes,result)
    assert scoring.limits([.002,.002],.002)['decision']=='REJECTED'
    assert scoring.limits([.003,.003],.002)['decision']=='SUPPORTED'
    assert scoring.limits([-.1,.1],.002)['decision']=='UNRESOLVED'


def test_barrier_then_complete_short_synthetic_pipeline(monkeypatch,tmp_path):
    for config in (P['reader'],e.DESIGN['reader']):
        for name,value in dict(read_steps=24,settling_steps=12,observe_steps=4).items():
            monkeypatch.setitem(config,name,value)
    rows,forecasts,_,packets=fixture_panel()
    incomplete=tmp_path/'incomplete';incomplete.mkdir()
    with pytest.raises(ValueError):
        runner.work(incomplete,rows,forecasts[:-1],packets,runner.Guard(incomplete,120),'synthetic')
    assert not (incomplete/'FORECAST_SEAL.json').exists() and not (incomplete/'futures').exists()
    target=tmp_path/'complete';target.mkdir()
    events=[]
    result=runner.work(target,rows,forecasts,packets,runner.Guard(target,120),'synthetic',
                       lambda stage,details:events.append((stage,details)))
    assert result['records']==7 and result['acquisition_blocks']==2 and result['case_regimes']==14
    assert result['primary_native_reads']==266 and result['flat_native_reads']==76
    assert len(events)==4 and read(target/'VERIFICATION.json')['status']=='PASS'
    seal=read(target/'FORECAST_SEAL.json')
    assert seal['forecasts']==forecasts and seal['complete_cohort_checked_before_any_future']
    for ref in read(target/'FUTURE_REFERENCES.json'):
        folder,committed=ledger.referenced(target,ref)
        raw=ev.load(folder/'future.npz',read(folder/'future.json')['raw_sha256'])
        assert raw['generations'].tolist()==list(range(15,34))
        assert raw['g32_packets'].tobytes()==raw['outgoing'][-2].tobytes()
        assert raw['incoming'][1:].tobytes()==raw['outgoing'][:-1].tobytes()
        assert committed['identity']['seal_sha256']==ev.sha(target/'FORECAST_SEAL.json')


def test_hard_budget_guard(tmp_path):
    with pytest.raises(TimeoutError):runner.Guard(tmp_path,0).check()
