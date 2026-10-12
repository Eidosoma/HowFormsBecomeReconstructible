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
from E046_failure_chronology import metrics as m,audit
import numpy as np


def inputs():
    return [ROOT/p for p in ('common.py','run_python.sh','E015_functional_inheritance/audit.py')]+[
        HERE/p for p in ('metrics.py','audit.py','run.py','tests.py','plot.py','PROTOCOL.md','SOURCE_DATA.json')]


def source_check():
    index=json.loads((HERE/'SOURCE_DATA.json').read_text())
    for rel,digest in index['sha256'].items():assert sha(ROOT/rel)==digest,rel
    assert index['blocks']==list(range(32000,32032)) and index['source_policy_index']==3
    for mode in ('fixture','scientific'):
        ids=[900041] if mode=='fixture' else list(range(32000,32032))
        paths=index[mode+'_runs'];assert set(paths)=={'diagnosis'}
        path=ROOT/paths['diagnosis'];manifest=verify(path)
        assert manifest['contract']['blocks']==ids and manifest['contract']['experiment']=='E042'
        summary=json.loads((path/'summary.json').read_text())
        assert summary['conditions'][3]=='bridge_rewrite' and summary['active'][3]==3
        assert summary['fields']['body']==list(m.OUTPUT_FIELDS)
        assert summary['horizons']==[0,1,3,8,16,24,32]
        a=json.loads((path/'INDEPENDENT_AUDIT.json').read_text())
        assert a['status']=='PASS' and a['complete_sha256']==sha(path/'COMPLETE.json')
    return index


def statistics(numerator,denominator,draws):
    n,d=np.asarray(numerator,float),np.asarray(denominator,float)
    nn,dd=n[draws].sum(axis=1),d[draws].sum(axis=1);valid=dd>0
    return dict(mean=float(n.sum()/d.sum()) if d.sum() else None,
        ci95=np.quantile(nn[valid]/dd[valid],[.025,.975]).tolist() if valid.any() else None,
        block_numerators=n.tolist(),block_denominators=d.tolist(),valid_bootstrap_draws=int(valid.sum()))


def summarize(data,ids):
    draws=rng('E046','bootstrap','failure_chronology').integers(0,len(ids),(10000,len(ids)))
    series={};definitions={};B,F,R=data['terminal_success'].shape
    def add(key, spec, value, mask, denominator=None):
        assert key not in series and value.shape==mask.shape
        axes=tuple(range(1,value.ndim));num=np.where(mask,value,0.).sum(axis=axes)
        den=mask.sum(axis=axes) if denominator is None else denominator
        series[key]=statistics(num,den,draws);definitions[key]=spec
    for group in m.GROUPS:
        select=np.ones((B,F,R),bool) if group=='all' else data['terminal_success']==(group=='terminal_success')
        add(group+'.cohort_fraction',dict(kind='cohort',group=group),np.ones_like(select),select,np.full(B,F*R))
        for t in range(32):
            for k,field in enumerate(m.FEATURES):
                add(f'{group}.g{t+1}.{field}',dict(kind='features',group=group,time=t,feature=k),
                    data['features'][:,t,...,k],select & data['feature_observed'][:,t,...,k])
            for k,field in enumerate(m.HISTORY_FIELDS):
                observed=select if t or k not in (2,3) else np.zeros_like(select)
                add(f'{group}.g{t+1}.history.{field}',dict(kind='history',group=group,time=t,feature=k),data['history'][:,t,...,k],observed)
        for k,field in enumerate(m.LINEAGE_FIELDS):
            add(group+'.lineage.'+field,dict(kind='lineage',group=group,feature=k),data['lineage'][...,k],select & data['lineage_observed'][...,k])
        for e,event in enumerate(m.EVENTS):
            for j,offset in enumerate(m.OFFSETS):
                for k,field in enumerate(m.FEATURES):
                    add(f'{group}.{event}.offset{offset}.{field}',dict(kind='event',group=group,event=e,offset=j,feature=k),
                        data['event_values'][:,e,j,...,k],select & data['event_observed'][:,e,j,...,k])
        for kind in ('closed_spells','open_spells'):
            for t in range(32):
                add(f'{group}.{kind}.length{t+1}',dict(kind=kind,group=group,time=t),data[kind][:,t],select)
        for d,injury in enumerate(('intact','scattered','square')):
            for k,field in enumerate(m.OUTPUT_FIELDS):
                add(f'{group}.terminal.{injury}.{field}',dict(kind='terminal',group=group,injury=d,feature=k),data['terminal'][...,d,k],select)
    for t,label in enumerate(m.TRANSITIONS):
        select=data['transitions'][:,1:]==t
        add('transition.'+label+'.frequency',dict(kind='transition_frequency',transition=t),np.ones_like(select),select,np.full(B,31*F*R))
        for k,field in enumerate(m.FEATURES):
            add('transition.'+label+'.'+field,dict(kind='transition_feature',transition=t,feature=k),
                data['features'][:,1:,...,k],select & data['feature_observed'][:,1:,...,k])
    assert len(series)==4522
    return series,definitions


