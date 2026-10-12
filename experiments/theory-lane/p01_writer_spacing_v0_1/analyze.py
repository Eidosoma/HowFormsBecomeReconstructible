"""Frozen descriptive endpoint and trajectory reporting for the spacing pilot."""
import csv
import json

import numpy as np

from evidence import descriptor, sha, stamp, write_json


def read_cases(path):
    with np.load(path, allow_pickle=False) as f:
        index = json.loads(f['__index__'].tobytes())
        values = {k: f[k] for k in index}
    for name, array in values.items():
        assert descriptor(array) == index[name]
    return values


def paired_table(candidate, baseline):
    assert candidate.shape == baseline.shape and candidate.dtype == baseline.dtype == bool
    return dict(both_pass=int((candidate & baseline).sum()), rescued=int((candidate & ~baseline).sum()),
        harmed=int((~candidate & baseline).sum()), both_fail=int((~candidate & ~baseline).sum()))


def write_csv(path, records):
    with path.open('x', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def summarize(cases, cfg):
    names = cfg['writers']+['erased']
    endpoint = np.stack([c['assay_both_pass'] for c in cases])
    margins = np.stack([c['assay_min_margin'] for c in cases])
    assert endpoint.shape == margins.shape == (len(cfg['blocks']), 6, 4, 4, 3)
    rates, comparisons = [], []
    for j, injury in enumerate(cfg['injuries']):
        for n, name in enumerate(names):
            current = endpoint[:, n, :, :, j]
            rates.append(dict(writer=name, provenance=cfg['provenance'][name], injury=injury,
                n=int(current.size), successes=int(current.sum()), mean_success=float(current.mean()),
                block_rates=current.mean(axis=(1, 2)).tolist(), mean_margin=float(margins[:, n, :, :, j].mean())))
        for candidate_name, baseline_name in [cfg['primary_contrast']]+cfg['secondary_contrasts']:
            a, b = (endpoint[:, names.index(name), :, :, j] for name in (candidate_name, baseline_name))
            differences = a.mean(axis=(1, 2))-b.mean(axis=(1, 2))
            comparisons.append(dict(candidate=candidate_name, baseline=baseline_name, injury=injury,
                mean_block_success_difference=float(differences.mean()), paired_counts=paired_table(a, b),
                blocks_positive=int((differences > 0).sum()), blocks_zero=int((differences == 0).sum()),
                blocks_negative=int((differences < 0).sum()),
                folds=[dict(block=block, n=16, success_difference=float(differences[i]),
                    **paired_table(a[i], b[i])) for i, block in enumerate(cfg['blocks'])]))
    primary = next(c for c in comparisons if c['injury'] == 'scattered' and
                   [c['candidate'], c['baseline']] == cfg['primary_contrast'])
    return dict(status='DEVELOPMENT_TIMING_INTERVENTION_NOT_CONFIRMATORY', created_at_utc=stamp(),
        blocks=cfg['blocks'], independent_unit='block', endpoint=cfg['primary_endpoint'],
        rates=rates, comparisons=comparisons, primary=primary,
        tolerance_generations=cfg['tolerance_generations'], provenance=cfg['provenance'],
        reused_controls_are_new_replicates=False, no_predictor_fitted=True,
        uncertainty='Eight exposed blocks; descriptive paired estimates, no confirmatory or equivalence claim.')


def plot(folder, histories, cfg):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors = ['#33373b', '#c64b40', '#6e98b1', '#245bac', '#9d5e91']
    labels = ['Original', 'Repeated tolerance (reused)', 'Single pulse (reused)', 'Six spaced', 'Initial + late cluster']
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), constrained_layout=True)
    for n, name in enumerate(cfg['writers']):
        for ax, metric, multiplier in ((axes[0], 'success_fraction', 100), (axes[1], 'signed_transfer', 1)):
            means = [np.mean([r[metric] for r in histories if r['generation'] == g and r['writer'] == name])
                     for g in range(3, 33)]
            ax.plot(range(3, 33), multiplier*np.array(means), label=labels[n], color=colors[n],
                    linestyle='--' if n in (1, 2) else '-', lw=2)
    axes[0].set(ylabel='Native both-cue body success (%)', ylim=(-2, 103))
    axes[1].set(ylabel='Outgoing signed transfer (64 linear steps)')
    for ax in axes:
        ax.axvline(13, color='#888888', ls=':', lw=1)
        ax.set(xlabel='Rebuild generation', xlim=(3, 32))
        ax.spines[['right', 'top']].set_visible(False)
        ax.grid(alpha=.18)
    handles, labels_ = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels_, loc='outside lower center', ncol=3, frameon=False)
    fig.suptitle('Equal-count schedules: six tolerance writes, first at 3 and last at 13\nEight development blocks; body scores precede the outgoing write')
    outputs = {}
    for ext in ('png', 'svg'):
        path = folder/f'trajectories.{ext}'
        assert not path.exists()
        fig.savefig(path, dpi=170)
        outputs[path.name] = sha(path)
    plt.close(fig)
    write_json(folder/'figure_provenance.json', dict(history_sha256=sha(folder/'generation_block_summaries.csv'),
        code_sha256=sha(__file__), outputs_sha256=outputs, inspected=False,
        scope='Equal-block means, no inferential bands. Transmission is a linear surrogate.'))


