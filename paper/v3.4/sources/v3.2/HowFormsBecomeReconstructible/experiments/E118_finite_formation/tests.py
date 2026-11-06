"""Known-answer finite operators, lineage isolation and excluded full genealogy."""
import copy
import json
from pathlib import Path
import sys
import time
import traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from common import cap_cpus,dump,new_run,rng,sha,utc
from E118_finite_formation import model,audit,data,experiment,inference
from E118_finite_formation.plan import HERE,ROOT,REGIMES,settings,parameters
from E118_finite_formation.run import code_paths,inventory
from E116_finite_resolution_pruning import model as finite,audit as finite_audit,dynamics

def unit():
    checks=[];delta=2**-16;stream=rng('E118','tests')
    w=stream.uniform(-1,1,(5,5,4,1,2,16,16))
    special=np.array([-0.,0.,.5*delta,-.5*delta,1.5*delta,-1.5*delta,2.5*delta,-2.5*delta,1e-300,-1e-300])
    w.reshape(5,-1)[:,:len(special)]=special;p=model.base.encode(w)
    q=model.channel(p);data.equal({'p':q},{'p':audit.channel(p)});experiment.commit_check(q)
    expected=np.array([-0.,0.,0.,-0.,2*delta,-2*delta,2*delta,-2*delta,0.,-0.])
    for i,r in enumerate(REGIMES):
        actual=model.base.decode(q)[i].reshape(-1)[:len(special)]
        data.equal({'w':actual},{'w':expected if parameters(r)['grid'] else special})
    checks+=['grid_ties_even_signed_zero_subnormals','identity_channel_and_idempotence']
    state=stream.uniform(-.5,.5,(5,5,4,1,2,16,16));state[:,:,0,:,1]=state[:,:,0,:,0]+1e-7
    masks=np.zeros((4,1,16,16),bool);masks[:,:,5,5]=True
    x=model.capture(p,state,masks,3.);data.equal(x,audit.capture(p,state,masks,3.))
    assert (x['fallback'][1,:,0]&~x['fallback'][0,:,0]).any()
    assert not model.base.decode(x['outgoing'])[...,5,5].any()
    checks+=['exact_and_tolerance_capture_independently_checked','physical_absence_stays_absent']
    tiny=np.full((4,2,16,16),1e-10);tiny[0]=0.;pk=model.base.encode(tiny)
    for floor in (0.,1e-4):
        a=finite.structure(pk,np.zeros((4,16,16),bool),np.full(4,floor))
        b=finite_audit.structure(pk,np.zeros((4,16,16),bool),np.full(4,floor))
        data.equal({str(i):v for i,v in enumerate(a)},{str(i):v for i,v in enumerate(b)})
        assert not a[3][0].any()
        if floor:assert abs(a[3][1]).sum()<.01
    checks+=['positive_floor_attenuates_without_deletion','zero_drive_at_zero_denominator']
    incoming=model.base.encode(np.zeros_like(w));pre=model.base.encode(np.full_like(w,delta/4))
    recovery=dict(incoming=incoming,pre_channel=pre,outgoing=model.channel(pre),fallback=np.ones(w.shape,bool))
    pr=model.prune(recovery);data.equal(pr,audit.prune(recovery));assert pr['selected'].all()
    assert not pr['delivered_selected'][3:].any() and pr['delivered_selected'][:3].all()
    z=copy.deepcopy(recovery);z['fallback'][:]=False
    a=model.prune(z);assert not a['selected'].any()
    data.equal({'a':a['packets'][:,:4]},{'a':a['packets'][:,4:8]})
    checks+=['pre_channel_tags_retain_grid_erased_noops','empty_selections_retained']
    initial=model.base.encode(np.ones((5,2,4,1,2,16,16))*np.arange(1,6)[:,None,None,None,None,None,None]*delta)
    final=model.base.encode(-np.ones((5,2,4,1,2,16,16))*delta*10)
    mixed=model.mixture(initial,final);data.equal(mixed,audit.mixture(initial,final))
    data.equal({'m':abs(model.base.decode(mixed['packets'])[:,2:4])},{'m':abs(model.base.decode(initial))})
    changed=initial.copy();changed[4]=model.base.encode(np.ones((2,4,1,2,16,16))*delta*20)
    data.equal({'a':model.mixture(changed,final)['packets'][:4]},{'a':mixed['packets'][:4]})
    checks.append('mixture_uses_only_own_history')
    cfg=settings('probe');steps=dict(read_steps=32,settling_steps=16)
    packets=model.base.encode(stream.uniform(-1e-5,1e-5,(5,1,4,4,2,16,16)))
    a=model.develop(packets,9000980,cfg['source_config'],steps,'E022',1)
    data.equal(a,audit.develop(packets,9000980,cfg['source_config'],steps,'E022',1))
    checks.append('full_width_all_regime_ancestry_replay')
    pulse=dict(cfg['body'],body_pre_steps=32,pulse_steps=8,observe_steps=8)
    p=np.repeat(packets,2,axis=1);c=dict(cfg['source_config'],observe_steps=8)
    a=model.develop(p,9000980,c,dict(read_steps=40,settling_steps=16),'E055',0,pulse)
    data.equal(a,audit.develop(p,9000980,c,dict(read_steps=40,settling_steps=16),'E055',0,pulse))
    data.equal({'a':a['before'][:,0]},{'a':a['before'][:,1]})
    assert (a['pulse_sites'].sum(axis=(-2,-1))==64).all()
    checks.append('independent_cue_pulse_noise_and_sham_equality')
    # Every strict performance/reversal boundary can veto the conjunction.
    stats={}
    for e,v in zip(inference.ENDPOINTS,(.7,.8,.8,.7)):
        stats['T1F1Q1/'+e+'/both']=dict(mean=v,ci95=[v,v])
        stats['T1F1Q1/'+e+'_minus_reference/both']=dict(mean=0.,ci95=[0.,0.])
    for ep,v in (('pruning0',.1),('pruning1',-.1)):stats['T1F1Q1/'+ep+'/both']=dict(mean=v,ci95=[v,v])
    result=inference.primary(stats);assert result['criterion_met'] and len(result['gates'])==10
    for g in result['gates']:
        s=copy.deepcopy(stats);s[g['statistic']]['ci95']=[g['limit']]*2;assert not inference.primary(s)['criterion_met']
    checks.append('all_ten_unchanged_gates_required_strictly')
    x=np.arange(3*5*6*4,dtype=float).reshape(3,5,6,4);terms=inference.terms(x)
    for i,r in enumerate(REGIMES):
        np.testing.assert_array_equal(terms[r+'/pruning0/both'],x[:,i,1,0]-x[:,i,0,0])
        np.testing.assert_array_equal(terms[r+'/P1_minus_reference/both'],x[:,i,3,0]-x[:,0,3,0])
    checks.append('five_condition_matched_contrasts')
    return checks

