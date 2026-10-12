"""Bind already exposed native controls; generate no new scientific lineages."""
import io
import json
import numpy as np
from common import ROOT,read,write,sha,descriptor,save_arrays,validate,stamp


def main():
    cfg=read(ROOT/'config.json');validate(cfg);folder=ROOT/'known';folder.mkdir(exist_ok=False)
    source=(ROOT/cfg['known_source_run']).resolve();bindings={}
    def bind(path,expected):
        assert sha(path)==expected,str(path);bindings[str(path)]=expected
    bind(source/'COMPLETE.json',cfg['known_source_complete_sha256'])
    outputs=read(source/'COMPLETE.json')['outputs_sha256']
    def get(name,keys,indexed=True):
        p=source/name;bind(p,outputs[name])
        with np.load(io.BytesIO(p.read_bytes()),allow_pickle=False) as f:
            index=json.loads(f['__index__'].tobytes())['arrays'] if indexed else None
            values={key:f[key] for key in keys}
        for k,v in values.items():
            if indexed:assert descriptor(v)==index[k],k
            assert v.dtype.kind in 'biuf' and np.isfinite(v).all(),k
        return values
    block=cfg['known_block']
    # Native teaching used ordinary NPZ, bound by its completed-run file hash.
    teaching=get(f'source_{block:06d}.npz',['teach_birth','teach_end','capture_states','weights','acquired'],indexed=False)
    before=get(f'boundary_{block:06d}_g13.npz',['outgoing'])
    after=get(f'boundary_{block:06d}_g14.npz',['masks','birth','end','mean_ports','outgoing'])
    values=dict(teach_birth=teaching['teach_birth'][1],teach_end=teaching['teach_end'][1],teach_capture_states=teaching['capture_states'][1],
        teach_weights=teaching['weights'][1],teach_acquired=teaching['acquired'][1],
        incoming=before['outgoing'][0:1],masks=after['masks'],birth=after['birth'][0],end=after['end'][0:1],mean_ports=after['mean_ports'][0:1],outgoing=after['outgoing'][0:1])
    digest=save_arrays(folder/'native_controls.npz',values)
    repair=(ROOT/cfg['repair_source_run']).resolve();bind(repair/'COMPLETE.json',cfg['repair_source_complete_sha256'])
    prior_manifest=read(repair/'manifest.json')
    for name in ('repair.py','optimizer.py','sign_graph.py','reader.py','audit_reader.py','audit_optimizer.py'):
        expected=prior_manifest['files_sha256'][name];bind(repair/'inputs'/name,expected);assert sha(ROOT/name)==expected
    write(folder/'COMPLETE.json',dict(status='COMPLETE',at_utc=stamp(),new_lineages_generated=0,
        sources_sha256=bindings,outputs_sha256={'native_controls.npz':digest},config_sha256=sha(ROOT/'config.json'),
        code_sha256={n:sha(ROOT/n) for n in ('common.py','prepare_known.py')}))
    print('Known teaching and renewal controls bound; new scientific lineages generated: zero.',flush=True)


if __name__=='__main__':main()
