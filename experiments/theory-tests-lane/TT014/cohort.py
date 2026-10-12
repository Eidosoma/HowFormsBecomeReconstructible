"""Fixed cohort identities and checked O-only interventions."""
import math
import time
import numpy as np
import native as n
import optimizer as opt
import optimizer_audit as oa
import repair
import support as s

OPT_FIELDS=['signs','candidate_costs','flips','final_improvable_nodes','cost','initial_cost','winner','sweeps','selected_improvable_nodes']
def identity(block,cfg):
    s.require(block in cfg['blocks'],'No block substitution');return cfg['lineage_namespace']+':'+str(block)
def history(block,cfg):return cfg['history_by_block'][str(block)]
def writer_code(generation,h,cfg):
    s.require(1<=generation<=14 and h in range(4),'Fixed development boundary')
    return int(generation in cfg['tolerance_generations'][h])


def masks(block,cfg):
    founders=np.repeat(np.arange(4),4);recipients=np.tile(np.arange(4),4)
    # Production construction differs from the flat reader's independent mask routine.
    import reader
    allowed=np.flatnonzero(~reader.PORTS.any(axis=0).ravel());values=np.zeros((16,8,16,16),bool)
    for i,(f,r) in enumerate(zip(founders,recipients)):
        for j,rep in enumerate(cfg['replicates']):
            rng=reader.stream(cfg['random_namespace'],int(block),'injury',int(rep),int(f)//2,int(r))
            values[i,j].flat[rng.choice(allowed,24,replace=False)]=True
    s.equal(values,n.fresh_masks(cfg,block,founders,recipients,cfg['replicates']),'Every assessment injury')
    return values


def construct(packets,block,h,cfg):
    s.require(packets.shape==(16,4096) and packets.dtype==np.uint8,'Every fixed-size outgoing record')
    outgoing=n.decode(packets);rows=[];solutions=[];resources=[];primary_time=[];audit_time=[]
    permutations=np.full((16,512),-1,np.int64)
    for case,o in enumerate(outgoing):
        begin=time.process_time();completed,solution,m=repair.recipient(o,cfg['optimizer']);primary_time.append(time.process_time()-begin)
        begin=time.process_time();coupling=oa.independent_coupling(o.reshape(2,16,16))
        s.equal(coupling.ravel(),opt.coupling(o),'Independent coupling')
        reference=oa.solve(coupling,opt.INPUT_PINS,cfg['optimizer'])
        for key in OPT_FIELDS:s.equal(np.asarray(solution[key]),np.asarray(reference[key]),'Independent optimizer '+key)
        observed=[abs(float(x)) for x in o.ravel() if x!=0];median=float(np.median(observed)) if observed else 0.
        s.require(m==median,'Independent imputed median')
        g=reference['signs'];signs=np.stack([g*np.roll(g,-1,axis=axis) for axis in [-1,-2]]).ravel()
        missing=np.flatnonzero(o.ravel()==0);expected=o.copy().ravel()
        for edge in missing:
            if median>0:expected[edge]=median*int(signs[edge])
        s.equal(completed,expected.reshape(2,256),'Independent repaired packet')
        f,r=divmod(case,4);order=n.random_stream(cfg['random_namespace'],int(block),'shuffle',int(h),f,r).permutation(len(missing))
        permutations[case,:len(order)]=order;shuffled=o.copy().ravel()
        if m>0:shuffled[missing]=m*signs[missing][order]
        s.equal(abs(completed),abs(shuffled.reshape(2,256)),'Matched shuffle magnitudes')
        s.equal(np.sort(completed.ravel()[missing]),np.sort(shuffled[missing]),'Matched added-sign multiset')
        for values in [completed.ravel(),shuffled]:s.equal(values[o.ravel()!=0],o.ravel()[o.ravel()!=0],'Observed O weights preserved')
        s.require(sorted(order.tolist())==list(range(len(missing))),'Complete fixed permutation')
        rows.append(np.stack((o,completed,shuffled.reshape(2,256),np.zeros_like(o))));solutions.append(solution)
        resources.append(dict(block=block,case=case,history=h,founder=f,recipient=r,missing_edges=len(missing),imputed_magnitude=m,
            added_abs_weight=math.fsum(abs(float(completed.ravel()[e])) for e in missing),
            shuffled_sign_changes=int(np.count_nonzero(completed.ravel()[missing]!=shuffled[missing])),
            optimizer_cost=solution['cost'],optimizer_sweeps=solution['sweeps'],selected_improvable_nodes=solution['selected_improvable_nodes']))
        audit_time.append(time.process_time()-begin)
    values=dict(block=np.array(block),history=np.array(h),packets=n.encode(np.stack(rows)),
        founders=np.repeat(np.arange(4),4),recipients=np.tile(np.arange(4),4),histories=np.full(16,h),masks=masks(block,cfg),
        replicates=np.array(cfg['replicates']),permutations=permutations,repair_cpu_seconds=np.array(primary_time),audit_cpu_seconds=np.array(audit_time))
    for key in ['missing_edges','imputed_magnitude','added_abs_weight','shuffled_sign_changes']:
        values[key]=np.array([row[key] for row in resources])
    for key in OPT_FIELDS:values['optimizer_'+key]=np.array([row[key] for row in solutions])
    s.equal(values['packets'][:,0],packets,'O input is untouched')
    return values,resources
