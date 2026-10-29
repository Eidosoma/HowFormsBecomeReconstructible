"""Freeze, benchmark and detach observation-budget and representation tests."""
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ProcessPoolExecutor, as_completed
import argparse
import json
import multiprocessing
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
import numpy as np

SOURCE = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(SOURCE))
from h007.io import checksum,save,seal,verify
from h019.audit import load
from h021.launch import cpu_snapshot
from h021.recovery import wait_for_capacity
from h031.workflow import INHERITED_FILES as PREVIOUS_FILES,NEW_FILES as H031_FILES,FIXTURES as PRIOR_FIXTURES
from h030.workflow import numerical_summary
from h033 import design as d,measure,predict,analysis

INHERITED_FILES = [*PREVIOUS_FILES,*H031_FILES]
NEW_FILES = ['h033/'+name for name in ('design.py','measure.py','predict.py','analysis.py','fixtures.py','workflow.py','PROTOCOL.md','README.md')]
FIXTURES = (*PRIOR_FIXTURES,'h033.fixtures')


def tasks_for(out,specs):
    tasks = dict(probe=[],finite=[],observation=[],train=[],test=[])
    for spec in specs:
        for kind in ('probe','finite','observation','future'):
            group = spec['split'] if kind=='future' else kind
            tasks[group].append(dict(out=str(out),name=kind+'_'+spec['key'],kind=kind,spec=spec))
    return tasks


