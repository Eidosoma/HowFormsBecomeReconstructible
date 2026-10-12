"""P10 common-graph schedule screen and bounded, actual-cell continuations."""
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
import paper_contact_schedule_design as d
import run_paper_m_calibration as p7
from run_paper_sheet import reference,load_array
from run_paper_topology import TopologyExperiment
from run_paper_staged_relay import phase,retained_M


class CommonGraphExperiment(TopologyExperiment):
    """Change construction only, then apply masks to native transport gates."""
    def configure(self,*args,**kwargs):
        self.common_graph=False
        return super().configure(*args,**kwargs)

    def configure_graph(self,ids,state,route):
        if len(ids)!=6 or state.shape!=(17,6) or route not in ('open','rna','cut'):
            raise ValueError('Invalid common graph setup')
        z,s=self.z,self.sim; original_build=z.setup_GJ_3D; original_install=z.GJs_3D_give_to_sim
        def count_edges(allow_diag):
            # No canonical lattice edges are asserted for this explicit graph.
            z.GJs_3D=[]
            return len(d.GRAPH)
        def install_edges():
            s.GJ_connects['from'][:]=[e[0] for e in d.GRAPH]
            s.GJ_connects['to'][:]=[e[1] for e in d.GRAPH]
        try:
            z.setup_GJ_3D=count_edges; z.GJs_3D_give_to_sim=install_edges
            super().configure([1,6],ids,state,'depol',60,0 if route=='rna' else 1.25e-14,
                              patch=[0,1,2],cut=route=='cut')
        finally:
            z.setup_GJ_3D=original_build; z.GJs_3D_give_to_sim=original_install
        self.common_graph=True; self.route=route
        self.set_active([])

    def set_active(self,active):
        if not self.common_graph or len(set(active))!=len(active) or any(i not in (0,1,2) for i in active):
            raise ValueError('Invalid active pupil mask')
        before=self.sim.cc_cells.copy(); self.active=list(active)
        self.edge_available[:]=[1.,1.]+[float(i in active and self.route!='cut') for i in range(3) for _ in range(2)]
        if not np.array_equal(before,self.sim.cc_cells): raise RuntimeError('Mask switch mutated cells')

    def phase(self,name,horizon,**kwargs):
        output=super().phase(name,horizon,**kwargs)
        if self.common_graph:
            self.records[-1]['setup'].update(grid_shape=None,storage_shape=[1,6],orthogonal_only=False,
                periodic=False,network_mode='explicit_common_graph',explicit_edges=[list(e) for e in d.GRAPH],
                scheduled_pupils=self.active,route=self.route)
        d.write_json(self.folder/'progress.json',self.records)
        return output


def stock_root(run):
    return run/'inputs/p9/inputs/p8/inputs/p7/inputs/p3'


def founder_state(case,run):
    if case['kind']=='continuation':
        prefix=d.make_case('screen',case['founder'],case['schedule'],'open',case['fine'])['id']
        return load_array(run,prefix,'r01_isolated_2'),[f'p10:pupil:01:{i:02d}' for i in range(3)]
    if case['founder']=='rewritten_restored_E':
        return load_array(run/'inputs/p9',d.LINEAGE,'r06_isolated_2'),[f'pupil:06:{i:02d}' for i in range(3)]
    E,M=reference(stock_root(run)); lab='E' if case['founder']=='ordinary_E_sham' else 'M'
    return np.repeat(E if lab=='E' else M,3,axis=1),[f'p10:founder:{lab}:{i:02d}' for i in range(3)]


def trajectory(exp,case,run):
    if case['kind']=='replay':
        p7.trajectory(exp,d.replay_source(case['layout']),run/'inputs/p9/inputs/p8/inputs/p7/inputs')
        return []
    E,_=reference(stock_root(run)); carry,ids=founder_state(case,run); rounds=[]
    numbers=range(2,7) if case['kind']=='continuation' else [1]
    window=20000 if case['kind']=='calibration' else 80000
    for number in numbers:
        prefix=f'r{number:02d}_'; base=(number-1)*100000
        fresh=[f'p10:pupil:{number:02d}:{i:02d}' for i in range(3)]
        exp.configure_graph(ids+fresh,np.concatenate((carry,np.repeat(E,3,axis=1)),axis=1),case['route'])
        for slot,(start,stop,active) in enumerate(d.segments(case['schedule']),1):
            exp.set_active(active)
            contact=phase(exp,prefix+f'segment_{slot:02d}',stop-start,base+start)
        exp.configure([1,3],fresh,contact[:,3:].copy(),isolated=True)
        phase(exp,prefix+'isolated_1',10000,base+window)
        carry=phase(exp,prefix+'isolated_2',10000,base+window+10000); ids=fresh
        mask=retained_M(exp,prefix)
        rounds.append(dict(round=number,retained_M=mask.tolist(),complete=bool(mask.all()),logical_end=base+window+20000))
        d.write_json(exp.folder/'relay_progress.json',dict(case=case,rounds=rounds,maximum_rounds=6,
            shared_screen_rounds=1 if case['kind']=='continuation' else 0))
        print('P10_ROUND '+json.dumps(rounds[-1]),flush=True)
        if not mask.all(): break
    return rounds


