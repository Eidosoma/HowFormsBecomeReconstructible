"""Independent scalar sign permutation and additional signed diagnostics."""
import numpy as np
from E077_fresh_reconstruction_tradeoff import audit_model as old
from E101_cross_noise_components.audit import diagnostics as baseline_diagnostics

AXES=(-3,-2,-1)


def shuffle_weights(donor,eligible,strata,task):
    out=donor.copy(); maps=np.empty(donor.shape,np.int16)
    for arm,f,r in np.ndindex(donor.shape[:3]):
        v=donor[arm,f,r].reshape(-1); mask=eligible[arm,f,r].reshape(-1); sig=strata[f,r].reshape(-1)
        mapping=list(range(512))
        for z in range(4):
            ids=[i for i in range(512) if mask[i] and v[i]!=0 and sig[i]==z]
            permutation=old.random('E102',task,'selected_sign_permutation',arm,f,r,z).permutation(len(ids))
            for j,target in enumerate(ids): mapping[target]=ids[int(permutation[j])]
        for i,source in enumerate(mapping):
            edge,y,x=np.unravel_index(i,(2,16,16)); value=abs(v[i])
            out[arm,f,r,edge,y,x]=-value if np.signbit(v[source]) else value
            maps[arm,f,r,edge,y,x]=source
    return out,maps


def intervene(saved,task):
    w=old.unpack(saved['packets']); e=saved['eligible'][:4]; R=w.shape[2]
    assert w.shape[0]==18
    for start in (4,8,12):
        assert np.array_equal(e,saved['eligible'][start:start+4]),'Selected-mask mismatch'
        assert w[:4][~e].tobytes()==w[start:start+4][~e].tobytes(),'Outside donor mismatch'
        assert np.array_equal(w[:4]!=0,w[start:start+4]!=0),'Selected support mismatch'
    assert abs(w[8:12]).tobytes()==abs(w[12:16]).tobytes(),'Magnitude donor mismatch'
    assert np.array_equal(np.signbit(w[:4]),np.signbit(w[8:12])),'Sign donor mismatch'
    assert not w[np.broadcast_to(~saved['physical'],w.shape)].any()
    masks=np.array([old.masks(task,R,f'E102_terminal_{d}_injury',0) for d in (0,1)])
    strata=np.zeros((4,R,2,16,16),np.uint8)
    for draw in (0,1):
        live=old.alive(masks[draw])
        for loc in np.ndindex(strata.shape):
            if live[loc]: strata[loc]+=2**draw
    shuffled,mapping=shuffle_weights(w[12:16],e,strata,task)
    output=np.empty(w.shape); eligible=np.zeros(w.shape,bool)
    for group,prior in enumerate((0,8,12)):
        output[group*4:group*4+4]=w[prior:prior+4]
    output[12:16]=shuffled; output[16:18]=w[16:18]
    for group in range(4): eligible[group*4:group*4+4]=e
    return dict(packets=old.pack(output),eligible=eligible,physical=saved['physical'].copy(),
                injury_masks=masks,survival_strata=strata,shuffle_source_edge=mapping)


def diagnostics(inter,fresh):
    result,coupling=baseline_diagnostics(inter,fresh)
    w=old.unpack(inter['packets']); e=inter['eligible']; donor=[8+i%4 if i<16 else i for i in range(18)]
    result['donor_sign_changes']=np.count_nonzero(e&(w!=0)&(np.signbit(w)!=np.signbit(w[donor])),axis=AXES)
    for prefix,weights,mask,kk in (('',w,e,coupling['coupling']),
        ('postinjury_',fresh['effective'],e&old.alive(fresh['masks']),fresh['coupling'])):
        for name,sign in (('positive',1),('negative',-1)):
            selected=mask&(sign*weights>0)
            result[prefix+'selected_'+name]=np.count_nonzero(selected,axis=AXES)
            result[prefix+'selected_'+name+'_mass']=np.where(selected,np.abs(weights),0.).sum(axis=AXES)
        result[prefix+'donor_coupling_l1']=np.abs(kk-kk[donor]).sum(axis=AXES)/256
        result[prefix+'donor_unsigned_coupling_l1']=np.abs(np.abs(kk)-np.abs(kk[donor])).sum(axis=AXES)/256
        negative=old.directions(mask&(weights<0)).sum(axis=-3)
        result[prefix+'donor_negative_incident_count_l1']=np.abs(negative-negative[donor]).sum(axis=(-2,-1))/256
    return result,coupling
