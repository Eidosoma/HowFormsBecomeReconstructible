"""Verify completed job commitments and interpretation coverage, read-only."""
import math
import support as s


def run():
    job=s.HERE/'jobs/audit_v1';out=s.HERE/'runs/audit_v1'
    meta=s.read(job/'job.json');manifest=s.read(out/'manifest.json');done=s.read(out/'COMPLETE.json')
    s.require(done['status']=='COMPLETE' and done['audit_status']=='PASS' and not (out/'FAILED.json').exists(),'Successful audit completion')
    s.require(manifest['job_sha256']==s.sha(job/'job.json') and manifest['inputs_sha256']==meta['inputs_sha256'],'Job commitment')
    for rel,digest in meta['inputs_sha256'].items():s.require(s.sha(job/'inputs/TT011'/rel)==digest,'Frozen input '+rel)
    for rel,digest in done['outputs_sha256'].items():s.require(s.sha(out/rel)==digest,'Completed output '+rel)
    benchmark=s.HERE/'runs'/meta['benchmark'];prior=s.read(benchmark/'COMPLETE.json')
    s.require(s.read(benchmark/'manifest.json')['inputs_sha256']==meta['inputs_sha256'],'Same successful benchmark inputs')
    for rel,digest in prior['outputs_sha256'].items():s.require(s.sha(benchmark/rel)==digest,'Benchmark output '+rel)
    intake=s.read(out/'INTAKE_AUDIT.json');alignment=s.read(out/'ALIGNMENT_AUDIT.json');scores=s.read(out/'SCORING_AUDIT.json')
    s.require(intake['status']==alignment['status']==scores['status']=='PASS','All final audit gates')
    s.require(intake['cases']==64 and intake['donor_slots']==128 and intake['diagnostic_contexts']==10880,'Complete construction and diagnostic scope')
    s.require(alignment['pairs']==alignment['independent_contradictions']==128 and alignment['published_certificates_checked']==256,'Complete certificate scope')
    s.require(alignment['unpinned_feasible']==alignment['pinned_feasible']==0,'Exact obstruction result')
    s.require(scores['raw_endpoints']==10880 and scores['dual_task_flags']==21760,'Complete dual-task scoring')
    expected=dict(reads=10880,state_rates=1280,block_summaries=160,rival_reads=3072,rival_blocks=24)
    s.require(scores['table_rows_checked']==expected,'All five tables')
    a=s.read(out/'analysis.json');v=s.read(out/'SCIENTIFIC_VERDICT.json')
    primary=a['fresh_intended_effects']['same_minus_opposite'];replacement=a['opposite_task_replacement']
    for row in [primary,replacement,a['signed_reward_minus_task_label']]:
        s.close(math.fsum(row['by_block'].values())/8,row['mean'],1e-12,'Equal-block reporting')
    s.require(v['primary_direction_observed']==(primary['mean']>0) and v['secondary_replacement_direction_observed']==(replacement['mean']>0),'Unchanged source directional rules')
    s.require(v['full_native_replay_performed'] is False and v['new_scientific_cohort'] is False and v['automatic_successor'] is False,'Bounded coverage claims')
    checks=s.read(out/'technical_checks.json');s.require(checks['status']=='PASS','Synthetic qualification')
    result=dict(status='PASS',recorded_utc=s.utc(),completion_utc=done['utc'],seconds=done['seconds'],
                completion_sha256=s.sha(out/'COMPLETE.json'),job_sha256=s.sha(job/'job.json'),closeout_code_sha256=s.sha(s.HERE/'closeout.py'),
                frozen_inputs_verified=len(meta['inputs_sha256']),outputs_verified=len(done['outputs_sha256']),
                diagnostic_contexts=intake['diagnostic_contexts'],recipient_donor_pairs=128,published_certificates_checked=256,
                raw_endpoints=10880,dual_task_flags=21760,table_rows=expected,primary=primary,replacement=replacement,
                signed_reward_minus_task_label=a['signed_reward_minus_task_label'],
                full_native_replay_performed=False,new_scientific_cohort=False,automatic_successor=False)
    s.dump(s.HERE/'CLOSEOUT.json',result);return result


if __name__=='__main__':
    import json
    print(json.dumps(run(),indent=2))
