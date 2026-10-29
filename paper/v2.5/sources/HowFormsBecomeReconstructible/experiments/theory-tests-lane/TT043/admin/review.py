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
    a, b, c, d = [x[:, i] for i in range(4)]
    out = np.stack([b-a, d-c, c-a, d-b, d-a, b-c, d-c-b+a], axis=1)
    if np.issubdtype(out.dtype, np.integer):
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
        m = ids.shape[1]; assert saved['mask_cases'][j] == n*m; changes = []
        for pi, profile in enumerate(PROFILES):
            value = data[profile][ids].astype(np.int64); d = value.shape[3]
            summed = value.sum((1, 3)); per_draw = value.sum(1); delta = differences(summed); changes.append(delta)
            assert np.all(delta[:, :4, 0] == 0)
            margin = data[profile+'_margin'][ids].sum((1, 3))
            temporal = summed[:, :, 5]-summed[:, :, 4]
            expected = dict(levels=summed.sum(0)/(12*n*m*d), effects=delta.sum(0)/(12*n*m*d),
                margin_levels=margin.sum(0)/(n*m*d), margin_effects=differences(margin).sum(0)/(n*m*d),
                record_counts=counts(delta), case_counts=counts(differences(value.sum(3).reshape(-1, 4, 6, 4))),
                draw_counts=counts(differences(per_draw).transpose(0, 2, 1, 3, 4).reshape(-1, 7, 6, 4)),
                temporal_change=temporal.sum(0)/(12*n*m*d), temporal_counts=counts(temporal))
            for name, v in expected.items():
                if np.issubdtype(saved[name].dtype, np.integer): np.testing.assert_array_equal(saved[name][j, pi], v)
                else: near(saved[name][j, pi], v)
        np.testing.assert_array_equal(saved['profile_joint_counts'][j], cross(*changes))
        original = data['original'][ids].astype(np.int64); d = original.shape[2]
        near(saved['original_levels'][j], original.sum((0, 1, 2))/(12*n*m*d))
        populated += 1
    return populated