def report(output,s):
    series=s['series']
    def q(key,scale=1):
        x=series[key]
        return 'n/a' if x['mean'] is None else f"{scale*x['mean']:.2f} [{scale*x['ci95'][0]:.2f},{scale*x['ci95'][1]:.2f}]"
    def count(key):return int(sum(series[key]['block_numerators']))
    lines=['# E046 — onset, recovery and persistence of rebuilding failure','','**'+s['status']+'**','',
        f"{s['lineages']} existing E041 lineages, all 32 saved rebuilding bodies. No new trajectories.",'',
        'Groups use original h32 normalized/scattered terminal success. They are outcome-conditioned descriptions, not prospective risk groups. Event generation means exclude absent events; all zero-denominator estimates are null.','',
        '| Group | Lineages | Ever body failure | Ever 3 consecutive failures | Final body fails | Total failed bodies per lineage [95%] |',
        '| --- | ---: | ---: | ---: | ---: | --- |']
    for group in m.GROUPS:
        prefix=group+'.lineage.'
        lines.append('| '+group+' | '+str(count(group+'.cohort_fraction'))+' | '+' | '.join(str(count(prefix+k)) for k in ('ever_failed','ever_three_consecutive','final_body_failed'))+' | '+q(prefix+'total_failed_bodies')+' |')
    lines+=['','| Group | First failure generation, among affected | Next-body recovery % | Recovery within 3, complete follow-up % | First spell closed % | Longest observed failure run |',
        '| --- | --- | --- | --- | --- | --- |']
    for group in m.GROUPS:
        fields=(('first_failure_generation',1),('next_body_recovered',100),('recovered_within_three',100),('first_failure_spell_closed',100),('longest_failure_run',1))
        lines.append('| '+group+' | '+' | '.join(q(group+'.lineage.'+k,scale) for k,scale in fields)+' |')
    lines+=['','| Generation | All bodies failing % | Later terminal successes: bodies failing % | Later terminal failures: bodies failing % |',
        '| --- | --- | --- | --- |']
    for g in (1,3,8,16,24,32):
        def failed(group):
            x=series[f'{group}.g{g}.body.both_correct']
            return 'n/a' if x['mean'] is None else f"{100*(1-x['mean']):.2f} [{100*(1-x['ci95'][1]):.2f},{100*(1-x['ci95'][0]):.2f}]"
        lines.append(f'| {g} | '+' | '.join(failed(group) for group in m.GROUPS)+' |')
    lines+=['','| All-boundary group (g2–32) | Boundaries | Incoming strong | Physical strong loss, before reading | Prior write weakening | Current write weakening, after reading | Current write weak promotions |',
        '| --- | ---: | --- | --- | --- | --- | --- |']
    for transition in m.TRANSITIONS:
        prefix='transition.'+transition+'.'
        lines.append('| '+transition+' | '+str(count(prefix+'frequency'))+' | '+' | '.join(q(prefix+k) for k in ('incoming.strong','injury.strong_lost','prior_write.strong_weakened','current_write.strong_weakened','current_write.weak_promoted'))+' |')
    lines+=['','All 4,522 fixed summaries, first-failure and first-three-failure windows (−3…+3), class trajectories, spell-length counts and per-lineage histories are retained. Three-failure onset is the first of three consecutive failed bodies, confirmed two generations later. An open failure spell at g32 is right-censored; it is not permanent failure. g1 has no preceding body or prior renewal write. All follow-up and boundary padding have explicit observation masks.', '',
        'Body g reads packet g−1 after injury g; its outgoing packet g is written afterward. Current-write changes cannot precede that same body response. Observed chronology does not establish why reading failed. Physical challenges differ by generation. Event alignment and final-outcome groups are selected on existing outcomes; transition contrasts also mix generations. All intervals are exploratory, pointwise whole-block estimates. Repeated boundaries are not independent replicates. Original E041/E045 claims remain unchanged; no new causal intervention or serial qualification is established.']
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n')


def worker(task):
    paths,block,complete,output=task
    cap_cpus(8);t=time.monotonic();data=m.extract(paths,block,complete);extraction=time.monotonic()-t
    t=time.monotonic();assert audit.inspect(paths,block,complete,data);checking=time.monotonic()-t
    np.savez_compressed(output/f'measurements_{block:06d}.npz',**data)
    dump(output/f'worker_{block}.json',dict(block=block,extraction_seconds=extraction,audit_seconds=checking,status='PASS'))
    return data,extraction,checking


