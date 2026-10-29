"""Bounded execution and explicit recovery of the identical frozen experiment."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import sys
import time
import traceback

import numpy as np

from bridge import ROOT, P, ev, read, verify_inputs
import acquisition
import ledger
import pipeline


@contextmanager
def exclusive_run(folder):
    """Keep the lock file across invocations; only its kernel lock is transient."""
    with (folder/'RUN.lock').open('a') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError('Another invocation owns this run') from error
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def initialize(folder, mode, binding, spec, resume=False, now=None):
    """Call only under the run lock. Recovery never extends the UTC deadline."""
    now = time.time() if now is None else now
    path = folder/'RUN.json'
    if (folder/'COMPLETE.json').exists():
        raise ValueError('Completed runs cannot be resumed or overwritten')
    if resume:
        saved = read(path)
        if saved['binding'] != binding or saved['mode'] != mode or saved['spec'] != spec:
            raise ValueError('Resume requires identical frozen inputs, mode and cohort')
        if now >= saved['deadline_epoch']:
            raise TimeoutError('Original run deadline expired; it cannot be reset')
        return saved
    if path.exists():
        raise FileExistsError('Existing run requires an explicit resume')
    ceiling = P['resources'][mode+'_wall_ceiling_seconds']
    saved = dict(utc=ev.utc(), mode=mode, binding=binding, spec=spec,
                 original_started_epoch=now, deadline_epoch=now+ceiling,
                 deadline_utc=datetime.fromtimestamp(now+ceiling, timezone.utc).isoformat())
    ledger.atomic_json(path, saved)
    return saved


class Guard:
    def __init__(self, root, run):
        self.root = root
        self.scientific = run['mode'] == 'outcome'
        self.deadline = run['deadline_epoch']
        self.end = time.monotonic()+max(0., self.deadline-time.time())
        resources = P['resources']
        self.maximum = resources['maximum_saved_bytes' if self.scientific else 'qualification_maximum_saved_bytes']
        self.minimum_free = resources['minimum_free_during_run_bytes' if self.scientific else 'qualification_minimum_free_disk_bytes']
        self.seen = set()
        self.saved_bytes = 0
        self.next_disk_check = 0.
        self.account(root)

    def account(self, folder):
        for path in folder.rglob('*'):
            if path.is_file() and path not in self.seen:
                self.seen.add(path)
                self.saved_bytes += path.stat().st_size

    def check(self):
        now = time.monotonic()
        if now >= self.end or time.time() >= self.deadline:
            raise TimeoutError('Frozen wall deadline exceeded; no automatic retry')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 > P['resources']['maximum_resident_bytes']:
            raise MemoryError('Frozen resident memory ceiling exceeded')
        if self.saved_bytes > self.maximum:
            raise OSError('Frozen saved-evidence ceiling exceeded')
        if now >= self.next_disk_check:
            if shutil.disk_usage(self.root).free < self.minimum_free:
                raise OSError('Insufficient free disk; preserve partial work and stop')
            self.next_disk_check = now+30.


def verify_configuration(mode):
    count = verify_inputs()
    if ev.sha(ROOT/'FROZEN_MODELS.json') != P['prediction']['sha256']:
        raise ValueError('Fixed model artifact changed')
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
        if os.environ.get(name) != '1':
            raise ValueError('One numerical thread is required: '+name)
    build = read(ROOT/'BUILD.json')
    if build['numpy_version'] != np.__version__ or build['python_version'] != sys.version:
        raise ValueError('Numerical runtime differs from the qualified build')
    if ev.sha(ROOT/'stencil.c') != build['source_sha256'] or ev.sha(ROOT/build['binary']) != build['binary_sha256']:
        raise ValueError('Qualified stencil source or binary changed')
    if mode == 'outcome':
        qualification = read(ROOT/'NATIVE_QUALIFICATION.json')
        if qualification['status'] != 'PASS':
            raise ValueError('Complete native runner qualification is required')
        for name, digest in qualification['source_sha256'].items():
            if ev.sha(ROOT/name) != digest:
                raise ValueError('Source changed after native qualification: '+name)
        if P['cohort']['blocks'] != list(range(304)) or P['cohort']['records_per_block'] != 64:
            raise ValueError('Scientific cohort differs from amendment 1')
    return count


def legacy_replay(root, spec, binding, guard):
    ident = pipeline.identity(binding, spec, 'legacy_g14_replay', block=34000)
    def work(folder):
        raw, rows, receipt = acquisition.acquire(34000, 'qualification', folder, guard, legacy=True)
        archived = ev.load(ROOT/'context/legacy_g14.npz', ev.sha(ROOT/'context/legacy_g14.npz'))
        for name in ('end', 'outgoing', 'mean_ports'):
            a, b = raw[name], archived[name]
            if a.shape != b.shape or a.dtype != b.dtype or a.tobytes() != b.tobytes():
                raise ArithmeticError('Legacy acquisition replay differs: '+name)
        ev.save(folder/'boundary.npz', raw)
        from verify_science import boundary
        verification = boundary(ROOT, folder, rows)
        value = dict(status='PASS', byte_exact_fields=['end', 'outgoing', 'mean_ports'],
                     receipt=receipt, boundary_verification=verification,
                     archived_sha256=ev.sha(ROOT/'context/legacy_g14.npz'),
                     new_scientific_outcomes=0)
        ev.write(folder/'VERIFICATION.json', value)
        return value
    folder, value = pipeline.unit(root/'units/legacy_replay', ident, work, guard)
    return dict(reference=ledger.reference(root, folder), **value['payload'])


def run(mode, folder, resume=False):
    folder = folder.resolve()
    if resume:
        if not folder.is_dir():
            raise FileNotFoundError('Resume run directory is missing')
    else:
        folder.mkdir(parents=True, exist_ok=False)
    with exclusive_run(folder):
        invocation = ledger.new_attempt(folder/'invocations')
        started, cpu = time.monotonic(), time.process_time()
        def timeout(*_):
            raise TimeoutError('Original frozen run deadline exceeded')
        old_handler = signal.signal(signal.SIGALRM, timeout)
        try:
            count = verify_configuration(mode)
            binding = ev.sha(ROOT/'INPUTS.json')
            spec = pipeline.specification(mode)
            saved = initialize(folder, mode, binding, spec, resume)
            signal.alarm(max(1, math.ceil(saved['deadline_epoch']-time.time())))
            ledger.atomic_json(invocation/'START.json', dict(utc=ev.utc(), mode=mode, resume=resume,
                pid=os.getpid(), binding=binding, deadline_utc=saved['deadline_utc']))
            sys.path.insert(0, str(ROOT/'inherited/reference'))
            import cpu_preflight
            admission = cpu_preflight.collect()
            ledger.atomic_json(invocation/'CPU_ADMISSION.json', admission)
            if not admission['within_limit']:
                raise RuntimeError('Shared CPU slot unavailable; no automatic retry')
            required = P['resources']['minimum_free_disk_bytes' if mode == 'outcome' else 'qualification_minimum_free_disk_bytes']
            available = shutil.disk_usage(folder).free
            ledger.atomic_json(invocation/'DISK_ADMISSION.json', dict(available_bytes=available, required_bytes=required))
            if available < required:
                raise OSError('Initial disk admission failed')
            guard = Guard(folder, saved)
            guard.check()
            ev.status(folder, status='RUNNING', mode=mode, stage='initialization', invocation=invocation.name)
            print(dict(status='RUNNING', mode=mode, resume=resume, deadline_utc=saved['deadline_utc']), flush=True)
            def event(stage, details):
                guard.check()
                ev.status(folder, status='RUNNING', mode=mode, stage=stage,
                          invocation=invocation.name, details=details)
            legacy = None
            if mode == 'native_qualification':
                event('legacy_g14_replay', {})
                legacy = legacy_replay(folder, spec, binding, guard)
                event('legacy_g14_replay_committed', {})
            result = pipeline.run(folder, spec, binding, guard, event)
            verify_inputs()
            guard.account(folder)
            guard.check()
            complete = dict(utc=ev.utc(), status='COMPLETE', mode=mode, binding=binding,
                result=result, legacy=legacy, wall_seconds=time.monotonic()-started,
                elapsed_from_original_launch_seconds=time.time()-saved['original_started_epoch'],
                cpu_seconds=time.process_time()-cpu,
                peak_resident_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                saved_bytes=guard.saved_bytes, frozen_input_files_verified=count,
                scientific_future_outcomes=0 if mode == 'native_qualification' else result['case_regimes'])
            ledger.atomic_json(invocation/'COMPLETE.json', complete)
            ledger.atomic_json(folder/'COMPLETE.json', complete)
            ev.status(folder, status='COMPLETE', mode=mode, stage='complete', invocation=invocation.name)
            print(dict(status='COMPLETE', mode=mode, wall_seconds=complete['wall_seconds'],
                       scientific_future_outcomes=complete['scientific_future_outcomes']), flush=True)
            return complete
        except BaseException as error:
            ledger.atomic_json(invocation/'FAILED.json', dict(utc=ev.utc(), type=type(error).__name__,
                message=str(error), traceback=traceback.format_exc()))
            ev.status(folder, status='FAILED', mode=mode, stage='failed', invocation=invocation.name)
            raise
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', required=True, choices=['native_qualification', 'outcome'])
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--resume', action='store_true')
    arguments = parser.parse_args()
    run(arguments.mode, arguments.output, arguments.resume)
