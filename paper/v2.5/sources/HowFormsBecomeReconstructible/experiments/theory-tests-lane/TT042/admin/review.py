"""Completion review: independent integer reductions and saved-data custody."""
import itertools, os, signal, sys, time, traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import *
import analysis


def counts(x):
    return np.stack([(x < 0).sum(0), (x == 0).sum(0), (x > 0).sum(0)], axis=-1)


def cross(x, y):
    out = np.zeros((*x.shape[1:], 3, 3), dtype=np.int64)
    for i, a in enumerate((-1, 0, 1)):
        for j, b in enumerate((-1, 0, 1)):
            out[..., i, j] = ((np.sign(x) == a) & (np.sign(y) == b)).sum(0)
    return out


def differences(x):
    a, b, c, d = [x[:, i].astype(np.int64) for i in range(4)]
    out = np.stack([b-a, d-c, c-a, d-b, d-a, b-c, d-c-b+a], axis=1)
    np.testing.assert_array_equal(out[:, 4], out[:, 0] + out[:, 3])
    np.testing.assert_array_equal(out[:, 4], out[:, 2] + out[:, 1])
    np.testing.assert_array_equal(out[:, 6], out[:, 1] - out[:, 0])
    return out


def integer(x):
    value = np.asarray(x); out = np.rint(value * 12).astype(np.int64)
    near(out / 12, value); assert np.isin(out, (0, 3, 4, 6, 12)).all()
    return out


def chosen_masks(view, world):
    if view == 'all_masks': return list(range(4))
    if view.startswith('mask:'): return [MASKS.index(view[5:])]
    y, x = np.indices((16, 16)); task = world // 4
    target = np.where((y if task < 2 else x) < 8, 1, -1) * (-1 if task % 2 else 1)
    choices = []
    for mask in range(4):
        keep = (y if mask < 2 else x) // 8 == mask % 2
        mean = target[keep].mean()
        label = 'positive_half_retained' if mean == 1 else 'negative_half_retained' if mean == -1 else 'both_polarities_retained'
        if label == view[9:]: choices.append(mask)
    assert choices
    return choices


def reduce_block(cases, data, saved):
    lookup = {(c['damage'], c['family'], c['mask'], c['body_source'], c['world']): i for i, c in enumerate(cases)}
    assert len(lookup) == len(cases) == 1152
    assert set(lookup) == set(itertools.product(DAMAGE, FAMILIES, MASKS, SOURCES, range(16)))
    populated = 0
    for j, condition in enumerate(CONDITIONS):
        damage, family, group, view, source = condition.split('|'); worlds = []
        for w in range(16):
            history = cases[lookup[damage, family, MASKS[0], source, w]]['developed_score']
            assert all(cases[lookup[damage, family, mask, source, w]]['developed_score'] == history for mask in MASKS)
            if group == 'all' or group == f'message:{w//4}' or (group == 'history:unique_pass' and history == 1) or (group == 'history:other' and history != 1): worlds.append(w)
        n = len(worlds); assert saved['records'][j] == n
        if not n:
            for name, array in saved.items():
                assert np.isnan(array[j]).all() if np.issubdtype(array.dtype, np.floating) else (array[j] == 0).all()
            continue
        ids = np.array([[lookup[damage, family, MASKS[m], source, w] for m in chosen_masks(view, w)] for w in worlds])
        m = ids.shape[1]; assert saved['mask_cases'][j] == n*m
        b, r, original = [data[name][ids].astype(np.int64) for name in ('body', 'recipient', 'original')]
        bs, rs, rd = b.sum(1), r.sum((1, 3)), r.sum(1)
        db, dr = differences(bs), differences(rs)
        assert np.all(db[:, :2, 0] == 0) and np.all(dr[:, [2, 3, 6]] == 0)
        within = bs[:, :, 4] - bs[:, :, 0]
        values = dict(body_levels=bs.sum(0)/(12*n*m), recipient_levels=rs.sum(0)/(12*n*m*4),
                      original_levels=original.sum((0, 1, 2))/(12*n*m*4),
                      body_effects=db.sum(0)/(12*n*m), recipient_effects=dr.sum(0)/(12*n*m*4),
                      body_within_effects=within.sum(0)/(12*n*m), body_within_counts=counts(within),
                      body_record_counts=counts(db), recipient_record_counts=counts(dr),
                      body_case_counts=counts(differences(b.reshape(-1, 4, 5, 4))),
                      recipient_case_counts=counts(differences(r.sum(3).reshape(-1, 4, 4))),
                      recipient_draw_counts=counts(differences(rd).transpose(0, 2, 1, 3).reshape(-1, 7, 4)),
                      joint_counts=cross(db[:, :, 4], dr), body_transition_counts=cross(db[:, :, 0], db[:, :, 4]))
        for name, value in values.items():
            if np.issubdtype(saved[name].dtype, np.integer): np.testing.assert_array_equal(saved[name][j], value)
            else: near(saved[name][j], value)
        populated += 1
    return populated


