"""New-block registry and excluded archived projections; no old science inputs."""
import hashlib
import io
import json
from pathlib import Path
import numpy as np
from common import dump, sha, utc
from E068_fresh_recovery_confirmation.plan import HERE, ROOT, BLOCKS, TECH_BLOCK


def manifests():
    paths = set(ROOT.glob('E*/runs/*/manifest.json')) | set(ROOT.glob('E*/jobs/*/manifest.json'))
    return sorted(p for p in paths if not p.is_relative_to(HERE))


def register():
    target = HERE / 'SOURCE_DATA.json'
    assert not target.exists()
    prior, seen = {}, set()
    for p in manifests():
        blocks = json.loads(p.read_text()).get('contract', {}).get('blocks', [])
        if blocks:
            prior[str(p.relative_to(ROOT))] = sha(p)
            seen.update(blocks)
    assert not seen.intersection(BLOCKS) and TECH_BLOCK not in BLOCKS
    predecessors = {}
    for name in ('E065_fresh_compatibility_confirmation', 'E067_ordinary_mixture_rebuilding'):
        p = ROOT / name / 'analysis/closeout_v1.json'
        c = json.loads(p.read_text())
        assert c['status'] == 'PASS'
        predecessors[str(p.relative_to(ROOT))] = sha(p)
    technical = {}
    names = ['acquisition_900041.npz', 'body_900041.npz', 'outgoing_900041.npz',
             'source_900041.npz', 'interventions_900041.npz']
    names += [f'source_boundary_900041_g{g}.npz' for g in range(1, 33)]
    names += [f'continuation_900041_g{g}.npz' for g in range(1, 4)]
    for mode in ('fixture', 'benchmark'):
        run = ROOT / 'E065_fresh_compatibility_confirmation/runs' / f'{mode}_v1'
        c = json.loads((run / 'COMPLETE.json').read_text())
        a = json.loads((run / 'INDEPENDENT_AUDIT.json').read_text())
        assert c['status'] == 'COMPLETE' and a['status'] == 'PASS'
        assert a['complete_sha256'] == sha(run / 'COMPLETE.json')
        for n in names:
            assert sha(run / n) == c['outputs_sha256'][n], n
        technical[mode] = dict(path=str(run.relative_to(ROOT)),
            receipts={str((run / n).relative_to(ROOT)): sha(run / n)
                for n in ('COMPLETE.json', 'INDEPENDENT_AUDIT.json', 'manifest.json')},
            files={n: c['outputs_sha256'][n] for n in names})
    dump(target, dict(utc=utc(), blocks=list(BLOCKS), excluded_block=TECH_BLOCK,
        prior_manifest_sha256=prior, prior_block_ids=sorted(seen), predecessors=predecessors,
        technical_references=technical, E067_outcomes_known=True,
        old_scientific_cases_pooled=False, scientific_outcomes_seen=False))


def verify_receipts(mode):
    reg = json.loads((HERE / 'SOURCE_DATA.json').read_text())
    seen = set()
    for rel, digest in reg['prior_manifest_sha256'].items():
        assert sha(ROOT / rel) == digest, rel
        seen.update(json.loads((ROOT / rel).read_text())['contract']['blocks'])
    assert sorted(seen) == reg['prior_block_ids'] and not seen.intersection(BLOCKS)
    assert reg['blocks'] == list(BLOCKS) and reg['excluded_block'] == TECH_BLOCK
    # Catch a conflicting newly reserved external run as well as the pinned past.
    for p in manifests():
        assert not set(json.loads(p.read_text()).get('contract', {}).get('blocks', [])).intersection(BLOCKS), str(p)
    for rel, digest in reg['predecessors'].items():
        assert sha(ROOT / rel) == digest, rel
    if mode != 'scientific':
        for rel, digest in reg['technical_references'][mode]['receipts'].items():
            assert sha(ROOT / rel) == digest, rel


def reference(mode, name):
    assert mode in ('fixture', 'benchmark'), 'Old source records are technical references only'
    entry = json.loads((HERE / 'SOURCE_DATA.json').read_text())['technical_references'][mode]
    raw = (ROOT / entry['path'] / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == entry['files'][name], name
    with np.load(io.BytesIO(raw), allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def technical_source(mode):
    previous = reference(mode, 'source_900041.npz')
    return {k: previous[k] for k in ('initial', 'final')}


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
    assert set(a) == set(b), (set(a) - set(b), set(b) - set(a))
    for k in a:
        assert a[k].shape == b[k].shape and a[k].dtype == b[k].dtype, k
        assert a[k].tobytes() == b[k].tobytes(), k
