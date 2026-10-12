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
    expected = (len(cfg['blocks']), len(names), 4, cfg['config']['recipients'], 3)
    assert endpoint.shape == margins.shape == expected
    assert endpoint.dtype == bool and np.isfinite(margins).all()
    rates, comparisons = [], []
    for j, injury in enumerate(cfg['injuries']):
        for n, name in enumerate(names):
            block_rates = endpoint[:, n, :, :, j].mean(axis=(1, 2))
            rates.append(dict(writer=name, provenance=cfg['provenance'][name], injury=injury, successes=int(endpoint[:, n, :, :, j].sum()),
                n=int(endpoint[:, n, :, :, j].size), mean_block_success=float(block_rates.mean()),
                block_success=[int(x.sum()) for x in endpoint[:, n, :, :, j]],
                block_rates=block_rates.tolist(), mean_margin=float(margins[:, n, :, :, j].mean())))
        for candidate_name, baseline_name in cfg['primary_contrasts']+cfg['secondary_contrasts']:
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
    primaries = [next(c for c in comparisons if c['injury'] == 'scattered' and
                      [c['candidate'], c['baseline']] == contrast) for contrast in cfg['primary_contrasts']]
    factorial = []
    for j, injury in enumerate(cfg['injuries']):
        values = sum(coefficient*endpoint[:, names.index(name), :, :, j].mean(axis=(1, 2))
                     for name, coefficient in cfg['factorial_coefficients'].items())
        factorial.append(dict(injury=injury, mean_block_interaction=float(values.mean()),
            folds=[dict(block=block, interaction=float(value)) for block, value in zip(cfg['blocks'], values, strict=True)],
            blocks_positive=int((values > 0).sum()), blocks_zero=int((values == 0).sum()), blocks_negative=int((values < 0).sum())))
    return dict(status='DEVELOPMENT_INTERVENTION_NOT_CONFIRMATORY', created_at_utc=stamp(),
        blocks=cfg['blocks'], inference_unit='block', endpoint=cfg['primary_endpoint'],
        rates=rates, comparisons=comparisons, primaries=primaries, factorial=factorial,
        factorial_definition='(p_original-p_magnitude_restored)-(p_sign_restored-p_tolerance)',
        factorial_coefficients=cfg['factorial_coefficients'], provenance=cfg['provenance'],
        reused_controls_are_new_replicates=False,
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
    endpoint_rows, history_rows, completion_rows = [], [], []
    for block, case in zip(cfg['blocks'], cases, strict=True):
        for n, writer in enumerate(cfg['writers']+['erased']):
            for founder in range(4):
                for recipient in range(cfg['config']['recipients']):
                    for j, injury in enumerate(cfg['injuries']):
                        endpoint_rows.append(dict(block=block, writer=writer, provenance=cfg['provenance'][writer], founder=founder, recipient=recipient,
                            injury=injury, success=int(case['assay_both_pass'][n, founder, recipient, j]),
                            margin=float(case['assay_min_margin'][n, founder, recipient, j])))
        for g, generation in enumerate(case['generations']):
            for n, writer in enumerate(cfg['writers']):
                stage = 'initial' if int(generation) == cfg['branch_generation'] else 'later'
                action = cfg['schedules'][writer][stage] if writer in cfg['schedules'] else writer
                history_rows.append(dict(block=block, generation=int(generation), writer=writer,
                    provenance=cfg['provenance'][writer], active_writer_policy=action,
                    success_fraction=float(case['body_both_pass'][g, n].mean()),
                    mean_margin=float(case['body_min_margin'][g, n].mean()),
                    newly_substituted_fraction=float(case['newly_substituted_fraction'][g, n].mean()),
                    sign_flip_fraction=float(case['sign_flip_fraction'][g, n].mean())))
            for n, writer in enumerate(cfg['simulated_writers']):
                completion_rows.append(dict(block=block, generation=int(generation), writer=writer,
                    magnitude_sign_fallback_fraction=float(case['simulated_magnitude_sign_fallback_fraction'][g, n].mean())))
    write_csv(folder/'terminal_lineages.csv', endpoint_rows)
    write_csv(folder/'generation_block_summaries.csv', history_rows)
    write_csv(folder/'sign_completion_block_summaries.csv', completion_rows)
    summary['terminal_csv_sha256'] = sha(folder/'terminal_lineages.csv')
    summary['history_csv_sha256'] = sha(folder/'generation_block_summaries.csv')
    summary['sign_completion_csv_sha256'] = sha(folder/'sign_completion_block_summaries.csv')
    write_json(folder/'analysis.json', summary)
    lines = ['# Writer magnitude control and single-pulse pilot', '',
        '**Development result: original replay and pulse-boundary checks passed; reused controls are bound to the completed prior pilot.**', '',
        '| Writer | Scattered successes | Percentage | Origin |', '|---|---:|---:|---|']
    for row in summary['rates']:
        if row['injury'] == 'scattered':
            lines.append(f"| {row['writer']} | {row['successes']}/{row['n']} | {100*row['mean_block_success']:.2f}% | {row['provenance']} |")
    for primary in summary['primaries']:
        counts = primary['paired_counts']
        lines += ['', f"**{primary['candidate']} minus {primary['baseline']}: {100*primary['mean_block_success_difference']:.2f} percentage points.**",
            f"{counts['rescued']} rescued, {counts['harmed']} harmed, {counts['both_pass']} successful under both, {counts['both_fail']} failed under both.",
            f"Blocks: {primary['blocks_positive']} positive, {primary['blocks_zero']} zero, {primary['blocks_negative']} negative.", '',
            '| Block | Difference (points) | Rescued | Harmed |', '|---|---:|---:|---:|']
        for fold in primary['folds']:
            lines.append(f"| {fold['block']} | {100*fold['success_difference']:.2f} | {fold['rescued']} | {fold['harmed']} |")
    lines += ['', '| Scattered secondary comparison | Difference (points) | Rescued | Harmed |', '|---|---:|---:|---:|']
    for comparison in summary['comparisons']:
        if comparison['injury'] == 'scattered' and [comparison['candidate'], comparison['baseline']] in cfg['secondary_contrasts']:
            counts = comparison['paired_counts']
            lines.append(f"| {comparison['candidate']} minus {comparison['baseline']} | {100*comparison['mean_block_success_difference']:.2f} | {counts['rescued']} | {counts['harmed']} |")
    interaction = next(f for f in summary['factorial'] if f['injury'] == 'scattered')
    lines += ['', f"Four-policy additive interaction, (pO-pM)-(pS-pT): **{100*interaction['mean_block_interaction']:.2f} percentage points**.",
        'This is an effect-modification contrast between whole writer policies on the probability scale. It is not a uniquely attributable fraction of failure, and no statistical interaction threshold or p-value was specified.', '',
        '| Block | Additive interaction (points) |', '|---|---:|']
    for fold in interaction['folds']:
        lines.append(f"| {fold['block']} | {100*fold['interaction']:.2f} |")
    lines += ['',
        'Each branch starts from the same saved generation-3 pre-write body with identical future masks and random draws. M retains original magnitudes and support, and takes tolerance signs wherever tolerance weights are nonzero. At zero tolerance weights it retains the original sign. This completion was fixed before outcomes; its use is recorded in sign_completion_block_summaries.csv. M is used throughout generations 3–32.', '',
        'P uses tolerance writing at generation 3 only. Its generation-4 body is checked against the saved tolerance body because it reads that same altered record; its generation-4 and later writes use the original rule. P-versus-original paired outcomes are reported even when aggregate success rates coincide. No equivalence margin was specified.', '',
        'The history table records the writer actually used at every generation. Its substitution and sign-flip fractions compare O and T evaluated on each branch’s body; they do not count actual tolerance-writing events in a branch using another policy. The sign-completion table likewise measures where M would use its declared zero-edge rule on that body.', '',
        'The main endpoint is terminal both-cue success under scattered damage, with the native strict margin greater than .25. Intact and square assays, continuous margins and body histories are secondary and retained in analysis.json and the CSVs. Eight blocks are the inference units. Reused data, known control outcomes and the outcome-informed hypothesis make this a development pilot. No confirmatory p-values are reported.', '',
        'The original end states, birth states, masks, outgoing packets and mean ports match E051 exactly at every renewal. Its terminal assays and the erased-record assay also match. Original scores, margins and writer diagnostics equal the prior pilot, whose T and S controls are reused under verified hashes. These are matched old observations, not an enlarged independent cohort.', '',
        'Holding dynamics are omitted for the same previously validated reason: they occur after packet capture, their bodies are discarded and their separate random streams do not affect later renewal. No native reader equation, timing, tolerance, geometry or scoring margin was tuned.', '',
        'A positive M-minus-T difference supports a benefit from restoring original magnitudes/support with the declared sign completion. M-versus-S and the four-policy interaction qualify any simple ranking of signs and magnitudes. A positive P-minus-T difference supports a benefit from ending tolerance writing after one event; P-versus-O measures its remaining consequences. Null or negative differences narrow those directional hypotheses. None establishes a long-horizon predictor or unique causal mediation.', '',
        'Raw branch boundaries, terminal arrays, case tables, replay receipts, source hashes and immutable launch inputs are retained in this run. COMPLETE.json binds its outputs. No original experiment files were changed.']
    with (folder/'REPORT.md').open('x') as f:
        f.write('\n'.join(lines)+'\n')
    return summary
