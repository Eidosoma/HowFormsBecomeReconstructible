"""Frozen preflight, fresh inherited pilot, measured workers and durable closeout."""
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
from h088.workflow import FILES as ANCESTOR_FILES
PARENT_FILES=list(dict.fromkeys(ANCESTOR_FILES))
from h089 import model as m,audit,measure,report,fixtures

PIN='5236bced20992dee0c0844e17d3fda182eaa3409273f1787261659194960ac37'
ARCHIVE_PIN='25ec7e4f8b7adc073eb69112f3ed8253396107519021de638b121bbf0b115cb4'
FILES=PARENT_FILES+['h088/INTERPRETATION.md']+['h089/'+name for name in
    ('PROTOCOL.md','model.py','audit.py','measure.py','report.py','fixtures.py','workflow.py')]
TOTALS=('numerical_checks','independently_verified_rows','records','writer_packets','lineage_nodes','local_nodes',
    'assay_cases','unique_neural_reads','unique_native_reads','pair_energy_comparisons','single_energy_comparisons',
    'saved_array_reload_checks','saved_graph_reload_checks','saved_raw_bundles','propagated_lineages')


def read(path):return json.loads(Path(path).read_text())


def archives(lane):
    source=lane/'runs/h086_inheritance_v1'
    assert checksum(source/'checksums.json')==ARCHIVE_PIN
    verify(source,'checksums.json');assert read(source/'COMPLETE.json')['integrity_passed']
    manifest=read(source/'checksums.json');result={}
    for kind,folder,ext in (('raw','raw','npz'),('graph','paths','json')):
        name=f'engineering_serial/{folder}/block_000.{ext}'
        result[kind]=str(source/name);result[kind+'_sha256']=manifest[name]
    check_archives(result);return result


def check_archives(bound):
    for kind in ('raw','graph'):assert checksum(bound[kind])==bound[kind+'_sha256']


def check_threads():
    assert all(os.environ.get(k)=='1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'))


def source_copy(out):
    for name in FILES:
        target=out/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
    shutil.copyfile(ROOT/'RUN_POLICY.md',out/'RUN_POLICY.md');shutil.copyfile(ROOT.parent/'RUN_POLICY.md',out/'shared_RUN_POLICY.md')


def launch(out,mode):
    command=[sys.executable,'-B',str(out/'source/h089/workflow.py'),mode,str(out)]
    subprocess.run([sys.executable,'-B',str(out/'source/h089/workflow.py'),'--help'],check=True,stdout=subprocess.DEVNULL,cwd=out)
    with out.with_suffix('.log').open('xb') as log:
        proc=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
            start_new_session=True,close_fds=True,cwd=ROOT)
    with out.with_suffix('.pid').open('x') as f:f.write(str(proc.pid)+'\n')
    result=dict(run=str(out),pid=proc.pid,launched_utc=utc(),freeze_sha256=checksum(out/'freeze.json'),detached=True)
    save(out.with_name(out.name+'_launch.json'),result);print(json.dumps(result,indent=2))


def history(parent):
    return dict(read(parent/'historical_verdicts.json'),h088=read(parent/'main/summary.json')['findings'],h088_comparative_superiority=False)


def verify_inputs(out):
    verify(out,'freeze.json');config=read(out/'config.json');parent=Path(config['parent'])
    assert checksum(parent/'checksums.json')==PIN==config['parent_manifest_sha256'];verify(parent,'checksums.json')
    assert read(parent/'COMPLETE.json')['integrity_passed']
    assert config['python']==sys.version and config['numpy']==np.__version__
    assert config['networks']==m.NETWORKS==16 and config['engineering']==m.ENGINEERING==4 and config['root_seed']==m.SEED==89089
    assert config['actual_handoffs']==2 and config['generations']==[0,1,2] and config['assay_cases_per_network']==720
    assert config['contrast_count']==len(measure.CONTRASTS)==172 and config['primary_comparators']==list(measure.PRIMARY_COMPARATORS)
    assert config['training_indices']==m.TRAIN.tolist() and config['heldout_indices']==m.TEST.tolist()
    assert read(out/'historical_verdicts.json')==history(parent)
    check_archives(read(out/'input_bindings.json'))
    return config


