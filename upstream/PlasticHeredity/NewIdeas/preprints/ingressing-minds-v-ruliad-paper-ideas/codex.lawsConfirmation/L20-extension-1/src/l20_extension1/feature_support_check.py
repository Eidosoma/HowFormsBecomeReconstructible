"""Independent D166 coordinate, nearest-neighbor and descriptive-score replay."""
import numpy as np
from . import feature_support as m


def same(got,want):
    if isinstance(want,dict):
        assert isinstance(got,dict) and set(got)==set(want)
        for key in want:same(got[key],want[key])
    elif isinstance(want,(list,tuple)):
        assert isinstance(got,(list,tuple)) and len(got)==len(want)
        for x,y in zip(got,want):same(x,y)
    elif want is None or isinstance(want,(str,bool,int)):
        assert got==want and (type(got) is bool if isinstance(want,bool) else True)
    else:np.testing.assert_allclose(got,want,atol=2e-10,rtol=0)


def scalar_matrix(f):
    columns=[f['start'][...,j] for j in range(7)]+[f['endpoint'][...,0,j] for j in range(6)]
    second=[f['endpoint'][...,1,:],f['endpoint'][...,2,:]]+[f['targeted'][...,j,:] for j in range(3)]
    for subtract in (False,True):
        for x in second:
            for j in range(6):columns.append(x[...,j]-f['endpoint'][...,0,j] if subtract else x[...,j])
    return np.stack(columns,-1)


def vector(f,encoding,condition):
    if encoding=='starting':return f['start']
    a=[f['start'][...,j] for j in range(7)];first=f['endpoint'][...,0,:]
    if encoding=='one_copy':return np.stack(a+[first[...,j] for j in range(6)],-1)
    k=m.EDITS.index(condition);second=f['endpoint'][...,k+1,:] if k<2 else f['targeted'][...,k-2,:]
    if encoding=='mean':return np.stack(a+[.5*first[...,j]+.5*second[...,j] for j in range(6)],-1)
    return np.stack(a+[first[...,j] for j in range(6)]+[second[...,j] for j in range(6)],-1)


def moments(x):
    n=len(x);mean=x.sum(0)/n;sd=np.sqrt(np.sum(np.square(x-mean),axis=0)/n)
    return dict(mean=mean,sd=sd,minimum=np.amin(x,0),maximum=np.amax(x,0),active=sd>1e-12)


