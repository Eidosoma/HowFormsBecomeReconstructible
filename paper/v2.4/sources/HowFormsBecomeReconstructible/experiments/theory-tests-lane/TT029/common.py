"""Saved-data analysis helpers. No simulator or stochastic generator imports."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LANE = ROOT.parent
UPSTREAM = LANE/'TT028'
BLOCKS = tuple(range(28000000, 28000064))
EXCLUDED = (608280, 608281)
FAMILIES = ('common', 'residual')
DAMAGES = ('mix000', 'mix050', 'mix100')
BODIES = ('own', 'foreign', 'neutral')
ARMS = ('corrected_0000', 'corrected_0100', 'corrected_1000', 'full_1000', 'zero_1000')
SELECTED = ARMS[:3]
STRATA = ('positive_half_retained', 'negative_half_retained', 'both_polarities_retained')
HISTORY = ('unique_pass', 'not_unique_pass')
SIGNS = ('improved', 'worsened', 'tied')
GROUPS = ('all',)+tuple('history:'+v for v in HISTORY)+tuple('injury:'+v for v in STRATA)+tuple(
    'history_injury:'+h+'|'+s for h in HISTORY for s in STRATA)+tuple('message:'+str(m) for m in range(4))
LEVELS = ('receiving_draw', 'fixed_output_pair', 'record_position')


def now(): return datetime.now(timezone.utc).isoformat()
def digest(value): return hashlib.sha256(value).hexdigest()
def sha(path): return digest(Path(path).read_bytes())
def read_json(path): return json.loads(Path(path).read_text())
def serialized(value): return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()
def write_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream: stream.write(serialized(value))
def verify(files):
    for name, expected in files.items(): assert sha(name) == expected, name
def arms(body): return ARMS if body == 'own' else (ARMS[0], ARMS[2])
def sign(value): return 'improved' if value > 0 else 'worsened' if value < 0 else 'tied'
def units(value):
    assert isinstance(value, (float, int)) and not isinstance(value, bool)
    assert value in (0., .25, 1/3, .5, 1.)
    result = round(value*12)
    assert abs(result/12-value) <= 2e-15
    return result
def grouping(row):
    return ('all', 'history:'+row['history'], 'injury:'+row['injury'],
        'history_injury:'+row['history']+'|'+row['injury'], 'message:'+str(row['message']))
def identities(values):
    return {k:dict(shape=list(v.shape), dtype=str(v.dtype), sha256=digest(v.tobytes())) for k,v in values.items()}


class Custody:
    def __init__(self, hashes):
        self.hashes = hashes
        self.consumed = {}

    def data(self, path):
        path = str(Path(path).resolve())
        data = Path(path).read_bytes()
        assert digest(data) == self.hashes[path], path
        self.consumed[path] = self.hashes[path]
        return data

    def json(self, path): return json.loads(self.data(path))
