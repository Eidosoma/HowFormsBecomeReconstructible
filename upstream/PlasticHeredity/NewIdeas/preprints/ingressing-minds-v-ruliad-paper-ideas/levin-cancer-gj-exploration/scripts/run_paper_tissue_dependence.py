"""P15 actual-state support withdrawal, fixed turnover and unconditional onward assays."""
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
import paper_tissue_dependence_design as d
from run_paper_contact_clock_recovery import ClockBoundedExperiment
from run_paper_staged_relay import phase
from run_paper_sheet import load_array
from run_paper_tissue_persistence import observe
import paper_bounded_clock as clock

def stock(run,fine):
    x=load_array(run/'inputs/p14/inputs/p13/inputs/p12/inputs/p11',
                 'stock'+('__fine' if fine else ''),'preparation')
    return x[:,168:169],x[:,1:2]

def turnover(exp,c,run):
    E,M=stock(run,c['fine']); src=d.source(c)
    value=load_array(run/'inputs/p14',src,'withdrawal_2')
    record=json.loads((run/'inputs/p14'/src/'result.json').read_text())
    ids=next(p['setup']['cell_ids'] for p in record['phases'] if p['phase']=='withdrawal_2').copy()
    if c['carrier']=='stock_E':
        value[:,list(d.PATCH)]=np.repeat(E,3,axis=1)
        for p,name in zip(d.PATCH,d.stock_ids(c)): ids[p]=name
    original_ids=[ids[p] for p in d.PATCH]
    source_labels=''.join(exp.z.GRN.state_char(value[:,p]) for p in d.PATCH)
    if source_labels!='EEE': raise ValueError('Registered source not corrected E')
    observations={}; replacements=[]; base=1060000
    for i,pos in enumerate(d.PATCH):
        initial=d.incoming(M,i); lab=exp.z.GRN.state_char(initial[:,0])
        if lab!='M': raise ValueError('Replacement not initially M')
        old_id=ids[pos]; ids[pos]=d.new_id(c,i)
        value=value.copy(); value[:,pos:pos+1]=initial
        exp.configure([13,13],ids,value,'depol',60,0 if c['route']=='patch_rna' else 1.25e-14,
                      patch=list(d.PATCH),internal=60,boundary=1,cut=c['route']!='tissue')
        name='replacement_'+str(i+1)
        value=phase(exp,name,20000,base+20000*i)
        observations[name]=observe(exp,name,d.PATCH)
        replacements.append(dict(position=pos,removed=old_id,inserted=ids[pos],initial_label=lab,
                                 stable_E=observations[name]['stable_E']))
        d.write_json(exp.folder/'tissue_progress.json',dict(case=c,replacements=replacements,observations=observations))
    exp.configure([1,3],[ids[p] for p in d.PATCH],value[:,list(d.PATCH)],isolated=True)
    for i in (1,2):
        name='isolated_'+str(i); phase(exp,name,10000,base+60000+(i-1)*10000)
        observations[name]=observe(exp,name,range(3),False)
    replaced=all(all(row['stable_E']) for row in replacements)
    isolated=all(all(observations['isolated_'+str(i)]['stable_E']) for i in (1,2))
    return dict(available=True,source_labels=source_labels,original_ids=original_ids,
        observations=observations,replacements=replacements,all_replacements_corrected=replaced,
        isolated_E_memory=isolated,renewal_success=replaced and isolated,logical_end=1140000)

def readout(exp,c,run):
    E,M=stock(run,c['fine'])
    if c['stage']=='readout':
        donors=np.repeat(E,3,axis=1); ids=d.benchmark_ids(); base=0
    else:
        parent=d.parent(c)
        donors=load_array(run,parent['id'],'isolated_2')
        record=json.loads((run/parent['id']/'result.json').read_text())
        ids=record['phases'][-1]['setup']['cell_ids'].copy(); base=1140000
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
    success=all(all(observations['isolated_'+str(i)]['stable_E']) for i in (1,2))
    return dict(available=True,donor_initial_labels=initial_donors,recipient_initial_labels=initial_recipients,
        donor_end_labels=donor_end,observations=observations,transmitted_E=success,logical_end=base+40000)

def trajectory(exp,c,run):
    return turnover(exp,c,run) if c['stage']=='turnover' else readout(exp,c,run)