def prepare(lane,out):
    prior = lane/'runs/h031_prediction_v1'; verify(prior,'checksums.json')
    complete = json.loads((prior/'COMPLETE.json').read_text())
    assert complete['qualified'] and complete['verdict']=='NO_QUALIFIED_ENTRANT_PREDICTION_ADVANTAGE'
    diagnosis = lane/'runs/h032_diagnostic_v1'; verify(diagnosis,'checksums.json')
    assert json.loads((diagnosis/'COMPLETE.json').read_text())['checks_passed']
    failed = lane/'runs/h021_recovery_v1/prediction/FAILED.json'
    unqualified = lane/'runs/h026_prediction_v1/COMPLETE.json'
    previous_prediction = lane/'runs/h028_prediction_v1/COMPLETE.json'
    assert json.loads(failed.read_text())['state']=='FAILED'
    assert not json.loads(unqualified.read_text())['qualified']
    assert json.loads(previous_prediction.read_text())['verdict']=='NO_QUALIFIED_ADVANTAGE_ON_CALIBRATED_GRID'
    out.mkdir(exist_ok=False)
    for name in INHERITED_FILES:
        if not name.endswith('/README.md'):
            assert checksum(lane/name)==checksum(prior/'source'/name),name
        path = out/'source'/name; path.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(prior/'source'/name,path)
    for name in NEW_FILES:
        path = out/'source'/name; path.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(lane/name,path)
    bindings = {str(prior/name):checksum(prior/name) for name in
                ('checksums.json','COMPLETE.json','evaluation.json','benchmark_serial.json','benchmark_decision.json')}
    for path in (failed,unqualified,previous_prediction,diagnosis/'checksums.json',diagnosis/'summary.json'):
        bindings[str(path)] = checksum(path)
    save(out/'external_bindings.json',bindings)
    specs = d.task_specs(); benchmark = [dict(spec=spec,input_name=spec['key']) for spec in d.benchmark_specs()]
    (out/'inputs').mkdir()
    for spec in specs+d.benchmark_specs():
        data = d.inputs(spec['mode'],spec['split'],spec['ids'],spec['cell'])
        assert all(np.isfinite(v).all() for v in data.values()) and d.support(data)
        np.savez_compressed(out/'inputs'/f'{spec["key"]}.npz',**data)
    np.savez_compressed(out/'bootstrap.npz',indices=d.rng([d.SEED,3]).integers(0,d.SOURCES,(d.BOOTSTRAPS,d.SOURCES)))
    old = json.loads((prior/'benchmark_serial.json').read_text())['tasks']
    unit = max(row['elapsed_seconds']/d.old.CELLS[int(row['name'].split('_')[1][1:])][1] for row in old)
    main_clock = sum(d.old.CELLS[spec['cell']][1] for spec in specs)
    bench_clock = sum(d.old.CELLS[item['spec']['cell']][1] for item in benchmark)
    forecast = 1.5*(main_clock+2*bench_clock)*unit*1.25+900
    save(out/'config.json',dict(experiment='H033',label='PROSPECTIVE_DEVELOPMENT',
        sources_per_split=d.SOURCES,root=d.SEED,specs=specs,tasks=tasks_for(out,specs),benchmark=benchmark,
        cells=[d.old.cell_metadata(cell) for cell in d.CELLS],selections=d.SELECTIONS,
        fractions=d.FRACTIONS,branches=d.branches(),support_cap_factor=.9,
        probe_paths=2*d.SOURCES*3*8,finite_paths=2*d.SOURCES*3*2*9,
        future_paths=2*d.SOURCES*3*2*9*d.TAILS,dt=d.DTS,horizon=24,tails=d.TAILS,
        observation_paths=2*d.SOURCES*3*2*9*d.TAILS,observed_replacements=d.OBSERVATION,
        feature_dimensions=d.DIMENSIONS,log_scale=d.LOG_SCALE,ablation=d.ABLATION,
        models=d.MODELS,candidate=d.CANDIDATE,comparators=d.COMPARATORS,fits=d.FIT_COUNT,
        prediction_family_size=30,representation_contrasts=24,observation_budget_contrasts=6,bootstrap_replicates=d.BOOTSTRAPS,
        prediction_practical_margin=d.PREDICTION_MARGIN,
        benchmark_main_scale=main_clock/bench_clock,initial_compute_forecast_seconds=forecast,
        forecast_note='H031 maximum full-pipeline serial cost per recovery-time unit x1.25 for additional observations, both benchmarks and main x1.5 +900s. Matched full-pipeline benchmark replaces this; capacity waits are additional.',
        candidate_workers=[1,4],numerical_threads=1,parallel_speed_threshold=.9,
        prepared_utc=datetime.now(timezone.utc).isoformat(),python_version=sys.version,numpy_version=np.__version__,
        prior_outcomes_pooled=False,private_material=False,original_h021_remains_failed=True,h026_remains_unqualified=True,
        numerical_gate='Inherited H028 probe and H031 finite/future gates, also applied to six-step observations; exact baselines and both 3- and 6-step prefixes, original support and common-dose secant refinement <=1e-4. Legacy 2e-11 separate.'))
    seal(out,'freeze.json',sorted(p for p in out.rglob('*') if p.is_file()))
    save(out/'STATUS.json',dict(state='PREPARED',phase='frozen',label='PROSPECTIVE_DEVELOPMENT'))


def reproduce_inputs(out,derived=False):
    config = json.loads((out/'config.json').read_text()); count=0; probe_keys=[]; tail_keys=[]
    for spec in config['specs']+[item['spec'] for item in config['benchmark']]:
        actual = load(out/'inputs'/f'{spec["key"]}.npz')
        expected = d.inputs(spec['mode'],spec['split'],spec['ids'],spec['cell'])
        assert actual.keys()==expected.keys()
        for key in expected:
            np.testing.assert_array_equal(actual[key],expected[key]); count+=1
        probe_keys.extend(actual['probe_keys'].reshape(-1,7).tolist())
        tail_keys.extend(actual['tail_keys'].reshape(-1,8).tolist())
        if derived and spec['mode']=='prediction':
            folder = out/'raw'/('probe_'+spec['key'])
            finite,future = d.derive(actual,[load(folder/f'raw_{i}.npz') for i in range(3)])
            for kind,values in (('finite',finite),('future',future),('observation',d.observation_inputs(future))):
                saved = load(out/'derived'/spec['key']/f'{kind}.npz')
                assert saved.keys()==values.keys()
                for key in values:
                    np.testing.assert_array_equal(saved[key],values[key]); count+=1
    assert len(probe_keys)==len({tuple(k) for k in probe_keys})
    assert len(tail_keys)==len({tuple(k) for k in tail_keys})
    np.testing.assert_array_equal(load(out/'bootstrap.npz')['indices'],
        d.rng([d.SEED,3]).integers(0,d.SOURCES,(d.BOOTSTRAPS,d.SOURCES)))
    return dict(arrays=count,distinct_probe_keys=len(probe_keys),distinct_candidate_tail_keys=len(tail_keys),derived=derived)


