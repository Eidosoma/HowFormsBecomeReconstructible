"""D167: descriptive algebra on saved passive copies; no dynamics or outcomes."""
import numpy as np

GROUPS=('A_ordinary','A_aligned','B_ordinary','B_aligned')
READ=(0,1,100,101,300);WRITE=(0,1,300,1000);FINAL=(0,1,100,300)
METRICS=('own_best','alternative_best','guide_margin','canonical_margin','rms')
STAGES=('input','routed')+tuple(f'read:{t}:{k}' for t in READ for k in ('V','ema','R'))+tuple(
    f'write:{t}:{k}' for t in WRITE for k in ('V','ema','R','theta'))+(
    'tanh_write_R','outgoing','terminal_packet')+tuple(f'final:{t}:{k}' for t in FINAL for k in ('V','ema','R'))
CHAIN=('input','routed')+tuple(f'read:{t}:R' for t in READ)+tuple(f'write:{t}:R' for t in WRITE)+(
    'tanh_write_R','outgoing','terminal_packet')
SIGN_TOL=1e-12
SHAPES={k:(4,4,2,2048) for k in ('input','routed','outgoing','terminal_packet')}
SHAPES.update(read_states=(4,4,2,5,3,16,16),write_states=(4,4,2,4,4,16,16),
    terminal_states=(4,4,2,4,3,16,16),scores=(4,4,2,2,2,16,16),shift=(4,4,2,2),
    founder_packets=(4,2,2048),guide=(4,2,16,16),initial_features=(4,4,4),diagnostic_features=(4,4,2,6))
PACKETS=('input','routed','outgoing','terminal_packet','founder_packets')


def targets():
    y,x=np.indices((16,16))
    return np.stack((np.where(y<8,1.,-1.),np.where(x%8<4,1.,-1.)))


def validate(raw):
    assert set(raw)==set(SHAPES)
    for k,shape in SHAPES.items():
        x=raw[k];assert isinstance(x,np.ndarray) and x.shape==shape
        assert x.dtype==(np.uint8 if k in PACKETS else np.int64 if k=='shift' else np.float64)
        assert np.isfinite(x).all()
    assert np.all(raw['guide'].std(axis=(-2,-1))>1e-9)


def decode(packet):
    assert packet.dtype==np.uint8 and packet.shape[-1]==2048
    result=np.ascontiguousarray(packet).view('<f8').reshape(packet.shape[:-1]+(16,16))
    assert np.isfinite(result).all()
    return result


def fields(raw):
    validate(raw);rows=[decode(raw[k]) for k in ('input','routed')]
    for name,count,width in (('read_states',5,3),('write_states',4,4)):
        rows += [raw[name][...,t,k,:,:] for t in range(count) for k in range(width)]
    rows += [np.tanh(raw['write_states'][...,-1,2,:,:]),decode(raw['outgoing']),decode(raw['terminal_packet'])]
    rows += [raw['terminal_states'][...,t,k,:,:] for t in range(4) for k in range(3)]
    result=np.stack(rows,axis=3)
    assert result.shape==(4,4,2,48,16,16)
    return result


def measurements(x,guide):
    assert x.shape==(4,4,2,48,16,16) and guide.shape==(4,2,16,16)
    centered=x-x.mean(axis=(-2,-1),keepdims=True);sd=centered.std(axis=(-2,-1))
    nonzero=sd>0;denom=np.where(nonzero,sd,1.)
    out=np.empty(x.shape[:-2]+(5,),dtype=np.float64)
    for life in range(4):
        bank=np.concatenate((targets(),guide[life]));bank-=bank.mean(axis=(-2,-1),keepdims=True)
        bank/=bank.std(axis=(-2,-1),keepdims=True)
        spectra=np.fft.fft2(centered[life]);template=np.conj(np.fft.fft2(bank))
        corr=np.fft.ifft2(spectra[...,None,:,:]*template).real/(256*denom[life,...,None,None,None])
        best=corr.max(axis=(-2,-1))
        canonical=np.einsum('gcsij,rij->gcsr',centered[life],targets())/(256*denom[life,...,None])
        for g in range(4):
            role=g//2;other=1-role
            out[life,g,...,0]=best[g,...,role]
            out[life,g,...,1]=best[g,...,other]
            out[life,g,...,2]=best[g,...,2+role]-best[g,...,2+other]
            out[life,g,...,3]=canonical[g,...,role]-canonical[g,...,other]
    out[...,:4]=np.where(nonzero[...,None],out[...,:4],0.)
    out[...,4]=np.sqrt(np.mean(x*x,axis=(-2,-1)))
    assert np.isfinite(out).all()
    return out