def endpoint_custody(index, sub, cases, data, manifest, extra):
    lookup = {case_key(c): i for i, c in enumerate(cases)}; cache = {}; checked = 0
    source_rows = folder('development', index)/'ROWS.json'
    old_case_path = exchange_folder('development', index)/'CASES.json'
    old_endpoint_path = exchange_folder('development', index)/'ENDPOINTS.npz'
    for p in (source_rows, old_case_path, old_endpoint_path):
        assert sha(p) == manifest[str(p)]; extra[str(p)] = manifest[str(p)]
    rows = {(case_key(r), r['draw']): r for r in read(source_rows)}
    previous_cases = read(old_case_path); previous = arrays(old_endpoint_path)
    previous_lookup = {case_key(c): i for i, c in enumerate(previous_cases)}
    for alias in read(sub/'ALIASES.json'):
        context_key = key(alias); mi = MASKS.index(alias['mask'])
        ids = np.array([lookup[(*context_key, w)] for w in range(16)])
        labels = np.array([[w//4, (w//4+2)%4, mi^1, mi] for w in range(16)]); world = np.arange(16)[:, None]
        for profile in PROFILES:
            for draw, names in enumerate(alias['profiles'][profile]):
                for ai, name in enumerate(names):
                    if name not in cache: cache[name] = arrays(sub/(name+'_body.npz'))
                    observed = cache[name]; probability = []; margin = []
                    for t in TIMES:
                        probability.append(observed[f's{t}_probabilities'][world, labels])
                        scores = observed[f's{t}_scores']; top = np.sort(scores, axis=1)[:, -2:]
                        other = np.where(labels == scores.argmax(axis=1)[:, None], top[:, :1], top[:, 1:])
                        margin.append(scores[world, labels]-other)
                    np.testing.assert_array_equal(data[profile][ids, ai, draw], integer(np.stack(probability, axis=1)))
                    near(data[profile+'_margin'][ids, ai, draw], np.stack(margin, axis=1)); checked += 16
        oldids = np.array([previous_lookup[(*context_key, w)] for w in range(16)])
        for packet in (0, 1):
            np.testing.assert_array_equal(data['continuing'][ids, 2+packet, 0, :5], previous['body'][oldids, packet])
        for draw in range(4):
            original = []; incoming = []; late = []
            for w in range(16):
                row = rows[((*context_key, w), draw)]
                original.append(row['original']); incoming.append(row['incoming']); late.append(row['after_late100'])
            np.testing.assert_array_equal(data['original'][ids, draw], integer(original))
            np.testing.assert_array_equal(data['fresh'][ids, 0, draw, -1], integer(incoming))
            np.testing.assert_array_equal(data['fresh'][ids, 1, draw, -1], integer(late))
    assert len(cache) == read(sub/'CHECK.json')['verification']['physical_continuations']
    return checked


def main():
    tick = time.monotonic(); os.sched_setaffinity(0, {6}); assert os.getpriority(os.PRIO_PROCESS, 0) == 0
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('600-second completion review deadline'))); signal.alarm(600)
    assert read(ROOT/'COMPLETION_PROCESS_CHECK.json')['no_active_jobs']
    assert read(ROOT/'COMPLETION_REVIEW_RESOURCE.json')['admission_pass']
    run = ROOT/'runs/feedback_v1'; complete = read(run/'COMPLETE.json'); frozen = read(ROOT/'FREEZE.json')
    assert complete['status'] == 'COMPLETE' and complete['freeze_sha256'] == sha(ROOT/'FREEZE.json')
    assert complete['seconds'] < frozen['deadline_seconds'] and complete['inputs'] == frozen['inputs'] == inputs()
    write(ROOT/'RESULT_INSPECTION.json', dict(recorded_utc=now(), completion_sha256=sha(run/'COMPLETE.json'),
          completion_precedes_inspection=True, inspection='User-requested status turn; recorded after the initial report read.',
          source_population_already_exposed=True, new_production_feedback_outcomes_now_exposed=True))
    verify(frozen['evidence']); verify(complete['inputs']); verify(complete['outputs'])
    manifest = read(ROOT/'SOURCE_MANIFEST.json'); verify(manifest['evidence'])
    used = {}; extra = {}; blocks = []; reduced = endpoints = 0
    for index in BLOCKS:
        sub = run/f'tissue_{index}'; observed = arrays(sub/'AGGREGATE.npz'); consumed = read(sub/'USED_INPUTS.json')
        assert all(manifest['development'][p] == h for p, h in consumed.items()); used.update(consumed)
        cases, data = read(sub/'CASES.json'), arrays(sub/'ENDPOINTS.npz')
        assert data['continuing'].shape == (1152, 4, 1, 6, 4) and data['fresh'].shape == (1152, 4, 4, 6, 4)
        endpoints += endpoint_custody(index, sub, cases, data, manifest['development'], extra)
        reduced += reduce_block(cases, data, observed); blocks.append(observed)
        print(json.dumps(dict(block=index, elapsed_seconds=time.monotonic()-tick, status='REVIEWED')), flush=True)
    verify(used); verify(extra)
    saved = arrays(run/'SUMMARY.npz'); expected_keys = set(); weights = np.stack([b['records'] for b in blocks])
    for name in blocks[0]:
        stacked = np.stack([b[name] for b in blocks]); expected_keys.add('block_'+name); near(saved['block_'+name], stacked)
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
    assert set(saved) == expected_keys and (run/'REPORT.md').read_text() == analysis.report(saved, 'development')
    panels = {}
    for damage in DAMAGE:
        j = INDEX[f'{damage}|residual|all|all_masks|own']; profiles = {}
        for pi, profile in enumerate(PROFILES):
            contrasts = {}
            for q, name in enumerate(COMPARISONS):
                contrasts[name] = dict(by_time_pp=(100*saved['equal_effects'][j, pi, q, :, 0]).tolist(),
                    block_effects_by_time_pp=(100*saved['block_effects'][:, j, pi, q, :, 0]).tolist(),
                    record_harm_tie_gain_by_time=saved['record_counts'][j, pi, q, :, 0].tolist(),
                    case_harm_tie_gain_by_time=saved['case_counts'][j, pi, q, :, 0].tolist(),
                    draw_harm_tie_gain_by_time=saved['draw_counts'][j, pi, q, :, 0].tolist(),
                    continuous_margin_by_time=saved['equal_margin_effects'][j, pi, q, :, 0].tolist())
            profiles[profile] = dict(contrasts=contrasts, levels_by_time_percent=(100*saved['equal_levels'][j, pi, :, :, 0]).tolist(),
                                    temporal_change_900_to_1000_pp=(100*saved['equal_temporal_change'][j, pi, :, 0]).tolist(),
                                    temporal_harm_tie_gain=saved['temporal_counts'][j, pi, :, 0].tolist())
        panels[damage] = dict(profiles=profiles, inherited_original_recipient_percent=float(100*saved['equal_original_levels'][j, 0]))
    findings = dict(classification='EXPOSED_RECEIVING_FEEDBACK_INTERVENTION', confirmatory=False, blocks=BLOCKS,
                    primary_view='residual|all|all_masks|own; target credit', profiles=PROFILES, arms=ARMS, times=TIMES, signs=SIGNS,
                    independent_population_blocks=4, source_positions=64, injury_cases_per_panel=256,
                    fresh_draws_per_record=4, continuing_draws_per_record=1, new_independent_futures=0,
                    all_cases_and_paired_harms_retained=True, original_matched_forcing=True, panels=panels)
    write(ROOT/'FINDINGS.json', findings); write(ROOT/'REVIEW_EXTRA_INPUTS.json', extra)
    closeout = dict(status='PASS', completed_utc=now(), seconds=time.monotonic()-tick,
                    complete_sha256=sha(run/'COMPLETE.json'), findings_sha256=sha(ROOT/'FINDINGS.json'),
                    review_code_sha256=sha(__file__), extra_inputs_sha256=sha(ROOT/'REVIEW_EXTRA_INPUTS.json'),
                    output_files_verified=len(complete['outputs']), consumed_source_files_verified=len(used),
                    extra_comparison_source_files_verified=len(set(extra)-set(used)),
                    condition_blocks_checked=4*len(CONDITIONS), populated_condition_blocks_independently_reduced=reduced,
                    case_arm_draw_endpoint_vectors_checked=endpoints, continuous_margin_entries_checked=endpoints*6*4,
                    all_summary_arrays_independently_reduced=True, report_reproduced=True,
                    physical_replay='Every physical continuation independently replayed during production; not rerun at closeout.',
                    physical_verification=complete['verification'], production_serial_parallel_not_repeated=True,
                    qualification_serial_parallel_passed=read(ROOT/'runs/qualification_v1/COMPLETE.json')['serial_parallel_bitwise_equal'],
                    study_bytes_at_review=size(), free_bytes_at_review=shutil.disk_usage(ROOT).free)
    space(); write(ROOT/'CLOSEOUT.json', closeout); signal.alarm(0); print(json.dumps(closeout), flush=True)


if __name__ == '__main__':
    try: main()
    except BaseException as error:
        write(ROOT/'COMPLETION_REVIEW_FAILED.json', dict(status='FAILED', recorded_utc=now(), error=repr(error), traceback=traceback.format_exc()))
        raise


