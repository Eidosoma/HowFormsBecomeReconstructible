import copy
import json
import numpy as np
import pytest
import serial
import audit_reader
import lineage_dynamics as dynamics
from common import ROOT,read,arrays,equal,save_arrays
from audit_serial import masks,audit_prepared,audit_noise
from analyze import analyze,render
from verify import verify


def test_noise_variance_pairing_and_flat_dynamics():
    cfg=copy.deepcopy(read(ROOT/'config.json'))
    # Exactly centered, unit-variance, orthogonal innovation vectors.
    z=np.tile([-1.,-1.,1.,1.],512).reshape(2,4,16,16)
    e=np.tile([-1.,1.,-1.,1.],512).reshape(2,4,16,16)
    draw,moments=serial.noise_pair(z,e,cfg['correlations'])
    for ni,rho in enumerate(cfg['correlations']):
        equal(draw[2*ni],draw[2*ni+1],'policy noise pairing')
        p,m,pp,mm,pm,n=moments[ni]
        np.testing.assert_allclose([p/n,m/n,pp/n,mm/n,pm/n],[0,0,1,1,rho],rtol=0,atol=1e-14)
    equal(draw[0,:,:,0],draw[0,:,:,1],'matched noise identity')
    equal(draw[4,:,:,1],dynamics.paired_founders(e),'independent forcing')
    cfg['cycle']['read_steps']=16;cfg['cycle']['settling_steps']=8
    cfg['development_config']['observe_steps']=4;cfg['reader']['observe_steps']=4
    cfg['budgets']=[16];cfg['settling_steps']=8
    identity='synthetic_noise_equations_only';generation=19
    weights=np.ones((6,16,2,16,16));weights[1,:,0,0,0]=-1.
    packets=dynamics.encode(weights)
    raw=serial.rebuild(packets,np.zeros((16,16,16),bool),identity,generation,cfg)
    equal(masks(identity,generation),raw['masks'],'independent injury')
    for founder,recipient in [(0,0),(3,2)]:
        case=founder*4+recipient
        audit=audit_reader.replay(packets[:,case],raw['masks'][case],founder,recipient,identity,0,cfg,original=True,generation=generation)
        for k in ('end','mean_ports'):equal(raw[k][:,case],audit[k][0],k)
        equal(raw['port_windows'][:,:,case],audit['port_windows'][0],'windows')
    np.testing.assert_allclose(raw['noise_moments'],audit_noise(identity,generation,cfg),rtol=1e-13,atol=1e-8)


def test_known_repairs_and_corruption():
    cfg=read(ROOT/'config.json');known=arrays(ROOT/'sources/native_controls.npz')
    incoming=np.repeat(known['outgoing'].reshape(1,16,4096),6,axis=0)
    prepared,details=serial.prepare(incoming,34000,15,cfg)
    checkcfg=copy.deepcopy(cfg);checkcfg['generations']=[15]
    d={k:np.asarray(v)[None] for k,v in details.items()}
    d.update(incoming=incoming[None],prepared=prepared[None])
    assert audit_prepared(d,34000,checkcfg)==48
    equal(prepared[1],prepared[3],'initial repair identity')
    d['prepared']=d['prepared'].copy();d['prepared'][0,5,0,17]^=1
    with pytest.raises(AssertionError):audit_prepared(d,34000,checkcfg)
    zero=np.zeros((2,16,16));repaired,_,m=serial.recipient_repair(zero,cfg['optimizer'])
    equal(repaired,zero,'erased record unchanged');assert m==0


