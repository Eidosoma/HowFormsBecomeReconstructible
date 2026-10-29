from common import *


def main():
    assert read(PRIOR/'CLOSEOUT.json')['status'] == 'PASS'
    previous = read(PRIOR/'SOURCE_MANIFEST.json')
    manifest = dict(created_utc=now(), native_code=previous['native_code'], copied_code={},
                    source_population_exposed=True, new_production_crossed_outcomes_generated=False)
    for name in ('physical_reference.py', 'kernel.py', 'audit.py'):
        assert sha(ROOT/name) == sha(PRIOR/name)
        manifest['copied_code'][str(ROOT/name)] = sha(ROOT/name)
    for role, name in [('excluded', 'qualification_v1'), ('development', 'feedback_v1')]:
        p = PRIOR/'runs'/name/'COMPLETE.json'; complete = read(p); assert complete['status'] == 'COMPLETE'
        manifest[role] = complete['outputs'] | {str(p):sha(p)}
    evidence = [PRIOR/n for n in ('FREEZE.json', 'CLOSEOUT.json', 'FINDINGS.json', 'COMPLETION_HANDOFF.json')]
    manifest['evidence'] = {str(p):sha(p) for p in evidence}; verify(manifest['evidence'])
    write(ROOT/'SOURCE_MANIFEST.json', manifest)
    bound = read(PRIOR/'COMPLETION_HANDOFF.json')['files']; verify(bound)
    bound = bound | {str(PRIOR/'COMPLETION_HANDOFF.json'):sha(PRIOR/'COMPLETION_HANDOFF.json')}; archived = {}
    for name, h in bound.items():
        source = Path(name); target = ROOT/'intake_inputs'/source.relative_to(LANE)
        target.parent.mkdir(parents=True, exist_ok=True); assert not target.exists()
        shutil.copyfile(source, target); assert sha(target) == h; archived[name] = dict(archive=str(target), sha256=h)
    write(ROOT/'intake_inputs/MANIFEST.json', archived)
    write(ROOT/'PLANNING_EXPOSURE.json', dict(recorded_utc=now(), source='Reviewed TT043; four exposed blocks and CC/FF diagonal outcomes known',
          new_production_crossed_outcomes_generated=False, confirmatory=False, new_independent_futures_planned=0))
    print(json.dumps(dict(status='PREPARED', archived_handoff_files=len(archived))))


if __name__ == '__main__': main()
