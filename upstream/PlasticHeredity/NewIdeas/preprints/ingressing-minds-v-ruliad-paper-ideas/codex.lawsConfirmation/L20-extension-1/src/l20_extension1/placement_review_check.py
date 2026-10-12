"""Independent saved-field features, integer score partitions and summaries."""
import numpy as np

KINDS=('intact','copy','read_off','write_off')
CASES=tuple((r,p,a,k) for r in (0,1) for p in (1000,1300) for a in (1000,1300) for k in KINDS)
PAIRS=(('content_at_early',2,0),('content_at_late',3,1),('placement_on_early',1,0),
       ('earlier_placement_on_late',2,3),('natural_change',3,0))
FIELDS=('mean','rms','centered_rms','canonical_own','canonical_alternative','canonical_margin',
        'best_own','best_alternative','best_margin','own_axis_energy','alternative_axis_energy',
        'residual_energy','continuous_margin','projection_own','projection_alternative')
yy,xx=np.indices((16,16))
T=np.array([np.where(yy<8,1.,-1.),np.where(xx%8<4,1.,-1.)])


def same(a,b):
    if isinstance(b,dict):
        assert set(a)==set(b)
        for key in b:same(a[key],b[key])
    elif isinstance(b,(list,tuple)):
        assert len(a)==len(b)
        for x,y in zip(a,b):same(x,y)
    elif isinstance(b,(float,np.floating)):
        assert np.isfinite(a) and abs(a-b)<=1e-11,(a,b)
    else:assert a==b,(a,b)


def measure(v,role):
    assert v.shape[-2:]==(16,16) and np.isfinite(v).all()
    mu=np.sum(v,axis=(-2,-1))/256;z=v-mu[...,None,None]
    energy=np.sum(z*z,axis=(-2,-1))/256;sd=np.sqrt(energy)
    cv=np.sum(z[...,None,:,:]*T,axis=(-2,-1))/256
    canon=np.zeros_like(cv);np.divide(cv,sd[...,None],out=canon,where=sd[...,None]>0)
    cc=np.fft.ifft2(np.fft.fft2(z)[...,None,:,:]*np.conj(np.fft.fft2(T))).real
    maxima=np.max(cc,axis=(-2,-1))/256;best=np.zeros_like(maxima)
    np.divide(maxima,sd[...,None],out=best,where=sd[...,None]>0)
    a=np.sum(z,axis=-1)/16;b=np.sum(z,axis=-2)/16
    row=np.sum(a*a,axis=-1)/16;column=np.sum(b*b,axis=-1)/16
    powers=(row,column)
    return np.stack((mu,np.sqrt(np.sum(v*v,axis=(-2,-1))/256),sd,canon[...,role],canon[...,1-role],
        canon[...,role]-canon[...,1-role],best[...,role],best[...,1-role],best[...,role]-best[...,1-role],
        powers[role],powers[1-role],energy-row-column,(cv[...,role]-cv[...,1-role])*.5,cv[...,role],cv[...,1-role]),-1)


def states(v,role):
    selected=T[0]!=T[1];u=v[...,selected]
    own=(u>.2)&(T[role][selected]>0)|(u<-.2)&(T[role][selected]<0)
    alt=(u>.2)&(T[1-role][selected]>0)|(u<-.2)&(T[1-role][selected]<0)
    assert not np.any(own&alt)
    return own.astype(np.int64)+2*alt.astype(np.int64)


def tables(left,right):
    encoded=(3*right+left).reshape(-1,128)
    return np.stack([np.bincount(row,minlength=9).reshape(3,3) for row in encoded]).reshape(left.shape[:-1]+(3,3))


def contributions(matrix):
    weight=(0,1,-1);output=np.zeros(matrix.shape[:-2]+(4,),np.int64)
    for old in range(3):
        for new in range(3):
            delta=weight[new]-weight[old]
            category=1 if old==0 else 2 if new==0 else 0
            output[...,category]+=matrix[...,old,new]*delta
            output[...,3]+=matrix[...,old,new]*delta
    return output


def cell_indices(role,kind):
    k=KINDS.index(kind)
    return [role*16+k+offset for offset in (0,4,8,12)]


