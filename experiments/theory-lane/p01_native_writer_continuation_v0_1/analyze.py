"""Predeclared paired native endpoints; called by the worker after full replay."""
import csv
import json
from pathlib import Path

import numpy as np

from evidence import descriptor, sha, stamp, write_json


def read_cases(path):
    with np.load(path, allow_pickle=False) as f:
        index = json.loads(f['__index__'].tobytes())
        values = {name: f[name] for name in index}
    for name, array in values.items():
        assert descriptor(array) == index[name]
    return values


def paired_table(candidate, baseline):
    assert candidate.shape == baseline.shape and candidate.dtype == baseline.dtype == bool
    return dict(both_pass=int((candidate & baseline).sum()),
                rescued=int((candidate & ~baseline).sum()),
                harmed=int((~candidate & baseline).sum()),
                both_fail=int((~candidate & ~baseline).sum()))


def summarize(cases, cfg):
    assert len(cases) == len(cfg['blocks'])
    names = cfg['writers']+['erased']
    endpoint = np.stack([case['assay_both_pass'] for case in cases])
    margins = np.stack([case['assay_min_margin'] for case in cases])
    expected = (len(cfg['blocks']), 4, 4, cfg['config']['recipients'], 3)
    assert endpoint.shape == margins.shape == expected
    assert endpoint.dtype == bool and np.isfinite(margins).all()
    rates, comparisons = [], []
    for j, injury in enumerate(cfg['injuries']):
        for n, name in enumerate(names):
            block_rates = endpoint[:, n, :, :, j].mean(axis=(1, 2))
            rates.append(dict(writer=name, injury=injury, successes=int(endpoint[:, n, :, :, j].sum()),
                n=int(endpoint[:, n, :, :, j].size), mean_block_success=float(block_rates.mean()),
                block_success=[int(x.sum()) for x in endpoint[:, n, :, :, j]],
                block_rates=block_rates.tolist(), mean_margin=float(margins[:, n, :, :, j].mean())))
        for candidate_name, baseline_name in [cfg['primary_contrast'], *cfg['secondary_contrasts']]:
            candidate = endpoint[:, names.index(candidate_name), :, :, j]
            baseline = endpoint[:, names.index(baseline_name), :, :, j]
            folds = []
            for i, block in enumerate(cfg['blocks']):
                folds.append(dict(block=block, n=candidate[i].size,
                    success_difference=float(candidate[i].mean()-baseline[i].mean()),
                    **paired_table(candidate[i], baseline[i])))
            differences = [f['success_difference'] for f in folds]
            comparisons.append(dict(candidate=candidate_name, baseline=baseline_name, injury=injury,
                mean_block_success_difference=float(np.mean(differences)),
                blocks_positive=sum(x > 0 for x in differences), blocks_zero=sum(x == 0 for x in differences),
                blocks_negative=sum(x < 0 for x in differences),
                paired_counts=paired_table(candidate, baseline), folds=folds))
    primary = next(c for c in comparisons if c['injury'] == 'scattered' and
                   [c['candidate'], c['baseline']] == cfg['primary_contrast'])
    gap = next(c['mean_block_success_difference'] for c in comparisons
               if c['injury'] == 'scattered' and c['candidate'] == 'exact_rewrite' and c['baseline'] == 'tolerance_rewrite')
    delta = primary['mean_block_success_difference']
    return dict(status='DEVELOPMENT_INTERVENTION_NOT_CONFIRMATORY', created_at_utc=stamp(),
        blocks=cfg['blocks'], inference_unit='block', endpoint=cfg['primary_endpoint'],
        rates=rates, comparisons=comparisons, primary=primary,
        descriptive_fraction_of_original_tolerance_gap=delta/gap if gap > 0 else None,
        interpretation=('Directional native rescue under this repeated sign intervention; not unique mediation or P01 confirmation.'
                        if delta > 0 else 'No native rescue at the declared endpoint; this result narrows the sign-restoration hypothesis.'),
        uncertainty='Eight exposed blocks; no confirmatory inference or unseen-condition test.')


