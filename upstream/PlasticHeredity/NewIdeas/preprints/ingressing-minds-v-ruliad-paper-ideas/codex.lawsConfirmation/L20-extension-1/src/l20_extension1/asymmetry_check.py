"""Independent D163 expanded-loss, aggregation and forward-model checks."""
import numpy as np
from . import asymmetry as m


def close(a,b,tol=3e-11):
    np.testing.assert_allclose(a,b,atol=tol,rtol=0)


def weighted(name):
    if name in m.OBSERVERS:return [(name,1.)]
    e,s=name.split(':');assert e in m.ENCODINGS and s=='mean_sham_loss'
    return [(e+':sham_plus',.5),(e+':sham_minus',.5)]


def reductions(value):
    n=len(value);return dict(overall=value.sum((0,1,2,3))/(64*n),
        blocks=value.sum((1,2,3))/64,groups=value.sum((0,1,3))/(16*n),
        futures=value.sum((0,1,2))/(16*n))


def check_aggregate(saved,value):
    expected=reductions(value)
    for name,v in expected.items():close(saved[name],v)
    block=expected['blocks'];future=expected['futures']
    close(saved['omit_founder'],[(block[:i].sum(0)+block[i+1:].sum(0))/(len(block)-1) for i in range(len(block))])
    close(saved['omit_future'],[(future[:i].sum(0)+future[i+1:].sum(0))/3 for i in range(4)])


def check_cohort(s,p,raw,y,ids):
    m.validate(p,raw,y,ids);n=len(ids)
    assert s['ids']==ids.tolist() and s['founders']==n and s['cases']==16*n and s['futures']==4
    assert s['terms']==list(m.TERMS)
    expected_specs=m.specifications();assert len(s['comparisons'])==len(expected_specs)==277
    for row,spec in zip(s['comparisons'],expected_specs):
        assert all(row[k]==v for k,v in spec.items())
        a=m.ALPHAS.index(spec['candidate_alpha']);b=m.ALPHAS.index(spec['reference_alpha'])
        direct=np.zeros_like(y);alignment=direct.copy();cost=direct.copy();bits=[]
        c_loss=sum(w*(p[k][a,...,None]-y)**2 for k,w in weighted(spec['candidate']))
        r_loss=sum(w*(p[k][b,...,None]-y)**2 for k,w in weighted(spec['reference']))
        direct=r_loss-c_loss
        for ck,cw in weighted(spec['candidate']):
            for rk,rw in weighted(spec['reference']):
                cp=p[ck][a,...,None];rp=p[rk][b,...,None];w=cw*rw
                # Expanded polynomial, independent of the production difference formula.
                alignment+=w*(2*cp*y-2*rp*y-2*cp*rp+2*rp*rp)
                cost+=np.broadcast_to(w*(cp*cp+rp*rp-2*cp*rp),y.shape)
                bits.append((w,np.broadcast_to(cp-rp,y.shape),y-rp))
        close(alignment-cost,direct)
        base=np.stack((alignment,cost,direct),-1);red=reductions(base)
        for key,axes,denom in (('overall',(0,1,2,3),64*n),('blocks',(1,2,3),64),
                               ('groups',(0,1,3),16*n),('futures',(0,1,2),16*n)):
            bias=sum(2*w*d.sum(axis=axes)*r.sum(axis=axes)/(denom*denom) for w,d,r in bits)
            v=red[key];expected=np.stack((v[...,0],bias,v[...,0]-bias,v[...,1],v[...,2]),-1)
            close(row[key],expected)
        for key,axes,count in (('omit_founder',(1,2,3),n),('omit_future',(0,1,2),4)):
            reduced=red['blocks' if key=='omit_founder' else 'futures']
            total=reduced.sum(0);v=(total-reduced)/(count-1)
            bias=0.
            for w,d,r in bits:
                db=d.sum(axis=axes)/(64 if key=='omit_founder' else 16*n)
                rb=r.sum(axis=axes)/(64 if key=='omit_founder' else 16*n)
                bias+=2*w*((db.sum()-db)/(count-1))*((rb.sum()-rb)/(count-1))
            close(row[key],np.stack((v[:,0],bias,v[:,0]-bias,v[:,1],v[:,2]),-1))
        close([row['candidate_mse'],row['reference_mse']],[c_loss.sum()/(64*n),r_loss.sum()/(64*n)])
        ref=float(r_loss.mean())
        if ref:close(row['relative_gain_percent'],100*float(direct.sum())/(64*n*ref),1e-8)
        else:assert row['relative_gain_percent'] is None
        mean_loss_reference=sum(w*(p[k][b]-y.mean(-1))**2 for k,w in weighted(spec['reference']))
        mean_loss_candidate=sum(w*(p[k][a]-y.mean(-1))**2 for k,w in weighted(spec['candidate']))
        close(direct.mean(),(mean_loss_reference-mean_loss_candidate).mean())
    assert set(s['absolute'])==set(m.OBSERVERS)
    for name in m.OBSERVERS:
        assert len(s['absolute'][name])==3
        for ai,a in enumerate(m.ALPHAS):
            r=s['absolute'][name][ai];error=p[name][ai,...,None]-y;loss=error**2
            assert r['alpha']==a and r['clipped']==np.count_nonzero(p[name][ai]!=raw[name][ai])
            close([r['mse'],r['rmse_points'],r['mae_points'],r['bias_points']],
                  [loss.sum()/(64*n),np.sqrt(loss.sum()/(64*n))*100,abs(error).sum()*100/(64*n),error.sum()*100/(64*n)])
            for key,v in reductions(loss[...,None]).items():
                if key!='overall':close(r[key],v[...,0])
    assert len(s['signs'])==9
    for row,(e,ai) in zip(s['signs'],[(e,a) for e in m.ENCODINGS for a in range(3)]):
        assert (row['encoding'],row['alpha'])==(e,m.ALPHAS[ai])
        plus,minus,passive=(p[e+':'+k][ai,...,None] for k in ('sham_plus','sham_minus','passive'))
        gp=(passive-y)**2-(plus-y)**2;gm=(passive-y)**2-(minus-y)**2
        expected=np.stack(((gp+gm)*.5,(gp-gm)*.5,gp,gm,gp-gm),-1)
        check_aggregate(row,expected)
    close(s['within_future_variance'],sum(float(np.sum((cell-cell.mean())**2)) for cell in y.reshape(-1,4))/(64*n))
    return dict(passes=True,comparisons=277,absolute_models=51,sign_identities=9,founders=n)


