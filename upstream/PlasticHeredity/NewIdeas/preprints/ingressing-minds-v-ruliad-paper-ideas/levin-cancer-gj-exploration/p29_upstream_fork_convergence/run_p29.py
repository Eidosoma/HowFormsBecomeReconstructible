"""P29 upstream prefix regeneration and independent downstream refinement."""
import argparse,os,subprocess,sys,tempfile,time
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from pathlib import Path
import numpy as np
import p29_design as d
import run_p27 as p27
import run_paper_renewal_maturation as r17
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

def stock(run,fine):
    data=arrays(run/'inputs/p11'/('stock'+('__fine' if fine else '')),'preparation')['final']
    return data[:,168:169],data[:,1:2]

arrays=p27.arrays
phase,observe,prior_runner=p27.phase,p27.observe,p27.prior_runner
configure_challenge,first_observation,first_challenge=p27.configure_challenge,p27.first_observation,p27.first_challenge
trajectory_diagnostics=p27.trajectory_diagnostics

def prefix_trajectory(exp,c,run):
    mapped=d.p17.case(founder=c['founder'],fine=c['fine'])
    out=r17.prefix(exp,mapped,run/'inputs/p17')
    provenance=dict(founder_source=d.founder_source(c),stock_source=d.stock_source(c),
        founder_result_sha256=d.digest(run/'inputs'/d.founder_source(c)/'result.json'),
        founder_phase_sha256=d.digest(run/'inputs'/d.founder_source(c)/'isolated_2.npz'),
        stock_result_sha256=d.digest(run/'inputs'/d.stock_source(c)/'result.json'),
        stock_phase_sha256=d.digest(run/'inputs'/d.stock_source(c)/'preparation.npz'))
    return out,provenance

def assemble(exp,run,c):
    key=d.prefix_source(c); src=run/key; record=d.read(src/'result.json'); rec=record['phases'][0]
    if record['case']!=d.prefix(c['founder'],c['source_fine'],c['prefix_resolution']) or not record['execution_pass']:
        raise ValueError('Wrong regenerated prefix')
    if rec['phase']!='replacement_01' or rec['logical_interval']!=[1180000,1180100]: raise ValueError('Wrong prefix epoch')
    before=arrays(src,'replacement_01')['final']; ids=rec['setup']['cell_ids'].copy()
    value=p27.native_refresh(exp,before.copy(),ids); folder=exp.folder/'assembly'; folder.mkdir()
    np.savez_compressed(folder/'checkpoint.npz',before=before,hybrid_before_refresh=before,assembled=value)
    meta=dict(source=key,source_result_sha256=d.digest(src/'result.json'),source_phase_sha256=d.digest(src/'replacement_01.npz'),
        source_epoch=1180100,common_logical_start=1180300,reanchor_without_integration=200,
        route='none',edited_primary_rows=[],edited_column=None,cell_ids=ids.copy(),
        original_ids=record['outcome']['original_ids'].copy(),algebraic_refresh=True,refresh_columns=[0,1,2],
        checkpoint_sha256=d.digest(folder/'checkpoint.npz'))
    d.write_json(folder/'assembly.json',meta)
    return value,ids,record['outcome']['original_ids'].copy(),meta