def result_record(exp,case,rounds):
    continuation=case['kind']=='continuation'
    return dict(case=case,ion_indices=exp.indices,phases=exp.records,rounds=rounds,execution_pass=True,
        stop_reason='historical_replay' if case['kind']=='replay' else 'single_round' if not continuation else
            'six_complete_rounds' if rounds[-1]['round']==6 and rounds[-1]['complete'] else 'first_incomplete_round',
        newly_simulated_rounds=len(rounds),shared_screen_rounds=int(continuation),
        external_schedule=True,all_cells_evolve=True,explicit_non_lattice_extension=case['kind']!='replay',
        teachers_retained_between_rounds=False,cell_division_simulated=False,parameter_retuning=False,
        outcome_dependent_cell_selection=False,cross_branch_pooling=False,extra_M_supplementation=False,
        screen_prefix_is_independent_replication=False,automatic_follow_on=False)


def worker(path):
    spec=json.loads(path.read_text()); d.validate_config(spec['config']); case=spec['case']; run=path.parent.parent
    allowed=d.fixed_cases()
    if case['kind']=='continuation':
        summary=json.loads((run/'summary.json').read_text()); choice=json.loads((run/'screen_audit.json').read_text())
        if not choice['quality_gate'] or summary['screen_audit']!=choice or d.digest(run/'screen_audit.json')!=summary['screen_audit_sha256']:
            raise ValueError('Unaudited continuation selection')
        allowed=d.continuation_cases(choice['selected'])
    if case not in allowed or Path(spec['inputs'])!=run/'inputs': raise ValueError('Unregistered P10 worker')
    exp=CommonGraphExperiment(path.parent,dict(id=case['id'],fine=case['fine']))
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
    from analyze_paper_contact_schedule import gate_audit,calibration_audit,screen_audit,integrity
    config=d.validate_config(json.loads(config_path.read_text())); d.source_check()
    if shutil.disk_usage(d.ROOT).free<5*1024**3: raise RuntimeError('Require 5 GiB free')
    began=time.monotonic(); deadline=began+config['total_budget_seconds']
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_dir=Path(tempfile.mkdtemp(prefix=f'paper-contact-schedule-{stamp}-',dir=d.ROOT/'runs'))
    hashes,frozen,inputs=freeze(run_dir); cases=d.fixed_cases()
    summary=dict(started_utc=stamp,revision=d.REVISION,config=config,registered_cases=cases,cases=[],
        hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,python=sys.version,
        packages={n:importlib.metadata.version(n) for n in ('numpy','scipy','matplotlib')},
        predecessor_gate=False,gate=None,calibration_audit=None,screen_audit=None,selected=[],stage='preflight')
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
    valid=batch('historical_replays',cases[:2])
    if valid: valid=audit('gate',gate_audit)['quality_gate']
    if valid: valid=batch('graph_calibration',cases[2:10])
    if valid:
        calibration=audit('calibration_audit',calibration_audit); valid=calibration['quality_gate']
        if valid and not calibration['eligible']: summary['completion_reason']='common_graph_not_qualified'
        elif valid:
            valid=batch('coarse_screen',cases[10:35])
            if valid: valid=batch('fine_screen',cases[35:60])
            if valid:
                screen=audit('screen_audit',screen_audit); valid=screen['quality_gate']
                if valid:
                    selected=screen['selected']; summary['selected']=selected
                    new_cases=d.continuation_cases(selected); summary['registered_cases']+=new_cases
                    d.write_json(run_dir/'summary.json',summary)
                    if new_cases: valid=batch('selected_continuations',new_cases)
                    summary['completion_reason']='selected_continuations_completed' if selected else 'no_eligible_schedule'
    d.source_check(); summary['integrity']=integrity(run_dir,summary)
    expected_count=10 if summary.get('completion_reason')=='common_graph_not_qualified' else 60+12*len(summary['selected'])
    summary.update(elapsed_seconds=time.monotonic()-began,stage='finished',all_execution_valid=bool(valid and
        len(summary['cases'])==expected_count and all(c['execution_pass'] for c in summary['cases']) and
        all(summary['integrity'].values())))
    d.write_json(run_dir/'summary.json',summary); print(f'Summary: {run_dir / "summary.json"}',flush=True)
    return 0 if summary['all_execution_valid'] else 1


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--worker',type=Path)
    p.add_argument('--config',type=Path,default=d.ROOT/'configs/paper_contact_schedule_v1.json'); args=p.parse_args()
    return worker(args.worker.resolve()) if args.worker else run(args.config.resolve())


if __name__=='__main__': raise SystemExit(main())
