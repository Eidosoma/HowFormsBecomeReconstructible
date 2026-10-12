"""P3 native 2D acquisition, restoration and onward assay; no native edits."""
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
import paper_sheet_design as d
from run_paper_memory import PaperExperiment


class SheetExperiment(PaperExperiment):
    def configure(self, shape, ids, state=None, algorithm='depol', power=1, kd=0, isolated=False):
        rows,cols=shape
        if rows<1 or cols<1 or len(ids)!=rows*cols or len(set(ids))!=len(ids):
            raise ValueError('Invalid sheet dimensions or duplicated identity')
        self.case=dict(id=self.case['id'],fine=self.case['fine'],algorithm=algorithm)
        self.shape=list(shape); self.ids=list(ids); self.isolated=isolated
        z,s=self.z,self.sim
        z.setup_basic_network(self.p,0,1,rows,cols,allow_diag=False,do_gate=True)
        z.GRN.seed3D_inputs(z.cc3D)
        z.GRN.set_very_healthy_3D(z.cc3D,slice(None),slice(None),slice(None))
        self.voltage_gate=s.GJ_scale_gates[0]
        self.expression_gate,_,self.cell_gate=z.algorithm_on(algorithm,power,.5,1)
        if isolated and self.cell_gate is not None: self.cell_gate.neighbor=False
        z.GRN.set_GJdiff(0 if isolated else kd)
        if isolated: s.GJ_diffusion.fill(0)
        if state is not None:
            if state.shape!=s.cc_cells.shape: raise ValueError('Transfer shape mismatch')
            np.copyto(s.cc_cells,state)
            if not np.array_equal(s.cc_cells,state): raise RuntimeError('State edited on transfer')
        self.indices=dict(s.ion_i)

    def phase(self,name,horizon,**kwargs):
        if shutil.disk_usage(d.ROOT).free<5*1024**3: raise RuntimeError('Require 5 GiB free before phase')
        result=super().phase(name,horizon,**kwargs)
        self.records[-1]['setup'].update(grid_shape=self.shape,orthogonal_only=True,periodic=False,
            mirna_transport=dict(valence=self.z.GRN.miR200_valence,medium_size=self.z.GRN.miR200_is_medium_size))
        d.write_json(self.folder/'progress.json',self.records)
        return result


def load_array(run,case,phase,key='final'):
    with np.load(run/case/(phase+'.npz'),allow_pickle=False) as data: return data[key].copy()


def reference(run):
    state=load_array(run,'reference','preparation','concentrations')[-1]
    return state[:,168:169],state[:,1:2]


def probe(exp,carriers,ids,M):
    exp.configure([2,2],ids+['probe:00'],np.concatenate((carriers,M),axis=1),'hypol',1,1.25e-14)
    final,_=exp.phase('onward_contact',20000)
    exp.configure([1,1],['probe:00'],final[:,3:4],isolated=True)
    exp.phase('onward_isolated_1',10000)
    exp.phase('onward_isolated_2',10000)


def trajectory(exp,case,run):
    if case['kind'] in ('reference','bank'):
        history=case.get('history','depol'); location=case.get('location','edge')
        source,sample,_=d.origins(location); ids=d.original_ids()
        exp.configure([13,13],ids,algorithm=history)
        for i in d.block(*source,4): exp.z.GRN.set_very_tumor(exp.sim.cc_cells,i)
        _,prepared=exp.phase('preparation',1000,native_preparation=True)
        if case['kind']=='reference': return
        exp.configure([13,13],ids,prepared,history,60,0 if case['blocked'] else d.FIXED['acquisition_kd'])
        contact,_=exp.phase('acquisition',20000)
        take=d.block(*sample,3)
        exp.configure([3,3],[ids[i] for i in take],contact[:,take],isolated=True)
        exp.phase('acquired_isolated_1',10000)
        exp.phase('acquired_isolated_2',10000)
        return
    E,M=reference(run)
    if case['kind']=='assay':
        probe(exp,np.repeat(E if case['label']=='E' else M,3,axis=1),
            ['reference:00','reference:01','reference:02'],M)
        return
    n=case['side']; sample=d.block(0,0,n,3)
    allids=d.original_ids(); _,origin,destination=d.origins(case['location'])
    bank_ids=[allids[i] for i in d.block(*origin,3)]
    ids=[bank_ids[i] for i in sample]
    held=load_array(run,case['bank'],'acquired_isolated_2')[:,sample]
    if case['kind']=='alone':
        positions=list(range(n*n))
        exp.configure([n,n],ids,held,isolated=True)
    else:
        positions=d.block(*destination,n)
        state=np.repeat(E,169,axis=1); state[:,positions]=held
        field_ids=[f'helper:r{r:02d}:c{c:02d}' for r in range(13) for c in range(13)]
        for i,name in zip(positions,ids): field_ids[i]=name
        algo,power=d.STRATEGIES[case['strategy']]
        exp.configure([13,13],field_ids,state,algo,power,0 if case['kind']=='blocked' else 1.25e-14)
    contact,_=exp.phase('restoration',20000)
    exp.configure([n,n],ids,contact[:,positions],isolated=True)
    exp.phase('isolated_1',10000)
    retained,_=exp.phase('isolated_2',10000)
    fixed=[0,1,n]
    probe(exp,retained[:,fixed],[ids[i] for i in fixed],M)


