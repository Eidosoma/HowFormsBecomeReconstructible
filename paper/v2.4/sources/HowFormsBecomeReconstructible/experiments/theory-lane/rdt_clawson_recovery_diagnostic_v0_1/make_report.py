"""Render the complete audited diagnostic; no fits, new simulations or selections."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys
import time

ROOT=Path(__file__).resolve().parent
R=ROOT/'results_v1'


def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')


def main():
    start,cpu=time.monotonic(),time.process_time()
    p=read(ROOT/'protocol.json');done=read(R/'COMPLETE.json');audit=read(R/'AUDIT.json')
    assert done['status']=='COMPLETE' and audit['status']=='PASS'
    assert sha(R/'OUTPUTS.json')==done['output_manifest_sha256']
    assert all(sha(R/name)==value for name,value in read(R/'OUTPUTS.json')['sha256'].items())
    reference=Path(p['source']).parents[1]/'jobs/qualification_v2/inputs/parent/qualified/native/inherited/reference'
    sys.path.insert(0,str(reference))
    import cpu_preflight
    admission=cpu_preflight.collect();admission.update(planned_threads=1,purpose='Render audited diagnostic report and scientific plot')
    admission['within_limit']=admission['other_active_or_recently_busy_threads']+1<=12
    write(ROOT/'checks/CPU_REPORT.json',admission)
    assert admission['within_limit']
    a=read(R/'RESULTS.json');ts=read(R/'TRAJECTORIES.json')
    step_counts={}
    for noise in p['scope']['regimes']:
        selected=[t for t in ts if t['noise']==noise and t['original_class']==0]
        step_counts[noise]=[dict(from_generation=15+i,to_generation=16+i,
            incorrect_to_correct=sum(t['passed'][i]==0 and t['passed'][i+1]==1 for t in selected),
            correct_to_incorrect=sum(t['passed'][i]==1 and t['passed'][i+1]==0 for t in selected)) for i in range(18)]
    write(ROOT/'checks/TRANSITIONS_BY_GENERATION.json',dict(status='DESCRIPTIVE_DERIVATION_FROM_AUDITED_TRAJECTORIES',
        original_class=0,steps=step_counts,source_sha256=sha(R/'TRAJECTORIES.json'),
        note='Location of the final observed transition is descriptive and was not a preregistered forecasting horizon.'))
    figures=ROOT/'figures';figures.mkdir(exist_ok=False)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(10.5,4.1),sharey=True,constrained_layout=True)
    for ax,noise in zip(axes,p['scope']['regimes'],strict=True):
        g=a['cells'][noise]['0']
        ax.plot(a['generations'],g['observed_trajectory'],'o-',color='#1b6b61',label='Observed continuation mean',markersize=4)
        ax.plot(a['generations'],g['predicted_transition_trajectory'],'--',color='#bb6424',label='Two-state probe forecast')
        ax.scatter([33],[g['models']['quadratic_successor64']['mean_forecast']],marker='D',s=40,color='#5a458b',label='Fixed successor forecast')
        ax.set(title=noise.capitalize()+' cue noise',xlabel='Generation',ylim=(0,1),xticks=[15,18,21,24,27,30,33])
        ax.grid(alpha=.18)
    axes[0].set_ylabel('Probability of the original taught response')
    axes[0].legend(loc='upper left',fontsize=8,frameon=False)
    fig.suptitle('Originally failing packets: 8 founders, 64 continuations per noise condition\nFixed-panel development diagnostic; curves are averages, not confidence bounds',fontsize=11)
    fig.savefig(figures/'continuation_forecasts.png',dpi=180)
    fig.savefig(figures/'continuation_forecasts.svg')
    plt.close(fig)
    lines=[
        'Saved-data recovery diagnostic — completed and audited',
        '',
        'Renewal has a positive immediate paired benefit for the historically failing packets in this panel. The simple time-homogeneous two-state forecasting reduction adds no advantage over the existing successor predictor. Both findings are development results derived from already exposed records. The original matched-recovery study retains its six-of-six directional pass.',
        '',
        'The calculation used 64 packet/noise cases, 2,048 paired probe triples and all 256 saved continuations. Nine targeted tests passed. A separate scalar audit rechecked 8,192 probe readouts, 4,864 trajectory readouts, all contingency tables, 180 model/cell losses and 1,216 matrix-based forecast checks. All 162 previously reported cells for the 27 fixed predictors reproduced unchanged.',
        '',
        'Immediate benefit after a failed writer read (W=0):',
        'Original class | Noise | W=0 probes | Rewritten success | Original reread success | Paired difference | Helped / harmed',
    ]
    for state in ('0','1'):
        for noise in p['scope']['regimes']:
            v=a['cells'][noise][state]['paired']['writer_fail']
            lines.append(f"{state} | {noise} | {v['n']} | {v['successor_successes']}/{v['n']} ({100*v['successor_rate']:.1f}%) | {v['direct_successes']}/{v['n']} ({100*v['direct_rate']:.1f}%) | {100*v['paired_benefit']:+.2f} percentage points | {v['helped']} / {v['harmed']}")
    lines += ['',
        'Class 0 means historically failing at the archived boundary; class 1 means historically passing. W=0 is a separate, transient failure of a new writer probe. All comparisons evaluate the rewritten and preserved incoming packets with the same evaluation mask, birth state and noise. Thus apparent recovery on a fresh reread is explicitly controlled. The intervention is complete writer renewal versus preserving the original packet; it does not isolate writing from the writer stage’s damage.',
        '',
        'For originally failing packets, both positive pooled conditional benefits remain positive when any one founder is left out. Individual founders include negative benefits. The rare failed-writer subset of originally passing packets instead shows harm. Those rows contain only 29 and 20 probe events nested in eight founders, not that many independent lineages. A failed read alone therefore does not identify which action is beneficial in these data. Conditional rates weight packets by their probability of entering W=0; the two noise regimes need not select the same mixture. Their difference is not an unconfounded causal noise effect.',
        '',
        'Terminal forecasting for originally failing packets (Brier error; lower is better):',
        'Model | Extra standalone reads | Matched | Independent',
    ]
    for model in ['transition64_jeffreys','raw_successor64_jeffreys','raw_direct64_jeffreys','quadratic_successor64','linear_direct64','quadratic_direct64','mean_direct64','scale_direct64','expression_direct64','expression_direct8','quadratic_boundary0','archived_tt008']:
        cost=8 if model.endswith('direct8') else 0 if model.endswith('boundary0') or model=='archived_tt008' else 64
        lines.append(f"{model} | {cost} | {a['cells']['matched']['0']['models'][model]['brier']:.6f} | {a['cells']['independent']['0']['models'][model]['brier']:.6f}")
    lines += ['',
        'The two-state model forecasts terminal success of 61.9% under matched noise and 73.4% under independent noise, versus observed 67.2% and 53.1%. It loses to the existing fixed successor predictor in both regimes. It also loses to the simple successor-success fraction in both regimes. The raw successor fraction’s favorable matched-noise score is exploratory; it is not a newly confirmed winner. All 30 models and both original classes are retained in results_v1/ALL_30_MODELS.csv.',
        '',
        'The model fixes a symmetric half-count prior, estimates an initial success probability and two transition probabilities from 32 writer/successor pairs, and propagates for 18 transitions. The target’s first read never enters its forecast. Five of 16 originally failing packets under matched noise and two under independent noise had no successful writer probe, leaving their error-entry rows determined solely by the prior. The corresponding empty recovery rows among originally passing packets numbered seven and ten. These limitations are reported; no prior was tuned after results.',
        '',
        'The saved trajectories reveal a useful diagnostic lead: for the originally failing subset, every observed success/failure transition occurred by g18 under matched noise and g17 under independent noise. The later states persisted through g33 on these paths. This finite observation does not prove absorbing states or identify the cause. It suggests testing whether early reconstruction changes the composition of successful and failing states, so initial binary transition rates cease to transport. The plot is in figures/continuation_forecasts.png and .svg. Any use of the observed stabilization point as a new predictor would require a separate development design and prospective evaluation.',
        '',
        'Terminal and uninterrupted success remain distinct. Among originally failing packets, terminal success was 43/64 matched and 34/64 independent, while uninterrupted success across the saved g15–g33 reads was 20/64 and 25/64. No future readout expressed the opposite taught rule among the 4,864 saved readouts. That preserves the narrow scoring distinction here, not arbitrary historical information or a general mechanism of memory.',
        '',
        f"The read-only calculation took {done['wall_seconds']:.3f} wall seconds and {done['cpu_seconds']:.3f} CPU seconds, including its tests and audit. It performed zero new native simulations, reads, outcomes or model fits. These timings exclude preparation and report rendering. The original study’s acquisition and computation remain sunk costs. A fresh transition measurement requires 64 primary reads. Fresh acquisition of all 32 W/S/D triples requires 96, before audits and boundary acquisition; the existing combined assay used 128. Extra cost for extracting these contrasts from saved arrays is zero native reads. The raw transition model does not use B11, whereas the stronger learned comparators retain boundary/signed-transfer information.",
        '',
        'This is a bounded development diagnostic on eight already studied founders at one injury level. It establishes neither a population effect nor RDT-specific mathematics, a biological mechanism, an optimal repair schedule, or long-horizon intervention benefit. Future scheduling must evaluate paired actions over its own horizon with action and measurement costs. No additional native run is queued.',
        '',
        'Source: rdt_matched_recovery_v0_1/runs/development_v1; completed scientific audit and closeout are bound by protocol.json.',
        'Details: results_v1/RESULTS.json; results_v1/AUDIT.json; results_v1/ALL_30_MODELS.csv; protocol.json.',
        'Paper motivation: ../clawson_closed_loop_review_v0_1/REVIEW.txt.',
        '',
    ]
    with (ROOT/'REPORT.txt').open('x') as f:f.write('\n'.join(lines))
    write(ROOT/'checks/REPORT_COMPLETE.json',dict(status='COMPLETE',utc=datetime.now(timezone.utc).isoformat(),
        source_complete_sha256=sha(R/'COMPLETE.json'),report_sha256=sha(ROOT/'REPORT.txt'),
        png_sha256=sha(figures/'continuation_forecasts.png'),svg_sha256=sha(figures/'continuation_forecasts.svg'),
        script_sha256=sha(Path(__file__)),render_wall_seconds=time.monotonic()-start,render_cpu_seconds=time.process_time()-cpu,
        new_native_reads=0,new_fits=0))
    print('Diagnostic report, all-model table and trajectory figure complete; no further run launched.',flush=True)


if __name__=='__main__':main()
