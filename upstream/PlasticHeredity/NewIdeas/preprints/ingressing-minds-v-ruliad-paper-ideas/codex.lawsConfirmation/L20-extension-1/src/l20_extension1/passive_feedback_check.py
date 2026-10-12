"""Independent D168 modular-index geometry and direct-sum accounting."""
import numpy as np
from . import passive_feedback as m, passive_stages_check as prior

same=prior.same


def ideal(s,role):
    assert s.shape[-1]==2 and s.dtype==np.int64 and np.all((s>=0)&(s<16)) and role in (0,1)
    if role==0:
        d=s[...,0];return 1-np.minimum(d,16-d)/4
    d=s[...,1]%8;return 1-np.minimum(d,8-d)/2


def rotate(x,s):
    yy,xx=np.indices((16,16))
    return x[(yy-int(s[0]))%16,(xx-int(s[1]))%16]


def correlation(a,b):
    assert a.shape==b.shape==(16,16)
    valid=bool(np.max(a)!=np.min(a) and np.max(b)!=np.min(b))
    if not valid:return 0.,False
    x=a.ravel()-a.sum()/256;y=b.ravel()-b.sum()/256
    return float(np.dot(x,y)/(np.linalg.norm(x)*np.linalg.norm(y))),True


def shape(field,role):
    x=field-field.sum()/256;norm=np.linalg.norm(x)
    if field.max()==field.min():return 0.
    template=prior.templates()[role]
    bank=[np.roll(template,j,axis=role) for j in range(16 if role==0 else 8)]
    return max(float(np.sum(x*b)/(16*norm)) for b in bank)


