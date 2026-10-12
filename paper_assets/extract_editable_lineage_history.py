#!/usr/bin/env python3
"""Extract the declared P11 history from saved arrays, without model imports."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SELECTION = ROOT / 'paper_assets/data/reconstruction-history-selection-v1.json'
RUN = 'paper-editable-lineage-20260915T125104Z-teji03a9'
DEFAULT = Path('/mnt/bioIce1/runs/runs') / RUN
CASES = ('write_M__M_open__fine', 'before__written__open__fine',
         'rewrite_E__written__E_open__fine', 'after__written__E_open__open__fine')
DEST = ROOT / 'paper_assets/data'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=DEFAULT)
    run = parser.parse_args().source_root.resolve()
    selection = json.loads(SELECTION.read_text())['P11']
    check(selection['run'] == RUN and selection['fine'], 'Unexpected editorial selection')
    summary = json.loads((run / 'summary.json').read_text())
    audit = json.loads((run / 'independent_audit.json').read_text())
    check(summary['stage'] == 'finished' and summary['all_execution_valid'], 'Incomplete run')
    check(audit['quality_gate'] and audit['ready_for_interpretation'], 'Saved audit did not qualify')
    check(len(summary['cases']) == 74 and audit['integration_calls'] == 434, 'Wrong campaign')
    check(summary['config']['experiment'] == 'P11_editable_lineage', 'Wrong experiment')
    paths = [run / 'summary.json', run / 'independent_audit.json']
    for filename in ('run_paper_editable_lineage.py', 'paper_editable_lineage_design.py',
                     'analyze_paper_memory.py', 'analyze_paper_editable_lineage.py',
                     'PAPER_EDITABLE_LINEAGE_PROTOCOL.md', 'paper_editable_lineage_v1.json'):
        path = run / 'frozen' / filename
        check(sha(path) == summary['frozen_hashes_sha256'][filename], f'Frozen source mismatch: {filename}')
        paths.append(path)
    for stage, expected in summary['gate_hashes'].items():
        path = run / (stage + '_audit.json')
        check(sha(path) == expected, f'Stage audit hash mismatch: {stage}')
        paths.append(path)

    data, phases, last = {}, [], {}
    continuity_checks, label_checks = 0, 0
    case_records = []
    for case in CASES:
        path = run / case / 'result.json'
        declared = next(x for x in summary['cases'] if x['id'] == case)
        check(sha(path) == declared['result_sha256'], f'Result hash mismatch: {case}')
        result = json.loads(path.read_text())
        check(result == declared['result'], f'Embedded result differs: {case}')
        check(result['ion_indices']['miR200_total'] == 5 and
              result['ion_indices']['Zeb_mRNA_total'] == 6, 'Unexpected regulator indices')
        paths.append(path)
        case_records.append({k: result[k] for k in ('case', 'source_case', 'source_phase', 'rounds')})
        kind = result['case']['kind']
        for saved in result['phases']:
            name = saved['phase']
            path = run / case / (name + '.npz')
            check(sha(path) == saved['sha256'], f'Phase hash mismatch: {case}/{name}')
            paths.append(path)
            key = f'phase_{len(phases):02d}'
            with np.load(path, allow_pickle=False) as archive:
                times = archive['times'].copy()
                states = archive['concentrations'].copy()
                initial, final = archive['initial'].copy(), archive['final'].copy()
            start, end = saved['logical_interval']
            ids = saved['setup']['cell_ids']
            check(states.shape == (len(times), 17, len(ids)), f'Invalid state shape: {name}')
            check(np.isfinite(states).all(), f'Nonfinite state: {name}')
            check(np.array_equal(times, np.arange(0, end - start + 1, 100)), f'Invalid saved clock: {name}')
            check(saved['clock']['maximum_step'] == 50, 'Expected finer resolution')
            np.testing.assert_array_equal(states[0], initial)
            np.testing.assert_array_equal(states[-1], final)
            # Frozen classifier: M if Zeb > miR200+2, E if miR200 > Zeb+2.
            mir, zeb = states[:, 5, :], states[:, 6, :]
            delta = mir - zeb
            labels = np.where(zeb > mir + 2, 'M', np.where(mir > zeb + 2, 'E', 'X'))
            check(''.join(labels[-1]) == saved['final_labels'], f'Final-label mismatch: {name}')
            check(np.array_equal(labels, np.where(delta > 2, 'E', np.where(delta < -2, 'M', 'X'))),
                  f'Subtraction changes a threshold classification: {name}')
            label_checks += 1
            for i, identity in enumerate(ids):
                if identity in last and last[identity][0] == start:
                    np.testing.assert_array_equal(last[identity][1], initial[:, i])
                    continuity_checks += 1
                last[identity] = (end, final[:, i].copy())
            # The three target/pupil cells are last; teachers/cues are retained in the extract too.
            target_indices = list(range(len(ids) - 3, len(ids)))
            panel = ('founders' if kind == 'write_M' else 'rewrite' if kind == 'rewrite_E'
                     else name.split('_', 1)[0])
            data[key + '_times'] = times
            data[key + '_states'] = states
            data[key + '_delta'] = delta
            phases.append({'key': key, 'case': case, 'name': name, 'panel': panel,
                           'logical_interval': [start, end], 'cell_ids': ids,
                           'target_indices': target_indices,
                           'target_cell_ids': [ids[i] for i in target_indices],
                           'isolated': saved['setup']['isolated'],
                           'scheduled_pupils': saved['setup'].get('scheduled_pupils'),
                           'source_sha256': saved['sha256'], 'final_labels': saved['final_labels']})
    check(len(phases) == 42 and phases[-1]['logical_interval'][1] == 680000, 'Incomplete selected lineage')
    for a, b in zip(phases, phases[1:]):
        check(a['logical_interval'][1] == b['logical_interval'][0], 'Non-contiguous logical clock')
    check(continuity_checks == 177, 'Unexpected number of same-cell state handoffs')
    # Compare all 17 entries at cross-case transitions, including R3 -> rewrite -> R4 teacher.
    for left, right, destination in ((2, 3, slice(0, 3)), (20, 21, slice(6, 9)), (23, 24, slice(0, 3))):
        a, b = phases[left], phases[right]
        check(a['target_cell_ids'] == b['cell_ids'][destination], 'Cross-case cell identities differ')
        np.testing.assert_array_equal(data[a['key'] + '_states'][-1],
                                      data[b['key'] + '_states'][0, :, destination])
    output = DEST / 'retained-editable-lineage-v1.npz'
    np.savez_compressed(output, **data)
    record = {
        'schema': 'forms_retained_p11_history_v1', 'selection': selection,
        'selection_file': str(SELECTION.relative_to(ROOT)), 'selection_sha256': sha(SELECTION),
        'archive_root': str(run), 'original_archive_root': audit['run'],
        'sources': [{'path': str(p), 'sha256': sha(p), 'bytes': p.stat().st_size} for p in paths],
        'data': str(output.relative_to(ROOT)), 'data_sha256': sha(output),
        'classifier': {'expression': 'total miR200 - total Zeb mRNA', 'indices': [5, 6],
                       'E': '> 2', 'M': '< -2', 'X': '[-2, 2]', 'units': 'model concentration units'},
        'clock': {'saved_interval': 100, 'maximum_step': 50, 'logical_horizon': 680000,
                  'units': 'model time units; initial 1000-unit stock preparation excluded'},
        'checks': {'phase_hashes': 42, 'result_hashes': 4, 'final_labels': label_checks,
                   'same_cell_full_state_handoffs': continuity_checks,
                   'cross_case_full_state_handoffs': 3, 'all_saved_times_regular': True},
        'case_records': case_records, 'phases': phases,
        'display': 'All saved samples for all three target/pupil cells in each panel; actual IDs retained. Lines join samples within a cell, never different cells across replacement.',
        'scope': 'Static selected-chain extraction and integrity checks, not a rerun of the complete independent campaign audit or a new success-rate analysis.',
        'extractor': str(Path(__file__).relative_to(ROOT)), 'extractor_sha256': sha(Path(__file__)),
        'new_simulations': 0, 'new_statistical_tests': 0,
    }
    output.with_suffix('.json').write_text(json.dumps(record, indent=2) + '\n')
    print(f'Extracted 42 P11 phases; 4 result hashes, 42 phase hashes, {continuity_checks} same-cell handoffs verified.')
    print(f'Portable arrays: {output.stat().st_size:,} bytes; no scientific model executed.')


if __name__ == '__main__':
    main()