def renewal(exp,c,run):
    value,ids,originals,meta=assemble(exp,run,c); fork_ids=ids.copy()
    initial_labels=''.join(exp.z.GRN.state_char(x) for x in value.T)
    if initial_labels!='EEE': raise ValueError('Registered assembly not EEE')
    observations={}; replacements=[]; cursor=1180300; _,M=stock(run,c['fine'])
    for at in range(1,c['replacements']+1):
        cycle,pos=divmod(at,3); value=value.copy(); incoming=d.prior.prior.incoming(M,c['draw'],at)
        lab=exp.z.GRN.state_char(incoming[:,0])
        if lab!='M': raise ValueError('Incoming cell not M')
        old=ids[pos]; ids[pos]=d.prior.prior.new_id(c,cycle,pos); value[:,pos:pos+1]=incoming
        replacements.append(dict(event=at+1,cycle=cycle,position=pos,removed=old,inserted=ids[pos],initial_label=lab))
        name='replacement_%02d'%(at+1)
        if at==1:
            for number,(left,right,route) in enumerate(d.prior.prior.challenge_segments(c),1):
                horizon=right-left
                configure_challenge(exp,ids,value,route); value=phase(exp,'challenge_%02d'%number,horizon,cursor); cursor+=horizon
            observations[name]=first_observation(exp,first_challenge(exp.folder,c))
        else:
            configure_challenge(exp,ids,value,'open'); value=phase(exp,name,300,cursor); cursor+=300
            observations[name]=observe(exp,name,range(3),False)
        d.write_json(exp.folder/'turnover_progress.json',dict(replacements=replacements))
    cursor=prior_runner.holds(exp,ids,value,cursor,observations)
    diagnostic=trajectory_diagnostics(first_challenge(exp.folder,c))
    out=dict(available=True,fork_ids=fork_ids,original_ids=originals,assembly_labels=initial_labels,
        observations=observations,replacements=replacements,retained_E=all(prior_runner.retained(observations)),
        first_cell_label_after_second=observations['replacement_02']['patch_labels'][0],
        first_cell_stable_E_after_second=observations['replacement_02']['stable_E'][0],
        later_windows_E=all(all(v['stable_E']) for k,v in observations.items() if k.startswith('replacement')),
        complete_carrier_replacement=not bool(set(ids)&set(fork_ids+originals)),logical_end=cursor,
        first_cell_sampled_behavior=diagnostic['sampled_behavior'],first_cell_M_observed=diagnostic['M_observed'])
    return out,dict(assembly=meta,assembly_metadata_sha256=d.digest(exp.folder/'assembly/assembly.json'),trajectory_diagnostics=diagnostic)


def trajectory(exp,c,run): return (prefix_trajectory if c['kind']=='prefix' else renewal)(exp,c,run)

def result_record(exp,c,out,provenance):
    return dict(case=c,ion_indices=exp.indices,phases=exp.records,outcome=out,provenance=provenance,
        execution_pass=True,clock_method=clock.METHOD,clock_policy='independent_prefix_and_downstream_refinement_v1',
        source_precision='fine' if c['source_fine'] else 'coarse',numerical_resolution=c['resolution'],
        prefix_resolution=c.get('prefix_resolution',c['resolution']),external_schedule=True,all_cells_evolve=True,
        independent_numerical_factors=True,numerical_parameters_refined=True,counterfactual_reconstruction=True,
        historical_numeric_replay=d.replay(c),historical_outcome_anchor=d.anchor(c),
        algebraic_refresh_at_assembly=c['kind']=='renewal',segmented_first_challenge=c['kind']=='renewal',
        global_network_timing_intervention=c['kind']=='renewal' and c['condition']!='baseline',
        primary_state_edits_at_assembly=False,new_incoming_protein_draws=False,repeated_pause=False,
        donors_clamped=False,readout_states_edited=False,autonomous_reproduction=False,cell_division_simulated=False,
        parameter_retuning=False,independent_biological_replicates=False,outcome_dependent_selection=False,
        automatic_follow_on=False,original_P27_gate_changed=False,new_onward_assays=False,full_historical_lineage_refined=False)

