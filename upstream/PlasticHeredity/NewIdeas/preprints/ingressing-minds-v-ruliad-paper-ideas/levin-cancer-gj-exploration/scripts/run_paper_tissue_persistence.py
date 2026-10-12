"""P14: live mixed-tissue intervention, withdrawal and controlled turnover."""
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
import paper_tissue_persistence_design as d
from run_paper_contact_clock_recovery import ClockBoundedExperiment
from run_paper_staged_relay import phase
from run_paper_sheet import load_array
import paper_bounded_clock as clock

def stock(run,fine):
    x=load_array(run/'inputs/p13/inputs/p12/inputs/p11','stock'+('__fine' if fine else ''),'preparation')
    return x[:,168:169],x[:,1:2]

def observe(exp,name,patch,tissue=True):
    with np.load(exp.folder/(name+'.npz'),allow_pickle=False) as a:
        final=a['final']; samples=a['concentrations']; times=a['times']
        lab=lambda x:np.array([exp.z.GRN.state_char(col) for col in x.T])
        end=lab(final); sampled=np.array([lab(x) for x in samples])
        late=sampled[times>=.75*times[-1]]
        masks={key:((end[list(patch)]==key)&(np.mean(late[:,list(patch)]==key,axis=0)>=.95)).tolist()
               for key in ('E','M')}
        value=dict(patch_labels=''.join(end[list(patch)]),stable_E=masks['E'],stable_M=masks['M'])
        if tissue:
            value.update(background_E_now_M=int(np.sum(end[list(d.BACKGROUND_E)]=='M')),
                maximum_background_E_now_M=int(np.max(np.sum(sampled[:,list(d.BACKGROUND_E)]=='M',axis=1))),
                competitor_labels=''.join(end[list(d.COMPETITORS)]))
        return value

def trajectory(exp,c,run):
    E,M=stock(run,c['fine']); src,name,carrier_ids=d.source(c); base=d.logical_base(c)
    carriers=np.repeat(M,3,axis=1) if src is None else load_array(run/'inputs/p13',src,name)
    if ''.join(exp.z.GRN.state_char(x) for x in carriers.T)!='MMM': raise ValueError('Source trio not M')
    ids=d.tissue_ids(c,carrier_ids); value=np.repeat(E,169,axis=1)
    value[:,list(d.COMPETITORS)]=np.repeat(M,9,axis=1)
    value[:,list(d.PATCH)]=carriers
    observed={}; replacements=[]
    def take(name,span,start,tissue=True):
        x=phase(exp,name,span,base+start)
        observed[name]=observe(exp,name,d.PATCH if tissue else range(3),tissue)
        d.write_json(exp.folder/'tissue_progress.json',dict(case=c,observations=observed,replacements=replacements))
        return x
    def configure_tissue(state,settings):
        exp.configure([13,13],ids,state,'depol',60,settings['kd'],patch=list(d.PATCH),
                      internal=settings['internal'],boundary=settings['boundary'],cut=settings['cut'])
    configure_tissue(value,d.treatment(c))
    value=take('intervention',20000,0)
    baseline=dict(internal=60,boundary=1,kd=1.25e-14,cut=False)
    configure_tissue(value,baseline)
    value=take('withdrawal_1',10000,20000)
    value=take('withdrawal_2',10000,30000)
    for i,position in enumerate(d.PATCH):
        fresh=d.incoming(M,i); initial=exp.z.GRN.state_char(fresh[:,0])
        if initial!='M': raise ValueError('Replacement is not initially M')
        old_id=ids[position]; ids[position]=d.new_id(c,i)
        value=value.copy(); value[:,position:position+1]=fresh
        configure_tissue(value,baseline)
        value=take('replacement_'+str(i+1),20000,40000+i*20000)
        replacements.append(dict(position=position,removed=old_id,inserted=ids[position],initial_label=initial,
            stable_E=observed['replacement_'+str(i+1)]['stable_E']))
    exp.configure([1,3],[ids[p] for p in d.PATCH],value[:,list(d.PATCH)],isolated=True)
    take('isolated_1',10000,100000,False)
    take('isolated_2',10000,110000,False)
    corrected=observed['intervention']['patch_labels']=='EEE'
    persistent=all(all(observed[n]['stable_E']) for n in ('withdrawal_1','withdrawal_2'))
    replaced=all(all(row['stable_E']) for row in replacements)
    isolated=all(all(observed[n]['stable_E']) for n in ('isolated_1','isolated_2'))
    out=dict(available=True,observations=observed,replacements=replacements,
        corrected_at_intervention_end=corrected,persistent_after_withdrawal=persistent,
        lost_stable_correction=corrected and not persistent,
        M_return_after_withdrawal=corrected and 'M' in observed['withdrawal_2']['patch_labels'],
        all_replacements_corrected=replaced,isolated_E_memory=isolated,
        tissue_correction=persistent and replaced and isolated,logical_end=base+120000)
    d.write_json(exp.folder/'tissue_progress.json',dict(case=c,observations=observed,replacements=replacements,outcome=out))
    return out

