"""Conditional whole-network inference for the fixed present-expression match."""
from pathlib import Path
import json
import numpy as np
from h005 import engine as e


def infer(current, signals, future, counts, config, audit_passed):
    n = len(current)
    index = e.e.m.rng(config['analysis_seed'], 'H005 whole-block bootstrap').integers(
        0, max(n, 1), (config['bootstrap_draws'], n))

    def estimate(values, directional=None):
        if not n:
            return dict(mean=None, low=None, high=None, equivalence_low=None,
                        equivalence_high=None, directional_lower=None)
        result = dict(mean=float(np.mean(values)), low=None, high=None, equivalence_low=None,
                      equivalence_high=None, directional_lower=None)
        if n > 1:
            means = np.asarray(values)[index].mean(axis=1)
            low, high, elo, ehi = np.quantile(means, [.025, .975, .05, .95])
            result.update(low=float(low), high=float(high), equivalence_low=float(elo), equivalence_high=float(ehi))
            if directional is not None:
                result['directional_lower'] = float(np.quantile(means, directional))
        return result

    gates = dict(at_least_64_matched_pairs=sum(counts)>=64,
                 at_least_16_nonempty_blocks=n>=16, integrity_passed=bool(audit_passed))
    validation = dict(success={h:estimate(current[:, i]) for i,h in enumerate(e.HISTORIES)})
    differences = dict(success=estimate(current[:, 1]-current[:, 0]))
    differences.update({f'output_{k}':estimate(signals[:, 1, k]-signals[:, 0, k]) for k in range(4)})
    validation['differences'] = differences
    for h in e.HISTORIES:
        stat = validation['success'][h]
        gates[h+'_validation_success_at_least_90pct'] = stat['mean'] is not None and stat['mean']>=.90
    for name, stat in differences.items():
        gates['current_'+name+'_equivalent_within_5pp'] = (
            stat['equivalence_low'] is not None and stat['equivalence_low']>=-.05 and stat['equivalence_high']<=.05)
    own = e.ARMS.index('renewal')
    contrasts = dict(history_gain4_minus_gain1=estimate(future[:, -1, 1, own]-future[:, -1, 0, own], .05/5))
    for control in ['foreign', 'read_off', 'write_off', 'damaged_copy']:
        contrasts['gain4_own_minus_'+control] = estimate(future[:, -1, 1, own]-future[:, -1, 1, e.ARMS.index(control)], .05/5)
    for name, stat in contrasts.items():
        minimum = .10 if name=='history_gain4_minus_gain1' else .15
        gates[name+'_minimum_effect'] = stat['mean'] is not None and stat['mean']>=minimum
        gates[name+'_positive_adjusted_lower'] = stat['directional_lower'] is not None and stat['directional_lower']>0
    result = dict(qualified=all(gates.values()) if config['mode']=='development' else None,
                  gates=gates, primary_contrasts=contrasts, directional_family_size=5,
                  current_validation=validation,
                  terminal={h:{a:estimate(future[:, -1, i, j]) for j,a in enumerate(e.ARMS)}
                            for i,h in enumerate(e.HISTORIES)})
    return result, estimate


def mean_pairs(values, eligible):
    values = np.asarray(values)
    return values.reshape(*values.shape[:-2], 16)[..., eligible.ravel()].mean(axis=-1)