def execute(mode):
    started=time.monotonic();affinity=cap_cpus(8);index=source_check();technical=mode=='benchmark'
    sources=index['fixture_runs' if technical else 'scientific_runs'];paths={k:ROOT/v for k,v in sources.items()}
    ids=[900041] if technical else list(range(32000,32032));workers=1 if technical else min(8,len(affinity) or 1)
    name='benchmark_v1' if technical else 'chronology_v1';output=HERE/'runs'/name;job=HERE/'jobs'/name
    if not job.exists():new_run(job,inputs(),dict(experiment='E046',mode=mode,no_new_trajectories=True,workers=workers))
    check_inputs(job)
    new_run(output,inputs(),dict(experiment='E046',mode=mode,blocks=ids,sources=sources,workers=workers,no_new_trajectories=True))
    try:
        dump(job/'pid.json',dict(pid=os.getpid(),utc=utc()))
        dump(job/'status.json',dict(status='RUNNING',stage='measurement_and_independent_verification',utc=utc(),pid=os.getpid()))
        complete={k:json.loads((p/'COMPLETE.json').read_text()) for k,p in paths.items()};t=time.monotonic()
        with ProcessPoolExecutor(max_workers=workers) as pool:
            rows=[]
            for block,result in zip(ids,pool.map(worker,[(paths,b,complete,output) for b in ids])):
                rows.append(result);print('Verified block',block,flush=True)
        measurement_wall=time.monotonic()-t
        data={k:np.stack([r[0][k] for r in rows]) for k in rows[0][0]}
        dump(job/'status.json',dict(status='RUNNING',stage='summaries_and_verification',utc=utc(),pid=os.getpid()))
        series,definitions=summarize(data,ids)
        summary=dict(experiment='E046',status='TECHNICAL_ONLY' if technical else 'EXPLORATORY_DIAGNOSIS_COMPLETE',
            blocks=ids,lineages=len(ids)*4*data['terminal_success'].shape[2],sources=sources,
            no_new_trajectories=True,prior_cases_reused=True,causal_claim_established=False,
            generations=list(range(1,33)),features=list(m.FEATURES),groups=list(m.GROUPS),history_fields=list(m.HISTORY_FIELDS),
            lineage_fields=list(m.LINEAGE_FIELDS),events=list(m.EVENTS),offsets=list(m.OFFSETS),transitions=list(m.TRANSITIONS),
            series=series,definitions=definitions,
            interval_scope='Exploratory pointwise whole-block bootstrap; outcome-conditioned ratios resample block totals',
            measurement_wall_seconds=measurement_wall,extraction_worker_seconds=sum(r[1] for r in rows),audit_worker_seconds=sum(r[2] for r in rows))
        audit.check_summaries(summary,data)
        reference=json.loads((paths['diagnosis']/'summary.json').read_text())['series']
        for g in range(1,33):
            assert series[f'all.g{g}.body.both_correct']['mean']==reference[f'body.g{g}.bridge_rewrite.both_correct']['mean']
        for d in ('intact','scattered','square'):
            assert series[f'all.terminal.{d}.both_correct']['mean']==reference[f'terminal.g32.bridge_rewrite.{d}.both_correct']['mean']
        assert len(series)==4522
        source_check()
        dump(output/'summary.json',summary);report(output,summary);finish(output,started,dict(experiment='E046',blocks_completed=len(ids)))
        dump(output/'INDEPENDENT_AUDIT.json',dict(status='PASS',utc=utc(),blocks=len(ids),
            every_history_event_spell_and_window_verified=True,all_32_body_and_three_terminal_source_means_reproduced=True,
            missing_followup_and_right_censoring_verified=True,all_aggregates_and_intervals_verified=True,
            e042_measurements_reused_from_pinned_audited_source=True,no_new_trajectories=True,
            complete_sha256=sha(output/'COMPLETE.json'),audit_code_sha256=sha(HERE/'audit.py')))
        subprocess.run([sys.executable,'-B',str(HERE/'plot.py'),str(output)],stdin=subprocess.DEVNULL,check=True)
        check_inputs(job);check_inputs(output);elapsed=time.monotonic()-started
        if technical:
            future_workers=min(8,len(affinity) or 1)
            estimate=1.8*sum(r[1]+r[2] for r in rows)*32*2/future_workers+180
            retained=sum(p.stat().st_size for p in output.rglob('*') if p.is_file())
            required=math.ceil(1.5*retained*64)+128*1024**2
            path=HERE/'analysis/forecast_v1.json';assert not path.exists()
            dump(path,dict(utc=utc(),benchmark_workflow_seconds=elapsed,benchmark_measurement_seconds=sum(r[1]+r[2] for r in rows),
                benchmark_run_bytes=retained,forecast_seconds=estimate,workers=future_workers,detached_required=estimate>600,
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
    name='benchmark_v1' if a.mode=='benchmark' else 'chronology_v1'
    if a.detach:
        assert not a.child and not (HERE/'jobs'/name).exists() and not (HERE/'runs'/name).exists()
        job=new_run(HERE/'jobs'/name,inputs(),dict(experiment='E046',mode=a.mode,workers=f['workers'],no_new_trajectories=True,detached=True))
        dump(job/'status.json',dict(status='PREPARED',utc=utc()))
        command=[sys.executable,'-B',str(Path(__file__).resolve()),'--mode',a.mode,'--child']
        with (job/'launcher.log').open('x') as log:
            process=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        dump(job/'launch.json',dict(pid=process.pid,utc=utc(),command=command));print('Detached PID',process.pid,flush=True)
    else:execute(a.mode)


if __name__=='__main__':main()
