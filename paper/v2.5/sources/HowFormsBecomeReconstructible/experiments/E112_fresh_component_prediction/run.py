"""Bounded excluded qualification, pre-source freeze and detached fixed-cohort run."""
import argparse
import ast
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import math
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from common import cap_cpus, check_inputs, dump, new_run, sha, utc
from E084_magnitude_placement.workflow import inventory
from E098_writer_pairing_tradeoff.run import scaled_source
from E098_writer_pairing_tradeoff import data as original_data
from E112_fresh_component_prediction import data, experiment, inference
from E112_fresh_component_prediction.plan import HERE, ROOT, settings, key


def code_paths():
    paths=set(HERE.glob('*.py')) | {HERE/'PROTOCOL.md', HERE/'DATA_DICTIONARY.md'}
    paths |= {ROOT/p for p in ('common.py','run_python.sh','RUN_POLICY.md','SOURCE_SNAPSHOT.json','SOURCE_LICENSE.txt')}
    pending=[p for p in paths if p.suffix=='.py']; seen=set()
    while pending:
        path=pending.pop()
        if path in seen:continue
        seen.add(path)
        for node in ast.walk(ast.parse(path.read_text())):
            names=[]
            if isinstance(node,ast.Import):names=[a.name for a in node.names]
            elif isinstance(node,ast.ImportFrom) and node.module:
                names=[node.module]+[node.module+'.'+a.name for a in node.names]
            for name in names:
                p=ROOT/(name.replace('.','/')+'.py')
                if p.is_file() and p not in paths:paths.add(p);pending.append(p)
    return sorted(paths)


