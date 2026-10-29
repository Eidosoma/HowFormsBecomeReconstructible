"""Separate scalar scoring checks on retained evidence; no predictor/runner imports."""
import importlib.util
import math
import statistics
from pathlib import Path

import numpy as np
from scipy.stats import t

from independent_arithmetic import load, probability, read, sha


def measurement(folder, row, forecast, config, models):
    folder = Path(folder); raw = load(folder/'probe.npz'); receipt = read(folder/'probe.json')
    if sha(folder/'probe.npz') != receipt['raw_sha256'] or receipt['native_reads'] != 72 or receipt['flat_native_reads'] != 3:
        raise ArithmeticError('Measurement accounting or raw hash changed')
    if raw['probes'].tolist() != list(range(32)) or raw['direct_probes'].tolist() != list(range(8)):
        raise ArithmeticError('Measurement probe budget changed')
    import hashlib
    if hashlib.sha256(raw['packet'].tobytes()).hexdigest() != row['packet_sha256']:
        raise ArithmeticError('Measurement is not of the enrolled packet')
    nframes = config['observe_steps']; counts = {}
    maximum_error = 0.
    for branch, count in [('writer', 32), ('successor', 32), ('direct', 8)]:
        windows = raw[branch+'_windows']
        if windows.shape != (count, nframes, 1, 2, 2):
            raise ArithmeticError('Wrong saved native window shape')
        means = np.array([math.fsum(v)/nframes for v in windows.transpose(0,2,3,4,1).reshape(-1,nframes)]).reshape(count,1,2,2)
        aligned = means*row['rule']*np.array([[1.,-1.],[-1.,1.]])
        maximum_error = max(maximum_error, float(np.max(abs(aligned-raw[branch+'_aligned']))))
        passed = (aligned.min(axis=(-1,-2)) > .25).astype(np.uint8)
        if maximum_error > 1e-12 or not np.array_equal(passed, raw[branch+'_passed']):
            raise ArithmeticError('Native task decision differs under independent mean calculation')
        counts[branch] = int(passed.sum())
    q, direct = counts['successor']/32, counts['direct']/8
    if forecast['q_rewrite'] != q or forecast['q_direct'] != direct:
        raise ArithmeticError('Forecast count feature changed')
    for name, extra in [('candidate', q), ('direct_rival', direct), ('tt008', None)]:
        p = probability(row['boundary'], extra, models[name])
        if abs(p-forecast['probabilities'][name]) > 1e-12:
            raise ArithmeticError('Frozen probability differs from separate scalar implementation')
    return dict(status='PASS', maximum_window_error=maximum_error, independently_checked_models=3)


def continuation(folder, rows, outcomes, config, seal_sha256, expected_audit_key):
    folder = Path(folder); raw = load(folder/'future.npz'); receipt = read(folder/'future.json')
    if sha(folder/'future.npz') != receipt['raw_sha256'] or receipt['forecast_seal_sha256'] != seal_sha256:
        raise ArithmeticError('Future does not bind its raw evidence and forecast seal')
    if (receipt['keys'] != [r['key'] for r in rows] or len(outcomes) != len(rows)
        or receipt['regime'] not in ('matched', 'independent')
        or any(r['regime'] != receipt['regime'] for r in outcomes)):
        raise ArithmeticError('Future record identities or regimes differ')
    if raw['generations'].tolist() != list(range(15,34)) or raw['incoming'].shape[0:3] != (19,len(rows),1):
        raise ArithmeticError('Wrong full continuation horizon or shape')
    if raw['windows'].shape != (19,len(rows),config['observe_steps'],1,2,2):
        raise ArithmeticError('Wrong terminal response evidence shape')
    for a, b in [(raw['incoming'][0,:,0],raw['initial_packets']),
                 (raw['incoming'][1:],raw['outgoing'][:-1]),
                 (raw['g32_packets'],raw['incoming'][-1]),
                 (raw['g32_packets'],raw['outgoing'][-2])]:
        if a.shape != b.shape or a.dtype != b.dtype or a.tobytes() != b.tobytes():
            raise ArithmeticError('Saved full rewrite chain is broken')
    import hashlib
    for j, row in enumerate(rows):
        if hashlib.sha256(raw['initial_packets'][j].tobytes()).hexdigest() != row['packet_sha256']:
            raise ArithmeticError('Future starts from the wrong boundary packet')
        windows = raw['windows'][-1,j,:,0]
        frames = config['observe_steps']
        means = np.array([math.fsum(windows[:,c,p])/frames for c in range(2) for p in range(2)]).reshape(2,2)
        aligned = means*row['rule']*np.array([[1.,-1.],[-1.,1.]])
        if np.max(abs(aligned-raw['terminal_aligned'][j])) > 1e-12:
            raise ArithmeticError('Independent terminal window mean differs')
        y = int(aligned.min() > .25)
        if y != int(raw['terminal_passed'][j]) or y != outcomes[j]['passed'] or outcomes[j]['key'] != row['key']:
            raise ArithmeticError('Saved native terminal outcome differs')
    audited = any(r['key'] == expected_audit_key for r in rows)
    expected = [dict(key=expected_audit_key,generation=g,byte_exact=True) for g in range(15,34)] if audited else []
    if receipt['audits'] != expected or receipt['flat_native_reads'] != 19*int(audited) or receipt['native_reads'] != 19*len(rows):
        raise ArithmeticError('Continuation audit schedule or cost differs')
    return dict(status='PASS', terminal_records=len(rows), flat_native_reads=receipt['flat_native_reads'])


