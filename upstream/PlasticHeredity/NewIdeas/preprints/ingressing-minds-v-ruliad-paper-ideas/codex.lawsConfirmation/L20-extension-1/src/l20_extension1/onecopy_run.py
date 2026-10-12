"""D154 one-copy development; reference forecasts reused, no dynamics or successor."""
import argparse
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import numpy as np
from . import onecopy_models as models,onecopy_check as checker,matched_run as previous
from laws_confirmation.io import environment_manifest,sha256_file,utc_now,atomic_json

io=previous.io;ROOT=previous.ROOT;WS=previous.WS
RUN='l20_extension1_one_copy_dev_v1_attempt1'
COMPLETE='9bf970f7a18fdfce684764a0bfbb697faefc9b24904ab57e892f99b86e2e131a'
AUDIT=ROOT/'logs/l20_extension1_matched_regularization_dev_v1_attempt1_saved_audit_v1.json'
AUDIT_HASH='f3176e0f9ce7c7a25978c11dd1879689f67feeb6291f4277cb624a33380b2380'
SCIENCE=('one-copy-baseline/PROTOCOL_V1.md','matched-regularization/RESULTS.md',
 'src/l20_extension1/onecopy_models.py','src/l20_extension1/onecopy_check.py','src/l20_extension1/onecopy_run.py',
 'tests/test_onecopy.py','scripts/run_one_copy.sh')
IDS=previous.IDS
ENV='L20_ONE_COPY_DETACHED';READY='D154_READY_FD'
ALLOWANCE=256*1024**2;RESERVE=4*1024**3


def paths():return ROOT/'runs'/RUN,ROOT/'outputs'/RUN
def freeze_path():return ROOT/'tmp'/f'{RUN}_freeze.json'
def timing_path():return ROOT/'tmp'/f'{RUN}_benchmark.json'
def benchmark_dir():return ROOT/'tmp'/f'{RUN}_benchmark'
def logfile(stage):return ROOT/'logs'/f'{RUN}_{stage}.log'


def resources(starting=True):
    previous.resources(False)
    if shutil.disk_usage(ROOT).free<RESERVE+(ALLOWANCE if starting else 0):raise RuntimeError('external reserve required')


def contract():
    return dict(run=RUN,source_complete=COMPLETE,source_audit=AUDIT_HASH,blocks=IDS.tolist(),cases=512,
        observers=list(models.MODELS),alphas=list(models.ALPHAS),pairs=list(map(list,models.PAIRS)),
        model_class=models.prior.group.CLASS,common_deviation_penalty_ratio=1,
        features='starting_7_then_U0_endpoint_6',new_feature_dimension=13,new_penalized_dimension=52,
        all_cases_retained=True,outer_whole_founder_folds=32,inner_selection=False,
        new_fits=96,new_predictions=1536,reference_fits_recomputed=False,reference_summary_exact=True,
        new_contrasts=21,retained_contrasts=90,equal_observation_budget=False,
        new_dynamics=0,new_founders=0,new_diagnostic_cycles=0,prospective_evidence=False,
        former_test_is_development=True,repeated_futures_training=False,no_best_alpha_selected=True,
        maximum_cpus=6,workers=1,numerical_threads=1,allowance=ALLOWANCE,reserve=RESERVE,
        benchmark_forecast='4*qualified_full_comparison_seconds+120',
        main_forecast='2*checked_full_comparison_seconds+2*hash_seconds+120',
        automatic_polling=False,automatic_retry=False,automatic_successor=False)


def source_files():
    run,out=previous.paths();c=io.read_json(run/'COMPLETE.json');m=io.read_json(run/'MANIFEST.json')
    assert sha256_file(run/'COMPLETE.json')==COMPLETE and c['status']=='COMPLETE'
    assert not (run/'FAILED.json').exists() and io.read_json(run/'STATUS.json')==c
    assert sha256_file(run/'MANIFEST.json')==c['manifest_sha256'] and m['environment']==environment_manifest()
    assert len(m['input_sha256'])==2032 and len(c['output_sha256'])==9
    expected={**m['input_sha256'],**c['output_sha256']}
    assert expected==io.hashes([Path(p) for p in expected])
    assert sha256_file(out/'output_hashes.sha256')==c['hash_index_sha256']
    assert (out/'output_hashes.sha256').read_text()==io.hash_text(c['output_sha256'])
    assert all(str(out/name) in expected for name in ('dataset.npz','predictions.npz','fits.json','summary.json','nested_predictions.npz'))
    assert sha256_file(AUDIT)==AUDIT_HASH;proof=io.read_json(AUDIT)
    assert proof['passes'] and proof['complete_sha256']==COMPLETE and proof['new_dynamics']==0 and proof['new_fixed_fits']==576 and proof['source_primary_unchanged']
    assert proof['input_hashes']==2032 and proof['outputs']==9
    files={Path(p) for p in expected}
    files.update((run/'COMPLETE.json',run/'STATUS.json',run/'MANIFEST.json',out/'output_hashes.sha256',AUDIT))
    files.update(WS/p for p in SCIENCE);return sorted(files)


