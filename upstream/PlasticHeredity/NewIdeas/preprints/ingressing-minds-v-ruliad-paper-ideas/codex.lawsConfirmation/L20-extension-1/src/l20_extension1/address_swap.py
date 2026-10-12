"""D169 matched address intervention; body and RNG owner never follow donor."""
from dataclasses import asdict
import numpy as np
from laws_confirmation import l20_guide_renewal as old
from . import diagnostics as features, passive_stages as stages

IDS={'development':tuple(range(90000,90016)), 'pilot':tuple(range(100000,100064)), 'disposable':(514240,)}
GROUPS=stages.GROUPS
RESPONSES=('write_R_change:0','write_R_change:1','write_R_change:300','write_R_change:1000',
           'outgoing_own','outgoing_guide','final_preference')
CONTRASTS=('original_gap','swapped_gap','address','background','interaction','address_at_U0','address_at_U1')
CELLS=tuple((g,c,a) for g in range(4) for c in range(2) for a in range(2))
LEVELS=(tuple(np.arange(-4,5)/4),tuple(np.arange(-2,3)/2))
SHAPES=dict(start=(4,2,3,16,16),donor_shift=(4,2,2),guide=(2,16,16),
    write_states=(4,2,2,4,4,16,16),terminal_states=(4,2,2,4,3,16,16),
    outgoing=(4,2,2,2048),terminal_packet=(4,2,2,2048),scores=(4,2,2,2,16,16),
    response=(4,2,2,7),q=(4,2))


def tag(co,index):
    assert co in IDS and type(index) is int and index in IDS[co]
    return 'l20-extension1-'+('heldout-v1' if co=='development' else 'pilot64-v1')+':diagnostics:'+(
        'disposable' if co=='disposable' else 'heldout')


def draw(co,index,life,copy,phase):
    assert type(life) is int and 0<=life<4 and type(copy) is int and copy in (0,1)
    assert phase in ('shift','write','final_birth','final_read')
    return old.generator(tag(co,index),index,life,f'trial{copy}:{phase}')


def best(field,role):
    x=field-field.mean();sd=x.std()
    if not sd:return 0.
    t=stages.targets()[role]
    return float((np.fft.ifft2(np.fft.fft2(x)*np.conj(np.fft.fft2(t))).real/(256*sd)).max())


def response(writes,outgoing,terminal,role,guide):
    base=best(writes[0,2],role)
    record=features.record_features(outgoing,role,guide)
    return np.array([best(w[2],role)-base for w in writes]+[record[0],record[2],
        features.terminal_features(terminal[-1,0],role)[0]],dtype=np.float64)


def validate_inputs(start,shift,guide):
    assert start.shape==(4,2,3,16,16) and start.dtype==np.float64 and np.isfinite(start).all()
    assert shift.shape==(4,2,2) and shift.dtype==np.int64 and np.all((shift>=0)&(shift<16))
    assert not np.any(np.all(shift==0,axis=-1))
    for g in range(4):np.testing.assert_array_equal(shift[g],shift[0])
    for a,b in ((0,1),(2,3)):np.testing.assert_array_equal(start[a],start[b])
    features.validate_guide(guide)


def validate(raw,lives=None):
    assert set(raw)==set(SHAPES)
    for k,shape in SHAPES.items():
        x=raw[k];want=((lives,)+shape) if lives is not None else shape
        assert x.shape==want and x.dtype==(np.uint8 if k in ('outgoing','terminal_packet') else
            np.int64 if k=='donor_shift' else np.float64) and np.isfinite(x).all(),k


