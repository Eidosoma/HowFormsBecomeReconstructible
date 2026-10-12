"""D151 independent observer boundary, SVD nested fits and score arithmetic."""
import numpy as np
from . import recovery_check as old

MODELS=('starting','passive','shuffle','attenuate','sham_plus','sham_minus')
SOURCES=('starting','passive_endpoint','challenge_endpoint')
CONTRASTS=(('attenuate','passive'),('attenuate','starting'),('attenuate','shuffle'),
    ('attenuate','sham_plus'),('attenuate','sham_minus'),('attenuate','mean_sham_loss'),
    ('sham_plus','passive'),('sham_minus','passive'),('passive','starting'),('shuffle','passive'))


def check_fits(p,m,data,baseline_predictions,baseline_fits):
    assert set(p)==set(m)==set(MODELS)
    a,e,t=data['start'],data['endpoint'],data['targeted']
    x={'starting':a}
    for name,second in (('passive',e[...,1,:]),('shuffle',e[...,2,:]),('attenuate',t[...,0,:]),
                        ('sham_plus',t[...,1,:]),('sham_minus',t[...,2,:])):
        x[name]=np.concatenate([a,e[...,0,:],second],axis=-1)
    for name,source in zip(MODELS[:3],SOURCES):
        np.testing.assert_array_equal(p[name],baseline_predictions[source]);assert m[name]==baseline_fits[source]
    proof={k:old.check_nested(p[k],m[k],x[k],data['labels'],data['block_ids']) for k in MODELS}
    return dict(passes=True,models=6,outer_folds=6*len(a),inner_folds=6*len(a)*(len(a)-1),
        exact_saved_baselines=3,prospective_evidence=False,checks=proof)


def contrasts(loss):
    return [dict(candidate=a,reference=b,**old.reduction(loss[a],loss[b])) for a,b in CONTRASTS]


def check_summary(summary,p,fits,data):
    y=data['labels'];f=data['futures'];assert y.shape==(32,4,4) and f.shape==(16,4,4,4)
    scores={};repeated={};original={};individual={};means={}
    for name in MODELS:
        prediction=p[name];assert prediction.shape==y.shape and np.isfinite(prediction).all()
        original[name]=(prediction-y)**2;score=old.error_stats(prediction,y)
        score['cohorts']={key:old.error_stats(prediction[a:b],y[a:b]) for key,a,b in (('d135',0,8),('d140',8,16),('former_test',16,32))}
        selected=[fold['model']['alpha'] for fold in fits[name]['folds']]
        score['selected_alphas']=selected;score['alpha_counts']={str(a):sum(v==a for v in selected) for a in old.ALPHAS}
        scores[name]=score;errors=prediction[16:,...,None]-f
        individual[name]=np.sum(errors**2,axis=-1)/4;means[name]=(prediction[16:]-np.sum(f,axis=-1)/4)**2
        repeated[name]=dict(individual_future_mse=float(np.sum(errors**2)/1024),individual_future_mae_points=float(np.sum(abs(errors))*100/1024),
            per_future_mse=(np.sum(errors**2,axis=(0,1,2))/256).tolist(),
            per_future_mae_points=(np.sum(abs(errors),axis=(0,1,2))*100/256).tolist(),
            individual_future_block_mse=(np.sum(errors**2,axis=(1,2,3))/64).tolist(),
            individual_future_group_mse=(np.sum(errors**2,axis=(0,1,3))/256).tolist(),
            mean_target_mse=float(np.sum(means[name])/256),mean_target_block_mse=(np.sum(means[name],axis=(1,2))/16).tolist(),
            mean_target_group_mse=(np.sum(means[name],axis=(0,1))/64).tolist())
    for loss in (original,individual,means):loss['mean_sham_loss']=(loss['sham_plus']+loss['sham_minus'])*.5
    pairs=contrasts(original);a,b=contrasts(individual),contrasts(means);rep=[]
    for left,right in zip(a,b):
        np.testing.assert_allclose(left['block_differences'],right['block_differences'],atol=1e-14,rtol=0)
        rep.append(dict(candidate=left['candidate'],reference=left['reference'],individual_futures=left,mean_target=right))
    expected=dict(schema='d151_targeted_prediction_development_v1',stage='POST_RESULT_DEVELOPMENT',
        prospective_evidence=False,blocks=32,cases=512,all_cases_retained=True,new_diagnostic_cycles=1536,
        new_actual_lineages=0,new_founders=0,models=scores,comparisons=pairs,central_comparison=pairs[0],
        repeated_future_models=repeated,repeated_future_comparisons=rep,repeated_future_blocks=16,
        repeated_future_outcomes=1024,repeated_outcomes_used_for_training=False,confidence_intervals=False,
        model_selected_for_deployment=False,automatic_successor=False,baseline_predictions_reused=True,
        observer_cycles=2,mean_sham_is_loss_average_not_prediction_ensemble=True,
        interpretation='Existing-founder development of a fixed repair-like diagnostic; not prospective validation.')
    old.same(summary,expected)
    return dict(passes=True,models=6,comparisons=10,blocks=32,cases=512,repeated_outcomes=1024,prospective_evidence=False)


def check_diagnostic_summary(summary,blocks,endpoint,plans):
    v=np.asarray([b['diagnostic_features'] for b in blocks]);r=np.asarray([b['record_values'] for b in blocks])
    changes=v-endpoint[...,1,None,:]
    cells=[cell for p in plans for life in p['lives'] for case in life for cell in case]
    assert len(cells)==1536 and v.shape==(32,4,4,3,6) and r.shape==(32,4,4,3,10)
    d=[cell['dose_rms'] for cell in cells];scales=[cell['competing_scale'] for cell in cells]
    expected=dict(cases=512,new_cycles=1536,edits=['attenuate','sham_plus','sham_minus'],
        diagnostic_means=(np.sum(v,axis=(0,1))/128).tolist(),matched_change_means=(np.sum(changes,axis=(0,1))/128).tolist(),
        matched_change_block_means=(np.sum(changes,axis=1)/4).tolist(),record_means=(np.sum(r,axis=(0,1))/128).tolist(),
        degenerate_cycles=sum(cell['degenerate'] for cell in cells),identity_cycles=sum(cell['identity'] for cell in cells),
        minimum_dose=min(d),maximum_dose=max(d),mean_dose=sum(d)/1536,
        minimum_attenuation_scale=min(scales),maximum_attenuation_scale=max(scales),
        matched_response_is_predictor_feature=False,prospective_evidence=False)
    old.same(summary,expected)
    return dict(passes=True,cases=512,new_cycles=1536,matched_response_is_predictor_feature=False)
