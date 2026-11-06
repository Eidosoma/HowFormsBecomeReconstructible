"""Review retained TT048 evidence without generating new receiving futures."""
from pathlib import Path
import math
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import *
import analysis  # Used only to check that the retained report matches its table.


def error_of_mean(values):
    x = np.asarray(values, dtype=float)
    n = x.shape[-1]
    assert n == 4
    return np.sqrt(sum((x[..., i] - x[..., j]) ** 2
                       for i in range(n) for j in range(i)) / (n * n * (n - 1)))


def compare(actual, expected):
    assert set(actual) == set(expected), (set(actual) - set(expected), set(expected) - set(actual))
    for name, value in expected.items():
        if np.issubdtype(np.asarray(value).dtype, np.inexact):
            near(actual[name], value, name)
        else:
            exact(actual[name], value, name)


def block_check(folder):
    p = arrays(folder / 'PREPARED.npz')
    saved = arrays(folder / 'AGGREGATE.npz')
    endpoints = arrays(folder / 'ENDPOINTS.npz')
    reconstructed = {name: np.empty_like(value) for name, value in endpoints.items()}
    max_error = 0.
    for ri, regime in enumerate(REGIMES):
        raw = arrays(folder / (regime + '.npz'))
        proof = read(folder / (regime + '.json'))
        assert proof['status'] == 'PASS' and proof['contexts'] == 384
        window = raw['port_windows'][0]
        mean = np.empty(window.shape[1:])
        for ix in np.ndindex(mean.shape):
            mean[ix] = math.fsum(float(window[(t,) + ix]) for t in range(32)) / 32
        near(raw['mean_ports'][0], mean, regime + ' retained windows')
        max_error = max(max_error, float(np.max(abs(raw['mean_ports'][0] - mean))))
        task = np.repeat([1, -1, 1, -1], 4)[:, None, None, None, None]
        signed = mean * task * np.array([[1., -1.], [-1., 1.]])
        for endpoint, values in [('intended', signed), ('opposite', -signed)]:
            margin = values.min(axis=(-1, -2))
            flags = margin > .25
            near(raw[endpoint + '_margin'][0], margin)
            exact(raw[endpoint + '_pass'][0], flags)
            reconstructed[endpoint + '_margin'][ri] = margin
            reconstructed[endpoint + '_pass'][ri] = flags
        assert not np.any(reconstructed['intended_pass'][ri] & reconstructed['opposite_pass'][ri])
        exact(p['packets'][ri, :, 0], p['inputs'][ri], 'preservation packet')
        for arm, proposal in ((4, 2), (5, 3)):
            for case in range(16):
                eligible = p['eligible'][ri, case, arm]
                expected = p['packets'][ri, case, proposal] if eligible else p['inputs'][ri, case]
                exact(p['packets'][ri, case, arm], expected, 'selective packet')
                action = 0 if not eligible else 1 if np.array_equal(expected, p['inputs'][ri, case]) else 2
                assert int(p['actions'][ri, case, arm]) == action
    compare(endpoints, reconstructed)
    decisions = read(folder / 'DECISIONS.json')
    assert len(decisions) == 128
    assert all(d['historical_status'] == 'UNVERIFIED' for row in decisions for d in row['decisions'])
    expected = {k: np.zeros_like(v) for k, v in saved.items()}
    expected['futures'][...] = 4
    expected['local_mc_se_defined'][...] = True
    for endpoint in ('intended', 'opposite'):
        x = reconstructed[endpoint + '_pass'].astype(int)
        delta = np.stack([x[:, :, j] - x[:, :, i] for i, j in PAIRS], axis=2)
        expected[endpoint + '_local_mean'] = x.sum(-1) / 4
        expected[endpoint + '_local_mc_se'] = error_of_mean(x)
        expected[endpoint + '_local_effect_mean'] = delta.sum(-1) / 4
        expected[endpoint + '_local_effect_mc_se'] = error_of_mean(delta)
    for gi, group in enumerate(GROUPS):
        ids = [c for c in range(16) if group == 'all'
               or group == ('initial_pass' if p['initial_pass'][c] else 'initial_fail')
               or group == 'history:' + str(int(p['history']))]
        count = len(ids)
        expected['records'][gi] = count
        if not count:
            continue
        for ri in range(8):
            for ai in range(6):
                eligible = p['eligible'][ri, ids, ai]
                expected['eligible_counts'][gi, ri, ai] = sum(eligible)
                expected['action_counts'][gi, ri, ai] = np.bincount(p['actions'][ri, ids, ai], minlength=3)
            for endpoint in ('intended', 'opposite'):
                x = reconstructed[endpoint + '_pass'][ri, ids].astype(int)
                levels = x.sum(0) / count
                expected[endpoint + '_counts'][gi, ri] = x.sum((0, 2))
                expected[endpoint + '_conditional_counts'][gi, ri] = (x * p['eligible'][ri, ids, :, None]).sum((0, 2))
                expected[endpoint + '_future_levels'][gi, ri] = levels
                expected[endpoint + '_margin_means'][gi, ri] = reconstructed[endpoint + '_margin'][ri, ids].sum((0, 2)) / (count * 4)
                for k, (i, j) in enumerate(PAIRS):
                    expected[endpoint + '_paired_table'][gi, ri, k] = np.bincount((2 * x[:, i] + x[:, j]).ravel(), minlength=4).reshape(2, 2)
                    differences = x[:, j] - x[:, i]
                    expected[endpoint + '_record_signs'][gi, ri, k] = np.bincount(np.sign(differences.sum(-1)) + 1, minlength=3)
                    expected[endpoint + '_effect_mc_se'][gi, ri, k] = error_of_mean(differences.sum(0) / count)
    compare(saved, expected)
    return expected, max_error


