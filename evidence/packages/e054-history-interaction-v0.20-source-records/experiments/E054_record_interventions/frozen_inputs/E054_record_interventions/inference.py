"""Prespecified block-level inference and numerical control diagnostics."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import rng
from E054_record_interventions.plan import HISTORIES, ARMS, INJURIES, PRIMARY
import numpy as np


def diagnostics(inter, raw):
    H, A, F, R = inter['weights'].shape[:4]
    k = raw['coupling'].reshape(H, A, F, R, 3, 4, 16, 16)
    d = raw['denominator'].reshape(H, A, F, R, 3, 16, 16)
    s = inter['noise_signs']
    factors = np.stack([s*np.roll(s, shift, axis) for shift, axis in
                        ((-1, -1), (1, -1), (-1, -2), (1, -2))], axis=-3)
    aligned = k*factors[:, :, :, :, None]
    ports = raw['mean_ports'].reshape(H, A, F, R, 2, 3, 2)
    controls = dict(scale_k_error=float(abs(k[:, 1]-k[:, 0]).max()),
        switch_aligned_k_error=float(abs(aligned[:, 4]-k[:, 0]).max()),
        scale_output_error=float(abs(ports[:, 1]-ports[:, 0]).max()),
        switch_output_error=float(abs(ports[:, 4]-ports[:, 0]).max()),
        restoration_exact=bool(np.array_equal(raw['end'].reshape(H, A, F, R, 2, 3, 16, 16)[:, 7],
                                              raw['end'].reshape(H, A, F, R, 2, 3, 16, 16)[:, 0])),
        cycle_parity_preserved=bool(np.array_equal(inter['graph_before'][:, 4], inter['graph_before'][:, 0]) and
            np.array_equal(raw['graph_after'].reshape(H, A, F, R, 3, 7)[:, 4], raw['graph_after'].reshape(H, A, F, R, 3, 7)[:, 0])),
        scale_support_preserved=bool(np.array_equal(inter['weights'][:, 1] != 0, inter['weights'][:, 0] != 0)))
    passed = (all(controls[k] for k in ('restoration_exact', 'cycle_parity_preserved', 'scale_support_preserved')) and
        controls['scale_k_error'] <= 1e-12 and controls['switch_aligned_k_error'] <= 1e-12 and
        controls['scale_output_error'] <= 1e-8 and controls['switch_output_error'] <= 1e-8)
    controls['pass'] = bool(passed)
    measures = dict(coupling_l1=abs(k-k[:, :1]).sum(axis=(-3, -2, -1))/256,
        aligned_coupling_l1=abs(aligned-k[:, :1]).sum(axis=(-3, -2, -1))/256,
        denominator_l1=abs(d-d[:, :1]).sum(axis=(-2, -1))/256)
    return measures, controls


def block_values(cases):
    values = {}
    for measure in ('both', 'transfer', 'aligned_transfer', 'coupling_l1', 'aligned_coupling_l1', 'denominator_l1'):
        stacked = np.stack([x[measure] for x in cases]).mean(axis=(3, 4))
        for h, history in enumerate(HISTORIES):
            for a, arm in enumerate(ARMS):
                for j, injury in enumerate(INJURIES):
                    values[f'{measure}/{history}/{arm}/{injury}'] = stacked[:, h, a, j]
    margins = np.stack([x['margin'] for x in cases]).mean(axis=(3, 4, 5))
    for h, history in enumerate(HISTORIES):
        for a, arm in enumerate(ARMS):
            for j, injury in enumerate(INJURIES): values[f'margin/{history}/{arm}/{injury}'] = margins[:, h, a, j]
    for measure in ('both', 'aligned_transfer'):
        for history in HISTORIES:
            for injury in INJURIES:
                for arm in ARMS[1:]:
                    values[f'effect/{measure}/{history}/{arm}/{injury}'] = (
                        values[f'{measure}/{history}/{arm}/{injury}']-values[f'{measure}/{history}/untouched/{injury}'])
                values[f'sign_contrast/{measure}/{history}/{injury}'] = (
                    values[f'{measure}/{history}/sign_isolated/{injury}']-values[f'{measure}/{history}/sign_switch/{injury}'])
                if history != 'acquired':
                    values[f'repair_contrast/{measure}/{history}/{injury}'] = (
                        values[f'{measure}/{history}/delete_returning/{injury}']-values[f'{measure}/{history}/delete_other/{injury}'])
        for pairing in ('paired', 'independent'):
            for arm in ARMS[1:]:
                for injury in INJURIES:
                    values[f'policy_interaction/{measure}/{pairing}/{arm}/{injury}'] = (
                        values[f'effect/{measure}/{pairing}_rewrite/{arm}/{injury}']-
                        values[f'effect/{measure}/{pairing}_preserve/{arm}/{injury}'])
    for a, b in PRIMARY:
        values[f'primary/{ARMS[a]}'] = values[f'both/paired_rewrite/{ARMS[a]}/scattered']-values[f'both/paired_rewrite/{ARMS[b]}/scattered']
    return values


def analyze(cases, controls, mode):
    values = block_values(cases); count = len(cases)
    draws = rng('E054', 'bootstrap', 'record_interventions').integers(0, count, (10000, count))
    stats = {}
    for name, v in values.items():
        tails = [1/120, 1-1/120] if name.startswith('primary/') else [.025, .975]
        stats[name] = dict(mean=float(v.mean()), interval=np.quantile(v[draws].mean(axis=1), tails).tolist(),
                          confidence=1-2*tails[0], block_means=v.tolist())
    passed = all(x['pass'] for x in controls)
    labels = {}
    for a, b in PRIMARY:
        lo, hi = stats[f'primary/{ARMS[a]}']['interval']
        labels[ARMS[a]] = None if mode != 'scientific' or not passed else (
            'LOSS_EXCEEDS_FIVE_POINTS' if hi < -.05 else 'LOSS_BOUNDED_WITHIN_FIVE_POINTS' if lo > -.05 else 'UNRESOLVED')
    return dict(status='TECHNICAL_ONLY' if mode != 'scientific' else 'MECHANISTIC_FOLLOWUP' if passed else 'NUMERICAL_CONTROL_FAILURE',
        cohort_reused=True, independent_blocks=count, controls_pass=passed, controls_by_block=controls,
        primary_classifications=labels, statistics=stats)


def report(summary):
    lines = ['# E054 record interventions', '', summary['status'], '',
        'Existing E051 records, fresh common readers; no success filtering. Technical runs support no scientific inference.', '',
        '| Primary sensitivity | Difference, percentage points | Family-adjusted interval | Classification |',
        '| --- | ---: | --- | --- |']
    for arm, label in summary['primary_classifications'].items():
        s = summary['statistics'][f'primary/{arm}']; lo, hi = s['interval']
        lines.append(f'| {arm} | {100*s["mean"]:.2f} | [{100*lo:.2f}, {100*hi:.2f}] | {label} |')
    lines += ['', 'Primary history: h32 matched-noise full rewrite; scattered injury. Sign contrast uses anchored switching as its reference.', '',
        '## Function, signed transfer and normalized coupling', '',
        'Scattered-injury means. K distance is average absolute entry change per cell; aligned K applies the known cell switch to the coordinated arm.', '',
        '| History | Intervention | Both cues (%) | r*T | Raw K distance | Aligned K distance |',
        '| --- | --- | ---: | ---: | ---: | ---: |']
    for history in HISTORIES:
        for arm in ARMS:
            get = lambda metric:summary['statistics'][f'{metric}/{history}/{arm}/scattered']['mean']
            lines.append(f'| {history} | {arm} | {100*get("both"):.2f} | {get("aligned_transfer"):.4f} | {get("coupling_l1"):.4f} | {get("aligned_coupling_l1"):.4f} |')
    lines += ['',
        'Secondary intervals are pointwise. Different perturbation doses do not rank feature importance. Deletion changes both access and normalized coupling.',
        'Source and post-injury graph summaries, edit exposure, all normalized couplings, trajectories, signed transfer and policy interactions are retained.',
        'Numerical controls pass: '+str(summary['controls_pass'])+'.']
    return '\n'.join(lines)+'\n'
