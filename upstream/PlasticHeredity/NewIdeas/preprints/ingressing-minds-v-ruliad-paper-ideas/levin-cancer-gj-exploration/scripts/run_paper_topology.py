"""P4 source-external regional expression assignments, paired location continuations."""
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
import paper_topology_design as d
from run_paper_sheet import SheetExperiment,load_array,reference


class TopologyExperiment(SheetExperiment):
    def configure(self,shape,ids,state,algorithm='depol',power=1,kd=0,isolated=False,
                  patch=(),internal=None,boundary=None,cut=False):
        super().configure(shape,ids,state,algorithm,power,kd,isolated)
        if len(set(patch))!=len(patch) or any(i<0 or i>=len(ids) for i in patch):
            raise ValueError('Invalid fixed patch identity map')
        internal=power if internal is None else internal; boundary=power if boundary is None else boundary
        mask=np.zeros(len(ids),dtype=bool); mask[list(patch)]=True
        fr,to=self.sim.GJ_connects['from'],self.sim.GJ_connects['to']
        self.regions=np.where(mask[fr]&mask[to],1,np.where(mask[fr]^mask[to],2,0)).astype(np.int8)
        self.edge_powers=np.choose(self.regions,[power,internal,boundary]).astype(float)
        self.edge_available=np.where((self.regions==2)&cut,0.,1.)
        self.compartments=dict(internal=internal,boundary=boundary,helper=power,boundary_cut=cut)
        gate=self.expression_gate; original=gate.func
        def regional(cc,vm,dv,t):
            scalar=gate.power
            try:
                gate.power=self.edge_powers
                return original(cc,vm,dv,t)*self.edge_available
            finally: gate.power=scalar
        gate.func=regional

    def diagnostics(self,state):
        value=super().diagnostics(state)
        value.update(edge_region=self.regions.copy(),edge_power=self.edge_powers.copy(),
                     edge_available=self.edge_available.copy())
        return value

    def phase(self,name,horizon,**kwargs):
        output=super().phase(name,horizon,**kwargs)
        self.records[-1]['setup']['compartment_expression']=dict(self.compartments)
        d.write_json(self.folder/'progress.json',self.records)
        return output


def source_ids(inputs,bank):
    info=json.loads((inputs/bank/'result.json').read_text())
    return next(p['setup']['cell_ids'] for p in info['phases'] if p['phase']=='acquired_isolated_2')


def probe(exp,carriers,ids,M,capacity=False):
    count=3 if capacity else 1; shape=[2,3] if capacity else [2,2]
    fresh=[f'new:{i:02d}' for i in range(3)] if capacity else ['probe:00']
    state=np.concatenate((carriers,np.repeat(M,count,axis=1)),axis=1)
    exp.configure(shape,ids+fresh,state,'hypol',1,1.25e-14,patch=[0,1,2])
    contact,_=exp.phase('onward_contact',20000)
    exp.configure([1,count],fresh,contact[:,3:],isolated=True)
    exp.phase('onward_isolated_1',10000); exp.phase('onward_isolated_2',10000)


def trajectory(exp,case,inputs):
    E,M=reference(inputs)
    if case['kind'] in ('assay','capacity'):
        if case['kind']=='assay' or case['label'].startswith('ordinary'):
            label=case['label'][-1]; state=np.repeat(E if label=='E' else M,3,axis=1)
            ids=['reference:00','reference:01','reference:02']
        else:
            state=load_array(inputs,case['source'],'isolated_2')[:,[0,1,3]]
            ids=[source_ids(inputs,'bank__depol__edge')[i] for i in (0,1,3)]
        probe(exp,state,ids,M,case['kind']=='capacity'); return
    n=case['side']; take=d.block(0,0,n,3)
    bankids=source_ids(inputs,case['bank']); ids=[bankids[i] for i in take]
    state=np.repeat(E,169,axis=1); positions=d.block(0 if case['location']=='edge' else 5,5,n)
    state[:,positions]=load_array(inputs,case['bank'],'acquired_isolated_2')[:,take]
    fieldids=[f'helper:r{r:02d}:c{c:02d}' for r in range(13) for c in range(13)]
    for index,name in zip(positions,ids): fieldids[index]=name
    exp.configure([13,13],fieldids,state,case['algorithm'],case['helper'],
        0 if case['kind']=='blocked' else 1.25e-14,patch=positions,
        internal=case['internal'],boundary=case['boundary'],cut=case['kind']=='cut')
    contact,_=exp.phase('restoration',20000)
    exp.configure([n,n],ids,contact[:,positions],isolated=True,patch=list(range(n*n)))
    exp.phase('isolated_1',10000); held,_=exp.phase('isolated_2',10000)
    fixed=[0,1,n]; probe(exp,held[:,fixed],[ids[i] for i in fixed],M)


