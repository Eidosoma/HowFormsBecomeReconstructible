"""Independent masks, repair construction, captures and selected flat native reads."""
import hashlib
import json
import math
import numpy as np
import audit_reader
import writer_audit
from common import equal


def masks(identity,generation):
    parts=['E015',identity,f'E022_renewal_g{generation}','damage']
    seed=int.from_bytes(hashlib.sha256(json.dumps(parts,separators=(',',':')).encode()).digest()[:16],'little')
    random=np.random.Generator(np.random.PCG64(seed))
    ports={16*y+x for row,col in ((7,1),(3,10),(11,10))
           for y in range(row,row+2) for x in range(col,col+2)}
    eligible=np.array([i for i in range(256) if i not in ports])
    square_count=sum(not ({16*((y+dy)%16)+(x+dx)%16 for dy in (-1,0,1) for dx in (-1,0,1)} & ports)
                     for y in range(16) for x in range(16))
    result=np.zeros((4,4,16,16),bool)
    for family in range(2):
        for recipient in range(4):
            chosen=random.choice(eligible,24,replace=False)
            result[2*family,recipient].flat[chosen]=True
            result[2*family+1,recipient].flat[chosen]=True
            random.integers(square_count)  # native unused square draw consumes RNG
    return result.reshape(16,16,16)


