"""Independent D158 SVD refits, complete scoring and influence decomposition."""
import numpy as np
from . import target_check as old

ALPHAS=(.001,.01,.1)
OBSERVERS=old.OBSERVERS
LOSS_OBSERVERS=old.LOSS_OBSERVERS
PAIRS=tuple(old.observer_pairs())
SCOPES=('original','individual_futures','mean_target')+tuple('repeat'+str(i) for i in range(4))+tuple('omit_repeat'+str(i) for i in range(4))


def valid(data):
    old.labels(data);n=len(data['block_ids'])
    assert n>=5
    return n


def reference_shapes(p,raw,n):
    assert set(p)==set(raw)==set(OBSERVERS)
    for k in OBSERVERS:
        assert p[k].shape==raw[k].shape==(3,n,4,4)
        assert np.isfinite(p[k]).all() and np.isfinite(raw[k]).all()
        np.testing.assert_array_equal(p[k],np.maximum(-1,np.minimum(1,raw[k])))


def check_all(p,raw,fits,data):
    n=valid(data);ids=data['block_ids'];x=old.matrices(data);y=np.sum(data['futures'],axis=-1)/4
    groups=np.tile(np.arange(4,dtype=np.int64),4*n)
    assert set(p)==set(raw)==set(fits)==set(OBSERVERS)
    for name in OBSERVERS:
        assert p[name].shape==raw[name].shape==(n,3,n-1,4,4)
        assert np.isfinite(p[name]).all() and np.isfinite(raw[name]).all()
        np.testing.assert_array_equal(p[name],np.maximum(-1,np.minimum(1,raw[name])))
        header={k:v for k,v in fits[name].items() if k!='deletions'}
        old.same(header,dict(blocks=ids.tolist(),alphas=list(ALPHAS),target='future_mean',observer=name,
            model_class=old.group.CLASS,training_blocks_per_fold=n-2,inner_selection=False,
            preprocessing='training-only; deletion and validation founder excluded'))
        assert len(fits[name]['deletions'])==n
        X=x[name].reshape(n*16,-1)
        for d,deleted in enumerate(fits[name]['deletions']):
            remaining=[b for b in range(n) if b!=d]
            assert set(deleted)=={'deleted_block','remaining_blocks','folds'}
            assert deleted['deleted_block']==int(ids[d]) and deleted['remaining_blocks']==ids[remaining].tolist()
            assert len(deleted['folds'])==n-1
            for j,(b,fold) in enumerate(zip(remaining,deleted['folds'])):
                keep=[v for v in range(n) if v not in (d,b)]
                assert set(fold)=={'validation_block','training_blocks','models'}
                assert fold['validation_block']==int(ids[b]) and fold['training_blocks']==ids[keep].tolist()
                train=np.concatenate([np.arange(v*16,(v+1)*16) for v in keep]);test=np.arange(b*16,(b+1)*16)
                pred,models=old.group.svd_path(X[train],y.ravel()[train],groups[train],X[test],groups[test])
                assert len(fold['models'])==3
                np.testing.assert_allclose(p[name][d,:,j],pred[:,:3].T.reshape(3,4,4),atol=2e-10,rtol=0)
                for i,m in enumerate(models[:3]):
                    old.check_record(fold['models'][i],m)
                    np.testing.assert_allclose(raw[name][d,i,j],old.raw_forward(m,X[test],groups[test]).reshape(4,4),atol=2e-10,rtol=0)
    return dict(passes=True,observers=12,settings=3,deletions=n,outer_fits=36*n*(n-1),
        inner_fits=0,svd_group_coordinates=True,both_exclusions_checked=True)


def loss_panel(p,data,i):
    y=data['labels'];f=data['futures'];mu=np.sum(f,axis=-1)/4;loss={};models={}
    for k in OBSERVERS:
        q=p[k][i];e=q[...,None]-f
        loss[k]=(np.square(q-y),np.square(e),np.square(q-mu))
        np.testing.assert_allclose(np.sum(e*e,axis=-1)/4,loss[k][2]+np.sum((f-mu[...,None])**2,axis=-1)/4,atol=1e-14,rtol=0)
        models[k]=dict(original=old.error_stats(q-y),individual_futures=old.error_stats(e),
            mean_target=old.error_stats(q-mu),by_repeat=[old.error_stats(e[...,j]) for j in range(4)])
    for prefix in ('separate:','mean:'):
        plus,minus=loss[prefix+'sham_plus'],loss[prefix+'sham_minus']
        loss[prefix+'mean_sham_loss']=tuple(.5*a+.5*b for a,b in zip(plus,minus))
    return loss,models


