"""Bind executable and sources before any scientific continuation is generated."""
import shutil
import sys
from common import ROOT,read,write,sha,stamp,validate


def main():
    cfg=read(ROOT/'config.json');validate(cfg)
    benchmark=read(ROOT/'benchmark/COMPLETE.json');validation=read(ROOT/'VALIDATION.json')
    source=read(ROOT/'sources/COMPLETE.json')
    assert benchmark['status']=='COMPLETE' and benchmark['byte_equal'] and benchmark['within_ceiling']
    assert benchmark['new_continuation_outcomes']==source['new_continuation_outcomes']==0
    assert validation['status']=='PASS' and validation['tests_passed']>=4
    for receipt in (benchmark,validation,source):
        assert receipt['config_sha256']==sha(ROOT/'config.json')
        for name,digest in receipt['code_sha256'].items():assert sha(ROOT/name)==digest,name
    for field,name in [('protocol_sha256','PROTOCOL.md'),('prediction_sha256','PREDICTION.json'),
                       ('sources_complete_sha256','sources/COMPLETE.json'),('benchmark_complete_sha256','benchmark/COMPLETE.json')]:
        assert validation[field]==sha(ROOT/name)
    for path,digest in source['sources_sha256'].items():assert sha(path)==digest,path
    for name,digest in source['outputs_sha256'].items():assert sha(ROOT/'sources'/name)==digest,name
    assert read(ROOT/'CPU_LAUNCH_PREFLIGHT.json')['within_limit']
    assert shutil.disk_usage(ROOT).free>2*1024**3
    folder=ROOT/'runs/pilot_v1';folder.mkdir(parents=True,exist_ok=False);files={}
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file():continue
        relative=path.relative_to(ROOT)
        if any(p in ('runs','__pycache__','.pytest_cache') for p in relative.parts):continue
        target=folder/'inputs'/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target);files[str(relative)]=sha(path)
    manifest=dict(status='FROZEN_READY_TO_LAUNCH',at_utc=stamp(),config=cfg,files_sha256=files,
        forecast_cpu_seconds=benchmark['forecast_cpu_seconds'],executable=sys.executable,
        workers=1,numerical_threads=1,automatic_polling=False,automatic_successor=False,executes_frozen_copy=True,
        new_scientific_continuation_outcomes_before_freeze=0,sources_complete_sha256=sha(ROOT/'sources/COMPLETE.json'))
    write(folder/'manifest.json',manifest)
    write(folder/'START.json',dict(status='READY',at_utc=stamp(),manifest_sha256=sha(folder/'manifest.json')))
    print(f'Frozen {len(files)} inputs; forecast {benchmark["forecast_cpu_seconds"]/60:.2f} CPU minutes.',flush=True)


if __name__=='__main__':main()
