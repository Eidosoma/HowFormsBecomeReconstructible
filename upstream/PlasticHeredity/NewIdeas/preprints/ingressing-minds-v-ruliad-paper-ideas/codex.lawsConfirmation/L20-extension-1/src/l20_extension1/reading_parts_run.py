"""D159 saved forecast component accounting; no fitting, dynamics, or selection."""
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
from . import influence_run as previous,reading_parts as models,reading_parts_check as checker
from laws_confirmation.io import environment_manifest,sha256_file,utc_now,atomic_json

io=previous.io;ROOT=previous.ROOT;WS=previous.WS
RUN='l20_extension1_reading_components_dev_v1_attempt1'
COMPLETE='ad4e943be3b2bd86001d0be2050b309905ea1670cc47d98b0a57ec1e77e517f9'
AUDIT=ROOT/'logs/l20_extension1_training_influence_dev_v1_attempt1_saved_audit_v1.json'
AUDIT_HASH='69d1bd0b994a347af5ee7a50edcdb1184ea54ee84425e96132e12dd4364d75f5'
SCIENCE=('reading-components/PROTOCOL_V1.md','training-influence/RESULTS.md',
 'src/l20_extension1/reading_parts.py','src/l20_extension1/reading_parts_check.py','src/l20_extension1/reading_parts_run.py',
 'tests/test_reading_components.py','scripts/run_reading_components.sh')
ENV='L20_READING_COMPONENTS_DETACHED';READY='D159_READY_FD';ALLOWANCE=2*1024**3;RESERVE=4*1024**3


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
        synthetic_models_fabricated_not_fitted=True,mean_target_only=True,
        workers=1,maximum_cpus=6,numerical_threads=1,allowance=ALLOWANCE,reserve=RESERVE,
        benchmark_forecast='24*qualified_small_audit_seconds+120',
        main_forecast='2*checked_full_audit_seconds+2*hash_seconds+120',
        automatic_polling=False,automatic_retry=False)

def source_files():
    run,out=previous.paths();c=io.read_json(run/'COMPLETE.json');m=io.read_json(run/'MANIFEST.json')
    assert sha256_file(run/'COMPLETE.json')==COMPLETE and c['status']=='COMPLETE'
    assert not (run/'FAILED.json').exists() and io.read_json(run/'STATUS.json')==c
    assert sha256_file(run/'MANIFEST.json')==c['manifest_sha256'] and m['environment']==environment_manifest()
    assert len(m['input_sha256'])==2181 and len(c['output_sha256'])==10
    expected={**m['input_sha256'],**c['output_sha256']}
    assert expected==io.hashes([Path(p) for p in expected])
    assert sha256_file(out/'output_hashes.sha256')==c['hash_index_sha256']
    assert (out/'output_hashes.sha256').read_text()==io.hash_text(c['output_sha256'])
    assert sha256_file(AUDIT)==AUDIT_HASH;proof=io.read_json(AUDIT)
    assert proof['passes'] and proof['complete_sha256']==COMPLETE and proof['source_primary_unchanged']
    assert proof['input_hashes']==2181 and proof['outputs']==10 and proof['new_dynamics']==0
    assert proof['new_fits']==8640 and proof['new_predictions']==138240 and proof['observer_comparison_records']==5445
    assert proof['training_effect_records']==672
    files={Path(p) for p in expected};files.update((run/'COMPLETE.json',run/'STATUS.json',run/'MANIFEST.json',out/'output_hashes.sha256',AUDIT))
    files.update(WS/p for p in SCIENCE);return sorted(files)

def qualification(path):
    io.require_beneath(path,ROOT/'logs');tree=ET.parse(path).getroot();cases=tree.findall('.//testcase')
    assert len(cases)>=50 and not any(tree.findall('.//'+n) for n in ('error','failure','skipped'))
    assert len({(c.get('classname'),c.get('name')) for c in cases})==len(cases)
    ours=[c for c in cases if c.get('classname','').endswith('test_reading_components')]
    required={'test_small_audit','test_mean_difference_coordinates','test_clipping','test_structural_zeros',
        'test_feature_boundary','test_outcomes_not_parts','test_repeat_permutation','test_group_coordinates',
        'test_mean_loss_not_ensemble','test_gap_symmetry','test_invalid_model','test_parts_corruption',
        'test_fit_corruption','test_case_corruption','test_summary_corruption','test_source_bridge',
        'test_roundtrip','test_constants','test_complete_specs','test_no_fitting_or_dynamics',
        'test_source_closure','test_resource_guard','test_detach_guard','test_startup_handshake',
        'test_no_automatic_successor','test_synthetic_permutation'}
    assert required<={c.get('name').split('[',1)[0] for c in ours}
    seconds=max(float(c.get('time')) for c in ours if c.get('name')=='test_small_audit')
    return dict(report=str(path),tests=len(cases),failures=0,skipped=0,qualified_small_audit_seconds=seconds,
        benchmark_forecast=24*seconds+120)

