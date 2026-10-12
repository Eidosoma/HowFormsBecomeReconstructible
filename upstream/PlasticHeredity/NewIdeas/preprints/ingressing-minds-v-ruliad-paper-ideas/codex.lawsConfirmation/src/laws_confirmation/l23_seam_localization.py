"""D083: locate composition error in saved D082 fields; never simulate."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

import numpy as np

from . import l23_layout_transfer as source
from .io import (atomic_text, canonical_digest, environment_manifest, external_root,
                 require_beneath, sha256_file, utc_now, write_hash_manifest)

RUN_ID = 'l23_seam_localization_v1_attempt1'
TIMES = (0, 1, 50, 150, 300)
BANDS = ('all', 'seam', 'interior', 'distance_0', 'distance_1', 'distance_2', 'distance_3')
ERRORS = ('standardized_squared_error', 'alignment_shortfall', 'raw_squared_error', 'sign_error')
KINDS = ('checker_whole_excess', 'checker_seam_minus_interior',
         'layout_change_whole_excess', 'layout_change_seam_minus_interior')
SCIENTIFIC_FILES = ('src/laws_confirmation/l23_seam_localization.py',
                    'scripts/audit_l23_seam_localization_outputs.py',
                    'tests/test_l23_seam_localization.py',
                    'scripts/run_l23_seam_localization.sh',
                    'protocols/L23_SEAM_LOCALIZATION_V1.md')
strict_json = source.strict_json


def checker():
    path = Path(__file__).resolve().parents[2]/SCIENTIFIC_FILES[1]
    spec = importlib.util.spec_from_file_location('d083_independent_checker', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def geometry(mask):
    assert mask.shape == (16, 16) and mask.dtype == bool
    seam = np.zeros_like(mask)
    for axis in (0, 1):
        for shift in (-1, 1):
            seam |= mask != np.roll(mask, shift, axis=axis)
    distance = np.full(mask.shape, -1, dtype=np.int64)
    distance[seam] = 0
    for depth in range(1, 16):
        new = np.zeros_like(mask)
        for axis in (0, 1):
            for shift in (-1, 1):
                new |= ((np.roll(distance, shift, axis=axis) == depth-1)
                        & (mask == np.roll(mask, shift, axis=axis)))
        distance[new & (distance < 0)] = depth
        if (distance >= 0).all():
            break
    if (distance < 0).any() or distance.max() > 3:
        raise ValueError('unexpected or missing seam geometry')
    bands = np.stack((np.ones_like(mask), distance == 0, distance >= 1,
                      *(distance == d for d in range(4))))
    counts = np.stack([np.sum(bands & h, axis=(1, 2)) for h in (mask, ~mask)])
    assert np.all(counts[:, 0] == 128) and np.all(counts[:, :3] > 0)
    return distance, bands, counts


def standardized(values):
    centered = values-values.mean(axis=-1, keepdims=True)
    scale = np.sqrt(np.square(centered).mean(axis=-1, keepdims=True))
    active = scale[..., 0] > 0
    return np.divide(centered, scale, out=np.zeros_like(centered), where=scale > 0), active


def statistics(v, forms, mask):
    assert v.ndim == 6 and v.shape[:3] == (12, 3, 7) and v.shape[-2:] == (16, 16)
    assert np.isfinite(v).all() and np.isfinite(forms).all()
    distance, bands, counts = geometry(mask)
    values = np.zeros((12, 3, 8, v.shape[3], 2, 7, 4))
    active = np.zeros((12, 3, 8, v.shape[3], 2, 2), dtype=np.uint8)
    for h, region in enumerate((mask, ~mask)):
        actual = v[..., region]
        target = np.stack([forms[ord(p[h])-65, region] for p in source.PAIRS])[:, None, None, None, :]
        zv, av = standardized(actual)
        zf, af = standardized(target)
        fields = (.5*np.square(zv-zf), 1-zv*zf, np.square(actual-target),
                  (actual > 0) != (target > 0))
        active[:, :, :7, :, h, 0] = av
        active[:, :, :7, :, h, 1] = np.broadcast_to(af, av.shape)
        for b, band in enumerate(bands):
            selected = band[region]
            if counts[h, b]:
                for m, field in enumerate(fields):
                    values[:, :, :7, :, h, b, m] = field[..., selected].mean(axis=-1)
    for h, r in ((0, 2), (1, 3)):
        values[:, :, 7, :, h] = values[:, :, r, :, h]
        active[:, :, 7, :, h] = active[:, :, r, :, h]
    return dict(values=values, active=active, distance=distance, counts=counts)


def score_panel(directory, canonical_forms, g, n, old_metrics, check):
    # Only declared saved V entries are loaded. No engine/context/replay calls.
    forms = source.transport(canonical_forms, source.layout_maps()[g])
    canonical_mask = np.indices((16, 16))[1] < 8
    mask = source.transport(canonical_mask, source.layout_maps()[g])
    rows = []
    with np.load(directory/f'panel_{g}_{n}.npz', allow_pickle=False) as raw:
        np.testing.assert_array_equal(raw['case_ids'],
            np.array([(p, b, r) for p in range(12) for b in range(3) for r in range(7)]))
        for t in TIMES:
            v = raw[f's{t}_V'].reshape(12, 3, 7, -1, 16, 16)
            row = statistics(v, forms, mask)
            assert check.check_snapshot(v, canonical_forms, g, row)
            if t == 300:
                assert check.check_endpoint(row['values'], old_metrics)
            rows.append(row)
    return dict(values=np.stack([r['values'] for r in rows]),
                active=np.stack([r['active'] for r in rows]),
                distance=rows[0]['distance'], counts=rows[0]['counts'])


def summary_of(blocks):
    means = sum(x.mean(axis=6) for x in blocks)/len(blocks)
    excess = np.stack([(x[:, :, :, :, :, 1]-x[:, :, :, :, :, 7]).mean(axis=(5, 6)) for x in blocks])
    return dict(means=means, composition_block_means=excess)


def describe(draws):
    blocks = draws.mean(axis=(1, 2))
    result = dict(mean=float(blocks.mean()), minimum=float(blocks.min()), maximum=float(blocks.max()),
                  block_means=blocks.tolist(), pair_means=draws.mean(axis=(0, 2)).tolist())
    for prefix, v in (('', blocks), ('paired_', draws)):
        result.update({prefix+'positive': int((v > 1e-12).sum()),
                       prefix+'tied': int((abs(v) <= 1e-12).sum()),
                       prefix+'negative': int((v < -1e-12).sum())})
    return result


def focal_of(blocks):
    rows = []
    for n, norm in enumerate(source.NORMS):
        # Keep block/layout/pair/start/band; average the two regions, not starts.
        values = np.stack([(x[:, n, -1, :, 1, 1, :, :, :, 0]
                           -x[:, n, -1, :, 1, 7, :, :, :, 0]).mean(axis=3) for x in blocks])
        for kind, label in enumerate(KINDS):
            v = values[:, 2]-values[:, 0] if kind >= 2 else values[:, 2]
            draws = v[..., 1]-v[..., 2] if kind % 2 else v[..., 0]
            rows.append(dict(norm=norm, kind=kind, label=label, **describe(draws)))
    return rows


def contract():
    return dict(run_id=RUN_ID, decision='D083', law='L23', source_run=source.RUN_ID,
        tissues=list(source.TISSUES), layouts=list(source.LAYOUTS), norms=list(source.NORMS),
        times=list(TIMES), pairs=list(source.PAIRS), budgets=list(source.BUDGETS),
        measured=list(source.MEASURED), bands=list(BANDS), errors=list(ERRORS),
        groups={name: list(pairs) for name, pairs in source.GROUPS.items()},
        draws=8, region_cells=128, focal_labels=list(KINDS), focal_endpoints=8,
        focal_budget='matched', focal_time=300, focal_group='all', focal_error=ERRORS[0],
        value_axes='layout,norm,time,pair,budget,measured,start,region,band,error',
        active_axes='layout,norm,time,pair,budget,measured,start,region,V_or_template',
        means_axes='layout,norm,time,pair,budget,measured,region,band,error',
        composition_block_axes='block,layout,norm,time,pair,budget,band,error',
        empty_shell_mean=0, empty_shells_are_missing=True, rotation_atol=1e-10,
        new_simulation_lives=0, dynamics_replays=0, outcome_informed=True,
        causal_seam_mechanism_identified=False, output_hashes=20, workers=1,
        reserve_bytes=5*1024**3, projected_output_allowance_bytes=1024**3)


def input_paths(root):
    directory = root/'outputs'/source.RUN_ID
    paths = []
    for name in ('input_hashes.sha256', 'output_hashes.sha256'):
        path = directory/name
        paths.append(path)
        paths.extend(Path(line.split('  ', 1)[1]) for line in path.read_text().splitlines())
    paths += [root/'runs'/source.RUN_ID/p for p in ('MANIFEST.json', 'STATUS.json', 'COMPLETE')]
    ws = Path(__file__).resolve().parents[2]
    paths += [ws/p for p in (*SCIENTIFIC_FILES, 'reviews/L23_LAYOUT_TRANSFER_2026-09-09.md')]
    return sorted(set(p.resolve() for p in paths))


def source_verified(root):
    directory = root/'outputs'/source.RUN_ID
    for name, count in (('input_hashes.sha256', 270), ('output_hashes.sha256', 181)):
        assert source.old.checker().check_hashes(directory/name) == count
    run = root/'runs'/source.RUN_ID
    status = json.loads((run/'STATUS.json').read_text())
    assert status['status'] == 'COMPLETE' and status['verified_saved_analysis'] is True
    assert (run/'COMPLETE').is_file() and not (run/'FAILED').exists()
    data = json.loads((directory/'analysis.json').read_text())
    for key, value in source.contract().items():
        assert canonical_digest(data[key]) == canonical_digest(value), key
    assert data['completed_cleanly'] and data['verified_saved_analysis'] and data['calibration_qualified']
    verification = json.loads((directory/'verification.json').read_text())
    assert verification['passes'] and verification['pooled_verified']
    return data


def preflight(root):
    cpus = source.preflight(root)
    if shutil.disk_usage(root).free < 5*1024**3:
        raise RuntimeError('five GiB required: four reserve plus one audit allowance')
    return cpus


def timing_path(root):
    return root/'tmp'/f'{RUN_ID}_benchmark.json'


def benchmark(root):
    cpus = preflight(root)
    path = timing_path(root)
    if path.exists():
        raise FileExistsError('immutable benchmark already exists')
    tick = time.monotonic()
    data = source_verified(root)
    paths = input_paths(root)
    hashes = {str(p): sha256_file(p) for p in paths}
    hashing = time.monotonic()-tick
    directory = root/'outputs'/source.RUN_ID/'tissue_31016'
    assert data['results'][0]['tissue'] == 31016
    with np.load(directory/'instruments.npz', allow_pickle=False) as f:
        forms = f['forms']
    tick = time.monotonic()
    row = score_panel(directory, forms, 0, 0, np.array(data['results'][0]['metrics'])[0, 0], checker())
    elapsed = time.monotonic()-tick
    assert np.isfinite(row['values']).all()
    assert hashes == {str(p): sha256_file(p) for p in paths}
    forecast = 96*elapsed+2*hashing+120
    record = dict(run_id=RUN_ID, passed=True, completed_utc=utc_now(), effects_not_reported=True,
        source_panel=[31016, 0, 0], checked_snapshots=5, panel_seconds=elapsed, hash_seconds=hashing,
        projected_seconds=forecast, must_detach=forecast > 600, cpu_affinity=cpus, input_sha256=hashes)
    strict_json(path, record, root)
    print(json.dumps({k: v for k, v in record.items() if k != 'input_sha256'}, indent=2), flush=True)
    return record


def prepare(root):
    run, out = root/'runs'/RUN_ID, root/'outputs'/RUN_ID
    if run.exists() or out.exists():
        raise FileExistsError('immutable run already exists')
    cpus = preflight(root)
    timing = json.loads(timing_path(root).read_text())
    hashes = {str(p): sha256_file(p) for p in input_paths(root)}
    assert timing['run_id'] == RUN_ID and timing['passed'] and timing['effects_not_reported']
    assert timing['source_panel'] == [31016, 0, 0] and timing['checked_snapshots'] == 5
    assert timing['input_sha256'] == hashes
    assert timing['panel_seconds'] > 0 and timing['hash_seconds'] > 0
    assert timing['projected_seconds'] == 96*timing['panel_seconds']+2*timing['hash_seconds']+120
    assert timing['must_detach'] is (timing['projected_seconds'] > 600)
    hashes[str(timing_path(root))] = sha256_file(timing_path(root))
    manifest = contract() | dict(prepared_utc=utc_now(), input_sha256=hashes,
        hash_contract=canonical_digest(hashes), timing=timing, cpu_affinity=cpus, environment=environment_manifest())
    run.mkdir(parents=True)
    out.mkdir(parents=True)
    strict_json(run/'MANIFEST.json', manifest, root)
    write_hash_manifest([Path(p) for p in hashes], out/'input_hashes.sha256', root)
    strict_json(run/'STATUS.json', dict(status='PREPARED', run_id=RUN_ID), root)
    print(json.dumps(dict(status='PREPARED', input_hashes=len(hashes), estimated_seconds=timing['projected_seconds'])), flush=True)
    return manifest


def verify(root):
    run = root/'runs'/RUN_ID
    manifest = json.loads((run/'MANIFEST.json').read_text())
    assert json.loads((run/'STATUS.json').read_text())['status'] == 'PREPARED'
    assert not (run/'COMPLETE').exists() and not (run/'FAILED').exists()
    for key, value in contract().items():
        assert canonical_digest(manifest[key]) == canonical_digest(value), key
    hashes = manifest['input_sha256']
    assert set(hashes) == {str(p) for p in input_paths(root)+[timing_path(root)]}
    assert canonical_digest(hashes) == manifest['hash_contract']
    assert all(sha256_file(Path(p)) == digest for p, digest in hashes.items())
    assert manifest['timing'] == json.loads(timing_path(root).read_text())
    return manifest


def detach(root):
    if not (root/'runs'/RUN_ID).exists():
        prepare(root)
    manifest = verify(root)
    run = root/'runs'/RUN_ID
    (run/'LAUNCH.lock').mkdir()
    logs = [root/'logs'/f'{RUN_ID}.{kind}.log' for kind in ('stdout', 'stderr')]
    with logs[0].open('xb') as out, logs[1].open('xb') as err:
        child = subprocess.Popen([sys.executable, '-m', 'laws_confirmation.l23_seam_localization',
            '--external-root', str(root), '--run'], cwd=Path(__file__).resolve().parents[2],
            stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True)
    record = dict(run_id=RUN_ID, pid=child.pid, launched_utc=utc_now(), polling_owner='user',
        estimated_seconds=manifest['timing']['projected_seconds'], status=str(run/'STATUS.json'),
        stdout_log=str(logs[0]), stderr_log=str(logs[1]))
    strict_json(run/'LAUNCH.json', record, root)
    atomic_text(run/'RUN.pid', str(child.pid)+'\n', root)
    print(json.dumps(record, indent=2), flush=True)
    return record


def run_audit(root):
    manifest = verify(root)
    run, out = root/'runs'/RUN_ID, root/'outputs'/RUN_ID
    if manifest['timing']['must_detach'] and not (run/'LAUNCH.lock').is_dir():
        raise RuntimeError('detached execution required above ten minutes')
    (run/'EXECUTION.lock').mkdir()
    start = time.monotonic()
    try:
        preflight(root)
        data = source_verified(root)
        check = checker()
        blocks, active_counts, rotations = [], [], []
        distances, band_counts = [], []
        for i, tissue in enumerate(source.TISSUES):
            directory = root/'outputs'/source.RUN_ID/f'tissue_{tissue}'
            old = np.array(data['results'][i]['metrics'])
            assert data['results'][i]['tissue'] == tissue
            with np.load(directory/'instruments.npz', allow_pickle=False) as f:
                forms = f['forms']
            panels = [[score_panel(directory, forms, g, n, old[g, n], check) for n in range(2)] for g in range(3)]
            values = np.array([[p['values'] for p in group] for group in panels])
            active = np.array([[p['active'] for p in group] for group in panels])
            counts = np.array([group[0]['counts'] for group in panels])
            distance = np.array([group[0]['distance'] for group in panels])
            rotations.append(check.check_block(values, active, counts))
            if distances:
                np.testing.assert_array_equal(distance, distances[0])
                np.testing.assert_array_equal(counts, band_counts[0])
            distances.append(distance)
            band_counts.append(counts)
            payload = dict(values=values, active=active, distance=distance, counts=counts, available=counts > 0)
            source.base.atomic_npz(out/f'tissue_{tissue}.npz', payload, root)
            with np.load(out/f'tissue_{tissue}.npz', allow_pickle=False) as saved:
                for key in payload:
                    np.testing.assert_array_equal(saved[key], payload[key])
            active_counts.append(dict(tissue=tissue, inactive_V=int((active[..., 0] == 0).sum()),
                                      inactive_template=int((active[..., 1] == 0).sum())))
            blocks.append(values)
            strict_json(run/'STATUS.json', dict(status='RUNNING', run_id=RUN_ID, checked_blocks=i+1,
                checked_snapshot_batches=30*(i+1), updated_utc=utc_now()), root)
            print(f'D083 saved snapshots independently checked: block {tissue}', flush=True)
        summary = summary_of(blocks)
        focal = focal_of(blocks)
        assert check.check_summary(blocks, summary, focal)
        source.base.atomic_npz(out/'summary.npz', summary, root)
        with np.load(out/'summary.npz', allow_pickle=False) as saved:
            assert check.check_summary(blocks, dict(saved), focal)
        analysis = contract() | dict(completed_utc=utc_now(), passes=True, focal=focal,
            counts=band_counts[0].tolist(), available=(band_counts[0] > 0).tolist(), inactive_counts=active_counts,
            isometry_max_abs_difference=max(rotations), source_outcomes_reused=True)
        strict_json(out/'analysis.json', analysis, root)
        assert check.check_summary(blocks, summary, json.loads((out/'analysis.json').read_text())['focal'])
        assert all(sha256_file(Path(p)) == digest for p, digest in manifest['input_sha256'].items())
        verification = dict(passes=True, snapshot_batches=480, endpoint_batches=96,
            independently_checked_statistics=True, independently_checked_pool=True,
            source_hashes_unchanged=True, input_hashes=len(manifest['input_sha256']),
            isometry_max_abs_difference=max(rotations), checked_utc=utc_now())
        strict_json(out/'verification.json', verification, root)
        paths = [out/f'tissue_{t}.npz' for t in source.TISSUES]
        paths += [out/p for p in ('summary.npz', 'analysis.json', 'verification.json', 'input_hashes.sha256')]
        assert len(paths) == 20
        write_hash_manifest(paths, out/'output_hashes.sha256', root)
        assert source.old.checker().check_hashes(out/'output_hashes.sha256') == 20
        status = dict(status='COMPLETE', run_id=RUN_ID, completed_utc=utc_now(),
            elapsed_seconds=time.monotonic()-start, checked_blocks=16, checked_snapshot_batches=480,
            verified_saved_analysis=True, new_simulation_lives=0, dynamics_replays=0)
        strict_json(run/'STATUS.json', status, root)
        atomic_text(run/'COMPLETE', status['completed_utc']+'\n', root)
        print(json.dumps(status, indent=2), flush=True)
        return 0
    except Exception as error:
        status = dict(status='FAILED', run_id=RUN_ID, failed_utc=utc_now(), error=str(error), traceback=traceback.format_exc())
        strict_json(run/'STATUS.json', status, root)
        atomic_text(run/'FAILED', status['failed_utc']+'\n', root)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--external-root', required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    for op in ('benchmark', 'prepare', 'detach', 'run'):
        group.add_argument('--'+op, action='store_true')
    args = parser.parse_args()
    root = external_root(args.external_root)
    if args.benchmark:
        benchmark(root)
    elif args.prepare:
        prepare(root)
    elif args.detach:
        detach(root)
    else:
        return run_audit(root)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
