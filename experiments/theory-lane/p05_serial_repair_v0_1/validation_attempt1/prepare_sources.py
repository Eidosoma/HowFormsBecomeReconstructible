"""Bind the entire exposed enrollment and known controls; no new continuations."""
from pathlib import Path
import numpy as np
from common import ROOT,read,write,sha,arrays,save_arrays,stamp,validate


def main():
    cfg=read(ROOT/'config.json');validate(cfg)
    folder=ROOT/'sources';folder.mkdir(exist_ok=False)
    source=Path(cfg['source_run']);bindings={}
    def bind(path,digest):
        assert sha(path)==digest,str(path);bindings[str(path)]=digest
    bind(source/'COMPLETE.json',cfg['source_complete_sha256'])
    bind(source/'manifest.json',cfg['source_manifest_sha256'])
    receipt=read(source/'COMPLETE.json')
    bind(source/'VERIFICATION.json',receipt['outputs_sha256']['VERIFICATION.json'])
    assert receipt['status']=='COMPLETE' and receipt['independent_verification_passed']
    initial=[];ports=[]
    for block in cfg['blocks']:
        name=f'lineage_{block:06d}.npz';digest=receipt['outputs_sha256'][name]
        bind(source/name,digest);d=arrays(source/name,digest)
        assert int(d['block'])==block and int(d['history'])==cfg['history_by_block'][str(block)]
        initial.append(d['outgoing'][-1]);ports.append(d['mean_ports'][-1])
    boundaries=dict(blocks=np.array(cfg['blocks']),initial_packets=np.stack(initial),
                    pre_continuation_ports=np.stack(ports))
    out={'boundaries.npz':save_arrays(folder/'boundaries.npz',boundaries)}
    km=source/'inputs/known/COMPLETE.json'
    bind(km,read(source/'manifest.json')['files_sha256']['known/COMPLETE.json'])
    known=read(km);kp=source/'inputs/known/native_controls.npz'
    bind(kp,known['outputs_sha256']['native_controls.npz']);kd=arrays(kp)
    # Recheck the native archive bindings that define this already exposed control.
    for p,digest in known['sources_sha256'].items():bind(Path(p),digest)
    out['native_controls.npz']=save_arrays(folder/'native_controls.npz',
        {k:kd[k] for k in ('incoming','masks','birth','end','mean_ports','outgoing')})
    for name,item in read(ROOT/'SOURCE_REUSE.json').items():
        bind(Path(item['source']),item['source_sha256'])
        if item['use']=='unchanged':assert sha(ROOT/name)==item['source_sha256']
    write(folder/'COMPLETE.json',dict(status='COMPLETE',at_utc=stamp(),
        new_continuation_outcomes=0,records=256,source_outcomes_exposed=True,
        sources_sha256=bindings,outputs_sha256=out,config_sha256=sha(ROOT/'config.json'),
        code_sha256={n:sha(ROOT/n) for n in ('common.py','prepare_sources.py')}))
    print('Bound all 256 exposed records and known native control; no continuation outcomes.',flush=True)


if __name__=='__main__':main()
