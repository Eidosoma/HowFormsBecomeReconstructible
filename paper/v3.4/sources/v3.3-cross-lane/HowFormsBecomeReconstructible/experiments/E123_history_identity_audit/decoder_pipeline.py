"""Predict, seal, then score the predeclared E123 retained-data comparison."""
from __future__ import annotations
from collections import defaultdict
import csv
from datetime import datetime,timezone
import gzip
import json
from pathlib import Path
import time
import numpy as np
from E123_history_identity_audit import decoder_design as design
from E123_history_identity_audit import decoder_models as models
from E123_history_identity_audit import decoder_scores as scoring
from E123_history_identity_audit.decoder_data import ALIASES,VIEWS
from E123_history_identity_audit.export import HERE,sha,dump


def checked_dataset(path):
    path=Path(path);complete=json.loads((path/"COMPLETE.json").read_text())
    assert complete["status"]=="COMPLETE"
    for name,digest in complete["outputs_sha256"].items():assert sha(path/name)==digest,name
    manifest=json.loads((path/"DATASET_MANIFEST.json").read_text())
    assert manifest["status"]=="DATASET_COMPLETE" and manifest["targets_outside_feature_files"]
    return manifest


def fit_and_seal(dataset,output):
    dataset=Path(dataset);output=Path(output);output.mkdir(parents=True,exist_ok=False)
    manifest=checked_dataset(dataset);blocks=manifest["source_blocks"]
    code_hashes={n:sha(HERE/n) for n in ("decoder_design.py","decoder_features.py","decoder_models.py","decoder_scores.py","decoder_data.py","decoder_pipeline.py","DECODER_DESIGN_V1.md","DECODER_AMENDMENT_V2.md")}
    splits=design.split_manifest(blocks);dump(output/"SPLITS.json",splits)
    dump(output/"SOURCE.json",dict(dataset=str(dataset),manifest_sha256=sha(dataset/"DATASET_MANIFEST.json"),
        complete_sha256=sha(dataset/"COMPLETE.json"),evidence_status=manifest["evidence_status"],code_sha256=code_hashes))
    schema=json.loads((HERE/"PREDICTION_SCHEMA.json").read_text())
    columns=schema["columns"]+["training_control","primary_weight_numerator","primary_weight_denominator"]
    dump(output/"PREDICTION_COLUMNS.json",columns)
    model_files=[];series=[];fit_seconds=0.;prediction_seconds=0.;write_start=time.perf_counter()
    detailed_costs=dict(model_fit_seconds=0.,calibration_seconds=0.,validation_prediction_seconds=0.)
    duplicate_predictions={};duplicate_checks=0
    with gzip.open(output/"predictions.csv.gz","xt",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader()
        for factor in design.FACTORS:
            with np.load(dataset/f"features_factor_{factor}.npz",allow_pickle=False) as z:feature_arrays={k:z[k] for k in z.files}
            with gzip.open(dataset/f"metadata_factor_{factor}.json.gz","rt") as stream_in:metadata=json.load(stream_in)
            rows=metadata["checkpoint"]
            groups=np.array([r["source_block_id"] for r in rows],dtype=np.int64)
            y=np.array([r["true_label"] for r in rows],dtype=np.int64)
            training=np.array([r["horizon"] in design.TRAIN_HORIZONS and r["condition"] in ("own","foreign") for r in rows])
            assert training.sum()==len(blocks)*32
            fold_arrays={b:np.array([splits["outer"][r["source_block_id"]] for r in rs]) for b,rs in metadata.items()}
            fold_models={};prediction_arrays={}
            controls=("actual","shuffled") if factor==4 else ("actual",)
            for control in controls:
                for view in design.FIT_VIEWS:
                    prefix=f"checkpoint__{view}"
                    x=feature_arrays[prefix+"__features"];t=feature_arrays[prefix+"__template"]
                    for fold in range(design.OUTER_FOLDS):
                        start=time.perf_counter()
                        fitted,receipt,_=models.fit_outer(x[training],t[training],y[training],groups[training],fold,shuffled=control=="shuffled")
                        fit_seconds+=time.perf_counter()-start
                        for k in detailed_costs:detailed_costs[k]+=receipt[k]
                        name=f"models_factor_{factor}_{control}_{view}_fold_{fold}.json"
                        dump(output/name,dict(models=fitted,receipt=receipt,feature_schema=manifest["feature_schema"][prefix]))
                        model_files.append(output/name)
                        fold_models[control,view,fold]=(fitted,receipt)
                        start=time.perf_counter()
                        for boundary in metadata:
                            if control=="shuffled" and boundary!="checkpoint":continue
                            eligible=(fold_arrays[boundary]==fold)
                            if control=="shuffled":
                                eligible&=np.array([r["horizon"]==256 and r["condition"] in ("own","foreign") for r in metadata[boundary]])
                            for destination in VIEWS[boundary]:
                                if ALIASES.get(destination,destination)!=view:continue
                                key=f"{boundary}__{destination}"
                                xx=feature_arrays[key+"__features"][eligible];tt=feature_arrays[key+"__template"][eligible]
                                for kind,model in fitted.items():
                                    storage=(control,boundary,destination,kind)
                                    if storage not in prediction_arrays:
                                        prediction_arrays[storage]=np.full((len(metadata[boundary]),4),np.nan)
                                    prediction_arrays[storage][eligible]=models.predict(model,xx,tt)
                        prediction_seconds+=time.perf_counter()-start
            # Setup has no fitted parameters and shares the full dictionary.
            for boundary in metadata:
                prediction_arrays["actual",boundary,"setup","uniform"]=np.full((len(metadata[boundary]),4),.25)
            saved={}
            for index,(spec,p_all) in enumerate(sorted(prediction_arrays.items())):
                control,boundary,view,kind=spec;rs=metadata[boundary]
                valid=np.isfinite(p_all).all(axis=1)
                expected=np.ones(len(rs),dtype=bool) if control=="actual" else np.array([r["horizon"]==256 and r["condition"] in ("own","foreign") for r in rs])
                assert np.array_equal(valid,expected),spec
                indices=np.flatnonzero(valid);p=p_all[valid];q=models.smooth(p)
                keys=np.array([manifest["dictionary_keys"][str(rs[i]["source_block_id"])] for i in indices])
                decision,tie,identical=scoring.decisions(p,keys)
                key=f"series_{index:03d}"
                saved[key+"__p"]=p;saved[key+"__q"]=q;saved[key+"__indices"]=indices
                series.append(dict(factor=factor,control=control,boundary=boundary,input_set=view,decoder=kind,
                    array_key=key,cases=len(indices),file=f"probabilities_factor_{factor}.npz"))
                for j,i in enumerate(indices):
                    row=rs[int(i)];fold=int(fold_arrays[boundary][i]);base=ALIASES.get(view,view)
                    if view=="setup":
                        model_hash=models.canonical_hash(dict(kind="uniform",p=[.25]*4));scaler_hash=models.canonical_hash(None)
                        feature_hash=models.canonical_hash(dict(setup="A,D identical within balanced stratum"))
                    else:
                        fitted,receipt=fold_models[control,base,fold]
                        model_hash=receipt["model_sha256"][kind]
                        scaler_hash=models.canonical_hash(fitted[kind].get("scale"))
                        feature_hash=models.canonical_hash(manifest["feature_schema"][f"{boundary}__{view}"])
                        duplicate_key=(factor,control,kind,base,fold,row["resource_sha256"][view])
                        if duplicate_key in duplicate_predictions:
                            np.testing.assert_allclose(p[j],duplicate_predictions[duplicate_key],rtol=0,atol=1e-12);duplicate_checks+=1
                        else:duplicate_predictions[duplicate_key]=p[j].copy()
                    primary=factor==4 and boundary=="checkpoint" and row["horizon"]==256 and row["condition"] in ("own","foreign")
                    out=dict(analysis_id="E123_identity_v1",source_block_id=row["source_block_id"],record_id=row["record_id"],pair_id=row["pair_id"],
                        regime="E014_E122_native_spatial",unit="source_block",condition=row["condition"],boundary=boundary,horizon=row["horizon"],
                        factor=factor,packet_bytes=row["packet_bytes"],fold_id=fold,exposure_status=manifest["evidence_status"],
                        target_id="acquisition_founder_four_way",true_label=row["true_label"],candidate_dictionary_id=row["candidate_dictionary_id"],
                        candidate_label_mapping="0,1,2,3",input_set_id=view,decoder_id=kind,model_sha256=model_hash,scaler_sha256=scaler_hash,
                        feature_schema_sha256=feature_hash,probability_rule_id="uniform_mixture_epsilon_1e-6",categorical_decision=int(decision[j]),
                        tie_flag=int(tie[j]),sample_weight_numerator=1,sample_weight_denominator=8*len(blocks),
                        prior_weight_profile_id="uniform_four_way_equal_source_condition_stratum",native_outcome_id=row["native_outcome_id"],
                        native_target=row["native_target"],native_qualified_count=row["native_qualified_count"],native_sign_count=row["native_sign_count"],
                        native_amplitude_count=row["native_amplitude_count"],native_cells=row["native_cells"],training_control=control,
                        primary_weight_numerator=int(primary),primary_weight_denominator=16*len(blocks))
                    out.update({f"raw_p{k}":float(p[j,k]) for k in range(4)});out.update({f"scored_p{k}":float(q[j,k]) for k in range(4)})
                    writer.writerow(out)
            np.savez_compressed(output/f"probabilities_factor_{factor}.npz",**saved)
    dump(output/"SERIES.json",series)
    dump(output/"COSTS_PREDICTION.json",dict(fitting_tuning_calibration_seconds=fit_seconds,inference_seconds=prediction_seconds,
        elapsed_prediction_phase_seconds=time.perf_counter()-write_start,dataset_costs=manifest["costs"],
        duplicate_probability_checks=duplicate_checks,native_reader_costs_are_in_dataset_source_manifest=True,**detailed_costs))
    for name,digest in code_hashes.items():assert sha(HERE/name)==digest,name
    files=[p for p in sorted(output.iterdir()) if p.is_file()]
    scoring.seal_files(output,files,dict(utc=datetime.now(timezone.utc).isoformat(),evidence_status=manifest["evidence_status"],
        dataset_manifest_sha256=sha(dataset/"DATASET_MANIFEST.json"),source_blocks=len(blocks),aggregate_scoring_started=False))
    return dict(status="PREDICTIONS_SEALED",source_blocks=len(blocks),series=len(series),duplicate_probability_checks=duplicate_checks)


def score_sealed(dataset,output):
    start=time.perf_counter();dataset=Path(dataset);output=Path(output)
    scoring.verify_seal(output);manifest=checked_dataset(dataset)
    source=json.loads((output/"SOURCE.json").read_text())
    assert source["manifest_sha256"]==sha(dataset/"DATASET_MANIFEST.json")
    series=json.loads((output/"SERIES.json").read_text());reports=[];primary={};primary_absolute={};null_alerts=[]
    for factor in design.FACTORS:
        with np.load(output/f"probabilities_factor_{factor}.npz",allow_pickle=False) as z:prob={k:z[k] for k in z.files}
        with gzip.open(dataset/f"metadata_factor_{factor}.json.gz","rt") as f:metadata=json.load(f)
        for s in [s for s in series if s["factor"]==factor]:
            indices=prob[s["array_key"]+"__indices"];p=prob[s["array_key"]+"__p"]
            rows=[metadata[s["boundary"]][int(i)] for i in indices]
            groups=np.array([r["source_block_id"] for r in rows]);y=np.array([r["true_label"] for r in rows])
            keys=np.array([manifest["dictionary_keys"][str(g)] for g in groups])
            for horizon,condition in sorted({(r["horizon"],r["condition"]) for r in rows}):
                mask=np.array([r["horizon"]==horizon and r["condition"]==condition for r in rows])
                summary=scoring.summarize(p[mask],y[mask],groups[mask],keys[mask])
                selected=[r for r,m in zip(rows,mask) if m]
                summary["native_counts"]=dict(qualified=sum(r["native_qualified_count"] for r in selected),
                    sign=sum(r["native_sign_count"] for r in selected),amplitude=sum(r["native_amplitude_count"] for r in selected),
                    cells=sum(r["native_cells"] for r in selected))
                reports.append(dict(**{k:s[k] for k in ("factor","control","boundary","input_set","decoder")},horizon=horizon,condition=condition,**summary))
            if factor==4 and s["boundary"]=="checkpoint":
                mask=np.array([r["horizon"]==256 and r["condition"] in ("own","foreign") for r in rows])
                key=(s["control"],s["decoder"],s["input_set"])
                primary[key]=(p[mask],y[mask],groups[mask],keys[mask])
                primary_absolute["/".join(key)]=scoring.summarize(p[mask],y[mask],groups[mask],keys[mask])
    comparisons={}
    for control in ("actual","shuffled"):
        for kind in ("ridge","template"):
            left,y,g,_=primary[control,kind,"record"];right,yr,gr,_=primary[control,kind,"joint"]
            np.testing.assert_array_equal(y,yr);np.testing.assert_array_equal(g,gr)
            comparisons[f"{control}/{kind}"]=scoring.paired_difference(left,right,y,g)
    for key,report in primary_absolute.items():
        if key.startswith("shuffled/") and report["log_loss_bits_ci95"][1]<2:
            null_alerts.append(dict(observer=key,reason="Positive null predictive information interval; retained diagnostic, not alone proof of leakage"))
    result=dict(status="POST_HOC_DECODER_ESTIMATES" if manifest["evidence_status"]!="SYNTHETIC_ONLY" else "SYNTHETIC_PIPELINE_ONLY",
        evidence_status=manifest["evidence_status"],primary=comparisons["actual/ridge"],comparisons=comparisons,
        primary_absolute=primary_absolute,all_strata=reports,null_diagnostics=null_alerts,source_blocks=len(manifest["source_blocks"]),
        seconds=time.perf_counter()-start,manuscript_changed=False,
        interpretation="Predictive performance for block-local donor identity; no conditional-information or causal-credit allocation")
    dump(output/"SCORES.json",result)
    lines=["# E123 retained identity audit", "", f"Status: **{result['status']}**", "",
        "Primary: 128-byte renewed records after 256 rewrites, regularized joint versus record observer.",
        f"Record-minus-joint log loss: {result['primary']['mean_bits']:.6f} bits; descriptive block interval {result['primary']['ci95_bits']}.",
        "", "Positive values mean better prediction from joint inputs. These are exposed-cohort auxiliary estimates; training folds overlap.",
        "The body here is regenerated from the record. Decoder improvement does not establish extra historical content from a surviving body.",
        "All condition/budget/horizon scores, confusion matrices, probability sensitivities, native counts and null diagnostics are in SCORES.json.",
        "No manuscript change; recognition and native reconstruction remain separate."]
    (output/"REPORT.md").write_text("\n".join(lines)+"\n")
    return dict(status=result["status"],source_blocks=result["source_blocks"],strata=len(reports),seconds=result["seconds"])
