"""Independent SVD, averaging identities and complete D157 score accounting."""
import math
import numpy as np
from . import group_check as group,matched_check as prior,mean_check as mean_prior

ALPHAS=(.001,.01,.1)
TARGETS=('original','future0','future1','future2','future3','future_mean')
EDITED=('passive','shuffle','attenuate','sham_plus','sham_minus')
OBSERVERS=('starting','one_copy')+tuple('separate:'+k for k in EDITED)+tuple('mean:'+k for k in EDITED)
LOSS_OBSERVERS=OBSERVERS+('separate:mean_sham_loss','mean:mean_sham_loss')


def same(a,b):
    if isinstance(b,dict):
        assert isinstance(a,dict) and a.keys()==b.keys()
        for k in b:same(a[k],b[k])
    elif isinstance(b,(list,tuple)):
        assert isinstance(a,(list,tuple)) and len(a)==len(b)
        for x,y in zip(a,b):same(x,y)
    elif isinstance(b,(float,np.floating)):
        assert not isinstance(a,bool) and math.isfinite(a) and abs(a-b)<=2e-10,(a,b)
    else:assert a==b,(a,b)


def matrices(data):
    a,e,t=data['start'],data['endpoint'],data['targeted'];n=len(a)
    assert a.shape==(n,4,4,7) and e.shape==t.shape==(n,4,4,3,6)
    result={'starting':a.copy(),'one_copy':np.concatenate([a,e[...,0,:]],axis=-1)}
    for k,second in zip(EDITED,(e[...,1,:],e[...,2,:],t[...,0,:],t[...,1,:],t[...,2,:])):
        result['separate:'+k]=np.concatenate([a,e[...,0,:],second],axis=-1)
        result['mean:'+k]=np.concatenate([a,.5*e[...,0,:]+.5*second],axis=-1)
    return result


def labels(data):
    n=len(data['block_ids']);assert data['labels'].shape==(n,4,4) and data['futures'].shape==(n,4,4,4)
    assert n>=4 and data['block_ids'].dtype==np.int64 and len(set(data['block_ids'].tolist()))==n
    for k in ('start','endpoint','targeted','labels','futures'):
        assert data[k].dtype==np.float64 and np.isfinite(data[k]).all()
    assert max(np.max(abs(data[k])) for k in ('labels','futures'))<=1
    result=[data['labels'].copy()]+[data['futures'][...,j].copy() for j in range(4)]
    return result+[np.sum(data['futures'],axis=-1)/4]


def raw_forward(model,x,g):
    beta=np.asarray(model['coefficients']);contrast=np.array([[-1,-1,1],[-1,1,-1],[1,-1,-1],[1,1,1]])/2
    slopes=beta[0]+contrast@beta[1:];center=(x-np.asarray(model['means'])[g])/np.asarray(model['scale'])
    return np.asarray(model['offsets'])[g]+np.sum(center*slopes[g],axis=1)


def check_record(actual,expected):
    assert actual.keys()==expected.keys() and actual['alpha']==expected['alpha'] and actual['model_class']==expected['model_class']
    for k in ('means','offsets','scale','coefficients'):
        np.testing.assert_allclose(actual[k],expected[k],atol=2e-10,rtol=0)


