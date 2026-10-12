"""P13: return actual P12 descendants to M and renew through three handovers."""
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
import paper_lineage_return_design as d
from run_paper_contact_clock_recovery import ClockBoundedExperiment
from run_paper_staged_relay import phase
from run_paper_sheet import load_array
import paper_bounded_clock as clock

from run_paper_lineage_robustness import retention

def stock(run,fine):
    x=load_array(run/'inputs/p12/inputs/p11','stock'+('__fine' if fine else ''),'preparation')
    return x[:,168:169],x[:,1:2]

def writing(exp,c,targets,ids,E,M,mode,base):
    nocue=mode in ('none','age')
    if nocue:
        exp.configure([1,3],ids,targets,'depol',1 if mode=='age' else 60,0,isolated=True)
    else:
        cue=E if mode=='sham' else M
        exp.configure([3,3],d.cue_ids(c)+ids,np.concatenate((np.repeat(cue,6,axis=1),targets),axis=1),
            'depol',60,0 if mode=='rna' else 1.25e-14,patch=list(range(6)),cut=mode=='cut')
    contact=phase(exp,'writing_contact',20000,base)
    exp.configure([1,3],ids,contact if nocue else contact[:,6:],isolated=True)
    phase(exp,'writing_isolated_1',10000,base+20000)
    held=phase(exp,'writing_isolated_2',10000,base+30000)
    masks=retention(exp,'writing_')
    return held,dict(retained_E=masks['E'],retained_M=masks['M'],qualified=all(masks['M']))

def relay(exp,c,carry,ids,E,number,route,base):
    prefix=f'r{number:02d}_'; fresh=d.pupil_ids(c,number); pupils=d.recipient(E,c['seed'],f'r{number:02d}')
    exp.configure_graph(ids+fresh,np.concatenate((carry,pupils),axis=1),route)
    initial=''.join(exp.z.GRN.state_char(x) for x in pupils.T); presignal=[None]*3
    for slot,(start,end,active) in enumerate(d.intervals(c['seed'],number),1):
        for i in active:
            if presignal[i] is None: presignal[i]=exp.z.GRN.state_char(exp.sim.cc_cells[:,3+i])
        exp.set_active(active)
        contact=phase(exp,prefix+f'segment_{slot:02d}',end-start,base+start)
    exp.configure([1,3],fresh,contact[:,3:],isolated=True)
    phase(exp,prefix+'isolated_1',10000,base+80000)
    held=phase(exp,prefix+'isolated_2',10000,base+90000)
    masks=retention(exp,prefix)
    return held,fresh,dict(round=number,desired='M',retained_E=masks['E'],retained_M=masks['M'],
        initial_labels=initial,presignal_labels=''.join(presignal),
        complete=all(masks['M']) and initial=='EEE' and presignal==['E']*3,
        negative=all(masks['E']),logical_end=base+100000)

def trajectory(exp,c,run):
    E,M=stock(run,c['fine']); base=d.logical_base(c)
    if c['stage']=='relay_controls':
        parent=d.parent(c); record=json.loads((run/parent['id']/'result.json').read_text())
        if not record['outcome']['writing']['qualified']:
            return dict(available=False,rounds=[],negative=False,skip_reason='parent_writing_unqualified')
        carry=load_array(run,parent['id'],'writing_isolated_2')
        ids=d.founder_ids(c) if c['history']=='benchmark' else d.source(c)[2]
        _,_,row=relay(exp,c,carry,ids,E,7,c['route'],base+40000)
        return dict(available=True,rounds=[row],negative=row['negative'])
    if c['stage']=='benchmarks':
        carry=d.recipient(M,c['seed'],'benchmark'); ids=d.founder_ids(c); mode='age'
    else:
        source,name,ids=d.source(c); carry=load_array(run/'inputs/p12',source,name)
        if any(exp.z.GRN.state_char(x)!='E' for x in carry.T): raise ValueError('P12 source is not the qualified E trio')
        mode=c['route']
    carry,writer=writing(exp,c,carry,ids,E,M,mode,base)
    if c['stage']=='writing_controls':
        return dict(available=True,writing=writer,rounds=[],negative=all(writer['retained_E']))
    rounds=[]; out=dict(available=True,writing=writer,rounds=rounds,complete=False,stop_reason='writer_not_M')
    def save(): d.write_json(exp.folder/'relay_progress.json',dict(case=c,rounds=rounds,outcome=out))
    save()
    if not writer['qualified']: return out
    for number in (7,8,9):
        carry,ids,row=relay(exp,c,carry,ids,E,number,'open',base+40000+(number-7)*100000)
        rounds.append(row); out['stop_reason']=f'round_{number}_incomplete'; save()
        if not row['complete']: return out
    out.update(complete=True,stop_reason='three_return_handovers_complete'); save()
    return out

