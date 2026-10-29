"""Count planned work using supplied bytes only, before simulating outcomes."""
from common import *
from sources import Source, configurations, identity


def main():
    groups = {}; used = {}
    for role in ('excluded', 'development'):
        blocks = {}
        for index in selected(role):
            source = Source(index, role); unique = {}; logical = 0; profiles = dict.fromkeys(PROFILES, 0)
            for alias in source.links.values():
                for profile, draw, feedback, packet, addr, initial in configurations(source, alias):
                    h = identity(profile, draw, feedback, addr, initial); blob = state_bytes(initial); logical += 1
                    assert h not in unique or unique[h] == blob
                    if h not in unique: unique[h] = blob; profiles[profile] += 1
            blocks[str(index)] = dict(physical=len(unique), logical=logical, profiles=profiles,
                                     unique_starting_identity_sha256=digest(encoded(sorted(unique))))
            used.update(source.c.used)
        groups[role] = dict(blocks=blocks, physical=sum(b['physical'] for b in blocks.values()))
    verify(used); write(ROOT/'LAYOUT_INPUTS.json', used)
    for role in groups:
        groups[role]['forecast_output_bytes'] = groups[role]['physical']*1024**2 + 1024**3
    total = sum(v['forecast_output_bytes'] for v in groups.values()) + 64*1024**2 + size()
    assert total < LIMIT and shutil.disk_usage(ROOT).free >= RESERVE + total
    value = dict(status='PASS', recorded_utc=now(), groups=groups, projected_study_bytes=total,
                 study_cap_bytes=LIMIT, free_reserve_bytes=RESERVE, source_inputs_sha256=sha(ROOT/'LAYOUT_INPUTS.json'),
                 output_rule='1 MiB per complete physical batch plus 1 GiB per phase and 64 MiB administration',
                 no_new_dynamics=True, no_production_outcomes_generated=True)
    write(ROOT/'LAYOUT.json', value); print(json.dumps(value), flush=True)


if __name__ == '__main__': main()
