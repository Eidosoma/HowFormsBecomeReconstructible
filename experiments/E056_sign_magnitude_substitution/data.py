"""Audited source receipts; no case selection by outcome."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import sha
from E056_sign_magnitude_substitution.plan import HERE, ROOT
import numpy as np


def load(path):
    with np.load(path, allow_pickle=False) as f:
        out = {k:f[k] for k in f.files}
    assert all(np.isfinite(v).all() for v in out.values())
    return out


def save(path, arrays):
    with path.open('xb') as f: np.savez_compressed(f, **arrays)


def receipt(mode):
    index = json.loads((HERE/'SOURCE_DATA.json').read_text())
    for rel, digest in index['predecessors'].items():
        assert sha(ROOT/rel) == digest, rel
        assert json.loads((ROOT/rel).read_text())['status'] == 'PASS'
    entry = index['sources'][mode]; run = ROOT/entry['path']
    for rel, digest in entry['receipts'].items(): assert sha(ROOT/rel) == digest, rel
    complete = json.loads((run/'COMPLETE.json').read_text())
    audit = json.loads((run/'INDEPENDENT_AUDIT.json').read_text())
    assert complete['status'] == 'COMPLETE' and audit['status'] == 'PASS'
    assert audit['complete_sha256'] == sha(run/'COMPLETE.json')
    assert not (run/'FAILED.json').exists()
    for name, digest in entry['files'].items(): assert complete['outputs_sha256'][name] == digest
    return run, entry


def source(mode, block):
    run, index = receipt(mode); name = f'outgoing_{block:06d}.npz'
    assert sha(run/name) == index['files'][name]
    packets = load(run/name)['packets']
    # H,T,C-or-P,F,R,packet bytes; all histories, founders and recipients retained.
    return dict(packets=np.stack((packets[:, :2], packets[:, 2:4]), axis=1))