def qualification(path):
    io.require_beneath(path,ROOT/'logs');tree=ET.parse(path).getroot();cases=tree.findall('.//testcase')
    assert len(cases)>=40 and not any(tree.findall('.//'+n) for n in ('error','failure','skipped'))
    assert len({(c.get('classname'),c.get('name')) for c in cases})==len(cases)
    ours=[c for c in cases if c.get('classname','').endswith('test_onecopy')]
    required={'test_full_comparison','test_outer_isolation','test_future_not_training','test_one_copy_boundary',
        'test_group_permutation','test_summary_corruption','test_model_corruption','test_mean_sham',
        'test_source_closure','test_source_identity','test_resource_guard','test_detach_guard',
        'test_startup_handshake','test_no_automatic_successor','test_roundtrip','test_no_reference_fits',
        'test_constants','test_clipping','test_error_corruption','test_reference_scores'}
    assert required<={c.get('name').split('[',1)[0] for c in ours}
    seconds=max(float(c.get('time')) for c in ours if c.get('name')=='test_full_comparison')
    return dict(report=str(path),tests=len(cases),failures=0,skipped=0,
        qualified_full_comparison_seconds=seconds,benchmark_forecast=4*seconds+120)


def freeze(report):
    resources()
    if any(p.exists() for p in (freeze_path(),timing_path(),benchmark_dir(),*paths(),logfile('execute'),logfile('benchmark'))):
        raise FileExistsError('single-use stage already exists')
    proof=qualification(report);tick=time.monotonic();inputs=io.hashes(source_files()+[report]);seconds=time.monotonic()-tick
    value=dict(frozen_utc=utc_now(),contract=contract(),test_proof=proof,input_sha256=inputs,
        environment=environment_manifest(),source_audit=io.read_json(AUDIT),source_hash_seconds=seconds,actual_cases_fitted=False)
    io.write_json(freeze_path(),value,ROOT)
    print(json.dumps(dict(status='FROZEN',inputs=len(inputs),test_proof=proof,source_hash_seconds=seconds)),flush=True)


def frozen():
    f=io.read_json(freeze_path());assert f['contract']==contract() and f['environment']==environment_manifest()
    report=Path(f['test_proof']['report']);assert f['test_proof']==qualification(report)
    assert f['input_sha256']==io.hashes(source_files()+[report]) and f['actual_cases_fitted'] is False
    assert f['source_audit']==io.read_json(AUDIT);return f


def detached_guard(required,stage):
    if required and os.environ.get(ENV)!='1':raise RuntimeError('forecast above ten minutes requires detachment')
    if os.environ.get(ENV)=='1':
        assert os.getpid()==os.getsid(0) and os.readlink('/proc/self/fd/0')=='/dev/null'
        assert Path(os.readlink('/proc/self/fd/1'))==logfile(stage)
        assert os.readlink('/proc/self/fd/2')==os.readlink('/proc/self/fd/1')


def ready(stage):
    descriptor=os.environ.pop(READY,None)
    if descriptor is not None:
        fd=int(descriptor)
        try:os.write(fd,json.dumps(dict(stage=stage,pid=os.getpid(),status='STARTED')).encode())
        except BrokenPipeError:pass
        finally:os.close(fd)


