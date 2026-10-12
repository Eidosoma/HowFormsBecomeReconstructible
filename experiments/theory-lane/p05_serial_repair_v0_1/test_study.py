import copy
import json
import numpy as np
import pytest
import serial
import audit_reader
import lineage_dynamics as dynamics
from common import ROOT,read,arrays,equal,save_arrays
from audit_serial import masks,audit_prepared
from analyze import analyze,render,summary
from verify import verify,check_summary


def test_native_stream_generation_and_flat_equations():
    cfg=copy.deepcopy(read(ROOT/'config.json'))
    cfg['cycle']['read_steps']=16;cfg['cycle']['settling_steps']=8
    cfg['development_config']['observe_steps']=4;cfg['reader']['observe_steps']=4
    cfg['budgets']=[16];cfg['settling_steps']=8
    identity='synthetic_serial_equations_only';generation=19
    weights=np.ones((4,16,2,16,16));weights[1,:,0,0,0]=-1.
    packets=dynamics.encode(weights);raw=serial.rebuild(packets,identity,generation,cfg)
    equal(masks(identity,generation),raw['masks'],'flat damage generator')
    audit=audit_reader.replay(packets[:,0],raw['masks'][0],0,0,identity,0,cfg,original=True,generation=generation)
    for k in ('end','mean_ports'):equal(raw[k][:,0],audit[k][0],k)
    equal(raw['port_windows'][:,:,0],audit['port_windows'][0],'windows')


def test_known_repairs_erasure_and_corruption():
    cfg=read(ROOT/'config.json');known=arrays(ROOT/'sources/native_controls.npz')
    incoming=np.repeat(known['outgoing'].reshape(1,16,4096),4,axis=0)
    prepared,details=serial.prepare(incoming,34000,15,cfg)
    checkcfg=copy.deepcopy(cfg);checkcfg['generations']=[15]
    d={k:np.asarray(v)[None] for k,v in details.items()}
    d.update(incoming=incoming[None],prepared=prepared[None])
    assert audit_prepared(d,34000,checkcfg)==48
    equal(prepared[1],prepared[2],'first repair identity')
    d['prepared']=d['prepared'].copy();d['prepared'][0,2,0,17]^=1
    with pytest.raises(AssertionError):audit_prepared(d,34000,checkcfg)
    zero=np.zeros((2,16,16))
    repaired,_,m=serial.recipient_repair(zero,cfg['optimizer'])
    equal(repaired,zero,'erased record remains erased');assert m==0


def test_branch_specific_handoff_and_one_time_schedule(monkeypatch):
    cfg=copy.deepcopy(read(ROOT/'config.json'));cfg['generations']=[15,16,17]
    def cheap_repair(w,options):
        result=w.copy();result[w==0]=1.
        sol=dict(signs=np.ones((16,16),np.int8),candidate_costs=np.zeros(32),flips=np.zeros(16,int),
                 final_improvable_nodes=np.zeros(16,int),cost=0.,initial_cost=0.,winner=0,sweeps=1,selected_improvable_nodes=0)
        return result,sol,1.
    monkeypatch.setattr(serial,'recipient_repair',cheap_repair)
    def fake_rebuild(packets,identity,generation,configuration):
        weights=np.ones((4,16,2,16,16))
        values=[1,2,2,3] if generation==15 else [4,5,6,7]
        for v,value in enumerate(values):weights[v]*=value
        weights[:,:,0,0,0]=0
        return dict(outgoing=dynamics.encode(weights),end=np.zeros((4,16,2,16,16)),mean_ports=np.zeros((4,16,2,2)))
    initial=dynamics.encode(np.ones((16,2,16,16)))
    d=serial.continue_block(initial,81000,cfg,False,fake_rebuild)
    equal(d['incoming'][1:],d['outgoing'][:-1],'own successor carried forward')
    equal(d['prepared'][1:,1],d['incoming'][1:,1],'one-time stops')
    assert not np.array_equal(d['prepared'][1,2],d['incoming'][1,2])
    assert not np.array_equal(d['incoming'][2,1],d['incoming'][2,2])
    assert d['applied'].sum()==112


def test_failed_primary_despite_terminal_recovery_and_tamper(tmp_path):
    cfg=read(ROOT/'config.json')
    for b in cfg['blocks']:
        good=np.zeros((18,4,16),bool);opposite=np.zeros_like(good)
        good[:,0,:12]=True;good[:,1,:8]=True
        good[:,2,:4]=True;good[1:,2,:]=True
        opposite[0,2,14:]=True;opposite[:,3,0]=True
        ports=np.zeros((18,4,16,2,2))
        for gi in range(18):
            for v in range(4):
                for case in range(16):
                    coefficient=.5 if good[gi,v,case] else -.5 if opposite[gi,v,case] else 0.
                    rule=1 if case//4%2==0 else -1
                    ports[gi,v,case]=coefficient*rule*np.array([[1.,-1.],[-1.,1.]])
        windows=np.repeat(ports[:,None],32,axis=1);ports=windows.mean(axis=1)
        applied=np.array([np.repeat(serial.schedule(g)[:,None],16,axis=1) for g in cfg['generations']])
        d=dict(block=np.array(b),history=np.array(cfg['history_by_block'][str(b)]),
            mean_ports=ports,port_windows=windows,**serial.score(ports),applied=applied,
            missing_edges=np.ones((18,4,16),int),added_edges=applied.astype(int),
            added_abs_weight=applied*.5,magnitude=applied*.5,
            repair_cpu_seconds=applied*.001,audit_cpu_seconds=applied*.002,
            renewal_cpu_seconds=np.full(18,.01))
        save_arrays(tmp_path/f'continuation_{b:06d}.npz',d)
    a=analyze(tmp_path,cfg)
    assert a['contrasts']['repeated_minus_baseline']['uninterrupted']['mean']==-.5
    assert a['contrasts']['repeated_minus_baseline']['terminal']['mean']==.25
    assert not a['primary_direction_observed']
    assert a['rates']['repeated']['ever_recovered']['mean']==.75
    assert a['rates']['repeated']['ever_opposite']['mean']==.125
    assert verify(tmp_path,cfg,scientific=False)['status']=='PASS'
    render(tmp_path,cfg);assert 'The primary directional forecast failed.' in (tmp_path/'REPORT.md').read_text()
    a['primary_direction_observed']=True;(tmp_path/'analysis.json').write_text(json.dumps(a))
    with pytest.raises(AssertionError):verify(tmp_path,cfg,scientific=False)
    a['primary_direction_observed']=False;(tmp_path/'analysis.json').write_text(json.dumps(a,indent=2)+'\n')
    # Whole-block resampling must preserve the four equally weighted histories.
    values=np.tile([0.,.25,.5,.75],4);s=summary(values,cfg)
    assert s['descriptive_stratified_block_bootstrap_95']==[.375,.375]
    check_summary(s,values,cfg);s['descriptive_stratified_block_bootstrap_95']=[0.,1.]
    with pytest.raises(AssertionError):check_summary(s,values,cfg)
