"""P6: temporary cue at round six followed by six opposite-state handovers."""
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
import paper_rewrite_design as d
from run_paper_topology import TopologyExperiment
from run_paper_sheet import load_array, reference


def trajectory(exp, case, inputs):
    E, M = reference(inputs/'p5/inputs/p4_inputs')
    if case['kind'] == 'assay':
        carry = np.repeat(E if case['label'] == 'E' else M, 3, axis=1)
        ids = [f'reference:{i:02d}' for i in range(3)]
    else:
        carry = load_array(inputs/'p5', case['source'], 'r06_isolated_2')
        original = json.loads((inputs/'p5'/case['source']/'result.json').read_text())
        ids = next(p['setup']['cell_ids'] for p in original['phases'] if p['phase'] == 'r06_isolated_2')
    if case['kind'] == 'rewrite':
        condition = case['condition']
        if condition == 'no_cue':
            exp.configure([1,3], ids, carry, case['algorithm'], 60, 0, isolated=True)
        else:
            cue = E if condition == 'E_sham' else M
            cue_ids = [f'cue:{i:02d}' for i in range(3)]
            exp.configure([2,3], ids+cue_ids, np.concatenate((carry, np.repeat(cue,3,axis=1)),axis=1),
                case['algorithm'], 60, 0 if condition == 'M_write_rna' else 1.25e-14,
                patch=[0,1,2], cut=condition == 'M_write_cut')
        contact, _ = exp.phase('writing_contact', 20000)
        exp.configure([1,3], ids, contact[:,:3], isolated=True)
        exp.phase('writing_isolated_1', 10000)
        carry, _ = exp.phase('writing_isolated_2', 10000)

    rounds = range(7,13) if case['kind'] == 'rewrite' else [7]
    for number in rounds:
        replay = case['kind'] == 'replay'
        prefix = f'r{number:02d}' if case['kind'] != 'assay' else 'onward'
        fresh = ([f'relay:07:{i:02d}' for i in range(3)] if replay else
                 [f'new:{i:02d}' for i in range(3)] if case['kind'] == 'assay' else
                 [f'rewrite:{number:02d}:{i:02d}' for i in range(3)])
        initial = np.concatenate((carry, np.repeat(M if replay else E,3,axis=1)),axis=1)
        condition = case.get('condition')
        exp.configure([2,3], ids+fresh, initial, 'hypol' if replay else 'depol',
            1 if replay else 60, 0 if condition == 'M_relay_rna' else 1.25e-14,
            patch=[0,1,2], cut=condition == 'M_relay_cut')
        contact, _ = exp.phase(prefix+'_contact', 20000)
        exp.configure([1,3], fresh, contact[:,3:], isolated=True)
        exp.phase(prefix+'_isolated_1', 10000)
        carry, _ = exp.phase(prefix+'_isolated_2', 10000)
        ids = fresh


def result_record(exp, case):
    return dict(case=case, ion_indices=exp.indices, phases=exp.records, execution_pass=True,
        parameter_retuning=False, outcome_dependent_selection=False, cell_division_simulated=False,
        artificial_target_schedule=False, external_handover_schedule=True,
        source_external_regional_intervention=True, midway_rewriting=case['kind']=='rewrite',
        historical_rounds=0 if case['kind']=='assay' else 6,
        newly_simulated_handover_rounds=6 if case['kind']=='rewrite' else 1,
        cue_cells_retained=False, stress_panel=False, return_to_E=False)


def worker(path):
    spec = json.loads(path.read_text()); d.validate_config(spec['config']); case = spec['case']
    if case not in d.fixed_cases() or Path(spec['inputs']) != path.parent.parent/'inputs':
        raise ValueError('Unregistered P6 worker or input path')
    exp = TopologyExperiment(path.parent, dict(id=case['id'], fine=case['fine']))
    trajectory(exp, case, Path(spec['inputs']))
    d.write_json(path.parent/'result.json', result_record(exp,case))
    return 0


def run_worker(case, config, run, deadline, env):
    record = dict(id=case['id'], execution_pass=False); remaining = deadline-time.monotonic()
    if remaining <= 0: return dict(record, status='not_launched_budget')
    if shutil.disk_usage(d.ROOT).free < 5*1024**3: return dict(record, status='not_launched_disk')
    folder = run/case['id']; folder.mkdir()
    d.write_json(folder/'spec.json',dict(case=case,config=config,inputs=str(run/'inputs')))
    start = time.monotonic(); print('Starting '+case['id'],flush=True)
    with (folder/'stdout.log').open('x') as log:
        try:
            proc = subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--worker',str(folder/'spec.json')],
                cwd=folder,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                timeout=min(remaining,config['worker_timeout_seconds']))
            record.update(status='finished',returncode=proc.returncode)
        except subprocess.TimeoutExpired:
            record.update(status='timeout',returncode=None)
    record['elapsed_seconds'] = time.monotonic()-start
    if (folder/'result.json').exists():
        result = json.loads((folder/'result.json').read_text()); record['result'] = result
        record['result_sha256'] = d.digest(folder/'result.json')
        record['execution_pass'] = record['returncode']==0 and result['execution_pass']
    print(f"{case['id']}: {'VALID' if record['execution_pass'] else 'INVALID'} ({record['elapsed_seconds']:.1f}s)",flush=True)
    return record


