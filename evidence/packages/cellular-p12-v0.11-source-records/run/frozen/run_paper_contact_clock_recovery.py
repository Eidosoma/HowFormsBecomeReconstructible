"""P10R complete rerun with native equations and auditable bounded clocks."""
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
import paper_contact_clock_recovery_design as d
import run_paper_m_calibration as p7
from run_paper_sheet import reference,load_array
from run_paper_topology import TopologyExperiment
from run_paper_staged_relay import phase,retained_M


import paper_bounded_clock as clock
from run_paper_contact_schedule import (CommonGraphExperiment,trajectory as original_trajectory,
    result_record as original_record,stock_root,founder_state)


class ClockBoundedExperiment(CommonGraphExperiment):
    def __init__(self,folder,case,native_replay=False):
        super().__init__(folder,case)
        self.native_replay=native_replay

    def phase(self,name,horizon,**kwargs):
        if self.native_replay: return super().phase(name,horizon,**kwargs)
        original=self.sim.sim; captured={}
        def bounded(actual):
            times,values,trace,meta=clock.integrate(self.sim,actual,100,50 if self.case['fine'] else 100)
            captured.update(trace=trace,metadata=meta)
            return times,values
        try:
            self.sim.sim=bounded
            result=super().phase(name,horizon,**kwargs)
        finally:
            self.sim.sim=original
        path=self.folder/(name+'.npz')
        with np.load(path,allow_pickle=False) as old: payload={k:old[k].copy() for k in old.files}
        payload.update(captured['trace']); np.savez_compressed(path,**payload)
        self.records[-1].update(sha256=d.digest(path),clock=captured['metadata'])
        d.write_json(self.folder/'progress.json',self.records)
        return result


def trajectory(exp,case,run):
    if case['kind']!='clock_probe': return original_trajectory(exp,case,run)
    source=run/'inputs/failed_attempt'/case['source']
    with np.load(source/'r01_isolated_1.npz',allow_pickle=False) as old: state=old['initial'].copy()
    info=json.loads((source/'result.json').read_text())
    ids=next(p['setup']['cell_ids'] for p in info['phases'] if p['phase']=='r01_isolated_1')
    exp.configure([1,3],ids,state,isolated=True)
    phase(exp,'isolated_1',10000,0); phase(exp,'isolated_2',10000,10000)
    return []


def result_record(exp,case,rounds):
    result=original_record(exp,case,rounds)
    result.update(clock_method='original_native' if case['kind']=='replay' else clock.METHOD,
                  failed_attempt_used_for_main_selection=False)
    if case['kind']=='clock_probe':
        result.update(stop_reason='clock_probe',explicit_non_lattice_extension=False,
                      source_is_pre_hold_initial=True)
    return result


def worker(path):
    spec=json.loads(path.read_text()); d.validate_config(spec['config']); case=spec['case']; run=path.parent.parent
    allowed=d.fixed_cases()
    if case['kind']=='continuation':
        summary=json.loads((run/'summary.json').read_text()); choice=json.loads((run/'screen_audit.json').read_text())
        if not choice['quality_gate'] or summary['screen_audit']!=choice or d.digest(run/'screen_audit.json')!=summary['screen_audit_sha256']:
            raise ValueError('Unaudited continuation selection')
        allowed=d.continuation_cases(choice['selected'])
    if case not in allowed or Path(spec['inputs'])!=run/'inputs': raise ValueError('Unregistered P10R worker')
    exp=ClockBoundedExperiment(path.parent,dict(id=case['id'],fine=case['fine']),native_replay=case['kind']=='replay')
    rounds=trajectory(exp,case,run)
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
    from analyze_paper_staged_relay import analyze
    report=analyze(d.PREDECESSOR)
    saved=json.loads((run/'inputs/p9/independent_audit.json').read_text())
    return bool(report==saved and report['quality_gate'] and
                report['independent_check_count']==19424 and report['native_integrations']==398)