def task(argument):
    out,cohort,block=argument;tick=time.perf_counter();stem=f'block_{block:03d}'
    try:
        tape=m.tapes(cohort,block);path=out/'tapes'/(stem+'.npz')
        with path.open('xb') as f:np.savez_compressed(f,**tape)
        commitment=out/'commitments'/(stem+'.json')
        save(commitment,dict(block=block,cohort=cohort,committed_utc=utc(),new_acquisition_started=False,
            all_generations_committed=True,tape_sha256=checksum(path),tape_digest=m.digest(tape)))
        pin=checksum(commitment);raw,graph=m.run_tapes(tape)
        path=out/'raw'/(stem+'.npz')
        with path.open('xb') as f:np.savez_compressed(f,**raw)
        save(out/'paths'/(stem+'.json'),graph)
        with np.load(path,allow_pickle=False) as f:saved={key:f[key] for key in f.files}
        assert set(saved)==set(raw)
        for key in raw:np.testing.assert_array_equal(raw[key],saved[key],err_msg=key)
        reloads=len(raw);del raw
        saved_graph=read(out/'paths'/(stem+'.json'));assert graph==saved_graph
        checked=audit.network(saved,saved_graph,cohort,block)
        rows=measure.network(saved,saved_graph,block);row_count=measure.verify(saved,saved_graph,rows)
        checked.update(block=block,independently_verified_rows=row_count,saved_array_reload_checks=reloads,
            saved_graph_reload_checks=1,saved_raw_bundles=1,raw_sha256=checksum(path))
        save(out/'blocks'/(stem+'.json'),rows);save(out/'audits'/(stem+'.json'),checked)
        assert checksum(commitment)==pin
        assert checksum(out/'tapes'/(stem+'.npz'))==read(commitment)['tape_sha256']
        return dict(**checked,active_seconds=time.perf_counter()-tick,commitment_sha256=pin)
    except BaseException:
        save(out/'audits'/(stem+'.FAILED.json'),dict(error=traceback.format_exc(),utc=utc()));raise


def batch(out,cohort,n,workers,progress):
    for name in ('raw','paths','blocks','audits','tapes','commitments'):(out/name).mkdir(parents=True,exist_ok=False)
    tick=time.perf_counter();results=[];arguments=[(out,cohort,b) for b in range(n)]
    if workers==1:
        for arg in arguments:results.append(task(arg));progress(completed_blocks=len(results),total_blocks=n)
    else:
        with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn')) as pool:
            for future in as_completed([pool.submit(task,arg) for arg in arguments]):
                results.append(future.result());progress(completed_blocks=len(results),total_blocks=n)
    result=dict(workers=workers,active_seconds=time.perf_counter()-tick,tasks=sorted(results,key=lambda r:r['block']))
    save(out/'batch.json',result);return result


def finish(out,result,main):
    blocks=[read(out/'blocks'/f"block_{r['block']:03d}.json") for r in result['tasks']]
    summary=report.produce(out,blocks,main);n=len(result['tasks'])
    checked=dict(passed=True,independent_networks=n,**{key:sum(r[key] for r in result['tasks']) for key in TOTALS},
        serialized_rows_checked=summary['serialized_rows_checked'],actual_handoffs_per_lineage=2,
        max_projection_record_error=max(r['max_projection_record_error'] for r in result['tasks']),
        max_field_error=max(r['max_field_error'] for r in result['tasks']),
        max_pair_energy_error=max(r['max_pair_energy_error'] for r in result['tasks']),
        minimum_decision_boundary_distance=min(r['minimum_decision_boundary_distance'] for r in result['tasks']),
        findings=summary['findings'],population_qualification=False,comparative_superiority_qualified=False,
        all_packets_and_predecessors_verified=True,copy_invariance=True,historical_verdicts_unchanged=True)
    assert checked['assay_cases']==720*n and checked['records']==303*n and checked['writer_packets']==234*n
    assert checked['independently_verified_rows']==(1440+344+720+303)*n+checked['unique_neural_reads']
    save(out/'verification.json',checked);return checked


