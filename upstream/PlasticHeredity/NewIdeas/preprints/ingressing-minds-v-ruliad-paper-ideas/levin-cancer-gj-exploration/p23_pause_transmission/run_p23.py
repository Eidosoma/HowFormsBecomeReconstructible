"""Execute P23 readouts without editing or re-preparing archived P22 donors."""
import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import numpy as np
import p23_design as d
import run_p22 as p22
from run_paper_preparation_support import RateExperiment, phase, observe, prior_runner
from analyze_paper_sheet import arrays
import paper_bounded_clock as clock

def stock(run,fine): return p22.stock(run/'inputs/p22',fine)
def trajectory(exp,c,run):
    path=run/'inputs/p22'/d.source(c); parent=d.read(path/'result.json')
    donors=arrays(path,'isolated_2')['final']; ids=parent['phases'][-1]['setup']['cell_ids'].copy()
    base=parent['outcome']['logical_end']; fresh=d.pupils(c); _,M=stock(run,c['fine'])
    if parent['case']!=d.parent(c) or base!=1201800: raise ValueError('Wrong P23 donor source')
    if donors.shape!=(17,3) or not np.isfinite(donors).all() or (donors<0).any(): raise ValueError('Invalid archived donor state')
    recipients=np.repeat(M,3,axis=1); recipient_initial=''.join(exp.z.GRN.state_char(x) for x in recipients.T)
    if recipient_initial!='MMM': raise ValueError('Readout recipients not M')
    if set(fresh)&set(ids+parent['outcome']['fork_ids']+parent['outcome']['original_ids']): raise ValueError('Recipient identity reused')
    donor_initial=''.join(exp.z.GRN.state_char(x) for x in donors.T)
    exp.configure([2,3],ids+fresh,np.concatenate((donors,recipients),axis=1),'depol',60,
        0 if c['readout']=='rna' else 1.25e-14,patch=[0,1,2],cut=c['readout']=='cut')
    value=phase(exp,'contact',20000,base); observations={'contact':observe(exp,'contact',range(3,6),False)}
    donor_end=''.join(exp.z.GRN.state_char(x) for x in value[:,:3].T)
    cursor=prior_runner.holds(exp,fresh,value[:,3:],base+20000,observations)
    out=dict(available=True,parent_retained_E=parent['outcome']['retained_E'],donor_initial_labels=donor_initial,
        recipient_initial_labels=recipient_initial,donor_end_labels=donor_end,observations=observations,
        contact_stable_E=all(observations['contact']['stable_E']),transmitted_E=all(prior_runner.retained(observations)),logical_end=cursor)
    provenance=dict(actual_parent='p22/'+d.source(c),parent_result_sha256=d.digest(path/'result.json'),
        parent_phase_sha256=d.digest(path/'isolated_2.npz'))
    return out,provenance
def result_record(exp,c,out,provenance):
    return dict(case=c,ion_indices=exp.indices,phases=exp.records,outcome=out,provenance=provenance,
        execution_pass=True,clock_method=clock.METHOD,clock_policy='phase_scaled_sampling_and_step_cap_v1',
        external_schedule=True,all_cells_evolve=True,archived_parent_readout=True,fixed_onward_schedules=True,
        selected_using_prior_results=True,parent_states_edited=False,algebraic_refresh=False,donors_clamped=False,
        repeated_pause=False,new_renewal_trajectories=False,autonomous_reproduction=False,cell_division_simulated=False,
        parameter_retuning=False,independent_biological_replicates=False,outcome_dependent_selection=False,
        automatic_follow_on=False,historical_numeric_replay=d.replay(c))
def worker(path):
    if path!=path.resolve(): raise ValueError('Worker cannot write through a directory reference')
    run=path.parent.parent; d.check_run_path(run); spec=d.read(path); c=spec['case']
    d.validate_config(spec['config']); summary=d.read(run/'summary.json')
    if c not in d.fixed_cases() or path.parent.name!=c['id'] or spec['inputs']!=str(run/'inputs'):
        raise ValueError('Unregistered P23 worker')
    if summary['stage']!=c['stage']: raise ValueError('Wrong P23 stage')
    if d.manifest()!=summary['hashes_sha256']: raise RuntimeError('P23 worker source changed')
    history=summary.get('predecessor_audit',{}); hp=run/'predecessor_audit.json'
    if not (summary.get('predecessor_gate') and history.get('quality_gate') and d.read(hp)==history and
            d.digest(hp)==summary.get('predecessor_audit_sha256')):
        raise ValueError('P22 preflight has not passed')
    for stage in d.STAGES[:d.STAGES.index(c['stage'])]:
        gp=run/(stage+'_audit.json'); gate=d.read(gp)
        if not gate['quality_gate'] or summary['gates'].get(stage)!=gate or summary['gate_hashes'].get(stage)!=d.digest(gp):
            raise ValueError('Invalid previous stage audit')
    key='p22/'+d.source(c); record=d.read(run/'inputs'/key/'result.json')
    names=['result.json','assembly/assembly.json','assembly/checkpoint.npz']+[rec['phase']+'.npz' for rec in record['phases']]
    for tail in names:
        name=key+'/'+tail
        if name not in summary['inputs'] or d.digest(run/'inputs'/name)!=summary['inputs'][name]['sha256']:
            raise ValueError('Archived parent changed')
    if not d.space_available(path.parent): raise RuntimeError('Require 5 GiB external reserve')
    exp=RateExperiment(path.parent,dict(id=c['id'],fine=c['fine']))
    with d.recovery.external_phases(): out,provenance=trajectory(exp,c,run)
    d.write_json(path.parent/'result.json',result_record(exp,c,out,provenance)); return 0

