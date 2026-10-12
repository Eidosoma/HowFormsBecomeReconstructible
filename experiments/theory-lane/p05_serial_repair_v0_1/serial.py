"""Four branches with their own body-written successors and fixed repair policy."""
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
    return np.array([False,generation==15,True,True])


def prepare(incoming,block,generation,cfg,independent=True):
    assert incoming.shape==(4,16,4096)
    weights=dynamics.decode(incoming);prepared=weights.copy();active=schedule(generation)
    fields=dict(applied=np.repeat(active[:,None],16,axis=1),
                missing_edges=(weights==0).sum(axis=(-3,-2,-1)),
                added_edges=np.zeros((4,16),int),added_abs_weight=np.zeros((4,16)),
                magnitude=np.zeros((4,16)),shuffle_changes=np.zeros((4,16),int),
                repair_cpu_seconds=np.zeros((4,16)),audit_cpu_seconds=np.zeros((4,16)))
    diagnostics={}
    checks=0
    for variant in np.flatnonzero(active):
        for case in range(16):
            w=weights[variant,case];t=time.process_time()
            completed,solution,magnitude=recipient_repair(w,cfg['optimizer'])
            missing=w==0;result=completed
            if variant==3:
                f,r=divmod(case,4)
                random=dynamics.stream(cfg['shuffle_namespace'],block,generation,f,r)
                order=random.permutation(int(missing.sum()));result=w.copy()
                if magnitude>0:result[missing]=magnitude*edge_signs(solution['signs'])[missing][order]
                fields['shuffle_changes'][variant,case]=int((result[missing]!=completed[missing]).sum())
                equal(abs(result),abs(completed),'shuffle unsigned resource match')
                equal(np.sort(result[missing]),np.sort(completed[missing]),'shuffle signed multiset')
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
                    diagnostics[key]=np.zeros((4,16)+value.shape,value.dtype)
                diagnostics[key][variant,case]=value
    fields.update({'optimizer_'+k:v for k,v in diagnostics.items()})
    fields['independent_optimizer_checks']=np.array(checks)
    return dynamics.encode(prepared),fields


def rebuild(packets,identity,generation,cfg):
    """Native renewal arithmetic, retaining the endpoint windows as audit evidence."""
    dc,cycle=cfg['development_config'],cfg['cycle']
    assert packets.shape==(4,16,4096)
    shaped=packets.reshape(4,4,4,4096)
    masks=dynamics.damage_masks(identity,f'E022_renewal_g{generation}',4)[:,:,1]
    effective=dynamics.decode(shaped)*dynamics.available_edges(masks)
    denominator=dynamics.incident(abs(effective))
    random=dynamics.stream('E022',identity,'develop',generation)
    birth=dc['birth_sd']*dynamics.matched_cues(random.standard_normal((2,4,16,16)))
    value=np.repeat(birth[None],4,axis=0)
    alive=(~masks)[None,:,:,None];cue=dynamics.CUES.reshape(1,1,1,2,1)
    value*=alive;value[...,dynamics.PORTS[0]]=cue;late=[]
    for t in range(cycle['read_steps']):
        noise=dynamics.matched_cues(random.standard_normal((2,4,16,16)))[None]
        value=dynamics.step(value,effective[:,:,:,None],denominator[:,:,:,None],
                            noise,dc,t>=cycle['settling_steps'])
        value*=alive;value[...,dynamics.PORTS[0]]=cue
        if t>=cycle['read_steps']-dc['observe_steps']:late.append(dynamics.read_ports(value))
    outgoing,_=dynamics.capture(value,masks,['exact_rewrite']*4,dc,cfg['tolerance'])
    windows=np.stack(late).reshape(dc['observe_steps'],4,16,2,2)
    return dict(masks=masks.reshape(16,16,16),birth=birth.reshape(16,2,16,16),
                end=value.reshape(4,16,2,16,16),outgoing=outgoing.reshape(4,16,4096),
                port_windows=windows,mean_ports=windows.mean(axis=0))


def score(ports,margin=.25):
    # Any leading axes; last dimensions are case, cue, output port.
    target=np.repeat([1.,-1.,1.,-1.],4)[:,None,None]*np.array([[1.,-1.],[-1.,1.]])
    aligned=ports*target
    minimum=aligned.min(axis=(-2,-1));opposite=-aligned.max(axis=(-2,-1))
    return dict(min_margin=minimum,both_pass=minimum>margin,
                opposite_margin=opposite,opposite_pass=opposite>margin)


def continue_block(initial,block,cfg,independent=True,rebuild_function=rebuild):
    assert initial.shape==(16,4096)
    incoming=np.repeat(initial[None],4,axis=0);collected={}
    for generation in cfg['generations']:
        prepared,details=prepare(incoming,block,generation,cfg,independent)
        t=time.process_time();raw=rebuild_function(prepared,seed_identity(block,cfg),generation,cfg)
        elapsed=time.process_time()-t
        if generation==15:
            for key in ('end','outgoing','mean_ports'):
                equal(raw[key][1],raw[key][2],'one-time and repeated first renewal '+key)
        values=dict(generation=np.array(generation),incoming=incoming,prepared=prepared,
                    renewal_cpu_seconds=np.array(elapsed),**raw,**details,**score(raw['mean_ports']))
        for name,value in values.items():collected.setdefault(name,[]).append(value.copy())
        # This is the only record crossing the next boundary. No prior or repaired
        # record substitutes for the actual body-written output.
        incoming=raw['outgoing']
    return dict(block=np.array(block),history=np.array(cfg['history_by_block'][str(block)]),
                **{k:np.stack(v) for k,v in collected.items()})
