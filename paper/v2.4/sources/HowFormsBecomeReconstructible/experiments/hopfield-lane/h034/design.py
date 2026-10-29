"""H034: sample observed prefixes, then branch their unchanged endpoint states."""
import json
from pathlib import Path
import numpy as np
from h019.audit import load
from h025.design import rng
from h033 import design as prior_design

SEED = 34034
DTS = prior_design.DTS
CELLS = prior_design.CELLS
SELECTIONS = prior_design.SELECTIONS
MODELS = prior_design.MODELS
START = 6
END = 24
TAILS = 32
CONTROLS = 32
CHUNK = 8
LABEL = 'POST_RESULT_CONDITIONAL_FUTURE_DIAGNOSTIC'


def choose(rows, disagreement, split, controls=CONTROLS):
    """No prior outcomes or forecasts are arguments to the sampling rule."""
    assert split in ('train', 'test')
    disagreement = np.asarray(disagreement)
    assert disagreement.dtype == bool and disagreement.shape == (len(rows),)
    selected, panels = [], []
    for cell in CELLS:
        for selection in SELECTIONS:
            indices = np.array([i for i, r in enumerate(rows)
                                if (r['cell'], r['selection']) == (cell, selection)])
            assert len(indices) > 0
            yes, no = indices[disagreement[indices]], indices[~disagreement[indices]]
            count = min(controls, len(no))
            key = [SEED, 0, int(split == 'test'), cell, SELECTIONS.index(selection)]
            sample = np.sort(rng(key).choice(no, count, replace=False))
            panels.append(dict(cell=cell, selection=selection, total=len(indices),
                early_disagreement=len(yes), early_agreement=len(no), controls=count, key=key))
            for i in np.r_[yes, sample]:
                selected.append(dict(rows[int(i)], row_index=int(i), split=split,
                    early_disagreement=bool(disagreement[i]),
                    inclusion_probability=1. if disagreement[i] else count/len(no)))
    return sorted(selected, key=lambda row: row['row_index']), panels


def future(rows, cell, benchmark=False):
    """Same future for paired paths and duplicate physical observed prefixes.

    Branch and fixed/selected labels deliberately do not enter the seed.
    Different observed H033 tails and train/test cohorts have distinct keys.
    """
    keys = np.array([[[SEED, 2 if benchmark else 1, int(row['split'] == 'test'),
        cell, row['source_id'], row['probe_id'], row['tail'], k]
        for k in range(TAILS)] for row in rows], np.uint32)
    uniforms = np.array([[rng(key).random(END-START) for key in group] for group in keys])
    _, interval, law = prior_design.old.CELLS[cell]
    offset, width = prior_design.old.LAWS[law]
    return dict(future_keys=keys, future_uniforms=uniforms,
        entrants=np.repeat(-offset-width*uniforms, 2, axis=0),
        interval=np.array(interval), stress=np.array(width), offset=np.array(offset))


def scan(prior, split):
    """Read exactly six observed replacements, without accessing full futures."""
    saved = json.loads((prior/f'rows_{split}.json').read_text())
    config = json.loads((prior/'config.json').read_text())
    rows, early = [], []
    for spec in config['specs']:
        if spec['split'] != split:
            continue
        data = load(prior/'derived'/spec['key']/'observation.npz')
        raw = load(prior/'raw'/('observation_'+spec['key'])/'raw_2.npz')
        assert raw['history'].shape == (len(data['initial']), 36, 7, 3)
        labels = (np.tanh(2*raw['history'][..., -1, :]) > .5).all(axis=-1)
        for case in range(len(data['initial'])):
            for branch in range(1, 9):
                for tail in range(4):
                    row = saved[len(rows)]
                    assert (row['cell'], row['selection'], row['source_id'], row['probe_id'], row['branch'], row['tail']) == (
                        spec['cell'], SELECTIONS[int(data['selection'][case])], int(data['source_id'][case]),
                        int(data['probe_id'][case]), branch, tail)
                    rows.append(dict(row, batch=spec['key'], case=case))
                    early.append(labels[case, tail] != labels[case, 4*branch+tail])
    assert len(rows) == len(saved) == 24576
    return rows, np.array(early, bool)


