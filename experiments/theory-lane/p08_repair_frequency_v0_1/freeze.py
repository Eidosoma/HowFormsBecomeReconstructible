"""Freeze the entire queued qualification and fixed development experiment."""
import shutil
import sys
from common import ROOT,read,write,sha,stamp,validate


def main():
    cfg=read(ROOT/'config.json');validate(cfg)
    source=read(ROOT/'sources/COMPLETE.json')
    assert source['config_sha256']==sha(ROOT/'config.json') and source['new_dynamics_generated']==0
    for path,digest in source['sources_sha256'].items():assert sha(path)==digest,path
    for name,digest in source['outputs_sha256'].items():assert sha(ROOT/'sources'/name)==digest,name
    for p in ROOT.glob('*.py'):compile(p.read_text(),str(p),'exec')
    assert shutil.disk_usage(ROOT).free>2*1024**3
    folder=ROOT/'runs/pilot_v1';folder.mkdir(parents=True,exist_ok=False);files={}
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file():continue
        relative=path.relative_to(ROOT)
        if any(p in ('runs','__pycache__','.pytest_cache') for p in relative.parts):continue
        target=folder/'inputs'/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target);files[str(relative)]=sha(path)
    estimate=read(ROOT/'PROVISIONAL_FORECAST.json')
    manifest=dict(status='FROZEN_READY_FOR_CPU_ADMISSION_AND_QUALIFICATION',at_utc=stamp(),config=cfg,files_sha256=files,
        forecast_cpu_seconds=estimate['total_provisional_cpu_seconds'],executable=sys.executable,
        forecast_status='Provisional from archived four-arm benchmark; exact three-arm measurement required before new schedule outcomes.',
        workers=1,numerical_threads=1,automatic_polling=False,automatic_successor=False,executes_frozen_copy=True,
        qualification_tests_required=7,qualification_first=True,scientific_generation_requires_qualified_receipt=True,
        new_causal_audit_outcomes_before_freeze=0,new_frequency_outcomes_before_freeze=0,
        source_complete_sha256=cfg['prior_complete_sha256'],prediction_sha256=sha(ROOT/'PREDICTION.json'),
        capacity_admission='CPU-only checks every 60 seconds until one slot is available; then start one worker and exit.')
    write(folder/'manifest.json',manifest)
    write(folder/'START.json',dict(status='READY_FOR_ADMISSION',at_utc=stamp(),manifest_sha256=sha(folder/'manifest.json')))
    print(f'Frozen {len(files)} inputs. Qualification pending; provisional total forecast {manifest["forecast_cpu_seconds"]/60:.2f} CPU minutes.',flush=True)


if __name__=='__main__':main()
