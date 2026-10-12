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
from E044_transition_diagnosis import metrics as m,audit
import numpy as np


def inputs():
    return [ROOT/p for p in ('common.py','run_python.sh','E015_functional_inheritance/audit.py',
        'E032_renewal_failure_diagnosis/metrics.py','E032_renewal_failure_diagnosis/audit.py')]+[
        HERE/p for p in ('metrics.py','audit.py','run.py','tests.py','plot.py','PROTOCOL.md','SOURCE_DATA.json')]


def source_check():
    index=json.loads((HERE/'SOURCE_DATA.json').read_text())
    for rel,digest in index['sha256'].items():assert sha(ROOT/rel)==digest,rel
    for mode in ('fixture','scientific'):
        ids=[900041] if mode=='fixture' else list(range(32000,32032))
        for role,rel in index[mode+'_runs'].items():
            path=ROOT/rel;manifest=verify(path)
            assert manifest['contract']['blocks']==ids
            assert manifest['contract']['experiment']==('E042' if role=='diagnosis' else 'E043')
            if role=='timing':
                assert manifest['contract']['source_policy']=='bridge_rewrite'
                assert manifest['contract']['config']['recipients']==(2 if mode=='fixture' else 4)
                assert manifest['contract']['panels']==[[h,t,r] for h in (24,32) for t in m.TIMINGS for r in ('fixed_four','local_strength')]
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
    draws=rng('E044','bootstrap','transition_diagnosis').integers(0,len(ids),(10000,len(ids)))
    series={};definitions={}
    def add(hi,d,group,label,k,den=None):
        a=data['features'][:,hi,:,:,d]
        selected=np.ones(a.shape[:-1],bool) if group is None else data['groups'][:,hi,:,:,d]==group
        n=(a[...,k]*selected).sum(axis=(1,2))
        denominator=np.full(len(ids),a.shape[1]*a.shape[2]) if k==0 else selected.sum(axis=(1,2)) if den is None else (a[...,den]*selected).sum(axis=(1,2))
        key=f'h{m.HORIZONS[hi]}.{m.DAMAGE[d]}.{m.GROUPS[group] if group is not None else "all"}.{label}'
        series[key]=statistics(n,denominator,draws)
        definitions[key]=dict(horizon=hi,injury=d,group=group,feature=k,denominator=den,population_denominator=k==0)
    for hi in range(2):
        for d in range(3):
            for group in (None,0,1,2,3):
                for k,field in enumerate(m.FEATURES):
                    den=m.FEATURES.index('witness.next_body_observed') if field=='witness.next_body_success' else None
                    add(hi,d,group,field,k,den)
                for label,(num,den) in m.RATIOS.items():add(hi,d,group,'repair.'+label,m.FEATURES.index(num),m.FEATURES.index(den))
    return series,definitions


