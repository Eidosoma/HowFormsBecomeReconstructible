"""One host resource sample for a single-thread saved-data analysis."""
import argparse
import os
import shutil
import time
from common import *


def sample():
    result = {}
    for p in Path('/proc').glob('[0-9]*'):
        if int(p.name) == os.getpid(): continue
        try:
            argv = (p/'cmdline').read_bytes().split(b'\0')
            if not argv or 'python' not in Path(argv[0].decode(errors='replace')).name: continue
            if '/home/robert/Random-Replications' not in str((p/'cwd').resolve()): continue
            for task in (p/'task').iterdir():
                fields = (task/'stat').read_text().rsplit(')',1)[1].split()
                result[task.name] = dict(pid=int(p.name), state=fields[0], ticks=int(fields[11])+int(fields[12]))
        except (OSError, ValueError): pass
    return result


def main(name='RESOURCE_CHECK.json'):
    assert len(list(Path('/proc').glob('[0-9]*'))) > 16, 'host namespace required for admission'
    a = sample(); time.sleep(1); b = sample()
    active = {k for k,v in b.items() if v['state']=='R' or (k in a and v['ticks']>a[k]['ticks'])}
    active |= {k for k,v in a.items() if v['state']=='R'}
    receipt = dict(recorded_utc=now(), active_project_threads=len(active), planned_workers=1,
        numerical_threads=1, ceiling=12, cpu=sorted(os.sched_getaffinity(0))[-1],
        free_bytes=shutil.disk_usage(ROOT).free, admission_pass=len(active)+1<=12 and shutil.disk_usage(ROOT).free>=2*1024**3,
        no_scientific_outputs_inspected=True)
    write_json(ROOT/name, receipt)
    print(receipt, flush=True)
    assert receipt['admission_pass']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--name', default='RESOURCE_CHECK.json')
    main(parser.parse_args().name)
