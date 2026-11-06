"""One-worker static diagnosis, excluded benchmark and immutable receipts."""
import argparse
import ast
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import cap_cpus,check_inputs,dump,new_run,sha,utc
from E117_saved_finite_sensitivity import data,analysis,inference
from E117_saved_finite_sensitivity.plan import HERE,ROOT,COPY_NAMES,settings,key

def inventory(workers=1):
    def snapshot():
        out={}
        for p in Path('/proc').iterdir():
            if not p.name.isdigit() or int(p.name)==os.getpid():continue
            try:
                args=(p/'cmdline').read_bytes().split(b'\0');name=Path(os.fsdecode(args[0])).name
                if not (name.startswith(('python','pytest')) or name in ('R','Rscript')):continue
                s=(p/'stat').read_text();s=s[s.rfind(')')+2:].split()
                out[int(p.name)]=dict(ticks=int(s[11])+int(s[12]),threads=int(s[17]),affinity=sorted(os.sched_getaffinity(int(p.name))))
            except (OSError,ValueError,IndexError):pass
        return out
    a=snapshot();tick=time.monotonic();time.sleep(1);b=snapshot();dt=time.monotonic()-tick;busy=[]
    for pid,r in b.items():
        use=(r['ticks']-a.get(pid,r)['ticks'])/os.sysconf('SC_CLK_TCK')/dt
        if use>=.2:busy.append(dict(pid=pid,sampled_cpu_percent=use*100,**r))
    capacity=sum(min(r['threads'],len(r['affinity'])) for r in busy)
    result=dict(utc=utc(),other_busy_capacity=capacity,other_busy_processes=busy,
        affinity=sorted(os.sched_getaffinity(0)),free_bytes=shutil.disk_usage(HERE).free,total_cpu_ceiling=12)
    assert workers+capacity<=12,result
    return result

def code_paths():
    paths=set(HERE.glob('*.py'))|{HERE/'PROTOCOL.md',HERE/'DATA_DICTIONARY.md'}
    paths|={ROOT/p for p in ('common.py','run_python.sh','RUN_POLICY.md')};pending=[p for p in paths if p.suffix=='.py'];seen=set()
    while pending:
        p=pending.pop()
        if p in seen:continue
        seen.add(p)
        for n in ast.walk(ast.parse(p.read_text())):
            names=[a.name for a in n.names] if isinstance(n,ast.Import) else [n.module]+[n.module+'.'+a.name for a in n.names] if isinstance(n,ast.ImportFrom) and n.module else []
            for name in names:
                q=ROOT/(name.replace('.','/')+'.py')
                if q.is_file() and q not in paths:paths.add(q);pending.append(q)
    return sorted(paths)

