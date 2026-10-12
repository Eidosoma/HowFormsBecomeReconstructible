"""Verify completed commitments, replay coverage and raw-score interpretation.

Read-only with respect to the frozen job and completed run. Does not rerun dynamics.
"""
import math
from pathlib import Path
import numpy as np
import support as s


def run():
    job=s.HERE/'jobs/audit_v1';out=s.HERE/'runs/audit_v1';frozen=job/'inputs/TT009'
    done=s.read(out/'COMPLETE.json');manifest=s.read(out/'manifest.json');meta=s.read(job/'job.json');plan=s.read(frozen/'plan.json')
    s.require(done['status']=='COMPLETE' and done['audit_status']=='PASS' and not (out/'FAILED.json').exists(),'Successful completion')
    s.require(manifest['job_sha256']==s.sha(job/'job.json') and manifest['inputs_sha256']==meta['inputs_sha256'],'Frozen job identity')
    for rel,h in meta['inputs_sha256'].items():s.require(s.sha(frozen/rel)==h,'Frozen input '+rel)
    for rel,h in done['outputs_sha256'].items():s.require(s.sha(out/rel)==h,'Completed output '+rel)
    s.require(done['blocks_completed']==plan['blocks'],'Complete block cohort')
    counts=dict(known=0,fixed=0,transfer=0,endpoint_scores=0);array_count=0;effects={'fixed':[], 'original':[], 'fresh':[]}
    scalar_scores=0;max_margin_error=0.
    for block in plan['blocks']:
        receipt=s.read(out/f'replay_{block:06d}.json')
        s.require(receipt['status']=='PASS' and receipt['block']==block,'Block replay identity')
        prepared=s.arrays(frozen/f'source/fixed/inputs/prepared/cases_{block:06d}.npz');n=len(prepared['founders'])
        known=receipt['known'];s.require(known['status']=='PASS' and known['cases']==n and known['arrays']==3,'Known replay coverage')
        s.require(set(known['array_sha256'])=={'birth','end','mean_ports'},'Known replay fields')
        for field,h in known['array_sha256'].items():s.require(s.descriptor(prepared['original_'+field])['sha256']==h,'Known native array receipt')
        counts['known']+=n;array_count+=3
        for kind in ['fixed','transfer']:
            replay=receipt[kind];raw=s.arrays(frozen/f'source/{kind}/run/reads_{block:06d}.npz')
            fields={'budgets','birth','end','port_windows','mean_ports','min_margin','both_pass'}
            s.require(replay['status']=='PASS' and replay['block']==block and replay['replicates']==list(range(16)),'Full replicate coverage')
            s.require(set(replay['array_sha256'])==fields and replay['arrays']==7,'Full native field coverage')
            for field,h in replay['array_sha256'].items():s.require(s.descriptor(raw[field])['sha256']==h,'Experimental native array receipt')
            trajectories=n*(3 if kind=='fixed' else 8)*16
            s.require(replay['trajectories']==trajectories and replay['endpoint_scores']==raw['both_pass'].size,'Block trajectory and endpoint counts')
            counts[kind]+=trajectories;counts['endpoint_scores']+=raw['both_pass'].size;array_count+=7
            passed=np.empty(raw['both_pass'].shape,dtype=bool)
            for frame,case,variant,rep in np.ndindex(passed.shape):
                sign=1 if int(raw['founders'][case])%2==0 else -1
                ports=raw['mean_ports'][frame,case,variant,rep]
                margin=min(sign*float(ports[0,0]),-sign*float(ports[0,1]),-sign*float(ports[1,0]),sign*float(ports[1,1]))
                max_margin_error=max(max_margin_error,abs(margin-float(raw['min_margin'][frame,case,variant,rep])))
                passed[frame,case,variant,rep]=margin>.25;scalar_scores+=1
            s.equal(passed,raw['both_pass'],'Scalar closeout success flags')
            frames=[(list(raw['budgets']).index(2048),'fixed')] if kind=='fixed' else [(0,'original'),(1,'fresh')]
            for frame,label in frames:
                first=passed[frame,:,1];second=passed[frame,:,0]
                effects[label].append((int(first.sum())-int(second.sum()))/first.size)
    s.require(counts==dict(known=64,fixed=3072,transfer=8192,endpoint_scores=17408),'Whole audit coverage')
    native=s.read(out/'NATIVE_AUDIT.json');s.require(native['counts']==counts and native['native_array_comparisons']==array_count==136,'Native summary agrees with receipts')
    fixed=s.read(out/'fixed_analysis.json');transfer=s.read(out/'transfer_analysis.json');verdict=s.read(out/'SCIENTIFIC_VERDICT.json')
    comparisons={'fixed':fixed['rewrite_effects']['2048'],'original':transfer['effects']['original']['rewrite'],'fresh':transfer['effects']['fresh']['rewrite']}
    independent={}
    for label,values in effects.items():
        mean=math.fsum(values)/len(values);row=comparisons[label]
        s.close(mean,row['mean'],1e-12,'Closeout equal-block effect')
        for block,value in zip(plan['blocks'],values,strict=True):s.close(value,row['by_block'][str(block)],1e-12,'Closeout block effect')
        independent[label]=dict(mean=mean,by_block=dict(zip(map(str,plan['blocks']),values,strict=True)),descriptive_source_interval_verified_by_worker=row['descriptive_block_bootstrap_95'])
    s.require(verdict['fresh_primary_prediction_passed']==(independent['fresh']['mean']>0)==transfer['primary_estimate_positive'],'Unchanged directional prediction')
    s.require(verdict['fresh_interval_spans_zero']==(comparisons['fresh']['descriptive_block_bootstrap_95'][0]<=0<=comparisons['fresh']['descriptive_block_bootstrap_95'][1]),'Uncertainty interpretation')
    for kind in ['fixed','transfer']:s.require(s.read(out/f'{kind}_SCORING_AUDIT.json')['status']=='PASS','Completed table/scoring audit')
    result=dict(status='PASS',recorded_utc=s.utc(),completion_utc=done['utc'],seconds=done['seconds'],completion_sha256=s.sha(out/'COMPLETE.json'),job_sha256=s.sha(job/'job.json'),
        frozen_inputs_verified=len(meta['inputs_sha256']),outputs_verified=len(done['outputs_sha256']),counts=counts,native_array_receipts_verified=array_count,
        scalar_endpoint_scores_checked=scalar_scores,maximum_scalar_margin_error=max_margin_error,independent_effects=independent,
        scientific_verdict=verdict['scientific_verdict'],classification=plan['classification'],new_scientific_cohort=False,
        requested_status_check=True,automatic_polling=False,successor_launched=False)
    s.dump(s.HERE/'CLOSEOUT.json',result);return result


if __name__=='__main__':
    import json
    print(json.dumps(run(),indent=2))
