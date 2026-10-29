#!/usr/bin/env python3
"""Correct pooled interval axes and report saved autonomous trajectories; no policies run."""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
            'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[key] = '1'
import sys
sys.dont_write_bytecode = True
import copy
import json
import math
from pathlib import Path
from time import perf_counter
import numpy as np
import run_fep_autonomous_reversal as C

ATTEMPT = C.ROOT/'attempt-01'
OUTPUT = C.ROOT/'reporting-2026-10-17'
CHECKS = {}


def check(name, ok):
    if not bool(ok):
        raise AssertionError(name)
    CHECKS[name] = CHECKS.get(name, 0)+1


def close(name, left, right, atol=3e-12):
    check(name, np.shape(left) == np.shape(right) and np.allclose(left, right, atol=atol, rtol=0))


def interval(x):
    check('interval_base_block_matrix', x.ndim == 2 and x.shape[1] > 1)
    b, n = x.shape
    mean = float(x.mean())
    se = float(np.sqrt(x.var(axis=1, ddof=1).sum()/(b*b*n)))
    return dict(mean=mean, mc_se=se, lower95=mean-1.96*se, upper95=mean+1.96*se)


def reference_interval(rows):
    """Python lists, explicit strata and independent two-pass variance."""
    nb, n = len(rows), len(rows[0])
    means = [math.fsum(map(float, row))/n for row in rows]
    variance = math.fsum(math.fsum((float(v)-mu)**2 for v in row)/(n-1)
                         for row, mu in zip(rows, means))/(nb*nb*n)
    mean, se = math.fsum(means)/nb, math.sqrt(variance)
    return dict(mean=mean, mc_se=se, lower95=mean-1.96*se, upper95=mean+1.96*se)


def verify_interval(saved, rows):
    expected = reference_interval(rows)
    check('interval_fields', set(saved) == set(expected))
    for key in expected:
        close('scalar_interval_'+key, saved[key], expected[key])


def cost_values(counts, selected, segment):
    # Selecting the segment FIRST avoids NumPy moving separated advanced axes.
    c = np.take(np.take(counts, segment, axis=4), selected, axis=2)
    b, n = counts.shape[:2]
    check('selected_count_axes', c.shape == (b, n, len(selected), 2, 3))
    check('selected_exposure_positive', np.all(c[..., 0] > 0))
    x = ((10*c[..., 1]+c[..., 2])/(10*c[..., 0])).mean(axis=2)
    check('averaged_cost_axes', x.shape == (b, n, 2))
    return x


def reference_values(counts, selected, segment):
    b, n = counts.shape[:2]
    return [[[math.fsum((int(counts[bi, i, j, a, segment, 1])+
                         int(counts[bi, i, j, a, segment, 2])/10)/
                        int(counts[bi, i, j, a, segment, 0]) for j in selected)/len(selected)
              for a in range(2)] for i in range(n)] for bi in range(b)]


def panel(x, reference):
    close('explicit_base_block_condition_loop', x, reference)
    r = np.array(reference)
    out = dict(arms={}, against_always={})
    for a, arm in enumerate(C.ARMS):
        out['arms'][arm] = interval(x[..., a])
        verify_interval(out['arms'][arm], r[..., a].tolist())
        out['against_always'][arm] = interval(x[..., a]-.1)
        verify_interval(out['against_always'][arm], (r[..., a]-.1).tolist())
    out['structured_minus_anytime'] = interval(x[..., 1]-x[..., 0])
    verify_interval(out['structured_minus_anytime'], (r[..., 1]-r[..., 0]).tolist())
    return out


def check_equal_panel(left, right):
    for a in C.ARMS:
        for group in ('arms', 'against_always'):
            for key in left[group][a]:
                close('condition_interval_unchanged', left[group][a][key], right[group][a][key])
    for key in left['structured_minus_anytime']:
        close('condition_paired_interval_unchanged', left['structured_minus_anytime'][key], right['structured_minus_anytime'][key])


