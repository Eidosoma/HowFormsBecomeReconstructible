"""Frozen fresh confirmation, exact worker comparison and durable closeout."""
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
from h083.workflow import FILES as PARENT_FILES
from h084 import model as m,audit,measure,inference,report,fixtures

PIN='102c5facaa88f68ca65616961f8adcc45e68ad9508965a5d15efddc336f6b816'
ARCHIVE_PIN='004bce5848dbbefe377b8dcdd0b536ba3c3c828c047f3717dded9ed0f07217c9'
FILES=PARENT_FILES+['h083/INTERPRETATION.md']+['h084/'+name for name in
    ('PROTOCOL.md','model.py','audit.py','measure.py','inference.py','report.py','fixtures.py','workflow.py')]
TOTALS=('numerical_checks','source_numerical_checks','independently_verified_rows','source_table_rows',
    'saved_array_reload_checks','saved_raw_bundles','pair_energy_comparisons','single_energy_comparisons',
    'new_query_continuations','new_records')


def read(path):return json.loads(Path(path).read_text())


def historical(parent):
    summary=read(parent/'main/summary.json')
    return dict(read(parent/'historical_verdicts.json'),h083_neighborhood=summary['neighborhood_result'],
        h083_saved_cohort_repair=summary['repair_result'],h083_comparative_superiority=False)


def verify_inputs(out):
    verify(out,'freeze.json');config=read(out/'config.json');parent=Path(config['parent'])
    assert checksum(parent/'checksums.json')==PIN==config['parent_manifest_sha256']
    verify(parent,'checksums.json');assert read(parent/'COMPLETE.json')['integrity_passed']
    assert read(out/'historical_verdicts.json')==historical(parent)
    for item in read(out/'context_bindings.json')['files']:
        assert checksum(item['path'])==item['sha256'],item['path']
    assert config['python']==sys.version and config['numpy']==np.__version__
    assert config['seed']==m.SEED==84084 and config['confirmation_networks']==m.NETWORKS==192
    assert config['engineering_networks']==m.ENGINEERING==4 and config['alpha']==inference.ALPHA==.05
    assert config['starts']==list(m.STARTS) and config['gaps']==list(m.GAPS)
    assert config['new_query_continuations_per_network']==m.pair.CONTINUATIONS==256
    assert config['pair_count']==m.pair.PAIR_COUNT==1128 and config['energy_tolerance']==m.pair.ENERGY_TOL==1e-10
    assert config['source_scenarios']==['own'] and config['predictors']==config['inherited_transitions']==0
    return config


def write_bundle(path,data):
    with path.open('xb') as f:np.savez_compressed(f,**data)
    with np.load(path,allow_pickle=False) as saved:
        assert set(saved.files)==set(data)
        result={key:saved[key] for key in saved.files}
    for key in data:np.testing.assert_array_equal(data[key],result[key],err_msg=key)
    return result


def task(argument):
    out,cohort,block=argument;tick=time.perf_counter();stem=f'block_{block:03d}'
    try:
        tape=m.tapes(cohort,block);digest=m.tape_digest(tape)
        saved_tape=write_bundle(out/'tapes'/(stem+'.npz'),tape)
        assert m.tape_digest(saved_tape)==digest
        commitment=out/'commitments'/(stem+'.json')
        save(commitment,dict(cohort=cohort,block=block,seed=m.SEED,tape_digest=digest,
            tape_sha256=checksum(out/'tapes'/(stem+'.npz')),committed_utc=utc(),dynamics_started=False))
        committed=checksum(commitment)
        raw=m.source(saved_tape);data=m.pair.run(m.reader_source(raw))
        raw_saved=write_bundle(out/'source_raw'/(stem+'.npz'),raw)
        saved=write_bundle(out/'raw'/(stem+'.npz'),data)
        reloads=len(tape)+len(raw)+len(data);del raw,data
        checked=audit.network(raw_saved,saved,cohort,block)
        rows=measure.network(saved,block);row_count=measure.verify(saved,rows)
        source_rows=measure.source_scores(raw_saved,rows,block)
        checked.update(block=block,independently_verified_rows=row_count,source_table_rows=source_rows,
            saved_array_reload_checks=reloads,saved_raw_bundles=3,tape_digest=digest,
            raw_sha256=checksum(out/'raw'/(stem+'.npz')),source_raw_sha256=checksum(out/'source_raw'/(stem+'.npz')))
        save(out/'blocks'/(stem+'.json'),rows);save(out/'audits'/(stem+'.json'),checked)
        assert checksum(commitment)==committed
        return dict(**checked,active_seconds=time.perf_counter()-tick,commitment_sha256=committed)
    except BaseException:
        save(out/'audits'/(stem+'.FAILED.json'),dict(error=traceback.format_exc(),utc=utc()));raise


