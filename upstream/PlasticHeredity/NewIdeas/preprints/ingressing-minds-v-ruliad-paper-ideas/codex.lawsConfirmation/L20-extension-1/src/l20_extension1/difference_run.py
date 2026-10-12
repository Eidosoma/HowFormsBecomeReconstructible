"""D160 matched-penalty raw difference-channel ablation; no dynamics or selection."""
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
from . import reading_parts_run as previous,difference_ablation as models,difference_check as checker
from laws_confirmation.io import environment_manifest,sha256_file,utc_now,atomic_json

io=previous.io;ROOT=previous.ROOT;WS=previous.WS
RUN='l20_extension1_difference_ablation_dev_v1_attempt1'
COMPLETE='437b6365798078f83d630192e4f1ce7b535d1a1918ec82c07d850d6ea392a675'
AUDIT=ROOT/'logs/l20_extension1_reading_components_dev_v1_attempt1_saved_audit_v1.json'
AUDIT_HASH='5ea0b0a99e191ec4bf8199470150c9a7d8fee51bd5cbe86ac1bb8e5989feb13c'
SCIENCE=('difference-ablation/PROTOCOL_V1.md','reading-components/RESULTS.md',
 'src/l20_extension1/difference_ablation.py','src/l20_extension1/difference_check.py','src/l20_extension1/difference_run.py',
 'tests/test_difference_ablation.py','scripts/run_difference_ablation.sh')
ENV='L20_DIFFERENCE_ABLATION_DETACHED';READY='D160_READY_FD';ALLOWANCE=2*1024**3;RESERVE=4*1024**3


def paths():return ROOT/'runs'/RUN,ROOT/'outputs'/RUN
def freeze_path():return ROOT/'tmp'/f'{RUN}_freeze.json'
def timing_path():return ROOT/'tmp'/f'{RUN}_benchmark.json'
def benchmark_dir():return ROOT/'tmp'/f'{RUN}_benchmark'
def logfile(stage):return ROOT/'logs'/f'{RUN}_{stage}.log'


def resources(starting=True):
    previous.resources(False)
    if shutil.disk_usage(ROOT).free<RESERVE+(ALLOWANCE if starting else 0):raise RuntimeError('external reserve required')


def contract():
    return dict(run=RUN,source_complete=COMPLETE,source_audit=AUDIT_HASH,founder_ids=list(range(90000,90016)),
        **models.metadata(16),comparisons=[list(p) for p in models.PAIRS],
        raw_difference_constraint=True,unchanged_original_penalty=True,mean_target_only=True,
        workers=1,maximum_cpus=6,numerical_threads=1,allowance=ALLOWANCE,reserve=RESERVE,
        benchmark_forecast='48*qualified_small_audit_seconds+120',
        main_forecast='2*checked_full_audit_seconds+2*hash_seconds+120',
        automatic_polling=False,automatic_retry=False)

def source_files():
    run,out=previous.paths();c=io.read_json(run/'COMPLETE.json');m=io.read_json(run/'MANIFEST.json')
    assert sha256_file(run/'COMPLETE.json')==COMPLETE and c['status']=='COMPLETE'
    assert not (run/'FAILED.json').exists() and io.read_json(run/'STATUS.json')==c
    assert sha256_file(run/'MANIFEST.json')==c['manifest_sha256'] and m['environment']==environment_manifest()
    assert len(m['input_sha256'])==2217 and len(c['output_sha256'])==5
    expected={**m['input_sha256'],**c['output_sha256']}
    assert expected==io.hashes([Path(p) for p in expected])
    assert sha256_file(out/'output_hashes.sha256')==c['hash_index_sha256']
    assert (out/'output_hashes.sha256').read_text()==io.hash_text(c['output_sha256'])
    assert sha256_file(AUDIT)==AUDIT_HASH;proof=io.read_json(AUDIT)
    assert proof['passes'] and proof['complete_sha256']==COMPLETE and proof['source_primary_unchanged']
    assert proof['input_hashes']==2217 and proof['outputs']==5 and proof['new_dynamics']==0
    assert proof['new_fits']==0 and proof['new_predictions']==0 and proof['observer_comparison_records']==5445
    assert proof['saved_models_replayed']==9216 and proof['saved_forecasts_replayed']==147456
    assert proof['training_effect_records']==672
    files={Path(p) for p in expected};files.update((run/'COMPLETE.json',run/'STATUS.json',run/'MANIFEST.json',out/'output_hashes.sha256',AUDIT))
    files.update(WS/p for p in SCIENCE);return sorted(files)