def reconstructed(raw):
    shift=raw['shift'];assert shift.shape==(4,4,2,2) and not np.any(np.all(shift==0,axis=-1))
    out={k:np.zeros(s,dtype=np.int64 if k=='shift' else bool if k.endswith('_valid') else np.float64) for k,s in m.SHAPES.items()}
    out['shift'][:]=shift
    for g in range(4):
        np.testing.assert_array_equal(shift[:,g],shift[:,0])
        out['q'][:,g,:,0]=ideal(shift[:,g],g//2)
        out['q'][:,g,:,1]=out['q'][:,g,:,0] if g%2==0 else 1.
    for life in range(4):
        for g in range(4):
            role=g//2
            for copy in range(2):
                assigned=shift[life,g,copy];effective=assigned if g%2==0 else (0,0)
                start=shape(raw['write_states'][life,g,copy,0,2],role)
                for j in range(4):
                    v,_,ref,theta=raw['write_states'][life,g,copy,j]
                    for k,s in enumerate((assigned,effective)):
                        value,valid=correlation(ref,rotate(ref,s));out['reference'][life,g,copy,j,k]=value
                        out['reference_valid'][life,g,copy,j,k]=valid
                    applied=rotate(theta,effective)
                    for k,(a,b) in enumerate(((theta,ref),(applied,ref),(theta,v),(applied,v))):
                        value,valid=correlation(a,b);out['feedback'][life,g,copy,j,k]=value
                        out['feedback_valid'][life,g,copy,j,k]=valid
                    out['response'][life,g,copy,j]=shape(ref,role)-start
                packet=np.frombuffer(raw['outgoing'][life,g,copy].tobytes(),dtype='<f8').reshape(16,16)
                out['response'][life,g,copy,4]=shape(packet,role)
                x=packet-packet.sum()/256;scale=np.sqrt(np.sum(x*x)/256)
                guide=raw['guide'][life];guide=guide-guide.sum(axis=(1,2))[:,None,None]/256
                guide=guide/np.sqrt(np.sum(guide*guide,axis=(1,2))/256)[:,None,None]
                sc=np.fft.ifft2(np.fft.fft2(x)[None]*np.conj(np.fft.fft2(guide))).real/(256*scale) if scale else np.zeros((2,16,16))
                peak=np.amax(sc,axis=(1,2));out['response'][life,g,copy,5]=peak[role]-peak[1-role]
                v=raw['terminal_states'][life,g,copy,-1,0];valid=abs(v)>.2
                counts=[np.count_nonzero(((v>0)==(t>0))&valid) for t in prior.templates()]
                out['response'][life,g,copy,6]=(counts[role]-counts[1-role])/256
    return out


def block(raw,got,saved):
    expected=reconstructed(raw);assert set(got)==set(expected)
    worst=0.
    for k in expected:
        assert got[k].shape==expected[k].shape and got[k].dtype==expected[k].dtype
        if got[k].dtype==np.float64:
            same(got[k],expected[k]);worst=max(worst,float(np.max(abs(got[k]-expected[k]))))
        else:np.testing.assert_array_equal(got[k],expected[k])
    field=saved['fields'];base=field[:,:,:,m.old.STAGES.index('write:0:R'),0]
    for j,t in enumerate((0,1,300,1000)):
        same(got['response'][...,j],field[:,:,:,m.old.STAGES.index(f'write:{t}:R'),0]-base)
    for k,column in ((4,0),(5,2),(6,4)):same(got['response'][...,k],raw['diagnostic_features'][...,column])
    same(got['response'][...,6],saved['preference'][...,-1])
    np.testing.assert_array_equal(raw['write_states'][:,:,:,0,3],0)
    assert not got['feedback_valid'][...,0,:].any()
    for a,b in ((0,1),(2,3)):
        np.testing.assert_array_equal(raw['write_states'][:,a,:,:2],raw['write_states'][:,b,:,:2])
        np.testing.assert_array_equal(got['feedback'][:,b,:,:,0],got['feedback'][:,b,:,:,1])
        np.testing.assert_array_equal(got['feedback'][:,b,:,:,2],got['feedback'][:,b,:,:,3])
    return dict(passes=True,diagnostic_copies=32,geometry_values=832,validity_flags=768,responses=224,
        max_error=worst,outcomes_used=False,new_dynamics=0)


def description(x,valid):
    sums=[];counts=[];means=[];gs=[];gn=[];gmean=[]
    for block in range(len(x)):
        sm=[sum(float(x[block,l,c]) for l in range(4) if valid[block,l,c]) for c in range(2)]
        ns=[sum(bool(valid[block,l,c]) for l in range(4)) for c in range(2)]
        sums.append(sm);counts.append(ns);means.append([sm[c]/ns[c] if ns[c] else None for c in range(2)])
        pairs=[float(x[block,l,1]-x[block,l,0]) for l in range(4) if all(valid[block,l])]
        gs.append(sum(pairs));gn.append(len(pairs));gmean.append(sum(pairs)/len(pairs) if pairs else None)
    ns=np.asarray(counts).sum(0);sm=np.asarray(sums).sum(0);n=sum(gn)
    return dict(copy_mean=[float(sm[c]/ns[c]) if ns[c] else None for c in range(2)],
        valid=ns.tolist(),invalid=(len(x)*4-ns).tolist(),founder_sum=sums,founder_count=counts,founder_mean=means,
        paired_gap=sum(gs)/n if n else None,paired_count=n,founder_gap=gmean,founder_gap_sum=gs,founder_pair_count=gn,
        positive=sum(v is not None and v>1e-12 for v in gmean),negative=sum(v is not None and v<-1e-12 for v in gmean),
        numerical_zero=sum(v is not None and abs(v)<=1e-12 for v in gmean),undefined=sum(v is None for v in gmean))


def assoc(x,valid,y):
    sufficient=[]
    for j in range(len(x)):
        xv=x[j,valid[j]];yv=y[j,valid[j]]
        sufficient.append([float(len(xv)),float(xv.sum()),float(yv.sum()),float(np.dot(xv,xv)),float(np.dot(xv,yv)),float(np.dot(yv,yv))])
    xx=x[valid];yy=y[valid];n=len(xx)
    dx=xx[:,None]-xx[None,:];dy=yy[:,None]-yy[None,:]
    sxx=float(np.sum(dx*dx)/(2*n)) if n else 0.;sxy=float(np.sum(dx*dy)/(2*n)) if n else 0.
    syy=float(np.sum(dy*dy)/(2*n)) if n else 0.
    return dict(valid_pairs=n,invalid_pairs=int(valid.size-n),mean_x=float(sum(xx)/n) if n else None,
        mean_y=float(sum(yy)/n) if n else None,sxx=sxx,sxy=sxy,syy=syy,
        slope=sxy/sxx if sxx>1e-24 else None,correlation=sxy/np.sqrt(sxx*syy) if sxx>1e-24 and syy>1e-24 else None,
        founder_sufficient=sufficient)


def levels(q,y,role):
    result=[]
    for level in (np.arange(-4,5)/4 if role==0 else np.arange(-2,3)/2):
        count=np.zeros((len(q),2),np.int64);sums=np.zeros((len(q),2,7));means=[]
        for b in range(len(q)):
            for c in range(2):
                for l in range(4):
                    if q[b,l,c]==level:count[b,c]+=1;sums[b,c]+=y[b,l,c]
            means.append([(sums[b,c]/count[b,c]).tolist() if count[b,c] else [None]*7 for c in range(2)])
        ns=count.sum(0);ss=sums.sum(0);total=int(ns.sum())
        result.append(dict(q=float(level),counts=ns.tolist(),proportions=[int(n)/(len(q)*4) for n in ns],
            founders=[int(np.count_nonzero(count[:,c])) for c in range(2)],founder_count=count.tolist(),founder_sum=sums.tolist(),
            founder_mean=means,copy_means=[(ss[c]/ns[c]).tolist() if ns[c] else [None]*7 for c in range(2)],
            pooled_mean=((ss[0]+ss[1])/total).tolist() if total else [None]*7))
    return result


def accounting(q,y,rows,k):
    by_q={r['q']:r for r in rows};gap=[];mix=[];residual=[]
    for b in range(len(q)):
        g=M=R=0.
        for l in range(4):
            mu=[by_q[float(q[b,l,c])]['pooled_mean'][k] for c in range(2)]
            assert all(v is not None for v in mu)
            g+=(y[b,l,1]-y[b,l,0])/4;M+=(mu[1]-mu[0])/4
            R+=((y[b,l,1]-mu[1])-(y[b,l,0]-mu[0]))/4
        gap.append(float(g));mix.append(float(M));residual.append(float(R))
    terms=[(r['counts'][1]-r['counts'][0])/(len(q)*4)*r['pooled_mean'][k] if sum(r['counts']) else 0. for r in rows]
    def omitted(v):
        z=[sum(v[:j]+v[j+1:])/(len(v)-1) for j in range(len(v))]
        return dict(values=z,minimum=min(z),maximum=max(z))
    G,M,R=[sum(v)/len(v) for v in (gap,mix,residual)];assert abs(G-M-R)<2e-10 and abs(sum(terms)-M)<2e-10
    return dict(gap=G,mixture=M,residual=R,level_terms=terms,founder_gap=gap,founder_mixture=mix,founder_residual=residual,
        gap_omissions=omitted(gap),mixture_omissions=omitted(mix),residual_omissions=omitted(residual),
        pooled_reference_refit_on_omission=False)


def summary(s,d,p,di,pi):
    assert s['schema']=='d168_passive_feedback_v1' and s['development_ids']==di.tolist() and s['pilot_ids']==pi.tolist()
    assert s['groups']==list(m.GROUPS) and s['times']==[0,1,300,1000] and s['responses']==list(m.RESPONSES)
    assert s['descriptors']==list(m.DESCRIPTORS) and s['profile_metrics']==list(m.PROFILE)
    assert len(s['profile_rows'])==272 and len(s['level_rows'])==56 and len(s['association_rows'])==224 and len(s['mixture_rows'])==56
    assert s['diagnostic_copies']==32*(len(di)+len(pi)) and s['independent_founders']==len(di)+len(pi)
    for k in ('post_test_description','all_cases_retained','source_primary_unchanged'):assert s[k] is True
    for k in ('outcomes_used','confidence_intervals','causal_attribution','prospective_evidence','automatic_successor'):assert s[k] is False
    for k in ('new_dynamics','new_fits','new_forecasts','new_founders'):assert s[k]==0
    ip=il=ia=im=0
    for co,a,ids in (('development',d,di),('pilot',p,pi)):
        m.validate(a,len(ids))
        for g,group in enumerate(m.GROUPS):
            specs=[('assigned_q',None,a['q'][:,:,g,:,0],np.ones((len(ids),4,2),bool)),
                ('effective_q',None,a['q'][:,:,g,:,1],np.ones((len(ids),4,2),bool))]
            for j,t in enumerate((0,1,300,1000)):
                r=a['reference'][:,:,g,:,j];rv=a['reference_valid'][:,:,g,:,j]
                f=a['feedback'][:,:,g,:,j];fv=a['feedback_valid'][:,:,g,:,j]
                vals=[r[...,0],r[...,1],f[...,0],f[...,1],f[...,2],f[...,3],f[...,1]-f[...,0],f[...,3]-f[...,2]]
                flags=[rv[...,0],rv[...,1],fv[...,0],fv[...,1],fv[...,2],fv[...,3],fv[...,0]&fv[...,1],fv[...,2]&fv[...,3]]
                specs.extend((name,t,x,v) for name,x,v in zip(m.PROFILE,vals,flags))
            for name,t,x,v in specs:
                same(s['profile_rows'][ip],dict(cohort=co,group=group,metric=name,time=t,**description(x,v)));ip+=1
            q=a['q'][:,:,g,:,0];y=a['response'][:,:,g];lr=levels(q,y,g//2)
            for row in lr:same(s['level_rows'][il],dict(cohort=co,group=group,**row));il+=1
            for k,name in enumerate(m.RESPONSES):
                same(s['mixture_rows'][im],dict(cohort=co,group=group,response=name,**accounting(q,y[...,k],lr,k)));im+=1
            descriptors=[(a['q'][:,:,g,:,0],np.ones_like(q,bool)),(a['q'][:,:,g,:,1],np.ones_like(q,bool)),
                (a['reference'][:,:,g,:,0,0],a['reference_valid'][:,:,g,:,0,0]),
                (a['feedback'][:,:,g,:,1,1],a['feedback_valid'][:,:,g,:,1,1])]
            for name,(x,v) in zip(m.DESCRIPTORS,descriptors):
                for k,response in enumerate(m.RESPONSES):
                    same(s['association_rows'][ia],dict(cohort=co,group=group,descriptor=name,response=response,
                        **assoc(x[...,1]-x[...,0],v[...,0]&v[...,1],y[...,1,k]-y[...,0,k])));ia+=1
    return dict(passes=True,profile_rows=ip,level_rows=il,association_rows=ia,mixture_rows=im,
        all_cases_retained=True,outcomes_used=False)
