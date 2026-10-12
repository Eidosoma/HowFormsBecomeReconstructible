"""Bind exposed starts, previous injuries and the two exact replay controls."""
from pathlib import Path
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
    bind(prior/'VERIFICATION.json',complete['outputs_sha256']['VERIFICATION.json'])
    assert complete['status']=='COMPLETE' and complete['independent_verification_passed']
    source_receipt=prior/'inputs/sources/COMPLETE.json'
    bind(source_receipt,manifest['files_sha256']['sources/COMPLETE.json'])
    previous=read(source_receipt)
    for path,digest in previous['sources_sha256'].items():bind(Path(path),digest)
    out={}
    original=arrays(prior/'inputs/sources/boundaries.npz',
                    previous['outputs_sha256']['boundaries.npz'])
    bind(prior/'inputs/sources/boundaries.npz',previous['outputs_sha256']['boundaries.npz'])
    fresh=Path(read(prior/'inputs/config.json')['source_run'])
    fresh_receipt=read(fresh/'COMPLETE.json')
    previous_masks=[]
    for bi,block in enumerate(cfg['blocks']):
        name=f'lineage_{block:06d}.npz';bind(fresh/name,fresh_receipt['outputs_sha256'][name])
        old=arrays(fresh/name);previous_masks.append(old['masks'][-1])
        equal(old['outgoing'][-1],original['initial_packets'][bi],'source enrollment')
        name=f'continuation_{block:06d}.npz';bind(prior/name,complete['outputs_sha256'][name])
        d=arrays(prior/name)
        equal(d['incoming'][0,0],original['initial_packets'][bi],'prior replay enrollment')
        selected={k:d[k][:,[0,2]].copy() for k in ('incoming','prepared','outgoing','end','mean_ports',
                                                'both_pass','opposite_pass','min_margin','opposite_margin')}
        selected['port_windows']=d['port_windows'][:,:,[0,2]].copy()
        selected.update(masks=d['masks'],birth=d['birth'],generation=d['generation'])
        out[f'matched_{block:06d}.npz']=save_arrays(folder/f'matched_{block:06d}.npz',selected)
    original['previous_masks']=np.stack(previous_masks)
    out['boundaries.npz']=save_arrays(folder/'boundaries.npz',original)
    known=prior/'inputs/sources/native_controls.npz'
    bind(known,previous['outputs_sha256']['native_controls.npz'])
    out['native_controls.npz']=save_arrays(folder/'native_controls.npz',arrays(known))
    for name,item in read(ROOT/'SOURCE_REUSE.json').items():
        bind(Path(item['source']),item['source_sha256'])
        if item['use'].startswith('unchanged'):assert sha(ROOT/name)==item['source_sha256'],name
    write(folder/'COMPLETE.json',dict(status='COMPLETE',at_utc=stamp(),records=256,
        source_outcomes_exposed=True,matched_controls_exposed=True,new_continuation_outcomes=0,
        sources_sha256=bindings,outputs_sha256=out,config_sha256=sha(ROOT/'config.json'),
        code_sha256={n:sha(ROOT/n) for n in ('common.py','prepare_sources.py')}))
    print('Bound 256 initial records, previous masks and both matched control histories.',flush=True)


if __name__=='__main__':main()