def test_own_successor_and_repair_schedule(monkeypatch):
    cfg=copy.deepcopy(read(ROOT/'config.json'));cfg['generations']=[15,16,17]
    def cheap_repair(w,options):
        result=w.copy();result[w==0]=1.
        sol=dict(signs=np.ones((16,16),np.int8),candidate_costs=np.zeros(32),flips=np.zeros(16,int),
                 final_improvable_nodes=np.zeros(16,int),cost=0.,initial_cost=0.,winner=0,sweeps=1,selected_improvable_nodes=0)
        return result,sol,1.
    monkeypatch.setattr(serial,'recipient_repair',cheap_repair)
    def fake(packets,previous_mask,identity,generation,configuration):
        weights=np.ones((6,16,2,16,16))
        for v in range(6):weights[v]*=(v+generation)
        weights[:,:,0,0,0]=0
        return dict(outgoing=dynamics.encode(weights),end=np.zeros((6,16,2,16,16)),
                    mean_ports=np.zeros((6,16,2,2)),masks=np.zeros((16,16,16),bool))
    initial=dynamics.encode(np.ones((16,2,16,16)))
    d=serial.continue_block(initial,np.zeros((16,16,16),bool),81000,cfg,False,fake)
    equal(d['incoming'][1:],d['outgoing'][:-1],'own successor')
    for v in (0,2,4):equal(d['prepared'][:,v],d['incoming'][:,v],'baseline unchanged')
    for v in (1,3,5):assert not np.array_equal(d['prepared'][1,v],d['incoming'][1,v])
    assert not np.array_equal(d['incoming'][1,1],d['incoming'][1,3])
    assert d['applied'].sum()==144


def test_baseline_catchup_failed_primary_and_tamper(tmp_path):
    cfg=read(ROOT/'config.json')
    for b in cfg['blocks']:
        good=np.zeros((18,6,16),bool);opposite=np.zeros_like(good)
        for v,count in enumerate([12,14,13,14,15,14]):good[:,v,:count]=True
        good[1:,5,:]=True;opposite[0,5,15]=True
        ports=np.zeros((18,6,16,2,2))
        for gi in range(18):
            for v in range(6):
                for case in range(16):
                    coefficient=.5 if good[gi,v,case] else -.5 if opposite[gi,v,case] else 0.
                    rule=1 if case//4%2==0 else -1
                    ports[gi,v,case]=coefficient*rule*np.array([[1.,-1.],[-1.,1.]])
        windows=np.repeat(ports[:,None],32,axis=1);ports=windows.mean(axis=1)
        applied=np.array([np.repeat(serial.schedule(g)[:,None],16,axis=1) for g in cfg['generations']])
        noise=np.array([[0.,0.,4194304.,4194304.,rho*4194304.,4194304.] for rho in cfg['correlations']])
        d=dict(block=np.array(b),history=np.array(cfg['history_by_block'][str(b)]),
            mean_ports=ports,port_windows=windows,**serial.score(ports),applied=applied,
            missing_edges=np.ones((18,6,16),int),added_edges=applied.astype(int),
            added_abs_weight=applied*.5,magnitude=applied*.5,repair_cpu_seconds=applied*.001,
            audit_cpu_seconds=applied*.002,renewal_cpu_seconds=np.full(18,.01),
            available_edges=np.full((18,6,16),400),fallback_edges=np.full((18,6,16),50),
            returning_edges=np.full((18,6,16),80),returning_fallback_edges=np.full((18,6,16),20),
            noise_moments=np.repeat(noise[None],18,axis=0))
        save_arrays(tmp_path/f'continuation_{b:06d}.npz',d)
    a=analyze(tmp_path,cfg)
    assert a['contrasts'][cfg['primary_contrast']]['uninterrupted']['mean']==-.0625
    assert a['contrasts'][cfg['primary_contrast']]['terminal']['mean']==.0625
    assert a['contrasts']['noise_0_repeated_minus_matched']['uninterrupted']['mean']==0
    assert a['contrasts']['noise_0_baseline_minus_matched']['uninterrupted']['mean']==.1875
    assert a['contrasts']['noise_0_gain_minus_matched']['uninterrupted']['mean']==-.1875
    assert not a['primary_direction_observed']
    assert verify(tmp_path,cfg,scientific=False)['status']=='PASS'
    render(tmp_path,cfg);assert 'The primary directional forecast failed.' in (tmp_path/'REPORT.md').read_text()
    a['primary_direction_observed']=True;(tmp_path/'analysis.json').write_text(json.dumps(a))
    with pytest.raises(AssertionError):verify(tmp_path,cfg,scientific=False)
    a['primary_direction_observed']=False;(tmp_path/'analysis.json').write_text(json.dumps(a,indent=2)+'\n')
