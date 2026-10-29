"""Recorded administrative continuation: reuse qualification; first production once."""
import argparse, math, os, select, subprocess, sys, time, traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import *
import execute, resources

HERE = ROOT / 'corrections/storage_layout_v2'
RESOURCE = 'corrections/storage_layout_v2/PRODUCTION_RESOURCE.json'
ARCHIVE = LANE / 'storage_archives/2026-10-24_completed-runs_v1'


def replace_file(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.continuation-pending')
    write(temporary, value)
    os.replace(temporary, path)


def state(phase, **extra):
    value = dict(study='TT042', status=phase, phase=phase, updated_utc=now(),
                 controller_pid=os.getpid(), qualification_status='PASS',
                 continuation='corrections/storage_layout_v2',
                 previous_failure='QUEUE_FAILED.json',
                 run='TT042/runs/exchange_v1',
                 automatic_polling=False, automatic_retry=False,
                 automatic_extension=False, automatic_successor=False, **extra)
    replace_file(HERE / 'STATUS.json', value)
    replace_file(ROOT / 'QUEUE_STATUS.json', value)
    replace_file(ROOT / 'CURRENT_EXECUTION.json', value)


def prepare():
    assert not (ROOT / 'FREEZE.json').exists()
    assert not (ROOT / 'runs/exchange_v1').exists()
    review = read(HERE / 'REVIEW.json')
    qpath = ROOT / 'runs/qualification_v1/COMPLETE.json'
    ppath = ROOT / 'checks/preflight_v1/COMPLETE.json'
    q, pre = read(qpath), read(ppath)
    assert review['status'] == 'PASS' and review['new_dynamics'] == 0
    assert review['code_sha256'] == sha(ROOT / 'admin/storage_layout_v2.py')
    assert review['qualification_sha256'] == sha(qpath)
    assert q['status'] == 'COMPLETE' and q['serial_parallel_bitwise_equal']
    assert pre['status'] == 'PASS' and q['inputs'] == pre['inputs'] == inputs()
    assert q['environment'] == execute.environment()
    assert not review['resource_limits_changed'] and not review['scientific_definitions_changed']
    assert (review['study_cap_bytes'], review['free_reserve_bytes']) == (LIMIT, RESERVE)
    verify(q['outputs']); verify(pre['outputs']); verify(q['inputs'])
    verify(read(ROOT / 'SOURCE_MANIFEST.json')['evidence'])
    verify(read(HERE / 'USED_STARTING_STATES.json'))
    assert read(ARCHIVE / 'COMPLETE.json')['status'] == 'COMPLETE'
    # Retain the formerly current handoff and failed queue before changing pointers.
    prior = ROOT / 'status_reviews/storage_gate_v1/HANDOFF.json'
    handoff = read(prior); verify(handoff['files'])
    saved = HERE / 'prior_handoff'; saved.mkdir()
    paths = set(handoff['files']) | {str(prior), str(ROOT / 'QUEUE_STATUS.json'),
                                    str(ROOT / 'QUEUE_FAILED.json')}
    custody = {}
    for name in sorted(paths):
        source = Path(name); target = saved / source.relative_to(LANE)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        assert sha(source) == sha(target)
        custody[name] = dict(archive=str(target), sha256=sha(target))
    write(HERE / 'PRIOR_HANDOFF_ARCHIVE.json', custody)
    forecast = math.ceil(3 * q['seconds'] + 60)
    projected = review['projected_additional_bytes']
    current = size(); free = shutil.disk_usage(ROOT).free
    assert forecast < 4 * 3600 and current + projected < LIMIT and free >= RESERVE + projected
    evidence = [qpath, ppath, HERE / 'REVIEW.json', HERE / 'USED_STARTING_STATES.json',
                HERE / 'PRIOR_HANDOFF_ARCHIVE.json', ROOT / 'QUEUE_FAILED.json',
                ROOT / 'admin/storage_layout_v2.py', Path(__file__),
                ARCHIVE / 'COMPLETE.json', ARCHIVE / 'CLOSEOUT.json']
    value = dict(study='TT042', frozen_utc=now(), inputs=inputs(),
                 evidence={str(p): sha(p) for p in evidence}, environment=execute.environment(),
                 cpus=[6, 7], workers=2, numerical_threads=1, blocks=BLOCKS, run_name='exchange_v1',
                 forecast_seconds=forecast, deadline_seconds=max(600, 2 * forecast),
                 forecast_new_output_bytes=projected, study_output_ceiling_bytes=LIMIT,
                 free_reserve_bytes=RESERVE, current_study_bytes=current, free_bytes=free,
                 projected_total_bytes=current + projected, budget_headroom_bytes=LIMIT-current-projected,
                 forecast_rule='3 times the measured two-block excluded duration plus 60 seconds',
                 storage_projection_method='Exact starting-state count and fixed numeric layouts; conservative NPZ envelopes and explicit metadata/report/admin allowances; REVIEW.json',
                 superseded_storage_formula='3 times two-block retained bytes plus 64 MiB; no former production freeze existed',
                 qualified_code_unchanged=True, limits_unchanged=True, qualification_reused=True,
                 first_production_attempt=True, source_population_exposed=True,
                 source_forcing_reused=True, recipient_evidence_inherited=True, new_receiving_assays=0,
                 new_production_outcomes_generated=False, confirmatory=False, all_cases_retained=True,
                 primary='mix050; residual|all|all_masks|own; target at 1900; both conditional packet effects, both conditional body effects, total and interaction',
                 automatic_polling=False, automatic_retry=False, automatic_extension=False, automatic_successor=False)
    write(ROOT / 'FREEZE.json', value)
    print(json.dumps({k: value[k] for k in ('frozen_utc', 'forecast_seconds', 'deadline_seconds',
                                          'projected_total_bytes', 'budget_headroom_bytes')}), flush=True)


def launch():
    frozen = read(ROOT / 'FREEZE.json')
    assert frozen['inputs'] == inputs() and frozen['environment'] == execute.environment()
    verify(frozen['evidence'])
    assert not (ROOT / 'runs/exchange_v1').exists() and not (HERE / 'LAUNCH.json').exists()
    assert len(list(Path('/proc').glob('[0-9]*'))) > 16
    assert size() + frozen['forecast_new_output_bytes'] < LIMIT
    assert shutil.disk_usage(ROOT).free >= RESERVE + frozen['forecast_new_output_bytes']
    # This is the only new host capacity admission, immediately before production.
    resources.main(RESOURCE)
    rd, wr = os.pipe(); log = HERE / 'production_v1.log'
    with log.open('xb') as out:
        child = subprocess.Popen(['bash', str(LANE / 'run_python.sh'), str(Path(__file__)), '--run'],
                                 cwd=LANE, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                                 start_new_session=True, pass_fds=(wr,),
                                 env=dict(os.environ, TT042_DETACHED='1', TT042_READY_FD=str(wr)))
    os.close(wr)
    ready = select.select([rd], [], [], 30)[0]
    message = os.read(rd, 64) if ready else b''; os.close(rd)
    value = dict(status='DETACHED_STARTED' if message == b'READY\n' else 'STARTUP_NOT_ACKNOWLEDGED',
                 pid=child.pid, acknowledged_utc=now(), log=str(log), freeze_sha256=sha(ROOT / 'FREEZE.json'),
                 forecast_seconds=frozen['forecast_seconds'], deadline_seconds=frozen['deadline_seconds'],
                 cpus=[6, 7], workers=2, numerical_threads=1, first_production_attempt=True,
                 qualification_reused=True, automatic_polling=False, automatic_retry=False, automatic_successor=False)
    write(HERE / 'LAUNCH.json', value)
    assert message == b'READY\n'
    print(json.dumps(value), flush=True)


def run_once():
    tick = time.monotonic()
    try:
        assert os.environ.get('TT042_DETACHED') == '1'
        os.sched_setaffinity(0, {6, 7}); assert os.getpriority(os.PRIO_PROCESS, 0) == 0
        frozen = read(ROOT / 'FREEZE.json'); verify(frozen['evidence'])
        assert frozen['inputs'] == inputs() and frozen['environment'] == execute.environment()
        state('PRODUCTION_RUNNING', production_started=True, production_completed=False,
              no_active_jobs=False, forecast_seconds=frozen['forecast_seconds'],
              deadline_seconds=frozen['deadline_seconds'], freeze_sha256=sha(ROOT / 'FREEZE.json'),
              production_results_inspected=False)
        fd = int(os.environ.pop('TT042_READY_FD'))
        os.write(fd, b'READY\n'); os.close(fd)
        result = execute.execute('development', 'exchange_v1', RESOURCE)
        write(HERE / 'COMPLETE.json', dict(status='COMPLETE', completed_utc=now(),
              seconds=time.monotonic()-tick, production_complete_sha256=sha(ROOT / 'runs/exchange_v1/COMPLETE.json'),
              scientific_interpretation_pending=True, automatic_polling=False, automatic_successor=False))
        state('COMPLETE_AWAITING_REVIEW', production_started=True, production_completed=True,
              completed_utc=result['completed_utc'], production_seconds=result['seconds'],
              no_active_jobs=True, production_results_inspected=False)
    except BaseException as error:
        write(HERE / 'FAILED.json', dict(status='FAILED', failed_utc=now(), error=repr(error),
              traceback=traceback.format_exc(), automatic_retry=False))
        state('FAILED', error=repr(error), no_active_jobs=True,
              production_started=(ROOT / 'runs/exchange_v1').exists(), production_completed=False)
        raise


def startup():
    assert len(list(Path('/proc').glob('[0-9]*'))) > 16
    assert not (HERE / 'STARTUP_CHECK.json').exists()
    launched = read(HERE / 'LAUNCH.json')
    age = (datetime.now(timezone.utc)-datetime.fromisoformat(launched['acknowledged_utc'])).total_seconds()
    if age < 15: time.sleep(15-age)
    pid = launched['pid']; fields = (Path('/proc')/str(pid)/'stat').read_text().rsplit(')', 1)[1].split()
    assert fields[0] not in ('Z', 'X') and os.getpgid(pid) == pid and os.sched_getaffinity(pid) == {6, 7}
    assert not (HERE / 'FAILED.json').exists()
    current = read(HERE / 'STATUS.json'); assert current['phase'] == 'PRODUCTION_RUNNING'
    workers = []
    for path in sorted((ROOT / 'runs/exchange_v1').glob('worker_*.json')):
        w = read(path); fields = (Path('/proc')/str(w['pid'])/'stat').read_text().rsplit(')', 1)[1].split()
        assert fields[0] not in ('Z', 'X') and os.sched_getaffinity(w['pid']) == {w['cpu']}
        assert os.getpriority(os.PRIO_PROCESS, w['pid']) == 0
        workers.append(w)
    assert len(workers) == 2 and {w['cpu'] for w in workers} == {6, 7}
    value = dict(status='PASS', recorded_utc=now(), pid=pid, workers=workers,
                 phase_at_observation=current['phase'], one_persistence_check=True,
                 scientific_results_inspected=False, post_startup_result_polling=False)
    write(HERE / 'STARTUP_CHECK.json', value); print(json.dumps(value), flush=True)


def handoff():
    check = read(HERE / 'STARTUP_CHECK.json'); frozen = read(ROOT / 'FREEZE.json')
    assert check['status'] == 'PASS' and not (HERE / 'HANDOFF.json').exists()
    for item in read(HERE / 'PRIOR_HANDOFF_ARCHIVE.json').values():
        assert sha(item['archive']) == item['sha256']
    message = '''

TT042's first production run is now launched after the recorded storage
correction on 24 October. The full excluded qualification is reused unchanged;
the old failed admission and handoff remain archived. Completed TT030/TT036 run
data were verified and moved to /mnt/datasets with working original-path links.
The archive covers 20,524,007,050 bytes and 143,608 files, completed in 22 minutes.

Storage admission now counts the actual 848 distinct production starting states
and fixed numeric file layouts, with conservative container and metadata/admin
allowances. The projected additional output is 790,430,220 bytes and fits the
existing 1 GiB study cap. The 4 GiB reserve, runtime limits, qualified scientific
code, source cases, controls, paired harms and protocol are unchanged. No new
physical outcome was generated to obtain this storage estimate.

The measured production forecast is 19 minutes 39 seconds; its fixed deadline
is 39 minutes 18 seconds. The single startup check confirmed two normal-priority
single-thread workers on CPUs 6 and 7. The detached run is unpolled until the
user requests status. There is no automatic retry, extension or successor.
Scientific interpretation remains pending; these are four exposed development
blocks, with TT040 recipient evidence inherited and no new receiving assays.
'''
    for name in ('README.md', 'EXECUTION.md'):
        with (ROOT / name).open('a') as f:
            f.write(message + '\nSee [storage review](corrections/storage_layout_v2/REVIEW.json), '
                    '[freeze](FREEZE.json), and [current status](CURRENT_EXECUTION.json).\n')
    brief = message + '\nSee [TT042](TT042/README.md) and [archive receipt](storage_archives/2026-10-24_completed-runs_v1/COMPLETE.json).\n'
    for name in ('README.md', 'THEORY_HANDOFF.md', 'DISCOVERY_LOG.md'):
        with (LANE / name).open('a') as f: f.write(brief)
    intake = read(LANE / 'prediction_intake_status.json'); intake['updated_utc'] = now()
    intake['body_packet_exchange_development'].update(
        status='PRODUCTION_LAUNCHED', status_at_handoff='PRODUCTION_LAUNCHED', observed_utc=check['recorded_utc'],
        observed_phase='PRODUCTION_RUNNING', production_started=True, production_completed=False,
        no_active_jobs=False, controller_pid=check['pid'], qualification_status='PASS',
        full_qualification_pending_at_handoff=False, qualification_reused=True,
        production_started_at_observation=True, new_production_outcomes_inspected=False,
        production_outcomes_exist=None,
        storage_correction='TT042/corrections/storage_layout_v2/REVIEW.json',
        dynamic_status='TT042/CURRENT_EXECUTION.json', forecast_seconds=frozen['forecast_seconds'],
        first_production_attempt=True, previous_failure_retained=True)
    replace_file(LANE / 'prediction_intake_status.json', intake)
    event = dict(recorded_utc=now(), study='TT042', event='first_production_after_recorded_storage_correction',
                 qualification_reused=True, qualified_scientific_inputs_unchanged=True, resource_limits_unchanged=True,
                 source_population_exposed=True, source_blocks=BLOCKS, new_receiving_assays=0,
                 new_production_outcomes_inspected=False, confirmatory=False, all_cases_retained=True,
                 previous_classifications_unchanged=True, automatic_polling=False, automatic_successor=False)
    with (LANE / 'exposure_register.jsonl').open('a') as f: f.write(json.dumps(event, sort_keys=True)+'\n')
    files = [LANE / n for n in ('README.md', 'THEORY_HANDOFF.md', 'DISCOVERY_LOG.md',
                               'prediction_intake_status.json', 'exposure_register.jsonl')]
    files += [ROOT / n for n in ('README.md', 'EXECUTION.md', 'FREEZE.json')]
    files += [HERE / n for n in ('REVIEW.json', 'USED_STARTING_STATES.json', 'PRIOR_HANDOFF_ARCHIVE.json',
                                'LAUNCH.json', 'STARTUP_CHECK.json', 'PRODUCTION_RESOURCE.json')]
    write(HERE / 'HANDOFF.json', dict(status='PASS', recorded_utc=now(), files={str(p):sha(p) for p in files},
          phase_at_startup_observation='PRODUCTION_RUNNING', scientific_results_inspected=False,
          dynamic_status_not_hash_bound='TT042/CURRENT_EXECUTION.json', automatic_polling=False))
    catalog_path = LANE / 'storage_archives/CURRENT_ARCHIVE.json'
    catalog = read(catalog_path)
    catalog.update(status='COMPLETE_VERIFIED', TT042_production_resumed=True,
                   TT042_status='TT042/CURRENT_EXECUTION.json')
    replace_file(catalog_path, catalog)
    print(json.dumps(dict(status='PASS', bound_files=len(files), scientific_results_inspected=False)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); group = parser.add_mutually_exclusive_group(required=True)
    for mode in ('prepare', 'launch', 'run', 'startup', 'handoff'): group.add_argument('--'+mode, action='store_true')
    args = parser.parse_args()
    {'prepare':prepare, 'launch':launch, 'run':run_once, 'startup':startup, 'handoff':handoff}[
        next(mode for mode in ('prepare', 'launch', 'run', 'startup', 'handoff') if getattr(args, mode))]()
