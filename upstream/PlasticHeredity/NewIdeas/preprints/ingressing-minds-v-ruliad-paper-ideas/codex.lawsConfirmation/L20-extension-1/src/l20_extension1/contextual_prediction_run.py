"""D176 write-once saved-data workflow. No physics or prospective launch route."""
import argparse
import os
from pathlib import Path
import sys
import time
import traceback
import xml.etree.ElementTree as ET
import zipfile
import numpy as np
from . import settings_prediction_run as io
from . import contextual_prediction as model, contextual_prediction_check as check

ROOT, WS = io.ROOT, io.WS
RUN = 'l20_extension1_contextual_prediction_dev_v1_attempt1'
PULSE = 'l20_extension1_feedback_pulse_dev_v1_attempt1'
SETTINGS = io.RUN
SCIENCE = ('contextual-prediction/PROTOCOL_V1.md', 'src/l20_extension1/contextual_prediction.py',
    'src/l20_extension1/contextual_prediction_check.py', 'src/l20_extension1/contextual_prediction_run.py',
    'tests/test_contextual_prediction.py')
PINS = {
    ROOT/'runs'/SETTINGS/'COMPLETE.json': '41a9fa1d8d63bdcdfab971b5470ab614bf4d2b13cd3a73555a8f239130db51d4',
    ROOT/'logs'/(SETTINGS+'_saved_audit_v1.json'): 'eb5b76b5d456fe8054a16e3de4270152158bef8f7437cae58a9f8123cae5fab2',
    ROOT/'tmp'/(SETTINGS+'_freeze.json'): 'dea3c08f0de000ff827bd1d2dcc46dffab74952420a12beccb98c6bb712fed4a',
    ROOT/'runs'/PULSE/'COMPLETE.json': '97c1a81a18a6186f4dfc3ddb22eaff81a6f707275a78fb0732ab3c188937ccea',
    ROOT/'logs'/(PULSE+'_saved_audit_v1.json'): 'ac8b1b3d7841beb9744817b6b83742d5365765d9a6217fcf0fcfe9b673840815',
    ROOT/'tmp'/(PULSE+'_freeze.json'): 'd0e7e0a784d19c3a42da9325c3ce129f88e7592c2cb384c5186427ce1af1a66b',
    ROOT/'outputs'/PULSE/'DIAGNOSTICS_SEALED.json': '2b09b9426fa1d6ad5222194245e6b97c041a8237b5a6f103fe8a37d1f536aa5f',
}
ARTIFACTS = ('features.npz', 'predictions.npz', 'raw_predictions.npz', 'fits.json', 'summary.json', 'case_losses.npz', 'verification.json')


def freeze_path(): return ROOT/'tmp'/(RUN+'_freeze.json')
def timing_path(): return ROOT/'tmp'/(RUN+'_benchmark.json')
def output_dir(): return ROOT/'outputs'/RUN
def complete_path(): return ROOT/'runs'/RUN/'COMPLETE.json'
def audit_path(): return ROOT/'logs'/(RUN+'_saved_audit_v1.json')


def fixture_alias(root, path):
    """Inventory only: never consume a symlink as an experiment input/output."""
    assert root.parent == ROOT/'tmp' and root.name.startswith(RUN+'_qualification_v')
    assert path.is_symlink()
    target = path.resolve(strict=True)
    if path.name == 'alias.json':
        assert path.parent.name.startswith('test_external_and_hash_guards')
        assert target == path.parent/'record.json' and target.is_file()
    else:
        stem = path.name.removesuffix('current')
        assert path.name.endswith('current') and target.parent == path.parent.resolve()
        assert target.name.startswith(stem) and target.name[len(stem):].isdigit() and target.is_dir()


def artifacts():
    files = set()
    for area in ('tmp', 'logs', 'runs', 'outputs'):
        for path in (ROOT/area).glob(RUN+'*'):
            assert not path.is_symlink()
            if path.is_file(): files.add(path)
            else:
                for p in path.rglob('*'):
                    if p.is_symlink():
                        fixture_alias(path, p)
                    elif p.is_file(): files.add(p)
    return sorted(files)


def resources():
    io.resources(); files = artifacts(); size = sum(p.stat().st_size for p in files)
    assert size < io.ALLOWANCE, 'retain evidence; stop at allowance'
    return dict(retained_bytes=size, files=len(files), cap_bytes=io.ALLOWANCE, maximum_cpus=6, numerical_threads=1)