def result_record(exp,c,outcome):
    return dict(case=c,ion_indices=exp.indices,phases=exp.records,outcome=outcome,execution_pass=True,
        clock_method=clock.METHOD,external_schedule=True,all_cells_evolve=True,
        actual_P13_descendants=c['history']!='fresh_M',historical_rounds=0 if c['history']=='fresh_M' else 9,
        only_new_cells_perturbed=True,shared_audited_stock=True,benchmark_prior_age_matched=False,
        autonomous_reproduction=False,parameter_retuning=False,outcome_dependent_cell_selection=False,
        carrier_reset=False,cross_branch_pooling=False,intervention_retained=False,
        cell_division_simulated=False,new_isolated_PH_handover=False,exact_paper_replication=False,
        independent_biological_replicates=False,automatic_follow_on=False)

def worker(path):
    spec=json.loads(path.read_text()); d.validate_config(spec['config']); c=spec['case']; run=path.parent.parent
    if c not in d.fixed_cases() or Path(spec['inputs'])!=run/'inputs': raise ValueError('Unregistered P14 worker')
    summary=json.loads((run/'summary.json').read_text())
    if summary['stage']!=c['stage']: raise ValueError('Wrong authorized stage')
    h=summary.get('predecessor_audit',{}); hp=run/'predecessor_audit.json'
    if (not summary.get('predecessor_gate') or not h.get('quality_gate') or
        json.loads(hp.read_text())!=h or d.digest(hp)!=summary.get('predecessor_audit_sha256')):
        raise ValueError('P13 preflight not passed')
    if json.loads((run/'frozen/paper_tissue_persistence_draws_v1.json').read_text())!=d.draw_book():
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
    from analyze_paper_lineage_return import analyze
    original=analyze(d.PREDECESSOR)
    saved=json.loads((run/'inputs/p13/independent_audit.json').read_text())
    archived=analyze(run/'inputs/p13'); archived['run']=str(d.PREDECESSOR)
    good=original==archived==saved and original['quality_gate'] and original['independent_check_count']==63744
    return dict(quality_gate=bool(good),original_matches_saved=original==saved,archive_matches_saved=archived==saved,
        prior_checks=original['independent_check_count'],prior_cases=original['completed_cases'],
        prior_calls=original['integration_calls'],actual_round_nine_sources=True)

def run(config_path):
    from analyze_paper_tissue_persistence import stage_audit,integrity
    config=d.validate_config(json.loads(config_path.read_text())); d.source_check()
    if json.loads((d.ROOT/'configs/paper_tissue_persistence_draws_v1.json').read_text())!=d.draw_book():
        raise ValueError('Unregistered draw book')
    if shutil.disk_usage(d.ROOT).free<5*1024**3: raise RuntimeError('Require 5 GiB free')
    began=time.monotonic(); deadline=began+config['total_budget_seconds']
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_dir=Path(tempfile.mkdtemp(prefix=f'paper-tissue-persistence-{stamp}-',dir=d.ROOT/'runs'))
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
    if not predecessor['quality_gate']: raise RuntimeError('P13 re-audit failed; no new integration permitted')
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
        if stage=='panel': summary['completion_reason']='all_registered_stages_completed'
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
    p.add_argument('--config',type=Path,default=d.ROOT/'configs/paper_tissue_persistence_v1.json'); args=p.parse_args()
    return worker(args.worker.resolve()) if args.worker else run(args.config.resolve())

if __name__=='__main__': raise SystemExit(main())
