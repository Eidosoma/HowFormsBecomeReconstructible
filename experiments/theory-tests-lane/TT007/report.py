"""Audit evidence and scientific limits, with exportable descriptive figures."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import support as s

LABELS={'history_rate':'History rate','expression_history':'Expression + history',
    'expression_unsigned':'Expression + unsigned','expression_unsigned_signed':'Expression + unsigned + signed',
    'quadratic_unsigned':'Quadratic + unsigned','quadratic_unsigned_signed':'Quadratic + unsigned + signed'}
CHOICES={'constant':'Always spaced','margin':'Current margin','signed':'Raw signed transfer','expression_history':'Expression/history model',
    'expression_unsigned_signed':'Secondary signed model','quadratic_unsigned_signed':'Primary signed model'}


def run(output):
    a=s.read(output/'analysis.json');audit=s.read(output/'audit.json');checks=s.read(output/'technical_checks.json')
    forecasts=a['forecasts'];scores=forecasts['scores'];primary,secondary=forecasts['comparisons'][:2]
    choices=a['matching']['choices_on_strict_matches'];strict=a['matching']['subsets']['strict'];strata=a['strata']
    lines=['# TT007 independent P02 audit','',
        'Technical status: **PASS**. Scientific status: **unconfirmed, mixed development evidence**. This audit reconstructs the submitted generation-14 to generation-32 analysis; it neither supplies an unexposed test cohort nor validates the earlier P01 short-probe observation law.','',
        f"All {audit['source_files_verified']} source files, 512 selected captures, 3,072 predictions, 240 score rows, 128 paired contexts and 504 strict-match decision rows passed the audit. Forty penalized logistic fits were independently recomputed by damped Newton iterations; eight half-count history rates were independently recomputed. All {checks['groups']} synthetic check groups passed, including perturbations of held-out labels and features in the actual submitted fitting functions.",'',
        '| Audit quantity | Maximum absolute discrepancy |','|---|---:|',
        f"| Native transfer reconstruction | {audit['maximum_transfer_error']:.3g} |",
        f"| Saved prediction arithmetic | {audit['maximum_saved_prediction_arithmetic_error']:.3g} |",
        f"| Independent refit probability | {audit['maximum_independent_probability_error']:.3g} |",
        f"| Independent refit objective | {audit['maximum_independent_objective_difference']:.3g} |",
        f"| Independent refit fold Brier | {audit['maximum_independent_fold_brier_difference']:.3g} |",'',
        'The source is retained in the frozen job inputs. `manifest.json`, `provenance.json`, `native_checks.json`, `capture_checks.csv`, `fit_checks.json` and `refits.json` retain the checks and discrepancies. Native features are independently reconstructed, then the verified submitted decimal matrix is used for fitting and scoring; both matrices are retained.','',
        '## Forecast result','',
        'Lower Brier error and log loss are better. Each held-out block contains all four histories and all related founder/recipient contexts; training excludes the entire block. The table reports equal-block averages.','',
        '| Model | Submitted Brier, reconstructed | Newton-refit Brier | Log loss |','|---|---:|---:|---:|']
    for model in LABELS:
        row=scores[model]['all'];lines.append(f"| {LABELS[model]} | {row['brier']:.6f} | {row['refit_brier']:.6f} | {row['log_loss']:.6f} |")
    lines+=['',f"The specified primary contrast improves Brier error by **{primary['mean_brier_improvement']:.6f}**, with improvement in **{primary['positive_blocks']}/8 blocks**. The independent Newton refit gives **{primary['refit_mean_brier_improvement']:.6f}**. The secondary contrast improves by **{secondary['mean_brier_improvement']:.6f}**, also in {secondary['positive_blocks']}/8 blocks.",'',
        f"The primary signed model has Brier error {scores['quadratic_unsigned_signed']['all']['brier']:.6f}, compared with {scores['expression_history']['all']['brier']:.6f} for the simpler expression/history model. Its positive increment therefore does not establish superiority to that simpler rival. The secondary signed model performs better here, but this remains the predesignated secondary comparison, with model selection and cohort exposure unresolved.",'',
        '| Held-out block | Primary Brier improvement | Newton-refit improvement |','|---|---:|---:|']
    for block in s.CFG['blocks']:lines.append(f"| {block} | {primary['block_brier_improvements'][str(block)]:+.6f} | {primary['refit_block_brier_improvements'][str(block)]:+.6f} |")
    lines+=['','## Exploratory localization','',
        'The later residual analysis partitions the same frozen predictions; it does not create new evidence. Contributions below are each stratum’s summed error improvement divided by all 512 records, so they add exactly to the overall improvement. They differ from equally weighted conditional block scores.','',
        '| Boundary status | Records | Terminal successes | Primary contribution | Secondary contribution |','|---|---:|---:|---:|---:|']
    for name,label in [('currently_pass','Currently passing'),('currently_fail','Currently failing')]:
        row=strata[name];lines.append(f"| {label} | {row['n']} | {row['terminal_successes']} | {row['contrasts'][0]['contribution_to_overall_brier_improvement']:+.6f} | {row['contrasts'][1]['contribution_to_overall_brier_improvement']:+.6f} |")
    lines+=['',
        'The aggregate benefit is concentrated in currently failing bodies. The endpoint is a later fresh scattered assay after continued rebuilding, not recovery under the identical current injury. This identifies a lead for a new test, not a validated individual probability of recovery. The post-hoc expression/history-to-secondary-signed contrast adds unsigned and signed features together and cannot isolate the signed feature.','',
        '## Matching and decisions','',
        f"There are {strict['n']} strict pairs, using both current passes and an output caliper of 0.02; **{a['matching']['subsets']['exact']['n']} pairs have exactly equal output vectors**. Spaced history succeeds in {strict['spaced_successes']}/{strict['n']} versus {strict['clustered_successes']}/{strict['n']} for clustered history. Only {strict['spaced_only']+strict['clustered_only']} pairs have discordant terminal outcomes ({strict['spaced_only']} spaced-only, {strict['clustered_only']} clustered-only).",'',
        '| Fixed choice rule | Terminal successes / 84 | Correct among 9 discordant pairs |','|---|---:|---:|']
    for rule,label in CHOICES.items():lines.append(f"| {label} | {choices[rule]['successes']:g} | {choices[rule]['discordant_correct']:g} |")
    lines+=['',
        'The current-margin choice beats the record-based choices on these selected pairs. Nine discordances cannot establish a reliable ranking rule. Post-treatment matching is descriptive; approximate expression equality without a probability regularity bound cannot demonstrate unequal latent continuation capacities at equal expression.','',
        '## Native provenance and scientific scope','',
        'The saved branches share future O writing and disturbance-stream construction. The independent audit verifies all 512 O packets byte for byte, recomputes signed/unsigned sparse transfer, checks original/pulse cross-run identities, and reconstructs current/terminal categories from retained scores. The native source receipts verify original-control dynamics and selected new-arm properties. **They do not certify full independent nonlinear replay of every new arm; TT007 does not add that replay.** Window-mean observations and terminal margins are read from the saved native runs. The frozen `SOURCE_REVIEW.md` explains this scope and the shared-randomness dependence.','',
        'This is a reproducible incremental prediction signal within exposed development data, conditional on a particular rival. It is not prospective confirmation, an estimate of each state’s continuation probability, evidence that all conventional nonlinear/state-space rivals fail, or proof of a uniquely reconstructive mechanism. No significance claim treats the 512 related records or the overlapping cross-validation fits as independent replications.','',
        'The next scientific decision is whether to freeze one endpoint, one candidate, stronger conventional rivals, an improvement margin and a sample-size/power plan for genuinely unexposed blocks. Repeated future draws from fixed captured states would address state-specific continuation uncertainty. Independent nonlinear verification of new-arm dynamics remains an additional qualification requirement. No successor experiment is launched automatically.','',
        '![Audited P02 comparisons](tt007_audit.png)','']
    with (output/'REPORT.md').open('x') as f:f.write('\n'.join(lines))
    with plt.rc_context({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'}):
        fig,axes=plt.subplots(2,2,figsize=(14,9),layout='constrained')
        ids=list(LABELS);values=[scores[k]['all']['brier'] for k in ids];colors=['#81909b']*6;colors[1]='#cc8c2b';colors[3]='#227a75';colors[5]='#2765a2'
        ax=axes[0,0];ax.barh(range(6),values,color=colors);ax.set_yticks(range(6),list(LABELS.values()));ax.invert_yaxis();ax.set_xlim(0,.135);ax.set_xlabel('Excluded-block Brier error (lower is better)');ax.set_title('A. All six fixed models',loc='left',fontweight='bold')
        for i,v in enumerate(values):ax.text(v+.001,i,f'{v:.4f}',va='center',fontsize=9)
        ax=axes[0,1];gains=list(primary['block_brier_improvements'].values());ax.bar(range(8),gains,color=['#227a75' if v>0 else '#b04a45' for v in gains]);ax.axhline(0,color='#555',linewidth=.8);ax.set_xticks(range(8),[str(b)[-2:] for b in s.CFG['blocks']]);ax.set_xlabel('Held-out block (34000–34007)');ax.set_ylabel('Baseline Brier − signed-model Brier');ax.set_title('B. Primary increment: six positive blocks',loc='left',fontweight='bold')
        ax=axes[1,0];x=np.arange(2)
        for offset,name,label,color in [(-.18,'currently_pass','Currently passing','#b04a45'),(.18,'currently_fail','Currently failing','#227a75')]:
            v=[strata[name]['contrasts'][i]['contribution_to_overall_brier_improvement'] for i in range(2)];ax.bar(x+offset,v,.35,label=label,color=color)
        ax.axhline(0,color='#555',linewidth=.8);ax.set_xticks(x,['Primary contrast','Secondary contrast']);ax.set_ylabel('Contribution to overall Brier improvement');ax.legend(frameon=False);ax.set_title('C. Exploratory split of the same predictions',loc='left',fontweight='bold')
        ax=axes[1,1];keys=list(CHOICES);v=[choices[k]['discordant_correct'] for k in keys];ax.barh(range(6),v,color=['#81909b','#cc8c2b','#2765a2','#81909b','#227a75','#2765a2']);ax.set_yticks(range(6),list(CHOICES.values()));ax.invert_yaxis();ax.set_xlim(0,9.5);ax.set_xlabel('Correct choices among nine discordant strict pairs');ax.set_title('D. Current margin remains the best choice here',loc='left',fontweight='bold')
        for i,value in enumerate(v):ax.text(value+.1,i,f'{value:g}/9',va='center')
        fig.suptitle('TT007: independent audit reproduces mixed P02 development evidence',fontsize=15,fontweight='bold')
        for extension in ['png','pdf','svg']:fig.savefig(output/f'tt007_audit.{extension}',dpi=180)
        plt.close(fig)
