"""Archive the queued handoff and record the completed packet-integrity pilot."""
from pathlib import Path
import os,shutil,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *

run=ROOT/'runs/damage_v1';complete=read(run/'COMPLETE.json');closeout=read(ROOT/'CLOSEOUT.json');findings=read(ROOT/'FINDINGS.json')
assert closeout['status']=='PASS_ALL_OUTPUT_HASHES_AGGREGATES_AND_PRIMARY_ROWS'
assert sha(run/'COMPLETE.json')==closeout['completion_sha256'] and sha(ROOT/'FINDINGS.json')==closeout['findings_sha256']
assert read(ROOT/'COMPLETION_PROCESS_CHECK.json')['no_active_tt040_jobs']
classification=findings['classification'];key='residual|all|all_masks|own'
primary={d:findings['panels'][d]['conditions'][key] for d in DAMAGE}
for d,bd,rd,bc,rc in (
    ('mix000',-3.90625,-1.66015625,(3,11,50),(6,15,43)),
    ('mix050',-1.171875,1.5625,(2,6,56),(15,10,39)),
    ('mix100',6.640625,13.18359375,(17,5,42),(41,7,16))):
    b=primary[d]['body']['comparisons']['late_minus_preserve'];r=primary[d]['fresh_recipient']['comparisons']['late_minus_preserve']
    near(b['equal_block_change_pp'],bd);near(r['equal_block_change_pp'],rd)
    assert b['record_mean_counts']==dict(zip(('gain','harm','tie'),bc))
    assert r['record_mean_counts']==dict(zip(('gain','harm','tie'),rc))
handoff=read(ROOT/'QUEUE_HANDOFF.json');verify(handoff['files']);stamp=now()
archive=ROOT/'completion_handoff_inputs';archive.mkdir(exist_ok=False)
paths=set(map(Path,handoff['files']))|{ROOT/n for n in ('QUEUE_HANDOFF.json','CURRENT_EXECUTION.json','QUEUE_STATUS.json','QUEUE_COMPLETE.json','LAUNCH.json','STARTUP_PERSISTENCE_CHECK.json')}
saved={}
for p in sorted(paths):
    dest=archive/p.relative_to(LANE);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    h=sha(p);assert sha(dest)==h;saved[str(p)]=dict(snapshot=str(dest),sha256=h)
write(archive/'MANIFEST.json',dict(files=saved,archived_utc=stamp))
def replace_file(path,value):
    temp=path.with_name(path.name+'.tt040-complete.pending');write(temp,value);os.replace(temp,path)

proof=complete['verification'];current=read(ROOT/'CURRENT_EXECUTION.json')
current.update(status='COMPLETE_REVIEWED',updated_utc=stamp,completed_utc=complete['completed_utc'],
    completed_blocks=4,actual_seconds=complete['seconds'],retained_bytes=complete['retained_bytes'],verification=proof,
    closeout='TT040/CLOSEOUT.json',findings='TT040/FINDINGS.json',report='TT040/runs/damage_v1/REPORT.md',
    scientific_classification=classification,confirmatory=False,processes_exited=True,no_active_jobs=True,
    scientific_results_inspected=True,new_production_outcomes_inspected=True,new_production_outcomes_generated=True,
    interim_scientific_outcomes_inspected=False,full_qualification_pending=False,qualification_status='PASS',benchmark_status='COMPLETE',
    successor_started=False,primary_half_mixed_late_minus_preserve_pp=dict(body_at_1900=-1.171875,fresh_recipient=1.5625),
    next_step='Use the retained informative-record harms to guide further diagnosis; no successor or fresh confirmation launched')
replace_file(ROOT/'CURRENT_EXECUTION.json',current)

