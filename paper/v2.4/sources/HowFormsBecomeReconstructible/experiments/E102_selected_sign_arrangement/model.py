"""Rearrange only signs within fixed two-injury survival strata."""
import numpy as np
from common import rng
from E077_fresh_reconstruction_tradeoff import model as old
from E101_cross_noise_components.model import diagnostics as baseline_diagnostics
from E102_selected_sign_arrangement.plan import references

base,reader,P = old.base,old.reader,old.P
AXES=(-3,-2,-1)


def shuffle_weights(donor,eligible,strata,task):
    out=donor.copy(); source=np.broadcast_to(np.arange(512,dtype=np.int16),(*donor.shape[:3],512)).copy()
    for arm,f,r in np.ndindex(donor.shape[:3]):
        values=donor[arm,f,r].ravel(); selected=eligible[arm,f,r].ravel()&(values!=0)
        signature=strata[f,r].ravel()
        for s in range(4):
            ids=np.flatnonzero(selected&(signature==s))
            permutation=rng('E102',task,'selected_sign_permutation',arm,f,r,s).permutation(len(ids))
            source[arm,f,r,ids]=ids[permutation]
        out[arm,f,r]=np.copysign(abs(values),values[source[arm,f,r]]).reshape(2,16,16)
    return out,source.reshape(donor.shape)


def intervene(saved,task):
    w=base.decode(saved['packets']); e=saved['eligible'][:4]
    b,m,d=w[:4],w[8:12],w[12:16]
    assert w.shape[0]==18
    for start in (4,8,12):
        assert np.array_equal(e,saved['eligible'][start:start+4]),'Selected-mask mismatch'
        assert b[~e].tobytes()==w[start:start+4][~e].tobytes(),'Outside donor mismatch'
        assert np.array_equal(b!=0,w[start:start+4]!=0),'Selected support mismatch'
    assert abs(m).tobytes()==abs(d).tobytes(),'Magnitude donor mismatch'
    assert np.array_equal(np.signbit(b),np.signbit(m)),'Sign donor mismatch'
    assert not w[np.broadcast_to(~saved['physical'],w.shape)].any()
    masks=np.stack([old.masks(task,w.shape[2],f'E102_terminal_{draw}_injury',0) for draw in (0,1)])
    alive=reader.surviving_edges(masks)
    strata=alive[0].astype(np.uint8)+2*alive[1].astype(np.uint8)
    shuffled,source=shuffle_weights(d,e,strata,task)
    packets=base.encode(np.concatenate((b,m,d,shuffled,w[[16,17]])))
    eligible=np.concatenate((e,e,e,e,np.zeros_like(e[:2])))
    for start,prior in ((0,0),(4,8),(8,12)):
        assert packets[start:start+4].tobytes()==saved['packets'][prior:prior+4].tobytes()
    return dict(packets=packets,eligible=eligible,physical=saved['physical'].copy(),
                injury_masks=masks,survival_strata=strata,shuffle_source_edge=source)


def diagnostics(inter,fresh):
    result,coupling=baseline_diagnostics(inter,fresh)
    w=base.decode(inter['packets']); e=inter['eligible']; _,donor=references()
    present=(w!=0)&e
    result['donor_sign_changes']=(present&(np.signbit(w)!=np.signbit(w[donor]))).sum(axis=AXES)
    for prefix,weights,mask,kk in (('',w,e,coupling['coupling']),
        ('postinjury_',fresh['effective'],e&reader.surviving_edges(fresh['masks']),fresh['coupling'])):
        for name,test in (('positive',weights>0),('negative',weights<0)):
            result[prefix+'selected_'+name]=(mask&test).sum(axis=AXES)
            result[prefix+'selected_'+name+'_mass']=(abs(weights)*(mask&test)).sum(axis=AXES)
        result[prefix+'donor_coupling_l1']=abs(kk-kk[donor]).sum(axis=AXES)/256
        result[prefix+'donor_unsigned_coupling_l1']=abs(abs(kk)-abs(kk[donor])).sum(axis=AXES)/256
        negative_incident=old.directed(mask&(weights<0)).sum(axis=-3)
        result[prefix+'donor_negative_incident_count_l1']=abs(negative_incident-negative_incident[donor]).sum(axis=(-2,-1))/256
    return result,coupling


def preflight_checks(inter):
    w=base.decode(inter['packets']); e=inter['eligible']; d,s=w[8:12],w[12:16]
    assert abs(d).tobytes()==abs(s).tobytes()==abs(w[4:8]).tobytes()
    for survival in (np.ones_like(inter['physical']),*reader.surviving_edges(inter['injury_masks'])):
        effective=w*survival; denominator,coupling=old.coupling(effective)
        for start in (4,12):
            assert denominator[start:start+4].tobytes()==denominator[8:12].tobytes()
            assert abs(coupling[start:start+4]).tobytes()==abs(coupling[8:12]).tobytes()
        for sign in (-1,1):
            count=((sign*effective>0)&e).sum(axis=AXES)
            assert np.array_equal(count[8:12],count[12:16])
    return dict(sign_counts_exact_globally_and_both_injuries=True,
                magnitudes_denominators_absolute_coupling_exact=True,no_reader_dynamics=True)


