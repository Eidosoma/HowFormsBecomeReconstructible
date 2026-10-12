import copy
import json
import numpy as np
import pytest
import serial
import policy
import warning
import audit_warning
import audit_reader
import lineage_dynamics as dynamics
from common import ROOT,read,arrays,equal,save_arrays
from audit_serial import masks,audit_noise
from audit_policy import audit_policy
from analyze import analyze,render
from verify import verify


def test_features_flat_audit_sign_inversion_and_degenerate_packets():
    rng=np.random.default_rng(108);w=rng.normal(size=(16,2,16,16));w[rng.random(w.shape)<.3]=0
    w[0]=0;packets=dynamics.encode(w)
    x=warning.features(packets)
    np.testing.assert_allclose(x,audit_warning.features(packets),rtol=2e-13,atol=2e-15)
    assert x[0].tolist()==[1.,1.,1.,0.,0.,0.]
    # Gauge inversion away from the input pins preserves unsigned statistics.
    signs=rng.choice([-1.,1.],(16,16,16));signs[:,7:9,1:3]=1.
    edge=np.stack((signs*np.roll(signs,-1,-1),signs*np.roll(signs,-1,-2)),axis=1)
    changed=warning.features(dynamics.encode(w*edge))
    equal(x[:,:5],changed[:,:5],'unsigned features do not see edge signs')
    assert not np.array_equal(x[:,5],changed[:,5])


def test_policies_exact_quotas_and_independent_audit_with_corruption():
    cfg=read(ROOT/'config.json');model=read(ROOT/'development/MODEL.json')
    rng=np.random.default_rng(208);spent=np.zeros((4,16),int);collected={}
    for g in cfg['generations']:
        w=rng.normal(size=(4,16,2,16,16));w[rng.random(w.shape)<.3]=0
        if g%3==0:w[0,:8]=0
        incoming=dynamics.encode(w)
        applied,detail=policy.select(incoming,spent,82000,g,cfg,model)
        # Other arms and outcome histories are inaccessible to the warning decision.
        altered=incoming.copy();altered[1:]=0
        comparison,_=policy.select(altered,spent,82000,g,cfg,model)
        equal(applied,comparison,'no cross-arm information')
        for k,v in dict(incoming=incoming,applied=applied,**detail).items():collected.setdefault(k,[]).append(v.copy())
        spent+=applied
    d={k:np.stack(v) for k,v in collected.items()}
    equal(spent,np.repeat(np.array([9,9,9,18])[:,None],16,axis=1),'fixed call budgets')
    audit_policy(d,82000,cfg,model)
    d['applied'][8,0,3]=~d['applied'][8,0,3]
    with pytest.raises(AssertionError):audit_policy(d,82000,cfg,model)


def test_four_policy_independent_noise_and_flat_dynamics():
    cfg=copy.deepcopy(read(ROOT/'config.json'))
    z=np.tile([-1.,-1.,1.,1.],512).reshape(2,4,16,16)
    e=np.tile([-1.,1.,-1.,1.],512).reshape(2,4,16,16)
    draws,moments=serial.noise_pair(z,e,[0.])
    for v in range(4):
        equal(draws[v,:,:,0],dynamics.paired_founders(z),'base forcing')
        equal(draws[v,:,:,1],dynamics.paired_founders(e),'independent forcing')
    np.testing.assert_array_equal(moments[0]/z.size,[0,0,1,1,0,1])
    cfg['cycle']['read_steps']=16;cfg['cycle']['settling_steps']=8
    cfg['development_config']['observe_steps']=4;cfg['reader']['observe_steps']=4
    cfg['budgets']=[16];cfg['settling_steps']=8
    identity='synthetic_p08_equations_only';generation=19
    weights=np.ones((4,16,2,16,16));weights[:,:,0,0,0]=-1.
    weights[2,:,:,4:6]=0;packets=dynamics.encode(weights)
    raw=serial.rebuild(packets,np.zeros((16,16,16),bool),identity,generation,cfg)
    equal(masks(identity,generation),raw['masks'],'independent injury')
    for founder,recipient in [(0,0),(3,2)]:
        case=founder*4+recipient
        flat=audit_reader.replay(packets[:,case],raw['masks'][case],founder,recipient,identity,0,cfg,
            original=True,generation=generation,rhos=[0.]*4)
        for key in ('end','mean_ports'):equal(raw[key][:,case],flat[key][0],key)
        equal(raw['port_windows'][:,:,case],flat['port_windows'][0],'windows')
    np.testing.assert_allclose(raw['noise_moments'],audit_noise(identity,generation,cfg),rtol=1e-13,atol=1e-8)


