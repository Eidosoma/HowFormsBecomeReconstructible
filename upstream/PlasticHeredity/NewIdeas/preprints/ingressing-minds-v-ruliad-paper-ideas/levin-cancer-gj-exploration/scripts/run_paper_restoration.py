"""P2: use actual P1-exposed cells for restoration, withdrawal and onward E."""
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

import paper_restoration_design as d
from run_paper_memory import PaperExperiment


class RestorationExperiment(PaperExperiment):
    def configure(self, ids, state, algorithm='depol', power=1, kd=0, oi=.5, isolated=False):
        # Rule changes are explicit interventions; the full concentration state is copied unchanged.
        self.case = dict(id=self.case['id'],fine=self.case['fine'],algorithm=algorithm,
                         power=power,mirna_blocked=(kd==0))
        self.build(ids,state,isolated=isolated)
        self.expression_gate.GJ_OiET = oi
        self.z.GRN.set_GJdiff(0 if isolated else kd)

    def phase(self, name, horizon, **kwargs):
        result = super().phase(name,horizon,**kwargs)
        self.records[-1]['setup']['tumor_rule']['GJ_OiET'] = self.expression_gate.GJ_OiET
        d.write_json(self.folder / 'progress.json',self.records)
        return result


def probe(exp, carriers, carrier_ids, M, *, replay=None):
    if replay is not None:
        ids = carrier_ids + [f'onward:{i:02d}' for i in range(14)]
        state = np.concatenate((carriers,np.repeat(M,14,axis=1)),axis=1)
        exp.configure(ids,state,replay['algorithm'],replay['power'],8.801117367933935e-16)
        endpoint,_ = exp.phase('onward_contact',20000)
        target, ids = endpoint[:,2:],ids[2:]
        exp.configure(ids,target,replay['algorithm'],replay['power'],isolated=True)
    else:
        ids = [carrier_ids[0],'probe:00',carrier_ids[1]]
        state = np.concatenate((carriers[:,:1],M,carriers[:,1:2]),axis=1)
        exp.configure(ids,state,'hypol',1,1.25e-14)
        endpoint,_ = exp.phase('onward_contact',20000)
        exp.configure(['probe:00'],endpoint[:,1:2],isolated=True)
    exp.phase('onward_isolated_1',10000)
    exp.phase('onward_isolated_2',10000)


def trajectory(exp, case, inputs):
    source = d.source_data(inputs,case['source'])
    if case['kind']=='replay':
        probe(exp,source['held'][:,:2],source['ids'][:2],source['E'],replay=source['result']['case'])
    elif case['kind']=='assay':
        probe(exp,np.repeat(source[case['label']],2,axis=1),['reference:00','reference:01'],source['M'])
    else:
        n = case['size']
        ids = source['ids'][:n]
        state = source['held'][:,:n].copy()
        if not case['alone']:
            state = np.concatenate((state,np.repeat(source['E'],25-n,axis=1)),axis=1)
            ids += [f'helper:{i:02d}' for i in range(25-n)]
        exp.configure(ids,state,case['algorithm'],case['power'],
            0 if case['mirna_blocked'] else case['kd'],case['oi'],case['alone'])
        contact,_ = exp.phase('restoration',20000)
        # Remove helpers AND treatment; actual evolved target state is retained.
        exp.configure(source['ids'][:n],contact[:,:n],isolated=True)
        exp.phase('isolated_1',10000)
        held,_ = exp.phase('isolated_2',10000)
        probe(exp,held[:,:2],source['ids'][:2],source['M'])


def worker(path):
    spec = json.loads(path.read_text())
    d.validate_config(spec['config'])
    case = spec['case']
    if case not in spec['config']['cases']:
        raise ValueError('Unregistered P2 worker')
    exp = RestorationExperiment(path.parent,dict(id=case['id'],fine=case['fine']))
    trajectory(exp,case,Path(spec['inputs']))
    d.write_json(path.parent / 'result.json',dict(case=case,ion_indices=exp.indices,phases=exp.records,
        execution_pass=True,parameter_retuning=False,outcome_dependent_selection=False,
        cell_division_simulated=False,artificial_target_schedule=False))
    return 0


def run_worker(case, config, run, deadline, env):
    record = dict(id=case['id'],execution_pass=False)
    remaining = deadline-time.monotonic()
    if remaining<=0:
        return dict(record,status='not_launched_budget')
    if shutil.disk_usage(d.ROOT).free < 5*1024**3:
        return dict(record,status='not_launched_disk')
    folder = run / case['id']
    folder.mkdir()
    d.write_json(folder / 'spec.json',dict(case=case,config=config,inputs=str(run / 'inputs')))
    start = time.monotonic()
    print('Starting '+case['id'],flush=True)
    with (folder / 'stdout.log').open('x') as output:
        try:
            result = subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--worker',str(folder / 'spec.json')],
                cwd=folder,env=env,stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,
                timeout=min(remaining,config['worker_timeout_seconds']))
            record.update(status='finished',returncode=result.returncode)
        except subprocess.TimeoutExpired:
            record.update(status='timeout',returncode=None)
    record['elapsed_seconds'] = time.monotonic()-start
    if (folder / 'result.json').exists():
        record['result'] = json.loads((folder / 'result.json').read_text())
        record['execution_pass'] = record['returncode']==0 and record['result']['execution_pass']
    print(f"{case['id']}: {'VALID' if record['execution_pass'] else 'INVALID'} ({record['elapsed_seconds']:.1f}s)",flush=True)
    return record