def npz(path, keys):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)) and all(k+'.npy' in names for k in keys)
        declared = {k+'.npy' for k in model.KEYS}
        assert all(p.endswith('.npy') and ('/' not in p or p in declared) and '\\' not in p for p in names)
    return io.load_npz(path, keys)


def source_inputs():
    io.verify_hashes(PINS)
    sf = io.read_json(ROOT/'tmp'/(SETTINGS+'_freeze.json'))['input_sha256']
    pf = io.read_json(ROOT/'tmp'/(PULSE+'_freeze.json'))['input_sha256']
    sd = io.read_json(ROOT/'runs'/SETTINGS/'COMPLETE.json')
    pd = io.read_json(ROOT/'runs'/PULSE/'COMPLETE.json')
    assert sd['status'] == 'COMPLETE'
    for name in (SETTINGS, PULSE): assert io.read_json(ROOT/'logs'/(name+'_saved_audit_v1.json'))['passes']
    seal = io.read_json(ROOT/'outputs'/PULSE/'DIAGNOSTICS_SEALED.json')
    assert seal['blocks'] == list(range(90000, 90016)) and seal['cases'] == 256 and not seal['actual_future_arrays_loaded']
    result = {str(p): h for p, h in PINS.items()}
    for filename in ('settings.npz', 'fits.json', 'predictions.npz', 'raw_predictions.npz'):
        p = ROOT/'outputs'/SETTINGS/filename; result[str(p)] = sd['output_sha256'][str(p)]
    for filename in ('fits.json', 'predictions.npz', 'raw_predictions.npz'):
        p = ROOT/'outputs'/PULSE/'panel'/filename; result[str(p)] = pd['output_sha256'][str(p)]
    p = ROOT/'outputs'/io.OLD157/'dataset.npz'; assert pf[str(p)] == sf[str(p)]; result[str(p)] = pf[str(p)]
    for index in range(90000, 90016):
        for ext in ('npz', 'json'):
            p = ROOT/'outputs'/PULSE/f'diagnostic_{index}.{ext}'
            result[str(p)] = seal['artifact_sha256'][str(p)]
            assert result[str(p)] == pd['output_sha256'][str(p)]
            p = ROOT/'outputs/l20_extension1_heldout_v1_attempt1'/f'diagnostic_{index}.{ext}'
            result[str(p)] = pf[str(p)]
    for rel in ('src/l20_extension1/settings_prediction.py', 'src/l20_extension1/settings_prediction_check.py',
                'src/l20_extension1/settings_prediction_run.py', 'src/l20_extension1/__init__.py'):
        p = WS/'L20-extension-1'/rel; result[str(p)] = sf[str(p)]
    for rel in ('src/laws_confirmation/io.py', 'src/laws_confirmation/__init__.py'):
        p = WS/rel; result[str(p)] = sf[str(p)]
    io.verify_hashes(result)
    return result


def qualification(xml):
    io.external(xml)
    assert xml.parent == ROOT/'logs' and xml.name.startswith(RUN+'_qualification_v') and xml.suffix == '.xml'
    root = ET.parse(xml).getroot(); tests = root.findall('.//testcase')
    assert len(tests) >= 35 and not any(root.findall('.//'+k) for k in ('failure', 'error', 'skipped'))
    names = {t.get('name').split('[', 1)[0] for t in tests}
    assert {'test_full_small_audit', 'test_founder_exclusion', 'test_double_tying', 'test_feature_boundary',
        'test_reference_identity', 'test_complete_report', 'test_time_gate'} <= names
    return len(tests)


def freeze(xml):
    resources(); count = qualification(xml); start = time.monotonic(); inputs = source_inputs()
    seconds = time.monotonic()-start
    paths = [WS/'L20-extension-1'/name for name in SCIENCE]+[xml]
    fixtures = ROOT/'tmp'/xml.stem
    assert fixtures.is_dir()
    paths += [p for p in artifacts() if fixtures in p.parents]
    result = dict(schema='d176_freeze_v1', frozen_utc=io.utc_now(), input_sha256=inputs,
        code_qualification_sha256=io.hashes(paths), tests=count, python=sys.version, numpy=np.__version__,
        source_hash_seconds=seconds, blocks=list(range(90000, 90016)), new_fits=192, reused_models=336,
        focal=['interaction/tied:pulse', 'interaction/tied:passive', .01], actual_arrays_loaded=False,
        prospective_evidence=False, automatic_successor=False)
    io.write_json(freeze_path(), result); return result


