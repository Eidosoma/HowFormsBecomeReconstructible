"""P9 bounded staged relay; all live states carried, waiting explicitly integrated."""
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
import paper_staged_relay_design as d
import run_paper_m_calibration as p7
from run_paper_sheet import reference,load_array
from run_paper_topology import TopologyExperiment


def founder_state(case,run):
    E,M=reference(run/'inputs/p8/inputs/p7/inputs/p3')
    h=case['founder']
    if h.startswith('rewritten_'):
        source='rewrite__'+h.removeprefix('rewritten_')+'__M_open'
        info=json.loads((run/'inputs/p8'/source/'result.json').read_text())
        ids=next(p['setup']['cell_ids'] for p in info['phases'] if p['phase']=='writing_isolated_2')
        return load_array(run/'inputs/p8',source,'writing_isolated_2'),ids
    label='E' if h=='ordinary_E_sham' else 'M'
    return np.repeat(E if label=='E' else M,3,axis=1),[f'founder:{label}:{i:02d}' for i in range(3)]


def phase(exp,name,horizon,logical_start):
    result=exp.phase(name,horizon)
    exp.records[-1]['logical_interval']=[logical_start,logical_start+horizon]
    d.write_json(exp.folder/'progress.json',exp.records)
    return result[0]


def retained_M(exp,prefix):
    # Use native state_char independently of the offline auditor's classifier.
    masks=[]
    for suffix in ('isolated_1','isolated_2'):
        with np.load(exp.folder/(prefix+suffix+'.npz'),allow_pickle=False) as a:
            final=a['final']; late=a['concentrations'][a['times']>=7500]
            if not len(late): raise RuntimeError('Missing retention samples')
            end=np.array([exp.z.GRN.state_char(final[:,i])=='M' for i in range(3)])
            frequency=np.mean([[exp.z.GRN.state_char(x[:,i])=='M' for i in range(3)] for x in late],axis=0)
            masks.append(end & (frequency>=.95))
    return masks[0] & masks[1]


def trajectory(exp,case,run):
    if case['kind']=='replay':
        p7.trajectory(exp,d.replay_source(case['layout']),run/'inputs/p8/inputs/p7/inputs')
        return []
    E,_=reference(run/'inputs/p8/inputs/p7/inputs/p3')
    carry,ids=founder_state(case,run); condition=case['condition']; rounds=[]
    sequential=condition.startswith('sequential')
    for number in range(1,7):
        prefix=f'r{number:02d}_'; base=(number-1)*80000
        fresh=[f'pupil:{number:02d}:{i:02d}' for i in range(3)]
        if sequential:
            teachers=carry.copy(); pupils=np.empty((17,0))
            for slot in range(3):
                exp.configure([2,2],ids+[fresh[slot]],np.concatenate((teachers,E),axis=1),'depol',60,
                    0 if condition=='sequential_rna' else 1.25e-14,patch=[0,1,2],cut=condition=='sequential_cut')
                contact=phase(exp,prefix+f'contact_{slot+1}',20000,base+slot*20000)
                teachers=contact[:,:3].copy(); new=contact[:,3:4].copy()
                if slot:
                    exp.configure([1,slot],fresh[:slot],pupils,isolated=True)
                    pupils=phase(exp,prefix+f'waiting_{slot+1}',20000,base+slot*20000)
                pupils=np.concatenate((pupils,new),axis=1)
        else:
            horizon=20000 if condition=='simultaneous_20' else 60000
            exp.configure([2,3],ids+fresh,np.concatenate((carry,np.repeat(E,3,axis=1)),axis=1),
                          'depol',60,1.25e-14,patch=[0,1,2])
            contact=phase(exp,prefix+'contact',horizon,base); pupils=contact[:,3:].copy()
            if condition=='simultaneous_20':
                exp.configure([1,3],fresh,pupils,isolated=True)
                pupils=phase(exp,prefix+'waiting',40000,base+20000)
        exp.configure([1,3],fresh,pupils,isolated=True)
        phase(exp,prefix+'isolated_1',10000,base+60000)
        carry=phase(exp,prefix+'isolated_2',10000,base+70000); ids=fresh
        mask=retained_M(exp,prefix)
        rounds.append(dict(round=number,retained_M=mask.tolist(),complete=bool(mask.all()),
                           logical_end=base+80000))
        d.write_json(exp.folder/'relay_progress.json',dict(case=case,rounds=rounds,
                     stopped_at_first_incomplete=not bool(mask.all()),maximum_rounds=6))
        print('P9_ROUND '+json.dumps(rounds[-1]),flush=True)
        if not mask.all(): break
    return rounds