def qualify_axes():
    # Deliberately unequal axes and nonidentical blocks expose the original bug.
    fixture = np.zeros((3, 5, 4, 2, 2, 3), dtype=np.int64)
    for b in range(3):
        for n in range(5):
            for j in range(4):
                for a in range(2):
                    fixture[b, n, j, a, :, :] = [100, b+n+j+a*(n % 2), 7+j+a]
    selected = [1, 3]
    x = cost_values(fixture, selected, 0)
    panel(x, reference_values(fixture, selected, 0))
    permuted = cost_values(fixture[:, [4, 1, 3, 0, 2]], selected, 0)
    close('within_base_block_permutation_interval', list(interval(x[..., 1]).values()), list(interval(permuted[..., 1]).values()))
    rates = (10*fixture[..., 1]+fixture[..., 2])/(10*fixture[..., 0])
    bad = rates[:, :, selected, :, 0].mean(axis=2)
    check('original_indexing_shape_detected', bad.shape == (2, 3, 2) and bad.shape != x.shape)
    check('original_indexing_variance_detected', abs(interval(bad[..., 1])['mc_se']-interval(x[..., 1])['mc_se']) > 1e-6)
    close('analytic_variance', interval(np.array([[0., 1., 2.], [2., 4., 6.]]))['mc_se'], math.sqrt(5/12))


def summarize_components(data, selected, original_diagnostics):
    out = {}
    counts = np.take(data['counts'], selected, axis=2)
    sums = np.take(data['sums'], selected, axis=2)
    for segment, name in enumerate(('episode', 'post_change')):
        if not np.all(counts[..., segment, 0] > 0):
            continue
        out[name] = {}
        for a, arm in enumerate(C.ARMS):
            c = counts[..., a, segment, :]
            errors = (c[..., 1]/c[..., 0]).mean(axis=2)
            paid = (c[..., 2]/(10*c[..., 0])).mean(axis=2)
            rate = cost_values(data['counts'], selected, segment)[..., a]
            close('error_and_purchase_cost_closure', errors+paid, rate)
            vtotal = rate.var(axis=1, ddof=1)
            covariance = ((errors-errors.mean(axis=1)[:, None])*(paid-paid.mean(axis=1)[:, None])).sum(axis=1)/(errors.shape[1]-1)
            close('cost_variance_component_closure', vtotal, errors.var(axis=1, ddof=1)+paid.var(axis=1, ddof=1)+2*covariance)
            out[name][arm] = dict(error_cost=interval(errors), purchase_cost=interval(paid),
                                  error_count_total=int(c[..., 1].sum()), purchase_count_total=int(c[..., 2].sum()),
                                  exposure_total=int(c[..., 0].sum()), purchases_per_episode=float(c[..., 2].mean()))
            for k, metric in enumerate(C.SUMS):
                value = (sums[..., a, segment, k]/c[..., 0]).mean(axis=2)
                verify_interval(original_diagnostics[arm][name][metric], value.tolist())
    return out


def reversal_phases(data):
    selected = C.panels()['reverse']
    counts = np.take(data['phase_counts'], selected, axis=2)
    sums = np.take(data['phase_sums'], selected, axis=2)
    lengths = (101-C.TAU[selected])[None, None, :]
    out = {}
    for a, arm in enumerate(C.ARMS):
        out[arm] = {}
        for phase, name in enumerate(('before_first', 'at_first', 'after_first')):
            c = counts[..., a, phase, :]
            cost = ((10*c[..., 1]+c[..., 2])/(10*lengths)).mean(axis=2)
            excess = ((10*c[..., 1]+c[..., 2]-c[..., 0])/(10*lengths)).mean(axis=2)
            exposure = (c[..., 0]/lengths).mean(axis=2)
            conditional = (sums[..., a, phase, 0]/lengths).mean(axis=2)
            floor = (sums[..., a, phase, 1]/lengths).mean(axis=2)
            out[arm][name] = dict(exposure_fraction=interval(exposure), realized_cost_contribution=interval(cost),
                                  realized_excess_over_always=interval(excess),
                                  conditional_excess_over_known_law=interval(conditional-floor),
                                  pooled_exposure=int(c[..., 0].sum()), pooled_wrong=int(c[..., 1].sum()),
                                  pooled_purchases=int(c[..., 2].sum()))
            if phase == 1:
                check('first_purchase_matches_always_exactly', np.all(excess == 0))
        actual = cost_values(data['counts'], selected, 1)[..., a]
        close('phase_realized_mean_closure', sum(out[arm][ph]['realized_cost_contribution']['mean'] for ph in out[arm]), actual.mean())
        close('phase_excess_mean_closure', sum(out[arm][ph]['realized_excess_over_always']['mean'] for ph in out[arm]), (actual-.1).mean())
    return out