def freeze(report):
    resources()
    if any(p.exists() for p in (freeze_path(),timing_path(),benchmark_dir(),*paths(),logfile('execute'),logfile('benchmark'))):
        raise FileExistsError('single-use stage already exists')
    proof=qualification(report);tick=time.monotonic();inputs=io.hashes(source_files()+[report]);seconds=time.monotonic()-tick
    value=dict(frozen_utc=utc_now(),contract=contract(),test_proof=proof,input_sha256=inputs,
        environment=environment_manifest(),source_audit=io.read_json(AUDIT),source_hash_seconds=seconds,actual_components_extracted=False)
    io.write_json(freeze_path(),value,ROOT)
    print(json.dumps(dict(status='FROZEN',inputs=len(inputs),test_proof=proof,source_hash_seconds=seconds)),flush=True)


def frozen():
    f=io.read_json(freeze_path());assert f['contract']==contract() and f['environment']==environment_manifest()
    report=Path(f['test_proof']['report']);assert f['test_proof']==qualification(report)
    assert f['input_sha256']==io.hashes(source_files()+[report]) and f['actual_components_extracted'] is False
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
    write_accounting(directory,data,b,br,p,raw,bfits,rfits)

def write_accounting(directory,data,b,br,p,raw,bfits,rfits):
    parts=models.extract(data,b,br,p,raw,bfits,rfits)
    arrays=models.accounting(parts,b,p,data)
    io.write_npz(directory/'parts.npz',parts,ROOT);io.write_npz(directory/'accounting.npz',arrays,ROOT)
    io.write_json(directory/'summary.json',models.summarize(parts,arrays,b,br,p,raw,data),ROOT)

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
            scientific_evidence=False,synthetic_models_fabricated=9216,new_fits=0,new_dynamics=0,actual_components_extracted=False)
        io.write_json(timing_path(),value,ROOT);print(json.dumps(value,indent=2),flush=True)
    except Exception as error:io.failure(directory,error,ROOT);raise


def verify_benchmark():
    d=benchmark_dir();data=io.load_npz(d/'synthetic.npz')
    for k,v in models.prior.fixture().items():np.testing.assert_array_equal(data[k],v)
    b=io.load_npz(d/'baseline.npz');br=io.load_npz(d/'baseline_raw.npz')
    p=io.load_npz(d/'predictions.npz');raw=io.load_npz(d/'raw_predictions.npz')
    bf=io.read_json(d/'baseline_fits.json');rf=io.read_json(d/'fits.json')
    return verify_accounting(d,data,b,br,p,raw,bf,rf,io.read_json(d/'source_summary.json'))

def verify_accounting(directory,data,b,br,p,raw,bfits,rfits,source):
    parts=io.load_npz(directory/'parts.npz');arrays=io.load_npz(directory/'accounting.npz')
    s=io.read_json(directory/'summary.json')
    return dict(replay=checker.check_parts(parts,data,b,br,p,raw,bfits,rfits),
        accounting=checker.check_accounting(arrays,parts,b,p,data),
        summary=checker.check_summary(s,parts,arrays,b,br,p,raw,data),
        source_bridge=checker.source_bridge(s,source),new_fits=0,new_predictions=0,new_dynamics=0,
        prospective_evidence=False,causal_attribution=False)

def timing_checked(audit=False):
    t=io.read_json(timing_path());assert t['status']=='COMPLETE' and t['scientific_evidence'] is t['actual_components_extracted'] is False
    assert t['freeze_sha256']==sha256_file(freeze_path()) and t['new_dynamics']==0 and t['new_fits']==0 and t['synthetic_models_fabricated']==9216
    assert {p.name for p in benchmark_dir().iterdir()}=={'synthetic.npz','baseline.npz','baseline_raw.npz','predictions.npz','raw_predictions.npz',
        'baseline_fits.json','fits.json','source_summary.json','parts.npz','accounting.npz','summary.json'}
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
    out=previous.paths()[1];data=io.load_npz(out/'dataset.npz')
    assert set(data)=={'start','endpoint','targeted','labels','futures','block_ids'}
    np.testing.assert_array_equal(data['block_ids'],np.arange(90000,90016,dtype=np.int64));models.prior.validate(data)
    b=io.load_npz(out/'baseline.npz');br=io.load_npz(out/'baseline_raw.npz')
    p=io.load_npz(out/'predictions.npz');raw=io.load_npz(out/'raw_predictions.npz')
    bfits=io.read_json(previous.previous.paths()[1]/'fits.json')
    rfits=io.read_json(out/'fits.json');source=io.read_json(out/'summary.json')
    return data,b,br,p,raw,bfits,rfits,source