def check_all(p,raw,m,data):
    n=len(data['block_ids']);ids=data['block_ids'];x=matrices(data);ys=labels(data)
    assert set(p)==set(raw)==set(m)==set(OBSERVERS)
    groups=np.tile(np.arange(4,dtype=np.int64),4*n);max_identity=0.
    for name in OBSERVERS:
        assert p[name].shape==raw[name].shape==(6,3,n,4,4)
        assert np.isfinite(p[name]).all() and np.isfinite(raw[name]).all() and np.max(abs(p[name]))<=1
        np.testing.assert_array_equal(p[name],np.maximum(-1,np.minimum(1,raw[name])))
        header={k:v for k,v in m[name].items() if k!='folds'}
        same(header,dict(blocks=ids.tolist(),alphas=list(ALPHAS),training_targets=list(TARGETS),
            model_class=group.CLASS,observer=name,preprocessing='training-only within each whole-founder fold',
            inner_selection=False,prospective_evidence=False))
        assert len(m[name]['folds'])==n;X=x[name].reshape(n*16,-1)
        for b,fold in enumerate(m[name]['folds']):
            others=[i for i in range(n) if i!=b];train=np.concatenate([np.arange(i*16,i*16+16) for i in others]);test=np.arange(b*16,b*16+16)
            assert set(fold)=={'training_blocks','validation_block','models'}
            assert fold['training_blocks']==[int(ids[i]) for i in others] and fold['validation_block']==int(ids[b])
            assert len(fold['models'])==6
            for j,y in enumerate(ys):
                guess,records=group.svd_path(X[train],y.ravel()[train],groups[train],X[test],groups[test])
                assert len(fold['models'][j])==3
                np.testing.assert_allclose(p[name][j,:,b],guess[:,:3].T.reshape(3,4,4),atol=2e-10,rtol=0)
                for i,expected in enumerate(records[:3]):
                    check_record(fold['models'][j][i],expected)
                    np.testing.assert_allclose(raw[name][j,i,b],raw_forward(expected,X[test],groups[test]).reshape(4,4),atol=2e-10,rtol=0)
            for i in range(3):
                average=fold['models'][5][i];singles=[fold['models'][j][i] for j in range(1,5)]
                for k in ('means','scale'):
                    for record in singles:np.testing.assert_array_equal(average[k],record[k])
                for k in ('coefficients','offsets'):
                    residual=np.asarray(average[k])-sum(np.asarray(r[k]) for r in singles)/4
                    np.testing.assert_allclose(residual,0,atol=2e-10,rtol=0);max_identity=max(max_identity,float(np.max(abs(residual))))
        np.testing.assert_allclose(raw[name][5],np.sum(raw[name][1:5],axis=0)/4,atol=2e-10,rtol=0)
    return dict(passes=True,observers=12,training_targets=6,settings=3,outer_fits=216*n,inner_fits=0,
        svd_group_coordinates=True,linear_averaging_identity=True,max_abs_model_mean_residual=max_identity)


def canonical(k):return k if k in ('starting','one_copy') else 'separate:'+k


def observer_pairs():
    one=[('one_copy','starting')]+[(k,'one_copy') for k in EDITED]+[('mean_sham_loss','one_copy')]
    # Frozen independently specified D153 and D155 pair definitions.
    return [(canonical(c),canonical(r)) for c,r in prior.PAIRS]+[(canonical(c),canonical(r)) for c,r in one]+mean_prior.specs()


def specifications():
    pairs=[]
    for t in TARGETS:
        for c,r in observer_pairs():pairs.append(dict(kind='observer',candidate_target=t,candidate=c,reference_target=t,reference=r))
    for k in LOSS_OBSERVERS:
        for t in ('original','future0','future1','future2','future3','single_mean_loss'):
            pairs.append(dict(kind='target',candidate_target='future_mean',candidate=k,reference_target=t,reference=k))
        pairs.append(dict(kind='target',candidate_target='single_mean_loss',candidate=k,reference_target='original',reference=k))
    return pairs


def error_stats(e):
    squared=np.square(e);count=e.size;n,l,g=e.shape[:3];repeats=1 if e.ndim==3 else e.shape[3]
    return dict(mse=float(np.sum(squared)/count),mae_points=float(100*np.sum(np.abs(e))/count),
        rmse_points=float(100*np.sqrt(np.sum(squared)/count)),bias_points=float(100*np.sum(e)/count),
        group_mse=[float(np.sum(squared[:,:,j,...])/(n*l*repeats)) for j in range(g)],
        block_mse=[float(np.sum(squared[b])/(l*g*repeats)) for b in range(n)])


def paired(c,r):
    n=len(c);delta=np.sum(r-c,axis=(1,2))/16;gain=float(np.sum(delta)/n);reference=float(np.sum(r)/(n*16))
    return dict(mse_reduction=gain,candidate_mse=float(np.sum(c)/(n*16)),reference_mse=reference,
        relative_reduction_percent=100*gain/reference if reference else None,
        block_differences=delta.tolist(),group_differences=(np.sum(r-c,axis=(0,1))/(n*4)).tolist(),
        positive_blocks=int(np.count_nonzero(delta>0)),negative_blocks=int(np.count_nonzero(delta<0)),
        zero_blocks=int(np.count_nonzero(delta==0)),
        leave_one_score_block_out=[float(np.sum(np.delete(delta,b))/(n-1)) for b in range(n)])


def comparison(c,r):
    co,cf,cm=c;ro,rf,rm=r
    answer=dict(original=paired(co,ro),individual_futures=paired(np.sum(cf,axis=3)/4,np.sum(rf,axis=3)/4),
        mean_target=paired(cm,rm),by_repeat=[paired(cf[...,j],rf[...,j]) for j in range(4)],leave_one_repeat_out=[])
    for j in range(4):
        keep=[k for k in range(4) if k!=j]
        answer['leave_one_repeat_out'].append(paired(sum(cf[...,k] for k in keep)/3,sum(rf[...,k] for k in keep)/3))
    np.testing.assert_allclose(answer['individual_futures']['block_differences'],answer['mean_target']['block_differences'],atol=1e-14,rtol=0)
    return answer


