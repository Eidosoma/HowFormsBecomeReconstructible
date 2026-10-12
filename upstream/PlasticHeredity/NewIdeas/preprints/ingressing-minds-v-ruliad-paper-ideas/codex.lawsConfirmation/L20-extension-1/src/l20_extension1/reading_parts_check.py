"""Independent D159 saved-coefficient replay and loss-gap checks; no fitting."""
import numpy as np
from . import target_check as old

ALPHAS=(.001,.01,.1)
OBSERVERS=old.OBSERVERS
LOSS_OBSERVERS=old.LOSS_OBSERVERS
PAIRS=tuple(old.observer_pairs())
PARTS=('group_offset','starting','reading_level','reading_half_difference','clipping')


def forward_parts(m,x,p,raw,alpha):
    f=x.shape[-1]
    assert set(m)=={'alpha','means','scale','offsets','coefficients','model_class'}
    assert m['alpha']==alpha and m['model_class']==old.group.CLASS
    mu,s,beta,offset=(np.asarray(m[k]) for k in ('means','scale','coefficients','offsets'))
    assert mu.shape==(4,f) and s.shape==(f,) and beta.shape==(4,f) and offset.shape==(4,)
    assert all(np.isfinite(v).all() for v in (x,mu,s,beta,offset,p,raw)) and np.min(s)>0
    answer=np.zeros((4,4,5))
    signs=((-1,-1,1),(-1,1,-1),(1,-1,-1),(1,1,1))
    for g in range(4):
        slope=beta[0]+sum(.5*signs[g][k]*beta[k+1] for k in range(3))
        w=slope/s
        z=x[:,g]-mu[g]
        answer[:,g,0]=offset[g]
        answer[:,g,1]=np.einsum('lf,f->l',z[:,:7],w[:7])
        if f==19:
            left=z[:,7:13];right=z[:,13:19]
            answer[:,g,2]=.5*np.einsum('lf,f->l',left+right,w[7:13]+w[13:19])
            answer[:,g,3]=.5*np.einsum('lf,f->l',right-left,w[13:19]-w[7:13])
        elif f==13:answer[:,g,2]=np.einsum('lf,f->l',z[:,7:],w[7:])
        else:assert f==7
    np.testing.assert_allclose(answer.sum(-1),raw,atol=2e-10,rtol=0)
    g=np.tile(np.arange(4,dtype=np.int64),4)
    np.testing.assert_allclose(old.raw_forward(m,x.reshape(16,f),g).reshape(4,4),raw,atol=2e-10,rtol=0)
    np.testing.assert_array_equal(p,np.maximum(-1,np.minimum(1,raw)))
    answer[...,4]=p-raw
    np.testing.assert_allclose(answer.sum(-1),p,atol=2e-10,rtol=0)
    return answer