def check_arrays(arrays,d,p,di,pi):
    m.validate(d,di);m.validate(p,pi);assert not set(di)&set(pi)
    nd,npilot=len(di),len(pi);ds,ps=scalar_matrix(d),scalar_matrix(p)
    keys={prefix+k for prefix in ('full_','reference_') for k in ('mean','sd','minimum','maximum','active')}
    keys|={co+'_'+k for co in ('development','pilot') for k in ('z','side','distance','box','neighbor_founder','neighbor_life','neighbor_view')}
    keys.add('active_dimensions');assert set(arrays)==keys
    assert all(np.isfinite(v).all() for v in arrays.values())
    full=moments(ds.reshape(nd*4,4,73))
    for key,v in full.items():same(arrays['full_'+key],v)
    assert arrays['development_z'].shape==arrays['development_side'].shape==(nd,4,4,73)
    assert arrays['pilot_z'].shape==arrays['pilot_side'].shape==(nd,npilot,4,4,73)
    for co in ('development','pilot'):
        assert arrays[co+'_z'].dtype==np.float64 and arrays[co+'_side'].dtype==np.int8
        shape=(nd,4,4,22) if co=='development' else (nd,npilot,4,4,22)
        for key in ('distance','box','neighbor_founder','neighbor_life','neighbor_view'):assert arrays[co+'_'+key].shape==shape
        assert arrays[co+'_distance'].dtype==np.float64 and arrays[co+'_box'].dtype==bool
        for key in ('neighbor_founder','neighbor_life','neighbor_view'):assert arrays[co+'_'+key].dtype==np.int64
    assert arrays['active_dimensions'].shape==(nd,4,22) and arrays['active_dimensions'].dtype==np.int64
    for key in full:
        assert arrays['reference_'+key].shape==(nd,4,73)
        assert arrays['reference_'+key].dtype==(bool if key=='active' else np.float64)
    maximum=0.;checked=0
    for b in range(nd):
        keep=[i for i in range(nd) if i!=b];stats=moments(ds[keep].reshape(4*(nd-1),4,73))
        for key,v in stats.items():same(arrays['reference_'+key][b],v)
        for co,x in [('development',ds[b]),('pilot',ps)]:
            z=np.zeros_like(x)
            for g in range(4):
                for j in range(73):
                    if stats['active'][g,j]:z[...,g,j]=(x[...,g,j]-stats['mean'][g,j])/stats['sd'][g,j]
            side=np.where(x<stats['minimum'],-1,np.where(x>stats['maximum'],1,0)).astype(np.int8)
            same(arrays[co+'_z'][b],z);np.testing.assert_array_equal(arrays[co+'_side'][b],side)
        for j,spec in enumerate(m.view_specs()):
            dv=vector(d,spec['encoding'],spec['condition']);pv=vector(p,spec['encoding'],spec['condition'])
            conditions=m.POOL if spec['reference']=='shared' else (spec['condition'],)
            ref=[vector(d,spec['encoding'],condition) for condition in conditions]
            for g in range(4):
                indices=[(int(di[i]),l,k) for i in sorted(keep,key=lambda i:int(di[i])) for l in range(4) for k in range(len(ref))]
                by_id={int(v):i for i,v in enumerate(di)}
                train=np.stack([ref[k][by_id[founder],l,g] for founder,l,k in indices]);s=moments(train)
                x=np.vstack([dv[b,:,g],pv[:,:,g].reshape(4*npilot,-1)])
                distances=np.zeros((len(x),len(train)));active=np.flatnonzero(s['active'])
                for feature in active:distances+=np.square((x[:,feature,None]-train[None,:,feature])/s['sd'][feature])
                if len(active):distances/=len(active)
                nearest=np.argmin(distances,axis=1);distance=np.sqrt(distances[np.arange(len(x)),nearest])
                identities=np.asarray(indices,dtype=np.int64)[nearest]
                box=np.any(x<s['minimum'],axis=1)|np.any(x>s['maximum'],axis=1)
                assert arrays['active_dimensions'][b,g,j]==len(active)
                for co,part,shape in [('development',slice(0,4),(4,)),('pilot',slice(4,None),(npilot,4))]:
                    got=arrays[co+'_distance'][b,...,g,j];want=distance[part].reshape(shape)
                    same(got,want);maximum=max(maximum,float(np.max(abs(got-want))));checked+=got.size
                    np.testing.assert_array_equal(arrays[co+'_box'][b,...,g,j],box[part].reshape(shape))
                    for column,key in enumerate(('neighbor_founder','neighbor_life','neighbor_view')):
                        np.testing.assert_array_equal(arrays[co+'_'+key][b,...,g,j],identities[part,column].reshape(shape))
    return dict(passes=True,nearest_distances=checked,max_distance_error=maximum,
                scalar_case_positions=73*16*(nd+nd*npilot),outcomes_used=False)


def quantile(x,q):
    values=np.sort(x.ravel());position=(len(values)-1)*q;lo=int(position);hi=min(lo+1,len(values)-1)
    return float(values[lo]+(position-lo)*(values[hi]-values[lo]))


def raw(x):
    mean=float(x.sum()/x.size)
    return dict(mean=mean,sd=float(np.sqrt(np.sum((x-mean)**2)/x.size)),minimum=float(np.amin(x)),maximum=float(np.amax(x)))


