"""Independent capture reconstruction, scalar substitutions and diagnostics."""
import numpy as np
from E077_fresh_reconstruction_tradeoff import audit_model as old

AXES=(-3,-2,-1)


def intervene(writer,pruning,cfg):
    physical=old.alive(writer['masks'])
    captured,ordinary,contrast,fallback=old.capture(writer['end'],physical,cfg['writer_beta'])
    assert old.pack(captured).tobytes()==writer['outgoing'].tobytes()
    for k,v in (('ordinary',ordinary),('contrast',contrast),('fallback',fallback)):
        assert v.tobytes()==writer[k].tobytes(),k
    x=np.tanh(cfg['writer_beta']*writer['end']); product=np.empty_like(ordinary)
    for direction,y,col in np.ndindex(2,16,16):
        yy,xx=(y,(col+1)%16) if direction==0 else ((y+1)%16,col)
        a,b=x[...,y,col],x[...,yy,xx]
        product[...,direction,y,col]=((a[...,0]+a[...,1])/2)*((b[...,0]+b[...,1])/2)
    assert product.tobytes()==writer['cue_independent'].tobytes()
    assert np.max(np.abs(ordinary-product-contrast))<=5e-16
    w=old.unpack(writer['outgoing']); e=pruning['eligible']; result=np.empty((38,*w.shape[1:]))
    eligible=np.zeros(result.shape,bool)
    for slot in range(18):
        result[slot]=w[slot]
        if slot not in (8,17): eligible[slot]=e[slot%9%4]
    for start,donor in ((18,0),(22,9),(26,13),(30,13),(34,13)):
        result[start:start+4]=w[donor:donor+4]; eligible[start:start+4]=e
    for arm,f,r,edge,y,col in np.ndindex(e.shape):
        loc=arm,f,r,edge,y,col
        if not e[loc]: continue
        available=physical[f,r,edge,y,col]
        for source in (0,4,9,13):
            idx=(source+arm,f,r,edge,y,col)
            value=ordinary[idx] if available else 0.
            assert (w[idx]!=0)==(value!=0),'Selected support mismatch'
            if source==4: assert np.float64(value).tobytes()==w[idx].tobytes(),'Paired pruned alias failed'
        for target,source in ((18,0),(22,9),(26,13)):
            result[target+arm,f,r,edge,y,col]=ordinary[source+arm,f,r,edge,y,col] if available else 0.
        h=w[13+arm,f,r,edge,y,col]; o=ordinary[13+arm,f,r,edge,y,col] if available else 0.
        result[30+arm,f,r,edge,y,col]=-abs(o) if np.signbit(h) else abs(o)
        result[34+arm,f,r,edge,y,col]=-abs(h) if np.signbit(o) else abs(h)
    return dict(packets=old.pack(result),eligible=eligible,physical=physical,capture_hybrid=captured,
        capture_ordinary=ordinary,capture_contrast=contrast,capture_fallback=fallback,mean_product=product)


def refs():
    natural=[]; ordinary=[]
    for slot in range(38):
        if slot<18: n=slot
        elif slot<22: n=slot-18
        elif slot<26: n=slot-13
        else: n=13+(slot-26)%4
        natural.append(n)
        if n<4: o=18+n
        elif n<9: o=n
        elif n<13: o=22+n-9
        elif n<17: o=26+n-13
        else: o=17
        ordinary.append(o)
    return natural,ordinary


def diagnostics(inter,fresh):
    w=old.unpack(inter['packets']); e=inter['eligible']; natural,ordinary=refs()
    d,k=old.coupling(w); count=np.count_nonzero(e,axis=AXES)
    result=dict(eligible_edges=count,no_eligible_edges=count==0,edges=np.count_nonzero(w,axis=AXES),
        selected_present=np.count_nonzero((w!=0)&e,axis=AXES),selected_weight_mass=np.where(e,abs(w),0.).sum(axis=AXES),
        weight_mass=np.abs(w).sum(axis=AXES))
    for name,ref in (('natural',natural),('ordinary',ordinary)):
        shared=(w!=0)&(w[ref]!=0)
        result[name+'_sign_changes']=np.count_nonzero(shared&(np.signbit(w)!=np.signbit(w[ref])),axis=AXES)
        result[name+'_support_gained']=np.count_nonzero((w!=0)&(w[ref]==0),axis=AXES)
        result[name+'_support_lost']=np.count_nonzero((w==0)&(w[ref]!=0),axis=AXES)
        result[name+'_selected_weight_l1']=np.where(e,abs(w-w[ref]),0.).sum(axis=AXES)
    for prefix,dd,kk in (('',d,k),('postinjury_',fresh['denominator'],fresh['coupling'])):
        result[prefix+'selected_coupling_share']=old.divide(np.where(old.directions(e),abs(kk),0.).sum(axis=AXES),abs(kk).sum(axis=AXES))
        result[prefix+'denominator_mean']=dd.mean(axis=(-2,-1))
        result[prefix+'isolated_fraction']=np.mean(dd==0,axis=(-2,-1))
        for name,ref in (('natural',natural),('ordinary',ordinary)):
            result[prefix+name+'_coupling_l1']=np.abs(kk-kk[ref]).sum(axis=AXES)/256
            result[prefix+name+'_unsigned_coupling_l1']=np.abs(np.abs(kk)-np.abs(kk[ref])).sum(axis=AXES)/256
    surviving=e&old.alive(fresh['masks'])
    result['no_surviving_selected']=np.count_nonzero((w!=0)&surviving,axis=AXES)==0
    return result,dict(packets=inter['packets'].copy(),denominator=d,coupling=k)
