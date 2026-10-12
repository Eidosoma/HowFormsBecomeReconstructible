"""Independent repair, damage, lineage-chain and acquisition checks."""
import hashlib
import json
import numpy as np
import audit_acquire
import audit_reader
import writer_audit
from common import equal


def rng(parts):
    seed=int.from_bytes(hashlib.sha256(json.dumps(parts,separators=(',',':')).encode()).digest()[:16],'little')
    return np.random.Generator(np.random.PCG64(seed))


def decode(packets):return np.frombuffer(packets.tobytes(),dtype='<f8').reshape(*packets.shape[:-1],2,16,16)


def check_records(data,block,cfg):
    weights=decode(data['packets']);assert weights.shape==(16,4,2,16,16)
    ports=sorted(16*y+x for y0,x0 in ((7,1),(3,10),(11,10)) for y in range(y0,y0+2) for x in range(x0,x0+2))
    inputs=[16*y+x for y in (7,8) for x in (1,2)];eligible=np.array([i for i in range(256) if i not in ports])
    assert data['founders'].tolist()==[f for f in range(4) for _ in range(4)]
    assert data['recipients'].tolist()==list(range(4))*4
    assert data['histories'].tolist()==[cfg['history_by_block'][str(block)]]*16
    for case in range(16):
        o=weights[case,0];nodes=data['optimizer_signs'][case]
        assert np.all(abs(nodes)==1) and np.all(nodes.ravel()[inputs]==1)
        values=sorted(abs(float(x)) for x in o.ravel() if x!=0);n=len(values)
        m=(values[n//2] if n%2 else (values[n//2-1]+values[n//2])/2) if n else 0.
        assert data['imputed_magnitudes'][case]==m
        completed=o.copy();shuffled=o.copy();indices=[];signs=[]
        for axis in (0,1):
            for y in range(16):
                for x in range(16):
                    if o[axis,y,x]!=0:continue
                    yy,xx=(y,(x+1)%16) if axis==0 else ((y+1)%16,x)
                    q=int(nodes[y,x])*int(nodes[yy,xx]);indices.append((axis,y,x));signs.append(q)
                    if m>0:completed[axis,y,x]=m*q
        f,r=divmod(case,4);h=int(data['histories'][case])
        order=rng([cfg['random_namespace'],block,'shuffle',h,f,r]).permutation(len(indices))
        if m>0:
            for coordinate,index in zip(indices,order):shuffled[coordinate]=m*signs[index]
        equal(weights[case,1],completed,'independent completion');equal(weights[case,2],shuffled,'independent shuffle')
        equal(abs(completed),abs(shuffled),'unsigned match')
        equal(np.sort(completed[o==0]),np.sort(shuffled[o==0]),'sign count match')
        assert not weights[case,3].any()
        assert data['missing_edge_counts'][case]==len(indices)
        assert data['added_abs_weight'][case]==abs(completed[o==0]).sum()
        assert data['shuffled_sign_changes'][case]==np.count_nonzero(completed[o==0]!=shuffled[o==0])
        for ri,rep in enumerate(cfg['replicates']):
            chosen=rng([cfg['random_namespace'],block,'injury',rep,f//2,r]).choice(eligible,24,replace=False)
            mask=np.zeros(256,bool);mask[chosen]=True
            equal(mask.reshape(16,16),data['masks'][case,ri],'independent fresh mask')


def check_lineage(acquisition,lineage,block,cfg,dynamics=True):
    seed=cfg['lineage_namespace']+':'+str(block);h=cfg['history_by_block'][str(block)]
    assert int(lineage['block'])==block and int(lineage['history'])==h
    if dynamics:
        other=audit_acquire.teach(seed,cfg['development_config'])
        for name,value in other.items():equal(value,acquisition[name],'flat acquisition '+name)
    first=np.repeat(acquisition['acquired'][:,None],4,axis=1).reshape(16,4096)
    equal(lineage['incoming'][0],first,'initial packet')
    equal(lineage['incoming'][1:],lineage['outgoing'][:-1],'uninterrupted lineage chain')
    assert lineage['writer_codes'].tolist()==[int(g in cfg['tolerance_generations'][h]) for g in range(1,15)]
    from lineage_dynamics import damage_masks
    for gi in range(14):
        # This shared geometry generator is separately checked against native archival masks.
        expected_masks=damage_masks(seed,f'E022_renewal_g{gi+1}',4)[:,:,1].reshape(16,16,16)
        equal(lineage['masks'][gi],expected_masks,'development mask stream')
        pair=writer_audit.writer_pair(lineage['bodies'][gi],writer_audit.available_edges(lineage['masks'][gi]),tolerance=cfg['tolerance'])
        w=pair['tolerance' if lineage['writer_codes'][gi] else 'exact']
        expected=np.ascontiguousarray(w,dtype='<f8').view(np.uint8).reshape(16,4096)
        equal(lineage['outgoing'][gi],expected,'independent capture')
    if dynamics:
        reference=audit_reader.replay(lineage['incoming'][-1,:1],lineage['masks'][-1,0],0,0,seed,0,cfg,original=True,rhos=[1.])
        equal(reference['birth'],lineage['births'][-1,0],'generation 14 reset')
        equal(reference['end'][0,0],lineage['bodies'][-1,0],'generation 14 body')
        equal(reference['mean_ports'][0,0],lineage['mean_ports'][-1,0],'generation 14 output')
