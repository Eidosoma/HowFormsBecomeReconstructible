"""Finite grouped tuning, train-only scaling and conditional softmax observers."""
from __future__ import annotations
import hashlib
import json
import time
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp
from E123_history_identity_audit import decoder_design as design


class FitFailure(RuntimeError):
    pass


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()


def softmax(z):
    z=np.asarray(z,dtype=np.float64)
    if z.ndim!=2 or z.shape[1]!=4 or not np.isfinite(z).all():
        raise ValueError("Finite four-candidate scores required")
    e=np.exp(z-z.max(axis=1,keepdims=True))
    return e/e.sum(axis=1,keepdims=True)


def smooth(p,epsilon=design.EPSILON):
    p=np.asarray(p,dtype=np.float64)
    if not 0<epsilon<.25 or p.ndim!=2 or p.shape[1]!=4 or not np.isfinite(p).all():
        raise ValueError("Invalid probability convention")
    if np.any(p<0) or np.any(p>1) or not np.allclose(p.sum(axis=1),1,rtol=0,atol=1e-12):
        raise ValueError("Normalized probabilities required")
    return (1-4*epsilon)*p+epsilon


def loss_bits(p,y,epsilon=design.EPSILON):
    q=smooth(p,epsilon);y=np.asarray(y)
    if y.shape!=(len(q),) or y.dtype.kind not in "iu" or np.any((y<0)|(y>3)):
        raise ValueError("Separate integer labels required")
    return -np.log2(q[np.arange(len(y)),y])


def centered(x):
    x=np.asarray(x,dtype=np.float64)
    if x.ndim!=3 or x.shape[1]!=4 or not x.shape[2] or not np.isfinite(x).all():
        raise ValueError("Finite candidate feature tensor required")
    return x-x.mean(axis=1,keepdims=True)


def objective(beta,x,y,ridge):
    scores=x@beta
    loss=float((logsumexp(scores,axis=1)-scores[np.arange(len(y)),y]).mean()+ridge*np.dot(beta,beta)/2)
    delta=softmax(scores);delta[np.arange(len(y)),y]-=1
    gradient=x.reshape(-1,x.shape[-1]).T@delta.ravel()/len(y)+ridge*beta
    return loss,gradient


def fit_ridge(x,y,ridge,maxiter=design.MAXITER):
    start=time.perf_counter();x=centered(x);y=np.asarray(y,dtype=np.int64)
    if y.shape!=(len(x),) or np.any((y<0)|(y>3)) or not ridge>0:
        raise ValueError("Invalid training labels or ridge")
    scale=np.maximum(np.sqrt(np.mean(x*x,axis=(0,1))),1e-12)
    standardized=np.ascontiguousarray(x/scale)
    scale_seconds=time.perf_counter()-start;optimization_start=time.perf_counter()
    result=minimize(objective,np.zeros(x.shape[-1]),args=(standardized,y,ridge),jac=True,method="L-BFGS-B",
        options=dict(maxiter=maxiter,ftol=design.FTOL,gtol=design.GTOL))
    loss,gradient=objective(result.x,standardized,y,ridge)
    gradient_inf=float(np.max(np.abs(gradient)))
    receipt=dict(success=bool(result.success),maxiter=int(maxiter),iterations=int(result.nit),evaluations=int(result.nfev),
        message=str(result.message),objective=loss,gradient_inf=gradient_inf,seconds=time.perf_counter()-start,
        scaling_seconds=scale_seconds,optimization_and_stationarity_seconds=time.perf_counter()-optimization_start)
    if not result.success or not np.isfinite(result.x).all() or not np.isfinite(loss) or gradient_inf>design.GRADIENT_LIMIT:
        raise FitFailure(json.dumps(dict(ridge=ridge,training_rows=len(y),**receipt),sort_keys=True))
    model=dict(kind="ridge",ridge=float(ridge),scale=scale.tolist(),beta=result.x.tolist(),inverse_temperature=1.)
    return model,receipt


def scores(model,x,template):
    if model["kind"]=="template":
        return np.asarray(template,dtype=np.float64)
    if model["kind"]!="ridge":
        raise ValueError("Unknown observer")
    scale=np.asarray(model["scale"]);beta=np.asarray(model["beta"])
    if x.shape[-1]!=len(beta):
        raise ValueError("Feature/model mismatch")
    return (centered(x)/scale)@beta


def predict(model,x,template):
    return softmax(model["inverse_temperature"]*scores(model,x,template))


