"""Bounded qualification and detached E122 execution; no automatic successors."""
import argparse,json,math,os,shutil,subprocess,sys,time,traceback
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import check_inputs,dump,new_run,sha,utc
from E122_specificity_ceiling_and_tail import sources,experiment,inference,tests
from E122_specificity_ceiling_and_tail.plan import ROOT,HERE,settings

def code_paths():
    return sorted(set(HERE.glob('*.py'))|{HERE/'PROTOCOL.md',HERE/'DATA_DICTIONARY.md'}|
        {ROOT/p for p in ('common.py','run_python.sh','RUN_POLICY.md','E006_compact_renewal/run.py',
                         'E001_unprescribed_capture/model.py','E001_unprescribed_capture/analyze.py')})

def inventory(workers=0):
    def sample():
        out={}
        for p in Path('/proc').iterdir():
            if not p.name.isdigit() or int(p.name)==os.getpid():continue
            try:
                args=(p/'cmdline').read_bytes().split(b'\0');name=Path(os.fsdecode(args[0])).name
                if not (name.startswith(('python','pytest')) or name in ('R','Rscript')):continue
                line=(p/'stat').read_text();s=line[line.rfind(')')+2:].split()
                out[int(p.name)]=dict(ticks=int(s[11])+int(s[12]),threads=int(s[17]),affinity=sorted(os.sched_getaffinity(int(p.name))))
            except (OSError,ValueError,IndexError):pass
        return out
    before=sample();start=time.monotonic();time.sleep(1);after=sample();elapsed=time.monotonic()-start
    busy=[]
    for pid,r in after.items():
        use=(r['ticks']-before.get(pid,r)['ticks'])/os.sysconf('SC_CLK_TCK')/elapsed
        if use>=.2:busy.append(dict(pid=pid,sampled_cpu_percent=100*use,**r))
    capacity=sum(min(v['threads'],len(v['affinity'])) for v in busy)
    if capacity+workers>12:raise RuntimeError('Shared twelve-CPU ceiling would be exceeded')
    affinity=sorted(os.sched_getaffinity(0));occupied={c for v in busy if len(v['affinity'])<=v['threads'] for c in v['affinity']}
    return dict(utc=utc(),busy=busy,busy_capacity=capacity,affinity=affinity,
                preferred_cpus=[c for c in affinity if c not in occupied],free_bytes=shutil.disk_usage(HERE).free)

