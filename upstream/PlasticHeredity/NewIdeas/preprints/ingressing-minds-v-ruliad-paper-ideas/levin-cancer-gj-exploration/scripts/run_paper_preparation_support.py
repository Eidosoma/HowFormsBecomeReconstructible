"""P19 equal-time preparation interventions with actual-cell renewal/readouts."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import numpy as np
import paper_preparation_support_design as d
from run_paper_turnover_limit import RateExperiment
from run_paper_staged_relay import phase
from run_paper_sheet import load_array
from run_paper_tissue_persistence import observe
import paper_bounded_clock as clock
import run_paper_preparation_turnover as prior_runner

def stock(run,fine): return prior_runner.stock(run/'inputs/p18',fine)
def prefix_checkpoint(run,c):
    mapped=d.prior.case('renewal',c['founder'],100,300,'open',fine=c['fine'])
    return prior_runner.prefix_checkpoint(run/'inputs/p18',mapped)

def space_available():
    return all(shutil.disk_usage(p).free>=5*1024**3 for p in (d.ROOT,d.STORE))

def replace(exp,c,M,value,ids,cycle,positions,event):
    value=value.copy(); inserted=[]
    for pos in positions:
        state=d.incoming(M,cycle,pos); lab=exp.z.GRN.state_char(state[:,0])
        if lab!='M': raise ValueError('Replacement not initially M')
        old=ids[pos]; ids[pos]=d.new_id(c,cycle,pos); value[:,pos:pos+1]=state
        inserted.append(dict(event=event,cycle=cycle,position=pos,removed=old,inserted=ids[pos],initial_label=lab))
    return value,inserted

def extra_preparation(exp,c,ids,value,cursor,observations):
    if c['mode']=='isolated': exp.configure([1,3],ids,value,isolated=True)
    else: exp.configure([1,3],ids,value,'depol',60,0 if c['mode']=='rna' else 1.25e-14)
    value=phase(exp,'preparation_extra',c['extra'],cursor)
    observations['preparation_extra']=observe(exp,'preparation_extra',range(3),False)
    return value,cursor+c['extra']

def baseline(exp,c,run):
    replay=d.replay_case(c)
    if replay is not None: return prior_runner.trajectory(exp,replay,run/'inputs/p18')
    E,M=stock(run,c['fine']); value=np.repeat(E,3,axis=1); ids=d.stock_ids(c); original=ids.copy()
    observations={}; replacements=[]; cursor=0
    value,new=replace(exp,c,M,value,ids,0,range(3),1); replacements.extend(new)
    exp.configure([1,3],ids,value,'depol',60,1.25e-14)
    value=phase(exp,'wipe_initial',100,cursor); cursor+=100
    observations['wipe_initial']=observe(exp,'wipe_initial',range(3),False)
    value,cursor=extra_preparation(exp,c,ids,value,cursor,observations)
    exp.configure([1,3],ids,value,'depol',60,1.25e-14)
    value=phase(exp,'wipe_first_remainder',600,cursor); cursor+=600
    observations['wipe_first_remainder']=observe(exp,'wipe_first_remainder',range(3),False)
    value,new=replace(exp,c,M,value,ids,1,range(3),2); replacements.extend(new)
    exp.configure([1,3],ids,value,'depol',60,1.25e-14)
    value=phase(exp,'wipe_second_cycle',900,cursor); cursor+=900
    observations['wipe_second_cycle']=observe(exp,'wipe_second_cycle',range(3),False)
    d.write_json(exp.folder/'turnover_progress.json',dict(replacements=replacements))
    cursor=prior_runner.holds(exp,ids,value,cursor,observations)
    return dict(available=True,original_ids=original,observations=observations,replacements=replacements,
        retained_E=all(prior_runner.retained(observations)),logical_end=cursor)

def renewal(exp,c,run):
    value,ids,cursor,record=prefix_checkpoint(run,c)
    initial_ids=ids.copy(); fork_labels=''.join(exp.z.GRN.state_char(x) for x in value.T)
    observations={}; replacements=[]; _,M=stock(run,c['fine'])
    value,cursor=extra_preparation(exp,c,ids,value,cursor,observations)
    preparation_labels=''.join(exp.z.GRN.state_char(x) for x in value.T)
    for at in range(1,6):
        cycle,pos=divmod(at,3); value,new=replace(exp,c,M,value,ids,cycle,[pos],at+1); replacements.extend(new)
        exp.configure([1,3],ids,value,'depol',60,1.25e-14)
        name='replacement_%02d'%(at+1); value=phase(exp,name,300,cursor); cursor+=300
        observations[name]=observe(exp,name,range(3),False)
        d.write_json(exp.folder/'turnover_progress.json',dict(replacements=replacements))
    cursor=prior_runner.holds(exp,ids,value,cursor,observations)
    later_good=all(all(v['stable_E']) for k,v in observations.items() if k.startswith('replacement'))
    return dict(available=True,fork_ids=initial_ids,fork_labels=fork_labels,
        preparation_end_labels=preparation_labels,preparation_window_E=all(observations['preparation_extra']['stable_E']),
        first_cell_stable_E_after_preparation=observations['preparation_extra']['stable_E'][0],
        observations=observations,retained_E=all(prior_runner.retained(observations)),logical_end=cursor,
        original_ids=record['outcome']['original_ids'],replacements=replacements,
        first_cell_label_after_second=observations['replacement_02']['patch_labels'][0],
        first_cell_stable_E_after_second=observations['replacement_02']['stable_E'][0],
        later_windows_E=later_good,complete_carrier_replacement=True)

def readout(exp,c,run):
    _,M=stock(run,c['fine']); parent=d.parent(c); donors=load_array(run,parent['id'],'isolated_2')
    record=json.loads((run/parent['id']/'result.json').read_text())
    ids=record['phases'][-1]['setup']['cell_ids'].copy(); base=record['outcome']['logical_end']
    fresh=d.pupils(c); pupils=np.repeat(M,3,axis=1)
    initial_donors=''.join(exp.z.GRN.state_char(x) for x in donors.T)
    initial_recipients=''.join(exp.z.GRN.state_char(x) for x in pupils.T)
    if initial_recipients!='MMM': raise ValueError('Readout recipients not M')
    exp.configure([2,3],ids+fresh,np.concatenate((donors,pupils),axis=1),'depol',60,
                  0 if c['readout']=='rna' else 1.25e-14,patch=[0,1,2],cut=c['readout']=='cut')
    value=phase(exp,'contact',20000,base)
    observations={'contact':observe(exp,'contact',range(3,6),False)}
    donor_end=''.join(exp.z.GRN.state_char(x) for x in value[:,:3].T)
    exp.configure([1,3],fresh,value[:,3:],isolated=True)
    for i in (1,2):
        name='isolated_'+str(i); phase(exp,name,10000,base+20000+(i-1)*10000)
        observations[name]=observe(exp,name,range(3),False)
    return dict(available=True,donor_initial_labels=initial_donors,recipient_initial_labels=initial_recipients,
        donor_end_labels=donor_end,observations=observations,
        transmitted_E=all(prior_runner.retained(observations)),logical_end=base+40000)

def trajectory(exp,c,run):
    return {'baseline':baseline,'renewal':renewal,'onward':readout}[c['stage']](exp,c,run)

def result_record(exp,c,outcome):
    return dict(case=c,ion_indices=exp.indices,phases=exp.records,outcome=outcome,execution_pass=True,
        clock_method=clock.METHOD,clock_policy='phase_scaled_sampling_and_step_cap_v1',
        external_schedule=True,all_cells_evolve=True,full_source_transfer=True,only_registered_columns_replaced=True,
        exact_archived_prefix_fork=c['stage']=='renewal',benchmark_prior_age_matched=False,
        archived_prefix_source=d.prefix_source(c) if c['stage']=='renewal' else None,
        autonomous_reproduction=False,parameter_retuning=False,outcome_dependent_cell_selection=False,
        fixed_onward_schedules=True,cross_branch_pooling=False,cell_division_simulated=False,
        independent_biological_replicates=False,automatic_follow_on=False,exact_P18_replay=d.replay_source(c) is not None,
        preparation_only_coupling_intervention=c['stage']=='renewal' or c['arm']=='wipe',
        later_coupling_restored=True,split_unsplit_exact_array_equality_required=False)

def worker(path):
    spec=json.loads(path.read_text()); d.validate_config(spec['config']); c=spec['case']; run=path.parent.parent
    summary=json.loads((run/'summary.json').read_text())
    if c not in d.fixed_cases() or Path(spec['inputs'])!=run/'inputs': raise ValueError('Unregistered P19 worker')
    if summary['stage']!=c['stage']: raise ValueError('Wrong P19 stage')
    history=summary.get('predecessor_audit',{}); hp=run/'predecessor_audit.json'
    if (not summary.get('predecessor_gate') or not history.get('quality_gate') or
        json.loads(hp.read_text())!=history or d.digest(hp)!=summary.get('predecessor_audit_sha256')):
        raise ValueError('P18 preflight not passed')
    for stage in d.STAGES[:d.STAGES.index(c['stage'])]:
        gp=run/(stage+'_audit.json'); gate=json.loads(gp.read_text())
        if (not gate['quality_gate'] or summary['gates'].get(stage)!=gate or
            summary['gate_hashes'].get(stage)!=d.digest(gp)): raise ValueError('Invalid prior-stage audit')
    if json.loads((run/'frozen/paper_preparation_support_draws_v1.json').read_text())!=d.draw_book():
        raise ValueError('Incoming draws changed')
    if c['stage']=='renewal':
        for tail in ('result.json','replacement_01.npz'):
            key='p18/inputs/p17/'+d.prefix_source(c)+'/'+tail
            if key not in summary['inputs'] or d.digest(run/'inputs'/key)!=summary['inputs'][key]['sha256']:
                raise ValueError('Changed or missing archived prefix')
    if c['stage']=='onward':
        source=d.parent(c)['id']; rows=[row for row in summary['cases'] if row['id']==source]
        if len(rows)!=1 or not rows[0]['execution_pass']: raise ValueError('Missing actual renewal parent')
        if d.digest(run/source/'result.json')!=rows[0]['result_sha256']: raise ValueError('Changed renewal parent')
        for rec in rows[0]['result']['phases']:
            if d.digest(run/source/(rec['phase']+'.npz'))!=rec['sha256']: raise ValueError('Changed parent raw phase')
    exp=RateExperiment(path.parent,dict(id=c['id'],fine=c['fine']))
    out=trajectory(exp,c,run); d.write_json(path.parent/'result.json',result_record(exp,c,out)); return 0

def run_worker(case,config,run,deadline,env):
    remaining=deadline-time.monotonic(); record=dict(id=case['id'],execution_pass=False)
    if remaining<=0: return dict(record,status='not_launched_budget')
    if not space_available(): return dict(record,status='not_launched_disk')
    folder=run/case['id']; folder.mkdir()
    d.write_json(folder/'spec.json',dict(case=case,config=config,inputs=str(run/'inputs')))
    start=time.monotonic(); print('Starting '+case['id'],flush=True)
    with (folder/'stdout.log').open('x') as log:
        try:
            proc=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--worker',str(folder/'spec.json')],
                cwd=folder,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                timeout=min(remaining,config['worker_timeout_seconds']))
            record.update(status='finished',returncode=proc.returncode)
        except subprocess.TimeoutExpired: record.update(status='timeout',returncode=None)
    record['elapsed_seconds']=time.monotonic()-start
    if (folder/'result.json').exists():
        result=json.loads((folder/'result.json').read_text()); record['result']=result
        record['result_sha256']=d.digest(folder/'result.json')
        record['execution_pass']=record['returncode']==0 and result['execution_pass']
    print(f"{case['id']}: {'VALID' if record['execution_pass'] else 'INVALID'} ({record['elapsed_seconds']:.1f}s)",flush=True)
    return record

def freeze(run):
    hashes=d.execution_manifest(); (run/'frozen').mkdir(); frozen={}
    for path in d.LOCAL_FILES:
        if path.name in frozen: raise ValueError('Frozen filename collision')
        shutil.copyfile(path,run/'frozen'/path.name); frozen[path.name]=hashes[str(path.relative_to(d.ROOT))]
        if d.digest(run/'frozen'/path.name)!=frozen[path.name]: raise RuntimeError('Source changed during freeze')
    inputs={}
    for name,source in d.input_paths().items():
        target=run/'inputs'/name; target.parent.mkdir(parents=True,exist_ok=True)
        before=d.digest(source); os.link(source,target)
        if not os.path.samefile(source,target) or not before==d.digest(source)==d.digest(target): raise RuntimeError('Input changed during freeze')
        inputs[name]=dict(source=str(source),sha256=before,storage="hardlink_immutable_v1")
    return hashes,frozen,inputs

def predecessor_audit(run):
    from analyze_paper_preparation_support import predecessor_audit as audit
    return audit(run)

def run(config_path):
    from analyze_paper_preparation_support import stage_audit,integrity
    config=d.validate_config(json.loads(config_path.read_text())); d.source_check()
    if not space_available(): raise RuntimeError('Require 5 GiB free on both filesystems')
    began=time.monotonic(); deadline=began+config['total_budget_seconds']
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_dir=Path(tempfile.mkdtemp(prefix=f'paper-preparation-support-{stamp}-',dir=d.ROOT/'runs'))
    hashes,frozen,inputs=freeze(run_dir)
    summary=dict(started_utc=stamp,revision=d.REVISION,config=config,registered_cases=d.fixed_cases(),cases=[],
        hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,python=sys.version,
        packages={n:importlib.metadata.version(n) for n in ('numpy','scipy','matplotlib')},
        predecessor_gate=False,predecessor_audit=None,gates={},gate_hashes={},stage='preflight')
    d.write_json(run_dir/'summary.json',summary); print(f'Run artifacts: {run_dir}',flush=True)
    history=predecessor_audit(run_dir); d.write_json(run_dir/'predecessor_audit.json',history)
    summary.update(predecessor_audit=history,predecessor_gate=history['quality_gate'],
        predecessor_audit_sha256=d.digest(run_dir/'predecessor_audit.json'))
    d.write_json(run_dir/'summary.json',summary)
    if not history['quality_gate']: raise RuntimeError('P18 re-audit failed; no new integration permitted')
    env=os.environ.copy(); env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',MPLBACKEND='Agg',
        MPLCONFIGDIR=str(d.ROOT/'.cache/matplotlib'),XDG_CACHE_HOME=str(d.ROOT/'.cache'),
        OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
    attempted=[]; valid=True
    for stage in d.STAGES:
        attempted.append(stage); summary['stage']=stage; d.write_json(run_dir/'summary.json',summary)
        cases=d.stage_cases(stage)
        with ThreadPoolExecutor(max_workers=2) as pool:
            tasks=[pool.submit(run_worker,c,config,run_dir,deadline,env) for c in cases]
            for task in as_completed(tasks):
                summary['cases'].append(task.result()); d.write_json(run_dir/'summary.json',summary)
        if not all(next(r for r in summary['cases'] if r['id']==c['id'])['execution_pass'] for c in cases):
            valid=False; summary['completion_reason']='execution_failure'; break
        gate=stage_audit(run_dir,stage); d.write_json(run_dir/(stage+'_audit.json'),gate)
        summary['gates'][stage]=gate; summary['gate_hashes'][stage]=d.digest(run_dir/(stage+'_audit.json'))
        d.write_json(run_dir/'summary.json',summary)
        if not gate['quality_gate']:
            valid=False; summary['completion_reason']='technical_gate_failure'; break
        if stage=='onward': summary['completion_reason']='all_registered_stages_completed'
    summary['attempted_stages']=attempted
    d.source_check(); summary['integrity']=integrity(run_dir,summary)
    summary.update(elapsed_seconds=time.monotonic()-began,stage='finished',all_execution_valid=bool(valid and
        attempted==list(d.STAGES) and len(summary['cases'])==192 and all(c['execution_pass'] for c in summary['cases']) and
        all(summary['integrity'].values())))
    d.write_json(run_dir/'summary.json',summary); print(f'Summary: {run_dir/"summary.json"}',flush=True)
    return 0 if summary['all_execution_valid'] else 1

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--worker',type=Path)
    p.add_argument('--config',type=Path,default=d.ROOT/'configs/paper_preparation_support_v1.json'); args=p.parse_args()
    return worker(args.worker.resolve()) if args.worker else run(args.config.resolve())

if __name__=='__main__': raise SystemExit(main())
