"""Excluded synthetic qualification and bounded cost measurements for E123."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import shutil
import sys
import time
import traceback
import numpy as np

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
from E123_history_identity_audit import decoder_design as design
from E123_history_identity_audit import decoder_features as features
from E123_history_identity_audit import decoder_models as models
from E123_history_identity_audit import decoder_scores as scoring
from E123_history_identity_audit.interface import encode
from E123_history_identity_audit.export import sha,dump


def synthetic_fields(factor=4,n=32):
    rng=np.random.Generator(np.random.PCG64(123941))
    d=rng.normal(0,.3,(4,4,4)).repeat(4,1).repeat(4,2)
    d-=d.mean(axis=(-2,-1),keepdims=True)
    y=np.arange(n,dtype=np.int64)%4
    state=d[y]+rng.normal(0,.06,(n,16,16))
    return dict(A_background=np.zeros((16,16),dtype=np.float64),A_factor=np.array(factor,dtype=np.int64),D=d,
        R=encode(state,factor),B=np.stack([state+rng.normal(0,.02,state.shape) for _ in range(3)],axis=1)),y


def restrict(payload,view):
    return {k:v for k,v in payload.items() if k in features.COMMON|features.RESOURCES[view]}


def synthetic_training(nblocks=16,perblock=16,dimension=10):
    rng=np.random.Generator(np.random.PCG64(123942+dimension))
    groups=np.repeat(np.arange(9100000,9100000+nblocks),perblock)
    y=np.tile(np.arange(perblock,dtype=np.int64)%4,nblocks)
    latent=rng.normal(0,.2,(len(y),4,10))
    x=np.tile(latent,(1,1,(dimension+9)//10))[...,:dimension]+rng.normal(0,.02,(len(y),4,dimension))
    x[np.arange(len(y)),y,0]+=1.4
    template=x[...,0]+rng.normal(0,.05,(len(y),4))
    return x,template,y,groups


def test(output):
    checks=[]
    payload,yfield=synthetic_fields()
    stored={}
    for view,dimension in (("record",10),("body",36),("joint",52)):
        x,t,names=features.build(restrict(payload,view),view)
        assert x.shape==(32,4,dimension) and len(names)==dimension
        assert np.array_equal(t.argmax(axis=1),yfield)
        stored[view]=(x,t)
        bad=dict(restrict(payload,view),true_label=yfield)
        try:features.build(bad,view)
        except ValueError:pass
        else:raise AssertionError("Target metadata entered features")
        order=np.array([2,0,3,1]);relabel=np.argsort(order)
        perm=dict(restrict(payload,view),D=payload["D"][order])
        xp,tp,_=features.build(perm,view)
        np.testing.assert_allclose(xp,x[:,order],rtol=0,atol=1e-14)
        np.testing.assert_allclose(tp,t[:,order],rtol=0,atol=1e-14)
        assert np.array_equal(tp.argmax(axis=1),relabel[yfield])
        row_order=np.arange(32)[::-1]
        row_payload={k:(v[row_order] if k in ("R","B") else v) for k,v in restrict(payload,view).items()}
        xr,tr,_=features.build(row_payload,view)
        np.testing.assert_array_equal(xr,x[row_order]);np.testing.assert_array_equal(tr,t[row_order])
    zero=dict(restrict(payload,"joint"),R=np.zeros_like(payload["R"]),B=np.zeros_like(payload["B"]))
    z,zt,_=features.build(zero,"joint");assert np.isfinite(z).all() and np.all(zt==0)
    checks.append("Feature dimensions, exact whitelist, candidate relabeling, row invariance and zero norms")

    x,t,y,groups=synthetic_training()
    z=models.centered(x[:19]);scale=np.maximum(np.sqrt(np.mean(z*z,axis=(0,1))),1e-12);z/=scale
    beta=np.linspace(-.1,.1,10);value,gradient=models.objective(beta,z,y[:19],.1)
    numeric=[]
    for i in range(len(beta)):
        left=beta.copy();right=beta.copy();left[i]-=1e-6;right[i]+=1e-6
        numeric.append((models.objective(right,z,y[:19],.1)[0]-models.objective(left,z,y[:19],.1)[0])/2e-6)
    np.testing.assert_allclose(gradient,numeric,rtol=0,atol=1e-8)
    model,fit=models.fit_ridge(x,y,.1)
    assert fit["success"] and fit["gradient_inf"]<=design.GRADIENT_LIMIT
    try:models.fit_ridge(x,y,.001,maxiter=0)
    except models.FitFailure as e:expected_failure=str(e)
    else:raise AssertionError("Nonconvergence was not rejected")
    checks.append("Analytic gradient against finite differences; finite stationary optimum; rejected nonconvergence")

    first,receipt,test_rows=models.fit_outer(x,t,y,groups,0)
    train_rows=~test_rows
    altered_y=y.copy();altered_y[test_rows]=(altered_y[test_rows]+1)%4
    second,second_receipt,_=models.fit_outer(x,t,altered_y,groups,0)
    assert receipt["model_sha256"]==second_receipt["model_sha256"]
    altered_x=x.copy();altered_x[test_rows]*=1e6
    altered_template=t.copy();altered_template[test_rows]*=1e6
    third,third_receipt,_=models.fit_outer(altered_x,altered_template,y,groups,0)
    assert receipt["model_sha256"]==third_receipt["model_sha256"]
    expected_scale=np.maximum(np.sqrt(np.mean(models.centered(x[train_rows])**2,axis=(0,1))),1e-12)
    np.testing.assert_array_equal(first["ridge"]["scale"],expected_scale)
    for inner in receipt["inner_fits"]:
        assert not set(inner["training_groups"])&set(inner["validation_groups"])
        assert not (set(inner["training_groups"])|set(inner["validation_groups"]))&set(receipt["test_groups"])
    permutation=np.arange(len(y))[::-1]
    reordered,reordered_receipt,_=models.fit_outer(x[permutation],t[permutation],y[permutation],groups[permutation],0)
    candidate_order=np.array([2,0,3,1]);inv=np.argsort(candidate_order)
    changed,_,_=models.fit_outer(x[:,candidate_order],t[:,candidate_order],inv[y],groups,0)
    for kind in first:
        p=models.predict(first[kind],x[test_rows],t[test_rows])
        np.testing.assert_allclose(models.predict(reordered[kind],x[test_rows],t[test_rows]),p,rtol=0,atol=1e-8)
        np.testing.assert_allclose(models.predict(changed[kind],x[test_rows][:,candidate_order],t[test_rows][:,candidate_order]),p[:,candidate_order],rtol=0,atol=1e-8)
        assert np.mean(p.argmax(axis=1)==y[test_rows])>.95
    null,null_receipt,_=models.fit_outer(x,t,y,groups,0,shuffled=True)
    assert null_receipt["shuffled_training_labels"]
    mapping=design.shuffle_map(set(groups));assert len({tuple(v) for v in mapping.values()})>1
    shuffled=design.shuffled_labels(y,groups)
    for g in set(groups):
        for label in range(4):
            assert len(set(shuffled[(groups==g)&(y==label)]))==1
    checks.append("Outer labels/features excluded; train-only scales; whole-source nested folds; row/dictionary equivariance; fixed block shuffle")

    probability=np.full((32,4),.25);keys=np.tile(scoring.candidate_keys(payload["D"]),(32,1))
    summary=scoring.summarize(probability,yfield,np.repeat(np.arange(8),4),keys)
    assert summary["accuracy"]==.25 and summary["log_loss_bits"]==2 and summary["predictive_information_bits"]==0
    assert sum(sum(r) for r in summary["confusion"])==32 and summary["tie_count"]==32
    wrong=np.eye(4)[(yfield+1)%4]
    poor=scoring.summarize(wrong,yfield,np.repeat(np.arange(8),4),keys)
    assert poor["predictive_information_bits"]<0 and np.isfinite(poor["log_loss_bits"])
    decision,tie,_=scoring.decisions(probability,keys)
    pd,pt,_=scoring.decisions(probability[:,candidate_order],keys[:,candidate_order])
    np.testing.assert_array_equal(pd,inv[decision]);np.testing.assert_array_equal(pt,tie)
    comparison=scoring.paired_difference(probability,np.eye(4)[yfield],yfield,np.repeat(np.arange(8),4))
    assert comparison["ci95_bits"][0]>1.9
    checks.append("Uniform 25%/2-bit baseline; categorical ties/confusion; negative information retained; paired score direction")

    fixture=output/"seal_fixture";fixture.mkdir()
    p=models.predict(first["ridge"],x[test_rows],t[test_rows])
    np.savez_compressed(fixture/"probabilities.npz",raw=p,scored=models.smooth(p))
    dump(fixture/"targets.json",dict(y=y[test_rows].tolist(),groups=groups[test_rows].tolist(),evidence_status="SYNTHETIC_ONLY"))
    dump(fixture/"models.json",dict(models=first,tuning=receipt))
    scoring.seal_files(fixture,[fixture/n for n in ("probabilities.npz","targets.json","models.json")],dict(evidence_status="SYNTHETIC_ONLY"))
    scoring.verify_seal(fixture)
    tampered=output/"intentionally_tampered_fixture";shutil.copytree(fixture,tampered)
    with (tampered/"targets.json").open("a") as f:f.write(" ")
    try:scoring.verify_seal(tampered)
    except ValueError:pass
    else:raise AssertionError("Modified sealed targets accepted")
    checks.append("Probabilities/models/targets sealed before scoring; altered target file rejected")
    dump(output/"SYNTHETIC_MODELS.json",dict(models=first,receipt=receipt,shuffle_models=null,shuffle_receipt=null_receipt))
    return dict(status="PASS",checks=checks,expected_nonconvergence=expected_failure,
                qualification_scope="Feature/model/scorer engine on excluded synthetic data; E122 ingestion and final release still pending",
                retained_data_fitted=False,new_native_trajectories=0)


def benchmark(output):
    measurements={};feature_seconds={}
    for view,dimension in (("record",10),("body",36),("joint",52)):
        payload,_=synthetic_fields(n=256)
        start=time.perf_counter();features.build(restrict(payload,view),view);feature_seconds[view]=time.perf_counter()-start
        x,t,y,groups=synthetic_training(nblocks=64,perblock=32,dimension=dimension)
        for shuffled in (False,True):
            models_,receipt,_=models.fit_outer(x,t,y,groups,0,shuffled=shuffled)
            name=view+("_shuffled" if shuffled else "_actual")
            measurements[name]=receipt["seconds"]
            dump(output/(name+".json"),dict(models=models_,receipt=receipt,evidence_status="SYNTHETIC_TIMING_ONLY"))
    # 2 budgets × 8 outer folds for actual fits, 1 primary budget × 8 for null.
    fitting=sum(t*(8 if name.endswith("shuffled") else 16) for name,t in measurements.items())
    construction=sum(feature_seconds.values())*64*2*1.125
    forecast=dict(measured_nested_seconds=measurements,measured_256_case_feature_seconds=feature_seconds,
        full_fitting_expected_seconds=fitting,full_feature_expected_seconds=construction,
        source_verification_reserved_seconds=180.,export_scoring_reserved_seconds=60.,
        expected_seconds=fitting+construction+240.,conservative_seconds=3*(fitting+construction+240.),
        caveat="Measured synthetic engine cost plus explicit source/export allowances, not a retained-data runtime measurement",
        one_numerical_thread=True,retained_data_fitted=False,new_native_trajectories=0)
    dump(output/"FORECAST.json",forecast)
    return dict(status="SYNTHETIC_BENCHMARK_COMPLETE",**forecast)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("action",choices=("test","benchmark"));parser.add_argument("--name",required=True)
    args=parser.parse_args()
    if not args.name or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for c in args.name):
        raise ValueError("Unique simple name required")
    output=HERE/"analysis"/args.name;output.mkdir(parents=True,exist_ok=False)
    available=sorted(os.sched_getaffinity(0));os.sched_setaffinity(0,{5 if 5 in available else available[-1]})
    inputs=[HERE/n for n in ("decoder_design.py","decoder_features.py","decoder_models.py","decoder_scores.py","decoder_checks.py","DECODER_DESIGN_V1.md","interface.py")]
    hashes={str(p.relative_to(ROOT)):sha(p) for p in inputs}
    for p in inputs:
        target=output/"inputs"/p.name;target.parent.mkdir(exist_ok=True);shutil.copyfile(p,target)
    start=time.perf_counter()
    dump(output/"START.json",dict(utc=datetime.now(timezone.utc).isoformat(),action=args.action,inputs_sha256=hashes,
        cpu_affinity=sorted(os.sched_getaffinity(0)),one_numerical_thread=True,evidence_status="SYNTHETIC_ONLY"))
    try:
        result=test(output) if args.action=="test" else benchmark(output)
        for rel,digest in hashes.items():assert sha(ROOT/rel)==digest,rel
        result.update(utc=datetime.now(timezone.utc).isoformat(),seconds=time.perf_counter()-start,inputs_sha256=hashes)
        dump(output/"RESULT.json",result)
        outputs={str(p.relative_to(output)):sha(p) for p in sorted(output.rglob("*")) if p.is_file()}
        dump(output/"COMPLETE.json",dict(status="COMPLETE",outputs_sha256=outputs,seconds=result["seconds"]))
        print(json.dumps({k:result[k] for k in ("status","seconds","retained_data_fitted","new_native_trajectories")},sort_keys=True))
    except BaseException:
        dump(output/"FAILED.json",dict(error=traceback.format_exc(),seconds=time.perf_counter()-start));raise


if __name__=="__main__":main()
