"""Fixed complete-results report; unfavorable outcomes use the same template."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import support as s

LABELS={'candidate':'Signed-transfer candidate','expression_history':'Expression + history','expression_unsigned':'Expression + unsigned',
    'quadratic_unsigned':'Quadratic + unsigned','expression_unsigned_rbf_b2_r0.001':'Nonlinear expression rival','packet_plus_expression_rbf_b2_r0.001':'Nonlinear full-packet rival'}


def run(output):
    a=s.read(output/'analysis.json');manifest=s.read(output/'manifest.json');registration=s.read(s.HERE/'REGISTRATION.json');seal=s.read(output/'PREDICTION_SEAL.json')
    lines=['# TT008 prospective P02 validation','',f"**{a['scientific_verdict']}**. Independent native replay and scoring checks: PASS.",'',
        f"The fixed study completed {a['blocks']} new blocks, {a['records']:,} related history records and {a['predictions']:,} sealed predictions. All predictions were sealed at {seal['sealed_utc']} before any new post-boundary continuation. The model artifact and protocol were frozen before generating these blocks. No test-outcome refitting or model selection occurred.",'',
        'The population, endpoint and supplied apparatus match the development experiment. This is in-domain validation of an openly selected development candidate. It does not change TT007’s original primary result, validate P01, establish a causal state-capacity inequality or demonstrate cross-apparatus RDT generality.','',
        '## Fixed primary comparisons','',
        'The gain is baseline Brier loss minus candidate Brier loss, averaged first within each block and then across 64 blocks. Both one-sided 95% lower limits must exceed 0.002. Student-t inference is approximate and conditional on the fixed training sample; each block keeps its related histories, paired founders and recipients together.','',
        '| Primary rival | Mean Brier gain | Lower one-sided 95% limit | Upper one-sided 95% limit | Positive blocks | Lower limit >0.002 |','|---|---:|---:|---:|---:|---|']
    for name in registration['primary_baselines']:
        r=a['contrasts'][name];lines.append(f"| {LABELS[name]} | {r['mean']:+.6f} | {r['lower_one_sided95']:+.6f} | {r['upper_one_sided95']:+.6f} | {r['positive_blocks']}/64 | {r['passes_practical_superiority']} |")
    lines+=['',f"Conjunctive practical-superiority gate: **{'PASS' if a['primary_passed'] else 'NOT PASSED'}**. A failed lower-limit gate does not establish equality. The 0.002 margin is an operational predictive threshold, not a physical-energy or fitness claim.",'',
        '## All frozen rivals','',
        '| Model | Equal-block Brier error | Log loss |','|---|---:|---:|']
    for name in a['models']:
        r=a['metrics'][name]['all'];lines.append(f"| {LABELS[name]} | {r['brier']:.6f} | {r['log_loss']:.6f} |")
    lines+=['','The nonlinear full-packet rival receives all 512 outgoing weights. The other nonlinear rival receives the expression/history/unsigned channels. Secondary rival rankings do not replace the two primary comparisons. All models use the same 512 exposed development labels; candidate and comparator training/tuning and representation costs remain distinct. Kernel predictions are clipped to [0,1]; reported log loss clips the scored outcome probability below at 1e-15.','',
        '## Histories and exploratory strata','',
        '| History | Terminal successes / 1,024 |','|---|---:|']
    for name,r in a['history_counts'].items():lines.append(f"| {name} | {r['terminal_successes']} |")
    lines+=['','| Generation-14 status | Records | Terminal successes | Gain contribution vs expression/history | Gain contribution vs expression/unsigned |','|---|---:|---:|---:|---:|']
    for key,label in [('1','Passing'),('0','Failing')]:
        r=a['strata'][key];lines.append(f"| {label} | {r['n']} | {r['terminal_successes']} | {r['contrasts']['expression_history']['contribution_to_overall']:+.6f} | {r['contrasts']['expression_unsigned']['contribution_to_overall']:+.6f} |")
    lines+=['','Stratum contributions sum to the overall gain. These are descriptive diagnostics. Later success is a fresh scattered assay after continued rebuilding, not recovery under the same current injury.','',
        f"There are {a['strict_pairs']} strict spaced/clustered matches under the fixed both-pass/0.02 rule and {a['exact_pairs']} pairs with exactly equal output vectors. Approximate matches alone do not establish equal state-specific success probability. No repeated-future capacity estimate or causal mediation claim is made.",'',
        '| Fixed decision rule | Selected successes | Discordant pairs | Correct discordant choices | Ties on discordant pairs |','|---|---:|---:|---:|---:|']
    for name,r in a['matched_decisions'].items():lines.append(f"| {LABELS.get(name,name)} | {r['successes']:g} | {r['discordant']} | {r['discordant_correct']:g} | {r['discordant_ties']} |")
    lines+=['','## Technical evidence and limits','',
        f"Erased scattered controls succeeded {a['erased_scattered_successes']}/{a['erased_scattered_assays']}. Independent scoring checked {a['raw_terminal_rows_checked']:,} terminal rows against raw cue/port means and all block loss contrasts by scalar arithmetic. The largest sealed-prediction reconstruction discrepancy was {a['maximum_prediction_reconstruction_error']:.3g}.",'',
        'The complete known block passed every retained generation 3–32 boundary and terminal comparison before new test generation. Production acquisition and every new nonlinear read/capture were separately replayed byte for byte. Damage, reset, cue-end bodies, outgoing packets and temporal means are retained with array hashes. Source holding states are causally discarded and were not simulated; no holding-state endpoint is claimed.','',
        'The model search and sample plan used eight exposed development blocks. The plug-in 64-block power estimate was approximately 81.9% against the simple rival, versus 41.2% under the stated higher-variance sensitivity. No adaptation was made to improve those estimates after test access. Prediction separation is procedural within a shared filesystem, not independent custody or external replication.','',
        f"Execution used one process and one numerical thread, CPU affinity {manifest['cpu_affinity']}. The frozen runtime forecast was {manifest['forecast_seconds']/3600:.2f} hours. Inputs, fitted coefficients/kernel supports, registration, qualification, native arrays, predictions, scores, replay receipts and software identities are retained. The run has no automatic successor.",'',
        '![Prospective results](tt008_results.png)','']
    with (output/'REPORT.md').open('x') as f:f.write('\n'.join(lines))
    with plt.rc_context({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'}):
        fig,axes=plt.subplots(2,2,figsize=(14,9),layout='constrained');models=a['models']
        ax=axes[0,0];values=[a['metrics'][m]['all']['brier'] for m in models]
        ax.barh(range(len(models)),values,color=['#2765a2','#cc8c2b','#81909b','#81909b','#227a75','#81909b']);ax.set_yticks(range(len(models)),[LABELS[m] for m in models]);ax.invert_yaxis();ax.set_xlabel('Prospective Brier error (lower is better)');ax.set_title('A. All frozen models',loc='left')
        ax=axes[0,1]
        for i,name in enumerate(registration['primary_baselines']):
            r=a['contrasts'][name];ax.errorbar(r['mean'],i,xerr=r['mean']-r['lower_one_sided95'],fmt='o',capsize=5,label=LABELS[name])
        ax.axvline(.002,color='#b04a45',linestyle='--',label='Required gain .002');ax.axvline(0,color='#777',linewidth=.8);ax.set_yticks(range(2),[LABELS[m] for m in registration['primary_baselines']]);ax.set_xlabel('Brier improvement; two one-sided 95% limits');ax.set_title('B. Fixed primary claims',loc='left')
        ax=axes[1,0]
        for name in registration['primary_baselines']:ax.plot(range(64),a['contrasts'][name]['block_values'],'.-',linewidth=.6,label=LABELS[name])
        ax.axhline(0,color='#555',linewidth=.8);ax.set_xlabel('New block index 0–63');ax.set_ylabel('Baseline Brier − candidate Brier');ax.legend(frameon=False,fontsize=8);ax.set_title('C. Every block, including unfavorable cases',loc='left')
        ax=axes[1,1];x=np.arange(2)
        for offset,key,label,color in [(-.18,'1','Currently passing','#cc8c2b'),(.18,'0','Currently failing','#227a75')]:
            ax.bar(x+offset,[a['strata'][key]['contrasts'][m]['contribution_to_overall'] for m in registration['primary_baselines']],.35,label=label,color=color)
        ax.axhline(0,color='#555',linewidth=.8);ax.set_xticks(x,['Expression/history rival','Expression/unsigned rival']);ax.set_ylabel('Contribution to overall Brier improvement');ax.legend(frameon=False);ax.set_title('D. Descriptive current-status decomposition',loc='left')
        fig.suptitle('TT008: frozen models on 64 new blocks',fontsize=16,fontweight='bold')
        for ext in ['png','pdf','svg']:fig.savefig(output/f'tt008_results.{ext}',dpi=180)
        plt.close(fig)
