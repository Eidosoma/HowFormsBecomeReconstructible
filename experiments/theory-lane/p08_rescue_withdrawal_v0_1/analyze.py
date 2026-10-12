"""Descriptive saved-output analysis with independent temporal scoring and linkage checks."""
import time
import numpy as np
import writer_audit
from common import ROOT, arrays, equal, read, sha, stamp, write

BRANCHES = ['no_rescue', 'rescue_then_withdraw', 'continued_repair']


def paired(left, right):
    return dict(both=int(np.count_nonzero(left & right)), left_only=int(np.count_nonzero(left & ~right)),
                right_only=int(np.count_nonzero(~left & right)), neither=int(np.count_nonzero(~left & ~right)),
                difference_count=int(left.sum()) - int(right.sum()))


def totals(values):
    return {name: int(values[:, i].sum()) for i, name in enumerate(BRANCHES)}


def summarize(folder, rows, begin, cpu_begin):
    protocol = read(ROOT / 'PROTOCOL.json')
    selection = read(ROOT / 'SELECTION.json')
    cfg = read(ROOT / 'source_config.json')
    assert len(rows) == len(selection['events']) == 46 and protocol['horizon'] == 18
    good_all, opposite_all, first_failures, records = [], [], [], []
    source_checks = 0
    for event, row in zip(selection['events'], rows, strict=True):
        data = arrays(folder / row['file'], row['sha256'])
        source = arrays(ROOT / event['fixture'], event['fixture_sha256'])
        assert (row['block'], row['case'], row['generation']) == (event['block'], event['case'], event['generation'])
        equal(data['generation'], np.arange(event['generation'], event['generation'] + 19), 'relative follow-up')
        equal(data['incoming'][1:], data['outgoing'][:-1], 'own written successors')
        equal(data['incoming'][0], np.repeat(source['incoming'][None], 3, axis=0), 'same boundary input')
        equal(data['prepared'][0], source['packets'][[0, 1, 1]], 'saved boundary interventions')
        equal(data['end'][0], source['end'][[0, 1, 1]], 'saved boundary bodies')
        equal(data['birth'][0], source['birth'], 'saved reset')
        equal(data['mask'][0], source['mask'], 'saved injury')
        equal(data['outgoing'][0, 0], source['source_factual_outgoing'], 'saved factual write')
        equal(data['outgoing'][0, 1], data['outgoing'][0, 2], 'identical rescued branches')
        equal(data['prepared'][1:, :2], data['incoming'][1:, :2], 'no hidden future repair')
        expected_applied = np.tile([False, False, True], (19, 1))
        expected_applied[0] = [False, True, True]
        equal(data['applied'], expected_applied, 'repair timing')
        assert data['applied'].sum(axis=0).tolist() == [0, 1, 19]
        assert data['port_windows'].shape == (19, 32, 3, 2, 2)
        means = np.zeros((19, 3, 2, 2))
        for t in range(32):
            means += data['port_windows'][:, t]
        means /= 32
        equal(means, data['mean_ports'], 'independent observed-window means')
        rule = 1 if event['case'] // 4 in (0, 2) else -1
        aligned = np.empty_like(means)
        for cue in range(2):
            for port in range(2):
                aligned[:, :, cue, port] = means[:, :, cue, port] * rule * (1 if cue == port else -1)
        margins = np.minimum.reduce([aligned[:, :, 0, 0], aligned[:, :, 0, 1], aligned[:, :, 1, 0], aligned[:, :, 1, 1]])
        opposite = -np.maximum.reduce([aligned[:, :, 0, 0], aligned[:, :, 0, 1], aligned[:, :, 1, 0], aligned[:, :, 1, 1]])
        equal(margins, data['min_margin'], 'independent task margins')
        equal(opposite, data['opposite_margin'], 'independent opposite margins')
        good = margins > .25
        equal(good, data['both_pass'], 'strict scoring')
        equal(opposite > .25, data['opposite_pass'], 'strict opposite scoring')
        assert good[0].tolist() == [False, True, True]
        for gi in range(19):
            pair = writer_audit.writer_pair(data['end'][gi], writer_audit.available_edges(data['mask'][gi]),
                cfg['development_config']['writer_beta'], cfg['tolerance'])
            packet = np.ascontiguousarray(pair['exact'], dtype='<f8').view(np.uint8).reshape(3, 4096)
            equal(packet, data['outgoing'][gi], 'separate saved-body writer')
        future = good[1:]
        good_all.append(future)
        opposite_all.append((opposite > .25)[1:])
        failures = [next((j + 1 for j in range(18) if not future[j, v]), None) for v in range(3)]
        first_failures.append(failures)
        records.append(dict(block=event['block'], case=event['case'], generation=event['generation'],
            history=event['history'], once_uninterrupted=event['once_uninterrupted'],
            first_successor=future[0].tolist(), terminal=future[-1].tolist(),
            uninterrupted=[bool(all(future[:, v])) for v in range(3)], first_failure_offset=failures))
        source_checks += 1
    good = np.stack(good_all)
    opposite = np.stack(opposite_all)
    uninterrupted = np.logical_and.accumulate(good, axis=1)
    final = uninterrupted[:, -1]
    subgroup = np.array([r['once_uninterrupted'] for r in records], bool)
    assert subgroup.sum() == 20
    elapsed, cpu = time.monotonic() - begin, time.process_time() - cpu_begin
    result = dict(status='COMPLETE', at_utc=stamp(), seconds=elapsed, cpu_seconds=cpu,
        contexts=46, source_blocks=36, horizon=18, branches=BRANCHES,
        first_successor=totals(good[:, 0]), uninterrupted=totals(final), terminal=totals(good[:, -1]),
        uninterrupted_by_offset=[dict(offset=j + 1, **totals(uninterrupted[:, j])) for j in range(18)],
        current_success_by_offset=[dict(offset=j + 1, **totals(good[:, j])) for j in range(18)],
        opposite_success_by_offset=[dict(offset=j + 1, **totals(opposite[:, j])) for j in range(18)],
        paired_uninterrupted=dict(rescue_vs_none=paired(final[:, 1], final[:, 0]),
                                 continued_vs_withdrawal=paired(final[:, 2], final[:, 1])),
        by_history={h: totals(final[np.array([r['history'] == h for r in records])]) for h in cfg['histories']},
        once_better_subgroup=dict(contexts=20, first_successor=totals(good[subgroup, 0]),
            uninterrupted=totals(final[subgroup]), terminal=totals(good[subgroup, -1])),
        records=records, raw_files=rows, source_complete_sha256=selection['source_complete_sha256'],
        boundary_complete_sha256=selection['boundary_complete_sha256'], selection_sha256=sha(ROOT / 'SELECTION.json'),
        frozen_sha256=sha(ROOT / 'FROZEN.json'), original_prospective_verdict='UNRESOLVED',
        scientific_status='POST_HOC_SELECTED_STATE_MECHANISM_STUDY', interpretation=protocol['interpretation'],
        automatic_successor=False)
    write(folder / 'VERIFICATION.json', dict(status='PASS', at_utc=stamp(),
        own_successor_chains=46, boundary_sources_checked=source_checks, independently_recounted_future_reads=2484,
        independent_flat_reads_during_run=sum(r['independent_flat_reads'] for r in rows),
        independent_optimizers_during_run=sum(r['independent_optimizers'] for r in rows),
        independently_checked_captures=2622, all_raw_hashes_checked=True, original_prospective_verdict='UNRESOLVED'))
    assert sum(r['independent_flat_reads'] for r in rows) == 2484
    assert sum(r['independent_optimizers'] for r in rows) == 828
    lines = ['Rescue withdrawal and successor competence', '',
        f'After 18 additional rebuilds, uninterrupted successor success was {result["uninterrupted"]["rescue_then_withdraw"]}/46 after one rescue and withdrawal, {result["uninterrupted"]["no_rescue"]}/46 without rescue, and {result["uninterrupted"]["continued_repair"]}/46 with continued repair.', '',
        'Each branch inherited its own packet written by the original writer and began each successor read in a fresh body. All branches shared injury and cue forcing at the same absolute generation. Follow-up continued after failures.', '',
        'Branch | First successor | Uninterrupted through 18 | Success at 18 | Repair calls including boundary',
        '--- | ---: | ---: | ---: | ---:']
    for i, name in enumerate(BRANCHES):
        lines.append(f'{name} | {result["first_successor"][name]}/46 | {result["uninterrupted"][name]}/46 | {result["terminal"][name]}/46 | {[0, 1, 19][i]}')
    lines += ['', 'The endpoint excludes the already known rescue read for every branch. A terminal success after an earlier failure is recovery, not uninterrupted competence. These 46 states were selected from 36 blocks because the original six-call branch failed and a current repair rescued it; the findings describe this selected panel.', '',
        'Every future read matched the separate flat dynamics implementation, every future optimizer matched its separate implementation, and every written successor was checked against the separate writer calculation. All raw windows, scores, repair schedules and chain links passed the output audit.', '',
        protocol['interpretation'], '',
        'The original prospective doubled-efficiency verdict remains UNRESOLVED. These call budgets differ and do not test a fixed-budget adaptive policy. No successor experiment was launched.', '',
        f'Runtime: {elapsed / 60:.2f} minutes wall and {cpu / 60:.2f} minutes CPU, one numerical thread.', '',
        'Evidence: [frozen protocol](../PROTOCOL.json), [frozen inputs](../FROZEN.json), [selection](../SELECTION.json), [verification](VERIFICATION.json), [results](COMPLETE.json).', '']
    with (folder / 'REPORT.md').open('x') as f:
        f.write('\n'.join(lines))
    write(folder / 'EXPOSURE_AND_DECISIONS.json', dict(at_utc=stamp(),
        prior_exposure='All source schedules through generation 32 and all 46 immediate rescue outcomes known before design.',
        newly_exposed='All 46 paired successor chains, including forcing realizations after generation 32.',
        study_status='Post-hoc mechanism study with continuation design frozen before new rescued-chain outcomes.',
        hypothesis_limits=protocol['interpretation'], original_prospective_verdict='UNRESOLVED', automatic_successor=False))
    result['files_sha256'] = {p.name: sha(p) for p in folder.iterdir() if p.is_file() and p.name not in
                             ('STATUS.json', 'console.log', 'admission.log')}
    write(folder / 'COMPLETE.json', result)
    return result
