"""User-requested completion verification; no rerun or successor launch."""
import json
import support as s


def run():
    output=s.HERE/'runs/audit_v1';jobdir=s.HERE/'jobs/audit_v1';benchmark=s.HERE/'runs/benchmark_v1'
    complete=s.read(output/'COMPLETE.json');job=s.read(jobdir/'job.json');manifest=s.read(output/'manifest.json')
    s.require(complete['status']=='COMPLETE' and complete['audit_status']=='PASS' and complete['mode']=='audit','Successful full audit')
    s.require(complete['full_native_replay_performed'] and not complete['new_scientific_outcomes'],'Replay scope')
    s.require(not (output/'FAILED.json').exists(),'No failed final run')
    s.require(s.sha(jobdir/'job.json')==manifest['job_sha256']==s.read(s.HERE/'STARTUP_CHECK.json')['job_sha256'],'Job identity')
    bench_done=s.read(benchmark/'COMPLETE.json');bench_manifest=s.read(benchmark/'manifest.json')
    s.require(bench_done['status']=='COMPLETE' and bench_done['audit_status']=='PASS' and bench_done['mode']=='benchmark','Successful qualification')
    s.require(s.sha(benchmark/'COMPLETE.json')==job['qualification']['complete_sha256'],'Qualification identity')
    s.require(job['inputs_sha256']==manifest['inputs_sha256']==bench_manifest['inputs_sha256'],'Identical benchmark and audit inputs')
    for rel,digest in job['inputs_sha256'].items():
        s.require(s.sha(jobdir/'inputs/TT013'/rel)==digest,'Frozen audit input '+rel)
        s.require(s.sha(s.HERE/'jobs/benchmark_v1/inputs/TT013'/rel)==digest,'Frozen benchmark input '+rel)
    for folder,done in [(output,complete),(benchmark,bench_done)]:
        actual={str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file() and p.name not in ['STATUS.json','COMPLETE.json']}
        s.require(actual==set(done['outputs_sha256']),'Complete committed output set')
        for rel,digest in done['outputs_sha256'].items():s.require(s.sha(folder/rel)==digest,'Committed output '+rel)
    receipts=[s.read(output/f'replay_{block:06d}.json') for block in range(34000,34008)]
    totals={kind:sum(row['receipts'][kind]['trajectories'] for row in receipts) for kind in ['known','original','fresh']}
    arrays=sum(row['receipts'][kind]['arrays'] for row in receipts for kind in totals)
    s.require(totals==dict(known=64,original=576,fresh=9216) and arrays==152,'Complete replay coverage')
    s.require(all(row['status']=='PASS' and all(value['status']=='PASS' for value in row['receipts'].values()) for row in receipts),'Every replay receipt passes')
    native=s.read(output/'NATIVE_AUDIT.json');intake=s.read(output/'INTAKE_AUDIT.json');scoring=s.read(output/'SCORING_AUDIT.json')
    provenance=s.read(output/'PROVENANCE_AUDIT.json');technical=s.read(output/'TECHNICAL_CHECKS.json')
    s.require(all(row['status']=='PASS' for row in [native,intake,scoring,provenance,technical]),'Every audit stage passes')
    s.require(native['totals']==totals and native['native_array_comparisons']==arrays,'Replay summary coverage')
    s.require(intake['problems']==intake['independent_optimizer_checks']==64 and intake['independent_record_checks']==576 and intake['reconstructed_fields']==200,'Complete reconstruction')
    s.require(intake['missing_edges_outside_original_injury']==50 and intake['cases_with_extra_live_edges']==35,'Added live edges retained')
    s.require(scoring['original_mask_historical_identity'] and scoring['original_mask_recipient_identity_eligible_cases']==29,'Applicable original-mask identity')
    s.require(scoring['raw_endpoints']==9792 and scoring['dual_task_flags']==19584,'Complete endpoint scope')
    s.require(scoring['table_rows']==dict(reads=9792,state_rates=1152,block_summaries=144),'Complete table scope')
    s.require(provenance['information_boundary']['status']=='PASS' and not provenance['source_functions_executed'],'Information-boundary audit')
    analysis=s.read(output/'analysis.json');verdict=s.read(output/'SCIENTIFIC_VERDICT.json');primary=analysis['intended_effects']['recipient_minus_outgoing']
    s.require(verdict['primary']==primary and verdict['primary_direction_observed']==(primary['mean']>0),'Primary point rule preserved')
    s.require(verdict['recipient_minus_shuffled']==analysis['intended_effects']['recipient_minus_shuffled'],'Separate shuffle contrast')
    s.require(verdict['full_native_replay'] and not verdict['irreducible_historical_content_established'] and not verdict['new_scientific_cohort'],'Interpretation bounds')
    result=dict(status='PASS',recorded_utc=s.utc(),closeout_code_sha256=s.sha(s.HERE/'closeout.py'),
        completion_utc=complete['utc'],completion_sha256=s.sha(output/'COMPLETE.json'),job_sha256=s.sha(jobdir/'job.json'),
        benchmark_completion_sha256=s.sha(benchmark/'COMPLETE.json'),benchmark_outputs_verified=len(bench_done['outputs_sha256']),
        seconds=complete['seconds'],frozen_inputs_verified=len(job['inputs_sha256']),outputs_verified=len(complete['outputs_sha256']),
        native_replay_totals=totals,native_array_receipts_verified=arrays,optimizer_problems=64,records=576,reconstructed_fields=200,
        raw_endpoints=9792,dual_task_flags=19584,primary=primary,
        secondary_contrasts={key:value for key,value in analysis['intended_effects'].items() if key!='recipient_minus_outgoing'},
        fresh_intended_rates={key:row['intended'] for key,row in analysis['rate_summaries']['fresh'].items()},
        extra_live_edges=50,cases_with_extra_live_edges=35,full_native_replay_performed=True,
        source_scientific_functions_executed=False,source_aggregate_results_exposed_before_audit=True,
        new_scientific_cohort=False,automatic_polling=False,automatic_successor=False)
    s.dump(s.HERE/'CLOSEOUT.json',result)
    return {key:result[key] for key in ['status','completion_utc','completion_sha256','seconds','frozen_inputs_verified','outputs_verified','primary']}


if __name__=='__main__':print(json.dumps(run(),indent=2))
