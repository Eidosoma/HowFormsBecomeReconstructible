"""D185 fresh-process saved-output readback; no dynamics and no new metrics."""

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import time

import numpy as np

ROOT = Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L22-active-form-trace-v1')
BLOCKS = (30056, 30057, 30058, 30059)


def read(path): return json.loads(path.read_text())


def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def audit():
    tick = time.monotonic()
    assert set(os.sched_getaffinity(0)) == {6} and os.getpriority(os.PRIO_PROCESS, 0) >= 10
    assert os.environ['OPENBLAS_NUM_THREADS'] == '1'
    done, freeze = read(ROOT/'COMPLETE.json'), read(ROOT/'FREEZE.json')
    assert done['status'] == 'COMPLETE' and done['new_dynamics'] == 0
    assert done['freeze_sha256'] == sha(ROOT/'FREEZE.json')
    assert done['manifest_sha256'] == sha(ROOT/'MANIFEST.json')
    assert read(ROOT/'MANIFEST.json')['freeze_sha256'] == sha(ROOT/'FREEZE.json')
    for p, digest in freeze['inputs'].items(): assert sha(p) == digest, p
    for p, digest in done['output_sha256'].items(): assert sha(p) == digest, p
    assert set(done['output_sha256']) == {str(p) for p in (ROOT/'outputs').iterdir()}
    s = read(ROOT/'outputs/SUMMARY.json')
    assert s['blocks'] == list(BLOCKS) and s['records'] == 64 and not s['confirmation']
    assert s['new_dynamics'] == s['fitted_models'] == 0
    assert s['fields'] == freeze['fields'] and len(s['fields']) == 13
    values = {}
    for b in BLOCKS:
        with np.load(ROOT/f'outputs/tissue_{b}.npz', allow_pickle=False) as z:
            assert set(z.files) == set(s['metrics']) and len(z.files) == 1611
            values[b] = {k: z[k] for k in z.files}
    comparisons, maximum = 0, 0.
    for key, reported in s['metrics'].items():
        for b in BLOCKS:
            assert values[b][key].shape == (16, 13) and np.isfinite(values[b][key]).all()
        for block in (None, *range(4)):
            bs = BLOCKS if block is None else (BLOCKS[block],)
            for message in (None, *range(4)):
                worlds = range(16) if message is None else range(4*message, 4*message+4)
                if block is message is None: actual = reported['mean']
                elif block is None: actual = reported['by_message'][message]
                elif message is None: actual = reported['by_block'][block]
                else: actual = reported['by_block_message'][block][message]
                for j in range(13):
                    expected = math.fsum(float(values[b][key][w, j]) for b in bs for w in worlds)/(len(bs)*len(worlds))
                    error = abs(expected-actual[j])
                    assert error < 2e-12, (key, block, message, j)
                    maximum = max(maximum, error); comparisons += 1
    return dict(status='PASS', completed_utc=datetime.now(timezone.utc).isoformat(),
                seconds=time.monotonic()-tick, input_hashes=len(freeze['inputs']), output_hashes=5,
                arrays=4*1611, summary_scalar_comparisons=comparisons, summary_max_abs=maximum,
                complete_sha256=sha(ROOT/'COMPLETE.json'), freeze_sha256=sha(ROOT/'FREEZE.json'),
                checker_sha256=sha(__file__), new_dynamics=0, automatic_successor=False)


if __name__ == '__main__':
    receipt = ROOT/'SAVED_CHECK.json'
    assert not receipt.exists(), 'retain earlier audit'
    result = audit()
    with receipt.open('x') as stream: json.dump(result, stream, sort_keys=True, indent=2)
    print(json.dumps(result, indent=2))
