"""Post-hoc D148 raw-field accounting; no dynamics, fitting or new threshold."""
import numpy as np

KINDS=('intact','copy','read_off','write_off')
CASES=tuple((r,p,a,k) for r in (0,1) for p in (1000,1300) for a in (1000,1300) for k in KINDS)
TIMES=(0,1,100,300)
PAIRS=(('content_at_early',2,0),('content_at_late',3,1),('placement_on_early',1,0),
       ('earlier_placement_on_late',2,3),('natural_change',3,0))
FIELDS=('mean','rms','centered_rms','canonical_own','canonical_alternative','canonical_margin',
        'best_own','best_alternative','best_margin','own_axis_energy','alternative_axis_energy',
        'residual_energy','continuous_margin','projection_own','projection_alternative')
STATES=('quiet','own','alternative')
y,x=np.indices((16,16))
TARGETS=np.stack((np.where(y<8,1.,-1.),np.where(x%8<4,1.,-1.)))
BANK=np.stack([np.roll(TARGETS[0],i,axis=0) for i in range(16)]+
              [np.roll(TARGETS[1],i,axis=1) for i in range(8)]).reshape(24,256)
DISAGREE=TARGETS[0]!=TARGETS[1]


def measure(value,role):
    value=np.asarray(value)
    if value.shape[-2:]!=(16,16) or not np.isfinite(value).all() or role not in (0,1):
        raise ValueError('finite 16x16 fields and a declared role required')
    mean=value.mean(axis=(-2,-1));z=value-mean[...,None,None]
    var=np.mean(z*z,axis=(-2,-1));sd=np.sqrt(var)
    cov=(z.reshape(-1,256)@BANK.T/256).reshape(value.shape[:-2]+(24,))
    corr=np.divide(cov,sd[...,None],out=np.zeros_like(cov),where=sd[...,None]!=0)
    canonical=np.stack((corr[...,0],corr[...,16]),-1)
    projection=np.stack((cov[...,0],cov[...,16]),-1)
    best=np.stack((corr[...,:16].max(axis=-1),corr[...,16:].max(axis=-1)),-1)
    row=z.mean(axis=-1);col=z.mean(axis=-2)
    axis=np.stack((np.mean(row*row,axis=-1),np.mean(col*col,axis=-1)),-1)
    residual=z-row[...,None]-col[...,None,:]
    energy=np.mean(residual*residual,axis=(-2,-1))
    np.testing.assert_allclose(axis.sum(axis=-1)+energy,var,atol=2e-14,rtol=1e-13)
    return np.stack((mean,np.sqrt(np.mean(value*value,axis=(-2,-1))),sd,
        canonical[...,role],canonical[...,1-role],canonical[...,role]-canonical[...,1-role],
        best[...,role],best[...,1-role],best[...,role]-best[...,1-role],
        axis[...,role],axis[...,1-role],energy,(projection[...,role]-projection[...,1-role])/2,
        projection[...,role],projection[...,1-role]),-1)


def codes(v,role):
    v=np.asarray(v)
    if v.shape[-2:]!=(16,16) or not np.isfinite(v).all() or role not in (0,1):raise ValueError('finite field required')
    u=v[...,DISAGREE];active=abs(u)>.2
    own=(u>0)==(TARGETS[role][DISAGREE]>0)
    return np.where(active,np.where(own,1,2),0).astype(np.int8)


def transitions(left,right):
    if left.shape!=right.shape or left.shape[-1]!=128:raise ValueError('128 paired disagreement positions required')
    if not np.isin(left,(0,1,2)).all() or not np.isin(right,(0,1,2)).all():raise ValueError('three declared categories required')
    return np.stack([np.stack([np.sum((right==i)&(left==j),axis=-1) for j in range(3)],-1) for i in range(3)],-2)


def parts(t):
    both=2*(t[...,2,1]-t[...,1,2]);activation=t[...,0,1]-t[...,0,2]
    deactivation=t[...,2,0]-t[...,1,0]
    return np.stack((both,activation,deactivation,both+activation+deactivation),-1)