def qualification(path):
    io.require_beneath(path,ROOT/'logs');tree=ET.parse(path).getroot();cases=tree.findall('.//testcase')
    assert len(cases)>=50 and not any(tree.findall('.//'+n) for n in ('error','failure','skipped'))
    assert len({(c.get('classname'),c.get('name')) for c in cases})==len(cases)
    ours=[c for c in cases if c.get('classname','').endswith('test_difference_ablation')]
    required={'test_small_audit','test_embedding','test_full_metric','test_raw_not_standardized_tying',
        'test_exclusion_isolation','test_heldout_features','test_original_not_training','test_feature_boundary',
        'test_repeat_permutation','test_founder_permutation','test_group_permutation','test_equal_mean_invariance',
        'test_clipping','test_constants','test_rank_deficient','test_fit_corruption','test_source_corruption',
        'test_summary_corruption','test_error_corruption','test_mean_losses','test_source_bridge','test_roundtrip',
        'test_complete_specs','test_source_closure','test_resource_guard','test_detach_guard','test_startup_handshake',
        'test_no_automatic_successor','test_no_dynamics_or_reference_refits'}
    assert required<={c.get('name').split('[',1)[0] for c in ours}
    seconds=max(float(c.get('time')) for c in ours if c.get('name')=='test_small_audit')
    return dict(report=str(path),tests=len(cases),failures=0,skipped=0,qualified_small_audit_seconds=seconds,
        benchmark_forecast=48*seconds+120)

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


def fixture_write(directory):
    data,b,br,p,raw,bfits,rfits=models.fixture()
    for name,values in (('synthetic',data),('baseline',b),('baseline_raw',br),('predictions',p),('raw_predictions',raw)):
        io.write_npz(directory/(name+'.npz'),values,ROOT)
    io.write_json(directory/'baseline_fits.json',bfits,ROOT);io.write_json(directory/'fits.json',rfits,ROOT)
    io.write_json(directory/'source_summary.json',models.prior.summarize(p,raw,b,br,data),ROOT)
    write_experiment(directory,data,b,br,p,raw,bfits,rfits)

def write_experiment(directory,data,b,br,p,raw,bfits,rfits,progress=None):
    nb,nbr,npred,nraw,records=models.fit_all(data,b,br,p,raw,bfits,rfits,progress)
    for name,values in (('tied_full',nb),('tied_full_raw',nbr),('tied_deletions',npred),('tied_deletions_raw',nraw)):
        io.write_npz(directory/(name+'.npz'),values,ROOT)
    io.write_json(directory/'tied_fits.json',records,ROOT)
    io.write_json(directory/'summary.json',models.summarize(b,br,p,raw,nb,nbr,npred,nraw,data),ROOT)
    io.write_npz(directory/'case_errors.npz',models.case_errors(nb,npred,b,p,data),ROOT)

def benchmark():
    resources();f=frozen();detached_guard(f['test_proof']['benchmark_forecast']>600,'benchmark')
    directory=benchmark_dir();directory.mkdir()
    try:
        ready('benchmark');tick=time.monotonic();fixture_write(directory)
        checked=verify_benchmark();review_seconds=time.monotonic()-tick;tick=time.monotonic();frozen();hash_seconds=time.monotonic()-tick
        size=sum(p.stat().st_size for p in directory.iterdir());budget=4*size+64*1024**2;assert budget<=ALLOWANCE
        forecast=2*review_seconds+2*hash_seconds+120
        value=dict(status='COMPLETE',completed_utc=utc_now(),verification=checked,checked_full_audit_seconds=review_seconds,
            hash_seconds=hash_seconds,projected_seconds=forecast,must_detach=forecast>600,benchmark_bytes=size,projected_bytes=budget,
            freeze_sha256=sha256_file(freeze_path()),output_sha256=io.hashes(list(directory.iterdir())),
            scientific_evidence=False,synthetic_reference_fits=9216,synthetic_new_fits=3840,new_dynamics=0,actual_cases_fitted=False)
        io.write_json(timing_path(),value,ROOT);print(json.dumps(value,indent=2),flush=True)
    except Exception as error:io.failure(directory,error,ROOT);raise