def checks(inter,fresh,cases,coupling,draw):
    w=base.decode(inter['packets']); e=inter['eligible']; baseline,donor=references()
    assert w.shape[0]==18 and inter['packets'].shape[-1]==4096
    assert w[~e].tobytes()==w[baseline][~e].tobytes(),'Outside bytes changed'
    assert np.array_equal(w!=0,w[baseline]!=0),'Support changed'
    assert not w[np.broadcast_to(~inter['physical'],w.shape)].any()
    assert np.array_equal(fresh['masks'],inter['injury_masks'][draw]),'Injury conditioning mismatch'
    alive=reader.surviving_edges(inter['injury_masks'])
    assert np.array_equal(inter['survival_strata'],alive[0]+2*alive[1].astype(np.uint8))
    d,s=w[8:12],w[12:16]
    for arm,f,r in np.ndindex(d.shape[:3]):
        source=inter['shuffle_source_edge'][arm,f,r].ravel()
        values=d[arm,f,r].ravel(); selected=e[arm,f,r].ravel()&(values!=0)
        strata=inter['survival_strata'][f,r].ravel()
        assert np.array_equal(np.sort(source),np.arange(512)),'Map is not bijective'
        assert np.array_equal(source[~selected],np.flatnonzero(~selected)),'Unselected edge moved'
        assert np.array_equal(strata[source],strata),'Stratum crossed'
        assert s[arm,f,r].ravel().tobytes()==np.copysign(abs(values),values[source]).tobytes(),'Sign map mismatch'
        for z in range(4):
            pool=selected&(strata==z)
            assert np.count_nonzero(values[pool]<0)==np.count_nonzero(s[arm,f,r].ravel()[pool]<0)
    for start in (4,12):
        assert abs(w[start:start+4]).tobytes()==abs(d).tobytes()
        for arrays in (coupling,fresh):
            assert arrays['denominator'][start:start+4].tobytes()==arrays['denominator'][8:12].tobytes()
            assert abs(arrays['coupling'][start:start+4]).tobytes()==abs(arrays['coupling'][8:12]).tobytes()
    assert np.array_equal(np.signbit(w[:4]),np.signbit(w[4:8]))
    for weights in (w,fresh['effective']):
        for sign in (1,-1):
            count=((sign*weights>0)&e).sum(axis=AXES)
            assert np.array_equal(count[8:12],count[12:16]),'Selected sign counts changed'
    # Bytes of zeros are retained, including the signs of stored zero values.
    assert s[d==0].tobytes()==d[d==0].tobytes()
    for arrays in (coupling,fresh):
        np.testing.assert_allclose(abs(arrays['coupling']).sum(axis=-3),(arrays['denominator']>0).astype(float),rtol=0,atol=4e-15)
    empty=~(e&reader.surviving_edges(fresh['masks'])).any(axis=AXES)
    assert fresh['end'][empty].tobytes()==fresh['end'][baseline][empty].tobytes()
    same=(fresh['effective'][12:16]==fresh['effective'][8:12]).all(axis=AXES)
    assert fresh['end'][12:16][same].tobytes()==fresh['end'][8:12][same].tobytes()
    for slot in (16,17):
        for f in (0,2):
            assert inter['packets'][slot,f].tobytes()==inter['packets'][slot,f+1].tobytes()
            assert fresh['end'][slot,f].tobytes()==fresh['end'][slot,f+1].tobytes()
            assert not (cases['both'][slot,f]&cases['both'][slot,f+1]).any()
    assert (fresh['masks'].sum((-2,-1))==24).all() and not fresh['masks'][...,P.any(axis=0)].any()
    assert np.array_equal(cases['both'],cases['minimum_margin']>.25)
    return dict(outside_bytes_exact=True,support_preserved=True,permutation_bijective_within_strata=True,
        selected_sign_counts_exact_before_and_after_injury=True,magnitudes_denominators_absolute_coupling_exact=True,
        zeros_preserved=True,conditioned_masks_match_reader=True,unchanged_effective_packets_alias_exactly=True,
        erased_aliases_verified=True,natural_normalization_verified=True,strict_success_verified=True)


def inventory(inter):
    w=base.decode(inter['packets']); d,s=w[8:12],w[12:16]; e=inter['eligible'][:4]
    rows=[]
    for arm,f,r in np.ndindex(d.shape[:3]):
        values=d[arm,f,r].ravel(); selection=e[arm,f,r].ravel()&(values!=0)
        strata=inter['survival_strata'][f,r].ravel(); mixed=0; expected=0.; sizes=[]
        for z in range(4):
            v=values[selection&(strata==z)]; n=len(v); neg=int((v<0).sum()); sizes.append(n)
            mixed+=int(0<neg<n)
            expected+=2*neg*(n-neg)/n if n else 0.
        changed=int((selection&(np.signbit(values)!=np.signbit(s[arm,f,r].ravel()))).sum())
        rows.append(dict(arm=arm,kind='native' if arm<2 else 'mixture',founder=f,recipient=r,
            selected_present=int(selection.sum()),positive=int((values[selection]>0).sum()),
            negative=int((values[selection]<0).sum()),stratum_sizes=sizes,mixed_sign_strata=mixed,
            expected_sign_changes=expected,actual_sign_changes=changed,unchanged=changed==0))
    return rows