def compare_benchmarks(out,items):
    arrays = 0
    for item in items:
        a,b = [out/'raw'/(item['input_name']+'_'+mode) for mode in ('serial','parallel')]
        relative = sorted(str(p.relative_to(a)) for p in a.rglob('*') if p.is_file())
        assert relative==sorted(str(p.relative_to(b)) for p in b.rglob('*') if p.is_file())
        for name in relative:
            if name.endswith('.npz'):
                x,y = load(a/name),load(b/name); assert x.keys()==y.keys()
                for key in x:
                    np.testing.assert_array_equal(x[key],y[key]); arrays+=1
            else:
                assert json.loads((a/name).read_text())==json.loads((b/name).read_text())
        for root in (a,b):
            for level in range(3):
                measure.prefix_parity(load(root/'finite'/f'raw_{level}.npz'),load(root/'future'/f'raw_{level}.npz'))
                measure.observation_parity(load(root/'observation'/f'raw_{level}.npz'),load(root/'future'/f'raw_{level}.npz'))
    return arrays


def execute(out):
    started = time.perf_counter(); config = json.loads((out/'config.json').read_text())
    status = dict(state='RUNNING',phase='verification',label='PROSPECTIVE_DEVELOPMENT')
    timings,admissions,groups = {},{},{}
    def progress(**values):
        status.update(values,elapsed_seconds=time.perf_counter()-started,updated_utc=datetime.now(timezone.utc).isoformat())
        save(out/'STATUS.json',status); print(json.dumps(status),flush=True)
    def capacity(workers,phase):
        def update(record):
            progress(state='RUNNING' if record['capacity_available'] else 'WAITING_CAPACITY',phase='capacity_'+phase,capacity=record)
        admissions[phase] = wait_for_capacity(workers,cpu_snapshot,update)
        save(out/(phase+'_admission.json'),admissions[phase])
    def tasks(phase,function,items,workers):
        capacity(workers,phase); verify(out,'freeze.json')
        if phase=='test':
            predict.submit_test(out,len(items))
        progress(state='RUNNING',phase=phase,workers=workers,completed_tasks=0,total_tasks=len(items),failed_qualifications=0)
        before,results = time.perf_counter(),[]
        def accept(row):
            results.append(row)
            progress(completed_tasks=len(results),failed_qualifications=sum(not r.get('qualified',True) for r in results))
        if workers==1:
            for item in items:
                accept(function(item))
        else:
            with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn')) as pool:
                futures = [pool.submit(function,item) for item in items]
                for future in as_completed(futures):
                    accept(future.result())
        timings[phase] = time.perf_counter()-before
        if function in (measure.task,measure.benchmark_task):
            paths = sorted(p for item in items for p in (out/'raw'/item['name']).rglob('*') if p.is_file())
            seal(out,phase+'_sha256.json',paths)
        return sorted(results,key=lambda r:r['name'])
    def finish(verdict,qualified,evaluation=None):
        progress(phase='reporting')
        for name in ('freeze.json','decision_sha256.json','benchmark_serial_sha256.json','benchmark_parallel_sha256.json',
                     'probe_sha256.json','derived_sha256.json','finite_sha256.json','observation_sha256.json','feature_sha256.json',
                     'train_sha256.json','prediction_sha256.json','test_sha256.json'):
            if (out/name).exists():
                verify(out,name)
        bindings = json.loads((out/'external_bindings.json').read_text())
        assert all(checksum(p)==digest for p,digest in bindings.items())
        save(out/'summary.json',dict(label='PROSPECTIVE_DEVELOPMENT',verdict=verdict,qualified=qualified,
            evaluation=evaluation,groups=groups,numerical=numerical_summary(out,groups),timings=timings,
            capacity_wait_seconds=sum(a['wait_seconds'] for a in admissions.values()),
            elapsed_seconds=time.perf_counter()-started,original_h021_remains_failed=True,h026_remains_unqualified=True))
        progress(state='COMPLETE',phase='complete',verdict=verdict,qualified=qualified,remaining_compute_forecast_seconds=0.,
                 completed_utc=datetime.now(timezone.utc).isoformat())
        save(out/'COMPLETE.json',status); seal(out,'checksums.json',sorted(p for p in out.rglob('*') if p.is_file()))
        verify(out,'checksums.json')
    try:
        with (out/'EXECUTION.json').open('x') as stream:
            json.dump(dict(pid=os.getpid(),started_utc=datetime.now(timezone.utc).isoformat()),stream)
        verify(out,'freeze.json'); capacity(1,'fixtures'); progress(state='RUNNING',phase='fixtures')
        before = time.perf_counter()
        with (out/'fixtures.log').open('x') as stream:
            subprocess.run([sys.executable,'-B','-m','unittest','-v',*FIXTURES],cwd=SOURCE,
                stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,check=True)
        timings['fixtures'] = time.perf_counter()-before
        count = int(re.search(r'Ran (\d+) tests',(out/'fixtures.log').read_text()).group(1))
        progress(fixture_tests_passed=count,input_reproduction=reproduce_inputs(out))
        benchmarks = {}
        for mode,workers in (('serial',1),('parallel',4)):
            items = [dict(item,out=str(out),name=item['input_name']+'_'+mode) for item in config['benchmark']]
            rows = tasks('benchmark_'+mode,measure.benchmark_task,items,workers)
            benchmarks[mode] = dict(tasks=rows,elapsed_seconds=timings['benchmark_'+mode],qualified=all(r['qualified'] for r in rows))
            save(out/('benchmark_'+mode+'.json'),benchmarks[mode])
        arrays = compare_benchmarks(out,config['benchmark'])
        serial,parallel = [benchmarks[m]['elapsed_seconds'] for m in ('serial','parallel')]
        workers = 4 if parallel<.9*serial else 1
        decision = dict(workers=workers,serial_seconds=serial,parallel_seconds=parallel,arrays_exactly_equal=arrays,
            benchmark_qualified=all(b['qualified'] for b in benchmarks.values()),
            remaining_compute_forecast_seconds=(parallel if workers==4 else serial)*config['benchmark_main_scale']*1.5+900,
            capacity_wait_additional=True)
        save(out/'benchmark_decision.json',decision)
        seal(out,'decision_sha256.json',[out/name for name in ('benchmark_decision.json','benchmark_serial.json',
             'benchmark_parallel.json','benchmark_serial_sha256.json','benchmark_parallel_sha256.json')])
        progress(phase='benchmark_complete',selected_workers=workers,**{k:decision[k] for k in ('benchmark_qualified','remaining_compute_forecast_seconds')})
        if not decision['benchmark_qualified']:
            finish('BENCHMARK_NUMERICALLY_UNQUALIFIED',False); return
        for phase in ('probe','finite','observation','train'):
            groups[phase] = tasks(phase,measure.task,config['tasks'][phase],workers)
            if not all(r['qualified'] for r in groups[phase]):
                finish(phase.upper()+'_NUMERICALLY_UNQUALIFIED',False); return
            if phase=='probe':
                assert sum(r['paths'] for r in groups[phase])==config['probe_paths']
                capacity(1,'derivation'); progress(state='RUNNING',phase='derivation')
                predict.derive_inputs(out); progress(derived_reproduction=reproduce_inputs(out,derived=True))
            elif phase=='finite':
                assert sum(r['paths'] for r in groups[phase])==config['finite_paths']
            elif phase=='observation':
                assert sum(r['paths'] for r in groups[phase])==config['observation_paths']
                capacity(1,'features'); progress(state='RUNNING',phase='features'); predict.make_features(out)
        target = predict.targets(out,'train')
        np.savez_compressed(out/'targets_train.npz',target=target,flip=predict.flips(target))
        train_paths = [out/name for name in json.loads((out/'train_sha256.json').read_text())]
        seal(out,'train_sha256.json',train_paths+[out/'targets_train.npz'])
        fits = tasks('fit',predict.fit_task,[dict(out=str(out),name=name) for name in d.MODELS],workers)
        assert sum(r['fits'] for r in fits)==d.FIT_COUNT
        predict.seal_predictions(out)
        progress(phase='predictions_sealed',fit_count=d.FIT_COUNT,prediction_manifest_sha256=checksum(out/'prediction_sha256.json'))
        groups['test'] = tasks('test',measure.task,config['tasks']['test'],workers)
        if not all(r['qualified'] for r in groups['test']):
            finish('TEST_NUMERICALLY_UNQUALIFIED',False); return
        assert sum(r['paths'] for p in ('train','test') for r in groups[p])==config['future_paths']
        result = analysis.closeout(out); finish(result['verdict'],True,result)
    except Exception:
        failure = dict(state='FAILED',phase=status.get('phase'),label='PROSPECTIVE_DEVELOPMENT',error=traceback.format_exc(),
            failed_utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.perf_counter()-started)
        save(out/'FAILED.json',failure); save(out/'STATUS.json',failure); raise