def worker(path):
    spec=json.loads(path.read_text()); d.validate_config(spec['config']); case=spec['case']
    if case not in d.fixed_cases() or Path(spec['run'])!=path.parent.parent:
        raise ValueError('Unregistered worker or dependency location')
    if case['kind']=='benchmark':
        # Execute the unchanged historical worker, with the exact old case specification.
        import run_pilot
        pilot_spec=path.parent/'pilot-spec.json'
        d.write_json(pilot_spec,dict(case=d.PILOT_CASE,threshold_relative_tolerance=.02))
        return run_pilot.worker(pilot_spec)
    exp=SheetExperiment(path.parent,dict(id=case['id'],fine=case['fine']))
    trajectory(exp,case,Path(spec['run']))
    d.write_json(path.parent/'result.json',dict(case=case,ion_indices=exp.indices,phases=exp.records,
        execution_pass=True,parameter_retuning=False,outcome_dependent_selection=False,
        cell_division_simulated=False,artificial_target_schedule=False))
    return 0


def run_worker(case,config,run,deadline,env):
    record=dict(id=case['id'],execution_pass=False)
    remaining=deadline-time.monotonic()
    if remaining<=0: return dict(record,status='not_launched_budget')
    if shutil.disk_usage(d.ROOT).free<5*1024**3: return dict(record,status='not_launched_disk')
    folder=run/case['id']; folder.mkdir()
    d.write_json(folder/'spec.json',dict(case=case,config=config,run=str(run)))
    began=time.monotonic(); print('Starting '+case['id'],flush=True)
    with (folder/'stdout.log').open('x') as output:
        try:
            proc=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--worker',str(folder/'spec.json')],
                cwd=folder,env=env,stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,
                timeout=min(remaining,config['worker_timeout_seconds']))
            record.update(status='finished',returncode=proc.returncode)
        except subprocess.TimeoutExpired: record.update(status='timeout',returncode=None)
    record['elapsed_seconds']=time.monotonic()-began
    if (folder/'result.json').exists():
        result=json.loads((folder/'result.json').read_text()); record['result']=result
        record['result_sha256']=d.digest(folder/'result.json')
        record['execution_pass']=record['returncode']==0 and result.get('execution_pass',result.get('pass',False))
    print(f"{case['id']}: {'VALID' if record['execution_pass'] else 'INVALID'} ({record['elapsed_seconds']:.1f}s)",flush=True)
    return record


def freeze(run):
    hashes=d.execution_manifest(); (run/'frozen').mkdir(); frozen={}
    for path in d.LOCAL_FILES:
        if path.name in frozen: raise ValueError('Frozen name collision')
        shutil.copyfile(path,run/'frozen'/path.name)
        frozen[path.name]=hashes[str(path.relative_to(d.ROOT))]
        if d.digest(run/'frozen'/path.name)!=frozen[path.name]: raise RuntimeError('Execution changed during freeze')
    inputs={}
    for name,source in d.input_paths().items():
        target=run/'inputs'/name; target.parent.mkdir(parents=True,exist_ok=True)
        before=d.digest(source); shutil.copyfile(source,target)
        if not before==d.digest(source)==d.digest(target): raise RuntimeError('Input changed during freeze')
        inputs[name]=dict(source=str(source),sha256=before)
    return hashes,frozen,inputs


