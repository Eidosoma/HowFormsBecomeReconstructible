"""P11 staged editable-lineage experiment; no historical dynamic founder inputs."""
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
import paper_editable_lineage_design as d
import run_paper_sheet as p3
from run_paper_contact_clock_recovery import ClockBoundedExperiment
from run_paper_staged_relay import phase
import paper_bounded_clock as clock


def stock(run,fine):
    value=p3.load_array(run,d.case('stock',fine=fine)['id'],'preparation')
    return value[:,168:169],value[:,1:2]


def retained(exp,prefix,label):
    masks=[]
    for suffix in ('isolated_1','isolated_2'):
        with np.load(exp.folder/(prefix+suffix+'.npz'),allow_pickle=False) as a:
            late=a['concentrations'][a['times']>=7500]
            if len(late)!=26: raise ValueError('Missing regularly sampled retention window')
            end=np.array([exp.z.GRN.state_char(a['final'][:,i])==label for i in range(3)])
            frequency=np.mean([[exp.z.GRN.state_char(x[:,i])==label for i in range(3)] for x in late],axis=0)
            masks.append(end & (frequency>=.95))
    return masks[0] & masks[1]


def trajectory(exp,c,run):
    kind=c['kind']
    if kind=='stock':
        ids=[f'original:r{row:02d}:c{col:02d}' for row in range(13) for col in range(13)]
        exp.configure([13,13],ids,None,algorithm='depol')
        for row in range(4):
            for col in range(1,5): exp.z.GRN.set_very_tumor(exp.sim.cc_cells,row*13+col)
        exp.phase('preparation',1000,native_preparation=True)
        exp.records[-1]['logical_interval']=[0,1000]
        d.write_json(exp.folder/'progress.json',exp.records)
        return []
    E,M=stock(run,c['fine'])
    if kind in ('write_M','age_M','rewrite_E'):
        ids=d.target_ids(c)
        carry=(p3.load_array(run,d.source_case(c),d.source_phase(c)) if kind=='rewrite_E'
               else np.repeat(M if kind=='age_M' else E,3,axis=1))
        base=340000 if kind=='rewrite_E' else 0
        prefix='age_' if kind=='age_M' else 'writing_'
        cond=c['condition']; nocue=kind=='age_M' or cond=='no_cue'
        if nocue:
            exp.configure([1,3],ids,carry,'depol',1 if kind=='age_M' else 60,0,isolated=True)
        else:
            cue=E if cond.startswith('E') else M
            cues=[f'p11:{kind}:{c["history"]}:cue:{i:02d}' for i in range(6)]
            exp.configure([3,3],cues+ids,np.concatenate((np.repeat(cue,6,axis=1),carry),axis=1),
                'depol',60,0 if cond.endswith('_rna') else 1.25e-14,patch=list(range(6)),cut=cond.endswith('_cut'))
        contact=phase(exp,prefix+'contact',20000,base)
        exp.configure([1,3],ids,contact if nocue else contact[:,6:],isolated=True)
        phase(exp,prefix+'isolated_1',10000,base+20000)
        phase(exp,prefix+'isolated_2',10000,base+30000)
        return []
    if kind=='calibration_E':
        teacher=M if c['condition']=='M_sham' else E
        carry=np.repeat(teacher,3,axis=1); ids=[f'p11:calibration:teacher:{i:02d}' for i in range(3)]
        route=c['condition'].rsplit('_',1)[-1]; route=route if route in ('rna','cut') else 'open'
        numbers=range(1,2); base=0; desired='E'; recipient=M
    else:
        carry=p3.load_array(run,d.source_case(c),d.source_phase(c))
        if kind=='before':
            ids=d.founder_ids(c['history']); numbers=range(1,4); base=40000; desired='M'; recipient=E
        else:
            ids=d.pupil_ids(d.case('before',history=c['history']),3)
            numbers=range(4,7); base=380000; desired='E'; recipient=M
        route=c['route']
    rounds=[]; start_number=numbers.start
    for number in numbers:
        prefix=f'r{number:02d}_'; start=base+(number-start_number)*100000
        fresh=d.pupil_ids(c,number)
        exp.configure_graph(ids+fresh,np.concatenate((carry,np.repeat(recipient,3,axis=1)),axis=1),route)
        presignal=[]
        for i in range(4):
            active=[i] if i<3 else []
            if i<3: presignal.append(exp.z.GRN.state_char(exp.sim.cc_cells[:,3+i]))
            exp.set_active(active)
            contact=phase(exp,prefix+f'segment_{i+1:02d}',20000,start+20000*i)
        exp.configure([1,3],fresh,contact[:,3:],isolated=True)
        phase(exp,prefix+'isolated_1',10000,start+80000)
        carry=phase(exp,prefix+'isolated_2',10000,start+90000); ids=fresh
        mask=retained(exp,prefix,desired)
        rounds.append(dict(round=number,desired=desired,retained=mask.tolist(),complete=bool(mask.all()),
                           presignal_labels=''.join(presignal),logical_end=start+100000))
        d.write_json(exp.folder/'relay_progress.json',dict(case=c,rounds=rounds))
        if not mask.all(): break
    return rounds


