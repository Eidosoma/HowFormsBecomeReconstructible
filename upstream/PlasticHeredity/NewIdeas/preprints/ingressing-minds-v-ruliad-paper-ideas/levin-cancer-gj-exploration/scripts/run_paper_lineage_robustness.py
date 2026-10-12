"""P12: registered stress screens, held-out editable lineages, matched controls."""
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
import paper_lineage_robustness_design as d
from run_paper_contact_clock_recovery import ClockBoundedExperiment
from run_paper_staged_relay import phase
from run_paper_sheet import load_array
import paper_bounded_clock as clock

def stock(run,fine):
    case='stock'+('__fine' if fine else '')
    x=load_array(run/'inputs/p11',case,'preparation')
    return x[:,168:169],x[:,1:2]

def retention(exp,prefix):
    result={}
    for label in ('E','M'):
        masks=[]
        for part in ('isolated_1','isolated_2'):
            with np.load(exp.folder/(prefix+part+'.npz'),allow_pickle=False) as x:
                samples=x['concentrations'][x['times']>=7500]
                if len(samples)!=26: raise ValueError('Incomplete retention window')
                masks.append(np.array([exp.z.GRN.state_char(x['final'][:,i])==label and
                    np.mean([exp.z.GRN.state_char(row[:,i])==label for row in samples])>=.95 for i in range(3)]))
        result[label]=(masks[0]&masks[1]).tolist()
    return result

def writing(exp,c,targets,ids,E,M,prefix,mode,desired,base):
    nocue=mode in ('none','age')
    if nocue:
        exp.configure([1,3],ids,targets,'depol',1 if mode=='age' else 60,0,isolated=True)
    else:
        cues=[d.stem(c)+f':{prefix}:cue:{i:02d}' for i in range(6)]
        cue=E if mode=='E' else M
        exp.configure([3,3],cues+ids,np.concatenate((np.repeat(cue,6,axis=1),targets),axis=1),
                      'depol',60,1.25e-14,patch=list(range(6)))
    contact=phase(exp,prefix+'contact',20000,base)
    exp.configure([1,3],ids,contact if nocue else contact[:,6:],isolated=True)
    phase(exp,prefix+'isolated_1',10000,base+20000)
    held=phase(exp,prefix+'isolated_2',10000,base+30000)
    masks=retention(exp,prefix)
    return held,dict(name=prefix,desired=desired,retained_E=masks['E'],retained_M=masks['M'],
                     qualified=all(masks[desired]))

def relay(exp,c,carry,ids,recipient,timing,protein,number,desired,route,base):
    prefix=f'r{number:02d}_'; fresh=d.pupil_ids(c,number)
    pupils=d.recipient(recipient,c['seed'],f'r{number:02d}',protein)
    exp.configure_graph(ids+fresh,np.concatenate((carry,pupils),axis=1),route)
    initial=''.join(exp.z.GRN.state_char(x) for x in pupils.T)
    presignal=[None]*3
    for slot,(start,end,active) in enumerate(d.intervals(c['seed'],number,timing),1):
        for i in active:
            if presignal[i] is None: presignal[i]=exp.z.GRN.state_char(exp.sim.cc_cells[:,3+i])
        exp.set_active(active)
        contact=phase(exp,prefix+f'segment_{slot:02d}',end-start,base+start)
    exp.configure([1,3],fresh,contact[:,3:],isolated=True)
    phase(exp,prefix+'isolated_1',10000,base+80000)
    held=phase(exp,prefix+'isolated_2',10000,base+90000)
    masks=retention(exp,prefix); opposite='E' if desired=='M' else 'M'
    return held,fresh,dict(round=number,desired=desired,retained_E=masks['E'],retained_M=masks['M'],
        initial_labels=initial,presignal_labels=''.join(presignal),
        complete=all(masks[desired]) and initial==opposite*3 and presignal==[opposite]*3,
        negative=all(masks[opposite]),logical_end=base+100000)

def control_source(c,run):
    parent=d.parent(c); folder=run/parent['id']
    out=json.loads((folder/'result.json').read_text())['outcome']; kind=c['route']
    if kind.startswith('before'):
        return parent['id'],'founder_isolated_2',d.founder_ids(parent),out['founder']['qualified']
    if kind.startswith('after'):
        return parent['id'],'rewrite_isolated_2',d.pupil_ids(parent,3),bool(out['rewrite'] and out['rewrite']['qualified'])
    return parent['id'],'r03_isolated_2',d.pupil_ids(parent,3),out['before_complete']

