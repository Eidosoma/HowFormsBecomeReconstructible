"""Pinned archives, exact byte comparisons and append-only result files."""
import csv
import io
import json
from pathlib import Path
import numpy as np
from common import dump, sha, utc
from E116_finite_resolution_pruning.plan import HERE, ROOT, COPIES


def equal(a, b, label=''):
    assert a.shape == b.shape and a.dtype == b.dtype, (label, a.shape, b.shape, a.dtype, b.dtype)
    assert a.tobytes() == b.tobytes(), (label, float(np.max(np.abs(a.astype(float)-b.astype(float)))))


def save(path, arrays):
    assert all(np.isfinite(v).all() for v in arrays.values())
    with Path(path).open('xb') as f:
        np.savez_compressed(f, **arrays)


def load(path):
    with np.load(path, allow_pickle=False) as z:
        out = {k: z[k] for k in z.files}
    assert all(np.isfinite(v).all() for v in out.values())
    return out


def registry(mode=None, full=False):
    reg = json.loads((HERE/'SOURCE_DATA.json').read_text())
    for rel, h in reg['receipts'].items():
        assert sha(ROOT/rel) == h, rel
    if full:
        for label, source in reg['sources'].items():
            if mode is not None and label != mode: continue
            for name, info in source['files'].items():
                p = ROOT/source['path']/name
                assert p.stat().st_size == info['bytes'] and sha(p) == info['sha256'], str(p)
    return reg


def register():
    target = HERE/'SOURCE_DATA.json'; assert not target.exists()
    draft = json.loads((HERE/'planning/SOURCE_INVENTORY.json').read_text())
    receipts = {}
    for source in draft['sources'].values():
        p = ROOT/source['path']/'COMPLETE.json'
        assert sha(p) == source['complete_sha256']
        c = json.loads(p.read_text()); assert c['status'] == 'COMPLETE' and c['controls_pass']
        receipts[str(p.relative_to(ROOT))] = sha(p)
        manifest = p.parent/'manifest.json'
        assert sha(manifest) == c['outputs_sha256']['manifest.json']
        receipts[str(manifest.relative_to(ROOT))] = sha(manifest)
        for name, info in source['files'].items():
            item = p.parent/name
            assert sha(item) == info['sha256'] == c['outputs_sha256'][name], name
            assert item.stat().st_size == info['bytes']
    close = ROOT/'E112_fresh_component_prediction/analysis/closeout_v1.json'
    assert sha(close) == draft['closeout_sha256'] and json.loads(close.read_text())['status'] == 'PASS'
    receipts[str(close.relative_to(ROOT))] = sha(close)
    dump(target, dict(utc=utc(), sources=draft['sources'], receipts=receipts,
        all_source_files_rehashed=True, all_cases_retained=True, finite_outcomes_seen=False,
        planning_inventory_sha256=sha(HERE/'planning/SOURCE_INVENTORY.json')))


def source(mode, name):
    s = registry()['sources'][mode]; p = ROOT/s['path']/name
    raw = p.read_bytes()
    import hashlib
    assert hashlib.sha256(raw).hexdigest() == s['files'][name]['sha256'], name
    if name.endswith('.npz'):
        with np.load(io.BytesIO(raw), allow_pickle=False) as z: return {k:z[k] for k in z.files}
    return raw


def source_settings(mode):
    s = registry()['sources'][mode]
    return json.loads((ROOT/s['path']/'manifest.json').read_text())['contract']


def export(path, rows):
    assert rows
    fields = list(rows[0]); assert all(list(r) == fields for r in rows)
    with Path(path).open('x', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)


def copy_tables(mode, run):
    for name in COPIES:
        raw = source(mode, name)
        with (run/('source_'+name)).open('xb') as f: f.write(raw)


def original_rows(mode):
    rows = list(csv.DictReader(io.StringIO(source(mode,'original_cases.csv').decode())))
    return {tuple(int(r[k]) for k in ('task','arm','founder','recipient','draw')):r for r in rows}
