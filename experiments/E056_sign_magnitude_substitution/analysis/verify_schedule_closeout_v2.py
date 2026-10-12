"""Verify the scheduling receipts added after the frozen scientific closeout code."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def main():
    job = HERE / 'jobs/substitution_v1'
    run = HERE / 'runs/substitution_v1'
    jm, rm = read(job / 'manifest.json'), read(run / 'manifest.json')
    jc, rc = jm['contract'], rm['contract']
    ready = read(HERE / 'analysis/technical_v2.json')
    closeout = read(HERE / 'analysis/closeout_v1.json')
    assert ready['status'] == closeout['status'] == 'PASS'
    assert jm['inputs_sha256'] == rm['inputs_sha256'] == ready['inputs_sha256']
    assert jc['workers'] == rc['workers'] == 4
    assert jc['scheduling_revision'] == ready['scheduling_revision'] == 'four_workers_v2'
    assert jc['predecessor_evidence'] == rc['predecessor_evidence']
    evidence = dict(jc['predecessor_evidence'])
    for rel, digest in ready['evidence_sha256'].items():
        assert rel not in evidence or evidence[rel] == digest
        evidence[rel] = digest
    for rel, digest in evidence.items():
        assert sha(ROOT / rel) == digest, rel
    launch = read(job / 'launch.json')
    verified = read(HERE / 'analysis/scientific_launch_verification_v1.json')
    assert launch['workers'] == 4 and launch['detached'] and launch['stdin'] == '/dev/null'
    assert verified['status'] == 'PASS' and verified['launch'] == launch
    assert verified['frozen_inputs_verified'] == 26
    assert len(verified['workers']) == 4 and all(w['threads'] == 1 for w in verified['workers'])
    controller = jc['launch_controller_sha256']
    assert controller == launch['launch_controller_sha256']
    assert controller == sha(HERE / 'analysis/launch_v2.py') == sha(job / 'launch_controller_v2.py')
    status = read(job / 'status.json')
    assert status['status'] == 'COMPLETE' and not status['automatic_successor_started']
    assert status['complete_sha256'] == sha(run / 'COMPLETE.json')
    assert status['audit_sha256'] == sha(run / 'INDEPENDENT_AUDIT.json')
    for path in (job / 'manifest.json', run / 'manifest.json', job / 'launch.json',
                 job / 'launch_controller_v2.py', job / 'status.json',
                 HERE / 'analysis/closeout_v1.json',
                 HERE / 'analysis/scientific_launch_verification_v1.json'):
        evidence[str(path.relative_to(ROOT))] = sha(path)
    result = dict(status='PASS', utc=datetime.now(timezone.utc).isoformat(),
                  workers=4, frozen_inputs=26, predecessor_receipts_verified=4,
                  technical_v2_receipts_verified=len(ready['evidence_sha256']),
                  evidence_sha256=evidence, code_sha256=sha(__file__),
                  automatic_successor_started=False)
    with (HERE / 'analysis/schedule_closeout_v2.json').open('x') as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write('\n')
    print('PASS: four predecessor receipts, 19 readiness receipts and pinned four-worker controller')


if __name__ == '__main__':
    main()