if __name__=='__main__':
    cap_cpus(1);(HERE/'analysis').mkdir(exist_ok=True)
    i=1
    while (HERE/f'analysis/tests_attempt_{i:03d}.json').exists():i+=1
    receipt=HERE/f'analysis/tests_attempt_{i:03d}.json';start=time.monotonic()
    run=None
    try:
        data.registry(full=True);resources=inventory(1)
        checks=unit()
        cfg=settings('fixture');cfg['blocks']=[9000980]
        run=new_run(HERE/f'runs/tests_attempt_{i:03d}',code_paths()+[HERE/'SOURCE_DATA.json'],cfg)
        _,_,report=experiment.block('fixture',9000980,cfg,run)
        dump(receipt,dict(status='PASS',utc=utc(),seconds=time.monotonic()-start,checks=checks,
            complete_reference_replay=True,excluded_report=report,resources=resources,
            inputs_sha256={str(p.relative_to(ROOT)):sha(p) for p in code_paths()},registry_sha256=sha(HERE/'SOURCE_DATA.json')))
        print(json.dumps(dict(status='PASS',checks=len(checks),seconds=time.monotonic()-start)))
    except BaseException:
        dump(receipt,dict(status='FAILED',utc=utc(),seconds=time.monotonic()-start,traceback=traceback.format_exc(),
            inputs_sha256={str(p.relative_to(ROOT)):sha(p) for p in code_paths()},automatic_restart=False))
        raise