def reconstruct(raw):
    assert raw['terminal_states'].shape==(4,2,32,3,4,3,16,16)
    fields=np.empty((4,2,32,3,4,3,15));record=np.empty((4,2,32,3,2,15))
    count=np.empty((4,2,32,3,4,3),np.int64);states_by_case=[]
    for ci in range(32):
        role=ci//16;v=raw['terminal_states'][:,:,ci]
        fields[:,:,ci]=measure(v,role)
        for j,key in enumerate(('packet','terminal_packet')):
            a=raw[key][:,:,ci];assert a.shape==(4,2,3,2048) and a.dtype==np.uint8
            value=np.array([np.frombuffer(p.tobytes(),'<f8').reshape(16,16) for p in a.reshape(-1,2048)]).reshape(4,2,3,16,16)
            record[:,:,ci,:,j]=measure(value,role)
        c=states(v[...,0,:,:],role);states_by_case.append(c)
        count[:,:,ci]=np.stack([np.count_nonzero(c==k,axis=-1) for k in range(3)],-1)
    transition=np.empty((4,2,8,3,5,4,3,3),np.int64)
    for role in (0,1):
        for ki,kind in enumerate(KINDS):
            q=cell_indices(role,kind)
            for pi,(_,a,b) in enumerate(PAIRS):transition[:,:,4*role+ki,:,pi]=tables(states_by_case[q[a]],states_by_case[q[b]])
    return dict(fields=fields,records=record,counts=count,transitions=transition)


def check_block(actual,raw):
    expected=reconstruct(raw);assert set(actual)==set(expected)
    for key,value in expected.items():
        assert actual[key].shape==value.shape and actual[key].dtype==value.dtype
        if value.dtype==np.int64:np.testing.assert_array_equal(actual[key],value)
        else:np.testing.assert_allclose(actual[key],value,atol=1e-11,rtol=0)
    c=actual['counts'];assert np.all(c.sum(axis=-1)==128)
    np.testing.assert_array_equal((c[...,1]-c[...,2])/256,raw['terminal_values'][...,0])
    r=actual['records'];f=actual['fields']
    for j,route,k in ((0,0,6),(1,0,8),(3,0,7),(4,1,3),(5,1,4),(6,1,5)):
        np.testing.assert_allclose(r[...,route,k],raw['record_values'][...,j],atol=1e-11,rtol=0)
    np.testing.assert_allclose(f[...,2,6],raw['terminal_values'][...,1],atol=1e-11,rtol=0)
    assert np.all(actual['transitions'].sum(axis=(-2,-1))==128)
    return dict(passes=True,labelled_cells=768,field_checkpoints=9216,packet_fields=1536,score_transition_tables=3840,new_dynamics=0)


def describe(v):
    assert v.shape==(16,4,2)
    means=v.sum(axis=(1,2))/8
    return dict(mean=float(v.sum()/128),block_means=means.tolist(),positive=int(np.count_nonzero(v>0)),
        negative=int(np.count_nonzero(v<0)),zero=int(np.count_nonzero(v==0)),positive_blocks=int(np.count_nonzero(means>0)),
        negative_blocks=int(np.count_nonzero(means<0)),zero_blocks=int(np.count_nonzero(means==0)))


