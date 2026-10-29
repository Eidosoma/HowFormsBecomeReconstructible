"""Archive the execution handoff and publish reviewed fresh-confirmation results."""
from pathlib import Path
import os,shutil,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *

run=ROOT/'runs/confirmation_v1'
complete=read(run/'COMPLETE.json');closeout=read(ROOT/'CLOSEOUT.json');findings=read(ROOT/'FINDINGS.json')
assert closeout['status']=='PASS_RETAINED_RECEIPT_AGGREGATE_AND_PRIMARY_ROW_REVIEW'
assert sha(run/'COMPLETE.json')==closeout['completion_sha256']
assert sha(ROOT/'FINDINGS.json')==closeout['findings_sha256']
assert read(ROOT/'COMPLETION_PROCESS_CHECK.json')['no_active_tt039_jobs']
decision=findings['confirmation'];classification=decision['joint_classification']
assert classification=='CONFIRMED_JOINT_LATE_WRITING_BENEFIT'
assert findings['independent_decision_review']['joint_classification']==classification
primary=findings['comparisons']['residual|all|all_masks|own']
b=primary['body'];r=primary['fresh_recipient'];within=primary['within_arm_changes']
bc=b['comparisons']['late_minus_preserve'];rc=r['comparisons']['late_minus_preserve']
near(b['target_credit_percent_by_arm'],[39.16015625,40.46630859375,43.212890625,32.470703125])
near(r['target_credit_percent_by_arm'],[25.,40.191650390625,39.4378662109375,31.60400390625])
assert bc['record_mean_counts']==dict(gain=389,harm=163,tie=472)
assert rc['record_mean_counts']==dict(gain=853,harm=91,tie=80)
assert primary['joint_record_mean_counts'][1]==[[22,11,130],[46,39,387],[23,30,336]]
assert within['late']['record_mean_counts']==dict(gain=354,harm=352,tie=318)
near(within['late']['equal_block_change_pp'],-.2197265625)
near(within['preserve']['equal_block_change_pp'],-4.3212890625)

handoff=read(ROOT/'QUEUE_V2_HANDOFF.json');verify(handoff['files'])
stamp=now();archive=ROOT/'completion_handoff_inputs';archive.mkdir(exist_ok=False)
paths=set(map(Path,handoff['files']))|{ROOT/n for n in (
    'QUEUE_V2_HANDOFF.json','CURRENT_EXECUTION.json','QUEUE_V2_STATUS.json','QUEUE_V2_COMPLETE.json',
    'QUEUE_FAILED.json','checks/qualification_v1/FAILED.json','LAUNCH.json','STARTUP_PERSISTENCE_CHECK.json')}
saved={}
for path in sorted(paths):
    dest=archive/path.relative_to(LANE);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
    h=sha(path);assert sha(dest)==h;saved[str(path)]=dict(snapshot=str(dest),sha256=h)
write(archive/'MANIFEST.json',dict(files=saved,archived_utc=stamp))

def replace_file(path,value):
    temp=path.with_name(path.name+'.tt039-complete.pending');write(temp,value);os.replace(temp,path)

proof=complete['verification'];current=read(ROOT/'CURRENT_EXECUTION.json')
current.update(status='COMPLETE_REVIEWED',updated_utc=stamp,completed_utc=complete['completed_utc'],
    actual_seconds=complete['seconds'],completed_blocks=64,retained_bytes=complete['retained_bytes'],verification=proof,
    closeout='TT039/CLOSEOUT.json',findings='TT039/FINDINGS.json',report='TT039/runs/confirmation_v1/REPORT.md',
    confirmation='TT039/runs/confirmation_v1/CONFIRMATION.json',scientific_classification=classification,
    processes_exited=True,no_active_jobs=True,scientific_results_inspected=True,new_production_outcomes_inspected=True,
    new_production_outcomes_generated=True,source_population_exposed_at_enrollment=False,source_population_exposed=True,
    source_population_reused=False,interim_scientific_outcomes_inspected=False,successor_started=False,
    full_source_checks_passed_during_run=True,qualification_status='PASS',benchmark_status='COMPLETE',
    primary_late_minus_preserve_pp=dict(body_at_1900=bc['equal_block_change_pp'],fresh_recipient=rc['equal_block_change_pp']),
    next_step='Incorporate this fresh confirmation into the lane synthesis; no successor experiment started')
replace_file(ROOT/'CURRENT_EXECUTION.json',current)

