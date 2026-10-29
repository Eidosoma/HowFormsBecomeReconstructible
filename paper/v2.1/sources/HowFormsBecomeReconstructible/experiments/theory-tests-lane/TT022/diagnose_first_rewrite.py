"""Exploratory first-rewrite analysis of checked TT022 arrays; no dynamics."""
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import time
import traceback

import numpy as np

import common as c
import design
import execute
import reference as ref
import tt019_reference as physical

DESTINATION = c.ROOT/'diagnostics/first_rewrite_v1'
ORIGINAL = c.ROOT/'runs/serial_v1'
STAGES = ('developed', 'injured', 'repair_step_1', 'repaired', 'next_body')
STRATA = ('positive_half_retained', 'negative_half_retained', 'both_polarities_retained')
MEASURES = ('recognition', 'margin', 'own_projection')
REQUIRED = ('g01.json', 'g02.json', 'g01_develop.npz', 'g01_boundary.npz',
            'g01_repair.npz', 'g01_body.npz', 'g02_develop.npz', 'records.json', 'CHECK.json')


def average(values):
    values = list(values)
    return math.fsum(values)/len(values) if values else None


def measure(field, codes, labels):
    """Check vector projection against scalar summation before assigning ties."""
    vector = field.reshape(len(field), -1)@codes.reshape(4, -1).T/256
    scalar = np.asarray([[math.fsum(float(a)*float(b) for a, b in zip(row.flat, code.flat))/256
                          for code in codes] for row in field])
    assert np.isfinite(scalar).all() and np.max(np.abs(vector-scalar)) <= 2e-13
    ties = np.abs(scalar-scalar.max(axis=1, keepdims=True)) <= 1e-12
    probabilities = ties/ties.sum(axis=1, keepdims=True)
    ix = np.arange(len(field))
    own = scalar[ix, labels]
    others = scalar.copy(); others[ix, labels] = -np.inf
    return dict(recognition=probabilities[ix, labels], margin=own-others.max(axis=1),
                own_projection=own, probabilities=probabilities, scores=scalar)


def saved_scores(value, observed):
    assert np.max(np.abs(value['scores']-observed['scores'])) <= 2e-13
    c.ref.exact(value['probabilities'], observed['probabilities'], 'diagnostic saved probabilities')
    c.ref.exact(value['recognition'][:, None], observed['correctness'], 'diagnostic saved recognition')
    assert np.max(np.abs(value['margin'][:, None]-observed['margins'])) <= 2e-13


def geometry(fresh, target):
    assert fresh.dtype == np.bool_ and fresh.shape == target.shape
    assert np.all(fresh.sum(axis=(1, 2)) == 128)
    retained_mean = (target*~fresh).sum(axis=(1, 2))/128
    assert set(retained_mean) <= {-1., 0., 1.}
    return [STRATA[0] if v == 1 else STRATA[1] if v == -1 else STRATA[2] for v in retained_mean]


def packet_stats(initial, value, codes, labels, fresh):
    score = measure(value, codes, labels)
    a = initial-initial.mean(axis=(1, 2), keepdims=True)
    b = value-value.mean(axis=(1, 2), keepdims=True)
    denominator = np.sqrt((a*a).sum(axis=(1, 2))*(b*b).sum(axis=(1, 2)))
    correlation = np.divide((a*b).sum(axis=(1, 2)), denominator,
        out=np.zeros(len(value)), where=denominator > 0)
    delta = value-initial
    retained_axis = np.where(fresh, -1., 1.)
    return dict(code_margin=score['margin'], own_projection=score['own_projection'],
        incoming_correlation=correlation, rms_displacement=np.sqrt((delta*delta).mean(axis=(1, 2))),
        fresh_rms_displacement=np.sqrt(((delta*delta)*fresh).sum(axis=(1, 2))/128),
        retained_rms_displacement=np.sqrt(((delta*delta)*~fresh).sum(axis=(1, 2))/128),
        retained_axis_projection=(value*retained_axis).mean(axis=(1, 2)),
        packet_std=value.std(axis=(1, 2)), correlation_degenerate=(denominator == 0).astype(float))


def handoff(packet, next_incoming):
    c.ref.exact(packet, next_incoming, 'first outgoing packet is second incoming packet')


def rejects(call):
    try:
        call()
    except AssertionError:
        return True
    raise AssertionError('corruption not rejected')


