"""P5: fixed twelve-round 2D relay, continuing actual archived P4 recipients."""
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
import paper_relay_design as d
from run_paper_topology import TopologyExperiment,trajectory as p4_trajectory
from run_paper_sheet import load_array,reference


def trajectory(exp,case,inputs):
    source=inputs/case['source']
    old=json.loads((source/'result.json').read_text())
    if case['kind']=='replay':
        p4_trajectory(exp,old['case'],inputs/'p4_inputs'); return
    _,M=reference(inputs/'p4_inputs')
    carry=load_array(inputs,case['source'],'onward_isolated_2')
    ids=next(p['setup']['cell_ids'] for p in old['phases'] if p['phase']=='onward_isolated_2')
    for round_number in range(2,13):
        fresh=[f'relay:{round_number:02d}:{i:02d}' for i in range(3)]
        initial=np.concatenate((carry,np.repeat(M,3,axis=1)),axis=1)
        exp.configure([2,3],ids+fresh,initial,'hypol',1,
            0 if case['route']=='rna_blocked' else 1.25e-14,patch=[0,1,2],cut=case['route']=='border_cut')
        contact,_=exp.phase(f'r{round_number:02d}_contact',20000)
        exp.configure([1,3],fresh,contact[:,3:],isolated=True)
        exp.phase(f'r{round_number:02d}_isolated_1',10000)
        carry,_=exp.phase(f'r{round_number:02d}_isolated_2',10000)
        ids=fresh


def worker(path):
    spec=json.loads(path.read_text()); d.validate_config(spec['config']); case=spec['case']
    if case not in d.fixed_cases() or Path(spec['inputs'])!=path.parent.parent/'inputs':
        raise ValueError('Unregistered P5 worker or input path')
    exp=TopologyExperiment(path.parent,dict(id=case['id'],fine=case['fine']))
    trajectory(exp,case,Path(spec['inputs']))
    d.write_json(path.parent/'result.json',dict(case=case,ion_indices=exp.indices,phases=exp.records,
        execution_pass=True,parameter_retuning=False,outcome_dependent_selection=False,
        cell_division_simulated=False,artificial_target_schedule=False,
        external_handover_schedule=True,source_external_regional_intervention=True,
        historical_rounds=0 if case['kind']=='replay' else 1,
        newly_simulated_rounds=1 if case['kind']=='replay' else 11,
        total_rounds=1 if case['kind']=='replay' else 12,midway_rewriting=False,stress_panel=False))
    return 0


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
        if d.digest(run/'frozen'/path.name)!=frozen[path.name]: raise RuntimeError('Changed source during freeze')
    inputs={}
    for name,source in d.input_paths().items():
        target=run/'inputs'/name; target.parent.mkdir(parents=True,exist_ok=True)
        before=d.digest(source); shutil.copyfile(source,target)
        if not before==d.digest(source)==d.digest(target): raise RuntimeError('Changed input during freeze')
        inputs[name]=dict(source=str(source),sha256=before)
    return hashes,frozen,inputs


def predecessor_gate(run):
    from analyze_paper_topology import analyze
    result=analyze(d.PREDECESSOR)
    saved=json.loads((run/'inputs/p4/independent_audit.json').read_text())
    return result==saved and result['quality_gate'] and result['independent_check_count']==42565 and result['native_integrations']==858


def run(config_path):
    from analyze_paper_relay import gate_audit,integrity
    config=d.validate_config(json.loads(config_path.read_text())); d.source_check()
    if shutil.disk_usage(d.ROOT).free<5*1024**3: raise RuntimeError('Require 5 GiB free')
    began=time.monotonic(); deadline=began+config['total_budget_seconds']
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_dir=Path(tempfile.mkdtemp(prefix=f'paper-relay-{stamp}-',dir=d.ROOT/'runs'))
    hashes,frozen,inputs=freeze(run_dir); cases=d.fixed_cases()
    summary=dict(started_utc=stamp,revision=d.REVISION,config=config,registered_cases=cases,cases=[],
        hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,python=sys.version,
        packages={n:importlib.metadata.version(n) for n in ('numpy','scipy','matplotlib')},
        predecessor_gate=False,gate=None,stage='preflight')
    d.write_json(run_dir/'summary.json',summary); print(f'Run artifacts: {run_dir}',flush=True)
    summary['predecessor_gate']=predecessor_gate(run_dir); d.write_json(run_dir/'summary.json',summary)
    if not summary['predecessor_gate']: raise RuntimeError('P4 re-audit fails; no P5 native integration permitted')
    env=os.environ.copy(); env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',MPLBACKEND='Agg',
        MPLCONFIGDIR=str(d.ROOT/'.cache/matplotlib'),XDG_CACHE_HOME=str(d.ROOT/'.cache'),
        OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
    for stage,selected in (('capacity_replays',cases[:4]),('relay_panel',cases[4:])):
        summary['stage']=stage; d.write_json(run_dir/'summary.json',summary)
        with ThreadPoolExecutor(max_workers=2) as pool:
            tasks=[pool.submit(run_worker,c,config,run_dir,deadline,env) for c in selected]
            for task in as_completed(tasks):
                summary['cases'].append(task.result()); d.write_json(run_dir/'summary.json',summary)
        if stage=='capacity_replays':
            gate=gate_audit(run_dir); d.write_json(run_dir/'gate.json',gate)
            summary.update(gate=gate,gate_sha256=d.digest(run_dir/'gate.json')); d.write_json(run_dir/'summary.json',summary)
            if not gate['quality_gate']: summary['stopped_after_gate']=True; break
    d.source_check(); summary['integrity']=integrity(run_dir,summary)
    summary.update(elapsed_seconds=time.monotonic()-began,stage='finished',all_execution_valid=(
        len(summary['cases'])==28 and all(c['execution_pass'] for c in summary['cases']) and
        all(summary['integrity'].values()) and bool((summary.get('gate') or {}).get('quality_gate'))))
    d.write_json(run_dir/'summary.json',summary); print(f'Summary: {run_dir / "summary.json"}',flush=True)
    return 0 if summary['all_execution_valid'] else 1


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--worker',type=Path)
    p.add_argument('--config',type=Path,default=d.ROOT/'configs/paper_relay_v1.json'); args=p.parse_args()
    return worker(args.worker.resolve()) if args.worker else run(args.config.resolve())


if __name__=='__main__': raise SystemExit(main())