message="""
[TT039 fresh late-writing confirmation](TT039/README.md) is **complete and
reviewed: CONFIRMED_JOINT_LATE_WRITING_BENEFIT**. All 64 newly reserved blocks
finished on 23 October 2026 at 23:51:57 UTC, in **11 hours 40 minutes 17 seconds**
on two CPUs. Both co-primary endpoints pass the frozen late-minus-preservation
comparison in the residual family, own source, averaged over all four masks:

| Mean original-target recognition credit | Preservation | Late writing | Difference | Registered lower bound |
|---|---:|---:|---:|---:|
| Body at update 1900 | 39.16% | 43.21% | +4.0527 pp | +3.2630 pp |
| Fresh recipient after 1000 updates | 25.00% | 39.44% | +14.4379 pp | +13.6252 pp |

These are fractional recognition scores, not binary success rates. The decision
uses 64 paired block means, approximate Student-t bounds, one-sided alpha .025
per endpoint, Bonferroni family alpha .05 and margin zero. Both bounds exceed
zero. The conservative Hoeffding sensitivity bounds do not; no minimum practical
gain or distribution-free positive result is established.

All harms remain: body record means have **389 gains / 163 harms / 472 ties**;
recipient record means have **853 gains / 91 harms / 80 ties**. Negative-half
retention favors preservation by 3.0273 body and 4.0527 recipient points.
The later body advantage mainly reflects preservation declining after update
1000; the late-writing mean changes by -0.2197 points versus -4.3213 for
preservation. This does not establish stability of every body.

The run independently replayed 719,808 native arrays and performed 442,368 new
receiving assays across 512 new receiving conditions. Completion review checked
715 saved artifacts, all five checkpoint summaries, paired harms, and independent
primary-row and confidence-bound calculations. No interim scientific inspection
occurred. The initial validation-only timing failure and correction remain
preserved. All processes have exited. This fixed-schedule result does not establish
optimal timing, uninterrupted performance, indefinite stability, independent
teaching cues, general damage robustness or serial heredity. TT028 primary/joint
and TT036's confirmation classifications are unchanged. No successor has started.

See [report](TT039/runs/confirmation_v1/REPORT.md), [findings](TT039/FINDINGS.json)
and [review scope](TT039/CLOSEOUT.json).
"""
assert len(closeout['receipt_report_aggregate_and_primary_row_hashes_checked'])==715
for name in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md'):
    with (LANE/name).open('a') as f:f.write('\n'+message)

details="""
The prespecified writing windows were preservation (no writing), early (1–100),
late (901–1000), and full (1–1000). All bodies continued to update 1900, with
writing off after 1000. Every outgoing packet was tested in four fresh receiving
conditions per corruption, with matched recipient birth and forcing across arms.
No production source states or recipient outcomes were inherited from TT038.

| Schedule | Body at 1000 | Body at 1900 | Fresh-recipient credit |
|---|---:|---:|---:|
| Preservation | 43.48% | 39.16% | 25.00% |
| Early | 39.70% | 40.47% | 40.19% |
| Late | 43.43% | 43.21% | 39.44% |
| Full, then hold | 31.62% | 32.47% | 31.60% |

The pointwise two-sided 95% intervals are **+3.2630 to +4.8425 body points**
and **+13.6252 to +15.2505 recipient points**. The conservative distribution-free
Hoeffding lower sensitivities are -29.8998 and -19.5147 points, respectively.
The frozen gate uses the approximate Student-t rule. No secondary result can
rescue that gate. Blocks are the independent population units; record means,
physical masks, corruption draws and receiving draws are dependent observations.

Among 1,024 primary record means, 336 improve on both endpoints, 22 decline on
both, 153 move in opposing directions, and 513 tie on at least one endpoint.
Body block means improve in 55 blocks, decline in five and tie in four;
recipient block means improve in all 64. The late body's own 1900-minus-1000
change still has 354 record gains, 352 harms and 318 ties.

The common family has the same average direction: +3.8696 body and +14.7064
recipient points. Source and damage geometry matter: residual foreign-source
late-minus-preservation averages are -1.2939 body and -1.4648 recipient points.
Early writing gives 0.7538 more recipient points than late writing, while late
gives 2.7466 more body points. These are descriptive secondary comparisons.
All original histories, four credits and six arm contrasts are retained.

Freshness is supported by the reserved identities, declared random-seed inventory
and preproduction freeze. The identity search was bounded locally and is not
independent custody or global proof of non-use. Teaching and repair cues retain
their declared coupling. The finite channel is 256 binary64 values (2048 bytes).
No descendant chains were tested, and each packet's four receiving conditions
per corruption provide only a coarse estimate of its individual reliability.

The completion review reconciled all block receipts, all five checkpoint
aggregates, global weights/counts/joint marginals, within-arm changes, independent
integer reductions of primary saved rows, and the frozen decision. Full physical
replay and raw output checks passed during acquisition; closeout did not repeat
every physical trajectory or rehash every raw output. Review scope is explicit
in CLOSEOUT.json. The failed qualification v1 and its validation-only correction
are retained; v2 qualification and benchmark passed before the production freeze.

The prior handoff is preserved in
[the completion archive](completion_handoff_inputs/MANIFEST.json). The recorded
correction is in [CORRECTION.json](corrections/metadata_timer_v1/CORRECTION.json).
"""
(ROOT/'README.md').write_text('# TT039 — fresh confirmation of late writing\n\n'+message.replace('(TT039/','(')+'\n'+details)
with (PRIOR/'README.md').open('a') as f:
    f.write('\nTT039 is complete and reviewed on 64 fresh source blocks. The frozen late-minus-preservation comparison passes both co-primary outcomes: +4.0527 body points at 1900 and +14.4379 fresh-recipient points. Individual and geometry harms remain. See [TT039 findings](../TT039/README.md). No successor is running.\n')
