"""Independent scalar subset assignments and explicit reader/score algebra."""
import hashlib
import numpy as np
from E015_functional_inheritance.audit import random,pair,unpack,pack,ports
from E062_cross_stage_compatibility.audit_model import graph_batch

P=ports()


def intervene(source):
    old,final=unpack(source['initial']),unpack(source['final']);R=old.shape[2]
    w=np.empty((13,4,R,2,16,16))
    for start in (0,2,4,6,8,10):w[start:start+2]=final
    w[12]=0.;noop=final.copy()
    common=np.zeros_like(old,bool);changed=common.copy();unchanged=common.copy();later=common.copy()
    for a,f,r,e,y,x in np.ndindex(old.shape):
        o,n=old[a,f,r,e,y,x],final[a,f,r,e,y,x]
        if n!=0:
            if o==0:later[a,f,r,e,y,x]=True
            else:
                common[a,f,r,e,y,x]=True
                is_changed=bool(np.signbit(o)!=np.signbit(n))
                changed[a,f,r,e,y,x]=is_changed;unchanged[a,f,r,e,y,x]=not is_changed
                value=(-1. if n<0 else 1.)*abs(o)
                w[(8 if is_changed else 10)+a,f,r,e,y,x]=value
                w[2+a,f,r,e,y,x]=value
                w[4+a,f,r,e,y,x]=(-1. if o<0 else 1.)*abs(n)
                w[6+a,f,r,e,y,x]=o
                noop[a,f,r,e,y,x]=(-1. if n<0 else 1.)*abs(n)
    d,k=coupling(w)
    return dict(packets=pack(w),nochange_packets=pack(noop),common=common,changed=changed,
        unchanged=unchanged,later_only=later,denominator=d,coupling=k,**graph_batch(w))


