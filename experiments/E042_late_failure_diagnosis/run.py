"""Frozen, append-only diagnosis of saved records, with independent verification."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
from common import cap_cpus,check_inputs,dump,finish,new_run,rng,sha,utc
from E015_functional_inheritance.audit import verify
from E042_late_failure_diagnosis import metrics as m,audit
import numpy as np


def inputs():
    return [ROOT/p for p in ('common.py','run_python.sh','E015_functional_inheritance/audit.py',
        'E032_renewal_failure_diagnosis/metrics.py','E032_renewal_failure_diagnosis/audit.py')]+[
        HERE/p for p in ('metrics.py','audit.py','run.py','tests.py','plot.py','PROTOCOL.md','SOURCE_DATA.json')]


def source_check():
    index=json.loads((HERE/'SOURCE_DATA.json').read_text())
    for rel,digest in index['sha256'].items():assert sha(ROOT/rel)==digest,rel
    for key in ('source_run','fixture_run'):
        path=ROOT/index[key];verify(path)
        a=json.loads((path/'INDEPENDENT_AUDIT.json').read_text())
        assert a['status']=='PASS' and a['complete_sha256']==sha(path/'COMPLETE.json')
    assert json.loads((ROOT/'E041_full_rewrite_confirmation/analysis/closeout_v1.json').read_text())['status']=='PASS'
    return index


def statistics(numerator,denominator,draws):
    n,d=np.asarray(numerator,float),np.asarray(denominator,float)
    nn,dd=n[draws].sum(axis=1),d[draws].sum(axis=1);valid=dd>0
    return dict(mean=float(n.sum()/d.sum()) if d.sum() else None,
        ci95=np.quantile(nn[valid]/dd[valid],[.025,.975]).tolist() if valid.any() else None,
        block_numerators=n.tolist(),block_denominators=d.tolist(),valid_bootstrap_draws=int(valid.sum()))


def summarize(data,ids):
    draws=rng('E042','bootstrap','late_failure').integers(0,len(ids),(10000,len(ids)))
    series={};definitions={}
    def add(kind,t,c,k,injury=None,denominator=None,subset=None,label=None):
        policies=m.ACTIVE if kind in ('body','transitions','joint') else m.GRAPH_CONDITIONS if kind=='graph' else range(11)
        h=m.HORIZONS[t] if kind in ('terminal','graph','terminal_transitions') else m.HORIZONS[t+1] if kind=='joint' else t if kind=='packet' else t+1
        key=f'{kind}.g{h}.{m.CONDITIONS[policies[c]]}.'+(m.DAMAGE[injury]+'.' if injury is not None else '')+(label or m.FIELDS[kind][k])
        values=data[kind][:,t,c]
        if injury is not None:values=values[:,:,:,injury]
        selected=np.ones(values.shape[:-1],bool)
        if subset:
            q=subset
            selected=data['terminal'][:,q['stage'],q['condition'],:,:,q['injury'],q['feature']].astype(bool)
            if q['invert']:selected=~selected
            key+='|'+m.DAMAGE[q['injury']]+'_'+('failure' if q['invert'] else m.OUTPUT_FIELDS[q['feature']])
        numerator=(values[...,k]*selected).sum(axis=(1,2))
        den=selected.sum(axis=(1,2)) if denominator is None else (values[...,denominator]*selected).sum(axis=(1,2))
        assert key not in series,key
        series[key]=statistics(numerator,den,draws)
        definitions[key]=dict(kind=kind,stage=t,condition=c,feature=k,injury=injury,denominator=denominator,subset=subset)
    for kind,values in data.items():
        stages=range(values.shape[1])
        if kind=='packet':stages=m.HORIZONS
        if kind=='repair':stages=[h-1 for h in m.HORIZONS[1:]]
        for t in stages:
            for c in range(values.shape[2]):
                for d in (range(3) if kind in ('terminal','graph','terminal_transitions') else (None,)):
                    for k in range(values.shape[-1]):add(kind,t,c,k,d)
                if kind=='repair':
                    for label,(num,den) in m.RATIOS.items():add(kind,t,c,num,denominator=den,label=label)
    for t,h in enumerate(m.HORIZONS[1:],1):
        for c in m.GRAPH_CONDITIONS:
            for injury in (0,1):
                for feature,invert in ((0,False),(0,True),(2,False)):
                    subset=dict(kind='terminal',stage=t,condition=c,injury=injury,feature=feature,invert=invert)
                    for k in (0,1,3,4,5,8,10,11,12):add('packet',h,c,k,subset=subset)
                    for k in range(4):add('graph',t,c,k,injury,subset=subset)
            subset=dict(kind='terminal',stage=t,condition=c,injury=1,feature=0,invert=True)
            for k in (1,3,4,5,6,7,8):add('joint',t-1,m.ACTIVE.index(c),k,subset=subset)
            # Restrict next-body witness to horizons with a saved subsequent body.
            add('joint',t-1,m.ACTIVE.index(c),9,denominator=10,label='next_body_success_given_scattered_failure')
    return series,definitions


def report(output,s):
    series=s['series']
    def value(key,percent=False):
        x=series[key];factor=100 if percent else 1
        return 'n/a' if x['mean'] is None else f"{factor*x['mean']:.3f} [{factor*x['ci95'][0]:.3f},{factor*x['ci95'][1]:.3f}]"
    lines=['# E042 — late failure diagnosis','','**'+s['status']+'**','',
        f"{len(s['blocks'])} reused E041 blocks; {s['lineages']} lineages. No new simulated trajectories or causal intervention.",'',
        'All intervals are exploratory, pointwise whole-block bootstrap intervals. Counts and conditional denominators are retained.','',
        '| Horizon | Policy | Scattered both correct % | Locked output % | Reversed % | Other failure % | Failure despite intact success % of scattered failures | Any other terminal success % of failures | Next body success % of failures with follow-up |',
        '| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for h in m.HORIZONS[1:]:
        for c in ('bridge_preserve','bridge_rewrite'):
            keys=[f'terminal.g{h}.{c}.scattered.{field}' for field in ('both_correct','locked_output_failure','both_reversed','other_failure')]
            keys += [f'joint.g{h}.{c}.{field}|scattered_failure' for field in ('intact_success_scattered_failure','scattered_failure_other_terminal_success')]
            keys += [f'joint.g{h}.{c}.next_body_success_given_scattered_failure']
            lines.append(f'| {h} | {c} | '+' | '.join(value(k,True) for k in keys)+' |')
    lines += ['','| Horizon | Policy | Strong edges | Available weak promoted | Strong edges lost to injury | Changed acquired signs | Injured strong graph: all outputs reachable % | Injured nonzero graph: all outputs reachable % |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for h in m.HORIZONS[1:]:
        for c in ('bridge_preserve','bridge_rewrite'):
            keys=[f'packet.g{h}.{c}.{field}' for field in ('strong','weak_promoted','physical_strong_lost','changed_sign_nonzero')]
            vals=[value(k) for k in keys]+[value(f'graph.g{h}.{c}.scattered.{field}',True) for field in ('strong_all_outputs','nonzero_all_outputs')]
            lines.append(f'| {h} | {c} | '+' | '.join(vals)+' |')
    lines += ['','A failed challenge followed by success with the same record in another recorded context is evidence against treating that failure as complete irreversible loss. Failures across all observed contexts do not establish absence of latent information. Each horizon uses different injury/birth/noise challenges; recovery does not imply that record quality improved. Strong/nonzero graphs ignore signs and magnitudes and cannot establish sufficient function. Output locking describes saved responses, not an inferred attractor. Conditional associations and sign changes do not establish causality. All policies, all boundaries, retained measurements and declared summaries remain available. A targeted intervention requires a separate frozen design.']
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n')


def worker(task):
    source,block,complete,output=task
    cap_cpus(8);t=time.monotonic();data=m.extract(source,block,complete);extraction=time.monotonic()-t
    t=time.monotonic();assert audit.inspect(source,block,complete,data);checking=time.monotonic()-t
    np.savez_compressed(output/f'measurements_{block:06d}.npz',**data)
    dump(output/f'worker_{block}.json',dict(block=block,extraction_seconds=extraction,audit_seconds=checking,status='PASS'))
    return data,extraction,checking


def execute(mode):
    started=time.monotonic();affinity=cap_cpus(8);index=source_check();technical=mode=='benchmark'
    source=ROOT/index['fixture_run' if technical else 'source_run']
    ids=index['fixture_blocks' if technical else 'source_blocks'];workers=1 if technical else min(8,len(affinity) or 1)
    name='benchmark_v1' if technical else 'diagnosis_v1';output=HERE/'runs'/name;job=HERE/'jobs'/name
    if not job.exists():new_run(job,inputs(),dict(experiment='E042',mode=mode,no_new_trajectories=True,workers=workers))
    check_inputs(job)
    new_run(output,inputs(),dict(experiment='E042',mode=mode,blocks=ids,source=str(source.relative_to(ROOT)),workers=workers,no_new_trajectories=True))
    try:
        dump(job/'pid.json',dict(pid=os.getpid(),utc=utc()))
        dump(job/'status.json',dict(status='RUNNING',stage='measurement_and_independent_verification',utc=utc(),pid=os.getpid()))
        complete=json.loads((source/'COMPLETE.json').read_text());t=time.monotonic()
        with ProcessPoolExecutor(max_workers=workers) as pool:
            rows=[]
            for block,result in zip(ids,pool.map(worker,[(source,b,complete,output) for b in ids])):
                rows.append(result);print('Verified block',block,flush=True)
        measurement_wall=time.monotonic()-t
        data={k:np.stack([r[0][k] for r in rows]) for k in rows[0][0]}
        dump(job/'status.json',dict(status='RUNNING',stage='summaries_and_verification',utc=utc(),pid=os.getpid()))
        series,definitions=summarize(data,ids)
        summary=dict(experiment='E042',status='TECHNICAL_ONLY' if technical else 'EXPLORATORY_DIAGNOSIS_COMPLETE',
            blocks=ids,lineages=len(ids)*4*data['packet'].shape[4],source=str(source.relative_to(ROOT)),
            no_new_trajectories=True,prior_cases_reused=True,causal_claim_established=False,
            conditions=m.CONDITIONS,active=m.ACTIVE,graph_conditions=m.GRAPH_CONDITIONS,horizons=m.HORIZONS,
            fields=m.FIELDS,series=series,definitions=definitions,
            interval_scope='Exploratory pointwise whole-block bootstrap; conditional ratios resample block totals',
            measurement_wall_seconds=measurement_wall,extraction_worker_seconds=sum(r[1] for r in rows),audit_worker_seconds=sum(r[2] for r in rows))
        audit.check_summaries(summary,data)
        reference=json.loads((source/'summary.json').read_text())
        for g in range(1,33):
            for c in [m.CONDITIONS[i] for i in m.ACTIVE]:
                assert series[f'body.g{g}.{c}.both_correct']['mean']==reference['body_reading'][str(g)][c]['both_cues']['mean']
        for h in m.HORIZONS:
            for c in m.CONDITIONS:
                for d in m.DAMAGE:
                    assert series[f'terminal.g{h}.{c}.{d}.both_correct']['mean']==reference['groups'][str(h)]['local_strength']['initial' if h==0 else c]['both_cues'][d]['own']['mean']
        dump(output/'summary.json',summary);report(output,summary);finish(output,started,dict(experiment='E042',blocks_completed=len(ids)))
        dump(output/'INDEPENDENT_AUDIT.json',dict(status='PASS',utc=utc(),blocks=len(ids),
            every_measurement_verified=True,all_source_scores_reproduced=True,graph_union_find_verified=True,
            all_output_classes_and_histories_verified=True,joint_failure_witnesses_verified=True,
            all_aggregates_and_intervals_verified=True,no_new_trajectories=True,
            complete_sha256=sha(output/'COMPLETE.json'),audit_code_sha256=sha(HERE/'audit.py')))
        subprocess.run([sys.executable,'-B',str(HERE/'plot.py'),str(output)],stdin=subprocess.DEVNULL,check=True)
        check_inputs(job);check_inputs(output);elapsed=time.monotonic()-started
        if technical:
            future_workers=min(8,len(affinity) or 1)
            estimate=1.8*(sum(r[1]+r[2] for r in rows))*32*2/future_workers+180
            retained=sum(p.stat().st_size for p in output.rglob('*') if p.is_file())
            required=math.ceil(1.5*retained*64)+128*1024**2
            path=HERE/'analysis/forecast_v1.json';assert not path.exists()
            dump(path,dict(utc=utc(),benchmark_workflow_seconds=elapsed,benchmark_measurement_seconds=sum(r[1]+r[2] for r in rows),
                forecast_seconds=estimate,workers=future_workers,detached_required=estimate>600,
                formula='1.8*(benchmark extraction+audit worker seconds)*32*2/workers+180',
                benchmark_complete_sha256=sha(output/'COMPLETE.json'),benchmark_audit_sha256=sha(output/'INDEPENDENT_AUDIT.json'),
                storage_with_reserve_bytes=required,available_bytes=shutil.disk_usage(HERE).free,
                capacity_pass=required<shutil.disk_usage(HERE).free,inputs_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs()}))
        dump(job/'status.json',dict(status='COMPLETE',utc=utc(),seconds=elapsed,complete_sha256=sha(output/'COMPLETE.json'),
            audit_sha256=sha(output/'INDEPENDENT_AUDIT.json'),figure_provenance_sha256=sha(HERE/'figures'/name/'provenance.json'),automatic_successor_started=False))
        print(json.dumps(dict(status='COMPLETE',mode=mode,seconds=elapsed,measurement_wall_seconds=measurement_wall,series=len(series)),indent=2),flush=True)
    except BaseException:
        failure=dict(status='FAILED',utc=utc(),traceback=traceback.format_exc())
        dump(job/'status.json',failure);dump(output/'FAILED.json',failure);raise


def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=('benchmark','scientific'),required=True)
    p.add_argument('--detach',action='store_true');p.add_argument('--child',action='store_true');a=p.parse_args();cap_cpus(8)
    if a.mode=='scientific':
        f=json.loads((HERE/'analysis/forecast_v1.json').read_text())
        t=json.loads((HERE/'analysis/technical_v1.json').read_text());assert t['status']=='PASS'
        for rel,digest in f['inputs_sha256'].items():assert sha(ROOT/rel)==digest
        assert sha(HERE/'analysis/freeze_v1/manifest.json')==t['freeze_manifest_sha256']
        assert f['capacity_pass'] and shutil.disk_usage(HERE).free>f['storage_with_reserve_bytes']
        if f['detached_required'] and not(a.detach or a.child):raise ValueError('Forecast >600s; detached execution required')
    name='benchmark_v1' if a.mode=='benchmark' else 'diagnosis_v1'
    if a.detach:
        assert not a.child and not (HERE/'jobs'/name).exists() and not (HERE/'runs'/name).exists()
        job=new_run(HERE/'jobs'/name,inputs(),dict(experiment='E042',mode=a.mode,workers=f['workers'],no_new_trajectories=True,detached=True))
        dump(job/'status.json',dict(status='PREPARED',utc=utc()))
        command=[sys.executable,'-B',str(Path(__file__).resolve()),'--mode',a.mode,'--child']
        with (job/'launcher.log').open('x') as log:
            process=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        dump(job/'launch.json',dict(pid=process.pid,utc=utc(),command=command));print('Detached PID',process.pid,flush=True)
    else:execute(a.mode)


if __name__=='__main__':main()
