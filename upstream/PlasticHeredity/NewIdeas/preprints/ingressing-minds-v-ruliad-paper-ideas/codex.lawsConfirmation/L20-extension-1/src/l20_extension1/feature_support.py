"""D166 outcome-free scalar range and multivariate input-support accounting."""
import numpy as np

GROUPS=('A_ordinary','A_aligned','B_ordinary','B_aligned')
START=('own_best','best_margin','guide_margin','canonical_margin','own_axis_rms','alternative_axis_rms','residual_rms')
END=('own_best','best_margin','guide_margin','canonical_margin','preference','V_rms')
EDITS=('passive','shuffle','attenuate','sham_plus','sham_minus')
POOL=('passive','sham_plus','sham_minus')
EPS=1e-12
SCALARS=tuple('start:'+k for k in START)+tuple('first:'+k for k in END)+tuple(
    prefix+':'+edit+':'+k for prefix in ('second','response') for edit in EDITS for k in END)


def view_specs():
    return [dict(name=k,encoding=k,condition=None,reference='own',dimensions=d) for k,d in (('starting',7),('one_copy',13))]+[
        dict(name=reference+':'+e+':'+k,encoding=e,condition=k,reference=reference,dimensions=19 if e=='separate' else 13)
        for reference in ('own','shared') for e in ('separate','mean') for k in EDITS]


def validate(features,ids):
    assert set(features)=={'start','endpoint','targeted'},'only permitted measurements'
    n=len(ids)
    assert n>=3 and ids.shape==(n,) and ids.dtype==np.int64 and len(set(ids))==n
    assert features['start'].shape==(n,4,4,7)
    assert features['endpoint'].shape==features['targeted'].shape==(n,4,4,3,6)
    assert all(v.dtype==np.float64 and np.isfinite(v).all() for v in features.values())


def seconds(features):
    e,t=features['endpoint'],features['targeted']
    return dict(zip(EDITS,(e[...,1,:],e[...,2,:],t[...,0,:],t[...,1,:],t[...,2,:])))


def scalars(features):
    first=features['endpoint'][...,0,:];other=seconds(features)
    return np.concatenate([features['start'],first]+[other[k] for k in EDITS]+[other[k]-first for k in EDITS],axis=-1)


def vectors(features):
    a=features['start'];first=features['endpoint'][...,0,:]
    result=dict(starting=a,one_copy=np.concatenate((a,first),axis=-1))
    for e in ('separate','mean'):
        for k,second in seconds(features).items():
            result[e+':'+k]=np.concatenate((a,first,second),axis=-1) if e=='separate' else np.concatenate((a,(first+second)/2),axis=-1)
    return result


def stats(x):
    mean=x.mean(axis=0);sd=np.sqrt(np.mean((x-mean)**2,axis=0))
    return dict(mean=mean,sd=sd,minimum=x.min(axis=0),maximum=x.max(axis=0),active=sd>EPS)


def position(x,reference):
    z=np.divide(x-reference['mean'],reference['sd'],out=np.zeros_like(x),where=reference['active'])
    side=(x>reference['maximum']).astype(np.int8)-(x<reference['minimum']).astype(np.int8)
    return z,side


def reference(vectors_,spec,keep,ids,g):
    """Canonical founder/life/view row order makes tie-breaking deterministic."""
    keep=np.asarray(sorted(keep,key=lambda b:int(ids[b])),dtype=np.int64)
    keys=[spec['encoding']] if spec['condition'] is None else [spec['encoding']+':'+k for k in
        (POOL if spec['reference']=='shared' else (spec['condition'],))]
    rows=np.stack([vectors_[key][keep,:,g] for key in keys],axis=2)
    indices=np.stack(np.meshgrid(ids[keep],np.arange(4,dtype=np.int64),np.arange(len(keys),dtype=np.int64),indexing='ij'),-1).reshape(-1,3)
    return rows.reshape(-1,rows.shape[-1]),indices


def nearest(x,train,identities):
    r=stats(train);active=r['active'];count=int(active.sum())
    if count:
        delta=(x[:,None,active]-train[None,:,active])/r['sd'][active]
        squared=np.sum(delta*delta,axis=-1)/count
    else:squared=np.zeros((len(x),len(train)))
    index=squared.argmin(axis=1)
    distance=np.sqrt(squared[np.arange(len(x)),index])
    box=((x<r['minimum'])|(x>r['maximum'])).any(axis=1)
    return distance,box,identities[index],count


def calculate(development,pilot,development_ids,pilot_ids):
    validate(development,development_ids);validate(pilot,pilot_ids)
    assert not set(development_ids)&set(pilot_ids)
    nd,npilot=len(development_ids),len(pilot_ids);d,p=scalars(development),scalars(pilot)
    out={};full=stats(d.reshape(nd*4,4,73))
    for key,value in full.items():out['full_'+key]=value
    fold=[]
    for b in range(nd):fold.append(stats(d[np.arange(nd)!=b].reshape((nd-1)*4,4,73)))
    for key in full:out['reference_'+key]=np.stack([v[key] for v in fold])
    dz=[];ds=[];pz=[];ps=[]
    for b,ref in enumerate(fold):
        z,side=position(d[b],ref);dz.append(z);ds.append(side)
        z,side=position(p,ref);pz.append(z);ps.append(side)
    out.update(development_z=np.stack(dz),development_side=np.stack(ds),pilot_z=np.stack(pz),pilot_side=np.stack(ps))
    dv,pv=vectors(development),vectors(pilot);specs=view_specs();nv=len(specs)
    for co,shape in [('development',(nd,4,4,nv)),('pilot',(nd,npilot,4,4,nv))]:
        for name,dtype in [('distance',np.float64),('box',bool),('neighbor_founder',np.int64),('neighbor_life',np.int64),('neighbor_view',np.int64)]:
            out[co+'_'+name]=np.empty(shape,dtype=dtype)
    out['active_dimensions']=np.empty((nd,4,nv),dtype=np.int64)
    for b in range(nd):
        keep=np.flatnonzero(np.arange(nd)!=b)
        for j,spec in enumerate(specs):
            key=spec['encoding'] if spec['condition'] is None else spec['encoding']+':'+spec['condition']
            for g in range(4):
                train,identities=reference(dv,spec,keep,development_ids,g)
                queries=np.concatenate((dv[key][b,:,g],pv[key][:,:,g].reshape(npilot*4,-1)))
                dist,box,neighbor,count=nearest(queries,train,identities)
                out['active_dimensions'][b,g,j]=count
                for co,part,shape in [('development',slice(0,4),(4,)),('pilot',slice(4,None),(npilot,4))]:
                    for name,value in [('distance',dist),('box',box),('neighbor_founder',neighbor[:,0]),
                                       ('neighbor_life',neighbor[:,1]),('neighbor_view',neighbor[:,2])]:
                        out[co+'_'+name][b,...,g,j]=value[part].reshape(shape)
    return out