def launch(version):
    if not version.replace('_','').isalnum():
        raise ValueError('Simple version required')
    out = SOURCE/f'runs/h033_prediction_{version}'
    log,pidfile,ledger = out.with_suffix('.log'),out.with_suffix('.pid'),out.with_name(out.name+'_launch.json')
    if any(p.exists() for p in (out,log,pidfile,ledger)):
        raise FileExistsError('Occupied H033 destination')
    prepare(SOURCE,out); config=json.loads((out/'config.json').read_text())
    command = [sys.executable,'-B',str(out/'source/h033/workflow.py'),'--execute',str(out)]
    env = os.environ.copy(); (SOURCE/'.cache/tmp').mkdir(parents=True,exist_ok=True)
    env.update(TMPDIR=str(SOURCE/'.cache/tmp'),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
        NUMEXPR_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',MPLCONFIGDIR=str(SOURCE/'.cache/matplotlib'),XDG_CACHE_HOME=str(SOURCE/'.cache'))
    record = dict(state='PREPARED',label='PROSPECTIVE_DEVELOPMENT',output=str(out),log=str(log),command=command,
        detached=True,candidate_workers=[1,4],numerical_threads=1,initial_compute_forecast_seconds=config['initial_compute_forecast_seconds'],
        capacity_wait_additional=True,freeze_sha256=checksum(out/'freeze.json'))
    save(ledger,record)
    with log.open('xb') as stream:
        process = subprocess.Popen(command,cwd=out/'source',env=env,stdin=subprocess.DEVNULL,stdout=stream,
            stderr=subprocess.STDOUT,start_new_session=True,close_fds=True)
    pidfile.write_text(str(process.pid)+'\n'); record.update(state='LAUNCHED',pid=process.pid); save(ledger,record)
    print(json.dumps(record),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(); group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--launch',metavar='VERSION'); group.add_argument('--execute',type=Path)
    args=parser.parse_args()
    launch(args.launch) if args.launch else execute(args.execute.resolve())