def diagnostics(source,inter,fresh,cfg):
    w=unpack(inter['packets']);R=w.shape[2];v=fresh['mean_ports'];m=np.empty(v.shape[:-1]);tr=np.empty(v.shape[:-2])
    for a,f,r in np.ndindex(13,4,R):
        rule=(1.,-1.,1.,-1.)[f]
        for c,cue in enumerate((1.,-1.)):
            m[a,f,r,c]=min(rule*cue*v[a,f,r,c,0],-rule*cue*v[a,f,r,c,1])
        tr[a,f,r]=((v[a,f,r,0,0]-v[a,f,r,1,0])-(v[a,f,r,0,1]-v[a,f,r,1,1]))/4
    out=dict(margin=m,minimum_margin=m.min(axis=-1),both=(m>cfg['margin']).all(axis=-1),
        transfer=tr,aligned_transfer=tr*np.array([1.,-1.,1.,-1.])[None,:,None])
    refs=[0,1,0,1,0,1,0,1,0,1,0,1,12];ref=w[refs];axes=(-3,-2,-1)
    out.update(weight_mass=np.abs(w).sum(axis=axes),
        sign_changes=np.count_nonzero((w!=0)&(ref!=0)&((w<0)!=(ref<0)),axis=axes),
        support_gained=np.count_nonzero((w!=0)&(ref==0),axis=axes),support_lost=np.count_nonzero((w==0)&(ref!=0),axis=axes))
    for name in ('common','changed','unchanged','later_only'):out[name+'_edges']=np.count_nonzero(inter[name],axis=axes)
    fields=('edges','components','cycle_rank','negative_basis_cycles','input_reachable','positive_port_reachable','negative_port_reachable')
    masks={}
    for name in ('changed','unchanged','later_only'):
        raw=inter[name][[0,1,0,1,0,1,0,1,0,1,0,1,0]];directed=np.empty((13,4,R,4,16,16),bool)
        for y,x in np.ndindex(16,16):
            for j,(edge,yy,xx) in enumerate(((0,y,x),(0,y,(x-1)%16),(1,y,x),(1,(y-1)%16,x))):
                directed[...,j,y,x]=raw[...,edge,yy,xx]
        masks[name]=directed
    for prefix,raw in (('',inter),('postinjury_',fresh)):
        k,d,g,anchor=raw['coupling'],raw['denominator'],raw['graph'],raw['anchor']
        out[prefix+'coupling_l1']=np.stack([abs(k[a]-k[refs[a]]).sum(axis=axes)/256 for a in range(13)])
        out[prefix+'unsigned_coupling_l1']=np.stack([abs(abs(k[a])-abs(k[refs[a]])).sum(axis=axes)/256 for a in range(13)])
        out[prefix+'denominator_l1']=np.stack([abs(d[a]-d[refs[a]]).mean(axis=(-2,-1)) for a in range(13)])
        for name,mask in masks.items():out[prefix+name+'_influence']=np.where(mask,np.abs(k),0.).sum(axis=axes)/256
        for j,name in enumerate(fields):out[prefix+name]=g[...,j]
        out[prefix+'inconsistent']=g[...,3]!=0
        means=[]
        for j,label in enumerate(('input','positive','negative')):
            points=np.flatnonzero(P[j]);flat=anchor.reshape(13,4,R,256)
            mean=flat[...,points].sum(axis=-1)/len(points);means.append(mean)
            out[prefix+'anchor_'+label]=mean
            out[prefix+'unreachable_'+label]=np.count_nonzero(flat[...,points]==0,axis=-1)
        out[prefix+'forest_rule_alignment']=(means[1]-means[2])*np.array([1.,-1.,1.,-1.])[None,:,None]/2
    final,old=unpack(source['final']),unpack(source['initial']);c=inter['common']
    checks=dict(native_bytes_unchanged=inter['packets'][:2].tobytes()==source['final'].tobytes(),
        nochange_alias_byte_exact=inter['nochange_packets'].tobytes()==source['final'].tobytes(),
        partition_complete=np.array_equal(inter['changed'].astype(int)+inter['unchanged'].astype(int),c.astype(int)),
        partition_disjoint=not np.any(inter['changed']&inter['unchanged']),
        support_preserved=all(np.array_equal(w[i:i+2]!=0,final!=0) for i in (2,4,6,8,10)),
        final_signs_preserved=all(np.array_equal(np.sign(w[i:i+2]),np.sign(final)) for i in (2,8,10)),
        injury_count_correct=(fresh['masks'].sum(axis=(-2,-1))==24).all(),
        ports_protected=not fresh['masks'][...,P.any(axis=0)].any(),
        erased_zero=not np.count_nonzero(w[12]),erased_no_success=not out['both'][12].any())
    for start,name in ((8,'changed'),(10,'unchanged'),(2,'common')):
        selected=inter[name]
        checks[name+'_earlier_magnitudes_exact']=np.array_equal(np.abs(w[start:start+2][selected]),np.abs(old[selected]))
        checks[name+'_unselected_bytes_preserved']=w[start:start+2][~selected].tobytes()==final[~selected].tobytes()
    for stage,prefix,raw in (('pre','',inter),('post','postinjury_',fresh)):
        checks[stage+'_sign_graph_fixed']=all(np.array_equal(raw['graph'][i:i+2],raw['graph'][:2]) and
            np.array_equal(raw['anchor'][i:i+2],raw['anchor'][:2]) for i in (2,8,10))
        influence=out[prefix+'changed_influence']+out[prefix+'unchanged_influence']+out[prefix+'later_only_influence']
        checks[stage+'_influence_partition']=np.allclose(influence,np.count_nonzero(raw['denominator'],axis=(-2,-1))/256,atol=3e-15,rtol=3e-14)
        checks[stage+'_signed_unsigned_displacement_match']=np.array_equal(out[prefix+'coupling_l1'][[0,1,2,3,8,9,10,11,12]],out[prefix+'unsigned_coupling_l1'][[0,1,2,3,8,9,10,11,12]])
        checks[stage+'_sign_swap_denominators_fixed']=all(np.array_equal(raw['denominator'][i:i+2],raw['denominator'][j:j+2]) for i,j in ((0,4),(2,6)))
        checks[stage+'_old_sign_graph_fixed']=np.array_equal(raw['graph'][4:6],raw['graph'][6:8]) and np.array_equal(raw['anchor'][4:6],raw['anchor'][6:8])
    checks['earlier_signs_exact']=all(np.array_equal(np.sign(w[i:i+2][c]),np.sign(old[c])) for i in (4,6))
    checks['of_magnitudes_exact']=np.array_equal(np.abs(w[4:6]),np.abs(final))
    checks['oo_values_exact']=w[6:8][c].tobytes()==old[c].tobytes()
    checks['sign_substitution_other_bytes_fixed']=all(w[i:i+2][~c].tobytes()==final[~c].tobytes() for i in (4,6))
    checks={k:bool(v) for k,v in checks.items()};checks['pass']=all(checks.values())
    return out,checks


