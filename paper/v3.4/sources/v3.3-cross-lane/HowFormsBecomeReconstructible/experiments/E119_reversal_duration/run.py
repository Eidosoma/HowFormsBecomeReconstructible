"""One bounded qualification and detached launch per authorized reviewer test."""
import argparse,ast,json,math,os,subprocess,sys,time,traceback,zipfile
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import dump,sha,utc,new_run,check_inputs
from E118_finite_formation.run import inventory
from E119_reversal_duration import data,experiment,inference,tests
from E119_reversal_duration.plan import ROOT,DIRECTORIES,settings,here

def code_paths():
    paths=set(here('duration').glob('*.py'))|{here(s)/'PROTOCOL.md' for s in DIRECTORIES}
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

def latest_tests():
    p=sorted((here('duration')/'analysis').glob('tests_attempt_*.json'))[-1]
    t=json.loads(p.read_text());assert t['status']=='PASS'
    assert t['inputs_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in code_paths()}
    for s,h in t['registries'].items():assert sha(here(s)/'SOURCE_DATA.json')==h
    return p

def inputs(study,mode):
    p=code_paths()+[here(study)/'SOURCE_DATA.json',latest_tests()]
    if mode=='scientific':p += [here(study)/'SAMPLE_FREEZE.json',here(study)/'analysis/qualification_v1.json',here(study)/'analysis/forecast_v1.json']
    return p

def qualification(study):
    q=json.loads((here(study)/'analysis/qualification_v1.json').read_text());assert q['status']=='PASS'
    assert q['inputs_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in inputs(study,'benchmark')}
    for p,h in q['evidence'].items():assert sha(ROOT/p)==h,p
    f=json.loads((here(study)/'SAMPLE_FREEZE.json').read_text())
    assert f['settings']==settings(study,'scientific') and f['before_new_scientific_outcomes']
    return q

def worker(study,mode,task,cfg,run):
    check_inputs(run);return experiment.block(study,mode,task,cfg,run)

def execute(study,mode,name,workers):
    start=time.monotonic();cfg=settings(study,mode);latest_tests();assert 1<=workers<=2
    if mode=='scientific':qualification(study);check_inputs(here(study)/'jobs'/name)
    else:assert workers==1
    run=new_run(here(study)/'runs'/name,inputs(study,mode),dict(**cfg,workers=workers))
    reports=[]
    def status(state,stage):dump(run/'STATUS.json',dict(status=state,stage=stage,utc=utc(),pid=os.getpid(),
        completed_blocks=sorted(r['task'] for r in reports),total_blocks=len(cfg['blocks']),workers=workers,
        seconds=time.monotonic()-start,automatic_restart=False,automatic_extension=False,automatic_successor=False))
    try:
        status('RUNNING','verifying_inputs_and_resources');dump(run/'resources.json',inventory(workers))
        data.verify(study,True)
        if study=='histories':data.fresh_audit()
        status('RUNNING','lineages_and_independent_replay');rows=[];mechanism=[]
        def accept(result):
            part,mech,report=result;rows.extend(part);mechanism.extend(mech);reports.append(report)
            status('RUNNING','lineages_and_independent_replay')
            print(f"Verified {study} block {report['task']}: {report['seconds']:.2f}s",flush=True)
        if workers==1:
            for task in cfg['blocks']:accept(worker(study,mode,task,cfg,run))
        else:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                futures=[pool.submit(worker,study,mode,b,cfg,run) for b in cfg['blocks']]
                for future in as_completed(futures):accept(future.result())
        fields=('task','regime','renewal_injury','reader','kind','history','founder','recipient','draw','generation','policy')
        rows.sort(key=lambda r:tuple(r[k] for k in fields))
        data.export(run/'cases.csv',rows);data.export(run/'mechanism.csv',mechanism)
        status('RUNNING','whole_source_inference');summary=inference.summarize(rows,cfg,run)
        dump(run/'summary.json',summary);(run/'REPORT.md').write_text(inference.report(summary));inference.plot(run,summary)
        checks=dict(status='PASS',blocks=len(reports),rows=len(rows),mechanism_rows=len(mechanism),
            record_steps=sum(r['record_steps'] for r in reports),all_new_steps_independently_replayed=True,
            all_sources_retained=True,assessment_feedback=False,transmit_after_failure=True,
            independent_block_values_checked=summary['independent_block_values_checked'])
        dump(run/'CHECKS.json',checks);check_inputs(run);data.verify(study,True)
        if mode=='scientific':check_inputs(here(study)/'jobs'/name)
        status('COMPLETE','finished')
        hashes={str(p.relative_to(run)):sha(p) for p in sorted(run.rglob('*')) if p.is_file()}
        dump(run/'COMPLETE.json',dict(status='COMPLETE',utc=utc(),study=study,mode=mode,seconds=time.monotonic()-start,
            controls_pass=True,outputs_sha256=hashes,blocks=len(reports),scientific_claim_allowed=mode=='scientific'))
        print(json.dumps(dict(status='COMPLETE',study=study,seconds=time.monotonic()-start)),flush=True)
    except BaseException:
        f=dict(status='FAILED',utc=utc(),study=study,seconds=time.monotonic()-start,traceback=traceback.format_exc(),
            completed_blocks=[r['task'] for r in reports],automatic_restart=False)
        dump(run/'FAILED.json',f);dump(run/'STATUS.json',f);raise

def verify(study,name):
    run=here(study)/'runs'/name;check_inputs(run);c=json.loads((run/'COMPLETE.json').read_text())
    assert c['status']=='COMPLETE' and c['controls_pass']
    for p,h in c['outputs_sha256'].items():assert sha(run/p)==h,p
    data.verify(study,True);return run,c

def qualify(study,name,workers):
    run,c=verify(study,name);assert c['mode']=='benchmark' and c['blocks']==1
    assert not (here(study)/'SAMPLE_FREEZE.json').exists()
    report=json.loads(next(run.glob('block_*.json')).read_text())
    # Full width/all stages, scaling read steps only; acquisition remains identical.
    science=settings(study,'scientific');bench=settings(study,'benchmark')
    stage_scales={'dynamics':16.,'acquisition':1.,'storage':2.}
    scaled=sum(v*stage_scales[k] for k,v in report['timings'].items())
    nonstage=max(0.,report['seconds']-sum(report['timings'].values()))
    scaled+=2*nonstage
    # Threefold allowance covers changes in exact aliases, compression and shared load.
    overhead=max(180.,32*max(0.,c['seconds']-report['seconds']))
    expected=math.ceil(32/workers)*scaled+overhead;conservative=3*math.ceil(32/workers)*scaled+overhead
    raw=0
    for p in run.glob('*.npz'):
        with zipfile.ZipFile(p) as z:
            raw+=sum(i.file_size*(16 if 'hashes' in i.filename else 1) for i in z.infolist())
    other=sum(p.stat().st_size for p in run.rglob('*') if p.is_file() and p.suffix!='.npz')
    reserve=math.ceil(1.5*32*(raw+other))+1024**3
    resources=inventory(workers);assert resources['free_bytes']>reserve
    assert conservative<science['conservative_resource_limit_seconds']
    forecast=dict(utc=utc(),study=study,workers=workers,expected_seconds=expected,conservative_seconds=conservative,
        benchmark_seconds=c['seconds'],scaled_per_source_seconds=scaled,analysis_allowance_seconds=overhead,
        timing_margin=3,storage_reserve_bytes=reserve,stage_scales=stage_scales,resources=resources,
        detach_required=conservative>600)
    out=here(study)/'analysis';out.mkdir(exist_ok=True);dump(out/'forecast_v1.json',forecast)
    hashes={str(p.relative_to(ROOT)):sha(p) for p in inputs(study,'benchmark')}
    evidence={str(p.relative_to(ROOT)):sha(p) for p in (run/'COMPLETE.json',run/'CHECKS.json',run/'results.png',latest_tests(),out/'forecast_v1.json')}
    dump(out/'qualification_v1.json',dict(status='PASS',utc=utc(),inputs_sha256=hashes,evidence=evidence,
        figures_inspected=True,outputs_verified=len(c['outputs_sha256'])))
    dump(here(study)/'SAMPLE_FREEZE.json',dict(utc=utc(),settings=science,before_new_scientific_outcomes=True,
        known_starting_sources=study!='histories',qualification_sha256=sha(out/'qualification_v1.json')))
    print(json.dumps(forecast))

def launch(study,name):
    qualification(study);f=json.loads((here(study)/'analysis/forecast_v1.json').read_text());workers=f['workers']
    res=inventory(workers);assert res['free_bytes']>f['storage_reserve_bytes']
    burden={cpu:sum(r['sampled_cpu_percent']/len(r['affinity']) for r in res['other_busy_processes'] if cpu in r['affinity']) for cpu in res['affinity']}
    selected=sorted(sorted(burden,key=lambda c:(burden[c],c))[:workers]);os.sched_setaffinity(0,selected);res['selected_affinity']=selected
    job=new_run(here(study)/'jobs'/name,inputs(study,'scientific'),dict(**settings(study,'scientific'),workers=workers))
    with (job/'run.log').open('xb') as log:
        proc=subprocess.Popen(['bash',str(ROOT/'run_python.sh'),str(here('duration')/'run.py'),'execute',
            '--study',study,'--mode','scientific','--name',name,'--workers',str(workers)],cwd=ROOT,
            stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    dump(job/'launch.json',dict(utc=utc(),pid=proc.pid,study=study,workers=workers,detached=True,
        stdin='/dev/null',resources=res,forecast=f,automatic_restart=False,automatic_successor=False))
    end=time.monotonic()+45
    while time.monotonic()<end and proc.poll() is None:
        try:s=json.loads((here(study)/'runs'/name/'STATUS.json').read_text())
        except (FileNotFoundError,json.JSONDecodeError):time.sleep(.25);continue
        if s['status']=='FAILED':raise RuntimeError(s)
        if s['stage']=='lineages_and_independent_replay':
            check_inputs(job);check_inputs(here(study)/'runs'/name)
            assert os.getsid(proc.pid)==proc.pid and os.readlink(f'/proc/{proc.pid}/fd/0')=='/dev/null'
            dump(job/'startup.json',dict(status='PASS',utc=utc(),pid=proc.pid,workers=workers,
                automatic_polling=False,resource_guard_passed=True))
            print(json.dumps(dict(status='RUNNING',study=study,pid=proc.pid,workers=workers,
                expected_seconds=f['expected_seconds'],conservative_seconds=f['conservative_seconds'])));return
        time.sleep(.25)
    dump(job/'startup_failed.json',dict(utc=utc(),pid=proc.pid,returncode=proc.poll()))
    raise RuntimeError('Bounded startup did not pass; inspect retained log, do not automatically restart')

def closeout(study,name):
    run,c=verify(study,name);assert c['mode']=='scientific'
    out=here(study)/'analysis/closeout_v1.json';assert not out.exists()
    dump(out,dict(status='PASS',utc=utc(),seconds=c['seconds'],outputs_verified=len(c['outputs_sha256']),
        inputs_verified=len(json.loads((run/'manifest.json').read_text())['inputs_sha256']),
        figures_inspected=True,complete_sha256=sha(run/'COMPLETE.json'),checks=json.loads((run/'CHECKS.json').read_text()),
        retained_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()),automatic_successor=False))
    print(out.read_text())

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['register','test','execute','qualify','launch','closeout'])
    p.add_argument('--study',choices=list(DIRECTORIES),default='duration');p.add_argument('--mode',choices=['benchmark','scientific'],default='benchmark')
    p.add_argument('--name',default='benchmark_v1');p.add_argument('--workers',type=int,default=1);p.add_argument('--figures-inspected',action='store_true')
    a=p.parse_args()
    if a.action=='register':
        for s in DIRECTORIES:data.register(s)
        print('Registered two saved-source tests and one fresh-history cohort.')
    elif a.action=='test':tests.run(code_paths())
    elif a.action=='execute':execute(a.study,a.mode,a.name,a.workers)
    elif a.action=='qualify':assert a.figures_inspected;qualify(a.study,a.name,a.workers)
    elif a.action=='launch':launch(a.study,a.name)
    elif a.action=='closeout':assert a.figures_inspected;closeout(a.study,a.name)
