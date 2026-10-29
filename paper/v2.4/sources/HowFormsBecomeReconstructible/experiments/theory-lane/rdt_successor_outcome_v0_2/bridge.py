"""Local immutable native equations and the separately frozen precision protocol."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'inherited'))
import engine as e
import audit
import evidence as ev

P = PROTOCOL = json.loads((ROOT/'protocol.json').read_text())
assert P['reader'] == e.DESIGN['reader']
assert P['writer']['beta'] == e.DESIGN['writer']['beta']


def read(path):
    return json.loads(Path(path).read_text())


def verify_inputs():
    entries = read(ROOT/'INPUTS.json')['sha256']
    for name, digest in entries.items():
        if ev.sha(ROOT/name) != digest:
            raise ValueError('Frozen input changed: '+name)
    return len(entries)