def trajectory(exp,c,run,selection):
    E,M=stock(run,c['fine']); timing,protein=d.levels(c,selection); rounds=[]
    if c['stage'] in ('baseline','timing','cells'):
        source,source_phase,ids=d.archived_source(c); carry=load_array(run/'inputs/p11',source,source_phase)
        _,_,row=relay(exp,c,carry,ids,E if c['label']=='M' else M,timing,protein,1,c['label'],c['route'],0)
        return dict(available=True,rounds=[row],complete=row['complete'],negative=row['negative'])
    if c['stage']=='controls':
        kind=c['route']
        if kind=='founder_none':
            targets=d.recipient(E,c['seed'],'founder',protein)
            _,writer=writing(exp,c,targets,d.founder_ids(c),E,M,'founder_','none','E',0)
            return dict(available=True,rounds=[],writer=writer,negative=all(writer['retained_E']))
        source,name,ids,available=control_source(c,run)
        if not available: return dict(available=False,rounds=[],negative=False,skip_reason='parent_prefix_unavailable')
        carry=load_array(run,source,name)
        if kind.startswith(('before','after')):
            before=kind.startswith('before'); number=1 if before else 4; desired='M' if before else 'E'
            _,_,row=relay(exp,c,carry,ids,E if before else M,timing,protein,number,desired,
                          kind.rsplit('_',1)[-1],40000 if before else 380000)
            return dict(available=True,rounds=[row],negative=row['negative'])
        _,writer=writing(exp,c,carry,ids,E,M,'rewrite_','M' if kind=='rewrite_sham' else 'none','E',340000)
        return dict(available=True,rounds=[],writer=writer,negative=all(writer['retained_M']))
    # Full new chain, including new writing/aging rather than archived dynamic founders.
    ids=d.founder_ids(c)
    initial=d.recipient(E if c['history']=='written' else M,c['seed'],'founder',protein)
    carry,founder=writing(exp,c,initial,ids,E,M,'founder_','M' if c['history']=='written' else 'age','M',0)
    out=dict(available=True,founder=founder,rewrite=None,rounds=rounds,before_complete=False,
             complete=False,stop_reason='founder_not_M')
    def save():
        d.write_json(exp.folder/'relay_progress.json',dict(case=c,rounds=rounds,outcome=out))
    save()
    if not founder['qualified']: return out
    for number in range(1,4):
        carry,ids,row=relay(exp,c,carry,ids,E,timing,protein,number,'M','open',40000+(number-1)*100000)
        rounds.append(row); out['stop_reason']=f'before_round_{number}_incomplete'; save()
        if not row['complete']: return out
    out['before_complete']=True
    carry,writer=writing(exp,c,carry,ids,E,M,'rewrite_','E','E',340000)
    out.update(rewrite=writer,stop_reason='rewrite_not_E'); save()
    if not writer['qualified']: return out
    for number in range(4,7):
        carry,ids,row=relay(exp,c,carry,ids,M,timing,protein,number,'E','open',380000+(number-4)*100000)
        rounds.append(row); out['stop_reason']=f'after_round_{number}_incomplete'; save()
        if not row['complete']: return out
    out.update(complete=True,stop_reason='six_handover_chain_complete'); save()
    return out

def result_record(exp,c,outcome,selection):
    if outcome['available']:
        indices=exp.indices
    else:
        if exp.records: raise ValueError('Unavailable control unexpectedly ran phases')
        indices=None  # No cell system was configured for a structural skip.
    return dict(case=c,ion_indices=indices,phases=exp.records,outcome=outcome,selection=dict(selection),
        execution_pass=True,clock_method=clock.METHOD,external_schedule=True,all_cells_evolve=True,
        only_new_cells_perturbed=True,shared_audited_stock=True,
        initial_writing_resimulated=c['stage']=='combined',independent_biological_replicates=False,
        fine_is_independent_trial=False,autonomous_reproduction=False,parameter_retuning=False,
        outcome_dependent_cell_selection=False,carrier_reset=False,automatic_follow_on=False)

