"""Hash-verified retained fields; no generation of replacement source cases."""
import json
from pathlib import Path
import numpy as np
from common import dump, sha, utc
from E122_specificity_ceiling_and_tail.plan import ROOT,HERE,SOURCE,BENCH_SOURCE,BLOCKS,BENCHMARK,FACTORS

def root(mode):
    return SOURCE if mode == 'scientific' else BENCH_SOURCE

def register():
    target=HERE/'SOURCE_DATA.json'
    assert not target.exists()
    files={}; metadata={}; schemas={}
    for mode,ids in [('scientific',BLOCKS),('benchmark',(BENCHMARK,))]:
        src=root(mode); completion=json.loads((src/'COMPLETE.json').read_text())
        assert completion['status']=='COMPLETE' and not (src/'FAILED.json').exists()
        for name in ('COMPLETE.json','manifest.json','INDEPENDENT_AUDIT.json','summary.json'):
            p=src/name
            if p.exists(): metadata[str(p.relative_to(ROOT))]=sha(p)
        for block in ids:
            names=[f'source_{block:06d}.npz']+[f'block_{block:06d}_factor_{f}.npz' for f in FACTORS]
            for name in names:
                p=src/name; actual=sha(p)
                assert actual == completion['outputs_sha256'][name],str(p)
                files[str(p.relative_to(ROOT))]=dict(sha256=actual,bytes=p.stat().st_size,block=block,mode=mode)
                if block==ids[0]:
                    with np.load(p,allow_pickle=False) as z:
                        schemas[str(p.relative_to(ROOT))]={k:dict(shape=list(z[k].shape),dtype=str(z[k].dtype),bytes=z[k].nbytes) for k in z.files}
        if mode=='scientific':
            audit=json.loads((src/'INDEPENDENT_AUDIT.json').read_text())
            assert audit['status']=='PASS' and audit['complete_sha256']==sha(src/'COMPLETE.json')
    value=dict(utc=utc(),status='PASS',files=files,metadata_sha256=metadata,example_native_schemas=schemas,
        inclusion='All 64 E014 blocks, four founders, two recipients, both budgets; failed formations retained.',
        exposure='Known E014 cohort; new continuation and protected-foreign reads frozen before collection.',
        missing_fields=[],lossy_conversions=[],source_regeneration=False)
    dump(target,value);return value

def verify(mode,block=None):
    registry=json.loads((HERE/'SOURCE_DATA.json').read_text()); count=0
    for rel,h in registry['metadata_sha256'].items():
        assert sha(ROOT/rel)==h,rel
    for rel,info in registry['files'].items():
        if info['mode']==mode and (block is None or info['block']==block):
            assert sha(ROOT/rel)==info['sha256'],rel;count+=1
    return count

def load(mode,block,factor):
    src=root(mode)
    with np.load(src/f'block_{block:06d}_factor_{factor}.npz',allow_pickle=False) as z:
        keep=('prototype','prototype_halves','acquired','background','incoming','outgoing',
              'checkpoint_numbers','checkpoint_packets','checkpoint_read','checkpoint_birth','checkpoint_mask',
              'generation_read','generation_written')
        data={k:z[k].copy() for k in keep}
    np.testing.assert_array_equal(data['incoming'][1:],data['outgoing'][:-1])
    np.testing.assert_array_equal(data['checkpoint_packets'][-1],data['outgoing'][-1])
    with np.load(src/f'source_{block:06d}.npz',allow_pickle=False) as z:
        for k in ('prototype','prototype_halves','acquired','background'):
            np.testing.assert_array_equal(data[k],z[k])
    return data