def latest_tests():
    p=sorted((HERE/'analysis').glob('tests_attempt_*.json'))[-1];x=json.loads(p.read_text())
    assert x['status']=='PASS'
    assert x['inputs_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in code_paths()}
    assert x['registry_sha256']==sha(HERE/'SOURCE_DATA.json')
    return p

def inputs(mode):
    paths=code_paths()+[HERE/'SOURCE_DATA.json',latest_tests()]
    if mode=='scientific':paths += [HERE/'SAMPLE_FREEZE.json',HERE/'analysis/qualification_v1.json',HERE/'analysis/forecast_v1.json']
    return paths

def qualification():
    q=json.loads((HERE/'analysis/qualification_v1.json').read_text());assert q['status']=='PASS'
    assert q['inputs_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in inputs('benchmark')}
    for rel,h in q['evidence'].items():assert sha(ROOT/rel)==h,rel
    freeze=json.loads((HERE/'SAMPLE_FREEZE.json').read_text())
    assert freeze['settings']==settings('scientific') and freeze['before_new_scientific_reads']
    return q

def worker(mode,block,run):
    check_inputs(run);return experiment.block(mode,block,run)

def execute(mode,name,workers):
    start=time.monotonic();cfg=settings(mode);latest_tests();assert 1<=workers<=4
    if mode=='scientific':qualification()
    else:assert workers==1
    check_inputs(HERE/'jobs'/name)
    run=new_run(HERE/'runs'/name,inputs(mode),dict(**cfg,workers=workers));reports=[]
    def status(state,stage):dump(run/'STATUS.json',dict(status=state,stage=stage,utc=utc(),pid=os.getpid(),
        completed_blocks=[r['block'] for r in reports],total_blocks=len(cfg['blocks']),workers=workers,
        seconds=time.monotonic()-start,automatic_restart=False,automatic_extension=False,automatic_successor=False))
    try:
        status('RUNNING','checking_sources');dump(run/'resources.json',inventory(workers));sources.verify(mode)
        status('RUNNING','continuing_retained_lineages')
        def accept(r):
            reports.append(r);status('RUNNING','continuing_retained_lineages')
            print(f"Verified source {r['block']} at both budgets: {r['seconds']:.2f} s",flush=True)
        if workers==1:
            for b in cfg['blocks']:accept(worker(mode,b,run))
        else:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                futures=[pool.submit(worker,mode,b,run) for b in cfg['blocks']]
                for f in as_completed(futures):accept(f.result())
        status('RUNNING','paired_inference_and_tail_models');summary=inference.analyze(run,cfg)
        checks=dict(status='PASS',source_blocks=len(reports),both_budgets=True,all_sources_retained=True,
            old_checkpoint_projection_exact=True,protected_copy_exact=True,observer_feedback=False,
            independent_replay_generations=cfg['audit_generations'],independent_checkpoint_reads=8*2*len(reports),
            all_steps_independently_replayed=False,all_boundaries_saved=True,
            independent_sum_count_checks=summary['independent_sum_count_checks'],new_decoder_fitted=False)
        dump(run/'CHECKS.json',checks);sources.verify(mode);check_inputs(run);check_inputs(HERE/'jobs'/name)
        status('COMPLETE','finished')
        hashes={str(p.relative_to(run)):sha(p) for p in sorted(run.rglob('*')) if p.is_file()}
        dump(run/'COMPLETE.json',dict(status='COMPLETE',utc=utc(),mode=mode,seconds=time.monotonic()-start,
            outputs_sha256=hashes,controls_pass=True,blocks=len(reports),scientific_claim_allowed=mode=='scientific'))
        print(json.dumps(dict(status='COMPLETE',mode=mode,seconds=time.monotonic()-start)),flush=True)
    except BaseException:
        failure=dict(status='FAILED',utc=utc(),seconds=time.monotonic()-start,completed_blocks=[r['block'] for r in reports],
                     traceback=traceback.format_exc(),automatic_restart=False)
        dump(run/'FAILED.json',failure);dump(run/'STATUS.json',failure);raise

def verify(name):
    run=HERE/'runs'/name;check_inputs(run);c=json.loads((run/'COMPLETE.json').read_text())
    assert c['status']=='COMPLETE' and c['controls_pass'] and not (run/'FAILED.json').exists()
    for rel,h in c['outputs_sha256'].items():assert sha(run/rel)==h,rel
    sources.verify(c['mode']);return run,c

def qualify(name,workers):
    run,c=verify(name);assert c['mode']=='benchmark' and c['blocks']==1
    assert not (HERE/'SAMPLE_FREEZE.json').exists();assert 1<=workers<=4
    source=json.loads((run/'block_900014.json').read_text())
    analysis=json.loads((run/'summary.json').read_text())['seconds']
    per=source['seconds'];overhead=max(180.,c['seconds']-per,analysis)
    expected=math.ceil(64/workers)*per+overhead
    fields=sum(p.stat().st_size for p in run.glob('block_*.npz'))
    reserve=int(3*64*fields+1_000_000_000)
    resources=inventory(workers);assert resources['free_bytes']>reserve
    forecast=dict(utc=utc(),workers=workers,measured_full_block_seconds=per,measured_analysis_seconds=analysis,
        expected_seconds=expected,conservative_seconds=3*math.ceil(64/workers)*per+3*overhead,
        disk_reserve_bytes=reserve,resources=resources,detach_required=expected>600)
    dump(HERE/'analysis/forecast_v1.json',forecast)
    q=dict(status='PASS',utc=utc(),inputs_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs('benchmark')},
        evidence={str((run/p).relative_to(ROOT)):sha(run/p) for p in ('COMPLETE.json','CHECKS.json','specificity.png','specificity.pdf','block_900014.json')},
        figures_inspected=True,no_scientific_outcomes_used=True)
    dump(HERE/'analysis/qualification_v1.json',q)
    dump(HERE/'SAMPLE_FREEZE.json',dict(utc=utc(),settings=settings('scientific'),before_new_scientific_reads=True,
        qualification_sha256=sha(HERE/'analysis/qualification_v1.json'),known_source_cohort=True))
    print(json.dumps(forecast,indent=2))

def launch(mode,name,workers):
    latest_tests();cfg=settings(mode);assert 1<=workers<=4
    if mode=='scientific':
        qualification();forecast=json.loads((HERE/'analysis/forecast_v1.json').read_text());assert workers==forecast['workers']
    else:
        assert workers==1;t=json.loads(latest_tests().read_text())
        per=sum(t['full_generation_seconds'])/len(t['full_generation_seconds'])
        expected=500*per+180
        forecast=dict(utc=utc(),basis='Full-width excluded legacy generations; 480 new rewrites plus selected replay/checkpoints and analysis allowance.',
            expected_seconds=expected,conservative_seconds=3*expected,disk_reserve_bytes=1_000_000_000,workers=1)
        forecast_path=HERE/'analysis/benchmark_forecast_v1.json';assert not forecast_path.exists();dump(forecast_path,forecast)
    resources=inventory(workers)
    assert resources['free_bytes']>forecast['disk_reserve_bytes']
    cpus=resources['preferred_cpus'][:workers]
    if len(cpus)<workers:raise RuntimeError('Not enough currently unoccupied CPU affinities for this bounded launch')
    job=new_run(HERE/'jobs'/name,inputs(mode),dict(mode=mode,name=name,workers=workers,cpus=cpus,forecast=forecast))
    command=[sys.executable,'-B',str(HERE/'run.py'),'execute','--mode',mode,'--name',name,'--workers',str(workers)]
    with (job/'run.log').open('x') as log:
        p=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
            start_new_session=True,cwd=ROOT,preexec_fn=lambda:os.sched_setaffinity(0,cpus))
    dump(job/'launch.json',dict(utc=utc(),pid=p.pid,command=command,mode=mode,workers=workers,cpus=cpus,
        expected_seconds=forecast['expected_seconds'],conservative_seconds=forecast['conservative_seconds'],
        disk_reserve_bytes=forecast['disk_reserve_bytes'],resources=resources))
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        s=HERE/'runs'/name/'STATUS.json'
        if s.exists():
            try:value=json.loads(s.read_text())
            except json.JSONDecodeError:time.sleep(.1);continue
            if value['status']=='FAILED':raise RuntimeError(value)
            if value['pid']==p.pid and p.poll() is None:
                check_inputs(job);check_inputs(s.parent)
                dump(job/'startup.json',dict(status='PASS',utc=utc(),pid=p.pid,mode=mode,workers=workers,cpus=cpus,
                    bounded_startup_only=True,automatic_monitoring=False))
                print(json.dumps(dict(status='RUNNING',mode=mode,pid=p.pid,workers=workers,cpus=cpus,
                    expected_seconds=forecast['expected_seconds'],conservative_seconds=forecast['conservative_seconds'],run=str(s.parent))))
                return
        if p.poll() is not None:break
        time.sleep(.2)
    dump(job/'startup_failure.json',dict(utc=utc(),pid=p.pid,returncode=p.poll()));raise RuntimeError('Startup did not pass; no automatic restart')

