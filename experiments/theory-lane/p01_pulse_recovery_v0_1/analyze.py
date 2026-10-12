"""Fixed descriptive recovery analysis; no fitted prediction model."""
import csv
from itertools import product
import json
from pathlib import Path

import numpy as np

from extract import HERE, read, sha, stamp, write_json

INTEGER = {'block', 'generation', 'founder', 'recipient', 'body_pass', 'terminal_success'}
TEXT = {'writer', 'active_writer'}
METRICS = ('body_margin', 'body_pass', 'body_margin_minus_original', 'signed_transfer',
    'unsigned_access', 'transfer_minus_original', 'abs_transfer_gap_original',
    'reader_distance_original', 'reader_action_distance_same_body_original',
    'counterfactual_original_transfer', 'body_mean_abs_cue_difference',
    'hypothetical_tolerance_substitution_fraction', 'hypothetical_sign_flip_fraction')
O, T, S, M, P = ('exact_rewrite', 'tolerance_rewrite', 'sign_restored',
                 'magnitude_restored', 'single_tolerance_rewrite')


def write_csv(path, rows):
    with path.open('x', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def load_rows():
    folder = HERE / 'results'
    done = read(folder / 'EXTRACTION_COMPLETE.json')
    assert done['status'] == 'COMPLETE' and not (folder / 'FAILED.json').exists()
    assert sha(folder / 'lineages.csv') == done['outputs_sha256']['lineages.csv']
    with (folder / 'lineages.csv').open(newline='') as f:
        return [{k: v if k in TEXT else int(v) if k in INTEGER else float(v)
                 for k, v in row.items()} for row in csv.DictReader(f)]


def main():
    cfg, rows = read(HERE / 'config.json'), load_rows()
    folder = HERE / 'results'
    names, blocks, generations = cfg['writers'], cfg['blocks'], cfg['generations']
    data = {(r['block'], r['generation'], r['writer'], r['founder'], r['recipient']): r for r in rows}
    expected = set(product(blocks, generations, names, range(4), range(4)))
    assert len(data) == len(rows) == len(expected) and set(data) == expected
    block_rows, group_map = [], {}
    for b, g, w in product(blocks, generations, names):
        group = [data[b, g, w, f, r] for f, r in product(range(4), repeat=2)]
        record = dict(block=b, generation=g, writer=w, active_writer=group[0]['active_writer'], n=16,
                      body_successes=sum(r['body_pass'] for r in group))
        record.update({k: float(np.mean([r[k] for r in group])) for k in METRICS})
        block_rows.append(record)
        group_map[b, g, w] = record
    write_csv(folder / 'block_timecourses.csv', block_rows)
    curves = []
    for g, w in product(generations, names):
        group = [group_map[b, g, w] for b in blocks]
        curves.append(dict(generation=g, writer=w, n=128,
            body_successes=sum(r['body_successes'] for r in group),
            metrics={k: dict(mean=float(np.mean([r[k] for r in group])),
                block_values=[r[k] for r in group]) for k in METRICS}))

    paired = []
    for g, baseline in product(generations, (O, T)):
        folds = []
        for b in blocks:
            counts = dict(both_pass=0, rescued=0, harmed=0, both_fail=0)
            for f, r in product(range(4), repeat=2):
                candidate, reference = data[b, g, P, f, r], data[b, g, baseline, f, r]
                label = {(1, 1): 'both_pass', (1, 0): 'rescued', (0, 1): 'harmed', (0, 0): 'both_fail'}[
                    candidate['body_pass'], reference['body_pass']]
                counts[label] += 1
            folds.append(dict(block=b, paired_counts=counts,
                differences={k: group_map[b, g, P][k]-group_map[b, g, baseline][k] for k in METRICS}))
        paired.append(dict(generation=g, candidate=P, baseline=baseline, blocks=folds,
            paired_counts={k: sum(f['paired_counts'][k] for f in folds) for k in counts},
            differences={k: float(np.mean([f['differences'][k] for f in folds])) for k in METRICS}))

    recovery = []
    for first, last in cfg['recovery_comparisons']:
        for w in (P, T):
            for metric in ('reader_distance_original', 'abs_transfer_gap_original'):
                changes = [group_map[b, last, w][metric]-group_map[b, first, w][metric] for b in blocks]
                recovery.append(dict(writer=w, metric=metric, first_generation=first, last_generation=last,
                    initial_mean=float(np.mean([group_map[b, first, w][metric] for b in blocks])),
                    final_mean=float(np.mean([group_map[b, last, w][metric] for b in blocks])),
                    mean_change=float(np.mean(changes)), block_changes=changes,
                    blocks_decreased=sum(v < 0 for v in changes), blocks_increased=sum(v > 0 for v in changes),
                    blocks_unchanged=sum(v == 0 for v in changes)))

    recovery_times, terminal_strata, ever_failures = [], {}, {}
    for b, f, r in product(blocks, range(4), range(4)):
        if data[b, 4, O, f, r]['body_pass'] and not data[b, 4, P, f, r]['body_pass']:
            first_pass = next((g for g in range(5, 33) if data[b, g, P, f, r]['body_pass']), None)
            recovery_times.append(dict(block=b, founder=f, recipient=r, first_later_body_pass=first_pass,
                censored_at_generation_32=first_pass is None))
        po, oo = (data[b, 3, w, f, r]['terminal_success'] for w in (P, O))
        stratum = {(1, 1): 'both_pass', (1, 0): 'pulse_only', (0, 1): 'original_only', (0, 0): 'both_fail'}[po, oo]
        terminal_strata.setdefault(stratum, []).append((b, f, r))
    strata_rows = []
    for name, ids in terminal_strata.items():
        for g in (3, 4, 6):
            group = [data[b, g, P, f, r] for b, f, r in ids]
            strata_rows.append(dict(stratum=name, generation=g, n=len(ids),
                body_successes=sum(r['body_pass'] for r in group),
                metrics={k: dict(mean=float(np.mean([r[k] for r in group])),
                    minimum=min(r[k] for r in group), maximum=max(r[k] for r in group)) for k in METRICS}))
    for w in names:
        ids = [(b, f, r) for b, f, r in product(blocks, range(4), range(4))
               if any(not data[b, g, w, f, r]['body_pass'] for g in range(4, 33))]
        ever_failures[w] = dict(ever_failed_body=len(ids), never_failed_body=128-len(ids),
            terminal_successes=sum(data[b, 3, w, f, r]['terminal_success'] for b, f, r in product(blocks, range(4), range(4))),
            failed_body_but_passed_terminal=sum(data[b, 3, w, f, r]['terminal_success'] for b, f, r in ids))
    harmed = []
    for b, f, r in terminal_strata.get('original_only', []):
        harmed.append(dict(block=b, founder=f, recipient=r,
            pulse_failed_body_generations=[g for g in range(4, 33) if not data[b, g, P, f, r]['body_pass']],
            original_failed_body_generations=[g for g in range(4, 33) if not data[b, g, O, f, r]['body_pass']],
            early_pulse_measurements=[{k: data[b, g, P, f, r][k] for k in ('generation', *METRICS)} for g in (3, 4, 6)],
            terminal_pulse_margin=data[b, 3, P, f, r]['terminal_margin'],
            terminal_original_margin=data[b, 3, O, f, r]['terminal_margin']))
    summary = dict(status='DEVELOPMENT_RECOVERY_ANALYSIS', created_at_utc=stamp(), blocks=blocks,
        rows=len(rows), independent_unit='block', no_prediction_model_fitted=True,
        terminal_label_not_used_to_define_diagnostics=True, curves=curves,
        paired_body_comparisons=paired, declared_recovery_comparisons=recovery,
        early_pulse_impairment_recovery=recovery_times,
        terminal_strata={k: len(terminal_strata.get(k, [])) for k in ('both_pass', 'pulse_only', 'original_only', 'both_fail')},
        early_measurements_by_terminal_stratum=strata_rows,
        body_failure_and_terminal_success=ever_failures, all_terminal_harmed_lineages=harmed,
        csv_sha256={n: sha(folder / n) for n in ('lineages.csv', 'block_timecourses.csv')})
    write_json(folder / 'analysis.json', summary)
    print(json.dumps(dict(recovery=recovery, early_impaired=len(recovery_times),
        terminal_strata=summary['terminal_strata'], body_failure_and_terminal_success=ever_failures), indent=2))
    for g in (3, 4, 5, 6, 8, 16, 32):
        print('generation', g, [(r['writer'], r['body_successes'],
            r['metrics']['signed_transfer']['mean'], r['metrics']['reader_distance_original']['mean'])
            for r in curves if r['generation'] == g])


if __name__ == '__main__':
    main()
