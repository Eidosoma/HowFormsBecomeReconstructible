"""Execute the registered P30 refined boundary and actual-parent transmission panel."""
import argparse,os,subprocess,sys,tempfile,time
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from pathlib import Path
import numpy as np
import p30_design as d
import run_p29 as p29
import run_p27 as p27
import paper_bounded_clock as clock
ResolutionExperiment=p29.ResolutionExperiment
stock,arrays,phase,observe,prior_runner=p29.stock,p29.arrays,p29.phase,p29.observe,p29.prior_runner
configure_challenge,first_observation,first_challenge=p29.configure_challenge,p29.first_observation,p29.first_challenge
trajectory_diagnostics=p29.trajectory_diagnostics

def assemble(exp,run,c):
    key=d.prefix_source(c); src=run/'inputs'/key; record=d.read(src/'result.json'); rec=record['phases'][0]
    if record['case']!=d.prior.prefix(c['founder'],c['source_fine'],c['prefix_resolution']) or not record['execution_pass']:
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
        cycle,pos=divmod(at,3); value=value.copy(); incoming=d.grid.incoming(M,c['draw'],at)
        lab=exp.z.GRN.state_char(incoming[:,0])
        if lab!='M': raise ValueError('Incoming cell not M')
        old=ids[pos]; ids[pos]=d.grid.new_id(c,cycle,pos); value[:,pos:pos+1]=incoming
        replacements.append(dict(event=at+1,cycle=cycle,position=pos,removed=old,inserted=ids[pos],initial_label=lab))
        name='replacement_%02d'%(at+1)
        if at==1:
            for number,(left,right,route) in enumerate(d.grid.challenge_segments(c),1):
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

def readout(exp,c,run):
    source=d.reference_parent(c) if c['condition']=='reference' else d.parent(c)['id']
    path=(run/'inputs'/source) if c['condition']=='reference' else run/source
    record=d.read(path/'result.json'); donors=arrays(path,'isolated_2')['final']
    ids=record['phases'][-1]['setup']['cell_ids'].copy(); base=record['outcome']['logical_end']
    if base!=1200300+300*c['replacements'] or donors.shape!=(17,3): raise ValueError('Wrong onward parent')
    _,M=stock(run,c['fine']); fresh=d.pupils(c); recipients=np.repeat(M,3,axis=1)
    if set(fresh)&set(ids+record['outcome']['fork_ids']+record['outcome']['original_ids']): raise ValueError('Recipient identity reused')
    donor_initial=''.join(exp.z.GRN.state_char(x) for x in donors.T)
    recipient_initial=''.join(exp.z.GRN.state_char(x) for x in recipients.T)
    if recipient_initial!='MMM': raise ValueError('Readout recipients not M')
    exp.configure([2,3],ids+fresh,np.concatenate((donors,recipients),axis=1),'depol',60,
        0 if c['readout']=='rna' else 1.25e-14,patch=[0,1,2],cut=c['readout']=='cut')
    value=phase(exp,'contact',20000,base); observations={'contact':observe(exp,'contact',range(3,6),False)}
    donor_end=''.join(exp.z.GRN.state_char(x) for x in value[:,:3].T)
    cursor=prior_runner.holds(exp,fresh,value[:,3:],base+20000,observations)
    out=dict(available=True,parent_retained_E=record['outcome']['retained_E'],donor_initial_labels=donor_initial,
        recipient_initial_labels=recipient_initial,donor_end_labels=donor_end,observations=observations,
        contact_stable_E=all(observations['contact']['stable_E']),transmitted_E=all(prior_runner.retained(observations)),logical_end=cursor)
    return out,dict(actual_parent=source,parent_result_sha256=d.digest(path/'result.json'),parent_phase_sha256=d.digest(path/'isolated_2.npz'))

def trajectory(exp,c,run): return (readout if c['readout'] else renewal)(exp,c,run)

