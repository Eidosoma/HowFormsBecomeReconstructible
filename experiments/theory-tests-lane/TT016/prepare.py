"""Freeze previously qualified implementations and exposed benchmark evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
LANE = HERE.parent


def run():
    files, bindings, reuse = {}, [], {}
    def sha(p):
        with p.open('rb') as f:
            return hashlib.file_digest(f, 'sha256').hexdigest()
    jobs = {n: json.loads((LANE / n / 'jobs' / mode / 'job.json').read_text())
            for n, mode in [('TT014', 'validation_v1'), ('TT015', 'audit_v1')]}
    def copy(study, original, target, expected=None, role=None):
        p = LANE / study / original
        digest = sha(p)
        if expected is not None:
            assert digest == expected, original
        q = HERE / target
        q.parent.mkdir(parents=True, exist_ok=True)
        with q.open('xb') as f:
            f.write(p.read_bytes())
        assert sha(q) == digest
        files[target] = digest
        bindings.append(dict(original=str(p), local=target, sha256=digest))
        if role:
            reuse[target] = dict(original=str(p), sha256=digest, role=role, unchanged=True)
    for name in ['lineage.py', 'native.py', 'optimizer.py', 'optimizer_audit.py', 'repair.py',
                 'source/spacing_dynamics.py', 'source/native/common.py',
                 'source/native/E015_functional_inheritance/model.py',
                 'source/native/E016_teaching_consistency/model.py',
                 'source/known/teaching.npz', 'source/known/g12.npz',
                 'source/known/g13.npz', 'source/known/g14.npz']:
        copy('TT014', name, name, jobs['TT014']['inputs_sha256'][name],
             'Qualified production acquisition/native adapter or independent repair and Prim solver')
    for original, target in [('lineage_audit.py', 'core.py'), ('support.py', 'support.py'),
                             ('capacity.py', 'capacity.py')]:
        copy('TT014', original, target, jobs['TT014']['inputs_sha256'][original], 'Qualified independent/helper module')
    copy('TT015', 'dynamics.py', 'dynamics_audit.py', jobs['TT015']['inputs_sha256']['dynamics.py'],
         'Unchanged indexed-neighbor continuation replay and flat writer')
    original = 'source/noise/inputs/lineage_dynamics.py'
    copy('TT015', original, 'roll_dynamics.py', jobs['TT015']['inputs_sha256'][original],
         'Qualified roll-based dynamics, now explicitly used as production implementation')
    for study, mode in [('TT014', 'validation_v1'), ('TT015', 'audit_v1')]:
        done = json.loads((LANE / study / 'runs' / mode / 'COMPLETE.json').read_text())
        close = json.loads((LANE / study / 'CLOSEOUT.json').read_text())
        assert done['audit_status'] == close['status'] == 'PASS'
        assert close['completion_sha256'] == sha(LANE / study / 'runs' / mode / 'COMPLETE.json')
        for rel, target in [(f'runs/{mode}/COMPLETE.json', 'COMPLETE.json'),
                            (f'jobs/{mode}/job.json', 'job.json'), ('CLOSEOUT.json', 'CLOSEOUT.json')]:
            copy(study, rel, 'source/' + study.lower() + '/' + target)
        for name in ['NATIVE_AUDIT.json', 'SCORING_AUDIT.json', 'TECHNICAL_CHECKS.json']:
            copy(study, f'runs/{mode}/{name}', 'source/' + study.lower() + '/' + name,
                 done['outputs_sha256'][name])
    for label in ['serial', 'noise']:
        original = f'source/{label}/run/continuation_081000.npz'
        copy('TT015', original, f'source/known/{label}_081000.npz', jobs['TT015']['inputs_sha256'][original])
    for original, target in [('source/noise/inputs/config.json', 'source/known/noise_config.json'),
                             ('source/noise/inputs/sources/boundaries.npz', 'source/known/boundaries.npz')]:
        copy('TT015', original, target, jobs['TT015']['inputs_sha256'][original])
    for name in ['PROTOCOL.md', 'statistics_block.py', 'engine.py', 'run.py', 'checks.py']:
        copy('TT014', name, 'source/design_reference/tt014_' + name, jobs['TT014']['inputs_sha256'][name])
    for name in ['PROTOCOL.md', 'scoring.py', 'intake.py']:
        copy('TT015', name, 'source/design_reference/tt015_' + name, jobs['TT015']['inputs_sha256'][name])
    stamp = datetime.now(timezone.utc).isoformat()
    for name, value in [
        ('SOURCE_RECEIPT.json', dict(recorded_utc=stamp, files_sha256=files, bindings=bindings,
                                    bytes=sum((HERE / x).stat().st_size for x in files), new_test_outcomes_generated=False)),
        ('IMPLEMENTATION_REUSE.json', dict(recorded_utc=stamp, reused=reuse,
            changed_modules=['continuation.py', 'interventions.py', 'analysis.py', 'statistics_block.py',
                             'engine.py', 'checks.py', 'report.py', 'register.py', 'run.py'],
            production_source_functions_execute=True, independent_full_replays=True,
            continuation_moment_adapter='Unchanged audit computes rho 1,.999,0 moments; retain active rho 1,0 rows.',
            new_test_outcomes_generated=False))]:
        with (HERE / name).open('x') as f:
            json.dump(value, f, indent=2, sort_keys=True)
            f.write('\n')
    print(json.dumps(dict(files=len(files), bytes=sum((HERE / x).stat().st_size for x in files))))


if __name__ == '__main__':
    run()
