"""Bind the exposed cohort and copy two verified independent-noise controls."""
from pathlib import Path
import shutil
import numpy as np
from common import ROOT,read,write,sha,arrays,save_arrays,stamp,validate,equal


def main():
    cfg=read(ROOT/'config.json');validate(cfg)
    folder=ROOT/'sources';folder.mkdir(exist_ok=False);bindings={}
    def bind(path,digest):
        assert sha(path)==digest,str(path);bindings[str(path)]=digest
    prior=Path(cfg['prior_run'])
    bind(prior/'COMPLETE.json',cfg['prior_complete_sha256'])
    bind(prior/'manifest.json',cfg['prior_manifest_sha256'])
    complete=read(prior/'COMPLETE.json');manifest=read(prior/'manifest.json')
    assert complete['status']=='COMPLETE' and complete['independent_verification_passed']
    bind(prior/'VERIFICATION.json',complete['outputs_sha256']['VERIFICATION.json'])
    assert read(prior/'VERIFICATION.json')['status']=='PASS'
    source_receipt=prior/'inputs/sources/COMPLETE.json'
    bind(source_receipt,manifest['files_sha256']['sources/COMPLETE.json'])
    previous=read(source_receipt)
    for path,digest in previous['sources_sha256'].items():bind(Path(path),digest)
    prior_cfg=read(prior/'inputs/config.json')
    bind(prior/'inputs/config.json',manifest['files_sha256']['config.json'])
    for key in ('blocks','history_by_block','development_config','reader','cycle','optimizer','continuation_namespace','innovation_namespace'):
        assert cfg[key]==prior_cfg[key],key
    assert [prior_cfg['variants'][i] for i in cfg['control_source_indices']]==cfg['control_variants']
    outputs={}
    for name in ('boundaries.npz','native_controls.npz'):
        path=prior/'inputs/sources'/name;bind(path,previous['outputs_sha256'][name])
        arrays(path);shutil.copyfile(path,folder/name);outputs[name]=sha(folder/name)
    starts=arrays(folder/'boundaries.npz')
    for bi,block in enumerate(cfg['blocks']):
        path=prior/f'continuation_{block:06d}.npz';bind(path,complete['outputs_sha256'][path.name])
        d=arrays(path);selected={}
        for key,value in d.items():
            if key in ('renewal_cpu_seconds','independent_optimizer_checks'):continue
            if key in ('generation','masks','birth','block','history'):selected[key]=value
            elif key=='noise_moments':selected[key]=value[:,2:3].copy()
            elif key=='port_windows':selected[key]=value[:,:,[4,5]].copy()
            else:selected[key]=value[:,[4,5]].copy()
        equal(selected['incoming'][0,0],starts['initial_packets'][bi],'complete enrollment')
        equal(selected['incoming'][0,1],starts['initial_packets'][bi],'complete enrollment')
        name=f'controls_{block:06d}.npz';outputs[name]=save_arrays(folder/name,selected)
    for name,item in read(ROOT/'SOURCE_REUSE.json').items():
        bind(Path(item['source']),item['source_sha256'])
        if item['use']=='unchanged':assert sha(ROOT/name)==item['source_sha256'],name
    write(folder/'COMPLETE.json',dict(status='COMPLETE',at_utc=stamp(),records=256,
        source_outcomes_exposed=True,controls_exposed=True,new_continuation_outcomes=0,
        reused_control_contexts=9216,control_source_indices=[4,5],
        sources_sha256=bindings,outputs_sha256=outputs,config_sha256=sha(ROOT/'config.json'),
        code_sha256={name:sha(ROOT/name) for name in ('common.py','prepare_sources.py')}))
    print('Bound all 256 starts and copied 9,216 verified baseline/repeated control contexts.',flush=True)


if __name__=='__main__':main()
