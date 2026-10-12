"""D177 write-once feasibility gate; no population-pilot or predictor route."""
import argparse
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET
import numpy as np
from laws_confirmation.io import sha256_file, utc_now
from . import recipient_identity as model, recipient_identity_check as check

ROOT, WS = model.ROOT, model.WS
RUN = 'l20_extension1_recipient_identity_v1_attempt1'
CAP, RESERVE = 128*1024**2, 4*1024**3
SCIENCE = ('record-recipient/FEASIBILITY_PROTOCOL_V1.md',
    'src/l20_extension1/recipient_identity.py', 'src/l20_extension1/recipient_identity_check.py',
    'src/l20_extension1/recipient_identity_run.py', 'tests/test_recipient_identity.py')
ENV, READY = 'D177_DETACHED_STAGE', 'D177_READY_FD'
files = model.files
EXECUTION_OWNED = False


def freeze_path(): return ROOT/'tmp'/(RUN+'_freeze.json')
def output_dir(): return ROOT/'outputs'/RUN
def run_dir(): return ROOT/'runs'/RUN
def audit_path(): return ROOT/'logs'/(RUN+'_saved_audit_v1.json')


def external(path):
    path = Path(path)
    assert ROOT.resolve() in path.resolve().parents
    assert not path.is_symlink() and not any(p.is_symlink() for p in path.parents)
    return path


def write_json(path, value):
    external(path).parent.mkdir(parents=True, exist_ok=True)
    files.write_json(path, value, ROOT)


def write_npz(path, raw):
    external(path).parent.mkdir(parents=True, exist_ok=True)
    files.write_npz(path, raw, ROOT)


def inventory_files():
    paths = []
    for area in ('tmp','logs','runs','outputs'):
        for root in (ROOT/area).glob(RUN+'*'):
            assert not root.is_symlink()
            for path in ([root] if root.is_file() else root.rglob('*')):
                if path.is_symlink():
                    target = path.resolve(strict=True)
                    assert root.name.startswith(RUN+'_qualification_v')
                    assert path.name.endswith('current') and target.parent == path.parent.resolve()
                    stem = path.name[:-7]
                    assert target.name.startswith(stem) and target.name[len(stem):].isdigit() and target.is_dir()
                elif path.is_file():
                    paths.append(path)
    return sorted(set(paths))


def resources():
    assert not sys.flags.optimize and os.environ.get('PYTHONDONTWRITEBYTECODE') == '1'
    assert 0 < len(os.sched_getaffinity(0)) <= 6 and set(os.sched_getaffinity(0)) <= set(range(6))
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
        assert os.environ.get(key) == '1'
    for key in ('TMPDIR','XDG_CACHE_HOME'):
        p = Path(os.environ.get(key,'/')).resolve()
        assert ROOT in p.parents and p.is_dir()
    assert shutil.disk_usage(ROOT).free >= CAP+RESERVE
    paths = inventory_files(); size = sum(p.stat().st_size for p in paths)
    assert size < CAP
    return dict(bytes=size, files=len(paths), cap_bytes=CAP, maximum_cpus=6, numerical_threads=1)


def source_inputs():
    expected = {}
    def bind(path, digest):
        path = Path(path)
        assert path.is_file() and not path.is_symlink() and sha256_file(path) == digest, str(path)
        assert str(path) not in expected or expected[str(path)] == digest
        expected[str(path)] = digest
    complete = ROOT/'runs'/model.SOURCE/'COMPLETE.json'
    manifest = complete.parent/'MANIFEST.json'
    bind(complete, model.SOURCE_SHA); bind(manifest, model.MANIFEST_SHA)
    done, mf = files.read_json(complete), files.read_json(manifest)
    assert done['status'] == 'COMPLETE' and done['manifest_sha256'] == model.MANIFEST_SHA
    history = dict(mf['input_sha256'])
    benchmark = ROOT/'tmp'/(model.SOURCE+'_benchmark.json')
    bind(benchmark, history[str(benchmark)])
    bm = files.read_json(benchmark)
    for p in model.paths(model.DISPOSABLE):
        bind(p, bm['artifact_sha256'][str(p)])
    for index in range(90000,90016):
        p = model.paths(index)[1]
        bind(p,done['output_sha256'][str(p)])
    # Only the packets/guide of the disposable are read, not main outcome arrays.
    new = {str((WS/p).resolve()) for p in SCIENCE}
    model.old.context(model.DISPOSABLE)
    for module in tuple(sys.modules.values()):
        name = getattr(module, '__file__', None)
        if not name: continue
        p = Path(name).resolve()
        if model.old.ORIGIN in p.parents and p.suffix == '.py' and str(p) not in new:
            assert str(p) in history, 'unbound inherited repository code: '+str(p)
            bind(p,history[str(p)])
    return expected


def verify(mapping):
    for path,digest in mapping.items():
        p=Path(path)
        assert p.is_file() and not p.is_symlink() and sha256_file(p)==digest, path