def benchmark():
    resources();f=frozen();detached_guard(f['test_proof']['benchmark_forecast']>600,'benchmark')
    directory=benchmark_dir();directory.mkdir()
    try:
        ready('benchmark');tick=time.monotonic();data,references,nested,source=models.fixture();p,m=models.fit_all(data)
        io.write_npz(directory/'synthetic.npz',data,ROOT);io.write_npz(directory/'predictions.npz',p,ROOT)
        io.write_json(directory/'fits.json',m,ROOT);io.write_npz(directory/'reference_predictions.npz',references,ROOT)
        io.write_npz(directory/'reference_nested_predictions.npz',nested,ROOT)
        io.write_json(directory/'summary.json',models.summarize(p,references,source,data),ROOT)
        io.write_npz(directory/'case_errors.npz',models.case_errors(p,references,nested,data),ROOT)
        proof=verify_benchmark();model_seconds=time.monotonic()-tick;tick=time.monotonic();frozen();hash_seconds=time.monotonic()-tick
        size=sum(p.stat().st_size for p in directory.iterdir());budget=4*size+64*1024**2;assert budget<=ALLOWANCE
        forecast=2*model_seconds+2*hash_seconds+120
        t=dict(status='COMPLETE',completed_utc=utc_now(),verification=proof,
            checked_full_comparison_seconds=model_seconds,hash_seconds=hash_seconds,projected_seconds=forecast,
            must_detach=forecast>600,benchmark_bytes=size,projected_bytes=budget,
            freeze_sha256=sha256_file(freeze_path()),output_sha256=io.hashes(list(directory.iterdir())),
            scientific_evidence=False,actual_cases_fitted=False,new_dynamics=0)
        io.write_json(timing_path(),t,ROOT);print(json.dumps(t,indent=2),flush=True)
    except Exception as error:io.failure(directory,error,ROOT);raise


def verify_benchmark():
    d=benchmark_dir();data=io.load_npz(d/'synthetic.npz');p=io.load_npz(d/'predictions.npz');m=io.read_json(d/'fits.json')
    references=io.load_npz(d/'reference_predictions.npz');nested=io.load_npz(d/'reference_nested_predictions.npz')
    expected,guesses,old,source=models.fixture()
    for actual,wanted in ((data,expected),(references,guesses),(nested,old)):
        assert set(actual)==set(wanted)
        for k in wanted:np.testing.assert_array_equal(actual[k],wanted[k])
    return dict(fits=checker.check_all(p,m,data),reference_fits_recomputed=False,
        summary=checker.check_summary(io.read_json(d/'summary.json'),p,references,nested,source,data),
        errors=checker.check_errors(io.load_npz(d/'case_errors.npz'),p,references,nested,data))


def timing_checked(audit=False):
    t=io.read_json(timing_path());assert t['status']=='COMPLETE' and t['scientific_evidence'] is t['actual_cases_fitted'] is False
    assert t['freeze_sha256']==sha256_file(freeze_path()) and t['new_dynamics']==0
    assert {p.name for p in benchmark_dir().iterdir()}=={'synthetic.npz','predictions.npz','fits.json',
        'reference_predictions.npz','reference_nested_predictions.npz','summary.json','case_errors.npz'}
    assert t['output_sha256']==io.hashes(list(benchmark_dir().iterdir()))
    assert t['benchmark_bytes']==sum(p.stat().st_size for p in benchmark_dir().iterdir())
    assert t['projected_seconds']==2*t['checked_full_comparison_seconds']+2*t['hash_seconds']+120
    assert t['must_detach']==(t['projected_seconds']>600)
    assert t['projected_bytes']==4*t['benchmark_bytes']+64*1024**2<=ALLOWANCE
    if audit:assert verify_benchmark()==t['verification']
    return t


def inputs():
    f=frozen();timing_checked()
    return io.hashes([Path(p) for p in f['input_sha256']]+[freeze_path(),timing_path(),*benchmark_dir().iterdir()])


def output_names():
    return ['dataset.npz','predictions.npz','fits.json','reference_predictions.npz','reference_nested_predictions.npz',
        'case_errors.npz','summary.json','verification.json','input_hashes.sha256']


def source_data():
    out=previous.paths()[1];data=io.load_npz(out/'dataset.npz')
    assert set(data)=={'start','endpoint','targeted','labels','futures','block_ids'}
    assert data['start'].shape==(32,4,4,7) and data['endpoint'].shape==data['targeted'].shape==(32,4,4,3,6)
    assert data['labels'].shape==(32,4,4) and data['futures'].shape==(16,4,4,4)
    np.testing.assert_array_equal(data['block_ids'],IDS)
    for name,value in data.items():
        assert value.dtype==(np.int64 if name=='block_ids' else np.float64) and np.isfinite(value).all()
    assert np.max(abs(data['labels']))<=1 and np.max(abs(data['futures']))<=1
    return data,io.load_npz(out/'predictions.npz'),io.load_npz(out/'nested_predictions.npz'),io.read_json(out/'summary.json')


