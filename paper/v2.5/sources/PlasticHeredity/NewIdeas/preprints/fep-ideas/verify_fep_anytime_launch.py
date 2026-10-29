#!/usr/bin/env python3
"""Read frozen identities and seeds without importing simulation or policy code."""
import argparse
import sys
sys.dont_write_bytecode = True
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
from time import perf_counter
from datetime import datetime, timezone

parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
OUTPUT = parser.parse_args().output
assert OUTPUT.parent == Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-anytime-change-v1')
CHECKS = 0


def check(ok, label):
    global CHECKS
    assert ok, label
    CHECKS += 1


def identity(path):
    path = Path(path)
    h = sha256()
    with path.open('rb') as stream:
        for b in iter(lambda: stream.read(1048576), b''): h.update(b)
    return dict(path=str(path.resolve()), bytes=path.stat().st_size, sha256=h.hexdigest())


def main():
    start = perf_counter()
    mount = json.loads(subprocess.check_output(['findmnt', '-J', '-T', '/mnt/bioIce1', '-o', 'TARGET,SOURCE,FSTYPE'], text=True))['filesystems'][0]
    check(mount == dict(target='/mnt/bioIce1', source='/dev/sdc1', fstype='ext4'), 'external mount')
    check(not (OUTPUT/'EXECUTION_STARTED.json').exists() and not (OUTPUT/'LAUNCH.json').exists(), 'main not started')
    check(not list(OUTPUT.glob('FAILURE*')), 'no failed preparation')
    prep, pop, seeds, qual, bench = [json.loads((OUTPUT/name).read_text()) for name in
        ('PREPARATION.json', 'POPULATION.json', 'SEEDS.json', 'QUALIFICATION.json', 'BENCHMARK.json')]
    for group in ('inputs', 'source_snapshots', 'preserved'):
        for rec in prep[group]: check(identity(rec['path']) == rec, group+' identity')
    for rec in prep['source_snapshots']:
        check(any(rec['sha256'] == item['sha256'] and rec['bytes'] == item['bytes'] for item in prep['inputs']), 'snapshot matches source')
    failed = OUTPUT.parent/'attempt-01'
    check((failed/'FAILURE_prepare.json').is_file() and not (failed/'EXECUTION_STARTED.json').exists(), 'preserved failure before main')
    for name in ('POPULATION.json','SEEDS.json'):
        check((OUTPUT/name).read_bytes() == (failed/name).read_bytes(), 'unchanged frozen '+name)
    for name in ('FEP_ANYTIME_CHANGE_V1.md','qualify_fep_anytime_change.py'):
        check((OUTPUT/'inputs'/name).read_bytes() == (failed/'inputs'/name).read_bytes(), 'unchanged design/reference '+name)
    old_source=(failed/'inputs/check_fep_anytime_change.py').read_text()
    corrected=old_source.replace('atol=4e-15, rtol=0)', 'atol=2*f.nh*np.finfo(float).eps, rtol=0)')
    corrected=corrected.replace("    paths += sorted((PREVIOUS.parent/'readback-2026-10-10').iterdir())",
        "    paths += sorted((PREVIOUS.parent/'readback-2026-10-10').iterdir())\n    paths += [SOURCE/'FEP_ANYTIME_CHANGE_V1_CORRECTION.md', ROOT/'diagnostic-01/NORMALIZATION.json']")
    check((OUTPUT/'inputs/check_fep_anytime_change.py').read_text() == corrected, 'only documented assertion and preservation changes')
    previous = json.loads((OUTPUT.parent.parent/'fep-unexpected-change-v1/attempt-01/POPULATION.json').read_text())
    check(pop['bases'] == previous['bases'] and len(pop['bases']) == 27, 'unchanged base laws')
    check(pop['conditions'] == previous['conditions'], 'original panel')
    families = ['A_loss', 'B_loss', 'reverse', 'A_partial', 'B_partial', 'both_partial']
    check(pop['conditions'][19:] == [[f,t] for f in families for t in (13,38,63,88)], 'prospective shifted panel')
    check(pop['arms'] == previous['arms']+['CT3-anytime'] and len(pop['arms']) == 10, 'unchanged arms plus new model')
    check(pop['learner_change_times'] == list(range(1,101)) and pop['old_learner_change_times'] == [26,51,76] and pop['unexpected_physical_times'] == [13,38,63,88], 'timing separation')
    check(pop['model_prior'] == dict(no_change='1/2', per_time_kind='1/600', kinds=['G','A','B'], conditional_hazard='1/(201-t)', hypotheses=301), 'model prior frozen')
    check(pop['windows'] == [dict(start=t,tasks=min(25,101-t)) for t in (13,26,38,51,63,76,88)], 'window lengths')
    check(pop['coefficient_denominator'] == 144 and pop['post_scale'] == 34234200, 'exact denominators')
    for name, co in pop['coefficients'].items():
        check(len(co) == 43 and all(isinstance(x,int) and x >= 0 for x in co) and sum(co) == 144, 'weights '+name)
        if name.endswith('_full'): check(co[0] == 72, 'half stable '+name)
        if name.startswith('supported_'): check(all(x == 0 for x in co[19:]), 'supported isolation '+name)
        if name.startswith('unexpected_'): check(all(x == 0 for x in co[1:19]), 'unexpected isolation '+name)
    all_seeds = set()
    for group, prefix in (('blocks','fep-anytime-change-v1'),('flip_blocks','fep-anytime-change-v1-transfer-flips')):
        check(set(seeds[group]) == {m['label'] for m in pop['bases']}, 'all seed strata')
        for label, values in seeds[group].items():
            check(len(values) == 1024, 'seed stratum size')
            for block, value in enumerate(values):
                expected = str(int.from_bytes(sha256(f'{prefix}|20260924|{label}|{block}'.encode('ascii')).digest(), 'big'))
                check(value == expected, 'seed derivation')
                all_seeds.add(value)
    check(len(all_seeds) == 55296, 'unique seeds')
    for study, attempt in (('fep-unexpected-change-v1','01'),('fep-weak-prior-confirmation-v1','01'),('fep-calibrated-change-v1','02'),
            ('fep-changing-world-v1','01'),('fep-future-aware-checking-v1','01'),('fep-three-decision-checking-v1','01')):
        old = json.loads((OUTPUT.parent.parent/study/f'attempt-{attempt}/SEEDS.json').read_text())
        values = {x for group in ('blocks','flip_blocks') for row in old.get(group,{}).values() for x in row}
        check(not all_seeds.intersection(values), 'prior cohort separation '+study)
    check(qual['status'] == 'PASS' and qual['new_policy_implementations'] == 1 and qual['same_support_bridge'] and qual['old_arrays'] == 26, 'qualification')
    check(qual['rational_cases'] == 42 and qual['fresh_one_four_worker_chunks'] == 4, 'inherited and parallel checks')
    check(bench['workers'] == 4 and bench['synthetic_blocks'] == 32 and bench['conditions_per_block'] == 43 and bench['arms'] == 10, 'benchmark scope')
    check(bench['forecast_seconds'] == 120+3*bench['wall_seconds']*27648/32, 'frozen forecast')
    check(bench['requires_detached'] == (bench['forecast_seconds'] > 600), 'detachment rule')
    check(prep['cpus'] == [0,1,2,3] and all(r['cpus'] == prep['cpus'] for r in bench['records']), 'four CPU records')
    check(not (OUTPUT/'EXECUTION_STARTED.json').exists(), 'still no main execution')
    source = Path(__file__).resolve()
    snapshot = OUTPUT/source.name
    shutil.copyfile(source, snapshot)
    result = dict(status='PASS', utc=datetime.now(timezone.utc).isoformat(), assertions=CHECKS,
        wall_seconds=perf_counter()-start, source=identity(source), snapshot=identity(snapshot),
        verified_inputs=len(prep['inputs']), verified_snapshots=len(prep['source_snapshots']), verified_preserved=len(prep['preserved']),
        recomputed_seeds=len(all_seeds), main_started=False, policy_imported=False,
        preparation=identity(OUTPUT/'PREPARATION.json'), qualification=identity(OUTPUT/'QUALIFICATION.json'), benchmark=identity(OUTPUT/'BENCHMARK.json'))
    with (OUTPUT/'PRELAUNCH.json').open('x') as stream: json.dump(result,stream,indent=2,sort_keys=True); stream.write('\n')
    print(json.dumps(result))


if __name__ == '__main__': main()
