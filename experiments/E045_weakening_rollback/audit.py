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
from E015_functional_inheritance.audit import verify, random, EXPECTED, pack, unpack
from E031_renewal_durability.audit import load_compact, replay_assay
import numpy as np

VARIANTS = ('original', 'targeted_rollback', 'random_rollback')
RECEIVERS = ('fixed_four', 'local_strength')
HORIZONS = (24, 32)
ARMS = ('own', 'foreign', 'shuffled', 'erased', 'untrained', 'communication_off', 'source_cut')
DAMAGE = ('intact', 'scattered', 'square')
PANELS = tuple((h, t, r) for h in HORIZONS for r in RECEIVERS for t in VARIANTS)
PAIRS = (('targeted_rollback', 'original'), ('random_rollback', 'original'), ('targeted_rollback', 'random_rollback'))
FIELDS = ('target_edges', 'pool_edges', 'random_edges', 'overlap_edges',
          'target_sign_restores', 'random_sign_restores', 'target_absolute_gain', 'random_absolute_gain')


def load(path):
    with np.load(path, allow_pickle=False) as h: return {k:h[k] for k in h.files}


def reconstruct(incoming, outgoing, dead, block, horizon):
    """Independent coordinate-wise selection, using no production imports."""
    old, new = unpack(incoming), unpack(outgoing)
    assert old.shape == new.shape and dead.shape == old.shape[:2]+(16, 16)
    available = np.zeros_like(old, dtype=bool)
    target = np.zeros_like(available); pool = target.copy(); selected = target.copy()
    orders = np.empty(old.shape[:2]+(512,), dtype=np.int64)
    modified = np.stack((new.copy(), new.copy(), new.copy()))
    for f in range(4):
        for r in range(old.shape[1]):
            for direction in range(2):
                for y in range(16):
                    for x in range(16):
                        next_y, next_x = ((y, (x+1) % 16) if direction == 0 else ((y+1) % 16, x))
                        key = (f, r, direction, y, x)
                        available[key] = not (dead[f, r, y, x] or dead[f, r, next_y, next_x])
                        if not available[key]:
                            assert new[key] == 0.
                        elif abs(old[key]) > .5:
                            pool[key] = old[key] != new[key]
                            target[key] = abs(new[key]) <= .5
            order = random('E045', block, 'rollback', horizon, f, r).permutation(512)
            orders[f, r] = order
            eligible = [int(i) for i in order if pool[f, r].flat[i]]
            need = int(target[f, r].sum())
            assert need <= len(eligible)
            for i in eligible[:need]: selected[f, r].flat[i] = True
            for mask, variant in ((target, 1), (selected, 2)):
                for i in np.flatnonzero(mask[f, r]):
                    modified[variant, f, r].flat[i] = old[f, r].flat[i]
            assert int(selected[f, r].sum()) == need
    changed_sign = np.sign(old) != np.sign(new)
    gain = np.abs(old)-np.abs(new)
    counts = np.stack([a.sum(axis=(-3, -2, -1)) for a in
        (target, pool, selected, target & selected, target & changed_sign, selected & changed_sign)]
        + [(gain*a).sum(axis=(-3, -2, -1)) for a in (target, selected)], axis=-1)
    packets = pack(modified)
    np.testing.assert_array_equal(packets[0], outgoing)
    return dict(incoming=incoming, outgoing=outgoing, renewal_mask=dead, available=available,
        target=target, pool=pool, selected=selected, permutations=orders, packets=packets, counts=counts)