def coupling(w):
    d=np.empty(w.shape[:-3]+(16,16));k=np.zeros(w.shape[:-3]+(4,16,16))
    for y,x in np.ndindex(16,16):
        terms=(w[...,0,y,x],w[...,0,y,(x-1)%16],w[...,1,y,x],w[...,1,(y-1)%16,x])
        total=abs(terms[0])+abs(terms[1])+abs(terms[2])+abs(terms[3]);d[...,y,x]=total
        for j,a in enumerate(terms):np.divide(a,total,out=k[...,j,y,x],where=total>0)
    return d,k



def assay(packets,block,cfg):
    w=unpack(packets);A,F,R=w.shape[:3]
    g=random('E065',block,'fresh_injury');available=np.flatnonzero(~P.any(axis=0).ravel())
    m=np.zeros((2,R,16,16),bool)
    for f in range(2):
        for r in range(R):m[f,r].ravel()[g.choice(available,24,replace=False)]=True
    mask=pair(m);effective=np.zeros_like(w)
    for e,y,x in np.ndindex(2,16,16):
        yy,xx=(y,(x+1)%16) if e==0 else ((y+1)%16,x)
        effective[...,e,y,x]=w[...,e,y,x]*(~mask[...,y,x]&~mask[...,yy,xx])
    d,k=coupling(effective)
    stream=random('E065',block,'fresh_reader');shape=(2,R,16,16)
    birth=cfg['birth_sd']*pair(stream.standard_normal(shape))
    v=np.empty((A,F,R,2,16,16))
    for a,c in np.ndindex(A,2):v[a,:,:,c]=birth
    live=(~mask)[None,:,:,None];cues=np.array([1.,-1.]).reshape(1,1,1,2,1)
    v*=live;v[...,P[0]]=cues;trace=[];hashes=[]
    h=effective[...,0,:,:][:,:,:,None];vertical=effective[...,1,:,:][:,:,:,None]
    for t in range(cfg['read_steps']):
        eta=pair(stream.standard_normal(shape))[None,:,:,None]
        incoming=h*np.roll(v,-1,-1)
        incoming=incoming+np.roll(h,1,-1)*np.roll(v,1,-1)
        incoming=incoming+vertical*np.roll(v,-1,-2)
        incoming=incoming+np.roll(vertical,1,-2)*np.roll(v,1,-2)
        normal=np.zeros_like(v);np.divide(incoming,d[:,:,:,None],out=normal,where=d[:,:,:,None]!=0)
        local=v-v**3 if t>=cfg['settling_steps'] else -v**3
        drift=local+2.*(normal-v)
        v=np.clip(v+cfg['dt']*drift+cfg['noise']*eta,-2.,2.)
        v*=live;v[...,P[0]]=cues
        hashes.append(np.frombuffer(hashlib.sha256(np.asarray(v,dtype='<f8').tobytes()).digest(),dtype=np.uint8))
        if t>=cfg['read_steps']-cfg['observe_steps']:
            trace.append(np.stack((v[...,P[1]].mean(axis=-1),v[...,P[2]].mean(axis=-1)),axis=-1))
    trace=np.array(trace)
    return dict(masks=mask,effective=effective,denominator=d,coupling=k,birth=birth,end=v,
        late_ports=trace,mean_ports=trace.mean(axis=0),state_hashes=np.array(hashes))


