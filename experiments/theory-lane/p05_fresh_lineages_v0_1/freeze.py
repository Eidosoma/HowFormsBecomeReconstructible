"""Bind the complete executable before any new scientific lineage is generated."""
import shutil
import sys
from common import ROOT,read,write,sha,stamp,validate


def main():
    cfg=read(ROOT/'config.json');validate(cfg)
    benchmark=read(ROOT/'benchmark/COMPLETE.json');validation=read(ROOT/'VALIDATION.json');known=read(ROOT/'known/COMPLETE.json')
    assert benchmark['status']=='COMPLETE' and benchmark['byte_equal'] and benchmark['within_ceiling']
    assert benchmark['new_lineages_generated']==known['new_lineages_generated']==0
    assert validation['status']=='PASS' and validation['tests_passed']>=4
    for receipt in (benchmark,validation,known):
        assert receipt['config_sha256']==sha(ROOT/'config.json')
        for name,digest in receipt['code_sha256'].items():assert sha(ROOT/name)==digest,name
    for path,digest in known['sources_sha256'].items():assert sha(path)==digest,path
    for name,digest in known['outputs_sha256'].items():assert sha(ROOT/'known'/name)==digest,name
    assert shutil.disk_usage(ROOT).free>1024**3
    folder=ROOT/'runs/pilot_v1';folder.mkdir(parents=True,exist_ok=False);files={}
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file():continue
        relative=path.relative_to(ROOT)
        if any(p in ('runs','__pycache__','.pytest_cache') for p in relative.parts):continue
        target=folder/'inputs'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target);files[str(relative)]=sha(path)
    manifest=dict(status='FROZEN_READY_TO_LAUNCH',at_utc=stamp(),config=cfg,files_sha256=files,forecast_cpu_seconds=benchmark['forecast_cpu_seconds'],
        executable=sys.executable,workers=1,numerical_threads=1,automatic_polling=False,automatic_successor=False,executes_frozen_copy=True,
        new_scientific_lineages_generated_before_freeze=0,known_complete_sha256=sha(ROOT/'known/COMPLETE.json'))
    write(folder/'manifest.json',manifest);write(folder/'START.json',dict(status='READY',at_utc=stamp(),manifest_sha256=sha(folder/'manifest.json')))
    print(f'Frozen {len(files)} inputs; forecast {benchmark["forecast_cpu_seconds"]/60:.2f} minutes.',flush=True)


if __name__=='__main__':main()
