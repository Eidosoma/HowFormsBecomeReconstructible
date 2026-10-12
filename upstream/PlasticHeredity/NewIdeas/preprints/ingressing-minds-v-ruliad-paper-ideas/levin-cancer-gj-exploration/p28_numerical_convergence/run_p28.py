"""P28 fixed archived inputs crossed with a fixed native numerical ladder."""
import argparse,os,subprocess,sys,tempfile,time
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from pathlib import Path
import numpy as np
import p28_design as d
import run_p27 as p27
from run_paper_contact_schedule import CommonGraphExperiment
import paper_bounded_clock as clock

class ResolutionExperiment(CommonGraphExperiment):
    def __init__(self,folder,c):
        self.resolution=c['resolution']
        super().__init__(folder,dict(id=c['id'],fine=c['source_fine']))
        for key,value in d.integrator(c).items(): setattr(self.p,key,value)
    def phase(self,name,horizon,**kwargs):
        if not d.space_available(self.folder): raise RuntimeError('Require five GiB on actual output filesystem')
        original=self.sim.sim; captured={}
        def bounded(actual):
            sample=min(100,actual/20); maximum=min(100,actual/100)/self.resolution
            times,values,trace,meta=clock.integrate(self.sim,actual,sample,maximum)
            captured.update(trace=trace,metadata=meta)
            return times,values
        try:
            self.sim.sim=bounded; result=super().phase(name,horizon,**kwargs)
        finally: self.sim.sim=original
        path=self.folder/(name+'.npz')
        with np.load(path,allow_pickle=False) as old: payload={k:old[k].copy() for k in old.files}
        payload.update(captured['trace']); np.savez_compressed(path,**payload)
        self.records[-1].update(sha256=d.digest(path),clock=captured['metadata'])
        d.write_json(self.folder/'progress.json',self.records)
        return result

def trajectory(exp,c,run): return p27.renewal(exp,c,run)
def result_record(exp,c,out,provenance):
    result=p27.result_record(exp,c,out,provenance)
    result.update(clock_policy='fixed_source_geometric_resolution_v1',
        source_precision='fine' if c['source_fine'] else 'coarse',numerical_resolution=c['resolution'],
        independent_source_and_solver_factors=True,numerical_parameters_refined=True,
        original_P27_gate_changed=False,new_onward_assays=False,
        fixed_onward_schedules=False,historical_numeric_replay=d.replay(c),
        historical_outcome_anchor='p27/'+d.original_case(c)['id'] if c['condition'] in ('baseline','pause_0_25') else None)
    return result

def worker(path):
    if path!=path.resolve(): raise ValueError('Worker cannot write through directory reference')
    run=path.parent.parent; d.check_run_path(run); spec=d.read(path); c=spec['case']; d.validate_config(spec['config'])
    summary=d.read(run/'summary.json')
    if c not in d.fixed_cases() or c['id']!=path.parent.name or spec['inputs']!=str(run/'inputs'): raise ValueError('Unregistered P28 worker')
    if summary['stage']!=c['stage']: raise ValueError('Wrong P28 stage')
    if d.manifest()!=summary['hashes_sha256']: raise RuntimeError('P28 worker source changed')
    if d.read(run/'frozen/p28_numerical_convergence/draws.json')!=d.draw_book(): raise RuntimeError('Draws changed')
    history=summary.get('predecessor_audit',{}); hp=run/'predecessor_audit.json'
    if not (summary.get('predecessor_gate') and history.get('quality_gate') and d.read(hp)==history and d.digest(hp)==summary['predecessor_audit_sha256']):
        raise ValueError('P27 diagnostic archive preflight missing')
    for stage in d.STAGES[:d.STAGES.index(c['stage'])]:
        path_gate=run/(stage+'_audit.json'); gate=d.read(path_gate)
        if not gate['quality_gate'] or summary['gates'].get(stage)!=gate or summary['gate_hashes'][stage]!=d.digest(path_gate): raise ValueError('Invalid prior stage gate')
    # Same fork and stock for all resolution levels of a given source precision.
    for key in (d.prior.source(c)+'/result.json',d.prior.source(c)+'/assembly/checkpoint.npz',
                'p27/'+d.original_case(c)['id']+'/result.json'):
        if d.digest(run/'inputs'/key)!=summary['inputs'][key]['sha256']: raise RuntimeError('Archived source changed')
    if not d.space_available(path.parent): raise RuntimeError('Require five GiB external reserve')
    exp=ResolutionExperiment(path.parent,c)
    with d.recovery.external_phases(): out,provenance=trajectory(exp,c,run)
    d.write_json(path.parent/'result.json',result_record(exp,c,out,provenance))
    return 0