def write_csv(path, records):
    with path.open('x', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def analyze(folder, cfg):
    cases = [read_cases(folder/f'cases_{b:06d}.npz') for b in cfg['blocks']]
    summary = summarize(cases, cfg)
    for i, block in enumerate(cfg['blocks']):
        assert int(cases[i]['block']) == block
    endpoint_rows, history_rows = [], []
    for block, case in zip(cfg['blocks'], cases, strict=True):
        for n, writer in enumerate(cfg['writers']+['erased']):
            for founder in range(4):
                for recipient in range(cfg['config']['recipients']):
                    for j, injury in enumerate(cfg['injuries']):
                        endpoint_rows.append(dict(block=block, writer=writer, founder=founder, recipient=recipient,
                            injury=injury, success=int(case['assay_both_pass'][n, founder, recipient, j]),
                            margin=float(case['assay_min_margin'][n, founder, recipient, j])))
        for g, generation in enumerate(case['generations']):
            for n, writer in enumerate(cfg['writers']):
                history_rows.append(dict(block=block, generation=int(generation), writer=writer,
                    success_fraction=float(case['body_both_pass'][g, n].mean()),
                    mean_margin=float(case['body_min_margin'][g, n].mean()),
                    newly_substituted_fraction=float(case['newly_substituted_fraction'][g, n].mean()),
                    sign_flip_fraction=float(case['sign_flip_fraction'][g, n].mean())))
    write_csv(folder/'terminal_lineages.csv', endpoint_rows)
    write_csv(folder/'generation_block_summaries.csv', history_rows)
    summary['terminal_csv_sha256'] = sha(folder/'terminal_lineages.csv')
    summary['history_csv_sha256'] = sha(folder/'generation_block_summaries.csv')
    write_json(folder/'analysis.json', summary)
    primary = summary['primary']
    lines = ['# Controlled native writer continuation pilot', '',
        '**Development result; all selected original/tolerance controls passed native replay.**', '',
        f"Sign-restored minus tolerance h32 scattered success: {100*primary['mean_block_success_difference']:.2f} percentage points.",
        summary['interpretation'], '',
        '| Writer | Scattered successes | Percentage |', '|---|---:|---:|']
    for row in summary['rates']:
        if row['injury'] == 'scattered':
            lines.append(f"| {row['writer']} | {row['successes']}/{row['n']} | {100*row['mean_block_success']:.2f}% |")
    counts = primary['paired_counts']
    lines += ['', f"Relative to tolerance: {counts['rescued']} rescued, {counts['harmed']} harmed, "
              f"{counts['both_pass']} successful under both, {counts['both_fail']} failed under both.",
              f"Block differences: {primary['blocks_positive']} positive, {primary['blocks_zero']} zero, "
              f"{primary['blocks_negative']} negative.", '',
              '| Block | Sign-restored minus tolerance (points) | Rescued | Harmed |', '|---|---:|---:|---:|']
    for fold in primary['folds']:
        lines.append(f"| {fold['block']} | {100*fold['success_difference']:.2f} | {fold['rescued']} | {fold['harmed']} |")
    lines += ['',
        'Each branch starts from the same saved generation-3 pre-write body. Its assigned writer acts at that boundary and every subsequent renewal through generation 32. Damage and random draws are identical across branches. The sign-restored writer preserves the tolerance writer’s magnitudes and support on the same body while restoring original-writer signs. Later body states can differ.', '',
        'The main endpoint is terminal both-cue success under scattered damage, with the native strict margin greater than .25. Intact and square assays, continuous margins and body histories are secondary and retained in analysis.json and the CSVs. Eight blocks are the inference units. Reused data, known control outcomes and the outcome-informed hypothesis make this a development pilot. No confirmatory p-values are reported.', '',
        'The selected original and tolerance end states, birth states, masks, outgoing packets and mean ports match saved E051 boundaries exactly. Their terminal assays and the shared erased-record assay also match. Scores are checked against saved case arrays. This establishes the selected continuation replay; it does not audit teaching, all E051 conditions or the complete original experiment.', '',
        'Holding dynamics are omitted because they occur after packet capture, their bodies are discarded and their independent write streams do not affect later renewal. Original/tolerance replay checks constrain this omission. No native reader equation, timing, tolerance, geometry or scoring margin was tuned.', '',
        'This intervention estimates the effect of a repeated writer policy. A positive result supports a contribution from the restored sign policy in this matched-cue regime, while magnitude changes and feedback can still matter. A null or negative result supplies no rescue evidence here. Neither outcome establishes a short-probe long-horizon predictor, autonomous apparatus maintenance or transfer to other cue conditions.', '',
        'Raw branch boundaries, terminal arrays, case tables, replay receipts, source hashes and immutable launch inputs are retained in this run. COMPLETE.json binds its outputs. No original experiment files were changed.']
    with (folder/'REPORT.md').open('x') as f:
        f.write('\n'.join(lines)+'\n')
    return summary
