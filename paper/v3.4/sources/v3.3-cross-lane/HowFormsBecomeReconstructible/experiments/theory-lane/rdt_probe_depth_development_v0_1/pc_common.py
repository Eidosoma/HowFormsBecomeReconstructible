"""Explicit sources and exact native interfaces for retained-cohort development."""
from datetime import datetime, timezone
import csv
import hashlib
import json
import os
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parent
LANE = ROOT.parent
OLD = LANE / 'rdt_fresh_equal_read_v0_1'
NATIVE_INPUTS = OLD / 'jobs/qualification_v1/inputs'
RUN = OLD / 'runs/scientific_v1'
REPORT = LANE / 'rdt_fresh_equal_read_reporting_v0_1'
PRICING = LANE / 'rdt_probe_depth_cost_v0_1/amendment_v2'
PRICE_REPORT = LANE / 'rdt_probe_depth_cost_v0_1/reporting_v2/results_v1'
INPUT_SHA = '5b6f74510e7fcb26e81a86d62c886d532607fba24d07b7d67868ce3e617f3dea'
REPORT_SHA = 'c8f07f6be55b52078a76d27613f99aed028fca692eed64f3d4cfc99c74172901'
REGIMES = ('matched', 'independent')
PROFILES = ('balanced','balanced_fail','balanced_pass','population','population_fail','population_pass')
LEGACY = ('successor32','direct64','pooled32','direct8','tt008')
ORDINARY = ('class_history','boundary','cheap_all','no_body_expression')
FAMILIES = (*ORDINARY, 'direct8', 'depth0', 'depth1', 'depth2')
OLD_STAGE = 'equal_read_fresh_v1'
STAGES = {scope: 'rdt_probe_depth_development_v0_1/' + scope + '_writer_2' for scope in ('qualification','development')}
_NATIVE = None


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


def utc():
    return datetime.now(timezone.utc).isoformat()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def csv_rows(path):
    with Path(path).open() as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    require(bool(rows), 'Nonempty table')
    with Path(path).open('x', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def row_key(row):
    return int(row['block']), row['history'], int(row['founder']), int(row['recipient'])


def native():
    global _NATIVE
    if _NATIVE is None:
        require(sha(NATIVE_INPUTS/'INPUTS.json') == INPUT_SHA, 'Frozen native input manifest')
        for name, digest in read(NATIVE_INPUTS/'INPUTS.json')['sha256'].items():
            require(sha(NATIVE_INPUTS/name) == digest, 'Changed native input: ' + name)
        sys.path.insert(0, str(NATIVE_INPUTS))
        import ff_common, fast_reader, probes
        ff_common.configure('scientific')
        _NATIVE = ff_common, fast_reader, probes
    return _NATIVE


def cheap():
    for item in read(ROOT/'COMPARATOR_BINDING.json')['files'].values():
        require(sha(ROOT/item['local']) == item['sha256'], 'Comparator source changed')
    sys.path.insert(0, str(ROOT/'comparator'))
    import features, models
    return features, models


def save_arrays(path, arrays):
    require(all(np.isfinite(a).all() for a in arrays.values()), 'Finite exact arrays')
    index = {k: dict(shape=list(a.shape), dtype=a.dtype.str, sha256=hashlib.sha256(a.tobytes()).hexdigest())
             for k, a in arrays.items()}
    with Path(path).open('xb') as f:
        np.savez_compressed(f, **arrays, __index__=np.frombuffer(json.dumps(index,sort_keys=True).encode(),np.uint8))
    return sha(path)


def load_arrays(path, expected):
    require(sha(path) == expected, 'Native array archive identity: ' + str(path))
    with np.load(path, allow_pickle=False) as z:
        index = json.loads(z['__index__'].tobytes())
        require(set(z.files) == set(index) | {'__index__'}, 'Array index coverage')
        out = {name:z[name] for name in index}
    for name,a in out.items():
        require(dict(shape=list(a.shape),dtype=a.dtype.str,sha256=hashlib.sha256(a.tobytes()).hexdigest()) == index[name],
                'Native array contents: ' + name)
        require(np.isfinite(a).all(), 'Finite arrays')
    return out


def verify_freeze():
    freeze = read(ROOT/'FREEZE.json')
    for name,h in freeze['files_sha256'].items():
        require(sha(ROOT/name) == h, 'Frozen development source changed: ' + name)
    prepared = read(ROOT/'prepared/SOURCES.json')
    for name,h in prepared['output_files_sha256'].items():
        require(sha(ROOT/'prepared'/name) == h, 'Prepared interface changed: ' + name)
    return sha(ROOT/'FREEZE.json')