def check_source_identity(data,references,nested,summary):
    expected,guesses,old,source=source_data()
    for actual,wanted in ((data,expected),(references,guesses),(nested,old)):
        assert set(actual)==set(wanted)
        for k in wanted:np.testing.assert_array_equal(actual[k],wanted[k])
    assert summary['retained_d153']==source
    return dict(passes=True,exact_fixed_observers=6,exact_nested_observers=6,exact_source_arrays=6,exact_reference_summary=True)


def verify_saved():
    out=paths()[1];data=io.load_npz(out/'dataset.npz');p=io.load_npz(out/'predictions.npz');m=io.read_json(out/'fits.json')
    references=io.load_npz(out/'reference_predictions.npz');nested=io.load_npz(out/'reference_nested_predictions.npz')
    s=io.read_json(out/'summary.json');source=io.read_json(previous.paths()[1]/'summary.json')
    proof=check_source_identity(data,references,nested,s);fits=checker.check_all(p,m,data)
    score=checker.check_summary(s,p,references,nested,source,data)
    errors=checker.check_errors(io.load_npz(out/'case_errors.npz'),p,references,nested,data)
    return dict(source=proof,fits=fits,summary=score,errors=errors,
        reference_fits_recomputed=False,new_dynamics=0,prospective_evidence=False)


def saved_audit():
    resources(False);run,out=paths();m=io.read_json(run/'MANIFEST.json')
    assert m['input_sha256']==inputs() and m['contract']==contract() and m['environment']==environment_manifest()
    assert m['actual_cases_fitted'] is False and m['prepared_utc']>=io.read_json(freeze_path())['frozen_utc']
    assert {p.name for p in out.iterdir()}==set(output_names())|{'output_hashes.sha256'}
    assert (out/'input_hashes.sha256').read_text()==io.hash_text(m['input_sha256'])
    proof=verify_saved();assert io.read_json(out/'verification.json')==proof
    c=io.read_json(run/'COMPLETE.json');assert c['status']=='COMPLETE' and io.read_json(run/'STATUS.json')==c
    assert not (run/'FAILED.json').exists() and (run/'EXECUTION.lock').is_dir()
    assert c['manifest_sha256']==sha256_file(run/'MANIFEST.json') and c['verification']==proof
    assert c['output_sha256']==io.hashes([out/n for n in output_names()])
    assert c['hash_index_sha256']==sha256_file(out/'output_hashes.sha256')
    assert (out/'output_hashes.sha256').read_text()==io.hash_text(c['output_sha256'])
    assert c['output_bytes']==sum(p.stat().st_size for p in out.iterdir())<=ALLOWANCE
    return dict(passes=True,input_hashes=len(m['input_sha256']),outputs=len(output_names()),blocks=32,cases=512,
        new_fixed_fits=96,reference_fits_recomputed=False,reference_observers_reused=6,new_dynamics=0,prospective_evidence=False,source_primary_unchanged=True)


def execute():
    resources();pin=inputs();t=timing_checked(True);detached_guard(t['must_detach'],'execute');run,out=paths()
    if run.exists() or out.exists():raise FileExistsError('single-use paths already exist')
    run.mkdir();out.mkdir();began=time.monotonic()
    try:
        manifest=dict(prepared_utc=utc_now(),contract=contract(),input_sha256=pin,timing=t,environment=environment_manifest(),
            affinity=sorted(os.sched_getaffinity(0)),actual_cases_fitted=False)
        io.write_json(run/'MANIFEST.json',manifest,ROOT)
        with (out/'input_hashes.sha256').open('x') as stream:stream.write(io.hash_text(pin))
        (run/'EXECUTION.lock').mkdir();ready('execute');data,references,nested,source=source_data()
        io.write_npz(out/'dataset.npz',data,ROOT);io.write_npz(out/'reference_predictions.npz',references,ROOT)
        io.write_npz(out/'reference_nested_predictions.npz',nested,ROOT);completed=[]
        def progress(block):
            completed.append(block);atomic_json(run/'STATUS.json',dict(status='FITTING_ONE_COPY',blocks_done=completed,updated_utc=utc_now()),ROOT)
        atomic_json(run/'STATUS.json',dict(status='FITTING_ONE_COPY',blocks_done=[],updated_utc=utc_now()),ROOT)
        p,m=models.fit_all(data,progress);s=models.summarize(p,references,source,data)
        io.write_npz(out/'predictions.npz',p,ROOT);io.write_json(out/'fits.json',m,ROOT)
        io.write_npz(out/'case_errors.npz',models.case_errors(p,references,nested,data),ROOT);io.write_json(out/'summary.json',s,ROOT)
        atomic_json(run/'STATUS.json',dict(status='INDEPENDENT_SAVED_CHECK',updated_utc=utc_now()),ROOT)
        proof=verify_saved();io.write_json(out/'verification.json',proof,ROOT);assert pin==inputs()
        hashes=io.hashes([out/n for n in output_names()])
        with (out/'output_hashes.sha256').open('x') as stream:stream.write(io.hash_text(hashes))
        size=sum(p.stat().st_size for p in out.iterdir());assert size<=ALLOWANCE
        c=dict(status='COMPLETE',completed_utc=utc_now(),elapsed_seconds=time.monotonic()-began,output_bytes=size,
            manifest_sha256=sha256_file(run/'MANIFEST.json'),output_sha256=hashes,hash_index_sha256=sha256_file(out/'output_hashes.sha256'),
            verification=proof,new_dynamics=0,automatic_polling=False,automatic_retry=False,automatic_successor=False)
        io.write_json(run/'COMPLETE.json',c,ROOT);atomic_json(run/'STATUS.json',c,ROOT)
        print(json.dumps({k:v for k,v in c.items() if k not in ('output_sha256','verification')},indent=2),flush=True)
    except Exception as error:
        io.failure(run,error,ROOT);atomic_json(run/'STATUS.json',dict(status='FAILED',error=str(error),failed_utc=utc_now()),ROOT);raise