def run_worker(c,run,deadline,env):
    row=dict(id=c['id'],execution_pass=False); left=deadline-time.monotonic()
    if left<=0: return dict(row,status='not_launched_budget')
    if not d.space_available(run): return dict(row,status='not_launched_disk')
    folder=run/c['id']; folder.mkdir()
    d.write_json(folder/'spec.json',dict(case=c,config=d.FIXED,inputs=str(run/'inputs')))
    start=time.monotonic(); print('Starting '+c['id'],flush=True)
    with (folder/'stdout.log').open('x') as output:
        try:
            p=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--worker',str(folder/'spec.json')],
                cwd=d.ROOT,env=env,stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,
                timeout=min(left,d.FIXED['worker_timeout_seconds']))
            row.update(status='finished',returncode=p.returncode)
        except subprocess.TimeoutExpired: row.update(status='timeout',returncode=None)
    row['elapsed_seconds']=time.monotonic()-start
    if (folder/'result.json').exists():
        result=d.read(folder/'result.json'); row.update(result=result,result_sha256=d.digest(folder/'result.json'))
        row['execution_pass']=row['returncode']==0 and result['execution_pass']
    print(c['id']+(': VALID' if row['execution_pass'] else ': INVALID'),flush=True)
    return row

def execute_stage(cases,run,summary,deadline,env):
    """Only two in flight; never submit another case after an observed failure."""
    todo=iter(cases); valid=True
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending={pool.submit(run_worker,c,run,deadline,env) for c in [next(todo),next(todo)]}
        while pending:
            done,pending=wait(pending,return_when=FIRST_COMPLETED)
            for task in done:
                row=task.result(); summary['cases'].append(row); valid &= bool(row['execution_pass'])
                d.write_json(run/'summary.json',summary)
            if valid:
                for _ in done:
                    c=next(todo,None)
                    if c is not None: pending.add(pool.submit(run_worker,c,run,deadline,env))
    return valid and {r['id'] for r in summary['cases'] if r['id'] in {c['id'] for c in cases}}=={c['id'] for c in cases}

def run(job):
    import analyze_p23 as audit
    from supervise_p23 import child_env, now
    d.verify_launch(job); status=d.read(job/'status.json')
    if status.get('verification_exit_code')!=0 or status.get('verification_log_sha256')!=d.digest(job/'verification.log'):
        raise RuntimeError('P23 software verification has not passed')
    if not d.space_available(d.RUNS): raise RuntimeError('Require 5 GiB external reserve')
    start=time.monotonic(); deadline=start+d.FIXED['total_budget_seconds']
    folder=Path(tempfile.mkdtemp(prefix='p23-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-',dir=d.RUNS))
    d.archive_view(folder); (folder/'frozen').symlink_to(job/'frozen',target_is_directory=True)
    launch=d.read(job/'launch.json')
    summary=dict(started_utc=now(),job=str(job),revision=d.REVISION,config=d.FIXED,registered_cases=d.fixed_cases(),
        cases=[],hashes_sha256=launch['hashes_sha256'],inputs=d.read(job/'input_manifest.json'),
        inherited_verification=launch['inherited_verification'],verification_log_sha256=d.digest(job/'verification.log'),
        predecessor_gate=False,predecessor_audit=None,gates={},gate_hashes={},attempted_stages=[],stage='preflight')
    d.write_json(folder/'summary.json',summary); print('Run artifacts: '+str(folder),flush=True)
    if not all(d.integrity(folder,summary).values()): raise RuntimeError('P23 archive or source integrity failed')
    history=audit.predecessor_audit(folder); d.write_json(folder/'predecessor_audit.json',history)
    summary.update(predecessor_gate=history['quality_gate'],predecessor_audit=history,
        predecessor_audit_sha256=d.digest(folder/'predecessor_audit.json'))
    d.write_json(folder/'summary.json',summary)
    if not history['quality_gate']: raise RuntimeError('Fresh P22 mathematical audit failed')
    valid=True; env=child_env(job)
    for stage in d.STAGES:
        summary['stage']=stage; summary['attempted_stages'].append(stage); d.write_json(folder/'summary.json',summary)
        if not execute_stage(d.stage_cases(stage),folder,summary,deadline,env):
            valid=False; summary['completion_reason']='execution_failure'; break
        gate=audit.stage_audit(folder,stage); d.write_json(folder/(stage+'_audit.json'),gate)
        summary['gates'][stage]=gate; summary['gate_hashes'][stage]=d.digest(folder/(stage+'_audit.json'))
        d.write_json(folder/'summary.json',summary)
        if not gate['quality_gate']:
            valid=False; summary['completion_reason']='technical_gate_failure'; break
        if stage=='onward': summary['completion_reason']='all_registered_stages_completed'
    summary['integrity']=d.integrity(folder,summary)
    summary.update(stage='finished',elapsed_seconds=time.monotonic()-start,all_execution_valid=bool(valid and
        len(summary['cases'])==48 and all(r['execution_pass'] for r in summary['cases']) and all(summary['integrity'].values())))
    d.write_json(folder/'summary.json',summary); return 0 if summary['all_execution_valid'] else 1

def main():
    p=argparse.ArgumentParser(description=__doc__); g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--worker',type=Path); g.add_argument('--run',type=Path); args=p.parse_args()
    if args.worker: return worker(args.worker.absolute())
    job=args.run.absolute()
    if job!=job.resolve() or job.parent!=d.JOBS: raise ValueError('Wrong P23 job directory')
    return run(job)

if __name__=='__main__': raise SystemExit(main())