def result_record(exp,c,outcome):
    return dict(case=c,ion_indices=exp.indices,phases=exp.records,outcome=outcome,execution_pass=True,
        clock_method=clock.METHOD,external_schedule=True,all_cells_evolve=True,
        full_source_transfer=True,only_registered_columns_replaced=True,
        benchmark_prior_age_matched=False,autonomous_reproduction=False,parameter_retuning=False,
        outcome_dependent_cell_selection=False,cross_branch_pooling=False,
        cell_division_simulated=False,independent_biological_replicates=False,automatic_follow_on=False,
        exact_P14_suffix_replay=c['stage']=='turnover' and c['carrier']=='actual' and c['route']=='tissue')

def worker(path):
    spec=json.loads(path.read_text()); d.validate_config(spec['config']); c=spec['case']; run=path.parent.parent
    if c not in d.fixed_cases() or Path(spec['inputs'])!=run/'inputs': raise ValueError('Unregistered P15 worker')
    summary=json.loads((run/'summary.json').read_text())
    if summary['stage']!=c['stage']: raise ValueError('Wrong P15 stage')
    history=summary.get('predecessor_audit',{}); hp=run/'predecessor_audit.json'
    if (not summary.get('predecessor_gate') or not history.get('quality_gate') or
        json.loads(hp.read_text())!=history or d.digest(hp)!=summary.get('predecessor_audit_sha256')):
        raise ValueError('P14 preflight not passed')
    for stage in d.STAGES[:d.STAGES.index(c['stage'])]:
        gp=run/(stage+'_audit.json'); gate=json.loads(gp.read_text())
        if (not gate['quality_gate'] or summary['gates'].get(stage)!=gate or
            summary['gate_hashes'].get(stage)!=d.digest(gp)): raise ValueError('Invalid prior-stage audit')
    if json.loads((run/'frozen/paper_tissue_dependence_draws_v1.json').read_text())!=d.draw_book():
        raise ValueError('Incoming draws changed')
    if c['stage']=='onward':
        source=d.parent(c)['id']; rows=[row for row in summary['cases'] if row['id']==source]
        if len(rows)!=1 or not rows[0]['execution_pass']: raise ValueError('Missing actual turnover parent')
        if d.digest(run/source/'result.json')!=rows[0]['result_sha256']: raise ValueError('Changed turnover parent')
        for rec in rows[0]['result']['phases']:
            if d.digest(run/source/(rec['phase']+'.npz'))!=rec['sha256']: raise ValueError('Changed parent raw phase')
    exp=ClockBoundedExperiment(path.parent,dict(id=c['id'],fine=c['fine']))
    out=trajectory(exp,c,run); d.write_json(path.parent/'result.json',result_record(exp,c,out)); return 0

def run_worker(case,config,run,deadline,env):
    remaining=deadline-time.monotonic(); record=dict(id=case['id'],execution_pass=False)
    if remaining<=0: return dict(record,status='not_launched_budget')
    if shutil.disk_usage(d.ROOT).free<5*1024**3: return dict(record,status='not_launched_disk')
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
        before=d.digest(source); shutil.copyfile(source,target)
        if not before==d.digest(source)==d.digest(target): raise RuntimeError('Input changed during freeze')
        inputs[name]=dict(source=str(source),sha256=before)
    return hashes,frozen,inputs

def predecessor_audit(run):
    from analyze_paper_tissue_dependence import predecessor_audit as audit
    return audit(run)

def run(config_path):
    from analyze_paper_tissue_dependence import stage_audit,integrity
    config=d.validate_config(json.loads(config_path.read_text())); d.source_check()
    if shutil.disk_usage(d.ROOT).free<5*1024**3: raise RuntimeError('Require 5 GiB free')
    began=time.monotonic(); deadline=began+config['total_budget_seconds']
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_dir=Path(tempfile.mkdtemp(prefix=f'paper-tissue-dependence-{stamp}-',dir=d.ROOT/'runs'))
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
    if not history['quality_gate']: raise RuntimeError('P14 re-audit failed; no new integration permitted')
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
        attempted==list(d.STAGES) and len(summary['cases'])==102 and all(c['execution_pass'] for c in summary['cases']) and
        all(summary['integrity'].values())))
    d.write_json(run_dir/'summary.json',summary); print(f'Summary: {run_dir/"summary.json"}',flush=True)
    return 0 if summary['all_execution_valid'] else 1

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--worker',type=Path)
    p.add_argument('--config',type=Path,default=d.ROOT/'configs/paper_tissue_dependence_v1.json'); args=p.parse_args()
    return worker(args.worker.resolve()) if args.worker else run(args.config.resolve())

if __name__=='__main__': raise SystemExit(main())
