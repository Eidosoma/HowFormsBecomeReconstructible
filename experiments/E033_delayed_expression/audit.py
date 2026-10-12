"""Independent terminal replay and statistics; no production model imports."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import sys
import time
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, dump, sha, utc
from E015_functional_inheritance.audit import verify, random, EXPECTED
from E031_renewal_durability.audit import load_compact, replay_assay
import numpy as np

TIMINGS = ('original', 'delayed_same_duration', 'extra_time', 'delayed_extra_time')
RECEIVERS = ('fixed_four', 'local_strength')
HORIZONS = (8, 16)
ARMS = ('own', 'foreign', 'shuffled', 'erased', 'untrained', 'communication_off', 'source_cut')
DAMAGE = ('intact', 'scattered', 'square')
PANELS = tuple((h, t, r) for h in HORIZONS for t in TIMINGS for r in RECEIVERS)
PAIRS = (('delayed_same_duration', 'original'), ('extra_time', 'original'), ('delayed_extra_time', 'original'),
         ('delayed_extra_time', 'extra_time'), ('delayed_extra_time', 'delayed_same_duration'))


def load(path):
    with np.load(path, allow_pickle=False) as h: return {k:h[k] for k in h.files}


def schedules(cycle, factor):
    s, t = cycle['settling_steps'], cycle['read_steps']
    return [dict(cycle, settling_steps=a, read_steps=b) for a, b in ((s, t), (s*factor, t), (s, t+(factor-1)*s), (s*factor, t+(factor-1)*s))]


def inspect(task):
    run, source, block, cfg, cycle, factor = task
    cs, ms, vs = [], [], []
    for h in HORIZONS:
        record = load(source/f'boundary_{block:06d}_g{h}.npz')['outgoing'][0]
        old = load_compact(source/f'assay_{block:06d}_h{h}.npz', 'assay')
        for i, timing in enumerate(schedules(cycle, factor)):
            raw = load_compact(run/f'assay_{block:06d}_h{h}_t{i}.npz', 'assay')
            c, m, v = replay_assay(raw, record[None], block, h, cfg, timing)
            if i == 0:
                np.testing.assert_array_equal(v, old['mean_ports'][[0, 10]])
                for k in ('masks', 'permutations'): np.testing.assert_array_equal(raw[k], old[k])
            cs.append(c); ms.append(m); vs.append(v)
    actual = dict(correct=np.concatenate(cs), margin=np.concatenate(ms), ports=np.concatenate(vs))
    retained = load(run/f'cases_{block:06d}.npz')
    assert set(retained) == set(actual)
    for k in actual: np.testing.assert_array_equal(actual[k], retained[k])
    return actual


def audit(run, workers=8):
    started = time.monotonic(); cap_cpus(8)
    manifest = verify(run); contract = manifest['contract']; s = json.loads((run/'summary.json').read_text())
    cfg, cycle, ids, factor = (contract[k] for k in ('config', 'cycle', 'blocks', 'factor'))
    technical = contract['mode'] != 'scientific'; source = ROOT/contract['source']
    src = verify(source)['contract']
    assert cfg == src['config'] and cycle == src['cycle'] and ids == src['blocks']
    assert ids == ([900031] if technical else list(range(27000, 27032)))
    assert factor == (2 if contract['mode'] == 'fixture' else 4)
    if contract['mode'] == 'scientific':
        assert cfg == EXPECTED and cycle == dict(read_steps=2048, settling_steps=256, write_steps=128, generations=16)
    assert contract['panels'] == s['panels'] == [list(p) for p in PANELS]
    assert s['schedules'] == dict(zip(TIMINGS, schedules(cycle, factor)))
    assert s['cfg'] == cfg and s['base_cycle'] == cycle and s['blocks'] == ids
    assert s['prior_cases_reused'] and not s['packets_changed'] and not s['renewal_policy_changed']
    with ProcessPoolExecutor(max_workers=min(workers, len(ids))) as pool:
        cases = list(pool.map(inspect, [(run, source, b, cfg, cycle, factor) for b in ids]))
    correct = np.stack([x['correct'] for x in cases]); margin = np.stack([x['margin'] for x in cases])
    arrays = dict(accuracy=correct.mean(axis=(2, 3, 4)), both_cues=correct.all(axis=4).mean(axis=(2, 3)), margin=margin.mean(axis=(2, 3, 4)))
    draw = random('E033', 'bootstrap', 'delayed_expression').integers(0, len(ids), (10000, len(ids)))
    def check(values, st):
        np.testing.assert_array_equal(values, st['block_means'])
        assert float(values.mean()) == st['mean']
        np.testing.assert_array_equal(np.quantile(values[draw].mean(axis=1), [.025, .975]), st['ci95'])
    for p, (h, timing, receiver) in enumerate(PANELS):
        group = s['groups'][str(h)][receiver][timing]; gates = {}
        for d, injury in enumerate(DAMAGE):
            for a, arm in enumerate(ARMS):
                for metric, values in arrays.items(): check(values[:, p, d, a], group[metric][injury][arm])
                if a:
                    st = group['own_minus_control'][injury][arm]
                    check(arrays['accuracy'][:, p, d, 0]-arrays['accuracy'][:, p, d, a], st)
                    gates[f'advantage_{injury}_{arm}'] = st['ci95'][0] > .10
            for f, rule in enumerate((1, -1)):
                values = correct[:, p][:, [f, f+2]][:, :, :, :, d, 0].mean(axis=(1, 2, 3))
                st = group['own_accuracy_by_rule'][str(rule)][injury]; check(values, st)
                gates[f'accuracy_rule_{rule}_{injury}'] = st['ci95'][0] > .75
        assert group['gates'] == gates and group['all_original_gates_pass'] == all(gates.values())
    for h in HORIZONS:
        for receiver in RECEIVERS:
            for high, low in PAIRS:
                a, b = (PANELS.index((h, t, receiver)) for t in (high, low))
                st = s['contrasts'][str(h)][receiver][high+'_minus_'+low]
                for metric, values in arrays.items():
                    for d, injury in enumerate(DAMAGE): check(values[:, a, d, 0]-values[:, b, d, 0], st[metric][injury])
    hi, lo = PANELS.index((16, 'delayed_extra_time', 'local_strength')), PANELS.index((16, 'extra_time', 'local_strength'))
    check(arrays['both_cues'][:, hi, 1, 0]-arrays['both_cues'][:, lo, 1, 0], s['primary']['statistics'])
    assert s['primary']['margin'] == .10
    passed = s['primary']['statistics']['ci95'][0] > .10
    assert s['primary']['lower_above_010'] == (None if technical else passed)
    assert s['status'] == ('TECHNICAL_ONLY' if technical else 'DELAYED_EXPRESSION_BENEFIT_ESTABLISHED' if passed else 'DELAYED_EXPRESSION_BENEFIT_NOT_ESTABLISHED')
    absolute = s['groups']['16']['local_strength']['delayed_extra_time']['both_cues']['scattered']['own']['ci95'][0] > .75
    assert s['absolute_h16_delayed_extra_time_reliability_lower_above_075'] == (None if technical else absolute)
    assert s['individual_observations'] == correct.size == len(ids)*16*4*cfg['recipients']*2*3*7
    assert s['lineages'] == len(ids)*4*cfg['recipients'] and s['original_schedules_match_e031']
    verify(run); verify(source)
    result = dict(status='PASS', utc=utc(), seconds=time.monotonic()-started, blocks=len(ids),
        individual_observations=int(correct.size), all_receiver_updates_and_array_commitments_replayed=True,
        all_cases_scores_statistics_and_gates_verified=True, original_endpoints_match_e031_exactly=True,
        source_packets_unchanged=True, focal_time_matched_contrast_verified=True,
        complete_sha256=sha(run/'COMPLETE.json'), audit_code_sha256=sha(__file__), workers=workers)
    p = run/'INDEPENDENT_AUDIT.json'; assert not p.exists(); dump(p, result)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('run', type=Path); p.add_argument('--workers', type=int, default=8)
    a = p.parse_args(); assert 1 <= a.workers <= 8; audit(a.run.resolve(), a.workers)