def inspect(task):
    run, source, block, cfg, cycle = task
    cs, ms, vs = [], [], []
    intervention_counts = {}
    for h in HORIZONS:
        incoming = load(source/f'boundary_{block:06d}_g{h-1}.npz')['outgoing'][3]
        boundary = load(source/f'boundary_{block:06d}_g{h}.npz')
        actual = reconstruct(incoming, boundary['outgoing'][3], boundary['renewal_mask'], block, h)
        saved = load(run/f'intervention_{block:06d}_h{h}.npz')
        assert set(saved) == set(actual)
        for k in actual: np.testing.assert_array_equal(saved[k], actual[k], err_msg=k)
        intervention_counts[h] = actual['counts']
        old = load_compact(source/f'assay_{block:06d}_h{h}.npz', 'assay')
        raw = load_compact(run/f'assay_{block:06d}_h{h}.npz', 'assay')
        c, m, v = replay_assay(raw, actual['packets'], block, h, cfg, cycle)
        np.testing.assert_array_equal(v[[0, 3]], old['mean_ports'][[3, 14]])
        for k in ('masks', 'permutations'): np.testing.assert_array_equal(raw[k], old[k])
        cs.append(c); ms.append(m); vs.append(v)
    actual = dict(correct=np.concatenate(cs), margin=np.concatenate(ms), ports=np.concatenate(vs))
    retained = load(run/f'cases_{block:06d}.npz')
    assert set(retained) == set(actual)
    for k in actual: np.testing.assert_array_equal(actual[k], retained[k])
    actual['selection'] = intervention_counts
    return actual