def worker(path):
    spec=json.loads(path.read_text()); d.validate_config(spec['config']); case=spec['case']
    if case not in d.fixed_cases() or Path(spec['inputs'])!=path.parent.parent/'inputs':
        raise ValueError('Unregistered P4 worker')
    exp=TopologyExperiment(path.parent,dict(id=case['id'],fine=case['fine']))
    trajectory(exp,case,Path(spec['inputs']))
    d.write_json(path.parent/'result.json',dict(case=case,ion_indices=exp.indices,phases=exp.records,
        execution_pass=True,parameter_retuning=False,outcome_dependent_selection=False,
        cell_division_simulated=False,artificial_target_schedule=False,serial_relay_rounds=0,
        source_external_regional_intervention=True))
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
    from analyze_paper_sheet import analyze
    result=analyze(d.PREDECESSOR); saved=json.loads((run/'inputs/independent_audit.json').read_text())
    return result==saved and result['quality_gate'] and result['independent_check_count']==18941 and result['native_integrations']==465


def run(config_path):
    from analyze_paper_topology import gate_audit,integrity
    config=d.validate_config(json.loads(config_path.read_text())); d.source_check()
    if shutil.disk_usage(d.ROOT).free<5*1024**3: raise RuntimeError('Require 5 GiB free')
    began=time.monotonic(); deadline=began+config['total_budget_seconds']
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_dir=Path(tempfile.mkdtemp(prefix=f'paper-topology-{stamp}-',dir=d.ROOT/'runs'))
    hashes,frozen,inputs=freeze(run_dir); cases=d.fixed_cases()
    summary=dict(started_utc=stamp,revision=d.REVISION,config=config,registered_cases=cases,cases=[],
        hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,python=sys.version,
        packages={n:importlib.metadata.version(n) for n in ('numpy','scipy','matplotlib')},
        predecessor_gate=False,gate=None,stage='preflight')
    d.write_json(run_dir/'summary.json',summary); print(f'Run artifacts: {run_dir}',flush=True)
    summary['predecessor_gate']=predecessor_gate(run_dir); d.write_json(run_dir/'summary.json',summary)
    if not summary['predecessor_gate']: raise RuntimeError('P3 re-audit fails; no P4 native integration permitted')
    env=os.environ.copy(); env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',MPLBACKEND='Agg',
        MPLCONFIGDIR=str(d.ROOT/'.cache/matplotlib'),XDG_CACHE_HOME=str(d.ROOT/'.cache'),
        OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
    for stage,selected in (('source_replays',cases[:6]),('topology_panel',cases[6:])):
        summary['stage']=stage; d.write_json(run_dir/'summary.json',summary)
        with ThreadPoolExecutor(max_workers=2) as pool:
            tasks=[pool.submit(run_worker,c,config,run_dir,deadline,env) for c in selected]
            for task in as_completed(tasks):
                summary['cases'].append(task.result()); d.write_json(run_dir/'summary.json',summary)
        if stage=='source_replays':
            gate=gate_audit(run_dir); d.write_json(run_dir/'gate.json',gate)
            summary.update(gate=gate,gate_sha256=d.digest(run_dir/'gate.json')); d.write_json(run_dir/'summary.json',summary)
            if not gate['quality_gate']: summary['stopped_after_gate']=True; break
    d.source_check(); summary['integrity']=integrity(run_dir,summary)
    summary.update(elapsed_seconds=time.monotonic()-began,stage='finished',all_execution_valid=(
        len(summary['cases'])==146 and all(c['execution_pass'] for c in summary['cases']) and
        all(summary['integrity'].values()) and bool((summary.get('gate') or {}).get('quality_gate'))))
    d.write_json(run_dir/'summary.json',summary); print(f'Summary: {run_dir / "summary.json"}',flush=True)
    return 0 if summary['all_execution_valid'] else 1


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--worker',type=Path)
    p.add_argument('--config',type=Path,default=d.ROOT/'configs/paper_topology_v1.json'); args=p.parse_args()
    return worker(args.worker.resolve()) if args.worker else run(args.config.resolve())


if __name__=='__main__': raise SystemExit(main())
