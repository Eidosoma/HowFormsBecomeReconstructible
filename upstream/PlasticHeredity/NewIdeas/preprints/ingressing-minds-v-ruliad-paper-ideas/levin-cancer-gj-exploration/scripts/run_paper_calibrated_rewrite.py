"""P8 calibrated writing of actual lineage carriers, with one fresh probe."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
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
import paper_calibrated_rewrite_design as d
import run_paper_m_calibration as p7
from run_paper_sheet import reference,load_array
from run_paper_topology import TopologyExperiment


def initial_targets(case,run):
    E,_=reference(run/'inputs/p7/inputs/p3')
    background=case['background']
    if background=='fresh_E':
        return np.repeat(E,3,axis=1),[f'target:fresh:{i:02d}' for i in range(3)]
    if background=='aged_E':
        folder='age__E'+('__fine' if case['fine'] else '')
        return load_array(run,folder,'age_3'),[f'aged:{i:02d}' for i in range(3)]
    source='relay__'+background+'__open'
    info=json.loads((run/'inputs/p5'/source/'result.json').read_text())
    ids=next(p['setup']['cell_ids'] for p in info['phases'] if p['phase']=='r06_isolated_2')
    return load_array(run/'inputs/p5',source,'r06_isolated_2'),ids


def trajectory(exp,case,run):
    inputs=run/'inputs'
    if case['kind']=='replay':
        p7.trajectory(exp,d.replay_source(case['layout']),inputs/'p7/inputs')
        return
    E,M=reference(inputs/'p7/inputs/p3')
    if case['kind']=='age':
        exp.configure([1,3],[f'aged:{i:02d}' for i in range(3)],np.repeat(E,3,axis=1),isolated=True)
        for i,horizon in enumerate((20000,10000,10000),1): exp.phase(f'age_{i}',horizon)
        return
    carry,ids=initial_targets(case,run); condition=case['condition']
    if condition=='no_cue':
        exp.configure([1,3],ids,carry,'depol',60,0,isolated=True)
    else:
        cue=E if condition=='E_sham' else M
        state=np.concatenate((np.repeat(cue,6,axis=1),carry),axis=1)
        exp.configure([3,3],[f'cue:{i:02d}' for i in range(6)]+ids,state,'depol',60,
            0 if condition=='M_write_rna' else 1.25e-14,patch=list(range(6)),cut=condition=='M_write_cut')
    contact,_=exp.phase('writing_contact',20000)
    exp.configure([1,3],ids,contact if condition=='no_cue' else contact[:,6:],isolated=True)
    exp.phase('writing_isolated_1',10000)
    held,_=exp.phase('writing_isolated_2',10000)
    exp.configure([2,2],ids+['probe:00'],np.concatenate((held,E),axis=1),'depol',60,
        0 if condition=='M_probe_rna' else 1.25e-14,patch=[0,1,2],cut=condition=='M_probe_cut')
    contact,_=exp.phase('probe_contact',20000)
    exp.configure([1,1],['probe:00'],contact[:,3:4],isolated=True)
    exp.phase('probe_isolated_1',10000); exp.phase('probe_isolated_2',10000)


def result_record(exp,case):
    return dict(case=case,ion_indices=exp.indices,phases=exp.records,execution_pass=True,
        parameter_retuning=False,outcome_dependent_selection=False,cell_division_simulated=False,
        artificial_target_schedule=False,external_handover_schedule=True,cue_cells_retained=False,
        historical_rounds=6 if case.get('background') in ('ordinary_E','restored_E') else 0,
        newly_simulated_writing_events=int(case['kind']=='rewrite'),
        new_onward_handovers=int(case['kind']=='rewrite'),serial_relay=False,
        stress_panel=False,return_to_E=False,automatic_follow_on=False)


def worker(path):
    spec=json.loads(path.read_text()); d.validate_config(spec['config']); case=spec['case']
    if case not in d.fixed_cases() or Path(spec['inputs'])!=path.parent.parent/'inputs':
        raise ValueError('Unregistered P8 worker or input path')
    exp=TopologyExperiment(path.parent,dict(id=case['id'],fine=case['fine']))
    trajectory(exp,case,path.parent.parent)
    d.write_json(path.parent/'result.json',result_record(exp,case)); return 0


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


def predecessor_gate(run):
    from analyze_paper_m_calibration import analyze as audit7
    from analyze_paper_relay import analyze as audit5
    for key,source,audit,n,calls in (('p7',d.PREDECESSOR,audit7,14506,295),
                                  ('p5',d.LINEAGE_SOURCE,audit5,42065,804)):
        result=audit(source); saved=json.loads((run/'inputs'/key/'independent_audit.json').read_text())
        if not (result==saved and result['quality_gate'] and result['independent_check_count']==n and result['native_integrations']==calls):
            return False
    return True


def run(config_path):
    from analyze_paper_calibrated_rewrite import gate_audit,age_gate_audit,integrity
    config=d.validate_config(json.loads(config_path.read_text())); d.source_check()
    if shutil.disk_usage(d.ROOT).free<5*1024**3: raise RuntimeError('Require 5 GiB free')
    began=time.monotonic(); deadline=began+config['total_budget_seconds']
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_dir=Path(tempfile.mkdtemp(prefix=f'paper-calibrated-rewrite-{stamp}-',dir=d.ROOT/'runs'))
    hashes,frozen,inputs=freeze(run_dir); cases=d.fixed_cases()
    summary=dict(started_utc=stamp,revision=d.REVISION,config=config,registered_cases=cases,cases=[],
        hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,python=sys.version,
        packages={n:importlib.metadata.version(n) for n in ('numpy','scipy','matplotlib')},
        predecessor_gate=False,gate=None,age_gate=None,stage='preflight')
    d.write_json(run_dir/'summary.json',summary); print(f'Run artifacts: {run_dir}',flush=True)
    summary['predecessor_gate']=predecessor_gate(run_dir); d.write_json(run_dir/'summary.json',summary)
    if not summary['predecessor_gate']: raise RuntimeError('Historical re-audit failed; no P8 integration permitted')
    env=os.environ.copy(); env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',MPLBACKEND='Agg',
        MPLCONFIGDIR=str(d.ROOT/'.cache/matplotlib'),XDG_CACHE_HOME=str(d.ROOT/'.cache'),
        OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
    for stage,selected in (('historical_replays',cases[:3]),('age_preparation',cases[3:5]),('coarse_rewriting',cases[5:33]),('fine_rewriting',cases[33:])):
        summary['stage']=stage; d.write_json(run_dir/'summary.json',summary)
        with ThreadPoolExecutor(max_workers=2) as pool:
            tasks=[pool.submit(run_worker,c,config,run_dir,deadline,env) for c in selected]
            for task in as_completed(tasks):
                summary['cases'].append(task.result()); d.write_json(run_dir/'summary.json',summary)
        key='gate' if stage=='historical_replays' else 'age_gate' if stage=='age_preparation' else None
        if key:
            gate=gate_audit(run_dir) if key=='gate' else age_gate_audit(run_dir)
            d.write_json(run_dir/(key+'.json'),gate)
            summary[key]=gate; summary[key+'_sha256']=d.digest(run_dir/(key+'.json'))
            d.write_json(run_dir/'summary.json',summary)
            if not gate['quality_gate']: summary['stopped_after_gate']=key; break
        if not all(next(r for r in summary['cases'] if r['id']==c['id'])['execution_pass'] for c in selected):
            summary['stopped_after_stage']=stage; break
    d.source_check(); summary['integrity']=integrity(run_dir,summary)
    summary.update(elapsed_seconds=time.monotonic()-began,stage='finished',all_execution_valid=(
        len(summary['cases'])==61 and all(c['execution_pass'] for c in summary['cases']) and
        all(summary['integrity'].values()) and bool((summary.get('gate') or {}).get('quality_gate')) and bool((summary.get('age_gate') or {}).get('quality_gate'))))
    d.write_json(run_dir/'summary.json',summary); print(f'Summary: {run_dir / "summary.json"}',flush=True)
    return 0 if summary['all_execution_valid'] else 1


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--worker',type=Path)
    p.add_argument('--config',type=Path,default=d.ROOT/'configs/paper_calibrated_rewrite_v1.json'); args=p.parse_args()
    return worker(args.worker.resolve()) if args.worker else run(args.config.resolve())


if __name__=='__main__': raise SystemExit(main())
