"""Publish the checked full-cohort result and archive mutable handoffs."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os

ROOT=Path(__file__).resolve().parents[1]
PACKAGE=ROOT.parent
LANE=PACKAGE.parent
RUN=ROOT/'runs/resume_v1'
CHECKS=ROOT/'checks'
INPUT=PACKAGE/'jobs/replication_v1/inputs'
CONTROL=ROOT/'jobs/resume_v1/inputs'


def read(p):return json.loads(p.read_text())


def sha(p):
    with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def write(p,value):
    with p.open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


audit=read(CHECKS/'INDEPENDENT_CLOSEOUT_AUDIT.json')
complete=read(RUN/'COMPLETE.json')
analysis=read(RUN/'ANALYSIS.json')
assert audit['status']=='PASS' and audit['complete_sha256']==sha(RUN/'COMPLETE.json')
assert audit['decision']==complete['decision']=='REPEATED_REWRITE_REPLICATION_UNRESOLVED'
assert read(CHECKS/'CLOSEOUT_HOST_PROCESS_CHECK.json')['status']=='NO_REPLICATION_PROCESSES'
now=datetime.now(timezone.utc).isoformat()
primary=audit['primary']; counts=audit['all_policy_counts']; means=audit['all_policy_means']
contrasts=analysis['contrasts']['24']['independent']['all']


def interval(name):
    x=contrasts[name]
    return f"{100*x['mean']:+.4f} points; descriptive95% interval[{100*x['lower']:+.4f},{100*x['upper']:+.4f}]"


lines=[
'Repeated guarded rewriting versus one successful rewrite: fresh-founder scientific closeout',
'',
'Status: COMPLETE_AUDITED_CLOSED',
'Frozen decision: REPEATED_REWRITE_REPLICATION_UNRESOLVED',
'Run completed: '+complete['utc'],
'Independent closeout: '+now,
'',
'The fresh replication did not meet the frozen support criterion. Ongoing current-success',
f"guarding achieved821/1152 original-task successes at g16..33 (71.2674%), versus815/1152",
'(70.7465%) for first_success_once. The paired acquisition-block mean difference was',
f"{100*primary['mean']:+.4f} percentage points, two-sided95% t interval",
f"[{100*primary['lower']:+.4f},{100*primary['upper']:+.4f}]. The one-sided95% lower limit",
f"was{100*primary['lower_one_sided95']:+.4f} points; the upper limit was{100*primary['upper_one_sided95']:+.4f} points.",
'The required nondegenerate lower limit above zero was not attained, and the upper',
'limit was not at or below zero. The frozen result is therefore UNRESOLVED, not',
'confirmed advantage, contradiction, equivalence or proof of no effect.',
'',
'The uncertainty unit is16 acquisition blocks (df15). The64 packets,1152 repeated',
'read opportunities per policy and320 policy outcomes are not independent replicates.',
'The primary contrast contains six additional successful reads in total; block-level',
'differences include positive, negative and zero values. No sample extension, alternative',
'primary, retrospective margin, pooled development/replication test or new fit was used.',
'',
'policy                         downstream %   terminal %   uninterrupted %   accepted rewrites',
]
labels={'always_promote':'Always promote','matched_random':'Matched random allocation',
        'writer_success_guard':'Current-success guard','protected_retain':'Protected retain',
        'first_success_once':'One successful rewrite'}
for policy,label in labels.items():
    m=means[policy];c=counts[policy]
    lines.append(f"{label:30s}{100*m['downstream_successes']:13.4f}{100*m['terminal']:13.4f}{100*m['uninterrupted']:18.4f}{c['promotions']:20d}")
lines += [
'',
'Terminal and uninterrupted denominators are64. Counts in table order: terminal',
'39,44,48,42,47; uninterrupted37,36,38,15,37. Uninterrupted means success on every',
'g16..33 read, excluding the shared pre-action g15 read. All scores use the original',
'acquired rule, not just a stable output or either possible answer.',
'',
'Interpretation and ordinary controls',
'The earlier28-block exposed-panel development study estimated+2.7778 points for',
'guard versus one rewrite and met its development criterion. This fresh16-block',
'result is substantially smaller and does not replicate support. The earlier decision',
'is preserved; no formal between-study difference test was preregistered or added.',
'',
'The one-rewrite policy improved on protected retention by113 later successes,',
'while ongoing guarding improved by119. Thus one successful rewrite captured',
f"{100*audit['descriptive_single_rewrite_share_of_guard_gain_over_retention']:.2f}% of the observed guard-versus-retention gain on this cohort.",
'That is a descriptive ratio relative to a shared comparator, not a causal mechanism',
'decomposition, population percentage, equivalence conclusion or computational saving.',
'',
'Ongoing guarding accepted808 rewrites versus49 for first_success_once:759 additional',
'updates for six additional successful read opportunities in aggregate. Fifteen packets',
'never received a single-policy rewrite during g15..32. A success at g33 alone cannot',
'be inherited. Both policies incurred the same native reads and candidate construction',
'in this assay, including candidates that were rejected. The study did not test an',
'implementation that skips those computations after its first rewrite.',
'',
'All following comparisons are unadjusted secondary summaries:',
'  Guard minus matched random, average: '+interval('writer_success_guard__minus__matched_random__downstream_successes'),
'  Guard minus always promote, average: '+interval('writer_success_guard__minus__always_promote__downstream_successes'),
'  Guard minus protected retain, average: '+interval('writer_success_guard__minus__protected_retain__downstream_successes'),
'  One rewrite minus protected retain, average: '+interval('first_success_once__minus__protected_retain__downstream_successes'),
'  Guard minus one rewrite, terminal: '+interval('writer_success_guard__minus__first_success_once__terminal'),
'  Guard minus one rewrite, uninterrupted: '+interval('writer_success_guard__minus__first_success_once__uninterrupted'),
'',
'The guard-minus-random interval spans zero in this cohort. This study does not add',
'a demonstrated allocation advantage over the coupled random comparator. The earlier',
'28-fresh-block allocation replication remains supported under its own frozen test.',
'The random comparator here receives the contemporaneous guard group count K and',
'rewrites a uniform subset of its own four packets. It is a coupled diagnostic control,',
'not a standalone scheduler and not a rewrite-count match to first_success_once.',
'',
'Descriptive recovery accounting',
'Among29 shared g15 failures, guard/one-rewrite/protected had213/207/135 successful',
'later reads out of522. Among35 initial passes, the corresponding counts were',
'608/608/567 out of630. The entire six-read aggregate guard-minus-once difference',
'came from the initial-failure stratum; no within-stratum confirmatory prediction was',
'frozen. Identical aggregate608/630 counts do not imply identical individual trajectories.',
'',
'Guard, protected retain and first_success_once have identical first-success times',
'by construction, because each retains the original record until that first success.',
'This identity is not independent evidence for a recovery mechanism. Average occupancy,',
'terminal success, uninterrupted success and recovery remain separate outcomes.',
'',
'Design and resource amendment',
'Sixteen fresh acquisition blocks were selected in the originally frozen ascending',
'order after complete four-block waves. All16 attempts were eligible, with two g14',
'failures and two g14 passes per block chosen by the original rule-balanced hash.',
'The64 selected packets and all five policies were sealed before any target future.',
'Only injury24 and independent cue noise were tested. The reader used2048 steps,',
'1024 settling steps,dt0.2,noise0.02,birth SD0.05 and32 late frames; all four',
'original-rule-aligned means had to exceed0.25. The original beta3 exact writer,',
'including its exact-zero returning-edge fallback, was unchanged.',
'',
'The first attempt stopped on2026-10-29 after1130.271357 seconds because the frozen',
'4GB free-disk reserve was unavailable. All acquisitions, native qualification and',
'continuation blocks0..3 had completed. The failed run and its503-file stop manifest',
'remain untouched. A resource-only resume on2026-10-30 copied426 committed files',
'byte-for-byte and ran only blocks4..15 with the original frozen scientific worker,',
'source, forcing, policies, analysis and input manifest. No founder was replaced,',
'completed unit repeated or primary outcome changed. Status reviews had inspected',
'unit/resource metadata, including block0 action counts, but had not computed a',
'partial primary contrast before the amendment. This is explicitly recorded as a',
'resume after partial outcomes existed, not an unbroken pristine run.',
'',
'The original absolute deadlines expired during the pause. The documented resume',
'used a new2449-second deadline and charged all previous run duration once, preserving',
'both the original3600-second combined and3400-second target-phase duration allowances.',
f"The resumed run took{complete['resumed_wall_seconds']:.6f} seconds (10m25s); total charged",
f"runtime was{complete['wall_seconds']:.6f} seconds (29m15s). Target-phase charged time was",
f"{complete['target_charged_seconds']:.6f} seconds. The{audit['calendar_pause_seconds_excluded']:.3f}-second calendar pause and",
'preparation/closeout time are excluded from those summed run durations. Four one-thread',
'workers plus one parent reserve were retained under the shared12-thread allowance.',
'All12 launch/wave CPU admissions passed;9 actual worker batches completed, with',
'zero capacity waiting. The extra original CPU admission before the disk stop launched',
'no workers. The completed parent/process group was absent at the closeout host check.',
'',
'Cost and independent verification',
'  Scientific acquisition:14336 primary+192 flat=14528 full readers;32 teaching episodes.',
'  Scientific continuation:6080 primary+6080 full flat=12160 full readers.',
'  Reused qualification acquisition:1792 primary+24 flat=1816;4 teaching episodes.',
'  Reused qualification continuation:760 primary+760 flat=1520 full readers.',
'  Combined native total:30024, including20904 before the stop and9120 after resume.',
'Original software qualification separately used56 full2048-step readers and760',
'short32-step readers. All38 original checks passed. All32 new resume-controller',
'checks passed and used zero native reads. There were no estimation probes or fits.',
f"Recorded native worker CPU totals{audit['native_worker_cpu_seconds']:.6f} seconds, including flat audit",
'work; this is worker CPU, not an end-to-end total for preparation, parent orchestration',
'and independent closeout. Identical imports incur storage/I/O costs but no repeated',
'native evaluation. Cached/reused qualification is not counted as free historical work.',
'',
'The separate closeout imports no study modules. It verified76 original scientific',
'inputs,8 frozen controller inputs,562 output-manifest files,503 preserved stopped-run',
'artifacts and426 byte-identical imports. It checked18 acquisition commitments and',
'independently rescored1152 g14 boundary records, selection hashes and selected packets.',
'It rescored6840 native continuation readouts, checked360 saved full flat-reader chains,',
'regenerated324 block-generation allocation decisions (288 target), persistent single-',
'rewrite state and every inherited record. It verified320 target outcomes,256 exact-',
'rational policy/primary block summaries, two recovery contributions,10 recovery cells,',
'the unchanged criterion, timing, admissions and reader costs. This audits saved full',
'flat evidence; it does not claim a third native dynamics implementation or full forcing',
'rerun. The independent closeout generated no new native dynamics.',
'',
'Scientific boundary and next decision',
'This is fresh-founder replication within the same research programme, with hypothesis',
'and sample size informed by exposed development. It is not external preregistration',
'or an independent-laboratory replication. The finding supports retaining one successful',
'rewrite as a strong simple comparator; it does not establish that repeated rewriting',
'is unnecessary or that the policies are equivalent. The distinction and uncertainty',
'must remain visible in any subsequent account.',
'',
'The ordinary allocation replication and noise-precision studies retain their own',
'supported verdicts. The earlier six-test replication remains unresolved; historical-',
'guard and conditional-benefit candidates remain failed/stopped. This study does not',
'qualify an individualized intervention-benefit estimator or establish an RDT-specific',
'law. Known task labels, protected storage, recurring cues, reader and writer are supplied.',
'Before a more elaborate individualized scheduler, paired benefits for its exact action',
'and horizon must pass a separately frozen independent-future-bank measurement test.',
'No automatic sample extension, transfer test, new policy or successor is launched.',
'',
'Evidence: resource_resume_v1/runs/resume_v1/COMPLETE.json, OUTPUTS.json, ANALYSIS.json;',
'resource_resume_v1/checks/INDEPENDENT_CLOSEOUT_AUDIT.json and SCIENTIFIC_CLOSEOUT.json.',
'Original frozen inputs and all native runs are unchanged.',
'']
text='\n'.join(lines)
for destination in [ROOT/'SCIENTIFIC_REPORT.txt',PACKAGE/'SCIENTIFIC_REPORT.txt']:
    with destination.open('x') as stream:stream.write(text)
report=PACKAGE/'SCIENTIFIC_REPORT.txt'
closeout=dict(utc=now,status='COMPLETE_AUDITED_CLOSED',decision=complete['decision'],active_pid=None,active_run=None,
    completed_run=str(RUN),scientific_report=str(report),scientific_report_sha256=sha(report),
    resource_report_sha256=sha(ROOT/'SCIENTIFIC_REPORT.txt'),complete_sha256=sha(RUN/'COMPLETE.json'),
    output_manifest_sha256=sha(RUN/'OUTPUTS.json'),scientific_input_manifest_sha256=sha(INPUT/'INPUTS.json'),
    controller_input_manifest_sha256=sha(CONTROL/'INPUTS.json'),
    independent_closeout_audit_sha256=sha(CHECKS/'INDEPENDENT_CLOSEOUT_AUDIT.json'),
    host_process_check_sha256=sha(CHECKS/'CLOSEOUT_HOST_PROCESS_CHECK.json'),
    closeout_script_sha256=sha(Path(__file__)),primary=primary,
    selected_blocks=16,selected_packets=64,target_policy_outcomes=320,full_native_readers=30024,
    resumed_wall_seconds=complete['resumed_wall_seconds'],combined_charged_wall_seconds=complete['wall_seconds'],
    new_native_dynamics_for_closeout=0,new_model_fits=0,scientific_inputs_and_runs_unchanged=True,
    earlier_development_verdict_unchanged=True,equivalence_established=False,RDT_specific_validation=False,
    next_action='Preserve unresolved repeated-rewrite result and one-successful-rewrite comparator. No automatic extension or successor. Before individualized policy work, qualify independent-bank paired-benefit measurement at its exact action and horizon.',
    automatic_successor=False,automatic_retry=False,protected_sources=['TT018','rdt_packet_continuation_v0_1'])
write(CHECKS/'SCIENTIFIC_CLOSEOUT.json',closeout)
reference=dict(utc=now,status='REPLICATION_COMPLETE_AUDITED_CLOSED',decision=complete['decision'],
    scientific_report=str(report),scientific_report_sha256=sha(report),
    scientific_closeout=str(CHECKS/'SCIENTIFIC_CLOSEOUT.json'),scientific_closeout_sha256=sha(CHECKS/'SCIENTIFIC_CLOSEOUT.json'),
    source_development_verdict_unchanged=True,primary=primary,selected_fresh_blocks=16,automatic_successor=False)
write(LANE/'rdt_success_guard_single_rewrite_v0_1/FRESH_FOUNDER_REPLICATION_CLOSEOUT_REFERENCE.json',reference)
write(PACKAGE/'checks/SCIENTIFIC_CLOSEOUT_REFERENCE.json',reference)
for folder in [CHECKS,PACKAGE/'checks']:
    current=folder/'HANDOFF.json'
    with (folder/'HANDOFF_BEFORE_SCIENTIFIC_CLOSEOUT.json').open('xb') as stream:stream.write(current.read_bytes())
    handoff=dict(utc=now,status='COMPLETE_AUDITED_CLOSED',active_pid=None,active_run=None,
        completed_run=str(RUN),decision=complete['decision'],report=str(report),
        report_sha256=sha(report),closeout=str(CHECKS/'SCIENTIFIC_CLOSEOUT.json'),
        closeout_sha256=sha(CHECKS/'SCIENTIFIC_CLOSEOUT.json'),
        next_action=closeout['next_action'],automatic_successor=False,automatic_polling=False,
        protected_sources=closeout['protected_sources'])
    temporary=folder/'HANDOFF_CLOSED.tmp'
    write(temporary,handoff);os.replace(temporary,current)
for relative,expected in read(RUN/'OUTPUTS.json')['sha256'].items():assert sha(RUN/relative)==expected
assert sha(RUN/'COMPLETE.json')==audit['complete_sha256']
assert sha(report)==sha(ROOT/'SCIENTIFIC_REPORT.txt')
assert read(CHECKS/'HANDOFF.json')['active_pid'] is None
print(json.dumps({k:closeout[k] for k in ['status','decision','scientific_report','scientific_report_sha256','combined_charged_wall_seconds','primary']}))
