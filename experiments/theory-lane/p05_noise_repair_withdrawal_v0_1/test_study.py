import copy
import json
import numpy as np
import pytest
import serial
import audit_reader
import lineage_dynamics as dynamics
from common import ROOT,read,arrays,equal,save_arrays
from audit_serial import masks,audit_noise,audit_block
from analyze import analyze,render
from verify import verify


def test_independent_noise_and_single_arm_flat_dynamics():
    cfg=copy.deepcopy(read(ROOT/'config.json'))
    z=np.tile([-1.,-1.,1.,1.],512).reshape(2,4,16,16)
    e=np.tile([-1.,1.,-1.,1.],512).reshape(2,4,16,16)
    draws,moments=serial.noise_pair(z,e,[0.])
    equal(draws[0,:,:,0],dynamics.paired_founders(z),'base forcing')
    equal(draws[0,:,:,1],dynamics.paired_founders(e),'independent forcing')
    np.testing.assert_allclose(moments[0]/z.size,[0,0,1,1,0,1],rtol=0,atol=0)
    cfg['cycle']['read_steps']=16;cfg['cycle']['settling_steps']=8
    cfg['development_config']['observe_steps']=4;cfg['reader']['observe_steps']=4
    cfg['budgets']=[16];cfg['settling_steps']=8
    identity='synthetic_withdrawal_equations_only';generation=19
    weights=np.ones((1,16,2,16,16));weights[:,:,0,0,0]=-1.
    packets=dynamics.encode(weights)
    raw=serial.rebuild(packets,np.zeros((16,16,16),bool),identity,generation,cfg)
    equal(masks(identity,generation),raw['masks'],'independent injury')
    for founder,recipient in [(0,0),(3,2)]:
        case=founder*4+recipient
        flat=audit_reader.replay(packets[:,case],raw['masks'][case],founder,recipient,identity,0,cfg,
            original=True,generation=generation,rhos=[0.])
        for key in ('end','mean_ports'):equal(raw[key][:,case],flat[key][0],key)
        equal(raw['port_windows'][:,:,case],flat['port_windows'][0],'windows')
    np.testing.assert_allclose(raw['noise_moments'],audit_noise(identity,generation,cfg),rtol=1e-13,atol=1e-8)


def test_known_first_repair_reused_controls_and_corruption():
    cfg=copy.deepcopy(read(ROOT/'config.json'));cfg['generations']=[15]
    full=arrays(ROOT/'sources/controls_081000.npz')
    controls={k:a.copy() if k in ('block','history') else a[:1].copy() for k,a in full.items()}
    boundary=arrays(ROOT/'sources/boundaries.npz');initial=boundary['initial_packets'][0]
    prepared,details=serial.prepare(initial[None],81000,15,cfg)
    new={}
    for key,value in controls.items():
        if key in serial.COMMON_FIELDS:new[key]=value.copy()
        elif key=='port_windows':new[key]=value[:,:,1:2].copy()
        else:new[key]=value[:,1:2].copy()
    new['prepared']=prepared[None]
    for key,value in details.items():new[key]=value[None]
    new['new_arm_renewal_cpu_seconds']=np.zeros(1)
    first={k:v[0] for k,v in new.items() if k not in ('block','history')}
    serial.check_first(first,controls)
    combined=serial.assemble(new,controls)
    result=audit_block(combined,initial,boundary['previous_masks'][0],controls,81000,cfg)
    assert result['new_independent_optimizer_checks']==16 and result['independent_repair_constructions']==32
    assert result['native_audit_contexts']==2
    damaged={k:v.copy() for k,v in first.items()};damaged['prepared'][0,0,17]^=1
    with pytest.raises(AssertionError):serial.check_first(damaged,controls)
    bad={k:v.copy() for k,v in combined.items()};bad['outgoing'][0,0,0,17]^=1
    with pytest.raises(AssertionError):audit_block(bad,initial,boundary['previous_masks'][0],controls,81000,cfg)
    zero=np.zeros((2,16,16));repaired,_,m=serial.recipient_repair(zero,cfg['optimizer'])
    equal(repaired,zero,'erased record unchanged');assert m==0


