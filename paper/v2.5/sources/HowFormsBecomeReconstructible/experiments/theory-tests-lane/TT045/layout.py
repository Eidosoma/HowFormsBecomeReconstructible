"""Byte-only work and storage bounds before simulating new futures."""
from common import *
from sources import Source, configurations, identity


def main():
    groups = {}; used = {}
    for role in ('excluded', 'development'):
        blocks = {}
        for index in selected(role):
            source = Source(index, role); unique = {}; starting = {}; logical = 0
            owners = dict.fromkeys(PROFILES, 0); by_profile = dict.fromkeys(PROFILES, 0)
            for alias in source.links.values():
                for profile, birth, future, packet, addr, initial in configurations(source, alias):
                    blob = state_bytes(initial); ih = digest(blob); h = identity(addr, initial)
                    if ih in starting: assert starting[ih] == blob
                    else: starting[ih] = blob
                    assert h not in unique or unique[h] == ih
                    if h not in unique: unique[h] = ih; owners[profile] += 1
                    logical += 1; by_profile[profile] += 1
            blocks[str(index)] = dict(physical=len(unique), logical=logical, physical_owners=owners,
                logical_by_profile=by_profile, distinct_initial_states_and_packets=len(starting),
                unique_starting_identity_sha256=digest(encoded(sorted(unique))))
            used.update(source.c.used)
        groups[role] = dict(blocks=blocks, physical=sum(v['physical'] for v in blocks.values()))
        groups[role]['forecast_output_bytes'] = groups[role]['physical']*BATCH_BYTES+1024**3
    verify(used); write(ROOT/'LAYOUT_INPUTS.json', used)
    total = sum(v['forecast_output_bytes'] for v in groups.values())+64*1024**2+size()
    assert total < LIMIT and shutil.disk_usage(ROOT).free >= RESERVE+total
    value = dict(status='PASS', recorded_utc=now(), groups=groups, projected_study_bytes=total,
        study_cap_bytes=LIMIT, free_reserve_bytes=RESERVE, package_cap_bytes=BATCH_BYTES,
        source_inputs_sha256=sha(ROOT/'LAYOUT_INPUTS.json'), seed_manifest_sha256=sha(ROOT/'SEEDS.json'),
        output_rule='700 KiB per complete packed physical package plus 1 GiB per phase and 64 MiB administration',
        no_new_dynamics=True, no_production_future_outcomes_generated=True)
    write(ROOT/'LAYOUT.json', value)
    print(json.dumps({k:v for k,v in value.items() if k != 'groups'} | {'physical':{r:g['physical'] for r,g in groups.items()}}), flush=True)


if __name__ == '__main__': main()
