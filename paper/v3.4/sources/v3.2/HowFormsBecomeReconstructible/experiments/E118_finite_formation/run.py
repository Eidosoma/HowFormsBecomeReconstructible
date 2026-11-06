"""Tests, excluded timing, frozen execution and bounded detached startup."""
import argparse
import ast
from concurrent.futures import ProcessPoolExecutor,as_completed
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import cap_cpus,check_inputs,dump,new_run,sha,utc
from E118_finite_formation import data,experiment,inference
from E118_finite_formation.plan import HERE,ROOT,settings,key


def code_paths():
    paths=set(HERE.glob('*.py'))|{HERE/'PROTOCOL.md',HERE/'DATA_DICTIONARY.md',ROOT/'E116_finite_resolution_pruning/PLAN.json'}
    paths|={ROOT/p for p in ('common.py','run_python.sh','RUN_POLICY.md')}
    pending=[p for p in paths if p.suffix=='.py'];seen=set()
    while pending:
        p=pending.pop()
        if p in seen:continue
        seen.add(p)
        for node in ast.walk(ast.parse(p.read_text())):
            names=[]
            if isinstance(node,ast.Import):names=[a.name for a in node.names]
            elif isinstance(node,ast.ImportFrom) and node.module:
                names=[node.module]+[node.module+'.'+a.name for a in node.names]
            for name in names:
                q=ROOT/(name.replace('.','/')+'.py')
                if q.is_file() and q not in paths:paths.add(q);pending.append(q)
    return sorted(paths)


def inventory(workers=None):
    def sample():
        out={}
        for p in Path('/proc').iterdir():
            if not p.name.isdigit() or int(p.name)==os.getpid():continue
            try:
                args=(p/'cmdline').read_bytes().split(b'\0');name=Path(os.fsdecode(args[0])).name
                if not (name.startswith(('python','pytest')) or name in ('R','Rscript')):continue
                raw=(p/'stat').read_text();s=raw[raw.rfind(')')+2:].split()
                out[int(p.name)]=dict(ticks=int(s[11])+int(s[12]),threads=int(s[17]),affinity=sorted(os.sched_getaffinity(int(p.name))))
            except (OSError,ValueError,IndexError):pass
        return out
    before=sample();tick=time.monotonic();time.sleep(1);after=sample();elapsed=time.monotonic()-tick;busy=[]
    for pid,r in after.items():
        use=(r['ticks']-before.get(pid,r)['ticks'])/os.sysconf('SC_CLK_TCK')/elapsed
        if use>=.2:busy.append(dict(pid=pid,sampled_cpu_percent=100*use,**r))
    capacity=sum(min(r['threads'],len(r['affinity'])) for r in busy)
    result=dict(utc=utc(),other_busy_processes=busy,other_busy_capacity=capacity,
        free_bytes=shutil.disk_usage(HERE).free,affinity=sorted(os.sched_getaffinity(0)),total_cpu_ceiling=12)
    if workers is not None and workers+capacity>12:raise RuntimeError('CPU guard: '+json.dumps(result))
    return result