def closeout(name):
    run,c=verify(name);assert c['mode']=='scientific'
    out=HERE/'analysis/closeout_v1.json';assert not out.exists()
    dump(out,dict(status='PASS',utc=utc(),seconds=c['seconds'],outputs_verified=len(c['outputs_sha256']),
        inputs_verified=len(json.loads((run/'manifest.json').read_text())['inputs_sha256']),figures_inspected=True,
        complete_sha256=sha(run/'COMPLETE.json'),checks=json.loads((run/'CHECKS.json').read_text()),
        retained_bytes=sum(p.stat().st_size for p in run.rglob('*') if p.is_file()),automatic_successor=False))
    print(out.read_text())

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['test','launch','execute','qualify','closeout'])
    p.add_argument('--mode',choices=['benchmark','scientific'],default='benchmark');p.add_argument('--name',default='benchmark_v1')
    p.add_argument('--workers',type=int,default=1);p.add_argument('--figures-inspected',action='store_true');a=p.parse_args()
    if a.action=='test':path,result=tests.run(code_paths());print(json.dumps(dict(path=str(path),**result)))
    elif a.action=='execute':execute(a.mode,a.name,a.workers)
    elif a.action=='launch':launch(a.mode,a.name,a.workers)
    elif a.action=='qualify':assert a.figures_inspected;qualify(a.name,a.workers)
    elif a.action=='closeout':assert a.figures_inspected;closeout(a.name)
