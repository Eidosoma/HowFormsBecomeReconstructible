"""Local evidence, immutable native adapter and archived predictors."""
from copy import deepcopy
from pathlib import Path
import math
import os
import resource
import shutil
import sys
import time

import numpy as np
from scipy.special import expit

ROOT = Path(__file__).resolve().parent
NATIVE = ROOT / 'native'
sys.path.insert(0, str(NATIVE))
from bridge import P, ev, read
import ledger

C = read(ROOT / 'protocol.json')
ORIGINAL = deepcopy(P)
MODELS = read(ROOT / 'FROZEN_MODELS.json')['models']


def require(condition, message):
    if not condition:
        raise ValueError(message)


def manifest(folder, excludes=()):
    entries = {}
    for path in sorted(Path(folder).rglob('*')):
        require(not path.is_symlink(), 'Symlinks are not evidence')
        name = str(path.relative_to(folder))
        if path.is_file() and name not in excludes:
            entries[name] = ev.sha(path)
    return entries


def verify_sources():
    for name, item in read(ROOT / 'SOURCE_BINDINGS.json')['files'].items():
        require(ev.sha(ROOT / 'context' / name) == item['sha256'], 'Changed archived source: ' + name)
    require(manifest(NATIVE) == read(ROOT / 'NATIVE_PROVENANCE.json')['sha256'], 'Changed native implementation')
    archive = read(ROOT / 'context/ARCHIVED_FITS.json')
    for name, key in C['models'].items():
        require(MODELS[name] == archive['none']['models'][key], 'Changed archived coefficients')
    return len(read(ROOT / 'SOURCE_BINDINGS.json')['files'])


def verify_snapshot():
    require(manifest(ROOT, ('INPUTS.json',)) == read(ROOT / 'INPUTS.json')['sha256'], 'Frozen snapshot changed')
    verify_sources()
    return len(read(ROOT / 'INPUTS.json')['sha256'])


def configure(scope='benchmark'):
    require(scope in ('benchmark', 'development'), 'Unknown forcing scope')
    P.clear()
    P.update(deepcopy(ORIGINAL))
    P['forcing']['namespace'] = C['benchmark']['namespace'] if scope == 'benchmark' else read(ROOT / 'DEVELOPMENT.json')['namespace']


def feature_matrix(data, rows, spec):
    boundary = np.asarray(data['boundary'])[rows]
    require(boundary.ndim == 2 and boundary.shape[1] == 11 and np.isfinite(boundary).all(), 'Eleven finite boundary features required')
    if spec['kind'] == 'boundary':
        return boundary
    n = spec['n']
    require(n > 0, 'Positive probe count required')
    keys = ('writer', 'retained') if spec['kind'] == 'direct_pooled' else (spec['kind'],)
    for key in keys:
        require(key in ('writer', 'retained', 'rewrite'), 'Unknown predictor')
        values = np.asarray(data[key])
        require(values.ndim == 2 and values.shape[1] >= n and np.isin(values[rows, :n], [0, 1]).all(),
                'Complete binary probe prefix required')
    if spec['kind'] == 'direct_pooled':
        q = (np.asarray(data['writer'])[rows, :n].sum(axis=1) + np.asarray(data['retained'])[rows, :n].sum(axis=1)) / (2 * n)
    else:
        require(spec['kind'] in ('rewrite', 'retained'), 'Unknown predictor')
        q = np.asarray(data[spec['kind']])[rows, :n].mean(axis=1)
    require(np.isfinite(q).all() and np.all((q >= 0) & (q <= 1)), 'Invalid probe success fraction')
    return np.column_stack((boundary, q))


def probability_matrix(x, fitted):
    m = fitted['model']
    z = (np.asarray(x) - np.asarray(m['scaling']['mean'])) / np.asarray(m['scaling']['scale'])
    return expit(np.column_stack((np.ones(len(z)), z)) @ np.asarray(m['coefficients']))


def probability_scalar(features, fitted):
    m = fitted['model']
    require(len(features) + 1 == len(m['coefficients']), 'Feature dimension differs')
    eta = math.fsum([m['coefficients'][0]] + [b * (x - mu) / sd for x, b, mu, sd in
                    zip(features, m['coefficients'][1:], m['scaling']['mean'], m['scaling']['scale'], strict=True)])
    return 1 / (1 + math.exp(-eta)) if eta >= 0 else math.exp(eta) / (1 + math.exp(eta))


def environment(folder):
    Path(folder).mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               TMPDIR=str(folder), PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
    return env


class Guard:
    def __init__(self, folder, deadline):
        self.folder, self.deadline = Path(folder), deadline

    def check(self):
        require(time.time() < self.deadline, 'Fixed deadline reached; no extension')
        require(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 < C['runtime']['maximum_worker_resident_bytes'], 'Memory ceiling')
        require(shutil.disk_usage(self.folder).free >= C['runtime']['minimum_free_bytes'], 'Disk floor')


def complete(folder, result):
    paths = manifest(folder, ('STATUS.json', 'COMPLETE.json', 'OUTPUTS.json'))
    require(sum((folder / p).stat().st_size for p in paths) <= C['runtime']['maximum_saved_bytes'], 'Saved-data ceiling')
    ledger.atomic_json(folder / 'OUTPUTS.json', dict(sha256=paths))
    result.update(status='COMPLETE', utc=ev.utc(), output_manifest_sha256=ev.sha(folder / 'OUTPUTS.json'))
    ledger.atomic_json(folder / 'COMPLETE.json', result)
    ev.status(folder, status='COMPLETE', decision=result['decision'])


def verify_complete(folder):
    result = read(folder / 'COMPLETE.json')
    require(result['status'] == 'COMPLETE', 'Completed evidence required')
    require(result['output_manifest_sha256'] == ev.sha(folder / 'OUTPUTS.json'), 'Changed output commitment')
    require(read(folder / 'OUTPUTS.json')['sha256'] == manifest(folder, ('STATUS.json', 'COMPLETE.json', 'OUTPUTS.json')), 'Changed saved evidence')
    return result
