"""Freeze the qualified prediction before any reserved-namespace outcome."""
import shutil
import sys
from common import ROOT,read,write,sha,stamp,validate


def main():
    cfg=read(ROOT/'config.json');validate(cfg);q=read(ROOT/'qualification_v2/COMPLETE.json')
    assert q['status']=='PASS' and q['new_test_outcomes']==0
    assert q['config_sha256']==sha(ROOT/'config.json') and q['sources_complete_sha256']==sha(ROOT/'sources/COMPLETE.json')
    for name,digest in q['code_sha256'].items():assert sha(ROOT/name)==digest,name
    source=read(ROOT/'sources/COMPLETE.json');assert source['config_sha256']==sha(ROOT/'config.json')
    for path,digest in source['sources_sha256'].items():assert sha(path)==digest,path
    for name,digest in source['outputs_sha256'].items():assert sha(ROOT/'sources'/name)==digest,name
    assert q['forecast_cpu_seconds']<=cfg['forecast_ceiling_cpu_seconds'] and shutil.disk_usage(ROOT).free>6*1024**3
    folder=ROOT/'runs/prospective_v1';folder.mkdir(parents=True,exist_ok=False);files={}
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file():continue
        relative=path.relative_to(ROOT)
        if any(p in ('runs','__pycache__','.pytest_cache','.cache','test_work','tmp') for p in relative.parts):continue
        target=folder/'inputs'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target);files[str(relative)]=sha(path)
    manifest=dict(status='QUALIFIED_AND_FROZEN_BEFORE_TEST_OUTCOMES',at_utc=stamp(),config=cfg,files_sha256=files,
        forecast_cpu_seconds=q['forecast_cpu_seconds'],executable=sys.executable,workers=1,numerical_threads=1,
        automatic_polling=False,automatic_successor=False,executes_frozen_copy=True,new_test_outcomes=0,
        prediction_sha256=sha(ROOT/'PREDICTION.json'),qualification_sha256=sha(ROOT/'qualification_v2/COMPLETE.json'),
        claim_status='Locally timestamped prospective seed holdout; exposed model family and development-selected schedule. Not external registration.')
    write(folder/'manifest.json',manifest);write(folder/'START.json',dict(status='READY_FOR_ADMISSION',at_utc=stamp(),manifest_sha256=sha(folder/'manifest.json')))
    print(f"Frozen {len(files)} inputs and all 132 blocks before test outcomes. Forecast {q['forecast_cpu_seconds']/3600:.2f} CPU hours.",flush=True)


if __name__=='__main__':main()