def boundary(inputs, folder, rows, synthetic=False):
    inputs, folder = Path(inputs), Path(folder)
    raw = load(folder/'boundary.npz'); histories = read(inputs/'protocol.json')['acquisition']['histories']
    spec = importlib.util.spec_from_file_location('separate_transfer_audit',inputs/'inherited/audit.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    for row in rows:
        h = histories.index(row['history']); packet = raw['outgoing'][h,row['founder'],row['recipient']]
        weights = np.frombuffer(packet.tobytes(),dtype='<f8').reshape(2,16,16)
        import hashlib
        if hashlib.sha256(weights.tobytes()).hexdigest() != row['packet_sha256']:
            raise ArithmeticError('Enrollment packet hash differs')
        aligned = raw['mean_ports'][h,row['founder'],row['recipient']]*row['rule']*np.array([[1.,-1.],[-1.,1.]])
        signed, unsigned = module.transfer(weights,row['rule'])
        values = [*aligned.ravel(),float(aligned.min()),float(aligned.min()>.25),float(unsigned),
                  *[float(h==j) for j in (1,2,3)],float(signed)]
        if not np.allclose(values,row['boundary'],rtol=0,atol=1e-12) or row['current_pass'] != int(aligned.min()>.25):
            raise ArithmeticError('Saved eleven-feature boundary differs')
    return dict(status='PASS', records=len(rows), synthetic=synthetic)


def analysis(forecasts, outcomes, result, blocks):
    labels = {(tuple(r['key']),r['regime']):r['passed'] for r in outcomes}
    checked = 0
    decisions = []
    for regime in ('matched','independent'):
        rows = [r for r in forecasts if r['regime']==regime]
        for rival, margin in [('tt008',.002),('direct_rival',0.)]:
            values = []
            for block in blocks:
                terms = []
                for row in rows:
                    if row['block'] != block:continue
                    y = labels[(tuple(row['key']),regime)]
                    terms.append((row['probabilities'][rival]-y)**2-(row['probabilities']['candidate']-y)**2)
                if not terms:raise ArithmeticError('Missing inference block')
                values.append(math.fsum(terms)/len(terms))
            mean = statistics.mean(values); sd = statistics.stdev(values)
            radius = float(t.ppf(.975,len(values)-1))*sd/math.sqrt(len(values))
            lower, upper = mean-radius, mean+radius
            decision = 'SUPPORTED' if lower>margin else 'REJECTED' if upper<=margin else 'UNRESOLVED'
            row = result['regimes'][regime]['primary'][rival]
            for name, value in [('mean_gain',mean),('sample_sd',sd),('lower',lower),('upper',upper)]:
                if abs(row[name]-value)>1e-12:raise ArithmeticError('Independent block inference mismatch')
            if row['decision']!=decision or row['blocks']!=len(blocks):
                raise ArithmeticError('Independent inference decision mismatch')
            decisions.append(decision)
            checked += 1
    decision = ('ALL_FOUR_ADVANTAGES_SUPPORTED' if all(v == 'SUPPORTED' for v in decisions)
                else 'AT_LEAST_ONE_ADVANTAGE_REJECTED' if 'REJECTED' in decisions else 'UNRESOLVED')
    if result['decision'] != decision:
        raise ArithmeticError('Independent joint inference decision mismatch')
    return dict(status='PASS', independently_reduced_primary_comparisons=checked)
