"""Independent SVD fits, fixed-alpha bridge and complete D153 score accounting."""
import numpy as np
from . import group_check as group, group_review_check as review

MODELS=('starting','passive','shuffle','attenuate','sham_plus','sham_minus')
ALPHAS=(.001,.01,.1)
PAIRS=(('passive','starting'),('shuffle','starting'),('shuffle','passive'),
    ('attenuate','starting'),('attenuate','passive'),('attenuate','shuffle'),
    ('attenuate','sham_plus'),('attenuate','sham_minus'),('sham_plus','starting'),
    ('sham_plus','passive'),('sham_plus','shuffle'),('sham_minus','starting'),
    ('sham_minus','passive'),('sham_minus','shuffle'),('sham_minus','sham_plus'),
    ('attenuate','mean_sham_loss'),('mean_sham_loss','starting'),('mean_sham_loss','passive'))
COHORTS=(('d135',0,8),('d140',8,16),('former_test',16,32))
same=group.old.same


def check_all(p,m,data):
    assert set(p)==set(m)==set(MODELS);x=group.matrices(data);ids=data['block_ids'];n=len(ids)
    assert ids.dtype==np.int64 and len(set(ids.tolist()))==n and data['labels'].shape==(n,4,4)
    for name in MODELS:
        assert p[name].shape==(3,n,4,4) and np.isfinite(p[name]).all() and np.max(abs(p[name]))<=1
        assert len(m[name]['folds'])==n
        X=x[name].reshape(n*16,-1);Y=data['labels'].ravel();g=np.tile(np.arange(4,dtype=np.int64),4*n)
        assert np.isfinite(Y).all() and np.max(abs(Y))<=1
        for b in range(n):
            blocks=[i for i in range(n) if i!=b];train=np.concatenate([np.arange(i*16,(i+1)*16) for i in blocks])
            test=np.arange(b*16,(b+1)*16)
            guesses,models=group.svd_path(X[train],Y[train],g[train],X[test],g[test])
            np.testing.assert_allclose(p[name][:,b],guesses[:,:3].T.reshape(3,4,4),atol=2e-10,rtol=0)
            same(m[name]['folds'][b],dict(validation_block=int(ids[b]),training_blocks=[int(ids[i]) for i in blocks],models=models[:3]))
        same({k:v for k,v in m[name].items() if k!='folds'},dict(blocks=ids.tolist(),alphas=list(ALPHAS),
            preprocessing='training-only in every outer fold',inner_selection=False,
            prospective_evidence=False,model_class=group.CLASS))
    return dict(passes=True,models=6,settings=3,outer_fits=n*18,inner_fits=0,svd_group_coordinates=True)


def bridge(p,m,old,old_fits,data):
    assert set(old)==set(old_fits)==set(MODELS);n=len(data['block_ids'])
    for name in MODELS:
        assert old[name].shape==(n,4,4) and len(old_fits[name]['folds'])==n
        for b in range(n):
            previous=old_fits[name]['folds'][b];a=previous['model']['alpha'];i=ALPHAS.index(a)
            assert previous['selected_index']==i
            current=m[name]['folds'][b]
            assert previous['validation_block']==current['validation_block']
            assert previous['training_blocks']==current['training_blocks']
            same(current['models'][i],previous['model'])
            np.testing.assert_allclose(p[name][i,b],old[name][b],atol=2e-10,rtol=0)
    return dict(passes=True,selected_outer_models=n*6,selected_outer_predictions=n*96,nested_refitted=False)


def effects(c,r):
    result=group.reduction(c,r);differences=np.asarray(result['block_differences'])
    result['leave_one_score_block_out']=[float(np.sum(np.delete(differences,i))/(len(c)-1)) for i in range(len(c))]
    result['groups']=[group.reduction(c[:,:,g:g+1],r[:,:,g:g+1]) for g in range(4)]
    return result


def contrast(c,r,cf,rf,cm,rm):
    future=effects(cf,rf);mean=effects(cm,rm)
    np.testing.assert_allclose(future['block_differences'],mean['block_differences'],atol=1e-14,rtol=0)
    return dict(original=effects(c,r),cohorts={k:effects(c[l:h],r[l:h]) for k,l,h in COHORTS},
        individual_futures=future,mean_target=mean)