message="""
[TT040 packet-integrity timing development](TT040/README.md) is **complete and
reviewed**. The four fixed exposed source blocks finished at 11:57:53 UTC on
24 October 2026 in **1 hour 17 seconds**, on two single-thread CPUs. All new
physical checks passed. The result is a tradeoff, not a confirmation of repair
without cost.

In the prespecified residual-family, own-source, all-mask comparison, late
writing minus preservation changes fractional original-target recognition by:

| Incoming packet | Body at 1900 (pp) | Fresh recipient (pp) |
|---|---:|---:|
| Intact | -3.9063 | -1.6602 |
| Half-mixed with noise: primary | -1.1719 | +1.5625 |
| Fully replaced | +6.6406 | +13.1836 |

For half-mixed packets, recipient credit rises from 76.1719% to 77.7344%, while
body credit falls from 76.9531% to 75.7813%. Recipient block effects are -0.7813,
+3.9063, 0 and +3.1250 points; body effects are -3.1250, 0, -1.5625 and 0.
Among 64 source-position means, recipient changes retain **15 gains / 10 harms /
39 ties**, and body changes retain **2 gains / 6 harms / 56 ties**. These 64
positions are dependent within the four source blocks.

Intact residual packets decline from 86.7188% to 85.0586% recipient credit.
Their changes retain 6 record gains, 15 harms and 43 ties; body changes retain
3 gains, 11 harms and 50 ties. Fully replaced packets improve on both endpoints
on average, but those gains cannot rescue the informative-record losses.
The common-family half-mixed averages also favor preservation: -0.7813 body
and -0.6836 recipient points.

This is a small development experiment on exposed sources, with one corruption
realization and four new receiving conditions per block. Mixture weight .5 is
an amplitude weight, not a fraction of information erased. No significance,
noninferiority, absence-of-harm or fresh-confirmation claim is made. All cases,
controls and paired harms remain. TT028 primary/joint and TT036/TT039
confirmation classifications are unchanged; no serial inheritance was tested.

Completion review rehashed all **7,964 retained outputs**, checked source and
frozen-input bindings, reconciled all three mixture panels and five body
checkpoints, and independently reduced the primary saved rows for all four
arms, four credits and six contrasts. The run replayed 68,800 native arrays,
performed 41,984 new receiving assays and used 16 new receiving conditions
shared across damage levels. Source states were reused from TT039. All
processes have exited, and no successor has started.

See [report](TT040/runs/damage_v1/REPORT.md), [findings](TT040/FINDINGS.json)
and [review scope](TT040/CLOSEOUT.json).
"""
assert closeout['output_files_rehashed']==7964
for name in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md'):
    with (LANE/name).open('a') as f:f.write('\n'+message)
details="""
The four source identities are 39010000, 39010016, 39010032 and 39010048,
selected by position in the prior ordered cohort rather than outcomes.
All four schedules were retained: preservation, early 1-100, late 901-1000 and
full 1-1000. Every body continued to 1900 with writing off after 1000. Fresh
receiving conditions paired birth and forcing across every mixture, schedule,
family, physical mask and own/foreign/neutral body source. Intact preservation
equals the original packet byte for byte, with the same physical receiving assay.

Residual own-source record-mean joint tables retain opposing outcomes. For
half mixing, one record improves on both endpoints, two decline on both,
three change in opposing directions and 58 tie on at least one endpoint.
Recipient improvements therefore do not imply simultaneous body improvements.
The positive-half-retained primary stratum has +8.9844 recipient and +3.1250
body points; the negative-half stratum has -2.7344 and -1.5625. Mixed halves
have zero mean recipient change and -3.1250 body points, while retaining
10 recipient gains and 10 harms. Geometry is descriptive and task-aligned;
it does not supply an autonomous repair policy.

Early writing also harms intact residual inputs (-8.4961 recipient and -8.5938
body points) and half-mixed inputs (-2.0508 recipient and -4.2969 body points)
relative to preservation. Full writing has larger residual mean losses in
both informative-packet panels. These secondary comparisons do not establish
optimal timing or a safe schedule. A positive complete-replacement result
does not establish benefit for every damage level or individual record.

The frozen run and all outputs are unchanged. Closeout independently verifies
saved-row arithmetic and all retained hashes; it does not rerun the physical
trajectories. Independent physical replay passed during acquisition. The
original qualified input snapshots and the prior handoff remain retained in
[the completion archive](completion_handoff_inputs/MANIFEST.json).
"""
(ROOT/'README.md').write_text('# TT040 — informative-record tradeoffs\n\n'+message.replace('(TT040/','(')+'\n'+details)
with (PRIOR/'README.md').open('a') as f:
    f.write('\nTT040 is complete and reviewed on four exposed source blocks. For half-mixed residual records, late writing gives +1.5625 recipient points with -1.1719 body points; intact records lose 1.6602 recipient and 3.9063 body points. This bounded development result does not change TT039\'s full-replacement confirmation. See [TT040 findings](../TT040/README.md). No successor is running.\n')