def result_record(exp,c,out,provenance):
    return dict(case=c,ion_indices=exp.indices,phases=exp.records,outcome=out,provenance=provenance,
        execution_pass=True,clock_method=clock.METHOD,clock_policy='joint_preparation_downstream_refinement_v1',
        source_precision='fine' if c['source_fine'] else 'coarse',numerical_resolution=c['resolution'],
        prefix_resolution=c['prefix_resolution'],external_schedule=True,all_cells_evolve=True,
        independent_source_and_solver_factors=True,numerical_parameters_refined=True,counterfactual_reconstruction=True,
        fixed_onward_schedules=True,full_grid_contraction_claimed=False,
        historical_numeric_replay=d.replay(c),historical_outcome_anchor=d.anchor(c),
        algebraic_refresh_at_assembly=not bool(c['readout']),segmented_first_challenge=not bool(c['readout']),
        global_network_timing_intervention=not bool(c['readout']) and c['condition']!='baseline',
        primary_state_edits_at_assembly=False,new_incoming_protein_draws=False,repeated_pause=False,
        donors_clamped=False,readout_states_edited=False,autonomous_reproduction=False,cell_division_simulated=False,
        parameter_retuning=False,independent_biological_replicates=False,outcome_dependent_selection=False,
        automatic_follow_on=False,original_P27_gate_changed=False,new_onward_assays=c['stage']=='onward',full_historical_lineage_refined=False)

