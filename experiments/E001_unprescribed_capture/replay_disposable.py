"""Exact full-configuration replay of the retained disposable benchmark."""
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from common import cap_cpus, check_inputs, dump, sha
from model import checks, simulate
import numpy as np

cap_cpus()
run=HERE/"runs/benchmark_v1"
check_inputs(run)
started=time.monotonic()
replayed=simulate(900001,"homogeneous")
with np.load(run/"block_900001_homogeneous.npz",allow_pickle=False) as saved:
    assert set(saved.files)==set(replayed)
    for key in replayed:
        np.testing.assert_array_equal(replayed[key],saved[key])
result=dict(status="PASS",all_arrays_exact=len(replayed),seconds=time.monotonic()-started,
            source_code_sha256=sha(HERE/"model.py"),replay_script_sha256=sha(__file__),
            complete_sha256=sha(run/"COMPLETE.json"),checks=checks(replayed))
path=run/"EXACT_REPLAY.json"
if path.exists():raise FileExistsError(path)
dump(path,result)
print(json.dumps(result,indent=2))
