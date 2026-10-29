"""Three fixed policies using the unchanged record-only optimizer and independent audit."""
import math
import time
import numpy as np
import native as n
import optimizer as opt
import optimizer_audit as audit
import repair
import support as s

FIELDS=('signs','candidate_costs','flips','final_improvable_nodes','cost','initial_cost','winner','sweeps','selected_improvable_nodes')


def prepare(incoming,generation,options):
    s.require(incoming.dtype==np.uint8 and incoming.ndim==3 and incoming.shape[0]==3 and incoming.shape[-1]==4096,'Three policies')
    s.require(15<=generation<=32,'Prespecified repair horizon')
    weights=n.decode(incoming);prepared=weights.copy();count=weights.shape[1]
    active=np.array([False,generation==15,True])
    details=dict(applied=np.repeat(active[:,None],count,axis=1),missing_edges=(weights==0).sum(axis=(-2,-1)),
        added_edges=np.zeros((3,count),int),added_abs_weight=np.zeros((3,count)),magnitude=np.zeros((3,count)),
        repair_cpu_seconds=np.zeros((3,count)),audit_cpu_seconds=np.zeros((3,count)))
    diagnostics={};calls=0;maximum=0.
    for policy in range(3):
        if not active[policy]:continue
        for future in range(count):
            w=weights[policy,future];start=time.process_time()
            completed,solution,magnitude=repair.recipient(w,options)
            details['repair_cpu_seconds'][policy,future]=time.process_time()-start
            start=time.process_time()
            coupling=audit.independent_coupling(w.reshape(2,16,16))
            s.equal(coupling.ravel(),opt.coupling(w),'Independent current-record coupling')
            reference=audit.solve(coupling,opt.INPUT_PINS,options)
            for field in FIELDS:
                value=np.asarray(solution[field]);s.equal(value,np.asarray(reference[field]),'Independent optimizer '+field)
                if field not in diagnostics:diagnostics[field]=np.zeros((3,count)+value.shape,value.dtype)
                diagnostics[field][policy,future]=value
            observed=abs(w[w!=0.]);median=float(np.median(observed)) if len(observed) else 0.
            s.require(median==magnitude,'Independent repair magnitude')
            nodes=reference['signs']
            signs=np.stack((nodes*np.roll(nodes,-1,-1),nodes*np.roll(nodes,-1,-2))).reshape(2,256)
            expected=w.copy();missing=w==0.
            if median>0:expected[missing]=median*signs[missing]
            s.equal(completed,expected,'Independent completed record')
            s.equal(completed[~missing],w[~missing],'Observed nonzero edge bytes preserved')
            prepared[policy,future]=completed
            total=float(abs(completed[missing]).sum());scalar=math.fsum(map(abs,map(float,completed[missing])))
            error=abs(total-scalar);s.require(error<=8*np.finfo(float).eps*abs(scalar)+4*np.nextafter(0.,1.),'Repair resource sum')
            maximum=max(maximum,error)
            details['added_edges'][policy,future]=int(np.count_nonzero(completed[missing]))
            details['added_abs_weight'][policy,future]=total;details['magnitude'][policy,future]=magnitude
            details['audit_cpu_seconds'][policy,future]=time.process_time()-start;calls+=1
    details.update({'optimizer_'+k:v for k,v in diagnostics.items()})
    details.update(independent_optimizer_checks=np.array(calls),resource_max_error=np.array(maximum))
    packets=n.encode(prepared)
    for policy in range(3):
        if not active[policy]:s.equal(packets[policy],incoming[policy],'No inactive modification')
    if generation==15:s.equal(packets[1],packets[2],'Common initial repair')
    s.require(calls==count*(2 if generation==15 else 1),'Complete repair call accounting')
    return packets,details
