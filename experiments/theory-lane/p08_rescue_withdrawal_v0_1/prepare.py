"""Extract already observed boundaries and known qualification trajectories."""
import hashlib
import io
import json
from pathlib import Path

import numpy as np
from common import ROOT, arrays, descriptor, equal, read, save_arrays, sha, stamp, validate, write

BOUNDARY = ROOT.parent / 'p08_failure_boundary_audit_v0_1'
SOURCE = ROOT.parent / 'p08_repair_efficiency_v0_1' / 'runs' / 'prospective_v1'


def checked_source(block, complete):
    path = SOURCE / f'continuation_{block:06d}.npz'
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == complete['outputs_sha256'][path.name]
    return raw, digest


def take_fields(raw, names):
    with np.load(io.BytesIO(raw), allow_pickle=False) as f:
        index = json.loads(f['__index__'].tobytes())
        result = {name: f[name] for name in names}
    for name, a in result.items():
        assert descriptor(a) == index[name], name
        if a.dtype.kind == 'f':
            assert np.isfinite(a).all()
    return result


def main():
    validate(read(ROOT / 'source_config.json'))
    assert sha(BOUNDARY / 'COMPLETE.json') == 'd6fa26a1926168ebaf839d3d7baf2ac892c7d008555b2d8b11a7bcee53231f34'
    assert sha(SOURCE / 'COMPLETE.json') == '29d8dcbc4a2e5395784b17e561f36a27630e5719d8ce2ba77f78c42e76b950ca'
    boundary_complete = read(BOUNDARY / 'COMPLETE.json')
    for name, digest in boundary_complete['files_sha256'].items():
        assert sha(BOUNDARY / name) == digest, name
    assert read(BOUNDARY / 'VERIFICATION.json')['status'] == 'PASS'
    selection = read(BOUNDARY / 'SELECTION.json')['events']
    result = read(BOUNDARY / 'run' / 'COMPLETE.json')
    complete = read(SOURCE / 'COMPLETE.json')
    assert len(selection) == len(result['rows']) == 46 and result['counts']['rescue'] == 46
    fixtures = ROOT / 'fixtures'
    fixtures.mkdir(exist_ok=False)
    rows, source_files = [], {}
    for block in sorted({e['block'] for e in selection}):
        raw, digest = checked_source(block, complete)
        source_files[f'continuation_{block:06d}.npz'] = digest
        data = take_fields(raw, ['outgoing'])
        for i, (e, r) in enumerate(zip(selection, result['rows'], strict=True)):
            if e['block'] != block:
                continue
            assert (e['block'], e['case'], e['generation']) == (r['block'], r['case'], r['generation'])
            saved = arrays(BOUNDARY / 'run' / r['file'], r['sha256'])
            assert saved['both_pass'].tolist() == [False, True]
            saved['source_factual_outgoing'] = data['outgoing'][e['generation'] - 15, 1, e['case']]
            name = f'fixtures/boundary_{i:02d}.npz'
            rows.append(dict(e, fixture=name, fixture_sha256=save_arrays(ROOT / name, saved),
                             boundary_result_file=r['file'], boundary_result_sha256=r['sha256']))
    assert len(rows) == 46 and len({(e['block'], e['case'], e['generation']) for e in rows}) == 46
    known = []
    names = ['incoming', 'prepared', 'outgoing', 'masks', 'birth', 'end', 'port_windows',
             'mean_ports', 'min_margin', 'both_pass', 'opposite_margin', 'opposite_pass', 'applied']
    for i, (block, case) in enumerate([(83000, 0), (83011, 6)]):
        raw, digest = checked_source(block, complete)
        source_files[f'continuation_{block:06d}.npz'] = digest
        data = take_fields(raw, names)
        sliced = {}
        for key, a in data.items():
            sliced[key] = a[1:3, case] if key in ('masks', 'birth') else a[1:3, :, :, case] if key == 'port_windows' else a[1:3, :, case]
        assert sliced['applied'].tolist() == [[False, False, True], [False, False, True]]
        equal(sliced['incoming'][1], sliced['outgoing'][0], 'known own successor')
        name = f'fixtures/known_{i:02d}.npz'
        known.append(dict(block=block, case=case, generations=[16, 17], fixture=name,
                          fixture_sha256=save_arrays(ROOT / name, sliced)))
    write(ROOT / 'SELECTION.json', dict(at_utc=stamp(), events=rows, known_controls=known,
        source_complete_sha256=sha(SOURCE / 'COMPLETE.json'), boundary_complete_sha256=sha(BOUNDARY / 'COMPLETE.json'),
        boundary_selection_sha256=sha(BOUNDARY / 'SELECTION.json'), source_files_sha256=source_files,
        boundary_frozen_sha256=sha(BOUNDARY / 'FROZEN.json'), distinct_blocks=36,
        source_note='All 46 immediately rescued states retained, without inspecting any newly written rescued successors.'))
    print('Prepared all 46 saved paired boundary states and two exposed two-step qualification contexts.', flush=True)


if __name__ == '__main__':
    main()