def global_check(items, saved):
    expected = {'block_' + k: np.stack([b[k] for b in items]) for k in items[0]}
    weights = expected['block_records']
    records = weights.sum(0)
    present = weights > 0
    blocks = present.sum(0)
    expected.update(group_records=records, group_blocks=blocks)
    totals = ['eligible_counts', 'action_counts']
    for endpoint in ('intended', 'opposite'):
        totals += [endpoint + suffix for suffix in ('_counts', '_conditional_counts', '_paired_table', '_record_signs')]
    for k in totals:
        expected['sum_' + k] = expected['block_' + k].sum(0)
    for endpoint in ('intended', 'opposite'):
        counts = expected['block_' + endpoint + '_counts']
        rates = counts / np.maximum(weights, 1)[:, :, None, None] / 4
        equal_rates = rates.sum(0) / blocks[:, None, None]
        expected['block_' + endpoint + '_rates'] = rates
        expected['equal_' + endpoint + '_rates'] = equal_rates
        expected['pooled_' + endpoint + '_rates'] = counts.sum(0) / records[:, None, None] / 4
        expected[endpoint + '_eligible_rates'] = expected['sum_' + endpoint + '_conditional_counts'] / np.maximum(expected['sum_eligible_counts'], 1) / 4
        expected['equal_' + endpoint + '_effects'] = np.stack([equal_rates[:, :, j] - equal_rates[:, :, i] for i, j in PAIRS], -1)
        variances = expected['block_' + endpoint + '_effect_mc_se'] ** 2
        expected['equal_' + endpoint + '_effect_mc_se'] = np.sqrt((variances * present[:, :, None, None]).sum(0)) / blocks[:, None, None]
        expected['pooled_' + endpoint + '_effect_mc_se'] = np.sqrt((variances * weights[:, :, None, None] ** 2).sum(0)) / records[:, None, None]
        expected['equal_' + endpoint + '_margin_means'] = expected['block_' + endpoint + '_margin_means'].sum(0) / blocks[:, None, None]
    expected['eligible_rate_defined'] = expected['sum_eligible_counts'] > 0
    expected['eligible_coverage'] = expected['sum_eligible_counts'] / records[:, None, None]
    expected['action_coverage'] = expected['sum_action_counts'] / records[:, None, None, None]
    compare(saved, expected)


def main():
    tick = time.monotonic()
    run = ROOT / 'runs/one_read_v1'
    destination = ROOT / 'completion_review_v1'
    destination.mkdir(exist_ok=False)
    evidence = [run / 'COMPLETE.json', ROOT / 'runs/qualification_v1/COMPLETE.json',
                ROOT / 'FREEZE.json', ROOT / 'QUEUE_COMPLETE.json', ROOT / 'checks/preflight_v2/COMPLETE.json']
    complete, qualification, frozen, queue, preflight = [read(p) for p in evidence]
    assert complete['status'] == qualification['status'] == 'COMPLETE'
    assert qualification['serial_parallel_bitwise_equal']
    assert complete['blocks'] == list(BLOCKS) and complete['new_source_population'] is False
    assert complete['inputs'] == qualification['inputs'] == preflight['inputs'] == frozen['inputs'] == inputs()
    assert queue['complete_sha256'] == sha(run / 'COMPLETE.json')
    for files in (complete['outputs'], qualification['outputs'], preflight['outputs'], frozen['evidence'], read(ROOT / 'SOURCE_MANIFEST.json')['source_files']):
        verify(files)
    items = []
    errors = []
    for index in BLOCKS:
        sub = run / f'block_{index}'
        receipt = read(sub / 'COMPLETE.json')
        assert receipt['status'] == 'COMPLETE' and receipt['futures'] == 4
        verify(receipt['outputs'])
        verify(read(sub / 'USED_INPUTS.json'))
        item, error = block_check(sub)
        items.append(item)
        errors.append(error)
    summary = arrays(run / 'SUMMARY.npz')
    global_check(items, summary)
    assert (run / 'REPORT.md').read_text() == analysis.report(summary)
    receipt = dict(status='PASS',reviewed_utc=now(),seconds=time.monotonic()-tick,
        evidence={str(p): sha(p) for p in evidence},review_script_sha256=sha(Path(__file__)),
        frozen_input_files=len(frozen['inputs']),production_output_files=len(complete['outputs']),
        qualification_output_files=len(qualification['outputs']),blocks=8,records=128,
        contexts=24576,scalar_port_window_means=98304,maximum_scalar_mean_error=max(errors),
        independently_reduced_block_arrays=len(items[0])*8,independently_reduced_global_arrays=len(summary),
        all_15_paired_contrasts_checked=True,all_strata_and_empty_denominators_checked=True,
        paired_conditional_mc_errors_checked=True,abstention_packet_and_action_identity_checked=True,
        historical_status_always_unverified=True,new_physical_futures_generated=False,
        native_dynamics_replay='Performed during production; retained proofs and hashes checked here',
        qualification_serial_parallel_check='PASS; production flag false means this qualification-only comparison is not repeated',
        population_confirmation=False,automatic_successor=False)
    write(destination / 'REVIEW.json', receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k != 'evidence'}, sort_keys=True))


if __name__ == '__main__':
    main()
