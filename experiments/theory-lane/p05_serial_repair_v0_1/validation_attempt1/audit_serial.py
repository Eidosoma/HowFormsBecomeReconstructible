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
        active=(False,generation==15,True,True)
        for v in range(4):
            for case in range(16):
                w=incoming[gi,v,case];observed=w!=0;missing=~observed
                assert bool(d['applied'][gi,v,case])==active[v]
                assert d['missing_edges'][gi,v,case]==int(missing.sum())
                expected=w.copy()
                if active[v]:
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
                    if v==3:
                        founder,recipient=divmod(case,4)
                        parts=[cfg['shuffle_namespace'],block,generation,founder,recipient]
                        seed=int.from_bytes(hashlib.sha256(json.dumps(parts,separators=(',',':')).encode()).digest()[:16],'little')
                        rng=np.random.Generator(np.random.PCG64(seed))
                        added=added[rng.permutation(len(added))]
                    if magnitude>0:expected[missing]=magnitude*added
                    coherent=w.copy()
                    if magnitude>0:coherent[missing]=magnitude*edge_signs[missing]
                    assert d['shuffle_changes'][gi,v,case]==(int((expected[missing]!=coherent[missing]).sum()) if v==3 else 0)
                    equal(abs(expected),abs(coherent),'unsigned resource control')
                    equal(np.sort(expected[missing]),np.sort(coherent[missing]),'sign multiset')
                else:
                    assert d['magnitude'][gi,v,case]==0 and d['shuffle_changes'][gi,v,case]==0
                    assert d['repair_cpu_seconds'][gi,v,case]==d['audit_cpu_seconds'][gi,v,case]==0
                equal(expected,prepared[gi,v,case],'scalar prepared packet')
                assert d['added_edges'][gi,v,case]==int((expected[missing]!=0).sum())
                assert d['added_abs_weight'][gi,v,case]==float(abs(expected[missing]).sum())
                assert d['repair_cpu_seconds'][gi,v,case]>=0 and d['audit_cpu_seconds'][gi,v,case]>=0
    return calls


def audit_block(d,initial,block,cfg):
    G=len(cfg['generations'])
    assert d['incoming'].shape==d['prepared'].shape==d['outgoing'].shape==(G,4,16,4096)
    equal(d['generation'],np.array(cfg['generations']),'generation schedule')
    equal(d['incoming'][0],np.repeat(initial[None],4,axis=0),'initial enrollment')
    equal(d['incoming'][1:],d['outgoing'][:-1],'each branch keeps own written successor')
    equal(d['prepared'][0,1],d['prepared'][0,2],'identical initial repair')
    for key in ('end','outgoing','mean_ports'):
        equal(d[key][0,1],d[key][0,2],'identical first renewal '+key)
    equal(d['prepared'][:,0],d['incoming'][:,0],'baseline untouched')
    equal(d['prepared'][1:,1],d['incoming'][1:,1],'one-time schedule')
    identity=cfg['continuation_namespace']+':'+str(block)
    calls=audit_prepared(d,block,cfg);native_contexts=0
    for gi,generation in enumerate(cfg['generations']):
        mask=masks(identity,generation);equal(mask,d['masks'][gi],'independent damage')
        available=writer_audit.available_edges(mask)
        expected=writer_audit.writer_pair(d['end'][gi],available,cfg['development_config']['writer_beta'],cfg['tolerance'])['exact']
        packet=np.ascontiguousarray(expected,dtype='<f8').view(np.uint8).reshape(4,16,4096)
        equal(packet,d['outgoing'][gi],'independent body capture')
        if generation in cfg['native_audit_generations']:
            # Fixed case 0: all four branches, two generations, every block.
            native=audit_reader.replay(d['prepared'][gi,:,0],mask[0],0,0,identity,0,cfg,original=True,generation=generation)
            equal(native['birth'],d['birth'][gi,0],'independent birth')
            equal(native['end'][0],d['end'][gi,:,0],'independent body')
            equal(native['mean_ports'][0],d['mean_ports'][gi,:,0],'independent means')
            equal(native['port_windows'][0],d['port_windows'][gi,:,:,0],'independent endpoint windows')
            native_contexts+=1
    assert calls==int(d['independent_optimizer_checks'].sum())
    assert np.array_equal(d['independent_optimizer_checks'],[48]+[32]*(G-1))
    return dict(independent_captures=G*4*16,independent_repair_constructions=calls,
                native_audit_contexts=native_contexts)