def worker(path):
    spec=json.loads(path.read_text()); d.validate_config(spec['config']); c=spec['case']; run=path.parent.parent
    if c not in d.fixed_cases() or Path(spec['inputs'])!=run/'inputs': raise ValueError('Unregistered P12 worker')
    summary=json.loads((run/'summary.json').read_text())
    if summary['stage']!=c['stage']: raise ValueError('Wrong authorized stage')
    for stage in d.STAGES[:d.STAGES.index(c['stage'])]:
        gate=summary['gates'].get(stage,{})
        gate_path=run/(stage+'_audit.json')
        if (not gate.get('quality_gate') or d.digest(gate_path)!=summary['gate_hashes'].get(stage)
            or json.loads(gate_path.read_text())!=gate):
            raise ValueError('Earlier technical gate did not pass')
        if stage=='baseline' and not gate.get('eligible'): raise ValueError('Baseline not qualified')
    selection=summary['selection']
    expected={mode:summary['gates'][mode]['selected'] for mode in ('timing','cells')
              if d.STAGES.index(mode)<d.STAGES.index(c['stage'])}
    if selection!=expected: raise ValueError('Selection differs from audited screening decisions')
    if c['stage'] in ('combined','controls') and any(selection.get(x) not in d.LEVELS for x in ('timing','cells')):
        raise ValueError('No registered qualifying challenge')
    if json.loads((run/'frozen/paper_lineage_robustness_draws_v1.json').read_text())!=d.draw_book():
        raise ValueError('Random draws changed')
    exp=ClockBoundedExperiment(path.parent,dict(id=c['id'],fine=c['fine']))
    out=trajectory(exp,c,run,selection)
    d.write_json(path.parent/'result.json',result_record(exp,c,out,selection)); return 0


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
    from analyze_paper_editable_lineage import analyze
    original=analyze(d.PREDECESSOR)
    saved=json.loads((run/'inputs/p11/independent_audit.json').read_text())
    archived=analyze(run/'inputs/p11'); archived['run']=str(d.PREDECESSOR)
    good=original==archived==saved and original['quality_gate'] and original['independent_check_count']==27610
    return dict(quality_gate=bool(good),original_matches_saved=original==saved,archive_matches_saved=archived==saved,
        prior_checks=original['independent_check_count'],prior_cases=original['completed_cases'],
        prior_calls=original['integration_calls'],shared_stock_and_replay_sources=True)

def run(config_path):
    from analyze_paper_lineage_robustness import stage_audit,integrity
    config=d.validate_config(json.loads(config_path.read_text())); d.source_check()
    if json.loads((d.ROOT/'configs/paper_lineage_robustness_draws_v1.json').read_text())!=d.draw_book():
        raise ValueError('Unregistered draw book')
    if shutil.disk_usage(d.ROOT).free<5*1024**3: raise RuntimeError('Require 5 GiB free')
    began=time.monotonic(); deadline=began+config['total_budget_seconds']
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_dir=Path(tempfile.mkdtemp(prefix=f'paper-lineage-robustness-{stamp}-',dir=d.ROOT/'runs'))
    hashes,frozen,inputs=freeze(run_dir)
    summary=dict(started_utc=stamp,revision=d.REVISION,config=config,registered_cases=d.fixed_cases(),cases=[],
        hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,python=sys.version,
        packages={n:importlib.metadata.version(n) for n in ('numpy','scipy','matplotlib')},
        predecessor_gate=False,predecessor_audit=None,gates={},gate_hashes={},selection={},stage='preflight')
    d.write_json(run_dir/'summary.json',summary); print(f'Run artifacts: {run_dir}',flush=True)
    predecessor=predecessor_audit(run_dir); d.write_json(run_dir/'predecessor_audit.json',predecessor)
    summary.update(predecessor_audit=predecessor,predecessor_gate=predecessor['quality_gate'],
        predecessor_audit_sha256=d.digest(run_dir/'predecessor_audit.json'))
    d.write_json(run_dir/'summary.json',summary)
    if not predecessor['quality_gate']: raise RuntimeError('P11 re-audit failed; no new integration permitted')
    env=os.environ.copy(); env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',MPLBACKEND='Agg',
        MPLCONFIGDIR=str(d.ROOT/'.cache/matplotlib'),XDG_CACHE_HOME=str(d.ROOT/'.cache'),
        OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
    attempted=[]; valid=True
    for stage in d.STAGES:
        if stage=='combined' and any(summary['selection'].get(k) is None for k in ('timing','cells')):
            summary['completion_reason']='no_qualified_combined_challenge'; break
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
        if stage in ('timing','cells'): summary['selection'][stage]=gate['selected']
        d.write_json(run_dir/'summary.json',summary)
        if not gate['quality_gate']:
            valid=False; summary['completion_reason']='technical_gate_failure'; break
        if stage=='baseline' and not gate['eligible']:
            summary['completion_reason']='baseline_not_qualified'; break
        if stage=='controls': summary['completion_reason']='combined_and_controls_completed'
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
    p.add_argument('--config',type=Path,default=d.ROOT/'configs/paper_lineage_robustness_v1.json'); args=p.parse_args()
    return worker(args.worker.resolve()) if args.worker else run(args.config.resolve())

if __name__=='__main__': raise SystemExit(main())
