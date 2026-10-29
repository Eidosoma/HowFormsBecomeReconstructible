from common import *


def main():
    assert read(PRIOR/'CLOSEOUT.json')['status'] == 'PASS'
    old = read(PRIOR/'SOURCE_MANIFEST.json')
    manifest = dict(created_utc=now(), native_code=old['native_code'], copied_code={str(ROOT/'physical_reference.py'):sha(ROOT/'physical_reference.py')},
                    source_population_exposed=True, new_production_outcomes_generated=False)
    assert sha(ROOT/'physical_reference.py') == sha(PRIOR/'physical_reference.py')
    for role, name in [('development', 'exchange_v1'), ('excluded', 'qualification_v1')]:
        p = PRIOR/'runs'/name/'COMPLETE.json'; receipt = read(p)
        assert receipt['status'] == 'COMPLETE'
        manifest[role] = old[role] | receipt['outputs'] | {str(p):sha(p)}
    evidence = [UP/n for n in ('FREEZE.json', 'CLOSEOUT.json', 'FINDINGS.json')]
    evidence += [PRIOR/n for n in ('FREEZE.json', 'CLOSEOUT.json', 'FINDINGS.json', 'COMPLETION_HANDOFF.json')]
    manifest['evidence'] = {str(p):sha(p) for p in evidence}; verify(manifest['evidence'])
    write(ROOT/'SOURCE_MANIFEST.json', manifest)
    bound = read(PRIOR/'COMPLETION_HANDOFF.json')['files']; verify(bound)
    bound = bound | {str(PRIOR/'COMPLETION_HANDOFF.json'):sha(PRIOR/'COMPLETION_HANDOFF.json')}; archive = {}
    for name, h in bound.items():
        p = Path(name); target = ROOT/'intake_inputs'/p.relative_to(LANE)
        target.parent.mkdir(parents=True, exist_ok=True); assert not target.exists()
        shutil.copyfile(p, target); assert sha(target) == h; archive[name] = dict(archive=str(target), sha256=h)
    write(ROOT/'intake_inputs/MANIFEST.json', archive)
    write(ROOT/'PLANNING_EXPOSURE.json', dict(recorded_utc=now(), source='Reviewed TT040/TT042; all four production blocks exposed',
          new_production_feedback_intervention_outcomes_generated=False, confirmatory=False, new_independent_futures_planned=0))
    print(json.dumps(dict(status='PREPARED', archived_handoff_files=len(archive))))


if __name__ == '__main__': main()
