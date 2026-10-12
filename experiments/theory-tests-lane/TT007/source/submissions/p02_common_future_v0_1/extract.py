"""Verified generation-14 measurements from completed runs; no simulation."""
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import time

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


def write_csv(path, rows):
    with Path(path).open('x', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def equal(a, b):
    assert a.shape == b.shape and a.dtype == b.dtype and a.tobytes() == b.tobytes()


def ports():
    result = np.zeros((3, 16, 16), bool)
    for i, (y, x) in enumerate(((7, 1), (3, 10), (11, 10))):
        result[i, y:y+2, x:x+2] = True
    return result


class Sources:
    def __init__(self, cfg):
        self.bindings, self.runs, self.outputs, self.configs = {}, {}, {}, {}
        for label in ('spacing', 'pulse'):
            folder = (HERE / cfg[label + '_run']).resolve()
            self.runs[label] = folder
            self.bind(folder / 'COMPLETE.json', cfg[label + '_complete_sha256'])
            done = read(folder / 'COMPLETE.json')
            assert done['status'] == 'COMPLETE' and done['native_replay_passed']
            assert done['blocks_completed'] == cfg['blocks']
            self.outputs[label] = done['outputs_sha256']
            path = self.file(label, 'manifest.json')
            native = read(path)['config']
            assert native['blocks'] == cfg['blocks'] and native['pairing'] == 'paired'
            assert native['branch_generation'] == 3 and native['terminal_generation'] == 32
            assert native['injuries'] == ['intact', 'scattered', 'square']
            self.configs[label] = native
        spacing = self.configs['spacing']
        assert spacing['writers'] == [cfg['histories'][0], 'tolerance_rewrite', *cfg['histories'][1:]]
        assert spacing['simulated_writers'] == [cfg['histories'][i] for i in (0, 2, 3)]
        for name in cfg['histories']:
            assert all(g < cfg['generation'] for g in spacing['tolerance_generations'][name])
        pulse = self.configs['pulse']
        assert pulse['simulated_writers'] == [cfg['histories'][0], 'magnitude_restored', cfg['histories'][1]]
        assert pulse['schedules'][cfg['histories'][1]]['later'] == cfg['histories'][0]
        self.bind((HERE / cfg['core_source']).resolve(), cfg['core_sha256'])

    def bind(self, path, expected):
        actual = sha(path)
        assert actual == expected, str(path)
        self.bindings[str(path.relative_to(HERE.parent))] = actual

    def file(self, label, name):
        path = self.runs[label] / name
        self.bind(path, self.outputs[label][name])
        return path

    def arrays(self, label, name):
        path = self.file(label, name)
        with np.load(io.BytesIO(path.read_bytes()), allow_pickle=False) as f:
            index = json.loads(f['__index__'].tobytes())
            assert set(f.files) == set(index) | {'__index__'}
            arrays = {k: f[k] for k in index}
        for k, a in arrays.items():
            assert index[k] == dict(shape=list(a.shape), dtype=a.dtype.str,
                                   sha256=hashlib.sha256(a.tobytes()).hexdigest())
            if a.dtype.kind == 'f':
                assert np.isfinite(a).all()
        return arrays


def extract(cfg):
    sources = Sources(cfg)
    spec = importlib.util.spec_from_file_location('frozen_core', HERE / cfg['core_source'])
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    p, records = ports(), []
    rules = np.tile(np.repeat([1., -1., 1., -1.], 4), 4)
    case_ids = [0, 2, 3, 4]
    g = cfg['generation']
    for block in cfg['blocks']:
        spacing, pulse = (sources.arrays(label, f'boundary_{block:06d}_g{g}.npz')
                          for label in ('spacing', 'pulse'))
        for field in ('masks', 'birth'):
            equal(spacing[field], pulse[field])
        for field in ('end', 'outgoing', 'mean_ports'):
            equal(spacing[field][0], pulse[field][0])
        assert not spacing['writer_codes'].any()
        combined = {k: np.stack((spacing[k][0], pulse[k][2], spacing[k][1], spacing[k][2]))
                    for k in ('end', 'outgoing', 'mean_ports')}
        body = combined['end'].reshape(64, 2, 16, 16)
        masks = np.broadcast_to(spacing['masks'], (4, 4, 4, 16, 16)).reshape(64, 16, 16)
        exact = core.writer_pair(body, core.available_edges(masks))['exact']
        packet = np.ascontiguousarray(exact, dtype='<f8').view(np.uint8).reshape(4, 4, 4, 4096)
        equal(packet, combined['outgoing'])
        rows = core.normalized(exact)
        signed = core.minimum_task_transfer(core.cue_transfer(rows, p[0], cfg['transfer_steps']), p, rules)
        unsigned_field = core.cue_transfer(abs(rows), p[0], cfg['transfer_steps'])
        unsigned = np.minimum(unsigned_field[..., p[1]].mean(axis=-1), unsigned_field[..., p[2]].mean(axis=-1))
        native_ports = combined['mean_ports'].reshape(64, 2, 2)
        aligned = native_ports * rules[:, None, None] * np.array([1., -1.])[None, :, None] * np.array([1., -1.])[None, None, :]
        aligned = aligned.reshape(64, 4)
        margin = aligned.min(axis=1)
        current = (aligned > cfg['margin']).all(axis=1)
        independently_scored = core.score_ports(native_ports, rules, cfg['margin'])
        equal(margin, independently_scored[0])
        equal(current, independently_scored[1])
        new, old = (sources.arrays(label, f'cases_{block:06d}.npz') for label in ('spacing', 'pulse'))
        assert int(new['block']) == int(old['block']) == block
        assert new['generations'].tolist() == old['generations'].tolist() == list(range(3, 33))
        gi = g - 3
        for field in ('body_both_pass', 'body_min_margin'):
            equal(new[field][gi, [0, 2]], old[field][gi, [0, 4]])
        for field in ('assay_both_pass', 'assay_min_margin'):
            equal(new[field][[0, 2]], old[field][[0, 4]])
        equal(current.reshape(4, 4, 4), new['body_both_pass'][gi, case_ids])
        equal(margin.reshape(4, 4, 4), new['body_min_margin'][gi, case_ids])
        assert not new['writer_codes'][gi:, case_ids].any()
        for name, actual in [('signed_transfer', signed), ('unsigned_access', unsigned)]:
            np.testing.assert_allclose(actual.reshape(4, 4, 4), new[name][gi, case_ids], rtol=0, atol=2e-14)
            np.testing.assert_allclose(actual.reshape(4, 4, 4)[[0, 2, 3]], spacing[name], rtol=0, atol=2e-14)
        terminal = new['assay_both_pass'][case_ids, :, :, 1].reshape(64)
        terminal_margin = new['assay_min_margin'][case_ids, :, :, 1].reshape(64)
        equal(terminal, terminal_margin > cfg['margin'])
        for i in range(64):
            hi, lineage = divmod(i, 16)
            founder, recipient = divmod(lineage, 4)
            row = dict(block=block, history=cfg['histories'][hi], founder=founder,
                       recipient=recipient, generation=g, task_rule=int(rules[i]))
            row.update(zip(cfg['expression_features'][:4], map(float, aligned[i])))
            row.update(current_margin=float(margin[i]), current_pass=int(current[i]),
                       unsigned_access=float(unsigned[i]), signed_transfer=float(signed[i]),
                       terminal_success=int(terminal[i]), terminal_margin=float(terminal_margin[i]))
            records.append(row)
    expected = {(r['block'], r['history'], r['founder'], r['recipient']): r for r in records}
    for filename in ('body_lineages.csv', 'terminal_lineages.csv'):
        checked = set()
        with sources.file('spacing', filename).open() as f:
            for raw in csv.DictReader(f):
                if raw['writer'] not in cfg['histories']:
                    continue
                body_row = filename.startswith('body')
                if body_row and int(raw['generation']) != g:
                    continue
                if not body_row and raw['injury'] != 'scattered':
                    continue
                key = (int(raw['block']), raw['writer'], int(raw['founder']), int(raw['recipient']))
                assert key not in checked
                checked.add(key)
                row = expected[key]
                prefix = 'current' if body_row else 'terminal'
                outcome = 'current_pass' if body_row else 'terminal_success'
                assert int(raw['success']) == row[outcome]
                assert float(raw['margin']) == row[prefix + '_margin']
                if body_row:
                    assert raw['active_writer_policy'] == 'exact_rewrite'
                    for name in ('signed_transfer', 'unsigned_access'):
                        assert abs(float(raw[name]) - row[name]) <= 2e-14
        assert checked == set(expected)
    return records, sources.bindings


def main():
    start = time.perf_counter()
    frozen = read(HERE / 'definition_snapshot.json')
    for name, digest in frozen['files_sha256'].items():
        assert sha(HERE / name) == digest
    cfg = read(HERE / 'config.json')
    result = HERE / 'results'
    result.mkdir(exist_ok=False)
    records, bindings = extract(cfg)
    write_csv(result / 'records.csv', records)
    write_json(result / 'extraction.json', dict(status='PASS', records=len(records),
        created_at_utc=datetime.now(timezone.utc).isoformat(), seconds=time.perf_counter()-start,
        current_boundary=cfg['generation'],
        source_files_sha256=bindings, exact_captures_verified=len(records),
        current_scores_and_terminal_labels_verified=True, csv_rows_crosschecked=2*len(records),
        records_sha256=sha(result / 'records.csv'), native_simulations=False))
    print(json.dumps(dict(status='PASS', records=len(records), seconds=time.perf_counter()-start)))


if __name__ == '__main__':
    main()