def freeze(run):
    hashes = d.execution_manifest(); (run/'frozen').mkdir(); frozen = {}
    for path in d.LOCAL_FILES:
        if path.name in frozen: raise ValueError('Frozen filename collision')
        shutil.copyfile(path,run/'frozen'/path.name); frozen[path.name]=hashes[str(path.relative_to(d.ROOT))]
        if d.digest(run/'frozen'/path.name)!=frozen[path.name]: raise RuntimeError('Changed source during freeze')
    inputs = {}
    for name,source in d.input_paths().items():
        target=run/'inputs'/name; target.parent.mkdir(parents=True,exist_ok=True)
        before=d.digest(source); shutil.copyfile(source,target)
        if not before==d.digest(source)==d.digest(target): raise RuntimeError('Changed input during freeze')
        inputs[name]=dict(source=str(source),sha256=before)
    return hashes,frozen,inputs


def predecessor_gate(run):
    from analyze_paper_relay import analyze
    result=analyze(d.PREDECESSOR)
    saved=json.loads((run/'inputs/p5/independent_audit.json').read_text())
    return result==saved and result['quality_gate'] and result['independent_check_count']==42065 and result['native_integrations']==804


def run(config_path):
    from analyze_paper_rewrite import gate_audit,integrity
    config=d.validate_config(json.loads(config_path.read_text())); d.source_check()
    if shutil.disk_usage(d.ROOT).free<5*1024**3: raise RuntimeError('Require 5 GiB free')
    began=time.monotonic(); deadline=began+config['total_budget_seconds']
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_dir=Path(tempfile.mkdtemp(prefix=f'paper-rewrite-{stamp}-',dir=d.ROOT/'runs'))
    hashes,frozen,inputs=freeze(run_dir); cases=d.fixed_cases()
    summary=dict(started_utc=stamp,revision=d.REVISION,config=config,registered_cases=cases,cases=[],
        hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,python=sys.version,
        packages={n:importlib.metadata.version(n) for n in ('numpy','scipy','matplotlib')},
        predecessor_gate=False,gate=None,stage='preflight')
    d.write_json(run_dir/'summary.json',summary); print(f'Run artifacts: {run_dir}',flush=True)
    summary['predecessor_gate']=predecessor_gate(run_dir); d.write_json(run_dir/'summary.json',summary)
    if not summary['predecessor_gate']: raise RuntimeError('P5 re-audit fails; no P6 native integration permitted')
    env=os.environ.copy(); env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',MPLBACKEND='Agg',
        MPLCONFIGDIR=str(d.ROOT/'.cache/matplotlib'),XDG_CACHE_HOME=str(d.ROOT/'.cache'),
        OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
    for stage,selected in (('round_seven_replays',cases[:2]),('capacity_diagnostics',cases[2:6]),('rewrite_panel',cases[6:])):
        summary['stage']=stage; d.write_json(run_dir/'summary.json',summary)
        with ThreadPoolExecutor(max_workers=2) as pool:
            tasks=[pool.submit(run_worker,c,config,run_dir,deadline,env) for c in selected]
            for task in as_completed(tasks):
                summary['cases'].append(task.result()); d.write_json(run_dir/'summary.json',summary)
        if stage=='round_seven_replays':
            gate=gate_audit(run_dir); d.write_json(run_dir/'gate.json',gate)
            summary.update(gate=gate,gate_sha256=d.digest(run_dir/'gate.json')); d.write_json(run_dir/'summary.json',summary)
            if not gate['quality_gate']: summary['stopped_after_gate']=True; break
        if not all(next(r for r in summary['cases'] if r['id']==c['id'])['execution_pass'] for c in selected):
            summary['stopped_after_stage']=stage; break
    d.source_check(); summary['integrity']=integrity(run_dir,summary)
    summary.update(elapsed_seconds=time.monotonic()-began,stage='finished',all_execution_valid=(
        len(summary['cases'])==62 and all(c['execution_pass'] for c in summary['cases']) and
        all(summary['integrity'].values()) and bool((summary.get('gate') or {}).get('quality_gate'))))
    d.write_json(run_dir/'summary.json',summary); print(f'Summary: {run_dir / "summary.json"}',flush=True)
    return 0 if summary['all_execution_valid'] else 1


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--worker',type=Path)
    p.add_argument('--config',type=Path,default=d.ROOT/'configs/paper_rewrite_v1.json'); args=p.parse_args()
    return worker(args.worker.resolve()) if args.worker else run(args.config.resolve())


if __name__=='__main__': raise SystemExit(main())
