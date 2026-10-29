"""Read-only inherited sources and the new paired-intervention contract."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'native'))
from bridge import P, e, audit, ev, read, verify_inputs as verify_native
import fast_reader
import runner as cached_runner
import ledger
import scoring_pilot
import audit_pilot
import independent_arithmetic

sys.path.insert(0, str(ROOT / 'repair_source'))
import repair
import optimizer
import audit_optimizer

C = read(ROOT / 'protocol.json')
assert C['reader'] == P['reader'] and C['writer'] == P['writer']
REGIMES = ('matched', 'independent')
ARMS = ('no_repair', 'repair_once')
MODELS = ('tt008', 'direct_rival', 'candidate')


def digest(array):
    return hashlib.sha256(array.tobytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_snapshot():
    root = ROOT.resolve()
    entries = read(root / 'INPUTS.json')['sha256']
    actual = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    require(actual == set(entries) | {'INPUTS.json'}, 'Frozen input coverage changed')
    require(not any(p.is_symlink() for p in root.rglob('*')), 'Input symlink')
    for name, value in entries.items():
        require(ev.sha(ledger.child(root, name)) == value, 'Changed input: ' + name)
    verify_native()
    return len(entries)


def admission():
    sys.path.insert(0, str(ROOT / 'native/inherited/reference'))
    import cpu_preflight
    return cpu_preflight.collect()