def qualification(xml):
    external(xml)
    assert xml.parent == ROOT/'logs' and xml.name.startswith(RUN+'_qualification_v') and xml.suffix == '.xml'
    tree = ET.parse(xml).getroot(); cases=tree.findall('.//testcase')
    assert cases and not any(tree.findall('.//'+k) for k in ('failure','error','skipped'))
    assert len(cases) == len({(t.get('classname'),t.get('name')) for t in cases})
    names={t.get('name').split('[',1)[0] for t in cases}
    required={'test_full_disposable_path','test_independent_replay','test_saved_no_dynamics',
        'test_inventory','test_activity_contract','test_corruption','test_metadata_corruption',
        'test_noise_isolation','test_recipient_access','test_report','test_time_gate','test_source_inputs','test_external_write_once'}
    assert required <= names
    timing = files.read_json(ROOT/'tmp'/xml.stem/'path_fixture'/'timing.json')
    assert timing['seconds'] > 0 and timing['full_independent_replay'] is True
    return dict(path=str(xml), tests=len(cases), full_path_seconds=timing['seconds'])


def freeze(xml):
    resources()
    for p in (freeze_path(),run_dir(),output_dir(),audit_path()):
        assert not p.exists(), str(p)
    q=qualification(xml); start=time.monotonic(); source=source_inputs(); elapsed=time.monotonic()-start
    paths=[WS/p for p in SCIENCE]+[xml]
    fixture=ROOT/'tmp'/xml.stem
    paths += [p for p in inventory_files() if fixture in p.parents]
    value=dict(schema='d177_freeze_v1',frozen_utc=utc_now(),inputs=source,
        science_qualification=files.hashes(paths),qualification=q,source_hash_seconds=elapsed,
        conservative_seconds=24*q['full_path_seconds']+2*elapsed+60,
        python=sys.version,numpy=np.__version__,hosts=list(model.HOSTS),cases=[list(c) for c in model.CASES],
        source_index=514240,source_life=0,main_population_pilot_allowed=False,new_predictors=0,
        activity_contract=model.activity_contract(), host_inventory=model.inventory(),
        automatic_successor=False)
    write_json(freeze_path(),value)
    return {k:v for k,v in value.items() if k not in ('inputs','science_qualification')}


def frozen():
    f=files.read_json(freeze_path())
    verify(f['inputs']);verify(f['science_qualification'])
    assert f['python']==sys.version and f['numpy']==np.__version__
    assert f['hosts']==list(model.HOSTS) and f['cases']==[list(c) for c in model.CASES]
    assert f['main_population_pilot_allowed'] is False
    return f


def time_gate(seconds,detached=False):
    assert np.isfinite(seconds) and seconds>0
    if seconds>600 and not detached:
        raise RuntimeError('Use detached stage with durable log; no polling')
    return bool(seconds>600)


def cell_name(host,role,writer):
    assert host in model.HOSTS and (role,writer) in model.CASES
    return f'path_{host}_{role}_{writer}'


def saved_panel(directory, source, guide, frozen_contract):
    rows={};proofs=[]
    for host in model.HOSTS:
        for role,writer in model.CASES:
            name=cell_name(host,role,writer)
            raw=files.load_npz(directory/(name+'.npz')); record=files.read_json(directory/(name+'.json'))
            meta=record['metadata'];prior=record['replay']
            assert (meta['recipient'],meta['role'],meta['writer'])==(host,role,writer)
            proof=check.check(raw,meta,source,guide,False)
            assert prior['full_physics_replayed'] and prior['passes']
            assert set(proof)==set(prior)
            for k,v in proof.items():
                if k.endswith('_max_abs'):
                    assert 0<=prior[k]<= (1e-12 if k in ('selector_max_abs','metric_max_abs') else 1e-10)
                elif k!='full_physics_replayed':
                    assert prior[k]==v
            rows[host,role,writer]=(raw,meta);proofs.append(prior)
    report=files.read_json(directory/'summary.json')
    check.prior.nested(report['inventory'],model.inventory())
    check.prior.nested(report['inventory'],frozen_contract['host_inventory'])
    check.prior.nested(report['activity'],frozen_contract['activity_contract'])
    report_proof=check.compare_report(report,rows)
    return dict(passes=True,paths=12,generation_paths=36,terminal_readers=12,
        full_dynamics_replayed_at_generation=True,new_dynamics=0,
        saved_statistics=report_proof,maximum_replay_discrepancy=max(p[k] for p in proofs for k in
            ('reader_max_abs','writer_max_abs','terminal_max_abs')),automatic_successor=False)


def acknowledge():
    fd=os.environ.get(READY)
    if fd:
        assert os.environ.get(ENV) and os.getsid(0)==os.getpid()
        os.write(int(fd),b'READY\n');os.close(int(fd))


