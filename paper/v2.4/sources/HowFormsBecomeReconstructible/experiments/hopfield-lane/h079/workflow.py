"""Frozen intact-record pilot, exact worker benchmark and durable closeout."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import argparse
import json
import multiprocessing
import os
import shutil
import subprocess
import sys
import time
import traceback
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from h007.io import checksum,save,seal,verify
from h052.workflow import capacity,utc
from h061.workflow import watch
from h063.workflow import compare
from h078.workflow import FILES as PARENT_FILES
from h079 import model as m,audit,report,fixtures,inference
from h078 import measure

PIN='6f9f13d5069ef86bdba643c2e6b537fc070351bbe8affff0adcc820071a39dfc'
FILES=PARENT_FILES+['h078/INTERPRETATION.md','h078/review_saved.py']+['h079/'+n for n in
    ('PROTOCOL.md','model.py','audit.py','inference.py','report.py','fixtures.py','workflow.py')]


def read(path):return json.loads(Path(path).read_text())


def verify_inputs(out):
    verify(out,'freeze.json');config=read(out/'config.json');parent=Path(config['context_parent'])
    assert checksum(parent/'checksums.json')==PIN==config['context_parent_manifest']
    manifest=read(parent/'checksums.json')
    for name,pin in config['bound_context_artifacts'].items():assert checksum(parent/name)==pin==manifest[name]
    assert read(parent/'COMPLETE.json')['integrity_passed']
    assert read(out/'historical_verdicts.json')==dict(read(parent/'historical_verdicts.json'),
        h078_capability=read(parent/'main/summary.json')['capability_screen'])
    assert config['python']==sys.version and config['numpy']==np.__version__
    assert config['seed']==m.SEED==79079 and config['bootstrap_seed']==report.SEED==7907901
    assert config['replication_networks']==m.NETWORKS==192 and config['engineering_networks']==m.ENGINEERING==4
    assert config['replication_design']==inference.design()
    assert config['gaps']==list(m.GAPS) and config['horizons']==list(m.HORIZONS)
    assert config['scenarios']==list(m.SCENARIOS) and config['methods']==list(m.METHODS)
    assert config['schedules']==list(m.SCHEDULES)
    assert config['neurons']==m.N==128 and not config['inheritance_tested']
    return config


def task(arg):
    out,cohort,block=arg;tick=time.perf_counter();stem=f'block_{block:03d}'
    try:
        commitment=out/'commitments'/(stem+'.json')
        save(commitment,dict(cohort=cohort,block=block,seed=m.SEED,committed_utc=utc(),dynamics_started=False))
        committed=checksum(commitment);raw=m.run(cohort,block);path=out/'raw'/(stem+'.npz')
        m.save(path,raw);saved=m.load(path);assert raw.keys()==saved.keys()
        for key in raw:np.testing.assert_array_equal(raw[key],saved[key],err_msg=key)
        reloads=len(saved);del raw
        checked=audit.network(saved,cohort,block);rows=measure.network(saved,block)
        row_count=measure.verify(saved,rows);assert row_count==measure.ROWS
        checked.update(block=block,independently_verified_rows=row_count,saved_array_reload_checks=reloads,
            raw_sha256=checksum(path),saved_raw_bundles=1)
        save(out/'blocks'/(stem+'.json'),rows);save(out/'audits'/(stem+'.json'),checked)
        assert checksum(commitment)==committed
        return dict(**checked,active_seconds=time.perf_counter()-tick,commitment_sha256=committed)
    except BaseException:
        save(out/'audits'/(stem+'.FAILED.json'),dict(error=traceback.format_exc(),utc=utc()));raise


def batch(out,cohort,n,workers,progress):
    for name in ('raw','blocks','audits','commitments'):(out/name).mkdir(parents=True,exist_ok=False)
    tick=time.perf_counter();tasks=[];arguments=[(out,cohort,i) for i in range(n)]
    if workers==1:
        for arg in arguments:tasks.append(task(arg));progress(completed_blocks=len(tasks),total_blocks=n)
    else:
        with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn')) as pool:
            for future in as_completed([pool.submit(task,arg) for arg in arguments]):
                tasks.append(future.result());progress(completed_blocks=len(tasks),total_blocks=n)
    result=dict(workers=workers,cohort=cohort,active_seconds=time.perf_counter()-tick,tasks=sorted(tasks,key=lambda r:r['block']))
    save(out/'batch.json',result);return result


def finish(out,result,main):
    blocks=[read(out/'blocks'/f"block_{r['block']:03d}.json") for r in result['tasks']]
    summary=report.produce(out,blocks,main)
    checked=dict(passed=True,networks=len(result['tasks']),
        **{k:sum(t[k] for t in result['tasks']) for k in ('numerical_checks','independently_verified_rows','saved_array_reload_checks','saved_raw_bundles')},
        projection_extended_replay=True,switch_clamp_and_neural_energy_balance=True,conventional_controls_audited=True,
        max_projection_record_error=max(t['max_projection_record_error'] for t in result['tasks']),
        max_projection_field_error=max(t['max_projection_field_error'] for t in result['tasks']),
        projection_boundary_distance=min(t['projection_boundary_distance'] for t in result['tasks']),
        network_intervals=summary['network_intervals'],capability_screen=summary['capability_screen'],
        timing_iteration_verdict=summary['timing_iteration_verdict'],
        comparative_superiority_qualified=False,inheritance_tested=False)
    assert checked['independently_verified_rows']==measure.ROWS*len(result['tasks'])
    save(out/'verification.json',checked);return checked


def execute(out):
    assert ROOT==out/'source','Execute the frozen snapshot only'
    tick=time.perf_counter();status=dict(state='RUNNING',phase='verify_inputs',workers=0,pid=os.getpid(),started_utc=utc())
    def progress(**kw):
        status.update(kw,updated_utc=utc(),elapsed_seconds=time.perf_counter()-tick)
        save(out/'STATUS.json',status);print(json.dumps(status),flush=True)
    admissions=[]
    def admit(phase,workers):
        counts=dict(completed_blocks=0,total_blocks=m.NETWORKS if phase=='main' else m.ENGINEERING) if phase in ('main','engineering_serial','engineering_parallel') else {}
        progress(phase=phase+'_admission',workers=0,**counts)
        admissions.append(capacity(out/(phase+'_admission.json'),workers,progress))
        progress(state='RUNNING',phase=phase,workers=workers)
    try:
        progress();config=verify_inputs(out)
        assert all(os.environ.get(k)=='1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'))
        admit('fixtures',1);tests=fixtures.run(out/'report_fixture');save(out/'fixtures.json',tests)
        results={}
        for name,workers in (('engineering_serial',1),('engineering_parallel',4)):
            admit(name,workers);progress(completed_blocks=0,total_blocks=4)
            results[name]=batch(out/name,'engineering',4,workers,progress)
        equivalent=compare(out);serial=results['engineering_serial']['active_seconds'];parallel=results['engineering_parallel']['active_seconds']
        workers=4 if serial/parallel>=1.15 else 1;forecast=1.25*(parallel if workers==4 else serial)*(m.NETWORKS/m.ENGINEERING)+120
        choice=dict(workers=workers,serial_seconds=serial,parallel_seconds=parallel,speedup=serial/parallel,threshold=1.15,
            **equivalent,main_forecast_seconds=forecast,decided_before_replication=True,decided_utc=utc())
        save(out/'worker_choice.json',choice);progress(main_forecast_seconds=forecast)
        admit('engineering_report',1);engineering=finish(out/'engineering_serial',results['engineering_serial'],False)
        admit('main',workers);progress(completed_blocks=0,total_blocks=m.NETWORKS)
        result=batch(out/'main','replication',m.NETWORKS,workers,progress)
        admit('main_report',1);main=finish(out/'main',result,True)
        progress(phase='closeout');verify_inputs(out)
        for name in FILES:assert checksum(out/'source'/name)==checksum(Path(config['lane_root'])/name),name
        waits=sum(v['wait_seconds'] for v in admissions)
        save(out/'execution_summary.json',dict(passed=True,fixtures=tests['count'],engineering=engineering,main=main,
            worker_choice=choice,capacity_wait_seconds=waits,active_seconds=time.perf_counter()-tick-waits,
            source_files_unchanged=len(FILES),historical_verdicts_unchanged=True,context_artifacts_unchanged=True,
            reused_numerical_networks=0,inheritance_tested=False,predictors_fitted=0,next_campaign_launched=False))
        progress(state='COMPLETE',phase='complete',workers=0,completed_utc=utc(),integrity_passed=True)
        save(out/'COMPLETE.json',status)
        seal(out,'checksums.json',[p for p in sorted(out.rglob('*')) if p.is_file() and p.name!='checksums.json'])
        verify(out,'checksums.json');receipt=Path(config['closeout_receipt']);assert not receipt.exists()
        save(receipt,dict(passed=True,completed_utc=utc(),run=str(out),manifest_sha256=checksum(out/'checksums.json'),
            main_checks=main['numerical_checks'],main_rows=main['independently_verified_rows'],capability_screen=main['capability_screen'],
            timing_iteration_verdict=main['timing_iteration_verdict'],
            comparative_superiority_qualified=False,inheritance_tested=False,historical_verdicts_unchanged=True,next_campaign_launched=False))
    except BaseException:
        failure=dict(state='FAILED',phase=status['phase'],failed_utc=utc(),error=traceback.format_exc())
        if (out/'checksums.json').exists():save(out.with_name(out.name+'_postseal_failure.json'),failure)
        else:progress(**failure,workers=0);save(out/'FAILED.json',status)
        raise


def prepare(out):
    assert out.is_relative_to(ROOT/'runs') and out.name.startswith('h079_replication_')
    suffix=out.name.removeprefix('h079_replication_');receipt=ROOT/'.cache'/('h079_closeout_'+suffix+'.json')
    assert not any(p.exists() for p in (out,out.with_suffix('.log'),out.with_suffix('.pid'),out.with_name(out.name+'_launch.json'),receipt))
    parent=ROOT/'runs/h078_timing_v1';assert checksum(parent/'checksums.json')==PIN
    manifest=read(parent/'checksums.json');assert read(parent/'COMPLETE.json')['integrity_passed']
    bound={name:manifest[name] for name in ('COMPLETE.json','historical_verdicts.json','main/summary.json')}
    for name,pin in bound.items():assert checksum(parent/name)==pin
    for name in PARENT_FILES:assert checksum(ROOT/name)==checksum(parent/'source'/name),name
    out.mkdir(parents=True,exist_ok=False)
    for name in FILES:
        target=out/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
    shutil.copyfile(ROOT/'RUN_POLICY.md',out/'RUN_POLICY.md');shutil.copyfile(ROOT.parent/'RUN_POLICY.md',out/'shared_RUN_POLICY.md')
    save(out/'historical_verdicts.json',dict(read(parent/'historical_verdicts.json'),
        h078_capability=read(parent/'main/summary.json')['capability_screen']))
    save(out/'config.json',dict(experiment='H079',created_utc=utc(),lane_root=str(ROOT),python=sys.version,numpy=np.__version__,
        context_parent=str(parent),context_parent_manifest=PIN,bound_context_artifacts=bound,
        seed=m.SEED,replication_networks=m.NETWORKS,engineering_networks=m.ENGINEERING,replication_design=inference.design(),neurons=m.N,gaps=list(m.GAPS),horizons=list(m.HORIZONS),
        scenarios=list(m.SCENARIOS),methods=list(m.METHODS),schedules=list(m.SCHEDULES),feedback_tapes={k:v.tolist() for k,v in m.FEEDBACK.items()},bootstrap_seed=report.SEED,bootstrap_samples=report.SAMPLES,
        classification='fresh prospective timing replication',inheritance_tested=False,shared_cpu_limit=12,numerical_threads=1,
        worker_candidates=[1,4],closeout_receipt=str(receipt),watch_receipt=str(ROOT/'.cache'/('h079_watch_'+suffix+'.json')),
        next_campaign_launched=False))
    seal(out,'freeze.json',[p for p in sorted(out.rglob('*')) if p.is_file()])
    command=[sys.executable,'-B',str(out/'source/h079/workflow.py'),'--execute',str(out)]
    subprocess.run([sys.executable,'-B',str(out/'source/h079/workflow.py'),'--help'],check=True,stdout=subprocess.DEVNULL,cwd=out)
    with out.with_suffix('.log').open('xb') as log:
        proc=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,cwd=ROOT)
    with out.with_suffix('.pid').open('x') as f:f.write(str(proc.pid)+'\n')
    launch=dict(run=str(out),pid=proc.pid,launched_utc=utc(),freeze_sha256=checksum(out/'freeze.json'),detached=True,short_run_watcher_authorized=True)
    save(out.with_name(out.name+'_launch.json'),launch);print(json.dumps(launch,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();mode=p.add_mutually_exclusive_group(required=True)
    for k in ('prepare','execute','watch'):mode.add_argument('--'+k,type=Path)
    args=p.parse_args()
    if args.prepare:prepare(args.prepare.resolve())
    elif args.execute:execute(args.execute.resolve())
    else:watch(args.watch.resolve())
