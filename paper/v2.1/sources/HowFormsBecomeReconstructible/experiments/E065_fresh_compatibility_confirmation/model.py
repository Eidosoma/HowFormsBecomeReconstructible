"""Six cross-stage substitutions and fresh terminal readers."""
import hashlib
import numpy as np
from common import rng
from E022_reader_compensation import model as reader
from E062_cross_stage_compatibility import graph
from E065_fresh_compatibility_confirmation.plan import GRAPH_FIELDS

base=reader.base
P=base.PORTS
REFERENCE=np.array([0,1,0,1,0,1,0,1,0,1,0,1,12])
SOURCE_ARM=np.array([0,1,0,1,0,1,0,1,0,1,0,1,0])


def incoming(w):
    h,v=w[...,0,:,:],w[...,1,:,:]
    return np.stack((h,np.roll(h,1,-1),v,np.roll(v,1,-2)),axis=-3)


def coupling(w):
    d=reader.incident_sum(abs(w));raw=incoming(w)
    k=np.zeros_like(raw);np.divide(raw,d[...,None,:,:],out=k,where=d[...,None,:,:]>0)
    return d,k


def intervene(source):
    old,final=base.decode(source['initial']),base.decode(source['final'])
    assert old.shape==final.shape and old.shape[:2]==(2,4)
    common=(old!=0)&(final!=0)
    changed=common&((old<0)!=(final<0));unchanged=common&~changed;later=(final!=0)&~common
    fo=final.copy();of=final.copy();oo=final.copy();c=final.copy();s=final.copy()
    fo[common]=np.copysign(abs(old[common]),final[common])
    of[common]=np.copysign(abs(final[common]),old[common]);oo[common]=old[common]
    c[changed]=np.copysign(abs(old[changed]),final[changed])
    s[unchanged]=np.copysign(abs(old[unchanged]),final[unchanged])
    packets=(final,fo,of,oo,c,s)
    noop=final.copy();noop[common]=np.copysign(abs(final[common]),final[common])
    w=np.concatenate((*packets,np.zeros_like(final[:1])),axis=0);assert np.isfinite(w).all()
    d,k=coupling(w)
    return dict(packets=base.encode(w),nochange_packets=base.encode(noop),common=common,changed=changed,
        unchanged=unchanged,later_only=later,denominator=d,coupling=k,**graph.batch(w))


def diagnostics(source,inter,fresh,cfg):
    w=base.decode(inter['packets']);final=base.decode(source['final']);old=base.decode(source['initial'])
    ref=w[REFERENCE];axes=(-3,-2,-1);common=inter['common']
    cases=score(fresh['mean_ports'],cfg['margin'])
    cases.update(weight_mass=abs(w).sum(axis=axes),
        sign_changes=((w!=0)&(ref!=0)&((w<0)!=(ref<0))).sum(axis=axes),
        support_gained=((w!=0)&(ref==0)).sum(axis=axes),support_lost=((w==0)&(ref!=0)).sum(axis=axes))
    for name in ('common','changed','unchanged','later_only'):cases[name+'_edges']=inter[name].sum(axis=axes)
    for prefix,raw in (('',inter),('postinjury_',fresh)):
        k=raw['coupling'];d=raw['denominator'];g=raw['graph'];anchor=raw['anchor']
        cases[prefix+'coupling_l1']=abs(k-k[REFERENCE]).sum(axis=axes)/256
        cases[prefix+'unsigned_coupling_l1']=abs(abs(k)-abs(k[REFERENCE])).sum(axis=axes)/256
        cases[prefix+'denominator_l1']=abs(d-d[REFERENCE]).mean(axis=(-2,-1))
        for name in ('changed','unchanged','later_only'):
            selected=incoming(inter[name][SOURCE_ARM])
            cases[prefix+name+'_influence']=np.where(selected,abs(k),0.).sum(axis=axes)/256
        for j,name in enumerate(GRAPH_FIELDS):cases[prefix+name]=g[...,j]
        cases[prefix+'inconsistent']=(g[...,3]>0)
        means=[]
        for j,label in enumerate(('input','positive','negative')):
            v=anchor[...,P[j]];means.append(v.mean(axis=-1))
            cases[prefix+'anchor_'+label]=means[-1]
            cases[prefix+'unreachable_'+label]=(v==0).sum(axis=-1)
        cases[prefix+'forest_rule_alignment']=(means[1]-means[2])*base.RULES.reshape(1,4,1)/2
    check=dict(native_bytes_unchanged=inter['packets'][:2].tobytes()==source['final'].tobytes(),
        nochange_alias_byte_exact=inter['nochange_packets'].tobytes()==source['final'].tobytes(),
        partition_complete=np.array_equal(inter['changed']|inter['unchanged'],common),
        partition_disjoint=not (inter['changed']&inter['unchanged']).any(),
        support_preserved=all(np.array_equal(w[i:i+2]!=0,final!=0) for i in (2,4,6,8,10)),
        final_signs_preserved=all(np.array_equal(np.sign(w[i:i+2]),np.sign(final)) for i in (2,8,10)),
        injury_count_correct=bool((fresh['masks'].sum(axis=(-2,-1))==24).all()),
        ports_protected=not fresh['masks'][...,P.any(axis=0)].any(),
        erased_zero=not w[12].any(),erased_no_success=not cases['both'][12].any())
    for start,name in ((8,'changed'),(10,'unchanged'),(2,'common')):
        selected=inter[name]
        check[name+'_earlier_magnitudes_exact']=np.array_equal(abs(w[start:start+2][selected]),abs(old[selected]))
        check[name+'_unselected_bytes_preserved']=w[start:start+2][~selected].tobytes()==final[~selected].tobytes()
    for stage,prefix,raw in (('pre','',inter),('post','postinjury_',fresh)):
        check[stage+'_sign_graph_fixed']=all(np.array_equal(raw['graph'][i:i+2],raw['graph'][:2]) and
            np.array_equal(raw['anchor'][i:i+2],raw['anchor'][:2]) for i in (2,8,10))
        total=sum(cases[prefix+n+'_influence'] for n in ('changed','unchanged','later_only'))
        check[stage+'_influence_partition']=np.allclose(total,(raw['denominator']>0).mean(axis=(-2,-1)),atol=3e-15,rtol=3e-14)
        check[stage+'_signed_unsigned_displacement_match']=np.array_equal(cases[prefix+'coupling_l1'][[0,1,2,3,8,9,10,11,12]],cases[prefix+'unsigned_coupling_l1'][[0,1,2,3,8,9,10,11,12]])
        check[stage+'_sign_swap_denominators_fixed']=all(np.array_equal(raw['denominator'][i:i+2],raw['denominator'][j:j+2]) for i,j in ((0,4),(2,6)))
        check[stage+'_old_sign_graph_fixed']=np.array_equal(raw['graph'][4:6],raw['graph'][6:8]) and np.array_equal(raw['anchor'][4:6],raw['anchor'][6:8])
    check['earlier_signs_exact']=all(np.array_equal(np.sign(w[i:i+2][common]),np.sign(old[common])) for i in (4,6))
    check['of_magnitudes_exact']=np.array_equal(abs(w[4:6]),abs(final))
    check['oo_values_exact']=w[6:8][common].tobytes()==old[common].tobytes()
    check['sign_substitution_other_bytes_fixed']=all(w[i:i+2][~common].tobytes()==final[~common].tobytes() for i in (4,6))
    check={k:bool(v) for k,v in check.items()};check['pass']=all(check.values())
    return cases,check