def matrix(data,name):
    a,e,t=data['start'],data['endpoint'],data['targeted']
    if name=='starting':return a
    if name=='one_copy':return np.concatenate([a,e[:,:,:,0]],axis=3)
    prefix,kind=name.split(':');j=m.EDITS.index(kind)
    second=e[:,:,:,j+1] if j<2 else t[:,:,:,j-2]
    if prefix=='mean':return np.concatenate([a,.5*e[:,:,:,0]+.5*second],axis=3)
    return np.concatenate([a,e[:,:,:,0],second],axis=3)


def forward(model,x):
    result=np.empty(x.shape[:3]);q=((-1,-1,1),(-1,1,-1),(1,-1,-1),(1,1,1))
    for g in range(4):
        z=(x[:,:,g]-np.array(model['means'])[g])/np.array(model['scale'])
        result[:,:,g]=float(model['offsets'][g])+z@np.array(model['coefficients'])[0]
        for j in range(3):result[:,:,g]+=.5*q[g][j]*(z@np.array(model['coefficients'])[j+1])
    return result


def check_models(s,arrays,data,models,p,raw,y,ids):
    assert s['parts']==['feature','model','clipping'] and s['saved_models_reconstructed']==51
    assert s['saved_forecasts_reconstructed']==51*16*len(ids) and s['causal_attribution'] is False
    assert s['crossed_forecasts_deployed'] is False and len(s['comparisons'])==9
    for name in m.OBSERVERS:
        x=matrix(data,name)
        for ai in range(3):
            restored=forward(models[name][ai],x)
            close(restored,raw[name][ai],2e-10);close(np.clip(restored,-1,1),p[name][ai],2e-10)
    expected_keys=set()
    for row,(e,ai) in zip(s['comparisons'],[(e,a) for e in m.ENCODINGS for a in range(3)]):
        assert (row['encoding'],row['alpha'])==(e,m.ALPHAS[ai])
        kp,km=e+':sham_plus',e+':sham_minus';xp,xm=matrix(data,kp),matrix(data,km)
        mp,mm=models[kp][ai],models[km][ai]
        # Cross-evaluations here verify an algebra identity; none is deployed or scored as an observer.
        pp,pm,mpred,mmred=forward(mp,xp),forward(mp,xm),forward(mm,xp),forward(mm,xm)
        feature=(pp-pm+mpred-mmred)/2;model=(pp-mpred+pm-mmred)/2
        clipping=(p[kp][ai]-raw[kp][ai])-(p[km][ai]-raw[km][ai])
        parts=np.stack((feature,model,clipping),-1);key=e+'__'+str(ai)
        expected_keys.update((key+'__forecast_parts',key+'__gain_parts'))
        close(arrays[key+'__forecast_parts'],parts)
        expected=parts[...,None,:]*(2*y-p[kp][ai,...,None]-p[km][ai,...,None])[...,None]
        close(arrays[key+'__gain_parts'],expected)
        close(expected.sum(-1),(p[km][ai,...,None]-y)**2-(p[kp][ai,...,None]-y)**2)
        check_aggregate(row['gain'],expected)
        close(row['forecast_mean'],parts.sum((0,1,2))/(16*len(ids)))
        close(row['forecast_rms'],np.sqrt((parts*parts).sum((0,1,2))/(16*len(ids))))
    assert set(arrays)==expected_keys and 0<=s['max_raw_error']<=2e-10
    return dict(passes=True,models=51,forecasts=51*16*len(ids),decompositions=9,arrays=18)


