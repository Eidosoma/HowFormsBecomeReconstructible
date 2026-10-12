"""Six branches: fixed repair crossed with three cue-noise correlations."""
import time
import numpy as np
import lineage_dynamics as dynamics
import audit_optimizer
from repair import recipient_repair,edge_signs
from common import equal

DIAGNOSTICS=('signs','candidate_costs','flips','final_improvable_nodes',
             'cost','initial_cost','winner','sweeps','selected_improvable_nodes')


def seed_identity(block,cfg):
    return cfg['continuation_namespace']+':'+str(block)


def schedule(generation):
    return np.array([False,True]*3)


def prepare(incoming,block,generation,cfg,independent=True):
    assert incoming.shape==(6,16,4096)
    weights=dynamics.decode(incoming);prepared=weights.copy();active=schedule(generation)
    fields=dict(applied=np.repeat(active[:,None],16,axis=1),
                missing_edges=(weights==0).sum(axis=(-3,-2,-1)),
                added_edges=np.zeros((6,16),int),added_abs_weight=np.zeros((6,16)),
                magnitude=np.zeros((6,16)),
                repair_cpu_seconds=np.zeros((6,16)),audit_cpu_seconds=np.zeros((6,16)))
    diagnostics={}
    checks=0
    for variant in np.flatnonzero(active):
        for case in range(16):
            w=weights[variant,case];t=time.process_time()
            completed,solution,magnitude=recipient_repair(w,cfg['optimizer'])
            missing=w==0;result=completed
            fields['repair_cpu_seconds'][variant,case]=time.process_time()-t
            if independent:
                t=time.process_time()
                coupling=audit_optimizer.independent_coupling(w)
                other=audit_optimizer.solve(coupling,np.flatnonzero(dynamics.PORTS[0].ravel()),cfg['optimizer'])
                for key in DIAGNOSTICS:
                    if isinstance(solution[key],np.ndarray):equal(solution[key],other[key],key)
                    else:assert solution[key]==other[key],key
                fields['audit_cpu_seconds'][variant,case]=time.process_time()-t;checks+=1
            equal(result[~missing],w[~missing],'observed edges preserved')
            prepared[variant,case]=result
            fields['added_edges'][variant,case]=int((result[missing]!=0).sum())
            fields['added_abs_weight'][variant,case]=float(abs(result[missing]).sum())
            fields['magnitude'][variant,case]=magnitude
            for key in DIAGNOSTICS:
                value=np.asarray(solution[key])
                if key not in diagnostics:
                    diagnostics[key]=np.zeros((6,16)+value.shape,value.dtype)
                diagnostics[key][variant,case]=value
    fields.update({'optimizer_'+k:v for k,v in diagnostics.items()})
    fields['independent_optimizer_checks']=np.array(checks)
    return dynamics.encode(prepared),fields


def noise_pair(z,e,rhos):
    second=[z.copy() if rho==1. else rho*z+np.sqrt(1.-rho*rho)*e for rho in rhos]
    first=dynamics.paired_founders(z)
    draws=np.stack([np.stack((first,dynamics.paired_founders(y)),axis=2) for y in second])
    moments=np.array([[z.sum(),y.sum(),(z*z).sum(),(y*y).sum(),(z*y).sum(),z.size] for y in second])
    return np.repeat(draws,2,axis=0),moments


def mechanism(body,mask,previous_mask,beta):
    x=np.tanh(beta*body);difference=(x[:,:,:,0]-x[:,:,:,1])/2
    contrast=np.stack((difference*np.roll(difference,-1,-1),difference*np.roll(difference,-1,-2)),axis=-3)
    available=dynamics.available_edges(mask)
    returning=previous_mask.reshape(4,4,16,16)&~mask
    incident=np.stack((returning|np.roll(returning,-1,-1),returning|np.roll(returning,-1,-2)),axis=-3)&available
    return dict(available_edges=np.broadcast_to(available,contrast.shape).sum(axis=(-3,-2,-1)).reshape(6,16),
        fallback_edges=((contrast==0)&available).sum(axis=(-3,-2,-1)).reshape(6,16),
        returning_edges=np.broadcast_to(incident,contrast.shape).sum(axis=(-3,-2,-1)).reshape(6,16),
        returning_fallback_edges=((contrast==0)&incident).sum(axis=(-3,-2,-1)).reshape(6,16))