def preference(raw):
    v=raw['terminal_states'][...,0,:,:]
    active=abs(v)>.2;result=np.empty((4,4,2,4),dtype=np.float64)
    for g in range(4):
        own=targets()[g//2]>0;alt=targets()[1-g//2]>0
        result[:,g]=np.mean(((v[:,g]>0)==own)&active[:,g],axis=(-2,-1))-np.mean(
            ((v[:,g]>0)==alt)&active[:,g],axis=(-2,-1))
    return result


def extract(raw):return dict(fields=measurements(fields(raw),raw['guide']),preference=preference(raw))


def endpoints(a):
    x=a['fields'];o=x[:,:,:,STAGES.index('outgoing')];t=x[:,:,:,STAGES.index('terminal_packet')]
    end=np.stack((o[...,0],o[...,0]-o[...,1],o[...,2],t[...,3],a['preference'][...,-1],
        x[:,:,:,STAGES.index('final:300:V'),4]),axis=-1)
    p=x[:,:,:,0];r=x[:,:,:,1]
    start=np.stack((p[...,0],p[...,0]-p[...,1],p[...,2],r[...,3]),axis=-1)
    return start,end


def describe(x,ids):
    assert x.shape==(len(ids),4,2) and len(ids)>1
    means=x.mean(axis=1);gap=means[:,1]-means[:,0];total=np.abs(gap).sum()
    omit=(gap.sum()-gap)/(len(ids)-1);top=int(np.argmax(abs(gap)))
    return dict(copy_mean=x.mean(axis=(0,1)).tolist(),copy_sd=x.std(axis=(0,1)).tolist(),
        gap_mean=float(gap.mean()),gap_sd=float(gap.std()),mean_absolute_gap=float(abs(gap).mean()),
        founder_means=means.tolist(),founder_gap=gap.tolist(),gap_minimum=float(gap.min()),gap_maximum=float(gap.max()),
        positive=int(np.count_nonzero(gap>SIGN_TOL)),negative=int(np.count_nonzero(gap<-SIGN_TOL)),
        numerical_zero=int(np.count_nonzero(abs(gap)<=SIGN_TOL)),omitted_founder_means=omit.tolist(),
        omission_minimum=float(omit.min()),omission_maximum=float(omit.max()),
        largest_absolute_founder=int(ids[top]),largest_absolute_share=float(abs(gap[top])/total) if total else None)


def row(d,p,di,pi,**labels):
    dev,pilot=describe(d,di),describe(p,pi)
    return dict(**labels,development=dev,pilot=pilot,gap_change=pilot['gap_mean']-dev['gap_mean'],
        copy_mean_change=(np.array(pilot['copy_mean'])-np.array(dev['copy_mean'])).tolist())


def validate_panel(a,di,pi):
    assert set(a)=={'development_fields','development_preference','pilot_fields','pilot_preference'}
    assert di.ndim==pi.ndim==1 and di.dtype==pi.dtype==np.int64 and len(di)>1 and len(pi)>1
    assert len(set(di))==len(di) and len(set(pi))==len(pi) and not set(di)&set(pi)
    for co,ids in (('development',di),('pilot',pi)):
        assert a[co+'_fields'].shape==(len(ids),4,4,2,48,5)
        assert a[co+'_preference'].shape==(len(ids),4,4,2,4)
    assert all(v.dtype==np.float64 and np.isfinite(v).all() for v in a.values())


def summarize(a,di,pi):
    validate_panel(a,di,pi);rows=[];prefs=[];edges=[]
    d,p=a['development_fields'],a['pilot_fields']
    for g,group in enumerate(GROUPS):
        for j,stage in enumerate(STAGES):
            for k,metric in enumerate(METRICS):
                rows.append(row(d[:,:,g,:,j,k],p[:,:,g,:,j,k],di,pi,group=group,stage=stage,metric=metric))
        for j,t in enumerate(FINAL):
            prefs.append(row(a['development_preference'][:,:,g,:,j],a['pilot_preference'][:,:,g,:,j],
                di,pi,group=group,time=t))
        for left,right in zip(CHAIN,CHAIN[1:]):
            u,v=STAGES.index(left),STAGES.index(right)
            for k,metric in enumerate(METRICS):
                edges.append(row(d[:,:,g,:,v,k]-d[:,:,g,:,u,k],p[:,:,g,:,v,k]-p[:,:,g,:,u,k],
                    di,pi,group=group,left=left,right=right,metric=metric))
    return dict(schema='d167_passive_stages_v1',development_ids=di.tolist(),pilot_ids=pi.tolist(),
        groups=list(GROUPS),stages=list(STAGES),metrics=list(METRICS),reference_chain=list(CHAIN),
        final_times=list(FINAL),sign_tolerance=SIGN_TOL,field_rows=rows,preference_rows=prefs,transition_rows=edges,
        fields_measured=int(sum(v.size//5 for k,v in a.items() if k.endswith('_fields'))),
        diagnostic_copies=32*(len(di)+len(pi)),all_cases_retained=True,outcomes_used=False,
        forecasts_used=False,new_fits=0,new_forecasts=0,new_dynamics=0,new_diagnostic_cycles=0,new_founders=0,
        post_test_explanation=True,prospective_evidence=False,confidence_intervals=False,
        source_primary_unchanged=True,automatic_successor=False)