def latest_tests():
    path=sorted((HERE/'analysis').glob('tests_attempt_*.json'))[-1]
    value=json.loads(path.read_text());assert value['status']=='PASS'
    assert value['inputs_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in code_paths()}
    assert value['registry_sha256']==sha(HERE/'SOURCE_DATA.json')
    return path


def inputs(mode):
    paths=code_paths()+[HERE/'SOURCE_DATA.json',latest_tests()]
    if mode=='scientific':paths += [HERE/'SAMPLE_FREEZE.json',HERE/'analysis/qualification_v1.json',HERE/'analysis/forecast_v1.json']
    return paths


def qualification():
    q=json.loads((HERE/'analysis/qualification_v1.json').read_text());assert q['status']=='PASS'
    for path,h in q['evidence'].items():assert sha(ROOT/path)==h,path
    assert q['inputs_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in inputs('benchmark')}
    freeze=json.loads((HERE/'SAMPLE_FREEZE.json').read_text())
    assert freeze['settings']==settings('scientific') and freeze['frozen_before_scientific_sources']
    assert freeze['qualification_sha256']==sha(HERE/'analysis/qualification_v1.json')
    return q


def execute(mode,name,workers):
    tick=time.monotonic();cfg=settings(mode);latest_tests();data.registry()
    if mode=='scientific':qualification();check_inputs(HERE/'jobs'/name)
    resources=inventory(workers);run=new_run(HERE/'runs'/name,inputs(mode),dict(**cfg,workers=workers))
    reports={};parts={};originals={};eraseds={}
    def status(state,stage):
        dump(run/'STATUS.json',dict(status=state,stage=stage,utc=utc(),pid=os.getpid(),mode=mode,workers=workers,
            completed_blocks=sorted(reports),total_blocks=len(cfg['blocks']),seconds=time.monotonic()-tick,
            automatic_extension=False,automatic_restart=False,automatic_successor=False))
    try:
        status('RUNNING','frozen_before_source_generation');dump(run/'resources.json',resources)
        dump(run/'PREDICTION_FREEZE.json',dict(utc=utc(),before_scientific_source_generation=True,
            mode=mode,blocks=cfg['blocks'],primary=cfg['primary'],primary_group=cfg['primary_group'],
            protocol_sha256=sha(HERE/'PROTOCOL.md'),manifest_sha256=sha(run/'manifest.json'),
            registry_sha256=sha(HERE/'SOURCE_DATA.json'),old_scientific_cases_pooled=False))
        status('RUNNING','fresh_genealogy_then_component_cross')
        with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('fork')) as pool:
            futures=[pool.submit(experiment.worker,(str(run),b,cfg)) for b in cfg['blocks']]
            for future in as_completed(futures):
                try:b,rows,original,erased,report=future.result()
                except BaseException:
                    for pending in futures:pending.cancel()
                    raise
                reports[b]=report;parts[b]=rows;originals[b]=original;eraseds[b]=erased
                status('RUNNING','fresh_genealogy_then_component_cross')
                print(f'Verified block {b}: {report["seconds"]:.2f} s',flush=True)
        rows=[r for b in cfg['blocks'] for r in parts[b]]
        original=[r for b in cfg['blocks'] for r in originals[b]]
        erased=[r for b in cfg['blocks'] for r in eraseds[b]]
        status('RUNNING','inference_and_all_individual_harms')
        experiment.export_union(run/'cases.csv',rows)
        original_data.export(run/'original_cases.csv',original)
        original_data.export(run/'original_two_draw_means.csv',original_data.averages(original))
        events,fields=original_data.events(original);original_data.export(run/'original_events.csv',events,fields)
        original_data.export(run/'erased_controls.csv',erased)
        summary,component_events=inference.summarize(mode,rows,original)
        fields=list(dict.fromkeys(k for r in rows for k in r))
        data.output_csv(run/'events.csv',[{k:r.get(k) for k in fields} for r in component_events],fields)
        dump(run/'summary.json',summary);(run/'REPORT.md').write_text(inference.report(summary));inference.plot(run,summary)
        checks=dict(status='PASS',blocks=len(reports),context_draw_rows=len(rows),record_contexts=len(rows)//2,
            eligible_rows=sum(r['eligible'] for r in rows),erased_witness_rows=sum(r['erased'] for r in rows),
            longer_witness_rows=sum(r['longer_witness'] for r in rows),empty_witness_rows=sum(r['empty_witness'] for r in rows),
            original_endpoint_rows=len(original),original_event_rows=len(events),erased_control_rows=len(erased),
            component_event_rows=len(component_events),all_source_and_reader_states_independently_replayed=True,
            independent_port_checks=sum(r['reader']['independent_scalar_port_checks'] for r in reports.values()),
            component_variant_updates=sum(r['reader']['component_variant_updates'] for r in reports.values()),
            independent_block_sums_checked=summary['independent_block_sums_checked'],
            primary_fixed_before_sources=True,all_cases_endpoints_and_harms_retained=True,
            old_scientific_cases_pooled=False,workers=workers)
        dump(run/'CHECKS.json',checks);check_inputs(run);data.registry()
        if mode=='scientific':check_inputs(HERE/'jobs'/name)
        status('COMPLETE','finished')
        outputs={str(p.relative_to(run)):sha(p) for p in sorted(run.rglob('*')) if p.is_file()}
        dump(run/'COMPLETE.json',dict(status='COMPLETE',utc=utc(),seconds=time.monotonic()-tick,mode=mode,
            blocks=len(reports),workers=workers,controls_pass=True,outputs_sha256=outputs,
            primary_decision=summary['primary']['decision'],criterion_met=summary['criterion_met']))
        print(json.dumps(dict(status='COMPLETE',seconds=time.monotonic()-tick,blocks=len(reports))),flush=True)
    except BaseException:
        failure=dict(status='FAILED',utc=utc(),seconds=time.monotonic()-tick,completed_blocks=sorted(reports),
            traceback=traceback.format_exc(),automatic_restart=False)
        dump(run/'FAILED.json',failure);dump(run/'STATUS.json',failure);raise


def verify(name):
    run=HERE/'runs'/name;check_inputs(run)
    c=json.loads((run/'COMPLETE.json').read_text());assert c['status']=='COMPLETE' and c['controls_pass']
    for path,h in c['outputs_sha256'].items():assert sha(run/path)==h,path
    checks=json.loads((run/'CHECKS.json').read_text());assert checks['status']=='PASS';data.registry()
    return run,c,checks


def qualify(name):
    run,c,checks=verify(name);assert c['mode']=='benchmark' and checks['blocks']==2
    assert not (HERE/'SAMPLE_FREEZE.json').exists() and not (HERE/'analysis/qualification_v1.json').exists()
    assert json.loads((run/'manifest.json').read_text())['inputs_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in inputs('benchmark')}
    bench,science=settings('benchmark'),settings('scientific');details={};projected_raw=0
    for task in bench['blocks']:
        r=json.loads((run/f'component_worker_{task}.json').read_text());old=r['ancestry']
        scaled=scaled_source(old['source_timings'],bench,science)
        possible=16*science['recipients'];eligible=r['structural']['eligible']
        assert eligible>0,'Need a nonempty excluded benchmark to price component work'
        # Scale steps and every possible eligible context, not the old-cohort yield.
        component_scale=(science['reader']['read_steps']/bench['reader']['read_steps'])*possible/eligible
        dynamics=r['reader']['phase_seconds']+r['reader']['continuation_seconds']
        seconds=sum(v['scaled_seconds'] for v in scaled.values())+16*old['pipeline_seconds']+4*old['static_seconds']
        seconds+=component_scale*dynamics+4*r['static_component_seconds']
        details[str(task)]=dict(source_stage_scaling=scaled,earlier_endpoint_scale=16,
            component_scale_all_contexts_eligible=component_scale,all_eligible_contexts=possible,
            scaled_block_seconds=seconds)
    block=max(v['scaled_block_seconds'] for v in details.values())
    # Upper bound uncompressed scientific arrays. Component eligibility can be
    # full even if the excluded blocks have sparse cycles; hashes scale by time.
    for p in run.glob('*.npz'):
        task=next((b for b in bench['blocks'] if str(b) in p.name),None)
        r=json.loads((run/f'component_worker_{task}.json').read_text()) if task else None
        with np.load(p,allow_pickle=False) as z:
            for name in z.files:
                if p.name.startswith(('component_assay_','phase_assay_','component_scores_')):
                    scale=max(4,64/max(1,r['structural']['eligible']))
                    if 'hash' in name or name=='absolute_steps':scale=max(scale,4)
                else:
                    scale=16 if 'hash' in name and p.name.startswith(('source_boundary_','source_continuation_','source_recovery_')) else 4
                projected_raw+=z[name].nbytes*scale
    projected_raw+=sum(p.stat().st_size for p in run.glob('*.csv'))*4
    reserve=math.ceil(projected_raw/len(bench['blocks'])*len(science['blocks'])*1.5)+1024**3
    forecast=dict(utc=utc(),scientific_blocks=len(science['blocks']),block_details=details,
        scaled_block_seconds=block,timing_margin=3,storage_reserve_bytes=reserve,
        component_pricing_assumes_all_contexts_eligible=True,
        expected_seconds_by_workers={str(w):block*math.ceil(32/w)+240 for w in range(1,5)},
        conservative_seconds_by_workers={str(w):3*block*math.ceil(32/w)+240 for w in range(1,5)})
    resources=inventory();workers=min(4,12-resources['other_busy_capacity'],len(resources['affinity']))
    assert workers>=1 and forecast['conservative_seconds_by_workers'][str(workers)]<=43200
    assert resources['free_bytes']>reserve
    dump(HERE/'analysis/forecast_v1.json',forecast)
    evidence={str(p.relative_to(ROOT)):sha(p) for p in (run/'COMPLETE.json',run/'CHECKS.json',run/'endpoints.png',
        latest_tests(),HERE/'analysis/forecast_v1.json')}
    dump(HERE/'analysis/qualification_v1.json',dict(status='PASS',utc=utc(),figures_inspected=True,evidence=evidence,
        outputs_verified=len(c['outputs_sha256']),checks=checks,
        inputs_sha256=json.loads((run/'manifest.json').read_text())['inputs_sha256']))
    dump(HERE/'SAMPLE_FREEZE.json',dict(utc=utc(),settings=science,frozen_before_scientific_sources=True,
        qualification_sha256=sha(HERE/'analysis/qualification_v1.json'),forecast_sha256=sha(HERE/'analysis/forecast_v1.json'),
        resources=resources,qualified_workers=workers,selection_based_on_scientific_outcomes=False))
    print(json.dumps(dict(status='PASS',workers=workers,storage_reserve_bytes=reserve,
        expected_seconds=forecast['expected_seconds_by_workers'][str(workers)],
        conservative_seconds=forecast['conservative_seconds_by_workers'][str(workers)])))


def launch(name,workers):
    qualification();data.registry();resources=inventory()
    forecast=json.loads((HERE/'analysis/forecast_v1.json').read_text())
    workers=workers or min(4,12-resources['other_busy_capacity'],len(resources['affinity']))
    assert 1<=workers<=4 and workers+resources['other_busy_capacity']<=12
    assert resources['free_bytes']>forecast['storage_reserve_bytes']
    assert forecast['conservative_seconds_by_workers'][str(workers)]<=43200
    burden={cpu:sum(r['sampled_cpu_percent']/len(r['affinity']) for r in resources['other_busy_processes']
                   if cpu in r['affinity']) for cpu in resources['affinity']}
    selected=sorted(sorted(burden,key=lambda x:(burden[x],x))[:workers])
    os.sched_setaffinity(0,selected);resources['selected_affinity']=selected;assert not (HERE/'runs'/name).exists()
    job=new_run(HERE/'jobs'/name,inputs('scientific'),dict(**settings('scientific'),workers=workers))
    with (job/'run.log').open('xb') as log:
        proc=subprocess.Popen(['bash',str(ROOT/'run_python.sh'),str(HERE/'run.py'),'run','--mode','scientific',
            '--name',name,'--workers',str(workers)],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,
            stderr=subprocess.STDOUT,start_new_session=True)
    dump(job/'launch.json',dict(utc=utc(),pid=proc.pid,workers=workers,numerical_threads=1,detached=True,
        stdin='/dev/null',resources=resources,forecast=forecast,automatic_successor=False))
    deadline=time.monotonic()+45;path=HERE/'runs'/name/'STATUS.json'
    try:
        while time.monotonic()<deadline and proc.poll() is None:
            try:state=json.loads(path.read_text())
            except (FileNotFoundError,json.JSONDecodeError):time.sleep(.2);continue
            assert state['status']=='RUNNING',state
            assert os.getsid(proc.pid)==proc.pid and os.readlink(f'/proc/{proc.pid}/fd/0')=='/dev/null'
            check_inputs(job);check_inputs(HERE/'runs'/name)
            dump(job/'startup.json',dict(status='PASS',utc=utc(),pid=proc.pid,durable_status=state,
                stdin='/dev/null',frozen_inputs_verified=True,automatic_scientific_polling=False))
            print(json.dumps(dict(status='RUNNING',pid=proc.pid,workers=workers,
                expected_seconds=forecast['expected_seconds_by_workers'][str(workers)],
                conservative_seconds=forecast['conservative_seconds_by_workers'][str(workers)])));return
        raise TimeoutError('No durable RUNNING state within startup check; no restart')
    except BaseException:
        dump(job/'startup_failed.json',dict(status='FAILED',utc=utc(),pid=proc.pid,
            traceback=traceback.format_exc(),automatic_restart=False));raise


def closeout(name):
    run,c,checks=verify(name);assert c['mode']=='scientific' and c['blocks']==32
    assert checks['context_draw_rows']==4096 and checks['original_endpoint_rows']==4096
    qualification();check_inputs(HERE/'jobs'/name)
    target=HERE/'analysis/closeout_v1.json';assert not target.exists()
    dump(target,dict(status='PASS',utc=utc(),complete_sha256=sha(run/'COMPLETE.json'),checks=checks,
        outputs_verified=len(c['outputs_sha256']),frozen_inputs_verified=len(inputs('scientific')),
        figures_inspected=True,figure_sha256=sha(run/'endpoints.png'),seconds=c['seconds'],
        primary_decision=c['primary_decision'],criterion_met=c['criterion_met'],
        retained_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()),automatic_successor=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('register','run','verify','qualify','launch','closeout'))
    p.add_argument('--mode',choices=('benchmark','scientific'));p.add_argument('--name')
    p.add_argument('--workers',type=int,default=0);p.add_argument('--figures-inspected',action='store_true')
    a=p.parse_args();assert 0<=a.workers<=4
    if a.action=='launch':launch(a.name,a.workers)
    else:
        cap_cpus(a.workers or (4 if a.action=='qualify' else 1))
        if a.action=='register':data.register()
        elif a.action=='run':execute(a.mode,a.name,a.workers or 1)
        elif a.action=='verify':
            _,c,_=verify(a.name);print(json.dumps(dict(status='PASS',outputs=len(c['outputs_sha256']))))
        else:
            assert a.figures_inspected
            qualify(a.name) if a.action=='qualify' else closeout(a.name)
