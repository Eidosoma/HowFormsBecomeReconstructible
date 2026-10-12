"""Preserve already exposed inputs without changing any earlier experiment."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
LANE = HERE.parent


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    plan = json.loads((HERE/'plan.json').read_text())
    prior = LANE/plan['prior_run']
    if sha(prior/'COMPLETE.json') != plan['prior_complete_sha256']:
        raise ValueError('Prior completion identity changed')
    complete = json.loads((prior/'COMPLETE.json').read_text())
    for rel, digest in complete['outputs_sha256'].items():
        if sha(prior/rel) != digest: raise ValueError('Prior output changed: '+rel)
    if (HERE/'source_manifest.json').exists() or (HERE/'source').exists():
        raise FileExistsError('Prepared source already exists')
    now = datetime.now(timezone.utc).isoformat()
    with (LANE/'exposure_register.jsonl').open('a') as f:
        f.write(json.dumps(dict(event='UNCERTAINTY_DEVELOPMENT_REUSE', recorded_utc=now,
            study='TT004', classification='DEVELOPMENT', prior_run=plan['prior_run'],
            scope='All exposed TT003 repeated observations; frozen two-mode candidate and TT001 counterexample. No new native outcomes.'))+'\n')
    sources = {f'source/tt003/{name}':prior/name for name in ('COMPLETE.json', 'manifest.json', 'summary.json', 'observations.npz')}
    refs = json.loads((LANE/'TT003/reference_manifest.json').read_text())['files_sha256']
    for name in ('two_mode.py', 'joint_kernel.py'):
        path = LANE/'TT003/reference/theory'/name
        if sha(path) != refs['reference/theory/'+name]: raise ValueError('Theory source changed')
        sources['source/theory/'+name] = path
    sources['source/tt001/operators.py'] = LANE/'TT001/runs/development_v1/inputs/TT001/operators.py'
    receipt = dict(prepared_utc=now, prior_complete_sha256=plan['prior_complete_sha256'], files={})
    for rel, path in sources.items():
        destination = HERE/rel; destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        if sha(path) != sha(destination): raise ValueError('Source changed while copying')
        receipt['files'][rel] = dict(original_path=str(path), sha256=sha(destination))
    with (HERE/'source_manifest.json').open('x') as f: json.dump(receipt,f,indent=2); f.write('\n')
    print(json.dumps(dict(status='PREPARED', source_files=len(sources))))


if __name__ == '__main__': main()
