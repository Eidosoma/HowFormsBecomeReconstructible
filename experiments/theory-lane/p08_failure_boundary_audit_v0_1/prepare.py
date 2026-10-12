"""Select all exposed six-call first later failures without generating dynamics."""
import hashlib
import io
import json
from pathlib import Path

import numpy as np
from common import ROOT, descriptor, equal, read, save_arrays, sha, stamp, validate, write

SOURCE = ROOT.parent / 'p08_repair_efficiency_v0_1' / 'runs' / 'prospective_v1'
EXPLORATION = SOURCE.parents[1] / 'exploration_v0_1'
SOURCE_COMPLETE = '29d8dcbc4a2e5395784b17e561f36a27630e5719d8ce2ba77f78c42e76b950ca'


def fixture(f, get, event, variants):
    gi = event['generation'] - 15
    case = event['case']
    incoming = get('incoming')[gi, variants, case]
    for packet in incoming[1:]:
        equal(packet, incoming[0], 'identical incoming packets in known pair')
    assert hashlib.sha256(incoming[0].tobytes()).hexdigest() == event['incoming_sha256']
    result = dict(incoming=incoming[0], mask=get('masks')[gi, case],
                  birth=get('birth')[gi, case], source_variants=np.array(variants, dtype=np.int64))
    for key in ('prepared', 'end', 'mean_ports', 'min_margin', 'both_pass', 'applied'):
        result[key] = get(key)[gi, variants, case]
    result['port_windows'] = np.stack([get('port_windows')[gi, :, v, case] for v in variants], axis=1)
    return result


def main():
    cfg = read(ROOT / 'source_config.json')
    validate(cfg)
    assert sha(SOURCE / 'COMPLETE.json') == SOURCE_COMPLETE
    assert sha(EXPLORATION / 'findings.json') == '38554fcb0b3e44af5372fcd57c9b8f4ba1109c0593c2f0167ae3f6c1f0e1f70f'
    assert sha(EXPLORATION / 'independent_crosscheck.json') == '693bb3076eff8775ebc704b04ae310479627f7d3c1d8dd0e9f818b916fef4957'
    complete = read(SOURCE / 'COMPLETE.json')
    exposed = [e for e in read(EXPLORATION / 'failure_events.json') if e['variant'] == 'repairs_6']
    exposed.sort(key=lambda e: (e['block'], e['case'], e['generation']))
    assert len(exposed) == 46 and len({e['block'] for e in exposed}) == 36
    known = read(EXPLORATION / 'identical_state_comparisons.json')
    controls = [next(e for e in known if e['outcome'] == outcome) for outcome in ('harm', 'rescue')]
    target = ROOT / 'fixtures'
    target.mkdir(exist_ok=False)
    census, rows, qualification, source_files = [], [], [], {}
    for b in cfg['blocks']:
        path = SOURCE / f'continuation_{b:06d}.npz'
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == complete['outputs_sha256'][path.name]
        source_files[path.name] = digest
        with np.load(io.BytesIO(raw), allow_pickle=False) as f:
            index = json.loads(f['__index__'].tobytes())
            cache = {}

            def get(key):
                if key not in cache:
                    cache[key] = f[key]
                    assert descriptor(cache[key]) == index[key], (b, key)
                    if cache[key].dtype.kind == 'f':
                        assert np.isfinite(cache[key]).all(), (b, key)
                return cache[key]

            good = get('both_pass')
            for case in range(16):
                bad = np.flatnonzero(~good[:, 1, case])
                if good[0, 1, case] and len(bad):
                    census.append((b, case, int(bad[0]) + 15))
            for e in [e for e in exposed if e['block'] == b]:
                data = fixture(f, get, e, [1])
                assert e['phase'] == 2 and not bool(data['applied'][0])
                assert not bool(data['both_pass'][0]) and float(data['min_margin'][0]) == e['margin']
                equal(data['incoming'], data['prepared'][0], 'no factual repair')
                name = f'fixtures/failure_{len(rows):02d}.npz'
                rows.append(dict(e, fixture=name, fixture_sha256=save_arrays(ROOT / name, data)))
            for control_i, e in enumerate(controls):
                if e['block'] != b:
                    continue
                comparison = e['comparisons'][0]
                variants = [cfg['variants'].index(comparison[k]) for k in ('no_repair', 'repair')]
                data = fixture(f, get, e, variants)
                assert data['applied'].tolist() == [False, True]
                assert data['both_pass'].tolist() == [e['no_repair_pass'], e['repair_pass']]
                name = f'fixtures/known_{control_i:02d}.npz'
                qualification.append(dict(e, fixture=name, fixture_sha256=save_arrays(ROOT / name, data)))
    assert census == [(e['block'], e['case'], e['generation']) for e in exposed]
    assert len(rows) == 46 and len(qualification) == 2
    write(ROOT / 'SELECTION.json', dict(at_utc=stamp(), events=rows, known_controls=qualification,
        census_checked_blocks=132, selection='All first failures after successful generation 15 in the six-call branch; 46 cases in 36 blocks.',
        source_complete_sha256=SOURCE_COMPLETE, source_files_sha256=source_files,
        exploration_files_sha256={name: sha(EXPLORATION / name) for name in
            ('COMPLETE.json', 'failure_events.json', 'findings.json', 'independent_crosscheck.json', 'next_step.json', 'identical_state_comparisons.json')}))
    print('Selected all 46 first later failures; 132-block raw census matches exposed selection. Two known paired controls retained.', flush=True)


if __name__ == '__main__':
    main()
