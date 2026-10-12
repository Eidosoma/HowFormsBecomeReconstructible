"""Preserve interrupted evidence and stage a reviewable, unchanged resumption."""
from pathlib import Path
import shutil
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import ROOT,arrays,read,sha,stamp,validate,write


def main():
    old=ROOT/'runs/pilot_v1'
    original=read(old/'manifest.json')
    cfg=original['config'];validate(cfg)
    interrupted=read(old/'INTERRUPTED.json')
    assert interrupted['status']=='INTERRUPTED' and interrupted['completed_blocks']==[34000]
    for name,digest in original['code_sha256'].items():
        assert sha(ROOT/name)==digest,name
        assert sha(old/'inputs'/name)==digest,name
    folder=ROOT/'runs/pilot_v1_resume1';folder.mkdir(exist_ok=False)
    shutil.copytree(old/'inputs',folder/'inputs')
    code=dict(original['code_sha256'])
    for name in ('README.md','runner.py','prepare_resume.py','launch_persistent.py'):
        relative='recovery_v0_1/'+name
        dest=folder/'inputs'/relative;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/relative,dest);code[relative]=sha(ROOT/relative)
    block=34000
    receipt=read(old/f'worker_{block:06d}.json')
    source=old/f'reads_{block:06d}.npz'
    assert sha(source)==receipt['output_sha256']
    arrays(source,receipt['output_sha256'])
    for name in (source.name,f'worker_{block:06d}.json'):
        shutil.copyfile(old/name,folder/name)
    checkpoint={str(block):dict(data=sha(source),receipt=sha(old/f'worker_{block:06d}.json'))}
    bench=read(ROOT/'benchmark/COMPLETE.json')
    remaining=64-receipt['cases']
    forecast=1.5*bench['measured_seconds']*((remaining/16)*(16/2)*(4096/2048)+(remaining/16)*(1/2)*(1/3))+180
    manifest=dict(original,status='READY_TO_RESUME',created_at_utc=stamp(),code_sha256=code,
        forecast_cpu_seconds=forecast,resumption=dict(original_run=str(old),original_manifest_sha256=sha(old/'manifest.json'),
            interruption_sha256=sha(old/'INTERRUPTED.json'),reused_blocks=[34000],new_blocks=list(range(34001,34008)),
            checkpoint_sha256=checkpoint,scientific_configuration_unchanged=True,random_streams_unchanged=True,
            process_change='Detached persistent host worker, startup acknowledgment and file lock; no polling.'))
    write(folder/'manifest.json',manifest)
    write(folder/'START.json',dict(status='READY_TO_LAUNCH',at_utc=stamp(),manifest_sha256=sha(folder/'manifest.json')))
    print(dict(status='READY_TO_RESUME',run=str(folder),reused_blocks=[34000],remaining_cases=remaining,forecast_minutes=forecast/60))


if __name__=='__main__':
    main()
