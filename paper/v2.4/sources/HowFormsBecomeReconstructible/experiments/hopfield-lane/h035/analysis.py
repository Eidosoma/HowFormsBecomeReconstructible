"""Descriptive development screens, with networks as the independent unit."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import numpy as np
from h007.io import save
from h035 import design as d, experiment as e


def screens(joint, rules, donor_rules, checkpoints):
    """Fixed pilot screens on network means; no statistical confirmation."""
    a = {arm: i for i, arm in enumerate(d.ARMS)}
    c = {int(g): i for i, g in enumerate(checkpoints)}
    initial = dict(both_initial_joint=joint[c[0], 2, a['renewal']] >= .50,
        both_protected_g16_joint=joint[c[16], 2, a['protected_copy']] >= .50)
    for l, task in ((0, 0), (1, 1)):
        initial[f'{d.LOADS[l]}_initial_rule'] = rules[c[0], l, a['renewal'], task] >= .75
        initial[f'{d.LOADS[l]}_protected_rule'] = rules[c[16], l, a['protected_copy'], task] >= .75
    rewrite = {f'g{g}_both_joint': joint[c[g], 2, a['renewal']] >= .30 for g in (8, 16)}
    for arm in ('foreign_both', 'scrambled', 'erased', 'read_off', 'write_off', 'writer_scrambled'):
        rewrite['own_minus_'+arm] = joint[c[16], 2, a['renewal']] - joint[c[16], 2, a[arm]] >= .15
    rewrite['own_minus_damaged_copy'] = joint[c[16], 2, a['renewal']] - joint[c[16], 2, a['damaged_copy']] >= .10
    selective = {}
    for g in (0, 16):
        for arm, changed in (('foreign_a', 0), ('foreign_b', 1)):
            kept = 1-changed
            selective[f'g{g}_{arm}_donor_changed_rule'] = donor_rules[arm][c[g], 2, a[arm], changed] >= .50
            selective[f'g{g}_{arm}_kept_rule'] = rules[c[g], 2, a[arm], kept] >= rules[c[g], 2, a['renewal'], kept]-.10
            selective[f'g{g}_{arm}_changed_original_rule_gap'] = rules[c[g], 2, a['renewal'], changed]-rules[c[g], 2, a[arm], changed] >= .25
    gates = {name: {k: bool(v) for k, v in group.items()} for name, group in
             [('starting_task', initial), ('rewriting', rewrite), ('selective_content', selective)]}
    task_ok, rewrite_ok, selective_ok = [all(gates[k].values()) for k in gates]
    if not task_ok:
        verdict = 'STARTING_TASK_LIMITED'
    elif rewrite_ok and selective_ok:
        verdict = 'TWO_RULE_REWRITING_AND_SELECTIVE_CONTENT_LEAD'
    elif rewrite_ok:
        verdict = 'REWRITING_LEAD_WITH_SELECTIVE_CONTENT_LIMITATION'
    else:
        verdict = 'STARTING_TASK_PASSES_REWRITING_LIMITED'
    return dict(verdict=verdict, gates=gates, starting_task_passes=task_ok,
        rewriting_lead=task_ok and rewrite_ok, selective_content_lead=task_ok and selective_ok,
        confirmation=False, failed_gates=[group+'/'+k for group, values in gates.items() for k, passed in values.items() if not passed])


def analyze(out, paths, classification):
    out = Path(out)
    block_joint, block_rules, block_donors, body_joint = [], [], {a: [] for a in d.DONORS}, []
    rows = []
    for path in paths:
        with np.load(path) as raw:
            _, rules, joint = e.score(raw['reader_states'])
            block_joint.append(joint.mean(axis=(-2, -1)))
            block_rules.append(rules.mean(axis=(-3, -2)))
            for arm, donor in d.DONORS.items():
                block_donors[arm].append(e.score(raw['reader_states'], d.RULES[donor])[1].mean(axis=(-3, -2)))
            body_joint.append(e.score(raw['bodies'][:, 2])[2].mean(axis=(-2, -1)))
            checkpoints = raw['checkpoints'].tolist()
            for j, g in enumerate(checkpoints):
                for l, load in enumerate(d.LOADS):
                    for a, arm in enumerate(d.ARMS):
                        rows.append(dict(block=path.stem, generation=g, load=load, arm=arm,
                            rule_a=float(block_rules[-1][j, l, a, 0]), rule_b=float(block_rules[-1][j, l, a, 1]),
                            both=float(block_joint[-1][j, l, a])))
    j, r = np.array(block_joint), np.array(block_rules)
    donors = {a: np.array(v) for a, v in block_donors.items()}
    jm, rm = j.mean(axis=0), r.mean(axis=0)
    decision = screens(jm, rm, {a: v.mean(axis=0) for a, v in donors.items()}, checkpoints)
    summary = dict(experiment='H035', classification=classification, independent_networks=len(paths),
        histories_per_network=d.HISTORIES, descendants_per_history=d.REPLICATES,
        checkpoints=checkpoints, loads=d.LOADS, arms=d.ARMS,
        mean_joint=jm.tolist(), mean_rules=rm.tolist(), block_joint=j.tolist(), block_rules=r.tolist(),
        mean_donor_rules={a: v.mean(axis=0).tolist() for a, v in donors.items()},
        mean_both_load_body_joint=np.mean(body_joint, axis=0).tolist(),
        development_screens=decision, outcomes_pooled_with_engineering=False,
        resource_accounting=dict(unique_record_values=2016, record_payload_bytes=16128,
            dense_record_bytes=32768, unique_shared_base_values=2016,
            supplied_reader_cue_edges_scaled=240, teacher_only_at_formation=True,
            cue_trials_per_body=4, sweeps_per_trial=8, free_site_updates_per_body=1920,
            lineage_updates_per_arm_history_descendant=30720,
            coactivity_products_per_write=16384, writes_per_lineage=16,
            checkpoint_reads_per_lineage=5,
            copying_bodies_are_diagnostic=True, copying_requires_body_or_writer=False),
        limitations=['Eight pilot networks cannot establish a population effect.',
            'Histories, descendants, loads, checkpoints and arms share each base network.',
            'Single-rule loads repeat their two cue trials to match update and writer budgets.',
            'Four cue trials are reset and averaged at each boundary; this is batch coactivity, not online continual learning.',
            'Supplied cue geometry, output patches, fixed base, gain and teacher are apparatus.',
            'The two rules are independently assignable binary signs on shared output patches, not arbitrary tasks.',
            'No RDT predictor is fitted or assessed.'])
    save(out/'summary.json', summary)
    with (out/'network_outcomes.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    label = 'Pilot development screens' if classification == d.CLASSIFICATION else 'Engineering-only screens (excluded from pilot)'
    lines = ['# H035 — Two acquired cue rules', '',
        f'{classification}; {len(paths)} independent base networks, four histories and two descendants per history.', '',
        f'{label}: **{decision["verdict"]}**. This is not confirmation.', '',
        '| Load | G0 trained rule A | G0 trained rule B | G16 rule A | G16 rule B | G16 both |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    c0, c16, own = checkpoints.index(0), checkpoints.index(16), d.ARMS.index('renewal')
    for l, load in enumerate(d.LOADS):
        va = f'{100*rm[c0,l,own,0]:.2f}%' if l != 1 else 'untrained'
        vb = f'{100*rm[c0,l,own,1]:.2f}%' if l != 0 else 'untrained'
        lines.append(f'| {load} | {va} | {vb} | {100*rm[c16,l,own,0]:.2f}% | {100*rm[c16,l,own,1]:.2f}% | {100*jm[c16,l,own]:.2f}% |')
    lines += ['', 'Untrained-rule and single-load joint scores are descriptive only.', '',
        '| Both-rule load: arm | G0 both | G8 both | G16 A | G16 B | G16 both |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for a, arm in enumerate(d.ARMS):
        values = [jm[c0,2,a], jm[checkpoints.index(8),2,a], rm[c16,2,a,0], rm[c16,2,a,1], jm[c16,2,a]]
        lines.append('| '+arm+' | '+' | '.join(f'{100*v:.2f}%' for v in values)+' |')
    lines += ['', 'Selective foreign records are scored both against the original history and their donor history. '
        'These are interventions between independently acquired whole records; they do not surgically edit an isolated weight component.', '',
        '| Selective foreign record at G16 | Original A | Original B | Donor A | Donor B |',
        '| --- | ---: | ---: | ---: | ---: |']
    for arm in ('foreign_a', 'foreign_b'):
        a = d.ARMS.index(arm); dm = donors[arm].mean(axis=0)
        values = [*rm[c16,2,a], *dm[c16,2,a]]
        lines.append('| '+arm+' | '+' | '.join(f'{100*v:.2f}%' for v in values)+' |')
    lines += ['', f'G16 protected-copy minus renewal joint success: {100*(jm[c16,2,d.ARMS.index("protected_copy")]-jm[c16,2,own]):+.2f} percentage points.',
        f'G16 minus G0 renewal joint success: {100*(jm[c16,2,own]-jm[c0,2,own]):+.2f} percentage points.', '',
        'Failed frozen development gates: '+(', '.join(decision['failed_gates']) or 'none')+'.', '',
        'No confidence intervals or population qualification are assigned to this small pilot. All base-network outcomes appear in network_outcomes.csv and summary.json. '
        'No outcome is excluded, no threshold is retuned, and engineering inputs are excluded from the eight-network pilot.', '',
        'All three loads receive four eight-sweep cue trials per body (1,920 unclamped-site updates), a common 64-neuron base, cue gain 4 and the same damage law. '
        'Single-rule conditions repeat identical trial pairs. A record has 2,016 unique values (16,128 payload bytes), stored in a 32,768-byte dense matrix. '
        'The supplied base has another 2,016 unique values. Copying does not require the simulated diagnostic bodies or the coactivity writer.', '',
        'The founder alone sees output teaching. Descendants receive cues, fresh births, the shared base and their immediate incoming record. '
        'Four independently reset cue responses are combined by a batch coactivity writer. This tests supplied conditional functions through replacement; '
        'it does not establish discovered competence, general continual learning, beneficial reciprocal repair or RDT forecasting superiority.', '']
    (out/'REPORT.md').write_text('\n'.join(lines))
    plot(out, summary)
    return summary


def plot(out, summary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    j, r = np.array(summary['mean_joint']), np.array(summary['mean_rules'])
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), layout='constrained')
    g = summary['checkpoints']; own = d.ARMS.index('renewal')
    for l, task, label in ((0, 0, 'A alone: A'), (1, 1, 'B alone: B'), (2, 0, 'Both: A'), (2, 1, 'Both: B')):
        axes[0].plot(g, 100*r[:, l, own, task], '-o', label=label)
    axes[0].plot(g, 100*j[:, 2, own], '--s', color='black', label='Both: joint')
    axes[0].set(title='Complete rewriting, separately scored rules', xlabel='Full activity replacements', ylabel='Success (%)', ylim=(-3, 103))
    axes[0].legend(fontsize=8)
    arms = ['renewal', 'protected_copy', 'damaged_copy', 'foreign_both', 'erased', 'read_off', 'write_off']
    values = [100*j[-1, 2, d.ARMS.index(a)] for a in arms]
    axes[1].bar(range(len(arms)), values, color=['#117a59', '#4688be', '#777777', '#a066aa', '#999999', '#bbbbbb', '#cccccc'])
    axes[1].set_xticks(range(len(arms)), [a.replace('_', '\n') for a in arms], fontsize=8)
    axes[1].set(title='Both rules at replacement 16', ylabel='Joint success (%)', ylim=(-3, 103))
    for ax in axes:
        ax.grid(axis='y', alpha=.15)
    fig.suptitle(f'H035 · {summary["independent_networks"]} networks · {summary["classification"].replace("_", " ").lower()}')
    fig.savefig(out/'overview.png', dpi=160); fig.savefig(out/'overview.pdf'); plt.close(fig)