def qualification():
    grid = np.indices((16, 16))
    horizontal = np.where(grid[0] < 8, 1., -1.)
    vertical = np.where(grid[1] < 8, 1., -1.)
    codes = np.stack((horizontal, -horizontal, vertical, -vertical))
    labels = np.arange(4)
    perfect = measure(1.2*codes, codes, labels)
    assert np.all(perfect['recognition'] == 1.)
    assert np.all(measure(np.zeros_like(codes), codes, labels)['recognition'] == .25)
    assert np.all(measure(-codes, codes, labels)['recognition'] == 0.)
    fresh = np.broadcast_to(grid[0] >= 8, codes.shape).copy()
    assert geometry(fresh, codes) == [STRATA[0], STRATA[1], STRATA[2], STRATA[2]]
    assert geometry(~fresh, codes) == [STRATA[1], STRATA[0], STRATA[2], STRATA[2]]
    rejects(lambda: geometry(np.zeros_like(fresh), codes))
    baseline = .3*codes
    unchanged, opposite = (packet_stats(baseline, v, codes, labels, fresh) for v in (baseline, -baseline))
    assert np.max(np.abs(unchanged['incoming_correlation']-1)) < 2e-13
    assert np.all(unchanged['rms_displacement'] == 0.)
    assert np.max(np.abs(opposite['incoming_correlation']+1)) < 2e-13
    assert np.max(np.abs(opposite['rms_displacement']-.6)) < 2e-13
    handoff(baseline, baseline.copy())
    damaged = baseline.copy(); damaged.flat[0] = np.nextafter(damaged.flat[0], np.inf)
    rejects(lambda: handoff(baseline, damaged))
    observed = dict(scores=perfect['scores'], probabilities=perfect['probabilities'],
                    correctness=perfect['recognition'][:, None], margins=perfect['margin'][:, None])
    saved_scores(perfect, observed)
    wrong = dict(observed, correctness=np.zeros((4, 1)))
    rejects(lambda: saved_scores(perfect, wrong))
    return dict(status='PASS', checks=['known_codes', 'ties', 'opposite_codes', 'all_injury_strata',
        'complement_geometry', 'invalid_injury_rejected', 'unchanged_packet', 'opposite_packet',
        'byte_exact_handoff', 'one_ulp_wrong_handoff_rejected', 'saved_scores', 'wrong_scores_rejected'],
        new_dynamics=0)