def check_summary(s,p,raw,data):
    n=len(data['block_ids']);labels(data);y=data['labels'];f=data['futures'];mu=np.sum(f,axis=-1)/4;scores={}
    for i,alpha in enumerate(ALPHAS):
        models={};loss={}
        for j,t in enumerate(TARGETS):
            for k in OBSERVERS:
                q=p[k][j,i];e=q[...,None]-f;key=t+'/'+k
                loss[key]=(np.square(q-y),np.square(e),np.square(q-mu))
                np.testing.assert_allclose(np.sum(e*e,axis=-1)/4,loss[key][2]+np.sum((f-mu[...,None])**2,axis=-1)/4,atol=1e-14,rtol=0)
                models[key]=dict(original=error_stats(q-y),individual_futures=error_stats(e),mean_target=error_stats(q-mu),
                    by_repeat=[error_stats(e[...,r]) for r in range(4)],clipped_cases=int(np.count_nonzero(np.abs(raw[k][j,i])>1)))
            for prefix in ('separate:','mean:'):
                a,b=(loss[t+'/'+prefix+k] for k in ('sham_plus','sham_minus'))
                loss[t+'/'+prefix+'mean_sham_loss']=tuple(.5*x+.5*y for x,y in zip(a,b))
        for k in LOSS_OBSERVERS:
            loss['single_mean_loss/'+k]=tuple(sum(loss[t+'/'+k][j] for t in TARGETS[1:5])/4 for j in range(3))
        comparisons=[dict(**spec,**comparison(loss[spec['candidate_target']+'/'+spec['candidate']],
            loss[spec['reference_target']+'/'+spec['reference']])) for spec in specifications()]
        identity={k:dict(max_abs_unclipped_mean_residual=float(np.max(np.abs(raw[k][5,i]-sum(raw[k][j,i] for j in range(1,5))/4))),
            mean_fit_clipped_cases=int(np.count_nonzero(np.abs(raw[k][5,i])>1)),
            single_fit_clipped_cases=int(np.count_nonzero(np.abs(raw[k][1:5,i])>1)),
            max_abs_clipped_average_difference=float(np.max(np.abs(p[k][5,i]-sum(p[k][j,i] for j in range(1,5))/4)))) for k in OBSERVERS}
        scores[str(alpha)]=dict(models=models,comparisons=comparisons,averaging_identity=identity)
    expected=dict(schema='d157_target_averaging_development_v1',posthoc=True,prospective_evidence=False,
        blocks=n,cases=16*n,training_blocks_per_fold=n-1,all_cases_retained=True,training_targets=list(TARGETS),
        observers=list(OBSERVERS),alphas=list(ALPHAS),groups=['A_ordinary','A_aligned','B_ordinary','B_aligned'],
        new_fits=216*n,new_predictions=3456*n,feature_dimensions=[7,13]+[19]*5+[13]*5,
        model_class=group.CLASS,common_deviation_penalty_ratio=1,inner_selection=False,
        observer_contrasts=990,target_contrasts=294,total_contrasts=1284,
        repeated_outcomes_used_for_training=True,held_out_outcomes_used_for_training=False,
        mean_training_label_budget=4,single_training_label_budget=1,diagnostic_budgets_unchanged=True,
        equal_dimension_is_not_equal_complexity=True,mean_sham_is_loss_not_ensemble=True,
        single_mean_is_loss_not_ensemble=True,new_dynamics=0,new_founders=0,new_diagnostic_cycles=0,
        confidence_intervals=False,model_selected_for_deployment=False,former_test_is_development=True,
        no_best_alpha_or_repeat_selected=True,old_reference_fits_recomputed=False,automatic_successor=False,
        scores=scores,within_future_variance=float(np.sum((f-mu[...,None])**2)/f.size))
    same(s,expected)
    return dict(passes=True,observers=12,targets=6,settings=3,observer_contrasts=990,target_contrasts=294,
        blocks=n,cases=16*n,all_repeats_retained=True,mean_losses_not_ensembles=True)


def check_errors(arrays,p,data):
    expected=set()
    for k in OBSERVERS:
        for scope,e in (('original',p[k]-data['labels']),('futures',p[k][...,None]-data['futures']),
                        ('mean',p[k]-np.sum(data['futures'],axis=-1)/4)):
            for suffix,value in (('signed',e),('absolute',np.maximum(e,-e)),('squared',np.square(e))):
                name=k+'__'+scope+'__'+suffix;expected.add(name);np.testing.assert_allclose(arrays[name],value,atol=1e-14,rtol=0)
    assert set(arrays)==expected
    return dict(passes=True,case_arrays=108,all_cases_retained=True)