def result_record(exp,c,outcome):
    if outcome['available']: indices=exp.indices
    else:
        if exp.records: raise ValueError('Skipped control ran phases')
        indices=None
    return dict(case=c,ion_indices=indices,phases=exp.records,outcome=outcome,execution_pass=True,
        clock_method=clock.METHOD,external_schedule=True,all_cells_evolve=True,
        inherited_P12_ancestry=c['history']!='benchmark',historical_rounds=0 if c['history']=='benchmark' else 6,
        only_new_cells_perturbed=True,shared_audited_stock=True,benchmark_prior_age_matched=False,
        autonomous_reproduction=False,parameter_retuning=False,outcome_dependent_cell_selection=False,
        carrier_reset=False,cross_branch_pooling=False,cues_retained=False,independent_biological_replicates=False,
        automatic_follow_on=False)

def worker(path):
    spec=json.loads(path.read_text()); d.validate_config(spec['config']); c=spec['case']; run=path.parent.parent
    if c not in d.fixed_cases() or Path(spec['inputs'])!=run/'inputs': raise ValueError('Unregistered P13 worker')
    summary=json.loads((run/'summary.json').read_text())
    if summary['stage']!=c['stage']: raise ValueError('Wrong authorized stage')
    if not summary.get('predecessor_gate'): raise ValueError('P12 preflight not passed')
    for stage in d.STAGES[:d.STAGES.index(c['stage'])]:
        gate=summary['gates'].get(stage,{}); path_gate=run/(stage+'_audit.json')
        if (not gate.get('quality_gate') or d.digest(path_gate)!=summary['gate_hashes'].get(stage) or
            json.loads(path_gate.read_text())!=gate): raise ValueError('Earlier technical gate did not pass')
    if json.loads((run/'frozen/paper_lineage_return_draws_v1.json').read_text())!=d.draw_book():
        raise ValueError('Draw book changed')
    exp=ClockBoundedExperiment(path.parent,dict(id=c['id'],fine=c['fine']))
    out=trajectory(exp,c,run); d.write_json(path.parent/'result.json',result_record(exp,c,out)); return 0

def run_worker(case,config,run,deadline,env):
    record=dict(id=case['id'],execution_pass=False); remaining=deadline-time.monotonic()
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
    from analyze_paper_lineage_robustness import analyze
    original=analyze(d.PREDECESSOR)
    saved=json.loads((run/'inputs/p12/independent_audit.json').read_text())
    archived=analyze(run/'inputs/p12'); archived['run']=str(d.PREDECESSOR)
    good=original==archived==saved and original['quality_gate'] and original['independent_check_count']==110444
    return dict(quality_gate=bool(good),original_matches_saved=original==saved,archive_matches_saved=archived==saved,
        prior_checks=original['independent_check_count'],prior_cases=original['completed_cases'],
        prior_calls=original['integration_calls'],actual_round_six_sources=True)

def run(config_path):
    from analyze_paper_lineage_return import stage_audit,integrity
    config=d.validate_config(json.loads(config_path.read_text())); d.source_check()
    if json.loads((d.ROOT/'configs/paper_lineage_return_draws_v1.json').read_text())!=d.draw_book():
        raise ValueError('Unregistered draw book')
    if shutil.disk_usage(d.ROOT).free<5*1024**3: raise RuntimeError('Require 5 GiB free')
    began=time.monotonic(); deadline=began+config['total_budget_seconds']
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_dir=Path(tempfile.mkdtemp(prefix=f'paper-lineage-return-{stamp}-',dir=d.ROOT/'runs'))
    hashes,frozen,inputs=freeze(run_dir)
    summary=dict(started_utc=stamp,revision=d.REVISION,config=config,registered_cases=d.fixed_cases(),cases=[],
        hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,python=sys.version,
        packages={n:importlib.metadata.version(n) for n in ('numpy','scipy','matplotlib')},
        predecessor_gate=False,predecessor_audit=None,gates={},gate_hashes={},stage='preflight')
    d.write_json(run_dir/'summary.json',summary); print(f'Run artifacts: {run_dir}',flush=True)
    predecessor=predecessor_audit(run_dir); d.write_json(run_dir/'predecessor_audit.json',predecessor)
    summary.update(predecessor_audit=predecessor,predecessor_gate=predecessor['quality_gate'],
        predecessor_audit_sha256=d.digest(run_dir/'predecessor_audit.json'))
    d.write_json(run_dir/'summary.json',summary)
    if not predecessor['quality_gate']: raise RuntimeError('P12 re-audit failed; no new integration permitted')
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
        if stage=='relay_controls': summary['completion_reason']='all_registered_stages_completed'
    summary['attempted_stages']=attempted
    d.source_check(); summary['integrity']=integrity(run_dir,summary)
    expected=sum(len(d.stage_cases(s)) for s in attempted)
    summary.update(elapsed_seconds=time.monotonic()-began,stage='finished',all_execution_valid=bool(valid and
        len(summary['cases'])==expected and all(c['execution_pass'] for c in summary['cases']) and
        all(summary['integrity'].values())))
    d.write_json(run_dir/'summary.json',summary); print(f'Summary: {run_dir/"summary.json"}',flush=True)
    return 0 if summary['all_execution_valid'] else 1

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--worker',type=Path)
    p.add_argument('--config',type=Path,default=d.ROOT/'configs/paper_lineage_return_v1.json'); args=p.parse_args()
    return worker(args.worker.resolve()) if args.worker else run(args.config.resolve())

if __name__=='__main__': raise SystemExit(main())