def endpoint_custody(index, sub, cases, data):
    src = folder('development', index)
    oldrows = {(r['damage'], r['family'], r['mask'], r['body_source'], r['world'], r['draw']): r for r in read(src/'ROWS.json')}
    oldbodies = {(r['damage'], r['family'], r['mask'], r['body_source'], r['world']): r for r in read(src/'BODY_TRAJECTORY.json')}
    body = {p.name[:-9]: arrays(p) for p in (sub/'physical').glob('*_body.npz')}
    checked = 0
    for i, case in enumerate(cases):
        w = case['world']; mi = MASKS.index(case['mask']); labels = [w//4, (w//4+2)%4, mi^1, mi]
        key = (case['damage'], case['family'], case['mask'], case['body_source'], w)
        for ai, name in enumerate(case['continuations']):
            observed = body[Path(name).name]
            value = np.stack([observed[f's{t}_probabilities'][w, labels] for t in TIMES])
            np.testing.assert_array_equal(data['body'][i, ai], integer(value)); checked += 1
        for ai, field in ((0, 'body_preserve'), (3, 'body_late')):
            expected = [oldbodies[key]['body_by_time'][str(t)][field] for t in TIMES]
            np.testing.assert_array_equal(data['body'][i, ai], integer(expected))
        for draw in range(4):
            row = oldrows[(*key, draw)]
            for ai, name in enumerate(('incoming', 'after_late100', 'incoming', 'after_late100')):
                np.testing.assert_array_equal(data['recipient'][i, ai, draw], integer(row[name]))
            np.testing.assert_array_equal(data['original'][i, draw], integer(row['original']))
    return checked


def state_diagnostics(sub):
    # Exploratory saved-state diagnostic: score equality need not mean state equality.
    result = {}
    for damage in DAMAGE:
        result[damage] = dict(cases=0, nonidentical_body_fields=np.zeros((2, 5, 3), dtype=np.int64),
                             maximum_absolute_field_difference=np.zeros((2, 5, 3)))
    cache = {}
    for alias in read(sub/'ALIASES.json'):
        if alias['family'] != 'residual' or alias['body_source'] != 'own': continue
        current = result[alias['damage']]; current['cases'] += 16
        states = []
        for name in alias['continuations']:
            if name not in cache:
                cache[name] = arrays(sub/(name+'.npz'), [f's{t}_{k}' for t in TIMES for k in BODY_KEYS])
            states.append(cache[name])
        for pi, (a, b) in enumerate(((0, 2), (1, 3))):
            for ti, t in enumerate(TIMES):
                for fi, field in enumerate(BODY_KEYS):
                    x, y = states[a][f's{t}_{field}'], states[b][f's{t}_{field}']
                    unequal = np.any(x.view(np.uint8).reshape(16, -1) != y.view(np.uint8).reshape(16, -1), axis=1)
                    current['nonidentical_body_fields'][pi, ti, fi] += unequal.sum()
                    current['maximum_absolute_field_difference'][pi, ti, fi] = max(
                        current['maximum_absolute_field_difference'][pi, ti, fi], float(np.max(np.abs(x-y))))
    return result


def main():
    tick = time.monotonic(); os.sched_setaffinity(0, {6})
    assert os.getpriority(os.PRIO_PROCESS, 0) == 0
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('600-second completion review deadline')))
    signal.alarm(600)
    assert read(ROOT/'COMPLETION_PROCESS_CHECK.json')['no_active_jobs']
    assert read(ROOT/'COMPLETION_REVIEW_RESOURCE.json')['admission_pass']
    run = ROOT/'runs/exchange_v1'; complete = read(run/'COMPLETE.json'); frozen = read(ROOT/'FREEZE.json')
    assert complete['status'] == 'COMPLETE' and complete['freeze_sha256'] == sha(ROOT/'FREEZE.json')
    assert complete['seconds'] < frozen['deadline_seconds'] and complete['inputs'] == frozen['inputs'] == inputs()
    write(ROOT/'RESULT_INSPECTION.json', dict(recorded_utc=now(), completion_sha256=sha(run/'COMPLETE.json'),
          completion_precedes_inspection=True, inspection='User-requested status turn; this record follows the initial report read.',
          source_population_already_exposed=True, new_production_exchange_outcomes_now_exposed=True))
    verify(frozen['evidence']); verify(complete['inputs']); verify(complete['outputs'])
    manifest = read(ROOT/'SOURCE_MANIFEST.json'); verify(manifest['evidence'])
    used = {}; blocks = []; diagnostic_blocks = []; reduced = endpoints = 0
    for index in BLOCKS:
        sub = run/f'tissue_{index}'; observed = arrays(sub/'AGGREGATE.npz')
        consumed = read(sub/'USED_INPUTS.json')
        assert all(manifest['development'][p] == h for p, h in consumed.items()); used.update(consumed)
        cases, data = read(sub/'CASES.json'), arrays(sub/'ENDPOINTS.npz')
        endpoints += endpoint_custody(index, sub, cases, data)
        reduced += reduce_block(cases, data, observed)
        diagnostic_blocks.append(state_diagnostics(sub)); blocks.append(observed)
        print(json.dumps(dict(block=index, elapsed_seconds=time.monotonic()-tick, status='REVIEWED')), flush=True)
    verify(used)
    saved = arrays(run/'SUMMARY.npz'); expected_keys = set()
    weights = np.stack([b['records'] for b in blocks])
    for name in blocks[0]:
        stacked = np.stack([b[name] for b in blocks]); expected_keys.add('block_'+name)
        near(saved['block_'+name], stacked)
        if np.issubdtype(stacked.dtype, np.integer):
            np.testing.assert_array_equal(saved[name], stacked.sum(0)); expected_keys.add(name)
        else:
            equal = np.full_like(stacked[0], np.nan); pooled = equal.copy()
            for j in range(len(CONDITIONS)):
                ok = weights[:, j] > 0
                if not ok.any(): continue
                equal[j] = stacked[ok, j].sum(0)/ok.sum()
                pooled[j] = np.tensordot(weights[ok, j], stacked[ok, j], axes=1)/weights[ok, j].sum()
            near(saved['equal_'+name], equal); near(saved['pooled_'+name], pooled)
            expected_keys.update(('equal_'+name, 'pooled_'+name))
    assert set(saved) == expected_keys
    assert (run/'REPORT.md').read_text() == analysis.report(saved, 'development')
    panels = {}
    for damage in DAMAGE:
        j = INDEX[f'{damage}|residual|all|all_masks|own']
        contrasts = {}
        for q, name in enumerate(COMPARISONS):
            contrasts[name] = dict(body_by_time_pp=(100*saved['equal_body_effects'][j, q, :, 0]).tolist(),
                body_block_effects_1900_pp=(100*saved['block_body_effects'][:, j, q, 4, 0]).tolist(),
                body_record_harm_tie_gain=saved['body_record_counts'][j, q, 4, 0].tolist(),
                body_case_harm_tie_gain=saved['body_case_counts'][j, q, 4, 0].tolist(),
                recipient_effect_pp=float(100*saved['equal_recipient_effects'][j, q, 0]),
                recipient_record_harm_tie_gain=saved['recipient_record_counts'][j, q, 0].tolist(),
                recipient_case_harm_tie_gain=saved['recipient_case_counts'][j, q, 0].tolist(),
                joint_body_recipient_record_counts=saved['joint_counts'][j, q, 0].tolist())
        diag = dict(cases=sum(d[damage]['cases'] for d in diagnostic_blocks))
        diag['nonidentical_body_fields'] = sum(d[damage]['nonidentical_body_fields'] for d in diagnostic_blocks).tolist()
        diag['maximum_absolute_field_difference'] = np.max([d[damage]['maximum_absolute_field_difference'] for d in diagnostic_blocks], axis=0).tolist()
        panels[damage] = dict(contrasts=contrasts, body_levels_by_time_percent=(100*saved['equal_body_levels'][j, :, :, 0]).tolist(),
                              inherited_recipient_levels_percent=(100*saved['equal_recipient_levels'][j, :, 0]).tolist(),
                              saved_state_diagnostic=diag)
    findings = dict(classification='EXPOSED_BODY_PACKET_EXCHANGE', confirmatory=False, blocks=BLOCKS,
                    primary_view='residual|all|all_masks|own; target credit', arms=ARMS, times=TIMES, signs=SIGNS,
                    independent_population_blocks=4, source_positions=64, injury_cases_per_panel=256,
                    new_receiving_assays=0, inherited_recipient_evidence=True, original_matched_forcing=True,
                    all_cases_and_paired_harms_retained=True, panels=panels,
                    diagnostic_status='Post-result exploratory check of saved body-field equality; no new dynamics.',
                    diagnostic_axes=['packet T0/T1', 'time', 'V/ema/R'])
    write(ROOT/'FINDINGS.json', findings)
    closeout = dict(status='PASS', completed_utc=now(), seconds=time.monotonic()-tick,
                    complete_sha256=sha(run/'COMPLETE.json'), findings_sha256=sha(ROOT/'FINDINGS.json'),
                    review_code_sha256=sha(__file__), output_files_verified=len(complete['outputs']),
                    consumed_source_files_verified=len(used), condition_blocks_checked=4*len(CONDITIONS),
                    populated_condition_blocks_independently_reduced=reduced, body_case_arms_checked=endpoints,
                    all_summary_arrays_independently_reduced=True, report_reproduced=True,
                    physical_replay='Every physical continuation independently replayed during production; not rerun at closeout.',
                    physical_verification=complete['verification'], production_serial_parallel_not_repeated=True,
                    qualification_serial_parallel_passed=read(ROOT/'runs/qualification_v1/COMPLETE.json')['serial_parallel_bitwise_equal'],
                    study_bytes_at_review=size(), free_bytes_at_review=shutil.disk_usage(ROOT).free)
    space(); write(ROOT/'CLOSEOUT.json', closeout); signal.alarm(0)
    print(json.dumps(closeout), flush=True)


if __name__ == '__main__':
    try: main()
    except BaseException as error:
        write(ROOT/'COMPLETION_REVIEW_FAILED.json', dict(status='FAILED', recorded_utc=now(), error=repr(error), traceback=traceback.format_exc()))
        raise