def run(config_path):
    from analyze_paper_contact_clock_recovery import gate_audit,calibration_audit,screen_audit,integrity,clock_probe_audit,failed_attempt_audit
    config=d.validate_config(json.loads(config_path.read_text())); d.source_check()
    if shutil.disk_usage(d.ROOT).free<5*1024**3: raise RuntimeError('Require 5 GiB free')
    began=time.monotonic(); deadline=began+config['total_budget_seconds']
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_dir=Path(tempfile.mkdtemp(prefix=f'paper-contact-clock-recovery-{stamp}-',dir=d.ROOT/'runs'))
    hashes,frozen,inputs=freeze(run_dir); cases=d.fixed_cases()
    summary=dict(started_utc=stamp,revision=d.REVISION,config=config,registered_cases=cases,cases=[],
        hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,python=sys.version,
        packages={n:importlib.metadata.version(n) for n in ('numpy','scipy','matplotlib')},
        predecessor_gate=False,gate=None,failed_attempt_audit=None,clock_probe_audit=None,calibration_audit=None,screen_audit=None,selected=[],stage='preflight')
    d.write_json(run_dir/'summary.json',summary); print(f'Run artifacts: {run_dir}',flush=True)
    summary['predecessor_gate']=predecessor_gate(run_dir); d.write_json(run_dir/'summary.json',summary)
    if not summary['predecessor_gate']: raise RuntimeError('P9 re-audit failed; no P10 integration permitted')
    env=os.environ.copy(); env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',MPLBACKEND='Agg',
        MPLCONFIGDIR=str(d.ROOT/'.cache/matplotlib'),XDG_CACHE_HOME=str(d.ROOT/'.cache'),
        OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
    def batch(stage,selected):
        summary['stage']=stage; d.write_json(run_dir/'summary.json',summary)
        with ThreadPoolExecutor(max_workers=2) as pool:
            tasks=[pool.submit(run_worker,c,config,run_dir,deadline,env) for c in selected]
            for task in as_completed(tasks):
                summary['cases'].append(task.result()); d.write_json(run_dir/'summary.json',summary)
        return all(next(r for r in summary['cases'] if r['id']==c['id'])['execution_pass'] for c in selected)
    def audit(name,function):
        report=function(run_dir); d.write_json(run_dir/(name+'.json'),report)
        summary.update({name:report,name+'_sha256':d.digest(run_dir/(name+'.json'))})
        d.write_json(run_dir/'summary.json',summary)
        return report
    valid=audit('failed_attempt_audit',failed_attempt_audit)['quality_gate']
    if valid: valid=batch('historical_replays',cases[:2])
    if valid: valid=audit('gate',gate_audit)['quality_gate']
    if valid: valid=batch('clock_probes',cases[2:14])
    if valid: valid=audit('clock_probe_audit',clock_probe_audit)['quality_gate']
    if valid: valid=batch('graph_calibration',cases[14:22])
    if valid:
        calibration=audit('calibration_audit',calibration_audit); valid=calibration['quality_gate']
        if valid and not calibration['eligible']: summary['completion_reason']='common_graph_not_qualified'
        elif valid:
            valid=batch('coarse_screen',cases[22:47])
            if valid: valid=batch('fine_screen',cases[47:72])
            if valid:
                screen=audit('screen_audit',screen_audit); valid=screen['quality_gate']
                if valid:
                    selected=screen['selected']; summary['selected']=selected
                    new_cases=d.continuation_cases(selected); summary['registered_cases']+=new_cases
                    d.write_json(run_dir/'summary.json',summary)
                    if new_cases: valid=batch('selected_continuations',new_cases)
                    summary['completion_reason']='selected_continuations_completed' if selected else 'no_eligible_schedule'
    d.source_check(); summary['integrity']=integrity(run_dir,summary)
    expected_count=22 if summary.get('completion_reason')=='common_graph_not_qualified' else 72+12*len(summary['selected'])
    summary.update(elapsed_seconds=time.monotonic()-began,stage='finished',all_execution_valid=bool(valid and
        len(summary['cases'])==expected_count and all(c['execution_pass'] for c in summary['cases']) and
        all(summary['integrity'].values())))
    d.write_json(run_dir/'summary.json',summary); print(f'Summary: {run_dir / "summary.json"}',flush=True)
    return 0 if summary['all_execution_valid'] else 1


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--worker',type=Path)
    p.add_argument('--config',type=Path,default=d.ROOT/'configs/paper_contact_clock_recovery_v1.json'); args=p.parse_args()
    return worker(args.worker.resolve()) if args.worker else run(args.config.resolve())


if __name__=='__main__': raise SystemExit(main())
