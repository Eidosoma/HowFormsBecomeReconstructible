"""Publish verified local findings and update the lane handoff; no new experiment."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from study import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
 run=ROOT/'runs/fresh_one_read_v1';review=read(ROOT/'completion_review_v1/REVIEW.json')
 process=read(ROOT/'completion_review_v1/PROCESS_CHECK.json');complete=read(run/'COMPLETE.json')
 assert review['status']==process['status']=='PASS' and complete['inputs']==inputs()
 assert review['evidence'][str(run/'COMPLETE.json')]==sha(run/'COMPLETE.json')
 verify(complete['outputs']);sums=arrays(run/'SUMMARY.npz');inference=read(run/'INFERENCE.json')
 prior=ROOT/'completion_handoff_inputs';prior.mkdir(exist_ok=False)
 paths=[LANE/n for n in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md','prediction_intake_status.json','exposure_register.jsonl')]
 paths += [ROOT/'README.md',ROOT/'CURRENT_EXECUTION.json'];copies={}
 for p in paths:
  q=prior/p.relative_to(LANE);q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
  assert sha(p)==sha(q);copies[str(p)]=dict(copy=str(q),sha256=sha(q))
 write(prior/'MANIFEST.json',copies)
 ri=REGIMES.index('mixed_unmarked');labels=['Preserve','Forest repair','Screened forest']
 fig,axes=plt.subplots(1,3,figsize=(12,4.6),gridspec_kw={'width_ratios':[1,1.2,1]})
 xx=np.arange(3);edits=sums['sum_edit_counts'][0,ri]
 axes[0].bar(xx,edits,color=['#A9B2BD','#74879B','#315A7D']);axes[0].set_ylabel('Edited records / 512');axes[0].set_ylim(0,580)
 for x,v in zip(xx,edits):axes[0].text(x,v+10,str(v),ha='center',fontsize=9)
 for dx,ep,color,label in ((-.19,'intended','#1864A2','Intended task'),(.19,'opposite','#D87825','Opposite task')):
  levels=sums['equal_'+ep+'_rates'][0,ri]*100
  axes[1].bar(xx+dx,levels,width=.36,color=color,label=label)
  for x,v in zip(xx+dx,levels):axes[1].text(x,v+.35,f'{v:.2f}',ha='center',fontsize=8)
 axes[1].set_ylim(0,21);axes[1].set_ylabel('Success across all 2,048 contexts (%)')
 axes[1].legend(loc='upper center',ncol=1,frameon=False,fontsize=8)
 margins=sums['equal_intended_margin_means'][0,ri]
 axes[2].bar(xx,margins,color=['#A9B2BD','#74879B','#315A7D']);axes[2].set_ylim(-.94,.04)
 axes[2].set_ylabel('Mean intended margin (higher is better)')
 for x,v in zip(xx,margins):axes[2].text(x,v-.035,f'{v:.3f}',ha='center',va='top',fontsize=9)
 for ax in axes:
  ax.set_xticks(xx,labels,rotation=20,ha='right',fontsize=8);ax.spines[['top','right']].set_visible(False)
  ax.set_axisbelow(True);ax.grid(axis='y',alpha=.15)
 fig.suptitle('TT049 mixed unmarked damage: fewer edits and harms, with an explicit margin tradeoff',fontsize=12)
 fig.text(.035,.04,'32 fresh source blocks; 512 records; four paired futures each. Wrong-history controls remain accepted.',fontsize=9)
 fig.subplots_adjust(left=.07,right=.98,wspace=.42,top=.87,bottom=.23)
 for name in ('FINDINGS.png','FINDINGS.svg'):assert not (ROOT/name).exists();fig.savefig(ROOT/name,dpi=180)
 plt.close(fig)
 rows=[]
 for ai,label in enumerate(labels):
  rows.append(f"| {label} | {int(edits[ai])}/512 | {int(sums['sum_intended_counts'][0,ri,ai])}/2048 — {sums['equal_intended_rates'][0,ri,ai]*100:.2f}% | {int(sums['sum_opposite_counts'][0,ri,ai])}/2048 — {sums['equal_opposite_rates'][0,ri,ai]*100:.2f}% | {margins[ai]:.4f} |")
 intervals=[]
 for label,key,scale in [('Intended success change (pp)','intended_S_minus_G',100),('Opposite success change (pp)','opposite_S_minus_G',100),
                          ('Intended margin change','intended_margin_S_minus_G',1),('Edited records avoided (pp)','edits_avoided',100)]:
  v=inference['regimes']['mixed_unmarked'][key]
  interval=lambda x:'['+', '.join(f'{z*scale:.3f}' for z in x)+']'
  intervals.append(f"| {label} | {v['mean']*scale:.3f} | {interval(v['interval95'])} | {interval(v['bounded_interval95'])} |")
 findings='''# TT049 — the screening benefit carries to fresh sources, with limits

TT049 completed on **31 October 2026 at 14:40:47 UTC**. Production took
2 h 36 m 21 s on two CPUs, after 10 m 22 s of excluded qualification. The
independent saved-evidence review passed on 1 November. All 35 recorded
controller/worker processes have exited. No successor has been launched.

This was the frozen one-read test proposed after TT048 development. It enrolled
**32 new source blocks, eight per writing history, all 512 generation-14 records,
and four new matched receiving futures per record**. All 417 initially passing
and 95 initially failing records remain. Each arm/regime contains 2,048 paired
receiving contexts; population inference uses the 32 independent source blocks.
These are fresh in-domain records, not a new physical model or noise-pairing test.

## Mixed unmarked damage: primary panel

| Arm | Edited records | Intended-task success | Opposite-task success | Mean intended margin |
|---|---:|---:|---:|---:|
'''+ '\n'.join(rows)+'''

The screen avoids 342/512 edits (**66.80%**) and preserves every observed
intended rescue from unconditional forest repair. Relative to preservation,
both methods rescue **329** receiving contexts. Unconditional repair harms 17
previously successful contexts; screening harms five. The screen's 12 extra
intended successes therefore come entirely from preserving existing success.
Eleven records have a higher four-future success mean than under unconditional
repair; 501 tie and none have a lower mean. Nine block means improve and 23 tie.

There are still five paired harms versus preservation, affecting five record
means, and no guarantee that rescue retention holds outside this finite test.
All record gains/harms and all three paired arm tables remain in the outputs.

Screening also preserves five opposite-task successes that unconditional repair
had removed. Both methods create 240 opposite-task successes where preservation
fails that opposite-task criterion. Thus opposite success rises from 242 to
247 contexts. This is not correction of the intended historical identity.

Average intended margin falls by **.1355** compared with unconditional repair,
in 31 of the 32 blocks. It remains above preservation: the margin improvement
over preservation is +.38495 for unconditional repair and +.24940 for screening.
Some skipped edits help below the binary success threshold. Fewer edits and
higher threshold success do not establish uniform improvement across endpoints.
Every record still pays for forest inference; edited-record counts are not a
measurement of energy, total CPU saving, or later serial reliability.

![Mixed-damage findings](FINDINGS.png)

## The other regimes and wrong-history controls

With sign flips, screening reduces edits from 512 to 194, retains all 359
intended rescues, and reduces paired harms from 34 to 10. Intended success rises
from 369/2048 (18.02%) to 393/2048 (19.19%). Opposite success also rises from
353/2048 (17.24%) to 361/2048 (17.63%), and intended margin falls by .0790 relative
to unconditional repair. These remain separate outcomes.

For original packets, both repairs achieve 1789/2048 (87.35%) intended success,
versus 1670/2048 (81.54%) for preservation. Both retain 10 paired harms against
preservation. With added missing edges, screening gives 1766/2048 (86.23%)
intended success versus 1765/2048 (86.18%) for unconditional repair and 1374/2048
(67.09%) for preservation; paired harms are 13 and 14, respectively. The screen
has no observed rescue loss in any input regime, but this is an empirical result,
not an equivalence or noninferiority claim.

The screen accepts **all 512 records in both wrong-history panels**:

| Control | Intended success, all arms | Opposite success, all arms | Screen edits |
|---|---:|---:|---:|
| Actual opposite founder's learned packet | 0/2048 | 2048/2048 — 100% | 16/512 |
| Balanced wrong-task construction | 0/2048 | 1892/2048 — 92.38% | 0/512 |

Acceptance is distinct from editing: 496 of the learned wrong-history packets
and all balanced wrong packets are accepted unchanged. The balanced aligned
control also receives no edits and achieves 1892/2048 intended successes. All
arms fail on complete erasure. Control labels occur only in construction and
scoring; the screen receives no historical orientation. Every algorithm output
still marks history **UNVERIFIED**.

## Uncertainty and scope

The preregistered all-record S-minus-G quantities for mixed damage are below.
The intervals are **pointwise**, not simultaneous across all endpoints/regimes.
The Welch–Satterthwaite estimates and the much wider distribution-free bounds
must not be presented as equally strong claims.

| Quantity | Estimate | Stratified 95% interval | Bounded 95% interval |
|---|---:|---:|---:|
'''+ '\n'.join(intervals)+'''

The bounded interval supports a reduction in edit frequency; it does not resolve
the signs of the modest success changes or margin change. When estimated
variance is zero, the frozen method uses a nonzero bounded interval. For example,
zero observed intended rescues lost has a [0, .2401] bounded interval for the
population-average rate, rather than a zero-width certainty claim. No composite
positive verdict or equivalence claim was specified. Four futures still give
coarse estimates for each particular record.

The [production report](runs/fresh_one_read_v1/REPORT.md),
[all summary arrays](runs/fresh_one_read_v1/SUMMARY.npz) and
[all population intervals](runs/fresh_one_read_v1/INFERENCE.json) retain all
regimes, source histories, original pass/fail strata, selected-case denominators,
paired harms and separate margins. Conditional receiving Monte Carlo errors are
kept distinct from source-population intervals.

## Verification and decision

[The completion review](completion_review_v1/REVIEW.json) verified all 48 frozen
inputs, 1,310 production files and 109 qualification files. It checked 480 fresh
source stream births and all 448 source packet-chain links, independently
reconstructed endpoints from 196,608 retained port-window means, independently
reduced 896 block arrays and 62 global arrays, and checked all 104 population
intervals. Screen packet, state and endpoint identities passed. The maximum
compensated-mean discrepancy was 6.66e-16 with no threshold-flag disagreement.
Native source and receiving dynamics were independently replayed during
production; this completion review generated no new physical futures.

The scientific inputs and frozen rule are unchanged. Production retained about
312 MB, below the two-GiB study cap, and finished before its 16:15 UTC conservative
forecast. The closeout and original launch handoff are retained locally.

The supported contribution is a fixed, simple screen that substantially reduces
edits and avoids some harms while retaining the observed binary rescues on new
records. It still accepts coherent wrong history and gives up continuous-margin
improvement. Any attempt to verify or recover historical identity needs a
separate information design, with an explicit historical reference and absent
or misleading-reference controls. These results do not establish serial safety
and do not trigger a large serial confirmation. No new run is active.
'''
 with (ROOT/'FINDINGS.md').open('x') as f:f.write(findings)
 stamp=now()
 (ROOT/'README.md').write_text('''# TT049 — complete and independently reviewed

TT049 completed **31 October 2026 at 14:40 UTC**. Production took **2 h 36 m**;
the independent completion review passed on 1 November. No TT049 worker or
successor remains active.

On 32 new source blocks, 512 records and four matched futures per record, the
mixed-damage screen reduced edited records from **512 to 170**, retained all
**329 observed rescues**, and reduced paired harms from **17 to 5**. Intended
success rose from **16.21% to 16.80%** compared with unconditional graph repair.

The limits also persisted: opposite-task success rose from **11.82% to 12.06%**,
mean intended margin fell by **.1355**, and all coherent wrong-history controls
passed the screen. This supports the narrow edit/preservation benefit, with
explicit endpoint tradeoffs. Historical status remains UNVERIFIED.

See [findings, uncertainty and figure](FINDINGS.md), [completion review](completion_review_v1/REVIEW.json),
[production tables](runs/fresh_one_read_v1/REPORT.md), and the unchanged
[protocol](PROTOCOL.md). The previous launch handoff is preserved in
[completion_handoff_inputs](completion_handoff_inputs/MANIFEST.json).
''')
 note=f'''

TT049 completed 31 October 2026 at 14:40 UTC and passed independent review
{stamp}. See [TT049 findings](TT049/FINDINGS.md). The fixed fresh-source test
retained all 512 records across 32 independent blocks, including 95 initial
failures, with four paired receiving futures each. Mixed damage: screening
reduces edits 512→170, retains all 329 observed intended rescues and reduces
paired harms 17→5. Intended success rises 16.21%→16.80%; opposite success also
rises 11.82%→12.06%, and mean intended margin falls .1355 versus unconditional
repair. All coherent wrong-history controls remain accepted. No equivalence,
historical-verification or serial-safety claim follows. Pointwise and bounded
intervals remain visible, including nonzero fallback intervals for zero observed
variance. All native/evidence checks passed; no new run is active.
'''
 for name in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md'):
  with (LANE/name).open('a') as f:f.write(note)
 intake=read(LANE/'prediction_intake_status.json');intake['updated_utc']=stamp
 intake['fresh_graph_screen_test'].update(status='COMPLETE_REVIEWED',reviewed_utc=stamp,
  report='TT049/FINDINGS.md',review='TT049/completion_review_v1/REVIEW.json',scientific_results_inspected=True,
  source_population_exposed=True,no_active_jobs=True,mixed_edits_before_after=[512,170],
  mixed_intended_success_before_after=[332/2048,344/2048],mixed_opposite_success_before_after=[242/2048,247/2048],
  mixed_paired_harms_before_after=[17,5],mixed_rescues_retained=329,mixed_margin_change=-.1355479023294196,
  coherent_wrong_history_not_rejected=True,no_equivalence_claim=True,automatic_successor=False)
 replace(LANE/'prediction_intake_status.json',intake)
 current=read(ROOT/'CURRENT_EXECUTION.json');current.update(status='COMPLETE_REVIEWED',phase='COMPLETE_REVIEWED',updated_utc=stamp,
  reviewed_utc=stamp,report='TT049/FINDINGS.md',review='TT049/completion_review_v1/REVIEW.json',production_results_inspected=True,no_active_jobs=True)
 replace(ROOT/'CURRENT_EXECUTION.json',current)
 with (LANE/'exposure_register.jsonl').open('a') as f:
  f.write(json.dumps(dict(recorded_utc=stamp,study='TT049',event='completed_results_reviewed',blocks=BLOCKS,
   source_population_now_exposed=True,all_production_results_exposed=True,complete_sha256=sha(run/'COMPLETE.json'),
   no_new_physical_futures=True,automatic_successor=False),sort_keys=True)+'\n')
 files=paths+[ROOT/n for n in ('FINDINGS.md','FINDINGS.png','FINDINGS.svg','admin/review.py','admin/closeout.py',
  'completion_review_v1/REVIEW.json','completion_review_v1/PROCESS_CHECK.json','completion_review_v1.log',
  'completion_handoff_inputs/MANIFEST.json','runs/fresh_one_read_v1/COMPLETE.json')]
 value=dict(status='PASS',recorded_utc=stamp,files={str(p):sha(p) for p in files},
  complete_sha256=sha(run/'COMPLETE.json'),review_sha256=sha(ROOT/'completion_review_v1/REVIEW.json'),
  original_scientific_inputs_unchanged=True,all_production_results_exposed=True,no_active_jobs=True,
  no_new_physical_futures=True,automatic_successor=False)
 write(ROOT/'CLOSEOUT.json',value);verify(value['files']);assert inputs()==complete['inputs']
 print(json.dumps(dict(status='PASS',bound_files=len(files),report='TT049/FINDINGS.md',no_active_jobs=True)))


if __name__=='__main__':main()