def frozen():
    f = io.read_json(freeze_path())
    io.verify_hashes(f['input_sha256']); io.verify_hashes(f['code_qualification_sha256'])
    assert f['python'] == sys.version and f['numpy'] == np.__version__
    assert f['blocks'] == list(range(90000, 90016))
    return f


def development_data():
    d = npz(ROOT/'outputs'/io.OLD157/'dataset.npz', ('start', 'endpoint', 'futures', 'block_ids'))
    assert d['block_ids'].tolist() == list(range(90000, 90016))
    q = npz(ROOT/'outputs'/SETTINGS/'settings.npz', ('q', 'block_ids'))
    np.testing.assert_array_equal(q['block_ids'], d['block_ids'])
    pulses, shifts = [], []
    for b, index in enumerate(d['block_ids'].tolist()):
        original = ROOT/'outputs/l20_extension1_heldout_v1_attempt1'/f'diagnostic_{index}'
        old = npz(original.with_suffix('.npz'), ('shift', 'diagnostic_features'))
        om = io.read_json(original.with_suffix('.json'))
        new = ROOT/'outputs'/PULSE/f'diagnostic_{index}'
        packet = npz(new.with_suffix('.npz'), ('shift', 'starting_features', 'diagnostic_features'))
        nm = io.read_json(new.with_suffix('.json'))
        assert om['index'] == nm['index'] == index and nm['cohort'] == 'development'
        for life in range(4):
            a, c = om['lives'][life], nm['lives'][life]
            assert a['life'] == c['life'] == life and a['index'] == c['index'] == index
            assert a['cases'] == c['cases'] == io.CASES
            assert a['branches'] == ['U0', 'U1', 'C1'] and c['branches'] == ['U1', 'P1']
            assert not a['diagnostic_to_lineage'] and not c['diagnostic_to_lineage']
        np.testing.assert_allclose(packet['starting_features'], d['start'][b], atol=1e-12, rtol=0)
        np.testing.assert_array_equal(old['diagnostic_features'], d['endpoint'][b])
        np.testing.assert_array_equal(packet['diagnostic_features'][..., 0, :], d['endpoint'][b, ..., 1, :])
        np.testing.assert_array_equal(packet['shift'][..., 0, :], old['shift'][..., 1, :])
        np.testing.assert_array_equal(packet['shift'][..., 1, :], old['shift'][..., 1, :])
        shifts.append(old['shift'][..., :2, :]); pulses.append(packet['diagnostic_features'][..., 1, :])
    shifts = np.stack(shifts)
    np.testing.assert_array_equal(q['q'], model.prior.effective_q(shifts))
    np.testing.assert_array_equal(q['q'], check.legacy.rolled_q(shifts))
    data = dict(start=d['start'], u0=d['endpoint'][..., 0, :], u1=d['endpoint'][..., 1, :],
        pulse=np.stack(pulses), q=q['q'], futures=d['futures'], block_ids=d['block_ids'])
    model.validate(data, development=True)
    return data


def references():
    p, r, fits = {}, {}, {}
    for version, folder, names in (('old', ROOT/'outputs'/PULSE/'panel', model.OBSERVERS),
                                   ('settings', ROOT/'outputs'/SETTINGS, model.OBSERVERS[:3])):
        rp, rr = npz(folder/'predictions.npz', names), npz(folder/'raw_predictions.npz', names)
        records = io.read_json(folder/'fits.json')
        for name in names: p[version+'/'+name], r[version+'/'+name], fits[version+'/'+name] = rp[name], rr[name], records[name]
    assert set(p) == set(r) == set(fits) == set(model.REFERENCES)
    return p, r, fits


def check_panel(directory, data, references):
    rp, rr, rf = references
    p, r, fits = dict(rp), dict(rr), dict(rf)
    newp = npz(directory/'predictions.npz', model.NEW); newr = npz(directory/'raw_predictions.npz', model.NEW)
    newf = io.read_json(directory/'fits.json'); assert set(newf) == set(model.NEW)
    p.update(newp); r.update(newr); fits.update(newf)
    saved = npz(directory/'features.npz', model.NEW)
    expected = model.panels({k: data[k] for k in model.MEASUREMENTS})
    for k in model.NEW: np.testing.assert_array_equal(saved[k], expected[k])
    report, losses = io.read_json(directory/'summary.json'), npz(directory/'case_losses.npz', model.KEYS)
    return dict(passes=True, models=check.fits(data, p, r, fits, rp, rr, rf),
        scores=check.report(data, p, r, report, losses), reference_models_reused=336 if len(data['start']) == 16 else len(data['start'])*21)


