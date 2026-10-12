"""Independent equations for extraction, substitutions, reader and diagnostics."""
import hashlib
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from E015_functional_inheritance.audit import random, pair, unpack, pack, ports
from E022_reader_compensation.audit import advance_compensated
from E054_record_interventions.audit_model import coupling, graph_batch, equal, ENDS
import numpy as np

P=ports()


def source(run,block):
    with np.load(run/f'outgoing_{block:06d}.npz',allow_pickle=False) as f: original=f['packets']
    result=np.empty((3,2,2,*original.shape[2:]),np.uint8)
    for t in range(2):
        for condition in range(2): result[:,t,condition]=original[:,2*t+condition]
    return dict(packets=result)


def anchored(w):
    labels=list(range(256)); tree=[[] for _ in range(256)]
    for e,(u,v) in enumerate(ENDS):
        if w.ravel()[e]==0 or labels[u]==labels[v]: continue
        old,new=labels[v],labels[u]
        labels=[new if k==old else k for k in labels]
        sign=-1 if w.ravel()[e]<0 else 1
        tree[u].append((v,sign)); tree[v].append((u,sign))
    result=np.zeros(256,np.int8)
    for anchor in np.flatnonzero(P[0]):
        if result[anchor]!=0: continue
        result[anchor]=1; stack=[anchor]
        while stack:
            u=stack.pop()
            for v,sign in tree[u]:
                if result[v]==0:
                    result[v]=int(result[u])*sign; stack.append(v)
    return result.reshape(16,16)


def anchored_batch(w):
    return np.array([anchored(x) for x in w.reshape(-1,2,16,16)]).reshape(*w.shape[:-3],16,16)


def intervene(packets):
    w=unpack(packets); H,T,_,F,R=w.shape[:5]
    assert np.isfinite(w).all() and w.shape[2]==2
    result=np.empty((H,T,5,F,R,2,16,16))
    for h,t,f,r in np.ndindex(H,T,F,R):
        c,p=w[h,t,0,f,r],w[h,t,1,f,r]
        assert np.array_equal(c!=0,p!=0), 'Source support mismatch'
        result[h,t,0,f,r]=c; result[h,t,1,f,r]=p
        result[h,t,2,f,r]=np.where(p==0,0.,np.where(c<0,-abs(p),abs(p)))
        result[h,t,3,f,r]=np.where(c==0,0.,np.where(p<0,-abs(c),abs(c)))
        result[h,t,4,f,r]=0.
    d,k=coupling(result)
    return dict(packets=pack(result),denominator=d,coupling=k,
                graph=graph_batch(result),anchor=anchored_batch(result))


def masks(block,R):
    available=np.flatnonzero(~P.any(axis=0).ravel()); squares=[]
    for y,x in np.ndindex(16,16):
        a=np.zeros((16,16),bool)
        for dy in (-1,0,1):
            for dx in (-1,0,1): a[(y+dy)%16,(x+dx)%16]=True
        if not (a&P.any(axis=0)).any(): squares.append(a)
    g=random('E015',block,'E056_fresh_reader','damage'); out=np.zeros((2,R,3,16,16),bool)
    for f,r in np.ndindex(2,R):
        out[f,r,1].ravel()[g.choice(available,24,replace=False)]=True
        out[f,r,2]=squares[int(g.integers(len(squares)))]
    return pair(out)


def digest(x):
    return np.frombuffer(hashlib.sha256(np.asarray(x,dtype='<f8').tobytes(order='C')).digest(),dtype=np.uint8)


def assay(packets,block,cfg):
    H,T,A,F,R=packets.shape[:5]; N=H*T*A
    weights=unpack(packets).reshape(N,F,R,2,16,16)
    mask=masks(block,R); edges=np.empty((F,R,3,2,16,16),bool)
    for e,(u,v) in enumerate(ENDS):
        m=mask.reshape(F,R,3,256)
        edges.reshape(F,R,3,512)[...,e]=~m[...,u]&~m[...,v]
    effective=weights[:,:,:,None]*edges[None]
    d,k=coupling(effective); g=random('E056',block,'fresh_reader')
    birth=cfg['birth_sd']*pair(g.standard_normal((2,R,3,16,16)))
    v=np.broadcast_to(birth[None,:,:,None],(N,F,R,2,3,16,16)).copy()
    live=(~mask)[None,:,:,None]; cue=np.array([1.,-1.]).reshape(1,1,1,2,1,1)
    v*=live; v[...,P[0]]=cue; trace=[]; hashes=[]
    for t in range(cfg['read_steps']):
        eta=pair(g.standard_normal((2,R,3,16,16)))[None,:,:,None]
        v=advance_compensated(v,effective[:,:,:,None],d[:,:,:,None],eta,cfg,t>=cfg['settling_steps'])
        v*=live; v[...,P[0]]=cue; hashes.append(digest(v))
        if t>=cfg['read_steps']-cfg['observe_steps']:
            trace.append(np.stack((v[...,P[1]].mean(axis=-1),v[...,P[2]].mean(axis=-1)),axis=-1))
    trace=np.array(trace)
    return dict(masks=mask,effective=effective,denominator=d,coupling=k,birth=birth,end=v,
        late_ports=trace,mean_ports=trace.mean(axis=0),state_hashes=np.array(hashes),
        graph=graph_batch(effective),anchor=anchored_batch(effective))