def check_summary(summary,blocks,original,block_ids=tuple(range(93000,93016)),fixture=False):
    assert len(blocks)==16 and len(block_ids)==16
    if not fixture:assert list(block_ids)==list(range(93000,93016))
    data={k:np.stack([b[k] for b in blocks]) for k in ('fields','records','counts','transitions')}
    c=data['counts'];f=data['fields'];r=data['records'];t=data['transitions'];pref=(c[...,1]-c[...,2])/256
    groups=[];contrasts=[];adverse=[]
    for ci,(role,p,a,kind) in enumerate(CASES):
        for g in range(3):
            if not fixture:
                old=next(z for z in original['groups'] if (z['role'],z['packet_stop'],z['address_stop'],z['condition'],z['generation'])==(role,p,a,kind,g+1))
                np.testing.assert_array_equal(pref[...,ci,g,-1],old['metrics']['terminal_preference']['life_noise_values'])
            groups.append(dict(role=role,packet_stop=p,address_stop=a,condition=kind,generation=g+1,
                preference=describe(pref[...,ci,g,-1]),score_count_profile=np.sum(c[...,ci,g,:,:],axis=(0,1,2)).tolist(),
                field_profile=(np.sum(f[...,ci,g,:,:,:],axis=(0,1,2))/128).tolist(),
                record_fields=(np.sum(r[...,ci,g,:,:],axis=(0,1,2))/128).tolist()))
    for role in (0,1):
        for ki,kind in enumerate(KINDS):
            q=cell_indices(role,kind)
            for g in range(3):
                for pi,(name,a,b) in enumerate(PAIRS):
                    delta=pref[...,q[a],g,:]-pref[...,q[b],g,:];m=t[:,:,:,role*4+ki,g,pi]
                    units=contributions(m);np.testing.assert_array_equal(units[...,-1]/256,delta)
                    change=r[...,q[a],g,1,:]-r[...,q[b],g,1,:];loss=delta[...,-1]<0
                    flags=(change[...,6]>0)&loss if name in ('content_at_early','content_at_late') else np.zeros_like(loss)
                    flags_ids=[[int(block_ids[bi]),l,n] for bi in range(16) for l in range(4) for n in range(2) if flags[bi,l,n]]
                    values={'preference':delta[...,-1],
                        'continuous_margin':f[...,q[a],g,-1,0,12]-f[...,q[b],g,-1,0,12],
                        'body_canonical_margin':f[...,q[a],g,-1,0,5]-f[...,q[b],g,-1,0,5],
                        'reference_canonical_margin':f[...,q[a],g,-1,2,5]-f[...,q[b],g,-1,2,5],
                        'record_own_best':change[...,6],'record_alternative_best':change[...,7],'record_canonical_margin':change[...,5]}
                    if not fixture:
                        old=next(z for z in original['decompositions'] if (z['role'],z['condition'],z['generation'])==(role,kind,g+1))
                        np.testing.assert_array_equal(delta[...,-1],old['decomposition'][name]['terminal_preference']['life_noise_values'])
                    contrasts.append(dict(role=role,condition=kind,generation=g+1,contrast=name,
                        terminal={k:describe(v) for k,v in values.items()},preference_profile=(delta.sum(axis=(0,1,2))/128).tolist(),
                        transition_profile=m.sum(axis=(0,1,2)).tolist(),contribution_profile=(units.sum(axis=(0,1,2))/(128*256)).tolist(),
                        declining_cases=int(np.count_nonzero(loss)),declining_case_net_units=units[...,-1,:][loss].sum(axis=0).tolist(),
                        own_shape_up_score_down_ids=flags_ids,flagged_alternative_shape_up=int(np.count_nonzero(flags&(change[...,7]>0))),
                        flagged_canonical_margin_down=int(np.count_nonzero(flags&(change[...,5]<0)))))
    for bi,index in enumerate(block_ids):
        for life in range(4):
            for noise in (0,1):
                for role in (0,1):
                    q=cell_indices(role,'intact')
                    for g in range(3):
                        v=[float(pref[bi,life,noise,ci,g,-1]) for ci in q]
                        if min(v)<=0:
                            adverse.append(dict(index=index,life=life,noise=noise,role=role,generation=g+1,preferences=v,
                                counts=np.stack([c[bi,life,noise,ci,g] for ci in q]).tolist(),
                                fields=np.stack([f[bi,life,noise,ci,g] for ci in q]).tolist(),
                                records=np.stack([r[bi,life,noise,ci,g] for ci in q]).tolist(),
                                transitions=t[bi,life,noise,role*4,g].tolist()))
    expected=dict(schema='d148_saved_content_review_v1',posthoc=True,new_dynamics=0,new_thresholds=0,refits=0,
        prospective_evidence=False,all_cases_retained=True,independent_blocks=16,labelled_cells=12288,times=[0,1,100,300],
        field_order=['V','M','R'],fields=list(FIELDS),score_states=['quiet','own','alternative'],transition_axes=['baseline','intervention'],
        contribution_order=['both_active_sign','activation','deactivation','net'],packet_order=['raw','routed'],cell_order=['EE','EL','LE','LL'],
        groups=groups,contrasts=contrasts,adverse_intact=adverse,original_primary=original['primary'],
        original_primary_classification=original['primary_interval_classification'],original_apparatus_passes=original['apparatus_qualified'],
        original_controls=len(original['controls']),fixture=fixture,scientific_evidence=not fixture)
    same(summary,expected)
    return dict(passes=True,groups=96,contrasts=120,independent_blocks=16,all_cases_retained=True,
        adverse_intact_endpoints=len(adverse),original_primary_unchanged=True,new_dynamics=0,new_thresholds=0)