def execute():
    global EXECUTION_OWNED
    resources();f=frozen()
    time_gate(f['conservative_seconds'],os.environ.get(ENV)=='execute')
    run_dir().mkdir(parents=True,exist_ok=False);EXECUTION_OWNED=True
    output_dir().mkdir(parents=True,exist_ok=False)
    manifest=dict(started_utc=utc_now(),freeze_sha256=sha256_file(freeze_path()),
        forecast_seconds=f['conservative_seconds'],main_population_pilot_started=False,automatic_successor=False)
    write_json(run_dir()/'MANIFEST.json',manifest);acknowledge()
    begin=time.monotonic();source,guide=model.load_source();rows={}
    inv=model.inventory();activity=model.activity_contract()
    for host in model.HOSTS:
        for role,writer in model.CASES:
            raw,meta=model.simulate(source[role].tobytes(),guide,host,role,writer)
            proof=check.check(raw,meta,source,guide,True)
            name=cell_name(host,role,writer)
            write_npz(output_dir()/(name+'.npz'),raw)
            write_json(output_dir()/(name+'.json'),dict(metadata=meta,replay=proof))
            rows[host,role,writer]=(raw,meta)
    summary=model.summary(rows,inv,activity)
    check.compare_report(summary,rows);write_json(output_dir()/'summary.json',summary)
    proof=saved_panel(output_dir(),source,guide,f)
    write_json(output_dir()/'verification.json',proof)
    verify(f['inputs']);verify(f['science_qualification'])
    output=files.hashes(sorted(output_dir().iterdir()))
    done=dict(status='COMPLETE',completed_utc=utc_now(),seconds=time.monotonic()-begin,
        freeze_sha256=sha256_file(freeze_path()),manifest_sha256=sha256_file(run_dir()/'MANIFEST.json'),
        output_sha256=output,verification=proof,resources=resources(),main_population_pilot_started=False,
        scientific_status='NATIVE_RECIPIENT_CONTRAST_ABSENT',automatic_successor=False)
    write_json(run_dir()/'COMPLETE.json',done)
    return {k:v for k,v in done.items() if k!='output_sha256'}


def audit():
    resources();f=frozen();time_gate(f['conservative_seconds'],os.environ.get(ENV)=='audit')
    assert not audit_path().exists();done=files.read_json(run_dir()/'COMPLETE.json')
    assert done['status']=='COMPLETE' and done['freeze_sha256']==sha256_file(freeze_path())
    assert sha256_file(run_dir()/'MANIFEST.json')==done['manifest_sha256']
    verify(done['output_sha256'])
    assert set(done['output_sha256'])=={str(p) for p in output_dir().iterdir()}
    acknowledge();start=time.monotonic();source,guide=model.load_source()
    def no_step(*args,**kwargs): raise AssertionError('fresh saved audit must not step dynamics')
    step=check.physics.step; check.physics.step=no_step
    try:
        proof=saved_panel(output_dir(),source,guide,f)
    finally:
        check.physics.step=step
    check.prior.nested(proof,done['verification'])
    result=dict(passes=True,completed_utc=utc_now(),seconds=time.monotonic()-start,
        complete_sha256=sha256_file(run_dir()/'COMPLETE.json'),freeze_sha256=sha256_file(freeze_path()),
        verification=proof,new_dynamics=0,resources=resources(),automatic_successor=False)
    write_json(audit_path(),result);return result


def launch(stage):
    assert stage in ('execute','audit')
    resources();f=frozen()
    if stage=='execute': assert not run_dir().exists() and not output_dir().exists()
    else: assert (run_dir()/'COMPLETE.json').exists() and not audit_path().exists()
    log=ROOT/'logs'/(RUN+'_'+stage+'.log');external(log)
    readfd,writefd=os.pipe()
    env=dict(os.environ,**{ENV:stage,READY:str(writefd)})
    with log.open('xb') as handle:
        child=subprocess.Popen([sys.executable,'-m','l20_extension1.recipient_identity_run','--'+stage],
            stdin=subprocess.DEVNULL,stdout=handle,stderr=subprocess.STDOUT,env=env,
            start_new_session=True,pass_fds=(writefd,))
    os.close(writefd)
    ready=select.select([readfd],[],[],min(55.,max(10.,2*f['source_hash_seconds']+10)))[0]
    message=os.read(readfd,64) if ready else b''
    os.close(readfd)
    result=dict(status='DETACHED_STARTED' if message==b'READY\n' else 'STARTUP_NOT_ACKNOWLEDGED',
        stage=stage,pid=child.pid,log=str(log),forecast_seconds=f['conservative_seconds'],
        automatic_polling=False,automatic_successor=False)
    write_json(ROOT/'logs'/(RUN+'_'+stage+'_launch.json'),result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    g=parser.add_mutually_exclusive_group(required=True)
    g.add_argument('--freeze',type=Path);g.add_argument('--execute',action='store_true')
    g.add_argument('--audit',action='store_true');g.add_argument('--launch',choices=('execute','audit'))
    args=parser.parse_args()
    try:
        result=freeze(args.freeze) if args.freeze else launch(args.launch) if args.launch else execute() if args.execute else audit()
        print(json.dumps(result,sort_keys=True),flush=True)
    except Exception as exc:
        if args.execute and EXECUTION_OWNED and not (run_dir()/'COMPLETE.json').exists() and not (run_dir()/'FAILED.json').exists():
            write_json(run_dir()/'FAILED.json',dict(failed_utc=utc_now(),error=str(exc),
                traceback=traceback.format_exc(),automatic_retry=False))
        raise


if __name__=='__main__': main()
