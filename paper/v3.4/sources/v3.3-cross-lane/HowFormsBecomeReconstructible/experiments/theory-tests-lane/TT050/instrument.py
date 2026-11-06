"""Pure trajectory hook: no RNG calls, packet edits, scores or continuation."""
from study import np, native
from interventions import graph, EDGES, PORTS

def traverse(w):
    """Independent adjacency traversal, not the construction union-find."""
    a=[[] for _ in range(256)];degree=np.zeros(256,np.int16)
    for direction,y,x in np.ndindex(2,16,16):
        if w[direction,y,x]==0:continue
        u=16*y+x;v=16*y+(x+1)%16 if direction==0 else 16*((y+1)%16)+x
        a[u].append(v);a[v].append(u);degree[u]+=1;degree[v]+=1
    labels=np.full(256,-1,np.int16)
    for root in range(256):
        if labels[root]>=0:continue
        stack=[root];labels[root]=root
        while stack:
            u=stack.pop()
            for v in a[u]:
                if labels[v]<0:labels[v]=root;stack.append(v)
    reach=np.empty((3,256),bool)
    for p in range(3):
        roots=set(int(labels[c]) for c in np.flatnonzero(PORTS[p]))
        reach[p]=[int(v) in roots for v in labels]
    return degree,labels,reach

def record(packets,reference,eligible,injury=None,writer=None,audit=True):
    w=native.base.decode(packets);ref=native.base.decode(reference)
    assert w.shape==ref.shape and eligible.shape==w.shape
    if injury is None:injury=np.zeros(w.shape[1:3]+(16,16),bool)
    physical=native.reader.surviving_edges(injury)
    live=(~injury)&~native.P.any(axis=0)
    w=w*physical;ref=ref*physical
    den,k=native.old.coupling(w);refden,_=native.old.coupling(ref)
    shape=w.shape[:3];degree=np.empty((*shape,16,16),np.int16);labels=np.empty_like(degree)
    reach=np.empty((*shape,3,16,16),bool)
    for loc in np.ndindex(shape):
        g=graph(w[loc]);degree[loc]=g[0].reshape(16,16);labels[loc]=g[1].reshape(16,16)
        reach[loc]=g[2].reshape(3,16,16)
        if audit:
            h=traverse(w[loc])
            for x,y in zip(g,h):assert x.tobytes()==y.tobytes(),'graph traversal'
    if audit:
        d2,k2=native.independent.legacy.coupling(w)
        assert den.tobytes()==d2.tobytes() and k.tobytes()==k2.tobytes(),'normalized coupling'
    newly=(refden>0)&(den==0)&live[None]
    arrays=dict(degree=degree,component=labels,port_reachable=reach,
        denominator=den,coupling=k,reference_denominator=refden,
        newly_isolated=newly,live_nonport=np.broadcast_to(live,den.shape).copy(),
        eligible=eligible.copy(),available_selected=eligible&physical,
        isolated_live=(den==0)&live[None],
        selected_coupling_share=native.old.fraction(
            (abs(k)*native.old.directed(eligible)).sum(axis=(-3,-2,-1)),abs(k).sum(axis=(-3,-2,-1))))
    if writer is not None:
        x=np.tanh(3.*writer['end']);d=(x[:,:,:,0]-x[:,:,:,1])/2
        arrays.update(raw_cue_contrast=(writer['end'][:,:,:,0]-writer['end'][:,:,:,1])/2,
            tanh_cue_contrast=d,edge_contrast=writer['contrast'].copy(),fallback=writer['fallback'].copy(),
            newly_isolated_zero_contrast=newly&(d==0),outgoing_support=native.base.decode(writer['outgoing'])!=0)
        if audit:
            q=np.stack((d*np.roll(d,-1,-1),d*np.roll(d,-1,-2)),axis=-3)
            assert q.tobytes()==arrays['edge_contrast'].tobytes()
            assert ((q==0)&physical).tobytes()==arrays['fallback'].tobytes()
    return arrays

def summarize(arrays):
    out={k:arrays[k].sum(axis=(-2,-1)) for k in ('newly_isolated','isolated_live')}
    out['selected_coupling_share']=arrays['selected_coupling_share']
    out['input_reachable_live']=(arrays['port_reachable'][...,0,:,:]&arrays['live_nonport']).sum(axis=(-2,-1))
    out['output1_from_input']=arrays['port_reachable'][...,0,:,:][...,native.P[1]].sum(axis=-1)
    out['output2_from_input']=arrays['port_reachable'][...,0,:,:][...,native.P[2]].sum(axis=-1)
    if 'fallback' in arrays:
        out['fallback_selected']=(arrays['fallback']&arrays['available_selected']).sum(axis=(-3,-2,-1))
        out['available_selected']=arrays['available_selected'].sum(axis=(-3,-2,-1))
        out['newly_isolated_zero_contrast']=arrays['newly_isolated_zero_contrast'].sum(axis=(-2,-1))
    return out