def batch(out,cohort,n,workers,progress):
    for name in ('raw','source_raw','tapes','blocks','audits','commitments'):(out/name).mkdir(parents=True,exist_ok=False)
    tick=time.perf_counter();tasks=[];arguments=[(out,cohort,block) for block in range(n)]
    if workers==1:
        for arg in arguments:tasks.append(task(arg));progress(completed_blocks=len(tasks),total_blocks=n)
    else:
        with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn')) as pool:
            for future in as_completed([pool.submit(task,arg) for arg in arguments]):
                tasks.append(future.result());progress(completed_blocks=len(tasks),total_blocks=n)
    assert len({r['tape_digest'] for r in tasks})==n
    result=dict(cohort=cohort,workers=workers,active_seconds=time.perf_counter()-tick,
        tasks=sorted(tasks,key=lambda r:r['block']))
    save(out/'batch.json',result);return result


def finish(out,result,main):
    blocks=[read(out/'blocks'/f"block_{r['block']:03d}.json") for r in result['tasks']]
    summary=report.produce(out,blocks,main)
    checked=dict(passed=True,networks=len(result['tasks']),**{key:sum(t[key] for t in result['tasks']) for key in TOTALS},
        serialized_rows_checked=summary['serialized_rows_checked'],predictors=0,inherited_transitions=0,
        fresh_acquisition_and_paths_audited=True,conventional_controls_audited=True,
        max_pair_energy_error=max(t['max_pair_energy_error'] for t in result['tasks']),
        max_field_error=max(t['max_field_error'] for t in result['tasks']),
        max_projection_record_error=max(t['max_projection_record_error'] for t in result['tasks']),
        minimum_decision_boundary_distance=min(t['minimum_decision_boundary_distance'] for t in result['tasks']),
        directional_verdict=summary['directional_verdict'],mean_verdict=summary['mean_verdict'],
        comparative_superiority_qualified=False,capability_qualification=False)
    assert checked['independently_verified_rows']==measure.ROWS*len(result['tasks'])
    assert checked['source_table_rows']==24*len(result['tasks'])
    save(out/'verification.json',checked);return checked


def execute(out):
    assert ROOT==out/'source','Execute frozen sources only'
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
        admit('fixtures',1);tests=fixtures.run(out/'report_fixture',config['archive_engineering_raw'])
        save(out/'fixtures.json',tests);results={}
        for group,workers in (('engineering_serial',1),('engineering_parallel',4)):
            admit(group,workers);results[group]=batch(out/group,'engineering',m.ENGINEERING,workers,progress)
        equivalent=compare(out);serial,parallel=[results[k]['active_seconds'] for k in ('engineering_serial','engineering_parallel')]
        workers=4 if serial/parallel>=1.15 else 1
        forecast=1.25*(parallel if workers==4 else serial)*(m.NETWORKS/m.ENGINEERING)+90
        choice=dict(workers=workers,serial_seconds=serial,parallel_seconds=parallel,speedup=serial/parallel,
            threshold=1.15,**equivalent,main_forecast_seconds=forecast,decided_before_main=True,decided_utc=utc())
        save(out/'worker_choice.json',choice);progress(main_forecast_seconds=forecast)
        size=sum(p.stat().st_size for p in (out/'engineering_serial').rglob('*') if p.is_file())
        needed=int(2*size*m.NETWORKS/m.ENGINEERING+100_000_000)
        assert shutil.disk_usage(out).free>needed,'insufficient free disk for retained raw evidence'
        save(out/'storage_forecast.json',dict(engineering_bytes=size,conservative_main_bytes=needed,
            free_bytes=shutil.disk_usage(out).free,checked_before_main=True))
        admit('engineering_report',1);engineering=finish(out/'engineering_serial',results['engineering_serial'],False)
        admit('main',workers);result=batch(out/'main','confirmation',m.NETWORKS,workers,progress)
        assert not ({t['tape_digest'] for t in result['tasks']}&{t['tape_digest'] for t in results['engineering_serial']['tasks']})
        admit('main_report',1);main=finish(out/'main',result,True)
        progress(phase='closeout');verify_inputs(out)
        for name in FILES:assert checksum(out/'source'/name)==checksum(Path(config['lane_root'])/name),name
        waits=sum(r['wait_seconds'] for r in admissions)
        save(out/'execution_summary.json',dict(passed=True,fixtures=tests['count'],engineering=engineering,main=main,
            worker_choice=choice,capacity_wait_seconds=waits,active_seconds=time.perf_counter()-tick-waits,
            source_files_unchanged=len(FILES),parent_unchanged=True,historical_verdicts_unchanged=True,
            reused_numerical_networks=0,inherited_transitions=0,predictors=0,next_campaign_launched=False))
        progress(state='COMPLETE',phase='complete',workers=0,completed_utc=utc(),integrity_passed=True)
        save(out/'COMPLETE.json',status)
        seal(out,'checksums.json',[p for p in sorted(out.rglob('*')) if p.is_file() and p.name!='checksums.json'])
        verify(out,'checksums.json');receipt=Path(config['closeout_receipt']);assert not receipt.exists()
        save(receipt,dict(passed=True,completed_utc=utc(),run=str(out),manifest_sha256=checksum(out/'checksums.json'),
            main_rows=main['independently_verified_rows'],main_checks=main['numerical_checks'],
            source_table_rows=main['source_table_rows'],new_query_continuations=main['new_query_continuations'],
            new_records=main['new_records'],directional_verdict=main['directional_verdict'],mean_verdict=main['mean_verdict'],
            comparative_superiority_qualified=False,historical_verdicts_unchanged=True,next_campaign_launched=False))
    except BaseException:
        failure=dict(state='FAILED',phase=status['phase'],failed_utc=utc(),error=traceback.format_exc())
        if (out/'checksums.json').exists():save(out.with_name(out.name+'_postseal_failure.json'),failure)
        else:progress(**failure,workers=0);save(out/'FAILED.json',status)
        raise


