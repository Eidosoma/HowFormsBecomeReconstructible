"""Execute the fixed P27 pause-window grid without changing native equations."""
import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import numpy as np
import p27_design as d
import run_p26 as p26
import run_p22 as p22
from run_paper_preparation_support import RateExperiment, phase, observe, prior_runner
from analyze_paper_sheet import arrays
import paper_bounded_clock as clock

def stock(run,fine): return p26.stock(run/'inputs/p26',fine)
native_refresh=p22.native_refresh
def first_challenge(folder,c):
    chunks=[arrays(folder,'challenge_%02d'%i) for i in range(1,len(d.BOUNDARIES))]
    for x,left,right in zip(chunks,d.BOUNDARIES,d.BOUNDARIES[1:]):
        if not np.array_equal(x['times'],np.arange(21)*((right-left)/20)):
            raise ValueError('Unexpected P27 sampling grid')
    times=np.concatenate([x['times'][int(i>0):]+d.BOUNDARIES[i] for i,x in enumerate(chunks)])
    values=np.concatenate([x['concentrations'][int(i>0):] for i,x in enumerate(chunks)])
    for left,right in zip(chunks,chunks[1:]):
        if not np.array_equal(left['final'],right['initial']): raise ValueError('Discontinuous challenge boundary')
    selected=np.isin(times,np.arange(0,301,15))
    if not np.array_equal(times[selected],np.arange(0,301,15)): raise ValueError('Missing common challenge sample')
    return dict(times=times[selected],concentrations=values[selected],initial=chunks[0]['initial'],final=chunks[-1]['final'])
first_observation=p22.first_observation
trajectory_diagnostics=p22.trajectory_diagnostics
configure_challenge=p22.configure_challenge

def mix_primary(before,after,c):
    for x in (before,after):
        if x.shape!=(17,3) or not np.isfinite(x).all() or (x<0).any(): raise ValueError('Invalid source state')
        if not np.all(x[4]==72) or np.any(x[16]): raise ValueError('Snail/ST changed')
    pos,rows=d.ROUTES[c['route']]; value=before.copy()
    if pos is not None: value[rows,pos]=after[rows,pos]
    return value

def assemble(exp,run,c):
    src=run/'inputs'/d.source(c); checkpoint=arrays(src/'assembly','checkpoint')
    record=d.read(src/'result.json'); source_meta=d.read(src/'assembly/assembly.json')
    if source_meta['common_logical_start']!=1180300: raise ValueError('Wrong P21 epoch')
    before,after=checkpoint['before'],checkpoint['after']; ids=source_meta['cell_ids'].copy()
    hybrid=mix_primary(before,after,c); value=native_refresh(exp,hybrid,ids)
    folder=exp.folder/'assembly'; folder.mkdir()
    np.savez_compressed(folder/'checkpoint.npz',before=before,after=after,hybrid_before_refresh=hybrid,assembled=value)
    pos,rows=d.ROUTES[c['route']]
    meta=dict(source=d.source(c),source_result_sha256=d.digest(src/'result.json'),
        source_checkpoint_sha256=d.digest(src/'assembly/checkpoint.npz'),source_metadata_sha256=d.digest(src/'assembly/assembly.json'),
        route=c['route'],edited_primary_rows=rows.copy(),edited_column=pos,cell_ids=ids.copy(),
        original_ids=record['outcome']['original_ids'].copy(),common_logical_start=1180300,
        algebraic_refresh=True,refresh_columns=[0,1,2],checkpoint_sha256=d.digest(folder/'checkpoint.npz'))
    d.write_json(folder/'assembly.json',meta)
    return value,ids,record['outcome']['original_ids'].copy(),meta

def renewal(exp,c,run):
    value,ids,originals,meta=assemble(exp,run,c); fork_ids=ids.copy()
    initial_labels=''.join(exp.z.GRN.state_char(x) for x in value.T)
    if initial_labels!='EEE': raise ValueError('Registered assembly not EEE')
    observations={}; replacements=[]; cursor=1180300; _,M=stock(run,c['fine'])
    for at in range(1,c['replacements']+1):
        cycle,pos=divmod(at,3); value=value.copy(); incoming=d.incoming(M,c['draw'],at)
        lab=exp.z.GRN.state_char(incoming[:,0])
        if lab!='M': raise ValueError('Incoming cell not M')
        old=ids[pos]; ids[pos]=d.new_id(c,cycle,pos); value[:,pos:pos+1]=incoming
        replacements.append(dict(event=at+1,cycle=cycle,position=pos,removed=old,inserted=ids[pos],initial_label=lab))
        name='replacement_%02d'%(at+1)
        if at==1:
            for number,(left,right,route) in enumerate(d.challenge_segments(c),1):
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
        execution_pass=True,clock_method=clock.METHOD,clock_policy='phase_scaled_sampling_and_step_cap_v1',
        external_schedule=True,all_cells_evolve=True,counterfactual_reconstruction=True,fixed_onward_schedules=True,
        primary_state_edits_at_assembly=False,algebraic_refresh_at_assembly=not bool(c['readout']),
        segmented_first_challenge=not bool(c['readout']),global_network_timing_intervention=c['condition'] not in ('baseline','reference') and not bool(c['readout']),
        new_incoming_protein_draws=False,repeated_pause=False,
        donors_clamped=False,readout_states_edited=False,autonomous_reproduction=False,cell_division_simulated=False,
        parameter_retuning=False,independent_biological_replicates=False,outcome_dependent_selection=False,
        automatic_follow_on=False,historical_numeric_replay=d.replay(c),historical_outcome_anchor=d.anchor(c),split_unsplit_exact_array_equality_required=False)