def raw_stats(x):
    return dict(mean=float(x.mean()),sd=float(np.std(x)),minimum=float(x.min()),maximum=float(x.max()))


def scalar_description(z,side,active,pilot):
    value=z[active];valid=value.size
    outside=side!=0
    return dict(below=float((side<0).mean()),above=float((side>0).mean()),outside=float(outside.mean()),
        standardized_mean=float(value.mean()) if valid else None,
        standardized_rms=float(np.sqrt((value*value).mean())) if valid else None,standardized_instances=valid,
        founder_outside=outside.mean((0,2) if pilot else 1).tolist(),
        reference_outside=outside.mean((1,2) if pilot else 1).tolist())


def vector_description(distance,box,pilot):
    return dict(mean=float(distance.mean()),median=float(np.quantile(distance,.5)),q90=float(np.quantile(distance,.9)),
        maximum=float(distance.max()),box_outside=float(box.mean()),
        founder_distance=distance.mean((0,2) if pilot else 1).tolist(),
        reference_distance=distance.mean((1,2) if pilot else 1).tolist(),
        founder_box=box.mean((0,2) if pilot else 1).tolist(),reference_box=box.mean((1,2) if pilot else 1).tolist())


def summarize(arrays,development,pilot,development_ids,pilot_ids):
    validate(development,development_ids);validate(pilot,pilot_ids)
    d,p=scalars(development),scalars(pilot);nd=len(development_ids);rows=[];vector_rows=[]
    for g,group in enumerate(GROUPS):
        for j,name in enumerate(SCALARS):
            ds,ps=raw_stats(d[:,:,g,j]),raw_stats(p[:,:,g,j]);sd=ds['sd'];active=arrays['reference_active'][:,g,j]
            dc=scalar_description(arrays['development_z'][:,:,g,j],arrays['development_side'][:,:,g,j],active,False)
            pc=scalar_description(arrays['pilot_z'][:,:,:,g,j],arrays['pilot_side'][:,:,:,g,j],active,True)
            rows.append(dict(group=group,feature=name,development_raw=ds,pilot_raw=ps,
                standardized_mean_shift=(ps['mean']-ds['mean'])/sd if sd>EPS else None,
                sd_ratio=ps['sd']/sd if sd>EPS else None,active_references=int(active.sum()),
                development=dc,pilot=pc,outside_rate_change=pc['outside']-dc['outside']))
        for j,spec in enumerate(view_specs()):
            dc=vector_description(arrays['development_distance'][:,:,g,j],arrays['development_box'][:,:,g,j],False)
            pc=vector_description(arrays['pilot_distance'][:,:,:,g,j],arrays['pilot_box'][:,:,:,g,j],True)
            vector_rows.append(dict(group=group,**spec,development=dc,pilot=pc,
                active_dimensions=arrays['active_dimensions'][:,g,j].tolist(),
                mean_distance_change=pc['mean']-dc['mean'],mean_distance_ratio=pc['mean']/dc['mean'] if dc['mean'] else None,
                box_rate_change=pc['box_outside']-dc['box_outside']))
    return dict(schema='d166_feature_support_v1',scalar_rows=rows,vector_rows=vector_rows,
        development_ids=development_ids.tolist(),pilot_ids=pilot_ids.tolist(),groups=list(GROUPS),
        scalar_names=list(SCALARS),views=view_specs(),reference_blocks=[development_ids[development_ids!=b].tolist() for b in development_ids],
        development_founders=nd,pilot_founders=len(pilot_ids),development_cases=16*nd,pilot_cases=16*len(pilot_ids),
        references=nd,scalar_group_rows=292,vector_group_rows=88,constant_sd_tolerance=EPS,
        independent_references=False,post_test_explanation=True,prospective_evidence=False,confidence_intervals=False,
        outcomes_used=False,forecasts_used=False,all_cases_retained=True,new_fits=0,new_forecasts=0,
        new_dynamics=0,new_diagnostic_cycles=0,new_founders=0,source_primary_unchanged=True,automatic_successor=False)


def fixture(nd=4,npilot=5,seed=16620260922):
    rng=np.random.default_rng(seed)
    def cohort(n):
        start=rng.normal(size=(n,4,4,7));endpoint=rng.normal(size=(n,4,4,3,6))
        targeted=endpoint.copy()+rng.normal(0,.3,size=endpoint.shape)
        return dict(start=start,endpoint=endpoint,targeted=targeted)
    return cohort(nd),cohort(npilot),np.arange(90000,90000+nd,dtype=np.int64),np.arange(100000,100000+npilot,dtype=np.int64)