def result_record(exp,c,rounds):
    relay=c['kind'] in ('calibration_E','before','after')
    stop=('complete_registered_rounds' if rounds and rounds[-1]['complete'] else 'first_incomplete_round') if relay else 'fixed_phase_complete'
    return dict(case=c,ion_indices=exp.indices,phases=exp.records,rounds=rounds,execution_pass=True,
        stop_reason=stop,clock_method=clock.METHOD,all_new_integrations_bounded=True,
        source_case=None if c['kind']=='stock' else d.source_case(c),
        source_phase=None if c['kind']=='stock' else d.source_phase(c),
        historical_endpoint_used_as_founder=False,external_schedule=True,all_cells_evolve=True,
        teachers_retained_between_rounds=False,cues_retained_after_writing=False,cell_division_simulated=False,
        parameter_retuning=False,outcome_dependent_cell_selection=False,cross_branch_pooling=False,
        extra_donor_supplementation=False,independent_random_replicates=False,automatic_follow_on=False)


def worker(path):
    spec=json.loads(path.read_text()); d.validate_config(spec['config']); c=spec['case']; run=path.parent.parent
    if c not in d.fixed_cases() or Path(spec['inputs'])!=run/'inputs': raise ValueError('Unregistered P11 worker')
    summary=json.loads((run/'summary.json').read_text())
    stage=next(s for s in d.STAGES if c in d.stage_cases(s))
    if summary['stage']!=stage: raise ValueError('Wrong authorized stage')
    for earlier in d.STAGES[:d.STAGES.index(stage)]:
        gate=summary['gates'].get(earlier,{})
        if not gate.get('quality_gate') or not gate.get('eligible') or (
            d.digest(run/(earlier+'_audit.json'))!=summary['gate_hashes'].get(earlier)):
            raise ValueError('Earlier stage has not qualified')
    exp=ClockBoundedExperiment(path.parent,dict(id=c['id'],fine=c['fine']))
    rounds=trajectory(exp,c,run)
    d.write_json(path.parent/'result.json',result_record(exp,c,rounds))
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
        if d.digest(run/'frozen'/path.name)!=frozen[path.name]: raise RuntimeError('Source changed during freeze')
    inputs={}
    for name,source in d.input_paths().items():
        target=run/'inputs'/name; target.parent.mkdir(parents=True,exist_ok=True)
        before=d.digest(source); shutil.copyfile(source,target)
        if not before==d.digest(source)==d.digest(target): raise RuntimeError('Input changed during freeze')
        inputs[name]=dict(source=str(source),sha256=before)
    return hashes,frozen,inputs



def predecessor_audit(run):
    from analyze_paper_contact_clock_recovery import analyze
    original=analyze(d.PREDECESSOR)
    saved=json.loads((run/'inputs/p10r/independent_audit.json').read_text())
    archived=analyze(run/'inputs/p10r'); archived['run']=str(d.PREDECESSOR)
    good=original==archived==saved and original['quality_gate'] and original['independent_check_count']==47340
    return dict(quality_gate=bool(good),original_matches_saved=original==saved,archive_matches_saved=archived==saved,
        prior_checks=original['independent_check_count'],prior_calls=original['native_integrations'],
        history_is_audit_input_only=True)


def run(config_path):
    from analyze_paper_editable_lineage import stage_audit,integrity
    config=d.validate_config(json.loads(config_path.read_text())); d.source_check()
    if shutil.disk_usage(d.ROOT).free<5*1024**3: raise RuntimeError('Require 5 GiB free')
    began=time.monotonic(); deadline=began+config['total_budget_seconds']
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_dir=Path(tempfile.mkdtemp(prefix=f'paper-editable-lineage-{stamp}-',dir=d.ROOT/'runs'))
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
    if not predecessor['quality_gate']: raise RuntimeError('P10R re-audit failed; no P11 integration permitted')
    env=os.environ.copy(); env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',MPLBACKEND='Agg',
        MPLCONFIGDIR=str(d.ROOT/'.cache/matplotlib'),XDG_CACHE_HOME=str(d.ROOT/'.cache'),
        OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
    valid=True; attempted=[]
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
        if not gate['eligible'] and stage!='after':
            summary['completion_reason']=stage+'_not_qualified'; break
        if stage=='after': summary['completion_reason']='after_completed'
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
    p.add_argument('--config',type=Path,default=d.ROOT/'configs/paper_editable_lineage_v1.json'); args=p.parse_args()
    return worker(args.worker.resolve()) if args.worker else run(args.config.resolve())


if __name__=='__main__': raise SystemExit(main())