def indices(role,kind):return tuple(CASES.index((role,p,a,kind)) for p in (1000,1300) for a in (1000,1300))


def extract(raw):
    assert raw['terminal_states'].shape==(4,2,32,3,4,3,16,16)
    assert raw['packet'].shape==raw['terminal_packet'].shape==(4,2,32,3,2048)
    fields=np.empty((4,2,32,3,4,3,15));records=np.empty((4,2,32,3,2,15))
    counts=np.empty((4,2,32,3,4,3),np.int64);cc=[]
    for ci,(role,_,_,_) in enumerate(CASES):
        fields[:,:,ci]=measure(raw['terminal_states'][:,:,ci],role)
        for j,key in enumerate(('packet','terminal_packet')):
            p=raw[key][:,:,ci];assert p.dtype==np.uint8
            field=np.frombuffer(p.tobytes(),'<f8').reshape(p.shape[:-1]+(16,16))
            records[:,:,ci,:,j]=measure(field,role)
        c=codes(raw['terminal_states'][:,:,ci,:,:,0],role);cc.append(c)
        counts[:,:,ci]=np.stack([(c==k).sum(axis=-1) for k in range(3)],-1)
    pref=(counts[...,1]-counts[...,2])/256
    np.testing.assert_array_equal(pref,raw['terminal_values'][...,0])
    np.testing.assert_allclose(fields[...,2,6],raw['terminal_values'][...,1],atol=1e-12,rtol=0)
    for col,route,col2 in ((0,0,6),(1,0,8),(3,0,7),(4,1,3),(5,1,4),(6,1,5)):
        np.testing.assert_allclose(raw['record_values'][...,col],records[...,route,col2],atol=1e-12,rtol=0)
    tables=np.empty((4,2,8,3,5,4,3,3),np.int64)
    for role in (0,1):
        for ki,kind in enumerate(KINDS):
            q=indices(role,kind)
            for pi,(_,a,b) in enumerate(PAIRS):
                table=transitions(cc[q[a]],cc[q[b]]);tables[:,:,role*4+ki,:,pi]=table
                np.testing.assert_array_equal(parts(table)[...,-1]/256,pref[:,:,q[a]]-pref[:,:,q[b]])
    return dict(fields=fields,records=records,counts=counts,transitions=tables)


def describe(v):
    v=np.asarray(v)
    assert v.shape==(16,4,2) and np.isfinite(v).all()
    b=v.mean(axis=(1,2))
    return dict(mean=float(v.mean()),block_means=b.tolist(),positive=int((v>0).sum()),negative=int((v<0).sum()),zero=int((v==0).sum()),
        positive_blocks=int((b>0).sum()),negative_blocks=int((b<0).sum()),zero_blocks=int((b==0).sum()))


def identities(mask,blocks):
    return [[blocks[b],int(l),int(n)] for b,l,n in np.argwhere(mask)]