def execute(out):
    assert ROOT==out/'source';tick=time.perf_counter();status=dict(state='RUNNING',phase='verify_inputs',workers=0,pid=os.getpid(),started_utc=utc())
    def progress(**kw):
        status.update(kw,updated_utc=utc(),elapsed_seconds=time.perf_counter()-tick)
        save(out/'STATUS.json',status);print(json.dumps(status),flush=True)
    admissions=[]
    def admit(phase,workers,n=None):
        counts=dict(completed_blocks=0,total_blocks=n) if n is not None else {}
        progress(phase=phase+'_admission',workers=0,**counts)
        admissions.append(capacity(out/(phase+'_admission.json'),workers,progress));progress(state='RUNNING',phase=phase,workers=workers)
    try:
        progress();config=verify_inputs(out);check_threads();results={}
        admit('fixtures',1);tests=fixtures.run(out/'report_fixture',read(out/'input_bindings.json'));save(out/'fixtures.json',tests)
        for group,workers in (('engineering_serial',1),('engineering_parallel',4)):
            admit(group,workers,4);results[group]=batch(out/group,'engineering',4,workers,progress)
        equal=compare(out);serial,parallel=[results[k]['active_seconds'] for k in ('engineering_serial','engineering_parallel')]
        workers=4 if serial/parallel>=1.15 else 1;forecast=1.25*(parallel if workers==4 else serial)*4+90
        choice=dict(workers=workers,serial_seconds=serial,parallel_seconds=parallel,speedup=serial/parallel,
            threshold=1.15,**equal,main_forecast_seconds=forecast,decided_before_main=True,decided_utc=utc())
        save(out/'worker_choice.json',choice);progress(main_forecast_seconds=forecast)
        size=sum(p.stat().st_size for p in (out/'engineering_serial').rglob('*') if p.is_file());needed=int(4*size*4+200_000_000)
        assert shutil.disk_usage(out).free>needed,'insufficient retained-data disk space'
        save(out/'storage_forecast.json',dict(engineering_bytes=size,conservative_main_bytes=needed,free_bytes=shutil.disk_usage(out).free))
        admit('engineering_report',1);engineering=finish(out/'engineering_serial',results['engineering_serial'],False)
        admit('main',workers,16);result=batch(out/'main','development',16,workers,progress)
        admit('main_report',1);main=finish(out/'main',result,True)
        progress(phase='closeout');verify_inputs(out)
        for name in FILES:assert checksum(out/'source'/name)==checksum(Path(config['lane_root'])/name),name
        waits=sum(r['wait_seconds'] for r in admissions)
        save(out/'execution_summary.json',dict(passed=True,fixtures=read(out/'fixtures.json')['count'],engineering=engineering,main=main,
            worker_choice=choice,capacity_wait_seconds=waits,active_seconds=time.perf_counter()-tick-waits,
            source_files_unchanged=len(FILES),parent_unchanged=True,historical_verdicts_unchanged=True,next_campaign_launched=False))
        progress(state='COMPLETE',phase='complete',workers=0,completed_utc=utc(),integrity_passed=True)
        save(out/'COMPLETE.json',status)
        seal(out,'checksums.json',[p for p in sorted(out.rglob('*')) if p.is_file() and p.name!='checksums.json'])
        verify(out,'checksums.json');receipt=Path(config['closeout_receipt']);assert not receipt.exists()
        save(receipt,dict(passed=True,completed_utc=utc(),run=str(out),manifest_sha256=checksum(out/'checksums.json'),
            main_rows=main['independently_verified_rows'],main_checks=main['numerical_checks'],findings=main['findings'],
            actual_handoffs=2,historical_verdicts_unchanged=True,next_campaign_launched=False))
    except BaseException:
        failure=dict(state='FAILED',phase=status['phase'],failed_utc=utc(),error=traceback.format_exc())
        if (out/'checksums.json').exists():save(out.with_name(out.name+'_postseal_failure.json'),failure)
        else:progress(**failure,workers=0);save(out/'FAILED.json',status)
        raise


def prepare(out):
    assert out.is_relative_to(ROOT/'runs') and out.name.startswith('h089_composition_')
    suffix=out.name.removeprefix('h089_composition_');receipt=ROOT/'.cache'/('h089_closeout_'+suffix+'.json')
    assert not any(p.exists() for p in (out,out.with_suffix('.pid'),out.with_suffix('.log'),out.with_name(out.name+'_launch.json'),receipt))
    parent=ROOT/'runs/h088_synchrony_v1';assert checksum(parent/'checksums.json')==PIN;verify(parent,'checksums.json')
    assert read(parent/'COMPLETE.json')['integrity_passed'] and len(FILES)==len(set(FILES))
    for name in PARENT_FILES:assert checksum(ROOT/name)==checksum(parent/'source'/name),name
    bound=archives(ROOT)
    out.mkdir(parents=True,exist_ok=False);source_copy(out)
    save(out/'input_bindings.json',bound);save(out/'historical_verdicts.json',history(parent))
    save(out/'config.json',dict(experiment='H089',created_utc=utc(),lane_root=str(ROOT),python=sys.version,numpy=np.__version__,
        parent=str(parent),parent_manifest_sha256=PIN,archive_manifest_sha256=ARCHIVE_PIN,
        root_seed=89089,networks=16,engineering=4,actual_handoffs=2,generations=[0,1,2],assay_cases_per_network=720,
        contrast_count=172,primary_comparators=list(measure.PRIMARY_COMPARATORS),classification='fresh held-out composition development pilot',
        training_indices=m.TRAIN.tolist(),heldout_indices=m.TEST.tolist(),capability_task_fraction=.75,source_gap=.25,
        worker_candidates=[1,4],shared_cpu_limit=12,numerical_threads=1,closeout_receipt=str(receipt),
        watch_receipt=str(ROOT/'.cache'/('h089_watch_'+suffix+'.json')),next_campaign_launched=False))
    seal(out,'freeze.json',[p for p in sorted(out.rglob('*')) if p.is_file()]);launch(out,'--execute')


if __name__=='__main__':
    p=argparse.ArgumentParser();mode=p.add_mutually_exclusive_group(required=True)
    for name in ('prepare','execute','watch'):mode.add_argument('--'+name,type=Path)
    args=p.parse_args()
    if args.prepare:prepare(args.prepare.resolve())
    elif args.execute:execute(args.execute.resolve())
    else:watch(args.watch.resolve())