def simulate_life(start,shift,guide,co,index,life,order=CELLS):
    validate_inputs(start,shift,guide);namespace=tag(co,index)
    assert len(order)==16 and set(order)==set(CELLS)
    ctx=old.context(index)
    raw={k:np.empty(s,dtype=np.uint8 if k in ('outgoing','terminal_packet') else
        np.int64 if k=='donor_shift' else np.float64) for k,s in SHAPES.items()}
    raw.update(start=start.copy(),donor_shift=shift.copy(),guide=guide.copy())
    entries={}
    for g in range(4):
        template=stages.targets()[g//2]
        for a in range(2):raw['q'][g,a]=np.mean(template*np.roll(template,tuple(shift[g,a]),(0,1)))
    for g,c,a in order:
        mode='translated' if g%2==0 else 'aligned'
        writes,wm=old.write_streams(start[g,c],ctx,draw(co,index,life,c,'write'),mode,shift[g,a],old.CONFIG)
        outgoing=old.encode(old.record(writes[-1,2]))
        packet,scores,selector=old.route(outgoing,'learned',guide)
        terminal,rm=old.read_selected(packet,ctx,draw(co,index,life,c,'final_birth'),
            draw(co,index,life,c,'final_read'),old.CONFIG,times=old.CONFIG.times)
        for k,v in dict(write_states=writes,terminal_states=terminal,outgoing=np.frombuffer(outgoing,np.uint8),
            terminal_packet=np.frombuffer(packet,np.uint8),scores=scores,
            response=response(writes,outgoing,terminal,g//2,guide)).items():raw[k][g,c,a]=v
        entries[g,c,a]=dict(body_copy=c,address_donor=a,mode=mode,writer=wm,selector=selector,reader=rm)
    validate(raw)
    meta=dict(cohort=co,index=index,life=life,tag=namespace,config=asdict(old.CONFIG),
        host=dict(index=index,tissue=asdict(ctx['tissue']),ladder=asdict(ctx['ladder']),blueprint=asdict(ctx['bp'])),
        cells=[entries[cell] for cell in CELLS],guide_sha256=old.GUIDE_SHA256,
        initial_reader_replayed=False,actual_lineage_outcomes_used=False,only_address_changed=True)
    return raw,meta


def contrasts(y):
    assert y.shape[-2:]==(2,2)
    z00,z01,z10,z11=y[...,0,0],y[...,0,1],y[...,1,0],y[...,1,1]
    e0,e1=z01-z00,z11-z10
    return np.stack((z11-z00,z10-z01,(e0+e1)/2,
        ((z10-z00)+(z11-z01))/2,e1-e0,e0,e1),-1)


def describe(founder,draws):
    assert founder.ndim==1 and len(founder)>1
    boot=founder[draws].mean(axis=1);omits=(founder.sum()-founder)/(len(founder)-1)
    return dict(mean=float(founder.mean()),founder_values=founder.tolist(),
        pointwise_founder_bootstrap_95=np.percentile(boot,[2.5,97.5]).tolist(),
        positive=int((founder>1e-12).sum()),negative=int((founder<-1e-12).sum()),
        numerical_zero=int((abs(founder)<=1e-12).sum()),omitted_means=omits.tolist(),
        omission_minimum=float(omits.min()),omission_maximum=float(omits.max()))


def summarize(panels,ids):
    assert set(panels)==set(ids)=={'development','pilot'}
    rows=[];support=[]
    for ci,co in enumerate(('development','pilot')):
        a=panels[co];n=len(ids[co]);y=a['response'];q=a['q']
        assert n>1 and len(set(ids[co]))==n
        assert y.shape==(n,4,4,2,2,7) and q.shape==(n,4,4,2)
        assert y.dtype==q.dtype==np.float64 and np.isfinite(y).all() and np.isfinite(q).all()
        draws=np.random.default_rng(16920260922+ci).integers(0,n,(20000,n))
        for g,group in enumerate(GROUPS):
            effects=contrasts(np.moveaxis(y[:,:,g],-1,-3))  # N,life,response,contrast
            for k,name in enumerate(RESPONSES):
                cell=y[:,:,g,:,:,k];values=effects[:,:,k]
                assert np.allclose(values[...,0],values[...,2]+values[...,3],atol=2e-12,rtol=0)
                assert np.allclose(values[...,1],values[...,3]-values[...,2],atol=2e-12,rtol=0)
                rows.append(dict(cohort=co,group=group,response=name,cell_mean=cell.mean((0,1)).tolist(),
                    founder_cell_mean=cell.mean(1).tolist(),contrasts={label:describe(values[...,j].mean(1),draws)
                    for j,label in enumerate(CONTRASTS)}))
            for q0 in LEVELS[g//2]:
                for q1 in LEVELS[g//2]:
                    mask=(q[:,:,g,0]==q0)&(q[:,:,g,1]==q1);counts=mask.sum(1)
                    picked=effects[mask];sums=np.sum(np.where(mask[...,None,None],effects,0),axis=1)
                    support.append(dict(cohort=co,group=group,q0=float(q0),q1=float(q1),cases=int(mask.sum()),
                        founders=int(np.count_nonzero(counts)),founder_counts=counts.tolist(),
                        founder_contrast_sums=sums.tolist(),
                        contrast_means=picked.mean(0).tolist() if len(picked) else [[None]*7 for _ in range(7)]))
    return dict(schema='d169_address_swap_v1',ids={k:list(v) for k,v in ids.items()},groups=list(GROUPS),
        responses=list(RESPONSES),contrasts=list(CONTRASTS),rows=rows,q_pair_rows=support,
        bootstrap_seeds=[16920260922,16920260923],bootstrap_resamples=20000,
        primary_focus=['development','B_ordinary','outgoing_own','address'],all_cases_retained=True,
        actual_lineage_outcomes_used=False,new_fits=0,new_forecasts=0,new_founders=0,
        post_test_intervention=True,prospective_prediction_evidence=False,
        conditional_on_saved_bodies_noise_and_guide=True,source_primary_unchanged=True,
        multiplicity_adjusted=False,equivalence_test=False,automatic_successor=False)
