"""Three scheduled repair budgets on an exposed cohort; retain own native successors."""
import time
import numpy as np
import lineage_dynamics as dynamics
import audit_optimizer
from repair import recipient_repair
from common import equal


DIAGNOSTICS=('signs','candidate_costs','flips','final_improvable_nodes',
             'cost','initial_cost','winner','sweeps','selected_improvable_nodes')


def seed_identity(block,cfg):
    return cfg['continuation_namespace']+':'+str(block)


def prepare(incoming,active,cfg,independent=True):
    assert incoming.shape==(3,16,4096) and active.shape==(3,16)
    weights=dynamics.decode(incoming);prepared=weights.copy()
    fields=dict(applied=active.copy(),
        missing_edges=(weights==0).sum(axis=(-3,-2,-1)),
        added_edges=np.zeros((3,16),int),added_abs_weight=np.zeros((3,16)),
        magnitude=np.zeros((3,16)),repair_cpu_seconds=np.zeros((3,16)),audit_cpu_seconds=np.zeros((3,16)))
    templates=dict(signs=np.zeros((16,16),np.int8),candidate_costs=np.zeros(32),
        flips=np.zeros(16,int),final_improvable_nodes=np.zeros(16,int),
        cost=np.array(0.),initial_cost=np.array(0.),winner=np.array(0),sweeps=np.array(0),selected_improvable_nodes=np.array(0))
    fields.update({'optimizer_'+key:np.zeros((3,16)+value.shape,value.dtype) for key,value in templates.items()})
    checks=0
    for v in range(3):
        for case in range(16):
            if not active[v,case]:continue
            w=weights[v,case];missing=w==0;t=time.process_time()
            result,solution,magnitude=recipient_repair(w,cfg['optimizer'])
            fields['repair_cpu_seconds'][v,case]=time.process_time()-t
            if independent:
                t=time.process_time()
                other=audit_optimizer.solve(audit_optimizer.independent_coupling(w),
                    np.flatnonzero(dynamics.PORTS[0].ravel()),cfg['optimizer'])
                for key in DIAGNOSTICS:
                    if isinstance(solution[key],np.ndarray):equal(solution[key],other[key],key)
                    else:assert solution[key]==other[key],key
                fields['audit_cpu_seconds'][v,case]=time.process_time()-t;checks+=1
            equal(result[~missing],w[~missing],'observed edges preserved')
            prepared[v,case]=result
            fields['added_edges'][v,case]=int((result[missing]!=0).sum())
            fields['added_abs_weight'][v,case]=float(abs(result[missing]).sum())
            fields['magnitude'][v,case]=magnitude
            for key in DIAGNOSTICS:fields['optimizer_'+key][v,case]=solution[key]
    fields['independent_optimizer_checks']=np.array(checks)
    return dynamics.encode(prepared),fields


def noise_pair(z,e,rhos):
    second=[z.copy() if rho==1. else rho*z+np.sqrt(1.-rho*rho)*e for rho in rhos]
    first=dynamics.paired_founders(z)
    draws=np.repeat(np.stack([np.stack((first,dynamics.paired_founders(y)),axis=2) for y in second]),3,axis=0)
    moments=np.array([[z.sum(),y.sum(),(z*z).sum(),(y*y).sum(),(z*y).sum(),z.size] for y in second])
    assert len(rhos)==1
    return draws,moments


def mechanism(body,mask,previous_mask,beta):
    x=np.tanh(beta*body);difference=(x[:,:,:,0]-x[:,:,:,1])/2
    contrast=np.stack((difference*np.roll(difference,-1,-1),difference*np.roll(difference,-1,-2)),axis=-3)
    available=dynamics.available_edges(mask)
    returning=previous_mask.reshape(4,4,16,16)&~mask
    incident=np.stack((returning|np.roll(returning,-1,-1),returning|np.roll(returning,-1,-2)),axis=-3)&available
    return dict(available_edges=np.broadcast_to(available,contrast.shape).sum(axis=(-3,-2,-1)).reshape(3,16),
        fallback_edges=((contrast==0)&available).sum(axis=(-3,-2,-1)).reshape(3,16),
        returning_edges=np.broadcast_to(incident,contrast.shape).sum(axis=(-3,-2,-1)).reshape(3,16),
        returning_fallback_edges=((contrast==0)&incident).sum(axis=(-3,-2,-1)).reshape(3,16))