def masks(block,R):
    stream=rng('E065',block,'fresh_injury');available=np.flatnonzero(~P.any(axis=0).ravel())
    m=np.zeros((2,R,16,16),bool)
    for f,r in np.ndindex(2,R):m[f,r].ravel()[stream.choice(available,24,replace=False)]=True
    return base.paired_founders(m)


def digest(v):
    return np.frombuffer(hashlib.sha256(np.asarray(v,dtype='<f8').tobytes()).digest(),dtype=np.uint8)


def assay(packets,block,cfg):
    w=base.decode(packets);A,F,R=w.shape[:3]
    mask=masks(block,R);effective=w*reader.surviving_edges(mask)[None];d,k=coupling(effective)
    stream=rng('E065',block,'fresh_reader');shape=(2,R,16,16)
    birth=cfg['birth_sd']*base.paired_founders(stream.standard_normal(shape))
    v=np.broadcast_to(birth[None,:,:,None],(A,F,R,2,16,16)).copy()
    live=(~mask)[None,:,:,None];cues=base.CUES.reshape(1,1,1,2,1)
    v*=live;v[...,P[0]]=cues;trace=[];hashes=[]
    config=base.Config(recipients=R,dt=cfg['dt'],noise=cfg['noise'])
    for t in range(cfg['read_steps']):
        eta=base.paired_founders(stream.standard_normal(shape))[None,:,:,None]
        v=reader.compensated_step(v,effective[:,:,:,None],d[:,:,:,None],eta,config,t>=cfg['settling_steps'])
        v*=live;v[...,P[0]]=cues;hashes.append(digest(v))
        if t>=cfg['read_steps']-cfg['observe_steps']:
            trace.append(np.stack([v[...,P[j]].mean(axis=-1) for j in (1,2)],axis=-1))
    trace=np.stack(trace)
    return dict(masks=mask,effective=effective,denominator=d,coupling=k,birth=birth,end=v,
        late_ports=trace,mean_ports=trace.mean(axis=0),state_hashes=np.stack(hashes))


def score(v,margin):
    desired=base.RULES.reshape(1,4,1,1)*base.CUES
    m=np.minimum(desired*v[...,0],-desired*v[...,1])
    transfer=((v[...,0,0]-v[...,1,0])-(v[...,0,1]-v[...,1,1]))/4
    return dict(margin=m,minimum_margin=m.min(axis=-1),both=(m>margin).all(axis=-1),
        transfer=transfer,aligned_transfer=transfer*base.RULES.reshape(1,4,1))