def pack(prior, rows, benchmark=False):
    assert rows and len({r['cell'] for r in rows}) == 1
    cell = rows[0]['cell']
    result = future(rows, cell, benchmark)
    fields = {name: [] for name in ('weights', 'prefix_entrants', 'original_initial')}
    for level in range(3):
        for key in ('initial', 'prefix_history', 'prefix_entries'):
            fields[f'{key}_{level}'] = []
        if benchmark:
            for key in ('archive_history', 'archive_entries'):
                fields[f'{key}_{level}'] = []
    if benchmark:
        fields['archive_entrants'] = []
    cache = {}
    for row in rows:
        batch = row['batch']
        if batch not in cache:
            if benchmark:
                root = prior/'raw'/(batch+'_serial')
                inputs = load(root/'observation_inputs.npz')
                observed = [load(root/'observation'/f'raw_{level}.npz') for level in range(3)]
                archived = [load(root/'future'/f'raw_{level}.npz') for level in range(3)]
                full = load(root/'future_inputs.npz')
            else:
                inputs = load(prior/'derived'/batch/'observation.npz')
                observed = [load(prior/'raw'/('observation_'+batch)/f'raw_{level}.npz') for level in range(3)]
                archived = full = None
            cache[batch] = inputs, observed, archived, full
        inputs, observed, archived, full = cache[batch]
        case = row['case']
        for path in (row['tail'], 4*row['branch']+row['tail']):
            fields['weights'].append(inputs['weights'][case])
            fields['prefix_entrants'].append(inputs['entrants'][case, path])
            fields['original_initial'].append(inputs['initial'][case])
            for level, raw in enumerate(observed):
                assert raw['history'].shape[-2] == 7 and raw['entries'].shape[-2] == 6
                assert float(raw['dt']) == DTS[level]
                assert float(raw['interval']) == float(result['interval'])
                np.testing.assert_array_equal(raw['identities'][-1], [9, 7, 8])
                fields[f'initial_{level}'].append(raw['history'][case, path, -1])
                fields[f'prefix_history_{level}'].append(raw['history'][case, path])
                fields[f'prefix_entries_{level}'].append(raw['entries'][case, path])
                if benchmark:
                    np.testing.assert_array_equal(raw['history'][case, path], archived[level]['history'][case, path, :7])
                    fields[f'archive_history_{level}'].append(archived[level]['history'][case, path, 6:])
                    fields[f'archive_entries_{level}'].append(archived[level]['entries'][case, path, 6:])
            if benchmark:
                fields['archive_entrants'].append(full['entrants'][case, path, 6:])
    result.update({name: np.array(value) for name, value in fields.items()})
    result.update(cell=np.array(cell), row_index=np.array([r['row_index'] for r in rows]),
        early_disagreement=np.array([r['early_disagreement'] for r in rows], bool),
        benchmark=np.array(benchmark), global_initial_identities=np.array([9, 7, 8]))
    for level in range(3):
        initial = result[f'initial_{level}'].reshape(-1, 2, 3)
        early = (np.tanh(2*initial) > .5).all(axis=-1)
        np.testing.assert_array_equal(early[:, 0] != early[:, 1], result['early_disagreement'])
    if not benchmark:
        split = rows[0]['split']; assert all(r['split'] == split for r in rows)
        indices = result['row_index']
        # Attached only after choose() has fixed every selected prefix.
        result['saved_forecasts'] = np.stack([load(prior/'models'/name/'predictions.npz')[
            'oof' if split == 'train' else 'prediction'][indices] for name in MODELS], axis=-1)
    validate(result)
    return result


def validate(data):
    pairs = len(data['row_index'])
    assert data['entrants'].shape == (2*pairs, TAILS, END-START)
    np.testing.assert_array_equal(data['entrants'][::2], data['entrants'][1::2])
    np.testing.assert_array_equal(data['weights'][::2], data['weights'][1::2])
    assert all(np.isfinite(value).all() for value in data.values())
    for key in ('entrants', 'prefix_entrants'):
        assert ((data[key] > -float(data['offset'])-float(data['stress'])) &
                (data[key] <= -float(data['offset']))).all()
    assert ((data['future_uniforms'] >= 0) & (data['future_uniforms'] < 1)).all()
    generated = np.array([[rng(key).random(END-START) for key in group] for group in data['future_keys']])
    np.testing.assert_array_equal(generated, data['future_uniforms'])
    np.testing.assert_array_equal(data['entrants'][::2], -float(data['offset'])-float(data['stress'])*generated)
    np.testing.assert_array_equal(data['global_initial_identities'], [9, 7, 8])
    for level in range(3):
        np.testing.assert_array_equal(data[f'initial_{level}'], data[f'prefix_history_{level}'][:, -1])


def prepare_inputs(prior, out):
    (out/'inputs').mkdir()
    tasks, panels, all_rows = [], {}, {}
    for split in ('train', 'test'):
        rows, early = scan(prior, split)
        selected, panel = choose(rows, early, split)
        panels[split], all_rows[split] = panel, selected
        for cell in CELLS:
            subset = [row for row in selected if row['cell'] == cell]
            for j, start in enumerate(range(0, len(subset), CHUNK)):
                group = subset[start:start+CHUNK]
                name = f'{split}_c{cell:02d}_{j:03d}'
                np.savez_compressed(out/'inputs'/f'{name}.npz', **pack(prior, group))
                tasks.append(dict(name=name, split=split, cell=cell, rows=group, pairs=len(group),
                    interval=float(prior_design.old.CELLS[cell][1])))
    benchmark = []
    for spec in prior_design.benchmark_specs():
        root = prior/'raw'/(spec['key']+'_serial')
        data = load(root/'observation_inputs.npz')
        raw = load(root/'observation/raw_2.npz')
        rows = []
        for i in range(CHUNK):
            case, branch, tail = i+CHUNK, 5, i % 4
            endpoint = raw['history'][case, [tail, 4*branch+tail], -1]
            labels = (np.tanh(2*endpoint) > .5).all(axis=-1)
            rows.append(dict(cell=spec['cell'], split='train', selection=SELECTIONS[1],
                source_id=int(data['source_id'][case]), probe_id=int(data['probe_id'][case]),
                branch=branch, tail=tail, batch=spec['key'], case=case, row_index=i,
                early_disagreement=bool(labels[0] != labels[1])))
        name = spec['key']
        np.savez_compressed(out/'inputs'/f'{name}.npz', **pack(prior, rows, benchmark=True))
        benchmark.append(dict(name=name, rows=rows, pairs=len(rows), cell=spec['cell'],
            interval=float(prior_design.old.CELLS[spec['cell']][1])))
    return tasks, benchmark, dict(panels=panels, rows=all_rows)