def worker(path):
    if path!=path.resolve(): raise ValueError('Worker cannot write through directory reference')
    run=path.parent.parent; d.check_run_path(run); spec=d.read(path); c=spec['case']; d.validate_config(spec['config'])
    summary=d.read(run/'summary.json')
    if c not in d.fixed_cases() or c['id']!=path.parent.name or spec['inputs']!=str(run/'inputs'): raise ValueError('Unregistered P29 worker')
    if summary['stage']!=c['stage']: raise ValueError('Wrong P29 stage')
    if d.manifest()!=summary['hashes_sha256']: raise RuntimeError('P29 worker source changed')
    if d.read(run/'frozen/p29_upstream_fork_convergence/draws.json')!=d.draw_book(): raise RuntimeError('P29 draws changed')
    history=summary.get('predecessor_audit',{}); hp=run/'predecessor_audit.json'
    if not (summary.get('predecessor_gate') and history.get('quality_gate') and d.read(hp)==history and d.digest(hp)==summary['predecessor_audit_sha256']):
        raise ValueError('P28 diagnostic archive preflight missing')
    for stage in d.STAGES[:d.STAGES.index(c['stage'])]:
        path_gate=run/(stage+'_audit.json'); gate=d.read(path_gate)
        if not gate['quality_gate'] or summary['gates'].get(stage)!=gate or summary['gate_hashes'].get(stage)!=d.digest(path_gate):
            raise ValueError('Invalid prior stage gate')
    keys=[d.founder_source(c)+'/result.json',d.founder_source(c)+'/isolated_2.npz',
        d.stock_source(c)+'/result.json',d.stock_source(c)+'/preparation.npz']
    if d.replay(c):
        record=d.read(run/'inputs'/d.replay(c)/'result.json')
        keys+=[d.replay(c)+'/result.json']+[d.replay(c)+'/'+p['phase']+'.npz' for p in record['phases']]
    for key in keys:
        if d.digest(run/'inputs'/key)!=summary['inputs'][key]['sha256']: raise RuntimeError('Archived source changed')
    if c['kind']=='renewal':
        key=d.prefix_source(c); rows=[x for x in summary['cases'] if x['id']==key]
        if len(rows)!=1 or not rows[0]['execution_pass']: raise ValueError('Missing regenerated prefix')
        if d.digest(run/key/'result.json')!=rows[0]['result_sha256']: raise ValueError('Regenerated prefix changed')
        for p in rows[0]['result']['phases']:
            if d.digest(run/key/(p['phase']+'.npz'))!=p['sha256']: raise ValueError('Regenerated prefix phase changed')
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
    import analyze_p29 as audit
    from supervise_p29 import child_env,now
    d.verify_launch(job); status=d.read(job/'status.json')
    if not (status.get('verification_exit_code')==0 and status.get('verification_tests')==d.FIXED['software_tests']
            and status.get('verification_log_sha256')==d.digest(job/'verification.log')):
        raise RuntimeError('Complete P29 software verification required')
    if not d.space_available(d.RUNS): raise RuntimeError('Require five GiB external reserve')
    start=time.monotonic(); deadline=start+d.FIXED['total_budget_seconds']
    folder=Path(tempfile.mkdtemp(prefix='p29-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-',dir=d.RUNS))
    d.archive_view(folder); (folder/'frozen').symlink_to(job/'frozen',target_is_directory=True); launch=d.read(job/'launch.json')
    summary=dict(started_utc=now(),job=str(job),revision=d.REVISION,config=d.FIXED,registered_cases=d.fixed_cases(),cases=[],
        hashes_sha256=launch['hashes_sha256'],inputs=d.read(job/'input_manifest.json'),inherited_verification=launch['inherited_verification'],
        verification_log_sha256=d.digest(job/'verification.log'),predecessor_gate=False,predecessor_audit=None,gates={},gate_hashes={},attempted_stages=[],stage='preflight')
    d.write_json(folder/'summary.json',summary); print('Run artifacts: '+str(folder),flush=True)
    history=audit.predecessor_audit(folder); d.write_json(folder/'predecessor_audit.json',history)
    summary.update(predecessor_gate=history['quality_gate'],predecessor_audit=history,predecessor_audit_sha256=d.digest(folder/'predecessor_audit.json'))
    d.write_json(folder/'summary.json',summary)
    if not history['quality_gate']: raise RuntimeError('P28 diagnostic archive verification failed')
    valid=True; env=child_env(job)
    for stage in d.STAGES:
        summary['stage']=stage; summary['attempted_stages'].append(stage); d.write_json(folder/'summary.json',summary)
        if not execute_stage(d.stage_cases(stage),folder,summary,deadline,env):
            valid=False; summary['completion_reason']='execution_failure'; break
        gate=audit.stage_audit(folder,stage); d.write_json(folder/(stage+'_audit.json'),gate)
        summary['gates'][stage]=gate; summary['gate_hashes'][stage]=d.digest(folder/(stage+'_audit.json')); d.write_json(folder/'summary.json',summary)
        if not gate['quality_gate']:
            valid=False; summary['completion_reason']='technical_gate_failure'; break
        if stage=='refinement': summary['completion_reason']='all_registered_stages_completed'
    summary['integrity']=d.integrity(folder,summary)
    summary.update(stage='finished',elapsed_seconds=time.monotonic()-start,all_execution_valid=bool(valid and len(summary['cases'])==116 and all(r['execution_pass'] for r in summary['cases']) and all(summary['integrity'].values())))
    d.write_json(folder/'summary.json',summary)
    return 0 if summary['all_execution_valid'] else 1

def main():
    p=argparse.ArgumentParser(description=__doc__); g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--worker',type=Path); g.add_argument('--run',type=Path); args=p.parse_args()
    if args.worker: return worker(args.worker.absolute())
    job=args.run.absolute()
    if job!=job.resolve() or job.parent!=d.JOBS: raise ValueError('Wrong P29 job directory')
    return run(job)
if __name__=='__main__': raise SystemExit(main())
