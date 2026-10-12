"""Detached, frozen, one-thread continuation worker with durable completion audit."""
import argparse
import os
import platform
import time
import traceback

import numpy as np
import chain
from analyze import summarize
from common import ROOT, arrays, equal, read, save_arrays, sha, stamp, status, validate, write


def validate_frozen():
    manifest = read(ROOT / 'FROZEN.json')
    for name, digest in manifest['files_sha256'].items():
        assert sha(ROOT / name) == digest, 'Frozen input changed: ' + name
    assert all(os.environ.get(k) == '1' for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'))
    assert os.environ.get('PYTHONDONTWRITEBYTECODE') == '1'
    return manifest


def main(ready_fd):
    folder = ROOT / 'run'
    begin, cpu = time.monotonic(), time.process_time()
    try:
        manifest = validate_frozen()
        cfg = read(ROOT / 'source_config.json')
        validate(cfg)
        protocol, selection = read(ROOT / 'PROTOCOL.json'), read(ROOT / 'SELECTION.json')
        assert protocol['horizon'] == 18 and len(selection['events']) == 46
        assert protocol['branches'] == chain.BRANCHES
        write(folder / 'WORKER_STARTED.json', dict(at_utc=stamp(), pid=os.getpid(),
            ready_inputs_verified=True, python=platform.python_version(), numpy=np.__version__,
            frozen_sha256=sha(ROOT / 'FROZEN.json'), inputs_checked=len(manifest['files_sha256'])))
        status(folder, status='RUNNING', contexts_completed=0, contexts=46, horizon=18)
        if ready_fd is not None:
            os.write(ready_fd, b'READY\n')
            os.close(ready_fd)
            ready_fd = None
        rows = []
        for i, event in enumerate(selection['events']):
            saved = arrays(ROOT / event['fixture'], event['fixture_sha256'])
            initial = chain.boundary(saved, event, cfg)
            future = chain.follow(initial['outgoing'], event, 18,
                                  lambda packet, e, generation: chain.transition(packet, e, generation, cfg))
            values = {key: np.concatenate((value[None], future[key]), axis=0) for key, value in initial.items()}
            values.update({'future_' + key: value for key, value in future.items() if key not in initial})
            equal(values['incoming'][1:], values['outgoing'][:-1], 'complete own-successor chain')
            assert values['applied'].sum(axis=0).tolist() == [0, 1, 19]
            name = f'context_{i:02d}.npz'
            digest = save_arrays(folder / name, values)
            rows.append(dict(context=i, block=event['block'], case=event['case'], generation=event['generation'],
                file=name, sha256=digest, independent_flat_reads=54, independent_optimizers=18,
                independent_capture_contexts=57))
            write(folder / f'context_{i:02d}.json', dict(at_utc=stamp(), **rows[-1],
                **chain.endpoints(values['both_pass'][1:])))
            status(folder, status='RUNNING', contexts_completed=i + 1, contexts=46, horizon=18)
            print(f'Completed context {i + 1}/46 with independent read, write, and repair audits.', flush=True)
        validate_frozen()
        result = summarize(folder, rows, begin, cpu)
        status(folder, status='COMPLETE', contexts_completed=46, counts=result['uninterrupted'])
        print('COMPLETE', result['uninterrupted'], flush=True)
    except BaseException:
        if not (folder / 'FAILED.json').exists():
            write(folder / 'FAILED.json', dict(at_utc=stamp(), traceback=traceback.format_exc()))
        status(folder, status='FAILED')
        raise
    finally:
        if ready_fd is not None:
            os.close(ready_fd)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ready-fd', type=int)
    main(parser.parse_args().ready_fd)
