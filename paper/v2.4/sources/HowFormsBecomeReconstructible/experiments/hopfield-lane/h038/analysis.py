"""Separate serial guidance, final access, copying deficits and path success."""
from collections import defaultdict
import csv
import numpy as np
from h007.io import save
from h035 import design as d
from h038 import experiment as e


def paired(after, before):
    delta = after.astype(int)-before.astype(int)
    return dict(gains=int((delta == 1).sum()), losses=int((delta == -1).sum()),
        readouts=int(delta.size), difference=float(delta.mean()))


def summarize(raw, source, block):
    outcomes, effects, gaps, bodies, paths = [], [], [], [], []
    for j, g in enumerate(source['checkpoints']):
        for l, load in enumerate(d.LOADS):
            scores = []
            for a, arm in enumerate(d.ARMS):
                # Probe zero is retained only for H035 exact replay.
                x = raw['states'][j, :, :, l, a, 1:]
                trained, rule, joint = e.score(x, l)
                scores.append(trained)
                donor = d.RULES[d.DONORS[arm]] if arm in d.DONORS else d.RULES
                _, donor_rule, donor_joint = e.score(x, l, donor)
                for b, body_gain in enumerate(e.GAINS):
                    for r, assay_gain in enumerate(e.GAINS):
                        outcomes.append(dict(block=block, generation=int(g), load=load, arm=arm,
                            reconstruction_gain=body_gain, assay_gain=assay_gain,
                            trained_success=float(trained[b, r].mean()),
                            rule_a=float(rule[b, r, ..., 0].mean()), rule_b=float(rule[b, r, ..., 1].mean()),
                            joint=float(joint[b, r].mean()),
                            donor_rule_a=float(donor_rule[b, r, ..., 0].mean()),
                            donor_rule_b=float(donor_rule[b, r, ..., 1].mean()),
                            donor_joint=float(donor_joint[b, r].mean()), readouts=int(trained[b, r].size)))
                for name, (after, before) in e.EFFECTS.items():
                    effects.append(dict(block=block, generation=int(g), load=load, arm=arm,
                        contrast=name, **paired(trained[after], trained[before])))
                s = trained.astype(int)
                effects.append(dict(block=block, generation=int(g), load=load, arm=arm,
                    contrast='interaction', gains=None, losses=None, readouts=int(s[0, 0].size),
                    difference=float((s[1, 1]-s[0, 1]-s[1, 0]+s[0, 0]).mean())))
            for b, body_gain in enumerate(e.GAINS):
                for r, assay_gain in enumerate(e.GAINS):
                    for arm in ('protected_copy', 'damaged_copy'):
                        gaps.append(dict(block=block, generation=int(g), load=load,
                            reconstruction_gain=body_gain, assay_gain=assay_gain,
                            contrast='renewal_minus_'+arm,
                            **paired(scores[0][b, r], scores[d.ARMS.index(arm)][b, r])))
    for l, load in enumerate(d.LOADS):
        for a, arm in enumerate(d.ARMS):
            x = raw['bodies'][:, :, l, a]
            own = e.body_success(x, l)
            donor_rules = d.RULES[d.DONORS[arm]] if arm in d.DONORS else d.RULES
            donor = e.body_success(x, l, donor_rules)
            for b, gain in enumerate(e.GAINS):
                for g in range(x.shape[1]):
                    bodies.append(dict(block=block, generation=g+1, load=load, arm=arm,
                        reconstruction_gain=gain, trained_success=float(own[b, g].mean()),
                        donor_success=float(donor[b, g].mean()),
                        successful_so_far=float(own[b, :g+1].all(0).mean()),
                        related_paths=int(own[b, g].size)))
                paths.append(dict(block=block, load=load, arm=arm, reconstruction_gain=gain,
                    all_boundaries_success=float(own[b].all(0).mean()),
                    donor_all_boundaries_success=float(donor[b].all(0).mean()),
                    mean_boundary_success=float(own[b].mean()), final_body_success=float(own[b, -1].mean()),
                    related_paths=int(own[b, 0].size)))
    return dict(block=block, outcome_rows=outcomes, effect_rows=effects,
                gap_rows=gaps, body_rows=bodies, path_rows=paths)


def grouped(rows, keys):
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[k] for k in keys)].append(row)
    return [(dict(zip(keys, key)), sorted(values, key=lambda r: r['block'])) for key, values in groups.items()]


def csv_write(path, rows):
    with path.open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def means(rows, keys, fields, count):
    return [dict(**key, **{f: float(np.mean([v[f] for v in values])) for f in fields},
        **{count: sum(v[count] for v in values)}) for key, values in grouped(rows, keys)]


def effects(rows, keys):
    result = []
    for key, values in grouped(rows, keys):
        diffs = [v['difference'] for v in values]
        result.append(dict(**key, difference=float(np.mean(diffs)), per_network=diffs,
            networks_positive=sum(x > 0 for x in diffs), networks_zero=sum(x == 0 for x in diffs),
            networks_negative=sum(x < 0 for x in diffs),
            **{k: None if values[0][k] is None else sum(v[k] for v in values)
               for k in ('gains', 'losses', 'readouts')}))
    return result


