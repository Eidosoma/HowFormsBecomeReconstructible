"""Pinned first-rewrite records; no old reader observations enter this assay."""
import hashlib
import io
import json
from pathlib import Path
import numpy as np
from common import dump, sha, utc
from E073_saved_cohort_reversal_replication.plan import HERE, ROOT, settings

FIELDS = ('incoming', 'outgoing', 'fallback', 'contrast', 'ordinary', 'masks')


def register():
    target = HERE / 'SOURCE_DATA.json'
    assert not target.exists()
    closepath = ROOT / 'E068_fresh_recovery_confirmation/analysis/closeout_v1.json'
    close = json.loads(closepath.read_text())
    assert close['status'] == 'PASS'
    known_path = ROOT / 'E072_single_pruning_persistence/analysis/closeout_v1.json'
    known = json.loads(known_path.read_text())
    assert known['status'] == 'PASS'
    predecessors = {str(closepath.relative_to(ROOT)): sha(closepath),
                    str(known_path.relative_to(ROOT)): sha(known_path)}
    known_run = ROOT / 'E072_single_pruning_persistence/runs/persistence_v1'
    for name, field in (('COMPLETE.json', 'complete_sha256'), ('INDEPENDENT_AUDIT.json', 'audit_sha256')):
        path = known_run / name
        assert sha(path) == known[field], path
        predecessors[str(path.relative_to(ROOT))] = sha(path)
    sources = {}
    for mode, name in (('fixture', 'fixture_v1'), ('benchmark', 'benchmark_v1'), ('scientific', 'confirmation_v1')):
        run = ROOT / 'E068_fresh_recovery_confirmation/runs' / name
        c = json.loads((run / 'COMPLETE.json').read_text())
        a = json.loads((run / 'INDEPENDENT_AUDIT.json').read_text())
        assert c['status'] == 'COMPLETE' and a['status'] == 'PASS' and a['controls_pass']
        assert a['complete_sha256'] == sha(run / 'COMPLETE.json')
        if mode == 'scientific':
            assert close['complete_sha256'] == sha(run / 'COMPLETE.json')
            assert close['audit_sha256'] == sha(run / 'INDEPENDENT_AUDIT.json')
        names = [f'boundary_{b:06d}_g1.npz' for b in settings(mode)['blocks']]
        for n in names:
            assert sha(run / n) == c['outputs_sha256'][n], n
        sources[mode] = dict(path=str(run.relative_to(ROOT)),
            receipts={str((run / n).relative_to(ROOT)): sha(run / n)
                      for n in ('COMPLETE.json', 'INDEPENDENT_AUDIT.json', 'manifest.json')},
            files={n: c['outputs_sha256'][n] for n in names},
            bytes=sum((run / n).stat().st_size for n in names))
    dump(target, dict(utc=utc(), predecessors=predecessors,
        sources=sources, E067_diagnosis_known=True, E068_outcomes_known=True, E069_outcomes_known=True, E070_outcomes_known=True, E071_outcomes_known=True, E072_outcomes_known=True,
        scientific_intervention_outcomes_seen=False, no_success_selection=True))


def verify_receipts(mode):
    reg = json.loads((HERE / 'SOURCE_DATA.json').read_text())
    for rel, digest in {**reg['predecessors'], **reg['sources'][mode]['receipts']}.items():
        assert sha(ROOT / rel) == digest, rel
    return reg['sources'][mode]


def source(mode, block):
    assert block in settings(mode)['blocks']
    reg = json.loads((HERE / 'SOURCE_DATA.json').read_text())['sources'][mode]
    name = f'boundary_{block:06d}_g1.npz'
    raw = (ROOT / reg['path'] / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == reg['files'][name], name
    with np.load(io.BytesIO(raw), allow_pickle=False) as z:
        out = {k: z[k] for k in FIELDS}
    assert out['incoming'].shape == out['outgoing'].shape == (5, 4, settings(mode)['recipients'], 4096)
    assert all(np.isfinite(x).all() for x in out.values())
    return out


def save(path, arrays):
    assert all(np.isfinite(x).all() for x in arrays.values())
    with Path(path).open('xb') as f:
        np.savez_compressed(f, **arrays)


def load(path):
    with np.load(path, allow_pickle=False) as z:
        out = {k: z[k] for k in z.files}
    assert all(np.isfinite(x).all() for x in out.values())
    return out


def equal(a, b):
    assert set(a) == set(b)
    for k in a:
        assert a[k].shape == b[k].shape and a[k].dtype == b[k].dtype, k
        assert a[k].tobytes() == b[k].tobytes(), k
