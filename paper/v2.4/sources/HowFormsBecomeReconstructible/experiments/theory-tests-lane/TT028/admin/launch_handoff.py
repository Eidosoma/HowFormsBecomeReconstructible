"""Link the authorized fresh confirmation to the completed TT027 record."""
from datetime import datetime,timedelta
from pathlib import Path
import json
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import common as c

def main():
    archive=c.read_json(ROOT/'intake_inputs/MANIFEST.json')
    for row in archive['files']:
        assert c.sha(row['original'])==c.sha(row['snapshot'])==row['sha256']
    frozen=c.read_json(ROOT/'FREEZE.json');launch=c.read_json(ROOT/'LAUNCH.json')
    proof=c.read_json(ROOT/'STARTUP_PERSISTENCE_CHECK.json')
    qpath=Path(c.read_json(ROOT/'QUALIFICATION.json')['path']);q=c.read_json(qpath)
    bench=c.read_json(ROOT/'runs/benchmark_v1/COMPLETE.json')
    assert frozen['status']=='FROZEN_PROSPECTIVE_CONDITIONAL_CORRECTION_CONFIRMATION'
    assert launch['status']=='DETACHED_STARTED' and proof['status']=='PASS'
    assert launch['pid']==proof['main_pid'] and len(proof['workers'])==2
    assert proof['checked_after_launching_command_returned'] and proof['startup_check_only']
    assert launch['freeze_sha256']==c.sha(ROOT/'FREEZE.json')
    assert proof['code_sha256']==c.sha(ROOT/'admin/persistence_check.py')
    c.verify(frozen['inputs']);c.verify(frozen['evidence'])
    ack=datetime.fromisoformat(launch['acknowledged_utc']);recorded=c.now()
    forecast=(ack+timedelta(seconds=frozen['forecast_seconds'])).isoformat()
    deadline=(ack+timedelta(seconds=frozen['deadline_seconds'])).isoformat()
    current=dict(study='TT028',status='STARTED_DETACHED_STARTUP_PERSISTENCE_VERIFIED_UNPOLLED',recorded_utc=recorded,
        classification='PROSPECTIVE_CONDITIONAL_CORRECTION_CONFIRMATION',authorization='User lets go after completed TT027 and next-step proposal',
        job='TT028/runs/confirmation_v1',log='TT028/confirmation_v1.log',pid=launch['pid'],acknowledged_utc=launch['acknowledged_utc'],
        freeze='TT028/FREEZE.json',freeze_sha256=c.sha(ROOT/'FREEZE.json'),protocol='TT028/PROTOCOL.md',
        launch='TT028/LAUNCH.json',launch_sha256=c.sha(ROOT/'LAUNCH.json'),
        startup_persistence='TT028/STARTUP_PERSISTENCE_CHECK.json',startup_persistence_sha256=c.sha(ROOT/'STARTUP_PERSISTENCE_CHECK.json'),
        population_blocks=64,records_per_family=1024,independent_corruptions=2,new_recipient_draws=8,
        developed_bodies_per_record=1,arms_by_body=frozen['arms_by_body'],damage=frozen['damage'],
        primary=frozen['primary'],claims=frozen['claims'],per_claim_alpha=frozen['per_claim_alpha'],
        workers=2,numerical_threads=1,cpus=frozen['cpus'],planned_verification=frozen['planned_verification'],
        forecast_seconds=frozen['forecast_seconds'],forecast_completion_from_ack_utc=forecast,
        deadline_seconds=frozen['deadline_seconds'],deadline_from_ack_utc=deadline,
        estimated_output_bytes=frozen['estimated_output_bytes'],run_byte_limit=frozen['run_byte_limit'],
        qualification=str(qpath.relative_to(c.LANE)),qualification_status=q['status'],qualification_checks=len(q['checks']),
        qualification_seconds=q['seconds'],qualification_serial_parallel_array_files=q['serial_parallel_array_files'],
        benchmark_status=bench['status'],benchmark_seconds=bench['seconds'],benchmark='TT028/runs/benchmark_v1/COMPLETE.json',
        reserved_blocks=list(c.BLOCKS),identity_reservation='TT028/RESERVATION.json',identity_review='TT028/RESERVATION_REVIEW.json',
        new_production_outcomes_inspected=False,frozen_inputs=len(frozen['inputs']),frozen_evidence=len(frozen['evidence']),
        scientific_baseline_reuse=False,selected_winner=False,serial_endpoint=False,
        startup_verified_after_launching_command_returned=True,live_workers_verified_at_startup=2,
        latest_execution_observation='TWO_LIVE_WORKERS_AFTER_HOST_LAUNCHER_RETURNED',latest_execution_observation_utc=proof['recorded_utc'],
        automatic_polling=False,automatic_retry=False,automatic_extension=False,automatic_successor=False,
        next_check_trigger='USER_STATUS_REQUEST',administrative_archive='TT028/intake_inputs/MANIFEST.json')
    c.write_json(ROOT/'CURRENT_EXECUTION.json',current)
    previous=c.read_json(c.LANE/'TT027/CURRENT_EXECUTION.json')
    previous.update(administrative_updated_utc=recorded,authorized_successor=dict(study='TT028',status=current['status'],
        current_execution='TT028/CURRENT_EXECUTION.json',proposal='TT027/NEXT_STEP.md',protocol='TT028/PROTOCOL.md',
        new_production_outcomes_inspected=False,automatic_polling=False))
    (c.LANE/'TT027/CURRENT_EXECUTION.json').write_bytes(c.serialized(previous))
    intake=c.read_json(c.LANE/'prediction_intake_status.json')
    intake.update(updated_utc=recorded,packet_damage_body_source_development=previous,conditional_correction_confirmation=current)
    (c.LANE/'prediction_intake_status.json').write_bytes(c.serialized(intake))
    public=(f'[TT028 fresh conditional-correction confirmation](TT028/README.md) is frozen and launched under the user\'s authorization. '
        'It enrolls all **64 new source blocks / 1,024 starting records per family**, retaining passing and failing histories. '
        'Two independent corruptions restore each fixed starting state; **eight new receiving futures per output** retain matched preservation and all paired harms. '
        'Own bodies retain zero, 100 and 1,000 corrected writing updates plus full-capture and zero-initial-memory controls. '
        'Foreign and neutral bodies compare full corrected writing with preservation. Both record families and all three corruption strengths remain.\n\n'
        'The primary informative half-mixing gain must exceed **two percentage points**. Source specificity and full-replacement correction have separate '
        '**five-point** margins; three registered tests share alpha .05 through Bonferroni and use 64 paired block means. '
        'Secondary results cannot rescue the primary. Individual eight-draw estimates include explicit pointwise uncertainty and remain coarse. '
        'This tests one repair episode, without a serial or autonomous-policy claim.\n\n'
        f'All **{len(q["checks"])} qualification checks** pass, including exact reconstruction of TT027\'s exposed source recipe and serial/two-worker equality. '
        f'The full-duration excluded benchmark completes in **{bench["seconds"]:.3f} seconds**. '
        f'Production started at **{launch["acknowledged_utc"]}**, with two live workers verified after the host launcher returned. '
        f'The conservative forecast is **{frozen["forecast_seconds"]/3600:.2f} hours**, finishing around **{forecast}**. '
        'The cohort and streams were frozen before production; no production effects have been inspected. '
        'The run is left unpolled until the user asks. See [protocol](TT028/PROTOCOL.md), [freeze](TT028/FREEZE.json) and '
        '[current execution](TT028/CURRENT_EXECUTION.json). No automatic retry, extension or successor is configured.\n')
    for name in ('README.md','THEORY_HANDOFF.md'):
        with (c.LANE/name).open('a') as stream:stream.write('\n\n'+public)
    with (c.LANE/'DISCOVERY_LOG.md').open('a') as stream:
        stream.write('\n\n## 2026-10-17: TT028 frozen fresh conditional-correction confirmation\n\n'+public)
    with (c.LANE/'TT027/README.md').open('a') as stream:
        stream.write('\nThe user has now authorized the [fresh confirmation](../TT028/README.md), which is frozen and running. '
            'TT027\'s scientific results and frozen inputs remain unchanged. See [TT028 current status](../TT028/CURRENT_EXECUTION.json).\n')
    (ROOT/'README.md').write_text('# TT028: fresh conditional correction confirmation\n\n'+public.replace('(TT028/','(')+
        '\nThe original identity scan flagged a disposable number inside a SHA256 value; '
        'the [review](RESERVATION_REVIEW.json) verified it was not a source identity. The failed scan remains intact, '
        'with no changed cohort or resampling.\n')
    c.write_json(ROOT/'EXECUTION.json',dict(freeze_sha256=c.sha(ROOT/'FREEZE.json'),qualification=str(qpath),
        qualification_seconds=q['seconds'],benchmark_seconds=bench['seconds'],forecast_seconds=frozen['forecast_seconds'],
        startup_persistence='TT028/STARTUP_PERSISTENCE_CHECK.json',original_sources_read_only=True,
        numerical_threads_per_worker=1,live_workers_verified=2,automatic_polling=False))
    event=dict(event='TT028_FRESH_CONFIRMATION_FROZEN_AND_PERSISTENT_STARTUP_VERIFIED',study='TT028',recorded_utc=recorded,
        prior_development='TT027',prior_development_exposed=True,freeze_sha256=c.sha(ROOT/'FREEZE.json'),
        launch_sha256=c.sha(ROOT/'LAUNCH.json'),blocks=list(c.BLOCKS),claims=frozen['claims'],
        no_production_effects_inspected=True,automatic_polling=False,automatic_retry=False,automatic_successor=False)
    with (c.LANE/'exposure_register.jsonl').open('a') as stream:stream.write(json.dumps(event,sort_keys=True,allow_nan=False)+'\n')
    for target in re.findall(r'\]\(([^)]+)\)',(ROOT/'README.md').read_text()):assert (ROOT/target).exists()
    assert c.read_json(c.LANE/'prediction_intake_status.json')['conditional_correction_confirmation']==current
    c.verify(frozen['inputs']);c.verify(frozen['evidence'])
    files={Path(r['original']) for r in archive['files']}
    files|={ROOT/n for n in ('README.md','EXECUTION.json','CURRENT_EXECUTION.json','FREEZE.json','LAUNCH.json',
        'STARTUP_PERSISTENCE_CHECK.json','RESERVATION_REVIEW.json','admin/persistence_check.py','admin/launch_handoff.py')}
    receipt=dict(status='PASS_LAUNCH_HANDOFF',recorded_utc=c.now(),files={str(p):c.sha(p) for p in sorted(files)},
        source_cohort_fresh=True,scientific_inputs_unchanged=True,production_effects_inspected=False,
        startup_verified_after_host_launcher_return=True,current_status_consistent=True,document_links_pass=True,
        automatic_polling=False,automatic_retry=False,automatic_extension=False,automatic_successor=False)
    c.verify(receipt['files']);c.write_json(ROOT/'LAUNCH_HANDOFF.json',receipt)
    print({k:v for k,v in receipt.items() if k!='files'},flush=True)
if __name__=='__main__':main()