def freeze(run):
    hashes = d.execution_manifest()
    (run / 'frozen').mkdir()
    frozen = {}
    for path in d.LOCAL_FILES:
        if path.name in frozen:
            raise ValueError('Frozen name collision')
        shutil.copyfile(path,run / 'frozen' / path.name)
        frozen[path.name] = hashes[str(path.relative_to(d.ROOT))]
        if d.digest(run / 'frozen' / path.name)!=frozen[path.name]:
            raise RuntimeError('Execution source changed while freezing')
    inputs = {}
    for name,source in d.input_paths().items():
        target = run / 'inputs' / name
        target.parent.mkdir(parents=True,exist_ok=True)
        before = d.digest(source)
        shutil.copyfile(source,target)
        if before!=d.digest(source) or before!=d.digest(target):
            raise RuntimeError('Source data changed while copying')
        inputs[name] = dict(source=str(source),sha256=before)
    return hashes,frozen,inputs


def run(config_path):
    from analyze_paper_memory import analyze as analyze_p1
    from analyze_paper_restoration import gate_audit, integrity
    config = d.validate_config(json.loads(config_path.read_text()))
    d.source_check()
    if shutil.disk_usage(d.ROOT).free<5*1024**3:
        raise RuntimeError('Require 5 GiB free')
    began = time.monotonic()
    deadline = began+config['total_budget_seconds']
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_dir = Path(tempfile.mkdtemp(prefix=f'paper-restoration-{stamp}-',dir=d.ROOT / 'runs'))
    hashes,frozen,inputs = freeze(run_dir)
    summary = dict(started_utc=stamp,revision=d.REVISION,config=config,cases=[],
        hashes_sha256=hashes,frozen_hashes_sha256=frozen,inputs=inputs,
        python=sys.version,packages={n:importlib.metadata.version(n) for n in ('numpy','scipy','matplotlib')},
        predecessor_gate=False,gate=None)
    d.write_json(run_dir / 'summary.json',summary)
    print(f'Run artifacts: {run_dir}',flush=True)
    # Pure read-only re-audit: no old run, array, code or audit is overwritten.
    pre = analyze_p1(d.PREDECESSOR)
    stored = json.loads((run_dir / 'inputs/independent_audit.json').read_text())
    summary['predecessor_gate'] = pre==stored and pre['quality_gate'] and pre['native_integrations']==372
    summary['predecessor_checks'] = pre['independent_check_count']
    d.write_json(run_dir / 'summary.json',summary)
    if not summary['predecessor_gate']:
        raise RuntimeError('P1 re-audit differs or fails; no P2 integration permitted')
    env = os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',MPLBACKEND='Agg',
        MPLCONFIGDIR=str(d.ROOT / '.cache/matplotlib'),XDG_CACHE_HOME=str(d.ROOT / '.cache'),
        OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
    for stage,cases in enumerate((config['cases'][:6],config['cases'][6:])):
        with ThreadPoolExecutor(max_workers=2) as pool:
            tasks=[pool.submit(run_worker,c,config,run_dir,deadline,env) for c in cases]
            for task in as_completed(tasks):
                summary['cases'].append(task.result())
                d.write_json(run_dir / 'summary.json',summary)
        if stage==0:
            gate = gate_audit(run_dir)
            d.write_json(run_dir / 'gate.json',gate)
            summary.update(gate=gate,gate_sha256=d.digest(run_dir / 'gate.json'))
            d.write_json(run_dir / 'summary.json',summary)
            if not gate['quality_gate']:
                summary['stopped_after_gate'] = True
                break
    d.source_check()
    summary.update(elapsed_seconds=time.monotonic()-began,all_execution_valid=(
        len(summary['cases'])==48 and all(c['execution_pass'] for c in summary['cases'])
        and summary['predecessor_gate'] and bool((summary.get('gate') or {}).get('quality_gate'))))
    summary['integrity'] = integrity(run_dir,summary)
    summary['all_execution_valid'] &= all(summary['integrity'].values())
    d.write_json(run_dir / 'summary.json',summary)
    print(f'Summary: {run_dir / "summary.json"}',flush=True)
    return 0 if summary['all_execution_valid'] else 1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--worker',type=Path)
    p.add_argument('--config',type=Path,default=d.ROOT / 'configs/paper_restoration_v1.json')
    args = p.parse_args()
    return worker(args.worker.resolve()) if args.worker else run(args.config.resolve())


if __name__=='__main__':
    raise SystemExit(main())
