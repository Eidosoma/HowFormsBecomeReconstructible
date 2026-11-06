"""Audit completed E123 predictions without refitting or changing frozen outputs."""
from __future__ import annotations
from collections import Counter
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback
import numpy as np

HERE=Path(__file__).resolve().parent; ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
from E123_history_identity_audit.export import sha,dump


def read(path): return json.loads(Path(path).read_text())


def main():
    allowed=sorted(os.sched_getaffinity(0));os.sched_setaffinity(0,{5 if 5 in allowed else allowed[-1]})
    output=HERE/'analysis'/'closeout_retained_v2';output.mkdir(parents=True,exist_ok=False)
    start=time.perf_counter();run=HERE/'runs'/'retained_v2';pred=run/'predictions';dataset=run/'dataset'
    try:
        complete=read(run/'COMPLETE.json');assert complete['status']=='COMPLETE'
        for rel,digest in complete['outputs_sha256'].items(): assert sha(run/rel)==digest,rel
        launch=read(HERE/'jobs'/'retained_v2'/'LAUNCH.json')
        for rel,digest in launch['inputs_sha256'].items():
            for base in (ROOT,run/'inputs',HERE/'jobs'/'retained_v2'/'inputs'):
                assert sha(base/rel)==digest,(base,rel)
        seal=read(pred/'PREDICTIONS_SEALED.json')
        assert seal['status']=='PREDICTIONS_SEALED_BEFORE_SCORING' and not seal['aggregate_scoring_started']
        assert seal['utc']<complete['utc']
        for rel,digest in seal['files_sha256'].items():assert sha(pred/rel)==digest,rel
        manifest=read(dataset/'DATASET_MANIFEST.json');splits=read(pred/'SPLITS.json');scores=read(pred/'SCORES.json')
        assert manifest['source_blocks']==list(range(12000,12064)) and manifest['targets_outside_feature_files']
        assert scores['source_blocks']==64 and scores['evidence_status']=='POST_HOC_RETAINED_E014_E122'
        assert sha(dataset/'DATASET_MANIFEST.json')==seal['dataset_manifest_sha256']
        source_files={}
        for source in manifest['sources']:
            for pathkey,hashkey in (('path','sha256'),('original_lineage_path','original_lineage_sha256')):
                path=source[pathkey];digest=source[hashkey]
                if path not in source_files:assert sha(ROOT/path)==digest,path
                source_files[path]=digest
        fits=[];model_count=0
        for path in sorted(pred.glob('models_*.json')):
            model_count+=1;receipt=read(path)['receipt'];train=set(receipt['training_groups']);test=set(receipt['test_groups'])
            assert len(train)==56 and len(test)==8 and train.isdisjoint(test)
            assert train|test==set(manifest['source_blocks'])
            for inner in receipt['inner_fits']:
                a=set(inner['training_groups']);b=set(inner['validation_groups'])
                assert len(a)==42 and len(b)==14 and a.isdisjoint(b) and a|b==train
                assert (a|b).isdisjoint(test)
            for fit in [r['fit'] for r in receipt['inner_fits']]+[receipt['final_fit']]:
                assert fit['success'] and fit['maxiter']==2000 and fit['iterations']<=2000
                assert np.isfinite(fit['objective']) and fit['gradient_inf']<=1e-5
                fits.append(fit)
        assert model_count==72 and len(fits)==1224
        seed=int(hashlib.sha256(b'E123:bootstrap:v1').hexdigest()[:32],16)
        bootstrap=np.random.Generator(np.random.PCG64(seed)).integers(0,64,size=(10000,64))
        strata={tuple(r[k] for k in ('factor','control','boundary','input_set','decoder','horizon','condition')):r
                for r in scores['all_strata']}
        series=read(pred/'SERIES.json');observations={};metadata_all={};indices_by_id={};block_exports=[];primary={}

        def evaluate(p,rows):
            y=np.array([r['true_label'] for r in rows]);groups=np.array([r['source_block_id'] for r in rows])
            assert np.isfinite(p).all() and np.all(p>=0) and np.all(p<=1)
            np.testing.assert_allclose(p.sum(axis=1),1,rtol=0,atol=1e-12)
            decision=[];ties=[]
            for probabilities,row in zip(p,rows):
                candidates=np.flatnonzero(probabilities>=probabilities.max()-1e-12)
                keys=manifest['dictionary_keys'][str(row['source_block_id'])]
                decision.append(min(candidates,key=lambda k:(keys[k],k)));ties.append(len(candidates)>1)
            decision=np.array(decision);ties=np.array(ties);correct=decision==y
            q=(1-4e-6)*p+1e-6;loss=-np.log2(q[np.arange(len(y)),y])
            block_loss=[];block_accuracy=[];block_rows=[]
            for block in manifest['source_blocks']:
                mask=groups==block;counts=np.bincount(y[mask],minlength=4)
                assert len(set(counts.tolist()))==1 and counts[0]>0
                n=int(mask.sum());c=int(correct[mask].sum());total=float(loss[mask].sum())
                block_loss.append(total/n);block_accuracy.append(c/n)
                block_rows.append(dict(source_block_id=block,n=n,correct=c,loss_bits_sum=total,
                    tie_count=int(ties[mask].sum()),predictive_information_bits=2-total/n))
            confusion=np.zeros((4,4),dtype=int)
            for actual,predicted in zip(y,decision):confusion[actual,predicted]+=1
            return dict(p=p,y=y,groups=groups,decisions=decision,ties=ties,block_rows=block_rows,
                block_loss=np.array(block_loss),block_accuracy=np.array(block_accuracy),confusion=confusion,
                n=len(y),correct=int(correct.sum()),tie_count=int(ties.sum()),loss=loss)

        def compare(measured,reported):
            for k in ('n','correct','tie_count'):assert measured[k]==reported[k],k
            np.testing.assert_array_equal(measured['confusion'],reported['confusion'])
            for k,value in (('accuracy',measured['block_accuracy'].mean()),('log_loss_bits',measured['block_loss'].mean()),
                            ('predictive_information_bits',2-measured['block_loss'].mean())):
                np.testing.assert_allclose(value,reported[k],rtol=0,atol=1e-12)
            for k,value in (('accuracy_ci95',measured['block_accuracy']),('log_loss_bits_ci95',measured['block_loss'])):
                ci=np.quantile(value[bootstrap].mean(axis=1),[.025,.975])
                np.testing.assert_allclose(ci,reported[k],rtol=0,atol=1e-12)
            for actual,expected in zip(measured['block_rows'],reported['block_counts']):
                assert actual.keys()==expected.keys()
                for k,v in actual.items():np.testing.assert_allclose(v,expected[k],rtol=0,atol=1e-12)
            for epsilon in (1e-9,.001):
                q=(1-4*epsilon)*measured['p']+epsilon
                value=-np.log2(q[np.arange(len(q)),measured['y']]).mean()
                np.testing.assert_allclose(value,reported['sensitivity_log_loss_bits'][str(epsilon)],rtol=0,atol=1e-12)

        checked_strata=0;expected_csv_rows=0
        for factor in (1,4):
            with gzip.open(dataset/f'metadata_factor_{factor}.json.gz','rt') as f: metadata=json.load(f)
            metadata_all[factor]=metadata
            for boundary,rows in metadata.items():
                indices_by_id[factor,boundary]={r['record_id']:i for i,r in enumerate(rows)}
                assert len(indices_by_id[factor,boundary])==len(rows)
            with np.load(pred/f'probabilities_factor_{factor}.npz',allow_pickle=False) as arrays:
                for s in (s for s in series if s['factor']==factor):
                    indices=arrays[s['array_key']+'__indices'];p=arrays[s['array_key']+'__p'];q=arrays[s['array_key']+'__q']
                    rows=[metadata[s['boundary']][int(i)] for i in indices]
                    np.testing.assert_array_equal(q,(1-4e-6)*p+1e-6)
                    full=np.full((len(metadata[s['boundary']]),4),np.nan);full[indices]=p
                    fullq=np.full_like(full,np.nan);fullq[indices]=q
                    key=tuple(s[k] for k in ('factor','control','boundary','input_set','decoder'))
                    observations[key]=(full,fullq);expected_csv_rows+=len(rows)
                    for horizon,condition in sorted({(r['horizon'],r['condition']) for r in rows}):
                        mask=np.array([r['horizon']==horizon and r['condition']==condition for r in rows])
                        selected=[r for r,keep in zip(rows,mask) if keep]
                        measured=evaluate(p[mask],selected);reported=strata[key+(horizon,condition)];compare(measured,reported)
                        native={k:sum(r[f'native_{field}'] for r in selected) for k,field in (
                            ('qualified','qualified_count'),('sign','sign_count'),('amplitude','amplitude_count'),('cells','cells'))}
                        assert native==reported['native_counts']
                        for b in measured['block_rows']:
                            local=[r for r in selected if r['source_block_id']==b['source_block_id']]
                            block_exports.append(dict(zip(('factor','control','boundary','input_set','decoder'),key),
                                horizon=horizon,condition=condition,**b,
                                native_qualified=sum(r['native_qualified_count'] for r in local),
                                native_sign=sum(r['native_sign_count'] for r in local),
                                native_amplitude=sum(r['native_amplitude_count'] for r in local),
                                native_cells=sum(r['native_cells'] for r in local)))
                        checked_strata+=1
                    if factor==4 and s['boundary']=='checkpoint':
                        mask=np.array([r['horizon']==256 and r['condition'] in ('own','foreign') for r in rows])
                        selected=[r for r,keep in zip(rows,mask) if keep]
                        measured=evaluate(p[mask],selected)
                        primary_key='/'.join(s[k] for k in ('control','decoder','input_set'))
                        compare(measured,scores['primary_absolute'][primary_key]);primary[primary_key]=measured
        assert checked_strata==548
        for control in ('actual','shuffled'):
            for kind in ('ridge','template'):
                left=primary[f'{control}/{kind}/record'];right=primary[f'{control}/{kind}/joint']
                np.testing.assert_array_equal(left['y'],right['y']);np.testing.assert_array_equal(left['groups'],right['groups'])
                difference=left['block_loss']-right['block_loss'];r=scores['comparisons'][f'{control}/{kind}']
                np.testing.assert_allclose(difference,r['block_differences'],rtol=0,atol=1e-12)
                np.testing.assert_allclose(difference.mean(),r['mean_bits'],rtol=0,atol=1e-12)
                np.testing.assert_allclose(np.quantile(difference[bootstrap].mean(axis=1),[.025,.975]),r['ci95_bits'],rtol=0,atol=1e-12)
        # Check the portable CSV against both sealed arrays and separate native metadata.
        seen=set();csv_rows=0
        with gzip.open(pred/'predictions.csv.gz','rt',newline='') as f:
            for row in csv.DictReader(f):
                factor=int(row['factor']);boundary=row['boundary']
                key=(factor,row['training_control'],boundary,row['input_set_id'],row['decoder_id'])
                i=indices_by_id[factor,boundary][row['record_id']];unique=key+(i,)
                assert unique not in seen;seen.add(unique)
                native=metadata_all[factor][boundary][i];p,q=observations[key]
                assert tuple(float(row[f'raw_p{k}']) for k in range(4))==tuple(p[i])
                assert tuple(float(row[f'scored_p{k}']) for k in range(4))==tuple(q[i])
                for k in ('source_block_id','true_label','horizon','native_target','native_qualified_count','native_sign_count','native_amplitude_count','native_cells'):
                    assert int(row[k])==native[k],k
                assert row['condition']==native['condition']
                assert int(row['fold_id'])==splits['outer'][str(native['source_block_id'])]
                options=np.flatnonzero(p[i]>=p[i].max()-1e-12)
                keys=manifest['dictionary_keys'][str(native['source_block_id'])]
                decision=min(options,key=lambda k:(keys[k],k))
                assert int(row['categorical_decision'])==decision and int(row['tie_flag'])==int(len(options)>1)
                isprimary=factor==4 and boundary=='checkpoint' and native['horizon']==256 and native['condition'] in ('own','foreign')
                assert int(row['primary_weight_numerator'])==int(isprimary)
                assert int(row['primary_weight_denominator'])==1024
                assert int(row['sample_weight_numerator'])==1 and int(row['sample_weight_denominator'])==512
                csv_rows+=1
        assert csv_rows==expected_csv_rows
        with gzip.open(output/'block_scores.csv.gz','xt',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(block_exports[0]));writer.writeheader();writer.writerows(block_exports)
        compact=dict(source_blocks=64,primary={k:v for k,v in scores['primary'].items() if k!='block_differences'},
            absolute={k:{kk:vv for kk,vv in v.items() if kk!='block_counts'} for k,v in scores['primary_absolute'].items()},
            comparisons={k:{kk:vv for kk,vv in v.items() if kk!='block_differences'} for k,v in scores['comparisons'].items()},
            null_diagnostics=scores['null_diagnostics'],costs=read(pred/'COSTS_PREDICTION.json'),
            source_manifest=str((dataset/'DATASET_MANIFEST.json').relative_to(ROOT)),
            original_predictions=str((pred/'predictions.csv.gz').relative_to(ROOT)))
        dump(output/'SUMMARY.json',compact)
        # Preserve all inputs to this check, including the unsuccessful V1 run.
        for rel,digest in complete['outputs_sha256'].items():assert sha(run/rel)==digest,rel
        preserved=read(HERE/'analysis/optimizer_amendment_v2/PRESERVED_V1.json')
        for rel,digest in preserved.items():assert sha(ROOT/rel)==digest,rel
        receipt=dict(status='PASS',utc=datetime.now(timezone.utc).isoformat(),seconds=time.perf_counter()-start,
            complete_sha256=sha(run/'COMPLETE.json'),script_sha256=sha(Path(__file__)),
            verified_run_outputs=len(complete['outputs_sha256']),verified_frozen_inputs=len(launch['inputs_sha256']),
            verified_sealed_files=len(seal['files_sha256']),verified_source_archives=len(source_files),source_blocks=64,
            model_files=model_count,successful_fits=len(fits),maximum_iterations=max(r['iterations'] for r in fits),
            maximum_gradient_inf=max(r['gradient_inf'] for r in fits),fits_exceeding_original_cap=sum(r['iterations']>300 for r in fits),
            scores_recomputed=checked_strata,primary_absolute_scores_recomputed=len(primary),paired_comparisons_recomputed=4,
            csv_rows_verified=csv_rows,block_score_rows=len(block_exports),v1_files_preserved=len(preserved),
            new_fits=0,new_native_trajectories=0,scientific_outputs_modified=False,
            scope='Source and artifact hashes; fit convergence/group exclusions; independent score/interval/native-count recomputation from sealed arrays; full CSV reconciliation. No model refit or native replay.',
            outputs_sha256={p.name:sha(p) for p in output.iterdir() if p.is_file()})
        dump(output/'RESULT.json',receipt)
        print(json.dumps({k:receipt[k] for k in ('status','seconds','verified_run_outputs','verified_source_archives','successful_fits','scores_recomputed','csv_rows_verified')}))
    except BaseException:
        dump(output/'FAILED.json',dict(utc=datetime.now(timezone.utc).isoformat(),error=traceback.format_exc(),seconds=time.perf_counter()-start));raise


if __name__=='__main__':main()