def prepare(out):
    assert out.is_relative_to(ROOT/'runs') and out.name.startswith('h084_confirmation_')
    suffix=out.name.removeprefix('h084_confirmation_');receipt=ROOT/'.cache'/('h084_closeout_'+suffix+'.json')
    assert not any(p.exists() for p in (out,out.with_suffix('.pid'),out.with_suffix('.log'),out.with_name(out.name+'_launch.json'),receipt))
    parent=ROOT/'runs/h083_pairs_v1';archive=ROOT/'runs/h081_selective_v2'
    assert checksum(parent/'checksums.json')==PIN and read(parent/'COMPLETE.json')['integrity_passed']
    assert checksum(archive/'checksums.json')==ARCHIVE_PIN and read(archive/'COMPLETE.json')['integrity_passed']
    verify(parent,'checksums.json');archive_name='engineering_serial/raw/block_000.npz'
    archive_raw=archive/archive_name;assert checksum(archive_raw)==read(archive/'checksums.json')[archive_name]
    for name in PARENT_FILES:assert checksum(ROOT/name)==checksum(parent/'source'/name),name
    out.mkdir(parents=True,exist_ok=False)
    for name in FILES:
        target=out/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
    shutil.copyfile(ROOT/'RUN_POLICY.md',out/'RUN_POLICY.md');shutil.copyfile(ROOT.parent/'RUN_POLICY.md',out/'shared_RUN_POLICY.md')
    bindings=[dict(path=str(path),sha256=checksum(path)) for path in
        (parent/'checksums.json',parent/'COMPLETE.json',parent/'main/summary.json',parent/'historical_verdicts.json',
         archive/'checksums.json',archive_raw)]
    save(out/'context_bindings.json',dict(files=bindings,archived_outcomes_used_for_engineering_identity_only=True))
    save(out/'historical_verdicts.json',historical(parent))
    save(out/'config.json',dict(experiment='H084',created_utc=utc(),lane_root=str(ROOT),python=sys.version,numpy=np.__version__,
        parent=str(parent),parent_manifest_sha256=PIN,archive_engineering_raw=str(archive_raw),seed=m.SEED,
        confirmation_networks=m.NETWORKS,engineering_networks=m.ENGINEERING,alpha=inference.ALPHA,
        classification='fresh fixed-rule response-pair confirmation',source_scenarios=['own'],
        gaps=list(m.GAPS),starts=list(m.STARTS),new_query_continuations_per_network=m.pair.CONTINUATIONS,
        pair_count=m.pair.PAIR_COUNT,energy_tolerance=m.pair.ENERGY_TOL,predictors=0,inherited_transitions=0,
        worker_candidates=[1,4],shared_cpu_limit=12,numerical_threads=1,
        closeout_receipt=str(receipt),watch_receipt=str(ROOT/'.cache'/('h084_watch_'+suffix+'.json')),
        next_campaign_launched=False))
    seal(out,'freeze.json',[p for p in sorted(out.rglob('*')) if p.is_file()])
    command=[sys.executable,'-B',str(out/'source/h084/workflow.py'),'--execute',str(out)]
    subprocess.run([sys.executable,'-B',str(out/'source/h084/workflow.py'),'--help'],check=True,stdout=subprocess.DEVNULL,cwd=out)
    with out.with_suffix('.log').open('xb') as log:
        proc=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,cwd=ROOT)
    with out.with_suffix('.pid').open('x') as f:f.write(str(proc.pid)+'\n')
    launch=dict(run=str(out),pid=proc.pid,launched_utc=utc(),freeze_sha256=checksum(out/'freeze.json'),
        detached=True,short_run_watcher_authorized=True)
    save(out.with_name(out.name+'_launch.json'),launch);print(json.dumps(launch,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();mode=p.add_mutually_exclusive_group(required=True)
    for key in ('prepare','execute','watch'):mode.add_argument('--'+key,type=Path)
    args=p.parse_args()
    if args.prepare:prepare(args.prepare.resolve())
    elif args.execute:execute(args.execute.resolve())
    else:watch(args.watch.resolve())
