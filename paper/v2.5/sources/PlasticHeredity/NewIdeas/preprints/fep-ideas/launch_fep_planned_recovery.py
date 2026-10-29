#!/usr/bin/env python3
"""Wait without polling for preparation, then launch and verify the frozen run."""
import sys
sys.dont_write_bytecode = True
import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import subprocess
import time
import traceback
from datetime import datetime, timezone

SOURCE = Path(__file__).resolve().parent
ROOT = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-planned-recovery-v1')
OUTPUT = ROOT/'attempt-01'


def utc():
    return datetime.now(timezone.utc).isoformat()


def write(name, value):
    with (ROOT/name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def process(pid):
    path = Path('/proc')/str(pid)
    stat = (path/'stat').read_text().rsplit(')', 1)[1].split()
    status = {line.split(':', 1)[0]: line.split(':', 1)[1].strip()
              for line in (path/'status').read_text().splitlines() if ':' in line}
    return dict(pid=pid, state=stat[0], start_ticks=int(stat[19]),
                session=int(stat[3]), process_group=int(stat[2]), nice=int(stat[16]),
                cpus=sorted(os.sched_getaffinity(pid)), threads=int(status['Threads']),
                rss=status.get('VmRSS'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare-pid', type=int, required=True)
    parser.add_argument('--prepare-start-ticks', type=int, required=True)
    args = parser.parse_args()
    os.sched_setaffinity(0, {0, 1, 2, 3})
    if os.getpriority(os.PRIO_PROCESS, 0) < 10:
        os.nice(10-os.getpriority(os.PRIO_PROCESS, 0))
    try:
        # pidfd readiness is process exit, not repeated progress inspection.
        try:
            descriptor = os.pidfd_open(args.prepare_pid)
        except ProcessLookupError:
            descriptor = None
        if descriptor is not None:
            try:
                current = process(args.prepare_pid)
            except (FileNotFoundError, ProcessLookupError):
                current = None
            if current is not None:
                assert current['start_ticks'] == args.prepare_start_ticks
        write('SUPERVISOR_STARTED.json', dict(utc=utc(), process=process(os.getpid()),
              preparation_pid=args.prepare_pid, preparation_start_ticks=args.prepare_start_ticks,
              waiting_for_preparation_exit=descriptor is not None,
              launcher_source=str(Path(__file__).resolve()), launcher_sha256=digest(__file__),
              wait_method='Linux pidfd/select; no progress polling'))
        if descriptor is not None:
            select.select([descriptor], [], [])
            os.close(descriptor)
        assert not list(OUTPUT.glob('FAILURE-*.json'))
        assert not (OUTPUT/'STARTED.json').exists()
        qualification = json.loads((OUTPUT/'QUALIFICATION.json').read_text())
        benchmark = json.loads((OUTPUT/'BENCHMARK.json').read_text())
        frozen = json.loads((OUTPUT/'FREEZE.json').read_text())
        assert qualification['passed']
        for path, expected in frozen['inputs'].items():
            assert digest(path) == expected, path
        for path, expected in frozen['snapshots'].items():
            assert digest(OUTPUT/'inputs'/path) == expected, path
        if not benchmark['within_compute_bound']:
            write('FEASIBILITY_STOP.json', dict(utc=utc(), status='STOPPED_BEFORE_MAIN',
                  forecast_seconds=benchmark['forecast_seconds']))
            return
        command = [sys.executable, '-B', '-u', str(SOURCE/'run_fep_planned_recovery.py'),
                   'run', '--output', str(OUTPUT), '--detached']
        with (ROOT/'attempt-01-detached.log').open('xb') as stream:
            child = subprocess.Popen(command, cwd=SOURCE, stdin=subprocess.DEVNULL,
                                     stdout=stream, stderr=subprocess.STDOUT,
                                     start_new_session=True, close_fds=True)
        write('LAUNCH.json', dict(utc=utc(), pid=child.pid, command=command,
              forecast_seconds=benchmark['forecast_seconds'],
              benchmark_sha256=digest(OUTPUT/'BENCHMARK.json'),
              qualification_sha256=digest(OUTPUT/'QUALIFICATION.json'),
              freeze_sha256=digest(OUTPUT/'FREEZE.json'), launcher_sha256=digest(__file__)))
        # Exactly one startup inspection; no subsequent progress polling.
        time.sleep(4)
        coordinator = process(child.pid)
        children = [int(v) for v in (Path('/proc')/str(child.pid)/'task'/str(child.pid)/'children').read_text().split()]
        workers = [process(pid) for pid in children]
        started = json.loads((OUTPUT/'STARTED.json').read_text())
        checks = dict(detached=coordinator['session'] == coordinator['process_group'] == child.pid,
                      four_workers=len(workers) == 4, declared_detached=started['detached'],
                      coordinator_identity=started['pid'] == child.pid,
                      coordinator_limits=len(coordinator['cpus']) <= 4 and coordinator['nice'] >= 10,
                      worker_limits=all(len(p['cpus']) <= 4 and p['nice'] >= 10 and p['threads'] == 1 for p in workers))
        write('LAUNCH_VERIFIED.json', dict(utc=utc(), passed=all(checks.values()), checks=checks,
              coordinator=coordinator, workers=workers, started_sha256=digest(OUTPUT/'STARTED.json'),
              future_progress_polling=False))
        assert all(checks.values())
    except BaseException:
        write('FAILURE-supervisor.json', dict(utc=utc(), traceback=traceback.format_exc(),
              main_may_have_started=(OUTPUT/'STARTED.json').exists()))
        raise


if __name__ == '__main__':
    main()