def audit(seal=False):
    t=timing_checked();detached_guard(t['must_detach'],'audit');ready('audit');tick=time.monotonic();proof=saved_audit()
    proof.update(checked_utc=utc_now(),elapsed_seconds=time.monotonic()-tick,
        complete_sha256=sha256_file(paths()[0]/'COMPLETE.json'),runner_sha256=sha256_file(Path(__file__)),
        checker_sha256=sha256_file(Path(checker.__file__)))
    if seal:io.write_json(ROOT/'logs'/f'{RUN}_saved_audit_v1.json',proof,ROOT)
    print(json.dumps(proof,indent=2),flush=True)


def detach(stage):
    resources();frozen()
    if stage=='execute':timing_checked();assert not any(p.exists() for p in paths())
    elif stage=='benchmark':assert not benchmark_dir().exists() and not timing_path().exists()
    elif stage=='audit':timing_checked();assert (paths()[0]/'COMPLETE.json').exists()
    else:raise ValueError('declared stage')
    lock=ROOT/'tmp'/f'{RUN}_{stage}_launch.lock';lock.mkdir();env=os.environ.copy();env[ENV]='1'
    reader,writer=os.pipe();env[READY]=str(writer)
    try:
        with logfile(stage).open('xb') as stream:
            child=subprocess.Popen([sys.executable,'-m','l20_extension1.onecopy_run','--'+('seal-audit' if stage=='audit' else stage)],
                cwd=WS.parent,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,
                start_new_session=True,pass_fds=(writer,))
    finally:os.close(writer)
    readable,_,_=select.select([reader],[],[],55);data=os.read(reader,4096) if readable else b'';os.close(reader)
    ack=json.loads(data) if data else None
    if ack is not None:assert ack==dict(stage=stage,pid=child.pid,status='STARTED')
    receipt=dict(status='DETACHED',stage=stage,pid=child.pid,launched_utc=utc_now(),startup_acknowledged=ack is not None,
        log=str(logfile(stage)),automatic_polling=False,automatic_retry=False,automatic_successor=False)
    io.write_json(lock/'LAUNCH.json',receipt,ROOT);print(json.dumps(receipt,indent=2),flush=True)


def main():
    if sys.flags.optimize:raise RuntimeError('assertions must remain enabled')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--test-report',type=Path)
    group=parser.add_mutually_exclusive_group(required=True)
    for name in ('freeze','benchmark','benchmark-audit','execute','audit','seal-audit','detach','detach-benchmark','detach-audit'):
        group.add_argument('--'+name,action='store_true')
    a=parser.parse_args()
    if a.freeze!=(a.test_report is not None):parser.error('test report only with freeze')
    if a.freeze:freeze(a.test_report)
    elif a.benchmark:benchmark()
    elif a.benchmark_audit:
        resources(False);frozen();t=timing_checked(True);print(json.dumps(dict(passes=True,projected_seconds=t['projected_seconds'],new_dynamics=0)))
    elif a.execute:execute()
    elif a.audit or a.seal_audit:audit(a.seal_audit)
    else:detach('benchmark' if a.detach_benchmark else 'audit' if a.detach_audit else 'execute')


if __name__=='__main__':main()