def result_record(exp,case,rounds):
    return dict(case=case,ion_indices=exp.indices,phases=exp.records,execution_pass=True,rounds=rounds,
        stop_reason='historical_replay' if case['kind']=='replay' else
            'six_complete_rounds' if rounds[-1]['complete'] and len(rounds)==6 else 'first_incomplete_round',
        newly_simulated_rounds=len(rounds),unattempted_rounds=0 if case['kind']=='replay' else 6-len(rounds),
        external_handover_schedule=True,donor_reuse_within_round=case['kind']=='relay' and case['condition'].startswith('sequential'),
        teachers_retained_between_rounds=False,waiting_cells_frozen=False,parameter_retuning=False,
        outcome_dependent_cell_selection=False,registered_stop_on_incomplete=True,
        cell_division_simulated=False,extra_M_supplementation=False,cross_branch_pooling=False,
        founder_prefix_is_new_replication=False,stress_panel=False,automatic_follow_on=False)


def worker(path):
    spec=json.loads(path.read_text()); d.validate_config(spec['config']); case=spec['case']
    if case not in d.fixed_cases() or Path(spec['inputs'])!=path.parent.parent/'inputs':
        raise ValueError('Unregistered P9 worker or input path')
    exp=TopologyExperiment(path.parent,dict(id=case['id'],fine=case['fine']))
    rounds=trajectory(exp,case,path.parent.parent)
    d.write_json(path.parent/'result.json',result_record(exp,case,rounds)); return 0


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
    from analyze_paper_calibrated_rewrite import analyze
    report=analyze(d.PREDECESSOR)
    saved=json.loads((run/'inputs/p8/independent_audit.json').read_text())
    return bool(report==saved and report['quality_gate'] and
                report['independent_check_count']==16949 and report['native_integrations']==351)


def run(config_path):
    from analyze_paper_staged_relay import gate_audit,integrity
    config=d.validate_config(json.loads(config_path.read_text())); d.source_check()
    if shutil.disk_usage(d.ROOT).free<5*1024**3: raise RuntimeError('Require 5 GiB free')
    began=time.monotonic(); deadline=began+config['total_budget_seconds']
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_dir=Path(tempfile.mkdtemp(prefix=f'paper-staged-relay-{stamp}-',dir=d.ROOT/'runs'))
    hashes,frozen,inputs=freeze(run_dir); cases=d.fixed_cases()
    summary=dict(started_utc=stamp,revision=d.REVISION,config=config,registered_cases=cases,cases=[],
        hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,python=sys.version,
        packages={n:importlib.metadata.version(n) for n in ('numpy','scipy','matplotlib')},
        predecessor_gate=False,gate=None,stage='preflight')
    d.write_json(run_dir/'summary.json',summary); print(f'Run artifacts: {run_dir}',flush=True)
    summary['predecessor_gate']=predecessor_gate(run_dir); d.write_json(run_dir/'summary.json',summary)
    if not summary['predecessor_gate']: raise RuntimeError('Historical re-audit failed; no P9 integration permitted')
    env=os.environ.copy(); env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',MPLBACKEND='Agg',
        MPLCONFIGDIR=str(d.ROOT/'.cache/matplotlib'),XDG_CACHE_HOME=str(d.ROOT/'.cache'),
        OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
    for stage,selected in (('historical_replays',cases[:2]),('coarse_relays',cases[2:18]),('fine_relays',cases[18:])):
        summary['stage']=stage; d.write_json(run_dir/'summary.json',summary)
        with ThreadPoolExecutor(max_workers=2) as pool:
            tasks=[pool.submit(run_worker,c,config,run_dir,deadline,env) for c in selected]
            for task in as_completed(tasks):
                summary['cases'].append(task.result()); d.write_json(run_dir/'summary.json',summary)
        if stage=='historical_replays':
            gate=gate_audit(run_dir); d.write_json(run_dir/'gate.json',gate)
            summary.update(gate=gate,gate_sha256=d.digest(run_dir/'gate.json'))
            d.write_json(run_dir/'summary.json',summary)
            if not gate['quality_gate']: summary['stopped_after_gate']=True; break
        if not all(next(r for r in summary['cases'] if r['id']==c['id'])['execution_pass'] for c in selected):
            summary['stopped_after_stage']=stage; break
    d.source_check(); summary['integrity']=integrity(run_dir,summary)
    summary.update(elapsed_seconds=time.monotonic()-began,stage='finished',all_execution_valid=(
        len(summary['cases'])==34 and all(c['execution_pass'] for c in summary['cases']) and
        all(summary['integrity'].values()) and bool((summary.get('gate') or {}).get('quality_gate'))))
    d.write_json(run_dir/'summary.json',summary); print(f'Summary: {run_dir / "summary.json"}',flush=True)
    return 0 if summary['all_execution_valid'] else 1


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--worker',type=Path)
    p.add_argument('--config',type=Path,default=d.ROOT/'configs/paper_staged_relay_v1.json'); args=p.parse_args()
    return worker(args.worker.resolve()) if args.worker else run(args.config.resolve())


if __name__=='__main__': raise SystemExit(main())

