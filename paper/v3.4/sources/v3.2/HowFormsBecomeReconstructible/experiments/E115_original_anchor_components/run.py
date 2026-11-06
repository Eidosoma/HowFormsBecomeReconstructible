"""Bounded reader experiment, excluded pricing, immutable freeze and receipts."""
import argparse
import ast
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import cap_cpus, check_inputs, dump, new_run, sha, utc
from E084_magnitude_placement.workflow import inventory
from E115_original_anchor_components import data, experiment, inference
from E115_original_anchor_components.plan import HERE, ROOT, COPY_NAMES, MIDPOINT_COPIES, settings, key


def code_paths():
    paths=set(HERE.glob('*.py'))|{HERE/'PROTOCOL.md',HERE/'DATA_DICTIONARY.md'}
    paths|={ROOT/p for p in ('common.py','run_python.sh','RUN_POLICY.md')}
    pending=[p for p in paths if p.suffix=='.py'];seen=set()
    while pending:
        p=pending.pop()
        if p in seen:continue
        seen.add(p)
        for node in ast.walk(ast.parse(p.read_text())):
            names=[]
            if isinstance(node,ast.Import):names=[a.name for a in node.names]
            elif isinstance(node,ast.ImportFrom) and node.module:names=[node.module]+[node.module+'.'+a.name for a in node.names]
            for name in names:
                q=ROOT/(name.replace('.','/')+'.py')
                if q.is_file() and q not in paths:paths.add(q);pending.append(q)
    return sorted(paths)