def summarize(blocks,original,block_ids=tuple(range(93000,93016)),fixture=False):
    assert len(blocks)==len(block_ids)==16
    if not fixture:assert tuple(block_ids)==tuple(range(93000,93016))
    data={k:np.stack([b[k] for b in blocks]) for k in blocks[0]}
    c=data['counts'];pref=(c[...,1]-c[...,2])/256;f=data['fields'];r=data['records'];t=data['transitions']
    groups=[];contrasts=[];adverse=[]
    for ci,(role,p,a,kind) in enumerate(CASES):
        for gi in range(3):
            if not fixture:
                prior=next(x for x in original['groups'] if (x['role'],x['packet_stop'],x['address_stop'],x['condition'],x['generation'])==(role,p,a,kind,gi+1))
                np.testing.assert_array_equal(pref[...,ci,gi,-1],prior['metrics']['terminal_preference']['life_noise_values'])
            groups.append(dict(role=role,packet_stop=p,address_stop=a,condition=kind,generation=gi+1,
                preference=describe(pref[...,ci,gi,-1]),score_count_profile=c[...,ci,gi,:,:].sum(axis=(0,1,2)).tolist(),
                field_profile=f[...,ci,gi,:,:,:].mean(axis=(0,1,2)).tolist(),record_fields=r[...,ci,gi,:,:].mean(axis=(0,1,2)).tolist()))
    for role in (0,1):
        for ki,kind in enumerate(KINDS):
            q=indices(role,kind)
            for gi in range(3):
                for pi,(name,a,b) in enumerate(PAIRS):
                    delta=pref[...,q[a],gi,:]-pref[...,q[b],gi,:];table=t[:,:,:,role*4+ki,gi,pi]
                    unit=parts(table);loss=delta[...,-1]<0
                    record_change=r[...,q[a],gi,1,:]-r[...,q[b],gi,1,:]
                    flags=(record_change[...,6]>0)&loss if name.startswith('content_') else np.zeros_like(loss)
                    measurements={'preference':delta[...,-1],
                        'continuous_margin':f[...,q[a],gi,-1,0,12]-f[...,q[b],gi,-1,0,12],
                        'body_canonical_margin':f[...,q[a],gi,-1,0,5]-f[...,q[b],gi,-1,0,5],
                        'reference_canonical_margin':f[...,q[a],gi,-1,2,5]-f[...,q[b],gi,-1,2,5],
                        'record_own_best':record_change[...,6],'record_alternative_best':record_change[...,7],
                        'record_canonical_margin':record_change[...,5]}
                    if not fixture:
                        old=next(x for x in original['decompositions'] if (x['role'],x['condition'],x['generation'])==(role,kind,gi+1))
                        np.testing.assert_array_equal(delta[...,-1],old['decomposition'][name]['terminal_preference']['life_noise_values'])
                    contrasts.append(dict(role=role,condition=kind,generation=gi+1,contrast=name,
                        terminal={k:describe(v) for k,v in measurements.items()},preference_profile=delta.mean(axis=(0,1,2)).tolist(),
                        transition_profile=table.sum(axis=(0,1,2)).tolist(),contribution_profile=(unit.mean(axis=(0,1,2))/256).tolist(),
                        declining_cases=int(loss.sum()),declining_case_net_units=unit[...,-1,:][loss].sum(axis=0).tolist(),
                        own_shape_up_score_down_ids=identities(flags,block_ids),
                        flagged_alternative_shape_up=int(np.sum(flags&(record_change[...,7]>0))),
                        flagged_canonical_margin_down=int(np.sum(flags&(record_change[...,5]<0)))))
    for bi,index in enumerate(block_ids):
        for life in range(4):
            for noise in (0,1):
                for role in (0,1):
                    q=indices(role,'intact')
                    for gi in range(3):
                        scores=np.array([pref[bi,life,noise,j,gi,-1] for j in q])
                        if np.any(scores<=0):
                            adverse.append(dict(index=index,life=life,noise=noise,role=role,generation=gi+1,
                                preferences=scores.tolist(),counts=c[bi,life,noise,q,gi].tolist(),
                                fields=f[bi,life,noise,q,gi].tolist(),records=r[bi,life,noise,q,gi].tolist(),
                                transitions=t[bi,life,noise,role*4,gi].tolist()))
    return dict(schema='d148_saved_content_review_v1',posthoc=True,new_dynamics=0,new_thresholds=0,refits=0,
        prospective_evidence=False,all_cases_retained=True,independent_blocks=16,labelled_cells=12288,
        times=list(TIMES),field_order=['V','M','R'],fields=list(FIELDS),score_states=list(STATES),
        transition_axes=['baseline','intervention'],contribution_order=['both_active_sign','activation','deactivation','net'],
        packet_order=['raw','routed'],cell_order=['EE','EL','LE','LL'],groups=groups,contrasts=contrasts,adverse_intact=adverse,
        original_primary=original['primary'],original_primary_classification=original['primary_interval_classification'],
        original_apparatus_passes=original['apparatus_qualified'],original_controls=len(original['controls']),
        fixture=fixture,scientific_evidence=not fixture)