def predictive_diagnostics(pop):
    """Descriptive reviewer-requested examination of saved beliefs; no inference replay."""
    selected = C.panels()['reverse']
    totals = np.zeros((2, 3, 6), dtype=float)
    for meta in pop:
        q = np.array([float(C.F(v)) for v in meta['laws'][3]])
        for first in range(0, C.BLOCKS, C.CHUNK):
            name = f'{meta["label"]}_{first:04d}_{first+C.CHUNK-1:04d}.npz'
            with np.load(ATTEMPT/'blocks'/name, allow_pickle=False) as saved:
                y = np.take(saved['warnings'], selected, axis=1)
                u = np.take(saved['subjective_u'], selected, axis=1)
                actions = np.take(saved['actions'], selected, axis=1)
                labels = np.take(saved['labels'], selected, axis=1)
                first_paid = np.take(saved['first'], selected, axis=1)
                saved_sums = np.take(saved['phase_sums'], selected, axis=1)
                true_p1 = (q[y ^ 3]/(q[y]+q[y ^ 3]))[:, :, None, :]
                prediction = np.where((y[:, :, None, :] >> 1) != 0, 1-u, u)
                answer = (y[:, :, None, :] >> 1) ^ (u > .5)
                map_risk = np.where(answer == 0, true_p1, 1-true_p1)
                best = np.minimum(true_p1, 1-true_p1)
                direction_regret = map_risk-best
                paid = actions == 2
                check('unaided_actions_follow_saved_beliefs', np.all(paid | (actions == answer)))
                check('purchase_mask_preserved', np.array_equal(labels >= 0, paid))
                post = (C.TIMES[None, :] >= C.TAU[selected, None])[None, :, None, :]
                masks = (post & (C.TIMES < first_paid[..., None]),
                         post & (C.TIMES == first_paid[..., None]),
                         post & (C.TIMES > first_paid[..., None]))
                for phase, mask in enumerate(masks):
                    close('saved_wrong_direction_reproduced',
                          (direction_regret*mask*~paid).sum(axis=-1), saved_sums[..., phase, 3])
                    for a in range(2):
                        take = mask[:, :, a]
                        diff = np.abs(prediction[:, :, a]-true_p1[:, :, 0])
                        regret = direction_regret[:, :, a]
                        totals[a, phase] += [int(take.sum()), float((diff*take).sum()),
                                             float((regret*take).sum()), int(((regret > 0) & take).sum()),
                                             int((paid[:, :, a] & take & (regret == 0)).sum()),
                                             int((paid[:, :, a] & take & (regret > 0)).sum())]
    out = {}
    for a, arm in enumerate(C.ARMS):
        out[arm] = {}
        for ph, name in enumerate(('before_first', 'at_first', 'after_first')):
            n, mae, regret, wrong, correct_paid, wrong_paid = totals[a, ph]
            out[arm][name] = dict(exposure=int(n), probability_mae=mae/n,
                                  belief_direction_regret=regret/n, wrong_belief_direction_fraction=wrong/n,
                                  purchases_with_correct_direction=int(correct_paid), purchases_with_wrong_direction=int(wrong_paid))
    return dict(scope='Descriptive, post-launch reviewer clarification; all reversal traces, pooled within each endogenous phase; not primary-weighted or causal.', values=out)


