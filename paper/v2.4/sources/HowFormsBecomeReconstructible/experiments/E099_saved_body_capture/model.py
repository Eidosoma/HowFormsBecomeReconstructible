"""Capture-only interventions, unchanged E077 terminal equations."""
import numpy as np
from E077_fresh_reconstruction_tradeoff import model as old
from E099_saved_body_capture.plan import references

base,reader,P = old.base,old.reader,old.P
AXES=(-3,-2,-1)


def intervene(writer,pruning,cfg):
    physical=reader.surviving_edges(writer['masks'])
    captured,ordinary,contrast,fallback=old.capture(writer['end'],physical,cfg['writer_beta'])
    assert base.encode(captured).tobytes()==writer['outgoing'].tobytes()
    for k,v in (('ordinary',ordinary),('contrast',contrast),('fallback',fallback)):
        assert v.tobytes()==writer[k].tobytes(),k
    x=np.tanh(cfg['writer_beta']*writer['end']); m=(x[...,0,:,:]+x[...,1,:,:])/2
    mean_product=np.stack((m*np.roll(m,-1,-1),m*np.roll(m,-1,-2)),axis=-3)
    assert mean_product.tobytes()==writer['cue_independent'].tobytes()
    np.testing.assert_allclose(ordinary,mean_product+contrast,rtol=0,atol=5e-16)
    w=base.decode(writer['outgoing']); e=pruning['eligible']
    o=np.where(physical,ordinary,0.)
    e18=np.concatenate((e,e,np.zeros_like(e[:1]),e,e,np.zeros_like(e[:1])))
    assert np.array_equal((w!=0)[e18],(o!=0)[e18]),'Selected support mismatch'
    # The paired pruned writer's H and O are identical on this selection.
    assert w[4:8][e].tobytes()==o[4:8][e].tobytes(),'Paired pruned alias failed'
    extra=[]
    for start in (0,9,13):
        v=w[start:start+4].copy(); v[e]=o[start:start+4][e]; extra.append(v)
    for signs,magnitudes in ((w[13:17],o[13:17]),(o[13:17],w[13:17])):
        v=w[13:17].copy(); v[e]=np.copysign(abs(magnitudes[e]),signs[e]); extra.append(v)
    packets=base.encode(np.concatenate((w,*extra)))
    selected=np.concatenate((e18,*([e]*5)))
    return dict(packets=packets,eligible=selected,physical=physical,capture_hybrid=captured,
        capture_ordinary=ordinary,capture_contrast=contrast,capture_fallback=fallback,mean_product=mean_product)


def diagnostics(inter,fresh):
    w=base.decode(inter['packets']); e=inter['eligible']; natural,ordinary=references()
    d,k=old.coupling(w); count=e.sum(axis=AXES)
    result=dict(eligible_edges=count,no_eligible_edges=count==0,edges=(w!=0).sum(axis=AXES),
        selected_present=((w!=0)&e).sum(axis=AXES),selected_weight_mass=(abs(w)*e).sum(axis=AXES),
        weight_mass=abs(w).sum(axis=AXES))
    for name,ref in (('natural',natural),('ordinary',ordinary)):
        shared=(w!=0)&(w[ref]!=0)
        result[name+'_sign_changes']=(shared&(np.signbit(w)!=np.signbit(w[ref]))).sum(axis=AXES)
        result[name+'_support_gained']=((w!=0)&(w[ref]==0)).sum(axis=AXES)
        result[name+'_support_lost']=((w==0)&(w[ref]!=0)).sum(axis=AXES)
        result[name+'_selected_weight_l1']=(abs(w-w[ref])*e).sum(axis=AXES)
    for prefix,dd,kk in (('',d,k),('postinjury_',fresh['denominator'],fresh['coupling'])):
        result[prefix+'selected_coupling_share']=old.fraction((abs(kk)*old.directed(e)).sum(axis=AXES),abs(kk).sum(axis=AXES))
        result[prefix+'denominator_mean']=dd.mean(axis=(-2,-1))
        result[prefix+'isolated_fraction']=(dd==0).mean(axis=(-2,-1))
        for name,ref in (('natural',natural),('ordinary',ordinary)):
            result[prefix+name+'_coupling_l1']=abs(kk-kk[ref]).sum(axis=AXES)/256
            result[prefix+name+'_unsigned_coupling_l1']=abs(abs(kk)-abs(kk[ref])).sum(axis=AXES)/256
    surviving=e&reader.surviving_edges(fresh['masks'])
    result['no_surviving_selected']=~((w!=0)&surviving).any(axis=AXES)
    return result,dict(packets=inter['packets'].copy(),denominator=d,coupling=k)


def checks(inter,fresh,cases,coupling):
    w=base.decode(inter['packets']); e=inter['eligible']; natural,ordinary=references()
    assert w.shape[0]==38 and inter['packets'].shape[-1]==4096
    assert w[~e].tobytes()==w[natural][~e].tobytes()
    assert np.array_equal(w!=0,w[natural]!=0)
    assert not w[np.broadcast_to(~inter['physical'],w.shape)].any()
    for left,right in ((26,30),(13,34)):
        assert abs(w[left:left+4]).tobytes()==abs(w[right:right+4]).tobytes()
        for source in (coupling,fresh):
            assert source['denominator'][left:left+4].tobytes()==source['denominator'][right:right+4].tobytes()
            assert abs(source['coupling'][left:left+4]).tobytes()==abs(source['coupling'][right:right+4]).tobytes()
    for left,right in ((26,34),(30,13)):
        assert np.array_equal(np.signbit(w[left:left+4]),np.signbit(w[right:right+4]))
    for v in (coupling,fresh):
        np.testing.assert_allclose(abs(v['coupling']).sum(axis=-3),(v['denominator']>0).astype(float),rtol=0,atol=4e-15)
    empty=~(e&reader.surviving_edges(fresh['masks'])).any(axis=AXES)
    assert fresh['end'][empty].tobytes()==fresh['end'][natural][empty].tobytes()
    for slot in (8,17):
        for f in (0,2):
            assert inter['packets'][slot,f].tobytes()==inter['packets'][slot,f+1].tobytes()
            assert fresh['end'][slot,f].tobytes()==fresh['end'][slot,f+1].tobytes()
            assert not (cases['both'][slot,f]&cases['both'][slot,f+1]).any()
    assert (fresh['masks'].sum((-2,-1))==24).all() and not fresh['masks'][...,P.any(axis=0)].any()
    assert np.array_equal(cases['both'],cases['minimum_margin']>.25)
    return dict(outside_bytes_preserved=True,support_preserved=True,sign_only_denominators_exact=True,
        sign_only_absolute_coupling_exact=True,magnitude_only_signs_exact=True,empty_selection_aliases_exact=True,
        erased_aliases_verified=True,natural_normalization_verified=True,strict_success_verified=True)
