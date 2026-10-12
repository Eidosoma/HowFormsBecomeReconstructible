"""Freeze a fully checked, reviewable run before the separate host launch."""
import shutil
import sys
from common import ROOT,read,sha,stamp,validate,write


def main():
    cfg=read(ROOT/'config.json');validate(cfg)
    benchmark=read(ROOT/'benchmark/COMPLETE.json')
    assert benchmark['status']=='COMPLETE' and benchmark['byte_equal'] and benchmark['within_ceiling']
    prepared=read(ROOT/'prepared/COMPLETE.json');validation=read(ROOT/'VALIDATION.json')
    assert prepared['records']==64 and prepared['new_native_outcomes']==0
    assert validation['status']=='PASS' and validation['tests_passed']>=8
    assert prepared['protocol_sha256']==sha(ROOT/'PROTOCOL.md')
    for receipt in (prepared,benchmark,validation):
        assert receipt['config_sha256']==sha(ROOT/'config.json')
        for name,digest in receipt['code_sha256'].items():assert sha(ROOT/name)==digest,name
    for name,digest in prepared['outputs_sha256'].items():assert sha(ROOT/'prepared'/name)==digest,name
    for path,digest in prepared['sources_sha256'].items():assert sha(path)==digest,path
    assert shutil.disk_usage(ROOT).free>1024**3
    folder=ROOT/'runs/pilot_v1';folder.mkdir(parents=True,exist_ok=False)
    files={}
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file():continue
        relative=path.relative_to(ROOT)
        if any(p in ('runs','__pycache__','.pytest_cache') for p in relative.parts):continue
        dest=folder/'inputs'/relative;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,dest);files[str(relative)]=sha(path)
    manifest=dict(status='FROZEN_READY_TO_LAUNCH',at_utc=stamp(),config=cfg,files_sha256=files,
        prepared_complete_sha256=sha(ROOT/'prepared/COMPLETE.json'),forecast_cpu_seconds=benchmark['forecast_cpu_seconds'],
        executable=sys.executable,workers=1,numerical_threads=1,automatic_polling=False,automatic_successor=False,
        scientific_status='DEVELOPMENT_BACKUP_TASK_SWAP_ON_EXPOSED_STATES',executes_frozen_copy=True)
    write(folder/'manifest.json',manifest)
    write(folder/'START.json',dict(status='READY',at_utc=stamp(),manifest_sha256=sha(folder/'manifest.json')))
    print(f'Frozen {len(files)} files at {folder}; forecast {benchmark["forecast_cpu_seconds"]/60:.2f} minutes.',flush=True)


if __name__=='__main__':main()
