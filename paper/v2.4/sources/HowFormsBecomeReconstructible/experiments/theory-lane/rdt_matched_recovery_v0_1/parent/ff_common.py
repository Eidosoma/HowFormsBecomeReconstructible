"""Immutable native adapter and bounded execution helpers for this study."""
from copy import deepcopy
from pathlib import Path
import os
import resource
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parent
QUALIFIED = ROOT/'qualified'
sys.path.insert(0, str(QUALIFIED))
import ec_common as equal_read
NATIVE = QUALIFIED/'native'
sys.path.insert(0, str(NATIVE))
from bridge import P, e, ev, read
import ledger

C = read(ROOT/'protocol.json')
ORIGINAL = deepcopy(P)
REGIMES = ('matched', 'independent')
MODELS = ('successor32', 'direct64', 'pooled32', 'direct8', 'tt008')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def configure(scope):
    require(scope in ('qualification', 'scientific'), 'Unknown scope')
    namespace = C['namespace'] if scope == 'scientific' else C['qualification_namespace']
    new = deepcopy(ORIGINAL)
    changes = {}
    for section, field, suffix in [('acquisition','namespace','acquisition'),
            ('selection','namespace','selection'), ('forcing','namespace','probe'),
            ('forcing','future_namespace','future')]:
        new[section][field] = namespace+'/'+suffix
        changes[section+'.'+field] = dict(before=ORIGINAL[section][field], after=new[section][field])
    # All native modules retain this same dict object. Numerical fields are unchanged.
    P.clear(); P.update(new)
    return changes


def specification(scope):
    require(scope in ('qualification', 'scientific'), 'Unknown scope')
    source = C['cohort'] if scope == 'scientific' else C['qualification']
    return dict(scope=scope, first_block=source['first_block'],
        eligible_blocks=source['eligible_blocks'], maximum_attempts=source['maximum_attempts'],
        wave_size=source['wave_size'], repeats=C['repeats'], regimes=C['regimes'])


def manifest(folder, excludes=()):
    folder = Path(folder)
    result = {}
    for p in sorted(folder.rglob('*')):
        require(not p.is_symlink(), 'Symlink in evidence')
        name = str(p.relative_to(folder))
        if p.is_file() and name not in excludes:
            result[name] = ev.sha(p)
    return result


def verify_snapshot():
    entries = read(ROOT/'INPUTS.json')['sha256']
    require(manifest(ROOT, ('INPUTS.json',)) == entries, 'Frozen input contents or coverage changed')
    require(ev.sha(QUALIFIED/'FROZEN_MODELS.json') == C['models_sha256'], 'Frozen five-model coefficients changed')
    source = read(ROOT/'SOURCE_BINDINGS.json')
    require(ev.sha(QUALIFIED/'INPUTS.json') == source['qualified_input_manifest_sha256'], 'Qualified measurement snapshot changed')
    equal_read.verify_snapshot()
    for name, item in source['copied_context'].items():
        require(ev.sha(ROOT/'context'/name) == item['sha256'], 'Changed context: '+name)
    budget = read(ROOT/'context/BUDGET_REVIEW_RESULTS.json')
    chosen = budget['chosen']
    require(ev.sha(ROOT/'context/BUDGET_REVIEW_RESULTS.json') == C['resource_basis']['budget_review_results_sha256'], 'Resource evidence changed')
    require((C['cohort']['eligible_blocks'], C['cohort']['maximum_attempts'], len(C['repeats'])) == (chosen['blocks'], chosen['charged_attempts'], chosen['repeats']), 'Scientific scope differs from priced design')
    require(chosen['conservative_wall_seconds'] == C['resource_basis']['full_cap_forecast_seconds'] <= 21300, 'Six-hour reserve not qualified')
    require(manifest(NATIVE) == read(ROOT/'NATIVE_PROVENANCE.json')['sha256'], 'Native source changed')
    return len(entries)


def binding():
    return dict(input_manifest_sha256=ev.sha(ROOT/'INPUTS.json'),
                protocol_sha256=ev.sha(ROOT/'protocol.json'), models_sha256=C['models_sha256'])


def identity(spec, kind, **fields):
    return dict(binding=binding(), spec=spec, kind=kind, **fields)


def environment(tmp):
    tmp = Path(tmp); tmp.mkdir(parents=True, exist_ok=True)
    value = os.environ.copy()
    value.update(PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                 MKL_NUM_THREADS='1', TMPDIR=str(tmp), PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
    return value


def worker_count(scope):
    require(scope in ('qualification', 'scientific'), 'Unknown worker scope')
    return C['qualification']['workers'] if scope == 'qualification' else C['resources']['workers']


def admission(scope):
    sys.path.insert(0, str(NATIVE/'inherited/reference'))
    import cpu_preflight
    receipt = cpu_preflight.collect()
    receipt['planned_threads'] = worker_count(scope)+1  # parent reserve
    receipt['within_limit'] = receipt['other_active_or_recently_busy_threads']+receipt['planned_threads'] <= 12
    return receipt


class Guard:
    def __init__(self, folder, deadline):
        self.folder, self.deadline = Path(folder), deadline
        self.next_disk = 0.

    def check(self):
        if time.time() >= self.deadline:
            raise TimeoutError('Fixed wall deadline reached; no extension or partial inference')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 > C['resources']['maximum_worker_resident_bytes']:
            raise MemoryError('Resident-memory ceiling reached')
        if time.monotonic() >= self.next_disk:
            require(shutil.disk_usage(self.folder).free >= C['resources']['minimum_free_bytes'], 'Disk floor reached')
            self.next_disk = time.monotonic()+30

    def account(self):
        self.check()
        size = sum(p.stat().st_size for p in self.folder.rglob('*') if p.is_file())
        require(size <= C['resources']['maximum_saved_bytes'], 'Saved-data ceiling reached')
        return size


def completed_outputs(folder, result):
    """Mutable status and final receipt are outside the stable evidence manifest."""
    entries = manifest(folder, ('STATUS.json', 'OUTPUTS.json', 'COMPLETE.json'))
    ledger.atomic_json(folder/'OUTPUTS.json', dict(sha256=entries))
    result.update(utc=ev.utc(), input_manifest_sha256=ev.sha(ROOT/'INPUTS.json'),
                  output_manifest_sha256=ev.sha(folder/'OUTPUTS.json'))
    ledger.atomic_json(folder/'COMPLETE.json', result)
    ev.status(folder, status='COMPLETE', decision=result['decision'], scope=result['scope'])


def verify_completed(folder):
    folder = Path(folder); result = read(folder/'COMPLETE.json')
    require(result['status'] == 'COMPLETE', 'Completion required')
    require(result['output_manifest_sha256'] == ev.sha(folder/'OUTPUTS.json'), 'Changed completion manifest')
    require(read(folder/'OUTPUTS.json')['sha256'] == manifest(folder, ('STATUS.json','OUTPUTS.json','COMPLETE.json')),
            'Changed completed evidence')
    return result