def verify_benchmark():
    d=benchmark_dir();data=io.load_npz(d/'synthetic.npz')
    for k,v in models.prior.fixture().items():np.testing.assert_array_equal(data[k],v)
    b=io.load_npz(d/'baseline.npz');br=io.load_npz(d/'baseline_raw.npz')
    p=io.load_npz(d/'predictions.npz');raw=io.load_npz(d/'raw_predictions.npz')
    bf=io.read_json(d/'baseline_fits.json');rf=io.read_json(d/'fits.json')
    return verify_experiment(d,data,b,br,p,raw,bf,rf,io.read_json(d/'source_summary.json'))

def verify_experiment(directory,data,b,br,p,raw,bfits,rfits,source):
    nb=io.load_npz(directory/'tied_full.npz');nbr=io.load_npz(directory/'tied_full_raw.npz')
    npred=io.load_npz(directory/'tied_deletions.npz');nraw=io.load_npz(directory/'tied_deletions_raw.npz')
    records=io.read_json(directory/'tied_fits.json');s=io.read_json(directory/'summary.json')
    return dict(fits=checker.check_all(nb,nbr,npred,nraw,records,data,b,br,p,raw,bfits,rfits),
        summary=checker.check_summary(s,nb,nbr,npred,nraw,data,b,br,p,raw),
        errors=checker.check_errors(io.load_npz(directory/'case_errors.npz'),nb,npred,b,p,data),
        source_bridge=checker.source_bridge(s,source,data,b,br,p,raw),new_dynamics=0,
        reference_fits_recomputed=False,prospective_evidence=False)

def timing_checked(audit=False):
    t=io.read_json(timing_path());assert t['status']=='COMPLETE' and t['scientific_evidence'] is t['actual_cases_fitted'] is False
    assert t['freeze_sha256']==sha256_file(freeze_path()) and t['new_dynamics']==0 and t['synthetic_reference_fits']==9216 and t['synthetic_new_fits']==3840
    assert {p.name for p in benchmark_dir().iterdir()}=={'synthetic.npz','baseline.npz','baseline_raw.npz','predictions.npz','raw_predictions.npz',
        'baseline_fits.json','fits.json','source_summary.json','tied_full.npz','tied_full_raw.npz',
        'tied_deletions.npz','tied_deletions_raw.npz','tied_fits.json','case_errors.npz','summary.json'}
    assert t['output_sha256']==io.hashes(list(benchmark_dir().iterdir()))
    assert t['benchmark_bytes']==sum(p.stat().st_size for p in benchmark_dir().iterdir())
    assert t['projected_seconds']==2*t['checked_full_audit_seconds']+2*t['hash_seconds']+120
    assert t['must_detach']==(t['projected_seconds']>600)
    assert t['projected_bytes']==4*t['benchmark_bytes']+64*1024**2<=ALLOWANCE
    if audit:assert verify_benchmark()==t['verification']
    return t


def inputs():
    f=frozen();timing_checked()
    return io.hashes([Path(p) for p in f['input_sha256']]+[freeze_path(),timing_path(),*benchmark_dir().iterdir()])


def source_data():
    # Source data, full/deletion forecasts and coefficients were already sealed by D159.
    return previous.source_data()

def source_identity():return previous.source_identity()

def output_names():
    return ['tied_full.npz','tied_full_raw.npz','tied_deletions.npz','tied_deletions_raw.npz',
        'tied_fits.json','case_errors.npz','summary.json','verification.json','input_hashes.sha256']