def report(output,s):
    series=s['series']
    def st(h,group,field):return series[f'h{h}.scattered.{group}.{field}']
    def n(h,group,field='cohort_fraction'):return int(sum(st(h,group,field)['block_numerators']))
    def value(h,group,field,scale=1):
        x=st(h,group,field)
        return 'n/a' if x['mean'] is None else f"{scale*x['mean']:.2f} [{scale*x['ci95'][0]:.2f},{scale*x['ci95'][1]:.2f}]"
    lines=['# E044 — timing changes and saved rewriting histories','','**'+s['status']+'**','',
        f"{len(s['blocks'])} reused blocks; {s['lineages']} lineages. No new trajectories or causal repair claim.",'',
        'Groups compare the original and delayed-extra-time normalized receivers. All intervals are exploratory, pointwise whole-block intervals, conditioned on the indicated outcome group.','',
        '| Horizon | Group | Cases | Original locked / reversed / other | Delayed locked / reversed / other | Current rebuilding body correct % | Earlier bodies failing % |',
        '| --- | --- | --- | --- | --- | --- | --- |']
    for h in m.HORIZONS:
        for group in m.GROUPS:
            labels=[' / '.join(str(n(h,group,t+'.'+c)) for c in ('locked_output_failure','both_reversed','other_failure')) for t in ('original','delayed_extra_time')]
            lines.append(f'| {h} | {group} | {n(h,group)} | '+' | '.join(labels)+f" | {value(h,group,'body.both_correct',100)} | {value(h,group,'history.prior_body_failure_fraction',100)} |")
    lines+=['','| h32 scattered group | Strong edges | Strong before latest rewrite | Latest strong weakening | Latest weak-to-strong promotion | Physical strong loss | Last 8 bodies: failures | Last 8 rewrites: strong weakening |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for group in m.GROUPS:
        fields=('packet.strong','history.previous_strong','packet.strong_weakened','packet.weak_promoted',
            'packet.physical_strong_lost','history.recent_body_failures','history.recent_strong_weakenings')
        lines.append('| '+group+' | '+' | '.join(value(32,group,f) for f in fields)+' |')
    lines+=['','| h32 scattered group | Original intact success % | Delayed intact success % | Strong injured graph connected % | Returning edges restored % | Young weak repairs promoted % |',
        '| --- | --- | --- | --- | --- | --- |']
    for group in m.GROUPS:
        fields=('witness.original_intact_correct','witness.delayed_intact_correct','graph.strong_all_outputs',
            'repair.returning_restored_fraction','repair.young_promoted_fraction')
        lines.append('| '+group+' | '+' | '.join(value(32,group,f,100) for f in fields)+' |')
    lines+=['','All h24/h32 injuries, three schedules, four mutually exclusive output classes, full class-transition tables, 113 retained features, declared conditional repair ratios and per-block counts are available in summary.json. h32 next-body success is unobserved and has a null estimate, never zero success. E042 packet/body/graph measurements are reused as previously audited inputs; the new joins, output classification, history windows, totals and intervals are independently checked.', '',
        'These groups are defined by outcomes on the same cohort. Small rescued/lost groups, nonrandom conditioning and repeated measurements prevent causal or fresh-confirmation claims. Output locking is a response label, not proof of an attractor. Unsigned connectivity omits weight signs and magnitudes. Associations between body failure and strong weakening do not identify which causes which. This diagnosis cannot overturn E043\'s failed timing criterion or E041\'s passed finite durability criterion. No additional reader or writing intervention ran.']
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
    name='benchmark_v1' if technical else 'diagnosis_v1';output=HERE/'runs'/name;job=HERE/'jobs'/name
    if not job.exists():new_run(job,inputs(),dict(experiment='E044',mode=mode,no_new_trajectories=True,workers=workers))
    check_inputs(job)
    new_run(output,inputs(),dict(experiment='E044',mode=mode,blocks=ids,sources=sources,workers=workers,no_new_trajectories=True))
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
        summary=dict(experiment='E044',status='TECHNICAL_ONLY' if technical else 'EXPLORATORY_DIAGNOSIS_COMPLETE',
            blocks=ids,lineages=len(ids)*4*data['features'].shape[3],sources=sources,
            no_new_trajectories=True,prior_cases_reused=True,causal_claim_established=False,
            horizons=list(m.HORIZONS),features=list(m.FEATURES),groups=list(m.GROUPS),timings=list(m.TIMINGS),damage=list(m.DAMAGE),
            series=series,definitions=definitions,
            interval_scope='Exploratory pointwise whole-block bootstrap; outcome-conditioned ratios resample block totals',
            measurement_wall_seconds=measurement_wall,extraction_worker_seconds=sum(r[1] for r in rows),audit_worker_seconds=sum(r[2] for r in rows))
        audit.check_summaries(summary,data)
        reference=json.loads((paths['timing']/'summary.json').read_text())
        group_names=('both_fail','rescued','lost','both_succeed')
        for h in m.HORIZONS:
            for d in m.DAMAGE:
                for t in m.TIMINGS:
                    assert series[f'h{h}.{d}.all.{t}.both_correct']['mean']==reference['groups'][str(h)]['local_strength'][t]['both_cues'][d]['own']['mean']
                counts=reference['transitions'][str(h)]['local_strength']['delayed_extra_time_minus_original'][d]['counts']
                for group,name_in_source in zip(m.GROUPS,group_names):
                    assert sum(series[f'h{h}.{d}.{group}.cohort_fraction']['block_numerators'])==counts[name_in_source]
        assert len(series)==3480
        source_check()
        dump(output/'summary.json',summary);report(output,summary);finish(output,started,dict(experiment='E044',blocks_completed=len(ids)))
        dump(output/'INDEPENDENT_AUDIT.json',dict(status='PASS',utc=utc(),blocks=len(ids),
            every_join_and_history_window_verified=True,all_e043_source_scores_and_transition_counts_reproduced=True,
            all_output_classes_verified=True,all_aggregates_and_intervals_verified=True,
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
    name='benchmark_v1' if a.mode=='benchmark' else 'diagnosis_v1'
    if a.detach:
        assert not a.child and not (HERE/'jobs'/name).exists() and not (HERE/'runs'/name).exists()
        job=new_run(HERE/'jobs'/name,inputs(),dict(experiment='E044',mode=a.mode,workers=f['workers'],no_new_trajectories=True,detached=True))
        dump(job/'status.json',dict(status='PREPARED',utc=utc()))
        command=[sys.executable,'-B',str(Path(__file__).resolve()),'--mode',a.mode,'--child']
        with (job/'launcher.log').open('x') as log:
            process=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        dump(job/'launch.json',dict(pid=process.pid,utc=utc(),command=command));print('Detached PID',process.pid,flush=True)
    else:execute(a.mode)


if __name__=='__main__':main()