def worker(path):
    if path!=path.resolve(): raise ValueError('Worker cannot write through a directory reference')
    run=path.parent.parent; d.check_run_path(run); spec=d.read(path); c=spec['case']
    d.validate_config(spec['config']); summary=d.read(run/'summary.json')
    if c not in d.fixed_cases() or path.parent.name!=c['id'] or spec['inputs']!=str(run/'inputs'): raise ValueError('Unregistered P30 worker')
    if summary['stage']!=c['stage']: raise ValueError('Wrong P30 stage')
    if d.manifest()!=summary['hashes_sha256']: raise RuntimeError('P30 worker source changed')
    if d.read(run/'frozen/p30_refined_pause_boundary/draws.json')!=d.draw_book(): raise ValueError('Incoming draws changed')
    history=summary.get('predecessor_audit',{}); hp=run/'predecessor_audit.json'
    if not (summary.get('predecessor_gate') and history.get('quality_gate') and d.read(hp)==history and d.digest(hp)==summary.get('predecessor_audit_sha256')):
        raise ValueError('Qualified P29 evidence preflight has not passed')
    for stage in d.STAGES[:d.STAGES.index(c['stage'])]:
        gp=run/(stage+'_audit.json'); gate=d.read(gp)
        if not gate['quality_gate'] or summary['gates'].get(stage)!=gate or summary['gate_hashes'].get(stage)!=d.digest(gp): raise ValueError('Invalid previous stage audit')
    sources=[d.reference_parent(c) if c['condition']=='reference' else d.prefix_source(c)]
    if d.replay(c): sources.append(d.replay(c))
    keys=[d.prior.stock_source(c)+'/'+n for n in ('result.json','preparation.npz')]
    for key in sources:
        old=d.read(run/'inputs'/key/'result.json')
        keys+=[key+'/result.json']+[key+'/'+p['phase']+'.npz' for p in old['phases']]
    for key in keys:
        if key not in summary['inputs'] or d.digest(run/'inputs'/key)!=summary['inputs'][key]['sha256']: raise ValueError('Archived source changed')
    if c['stage']=='onward':
        source=d.parent(c)['id']; rows=[row for row in summary['cases'] if row['id']==source]
        if len(rows)!=1 or not rows[0]['execution_pass']: raise ValueError('Missing actual renewal parent')
        if d.digest(run/source/'result.json')!=rows[0]['result_sha256']: raise ValueError('Parent result changed')
        for rec in rows[0]['result']['phases']:
            if d.digest(run/source/(rec['phase']+'.npz'))!=rec['sha256']: raise ValueError('Parent raw phase changed')
    if not d.space_available(path.parent): raise RuntimeError('Require five GiB external reserve')
    exp=ResolutionExperiment(path.parent,c)
    with d.recovery.external_phases(): out,provenance=trajectory(exp,c,run)
    d.write_json(path.parent/'result.json',result_record(exp,c,out,provenance)); return 0

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
    import analyze_p30 as audit
    from supervise_p30 import child_env,now
    d.verify_launch(job); status=d.read(job/'status.json')
    if not (status.get('verification_exit_code')==0 and status.get('verification_tests')==d.FIXED['software_tests']
            and status.get('verification_log_sha256')==d.digest(job/'verification.log')):
        raise RuntimeError('Complete P30 software verification required')
    if not d.space_available(d.RUNS): raise RuntimeError('Require five GiB external reserve')
    start=time.monotonic(); deadline=start+d.FIXED['total_budget_seconds']
    folder=Path(tempfile.mkdtemp(prefix='p30-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-',dir=d.RUNS))
    d.archive_view(folder); (folder/'frozen').symlink_to(job/'frozen',target_is_directory=True); launch=d.read(job/'launch.json')
    summary=dict(started_utc=now(),job=str(job),revision=d.REVISION,config=d.FIXED,registered_cases=d.fixed_cases(),cases=[],
        hashes_sha256=launch['hashes_sha256'],inputs=d.read(job/'input_manifest.json'),inherited_verification=launch['inherited_verification'],
        verification_log_sha256=d.digest(job/'verification.log'),predecessor_gate=False,predecessor_audit=None,gates={},gate_hashes={},attempted_stages=[],stage='preflight')
    d.write_json(folder/'summary.json',summary); print('Run artifacts: '+str(folder),flush=True)
    history=audit.predecessor_audit(folder); d.write_json(folder/'predecessor_audit.json',history)
    summary.update(predecessor_gate=history['quality_gate'],predecessor_audit=history,predecessor_audit_sha256=d.digest(folder/'predecessor_audit.json'))
    d.write_json(folder/'summary.json',summary)
    if not history['quality_gate']: raise RuntimeError('Qualified P29 evidence verification failed')
    valid=True; env=child_env(job)
    for stage in d.STAGES:
        summary['stage']=stage; summary['attempted_stages'].append(stage); d.write_json(folder/'summary.json',summary)
        if not execute_stage(d.stage_cases(stage),folder,summary,deadline,env):
            valid=False; summary['completion_reason']='execution_failure'; break
        gate=audit.stage_audit(folder,stage); d.write_json(folder/(stage+'_audit.json'),gate)
        summary['gates'][stage]=gate; summary['gate_hashes'][stage]=d.digest(folder/(stage+'_audit.json')); d.write_json(folder/'summary.json',summary)
        if not gate['quality_gate']:
            valid=False; summary['completion_reason']='technical_gate_failure'; break
        if stage=='onward': summary['completion_reason']='all_registered_stages_completed'
    summary['integrity']=d.integrity(folder,summary)
    summary.update(stage='finished',elapsed_seconds=time.monotonic()-start,all_execution_valid=bool(valid and len(summary['cases'])==856 and all(r['execution_pass'] for r in summary['cases']) and all(summary['integrity'].values())))
    d.write_json(folder/'summary.json',summary)
    return 0 if summary['all_execution_valid'] else 1

def main():
    p=argparse.ArgumentParser(description=__doc__); g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--worker',type=Path); g.add_argument('--run',type=Path); args=p.parse_args()
    if args.worker: return worker(args.worker.absolute())
    job=args.run.absolute()
    if job!=job.resolve() or job.parent!=d.JOBS: raise ValueError('Wrong P30 job directory')
    return run(job)

if __name__=='__main__': raise SystemExit(main())
