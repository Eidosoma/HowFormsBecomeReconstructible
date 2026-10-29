"""Count actual starting-state/forcing work without simulating new outcomes."""
from common import *
from sources import Source, configurations, identity


def main():
    groups = {}; used = {}
    for role in ('excluded', 'development'):
        blocks = {}
        for index in selected(role):
            source = Source(index, role); unique = {}; logical = 0; owners = dict.fromkeys(CELLS, 0); by_cell = dict.fromkeys(CELLS, 0)
            for alias in source.links.values():
                for cell, draw, packet, force, addr, initial in configurations(source, alias):
                    h = identity(force, addr, initial); blob = state_bytes(initial); logical += 1; by_cell[cell] += 1
                    assert h not in unique or unique[h] == blob
                    if h not in unique: unique[h] = blob; owners[cell] += 1
            blocks[str(index)] = dict(physical=len(unique), logical=logical, physical_owners=owners, logical_by_cell=by_cell,
                                     unique_starting_identity_sha256=digest(encoded(sorted(unique))))
            used.update(source.c.used)
        groups[role] = dict(blocks=blocks, physical=sum(v['physical'] for v in blocks.values()))
        groups[role]['forecast_output_bytes'] = groups[role]['physical']*1024**2 + 1024**3
    verify(used); write(ROOT/'LAYOUT_INPUTS.json', used)
    total = sum(v['forecast_output_bytes'] for v in groups.values()) + 64*1024**2 + size()
    assert total < LIMIT and shutil.disk_usage(ROOT).free >= RESERVE+total
    value = dict(status='PASS', recorded_utc=now(), groups=groups, projected_study_bytes=total, study_cap_bytes=LIMIT,
                 free_reserve_bytes=RESERVE, source_inputs_sha256=sha(ROOT/'LAYOUT_INPUTS.json'),
                 output_rule='1 MiB per physical batch plus 1 GiB per phase and 64 MiB administration',
                 no_new_dynamics=True, no_production_crossed_outcomes_generated=True)
    write(ROOT/'LAYOUT.json', value); print(json.dumps(value), flush=True)


if __name__ == '__main__': main()