def main():
    tick = perf_counter()
    C.resources()
    C.mount_check(ATTEMPT)
    check('fresh_reporting_directory', not OUTPUT.exists())
    check('expected_manifest', C.digest(ATTEMPT/'MANIFEST.json') == '92ae729ed63faa44a5296e7525357feb9ccbf83936334d04bcb03058e45324f5')
    check('expected_readback', C.digest(ATTEMPT/'READBACK.json') == '97160a67363acf2026184a0f1fc0992cf355644e6f321eac887fd8dfba99831e')
    frozen = C.check_inputs(ATTEMPT)
    manifest = json.loads((ATTEMPT/'MANIFEST.json').read_text())
    for name, expected in manifest['outputs'].items():
        check('preserved_output', C.digest(ATTEMPT/name) == expected)
    qualify_axes()
    pop = json.loads((ATTEMPT/'POPULATION.json').read_text())['bases']
    data = C.load_counts(ATTEMPT, pop)
    original = json.loads((ATTEMPT/'RESULTS.json').read_text())
    corrected = copy.deepcopy(original)
    components, changes = {}, []
    for name, selected in C.panels().items():
        components[name] = summarize_components(data, selected, original['diagnostics'][name])
        for seg, segment in enumerate(('episode', 'post_change')):
            if name == 'stable' and seg:
                continue
            values = cost_values(data['counts'], selected, seg)
            fixed = panel(values, reference_values(data['counts'], selected, seg))
            old = original['panels'][name][segment]
            for group in ('arms', 'against_always'):
                for arm in C.ARMS:
                    close('pooled_mean_preserved', old[group][arm]['mean'], fixed[group][arm]['mean'])
            close('paired_mean_preserved', old['structured_minus_anytime']['mean'], fixed['structured_minus_anytime']['mean'])
            corrected['panels'][name][segment] = fixed
            changes.append(dict(panel=name, segment=segment, old=old, corrected=fixed))
    conditions = []
    for bi, meta in enumerate(pop):
        for j, (family, onset) in enumerate(C.CONDITIONS):
            saved = original['conditions'][bi*25+j]
            row = copy.deepcopy(saved)
            count = data['counts'][bi:bi+1]
            for seg, name in enumerate(('episode', 'post_change')):
                if not j and seg:
                    continue
                computed = panel(cost_values(count, [j], seg), reference_values(count, [j], seg))
                check_equal_panel(saved[name], computed)
            old_floor = C.M.floor(meta['laws'][0])
            new_floor = old_floor if family == 'stable' else C.M.floor(meta['laws'][1+C.U.FAMILIES.index(family)])
            full_floor = ((onset-1)*old_floor+(101-onset)*new_floor)/100
            row['known_law_floor_exact'] = dict(episode=str(full_floor), post_change=None if not j else str(new_floor))
            row['zero_headroom_post_change'] = bool(j and new_floor == C.F(1, 10))
            conditions.append(row)
    corrected['criteria'] = {}
    for name in ('reverse', 'core'):
        p = corrected['panels'][name]['post_change']
        gates = dict(better_than_anytime=p['structured_minus_anytime']['upper95'] < 0,
                     below_always=p['against_always'][C.ARMS[1]]['upper95'] < 0)
        corrected['criteria'][name] = dict(gates, both=all(gates.values()))
    onset_results = {}
    for onset in C.U.UNEXPECTED:
        selected = [j for j, c in enumerate(C.CONDITIONS) if c == ('reverse', onset)]
        onset_results[str(onset)] = panel(cost_values(data['counts'], selected, 1), reference_values(data['counts'], selected, 1))
    phase = reversal_phases(data)
    prediction = predictive_diagnostics(pop)
    integrity = dict(main_inputs=len(frozen['inputs']), main_outputs=len(manifest['outputs']),
                     snapshots=len(frozen['snapshots']), all_preserved=True)
    analysis = dict(created=C.utc(), components=components, reversal_phases=phase,
                    reversal_onsets=onset_results, predictive_diagnostics=prediction,
                    integrity=integrity, intervals_corrected=len(changes)*5,
                    scientific_policies_rerun=0, main_means_preserved=True,
                    original_gates=original['criteria'], corrected_gates=corrected['criteria'],
                    zero_headroom_changed_conditions=sum(r['zero_headroom_post_change'] for r in conditions))
    OUTPUT.mkdir()
    for name, value in (('CORRECTED_RESULTS.json', corrected), ('INTERVAL_CORRECTION.json', changes),
                        ('CONDITION_RESULTS.json', conditions), ('REPORT_ANALYSIS.json', analysis)):
        C.write(OUTPUT/name, value)
    # Read the exact serialized outputs back; interval verification is repeated
    # against scalar per-block values, not against the vector reporter itself.
    readback = json.loads((OUTPUT/'CORRECTED_RESULTS.json').read_text())
    for name, selected in C.panels().items():
        for seg, segment in enumerate(('episode', 'post_change')):
            if name == 'stable' and seg:
                continue
            reference = np.array(reference_values(data['counts'], selected, seg))
            p = readback['panels'][name][segment]
            for a, arm in enumerate(C.ARMS):
                verify_interval(p['arms'][arm], reference[..., a].tolist())
                verify_interval(p['against_always'][arm], (reference[..., a]-.1).tolist())
            verify_interval(p['structured_minus_anytime'], (reference[..., 1]-reference[..., 0]).tolist())
    C.check_inputs(ATTEMPT)
    C.write(OUTPUT/'ANALYSIS_READBACK.json', dict(passed=True, completed=C.utc(), seconds=perf_counter()-tick,
                                                checks=CHECKS, total_checks=sum(CHECKS.values()),
                                                criteria_unchanged=original['criteria'] == corrected['criteria'],
                                                integrity=integrity, outputs={p.name: C.digest(p) for p in sorted(OUTPUT.iterdir())},
                                                source_sha256=C.digest(Path(__file__).resolve())))
    print(json.dumps(dict(passed=True, checks=sum(CHECKS.values()), seconds=perf_counter()-tick,
                          intervals_corrected=len(changes)*5, criteria=corrected['criteria'],
                          reversal=corrected['panels']['reverse']['post_change'],
                          predictive=prediction), indent=2), flush=True)


if __name__ == '__main__':
    main()