def summary(s,arrays,d,p,di,pi):
    assert s['schema']=='d166_feature_support_v1'
    assert s['development_ids']==di.tolist() and s['pilot_ids']==pi.tolist()
    assert s['reference_blocks']==[di[di!=b].tolist() for b in di]
    assert s['groups']==list(m.GROUPS) and s['scalar_names']==list(m.SCALARS) and s['views']==m.view_specs()
    assert s['development_founders']==len(di) and s['pilot_founders']==len(pi)
    assert s['development_cases']==16*len(di) and s['pilot_cases']==16*len(pi) and s['references']==len(di)
    assert s['scalar_group_rows']==len(s['scalar_rows'])==292 and s['vector_group_rows']==len(s['vector_rows'])==88
    assert s['constant_sd_tolerance']==1e-12
    for key in ('independent_references','prospective_evidence','confidence_intervals','outcomes_used','forecasts_used','automatic_successor'):assert s[key] is False
    for key in ('post_test_explanation','all_cases_retained','source_primary_unchanged'):assert s[key] is True
    for key in ('new_fits','new_forecasts','new_dynamics','new_diagnostic_cycles','new_founders'):assert s[key]==0
    ds,ps=scalar_matrix(d),scalar_matrix(p)
    for g,group in enumerate(m.GROUPS):
        for j,name in enumerate(m.SCALARS):
            r=s['scalar_rows'][g*73+j];assert r['group']==group and r['feature']==name
            rd,rp=raw(ds[:,:,g,j]),raw(ps[:,:,g,j]);same(r['development_raw'],rd);same(r['pilot_raw'],rp)
            scale=rd['sd'];same(r['standardized_mean_shift'],(rp['mean']-rd['mean'])/scale if scale>1e-12 else None)
            same(r['sd_ratio'],rp['sd']/scale if scale>1e-12 else None)
            active=arrays['reference_active'][:,g,j];assert r['active_references']==np.count_nonzero(active)
            for co in ('development','pilot'):
                z=arrays[co+'_z'][...,g,j];side=arrays[co+'_side'][...,g,j];v=z[active].ravel();outside=side!=0
                expected=dict(below=np.count_nonzero(side<0)/side.size,above=np.count_nonzero(side>0)/side.size,
                    outside=np.count_nonzero(outside)/side.size,standardized_mean=float(v.sum()/len(v)) if len(v) else None,
                    standardized_rms=float(np.sqrt(np.dot(v,v)/len(v))) if len(v) else None,standardized_instances=len(v),
                    founder_outside=[float(outside[:,b].sum()/(len(di)*4)) for b in range(len(pi))] if co=='pilot' else
                        [float(v.sum()/4) for v in outside],reference_outside=[float(v.sum()/v.size) for v in outside])
                same(r[co],expected)
            same(r['outside_rate_change'],r['pilot']['outside']-r['development']['outside'])
        for j,spec in enumerate(m.view_specs()):
            r=s['vector_rows'][g*22+j];assert r['group']==group and all(r[k]==v for k,v in spec.items())
            assert r['active_dimensions']==arrays['active_dimensions'][:,g,j].tolist()
            for co in ('development','pilot'):
                v=arrays[co+'_distance'][...,g,j];b=arrays[co+'_box'][...,g,j]
                expected=dict(mean=float(v.sum()/v.size),median=quantile(v,.5),q90=quantile(v,.9),maximum=float(np.amax(v)),
                    box_outside=np.count_nonzero(b)/b.size,reference_distance=[float(x.sum()/x.size) for x in v],
                    reference_box=[float(x.sum()/x.size) for x in b],
                    founder_distance=[float(v[:,k].sum()/(len(di)*4)) for k in range(len(pi))] if co=='pilot' else [float(x.sum()/4) for x in v],
                    founder_box=[float(b[:,k].sum()/(len(di)*4)) for k in range(len(pi))] if co=='pilot' else [float(x.sum()/4) for x in b])
                same(r[co],expected)
            same(r['mean_distance_change'],r['pilot']['mean']-r['development']['mean'])
            same(r['mean_distance_ratio'],r['pilot']['mean']/r['development']['mean'] if r['development']['mean'] else None)
            same(r['box_rate_change'],r['pilot']['box_outside']-r['development']['box_outside'])
    return dict(passes=True,scalar_group_rows=292,vector_group_rows=88,all_cases_retained=True,outcomes_used=False)