def panel(p,raw,data,i):
    loss,models=loss_panel(p,data,i)
    for k in OBSERVERS:models[k]['clipped_cases']=int(np.count_nonzero(np.abs(raw[k][i])>1))
    return dict(blocks=data['block_ids'].tolist(),models=models,
        comparisons=[dict(candidate=c,reference=r,**old.comparison(loss[c],loss[r])) for c,r in PAIRS])


def scopes(c):
    out={k:c[k] for k in SCOPES[:3]}
    for j in range(4):
        out['repeat'+str(j)]=c['by_repeat'][j]
        out['omit_repeat'+str(j)]=c['leave_one_repeat_out'][j]
    return out


def influence(full,score,refit,ids):
    sc=[v-full for v in score];tr=[r-s for r,s in zip(refit,score)];total=[v-full for v in refit]
    np.testing.assert_allclose(np.add(sc,tr),total,atol=1e-14,rtol=0)
    return dict(full_gain=full,score_only_gains=score,refitted_gains=refit,
        score_composition_change=sc,training_change=tr,total_change=total,
        positive_score_only=sum(v>0 for v in score),positive_refitted=sum(v>0 for v in refit),
        negative_refitted=sum(v<0 for v in refit),zero_refitted=sum(v==0 for v in refit),
        min_refitted=min(refit),max_refitted=max(refit),
        score_sign_reversals=[int(ids[j]) for j,v in enumerate(score) if v*full<0],
        refit_sign_reversals=[int(ids[j]) for j,v in enumerate(refit) if v*full<0])


def change(a,b):
    e=a-b;n=len(e)
    return dict(bias_points=float(100*np.sum(e)/e.size),mae_points=float(100*np.sum(np.abs(e))/e.size),
        rms_points=float(100*np.sqrt(np.sum(np.square(e))/e.size)),max_abs_points=float(100*np.max(np.abs(e))),
        group_rms_points=[float(100*np.sqrt(np.sum(e[:,:,g]**2)/(n*4))) for g in range(4)])