def check_parts(parts,data,b,br,p,raw,bfits,rfits):
    ids=data['block_ids'];n=len(ids);old.labels(data);assert n>=5
    x=old.matrices(data);count=0;largest=0.
    assert set(b)==set(br)==set(p)==set(raw)==set(bfits)==set(rfits)==set(OBSERVERS)
    assert set(parts)=={prefix+'__'+k for prefix in ('baseline','refit') for k in OBSERVERS}
    for k in OBSERVERS:
        assert b[k].shape==br[k].shape==(3,n,4,4) and p[k].shape==raw[k].shape==(n,3,n-1,4,4)
        assert parts['baseline__'+k].shape==(3,n,4,4,5) and parts['refit__'+k].shape==(n,3,n-1,4,4,5)
        bh=bfits[k];rh=rfits[k]
        old.same({key:v for key,v in bh.items() if key!='folds'},dict(blocks=ids.tolist(),alphas=list(ALPHAS),
            training_targets=list(old.TARGETS),model_class=old.group.CLASS,observer=k,
            preprocessing='training-only within each whole-founder fold',inner_selection=False,prospective_evidence=False))
        old.same({key:v for key,v in rh.items() if key!='deletions'},dict(blocks=ids.tolist(),alphas=list(ALPHAS),
            target='future_mean',model_class=old.group.CLASS,observer=k,training_blocks_per_fold=n-2,
            preprocessing='training-only; deletion and validation founder excluded',inner_selection=False))
        assert len(bh['folds'])==len(rh['deletions'])==n
        for d in [None]+list(range(n)):
            indices=list(range(n)) if d is None else [j for j in range(n) if j!=d]
            if d is None:folds=bh['folds']
            else:
                deletion=rh['deletions'][d];assert set(deletion)=={'deleted_block','remaining_blocks','folds'}
                assert deletion['deleted_block']==int(ids[d]) and deletion['remaining_blocks']==ids[indices].tolist()
                folds=deletion['folds']
            assert len(folds)==len(indices)
            for j,v in enumerate(indices):
                fold=folds[j];assert set(fold)=={'validation_block','training_blocks','models'}
                assert fold['validation_block']==int(ids[v])
                assert fold['training_blocks']==[int(ids[t]) for t in range(n) if t!=v and t!=d]
                if d is None:
                    assert len(fold['models'])==6 and all(len(row)==3 for row in fold['models'])
                    records=fold['models'][5]
                else:records=fold['models'];assert len(records)==3
                for a,alpha in enumerate(ALPHAS):
                    q,r,z=(b[k][a,v],br[k][a,v],parts['baseline__'+k][a,v]) if d is None else (
                        p[k][d,a,j],raw[k][d,a,j],parts['refit__'+k][d,a,j])
                    expected=forward_parts(records[a],x[k][v],q,r,alpha)
                    np.testing.assert_allclose(z,expected,atol=2e-10,rtol=0)
                    assert np.isfinite(z).all()
                    largest=max(largest,float(np.max(abs(z.sum(-1)-q))));count+=1
    return dict(passes=True,saved_models_replayed=count,saved_forecasts_replayed=16*count,
        max_abs_reconstruction_residual=largest,new_fits=0,part_arrays=24)


def members(name):
    if name in OBSERVERS:return [(name,1.)]
    assert name in ('separate:mean_sham_loss','mean:mean_sham_loss')
    root=name[:name.index(':')]
    return [(root+':sham_plus',.5),(root+':sham_minus',.5)]


def independent_gap(c,r,cp,rp,cq,rq,y,future):
    shape=np.broadcast_shapes(cq[members(c)[0][0]].shape+( (4,) if future else () ),y.shape)
    result=np.zeros(shape+(5,));direct=np.zeros(shape)
    for reference,wr in members(r):
        pr=rq[reference][...,None] if future else rq[reference]
        for candidate,wc in members(c):
            pc=cq[candidate][...,None] if future else cq[candidate]
            direct+=wr*wc*(np.square(pr-y)-np.square(pc-y))
            for part in range(5):
                dz=rp[reference][...,part]-cp[candidate][...,part]
                if future:dz=dz[...,None]
                result[...,part]+=wr*wc*2*dz*((pr+pc)/2-y)
    np.testing.assert_allclose(result.sum(-1),direct,atol=2e-10,rtol=0)
    return result


