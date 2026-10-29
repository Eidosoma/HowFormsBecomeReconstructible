"""Bind the already exposed study; read original evidence without modifying it."""
import hashlib
from pathlib import Path
import shutil

import numpy as np

from ec_common import ROOT, MODELS, ev, read, ledger, require, probability_scalar
from ec_probe import independent_scores

D = read(ROOT / 'DEVELOPMENT.json')
ANCHORS = dict(
    complete='7236b48882f41cae4547a518a150682e027c06befb51b7db3ae8554368b82615',
    outputs='5a3d1fff7aaf104962ab3422ed21e8a47d5b3a8626307c23148bc176ce4de320',
    inputs='7245c5041241c3a7e43e4bf65d4d4ff462695239e5f78146dbbfc8698a960fa6',
    audit='f3f53a4099adf5d3d56162b9a2ba987ac8e849fd45b93a63d5eae37d63139867')


def prepare():
    study = ROOT.parent / 'rdt_fresh_forecast_v0_1'
    run, inputs = study / 'runs/scientific_v1', study / 'jobs/qualification_v3/inputs'
    paths = {
        'FRESH_COMPLETE.json': run / 'COMPLETE.json',
        'FRESH_OUTPUTS.json': run / 'OUTPUTS.json',
        'FRESH_INPUTS.json': inputs / 'INPUTS.json',
        'FRESH_PROTOCOL.json': inputs / 'protocol.json',
        'FRESH_COHORT.json': run / 'selection/COHORT.json',
        'FRESH_SEAL.json': run / 'forecast_seal/FORECAST_SEAL.json',
        'FRESH_OUTCOMES.json': run / 'OUTCOMES.json',
        'FRESH_ANALYSIS.json': run / 'ANALYSIS.json',
        'FRESH_AUDIT.json': study / 'checks/SCIENTIFIC_V1_COMPLETED_EVIDENCE_AUDIT.json',
        'EQUAL_BENCHMARK_COMPLETE.json': ROOT / 'runs/benchmark_v1/COMPLETE.json',
        'EQUAL_BENCHMARK_RESULTS.json': ROOT / 'runs/benchmark_v1/RESULTS.json',
        'EQUAL_BENCHMARK_CLOSEOUT.json': ROOT / 'checks/BENCHMARK_V1_CLOSEOUT.json',
    }
    require(not (ROOT / 'DEV_SOURCE.json').exists(), 'Never replace a bound source')
    for key, name in [('complete', 'FRESH_COMPLETE.json'), ('outputs', 'FRESH_OUTPUTS.json'),
                      ('inputs', 'FRESH_INPUTS.json'), ('audit', 'FRESH_AUDIT.json')]:
        require(ev.sha(paths[name]) == ANCHORS[key], 'Source anchor changed: ' + key)
    output_hashes = read(paths['FRESH_OUTPUTS.json'])['sha256']
    input_hashes = read(paths['FRESH_INPUTS.json'])['sha256']
    bindings = {}
    for name, path in paths.items():
        digest = ev.sha(path)
        if path.is_relative_to(run) and path.name not in ('COMPLETE.json', 'OUTPUTS.json'):
            require(output_hashes[str(path.relative_to(run))] == digest, 'Unbound historical output')
        if path == inputs / 'protocol.json':
            require(input_hashes['protocol.json'] == digest, 'Unbound historical protocol')
        target = ROOT / 'context' / name
        require(not target.exists(), 'Never overwrite context')
        shutil.copyfile(path, target)
        require(ev.sha(target) == digest, 'Source copy differs')
        bindings[name] = dict(path=str(path), sha256=digest)
    for name, digest in read(ROOT / 'NATIVE_PROVENANCE.json')['sha256'].items():
        require(input_hashes['native/' + name] == digest, 'Native equations differ from source study')
    ledger.atomic_json(ROOT / 'DEV_SOURCE.json', dict(utc=ev.utc(), source_run=str(run),
        anchors=ANCHORS, context=bindings,
        exposure='All108 selected blocks, all864 original forecasts and all3456 outcomes were inspected before this comparator design. Development only.',
        evidence_scope='Use the completed full audit as provenance for saved outcomes; recheck hashes of all files consumed here. Do not claim a new full continuation replay.'))
    return verify_metadata()


