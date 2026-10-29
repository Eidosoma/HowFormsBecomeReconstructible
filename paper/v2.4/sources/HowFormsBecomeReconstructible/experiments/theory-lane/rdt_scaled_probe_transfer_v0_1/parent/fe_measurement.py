"""Five fixed predictors from the qualified 128-read shared measurement."""
import hashlib
import numpy as np
from ff_common import C, P, ev, read, require, ledger
from ec_common import MODELS, probability_scalar, probability_matrix
from ec_probe import measure, independent_scores


def verify_joint(records):
    require(set(records) == {'successor32', 'direct64'}, 'Both complete measurements required')
    s, sr = records['successor32']
    d, dr = records['direct64']
    for name, (raw, receipt) in records.items():
        n = 32 if name == 'successor32' else 64
        require(receipt['mode'] == name and receipt['native_reads'] == 64 and receipt['flat_native_reads'] == 2,
                'Equal standalone budgets required')
        require(raw['probes'].tolist() == list(range(n)), 'Probe coverage differs')
        require(receipt['namespace'] == P['forcing']['namespace'] and receipt['stage'] == C['stage'], 'Wrong declared measurement stream')
        require(all(receipt[k] == sr[k] for k in ('key', 'rule', 'regime', 'stage', 'namespace', 'boundary')), 'Mismatched case identities')
        require(np.array_equal(raw['packet'], s['packet']), 'Original packet changed')
        require(receipt['audits'] == ([dict(probe=0, byte_exact=True, native_reads=2)] if name == 'successor32' else
                [dict(probe=i, byte_exact=True, native_reads=1) for i in (0, 32)]), 'Wrong separate dynamics schedule')
        for branch in (('writer', 'successor') if name == 'successor32' else ('direct',)):
            require(raw[branch + '_windows'].shape == (n, 32, 1, 2, 2), 'Wrong native response shape')
            a, y = independent_scores(raw[branch + '_windows'], receipt['rule'])
            require(np.max(abs(a - raw[branch + '_aligned'])) < 1e-12 and np.array_equal(y, raw[branch + '_passed']), 'Independent endpoints differ')
        branch = 'successor' if name == 'successor32' else 'direct'
        q = float(raw[branch + '_passed'].mean())
        require(q == receipt['q'] and abs(probability_scalar([*receipt['boundary'], q], MODELS[name]) - receipt['probability']) < 1e-12,
                'Frozen probability differs')
    a = [x for x in sr['forcing'] if x['branch'] == 'successor']
    b = dr['forcing'][:32]
    require(len(sr['forcing']) == len(dr['forcing']) == 64 and len(a) == 32 and
            [f['probe'] for f in dr['forcing']] == list(range(64)) and
            [f['sha256'] for f in a] == [f['sha256'] for f in b], 'Shared evaluation forcing differs')
    writer = {f['sha256']['noise'] for f in sr['forcing'] if f['branch'] == 'writer'}
    direct = {f['sha256']['noise'] for f in dr['forcing']}
    require(len(writer) == 32 and len(direct) == 64 and writer.isdisjoint(direct), 'Independent draw reused')
    for key in ('mask', 'birth'):
        require(np.array_equal(s['successor_' + key], d['direct_' + key][:32]), 'Shared environment arrays differ')
    qs = dict(successor32=sr['q'], direct64=dr['q'],
        pooled32=(int(s['writer_passed'].sum()) + int(d['direct_passed'][:32].sum())) / 64,
        direct8=float(d['direct_passed'][:8].mean()), tt008=None)
    probabilities = {}
    for name, q in qs.items():
        features = sr['boundary'] + ([] if name == 'tt008' else [q])
        scalar = probability_scalar(features, MODELS[name])
        matrix = float(probability_matrix(np.array([features]), MODELS[name])[0])
        require(abs(scalar - matrix) < 1e-12, 'Independent five-model arithmetic differs')
        probabilities[name] = matrix
    return dict(status='PASS', primary_native_reads=128, flat_native_reads=4,
        distinct_base_environments=96, shared_evaluation_draws=32, fractions=qs, probabilities=probabilities,
        numerical_checks_only=True, scientific_future_outcomes=0)


def create(folder, row, packet, regime, guard, packet_index):
    order = ['successor32', 'direct64']
    if (packet_index + ('matched', 'independent').index(regime)) % 2:
        order.reverse()
    records = {name: measure(packet, row['rule'], row['key'], regime, name,
        row['boundary'], folder / name, guard, stage=C['stage']) for name in order}
    checked = verify_joint(records)
    prediction = dict(**row, regime=regime, fractions=checked['fractions'], probabilities=checked['probabilities'])
    ledger.atomic_json(folder / 'FORECAST.json', prediction)
    ledger.atomic_json(folder / 'VERIFICATION.json', checked)
    ledger.atomic_json(folder / 'ORDER.json', dict(order=order, packet_index=packet_index))
    require(check_saved(folder, row, regime) == prediction, 'Saved forecast differs')
    return prediction


def check_saved(folder, row, regime):
    records = {}
    for name in ('successor32', 'direct64'):
        receipt = read(folder / (name + '.json'))
        raw = ev.load(folder / (name + '.npz'), receipt['raw_sha256'])
        require(receipt['key'] == row['key'] and receipt['rule'] == row['rule'] and
                receipt['boundary'] == row['boundary'] and receipt['regime'] == regime,
                'Measurement differs from the enrolled task, packet or boundary')
        require(hashlib.sha256(raw['packet'].tobytes()).hexdigest() == row['packet_sha256'] and
                np.array_equal(raw['boundary'], np.asarray(row['boundary'])), 'Wrong original packet or raw boundary')
        records[name] = raw, receipt
    checked = verify_joint(records)
    expected = dict(**row, regime=regime, fractions=checked['fractions'], probabilities=checked['probabilities'])
    require(read(folder / 'FORECAST.json') == expected, 'Saved five-model forecast changed')
    require(read(folder / 'VERIFICATION.json') == checked, 'Saved measurement verification changed')
    return expected