def analyze(out):
    out = Path(out); config = json.loads((out/'config.json').read_text())
    rows=[]; counts=[]; current=[]; current_signals=[]; future=[]; persistence=[]; body=[]
    all_future=[]; pair_future=[]; all_eligibility=[]; norms=[]; links=[]
    for seed in config['seeds']:
        with np.load(out/f'present_{seed}.npz') as p:
            eligible=p['eligible']; count=int(eligible.sum()); counts.append(count); all_eligibility.append(eligible)
            norm=p['record_norm']; cue=p['cue_link']
            present=p['validation_success'].mean(axis=0)
            present_signals=p['validation_signals'].mean(axis=0)
        successes=[]; uninterrupted=[]; body_success=[]
        for fork in range(e.FORKS):
            with np.load(out/f'future_{seed}_{fork:02d}.npz') as raw:
                successes.append(raw['success']); uninterrupted.append(raw['uninterrupted']); body_success.append(raw['body_success'])
        successes=np.array(successes); uninterrupted=np.array(uninterrupted); body_success=np.array(body_success)
        pair_future.append(successes[:, -1].mean(axis=0))
        full=successes.mean(axis=(0, -2, -1)); all_future.append(full)
        row=dict(seed=seed, eligible_pairs=count, candidate_pairs=16, all_candidate_success=full.tolist())
        if count:
            c=mean_pairs(present, eligible)
            s=present_signals[:, eligible].mean(axis=1)
            f=mean_pairs(successes, eligible).mean(axis=0)
            u=mean_pairs(uninterrupted, eligible).mean(axis=0)
            b=mean_pairs(body_success, eligible).mean(axis=0)
            current.append(c); current_signals.append(s); future.append(f); persistence.append(u); body.append(b)
            norms.append(mean_pairs(norm, eligible)); links.append(mean_pairs(cue, eligible))
            row.update(matched_current_success=c.tolist(), matched_current_signals=s.tolist(),
                       matched_future_success=f.tolist(), matched_uninterrupted=u.tolist())
        rows.append(row)
    current=np.array(current).reshape(-1, 2); current_signals=np.array(current_signals).reshape(-1, 2, 4)
    future=np.array(future).reshape(-1, 4, 2, len(e.ARMS))
    persistence=np.array(persistence).reshape(-1, 2, len(e.ARMS))
    audited=json.loads((out/'audit.json').read_text())['passed']
    decision,estimate=infer(current,current_signals,future,counts,config,audited)
    summary=dict(experiment='H005', classification=config['classification'], blocks=len(rows),
        matched_blocks=len(current), candidate_pairs=len(rows)*16, eligible_pairs=sum(counts),
        histories=e.HISTORIES, arms=e.ARMS, checkpoints=e.CHECKPOINTS, forks=e.FORKS,
        decision=decision, block_rows=rows, audit_passed=audited,
        matched_mean_success=future.mean(axis=0).tolist() if len(future) else None,
        all_candidate_mean_success=np.mean(all_future,axis=0).tolist(),
        matched_body_success=np.mean(body,axis=0).tolist() if body else None,
        matched_mean_source_norm=np.mean(norms,axis=0).tolist() if norms else None,
        matched_mean_source_cue_link=np.mean(links,axis=0).tolist() if links else None,
        uninterrupted={h:{a:estimate(persistence[:, i, j]) for j,a in enumerate(e.ARMS)} for i,h in enumerate(e.HISTORIES)},
        descriptive_history_differences={a:estimate(future[:, -1, 1, j]-future[:, -1, 0, j]) for j,a in enumerate(e.ARMS)})
    e.e.save(out/'summary.json', summary)
    np.savez_compressed(out/'pair_summary.npz', seeds=config['seeds'], eligible=np.array(all_eligibility),
                        terminal_future_probability=np.array(pair_future), histories=e.HISTORIES, arms=e.ARMS)
    def pct(stat):
        if stat['mean'] is None:return 'no matched pairs'
        return f"{100*stat['mean']:.2f}%"+(f" [{100*stat['low']:.2f}, {100*stat['high']:.2f}]" if stat['low'] is not None else ' [no interval]')
    verdict='ENGINEERING_ONLY' if config['mode']=='benchmark' else 'DEVELOPMENT_CANDIDATE' if decision['qualified'] else 'DOES_NOT_QUALIFY'
    lines=['# H005: matched present expression and future continuation','',
        f"{config['classification']}. Decision: **{verdict}**.",
        f"{sum(counts)}/{len(rows)*16} candidate pairs matched in {len(current)}/{len(rows)} base networks. Eight future branches per pair; 16 additional replacements.",
        'Inputs are exposed H003 development checkpoints; future tapes are new. Every candidate pair was simulated, including nonmatches. The independent unit is the base network.', '',
        '| Packet history | Validation current success | Terminal renewed success | Uninterrupted success | Protected-copy terminal success |',
        '|---|---:|---:|---:|---:|']
    for h in e.HISTORIES:
        lines.append(f"| {h} | {pct(decision['current_validation']['success'][h])} | {pct(decision['terminal'][h]['renewal'])} | {pct(summary['uninterrupted'][h]['renewal'])} | {pct(decision['terminal'][h]['protected_copy'])} |")
    lines.extend(['','## Decisions and controls','',
        'Failed gates: '+(', '.join(k for k,v in decision['gates'].items() if not v) or 'none')+'.',
        'Current-expression validation uses separate probes and 90% intervals contained within the prespecified five-point bounds for success and all four output means. These probes never change eligibility.',
        'Primary future contrasts use one-sided Bonferroni percentile lower bounds at .05/5. Displayed intervals are marginal 95% whole-network bootstrap intervals. All mean-effect minima and coverage gates are required.', '',
        '| Primary difference | Estimate [95% interval], percentage points | Adjusted lower, points |','|---|---:|---:|'])
    for name,stat in decision['primary_contrasts'].items():
        lower='unavailable' if stat['directional_lower'] is None else f"{100*stat['directional_lower']:.2f}"
        lines.append(f'| {name} | {pct(stat)} | {lower} |')
    lines.extend(['','| Record arm | Gain-1-history terminal success | Gain-4-history terminal success |','|---|---:|---:|'])
    for arm in e.ARMS:lines.append(f"| {arm} | {pct(decision['terminal'][e.HISTORIES[0]][arm])} | {pct(decision['terminal'][e.HISTORIES[1]][arm])} |")
    lines.extend(['','## Interpretation boundary','',
        'The future reader, writer, damage law and time budget are identical across histories. Equalized packets must yield identical future activity and records. Present matching concerns a finite output observer; it does not assert identical hidden states or exact latent readout probabilities.',
        'Matching after different histories does not isolate the total or direct causal effect of past gain. Paired packet transplantation tests their consequences within the selected set. Full block counts, empty blocks, current validation intervals, and all candidate-pair outcomes are retained in summary.json and pair_summary.npz.',
        'Failure of coverage, current validation or the primary cannot be replaced by a favorable all-candidate, intermediate-horizon or uninterrupted result. This study fits no predictor and establishes no unique theory. H004 confirmation remains unchanged.',
        'Each packet still has 2016 independent symmetric entries, stored as float64 during dynamics. Exact ternary int8 archival coding saves disk space without changing the transmission boundary. Copying requires less computation than the diagnostic bodies simulated here. No private model, state or result enters this study.',
        f'Retained audit passed: {audited}.',''])
    (out/'REPORT.md').write_text('\n'.join(lines))
    plot(out, summary)