def worker(path):
    if path!=path.resolve(): raise ValueError('Worker cannot write through a directory reference')
    run=path.parent.parent; d.check_run_path(run); spec=d.read(path); c=spec['case']
    d.validate_config(spec['config']); summary=d.read(run/'summary.json')
    if c not in d.fixed_cases() or path.parent.name!=c['id'] or spec['inputs']!=str(run/'inputs'): raise ValueError('Unregistered P27 worker')
    if summary['stage']!=c['stage']: raise ValueError('Wrong P27 stage')
    if d.manifest()!=summary['hashes_sha256']: raise RuntimeError('P27 worker source changed')
    if d.read(run/'frozen/p27_pause_boundary/draws.json')!=d.draw_book(): raise ValueError('Incoming draws changed')
    history=summary.get('predecessor_audit',{}); hp=run/'predecessor_audit.json'
    if not (summary.get('predecessor_gate') and history.get('quality_gate') and d.read(hp)==history and d.digest(hp)==summary.get('predecessor_audit_sha256')):
        raise ValueError('P26 evidence preflight has not passed')
    for stage in d.STAGES[:d.STAGES.index(c['stage'])]:
        gp=run/(stage+'_audit.json'); gate=d.read(gp)
        if not gate['quality_gate'] or summary['gates'].get(stage)!=gate or summary['gate_hashes'].get(stage)!=d.digest(gp): raise ValueError('Invalid previous stage audit')
    if c['condition']=='reference':
        key=d.reference_parent(c); record=d.read(run/'inputs'/key/'result.json')
        names=['result.json','assembly/assembly.json','assembly/checkpoint.npz']+[rec['phase']+'.npz' for rec in record['phases']]
    else:
        key=d.source(c); names=['result.json','assembly/assembly.json','assembly/checkpoint.npz']
    for tail in names:
        name=key+'/'+tail
        if name not in summary['inputs'] or d.digest(run/'inputs'/name)!=summary['inputs'][name]['sha256']: raise ValueError('Archived source changed')
    if c['stage']=='onward':
        source=d.parent(c)['id']; rows=[row for row in summary['cases'] if row['id']==source]
        if len(rows)!=1 or not rows[0]['execution_pass']: raise ValueError('Missing actual renewal parent')
        if d.digest(run/source/'result.json')!=rows[0]['result_sha256']: raise ValueError('Parent result changed')
        for rec in rows[0]['result']['phases']:
            if d.digest(run/source/(rec['phase']+'.npz'))!=rec['sha256']: raise ValueError('Parent raw phase changed')
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
    import analyze_p27 as audit
    from supervise_p27 import child_env, now
    d.verify_launch(job); status=d.read(job/'status.json')
    if status.get('verification_exit_code')!=0 or status.get('verification_log_sha256')!=d.digest(job/'verification.log'):
        raise RuntimeError('P27 software verification has not passed')
    if not d.space_available(d.RUNS): raise RuntimeError('Require 5 GiB external reserve')
    start=time.monotonic(); deadline=start+d.FIXED['total_budget_seconds']
    folder=Path(tempfile.mkdtemp(prefix='p27-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-',dir=d.RUNS))
    d.archive_view(folder); (folder/'frozen').symlink_to(job/'frozen',target_is_directory=True)
    launch=d.read(job/'launch.json')
    summary=dict(started_utc=now(),job=str(job),revision=d.REVISION,config=d.FIXED,registered_cases=d.fixed_cases(),
        cases=[],hashes_sha256=launch['hashes_sha256'],inputs=d.read(job/'input_manifest.json'),
        inherited_verification=launch['inherited_verification'],verification_log_sha256=d.digest(job/'verification.log'),
        predecessor_gate=False,predecessor_audit=None,gates={},gate_hashes={},attempted_stages=[],stage='preflight')
    d.write_json(folder/'summary.json',summary); print('Run artifacts: '+str(folder),flush=True)
    if not all(d.integrity(folder,summary).values()): raise RuntimeError('P27 archive or source integrity failed')
    history=audit.predecessor_audit(folder); d.write_json(folder/'predecessor_audit.json',history)
    summary.update(predecessor_gate=history['quality_gate'],predecessor_audit=history,
        predecessor_audit_sha256=d.digest(folder/'predecessor_audit.json'))
    d.write_json(folder/'summary.json',summary)
    if not history['quality_gate']: raise RuntimeError('P26 completed-evidence verification failed')
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
        len(summary['cases'])==428 and all(r['execution_pass'] for r in summary['cases']) and all(summary['integrity'].values())))
    d.write_json(folder/'summary.json',summary); return 0 if summary['all_execution_valid'] else 1

def main():
    p=argparse.ArgumentParser(description=__doc__); g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--worker',type=Path); g.add_argument('--run',type=Path); args=p.parse_args()
    if args.worker: return worker(args.worker.absolute())
    job=args.run.absolute()
    if job!=job.resolve() or job.parent!=d.JOBS: raise ValueError('Wrong P27 job directory')
    return run(job)

if __name__=='__main__': raise SystemExit(main())
