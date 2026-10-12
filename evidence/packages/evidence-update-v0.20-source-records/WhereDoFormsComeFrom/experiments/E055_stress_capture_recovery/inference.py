"""Frozen block contrasts; transfer protection is a conjunction, not interaction alone."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import rng
from E055_stress_capture_recovery.plan import HISTORIES, ARMS, TIMES, INJURIES, GRAPH_FIELDS, PRIMARY_HISTORY
import numpy as np

METRICS = ('both', 'transfer', 'aligned_transfer', 'minimum_margin')
DIAGNOSTICS = ('shared_support', 'sign_disagreements', 'support_gained', 'support_lost',
               'coupling_l1', 'denominator_l1')


def block_values(cases):
    out = {}
    for metric in METRICS:
        fresh = np.stack([c['fresh_'+metric] for c in cases]).mean(axis=(-2, -1))
        body = np.stack([c['body_'+metric] for c in cases]).mean(axis=(-2, -1))
        for h, history in enumerate(HISTORIES):
            for a, arm in enumerate(ARMS):
                for j, injury in enumerate(INJURIES):
                    out[f'fresh/{metric}/{history}/{arm}/{injury}'] = fresh[:, h, a, j]
            for p, pulse in enumerate(('sham', 'pulse')):
                for t, name in enumerate(TIMES):
                    out[f'body/{metric}/{history}/{pulse}/{name}'] = body[:, h, p, t]
    for metric in ('both', 'aligned_transfer', 'minimum_margin'):
        for history in HISTORIES:
            for injury in INJURIES:
                get = lambda arm: out[f'fresh/{metric}/{history}/{arm}/{injury}']
                early = get('pulse_early')-get('sham_early')
                late = get('pulse_late')-get('sham_late')
                for label, value in (('early', early), ('late', late), ('interaction', late-early),
                    ('protected', get('protected_pulse')-get('protected_sham'))):
                    out[f'fresh_effect/{metric}/{history}/{label}/{injury}'] = value
            for name in TIMES:
                out[f'body_effect/{metric}/{history}/{name}'] = (
                    out[f'body/{metric}/{history}/pulse/{name}']-out[f'body/{metric}/{history}/sham/{name}'])
            out[f'body_effect/{metric}/{history}/interaction'] = (
                out[f'body_effect/{metric}/{history}/late']-out[f'body_effect/{metric}/{history}/early'])
        for history in HISTORIES[1:]:
            for injury in INJURIES:
                for effect in ('early', 'late', 'interaction'):
                    out[f'history_interaction/{metric}/{history}/{effect}/{injury}'] = (
                        out[f'fresh_effect/{metric}/{history}/{effect}/{injury}']-
                        out[f'fresh_effect/{metric}/acquired/{effect}/{injury}'])
    for metric in DIAGNOSTICS:
        values = np.stack([c[metric] for c in cases]).mean(axis=(-2, -1))
        for h, history in enumerate(HISTORIES):
            for a, arm in enumerate(ARMS):
                out[f'record/{metric}/{history}/{arm}'] = values[:, h, a]
    graph = np.stack([c['graph'] for c in cases]).mean(axis=(3, 4))
    fallback = np.stack([c['fallback_count'] for c in cases]).mean(axis=(-2, -1))
    distance = np.stack([c['body_state_distance'] for c in cases]).mean(axis=(-2, -1))
    for h, history in enumerate(HISTORIES):
        for a, arm in enumerate(ARMS):
            for g, field in enumerate(GRAPH_FIELDS):
                out[f'graph/{field}/{history}/{arm}'] = graph[:, h, a, g]
            if a < 4: out[f'record/fallback/{history}/{arm}'] = fallback[:, h, a]
        for t, label in enumerate(TIMES):
            out[f'body_distance/{history}/{label}'] = distance[:, h, t]
        for metric in ('requested_squared', 'delivered_squared', 'clipping_count'):
            out[f'pulse/{metric}/{history}'] = np.array([c['pulse_'+metric][h].mean() for c in cases])
    return out


def decisions(stats, mode, controls):
    enabled = mode == 'scientific' and controls
    fresh = f'fresh_effect/both/{PRIMARY_HISTORY}/'
    old = f'body_effect/both/{PRIMARY_HISTORY}/'
    bounds = lambda key: stats[key]['interval']
    gates = dict(early_transferred_loss_exceeds_five=bounds(fresh+'early/scattered')[1] < -.05,
        delay_interaction_exceeds_five=bounds(fresh+'interaction/scattered')[0] > .05,
        late_loss_bounded_within_five=bounds(fresh+'late/scattered')[0] > -.05,
        late_fresh_success_above_75=bounds(f'fresh/both/{PRIMARY_HISTORY}/pulse_late/scattered')[0] > .75)
    body = dict(early_body_loss_exceeds_five=bounds(old+'early')[1] < -.05,
        late_body_loss_bounded_within_five=bounds(old+'late')[0] > -.05,
        late_body_success_above_75=bounds(f'body/both/{PRIMARY_HISTORY}/pulse/late')[0] > .75)
    return ({k: bool(v) if enabled else None for k, v in gates.items()},
            {k: bool(v) if enabled else None for k, v in body.items()})


def analyze(cases, controls, mode):
    values = block_values(cases)
    draws = rng('E055', 'bootstrap', 'capture').integers(0, len(cases), (10000, len(cases)))
    stats = {k: dict(mean=float(v.mean()), interval=np.quantile(v[draws].mean(axis=1), [.025, .975]).tolist(),
                     confidence=.95, block_means=v.tolist()) for k, v in values.items()}
    ok = all(c['pass'] for c in controls)
    gates, body = decisions(stats, mode, ok)
    qualified = all(gates.values()) if mode == 'scientific' and ok else None
    joint = qualified and all(body.values()) if qualified is not None else None
    status = ('TECHNICAL_ONLY' if mode != 'scientific' else 'NUMERICAL_CONTROL_FAILURE' if not ok else
              'TRANSFER_PROTECTION_ESTABLISHED' if qualified else 'TRANSFER_PROTECTION_NOT_ESTABLISHED')
    return dict(status=status, cohort_reused=True, independent_blocks=len(cases),
        primary_history=PRIMARY_HISTORY, primary_injury='scattered', controls_pass=ok,
        controls_by_block=controls, primary_gates=gates, body_recovery_gates=body,
        transfer_protection=qualified, joint_body_and_transfer_recovery=joint, statistics=stats)


def report(s):
    stats = s['statistics']
    def fmt(key):
        v = stats[key]
        return f'{100*v["mean"]:.2f} [{100*v["interval"][0]:.2f}, {100*v["interval"][1]:.2f}]'
    lines = ['# E055 stress, recovery and capture', '', s['status'], '',
        'Existing E051 records; independent intrinsic cue noise in every current body; common fresh-reader assays.',
        'All source cases retained. Technical runs emit no scientific classifications.', '',
        '| Primary next-body contrast | Percentage points [95%] |', '| --- | ---: |']
    for name in ('early', 'late', 'interaction'):
        lines.append(f'| {name} | {fmt(f"fresh_effect/both/{PRIMARY_HISTORY}/{name}/scattered")} |')
    lines += ['', 'Primary transfer-protection requirements: '+str(s['primary_gates']),
        'Additional current-body recovery requirements: '+str(s['body_recovery_gates']),
        'Joint body-and-transfer recovery: '+str(s['joint_body_and_transfer_recovery']), '',
        '| History | Outgoing record | Fresh scattered success % [95%] |', '| --- | --- | ---: |']
    for history in HISTORIES:
        for arm in ARMS:
            lines.append(f'| {history} | {arm} | {fmt(f"fresh/both/{history}/{arm}/scattered")} |')
    lines += ['', '| History | Current body | Boundary | Both-cue success % [95%] |', '| --- | --- | --- | ---: |']
    for history in HISTORIES:
        for pulse in ('sham', 'pulse'):
            for stage in TIMES:
                lines.append(f'| {history} | {pulse} | {stage} | {fmt(f"body/both/{history}/{pulse}/{stage}")} |')
    lines += ['', 'Intervals are pointwise paired whole-block bootstrap intervals. The primary claim requires all four gates.',
        'A favourable interaction alone does not establish restoration. Body recovery and transferred function are separate.',
        'Diagnostic counts, signed transfer, normalized coupling, state displacement and full exposure remain in summary/raw evidence.',
        'Numerical controls pass: '+str(s['controls_pass'])+'.']
    return '\n'.join(lines)+'\n'