def analyze(folder, cfg):
    cases = [read_cases(folder/f'cases_{b:06d}.npz') for b in cfg['blocks']]
    summary = summarize(cases, cfg)
    endpoints, histories, lineage_histories = [], [], []
    for block, case in zip(cfg['blocks'], cases, strict=True):
        assert int(case['block']) == block and case['generations'].tolist() == list(range(3, 33))
        for n, name in enumerate(cfg['writers']+['erased']):
            for f in range(4):
                for r in range(4):
                    for j, injury in enumerate(cfg['injuries']):
                        endpoints.append(dict(block=block, writer=name, provenance=cfg['provenance'][name],
                            founder=f, recipient=r, injury=injury,
                            success=int(case['assay_both_pass'][n, f, r, j]), margin=float(case['assay_min_margin'][n, f, r, j])))
        for gi, generation in enumerate(case['generations']):
            g = int(generation)
            for n, name in enumerate(cfg['writers']):
                code = int(case['writer_codes'][gi, n])
                assert code == int(g in cfg['tolerance_generations'][name])
                action = 'tolerance_rewrite' if code else 'exact_rewrite'
                histories.append(dict(block=block, generation=g, writer=name, provenance=cfg['provenance'][name],
                    active_writer_policy=action, success_fraction=float(case['body_both_pass'][gi, n].mean()),
                    mean_margin=float(case['body_min_margin'][gi, n].mean()),
                    **{k: float(case[k][gi, n].mean()) for k in ('newly_substituted_fraction', 'sign_flip_fraction', 'signed_transfer', 'unsigned_access')}))
                for f in range(4):
                    for r in range(4):
                        lineage_histories.append(dict(block=block, generation=g, writer=name, founder=f, recipient=r,
                            active_writer_policy=action, success=int(case['body_both_pass'][gi, n, f, r]),
                            margin=float(case['body_min_margin'][gi, n, f, r]),
                            signed_transfer=float(case['signed_transfer'][gi, n, f, r]),
                            unsigned_access=float(case['unsigned_access'][gi, n, f, r])))
    write_csv(folder/'terminal_lineages.csv', endpoints)
    write_csv(folder/'generation_block_summaries.csv', histories)
    write_csv(folder/'body_lineages.csv', lineage_histories)
    summary['csv_sha256'] = {n: sha(folder/n) for n in ('terminal_lineages.csv', 'generation_block_summaries.csv', 'body_lineages.csv')}
    summary['post_pulse_body_generation'] = 14
    summary['post_pulse_body'] = [dict(writer=w, n=len(cases)*16,
        successes=sum(r['success'] for r in lineage_histories if r['generation'] == 14 and r['writer'] == w),
        block_rates=[next(r['success_fraction'] for r in histories if r['block'] == b and r['generation'] == 14 and r['writer'] == w)
                     for b in cfg['blocks']]) for w in cfg['writers']]
    write_json(folder/'analysis.json', summary)
    plot(folder, histories, cfg)
    primary = summary['primary']
    difference = primary['mean_block_success_difference']
    interpretation = ('The spaced schedule has higher terminal success in this development cohort.' if difference > 0 else
        'The spaced schedule has lower terminal success: the proposed direction is contradicted in this development cohort.' if difference < 0 else
        'The schedules have equal aggregate terminal success; this does not establish equivalence.')
    lines = ['# Equal-count writer spacing pilot', '', '**Development result.** '+interpretation, '',
        '| Policy | Scattered terminal successes | Rate | Origin |', '|---|---:|---:|---|']
    for rate in summary['rates']:
        if rate['injury'] == 'scattered':
            lines.append(f"| {rate['writer']} | {rate['successes']}/{rate['n']} | {100*rate['mean_success']:.2f}% | {rate['provenance']} |")
    counts = primary['paired_counts']
    lines += ['', f'Primary spaced-minus-cluster difference: **{100*difference:.2f} percentage points**.',
        f"{counts['rescued']} rescued, {counts['harmed']} harmed, {counts['both_pass']} successful under both and {counts['both_fail']} failed under both.",
        f"Blocks: {primary['blocks_positive']} positive, {primary['blocks_zero']} zero, {primary['blocks_negative']} negative.", '',
        '| Block | Difference (points) | Rescued | Harmed |', '|---|---:|---:|---:|']
    for fold in primary['folds']:
        lines.append(f"| {fold['block']} | {100*fold['success_difference']:.2f} | {fold['rescued']} | {fold['harmed']} |")
    lines += ['', 'Spaced T writes: 3, 5, 7, 9, 11, 13. Cluster T writes: 3, 9, 10, 11, 12, 13. Both have six events and 19 O writes at generations 14–32.', '',
        '| Policy | First post-pulse body, generation 14 | Final scattered terminal assay |', '|---|---:|---:|']
    for record in summary['post_pulse_body']:
        terminal = next(r for r in summary['rates'] if r['writer'] == record['writer'] and r['injury'] == 'scattered')
        lines.append(f"| {record['writer']} | {record['successes']}/{record['n']} | {terminal['successes']}/{terminal['n']} |")
    lines += ['', 'Generation 14 reads the final T-written record before making its first subsequent O write. Its body score and the h32 terminal assay use different declared bodies/damage; their difference is not a fixed-challenge recovery estimate.', '',
        '| Secondary scattered contrast | Difference (points) | Rescued | Harmed |', '|---|---:|---:|---:|']
    for c in summary['comparisons']:
        if c['injury'] == 'scattered' and [c['candidate'], c['baseline']] != cfg['primary_contrast']:
            lines.append(f"| {c['candidate']} minus {c['baseline']} | {100*c['mean_block_success_difference']:.2f} | {c['paired_counts']['rescued']} | {c['paired_counts']['harmed']} |")
    lines += ['', '![Native body and outgoing transmission histories](trajectories.png)', '',
        'All source bodies, outgoing packets, mean ports, writer-event codes and terminal arrays are retained. The original reproduces native E051 boundaries and assays; erased results match. Each new branch matches the completed single pulse until its first additional T write, including that write’s pre-capture body. Every scheduled capture is recomputed independently on its actual body.', '',
        'The original is replayed here; T and P are reused hash-bound observations. Related founders, recipients and generations are not independent blocks. These are eight exposed development blocks and no confirmatory p-value or equivalence margin was specified.', '',
        'The recorded action is the writer actually used. Substitution/sign-flip fractions describe the hypothetical O-to-T change on the current body even when O is used. The 64-step transmission calculation is a linear diagnostic, not native success probability. No diagnostic depth or schedule was tuned to these outcomes.', '',
        'Teaching and terminal cue randomness remain matched. Holding is omitted under the prior replay-validated contract. Full new-arm reader dynamics have not been separately reimplemented; original dynamics, shared prefixes, all captures, and independent result tables are checked.', '',
        'This result concerns the declared timing schedules. It does not establish return to the original network, a universal repair interval, unique causal mediation or a validated P01 predictor. The earlier negative predictor findings remain retained. No automatic successor run is started.']
    with (folder/'REPORT.md').open('x') as f:
        f.write('\n'.join(lines)+'\n')
    return summary