def rebuild(packets,previous_mask,identity,generation,cfg):
    dc,cycle=cfg['development_config'],cfg['cycle']
    assert packets.shape==(3,16,4096)
    shaped=packets.reshape(3,4,4,4096)
    masks=dynamics.damage_masks(identity,f'E022_renewal_g{generation}',4)[:,:,1]
    effective=dynamics.decode(shaped)*dynamics.available_edges(masks)
    denominator=dynamics.incident(abs(effective))
    random=dynamics.stream('E022',identity,'develop',generation)
    innovation=dynamics.stream(cfg['innovation_namespace'],identity,'innovation',generation)
    birth=dc['birth_sd']*dynamics.matched_cues(random.standard_normal((2,4,16,16)))
    innovation.standard_normal((2,4,16,16))  # unused birth innovation, explicit E051 convention
    value=np.repeat(birth[None],3,axis=0)
    alive=(~masks)[None,:,:,None];cue=dynamics.CUES.reshape(1,1,1,2,1)
    value*=alive;value[...,dynamics.PORTS[0]]=cue;late=[];moments=np.zeros((1,6))
    for t in range(cycle['read_steps']):
        noise,sums=noise_pair(random.standard_normal((2,4,16,16)),innovation.standard_normal((2,4,16,16)),cfg['correlations'])
        moments+=sums
        value=dynamics.step(value,effective[:,:,:,None],denominator[:,:,:,None],noise,dc,t>=cycle['settling_steps'])
        value*=alive;value[...,dynamics.PORTS[0]]=cue
        if t>=cycle['read_steps']-dc['observe_steps']:late.append(dynamics.read_ports(value))
    outgoing,_=dynamics.capture(value,masks,['exact_rewrite']*3,dc,cfg['tolerance'])
    windows=np.stack(late).reshape(dc['observe_steps'],3,16,2,2)
    return dict(masks=masks.reshape(16,16,16),birth=birth.reshape(16,2,16,16),
        end=value.reshape(3,16,2,16,16),outgoing=outgoing.reshape(3,16,4096),
        port_windows=windows,mean_ports=windows.mean(axis=0),noise_moments=moments,
        **mechanism(value,masks,previous_mask,dc['writer_beta']))


def score(ports,margin=.25):
    # Any leading axes; last dimensions are case, cue, output port.
    target=np.repeat([1.,-1.,1.,-1.],4)[:,None,None]*np.array([[1.,-1.],[-1.,1.]])
    aligned=ports*target
    minimum=aligned.min(axis=(-2,-1));opposite=-aligned.max(axis=(-2,-1))
    return dict(min_margin=minimum,both_pass=minimum>margin,
                opposite_margin=opposite,opposite_pass=opposite>margin)


COMMON_FIELDS=('generation','masks','birth','noise_moments','block','history')
NEW_ONLY_FIELDS=('renewal_cpu_seconds','independent_optimizer_checks')
BRANCH_FIELDS=('incoming','prepared','outgoing','end','mean_ports','min_margin','both_pass','opposite_margin','opposite_pass',
    'applied','missing_edges','added_edges','added_abs_weight','magnitude','repair_cpu_seconds','audit_cpu_seconds',
    'available_edges','fallback_edges','returning_edges','returning_fallback_edges')+tuple('optimizer_'+k for k in DIAGNOSTICS)


def schedule(generation,cfg):
    return np.repeat(np.array([generation in s for s in cfg['repair_generations'][:3]])[:,None],16,axis=1)


def check_first(d,reference):
    for key in BRANCH_FIELDS:
        if key in ('repair_cpu_seconds','audit_cpu_seconds'):continue
        equal(d[key],np.repeat(reference[key][0,0:1],3,axis=0),'exposed first repair/read '+key)
    equal(d['port_windows'],np.repeat(reference['port_windows'][0,:,0:1],3,axis=1),'exposed first windows')


def continue_block(initial,previous_mask,block,cfg,independent=True,rebuild_function=rebuild,reference=None):
    assert initial.shape==(16,4096)
    incoming=np.repeat(initial[None],3,axis=0);spent=np.zeros((3,16),int);collected={}
    for generation in cfg['generations']:
        active=schedule(generation,cfg)
        prepared,details=prepare(incoming,active,cfg,independent)
        t=time.process_time();raw=rebuild_function(prepared,previous_mask,seed_identity(block,cfg),generation,cfg)
        elapsed=time.process_time()-t
        values=dict(generation=np.array(generation),incoming=incoming,prepared=prepared,
            renewal_cpu_seconds=np.array(elapsed),**raw,**details,**score(raw['mean_ports']))
        if generation==15:
            for v in range(1,3):
                for key in ('prepared','end','outgoing','mean_ports','both_pass'):
                    equal(values[key][0],values[key][v],'identical first repair and read '+key)
            if reference is not None:check_first(values,reference)
        for name,value in values.items():collected.setdefault(name,[]).append(value.copy())
        spent+=active;incoming=raw['outgoing'];previous_mask=raw['masks']
    equal(spent,np.broadcast_to(np.array(cfg['repair_budgets'][:3])[:,None],(3,16)).copy(),'exact budgets')
    return dict(block=np.array(block),history=np.array(cfg['history_by_block'][str(block)]),
        **{k:np.stack(v) for k,v in collected.items()})


def assemble(new,controls):
    assert set(controls)==set(new)-set(NEW_ONLY_FIELDS)
    combined={}
    for key,value in new.items():
        if key in NEW_ONLY_FIELDS:combined[key]=value
        elif key in COMMON_FIELDS:
            equal(value,controls[key],'paired streams/identity '+key);combined[key]=value
        elif key=='port_windows':combined[key]=np.concatenate((value,controls[key]),axis=2)
        else:combined[key]=np.concatenate((value,controls[key]),axis=1)
    return combined