def score(p,data):
    y=data['labels'];f=data['futures'];scores={};loss={};future={};mean={};average=np.sum(f,axis=-1)/4
    for name in MODELS:
        v=p[name];assert v.shape==y.shape and np.isfinite(v).all() and np.max(abs(v))<=1
        loss[name]=np.square(v-y);e=v[16:,...,None]-f;future[name]=np.sum(e*e,axis=-1)/4
        mean[name]=np.square(v[16:]-average);count=e.size
        scores[name]=dict(original=group.error_stats(v,y),
            cohorts={c:group.error_stats(v[l:h],y[l:h]) for c,l,h in COHORTS},
            individual_futures=dict(mse=float(np.sum(e*e)/count),mae_points=float(100*np.sum(abs(e))/count),
                rmse_points=float(100*np.sqrt(np.sum(e*e)/count)),block_mse=(np.sum(e*e,axis=(1,2,3))/64).tolist(),
                group_mse=(np.sum(e*e,axis=(0,1,3))/256).tolist()),mean_target=group.error_stats(v[16:],average))
        np.testing.assert_allclose(future[name],mean[name]+np.sum((f-average[...,None])**2,axis=-1)/4,atol=1e-14,rtol=0)
    for bundle in (loss,future,mean):bundle['mean_sham_loss']=(bundle['sham_plus']+bundle['sham_minus'])*.5
    comparisons=[dict(candidate=c,reference=r,**contrast(loss[c],loss[r],future[c],future[r],mean[c],mean[r])) for c,r in PAIRS]
    return dict(models=scores,comparisons=comparisons),(loss,future,mean)


def check_summary(s,p,old,data):
    assert data['labels'].shape==(32,4,4) and data['futures'].shape==(16,4,4,4)
    assert np.isfinite(data['futures']).all() and np.max(abs(data['futures']))<=1
    scores={};losses={}
    for i,label in enumerate(('0.001','0.01','0.1','nested')):
        guesses=old if label=='nested' else {name:p[name][i] for name in MODELS}
        scores[label],losses[label]=score(guesses,data)
    changes=[]
    for label in ('0.001','0.01','0.1'):
        for name in MODELS:
            c,cf,cm=[v[name] for v in losses[label]];r,rf,rm=[v[name] for v in losses['nested']]
            changes.append(dict(setting=label,observer=name,reference='nested',**contrast(c,r,cf,rf,cm,rm)))
    expected=dict(schema='d153_matched_regularization_development_v1',stage='POST_RESULT_DEVELOPMENT',
        prospective_evidence=False,blocks=32,cases=512,all_cases_retained=True,alphas=[.001,.01,.1],
        settings=['0.001','0.01','0.1','nested'],observers=list(MODELS),new_fits=576,new_predictions=9216,
        inner_selection=False,model_class=group.CLASS,common_deviation_penalty_ratio=1,
        feature_dimensions=[7,19,19,19,19,19],penalized_dimensions=[28,76,76,76,76,76],
        equal_alpha_is_not_equal_effective_complexity=True,former_test_is_now_development=True,
        old_nested_predictions_reused=True,new_dynamics=0,new_founders=0,new_diagnostic_cycles=0,
        repeated_future_blocks=16,repeated_future_outcomes=1024,repeated_outcomes_used_for_training=False,
        confidence_intervals=False,model_selected_for_deployment=False,automatic_successor=False,
        mean_sham_is_loss_average_not_prediction_ensemble=True,focus=['sham_minus','passive'],no_best_alpha_selected=True,
        scores=scores,fixed_vs_nested=changes)
    same(s,expected)
    return dict(passes=True,settings=4,models=24,observer_contrasts=72,fixed_vs_nested_contrasts=18,
        blocks=32,cases=512,secondary_outcomes=1024)


def check_errors(stored,p,old,data):
    expected=set()
    for i,label in enumerate(('0.001','0.01','0.1','nested')):
        for name in MODELS:
            e=(old[name] if label=='nested' else p[name][i])-data['labels']
            for suffix,v in (('signed',e),('absolute',np.maximum(e,-e)),('squared',np.square(e))):
                key=label+'__'+name+'__'+suffix;expected.add(key);np.testing.assert_array_equal(stored[key],v)
    assert set(stored)==expected
    return dict(passes=True,case_arrays=72,all_cases_retained=True)