def latest_tests():
    p=sorted((HERE/'analysis').glob('tests_attempt_*.json'))[-1];t=json.loads(p.read_text())
    assert t['status']=='PASS' and t['complete_reference_replay']
    assert t['inputs_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in code_paths()}
    assert t['registry_sha256']==sha(HERE/'SOURCE_DATA.json')
    return p


def inputs(mode):
    result=code_paths()+[HERE/'SOURCE_DATA.json',latest_tests()]
    if mode=='scientific':result += [HERE/'SAMPLE_FREEZE.json',HERE/'analysis/qualification_v1.json',HERE/'analysis/forecast_v1.json']
    return result


def qualification():
    q=json.loads((HERE/'analysis/qualification_v1.json').read_text());assert q['status']=='PASS'
    for p,h in q['evidence'].items():assert sha(ROOT/p)==h,p
    assert q['inputs_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in inputs('benchmark')}
    f=json.loads((HERE/'SAMPLE_FREEZE.json').read_text())
    assert f['settings']==settings('scientific') and f['before_scientific_acquisition']
    assert f['qualification_sha256']==sha(HERE/'analysis/qualification_v1.json')
    return q


def worker(mode,task,cfg,run):
    check_inputs(run)
    return experiment.block(mode,task,cfg,run)


def execute(mode,name,workers):
    tick=time.monotonic();cfg=settings(mode);latest_tests();assert 1<=workers<=4
    if mode=='scientific':qualification();check_inputs(HERE/'jobs'/name)
    else:assert workers==1
    run=new_run(HERE/'runs'/name,inputs(mode),dict(**cfg,workers=workers));reports=[]
    def status(state,stage):
        dump(run/'STATUS.json',dict(status=state,stage=stage,utc=utc(),pid=os.getpid(),workers=workers,
            completed_blocks=sorted(r['task'] for r in reports),total_blocks=len(cfg['blocks']),
            seconds=time.monotonic()-tick,automatic_restart=False,automatic_extension=False,automatic_successor=False))
    try:
        status('RUNNING','resource_and_source_verification')
        dump(run/'resources.json',inventory(workers));data.registry(full=True);data.fresh_audit()
        rows=[];erased=[];status('RUNNING','finite_formation_and_independent_replay')
        def accept(result):
            part,controls,report=result;rows.extend(part);erased.extend(controls);reports.append(report)
            status('RUNNING','finite_formation_and_independent_replay')
            print(f"Checked source {report['task']}: {report['seconds']:.2f} s; fresh finite histories",flush=True)
        if workers==1:
            for b in cfg['blocks']:accept(worker(mode,b,cfg,run))
        else:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                futures=[pool.submit(worker,mode,b,cfg,run) for b in cfg['blocks']]
                for f in as_completed(futures):accept(f.result())
        rows.sort(key=lambda r:key(r)+(r['regime'],))
        erased.sort(key=lambda r:(r['task'],r['draw'],r['regime'],r['stage'],r['common'],r['founder'],r['recipient']))
        status('RUNNING','clustered_inference');summary,events=inference.summarize(rows,cfg)
        data.export(run/'cases.csv',rows);data.export(run/'erased.csv',erased)
        if events:data.export(run/'events.csv',events)
        else:(run/'events.csv').write_text(','.join(list(rows[0])+[e+'_finite_event' for e in inference.ENDPOINTS])+'\n')
        dump(run/'summary.json',summary);(run/'REPORT.md').write_text(inference.report(summary));inference.plot(run,summary)
        checks=dict(status='PASS',blocks=len(reports),condition_rows=len(rows),context_draw_rows=len(rows)//len(cfg['regimes']),
            erased_rows=len(erased),event_rows=len(events),new_source_blocks=len(reports),
            new_record_steps=sum(r['ancestry_record_steps']+r['endpoint_record_steps'] for r in reports),all_new_steps_independently_replayed=True,
            all_original_endpoints_and_harms_retained=True,independent_reference_histories=True,
            independent_block_values_checked=summary['independent_block_values_checked'],
            all_sources_retained=True,no_outcome_selection=True,finite_from_first_commit=True)
        dump(run/'CHECKS.json',checks);check_inputs(run);data.registry(full=True)
        if mode=='scientific':check_inputs(HERE/'jobs'/name)
        status('COMPLETE','finished')
        outputs={str(p.relative_to(run)):sha(p) for p in sorted(run.rglob('*')) if p.is_file()}
        dump(run/'COMPLETE.json',dict(status='COMPLETE',utc=utc(),mode=mode,seconds=time.monotonic()-tick,
            outputs_sha256=outputs,controls_pass=True,primary=summary['primary'],blocks=len(reports)))
        print(json.dumps(dict(status='COMPLETE',seconds=time.monotonic()-tick,primary=summary['primary']['decision'])),flush=True)
    except BaseException:
        failure=dict(status='FAILED',utc=utc(),seconds=time.monotonic()-tick,
            completed_blocks=[r['task'] for r in reports],traceback=traceback.format_exc(),automatic_restart=False)
        dump(run/'FAILED.json',failure);dump(run/'STATUS.json',failure);raise


def verify(name):
    run=HERE/'runs'/name;check_inputs(run);c=json.loads((run/'COMPLETE.json').read_text())
    assert c['status']=='COMPLETE' and c['controls_pass']
    for p,h in c['outputs_sha256'].items():assert sha(run/p)==h,p
    data.registry(full=True);return run,c


def qualify(name):
    run,c=verify(name);assert c['mode']=='benchmark' and c['blocks']==2
    assert not (HERE/'SAMPLE_FREEZE.json').exists()
    current={str(p.relative_to(ROOT)):sha(p) for p in inputs('benchmark')}
    assert json.loads((run/'manifest.json').read_text())['inputs_sha256']==current
    reports=[json.loads(p.read_text()) for p in run.glob('block_*.json')]
    science=settings('scientific');bench=settings('benchmark')
    details=[]
    for r in reports:
        stage={}
        for name,seconds in r['timings'].items():
            if name in ('E022','E058','recovery'):
                scale=science['source_steps']['read_steps']/bench['source_steps']['read_steps']
            elif name=='E055':
                scale=(science['body']['body_pre_steps']+science['body']['pulse_steps'])/(bench['body']['body_pre_steps']+bench['body']['pulse_steps'])
            elif name=='writer' or name.startswith('assay_r'):
                scale=science['steps']['read_steps']/bench['steps']['read_steps']
            elif name=='storage':scale=2.
            else:scale=1.
            stage[name]=dict(seconds=seconds,scale=scale,scaled=seconds*scale)
        details.append(dict(task=r['task'],stages=stage,cost=sum(x['scaled'] for x in stage.values())+2*r['static_other_seconds']))
    cost=max(d['cost'] for d in details)
    resources=inventory();workers=min(4,12-resources['other_busy_capacity'],len(resources['affinity']));assert workers>=1
    actual_summary=max(0.,c['seconds']-sum(r['seconds'] for r in reports))
    summary_allowance=max(240.,actual_summary*16)
    forecasts={str(w):dict(expected_seconds=math.ceil(32/w)*cost+summary_allowance,
        conservative_seconds=3*math.ceil(32/w)*cost+summary_allowance) for w in range(1,5)}
    raw=0
    for p in run.glob('*.npz'):
        with zipfile.ZipFile(p) as z:
            for info in z.infolist():raw+=info.file_size*(16 if 'hashes' in info.filename else 1)
    other=sum(p.stat().st_size for p in run.rglob('*') if p.is_file() and p.suffix!='.npz')
    reserve=math.ceil(1.5*(raw*16+other*32))+1024**3
    assert resources['free_bytes']>reserve
    assert forecasts[str(workers)]['conservative_seconds']<science['conservative_resource_limit_seconds']
    forecast=dict(utc=utc(),workers=workers,**forecasts[str(workers)],forecasts_by_workers=forecasts,
        details=details,summary_allowance_seconds=summary_allowance,storage_reserve_bytes=reserve,
        detach_required=forecasts[str(workers)]['conservative_seconds']>600,
        method='Full recipient-width, five-formulation, 32-boundary benchmark; scale each stage including replay; fixed 32 fresh sources')
    dump(HERE/'analysis/forecast_v1.json',forecast)
    evidence={str(p.relative_to(ROOT)):sha(p) for p in (run/'COMPLETE.json',run/'CHECKS.json',run/'finite_formation.png',
        latest_tests(),HERE/'analysis/forecast_v1.json')}
    dump(HERE/'analysis/qualification_v1.json',dict(status='PASS',utc=utc(),evidence=evidence,
        figures_inspected=True,outputs_verified=len(c['outputs_sha256']),inputs_sha256=current))
    dump(HERE/'SAMPLE_FREEZE.json',dict(utc=utc(),settings=settings('scientific'),
        before_scientific_acquisition=True,old_outcomes_known=False,
        source_registry_sha256=sha(HERE/'SOURCE_DATA.json'),resources=resources,
        qualification_sha256=sha(HERE/'analysis/qualification_v1.json')))
    print(json.dumps(forecast))


def launch(name):
    qualification();forecast=json.loads((HERE/'analysis/forecast_v1.json').read_text());workers=forecast['workers']
    resources=inventory(workers);assert resources['free_bytes']>forecast['storage_reserve_bytes']
    burden={cpu:sum(r['sampled_cpu_percent']/len(r['affinity']) for r in resources['other_busy_processes'] if cpu in r['affinity']) for cpu in resources['affinity']}
    selected=sorted(sorted(burden,key=lambda cpu:(burden[cpu],cpu))[:workers]);os.sched_setaffinity(0,selected)
    resources['selected_affinity']=selected
    job=new_run(HERE/'jobs'/name,inputs('scientific'),dict(**settings('scientific'),workers=workers))
    # Detach all scientific work; the forecast normally exceeds ten minutes.
    with (job/'run.log').open('xb') as log:
        proc=subprocess.Popen(['bash',str(ROOT/'run_python.sh'),str(HERE/'run.py'),'execute',
            '--mode','scientific','--name',name,'--workers',str(workers)],cwd=ROOT,
            stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    dump(job/'launch.json',dict(utc=utc(),pid=proc.pid,detached=True,workers=workers,resources=resources,
        forecast=forecast,stdin='/dev/null',automatic_restart=False,automatic_successor=False))
    deadline=time.monotonic()+45
    while time.monotonic()<deadline and proc.poll() is None:
        try:s=json.loads((HERE/'runs'/name/'STATUS.json').read_text())
        except (FileNotFoundError,json.JSONDecodeError):time.sleep(.25);continue
        if s['status']=='FAILED':raise RuntimeError(s)
        if s.get('stage')=='finite_formation_and_independent_replay':
            check_inputs(job);check_inputs(HERE/'runs'/name)
            assert (HERE/'runs'/name/'resources.json').exists()
            assert os.getsid(proc.pid)==proc.pid and os.readlink(f'/proc/{proc.pid}/fd/0')=='/dev/null'
            dump(job/'startup.json',dict(status='PASS',utc=utc(),pid=proc.pid,workers=workers,
                stage=s['stage'],resource_gate_passed=True,automatic_polling=False))
            print(json.dumps(dict(status='RUNNING',pid=proc.pid,workers=workers,
                expected_seconds=forecast['expected_seconds'],conservative_seconds=forecast['conservative_seconds'])));return
        time.sleep(.25)
    dump(job/'startup_failed.json',dict(status='FAILED',utc=utc(),automatic_restart=False))
    raise RuntimeError('Startup not established; preserve evidence and review, no restart loop')


def closeout(name):
    run,c=verify(name);assert c['mode']=='scientific' and c['blocks']==32
    qualification();check_inputs(HERE/'jobs'/name)
    checks=json.loads((run/'CHECKS.json').read_text())
    assert checks['context_draw_rows']==4096 and checks['condition_rows']==20480 and checks['finite_from_first_commit']
    target=HERE/'analysis/closeout_v1.json';assert not target.exists()
    dump(target,dict(status='PASS',utc=utc(),complete_sha256=sha(run/'COMPLETE.json'),checks=checks,
        outputs_verified=len(c['outputs_sha256']),inputs_verified=len(inputs('scientific')),
        figure_sha256=sha(run/'finite_formation.png'),figures_inspected=True,seconds=c['seconds'],
        retained_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()),automatic_successor=False))
    print(json.dumps(dict(status='PASS',seconds=c['seconds'],primary=c['primary']['decision'])))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('register','execute','qualify','launch','verify','closeout'))
    p.add_argument('--mode',choices=('benchmark','scientific'),default='benchmark');p.add_argument('--name',default='benchmark_v1')
    p.add_argument('--workers',type=int,default=1);p.add_argument('--figures-inspected',action='store_true');a=p.parse_args()
    (HERE/'analysis').mkdir(exist_ok=True)
    try:
        if a.action=='register':cap_cpus(1);data.register()
        elif a.action=='execute':cap_cpus(a.workers);execute(a.mode,a.name,a.workers)
        elif a.action=='launch':launch(a.name)
        elif a.action=='verify':_,c=verify(a.name);print(json.dumps(dict(status='PASS',outputs=len(c['outputs_sha256']))))
        else:
            assert a.figures_inspected
            qualify(a.name) if a.action=='qualify' else closeout(a.name)
    except BaseException:
        i=1
        while (HERE/f'analysis/{a.action}_failure_{i:03d}.json').exists():i+=1
        dump(HERE/f'analysis/{a.action}_failure_{i:03d}.json',dict(utc=utc(),traceback=traceback.format_exc(),automatic_restart=False));raise