def analyze(out, summaries, classification):
    names = ('outcome_rows', 'effect_rows', 'gap_rows', 'body_rows', 'path_rows')
    flat = {k: [row for s in summaries for row in s[k]] for k in names}
    for k, rows in flat.items():
        csv_write(out/(k+'.csv'), rows)
    outcomes = means(flat['outcome_rows'], ('generation', 'load', 'arm', 'reconstruction_gain', 'assay_gain'),
        ('trained_success', 'rule_a', 'rule_b', 'joint', 'donor_rule_a', 'donor_rule_b', 'donor_joint'), 'readouts')
    contrasts = effects(flat['effect_rows'], ('generation', 'load', 'arm', 'contrast'))
    gaps = effects(flat['gap_rows'], ('generation', 'load', 'reconstruction_gain', 'assay_gain', 'contrast'))
    bodies = means(flat['body_rows'], ('generation', 'load', 'arm', 'reconstruction_gain'),
        ('trained_success', 'donor_success', 'successful_so_far'), 'related_paths')
    paths = means(flat['path_rows'], ('load', 'arm', 'reconstruction_gain'),
        ('all_boundaries_success', 'donor_all_boundaries_success', 'mean_boundary_success', 'final_body_success'), 'related_paths')
    summary = dict(classification=classification, independent_source_networks=len(summaries),
        outcomes=outcomes, effects=contrasts, gaps=gaps, bodies=bodies, paths=paths,
        row_counts={k: len(v) for k, v in flat.items()}, primary_probe_count=e.PROBES,
        legacy_probes_excluded=True, confirmation=False, writer_changes=False, predictor_fits=0,
        prior_verdicts_changed=False, private_material=False, manuscript_edit=False)
    save(out/'summary.json', summary)
    lookup = {(r['generation'], r['load'], r['arm'], r['reconstruction_gain'], r['assay_gain']): r for r in outcomes}
    lines = ['# H038 — Guidance during inheritance versus final access', '',
        f'{classification}; {len(summaries)} exposed source networks. Eight fresh probes per checkpoint, with the legacy replay assay excluded.', '',
        'Each setting below is reconstruction gain / assay gain.', '',
        '| Generation | Record arm | 4 / 4 | 4 / 8 | 8 / 4 | 8 / 8 |',
        '| --- | --- | ---: | ---: | ---: | ---: |']
    for g in d.CHECKPOINTS:
        for arm in ('renewal', 'protected_copy', 'damaged_copy'):
            rates = [lookup[(g, 'both', arm, b, r)]['joint'] for b in e.GAINS for r in e.GAINS]
            lines.append(f'| {g} | {arm} | '+' | '.join(f'{v:.4%}' for v in rates)+' |')
    lines += ['', '| Generation | Renewal contrast | Difference (pp) | Networks positive / zero / negative |',
        '| --- | --- | ---: | --- |']
    for row in contrasts:
        if row['load'] == 'both' and row['arm'] == 'renewal':
            signs = ' / '.join(str(row['networks_'+s]) for s in ('positive', 'zero', 'negative'))
            lines.append(f"| {row['generation']} | {row['contrast']} | {100*row['difference']:+.4f} | {signs} |")
    lines += ['', '| Load | Reconstruction gain | Mean body success | Final body success | All boundaries successful |',
        '| --- | ---: | ---: | ---: | ---: |']
    for row in paths:
        if row['arm'] == 'renewal':
            lines.append(f"| {row['load']} | {row['reconstruction_gain']} | {row['mean_boundary_success']:.4%} | "
                f"{row['final_body_success']:.4%} | {row['all_boundaries_success']:.4%} |")
    lines += ['', 'The G16 both-rule contrast at common assay gain 8 is primary. The common gain-4 contrast tests portability to the original reader.',
        'Terminal fresh access, average body performance, and success at every boundary are separate outcomes.',
        'Copying gaps and all donor, erased, read-off, write-off and scrambling controls are retained in CSV/JSON.',
        'Eight exposed networks are the independent units. Histories, descendants, checkpoints and probes are related; no population confirmation or numerical qualification gate is claimed.',
        'Stronger reconstruction is a continuing apparatus intervention. A benefit does not show evolution or autonomous acquisition of that machinery.',
        'No predictor, private AI-lane material, manuscript edit or public release. All earlier verdicts remain unchanged.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
    plot(out, lookup, paths, len(summaries), classification)
    return summary


def plot(out, lookup, paths, networks, classification):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for b in e.GAINS:
        for r in e.GAINS:
            y = [lookup[(g, 'both', 'renewal', b, r)]['joint'] for g in d.CHECKPOINTS]
            axes[0].plot(d.CHECKPOINTS, y, marker='o', label=f'reconstruct {b}, assay {r}')
    axes[0].set(xlabel='Completed replacements', ylabel='Both-rule success in fresh recipients',
        ylim=(0, 1.03), xticks=d.CHECKPOINTS)
    axes[0].legend(fontsize=8)
    lookup_path = {(r['load'], r['arm'], r['reconstruction_gain']): r for r in paths}
    fields = ('mean_boundary_success', 'final_body_success', 'all_boundaries_success')
    for i, b in enumerate(e.GAINS):
        values = [lookup_path[('both', 'renewal', b)][f] for f in fields]
        axes[1].bar(np.arange(3)+(i-.5)*.35, values, width=.33, label=f'reconstruct {b}')
    axes[1].set(xticks=np.arange(3), xticklabels=['mean body', 'final body', 'every boundary'],
        ylabel='Both-rule success during inheritance', ylim=(0, 1.03))
    axes[1].legend(fontsize=8)
    for ax in axes:
        ax.grid(axis='y', alpha=.2)
    fig.suptitle(f'H038: {networks} source networks ({classification.lower()})', fontsize=10)
    fig.tight_layout(); fig.savefig(out/'overview.png', dpi=160); fig.savefig(out/'overview.pdf'); plt.close(fig)
