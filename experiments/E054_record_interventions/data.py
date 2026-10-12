"""Source provenance and immutable NPZ I/O (no scientific selection)."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import sha
from E054_record_interventions.plan import ROOT, HERE, SOURCE_INDICES
import numpy as np


def load(path):
    with np.load(path, allow_pickle=False) as f: return {k:f[k] for k in f.files}


def save(path, values):
    with path.open('xb') as f: np.savez_compressed(f, **values)


def receipt(mode):
    index = json.loads((HERE/'SOURCE_DATA.json').read_text())
    entry = index['sources'][mode]
    for rel, digest in entry['receipts'].items(): assert sha(ROOT/rel) == digest, rel
    run = ROOT/entry['path']
    complete = json.loads((run/'COMPLETE.json').read_text())
    audit = json.loads((run/'INDEPENDENT_AUDIT.json').read_text())
    assert complete['status'] == 'COMPLETE' and audit['status'] == 'PASS'
    assert audit['complete_sha256'] == sha(run/'COMPLETE.json')
    assert not (run/'FAILED.json').exists()
    assert json.loads((ROOT/index['closeout']).read_text())['status'] == 'PASS'
    assert sha(ROOT/index['closeout']) == index['closeout_sha256']
    for name, digest in entry['files'].items(): assert complete['outputs_sha256'][name] == digest
    return run, entry


def source(mode, block):
    from E015_functional_inheritance.model import decode
    run, entry = receipt(mode)
    names = [f'source_{block:06d}.npz', f'boundary_{block:06d}_g31.npz', f'boundary_{block:06d}_g32.npz']
    for name in names: assert sha(run/name) == entry['files'][name], name
    old, last = load(run/names[1]), load(run/names[2])
    with np.load(run/names[0], allow_pickle=False) as f: acquired = decode(f['acquired'][1])
    renewal = decode(last['outgoing'][list(SOURCE_INDICES)])
    R = renewal.shape[2]
    records = np.concatenate((np.repeat(acquired[:, None], R, axis=1)[None], renewal))
    returning = old['masks'] & ~last['masks']; alive = ~last['masks']
    available = np.stack((alive & np.roll(alive, -1, -1), alive & np.roll(alive, -1, -2)), axis=-3)
    incident = np.stack((returning | np.roll(returning, -1, -1),
                         returning | np.roll(returning, -1, -2)), axis=-3)
    incoming = decode(old['outgoing'][list(SOURCE_INDICES)])*available
    repair = np.zeros(records.shape, bool)
    repair[1:] = incident & available & (incoming == 0) & (renewal != 0)
    assert np.isfinite(records).all() and not (repair & (records == 0)).any()
    return dict(records=records, repair=repair)