def check_summary(s,p,raw,baseline,base_raw,data):
    n=valid(data);reference_shapes(baseline,base_raw,n);scores={}
    for i,a in enumerate(ALPHAS):
        full=panel(baseline,base_raw,data,i);deletions=[]
        for d in range(n):
            keep=[j for j in range(n) if j!=d]
            reduced={k:data[k][keep].copy() for k in ('start','endpoint','targeted','labels','futures','block_ids')}
            q={k:p[k][d] for k in OBSERVERS};qr={k:raw[k][d] for k in OBSERVERS}
            b={k:baseline[k][:,keep] for k in OBSERVERS};br={k:base_raw[k][:,keep] for k in OBSERVERS}
            new,_=loss_panel(q,reduced,i);ref,_=loss_panel(b,reduced,i)
            deletions.append(dict(deleted_block=int(data['block_ids'][d]),refitted=panel(q,qr,reduced,i),
                score_only=panel(b,br,reduced,i),
                training_effect=[dict(observer=k,**old.comparison(new[k],ref[k])) for k in LOSS_OBSERVERS],
                forecast_change={k:change(q[k][i],b[k][i]) for k in OBSERVERS}))
        decomposition=[]
        for j,(c,r) in enumerate(PAIRS):
            values={}
            for scope,metric in scopes(full['comparisons'][j]).items():
                score=[scopes(v['score_only']['comparisons'][j])[scope]['mse_reduction'] for v in deletions]
                refit=[scopes(v['refitted']['comparisons'][j])[scope]['mse_reduction'] for v in deletions]
                values[scope]=influence(metric['mse_reduction'],score,refit,data['block_ids'])
                for d in range(n):
                    effects={v['observer']:scopes(v)[scope]['mse_reduction'] for v in deletions[d]['training_effect']}
                    np.testing.assert_allclose(refit[d]-score[d],effects[c]-effects[r],atol=1e-14,rtol=0)
            decomposition.append(dict(candidate=c,reference=r,scopes=values))
        scores[str(a)]=dict(full=full,deletions=deletions,decomposition=decomposition)
    expected=dict(schema='d158_training_influence_development_v1',posthoc=True,prospective_evidence=False,
        blocks=n,cases=16*n,deletion_panels=n,training_blocks_per_fold=n-2,target='future_mean',
        observers=list(OBSERVERS),alphas=list(ALPHAS),groups=['A_ordinary','A_aligned','B_ordinary','B_aligned'],
        new_fits=36*n*(n-1),new_predictions=576*n*(n-1),reference_predictions_reused=576*n,
        observer_orientations=165,observer_comparison_records=165*(1+2*n),training_effect_records=42*n,
        decomposition_records=165,feature_dimensions=[7,13]+[19]*5+[13]*5,
        all_deletions_retained=True,all_repeats_retained=True,full_cohort_reference_retained=True,
        excluded_founder_in_training=False,validation_founder_in_training=False,mean_sham_is_loss_not_ensemble=True,
        no_best_setting_or_deletion_selected=True,old_reference_fits_recomputed=False,
        new_dynamics=0,new_founders=0,new_diagnostic_cycles=0,confidence_intervals=False,
        independent_deletion_replications=False,inner_selection=False,automatic_successor=False,
        scores=scores,within_future_variance=float(np.sum((data['futures']-np.sum(data['futures'],axis=-1,keepdims=True)/4)**2)/data['futures'].size))
    old.same(s,expected)
    return dict(passes=True,observer_orientations=165,deletions=n,observer_comparison_records=165*(1+2*n),
        training_effect_records=42*n,decomposition_records=165,all_deletions_retained=True,additive_accounting=True)


def check_errors(arrays,p,baseline,data):
    n=valid(data);expected=set()
    for prefix,values in (('baseline',baseline),('refit',p)):
        if prefix=='baseline':y=data['labels'];f=data['futures']
        else:
            keep=[[b for b in range(n) if b!=d] for d in range(n)]
            y=data['labels'][keep][:,None];f=data['futures'][keep][:,None]
        for k in OBSERVERS:
            errors={'original':values[k]-y,'futures':values[k][...,None]-f,'mean':values[k]-np.sum(f,axis=-1)/4}
            for scope,e in errors.items():
                for suffix,v in (('signed',e),('absolute',np.maximum(e,-e)),('squared',np.square(e))):
                    key=prefix+'__'+k+'__'+scope+'__'+suffix;expected.add(key)
                    np.testing.assert_allclose(arrays[key],v,atol=1e-14,rtol=0)
    for k in OBSERVERS:
        b=np.stack([baseline[k][:,[v for v in range(n) if v!=d]] for d in range(n)]);e=p[k]-b
        for suffix,v in (('signed',e),('absolute',np.maximum(e,-e)),('squared',np.square(e))):
            key='forecast_change__'+k+'__'+suffix;expected.add(key);np.testing.assert_allclose(arrays[key],v,atol=1e-14,rtol=0)
    assert set(arrays)==expected
    return dict(passes=True,case_arrays=252,all_deletions_retained=True)


def source_bridge(summary,reference):
    assert reference['schema']=='d157_target_averaging_development_v1' and reference['training_targets'][-1]=='future_mean'
    for a in ('0.001','0.01','0.1'):
        full=summary['scores'][a]['full'];prior=reference['scores'][a]
        for k in OBSERVERS:old.same(full['models'][k],prior['models']['future_mean/'+k])
        comparisons=[v for v in prior['comparisons'] if v['kind']=='observer' and v['candidate_target']=='future_mean']
        assert len(comparisons)==55
        for new,previous in zip(full['comparisons'],comparisons):
            old.same(new,{k:v for k,v in previous.items() if k not in ('kind','candidate_target','reference_target')})
    return dict(passes=True,exact_reference_values=True,observers=12,settings=3,contrasts=165,reference_fits_recomputed=False)