def source_identity():
    # Actual inputs are read directly from their hash-pinned predecessor paths.
    run,out=previous.paths()
    names=('dataset.npz','baseline.npz','baseline_raw.npz','predictions.npz','raw_predictions.npz','fits.json','summary.json')
    wanted=io.read_json(run/'COMPLETE.json')['output_sha256']
    files=[out/name for name in names];files.append(previous.previous.paths()[1]/'fits.json')
    expected={**io.read_json(run/'MANIFEST.json')['input_sha256'],**wanted}
    assert io.hashes(files)=={str(p):expected[str(p)] for p in files}
    return dict(passes=True,direct_source_files=8,blocks=16,cases=256,source_primary_unchanged=True)

def output_names():
    return ['parts.npz','accounting.npz','summary.json','verification.json','input_hashes.sha256']

def verify_saved():
    data,b,br,p,raw,bfits,rfits,source=source_data()
    return dict(source=source_identity(),
        **verify_accounting(paths()[1],data,b,br,p,raw,bfits,rfits,source))

def saved_audit():
    resources(False);run,out=paths();m=io.read_json(run/'MANIFEST.json')
    assert m['input_sha256']==inputs() and m['contract']==contract() and m['environment']==environment_manifest()
    assert m['actual_components_extracted'] is False and m['prepared_utc']>=io.read_json(freeze_path())['frozen_utc']
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
        observers=12,deletions=16,observer_orientations=165,observer_comparison_records=5445,training_effect_records=672,
        saved_models_replayed=9216,saved_forecasts_replayed=147456,new_fits=0,new_predictions=0,
        part_arrays=24,case_arrays=248,new_dynamics=0,prospective_evidence=False,source_primary_unchanged=True)


def execute():
    resources();pin=inputs();t=timing_checked(True);detached_guard(t['must_detach'],'execute');run,out=paths()
    if run.exists() or out.exists():raise FileExistsError('single-use comparison paths already exist')
    run.mkdir();out.mkdir();began=time.monotonic()
    try:
        manifest=dict(prepared_utc=utc_now(),contract=contract(),input_sha256=pin,timing=t,environment=environment_manifest(),
            affinity=sorted(os.sched_getaffinity(0)),actual_components_extracted=False)
        io.write_json(run/'MANIFEST.json',manifest,ROOT)
        with (out/'input_hashes.sha256').open('x') as stream:stream.write(io.hash_text(pin))
        (run/'EXECUTION.lock').mkdir();ready('execute')
        atomic_json(run/'STATUS.json',dict(status='ACCOUNTING_SAVED_FORECASTS',updated_utc=utc_now()),ROOT)
        data,b,br,p,raw,bfits,rfits,source=source_data()
        write_accounting(out,data,b,br,p,raw,bfits,rfits)
        atomic_json(run/'STATUS.json',dict(status='INDEPENDENT_SAVED_CHECK',updated_utc=utc_now()),ROOT)
        proof=verify_saved();io.write_json(out/'verification.json',proof,ROOT);assert pin==inputs()
        hashes=io.hashes([out/n for n in output_names()])
        with (out/'output_hashes.sha256').open('x') as stream:stream.write(io.hash_text(hashes))
        size=sum(p.stat().st_size for p in out.iterdir());assert size<=ALLOWANCE
        value=dict(status='COMPLETE',completed_utc=utc_now(),elapsed_seconds=time.monotonic()-began,output_bytes=size,
            manifest_sha256=sha256_file(run/'MANIFEST.json'),output_sha256=hashes,hash_index_sha256=sha256_file(out/'output_hashes.sha256'),
            verification=proof,new_fits=0,new_predictions=0,new_dynamics=0,automatic_polling=False,automatic_retry=False,automatic_successor=False)
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
            child=subprocess.Popen([sys.executable,'-m','l20_extension1.reading_parts_run','--'+('seal-audit' if stage=='audit' else stage)],
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