successor=dict(study='TT040',status='COMPLETE_REVIEWED',current_execution='TT040/CURRENT_EXECUTION.json',
    closeout='TT040/CLOSEOUT.json',findings='TT040/FINDINGS.json',scientific_classification=classification,
    confirmatory=False,completed_utc=complete['completed_utc'],successor_started=False)
prior=read(PRIOR/'CURRENT_EXECUTION.json');prior.update(authorized_successor=successor,administrative_updated_utc=stamp)
replace_file(PRIOR/'CURRENT_EXECUTION.json',prior)
intake=read(LANE/'prediction_intake_status.json');intake['fresh_late_writing_confirmation']['authorized_successor']=successor
intake['packet_integrity_timing_development'].update(successor,status_at_handoff='COMPLETE_REVIEWED',
    observed_phase='COMPLETE_REVIEWED',observed_utc=stamp,actual_seconds=complete['seconds'],verification=proof,
    scientific_results_inspected=True,new_production_outcomes_generated=True,new_production_outcomes_inspected=True,
    interim_scientific_outcomes_inspected=False,processes_exited=True,full_qualification_pending_at_handoff=False,
    qualification_status='PASS',benchmark_status='COMPLETE',primary_half_mixed_late_minus_preserve_pp=dict(body=-1.171875,recipient=1.5625))
intake['updated_utc']=stamp;replace_file(LANE/'prediction_intake_status.json',intake)
with (LANE/'exposure_register.jsonl').open('a') as f:
    f.write(json.dumps(dict(study='TT040',event='packet_integrity_timing_development_completed_and_reviewed',recorded_utc=stamp,
        completion_sha256=sha(run/'COMPLETE.json'),closeout_sha256=sha(ROOT/'CLOSEOUT.json'),findings_sha256=sha(ROOT/'FINDINGS.json'),
        scientific_classification=classification,source_population_exposed=True,source_population_reused=True,
        new_production_outcomes_inspected=True,interim_scientific_outcomes_inspected=False,confirmatory=False,
        new_independent_receiving_draws=16,new_receiving_assays=41984,successor_started=False,
        TT028_primary='NOT_CONFIRMED',TT036_confirmation_unchanged=True,TT039_confirmation_unchanged=True),sort_keys=True)+'\n')
bound=[LANE/n for n in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md','prediction_intake_status.json','exposure_register.jsonl',
    'TT039/README.md','TT039/CURRENT_EXECUTION.json')]+[ROOT/n for n in ('README.md','CURRENT_EXECUTION.json','FINDINGS.json',
    'CLOSEOUT.json','COMPLETION_PROCESS_CHECK.json','RESULT_INSPECTION.json','completion_handoff_inputs/MANIFEST.json',
    'admin/reconcile_completion.py','admin/completion_handoff.py')]
write(ROOT/'COMPLETION_HANDOFF.json',dict(status='PASS',recorded_utc=stamp,files={str(p):sha(p) for p in bound},
    scientific_classification=classification,confirmatory=False,successor_started=False,review_scope=closeout['review_checks']))
verify(read(ROOT/'COMPLETION_HANDOFF.json')['files']);assert inputs()==read(ROOT/'FREEZE.json')['inputs']
print(dict(status='COMPLETE_REVIEWED',blocks=4,archived_files=len(saved),bound_files=len(bound),
    scientific_classification=classification,successor_started=False))