def save_panel(directory, data, references):
    io.external(directory); directory.mkdir(parents=True, exist_ok=False)
    p, r, fits = model.fit_new(data, *references)
    summary, losses = model.report(data, p, r)
    x = model.panels({k: data[k] for k in model.MEASUREMENTS})
    io.write_npz(directory/'features.npz', {k: x[k] for k in model.NEW})
    io.write_npz(directory/'predictions.npz', {k: p[k] for k in model.NEW})
    io.write_npz(directory/'raw_predictions.npz', {k: r[k] for k in model.NEW})
    io.write_json(directory/'fits.json', {k: fits[k] for k in model.NEW})
    io.write_json(directory/'summary.json', summary); io.write_npz(directory/'case_losses.npz', losses)
    proof = check_panel(directory, data, references); io.write_json(directory/'verification.json', proof)
    return proof


def benchmark():
    f = frozen(); resources(); start = time.monotonic()
    data = model.fixture(); refs = model.synthetic_references(data)
    folder = ROOT/'tmp'/(RUN+'_benchmark')
    proof = save_panel(folder, data, refs)
    # A second complete saved-model check is included in the measured budget.
    check.same(check_panel(folder, data, refs), proof)
    elapsed = time.monotonic()-start
    result = dict(passes=True, seconds=elapsed, attached_bound_seconds=4*elapsed+4*f['source_hash_seconds']+60,
        freeze_sha256=io.sha256_file(freeze_path()), synthetic_only=True, real_arrays_loaded=False,
        verification=proof, benchmark_bytes=io.size(folder), resources=resources(), automatic_successor=False)
    io.write_json(timing_path(), result); return result


def time_gate(frozen_sha):
    b = io.read_json(timing_path())
    assert b['passes'] and b['freeze_sha256'] == frozen_sha
    assert b['attached_bound_seconds'] <= 600, 'detached execution required; do not start attached'
    assert resources()['retained_bytes']+2*b['benchmark_bytes']+32*1024**2 < io.ALLOWANCE, 'storage gate'
    return b


def execute():
    f = frozen(); time_gate(io.sha256_file(freeze_path()))
    assert not complete_path().exists() and not audit_path().exists()
    start = time.monotonic(); data = development_data(); refs = references()
    proof = save_panel(output_dir(), data, refs)
    io.verify_hashes(f['input_sha256'])
    result = dict(status='COMPLETE', completed_utc=io.utc_now(), seconds=time.monotonic()-start,
        freeze_sha256=io.sha256_file(freeze_path()), input_sha256=f['input_sha256'],
        output_sha256=io.hashes([output_dir()/k for k in ARTIFACTS]), output_bytes=io.size(output_dir()),
        verification=proof, new_fits=192, reused_models=336, new_dynamics=0,
        prospective_evidence=False, automatic_successor=False)
    io.write_json(complete_path(), result); return result


def audit():
    frozen(); time_gate(io.sha256_file(freeze_path()))
    done = io.read_json(complete_path()); assert done['status'] == 'COMPLETE'
    assert done['freeze_sha256'] == io.sha256_file(freeze_path())
    io.verify_hashes(done['output_sha256'])
    start = time.monotonic(); data = development_data(); refs = references()
    proof = check_panel(output_dir(), data, refs); check.same(proof, done['verification'])
    result = dict(passes=True, completed_utc=io.utc_now(), seconds=time.monotonic()-start,
        complete_sha256=io.sha256_file(complete_path()), freeze_sha256=io.sha256_file(freeze_path()),
        verification=proof, new_fits=0, new_dynamics=0, automatic_successor=False, resources=resources())
    io.write_json(audit_path(), result); return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('freeze', 'benchmark', 'execute', 'audit'))
    parser.add_argument('--xml', type=Path)
    args = parser.parse_args()
    log = ROOT/'logs'/(RUN+'_'+args.stage+'.log'); io.external(log).parent.mkdir(parents=True, exist_ok=True)
    with log.open('x') as stream:
        try:
            result = freeze(args.xml) if args.stage == 'freeze' else globals()[args.stage]()
            import json
            stream.write(json.dumps(result, sort_keys=True, indent=2)+'\n'); stream.flush()
            print(json.dumps({k: v for k, v in result.items() if k not in ('input_sha256', 'code_qualification_sha256', 'output_sha256')}, sort_keys=True))
        except Exception:
            traceback.print_exc(file=stream); stream.flush(); raise


if __name__ == '__main__': main()