def score(v,margin):
    m=np.empty(v.shape[:-1]); transfer=np.empty(v.shape[:-2]); rules=(1.,-1.,1.,-1.)
    for f,rule in enumerate(rules):
        for c,cue in enumerate((1.,-1.)):
            m[...,f,:,c]=np.minimum(rule*cue*v[...,f,:,c,0],-rule*cue*v[...,f,:,c,1])
        transfer[...,f,:]=((v[...,f,:,0,0]-v[...,f,:,1,0])-(v[...,f,:,0,1]-v[...,f,:,1,1]))/4
    aligned=transfer.copy()
    for f,rule in enumerate(rules): aligned[...,f,:]*=rule
    return dict(margin=m,minimum_margin=m.min(axis=-1),both=(m>margin).all(axis=-1),transfer=transfer,aligned_transfer=aligned)


def diagnostics(source,inter,fresh,cfg):
    w=unpack(inter['packets']); H,T,A,F,R=w.shape[:5]; ref=w[:,:,:1]
    common=(w!=0)&(ref!=0); axes=(-3,-2,-1)
    result=dict(shared_support=common.sum(axis=axes),
        sign_disagreements=(common&((w<0)!=(ref<0))).sum(axis=axes),
        support_gained=((w!=0)&(ref==0)).sum(axis=axes),support_lost=((w==0)&(ref!=0)).sum(axis=axes),
        coupling_l1=abs(inter['coupling']-inter['coupling'][:,:,:1]).sum(axis=axes)/256,
        denominator_l1=abs(inter['denominator']-inter['denominator'][:,:,:1]).sum(axis=(-2,-1))/256,
        graph=inter['graph'],
        port_alignment=np.stack([inter['anchor'][...,p].mean(axis=-1) for p in P],axis=-1),
        port_unreachable=np.stack([(inter['anchor'][...,p]==0).sum(axis=-1) for p in P],axis=-1))
    values=fresh['mean_ports'].reshape(H,T,A,F,R,2,3,2).transpose(0,1,2,6,3,4,5,7)
    result.update({f'fresh_{k}':v for k,v in score(values,cfg['margin']).items()})
    K=fresh['coupling'].reshape(H,T,A,F,R,3,4,16,16)
    result['postinjury_coupling_l1']=(abs(K-K[:,:,:1]).sum(axis=(-3,-2,-1))/256).transpose(0,1,2,5,3,4)
    original=unpack(source['packets']); c,p=original[:,:,0],original[:,:,1]
    checks=dict(sources_same_support=bool(np.array_equal(c!=0,p!=0)),
        sham_bytes_unchanged=bool(np.array_equal(inter['packets'][:,:,0],source['packets'][:,:,0])),
        pulse_bytes_unchanged=bool(np.array_equal(inter['packets'][:,:,1],source['packets'][:,:,1])),
        hybrid_support_unchanged=all(np.array_equal(w[:,:,a]!=0,c!=0) for a in range(4)),
        sign_restoration_exact=bool(np.array_equal(np.sign(w[:,:,2]),np.sign(c))),
        magnitude_restoration_exact=bool(np.array_equal(abs(w[:,:,3]),abs(c))),
        pulse_magnitudes_preserved=bool(np.array_equal(abs(w[:,:,2]),abs(p))),
        pulse_signs_preserved=bool(np.array_equal(np.sign(w[:,:,3]),np.sign(p))),
        sign_swap_denominators_fixed=bool(np.array_equal(inter['denominator'][:,:,0],inter['denominator'][:,:,3]) and
                                           np.array_equal(inter['denominator'][:,:,1],inter['denominator'][:,:,2])),
        ports_protected=bool(not fresh['masks'][...,P.any(axis=0)].any()),erased_zero=bool(not w[:,:,4].any()))
    end=fresh['end'].reshape(H,T,A,F,R,2,3,16,16)
    trace=fresh['late_ports'].reshape(cfg['observe_steps'],H,T,A,F,R,2,3,2)
    checks['erased_fields_common']=all(np.array_equal(end[h,t,4],end[0,0,4]) for h,t in np.ndindex(H,T))
    checks['erased_traces_common']=all(np.array_equal(trace[:,h,t,4],trace[:,0,0,4]) for h,t in np.ndindex(H,T))
    checks['pass']=all(checks.values())
    return result,checks
