"""D151 equal-budget six-model development comparison; D150 baselines unchanged."""
from copy import deepcopy
import numpy as np
from . import recovery_models as ridge

MODELS=('starting','passive','shuffle','attenuate','sham_plus','sham_minus')
BASELINES={'starting':'starting','passive':'passive_endpoint','shuffle':'challenge_endpoint'}
NEW=MODELS[3:]
CONTRASTS=(('attenuate','passive'),('attenuate','starting'),('attenuate','shuffle'),
    ('attenuate','sham_plus'),('attenuate','sham_minus'),('attenuate','mean_sham_loss'),
    ('sham_plus','passive'),('sham_minus','passive'),('passive','starting'),('shuffle','passive'))


def matrices(start,endpoint,targeted):
    if start.shape[-1]!=7 or endpoint.shape!=start.shape[:-1]+(3,6) or targeted.shape!=endpoint.shape:raise ValueError('seven starting and two six-feature copies')
    if not all(np.isfinite(a).all() for a in (start,endpoint,targeted)):raise ValueError('all finite cases retained')
    combine=lambda second:np.concatenate((start,endpoint[...,0,:],second),axis=-1)
    return dict(starting=start,passive=combine(endpoint[...,1,:]),shuffle=combine(endpoint[...,2,:]),
        **{name:combine(targeted[...,i,:]) for i,name in enumerate(NEW)})


def fit_new(data,baseline_predictions,baseline_fits):
    x=matrices(data['start'],data['endpoint'],data['targeted']);p={};m={}
    for name,source in BASELINES.items():
        p[name]=baseline_predictions[source].copy();m[name]=deepcopy(baseline_fits[source])
        assert p[name].shape==data['labels'].shape and m[name]['blocks']==data['block_ids'].tolist()
    for name in NEW:p[name],m[name]=ridge.nested(x[name],data['labels'],data['block_ids'])
    return p,m


def squared(predictions,y):
    result={k:(predictions[k]-y)**2 for k in MODELS}
    result['mean_sham_loss']=(result['sham_plus']+result['sham_minus'])/2
    return result


def pairs(loss):
    return [dict(candidate=a,reference=b,**ridge.paired(loss[a],loss[b])) for a,b in CONTRASTS]


def summarize(predictions,fits,data):
    assert set(predictions)==set(fits)==set(MODELS)
    y,futures=data['labels'],data['futures'];assert y.shape==(32,4,4) and futures.shape==(16,4,4,4)
    assert np.isfinite(y).all() and np.isfinite(futures).all() and np.max(abs(y))<=1 and np.max(abs(futures))<=1
    scores={};repeated={};future_loss={};mean_loss={}
    for name in MODELS:
        p=predictions[name];assert p.shape==y.shape and np.isfinite(p).all() and np.max(abs(p))<=1
        score=ridge.errors(p,y)
        score['cohorts']={key:ridge.errors(p[a:b],y[a:b]) for key,a,b in (('d135',0,8),('d140',8,16),('former_test',16,32))}
        selected=[fold['model']['alpha'] for fold in fits[name]['folds']]
        score['selected_alphas']=selected;score['alpha_counts']={str(a):selected.count(a) for a in ridge.ALPHAS}
        scores[name]=score;e=p[16:,...,None]-futures
        future_loss[name]=(e*e).mean(axis=-1);mean_loss[name]=(p[16:]-futures.mean(axis=-1))**2
        repeated[name]=dict(individual_future_mse=float((e*e).mean()),individual_future_mae_points=float(abs(e).mean()*100),
            per_future_mse=(e*e).mean(axis=(0,1,2)).tolist(),per_future_mae_points=(abs(e).mean(axis=(0,1,2))*100).tolist(),
            individual_future_block_mse=(e*e).mean(axis=(1,2,3)).tolist(),individual_future_group_mse=(e*e).mean(axis=(0,1,3)).tolist(),
            mean_target_mse=float(mean_loss[name].mean()),mean_target_block_mse=mean_loss[name].mean(axis=(1,2)).tolist(),
            mean_target_group_mse=mean_loss[name].mean(axis=(0,1)).tolist())
    for loss in (future_loss,mean_loss):loss['mean_sham_loss']=(loss['sham_plus']+loss['sham_minus'])/2
    comparisons=pairs(squared(predictions,y));a,b=pairs(future_loss),pairs(mean_loss)
    rep=[]
    for left,right in zip(a,b):
        np.testing.assert_allclose(left['block_differences'],right['block_differences'],atol=1e-14,rtol=0)
        rep.append(dict(candidate=left['candidate'],reference=left['reference'],individual_futures=left,mean_target=right))
    return dict(schema='d151_targeted_prediction_development_v1',stage='POST_RESULT_DEVELOPMENT',
        prospective_evidence=False,blocks=32,cases=512,all_cases_retained=True,new_diagnostic_cycles=1536,
        new_actual_lineages=0,new_founders=0,models=scores,comparisons=comparisons,central_comparison=comparisons[0],
        repeated_future_models=repeated,repeated_future_comparisons=rep,repeated_future_blocks=16,
        repeated_future_outcomes=1024,repeated_outcomes_used_for_training=False,confidence_intervals=False,
        model_selected_for_deployment=False,automatic_successor=False,baseline_predictions_reused=True,
        observer_cycles=2,mean_sham_is_loss_average_not_prediction_ensemble=True,
        interpretation='Existing-founder development of a fixed repair-like diagnostic; not prospective validation.')


def diagnostic_summary(raw_blocks,source_endpoint,plans):
    values=np.stack([b['diagnostic_features'] for b in raw_blocks])
    records=np.stack([b['record_values'] for b in raw_blocks])
    assert values.shape==(32,4,4,3,6) and records.shape==(32,4,4,3,10) and source_endpoint.shape==values.shape
    changed=values-source_endpoint[...,1,None,:]
    cells=[c for p in plans for life in p['lives'] for case in life for c in case]
    return dict(cases=512,new_cycles=1536,edits=list(NEW),
        diagnostic_means=values.mean(axis=(0,1)).tolist(),matched_change_means=changed.mean(axis=(0,1)).tolist(),
        matched_change_block_means=changed.mean(axis=1).tolist(),record_means=records.mean(axis=(0,1)).tolist(),
        degenerate_cycles=sum(c['degenerate'] for c in cells),identity_cycles=sum(c['identity'] for c in cells),
        minimum_dose=min(c['dose_rms'] for c in cells),maximum_dose=max(c['dose_rms'] for c in cells),
        mean_dose=float(np.mean([c['dose_rms'] for c in cells])),
        minimum_attenuation_scale=min(c['competing_scale'] for c in cells),
        maximum_attenuation_scale=max(c['competing_scale'] for c in cells),
        matched_response_is_predictor_feature=False,prospective_evidence=False)


def fixture(blocks=32):
    base,y=ridge.fixture(blocks,15120260919);rng=np.random.default_rng(151142)
    targeted=rng.normal(size=base['endpoint'].shape)
    data=dict(start=base['start'],endpoint=base['endpoint'],targeted=targeted,labels=y,
        block_ids=np.arange(blocks,dtype=np.int64),futures=np.clip(y[-16:,...,None]+rng.normal(scale=.07,size=(min(16,blocks),4,4,4)),-1,1))
    x=matrices(data['start'],data['endpoint'],targeted);p={};m={}
    for name,source in BASELINES.items():p[source],m[source]=ridge.nested(x[name],y,data['block_ids'])
    return data,p,m
