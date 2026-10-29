"""New study boundary; inherited scientific code remains byte-identical."""
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'legacy'))
import study as inherited
import actions
import paired
import verify as inherited_verify
import fixtures

ev, read, require, ledger = inherited.ev, inherited.read, inherited.require, inherited.ledger
REGIMES, MODELS = inherited.REGIMES, inherited.MODELS
C = read(ROOT / 'protocol.json')


def admission():
    result = inherited.admission()
    result['planned_threads'] = C['resources']['workers']
    result['within_limit'] = result['other_active_or_recently_busy_threads'] + result['planned_threads'] <= 12
    return result


def verify_snapshot():
    entries = read(ROOT / 'INPUTS.json')['sha256']
    actual = {str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file()}
    require(actual == set(entries) | {'INPUTS.json'}, 'Snapshot coverage changed')
    require(not any(p.is_symlink() for p in ROOT.rglob('*')), 'Snapshot symlink')
    for name, digest in entries.items():
        require(ev.sha(ledger.child(ROOT, name)) == digest, 'Changed input: ' + name)
    inherited.verify_snapshot()
    return len(entries)


def manifest(folder, exclusions=()):
    return {str(p.relative_to(folder)): ev.sha(p) for p in sorted(folder.rglob('*'))
            if p.is_file() and p.name != 'STATUS.json' and p.name not in exclusions}


def check_manifest(folder, entries):
    for name, digest in entries.items():
        require(ev.sha(ledger.child(folder, name)) == digest, 'Changed output: ' + name)


class Guard:
    def __init__(self, folder, deadline):
        self.folder, self.deadline, self.next_check = folder, deadline, 0.

    def check(self):
        now = time.time()
        if now >= self.deadline:
            raise TimeoutError('Shared hard wall deadline; no extension')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > C['resources']['maximum_worker_resident_bytes']:
            raise MemoryError('Worker memory cap')
        if now >= self.next_check:
            require(shutil.disk_usage(self.folder).free >= C['resources']['minimum_free_disk_bytes'], 'Free disk cap')
            require(sum(p.stat().st_size for p in self.folder.rglob('*') if p.is_file()) <= C['resources']['maximum_worker_saved_bytes'], 'Worker evidence cap')
            self.next_check = now + 20.


def numerical_environment(tmp):
    tmp.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
               MKL_NUM_THREADS='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', TMPDIR=str(tmp))
    return env