def audit(run, workers=8):
    started = time.monotonic(); cap_cpus(8)
    manifest = verify(run); contract = manifest['contract']; s = json.loads((run/'summary.json').read_text())
    cfg, cycle, ids = (contract[k] for k in ('config', 'cycle', 'blocks'))
    technical = contract['mode'] != 'scientific'; source = ROOT/contract['source']
    index = json.loads((HERE/'SOURCE_DATA.json').read_text())
    assert contract['source'] == index[dict(fixture='fixture_run', benchmark='benchmark_run', scientific='source_run')[contract['mode']]]
    src = verify(source)['contract']
    assert src['experiment'] == 'E041' and src['mode'] == contract['mode']
    assert cfg == src['config'] and cycle == dict(src['cycle'], settling_steps=4*src['cycle']['settling_steps']) and ids == src['blocks']
    assert ids == ([900041] if technical else list(range(32000, 32032)))
    assert 2*cycle['settling_steps'] == cycle['read_steps'] and cycle['generations'] == 32
    assert contract['source_policy'] == s['source_policy'] == 'bridge_rewrite'
    assert contract['source_policy_index'] == s['source_policy_index'] == 3
    for h in HORIZONS:
        names = [p[1] for p in src['panels'] if p[0] == h and p[2] == 'fixed_four']
        assert len(names) == 11 and names[3] == 'bridge_rewrite'
    if contract['mode'] == 'scientific':
        assert cfg == EXPECTED and cycle == dict(read_steps=2048, settling_steps=1024, write_steps=128, generations=32)
    assert contract['panels'] == s['panels'] == [list(p) for p in PANELS]
    assert contract['variants'] == s['variants'] == list(VARIANTS)
    assert s['cfg'] == cfg and s['cycle'] == cycle and s['blocks'] == ids
    assert s['prior_cases_reused'] and s['packets_changed'] and not s['renewal_policy_changed']
    assert s['experiment'] == 'E045' and s['mode'] == contract['mode']
    assert s['arms'] == list(ARMS) and s['damage'] == list(DAMAGE)
    assert s['variants'] == list(VARIANTS) and s['receivers'] == list(RECEIVERS)
    with ProcessPoolExecutor(max_workers=min(workers, len(ids))) as pool:
        cases = list(pool.map(inspect, [(run, source, b, cfg, cycle) for b in ids]))
    correct = np.stack([x['correct'] for x in cases]); margin = np.stack([x['margin'] for x in cases])
    arrays = dict(accuracy=correct.mean(axis=(2, 3, 4)), both_cues=correct.all(axis=4).mean(axis=(2, 3)), margin=margin.mean(axis=(2, 3, 4)))
    draw = random('E045', 'bootstrap', 'weakening_rollback').integers(0, len(ids), (10000, len(ids)))
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
                for d, injury in enumerate(DAMAGE):
                    previous = correct[:, b, :, :, :, d, 0].all(axis=3)
                    changed = correct[:, a, :, :, :, d, 0].all(axis=3)
                    count = s['transitions'][str(h)][receiver][high+'_minus_'+low][injury]
                    combinations = dict(both_fail=~previous & ~changed, rescued=~previous & changed,
                        lost=previous & ~changed, both_succeed=previous & changed)
                    assert count['total'] == previous.size
                    for name, selected in combinations.items():
                        np.testing.assert_array_equal(selected.sum(axis=(1, 2)), count['by_block'][name])
                        assert int(selected.sum()) == count['counts'][name]
                    assert sum(count['counts'].values()) == previous.size
    assert s['selection_fields'] == list(FIELDS) and s['selection_uses_terminal_outcomes'] is False
    for h in HORIZONS:
        counts = np.stack([case['selection'][h] for case in cases])
        st = s['selection'][str(h)]
        for j, field in enumerate(FIELDS):
            check(counts[..., j].mean(axis=(1, 2)), st['mean_per_lineage'][field])
            if j < 6: assert st['totals'][field] == int(counts[..., j].sum())
        assert st['affected_lineages'] == int((counts[..., 0] > 0).sum())
        assert st['lineages'] == len(ids)*4*cfg['recipients']
    hi = PANELS.index((32, 'targeted_rollback', 'local_strength'))
    assert set(s['primary']['comparisons']) == {'original', 'random_rollback'}
    passes = []
    for low, threshold in (('original', .05), ('random_rollback', 0.)):
        lo = PANELS.index((32, low, 'local_strength'))
        contrast = s['primary']['comparisons'][low]
        check(arrays['both_cues'][:, hi, 1, 0]-arrays['both_cues'][:, lo, 1, 0], contrast['statistics'])
        assert contrast['margin'] == threshold
        decision = contrast['statistics']['ci95'][0] > threshold
        assert contrast['lower_above_margin'] == (None if technical else decision)
        passes.append(decision)
    assert s['primary']['endpoint'] == 'h32 scattered normalized own-record both-cue success: targeted rollback'
    passed = all(passes)
    assert s['primary']['joint_pass'] == (None if technical else passed)
    assert s['status'] == ('TECHNICAL_ONLY' if technical else 'TARGETED_ROLLBACK_BENEFIT_ESTABLISHED' if passed else 'TARGETED_ROLLBACK_BENEFIT_NOT_ESTABLISHED')
    absolute = s['groups']['32']['local_strength']['targeted_rollback']['both_cues']['scattered']['own']['ci95'][0] > .75
    assert s['absolute_h32_targeted_reliability_lower_above_075'] == (None if technical else absolute)
    assert s['individual_observations'] == correct.size == len(ids)*12*4*cfg['recipients']*2*3*7
    assert s['lineages'] == len(ids)*4*cfg['recipients'] and s['original_endpoints_match_e041']
    verify(run); verify(source)
    for rel, digest in json.loads((HERE/'SOURCE_DATA.json').read_text())['sha256'].items(): assert sha(ROOT/rel) == digest
    result = dict(status='PASS', utc=utc(), seconds=time.monotonic()-started, blocks=len(ids),
        individual_observations=int(correct.size), all_receiver_updates_and_array_commitments_replayed=True,
        all_cases_scores_statistics_and_gates_verified=True, original_endpoints_match_e041_exactly=True,
        source_packets_unchanged=True, all_intervention_coordinates_and_counts_verified=True, joint_primary_verified=True, all_paired_rescue_and_loss_counts_verified=True,
        complete_sha256=sha(run/'COMPLETE.json'), audit_code_sha256=sha(__file__), workers=workers)
    p = run/'INDEPENDENT_AUDIT.json'; assert not p.exists(); dump(p, result)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('run', type=Path); p.add_argument('--workers', type=int, default=8)
    a = p.parse_args(); assert 1 <= a.workers <= 8; audit(a.run.resolve(), a.workers)
