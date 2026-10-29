from common import *


def main():
    assert read(PRIOR/'CLOSEOUT.json')['status'] == 'PASS'
    previous = read(PRIOR/'SOURCE_MANIFEST.json')
    manifest = dict(created_utc=now(), native_code=previous['native_code'], copied_code={},
                    source_population_exposed=True, new_production_future_outcomes_generated=False)
    for name in ('physical_reference.py', 'kernel.py', 'audit.py'):
        assert sha(ROOT/name) == sha(PRIOR/name); manifest['copied_code'][str(ROOT/name)] = sha(ROOT/name)
    for role, name in [('excluded', 'qualification_v1'), ('development', 'crossover_v1')]:
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
    seeds = {}; all_new = []; old = []
    for role in ('excluded', 'development'):
        seeds[role] = {}
        for index in selected(role):
            values = [future_address(role, index, k) for k in range(futures(role))]
            seeds[role][str(index)] = values; all_new.extend(values)
            old.extend([address(index)]+[reader_address(role, index, d) for d in range(births(role))])
    assert len(all_new) == len(set(all_new)) and not set(all_new)&set(old)
    write(ROOT/'SEEDS.json', dict(status='PASS', algorithm='SHA256 compact JSON domain/role/block/future; first 16 bytes little-endian',
          domain='TT045_fresh_forcing_v1', addresses=seeds, distinct_block_future_banks=len(all_new),
          prior_addresses=old, no_address_reuse=True, no_new_dynamics=True))
    write(ROOT/'PLANNING_EXPOSURE.json', dict(recorded_utc=now(), source='Reviewed TT044; four exposed blocks and old forcing outcomes',
          new_production_future_outcomes_generated=False, confirmatory=False, planned_new_futures_per_fixed_state=16))
    print(json.dumps(dict(status='PREPARED', archived_handoff_files=len(archived), new_seed_banks=len(all_new))))


if __name__ == '__main__': main()
