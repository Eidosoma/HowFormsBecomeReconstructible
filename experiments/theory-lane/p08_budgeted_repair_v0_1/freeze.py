"""Seal the policy, cohort, executable, provenance and analysis before fresh acquisition."""
import shutil
import sys
from common import ROOT,read,write,sha,stamp,validate


def main():
    cfg=read(ROOT/'config.json');validate(cfg)
    benchmark=read(ROOT/'benchmark/COMPLETE.json');validation=read(ROOT/'VALIDATION.json')
    assert benchmark['status']=='COMPLETE' and benchmark['byte_equal'] and benchmark['within_ceiling']
    assert benchmark['new_scientific_outcomes']==0
    assert validation['status']=='PASS' and validation['tests_passed']==9
    for receipt in (benchmark,validation):
        assert receipt['config_sha256']==sha(ROOT/'config.json')
        for name,digest in receipt['code_sha256'].items():assert sha(ROOT/name)==digest,name
    for name,digest in validation['document_sha256'].items():assert sha(ROOT/name)==digest,name
    for name,digest in read(ROOT/'DEVELOPMENT_FREEZE.json')['files_sha256'].items():assert sha(ROOT/name)==digest,name
    dev=read(ROOT/'development/COMPLETE.json')
    for name,digest in dev['outputs_sha256'].items():assert sha(ROOT/'development'/name)==digest,name
    for path,digest in dev['sources_sha256'].items():assert sha(path)==digest,path
    for source_name in ('COMPLETE.json','TEACHING_COMPLETE.json'):
        source=read(ROOT/'sources'/source_name)
        assert source['status']=='COMPLETE' and source['new_scientific_outcomes']==0
        assert source['config_sha256']==sha(ROOT/'config.json')
        for path,digest in source['sources_sha256'].items():assert sha(path)==digest,path
        for name,digest in source['outputs_sha256'].items():assert sha(ROOT/'sources'/name)==digest,name
        for name,digest in source.get('code_sha256',{}).items():assert sha(ROOT/name)==digest,name
    assert read(ROOT/'PREDICTION.json')['model_sha256']==sha(ROOT/'development/MODEL.json')
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
        capacity_admission='detached wait with CPU-only checks every 60 seconds until one slot is available',
        fresh_cohort_outcomes_before_freeze=0,development_complete_sha256=sha(ROOT/'development/COMPLETE.json'),
        model_sha256=sha(ROOT/'development/MODEL.json'),prediction_sha256=sha(ROOT/'PREDICTION.json'))
    write(folder/'manifest.json',manifest)
    write(folder/'START.json',dict(status='READY',at_utc=stamp(),manifest_sha256=sha(folder/'manifest.json')))
    print(f'Frozen {len(files)} inputs; forecast {benchmark["forecast_cpu_seconds"]/60:.2f} CPU minutes.',flush=True)


if __name__=='__main__':main()