def test_withdrawal_stops_all_repairs_and_keeps_own_successor(monkeypatch):
    cfg=copy.deepcopy(read(ROOT/'config.json'));cfg['generations']=[15,16,17]
    calls=[]
    def cheap_repair(w,options):
        calls.append(True);result=w.copy();result[w==0]=1.
        solution=dict(signs=np.ones((16,16),np.int8),candidate_costs=np.zeros(32),
            flips=np.zeros(16,int),final_improvable_nodes=np.zeros(16,int),
            cost=0.,initial_cost=0.,winner=0,sweeps=1,selected_improvable_nodes=0)
        return result,solution,1.
    monkeypatch.setattr(serial,'recipient_repair',cheap_repair)
    def fake(packets,previous_mask,identity,generation,configuration):
        weights=np.full((1,16,2,16,16),float(generation));weights[:,:,0,0,0]=0
        return dict(outgoing=dynamics.encode(weights),end=np.zeros((1,16,2,16,16)),
            mean_ports=np.zeros((1,16,2,2)),masks=np.zeros((16,16,16),bool))
    weights=np.ones((16,2,16,16));weights[:,0,0,0]=0
    d=serial.continue_block(dynamics.encode(weights),np.zeros((16,16,16),bool),81000,cfg,False,fake)
    assert len(calls)==16 and d['applied'].sum()==16
    equal(d['incoming'][1:],d['outgoing'][:-1],'own successor')
    equal(d['prepared'][1:],d['incoming'][1:],'withdrawal is exact')
    assert not np.array_equal(d['prepared'][0],d['incoming'][0])
    for key in d:
        if key.startswith('optimizer_') or key in ('added_edges','added_abs_weight','magnitude','repair_cpu_seconds','audit_cpu_seconds'):
            assert not np.any(d[key][1:]),key


def test_zero_primary_fails_despite_positive_terminal_and_tamper(tmp_path):
    cfg=read(ROOT/'config.json')
    for b in cfg['blocks']:
        good=np.zeros((18,3,16),bool);opposite=np.zeros_like(good)
        good[:,0,:12]=True;good[:,1:,:14]=True
        good[1:,1,:15]=True;good[1:,2,:]=True;opposite[0,1:,15]=True
        ports=np.zeros((18,3,16,2,2))
        for gi in range(18):
            for v in range(3):
                for case in range(16):
                    coefficient=.5 if good[gi,v,case] else -.5 if opposite[gi,v,case] else 0.
                    rule=1 if case//4%2==0 else -1
                    ports[gi,v,case]=coefficient*rule*np.array([[1.,-1.],[-1.,1.]])
        windows=np.repeat(ports[:,None],32,axis=1);ports=windows.mean(axis=1)
        applied=np.array([np.repeat(np.array([False,g==15,True])[:,None],16,axis=1) for g in cfg['generations']])
        noise=np.array([[0.,0.,4194304.,4194304.,0.,4194304.]])
        d=dict(block=np.array(b),history=np.array(cfg['history_by_block'][str(b)]),
            mean_ports=ports,port_windows=windows,**serial.score(ports),applied=applied,
            missing_edges=np.ones((18,3,16),int),added_edges=applied.astype(int),added_abs_weight=applied*.5,
            magnitude=applied*.5,repair_cpu_seconds=applied*.001,audit_cpu_seconds=applied*.002,
            new_arm_renewal_cpu_seconds=np.full(18,.01),available_edges=np.full((18,3,16),400),
            fallback_edges=np.zeros((18,3,16),int),returning_edges=np.full((18,3,16),80),
            returning_fallback_edges=np.zeros((18,3,16),int),noise_moments=np.repeat(noise[None],18,axis=0))
        save_arrays(tmp_path/f'continuation_{b:06d}.npz',d)
    a=analyze(tmp_path,cfg)
    assert a['contrasts']['repeated_minus_one_time']['uninterrupted']['mean']==0
    assert a['contrasts']['repeated_minus_one_time']['terminal']['mean']==.0625
    assert a['contrasts']['one_time_minus_baseline']['uninterrupted']['mean']==.125
    assert a['resources']['one_time']['repair_calls']==256
    assert a['resources']['repeated']['execution_origin']=='reused_previous_run'
    assert not a['primary_direction_observed']
    assert verify(tmp_path,cfg,scientific=False)['status']=='PASS'
    render(tmp_path,cfg);assert 'The primary directional forecast failed.' in (tmp_path/'REPORT.md').read_text()
    a['primary_direction_observed']=True;(tmp_path/'analysis.json').write_text(json.dumps(a))
    with pytest.raises(AssertionError):verify(tmp_path,cfg,scientific=False)
    a['primary_direction_observed']=False;(tmp_path/'analysis.json').write_text(json.dumps(a,indent=2)+'\n')