def run_worker(c,run,deadline,env):
    row=dict(id=c['id'],execution_pass=False); left=deadline-time.monotonic()
    if left<=0: return dict(row,status='not_launched_budget')
    if not d.space_available(run): return dict(row,status='not_launched_disk')
    folder=run/c['id']; folder.mkdir(); d.write_json(folder/'spec.json',dict(case=c,config=d.FIXED,inputs=str(run/'inputs')))
    start=time.monotonic(); print('Starting '+c['id'],flush=True)
    with (folder/'stdout.log').open('x') as output:
        try:
            proc=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--worker',str(folder/'spec.json')],
                cwd=d.ROOT,env=env,stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,timeout=min(left,d.FIXED['worker_timeout_seconds']))
            row.update(status='finished',returncode=proc.returncode)
        except subprocess.TimeoutExpired: row.update(status='timeout',returncode=None)
    row['elapsed_seconds']=time.monotonic()-start
    if (folder/'result.json').exists():
        result=d.read(folder/'result.json'); row.update(result=result,result_sha256=d.digest(folder/'result.json'))
        row['execution_pass']=row['returncode']==0 and result['execution_pass']
    print(c['id']+(': VALID' if row['execution_pass'] else ': INVALID'),flush=True)
    return row

def execute_stage(cases,run,summary,deadline,env):
    todo=iter(cases); valid=True
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending={pool.submit(run_worker,c,run,deadline,env) for c in [next(todo),next(todo)]}
        while pending:
            done,pending=wait(pending,return_when=FIRST_COMPLETED)
            for task in done:
                row=task.result(); summary['cases'].append(row); valid &= bool(row['execution_pass']); d.write_json(run/'summary.json',summary)
            if valid:
                for _ in done:
                    c=next(todo,None)
                    if c is not None: pending.add(pool.submit(run_worker,c,run,deadline,env))
    return valid and {r['id'] for r in summary['cases'] if r['id'] in {c['id'] for c in cases}}=={c['id'] for c in cases}

def run(job):
    import analyze_p28 as audit
    from supervise_p28 import child_env,now
    d.verify_launch(job); status=d.read(job/'status.json')
    if not (status.get('verification_exit_code')==0 and status.get('verification_tests')==d.FIXED['software_tests']
            and status.get('verification_log_sha256')==d.digest(job/'verification.log')):
        raise RuntimeError('Complete P28 software verification required')
    if not d.space_available(d.RUNS): raise RuntimeError('Require five GiB external reserve')
    start=time.monotonic(); deadline=start+d.FIXED['total_budget_seconds']
    folder=Path(tempfile.mkdtemp(prefix='p28-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-',dir=d.RUNS))
    d.archive_view(folder); (folder/'frozen').symlink_to(job/'frozen',target_is_directory=True); launch=d.read(job/'launch.json')
    summary=dict(started_utc=now(),job=str(job),revision=d.REVISION,config=d.FIXED,registered_cases=d.fixed_cases(),cases=[],
        hashes_sha256=launch['hashes_sha256'],inputs=d.read(job/'input_manifest.json'),inherited_verification=launch['inherited_verification'],
        verification_log_sha256=d.digest(job/'verification.log'),predecessor_gate=False,predecessor_audit=None,gates={},gate_hashes={},attempted_stages=[],stage='preflight')
    d.write_json(folder/'summary.json',summary); print('Run artifacts: '+str(folder),flush=True)
    history=audit.predecessor_audit(folder); d.write_json(folder/'predecessor_audit.json',history)
    summary.update(predecessor_gate=history['quality_gate'],predecessor_audit=history,predecessor_audit_sha256=d.digest(folder/'predecessor_audit.json'))
    d.write_json(folder/'summary.json',summary)
    if not history['quality_gate']: raise RuntimeError('Stopped P27 archive verification failed')
    valid=True; env=child_env(job)
    for stage in d.STAGES:
        summary['stage']=stage; summary['attempted_stages'].append(stage); d.write_json(folder/'summary.json',summary)
        if not execute_stage(d.stage_cases(stage),folder,summary,deadline,env):
            valid=False; summary['completion_reason']='execution_failure'; break
        gate=audit.stage_audit(folder,stage); d.write_json(folder/(stage+'_audit.json'),gate)
        summary['gates'][stage]=gate; summary['gate_hashes'][stage]=d.digest(folder/(stage+'_audit.json')); d.write_json(folder/'summary.json',summary)
        if not gate['quality_gate']:
            valid=False; summary['completion_reason']='technical_gate_failure'; break
        if stage=='convergence': summary['completion_reason']='all_registered_stages_completed'
    summary['integrity']=d.integrity(folder,summary)
    summary.update(stage='finished',elapsed_seconds=time.monotonic()-start,all_execution_valid=bool(valid and len(summary['cases'])==80 and all(r['execution_pass'] for r in summary['cases']) and all(summary['integrity'].values())))
    d.write_json(folder/'summary.json',summary)
    return 0 if summary['all_execution_valid'] else 1

def main():
    p=argparse.ArgumentParser(description=__doc__); g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--worker',type=Path); g.add_argument('--run',type=Path); args=p.parse_args()
    if args.worker: return worker(args.worker.absolute())
    job=args.run.absolute()
    if job!=job.resolve() or job.parent!=d.JOBS: raise ValueError('Wrong P28 job directory')
    return run(job)
if __name__=='__main__': raise SystemExit(main())