def extract(directory, index, future, family, policy, cfg, rcfg, ctx, manifest):
    def read(name):
        path = directory/name
        assert c.sha(path) == manifest[str(path)]
        return c.read_json(path)
    first, second = read('g01.json'), read('g02.json')
    def arrays(name, meta, label):
        path = directory/name
        assert c.sha(path) == manifest[str(path)] == meta['files'][label]
        raw = c.arrays(path)
        assert c.identities(raw) == meta['arrays'][label]
        return raw
    developed = arrays('g01_develop.npz', first, 'develop')
    boundary = arrays('g01_boundary.npz', first, 'boundary')
    repaired = arrays('g01_repair.npz', first, 'repair')
    body = arrays('g01_body.npz', first, 'body')
    following = arrays('g02_develop.npz', second, 'develop')
    proof, stored_rows = read('CHECK.json'), read('records.json')
    assert proof['status'] == 'PASS' and len(stored_rows) == 16
    assert [(r['world'], r['message'], r['replicate']) for r in stored_rows] == [(i, i//4, i % 4) for i in range(16)]
    initial = repaired['s0_theta']
    handoff(developed['s0_theta'], initial)
    c.ref.exact(repaired['s0_V'], boundary['injured_V'])
    selected = design.spec(family, policy)
    c.ref.exact(repaired['s0_R'], repaired['s0_V'] if selected.capture else np.zeros_like(initial))
    assert not np.any(repaired['s0_ema'])
    if selected.base.write:
        expected = physical.project((1-cfg.lam)*initial+cfg.lam*np.tanh(repaired['s1_R']), cfg.norm)
        c.ref.exact(repaired['s1_theta'], expected, 'native first write equation')
    else:
        c.ref.exact(initial, repaired['s1_theta']); c.ref.exact(initial, repaired[f's{cfg.sweeps}_theta'])
    if policy == 'average':
        expected = physical.project((1-cfg.lam)*initial+cfg.lam*np.tanh((repaired['s0_V']+repaired['s1_V'])/2), cfg.norm)
        assert np.max(np.abs(expected-repaired['a1_theta'])) <= 2e-12
    prefix = 'a' if policy == 'average' else 's'
    outgoing = repaired[f'{prefix}{cfg.sweeps}_theta']
    handoff(outgoing, following['s0_theta'])
    assert first['outgoing_sha256'] == second['input_sha256'] == hashlib.sha256(outgoing.tobytes()).hexdigest()
    codes, labels = ctx['codes'], np.arange(16)//4
    ref.scores(codes, developed, rcfg); ref.scores(codes, following, rcfg)
    ref.scores(codes, dict(body, **{f's{cfg.sweeps}_V': repaired[f's{cfg.sweeps}_V']}), rcfg)
    stages = {name: measure(value, codes, labels) for name, value in zip(STAGES,
        (developed[f's{cfg.sweeps}_V'], boundary['injured_V'], repaired['s1_V'], repaired[f's{cfg.sweeps}_V'], following[f's{cfg.sweeps}_V']))}
    for name, observed in (('developed', developed), ('repaired', body), ('next_body', following)):
        saved_scores(stages[name], observed)
    packets = {name: packet_stats(initial, value, codes, labels, boundary['fresh']) for name, value in (
        ('incoming', initial), ('step_1', repaired[f'{prefix}1_theta']), ('outgoing', outgoing))}
    memory = {}
    for step in (0, 1, cfg.sweeps):
        value = repaired[f's{step}_R']
        memory[f'step_{step}'] = {k: v for k, v in measure(value, codes, labels).items() if k in MEASURES}
        target = np.tanh(value)
        memory[f'target_{step}'] = {k: v for k, v in measure(target, codes, labels).items() if k in MEASURES}
        memory[f'target_{step}']['retained_axis_projection'] = (target*np.where(boundary['fresh'], -1., 1.)).mean(axis=(1, 2))
    groups = geometry(boundary['fresh'], codes[labels])
    rows = []
    for i in range(16):
        row = dict(block=index, future=future, family=family, policy=policy, world=i,
            message=int(labels[i]), replicate=i % 4, injury_stratum=groups[i],
            body={name: {k: float(values[k][i]) for k in MEASURES} for name, values in stages.items()},
            packet={name: {k: float(v[i]) for k, v in values.items()} for name, values in packets.items()},
            memory={name: {k: float(v[i]) for k, v in values.items()} for name, values in memory.items()})
        assert row['body']['developed']['recognition'] == stored_rows[i]['development'][0]
        assert row['body']['next_body']['recognition'] == stored_rows[i]['development'][1]
        assert row['body']['repaired']['recognition'] == stored_rows[i]['repaired'][0]
        rows.append(row)
    custody = dict(initial=initial.tobytes(), developed=developed[f's{cfg.sweeps}_V'].tobytes(),
        injured=boundary['injured_V'].tobytes(), mask=boundary['fresh'].tobytes(),
        next_birth=following['s0_V'].tobytes(), first_environment=proof['environment'][0], next_environment=proof['environment'][1])
    return rows, custody


def overview(rows):
    return dict(n=len(rows),
        body={stage: {key: average(r['body'][stage][key] for r in rows) for key in MEASURES} for stage in STAGES},
        packet={step: {key: average(r['packet'][step][key] for r in rows) for key in rows[0]['packet'][step]}
                for step in rows[0]['packet']},
        memory={step: {key: average(r['memory'][step][key] for r in rows) for key in rows[0]['memory'][step]}
                for step in rows[0]['memory']}) if rows else dict(n=0)


def paired(left, right):
    identity = lambda r: (r['block'], r['future'], r['world'])
    assert [identity(r) for r in left] == [identity(r) for r in right]
    assert all(a['injury_stratum'] == b['injury_stratum'] for a, b in zip(left, right))
    delta = [a['body']['next_body']['recognition']-b['body']['next_body']['recognition'] for a, b in zip(left, right)]
    return dict(n=len(delta), next_body_difference=average(delta),
        improved=sum(v > 0 for v in delta), worsened=sum(v < 0 for v in delta), tied=sum(v == 0 for v in delta))


def summarize(rows):
    output = {}
    for family in design.FAMILIES:
        arms = {}
        for policy in design.POLICIES:
            selected = [r for r in rows if r['family'] == family and r['policy'] == policy]
            assert len(selected) == 256
            arms[policy] = dict(overall=overview(selected),
                blocks={str(i): overview([r for r in selected if r['block'] == i]) for i in c.BLOCKS},
                messages={str(m): overview([r for r in selected if r['message'] == m]) for m in range(4)},
                injury_strata={group: overview([r for r in selected if r['injury_stratum'] == group]) for group in STRATA})
        left = [r for r in rows if r['family'] == family and r['policy'] == 'capture']
        right = [r for r in rows if r['family'] == family and r['policy'] == 'capture_once']
        transitions = Counter(''.join('1' if r['body'][stage]['recognition'] == 1 else '0'
                             for stage in ('developed', 'injured', 'next_body')) for r in left)
        output[family] = dict(arms=arms, capture_minus_once=dict(overall=paired(left, right),
            blocks={str(i): paired([r for r in left if r['block'] == i], [r for r in right if r['block'] == i]) for i in c.BLOCKS},
            injury_strata={group: paired([r for r in left if r['injury_stratum'] == group], [r for r in right if r['injury_stratum'] == group]) for group in STRATA}),
            capture_transition_table={f'{i:03b}': transitions[f'{i:03b}'] for i in range(8)},
            transition_bit_order=['developed_unique_pass', 'injured_unique_pass', 'next_body_unique_pass'])
    return dict(classification='POST_OUTCOME_EXPLORATORY_SAVED_TRAJECTORY_DIAGNOSTIC',
        blocks=list(c.BLOCKS), futures=4, records_per_family=64, rows=len(rows),
        new_dynamics=0, new_recipient_assays=0, significance_verdict=False, families=output)


def report(value):
    lines = ['# TT022 first-rewrite diagnostic', '',
        'Exploratory analysis after the serial results were inspected. Four exposed blocks; all cases retained; no new dynamics or receiving assays.', '',
        '| Family | Policy | First developed body | Injured body | After one update | After repair | Next fresh body |',
        '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for family in design.FAMILIES:
        for policy in design.POLICIES:
            arm = value['families'][family]['arms'][policy]['overall']
            lines.append(f'| {family} | {policy} | '+' | '.join(f"{100*arm['body'][stage]['recognition']:.3f}%" for stage in STAGES)+' |')
    lines += ['', '| Family | Retained target content | Draws | Capture next body | One-time next body | Paired difference | Improved / worsened / tied |',
        '| --- | --- | ---: | ---: | ---: | ---: | --- |']
    for family in design.FAMILIES:
        data = value['families'][family]
        for group in STRATA:
            a, b = (data['arms'][p]['injury_strata'][group] for p in ('capture', 'capture_once'))
            d = data['capture_minus_once']['injury_strata'][group]
            if not d['n']:
                lines.append(f'| {family} | {group} | 0 | — | — | — | — |'); continue
            lines.append(f"| {family} | {group} | {d['n']} | {100*a['body']['next_body']['recognition']:.3f}% | {100*b['body']['next_body']['recognition']:.3f}% | {100*d['next_body_difference']:.3f} pp | {d['improved']} / {d['worsened']} / {d['tied']} |")
    lines += ['', '| Family | Capture packet correlation with incoming | Packet RMS displacement | Own-code projection before / after |',
        '| --- | ---: | ---: | ---: |']
    for family in design.FAMILIES:
        p = value['families'][family]['arms']['capture']['overall']['packet']
        lines.append(f"| {family} | {p['outgoing']['incoming_correlation']:.6f} | {p['outgoing']['rms_displacement']:.6f} | {p['incoming']['own_projection']:.6f} / {p['outgoing']['own_projection']:.6f} |")
    lines += ['', 'Packet projections, memory projections and injury-stage recognition are diagnostics; only the next fresh-body read measures outgoing-record usefulness here.',
        'The matched capture/one-time branches share their initial packet, developed body and injury, and their next receiving environment. Their first repair changes both memory feedback and writing.',
        'The injury strata are defined from the saved mask and intended task before filtering outcomes, but chosen for analysis after TT022 results. Counts are future draws nested within four blocks.',
        'Only updates 0, 1 and 1,000 were saved. This cannot locate an exact intermediate failure time or identify a unique causal mechanism.',
        'Complete block, message, injury, transition, memory and packet summaries and every row are retained in SUMMARY.json and ROWS.json.', '']
    return '\n'.join(lines)


def main():
    tick = time.monotonic()
    os.nice(10)
    DESTINATION.mkdir(parents=True, exist_ok=False)
    def expired(signum, frame): raise TimeoutError('600-second saved-diagnostic limit')
    signal.signal(signal.SIGALRM, expired); signal.alarm(600)
    c.write_json(DESTINATION/'RUNNING.json', dict(status='RUNNING', started_utc=c.now(), new_dynamics=0,
        analysis_after_outcome_inspection=True, numerical_threads=1, deadline_seconds=600))
    try:
        frozen = c.read_json(c.ROOT/'FREEZE.json')
        assert c.runtime_hashes() == frozen['inputs'] and execute.environment() == frozen['environment']
        admission = c.read_json(c.ROOT/'FIRST_REWRITE_RESOURCE_CHECK.json')
        assert admission['within_limit'] and admission['planned_numerical_threads'] == 1
        closeout = c.read_json(c.ROOT/'CLOSEOUT.json')
        assert closeout['status'] == 'PASS' and c.sha(closeout['path']) == closeout['sha256']
        complete = c.read_json(closeout['path']); c.verify(complete['outputs'])
        prior = c.read_json(Path(closeout['path']).parent/'ORIGINAL_FILES.json')
        inputs = dict(frozen['inputs'])
        for name in (__file__, c.ROOT/'FIRST_REWRITE_PLAN.md', c.ROOT/'FIRST_REWRITE_RESOURCE_CHECK.json', c.ROOT/'CLOSEOUT.json', closeout['path'],
                     Path(closeout['path']).parent/'ORIGINAL_FILES.json'):
            inputs[str(Path(name).resolve())] = c.sha(name)
        for index in c.BLOCKS:
            for future in range(design.FUTURES):
                for family in design.FAMILIES:
                    for policy in design.POLICIES:
                        path = ORIGINAL/f'tissue_{index}'/f'future_{future:02d}'/family/policy
                        for name in REQUIRED: inputs[str(path/name)] = prior[str(path/name)]
        c.verify(inputs); c.verify(frozen['evidence'])
        c.write_json(DESTINATION/'INPUTS.json', inputs)
        c.write_json(DESTINATION/'QUALIFICATION.json', qualification())
        cfg, rcfg = design.configs('development')
        rows = []; matched_pairs = 0
        for index in c.BLOCKS:
            ctx = c.model.source.context(index, cfg)
            grid = np.indices((16, 16)); h = np.where(grid[0] < 8, 1., -1.); v = np.where(grid[1] < 8, 1., -1.)
            c.ref.exact(ctx['codes'], np.stack((h, -h, v, -v)), 'independent diagnostic codebook')
            for future in range(design.FUTURES):
                for family in design.FAMILIES:
                    custody = {}
                    for policy in design.POLICIES:
                        path = ORIGINAL/f'tissue_{index}'/f'future_{future:02d}'/family/policy
                        values, custody[policy] = extract(path, index, future, family, policy, cfg, rcfg, ctx, inputs)
                        rows.extend(values)
                    assert custody['capture'] == custody['capture_once']
                    matched_pairs += 16
            print(json.dumps(dict(stage='block_diagnosed', tissue=index)), flush=True)
        assert len(rows) == 3584 and matched_pairs == 512
        c.write_json(DESTINATION/'ROWS.json', rows)
        summary = summarize(rows); c.write_json(DESTINATION/'SUMMARY.json', summary)
        with (DESTINATION/'REPORT.md').open('x') as stream: stream.write(report(summary))
        assert c.serialized(summarize(c.read_json(DESTINATION/'ROWS.json'))) == (DESTINATION/'SUMMARY.json').read_bytes()
        assert report(c.read_json(DESTINATION/'SUMMARY.json')) == (DESTINATION/'REPORT.md').read_text()
        c.verify(inputs); c.verify(frozen['evidence'])
        outputs = {str(p): c.sha(p) for p in sorted(DESTINATION.iterdir()) if p.is_file()}
        receipt = dict(status='PASS', completed_utc=c.now(), seconds=time.monotonic()-tick,
            inputs=len(inputs), input_manifest_sha256=c.sha(DESTINATION/'INPUTS.json'), outputs=outputs,
            qualification_checks=12, rows=len(rows), blocks=list(c.BLOCKS),
            paired_capture_one_time_draws=matched_pairs, new_dynamics=0, new_recipient_assays=0,
            frozen_inputs_unchanged=True, source_outputs_unchanged=True,
            post_outcome_exploratory=True, significance_verdict=False, automatic_successor=False)
        c.write_json(DESTINATION/'COMPLETE.json', receipt); signal.alarm(0)
        c.write_json(c.ROOT/'FIRST_REWRITE_DIAGNOSTIC.json', dict(status='PASS', path=str(DESTINATION/'COMPLETE.json'),
            sha256=c.sha(DESTINATION/'COMPLETE.json'), classification=summary['classification'], new_dynamics=0))
        print(json.dumps({k: receipt[k] for k in ('status', 'seconds', 'inputs', 'rows', 'paired_capture_one_time_draws', 'new_dynamics')}), flush=True)
    except BaseException as error:
        c.write_json(DESTINATION/'FAILED.json', dict(status='FAILED', failed_utc=c.now(), error=repr(error), traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    main()