def rebuild(packets,previous_mask,identity,generation,cfg):
    dc,cycle=cfg['development_config'],cfg['cycle']
    assert packets.shape==(6,16,4096)
    shaped=packets.reshape(6,4,4,4096)
    masks=dynamics.damage_masks(identity,f'E022_renewal_g{generation}',4)[:,:,1]
    effective=dynamics.decode(shaped)*dynamics.available_edges(masks)
    denominator=dynamics.incident(abs(effective))
    random=dynamics.stream('E022',identity,'develop',generation)
    innovation=dynamics.stream(cfg['innovation_namespace'],identity,'innovation',generation)
    birth=dc['birth_sd']*dynamics.matched_cues(random.standard_normal((2,4,16,16)))
    innovation.standard_normal((2,4,16,16))  # unused birth innovation, explicit E051 convention
    value=np.repeat(birth[None],6,axis=0)
    alive=(~masks)[None,:,:,None];cue=dynamics.CUES.reshape(1,1,1,2,1)
    value*=alive;value[...,dynamics.PORTS[0]]=cue;late=[];moments=np.zeros((3,6))
    for t in range(cycle['read_steps']):
        noise,sums=noise_pair(random.standard_normal((2,4,16,16)),innovation.standard_normal((2,4,16,16)),cfg['correlations'])
        moments+=sums
        value=dynamics.step(value,effective[:,:,:,None],denominator[:,:,:,None],noise,dc,t>=cycle['settling_steps'])
        value*=alive;value[...,dynamics.PORTS[0]]=cue
        if t>=cycle['read_steps']-dc['observe_steps']:late.append(dynamics.read_ports(value))
    outgoing,_=dynamics.capture(value,masks,['exact_rewrite']*6,dc,cfg['tolerance'])
    windows=np.stack(late).reshape(dc['observe_steps'],6,16,2,2)
    return dict(masks=masks.reshape(16,16,16),birth=birth.reshape(16,2,16,16),
        end=value.reshape(6,16,2,16,16),outgoing=outgoing.reshape(6,16,4096),
        port_windows=windows,mean_ports=windows.mean(axis=0),noise_moments=moments,
        **mechanism(value,masks,previous_mask,dc['writer_beta']))


def score(ports,margin=.25):
    # Any leading axes; last dimensions are case, cue, output port.
    target=np.repeat([1.,-1.,1.,-1.],4)[:,None,None]*np.array([[1.,-1.],[-1.,1.]])
    aligned=ports*target
    minimum=aligned.min(axis=(-2,-1));opposite=-aligned.max(axis=(-2,-1))
    return dict(min_margin=minimum,both_pass=minimum>margin,
                opposite_margin=opposite,opposite_pass=opposite>margin)


def continue_block(initial,previous_mask,block,cfg,independent=True,rebuild_function=rebuild):
    assert initial.shape==(16,4096)
    incoming=np.repeat(initial[None],6,axis=0);collected={}
    for generation in cfg['generations']:
        prepared,details=prepare(incoming,block,generation,cfg,independent)
        t=time.process_time();raw=rebuild_function(prepared,previous_mask,seed_identity(block,cfg),generation,cfg)
        elapsed=time.process_time()-t
        if generation==15:
            equal(prepared[0],prepared[2],'initial baseline identity');equal(prepared[0],prepared[4],'initial baseline identity')
            equal(prepared[1],prepared[3],'initial repair identity');equal(prepared[1],prepared[5],'initial repair identity')
        values=dict(generation=np.array(generation),incoming=incoming,prepared=prepared,
                    renewal_cpu_seconds=np.array(elapsed),**raw,**details,**score(raw['mean_ports']))
        for name,value in values.items():collected.setdefault(name,[]).append(value.copy())
        # This is the only record crossing the next boundary. No prior or repaired
        # record substitutes for the actual body-written output.
        incoming=raw['outgoing'];previous_mask=raw['masks']
    return dict(block=np.array(block),history=np.array(cfg['history_by_block'][str(block)]),
                **{k:np.stack(v) for k,v in collected.items()})
