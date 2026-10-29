"""Completion review: independent integer reductions and saved-data custody."""
import itertools, os, signal, sys, time, traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import *
import analysis


def counts(x):
    return np.stack([(x < 0).sum(0), (x == 0).sum(0), (x > 0).sum(0)], axis=-1)


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


def differences(x):
    a, b, c, d, e, f, g, h = [x[:, i] for i in range(8)]
    p, q, r, s = b-a, d-c, f-e, h-g
    out = np.stack([p, q, r, s, c-a, g-e, e-a, g-c, g-a, c-e,
                    d-b, h-f, f-b, h-d, h-b, d-f, g-e-c+a, h-f-d+b,
                    r-p, s-q, q-p, s-r, s-r-q+p, s-p], axis=1)
    if np.issubdtype(out.dtype, np.integer):
        np.testing.assert_array_equal(out[:, 23], out[:, 18]+out[:, 21])
        np.testing.assert_array_equal(out[:, 23], out[:, 20]+out[:, 19])
        np.testing.assert_array_equal(out[:, 22], out[:, 19]-out[:, 18])
        np.testing.assert_array_equal(out[:, 22], out[:, 21]-out[:, 20])
        np.testing.assert_array_equal(out[:, 22], out[:, 17]-out[:, 16])
        for o in (4, 10):
            np.testing.assert_array_equal(out[:, o+4], out[:, o]+out[:, o+3])
            np.testing.assert_array_equal(out[:, o+4], out[:, o+2]+out[:, o+1])
    return out


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
        values = [data[cell][ids].astype(np.int64) for cell in ('CC', 'CF', 'FC', 'FF')]
        nd = values[-1].shape[3]; assert nd == 4 and [v.shape[3] for v in values] == [1, 4, 4, 4]
        # Exact integer numerators in a common denominator, not averaging routines from production.
        summed = np.concatenate([v.sum((1, 3))*(nd//v.shape[3]) for v in values], axis=1)
        delta = differences(summed)
        injury = np.concatenate([v.sum(3)*(nd//v.shape[3]) for v in values], axis=2).reshape(-1, 8, 6, 4)
        paired = np.concatenate([np.repeat(v.sum(1), nd//v.shape[3], axis=2) for v in values], axis=1)
        paired_delta = differences(paired); paired_counts = []
        for q in range(24):
            # Only the CC packet contrast uses its one actual receiving condition.
            paired_counts.append(counts(paired_delta[:, q, :1 if q == 0 else nd].reshape(-1, 6, 4)))
        denominators = np.array([n]+[n*nd]*23, dtype=np.int64)
        np.testing.assert_array_equal(saved['paired_indices'][j], denominators)
        assert np.all(delta[:, [0, 1, 2, 3, 4, 5, 10, 11, 16, 17, 18, 19, 20, 21, 22, 23], 0] == 0)
        margin = np.concatenate([data[cell+'_margin'][ids].sum((1, 3))/v.shape[3]
                                 for cell, v in zip(('CC', 'CF', 'FC', 'FF'), values)], axis=1)
        temporal = summed[:, :, 5]-summed[:, :, 4]
        expected = dict(levels=summed.sum(0)/(12*n*m*nd), effects=delta.sum(0)/(12*n*m*nd),
            margin_levels=margin.sum(0)/(n*m), margin_effects=differences(margin).sum(0)/(n*m),
            record_counts=counts(delta), case_counts=counts(differences(injury)),
            paired_index_counts=np.stack(paired_counts), temporal_change=temporal.sum(0)/(12*n*m*nd),
            temporal_counts=counts(temporal), original_levels=data['original'][ids].astype(np.int64).sum((0, 1, 2))/(12*n*m*nd))
        for name, v in expected.items():
            if np.issubdtype(saved[name].dtype, np.integer): np.testing.assert_array_equal(saved[name][j], v)
            else: near(saved[name][j], v)
        populated += 1
    return populated


def endpoint_custody(index, sub, cases, data, manifest, extra, outputs):
    lookup = {case_key(c): i for i, c in enumerate(cases)}; cache = {}; checked = 0
    previous_dir = prior_folder('development', index)
    for name in ('CASES.json', 'ENDPOINTS.npz'):
        p = previous_dir/name; assert sha(p) == manifest[str(p)]; extra[str(p)] = manifest[str(p)]
    previous_cases = read(previous_dir/'CASES.json'); previous = arrays(previous_dir/'ENDPOINTS.npz')
    previous_lookup = {case_key(c): i for i, c in enumerate(previous_cases)}
    for c in cases: assert c == previous_cases[previous_lookup[case_key(c)]]
    links = read(sub/'ALIASES.json')
    assert len(links) == 72 and {key(a) for a in links} == set(itertools.product(DAMAGE, FAMILIES, MASKS, SOURCES))
    for alias in links:
        context_key = key(alias); mi = MASKS.index(alias['mask'])
        ids = np.array([lookup[(*context_key, w)] for w in range(16)])
        labels = np.array([[w//4, (w//4+2)%4, mi^1, mi] for w in range(16)]); world = np.arange(16)[:, None]
        for cell in ('CC', 'CF', 'FC', 'FF'):
            assert len(alias['cells'][cell]) == (1 if cell == 'CC' else 4)
            for draw, names in enumerate(alias['cells'][cell]):
                assert len(names) == 2
                for packet, name in enumerate(names):
                    if name not in cache:
                        path = sub/(name+'_body.npz'); obs = arrays(path); info = read(sub/(name+'.json'))
                        assert info['proof'] == dict(native_arrays=24, body_scores=6, max_native_error=0., rng_match=True)
                        assert info['arrays']['body'] == identities(obs)
                        assert info['files'] == dict(state=outputs[str(sub/(name+'.npz'))], body=outputs[str(path)])
                        meta = info['metadata']; assert meta['feedback'] is False and meta['c_m'] == 0 and meta['rho'] == .002
                        assert meta['write_updates'] == 0 and meta['updates'] == meta['packet_hold_checks'] == 1000
                        cache[name] = (obs, meta)
                    observed, meta = cache[name]
                    continuing = cell in ('CC', 'FC')
                    assert meta['profile'] == ('continuing' if continuing else 'fresh')
                    assert meta['address'] == (address(index) if continuing else reader_address('development', index, draw))
                    probability = []; margin = []
                    for t in TIMES:
                        probability.append(observed[f's{t}_probabilities'][world, labels])
                        scores = observed[f's{t}_scores']; top = np.sort(scores, axis=1)[:, -2:]
                        other = np.where(labels == scores.argmax(axis=1)[:, None], top[:, :1], top[:, 1:])
                        margin.append(scores[world, labels]-other)
                    np.testing.assert_array_equal(data[cell][ids, packet, draw], integer(np.stack(probability, axis=1)))
                    near(data[cell+'_margin'][ids, packet, draw], np.stack(margin, axis=1)); checked += 16
        oldids = np.array([previous_lookup[(*context_key, w)] for w in range(16)])
        for cell, profile in (('CC', 'continuing'), ('FF', 'fresh')):
            exact(data[cell][ids], previous[profile][oldids, :2], 'TT043 baseline endpoint')
            exact(data[cell+'_margin'][ids], previous[profile+'_margin'][oldids, :2], 'TT043 baseline continuous margin')
        exact(data['original'][ids], previous['original'][oldids], 'inherited original comparator')
    assert len(cache) == read(sub/'CHECK.json')['verification']['physical_continuations']
    return checked


def main():
    tick = time.monotonic(); os.sched_setaffinity(0, {6}); assert os.getpriority(os.PRIO_PROCESS, 0) == 0
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('600-second completion review deadline'))); signal.alarm(600)
    assert read(ROOT/'COMPLETION_PROCESS_CHECK.json')['no_active_jobs']
    assert read(ROOT/'COMPLETION_REVIEW_RESOURCE.json')['admission_pass']
    run = ROOT/'runs/crossover_v1'; complete = read(run/'COMPLETE.json'); frozen = read(ROOT/'FREEZE.json')
    assert complete['status'] == 'COMPLETE' and complete['freeze_sha256'] == sha(ROOT/'FREEZE.json')
    assert complete['seconds'] < frozen['deadline_seconds'] and complete['inputs'] == frozen['inputs'] == inputs()
    write(ROOT/'RESULT_INSPECTION.json', dict(recorded_utc=now(), completion_sha256=sha(run/'COMPLETE.json'),
          completion_precedes_inspection=True, inspection='User-requested status turn; recorded after initial report read.',
          source_population_already_exposed=True, new_production_crossed_outcomes_now_exposed=True))
    verify(frozen['evidence']); verify(complete['inputs']); verify(complete['outputs'])
    manifest = read(ROOT/'SOURCE_MANIFEST.json'); verify(manifest['evidence'])
    used = {}; extra = {}; blocks = []; reduced = endpoints = 0
    for index in BLOCKS:
        sub = run/f'tissue_{index}'; observed = arrays(sub/'AGGREGATE.npz'); consumed = read(sub/'USED_INPUTS.json')
        assert all(manifest['development'][p] == h for p, h in consumed.items()); used.update(consumed)
        cases, data = read(sub/'CASES.json'), arrays(sub/'ENDPOINTS.npz')
        for cell in CELLS: assert data[cell].shape == (1152, 2, 1 if cell == 'CC' else 4, 6, 4)
        endpoints += endpoint_custody(index, sub, cases, data, manifest['development'], extra, complete['outputs'])
        reduced += reduce_block(cases, data, observed); blocks.append(observed)
        print(json.dumps(dict(block=index, elapsed_seconds=time.monotonic()-tick, status='REVIEWED')), flush=True)
    verify(used); verify(extra)
    saved = arrays(run/'SUMMARY.npz'); expected_keys = set(); weights = np.stack([b['records'] for b in blocks])
    for name in blocks[0]:
        stacked = np.stack([b[name] for b in blocks]); expected_keys.add('block_'+name)
        if np.issubdtype(stacked.dtype, np.integer):
            np.testing.assert_array_equal(saved['block_'+name], stacked)
            np.testing.assert_array_equal(saved[name], stacked.sum(0)); expected_keys.add(name)
        else:
            near(saved['block_'+name], stacked); equal = np.full_like(stacked[0], np.nan); pooled = equal.copy()
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
        j = INDEX[f'{damage}|residual|all|all_masks|own']; contrasts = {}
        for q, name in enumerate(COMPARISONS):
            contrasts[name] = dict(by_time_pp=(100*saved['equal_effects'][j, q, :, 0]).tolist(),
                block_effects_by_time_pp=(100*saved['block_effects'][:, j, q, :, 0]).tolist(),
                record_harm_tie_gain_by_time=saved['record_counts'][j, q, :, 0].tolist(),
                case_harm_tie_gain_by_time=saved['case_counts'][j, q, :, 0].tolist(),
                paired_index_harm_tie_gain_by_time=saved['paired_index_counts'][j, q, :, 0].tolist(),
                paired_index_denominator=int(saved['paired_indices'][j, q]),
                continuous_margin_by_time=saved['equal_margin_effects'][j, q, :, 0].tolist())
        panels[damage] = dict(contrasts=contrasts, levels_by_time_percent=(100*saved['equal_levels'][j, :, :, 0]).tolist(),
            temporal_change_900_to_1000_pp=(100*saved['equal_temporal_change'][j, :, 0]).tolist(),
            temporal_harm_tie_gain=saved['temporal_counts'][j, :, 0].tolist(),
            inherited_original_recipient_percent=float(100*saved['equal_original_levels'][j, 0]))
    findings = dict(classification='EXPOSED_RECEIVING_STATE_FORCING_CROSSOVER', confirmatory=False, blocks=BLOCKS,
        primary_view='residual|all|all_masks|own; target credit', cells=CELLS, arms=ARMS, times=TIMES, signs=SIGNS,
        feedback_gain=0., independent_population_blocks=4, source_positions=64, injury_cases_per_panel=256,
        actual_indices=dict(CC=1, CF=4, FC=4, FF=4), new_independent_futures=0, paired_not_cartesian=True,
        all_cases_and_paired_harms_retained=True, reused_forcing_streams=True, panels=panels)
    write(ROOT/'FINDINGS.json', findings); write(ROOT/'REVIEW_EXTRA_INPUTS.json', extra)
    closeout = dict(status='PASS', completed_utc=now(), seconds=time.monotonic()-tick,
        complete_sha256=sha(run/'COMPLETE.json'), findings_sha256=sha(ROOT/'FINDINGS.json'),
        review_code_sha256=sha(__file__), extra_inputs_sha256=sha(ROOT/'REVIEW_EXTRA_INPUTS.json'),
        output_files_verified=len(complete['outputs']), consumed_source_files_verified=len(used),
        extra_comparison_source_files_verified=len(set(extra)-set(used)),
        condition_blocks_checked=4*len(CONDITIONS), populated_condition_blocks_independently_reduced=reduced,
        case_packet_index_endpoint_vectors_checked=endpoints, continuous_margin_entries_checked=endpoints*6*4,
        all_summary_arrays_independently_reduced=True, report_reproduced=True, actual_CC_denominators_verified=True,
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

