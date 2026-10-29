"""One H039 campaign: wait for engineering exit, verify, launch confirmation."""
from pathlib import Path
from datetime import datetime, timezone
import json
import os
import select
import subprocess
import sys
import time
import traceback

OUT = Path(__file__).resolve().parent
CONFIG = json.loads((OUT/'config.json').read_text())
LANE = Path(CONFIG['lane'])
sys.path.insert(0, str(LANE))
from h007.io import checksum, save, verify
from h038.workflow import capacity


def main():
    tick = time.perf_counter()
    status = dict(pid=os.getpid(), purpose='Verify engineering and launch H039 confirmation once')
    def progress(**kw):
        status.update(kw, updated_utc=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.perf_counter()-tick)
        save(OUT/'STATUS.json', status); print(json.dumps(status), flush=True)
    def check_sources():
        verify(OUT, 'freeze.json')
        for name, digest in CONFIG['source_sha256'].items():
            assert checksum(LANE/name) == digest, 'Source changed while queued: '+name
    try:
        check_sources()
        smoke = Path(CONFIG['smoke']); pid = CONFIG['smoke_pid']
        progress(state='WAITING_ENGINEERING', phase='await_engineering_exit', engineering_pid=pid)
        # A kernel exit notification, not a loop inspecting experiment outcomes.
        try:
            descriptor = os.pidfd_open(pid)
        except ProcessLookupError:
            descriptor = None
        if descriptor is not None:
            try:
                command = (Path('/proc')/str(pid)/'cmdline').read_bytes()
                assert str(smoke/'source/h039/workflow.py').encode() in command, 'Engineering PID changed'
                poller = select.poll(); poller.register(descriptor, select.POLLIN); poller.poll()
            finally:
                os.close(descriptor)
        complete = json.loads((smoke/'COMPLETE.json').read_text())
        assert complete['state'] == 'COMPLETE' and complete['integrity_passed']
        verify(smoke, 'checksums.json'); check_sources()
        capacity(OUT, 1, 'independent_verification', progress)
        progress(state='RUNNING', phase='independent_engineering_verification')
        result_path = LANE/'.cache/h039_smoke_closeout_v1.json'
        with (OUT/'closeout.log').open('xb') as stream:
            subprocess.run([sys.executable, '-B', str(LANE/'h039/closeout.py'), str(smoke), str(result_path)],
                cwd=LANE, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, check=True)
        checked = json.loads(result_path.read_text())
        assert checked['passed'] and checked['run_manifest_sha256'] == checksum(smoke/'checksums.json')
        check_sources()
        progress(state='RUNNING', phase='launch_confirmation')
        with (OUT/'confirmation_launch.log').open('xb') as stream:
            subprocess.run([sys.executable, '-B', str(LANE/'h039/workflow.py'), '--mode', 'confirmation', '--version', 'v1'],
                cwd=LANE, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, check=True)
        launch = json.loads((LANE/'runs/h039_confirmation_v1_launch.json').read_text())
        assert launch['detached']
        progress(state='HANDED_OFF', phase='confirmation_launched', confirmation_pid=launch['pid'],
            confirmation_run=launch['output'], forecast_seconds=launch['forecast_seconds'],
            engineering_verification=str(result_path))
        save(OUT/'HANDOFF.json', status)
    except BaseException:
        progress(state='FAILED', phase='stopped', error=traceback.format_exc())
        save(OUT/'FAILED.json', status)
        raise


if __name__ == '__main__':
    main()
