"""Local immutable inputs, native implementation and bounded job utilities."""
from pathlib import Path
import hashlib
import json
import os
import resource
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'native'))
import bridge
import fast_reader

np=bridge.e.np
native=bridge.e.native
flat=bridge.audit
ev=bridge.ev
P=json.loads((ROOT/'protocol.json').read_text())
assert P['reader']==bridge.P['reader'] and P['writer']['beta']==bridge.P['writer']['beta']==3.
POLICIES=P['policies']


def read(path):return json.loads(Path(path).read_text())
def sha(path):return ev.sha(Path(path))
def write(path,value):return ev.write(Path(path),value)
def stamp():return ev.utc()
def digest(array):return hashlib.sha256(array.tobytes()).hexdigest()


def verify_snapshot():
    path=ROOT/'INPUTS.json'
    if not path.is_file():raise ValueError('Frozen inputs required')
    manifest=read(path)
    for rel,expected in manifest['sha256'].items():
        candidate=(ROOT/rel).resolve()
        if not candidate.is_relative_to(ROOT) or sha(candidate)!=expected:
            raise ValueError('Frozen input differs: '+rel)
    if bridge.verify_inputs()!=len(read(ROOT/'native/INPUTS.json')['sha256']):
        raise ValueError('Native snapshot differs')
    return len(manifest['sha256'])


def byte_equal(a,b,label):
    if a.shape!=b.shape or a.dtype!=b.dtype or a.tobytes()!=b.tobytes():
        raise ArithmeticError('Byte identity failed: '+label)


class Deadline:
    def __init__(self,epoch):self.epoch=float(epoch)
    def check(self):
        if time.time()>=self.epoch:raise TimeoutError('Fixed job/stage deadline exceeded; no retry')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>P['resource']['max_worker_resident_bytes']:
            raise MemoryError('Frozen per-process memory cap')


def tree_bytes(folder):return sum(p.stat().st_size for p in Path(folder).rglob('*') if p.is_file())


def check_disk(folder):
    if shutil.disk_usage(folder).free<P['resource']['min_free_bytes']:
        raise OSError('Required free disk reserve unavailable')


def binding():return dict(inputs_sha256=sha(ROOT/'INPUTS.json'),protocol_sha256=sha(ROOT/'protocol.json'))


def status(folder,**values):ev.status(Path(folder),**values)
