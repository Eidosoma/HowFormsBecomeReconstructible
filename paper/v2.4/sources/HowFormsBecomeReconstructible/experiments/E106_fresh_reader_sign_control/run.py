"""Frozen source comparison, measured runtime, bounded launch and durable status."""
import argparse
import ast
from concurrent.futures import ProcessPoolExecutor,as_completed
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
from common import cap_cpus,check_inputs,dump,new_run,sha,utc
from E084_magnitude_placement.workflow import inventory
from E106_fresh_reader_sign_control import data,experiment,inference
from E106_fresh_reader_sign_control.plan import HERE,ROOT,settings,VARIANTS,METRICS


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
                path=ROOT/(name.replace('.','/')+'.py')
                if path.is_file() and path not in paths:paths.add(path);pending.append(path)
    return sorted(paths)


def tests():
    p=sorted((HERE/'analysis').glob('tests_attempt_*.json'))[-1];r=json.loads(p.read_text())
    assert r['status']=='PASS' and r['inputs_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in code_paths()}
    assert r['registry_sha256']==sha(HERE/'SOURCE_DATA.json');return p


def inputs(mode):
    paths=code_paths()+[HERE/'SOURCE_DATA.json',tests()]
    if mode=='scientific':paths += [HERE/'analysis/preflight_v1.json',HERE/'analysis/qualification_v1.json',
                                  HERE/'analysis/forecast_v1.json',HERE/'SAMPLE_FREEZE.json']
    return paths


def verify(name):
    run=HERE/'runs'/name;check_inputs(run);c=json.loads((run/'COMPLETE.json').read_text())
    assert c['status']=='COMPLETE' and c['controls_pass']
    for p,h in c['outputs_sha256'].items():assert sha(run/p)==h,p
    data.registry(all_files=True);return run,c


def qualification():
    q=json.loads((HERE/'analysis/qualification_v1.json').read_text());assert q['status']=='PASS'
    for p,h in q['evidence'].items():assert sha(ROOT/p)==h,p
    assert q['inputs_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in inputs('benchmark')}
    f=json.loads((HERE/'SAMPLE_FREEZE.json').read_text());assert f['settings']==settings('scientific')
    assert f['qualification_sha256']==sha(HERE/'analysis/qualification_v1.json');return q


def worker(mode,b,cfg,run,expected):
    check_inputs(run);rows,report,_=experiment.block(mode,b,cfg,run,expected)
    dump(run/f'block_{b}.json',report);return rows,report


def execute(mode,name,workers):
    cfg=settings(mode);tests();assert 1<=workers<=4
    expected={}
    if mode=='scientific':
        qualification();expected=json.loads((HERE/'analysis/preflight_v1.json').read_text())['blocks']
    else:assert workers==1
    tick=time.monotonic();run=new_run(HERE/'runs'/name,inputs(mode),dict(**cfg,workers=workers));reports=[]
    def status(state,stage):
        dump(run/'STATUS.json',dict(status=state,stage=stage,utc=utc(),pid=os.getpid(),mode=mode,workers=workers,
            completed_blocks=sorted(r['task'] for r in reports),total_blocks=len(cfg['blocks']),seconds=time.monotonic()-tick,
            automatic_restart=False,automatic_extension=False,automatic_successor=False))
    try:
        status('RUNNING','source_verification');resources=inventory(workers);dump(run/'resources.json',resources)
        data.registry(all_files=True);original=data.original(mode)
        parent=json.loads(data.raw(mode,'original_summary.json'))
        for source,target in (('original_cases.csv','original_cases.csv'),('original_summary.json','original_summary.json'),
                              ('cases.csv','previous_cases.csv'),('summary.json','previous_summary.json')):
            with (run/target).open('xb') as f:f.write(data.raw(mode,source))
        endpoints=data.verify_endpoints(original,parent,cfg['blocks']);rows=[]
        status('RUNNING','readers_and_independent_replay')
        if workers==1:
            for b in cfg['blocks']:
                part,rep=worker(mode,b,cfg,run,expected.get(str(b)));rows.extend(part);reports.append(rep)
                status('RUNNING','readers_and_independent_replay');print(f"Checked {b}: {rep['seconds']:.2f}s",flush=True)
        else:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                pending={pool.submit(worker,mode,b,cfg,run,expected[str(b)]):b for b in cfg['blocks']}
                for future in as_completed(pending):
                    part,rep=future.result();rows.extend(part);reports.append(rep)
                    status('RUNNING','readers_and_independent_replay');print(f"Checked {rep['task']}: {rep['seconds']:.2f}s",flush=True)
        rows.sort(key=lambda r:data.identity(r)+(r['draw'],));assert len(rows)==len(original)
        old={data.identity(r)+(int(r['draw']),):r for r in data.table(mode,'cases.csv')}
        for r in rows:
            o=old[data.identity(r)+(r['draw'],)]
            for v in VARIANTS:
                for k in METRICS:assert r['previous_'+v+'_'+k]==float(o[v+'_'+k]),k
        status('RUNNING','clustered_summaries');summary,events,repeat_events=inference.summarize(mode,rows)
        summary['original_endpoint_checks']=endpoints;data.output_csv(run/'cases.csv',rows)
        fields=list(inference.IDENTIFIERS)+['eligible','affected','evaluated','contrast','direction','delta']+[v+'_'+m for v in VARIANTS for m in METRICS]
        data.output_csv(run/'events.csv',events,fields);dump(run/'summary.json',summary)
        fields=list(inference.IDENTIFIERS)+['eligible','affected','evaluated','contrast','previous_delta','fresh_delta']+[
            prefix+v+'_'+m for prefix in ('','previous_') for v in VARIANTS for m in METRICS]
        data.output_csv(run/'repeat_events.csv',repeat_events,fields)
        (run/'REPORT.md').write_text(inference.report(summary));inference.plot(run,summary)
        checks=dict(status='PASS',blocks=len(reports),contexts=len(rows)//2,context_draw_rows=len(rows),
            evaluated_context_draws=sum(r['evaluated_context_draws'] for r in reports),
            eligible_context_draws=sum(r['eligible_context_draws'] for r in reports),
            evaluated_variant_draws=sum(r['evaluated_variant_draws'] for r in reports),
            evaluated_variant_steps=sum(r['evaluated_variant_steps'] for r in reports),
            identity_context_draws=sum(r['identity_context_draws'] for r in reports),
            independent_block_sums=summary['independent_block_sums_checked'],original_endpoint_checks=endpoints,
            all_original_endpoints_and_harms_retained=True,all_previous_endpoints_verified=True,all_new_steps_replayed=True,
            all_new_D_baselines=True,old_outcomes_cached=False,all_old_new_streams_distinct=True,
            all_signed_multiset_constraints=True,all_no_ops_retained=True,new_source_blocks=0,new_reader_nuisances=True,new_injuries=False)
        if mode=='scientific':assert checks['evaluated_context_draws']==sum(x['evaluated_context_draws'] for x in expected.values())
        dump(run/'CHECKS.json',checks);check_inputs(run);data.registry(all_files=True);status('COMPLETE','finished')
        outputs={str(p.relative_to(run)):sha(p) for p in sorted(run.rglob('*')) if p.is_file()}
        dump(run/'COMPLETE.json',dict(status='COMPLETE',utc=utc(),mode=mode,blocks=len(reports),controls_pass=True,
            seconds=time.monotonic()-tick,outputs_sha256=outputs,primary_decision=summary['primary']['decision']))
        print(json.dumps(dict(status='COMPLETE',seconds=time.monotonic()-tick,primary=summary['primary'])))
    except BaseException:
        failure=dict(status='FAILED',utc=utc(),seconds=time.monotonic()-tick,completed_blocks=[r['task'] for r in reports],
            traceback=traceback.format_exc(),automatic_restart=False)
        dump(run/'FAILED.json',failure);dump(run/'STATUS.json',failure);raise


def preflight():
    target=HERE/'analysis/preflight_v1.json';assert not target.exists();tests();tick=time.monotonic();resources=inventory(1)
    data.registry(all_files=True);blocks={}
    for b in settings('scientific')['blocks']:
        _,_,item=experiment.prepare('scientific',b);blocks[str(b)]=item
    total=sum(v['evaluated_context_draws'] for v in blocks.values());work=sum(v['evaluated_variant_draws'] for v in blocks.values())
    assert total==4096 and work==6520 and sum(v['eligible_context_draws'] for v in blocks.values())==808
    assert sum(sum(v['affected_by_draw']) for v in blocks.values())==784
    dump(target,dict(status='PASS',utc=utc(),seconds=time.monotonic()-tick,blocks=blocks,resources=resources,
        evaluated_context_draws=total,evaluated_variant_draws=work,no_new_scientific_readers=True,
        inputs_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs('benchmark')}))
    print(json.dumps(dict(status='PASS',blocks=len(blocks),evaluated_context_draws=total,evaluated_variant_draws=work,seconds=time.monotonic()-tick)))


def qualify(name,figures_inspected):
    assert figures_inspected,'Inspect the retained technical figure before qualification'
    run,c=verify(name);assert c['mode']=='benchmark';assert not (HERE/'SAMPLE_FREEZE.json').exists()
    current={str(p.relative_to(ROOT)):sha(p) for p in inputs('benchmark')}
    assert json.loads((run/'manifest.json').read_text())['inputs_sha256']==current
    pre=json.loads((HERE/'analysis/preflight_v1.json').read_text());assert pre['status']=='PASS' and pre['inputs_sha256']==current
    reports=[json.loads(p.read_text()) for p in run.glob('block_*.json')];assert len(reports)==2
    unit=max(r['reader_seconds']/r['evaluated_variant_steps'] for r in reports if r['evaluated_variant_steps'])
    static=4*max(r['static_seconds'] for r in reports)
    block_seconds=[unit*x['evaluated_variant_draws']*2048+static for x in pre['blocks'].values()]
    resources=inventory();workers=min(4,12-resources['other_busy_capacity'],len(resources['affinity']));assert workers>=1
    forecasts={}
    for w in range(1,5):
        # A list-scheduling upper bound, also allowing the longest eligible block.
        bound=sum(block_seconds)/w+(1-1/w)*max(block_seconds)
        forecasts[str(w)]=dict(expected_seconds=bound+120,conservative_seconds=3*bound+120)
    raw=sum(sum(i.file_size for i in zipfile.ZipFile(p).infolist()) for p in run.glob('assay_*.npz'))
    benchmark_work=sum(r['evaluated_variant_draws'] for r in reports);scientific_work=pre['evaluated_variant_draws']
    remaining=sum(p.stat().st_size for p in run.rglob('*') if p.is_file() and not p.name.startswith('assay_'))
    reserve=math.ceil(1.5*(raw*max(4,scientific_work/max(1,benchmark_work))+64*remaining))+256*1024**2
    assert resources['free_bytes']>reserve
    forecast=dict(utc=utc(),block_reports=reports,reader_seconds_per_variant_step=unit,static_seconds_per_block=static,
        block_seconds=block_seconds,summary_allowance_seconds=120,timing_margin=3,forecasts_by_workers=forecasts,
        workers=workers,**forecasts[str(workers)],storage_reserve_bytes=reserve,
        detach_required=forecasts[str(workers)]['conservative_seconds']>600)
    dump(HERE/'analysis/forecast_v1.json',forecast)
    evidence={str(p.relative_to(ROOT)):sha(p) for p in (run/'COMPLETE.json',run/'CHECKS.json',run/'comparison.png',tests(),
              HERE/'analysis/forecast_v1.json',HERE/'analysis/preflight_v1.json')}
    dump(HERE/'analysis/qualification_v1.json',dict(status='PASS',utc=utc(),figures_inspected=True,evidence=evidence,
        outputs_verified=len(c['outputs_sha256']),inputs_sha256=current))
    dump(HERE/'SAMPLE_FREEZE.json',dict(utc=utc(),settings=settings('scientific'),resources=resources,
        qualification_sha256=sha(HERE/'analysis/qualification_v1.json'),no_scientific_fresh_reader_outcomes_seen=True,
        packet_inventory_sha256=sha(HERE/'analysis/preflight_v1.json'),all_sources_retained=True))
    print(json.dumps(dict(workers=workers,**forecasts[str(workers)],detach_required=forecast['detach_required'],storage_reserve_bytes=reserve)))


def launch(name):
    qualification();forecast=json.loads((HERE/'analysis/forecast_v1.json').read_text());workers=forecast['workers']
    resources=inventory(workers);assert resources['free_bytes']>forecast['storage_reserve_bytes']
    burden={cpu:sum(r['sampled_cpu_percent']/len(r['affinity']) for r in resources['other_busy_processes'] if cpu in r['affinity']) for cpu in resources['affinity']}
    selected=sorted(sorted(burden,key=lambda cpu:(burden[cpu],cpu))[:workers]);assert len(selected)==workers
    os.sched_setaffinity(0,selected);resources['selected_affinity']=selected
    job=new_run(HERE/'jobs'/name,inputs('scientific'),dict(**settings('scientific'),workers=workers))
    if not forecast['detach_required']:
        dump(job/'launch.json',dict(utc=utc(),pid=os.getpid(),workers=workers,detached=False,forecast=forecast,resources=resources))
        execute('scientific',name,workers);return
    with (job/'run.log').open('xb') as log:
        proc=subprocess.Popen([sys.executable,'-B',str(HERE/'run.py'),'execute','--mode','scientific','--name',name,'--workers',str(workers)],
            cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    dump(job/'launch.json',dict(utc=utc(),pid=proc.pid,workers=workers,detached=True,resources=resources,
        forecast=forecast,automatic_restart=False,automatic_successor=False))
    deadline=time.monotonic()+30
    while time.monotonic()<deadline and proc.poll() is None:
        try:s=json.loads((HERE/'runs'/name/'STATUS.json').read_text())
        except (FileNotFoundError,json.JSONDecodeError):time.sleep(.2);continue
        assert s['status']=='RUNNING';check_inputs(job);check_inputs(HERE/'runs'/name)
        assert os.getsid(proc.pid)==proc.pid and os.readlink(f'/proc/{proc.pid}/fd/0')=='/dev/null'
        dump(job/'startup.json',dict(status='PASS',utc=utc(),pid=proc.pid,workers=workers,
            detached=True,stdin='/dev/null',automatic_progress_polling=False,observed_status=s))
        print(json.dumps(dict(status='STARTED',pid=proc.pid,workers=workers,expected_seconds=forecast['expected_seconds'],
            conservative_seconds=forecast['conservative_seconds'])));return
    raise RuntimeError('Startup incomplete; preserve the job and logs; no automatic restart')


def closeout(name,figures_inspected):
    assert figures_inspected;run,c=verify(name);assert c['mode']=='scientific';p=HERE/'analysis/closeout_v1.json';assert not p.exists()
    checks=json.loads((run/'CHECKS.json').read_text());assert checks['status']=='PASS' and checks['blocks']==32
    assert checks['contexts']==2048 and checks['context_draw_rows']==4096 and checks['evaluated_context_draws']==4096
    assert checks['eligible_context_draws']==808 and checks['evaluated_variant_draws']==6520
    dump(p,dict(status='PASS',utc=utc(),complete_sha256=sha(run/'COMPLETE.json'),checks=checks,
        seconds=c['seconds'],outputs_verified=len(c['outputs_sha256']),frozen_inputs_verified=len(json.loads((run/'manifest.json').read_text())['inputs_sha256']),
        figure_sha256=sha(run/'comparison.png'),figures_inspected=True,
        retained_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()),automatic_successor=False))
    print(json.dumps(dict(status='PASS',seconds=c['seconds'],primary_decision=c['primary_decision'])))


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=('register','execute','preflight','qualify','launch','verify','closeout'))
    p.add_argument('--mode',choices=('benchmark','scientific'),default='benchmark');p.add_argument('--name',default='benchmark_v1')
    p.add_argument('--workers',type=int,default=1);p.add_argument('--figures-inspected',action='store_true');a=p.parse_args()
    (HERE/'analysis').mkdir(exist_ok=True)
    try:
        if a.action=='register':data.register()
        elif a.action=='execute':cap_cpus(a.workers);execute(a.mode,a.name,a.workers)
        elif a.action=='preflight':cap_cpus(1);preflight()
        elif a.action=='qualify':qualify(a.name,a.figures_inspected)
        elif a.action=='launch':launch(a.name)
        elif a.action=='verify':run,c=verify(a.name);print(json.dumps(dict(status='PASS',outputs=len(c['outputs_sha256']))))
        elif a.action=='closeout':closeout(a.name,a.figures_inspected)
    except BaseException:
        i=1
        while (HERE/f'analysis/{a.action}_failure_{i:03d}.json').exists():i+=1
        dump(HERE/f'analysis/{a.action}_failure_{i:03d}.json',dict(utc=utc(),action=a.action,name=a.name,
            traceback=traceback.format_exc(),automatic_restart=False));raise


if __name__=='__main__':main()