def plot(out, summary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(13,4),layout='constrained')
    rows=summary['block_rows']; axes[0].bar(range(len(rows)),[r['eligible_pairs'] for r in rows],color='#477b93')
    axes[0].set(title='Matching coverage',xlabel='Independent base network',ylabel='Eligible pairs (of 16)',ylim=(0,17))
    colors=['#777777','#117a59']
    if summary['matched_mean_success'] is not None:
        values=np.array(summary['matched_mean_success'])
        for i,h in enumerate(e.HISTORIES):
            current=summary['decision']['current_validation']['success'][h]['mean']
            axes[1].plot([0,*e.CHECKPOINTS],100*np.r_[current,values[:,i,0]],'-o',label=h,color=colors[i])
        for i,h in enumerate(e.HISTORIES):
            rates=[summary['decision']['terminal'][h][a]['mean'] for a in e.ARMS]
            axes[2].bar(np.arange(len(e.ARMS))+(i-.5)*.36,100*np.array(rates),width=.36,label=h,color=colors[i])
    else:
        axes[1].text(.5,.5,'No exact matches',ha='center',transform=axes[1].transAxes)
    axes[1].set(title='Matched records under a common future',xlabel='Additional replacements',ylabel='Fresh-reader success (%)',ylim=(-3,103))
    axes[1].legend(fontsize=7)
    axes[2].set(title='Terminal record controls',ylabel='Success (%)',ylim=(-3,103))
    axes[2].set_xticks(range(len(e.ARMS)),e.ARMS,rotation=45,ha='right',fontsize=7)
    for ax in axes:ax.grid(axis='y',alpha=.15)
    fig.suptitle(f"H005 · {summary['eligible_pairs']} matched pairs in {summary['matched_blocks']} base networks\n{summary['classification'].replace('_',' ').title()}",fontsize=11)
    fig.savefig(out/'overview.png',dpi=160); fig.savefig(out/'overview.pdf'); plt.close(fig)