def predecessor_gate(run):
    from analyze_paper_restoration import analyze
    report=analyze(d.PREDECESSOR)
    stored=json.loads((run/'inputs/p2/independent_audit.json').read_text())
    return bool(report==stored and report['quality_gate'] and report['native_integrations']==270
                and report['independent_check_count']==10886)


def run(config_path):
    from analyze_paper_sheet import gate_audit, bank_gate, integrity
    config=d.validate_config(json.loads(config_path.read_text())); d.source_check()
    if shutil.disk_usage(d.ROOT).free<5*1024**3: raise RuntimeError('Require 5 GiB free')
    began=time.monotonic(); deadline=began+config['total_budget_seconds']
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_dir=Path(tempfile.mkdtemp(prefix=f'paper-sheet-{stamp}-',dir=d.ROOT/'runs'))
    hashes,frozen,inputs=freeze(run_dir); cases=d.fixed_cases()
    summary=dict(started_utc=stamp,revision=d.REVISION,config=config,registered_cases=cases,cases=[],
        hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,python=sys.version,
        packages={n:importlib.metadata.version(n) for n in ('numpy','scipy','matplotlib')},
        predecessor_gate=False,gate=None,bank_gate=None,stage='preflight')
    d.write_json(run_dir/'summary.json',summary); print(f'Run artifacts: {run_dir}',flush=True)
    summary['predecessor_gate']=predecessor_gate(run_dir)
    d.write_json(run_dir/'summary.json',summary)
    if not summary['predecessor_gate']: raise RuntimeError('P2 read-only re-audit fails; no native P3 permitted')
    env=os.environ.copy(); env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',MPLBACKEND='Agg',
        MPLCONFIGDIR=str(d.ROOT/'.cache/matplotlib'),XDG_CACHE_HOME=str(d.ROOT/'.cache'),
        OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
    stages=[('reference',cases[:1]),('source_and_assay_checks',cases[1:4]),
            ('acquisition_banks',cases[4:19]),('restoration_panel',cases[19:])]
    for stage,selected in stages:
        summary['stage']=stage; d.write_json(run_dir/'summary.json',summary)
        with ThreadPoolExecutor(max_workers=2) as pool:
            tasks=[pool.submit(run_worker,c,config,run_dir,deadline,env) for c in selected]
            for task in as_completed(tasks):
                summary['cases'].append(task.result()); d.write_json(run_dir/'summary.json',summary)
        if not all(next(r for r in summary['cases'] if r['id']==c['id'])['execution_pass'] for c in selected):
            summary['stopped_after_stage']=stage; break
        audit=None
        if stage=='source_and_assay_checks': audit=gate_audit(run_dir); key='gate'
        elif stage=='acquisition_banks': audit=bank_gate(run_dir); key='bank_gate'
        if audit is not None:
            d.write_json(run_dir/(key+'.json'),audit); summary[key]=audit
            summary[key+'_sha256']=d.digest(run_dir/(key+'.json')); d.write_json(run_dir/'summary.json',summary)
            if not audit['quality_gate']: summary['stopped_after_stage']=stage; break
    d.source_check(); summary['integrity']=integrity(run_dir,summary)
    summary.update(elapsed_seconds=time.monotonic()-began,stage='finished',all_execution_valid=(
        len(summary['cases'])==85 and all(c['execution_pass'] for c in summary['cases']) and
        all(summary['integrity'].values()) and bool((summary.get('gate') or {}).get('quality_gate')) and
        bool((summary.get('bank_gate') or {}).get('quality_gate'))))
    d.write_json(run_dir/'summary.json',summary); print(f'Summary: {run_dir / "summary.json"}',flush=True)
    return 0 if summary['all_execution_valid'] else 1


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--worker',type=Path)
    p.add_argument('--config',type=Path,default=d.ROOT/'configs/paper_sheet_v1.json'); args=p.parse_args()
    return worker(args.worker.resolve()) if args.worker else run(args.config.resolve())


if __name__=='__main__': raise SystemExit(main())
