"""Pinned E051 sources and append-only array evidence."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import sha
from E055_stress_capture_recovery.plan import HERE, ROOT, SOURCE_INDICES
import numpy as np


def load(path):
    with np.load(path, allow_pickle=False) as f:
        out = {k: f[k] for k in f.files}
    assert all(np.isfinite(v).all() for v in out.values())
    return out


def save(path, arrays):
    with path.open('xb') as f:
        np.savez_compressed(f, **arrays)


def receipt(mode):
    index = json.loads((HERE / 'SOURCE_DATA.json').read_text())
    assert sha(ROOT / index['closeout']) == index['closeout_sha256']
    assert json.loads((ROOT / index['closeout']).read_text())['status'] == 'PASS'
    for rel, digest in index['predecessors'].items():
        assert sha(ROOT / rel) == digest, rel
        assert json.loads((ROOT / rel).read_text())['status'] == 'PASS'
    entry = index['sources'][mode]
    for rel, digest in entry['receipts'].items():
        assert sha(ROOT / rel) == digest, rel
    run = ROOT / entry['path']
    complete = json.loads((run / 'COMPLETE.json').read_text())
    audit = json.loads((run / 'INDEPENDENT_AUDIT.json').read_text())
    assert complete['status'] == 'COMPLETE' and audit['status'] == 'PASS'
    assert audit['complete_sha256'] == sha(run / 'COMPLETE.json')
    assert not (run / 'FAILED.json').exists()
    for name, digest in entry['files'].items():
        assert complete['outputs_sha256'][name] == digest
    return run, entry


def source(mode, block):
    from E015_functional_inheritance.model import decode
    run, entry = receipt(mode)
    names = (f'source_{block:06d}.npz', f'boundary_{block:06d}_g32.npz')
    for name in names:
        assert sha(run / name) == entry['files'][name], name
    a, last = [load(run / name) for name in names]
    acquired = decode(a['acquired'][1])
    renewed = decode(last['outgoing'][list(SOURCE_INDICES)])
    R = renewed.shape[2]
    records = np.concatenate((np.repeat(acquired[:, None], R, axis=1)[None], renewed))
    return dict(records=records, source_last_masks=last['masks'])
