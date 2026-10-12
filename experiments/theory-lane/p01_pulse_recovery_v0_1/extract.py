"""Measure completed pulse histories. No native simulation or outcome fitting."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import time
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


def stamp():
    return datetime.now(timezone.utc).isoformat()


def descriptor(a):
    return dict(shape=list(a.shape), dtype=a.dtype.str,
                sha256=hashlib.sha256(a.tobytes()).hexdigest())


def equal(a, b):
    assert a.shape == b.shape and a.dtype == b.dtype and a.tobytes() == b.tobytes()


def load_core(cfg):
    path = (HERE / cfg['core_source']).resolve()
    assert sha(path) == cfg['core_sha256']
    spec = importlib.util.spec_from_file_location('frozen_diagnostic_core', path)
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    return core


def ports():
    result = np.zeros((3, 16, 16), bool)
    for j, (y, x) in enumerate(((7, 1), (3, 10), (11, 10))):
        result[j, y:y+2, x:x+2] = True
    return result


class Sources:
    def __init__(self, cfg):
        self.bindings = {}
        self.runs, self.completed = {}, {}
        for label in ('prior', 'pulse'):
            folder = (HERE / cfg[label + '_run']).resolve()
            self.runs[label] = folder
            self.bind(folder / 'COMPLETE.json', cfg[label + '_complete_sha256'])
            done = read(folder / 'COMPLETE.json')
            assert done['status'] == 'COMPLETE' and done['native_replay_passed']
            assert done['blocks_completed'] == cfg['blocks']
            self.completed[label] = done['outputs_sha256']
            self.bind(folder / 'manifest.json', self.completed[label]['manifest.json'])
            manifest = read(folder / 'manifest.json')['config']
            assert manifest['blocks'] == cfg['blocks'] and manifest['pairing'] == 'paired'
            assert manifest['branch_generation'] == 3 and manifest['terminal_generation'] == 32
            expected = cfg['writers'][:3] if label == 'prior' else cfg['writers']
            assert manifest['writers'] == expected
            if label == 'pulse':
                assert manifest['simulated_writers'] == [cfg['writers'][j] for j in (0, 3, 4)]
        self.bind((HERE / cfg['core_source']).resolve(), cfg['core_sha256'])

    def bind(self, path, expected):
        digest = sha(path)
        assert digest == expected, str(path)
        self.bindings[str(path.relative_to(HERE.parent))] = digest

    def arrays(self, label, name):
        path = self.runs[label] / name
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        assert digest == self.completed[label][name], str(path)
        self.bindings[str(path.relative_to(HERE.parent))] = digest
        with np.load(io.BytesIO(content), allow_pickle=False) as f:
            index = json.loads(f['__index__'].tobytes())
            assert set(f.files) == set(index) | {'__index__'}
            result = {k: f[k] for k in index}
        for k, a in result.items():
            assert descriptor(a) == index[k], (str(path), k)
            if a.dtype.kind == 'f':
                assert np.isfinite(a).all(), (str(path), k)
        return result

    def cases(self, block, cfg):
        old, new = (self.arrays(label, f'cases_{block:06d}.npz') for label in ('prior', 'pulse'))
        assert int(old['block']) == int(new['block']) == block
        assert new['generations'].tolist() == old['generations'].tolist() == cfg['generations']
        for field in ('body_both_pass', 'body_min_margin', 'newly_substituted_fraction', 'sign_flip_fraction'):
            equal(new[field][:, :3], old[field])
        for field in ('assay_both_pass', 'assay_min_margin'):
            equal(new[field][[0, 1, 2, 5]], old[field])
        return new

    def boundary(self, block, generation):
        old, new = (self.arrays(label, f'boundary_{block:06d}_g{generation}.npz') for label in ('prior', 'pulse'))
        equal(new['masks'], old['masks'])
        if generation > 3:
            equal(new['birth'], old['birth'])
        for name in ('end', 'outgoing', 'mean_ports', 'newly_substituted_fraction', 'sign_flip_fraction'):
            equal(new[name][0], old[name][0])
        if generation == 3:
            for a in [*old['end'], *new['end']]:
                equal(a, old['end'][0])
            equal(new['outgoing'][2], old['outgoing'][1])
        if generation == 4:
            equal(new['end'][2], old['end'][1])
            equal(new['mean_ports'][2], old['mean_ports'][1])
        result = {'masks': new['masks']}
        for name in ('end', 'outgoing', 'mean_ports', 'newly_substituted_fraction', 'sign_flip_fraction'):
            result[name] = np.stack((new[name][0], old[name][1], old[name][2], new[name][1], new[name][2]))
        return result


def measurements(raw, generation, cfg, core):
    body = raw['end'].reshape(80, 2, 16, 16)
    masks = np.broadcast_to(raw['masks'], (5, 4, 4, 16, 16)).reshape(80, 16, 16)
    outgoing = raw['outgoing']
    assert outgoing.dtype == np.uint8 and outgoing.shape == (5, 4, 4, 4096)
    weights = np.frombuffer(outgoing.tobytes(), dtype='<f8').reshape(80, 2, 16, 16)
    available = core.available_edges(masks)
    pair = core.writer_pair(body, available, tolerance=cfg['tolerance'])
    o, t = pair['exact'].reshape(5, 16, 2, 16, 16), pair['tolerance'].reshape(5, 16, 2, 16, 16)
    m = np.where(t[3] != 0., np.sign(t[3]), np.sign(o[3])) * abs(o[3])
    expected = np.stack((o[0], t[1], np.sign(o[2])*abs(t[2]), m, t[4] if generation == 3 else o[4]))
    equal(weights.reshape(5, 16, 2, 16, 16), expected)
    assert not np.any((o == 0.) & (t != 0.))
    p = ports()
    eligible = (~masks) & (~p[0])
    rows, counterfactual = core.normalized(weights), core.normalized(pair['exact'])
    reference = np.broadcast_to(rows[:16], (5, 16, 4, 16, 16)).reshape(rows.shape)
    signed = core.cue_transfer(rows, p[0], cfg['transfer_steps'])
    unsigned = core.cue_transfer(abs(rows), p[0], cfg['transfer_steps'])
    counterfactual_field = core.cue_transfer(counterfactual, p[0], cfg['transfer_steps'])
    rules = np.tile(np.repeat([1., -1., 1., -1.], 4), 5)
    transfer = core.minimum_task_transfer(signed, p, rules)
    original_transfer = np.tile(transfer[:16], 5)
    margin, passed, _ = core.score_ports(raw['mean_ports'].reshape(80, 2, 2), rules, cfg['margin'])
    swapped = available & (pair['q'] != 0.) & (abs(pair['q']) <= cfg['tolerance'])
    flips = available & (pair['exact'] * pair['tolerance'] < 0.)
    available_count = available.sum(axis=(-3, -2, -1))
    fraction, flip_fraction = (a.sum(axis=(-3, -2, -1))/available_count for a in (swapped, flips))
    equal(fraction.reshape(5, 4, 4), raw['newly_substituted_fraction'])
    equal(flip_fraction.reshape(5, 4, 4), raw['sign_flip_fraction'])
    result = dict(body_margin=margin, body_pass=passed.astype(int),
        body_margin_minus_original=margin-np.tile(margin[:16], 5),
        signed_transfer=transfer,
        unsigned_access=np.minimum(unsigned[..., p[1]].mean(axis=-1), unsigned[..., p[2]].mean(axis=-1)),
        transfer_minus_original=transfer-original_transfer,
        abs_transfer_gap_original=abs(transfer-original_transfer),
        reader_distance_original=core.masked_mean(abs(rows-reference).sum(axis=-3), eligible),
        reader_action_distance_same_body_original=core.masked_mean(abs(rows-counterfactual).sum(axis=-3), eligible),
        counterfactual_original_transfer=core.minimum_task_transfer(counterfactual_field, p, rules),
        body_mean_abs_cue_difference=core.masked_mean(abs(body[:, 0]-body[:, 1])/2, eligible),
        hypothetical_tolerance_substitution_fraction=fraction, hypothetical_sign_flip_fraction=flip_fraction)
    for k, a in result.items():
        assert a.shape == (80,) and np.isfinite(a).all(), k
    return {k: a.reshape(5, 4, 4) for k, a in result.items()}


def main(mode):
    start = time.monotonic()
    cfg = read(HERE / 'config.json')
    definitions = read(HERE / 'definition_snapshot.json')
    for name, digest in definitions['files_sha256'].items():
        assert sha(HERE / name) == digest, name
    core, source = load_core(cfg), Sources(cfg)
    if mode == 'benchmark':
        case = source.cases(cfg['benchmark_block'], cfg)
        raw = source.boundary(cfg['benchmark_block'], cfg['benchmark_generation'])
        metrics = measurements(raw, cfg['benchmark_generation'], cfg, core)
        equal(metrics['body_margin'], case['body_min_margin'][0])
        assert np.array_equal(metrics['body_pass'], case['body_both_pass'][0])
        elapsed = time.monotonic()-start
        result = dict(status='PASS', seconds=elapsed, contexts=80, generations=1,
            conservative_forecast_seconds=3*elapsed*len(cfg['blocks'])*len(cfg['generations'])+30,
            new_native_dynamics=False, definition_snapshot_sha256=sha(HERE / 'definition_snapshot.json'))
        write_json(HERE / 'benchmark.json', result)
        print(json.dumps(result, indent=2))
        return
    benchmark = read(HERE / 'benchmark.json')
    assert benchmark['status'] == 'PASS' and benchmark['conservative_forecast_seconds'] <= 600
    destination = HERE / 'results'
    destination.mkdir(exist_ok=False)
    records = []
    try:
        for block in cfg['blocks']:
            cases = source.cases(block, cfg)
            for g, generation in enumerate(cfg['generations']):
                raw = source.boundary(block, generation)
                metrics = measurements(raw, generation, cfg, core)
                equal(metrics['body_margin'], cases['body_min_margin'][g])
                assert np.array_equal(metrics['body_pass'], cases['body_both_pass'][g])
                for n, writer in enumerate(cfg['writers']):
                    action = ('tolerance_rewrite' if generation == 3 else 'exact_rewrite') if n == 4 else writer
                    for f in range(4):
                        for r in range(4):
                            row = dict(block=block, generation=generation, writer=writer, active_writer=action,
                                founder=f, recipient=r,
                                terminal_success=int(cases['assay_both_pass'][n, f, r, 1]),
                                terminal_margin=float(cases['assay_min_margin'][n, f, r, 1]))
                            row.update({k: int(a[n, f, r]) if k == 'body_pass' else float(a[n, f, r]) for k, a in metrics.items()})
                            records.append(row)
        with (destination / 'lineages.csv').open('x', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
        result = dict(status='COMPLETE', completed_at_utc=stamp(), seconds=time.monotonic()-start,
            rows=len(records), blocks=cfg['blocks'], native_dynamics_rerun=False,
            original_histories_byte_equal=True, pulse_tolerance_boundary_equality=True,
            all_actual_writers_recomputed_byte_equal=True, all_native_scores_and_stored_writer_diagnostics_match=True,
            all_consumed_arrays_match_commitments=True, source_inputs_sha256=source.bindings,
            definition_snapshot_sha256=sha(HERE / 'definition_snapshot.json'),
            outputs_sha256={'lineages.csv': sha(destination / 'lineages.csv')})
        write_json(destination / 'EXTRACTION_COMPLETE.json', result)
        print(json.dumps({k: v for k, v in result.items() if k != 'source_inputs_sha256'}, indent=2))
    except Exception:
        write_json(destination / 'FAILED.json', dict(status='FAILED', utc=stamp(), traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['benchmark', 'extract'])
    main(parser.parse_args().mode)