def tests():
    p=sorted((HERE/'analysis').glob('tests_attempt_*.json'))[-1];t=json.loads(p.read_text())
    assert t['status']=='PASS' and t['inputs_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in code_paths()}
    assert t['registry_sha256']==sha(HERE/'SOURCE_DATA.json');return p


def inputs(mode):
    paths=code_paths()+[HERE/'SOURCE_DATA.json',tests()]
    if mode=='scientific':paths += [HERE/'SAMPLE_FREEZE.json',HERE/'analysis/qualification_v1.json',HERE/'analysis/forecast_v1.json']
    return paths


def qualification():
    q=json.loads((HERE/'analysis/qualification_v1.json').read_text());assert q['status']=='PASS'
    for p,h in q['evidence'].items():assert sha(ROOT/p)==h,p
    assert q['inputs_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in inputs('benchmark')}
    freeze=json.loads((HERE/'SAMPLE_FREEZE.json').read_text())
    assert freeze['settings']==settings('scientific') and freeze['before_anchored_scientific_outcomes']
    assert freeze['qualification_sha256']==sha(HERE/'analysis/qualification_v1.json');return q


def verify(name):
    run=HERE/'runs'/name;check_inputs(run);c=json.loads((run/'COMPLETE.json').read_text())
    assert c['status']=='COMPLETE' and c['controls_pass']
    for p,h in c['outputs_sha256'].items():assert sha(run/p)==h,p
    data.registry(all_files=True);return run,c


def worker(mode,task,cfg,known,sizes,run):
    check_inputs(run);rows,pairs,report=experiment.block(mode,task,cfg,known,sizes,run)
    dump(run/f'block_{task}.json',report);return rows,pairs,report


def execute(mode,name,workers):
    tick=time.monotonic();cfg=settings(mode);tests();assert 1<=workers<=4
    if mode=='scientific':qualification();check_inputs(HERE/'jobs'/name)
    else:assert workers==1
    run=new_run(HERE/'runs'/name,inputs(mode),dict(**cfg,workers=workers));reports=[]
    def status(state,stage):
        dump(run/'STATUS.json',dict(status=state,stage=stage,utc=utc(),pid=os.getpid(),mode=mode,workers=workers,
            completed_blocks=sorted(r['task'] for r in reports),total_blocks=len(cfg['blocks']),seconds=time.monotonic()-tick,
            automatic_restart=False,automatic_extension=False,automatic_successor=False))
    try:
        status('RUNNING','source_verification');dump(run/'resources.json',inventory(workers));reg=data.registry(all_files=True)
        known=data.known(mode);sizes=data.known(mode,'midpoint')
        for era,names in (('original',COPY_NAMES),('midpoint',MIDPOINT_COPIES)):
            for filename in names:
                path=run/(era+'_'+filename)
                with path.open('xb') as f:f.write(data.raw(mode,era,filename))
                assert sha(path)==reg['sources'][mode][era]['files'][filename]
        prior=json.loads((run/'original_summary.json').read_text());midpoint=json.loads((run/'midpoint_summary.json').read_text())
        original=data.table(mode,'original','original_cases.csv')
        assert len(original)==len(known) and {key(r) for r in original}==set(known)
        rows=[];pairs=[];status('RUNNING','anchored_readers_and_independent_replay')
        def accept(result):
            part,comparisons,rep=result
            assert rep['eligible_context_draws']==reg['sources'][mode]['original']['measured_rows_by_block'][str(rep['task'])]
            assert rep['evaluated_variant_draws']==reg['sources'][mode]['midpoint']['new_variant_draws_by_block'][str(rep['task'])]
            rows.extend(part);pairs.extend(comparisons);reports.append(rep)
            status('RUNNING','anchored_readers_and_independent_replay');print(f"Checked block {rep['task']}: {rep['seconds']:.3f} s",flush=True)
        arguments=[(mode,b,cfg,{k:v for k,v in known.items() if k[0]==b},{k:v for k,v in sizes.items() if k[0]==b},run) for b in cfg['blocks']]
        if workers==1:
            for args in arguments:accept(worker(*args))
        else:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                pending=[pool.submit(worker,*args) for args in arguments]
                for future in as_completed(pending):accept(future.result())
        rows.sort(key=key);pairs.sort(key=lambda r:key(r)+(r['component'],r['fixed_other'],r['later']))
        status('RUNNING','clustered_summaries_and_event_ledgers');summary,events,cross=inference.summarize(mode,rows,pairs,prior,midpoint)
        fields=list(dict.fromkeys(k for r in rows for k in r));pair_fields=list(pairs[0])
        data.export(run/'cases.csv',rows,fields);data.export(run/'responses.csv',[r for r in rows if r['measured']],fields)
        data.export(run/'comparisons.csv',pairs,pair_fields);data.export(run/'events.csv',events,pair_fields)
        crossing_fields=pair_fields+['variant','direction','threshold_before','threshold_after','threshold_distance_before',
            'crossing_fraction','old_weakest','new_weakest','weakest_changed','old_weakest_step','weakest_switch_term','failure_class']
        data.export(run/'crossings.csv',cross,crossing_fields);dump(run/'summary.json',summary)
        (run/'REPORT.md').write_text(inference.report(summary));inference.plot(run,summary)
        checks=dict(status='PASS',blocks=len(reports),context_draw_rows=len(rows),measured_rows=sum(r['measured'] for r in rows),
            comparisons=len(pairs),event_comparisons=len(events),success_crossings=len(cross),
            original_endpoint_rows=len(original),preserved_original_tables=len(COPY_NAMES),preserved_midpoint_tables=len(MIDPOINT_COPIES),
            scalar_port_checks=sum(r['scalar_port_checks'] for r in reports),original_source_scores=sum(r['original_source_scores'] for r in reports),
            independent_comparison_values=sum(r['independent_comparison_values'] for r in reports),
            independent_block_sums=summary['independent_block_sums_checked'],
            evaluated_variant_draws=sum(r['evaluated_variant_draws'] for r in reports),
            reused_variant_draws=sum(r['reused_variant_draws'] for r in reports),
            evaluated_variant_steps=sum(r['evaluated_variant_steps'] for r in reports),
            zero_targets=sum(r['zero_targets'] for r in reports),maximum_size_error=max(r['maximum_size_error'] for r in reports),
            maximum_component_leak=max(r['maximum_component_leak'] for r in reports),max_abs_initial=max(r['max_abs_initial'] for r in reports),
            all_new_steps_replayed=True,all_later_offsets_exact=True,all_scales_independently_reconstructed=True,
            all_original_endpoints_and_harms_retained=True,all_prior_primary_source_sums_exact=True,
            no_initial_clipping=True,no_injuries_or_streams_added=True,new_source_blocks=0)
        dump(run/'CHECKS.json',checks);check_inputs(run);data.registry(all_files=True)
        if mode=='scientific':check_inputs(HERE/'jobs'/name)
        status('COMPLETE','finished');outputs={str(p.relative_to(run)):sha(p) for p in sorted(run.rglob('*')) if p.is_file()}
        dump(run/'COMPLETE.json',dict(status='COMPLETE',utc=utc(),mode=mode,seconds=time.monotonic()-tick,
            blocks=len(reports),controls_pass=True,outputs_sha256=outputs,
            conclusion='ORIGINAL_ANCHOR_COMPONENTS',primary=summary['primary'],criterion_met=summary['criterion_met'],prior_primary_unchanged=True))
        print(json.dumps(dict(status='COMPLETE',seconds=time.monotonic()-tick,blocks=len(reports),decision=summary['primary']['decision'])),flush=True)
    except BaseException:
        failure=dict(status='FAILED',utc=utc(),seconds=time.monotonic()-tick,completed_blocks=[r['task'] for r in reports],
            traceback=traceback.format_exc(),automatic_restart=False)
        dump(run/'FAILED.json',failure);dump(run/'STATUS.json',failure);raise


def qualify(name):
    run,c=verify(name);assert c['mode']=='benchmark' and c['blocks']==2
    assert not (HERE/'SAMPLE_FREEZE.json').exists() and not (HERE/'analysis/qualification_v1.json').exists()
    current={str(p.relative_to(ROOT)):sha(p) for p in inputs('benchmark')}
    assert json.loads((run/'manifest.json').read_text())['inputs_sha256']==current
    reports=[json.loads(p.read_text()) for p in run.glob('block_*.json')];reg=data.registry()
    b,s=reg['sources']['benchmark']['original'],reg['sources']['scientific']['original']
    unit=max(r['reader_seconds']/r['evaluated_variant_steps'] for r in reports if r['evaluated_variant_steps'])
    static=4*max(r['static_seconds'] for r in reports)
    work=reg['sources']['scientific']['midpoint'];benchwork=reg['sources']['benchmark']['midpoint']
    costs=[unit*work['new_variant_draws_by_block'][str(task)]*1024+static for task in settings('scientific')['blocks']]
    resources=inventory();workers=min(4,12-resources['other_busy_capacity'],len(resources['affinity']));assert workers>=1
    forecasts={}
    for w in range(1,5):
        bound=sum(costs)/w+(1-1/w)*max(costs)
        forecasts[str(w)]=dict(expected_seconds=bound+180,conservative_seconds=3*bound+180)
    assert forecasts[str(workers)]['conservative_seconds']<=settings('scientific')['resource_limit_seconds']
    raw=sum(sum(i.file_size for i in zipfile.ZipFile(p).infolist()) for p in run.glob('assay_*.npz'))
    copied=sum((ROOT/reg['sources']['scientific'][era]['path']/name).stat().st_size
        for era,names in (('original',COPY_NAMES),('midpoint',MIDPOINT_COPIES)) for name in names)
    other=sum(p.stat().st_size for p in run.rglob('*') if p.is_file() and not p.name.startswith(('assay_','original_','midpoint_')))
    # Allow scientific-length hash traces and the complete 4,096-row export.
    reserve=math.ceil(copied+1.5*(raw*max(16,4*work['new_variant_draws']/max(1,benchwork['new_variant_draws']))+64*other))+256*1024**2
    assert resources['free_bytes']>reserve
    forecast=dict(utc=utc(),block_reports=reports,known_measured_rows=s['measured_rows'],all_source_blocks=32,
        reader_seconds_per_variant_step=unit,static_seconds_per_block=static,block_seconds=costs,
        summary_allowance_seconds=180,timing_margin=3,forecasts_by_workers=forecasts,workers=workers,
        **forecasts[str(workers)],storage_reserve_bytes=reserve,detach_required=forecasts[str(workers)]['conservative_seconds']>600,
        expected_variant_draws=work['new_variant_draws'],expected_reused_variant_draws=work['reused_variant_draws'],method='complete closed E112 inventory; no source selection')
    dump(HERE/'analysis/forecast_v1.json',forecast)
    evidence={str(p.relative_to(ROOT)):sha(p) for p in (run/'COMPLETE.json',run/'CHECKS.json',run/'anchored.png',tests(),HERE/'analysis/forecast_v1.json')}
    dump(HERE/'analysis/qualification_v1.json',dict(status='PASS',utc=utc(),figures_inspected=True,evidence=evidence,
        outputs_verified=len(c['outputs_sha256']),inputs_sha256=current))
    dump(HERE/'SAMPLE_FREEZE.json',dict(utc=utc(),settings=settings('scientific'),before_anchored_scientific_outcomes=True,
        old_outcomes_known=True,all_sources_retained=True,resources=resources,
        qualification_sha256=sha(HERE/'analysis/qualification_v1.json')))
    print(json.dumps({k:forecast[k] for k in ('workers','expected_seconds','conservative_seconds','detach_required','storage_reserve_bytes')}))


def launch(name):
    qualification();forecast=json.loads((HERE/'analysis/forecast_v1.json').read_text());workers=forecast['workers']
    resources=inventory(workers);assert resources['free_bytes']>forecast['storage_reserve_bytes']
    burden={cpu:sum(r['sampled_cpu_percent']/len(r['affinity']) for r in resources['other_busy_processes'] if cpu in r['affinity']) for cpu in resources['affinity']}
    selected=sorted(sorted(burden,key=lambda cpu:(burden[cpu],cpu))[:workers]);assert len(selected)==workers
    os.sched_setaffinity(0,selected);resources['selected_affinity']=selected
    job=new_run(HERE/'jobs'/name,inputs('scientific'),dict(**settings('scientific'),workers=workers))
    if not forecast['detach_required']:
        dump(job/'launch.json',dict(utc=utc(),pid=os.getpid(),detached=False,workers=workers,forecast=forecast,resources=resources))
        execute('scientific',name,workers);return
    with (job/'run.log').open('xb') as log:
        proc=subprocess.Popen(['bash',str(ROOT/'run_python.sh'),str(HERE/'run.py'),'execute','--mode','scientific','--name',name,'--workers',str(workers)],
            cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    dump(job/'launch.json',dict(utc=utc(),pid=proc.pid,detached=True,workers=workers,forecast=forecast,resources=resources,
        automatic_restart=False,automatic_successor=False))
    deadline=time.monotonic()+30
    while time.monotonic()<deadline and proc.poll() is None:
        try:s=json.loads((HERE/'runs'/name/'STATUS.json').read_text())
        except (FileNotFoundError,json.JSONDecodeError):time.sleep(.2);continue
        assert s['status']=='RUNNING';check_inputs(job);check_inputs(HERE/'runs'/name)
        assert os.getsid(proc.pid)==proc.pid and os.readlink(f'/proc/{proc.pid}/fd/0')=='/dev/null'
        dump(job/'startup.json',dict(status='PASS',utc=utc(),pid=proc.pid,workers=workers,automatic_polling=False))
        print(json.dumps(dict(status='RUNNING',pid=proc.pid,workers=workers,expected_seconds=forecast['expected_seconds'],conservative_seconds=forecast['conservative_seconds'])));return
    dump(job/'startup_failed.json',dict(status='FAILED',utc=utc(),automatic_restart=False))
    raise RuntimeError('Bounded startup failed; preserve evidence, no restart')


def closeout(name):
    run,c=verify(name);assert c['mode']=='scientific' and c['blocks']==32;qualification();check_inputs(HERE/'jobs'/name)
    checks=json.loads((run/'CHECKS.json').read_text())
    assert checks['context_draw_rows']==4096 and checks['measured_rows']==554 and checks['comparisons']==4432
    assert checks['evaluated_variant_draws']==4432 and checks['reused_variant_draws']==8864 and checks['all_new_steps_replayed']
    target=HERE/'analysis/closeout_v1.json';assert not target.exists()
    dump(target,dict(status='PASS',utc=utc(),complete_sha256=sha(run/'COMPLETE.json'),checks=checks,
        outputs_verified=len(c['outputs_sha256']),frozen_inputs_verified=len(inputs('scientific')),
        figures_inspected=True,figure_sha256=sha(run/'anchored.png'),seconds=c['seconds'],
        retained_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()),automatic_successor=False))
    print(json.dumps(dict(status='PASS',seconds=c['seconds'],outputs=len(c['outputs_sha256']))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('register','execute','qualify','launch','verify','closeout'))
    p.add_argument('--mode',choices=('benchmark','scientific'),default='benchmark');p.add_argument('--name',default='benchmark_v1')
    p.add_argument('--workers',type=int,default=1);p.add_argument('--figures-inspected',action='store_true')
    a=p.parse_args();(HERE/'analysis').mkdir(exist_ok=True)
    try:
        if a.action=='register':cap_cpus(1);data.register()
        elif a.action=='execute':cap_cpus(a.workers);execute(a.mode,a.name,a.workers)
        elif a.action=='launch':launch(a.name)
        elif a.action=='verify':
            _,c=verify(a.name);print(json.dumps(dict(status='PASS',outputs=len(c['outputs_sha256']))))
        else:
            assert a.figures_inspected
            qualify(a.name) if a.action=='qualify' else closeout(a.name)
    except BaseException:
        i=1
        while (HERE/f'analysis/{a.action}_failure_{i:03d}.json').exists():i+=1
        dump(HERE/f'analysis/{a.action}_failure_{i:03d}.json',dict(utc=utc(),action=a.action,
            traceback=traceback.format_exc(),automatic_restart=False));raise