def tests():
    p=sorted((HERE/'analysis').glob('tests_attempt_*.json'))[-1];t=json.loads(p.read_text())
    assert t['status']=='PASS'
    assert t['inputs_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in code_paths()}
    assert t['registry_sha256']==sha(HERE/'SOURCE_DATA.json');return p

def inputs(mode):
    paths=code_paths()+[HERE/'SOURCE_DATA.json',tests()]
    if mode=='scientific':paths += [HERE/'SAMPLE_FREEZE.json',HERE/'analysis/qualification_v1.json',HERE/'analysis/forecast_v1.json']
    return paths

def qualification():
    q=json.loads((HERE/'analysis/qualification_v1.json').read_text());assert q['status']=='PASS'
    for p,h in q['evidence'].items():assert sha(ROOT/p)==h,p
    assert q['inputs_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in inputs('benchmark')}
    f=json.loads((HERE/'SAMPLE_FREEZE.json').read_text());assert f['settings']==settings('scientific') and f['before_scientific_extraction']
    assert f['qualification_sha256']==sha(HERE/'analysis/qualification_v1.json');return q

def execute(mode,name):
    tick=time.monotonic();cfg=settings(mode);tests()
    if mode=='scientific':qualification();check_inputs(HERE/'jobs'/name)
    run=new_run(HERE/'runs'/name,inputs(mode),cfg);reports=[]
    def status(state,stage):
        dump(run/'STATUS.json',dict(status=state,stage=stage,utc=utc(),pid=os.getpid(),workers=1,
            completed_blocks=[r['task'] for r in reports],total_blocks=len(cfg['blocks']),seconds=time.monotonic()-tick,
            no_new_dynamics=True,automatic_restart=False,automatic_successor=False))
    try:
        status('RUNNING','resource_and_source_verification');dump(run/'resources.json',inventory())
        data.registry(mode,full=True);known=data.cases(mode);data.copy_tables(mode,run)
        prior=json.loads(data.raw(mode,'summary.json'));rows=[]
        status('RUNNING','saved_measurements_and_independent_checks')
        for task in cfg['blocks']:
            part,arrays,report=analysis.block(mode,task,known);data.save(run/f'derived_{task}.npz',arrays)
            data.export(run/f'features_{task}.csv',part);rows.extend(part);reports.append(report);dump(run/f'block_{task}.json',report)
            status('RUNNING','saved_measurements_and_independent_checks');print(f"Checked {task}: {report['seconds']:.2f}s",flush=True)
        rows.sort(key=key);assert {key(r) for r in rows}==set(known)
        status('RUNNING','descriptive_summaries');summary,events=inference.summarize(rows,cfg,prior)
        data.export(run/'case_features.csv',rows);data.export(run/'feature_events.csv',events,list(rows[0]))
        dump(run/'summary.json',summary);(run/'REPORT.md').write_text(inference.report(summary));inference.plot(run,summary)
        checks=dict(status='PASS',blocks=len(reports),condition_rows=len(rows),context_draw_rows=len(rows)//8,
            independent_metric_values=sum(r['independent_metric_values'] for r in reports),
            score_values_checked=sum(r['score_values_checked'] for r in reports),
            original_block_values_checked=summary['original_block_values_checked'],
            preserved_source_tables=len(COPY_NAMES),events=len(events),no_new_dynamics=True,
            earlier_primary_unchanged=summary['unchanged_E116_primary']==prior['primary'],
            all_original_endpoints_and_harms_retained=True,all_sources_retained=True)
        dump(run/'CHECKS.json',checks);check_inputs(run);data.registry(mode,full=True)
        if mode=='scientific':check_inputs(HERE/'jobs'/name)
        status('COMPLETE','finished')
        outputs={str(p.relative_to(run)):sha(p) for p in sorted(run.rglob('*')) if p.is_file()}
        dump(run/'COMPLETE.json',dict(status='COMPLETE',utc=utc(),mode=mode,seconds=time.monotonic()-tick,
            blocks=len(reports),controls_pass=True,outputs_sha256=outputs,no_new_dynamics=True,
            conclusion='EXPLORATORY_SAVED_FINITE_SENSITIVITY',prior_primary_unchanged=True))
        print(json.dumps(dict(status='COMPLETE',seconds=time.monotonic()-tick,blocks=len(reports))),flush=True)
    except BaseException:
        failure=dict(status='FAILED',utc=utc(),seconds=time.monotonic()-tick,completed_blocks=[r['task'] for r in reports],
            traceback=traceback.format_exc(),automatic_restart=False)
        dump(run/'FAILED.json',failure);dump(run/'STATUS.json',failure);raise

def verify(name):
    run=HERE/'runs'/name;check_inputs(run);c=json.loads((run/'COMPLETE.json').read_text())
    assert c['status']=='COMPLETE' and c['controls_pass']
    for p,h in c['outputs_sha256'].items():assert sha(run/p)==h,p
    data.registry(c['mode'],full=True);return run,c

def qualify(name):
    run,c=verify(name);assert c['mode']=='benchmark' and c['blocks']==2
    assert not (HERE/'SAMPLE_FREEZE.json').exists()
    current={str(p.relative_to(ROOT)):sha(p) for p in inputs('benchmark')}
    assert current==json.loads((run/'manifest.json').read_text())['inputs_sha256']
    reports=[json.loads(p.read_text()) for p in run.glob('block_*.json')];reg=data.registry()
    work=32*max(r['seconds'] for r in reports)
    overhead=max(0.,c['seconds']-sum(r['seconds'] for r in reports));allowance=max(120.,overhead*16)
    expected=work+allowance;conservative=3*work+allowance
    copies=sum(x['bytes'] for n,x in reg['sources']['scientific']['files'].items() if n in COPY_NAMES)
    variable=sum(p.stat().st_size for p in run.rglob('*') if p.is_file() and not p.name.startswith('source_'))
    reserve=math.ceil(copies+1.5*variable*16)+256*1024**2
    resources=inventory();assert resources['free_bytes']>reserve
    forecast=dict(utc=utc(),expected_seconds=expected,conservative_seconds=conservative,storage_reserve_bytes=reserve,
        all_source_blocks=32,seconds_per_full_width_block=max(r['seconds'] for r in reports),
        summary_allowance_seconds=allowance,workers=1,detach_required=conservative>600,
        method='Same full-width static arrays; 32 times worst measured block, 16-fold measured overhead allowance; no dynamics')
    dump(HERE/'analysis/forecast_v1.json',forecast)
    evidence={str(p.relative_to(ROOT)):sha(p) for p in (run/'COMPLETE.json',run/'CHECKS.json',run/'diagnosis.png',tests(),HERE/'analysis/forecast_v1.json')}
    dump(HERE/'analysis/qualification_v1.json',dict(status='PASS',utc=utc(),evidence=evidence,
        outputs_verified=len(c['outputs_sha256']),figures_inspected=True,inputs_sha256=current))
    dump(HERE/'SAMPLE_FREEZE.json',dict(utc=utc(),settings=settings('scientific'),before_scientific_extraction=True,
        old_outcomes_known=True,no_new_dynamics=True,resources=resources,qualification_sha256=sha(HERE/'analysis/qualification_v1.json')))
    print(json.dumps(forecast))

def launch(name):
    qualification();resources=inventory();forecast=json.loads((HERE/'analysis/forecast_v1.json').read_text())
    assert resources['free_bytes']>forecast['storage_reserve_bytes']
    burden={cpu:sum(r['sampled_cpu_percent']/len(r['affinity']) for r in resources['other_busy_processes'] if cpu in r['affinity']) for cpu in resources['affinity']}
    chosen=[min(burden,key=lambda cpu:(burden[cpu],cpu))];os.sched_setaffinity(0,chosen);resources['selected_affinity']=chosen
    job=new_run(HERE/'jobs'/name,inputs('scientific'),settings('scientific'))
    if not forecast['detach_required']:
        dump(job/'launch.json',dict(utc=utc(),pid=os.getpid(),detached=False,workers=1,forecast=forecast,resources=resources))
        execute('scientific',name);return
    with (job/'run.log').open('xb') as log:
        proc=subprocess.Popen(['bash',str(ROOT/'run_python.sh'),str(HERE/'run.py'),'execute','--mode','scientific','--name',name],
            cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    dump(job/'launch.json',dict(utc=utc(),pid=proc.pid,detached=True,workers=1,forecast=forecast,resources=resources,
        automatic_restart=False,automatic_successor=False))
    deadline=time.monotonic()+45
    while time.monotonic()<deadline and proc.poll() is None:
        try:s=json.loads((HERE/'runs'/name/'STATUS.json').read_text())
        except (FileNotFoundError,json.JSONDecodeError):time.sleep(.25);continue
        if s['status']=='FAILED':raise RuntimeError(s)
        if s.get('stage')=='saved_measurements_and_independent_checks':
            check_inputs(job);check_inputs(HERE/'runs'/name)
            assert os.getsid(proc.pid)==proc.pid and os.readlink(f'/proc/{proc.pid}/fd/0')=='/dev/null'
            dump(job/'startup.json',dict(status='PASS',utc=utc(),pid=proc.pid,workers=1,resource_gate_passed=True,automatic_polling=False))
            print(json.dumps(dict(status='RUNNING',pid=proc.pid,expected_seconds=forecast['expected_seconds'],conservative_seconds=forecast['conservative_seconds'])));return
        time.sleep(.25)
    dump(job/'startup_failed.json',dict(status='FAILED',utc=utc(),automatic_restart=False));raise RuntimeError('Bounded startup not established')

def closeout(name):
    run,c=verify(name);assert c['mode']=='scientific' and c['blocks']==32;qualification();check_inputs(HERE/'jobs'/name)
    checks=json.loads((run/'CHECKS.json').read_text());assert checks['condition_rows']==32768 and checks['earlier_primary_unchanged']
    target=HERE/'analysis/closeout_v1.json';assert not target.exists()
    dump(target,dict(status='PASS',utc=utc(),complete_sha256=sha(run/'COMPLETE.json'),checks=checks,
        outputs_verified=len(c['outputs_sha256']),frozen_inputs_verified=len(inputs('scientific')),
        source_files_verified=len(data.registry()['sources']['scientific']['files']),figures_inspected=True,
        figure_sha256=sha(run/'diagnosis.png'),seconds=c['seconds'],no_new_dynamics=True,
        retained_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()),automatic_successor=False))
    print(json.dumps(dict(status='PASS',seconds=c['seconds'],outputs=len(c['outputs_sha256']))))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('register','execute','qualify','launch','verify','closeout'))
    p.add_argument('--mode',choices=('benchmark','scientific'),default='benchmark');p.add_argument('--name',default='benchmark_v1');p.add_argument('--figures-inspected',action='store_true');a=p.parse_args()
    (HERE/'analysis').mkdir(exist_ok=True)
    try:
        if a.action=='register':cap_cpus(1);data.register()
        elif a.action=='execute':cap_cpus(1);execute(a.mode,a.name)
        elif a.action=='launch':launch(a.name)
        elif a.action=='verify':_,c=verify(a.name);print(json.dumps(dict(status='PASS',outputs=len(c['outputs_sha256']))))
        else:
            assert a.figures_inspected
            qualify(a.name) if a.action=='qualify' else closeout(a.name)
    except BaseException:
        i=1
        while (HERE/f'analysis/{a.action}_failure_{i:03d}.json').exists():i+=1
        dump(HERE/f'analysis/{a.action}_failure_{i:03d}.json',dict(utc=utc(),traceback=traceback.format_exc(),automatic_restart=False));raise