def check_accounting(arrays,parts,b,p,data):
    n=len(data['block_ids'])
    base={k:parts['baseline__'+k] for k in OBSERVERS}
    refit={k:parts['refit__'+k] for k in OBSERVERS}
    score={k:np.stack([base[k][:,[v for v in range(n) if v!=d]] for d in range(n)]) for k in OBSERVERS}
    sq={k:np.stack([b[k][:,[v for v in range(n) if v!=d]] for d in range(n)]) for k in OBSERVERS}
    yy=np.stack([data['labels'][[v for v in range(n) if v!=d]] for d in range(n)])[:,None]
    ff=np.stack([data['futures'][[v for v in range(n) if v!=d]] for d in range(n)])[:,None]
    keys=set()
    for label,cp,rp,cq,rq,y,f,pairs in (
        ('baseline',base,base,b,b,data['labels'],data['futures'],PAIRS),
        ('refit',refit,refit,p,p,yy,ff,PAIRS),
        ('training',refit,score,p,sq,yy,ff,tuple((k,k) for k in LOSS_OBSERVERS))):
        for j,(c,r) in enumerate(pairs):
            for scope,target,future in (('original',y,False),('futures',f,True)):
                key=f'{label}__pair{j:02d}__{scope}';keys.add(key)
                expected=independent_gap(c,r,cp,rp,cq,rq,target,future)
                assert arrays[key].shape==expected.shape and arrays[key].dtype==np.float64
                np.testing.assert_allclose(arrays[key],expected,atol=2e-10,rtol=0)
                if future:
                    mu=np.sum(f,axis=-1)/4
                    mg=independent_gap(c,r,cp,rp,cq,rq,mu,False)
                    np.testing.assert_allclose(np.sum(arrays[key],axis=-2)/4,mg,atol=2e-10,rtol=0)
    assert set(arrays)==keys
    return dict(passes=True,case_arrays=len(keys),mean_future_identity=True,mean_losses_not_ensembles=True)


def totals(x,detailed=True):
    n=len(x);means=np.sum(x,axis=(0,1,2))/(n*16)
    result=dict(mse_reduction=float(np.sum(means)),components=means.tolist())
    if detailed:
        result['block_components']=(np.sum(x,axis=(1,2))/16).tolist()
        result['group_components']=(np.sum(x,axis=(0,1))/(n*4)).tolist()
    return result


def contrast(o,f):
    mean=np.sum(f,axis=-2)/4
    return dict(original=totals(o),individual_futures=totals(mean),mean_target=totals(mean),
        by_repeat=[totals(f[:,:,:,j,:],False) for j in range(4)],
        leave_one_repeat_out=[totals(sum(f[:,:,:,j,:] for j in range(4) if j!=r)/3,False) for r in range(4)])


def part_stats(z):
    n=len(z);den=n*16
    return dict(mean=(np.sum(z,axis=(0,1,2))/den).tolist(),
        rms=np.sqrt(np.sum(z*z,axis=(0,1,2))/den).tolist(),group_mean=(np.sum(z,axis=(0,1))/(n*4)).tolist())


def panel(parts,b,br,p,raw,data,arrays,a,d=None,refit=False):
    idx=[v for v in range(len(data['block_ids'])) if v!=d]
    yy=data['labels'][idx];ff=data['futures'][idx];models={}
    for k in OBSERVERS:
        q=p[k][d,a] if refit else b[k][a,idx];rr=raw[k][d,a] if refit else br[k][a,idx]
        z=parts['refit__'+k][d,a] if refit else parts['baseline__'+k][a,idx]
        models[k]=dict(original=old.error_stats(q-yy),individual_futures=old.error_stats(q[...,None]-ff),
            mean_target=old.error_stats(q-np.sum(ff,axis=-1)/4),
            by_repeat=[old.error_stats(q-ff[...,r]) for r in range(4)],
            clipped_cases=int(np.count_nonzero(abs(rr)>1)),component_stats=part_stats(z))
    cs=[]
    for j,(c,r) in enumerate(PAIRS):
        if refit:
            o=arrays[f'refit__pair{j:02d}__original'][d,a];f=arrays[f'refit__pair{j:02d}__futures'][d,a]
        else:
            o=arrays[f'baseline__pair{j:02d}__original'][a,idx];f=arrays[f'baseline__pair{j:02d}__futures'][a,idx]
        cs.append(dict(candidate=c,reference=r,**contrast(o,f)))
    return dict(blocks=data['block_ids'][idx].tolist(),models=models,comparisons=cs)


