"""Capacity admission and persistent launch; no scientific run polling."""
import argparse
import json
import os
import select
import subprocess
import sys
import time
import traceback

from common import ROOT, read, sha, stamp, status, write
from cpu_preflight import collect
from run import validate_frozen


def spawn(command, log, ready_fd):
    return subprocess.Popen(command, cwd=ROOT, env=os.environ.copy(), stdin=subprocess.DEVNULL,
        stdout=log, stderr=subprocess.STDOUT, start_new_session=True, close_fds=True, pass_fds=(ready_fd,))


def receive_ack(fd):
    ready, _, _ = select.select([fd], [], [], 20.)
    message = os.read(fd, 64) if ready else b''
    os.close(fd)
    return message


def admit(ready_fd):
    folder = ROOT / 'run'

    def acknowledge(message):
        nonlocal ready_fd
        if ready_fd is not None:
            os.write(ready_fd, message)
            os.close(ready_fd)
            ready_fd = None

    try:
        validate_frozen()
        write(folder / 'ADMISSION_STARTED.json', dict(at_utc=stamp(), pid=os.getpid(), scientific_run_polling=False))
        checks = folder / 'admission_checks'
        checks.mkdir(exist_ok=False)
        attempt = 0
        while True:
            attempt += 1
            receipt = collect()
            write(checks / f'check_{attempt:04d}.json', receipt)
            if receipt['within_limit']:
                write(folder / 'CPU_ADMISSION.json', receipt)
                break
            status(folder, status='WAITING_FOR_CPU', capacity_checks=attempt)
            acknowledge(b'QUEUED\n')
            time.sleep(60)
        validate_frozen()
        receive, send = os.pipe()
        with (folder / 'console.log').open('xb') as log:
            child = spawn([sys.executable, '-B', str(ROOT / 'run.py'), '--ready-fd', str(send)], log, send)
        os.close(send)
        assert receive_ack(receive) == b'READY\n', 'Worker did not acknowledge verified startup; preserve evidence.'
        started = read(folder / 'WORKER_STARTED.json')
        assert started['pid'] == child.pid and started['ready_inputs_verified']
        with (folder / 'PID').open('x') as f:
            f.write(str(child.pid) + '\n')
        launch = dict(status='RUNNING', at_utc=stamp(), pid=child.pid, detached=True,
            stdin='/dev/null', workers=1, numerical_threads=1, scientific_run_polling=False,
            frozen_sha256=sha(ROOT / 'FROZEN.json'),
            forecast_minutes=read(ROOT / 'qualification' / 'COMPLETE.json')['forecast_wall_seconds'] / 60,
            selected_contexts=46, branches=3, successors_per_context=18, future_reads=2484,
            report=str(folder / 'REPORT.md'), completion_marker=str(folder / 'COMPLETE.json'))
        write(folder / 'LAUNCH.json', launch)
        write(folder / 'ADMISSION_COMPLETE.json', dict(at_utc=stamp(), status='STARTED_ONCE',
            worker_pid=child.pid, capacity_checks=attempt, scientific_run_polled=False))
        acknowledge(b'RUNNING\n')
        print(json.dumps(launch, indent=2), flush=True)
    except BaseException:
        write(folder / 'ADMISSION_FAILED.json', dict(at_utc=stamp(), traceback=traceback.format_exc()))
        status(folder, status='FAILED', phase='admission')
        raise
    finally:
        if ready_fd is not None:
            os.close(ready_fd)


def launch():
    manifest = validate_frozen()
    assert sys.executable == manifest['executable']
    folder = ROOT / 'run'
    folder.mkdir(exist_ok=False)
    receive, send = os.pipe()
    with (folder / 'admission.log').open('xb') as log:
        child = spawn([sys.executable, '-B', str(ROOT / 'launch.py'), '--admit-fd', str(send)], log, send)
    os.close(send)
    ack = receive_ack(receive)
    assert ack in (b'QUEUED\n', b'RUNNING\n'), 'Admission startup not acknowledged; preserve evidence.'
    with (folder / 'ADMISSION_PID').open('x') as f:
        f.write(str(child.pid) + '\n')
    write(folder / 'QUEUE.json', dict(at_utc=stamp(), admission_pid=child.pid,
        status='WAITING_FOR_CPU' if ack == b'QUEUED\n' else 'RUNNING', startup_acknowledged=True,
        scientific_run_polling=False, frozen_sha256=sha(ROOT / 'FROZEN.json')))
    print(json.dumps(read(folder / ('LAUNCH.json' if ack == b'RUNNING\n' else 'QUEUE.json')), indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--admit-fd', type=int)
    args = parser.parse_args()
    admit(args.admit_fd) if args.admit_fd is not None else launch()