def source_bridge(main,development,pilot_summary,planning):
    old=pilot_summary['prediction'];assert old['label']=='PREDICTIVE_DIFFERENCE_UNRESOLVED'
    assert main['ids']==old['founder_ids']==list(range(100000,100064))
    assert development['ids']==planning['source_founders']==list(range(90000,90016))
    assert len(old['comparisons'])==264 and len(old['selected_cheap_baseline_comparisons'])==4
    assert len(planning['comparisons'])==69
    for name in m.OBSERVERS:
        for a in range(3):
            for field in ('mse','mae_points','rmse_points','bias_points'):
                close(main['absolute'][name][a][field],old['absolute_scores'][name][a][field])
    expected=old['comparisons']+old['selected_cheap_baseline_comparisons']
    for new,prior in zip(main['comparisons'][:268],expected):
        assert (new['candidate'],new['reference'])==(prior['candidate'],prior['reference'])
        assert new['candidate_alpha']==prior.get('candidate_alpha',prior.get('alpha'))
        assert new['reference_alpha']==prior.get('reference_alpha',prior.get('alpha'))
        close(new['overall'][-1],prior['mse_reduction']);close(new['candidate_mse'],prior['candidate_mse'])
        close(new['reference_mse'],prior['reference_mse']);close(np.asarray(new['blocks'])[:,-1],prior['block_differences'])
        close(np.asarray(new['groups'])[:,-1],prior['group_differences']);close(np.asarray(new['futures'])[:,-1],prior['future_differences'])
    lookup={(r['candidate'],r['reference'],r['candidate_alpha']):r for r in development['comparisons'][:264]}
    for prior in planning['comparisons']:
        row=lookup[prior['candidate'],prior['reference'],prior['alpha']]
        close(row['overall'][-1],prior['mean_gain']);close(row['reference_mse'],prior['reference_mse'])
        close(np.asarray(row['blocks'])[:,-1],prior['block_gains'])
    return dict(passes=True,pilot_comparisons=268,pilot_absolute_scores=51,
                development_comparisons=len(planning['comparisons']),source_primary_unchanged=True)
