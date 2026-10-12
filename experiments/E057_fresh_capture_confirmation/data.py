"""Pinned predecessor evidence and a fresh-block register; no outcome selection."""
import json
from pathlib import Path
import numpy as np
from common import sha
from E057_fresh_capture_confirmation.plan import HERE, ROOT, BLOCKS, TECH_BLOCK, settings


def load(path):
    with np.load(path, allow_pickle=False) as handle:
        result = {k: handle[k] for k in handle.files}
    assert all(np.isfinite(v).all() for v in result.values()), str(path)
    return result


def save(path, arrays):
    assert all(np.isfinite(v).all() for v in arrays.values())
    with Path(path).open('xb') as handle:
        np.savez_compressed(handle, **arrays)


def receipt(mode):
    spec = json.loads((HERE/'SOURCE_DATA.json').read_text())
    seen = set()
    for rel, digest in spec['prior_manifest_sha256'].items():
        assert sha(ROOT/rel) == digest, rel
        seen.update(json.loads((ROOT/rel).read_text())['contract']['blocks'])
    assert sorted(seen) == spec['prior_block_ids']
    assert spec['blocks'] == list(BLOCKS) and not seen.intersection(BLOCKS)
    assert spec['excluded_block'] == TECH_BLOCK and TECH_BLOCK not in BLOCKS
    for rel, digest in spec['predecessors'].items():
        assert sha(ROOT/rel) == digest, rel
        assert json.loads((ROOT/rel).read_text())['status'] == 'PASS'
    if mode == 'scientific': return None
    entry = spec['technical_references'][mode]
    run = ROOT/entry['path']
    for rel,digest in entry['receipts'].items(): assert sha(ROOT/rel) == digest, rel
    complete=json.loads((run/'COMPLETE.json').read_text())
    audit=json.loads((run/'INDEPENDENT_AUDIT.json').read_text())
    assert complete['status']=='COMPLETE' and audit['status']=='PASS'
    assert audit['complete_sha256']==sha(run/'COMPLETE.json')
    c=json.loads((run/'manifest.json').read_text())['contract']; cfg=settings(mode)
    assert c['blocks']==[TECH_BLOCK] and c['config']==cfg['config'] and c['cycle']==cfg['cycle']
    for name,digest in entry['files'].items():
        assert complete['outputs_sha256'][name]==digest and sha(run/name)==digest, name
    return run


def compare(expected, actual):
    assert set(expected)==set(actual), (set(expected)-set(actual),set(actual)-set(expected))
    for key,x in expected.items():
        y=actual[key]
        assert x.shape==y.shape and x.dtype==y.dtype and x.tobytes()==y.tobytes(), key


def legacy_boundary(reference, block, generation, raw):
    old=load(reference/f'boundary_{block:06d}_g{generation}.npz')
    compare({'masks':raw['masks']},{'masks':old['masks']})
    for name in ('end','mean_ports','outgoing'):
        compare({name:raw[name]},{name:old[name][[0,20]]})
    for name in ('birth','noise_moments'):
        compare({name:raw[name]},{name:old[name][[0,4]]})
    compare({'write_state_hashes':raw['write_state_hashes']},
            {'write_state_hashes':old['write_state_hashes'][:,[0,20]]})
