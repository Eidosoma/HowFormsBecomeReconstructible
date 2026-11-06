"""Independent scalar-median completion; controls receive history separately."""
import math
import statistics
import numpy as np
import native as n
import optimizer as opt
import support as s


def median_observed(outgoing):
    observed=[abs(float(value)) for value in outgoing.ravel() if value!=0.]
    return float(statistics.median(observed)) if observed else 0.


def recipient(outgoing,options):
    s.require(outgoing.shape==(2,256) and outgoing.dtype==np.float64 and np.isfinite(outgoing).all(),'Finite native outgoing record')
    c=opt.coupling(outgoing);solution=opt.solve(c,opt.INPUT_PINS,options)
    opt.scalar_local_check(solution['signs'],c)
    m=median_observed(outgoing);s.require(math.isfinite(m),'Finite imputation')
    nodes=solution['signs'].ravel();q=nodes[opt.U]*nodes[opt.V]
    repaired=outgoing.copy().ravel()
    for edge,value in enumerate(outgoing.ravel()):
        if value==0. and m>0.:repaired[edge]=m*int(q[edge])
    s.equal(repaired[outgoing.ravel()!=0],outgoing.ravel()[outgoing.ravel()!=0],'Every observed edge preserved')
    return repaired.reshape(2,256),solution,m


def from_saved(case,options):
    """Reference adapter intentionally reads only the outgoing packet slot."""
    return recipient(n.decode(case['packets'][1]),options)


def references(outgoing,incoming,common,mask,solution,m,primary,permutation):
    s.require(outgoing.shape==incoming.shape==common.shape==(2,256),'Reference record shape')
    s.require(common.dtype==bool and mask.dtype==bool and mask.shape==(16,16),'Reference mask types')
    o=outgoing.ravel();i=incoming.ravel();k=common.ravel();injury=mask.ravel()
    nodes=solution['signs'].ravel();q=nodes[opt.U]*nodes[opt.V]
    unavailable=injury[opt.U]|injury[opt.V];full=unavailable&(i!=0)
    s.require(not o[unavailable].any() and np.all(~k|full),'Historical control support')
    missing=np.flatnonzero(o==0);s.require(sorted(map(int,permutation))==list(range(len(missing))),'Exact shuffle permutation')
    records=np.repeat(o[None],9,axis=0);records[0]=i;records[6]=primary.ravel();records[8]=0.
    for edge in range(512):
        if k[edge]:records[2,edge]=abs(float(i[edge]))*int(q[edge])
        if full[edge]:
            records[3,edge]=i[edge];records[4,edge]=abs(float(i[edge]))*int(q[edge]);records[5,edge]=m*int(q[edge])
    if m>0:
        for edge,index in zip(missing,permutation):records[7,edge]=m*int(q[missing[index]])
    for variant in range(2,8):s.equal(records[variant,o!=0],o[o!=0],'Observed weights preserved in reference '+str(variant))
    s.equal(abs(records[3]),abs(records[4]),'Own/completion matched unsigned record')
    s.equal(abs(records[6]),abs(records[7]),'Recipient/shuffle matched unsigned record')
    s.equal(np.sort(records[6,missing]),np.sort(records[7,missing]),'Recipient/shuffle identical added-weight multiset')
    extra=int(np.count_nonzero((o==0)&~unavailable))
    resources=dict(common_edges=int(k.sum()),full_backup_edges=int(full.sum()),recipient_missing_edges=len(missing),
        missing_edges_outside_original_injury=extra,imputed_magnitude=m,
        common_added_abs_weight=math.fsum(abs(float(records[2,e])) for e in missing),
        full_added_abs_weight=math.fsum(abs(float(records[4,e])) for e in missing),
        imputed_support_added_abs_weight=math.fsum(abs(float(records[5,e])) for e in missing),
        recipient_added_abs_weight=math.fsum(abs(float(records[6,e])) for e in missing),
        shuffled_sign_changes=int(np.count_nonzero(records[6,missing]!=records[7,missing])),
        optimizer_cost=solution['cost'],optimizer_sweeps=solution['sweeps'],selected_improvable_nodes=solution['selected_improvable_nodes'])
    return records.reshape(9,2,256),full.reshape(2,16,16),resources