def metadata(n):
    return dict(schema='d159_reading_components_development_v1',components=list(PARTS),blocks=n,cases=16*n,
        observers=list(OBSERVERS),alphas=list(ALPHAS),groups=['A_ordinary','A_aligned','B_ordinary','B_aligned'],
        observer_comparison_records=165*(2*n+1),training_effect_records=42*n,
        saved_models_replayed=36*n*n,saved_forecasts_replayed=576*n*n,new_fits=0,new_predictions=0,
        new_dynamics=0,new_founders=0,new_diagnostic_cycles=0,posthoc=True,prospective_evidence=False,
        all_deletions_retained=True,all_repeats_retained=True,all_settings_retained=True,
        component_only_forecasts=False,causal_attribution=False,
        centering='saved training group means; original raw-coordinate mean and half-difference',
        gap_rule='(reference_part-candidate_part)*(reference_prediction+candidate_prediction-2*outcome)',
        mean_sham_is_loss_not_ensemble=True,confidence_intervals=False,automatic_successor=False)


def check_summary(s,parts,arrays,b,br,p,raw,data):
    n=len(data['block_ids']);old.same({k:v for k,v in s.items() if k!='scores'},metadata(n))
    assert set(s['scores'])=={str(a) for a in ALPHAS}
    for a,alpha in enumerate(ALPHAS):
        deletions=[]
        for d in range(n):
            effects=[dict(observer=k,**contrast(arrays[f'training__pair{j:02d}__original'][d,a],
                arrays[f'training__pair{j:02d}__futures'][d,a])) for j,k in enumerate(LOSS_OBSERVERS)]
            deletions.append(dict(deleted_block=int(data['block_ids'][d]),
                refitted=panel(parts,b,br,p,raw,data,arrays,a,d,True),
                score_only=panel(parts,b,br,p,raw,data,arrays,a,d),training_effect=effects))
        old.same(s['scores'][str(alpha)],dict(full=panel(parts,b,br,p,raw,data,arrays,a),deletions=deletions))
    return dict(passes=True,observer_comparison_records=165*(1+2*n),training_effect_records=42*n,
        absolute_model_score_records=36*(1+2*n))


def bridge_comparison(new,source):
    for scope in ('original','individual_futures','mean_target'):
        a,b=new[scope],source[scope];old.same(a['mse_reduction'],b['mse_reduction'])
        np.testing.assert_allclose(np.sum(a['block_components'],axis=-1),b['block_differences'],atol=2e-10,rtol=0)
        np.testing.assert_allclose(np.sum(a['group_components'],axis=-1),b['group_differences'],atol=2e-10,rtol=0)
    for scope in ('by_repeat','leave_one_repeat_out'):
        assert len(new[scope])==len(source[scope])==4
        for a,b in zip(new[scope],source[scope]):old.same(a['mse_reduction'],b['mse_reduction'])


def source_bridge(summary,source):
    assert source['schema']=='d158_training_influence_development_v1'
    count=0;effects=0;modelcount=0
    for alpha in map(str,ALPHAS):
        new,oldpanel=summary['scores'][alpha],source['scores'][alpha]
        assert len(new['deletions'])==len(oldpanel['deletions'])==summary['blocks']
        pairs=[(new['full'],oldpanel['full'])]
        for a,b in zip(new['deletions'],oldpanel['deletions']):
            assert a['deleted_block']==b['deleted_block']
            pairs.extend(( (a['refitted'],b['refitted']),(a['score_only'],b['score_only']) ))
            assert len(a['training_effect'])==len(b['training_effect'])==14
            for c,r in zip(a['training_effect'],b['training_effect']):
                assert c['observer']==r['observer'];bridge_comparison(c,r);effects+=1
        for a,b in pairs:
            assert a['blocks']==b['blocks'] and len(a['comparisons'])==len(b['comparisons'])==55
            assert set(a['models'])==set(b['models'])==set(OBSERVERS)
            for name in OBSERVERS:
                old.same({k:v for k,v in a['models'][name].items() if k!='component_stats'},b['models'][name]);modelcount+=1
            for c,r in zip(a['comparisons'],b['comparisons']):
                assert (c['candidate'],c['reference'])==(r['candidate'],r['reference'])
                bridge_comparison(c,r);count+=1
    return dict(passes=True,observer_comparison_records=count,training_effect_records=effects,
        absolute_model_score_records=modelcount,source_primary_unchanged=True)