def choose_temperature(z,y):
    candidates=[float(loss_bits(softmax(t*z),y).mean()) for t in design.TEMPERATURES]
    minimum=min(candidates)
    index=next(i for i,v in enumerate(candidates) if v<=minimum+1e-12)
    return design.TEMPERATURES[index],candidates,index


def select_and_fit(x,template,y,groups,outer_fold):
    """Receives development data only. No held-out labels/features are needed."""
    start=time.perf_counter();groups=np.asarray(groups,dtype=np.int64);y=np.asarray(y,dtype=np.int64)
    if len(x)!=len(y) or template.shape!=(len(y),4) or groups.shape!=y.shape:
        raise ValueError("Mismatched development arrays")
    group_ids,group_counts=np.unique(groups,return_counts=True)
    if len(set(group_counts.tolist()))!=1:
        raise ValueError("Equal per-source training weight required")
    inner=design.fold_map(group_ids,outer_fold)
    inner_folds=np.array([inner[int(g)] for g in groups])
    candidates=[];inner_receipts=[];calibration_seconds=0.;validation_prediction_seconds=0.
    for ridge in design.RIDGES:
        oof=np.full((len(y),4),np.nan)
        for fold in range(design.INNER_FOLDS):
            validation=inner_folds==fold;training=~validation
            train_groups=sorted(set(groups[training].tolist()));validation_groups=sorted(set(groups[validation].tolist()))
            assert not set(train_groups)&set(validation_groups)
            model,fit=fit_ridge(x[training],y[training],ridge)
            prediction_start=time.perf_counter();oof[validation]=scores(model,x[validation],template[validation])
            validation_prediction_seconds+=time.perf_counter()-prediction_start
            inner_receipts.append(dict(ridge=ridge,fold=fold,training_groups=train_groups,
                validation_groups=validation_groups,model=model,model_sha256=canonical_hash(model),fit=fit))
        assert np.isfinite(oof).all()
        calibration_start=time.perf_counter();temperature,losses,index=choose_temperature(oof,y)
        calibration_seconds+=time.perf_counter()-calibration_start
        candidates.append(dict(ridge=ridge,inverse_temperature=temperature,losses_bits=losses,
                               selected_temperature_index=index,selected_loss_bits=losses[index]))
    minimum=min(c["selected_loss_bits"] for c in candidates)
    chosen=next(i for i,c in enumerate(candidates) if c["selected_loss_bits"]<=minimum+1e-12)
    ridge_model,final_fit=fit_ridge(x,y,candidates[chosen]["ridge"])
    ridge_model["inverse_temperature"]=candidates[chosen]["inverse_temperature"]
    calibration_start=time.perf_counter();template_temperature,template_losses,template_index=choose_temperature(template,y)
    calibration_seconds+=time.perf_counter()-calibration_start
    template_model=dict(kind="template",inverse_temperature=template_temperature)
    return dict(ridge=ridge_model,template=template_model),dict(training_groups=group_ids.tolist(),
        inner_map=inner,candidates=candidates,selected_candidate=chosen,inner_fits=inner_receipts,
        final_fit=final_fit,template_calibration_losses_bits=template_losses,
        template_calibration_index=template_index,seconds=time.perf_counter()-start,
        calibration_seconds=calibration_seconds,validation_prediction_seconds=validation_prediction_seconds,
        model_fit_seconds=sum(r["fit"]["seconds"] for r in inner_receipts)+final_fit["seconds"],
        model_sha256=dict(ridge=canonical_hash(ridge_model),template=canonical_hash(template_model)))


def fit_outer(x,template,y,groups,outer_fold,shuffled=False):
    """Selection wrapper isolates a complete outer test block before label use."""
    groups=np.asarray(groups,dtype=np.int64);y=np.asarray(y,dtype=np.int64)
    mapping=design.fold_map(set(groups))
    training=np.array([mapping[int(g)]!=outer_fold for g in groups]);test=~training
    if not training.any() or not test.any():
        raise ValueError("Empty outer split")
    development_labels=design.shuffled_labels(y[training],groups[training]) if shuffled else y[training]
    models,receipt=select_and_fit(x[training],template[training],development_labels,groups[training],outer_fold)
    receipt.update(outer_fold=int(outer_fold),test_groups=sorted(set(groups[test].tolist())),
                   shuffled_training_labels=bool(shuffled))
    assert not set(receipt["training_groups"])&set(receipt["test_groups"])
    return models,receipt,test
