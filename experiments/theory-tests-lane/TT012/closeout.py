"""User-requested completion check; no dynamics rerun or successor launch."""
import json
import support as s


def run():
    output=s.HERE/'runs/audit_v1';jobdir=s.HERE/'jobs/audit_v1'
    complete=s.read(output/'COMPLETE.json');job=s.read(jobdir/'job.json');manifest=s.read(output/'manifest.json')
    s.require(complete['status']=='COMPLETE' and complete['audit_status']=='PASS' and complete['mode']=='audit','Successful full audit')
    s.require(complete['full_native_replay_performed'] and not complete['new_scientific_outcomes'],'Replay scope')
    s.require(not (output/'FAILED.json').exists(),'No failed final run')
    s.require(s.sha(jobdir/'job.json')==manifest['job_sha256']==s.read(s.HERE/'STARTUP_CHECK.json')['job_sha256'],'Job identity')
    s.require(job['inputs_sha256']==manifest['inputs_sha256']==s.read(s.HERE/'runs/benchmark_v1/manifest.json')['inputs_sha256'],'Identical benchmark and audit inputs')
    for rel,digest in job['inputs_sha256'].items():s.require(s.sha(jobdir/'inputs/TT012'/rel)==digest,'Frozen input '+rel)
    for rel,digest in complete['outputs_sha256'].items():s.require(s.sha(output/rel)==digest,'Committed output '+rel)
    receipts=[s.read(output/f'replay_{block:06d}.json') for block in range(34000,34008)]
    totals={kind:sum(row['receipts'][kind]['trajectories'] for row in receipts) for kind in ['known','original','fresh']}
    arrays=sum(row['receipts'][kind]['arrays'] for row in receipts for kind in totals)
    s.require(totals==dict(known=64,original=576,fresh=9216) and arrays==152,'Complete replay coverage')
    s.require(all(row['status']=='PASS' and all(value['status']=='PASS' for value in row['receipts'].values()) for row in receipts),'Every replay receipt passes')
    native=s.read(output/'NATIVE_AUDIT.json');intake=s.read(output/'INTAKE_AUDIT.json');scoring=s.read(output/'SCORING_AUDIT.json')
    s.require(all(row['status']=='PASS' for row in [native,intake,scoring]),'Every audit stage passes')
    s.require(native['totals']==totals and native['native_array_comparisons']==arrays,'Replay summary coverage')
    s.require(intake['problems']==192 and intake['whole_hybrid_certificates']==128 and intake['reconstructed_fields']==208,'Complete reconstruction')
    s.require(scoring['raw_endpoints']==9792 and scoring['dual_task_flags']==19584,'Complete endpoint scope')
    s.require(scoring['table_rows']==dict(reads=9792,state_rates=1152,block_summaries=144),'Complete table scope')
    analysis=s.read(output/'analysis.json');verdict=s.read(output/'SCIENTIFIC_VERDICT.json');primary=analysis['intended_effects']['mean_alignment_effect']
    s.require(verdict['primary']==primary and verdict['primary_direction_observed']==(primary['mean']>0),'Primary point rule preserved')
    s.require(verdict['full_native_replay'] and not verdict['irreducible_historical_content_established'],'Interpretation bounds')
    result=dict(status='PASS',recorded_utc=s.utc(),closeout_code_sha256=s.sha(s.HERE/'closeout.py'),
        completion_utc=complete['utc'],completion_sha256=s.sha(output/'COMPLETE.json'),job_sha256=s.sha(jobdir/'job.json'),
        seconds=complete['seconds'],frozen_inputs_verified=len(job['inputs_sha256']),outputs_verified=len(complete['outputs_sha256']),
        native_replay_totals=totals,native_array_receipts_verified=arrays,optimizer_problems=192,hybrid_equivalence_checks=128,
        raw_endpoints=9792,dual_task_flags=19584,primary=primary,
        secondary_contrasts={key:analysis['intended_effects'][key] for key in ['aligned_minus_completion','aligned_minus_outgoing','own_minus_completion','completion_minus_outgoing']},
        fresh_intended_rates={key:row['intended'] for key,row in analysis['rate_summaries']['fresh'].items()},
        full_native_replay_performed=True,new_scientific_cohort=False,automatic_successor=False)
    s.dump(s.HERE/'CLOSEOUT.json',result)
    return {key:result[key] for key in ['status','completion_utc','completion_sha256','seconds','frozen_inputs_verified','outputs_verified','primary']}


if __name__=='__main__':print(json.dumps(run(),indent=2))
