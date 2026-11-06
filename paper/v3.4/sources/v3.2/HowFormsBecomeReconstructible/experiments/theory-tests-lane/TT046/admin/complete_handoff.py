"""Close the prospective damage confirmation after independent saved-data review."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *


def replace_file(p,value):
    p=Path(p);tmp=p.with_name(p.name+'.completion-pending');write(tmp,value);tmp.replace(p)


def main():
    run=ROOT/'runs/confirmation_v1';complete=read(run/'COMPLETE.json');frozen=read(ROOT/'FREEZE.json')
    close=read(ROOT/'CLOSEOUT.json');finding=read(ROOT/'FINDINGS.json');qualification=read(ROOT/'runs/qualification_v1/COMPLETE.json')
    expected='CONFIRMED_JOINT_DAMAGE_DEPENDENT_PACKET_BENEFIT'
    assert complete['status']=='COMPLETE' and close['status']=='PASS' and finding['classification']==expected
    assert close['primary_independently_verified']==expected and finding['primary']['independently_recomputed']
    assert close['complete_sha256']==sha(run/'COMPLETE.json') and close['findings_sha256']==sha(ROOT/'FINDINGS.json')
    assert close['review_code_sha256']==sha(ROOT/'admin/review_v2.py')
    assert qualification['serial_parallel_bitwise_equal'] and read(ROOT/'COMPLETION_PROCESS_CHECK.json')['no_active_jobs']
    verify(frozen['inputs']);verify(frozen['evidence'])
    half=finding['panels']['mix050']['contrasts'];full=finding['panels']['mix100']['contrasts'];intact=finding['panels']['mix000']['contrasts']
    assert full['packet_F']['by_time_pp'][-1]==15.386962890625
    assert intact['packet_F']['by_time_pp'][-1]==-1.34124755859375 and half['packet_F']['by_time_pp'][-1]==.103759765625
    assert full['packet_F']['case_harm_tie_gain_by_time'][-1]==[242,993,813]
    for name in ('packet_C','packet_F'):
        assert full[name]['block_harm_tie_gain_by_time'][-2:]==[[0,0,32],[0,0,32]]
    prior=ROOT/'LAUNCH_HANDOFF.json';bound=read(prior)['files'];verify(bound)
    archive=ROOT/'completion_handoff_inputs';archive.mkdir(exist_ok=False);archived={}
    paths=set(bound)|{str(prior),str(ROOT/'CURRENT_EXECUTION.json'),str(ROOT/'QUEUE_STATUS.json'),str(PRIOR/'README.md')}
    for name in sorted(paths):
        source=Path(name);target=archive/source.relative_to(LANE);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target);assert sha(source)==sha(target);archived[name]=dict(archive=str(target),sha256=sha(target))
    write(archive/'MANIFEST.json',archived)
    primary=finding['primary'];rows=[]
    for name,label in (('full_900','Full replacement, 900'),('full_1000','Full replacement, 1000'),
                       ('full_minus_intact_900','Full minus intact packet effect, 900'),('full_minus_intact_1000','Full minus intact packet effect, 1000')):
        ci=primary['endpoints'][name]['interval'];lo,hi=ci['pointwise_two_sided_95']
        rows.append(f"| {label} | {100*ci['mean']:+.4f} | {100*ci['lower_one_sided']:+.4f} | [{100*lo:+.4f}, {100*hi:+.4f}] |")
    primary_table='\n'.join(rows);levels=[];harms=[]
    for damage,label in (('mix000','Intact'),('mix050','Half-mixed'),('mix100','Full replacement')):
        p=finding['panels'][damage];levels.append(f"| {label} | {p['levels_by_time_percent'][2][-1]:.4f} | {p['levels_by_time_percent'][3][-1]:.4f} | {p['contrasts']['packet_F']['by_time_pp'][-1]:+.4f} |")
        harms.append('| '+label+' | '+' | '.join(map(str,p['contrasts']['packet_F']['case_harm_tie_gain_by_time'][-1]))+' |')
    text=f'''# TT046 — confirmed damage-dependent one-read packet benefit

**TT046 is complete and independently reviewed. All four predeclared primary
tests passed on 32 new source blocks.** Production finished at 05:06:52 UTC on
29 October 2026, taking **6 hours 6 minutes 6 seconds on two CPUs**. All processes
have exited; no successor is running.

In the stated residual/own source population, the actual late-written packet
has higher average fresh-recipient usefulness than preservation after full
replacement, at both 900 and 1000 updates. Its packet benefit also exceeds the
intact-packet effect at both horizons. This confirms the specific directional
mean claim selected from TT045 development. It does not establish a generally
beneficial rewriting rule, benefit for every record, or serial hereditary capacity.

The four co-primary results are percentage-point differences in target-success
credit, with paired source-block inference:

| Primary contrast and horizon | Mean (pp) | Adjusted one-sided lower bound (pp) | Pointwise two-sided 95% interval (pp) |
|---|---:|---:|---|
{primary_table}

All four adjusted lower bounds exceed zero, satisfying the frozen joint gate.
The adjustment is Bonferroni over four tests, alpha .0125 each, with 31 degrees
of freedom. Student-t coverage is approximate. The predeclared distribution-free
Hoeffding sensitivity remains inconclusive: its lower bounds are negative for
all four endpoints. Thus confirmation is under the specified approximate block
test; it is not a distribution-free guarantee. No extension, seed selection,
new threshold or secondary endpoint rescued the result.

At the 1000-update fresh-recipient readout:

| Incoming condition | Preserved packet (%) | Late-written packet (%) | Change (pp) |
|---|---:|---:|---:|
{chr(10).join(levels)}

These percentages are mean tied-winner target credit, including fractional ties.
The full-replacement benefit is positive in every one of the 32 blocks at both
horizons. It is +15.9485 points at 900 and +15.3870 at 1000. Continuing-state
packet benefits are also positive in every block at both horizons, with means
+16.0217 and +15.3564 points; those are secondary results. Full-replacement
fresh-recipient success remains about 40%, despite the clear gain from 25%.

Intact mean effects are negative at both horizons (-1.3885 and -1.3412 points),
and half-mixed mean effects are close to zero (+0.2457 and +0.1038). These control
means are descriptive; the primary test includes the full-minus-intact difference,
not a separate claim of intact harm or half-mixed equivalence. Half mixing means
an amplitude mixture with noise, not half the message information erased.

Paired harms are retained. The 1000-update fresh-state injury-case counts,
after averaging each case's four actual starting states and eight futures, are:

| Incoming condition | Harm | Tie | Gain |
|---|---:|---:|---:|
{chr(10).join(harms)}

Each row contains 2,048 dependent injury cases from 512 source positions in
32 blocks. In full replacement, 242 cases have negative sampled mean effects
despite the positive block means. These signs describe the retained estimates;
eight futures do not precisely identify every record's true expected effect.
Source-position, injury-case and position/future counts remain separate, as do
paired 900-to-1000 signs. All source histories, messages, masks, damage levels
and target/donor/template/opposite credits were retained.

Continuous margins remain separate secondary outcomes. At 1000, fresh-state
packet effects on target-versus-best-other margin are -0.00129542 for intact,
+0.01298554 for half mixing and +0.08458440 for full replacement. The half-mixed
margin gain coexists with a near-zero winner-credit change. Neither metric
substitutes for the other or measures future descendants after further writing.

Population uncertainty uses the 32 full source-block estimates, including finite
sampling of births/futures. Conditional Monte Carlo uncertainty instead holds
source records and starting states fixed. For example, the full-replacement
1000-update packet effect has population SE 0.4940 points and conditional MC SE
0.2102 points. Masks, positions and births within a block/future are dependent;
they were not counted as extra population units. Eight futures per fixed state
give coarse local estimates, and zero sampled variance is not certainty.

The source population is newly generated by the unchanged audited recipe, with
residual packets and own-body history only. Four fresh births receive all eight
new futures; states, packets, damage levels and masks share the appropriate
paired randomness within each block. One new corruption realization is sampled
per source block, so this does not estimate an individual record's full response
to possible corruptions. Teaching/source noise remains coupled across task
messages. The bounded identity scan and reviewed self-matches are documented in
RESERVATION.json and RESERVATION_REVIEW.json; other projects and global non-use
were not verified. These production outcomes are now exposed.

Writing is fixed at updates 901–1000 of one body episode. Both actual packets
are then read with feedback and writing off, native memory updating, and the
same finite 256-float64 channel (2048 bytes per record). The continuing profile
uses the preserved body's state for both packets. No adaptive policy, separate
body-source information intervention, serial rewriting, indefinite stability or
uninterrupted-performance claim follows. The confirmed narrow claim and its
harms can now enter the evidence synthesis; no new experiment is launched.

Production independently replayed 21,504 receiving batches (516,096 native
arrays), 768 writing batches (18,432 arrays), and the new source stages (1,504
arrays). Native discrepancies were zero. Qualification passed exact serial/
parallel comparison; that comparison was not repeated for production. The
separate saved-data review checked {close['output_files_verified']:,} output
files, all {close['condition_blocks_checked']:,} condition/block reductions,
{close['case_packet_state_future_endpoint_vectors_checked']:,} endpoint vectors,
{close['continuous_margin_entries_checked']:,} margin entries and all local/global
means, paired errors, signs and counts. It independently recomputed the primary
population variance and inverted the Student-t CDF for the decision bounds.
Source, writer, birth, packet and original-control custody also passed.

See [frozen report](runs/confirmation_v1/REPORT.md), [frozen confirmation](runs/confirmation_v1/CONFIRMATION.json),
[reviewed findings](FINDINGS.json), [closeout](CLOSEOUT.json), [protocol](PROTOCOL.md)
and [execution record](EXECUTION.md).
'''
    (ROOT/'README.md').write_text(text)
    arc=read(ARCHIVE/'COMPLETE.json');queue=read(ROOT/'QUEUE_COMPLETE.json')
    execution=f'''# TT046 execution and closeout

The detached sequence began on 28 October 2026 at 22:44 UTC and finished on
29 October at 05:06:54 UTC, after {queue['seconds']:.3f} seconds (6 hours
22 minutes 54 seconds). It used two normal-priority single-thread workers on
CPUs 6/7. One startup persistence check was followed only by user-requested
status review; no production outcomes were inspected before completion.

The completed TT045 raw run was archived to
/mnt/datasets/theory-tests-lane-archive/2026-10-28_completed-runs_v2.
All {arc['files_verified']:,} files ({arc['bytes_archived']:,} bytes) were verified
before releasing the local copy. Original paths remain readable through a
symlink. Archive time was {arc['seconds']:.3f} seconds (13 minutes 30 seconds),
above its 508-second estimate but below its 1524-second deadline.

Full excluded qualification passed in {qualification['seconds']:.3f} seconds
(3 minutes 12 seconds), with 156 receiving batches and exact serial/parallel
agreement. Production froze at {frozen['frozen_utc']}, started at
{complete['started_utc']}, and finished at {complete['completed_utc']}.
Production took {complete['seconds']:.3f} seconds (6 hours 6 minutes 6 seconds),
below its {frozen['forecast_seconds']}-second forecast (8 hours 8 minutes
48 seconds) and {frozen['deadline_seconds']}-second deadline. No scientific
phase failed, and no production retry, extension or protocol change occurred.

Production retained {complete['retained_bytes']:,} bytes. The study held
{close['study_bytes_at_review']:,} bytes at review, below its 18 GiB cap, with
{close['free_bytes_at_review']:,} local bytes free, above the 4 GiB reserve.
All 35 recorded controller/worker process IDs had exited at the host check.
There is no successor or automatic polling.

Before launch, the administrative reservation traversal timed out; a later scan
required a numeric-boundary correction and review of five self-declarations.
Those attempts and the bounded scan scope are retained. Physical preflight_v1
passed; a cached/live checkpoint-key representation issue was then reproduced
and fixed before full qualification. Preflight_v2 passed with the added
regression check. Dynamics, seeds and cohort were unchanged.

The initial completion checker matched saved writer starting arrays but used
the reader's concatenated-byte hash format for a writer checksum. The writer
uses per-array dtype/shape/bytes hashes inside canonical JSON. The checker was
corrected, with a matching-format fixture and rejected one-ULP mutation. The
old checker and failure remain in admin/review.py and
COMPLETION_REVIEW_FAILED.json; COMPLETION_REVIEW_CORRECTION.json explains the
supersession. Corrected admin/review_v2.py passed the full saved-data review in
{close['seconds']:.3f} seconds, under its 600-second deadline. This generated no
new dynamics and changed no frozen input or production output.

The completed review independently verified all four primary tests and retained
the inconclusive Hoeffding sensitivity. Earlier handoff files are preserved in
completion_handoff_inputs/MANIFEST.json. FINDINGS.json and CLOSEOUT.json bind the
interpretation and verification scope. Prior study classifications are unchanged.
'''
    (ROOT/'EXECUTION.md').write_text(execution)
    stamp=now();state=read(ROOT/'CURRENT_EXECUTION.json')|dict(status='COMPLETE_REVIEWED',phase='COMPLETE_REVIEWED',updated_utc=stamp,
        observed_utc=stamp,production_results_inspected=True,scientific_results_inspected=True,no_active_jobs=True,successor_started=False,
        classification=expected,population_confirmation=True,independent_population_blocks=32,production_population_was_new=True,
        production_outcomes_now_exposed=True,all_cases_and_paired_harms_retained=True,
        active_completion_review='TT046/admin/review_v2.py',superseded_checker_failure='TT046/COMPLETION_REVIEW_FAILED.json',
        closeout='TT046/CLOSEOUT.json',findings='TT046/FINDINGS.json',current_execution='TT046/CURRENT_EXECUTION.json',
        approximate_primary_coverage=True,hoeffding_sensitivity_confirmed=False,
        proposal='Integrate the confirmed narrow mean one-read claim and retained harms into the evidence synthesis; no successor selected or launched.')
    replace_file(ROOT/'CURRENT_EXECUTION.json',state);replace_file(ROOT/'QUEUE_STATUS.json',state)
    old=read(PRIOR/'CURRENT_EXECUTION.json');old['authorized_successor']=dict(study='TT046',status='COMPLETE_REVIEWED',classification=expected,path='TT046/README.md',observed_utc=stamp)
    replace_file(PRIOR/'CURRENT_EXECUTION.json',old)
    with (PRIOR/'README.md').open('a') as f:
        f.write('\n\nTT046 is now complete and reviewed: [fresh-source confirmation](../TT046/README.md).\nAll four predeclared approximate block tests passed on 32 new blocks. Full-\nreplacement fresh-recipient success rises from 25% to 40.387% at 1000, with\npaired harms retained. The claim is conditional on residual/own and one-read\nusefulness; TT045 classifications remain unchanged. No successor is active.\n')
    brief='''

TT046 is complete and independently reviewed: [fresh-source damage confirmation](TT046/README.md).
All four predeclared co-primary tests passed on 32 new source blocks under the
frozen approximate block Student-t/Bonferroni rule. Full-replacement fresh-state
packet effects are +15.9485/+15.3870 points at 900/1000; their adjusted lower
bounds are +14.8040/+14.2234. Full-minus-intact packet-effect differences are
+17.3370/+16.7282, with lower bounds +15.9549/+15.4828. The conservative
distribution-free Hoeffding sensitivity remains inconclusive.

At 1000, fresh-recipient success is 25% with preservation and 40.3870% after
late writing under full replacement. Intact change is -1.3412 points and
half-mixed change +0.1038. Full-replacement benefits are positive in all 32
blocks at both horizons and both receiving-state profiles. Paired harms remain:
fresh-state harm/tie/gain counts are 242/993/813 under full replacement,
299/1563/186 intact, and 293/1457/298 half-mixed, each among 2,048 dependent
injury cases. Individual estimates remain coarse with eight paired futures.

This confirms the specified residual/own one-episode mean one-read claim, with
four new fresh births fully crossed with eight futures. It does not establish
universal benefit, serial inheritance, uninterrupted performance or message-
specific reciprocal body correction. Population uncertainty uses 32 blocks;
conditional Monte Carlo errors remain separate. Production outcomes are now
exposed; prior classifications stay unchanged.

Production finished 29 October 2026 at 05:06:52 UTC in 6 hours 6 minutes on two
CPUs. All source/writer/receiving physical replay and corrected saved-data
review passed. The initial review's writer-hash-format error and correction
are preserved; no experiment output changed. TT045's 12.35 GB raw run was
archived with all checksums verified and original paths retained. All processes
have exited; no successor runs. The confirmed narrow claim and its limits are
ready for evidence synthesis. See [findings](TT046/FINDINGS.json) and
[review scope](TT046/CLOSEOUT.json).
'''
    for name in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md'):
        with (LANE/name).open('a') as f:f.write(brief)
    intake=read(LANE/'prediction_intake_status.json');intake['updated_utc']=stamp
    intake['damage_dependence_confirmation']=state|dict(report='TT046/README.md',protocol='TT046/PROTOCOL.md',predecessor='TT045',full_qualification_pending_at_handoff=False)
    intake['fresh_forcing_development']['authorized_successor']='TT046 complete and reviewed; four predeclared primary tests passed'
    replace_file(LANE/'prediction_intake_status.json',intake)
    with (LANE/'exposure_register.jsonl').open('a') as f:
        f.write(json.dumps(dict(recorded_utc=stamp,study='TT046',event='completed_fresh_source_confirmation_review',classification=expected,
            primary_selected_from_development=True,production_population_was_new=True,production_outcomes_now_exposed=True,
            source_blocks=BLOCKS,approximate_primary_coverage=True,hoeffding_sensitivity_confirmed=False,
            all_cases_and_paired_harms_retained=True,successor_started=False),sort_keys=True)+'\n')
    files=[LANE/n for n in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md','prediction_intake_status.json','exposure_register.jsonl','TT045/CURRENT_EXECUTION.json','TT045/README.md')]
    files+=[ROOT/n for n in ('README.md','EXECUTION.md','CURRENT_EXECUTION.json','QUEUE_STATUS.json','FINDINGS.json','CLOSEOUT.json',
        'RESULT_INSPECTION.json','COMPLETION_PROCESS_CHECK.json','COMPLETION_REVIEW_RESOURCE.json','COMPLETION_REVIEW_V2_RESOURCE.json',
        'COMPLETION_REVIEW_FAILED.json','COMPLETION_REVIEW_CORRECTION.json','admin/review.py','admin/review_v2.py','admin/complete_handoff.py',
        'completion_review.log','completion_review_v2.log','completion_handoff_inputs/MANIFEST.json')]
    space();verify(frozen['inputs']);verify(frozen['evidence'])
    write(ROOT/'COMPLETION_HANDOFF.json',dict(status='PASS',recorded_utc=now(),files={str(p):sha(p) for p in files},
        complete_sha256=sha(run/'COMPLETE.json'),closeout_sha256=sha(ROOT/'CLOSEOUT.json'),classification=expected,
        previous_handoff_preserved=True,scientific_results_inspected=True,successor_started=False))
    verify(read(ROOT/'COMPLETION_HANDOFF.json')['files'])
    print(json.dumps(dict(status='PASS',classification=expected,bound_files=len(files),no_active_jobs=True,successor_started=False)))


if __name__=='__main__':main()