def test_repair_preserves_observed_edges_and_untreated_packets():
    cfg=read(ROOT/'config.json');w=np.ones((4,16,2,16,16));w[:,:,0,3:5,5:9]=0
    w[0,0,:,7:10,11]=-1.;packets=dynamics.encode(w);active=np.zeros((4,16),bool);active[0,0]=True
    prepared,detail=serial.prepare(packets,active,cfg,independent=True)
    decoded=dynamics.decode(prepared)
    equal(decoded[0,0][w[0,0]!=0],w[0,0][w[0,0]!=0],'observed bytes')
    equal(prepared[~active],packets[~active],'inactive bytes')
    assert detail['independent_optimizer_checks']==1 and detail['added_edges'][0,0]==8
    erased=np.zeros((2,16,16));repaired,_,m=serial.recipient_repair(erased,cfg['optimizer'])
    equal(repaired,erased,'no information from fully erased packet');assert m==0


def test_native_successor_chain_retained_even_after_failure(monkeypatch):
    cfg=read(ROOT/'config.json');model=read(ROOT/'development/MODEL.json');calls=[]
    def cheap_repair(w,options):
        calls.append(True);result=w.copy();result[w==0]=1.
        solution=dict(signs=np.ones((16,16),np.int8),candidate_costs=np.zeros(32),
            flips=np.zeros(16,int),final_improvable_nodes=np.zeros(16,int),
            cost=0.,initial_cost=0.,winner=0,sweeps=1,selected_improvable_nodes=0)
        return result,solution,1.
    monkeypatch.setattr(serial,'recipient_repair',cheap_repair)
    def fake(packets,previous_mask,identity,generation,configuration):
        weights=np.full((4,16,2,16,16),float(generation));weights[:,:,0,0,0]=0
        if generation>15:weights+=np.arange(4)[:,None,None,None,None]
        return dict(outgoing=dynamics.encode(weights),end=np.zeros((4,16,2,16,16)),
            mean_ports=np.zeros((4,16,2,2)),masks=np.zeros((16,16,16),bool))
    initial=dynamics.encode(np.ones((16,2,16,16)))
    d=serial.continue_block(initial,np.zeros((16,16,16),bool),82000,cfg,model,False,fake)
    assert len(calls)==720 and not d['both_pass'].any()
    equal(d['incoming'][1:],d['outgoing'][:-1],'own successor including failed branches')
    equal(d['prepared'][~d['applied']],d['incoming'][~d['applied']],'no hidden inactive correction')


def test_zero_primary_fails_despite_positive_terminal_and_tamper(tmp_path):
    cfg=read(ROOT/'config.json')
    for b in cfg['blocks']:
        good=np.zeros((18,4,16),bool);opposite=np.zeros_like(good)
        good[:,:,:14]=True;good[1:,0,14]=True
        ports=np.zeros((18,4,16,2,2))
        for gi in range(18):
            for v in range(4):
                for case in range(16):
                    coefficient=.5 if good[gi,v,case] else 0.
                    rule=1 if case//4%2==0 else -1
                    ports[gi,v,case]=coefficient*rule*np.array([[1.,-1.],[-1.,1.]])
        windows=np.repeat(ports[:,None],32,axis=1);ports=windows.mean(axis=1)
        applied=np.array([np.repeat(np.array([g%2==1,g%2==1,g%2==1,True])[:,None],16,axis=1) for g in cfg['generations']])
        shape=(18,4,16);noise=np.array([[0.,0.,4194304.,4194304.,0.,4194304.]])
        d=dict(block=np.array(b),history=np.array(cfg['history_by_block'][str(b)]),
            mean_ports=ports,port_windows=windows,**serial.score(ports),applied=applied,
            missing_edges=np.ones(shape,int),added_edges=applied.astype(int),added_abs_weight=applied*.5,
            magnitude=applied*.5,repair_cpu_seconds=applied*.001,audit_cpu_seconds=applied*.002,
            diagnostic_cpu_seconds=np.zeros(shape),warning_reason=np.ones((18,16),int),
            renewal_cpu_seconds=np.full(18,.01),available_edges=np.full(shape,400),
            fallback_edges=np.zeros(shape,int),returning_edges=np.full(shape,80),
            returning_fallback_edges=np.zeros(shape,int),noise_moments=np.repeat(noise[None],18,axis=0))
        save_arrays(tmp_path/f'continuation_{b:06d}.npz',d)
    a=analyze(tmp_path,cfg)
    assert a['contrasts']['warning_minus_periodic']['uninterrupted']['mean']==0
    assert a['contrasts']['warning_minus_periodic']['terminal']['mean']==.0625
    assert a['resources']['warning']['repair_calls']==2304
    assert not a['primary_direction_observed']
    assert verify(tmp_path,cfg,scientific=False)['status']=='PASS'
    render(tmp_path,cfg);assert 'The primary directional forecast failed.' in (tmp_path/'REPORT.md').read_text()
    a['primary_direction_observed']=True;(tmp_path/'analysis.json').write_text(json.dumps(a))
    with pytest.raises(AssertionError):verify(tmp_path,cfg,scientific=False)
