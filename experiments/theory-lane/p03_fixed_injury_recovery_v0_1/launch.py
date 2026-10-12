"""Freeze, spawn once and preserve the session with one blocking OS wait."""
import os
import shutil
import subprocess
import sys

from common import ROOT,read,sha,stamp,validate,write


def main():
    cfg=read(ROOT/'config.json');validate(cfg)
    assert os.environ.get('PYTHONDONTWRITEBYTECODE')=='1'
    assert all(os.environ.get(k)=='1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'))
    benchmark=read(ROOT/'benchmark/COMPLETE.json')
    assert benchmark['status']=='COMPLETE' and benchmark['byte_equal'] and benchmark['within_ceiling']
    assert benchmark['config_sha256']==sha(ROOT/'config.json')
    for name,digest in benchmark['code_sha256'].items():
        assert sha(ROOT/name)==digest
    prepared=read(ROOT/'prepared/COMPLETE.json')
    assert prepared['records']==64 and prepared['config_sha256']==sha(ROOT/'config.json')
    assert prepared['protocol_sha256']==sha(ROOT/'PROTOCOL.md')
    for name,digest in prepared['code_sha256'].items():
        assert sha(ROOT/name)==digest
    for name,digest in prepared['outputs_sha256'].items():
        assert sha(ROOT/'prepared'/name)==digest
    for path,digest in prepared['sources_sha256'].items():
        assert sha(path)==digest
    validation=read(ROOT/'VALIDATION.json')
    assert validation['status']=='PASS' and validation['tests_passed']>=8
    for name,digest in validation['files_sha256'].items():
        assert sha(ROOT/name)==digest
    assert shutil.disk_usage(ROOT).free>1024**3
    folder=ROOT/'runs/pilot_v1';folder.mkdir(parents=True,exist_ok=False)
    originals=[p for p in sorted(ROOT.rglob('*')) if p.is_file() and 'runs' not in p.relative_to(ROOT).parts
               and '__pycache__' not in p.relative_to(ROOT).parts]
    code={}
    for path in originals:
        relative=path.relative_to(ROOT)
        destination=folder/'inputs'/relative;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,destination);code[str(relative)]=sha(path)
    manifest=dict(status='READY_TO_LAUNCH',created_at_utc=stamp(),config=cfg,code_sha256=code,
        prepared_complete_sha256=sha(ROOT/'prepared/COMPLETE.json'),protocol_sha256=sha(ROOT/'PROTOCOL.md'),
        forecast_cpu_seconds=benchmark['forecast_cpu_seconds'],workers=1,numerical_threads=1,
        automatic_polling=False,automatic_successor=False,executable=sys.executable,
        completion_pipeline='Known replay, fresh reads, analysis, independent reader/table audit, report and figures.')
    write(folder/'manifest.json',manifest)
    write(folder/'START.json',dict(status='RUNNING',at_utc=stamp(),manifest_sha256=sha(folder/'manifest.json')))
    with (folder/'console.log').open('xb') as log:
        child=subprocess.Popen([sys.executable,'-B',str(ROOT/'run.py'),'--run',str(folder)],cwd=ROOT,
            env=os.environ.copy(),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
            start_new_session=True,close_fds=True)
    receipt=dict(status='LAUNCHED',launched_at_utc=stamp(),pid=child.pid,run=str(folder),
        forecast_minutes=benchmark['forecast_cpu_seconds']/60,detached=True,polling=False,
        frozen_files=len(code),cases=64,replicates=16,variants=cfg['variants'],budgets=cfg['budgets'],
        completion_marker=str(folder/'COMPLETE.json'),completion_report=str(folder/'REPORT.md'),
        supervisor='One blocking child.wait; no repeated status reads or automatic polling.')
    write(folder/'LAUNCH.json',receipt)
    with (folder/'PID').open('x') as f:f.write(str(child.pid)+'\n')
    print(__import__('json').dumps(receipt,indent=2),flush=True)
    raise SystemExit(child.wait())


if __name__=='__main__':
    main()