def audit_prepared(d,block,cfg):
    incoming=np.frombuffer(d['incoming'].tobytes(),'<f8').reshape(-1,4,16,2,16,16)
    prepared=np.frombuffer(d['prepared'].tobytes(),'<f8').reshape(incoming.shape)
    calls=0
    for gi,generation in enumerate(cfg['generations']):
        active=d['applied'][gi]
        for v in range(4):
            for case in range(16):
                w=incoming[gi,v,case];observed=w!=0;missing=~observed
                assert bool(d['applied'][gi,v,case])==active[v,case]
                assert d['missing_edges'][gi,v,case]==int(missing.sum())
                expected=w.copy()
                if active[v,case]:
                    calls+=1
                    absolute=sorted(abs(float(x)) for x in w[observed])
                    n=len(absolute)
                    magnitude=(absolute[n//2] if n%2 else
                               (absolute[n//2-1]+absolute[n//2])/2) if n else 0.
                    assert d['magnitude'][gi,v,case]==magnitude
                    signs=d['optimizer_signs'][gi,v,case]
                    assert set(np.unique(signs))<={-1,1}
                    assert (signs[7:9,1:3]==1).all()
                    edge_signs=np.array([signs[y,x]*signs[yy,xx]
                        for direction in (0,1) for y in range(16) for x in range(16)
                        for yy,xx in [((y,(x+1)%16) if direction==0 else ((y+1)%16,x))]]).reshape(2,16,16)
                    added=edge_signs[missing]
                    if magnitude>0:expected[missing]=magnitude*added
                else:
                    assert d['magnitude'][gi,v,case]==0
                    assert d['repair_cpu_seconds'][gi,v,case]==d['audit_cpu_seconds'][gi,v,case]==0
                    for key in d:
                        if key.startswith('optimizer_'):assert not np.any(d[key][gi,v,case]),key
                equal(expected,prepared[gi,v,case],'scalar prepared packet')
                assert d['added_edges'][gi,v,case]==int((expected[missing]!=0).sum())
                assert d['added_abs_weight'][gi,v,case]==float(abs(expected[missing]).sum())
                assert d['repair_cpu_seconds'][gi,v,case]>=0 and d['audit_cpu_seconds'][gi,v,case]>=0
    return calls


def audit_noise(identity,generation,cfg):
    def random(parts):
        seed=int.from_bytes(hashlib.sha256(json.dumps(parts,separators=(',',':')).encode()).digest()[:16],'little')
        return np.random.Generator(np.random.PCG64(seed))
    steps=cfg['cycle']['read_steps'];shape=(steps+1,2,4,16,16)
    base=random(['E022',identity,'develop',generation]).standard_normal(shape)[1:].reshape(steps,-1)
    independent=random([cfg['innovation_namespace'],identity,'innovation',generation]).standard_normal(shape)[1:].reshape(steps,-1)
    results=[]
    for rho in cfg['correlations']:
        minus=base.copy() if rho==1. else rho*base+np.sqrt(1.-rho*rho)*independent
        terms=np.stack((base.sum(1),minus.sum(1),(base*base).sum(1),(minus*minus).sum(1),
                        (base*minus).sum(1),np.full(steps,base.shape[1])),axis=1)
        results.append(np.cumsum(terms,axis=0)[-1])
    return np.stack(results)


def audit_block(d,initial,previous_mask,block,cfg,model):
    from audit_policy import audit_policy
    G=len(cfg['generations'])
    assert d['incoming'].shape==d['prepared'].shape==d['outgoing'].shape==(G,4,16,4096)
    equal(d['generation'],np.array(cfg['generations']),'generation schedule')
    equal(d['incoming'][0],np.repeat(initial[None],4,axis=0),'initial enrollment')
    equal(d['incoming'][1:],d['outgoing'][:-1],'own written successor')
    audit_policy(d,block,cfg,model)
    for v in range(1,4):
        for key in ('prepared','end','outgoing','mean_ports','min_margin','both_pass','opposite_pass'):
            equal(d[key][0,0],d[key][0,v],'common first repair and read '+key)
    identity=cfg['continuation_namespace']+':'+str(block)
    calls=audit_prepared(d,block,cfg);native_contexts=0
    for gi,generation in enumerate(cfg['generations']):
        mask=masks(identity,generation);equal(mask,d['masks'][gi],'independent damage')
        available=writer_audit.available_edges(mask)
        pair=writer_audit.writer_pair(d['end'][gi],available,cfg['development_config']['writer_beta'],cfg['tolerance'])
        packet=np.ascontiguousarray(pair['exact'],dtype='<f8').view(np.uint8).reshape(4,16,4096)
        equal(packet,d['outgoing'][gi],'independent body capture')
        returning=previous_mask & ~mask
        incident=np.stack((returning|np.roll(returning,-1,-1),returning|np.roll(returning,-1,-2)),axis=-3)&available
        for key,support in [('available_edges',available),('returning_edges',incident)]:
            expected=np.broadcast_to(support,pair['q'].shape).sum(axis=(-3,-2,-1))
            equal(expected,d[key][gi],'eligible edge count '+key)
        for key,support in [('fallback_edges',available),('returning_fallback_edges',incident)]:
            equal(((pair['q']==0)&support).sum(axis=(-3,-2,-1)),d[key][gi],'fallback count '+key)
        np.testing.assert_allclose(d['noise_moments'][gi],audit_noise(identity,generation,cfg),rtol=1e-13,atol=1e-8)
        assert d['noise_moments'][gi,0,5]==cfg['cycle']['read_steps']*2048
        if generation in cfg['native_audit_generations']:
            for case in cfg['native_audit_cases']:
                native=audit_reader.replay(d['prepared'][gi,:,case],mask[case],case//4,case%4,identity,0,cfg,
                    original=True,generation=generation,rhos=[0.]*4)
                equal(native['birth'],d['birth'][gi,case],'independent birth')
                equal(native['end'][0],d['end'][gi,:,case],'independent body')
                equal(native['mean_ports'][0],d['mean_ports'][gi,:,case],'independent means')
                equal(native['port_windows'][0],d['port_windows'][gi,:,:,case],'independent endpoint windows')
                native_contexts+=4
        previous_mask=mask
    assert calls==720
    equal(d['independent_optimizer_checks'],d['applied'].sum(axis=(1,2)),'every optimizer checked')
    return dict(independent_captures=G*4*16,independent_repair_constructions=calls,
        new_independent_optimizer_checks=calls,native_audit_contexts=native_contexts,
        independent_noise_checks=G,independent_policy_decisions=G*4*16)
