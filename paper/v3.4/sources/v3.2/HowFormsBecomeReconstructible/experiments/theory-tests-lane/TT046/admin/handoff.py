"""Save launch status and prospective claims without inspecting outcomes."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *
from controller import replace_file


def main():
    launch=read(ROOT/'QUEUE_LAUNCH.json');startup=read(ROOT/'STARTUP_PERSISTENCE_CHECK.json')
    pre=read(ROOT/'checks/preflight_v2/COMPLETE.json');plan=read(ROOT/'QUEUE_PLAN.json');current=read(ROOT/'CURRENT_EXECUTION.json')
    assert launch['status']=='DETACHED_STARTED' and startup['status']=='PASS' and pre['status']=='PASS'
    assert pre['inputs']==plan['inputs']==inputs();verify(plan['evidence'])
    assert not (ROOT/'QUEUE_FAILED.json').exists()
    stamp=now();phase=current['phase'];reservation=read(ROOT/'RESERVATION.json')
    text=f'''# TT046 — new-source confirmation of damage-dependent packet usefulness

The authorized detached sequence has started. At the single startup check it
was in phase **{startup['phase_at_observation']}**; the handoff observation is
**{phase}**. These are timestamps, not continuing status promises. Current phase
is recorded in [CURRENT_EXECUTION.json](CURRENT_EXECUTION.json). No production
outcomes have been inspected.

TT045 found a repeatable full-replacement benefit under new futures of exposed
records, while the half-mixed main result remained small and timing dependent.
TT046 tests that development-selected lead on **32 new source identities**, with
four new fresh starting states and eight new paired futures per state. It keeps
intact, half-mixed and full-replacement packets, preservation, all source
histories, four physical half masks and all paired harms. The scope is residual
packets and the own-body source. Continuing-state and continuous-margin results
remain secondary.

The four co-primary tests ask whether fresh-recipient packet benefit under full
replacement is positive, and whether it exceeds the intact-packet benefit,
each at both 900 and 1000 updates. All four block-level lower bounds must exceed
zero. The family alpha is .05, divided by four; Student-t coverage is approximate,
with a bounded zero-variance fallback and Hoeffding sensitivity. A failed primary
test cannot be rescued by another condition. Individual harms may coexist with
mean benefit; neither serial heredity nor uninterrupted performance is tested.

Population uncertainty uses the 32 source blocks, not the many paired futures
or masks. Conditional Monte Carlo errors are retained separately. Eight futures
give coarse estimates for each fixed record; the four new births and all futures
are fully crossed. New source parent/capture/development and writing trajectories
undergo independent physical replay, as do every receiving trajectory. Late
writing remains fixed at updates 901–1000; receiving feedback and writing are off.

The accessible identity scan and review found no prior-use match for reserved identities
46010000–46010031. It checked {reservation['filename_count']:,} filenames and
{reservation['text_files_searched']:,} selected text/metadata files, with the
limits retained in [RESERVATION.json](RESERVATION.json) and
[RESERVATION_REVIEW.json](RESERVATION_REVIEW.json). Five hits were this study's
own planning/code declarations; all were reviewed and retained. It is not a global or
independent proof of non-use. No new production outcome was generated during
selection or preflight.

Excluded preflight passed in {pre['seconds']:.2f} seconds, including exact source
and intact-writer bridges, independent native replay, label/field rejection,
wrong-stream and one-ULP mutation rejection, paired-error/denominator fixtures,
and the four-endpoint decision fixtures. Full two-block qualification remains
part of the sequence; production is allowed only after that passes, exact
serial/parallel agreement is established, and a measured resource freeze is
written. Its conservative qualification forecast is
{pre['qualification_forecast_seconds']} seconds. Production's forecast is still
subject to the full qualification timing and a fixed 14-hour forecast ceiling.

The sequence first archives TT045's completed raw run under
/mnt/datasets/theory-tests-lane-archive/2026-10-28_completed-runs_v2, verifying
every destination checksum before releasing local storage and retaining the
original paths. This uses the user's existing archive authorization. Then it
qualifies once and, only if all checks and budgets pass, runs the 32-block study
once. The study cap is 18 GiB with a 4 GiB reserve; two single-thread workers use
CPUs 6/7. The controller records completion or failure and exits.

PID: {launch['pid']}. Log: [queue_v1.log](queue_v1.log). The single startup
persistence check passed. No ongoing automatic polling, retry, extension or
successor is authorized by this controller; the user requests later status.
See [protocol](PROTOCOL.md), [queue plan](QUEUE_PLAN.json),
[preflight](checks/preflight_v2/COMPLETE.json) and [execution](EXECUTION.md).
'''
    (ROOT/'README.md').write_text(text)
    execution=f'''# TT046 execution

User authorization: “lets go” after TT045's reviewed result and proposed fresh-
source confirmation. Production identities are reserved before new dynamics.
Preflight used only excluded identity 608280; full qualification uses 608280 and
608281. Source/native kernels are copied unchanged; new adapters implement the
cohort, corruption domain, crossing, denominators and frozen four-endpoint claim.

The initial Python identity traversal hit its 600-second deadline before any
scientific run. Its code/log were preserved; the direct ripgrep implementation
completed the current-project/archive scan after a filename-boundary correction.
The wider Random-Replications tree is outside this bounded scan. These were
administrative implementation corrections,
not a cohort change or a scientific retry. Physical preflight_v1 passed, after
which a cached/live checkpoint-key representation mismatch was identified before
full qualification. Its old code, receipts and reproducer were preserved in
corrections/metadata_pairing_v1. Canonical key comparison and a regression fixture
were added; preflight_v2 reran the excluded checks. Dynamics and seeds are unchanged.

Preflight: {pre['seconds']:.3f} seconds; eight new full receiving trajectories
took {pre['new_read_seconds']:.3f} seconds. Excluded qualification forecast:
{pre['qualification_forecast_seconds']} seconds; deadline:
{pre['qualification_deadline_seconds']} seconds. Upper production read count:
{pre['production_physical_upper_bound']:,} physical batches. Production output
allowance before administration: {pre['production_byte_bound']:,} bytes.

Archive, qualification and conditionally admitted production run under one
detached controller, PID {launch['pid']}, acknowledged {launch['acknowledged_utc']}.
One startup persistence check was recorded at {startup['recorded_utc']}, phase
{startup['phase_at_observation']}. No scientific outcomes were inspected.
Current phase at this handoff: {phase}, observed {stamp}.

The production forecast is frozen from the full excluded timing and must fit
the 14-hour ceiling and storage limits. A gate failure stops the sequence;
there is no automatic amendment or retry. Future status is durable in
CURRENT_EXECUTION.json and QUEUE_STATUS.json. All prior TT045 classifications
remain unchanged. Earlier handoffs are preserved in intake_inputs.
'''
    (ROOT/'EXECUTION.md').write_text(execution)
    status=dict(study='TT046',status_at_handoff=phase,observed_phase=phase,observed_utc=stamp,controller_pid=launch['pid'],
        current_execution='TT046/CURRENT_EXECUTION.json',dynamic_status='TT046/QUEUE_STATUS.json',report='TT046/README.md',protocol='TT046/PROTOCOL.md',
        population_confirmation=True,production_population_reused=False,new_production_outcomes_inspected=False,
        source_blocks=BLOCKS,independent_population_blocks=32,fixed_fresh_states_per_record=4,new_futures_per_fixed_state=8,
        full_qualification_pending_at_handoff=phase in ('ARCHIVING_COMPLETED_RUN','QUALIFICATION_RUNNING'),
        all_cases_and_paired_harms_retained=True,automatic_polling=False,automatic_retry=False,automatic_extension=False,automatic_successor=False)
    previous=read(PRIOR/'CURRENT_EXECUTION.json');previous['authorized_successor']=status
    replace_file(PRIOR/'CURRENT_EXECUTION.json',previous)
    intake=read(LANE/'prediction_intake_status.json');intake['updated_utc']=stamp;intake['damage_dependence_confirmation']=status
    intake['fresh_forcing_development']['authorized_successor']='TT046 authorized detached archive/qualification/confirmation sequence'
    replace_file(LANE/'prediction_intake_status.json',intake)
    brief=f'''

TT046 has started its authorized detached sequence: [fresh-source damage
confirmation](TT046/README.md), observed phase {phase} at {stamp}. It reserves
32 new blocks, four fresh births and eight paired futures per state, retaining
intact/half/full packet mixtures, preservation, all histories/masks and paired
harms. The scope is residual/own. Four co-primary fresh-state bounds must all
exceed zero: full-replacement packet benefit and its difference from intact,
each at 900 and 1000. Population inference uses source blocks; conditional
Monte Carlo errors remain separate. The lead was selected from TT045 development.

Excluded preflight passed; full qualification and measured production admission
are enforced by the controller. TT045 raw production is archived with complete
destination checksum verification and original paths preserved. The study uses
two single-thread workers on CPUs 6/7, an 18 GiB cap and 4 GiB reserve. One startup
persistence check passed. No outcomes have been inspected, and no automatic
polling, retry, extension or successor will occur. TT045 findings are unchanged.
'''
    for name in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md'):
        with (LANE/name).open('a') as f:f.write(brief)
    with (LANE/'exposure_register.jsonl').open('a') as f:
        f.write(json.dumps(dict(recorded_utc=stamp,study='TT046',event='authorized_prospective_damage_confirmation',
            primary_selected_from_TT045_development=True,source_blocks=BLOCKS,new_production_outcomes_inspected=False,
            preservation_and_all_paired_harms_retained=True,automatic_successor=False),sort_keys=True)+'\n')
    files=[LANE/n for n in ('README.md','THEORY_HANDOFF.md','DISCOVERY_LOG.md','prediction_intake_status.json','exposure_register.jsonl','TT045/CURRENT_EXECUTION.json')]
    files+=[ROOT/n for n in ('README.md','EXECUTION.md','QUEUE_PLAN.json','QUEUE_LAUNCH.json','STARTUP_PERSISTENCE_CHECK.json',
                           'admin/handoff.py','admin/check_startup.py','admin/reserve.py','admin/reserve_v2.py','admin/reserve_v3.py','RESERVATION_SCAN_CORRECTION.json','reservation.log',
                           'RESERVATION_FILENAMES.json','RESERVATION_CONTENT_SCAN.jsonl','RESERVATION_REVIEW.json','admin/review_reservation.py')]
    write(ROOT/'LAUNCH_HANDOFF.json',dict(status='PASS',recorded_utc=now(),observed_phase=phase,files={str(p):sha(p) for p in files},
        dynamic_files_not_bound=['TT046/CURRENT_EXECUTION.json','TT046/QUEUE_STATUS.json','storage_archives/CURRENT_ARCHIVE.json'],
        new_production_outcomes_inspected=False,prior_handoff_preserved=True,automatic_polling=False))
    verify(read(ROOT/'LAUNCH_HANDOFF.json')['files']);print(json.dumps(dict(status='PASS',observed_phase=phase,bound_files=len(files))))


if __name__=='__main__':main()