def verify_saved():
    data,b,br,p,raw,bfits,rfits,source=source_data()
    return dict(source=source_identity(),
        **verify_experiment(paths()[1],data,b,br,p,raw,bfits,rfits,source))

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
    return dict(passes=True,input_hashes=len(m['input_sha256']),outputs=len(output_names()),blocks=16,cases=256,
        observers=17,new_observers=5,deletions=16,observer_orientations=99,
        observer_comparison_records=3267,training_effect_records=288,reference_observer_comparison_records=5445,
        reference_training_effect_records=672,untouched_model_geometry_checks=3840,new_fits=3840,new_predictions=61440,
        case_arrays=120,new_dynamics=0,prospective_evidence=False,source_primary_unchanged=True)


def execute():
    resources();pin=inputs();t=timing_checked(True);detached_guard(t['must_detach'],'execute');run,out=paths()
    if run.exists() or out.exists():raise FileExistsError('single-use comparison paths already exist')
    run.mkdir();out.mkdir();began=time.monotonic()
    try:
        manifest=dict(prepared_utc=utc_now(),contract=contract(),input_sha256=pin,timing=t,environment=environment_manifest(),
            affinity=sorted(os.sched_getaffinity(0)),actual_cases_fitted=False)
        io.write_json(run/'MANIFEST.json',manifest,ROOT)
        with (out/'input_hashes.sha256').open('x') as stream:stream.write(io.hash_text(pin))
        (run/'EXECUTION.lock').mkdir();ready('execute')
        atomic_json(run/'STATUS.json',dict(status='FITTING_MATCHED_ABLATIONS',updated_utc=utc_now()),ROOT)
        data,b,br,p,raw,bfits,rfits,source=source_data()
        done=[]
        def progress(name):
            done.append(name);atomic_json(run/'STATUS.json',dict(status='FITTING_MATCHED_ABLATIONS',observers_done=done,updated_utc=utc_now()),ROOT)
        write_experiment(out,data,b,br,p,raw,bfits,rfits,progress)
        atomic_json(run/'STATUS.json',dict(status='INDEPENDENT_SAVED_CHECK',updated_utc=utc_now()),ROOT)
        proof=verify_saved();io.write_json(out/'verification.json',proof,ROOT);assert pin==inputs()
        hashes=io.hashes([out/n for n in output_names()])
        with (out/'output_hashes.sha256').open('x') as stream:stream.write(io.hash_text(hashes))
        size=sum(p.stat().st_size for p in out.iterdir());assert size<=ALLOWANCE
        value=dict(status='COMPLETE',completed_utc=utc_now(),elapsed_seconds=time.monotonic()-began,output_bytes=size,
            manifest_sha256=sha256_file(run/'MANIFEST.json'),output_sha256=hashes,hash_index_sha256=sha256_file(out/'output_hashes.sha256'),
            verification=proof,new_fits=3840,new_predictions=61440,new_dynamics=0,automatic_polling=False,automatic_retry=False,automatic_successor=False)
        io.write_json(run/'COMPLETE.json',value,ROOT);atomic_json(run/'STATUS.json',value,ROOT)
        print(json.dumps({k:v for k,v in value.items() if k not in ('output_sha256','verification')},indent=2),flush=True)
    except Exception as error:
        io.failure(run,error,ROOT);atomic_json(run/'STATUS.json',dict(status='FAILED',error=str(error),failed_utc=utc_now()),ROOT);raise


def audit(seal=False):
    t=timing_checked();detached_guard(t['must_detach'],'audit');ready('audit');tick=time.monotonic();proof=saved_audit()
    proof.update(checked_utc=utc_now(),elapsed_seconds=time.monotonic()-tick,complete_sha256=sha256_file(paths()[0]/'COMPLETE.json'),
        runner_sha256=sha256_file(Path(__file__)),checker_sha256=sha256_file(Path(checker.__file__)))
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
            child=subprocess.Popen([sys.executable,'-m','l20_extension1.difference_run','--'+('seal-audit' if stage=='audit' else stage)],
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
        resources(False);frozen();t=timing_checked(True);print(json.dumps(dict(passes=True,projected_seconds=t['projected_seconds'],new_fits=0,new_dynamics=0)))
    elif a.execute:execute()
    elif a.audit or a.seal_audit:audit(a.seal_audit)
    else:detach('benchmark' if a.detach_benchmark else 'audit' if a.detach_audit else 'execute')


if __name__=='__main__':main()
