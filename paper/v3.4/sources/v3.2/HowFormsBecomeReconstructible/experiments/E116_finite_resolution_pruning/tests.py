"""Independent numerical tests and byte-exact excluded historical replay."""
import argparse
import copy
import json
from pathlib import Path
import sys
import time
import traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from common import cap_cpus,dump,rng,sha,utc
from E116_finite_resolution_pruning import model,audit,data,dynamics,experiment,inference
from E116_finite_resolution_pruning.plan import HERE,ROOT,TECHNICAL,settings,BODY_FIELDS,REGIMES
from E116_finite_resolution_pruning.run import code_paths,inventory


def unit():
    checks=[];r=rng('E116','numerical_tests');delta=2**-16
    w=r.uniform(-1,1,(9,4,1,2,16,16))
    special=np.array([-0.,0.,.5*delta,-.5*delta,1.5*delta,-1.5*delta,2.5*delta,-2.5*delta,1e-300,-1e-300])
    w.reshape(-1)[:len(special)]=special;packets=model.base.encode(w)
    data.equal(model.quantize(packets,0),packets,'identity bytes')
    q=model.quantize(packets,delta);data.equal(q,audit.quantize(packets,delta),'ties/subnormals')
    data.equal(model.quantize(q,delta),q,'idempotence')
    expected=np.array([-0.,0.,0.,-0.,2*delta,-2*delta,2*delta,-2*delta,0.,-0.])
    data.equal(model.base.decode(q).reshape(-1)[:len(special)],expected,'specified ties')
    checks+=['identity_storage_bytes','grid_ties_even_and_signed_zero','grid_subnormals','grid_idempotence']
    v=r.uniform(-.5,.5,(9,4,1,2,16,16));v[:3,...,1,:,:]=v[:3,...,0,:,:]
    v[3:6,...,1,:,:]=v[3:6,...,0,:,:]+1e-7
    physical=r.random((4,1,2,16,16))>.15
    for tau in (0.,1e-4):experiment.assert_dict(model.capture(v,physical,tau),audit.capture(v,physical,tau))
    a=model.capture(v,physical,0);b=model.capture(v,physical,1e-4)
    assert (b['fallback']&~a['fallback']).any()
    legacy=model.old.capture(v,physical,3.)
    data.equal(a['pre_channel'],model.base.encode(legacy[0]),'exact fallback baseline')
    loc=tuple(np.argwhere((a['contrast']>0)&physical)[0]);tau=float(a['contrast'][loc])
    assert model.capture(v,physical,tau)['fallback'][loc]
    assert not model.capture(v,physical,np.nextafter(tau,0.))['fallback'][loc]
    checks+=['exact_zero_reference_capture','near_zero_tolerance_branch','physical_absence_masked']
    checks.append('fallback_boundary_is_inclusive')
    intact=np.full((4,4,1,2,16,16),delta/4);selected=np.ones_like(intact,dtype=bool)
    pruned=intact.copy();pruned[selected]=0.
    src=dict(packets=model.base.encode(np.concatenate((intact,pruned,np.zeros_like(intact[:1])))),eligible=selected)
    finite=experiment.initial_records(src,delta)
    data.equal(finite[:4],finite[4:8],'rounding-induced pruning noops retained')
    checks.append('selected_coordinates_and_rounding_noops')
    mask=np.zeros((4,16,16),bool);weights=r.uniform(-1,1,(4,2,16,16))*1e-8
    weights[0]=0.;weights[1]*=1e-20
    packet=model.base.encode(weights)
    for floor in (0.,1e-4):
        a=model.structure(packet,mask,np.full(4,floor));b=audit.structure(packet,mask,np.full(4,floor))
        for x,y in zip(a,b):data.equal(x,y,'floor')
        assert not a[3][0].any()
    a=model.structure(packet,mask,np.zeros(4));b=model.structure(packet,mask,np.full(4,1e-4))
    assert abs(b[3][1]).sum()<abs(a[3][1]).sum()*1e-10
    checks+=['zero_denominator_zero_drive','weak_weight_floor_attenuation','independent_normalized_couplings']
    # Identical numeric values but changed floor, recipient or signed-zero bytes are not cache matches.
    z=np.zeros(4096,np.uint8);zneg=model.base.encode(np.full((2,16,16),-0.))
    keys=[dynamics.record_key(p,e,f,rr) for p,e,f,rr in [(z,0.,0,0),(z,1e-4,0,0),(z,0.,0,1),(zneg,0.,0,0)]]
    assert len(set(keys))==4;checks.append('reuse_requires_all_exact_inputs')
    # Inference criterion: each individual gate can veto the conjunction.
    stats={}
    for e,val in zip(inference.ENDPOINTS,(.7,.8,.8,.7)):
        stats['T1F1Q1/'+e+'/both']=dict(mean=val,ci95=[val,val])
        stats['T1F1Q1/'+e+'_minus_reference/both']=dict(mean=0.,ci95=[0.,0.])
    stats['T1F1Q1/pruning0/both']=dict(mean=.1,ci95=[.1,.1])
    stats['T1F1Q1/pruning1/both']=dict(mean=-.1,ci95=[-.1,-.1])
    assert inference.primary(stats)['criterion_met']
    for gate in inference.primary(stats)['gates']:
        fail=copy.deepcopy(stats);fail[gate['statistic']]['ci95']=[gate['limit'],gate['limit']]
        assert not inference.primary(fail)['criterion_met']
    checks.append('every_one_of_ten_gates_required_strictly')
    x=np.zeros((3,8,6,4))
    for i,reg in enumerate(REGIMES):x[:,i]=int(reg['id'][1])*7+int(reg['id'][3])*3+int(reg['id'][5])*2
    terms=inference.terms(x)
    for name,value in [('T',7.),('F',3.),('Q',2.),('TF',0.),('TQ',0.),('FQ',0.),('TFQ',0.)]:
        np.testing.assert_array_equal(terms['factorial_'+name+'/I0/both'],np.full(3,value))
    checks.append('factorial_effects_and_interactions_identified')
    # Full recipient-width streams and sub-batching must give the same numerical state.
    cfg=settings('benchmark');cfg['steps']=dict(read_steps=32,settling_steps=16)
    context=np.array([(f,rr) for f in range(4) for rr in range(4)],np.int64)
    pk=model.base.encode(r.uniform(-1e-4,1e-4,(16,2,16,16)));floors=np.tile([0.,1e-4],8)
    a=model.simulate(pk,floors,context,9000980,cfg,'develop',1)
    experiment.assert_dict(a,audit.simulate(pk,floors,context,9000980,cfg,'develop',1))
    halves=[model.simulate(pk[s],floors[s],context[s],9000980,cfg,'develop',1) for s in (slice(0,7),slice(7,None))]
    for k in BODY_FIELDS:data.equal(a[k],np.concatenate([h[k] for h in halves]),'chunk independence '+k)
    experiment.assert_dict(model.scores(a['mean_ports'],context[:,0]),audit.scores(a['mean_ports'],context[:,0]))
    checks+=['full_recipient_width_independent_steps','chunk_independent_noise_and_outcomes','independent_scalar_scores']
    return checks