successor=dict(study='TT039',status='COMPLETE_REVIEWED',current_execution='TT039/CURRENT_EXECUTION.json',
    closeout='TT039/CLOSEOUT.json',findings='TT039/FINDINGS.json',scientific_classification=classification,
    completed_utc=complete['completed_utc'],body_endpoint=1900,recipient_endpoint=1000,
    new_source_blocks=64,new_independent_receiving_draws=512,successor_started=False)
predecessor=read(PRIOR/'CURRENT_EXECUTION.json')
predecessor.update(authorized_successor=successor,administrative_updated_utc=stamp)
replace_file(PRIOR/'CURRENT_EXECUTION.json',predecessor)
intake=read(LANE/'prediction_intake_status.json')
intake['postwriting_body_followup']['authorized_successor']=successor
intake['fresh_late_writing_confirmation'].update(successor,actual_seconds=complete['seconds'],verification=proof,
    status_at_handoff='COMPLETE_REVIEWED',observed_phase='COMPLETE_REVIEWED',observed_utc=stamp,
    scientific_results_inspected=True,new_production_outcomes_generated=True,new_production_outcomes_inspected=True,
    source_population_exposed_at_enrollment=False,source_population_exposed=True,source_population_reused=False,
    interim_scientific_outcomes_inspected=False,processes_exited=True,new_receiving_assays=442368,
    full_qualification_pending_at_handoff=False,qualification_status='PASS',benchmark_status='COMPLETE')
intake['updated_utc']=stamp;replace_file(LANE/'prediction_intake_status.json',intake)
with (LANE/'exposure_register.jsonl').open('a') as f:
    f.write(json.dumps(dict(study='TT039',event='fresh_late_writing_confirmation_completed_and_reviewed',recorded_utc=stamp,
        completion_sha256=sha(run/'COMPLETE.json'),closeout_sha256=sha(ROOT/'CLOSEOUT.json'),findings_sha256=sha(ROOT/'FINDINGS.json'),
        scientific_classification=classification,source_population_exposed_at_enrollment=False,source_population_exposed=True,
        scientific_results_inspected=True,interim_scientific_outcomes_inspected=False,new_source_blocks=64,
        new_independent_receiving_draws=512,new_receiving_assays=442368,successor_started=False,
        TT028_primary='NOT_CONFIRMED',TT028_joint='NOT_CONFIRMED',TT036_confirmation_unchanged=True),sort_keys=True)+'\n')
bound_paths=[LANE/n for n in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md','prediction_intake_status.json',
    'exposure_register.jsonl','TT038/README.md','TT038/CURRENT_EXECUTION.json')]+[ROOT/n for n in (
    'README.md','CURRENT_EXECUTION.json','FINDINGS.json','CLOSEOUT.json','COMPLETION_PROCESS_CHECK.json',
    'RESULT_INSPECTION.json','completion_handoff_inputs/MANIFEST.json','admin/reconcile_completion.py','admin/completion_handoff.py')]
write(ROOT/'COMPLETION_HANDOFF.json',dict(status='PASS',recorded_utc=stamp,files={str(p):sha(p) for p in bound_paths},
    successor_started=False,scientific_classification=classification,review_scope=closeout['review_checks'],
    raw_dynamics_rechecked_in_closeout=False,failed_attempt_and_correction_preserved=True))
verify(read(ROOT/'COMPLETION_HANDOFF.json')['files']);assert inputs()==read(ROOT/'FREEZE.json')['inputs']
print(dict(status='COMPLETE_REVIEWED',blocks=64,seconds=complete['seconds'],archived_files=len(saved),
    bound_files=len(bound_paths),scientific_classification=classification,successor_started=False))