def verify_metadata():
    bindings = read(ROOT / 'DEV_SOURCE.json')
    require(bindings['anchors'] == ANCHORS, 'Source anchors changed')
    for name, item in bindings['context'].items():
        require(ev.sha(ROOT / 'context' / name) == item['sha256'], 'Changed copied source: ' + name)
    audit = read(ROOT / 'context/FRESH_AUDIT.json')
    require(audit['status'] == 'PASS' and audit['complete_sha256'] == ANCHORS['complete'] and
            audit['output_manifest_sha256'] == ANCHORS['outputs'] and audit['verified_terminal_outcomes'] == 3456,
            'Completed source qualification required')
    done = read(ROOT / 'context/FRESH_COMPLETE.json')
    require(done['status'] == 'COMPLETE' and done['output_manifest_sha256'] == ANCHORS['outputs'] and
            done['input_manifest_sha256'] == ANCHORS['inputs'], 'Source completion differs')
    protocol = read(ROOT / 'context/FRESH_PROTOCOL.json')
    require(protocol['namespace'] + '/probe' == D['namespace'] and protocol['stage'] == D['stage'] and
            protocol['repeats'] == D['repeats'], 'Scientific forcing identity differs')
    cohort, seal = read(ROOT / 'context/FRESH_COHORT.json'), read(ROOT / 'context/FRESH_SEAL.json')
    require(cohort['complete'] and cohort['blocks'] == seal['blocks'] == list(range(D['blocks'])) and
            cohort['rows'] == seal['rows'] and len(cohort['rows']) == D['packets'], 'Whole original cohort required')
    require(len({tuple(r['key']) for r in cohort['rows']}) == D['packets'], 'Duplicate source packet')
    for b in cohort['blocks']:
        for c in (0, 1):
            require(sum(r['block'] == b and r['current_pass'] == c for r in cohort['rows']) == 2, 'Original balanced cohort changed')
    expected = {(tuple(r['key']), g) for r in cohort['rows'] for g in D['regimes']}
    require(len(seal['forecasts']) == D['cases'] and {(tuple(f['key']), f['regime']) for f in seal['forecasts']} == expected,
            'Complete unique original forecasts required')
    ys = read(ROOT / 'context/FRESH_OUTCOMES.json')
    require(len(ys) == 3456 and {(tuple(y['key']), y['regime'], y['replicate']) for y in ys} ==
            {(k, g, r) for k, g in expected for r in D['repeats']} and all(y['passed'] in (0, 1) for y in ys),
            'Complete four-repeat source outcomes required')
    original = read(ROOT / 'context/CURRENT_FROZEN_MODELS.json')
    for name, old in D['cached_names'].items():
        require(MODELS[name] == original[old], 'Changed original predictor')
    return dict(status='PASS', blocks=D['blocks'], packets=D['packets'], original_forecasts=D['cases'], saved_outcomes=len(ys))


def cases():
    rows = read(ROOT / 'context/FRESH_COHORT.json')['rows']
    result = []
    for b in range(D['blocks']):
        for i, row in enumerate(r for r in rows if r['block'] == b):
            for regime in D['regimes']:
                result.append(dict(index=len(result), row=row, regime=regime,
                    path=f'units/measure/b{b}/case_{i:02d}_{regime}'))
    return result


class Source:
    def __init__(self):
        self.bindings = read(ROOT / 'DEV_SOURCE.json')
        self.root = Path(self.bindings['source_run'])
        self.hashes = read(ROOT / 'context/FRESH_OUTPUTS.json')['sha256']
        self.forecasts = {(tuple(f['key']), f['regime']): f for f in read(ROOT / 'context/FRESH_SEAL.json')['forecasts']}

    def path(self, relative):
        path = ledger.child(self.root, relative)
        require(not path.is_symlink() and relative in self.hashes and ev.sha(path) == self.hashes[relative], 'Historical evidence changed: ' + relative)
        return path

    def case(self, item):
        row, regime = item['row'], item['regime']
        base = item['path']
        receipt = read(self.path(base + '/probe.json'))
        forecast = read(self.path(base + '/FORECAST.json'))
        raw = ev.load(self.path(base + '/probe.npz'), receipt['raw_sha256'])
        require(forecast == self.forecasts[(tuple(row['key']), regime)] and all(forecast.get(k) == v for k, v in row.items()), 'Source forecast identity differs')
        require(receipt['key'] == row['key'] and receipt['rule'] == row['rule'] and receipt['regime'] == regime and
                receipt['stage'] == D['stage'] and receipt['native_reads'] == 72 and receipt['flat_native_reads'] == 3, 'Source probe identity or budget differs')
        require(raw['probes'].tolist() == list(range(32)) and raw['direct_probes'].tolist() == list(range(8)), 'Source prefix coverage differs')
        require(hashlib.sha256(raw['packet'].tobytes()).hexdigest() == row['packet_sha256'], 'Wrong enrolled packet')
        for branch, count in [('writer', 32), ('successor', 32), ('direct', 8)]:
            require(raw[branch + '_windows'].shape == (count, 32, 1, 2, 2), 'Wrong source response shape')
            aligned, passed = independent_scores(raw[branch + '_windows'], row['rule'])
            require(np.max(abs(aligned - raw[branch + '_aligned'])) < 1e-12 and
                    np.array_equal(passed, raw[branch + '_passed']), 'Changed source endpoint')
        extras = dict(successor32=float(raw['successor_passed'].mean()), direct8=float(raw['direct_passed'].mean()), tt008=None)
        require(forecast['q_rewrite'] == extras['successor32'] and forecast['q_direct'] == extras['direct8'], 'Source fractions differ')
        for name, old in D['cached_names'].items():
            features = row['boundary'] + ([] if name == 'tt008' else [extras[name]])
            require(abs(probability_scalar(features, MODELS[name]) - forecast['probabilities'][old]) < 1e-12, 'Source scalar forecast differs')
        return raw, receipt, forecast