def references():
    reports=[]
    for task in TECHNICAL:
        cfg0=data.source_settings('benchmark');cfg=dict(config=cfg0['config'],recipients=1,chunk_records=128,
            steps={k:cfg0['reader'][k] for k in ('read_steps','settling_steps')})
        src=data.source('benchmark',f'source_pruning_{task}.npz')
        rec=data.source('benchmark',f'source_recovery_{task}.npz')
        experiment.assert_dict(src,audit.legacy.intervene(rec))
        writer=data.source('benchmark',f'writer_{task}.npz')
        assays=[data.source('benchmark',f'assay_{task}_r{d}.npz') for d in (0,1)]
        experiment.check_archived(task,src,writer,assays,cfg0)
        allpk=np.concatenate((src['packets'],writer['outgoing']))
        for phase,g,pk,ref,hkey in [('develop',1,src['packets'],writer,'paired_state_hashes')]+[
                (f'E098_terminal_{d}',0,allpk,assays[d],'state_hashes') for d in (0,1)]:
            n,F,R=pk.shape[:3];contexts=np.array([(f,r) for s,f,r in np.ndindex(n,F,R)])
            tick=time.monotonic()
            a=model.simulate(pk.reshape(-1,4096),np.zeros(n*F*R),contexts,task,cfg,phase,g)
            experiment.assert_dict(a,audit.simulate(pk.reshape(-1,4096),np.zeros(n*F*R),contexts,task,cfg,phase,g))
            for k in BODY_FIELDS:
                old=np.moveaxis(ref[k][:,:n],0,3).reshape(n*F*R,32,2,2) if k=='late_ports' else ref[k][:n].reshape(n*F*R,*a[k].shape[1:])
                data.equal(a[k],old,'legacy '+k)
            data.equal(a['state_hashes'],ref[hkey],'every archived step')
            # Exercise the scientific reuse path on excluded records, without rerunning dynamics.
            cache=dynamics.archived_cache(pk,ref)
            reused,work=dynamics.resolve(pk[None],[0.],task,cfg,phase,g,cache,None,'reference')
            assert work['new_records']==0 and work['archive_outcomes']==n*F*R
            for k in BODY_FIELDS:
                data.equal(reused[k].reshape(a[k].shape),a[k],'archive reuse '+k)
            reports.append(dict(task=task,phase=phase,records=n*F*R,steps=cfg['steps']['read_steps'],seconds=time.monotonic()-tick))
            print(f'Exact reference {task} {phase}: PASS',flush=True)
    return reports


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--unit',action='store_true');args=parser.parse_args()
    cap_cpus(1);(HERE/'analysis').mkdir(exist_ok=True);tick=time.monotonic()
    prefix='unit_attempt' if args.unit else 'tests_attempt';i=1
    while (HERE/f'analysis/{prefix}_{i:03d}.json').exists():i+=1
    path=HERE/f'analysis/{prefix}_{i:03d}.json'
    try:
        resource=inventory(1);data.registry(full=True);checks=unit();reports=[] if args.unit else references()
        dump(path,dict(status='PASS',utc=utc(),checks=checks,reference_reports=reports,
            complete_reference_replay=not args.unit,resources=resource,seconds=time.monotonic()-tick,
            inputs_sha256={str(p.relative_to(ROOT)):sha(p) for p in code_paths()},
            registry_sha256=sha(HERE/'SOURCE_DATA.json')))
        print(json.dumps(dict(status='PASS',checks=len(checks),seconds=time.monotonic()-tick)))
    except BaseException:
        dump(path,dict(status='FAILED',utc=utc(),seconds=time.monotonic()-tick,traceback=traceback.format_exc()));raise
