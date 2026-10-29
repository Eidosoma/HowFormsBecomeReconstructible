"""Grouped training, input chronology and sealed forecasts of paired outcome changes."""
from pathlib import Path
from datetime import datetime, timezone
import json
import numpy as np
from h007.io import checksum, save, seal, verify
from h019.audit import load
from h021 import fit
from h033 import design as d, measure


def no_test_futures(out):
    if (out/'TEST_SUBMISSION.json').exists() or list((out/'raw').glob('future_test_*')):
        raise AssertionError('Test futures already submitted or generated')


def derive_inputs(out):
    assert not list((out/'raw').glob('future_*'))
    verify(out, 'freeze.json'); verify(out, 'probe_sha256.json')
    config = json.loads((out/'config.json').read_text())
    for spec in config['specs']:
        folder = out/'raw'/('probe_'+spec['key'])
        assert json.loads((folder/'audit.json').read_text())['qualified']
        data = load(out/'inputs'/f'{spec["key"]}.npz')
        finite, future = d.derive(data, [load(folder/f'raw_{i}.npz') for i in range(3)])
        target = out/'derived'/spec['key']; target.mkdir(parents=True, exist_ok=False)
        np.savez_compressed(target/'finite.npz', **finite)
        np.savez_compressed(target/'future.npz', **future)
        np.savez_compressed(target/'observation.npz', **d.observation_inputs(future))
    save(out/'DERIVED_SEAL.json', dict(label='PROSPECTIVE_DEVELOPMENT',
        sealed_utc=datetime.now(timezone.utc).isoformat(), freeze_sha256=checksum(out/'freeze.json'),
        probe_manifest_sha256=checksum(out/'probe_sha256.json'), no_main_futures_generated=True))
    seal(out, 'derived_sha256.json', sorted((out/'derived').rglob('*.npz'))+[out/'DERIVED_SEAL.json',out/'probe_sha256.json'])


def make_features(out):
    no_test_futures(out)
    assert not list((out/'raw').glob('future_*'))
    for name in ('freeze.json', 'derived_sha256.json', 'finite_sha256.json', 'observation_sha256.json'):
        verify(out, name)
    config = json.loads((out/'config.json').read_text()); paths = []
    dimensions = None
    for split in ('train', 'test'):
        tables, rows = [], []
        for spec in config['specs']:
            if spec['split'] != split:
                continue
            assert json.loads((out/'raw'/('finite_'+spec['key'])/'audit.json').read_text())['qualified']
            observed = out/'raw'/('observation_'+spec['key'])
            audit = json.loads((observed/'audit.json').read_text())
            assert audit['qualified'] and audit['matched_prefix_verified']
            table, metadata = d.features(load(out/'derived'/spec['key']/'finite.npz'), load(observed/'raw_2.npz'))
            tables.append(table); rows.extend(metadata)
        joined = {key: np.concatenate([table[key] for table in tables]) for key in tables[0]}
        expected_rows = len(d.CELLS)*2*config['sources_per_split']*8*d.TAILS
        assert len(rows) == expected_rows and all(len(x)==expected_rows and np.isfinite(x).all() for x in joined.values())
        actual_dimensions = {key: x.shape[1] for key, x in joined.items()}
        assert dimensions is None or dimensions == actual_dimensions
        dimensions = actual_dimensions
        np.savez_compressed(out/f'features_{split}.npz', **joined)
        save(out/f'rows_{split}.json', rows)
        paths.extend([out/f'features_{split}.npz', out/f'rows_{split}.json'])
    assert dimensions == d.DIMENSIONS
    save(out/'feature_dimensions.json', dimensions)
    save(out/'FEATURE_SEAL.json', dict(sealed_utc=datetime.now(timezone.utc).isoformat(),
        maximum_observed_replacement=d.OBSERVATION, no_main_futures_generated=True))
    seal(out, 'feature_sha256.json', paths+[out/'feature_dimensions.json',out/'derived_sha256.json',
        out/'finite_sha256.json',out/'observation_sha256.json',out/'FEATURE_SEAL.json'])


def targets(out, split):
    assert split in ('train', 'test')
    if split == 'test':
        measure.require_test_seal(out)
    pieces = []
    config = json.loads((out/'config.json').read_text())
    for item in config['tasks'][split]:
        spec = item['spec']; folder = out/'raw'/item['name']
        data = load(out/'derived'/spec['key']/'future.npz')
        audit = json.loads((folder/'audit.json').read_text())
        assert audit['qualified'] and audit['matched_prefix_verified'] and audit['entrants_within_original_support']
        assert audit['matched_observation_verified']
        raw = load(folder/'raw_2.npz')
        assert float(raw['dt']) == d.DTS[-1] and float(raw['interval']) == float(data['interval'])
        assert raw['history'].shape[-2:] == (25, 3)
        expected = (np.tanh(2*raw['history'][...,13:25,:]) > .5).all(axis=(-2,-1))
        independent = (np.tanh(2*raw['independent_history'][...,13:25,:]) > .5).all(axis=(-2,-1))
        np.testing.assert_array_equal(expected, raw['target']); np.testing.assert_array_equal(expected, independent)
        measure.prefix_parity(load(out/'raw'/('finite_'+spec['key'])/'raw_2.npz'), raw)
        measure.observation_parity(load(out/'raw'/('observation_'+spec['key'])/'raw_2.npz'), raw)
        pieces.append(expected.reshape(len(data['initial']), 9, d.TAILS))
    return np.concatenate(pieces)


def flips(target):
    assert target.dtype == bool and target.shape[1:] == (9, d.TAILS)
    return (target[:,1:] != target[:,:1]).reshape(-1)


def specs(name):
    if name not in d.MODELS:
        raise ValueError('Undeclared predictor')
    columns = ('persistence6', 'full6') if name == 'same_observation' else (name,)
    return sorted([dict(id=f'{column}:ridge={ridge:g}', column=column, ridge=ridge)
                   for column in columns for ridge in d.RIDGES], key=lambda s:s['id'])


def brier(p, q):
    return q*(1-p)**2+(1-q)*p**2


def fit_one(name, train, q, fold, test):
    assert set(fold) == {0,1,2,3}
    selections, oof, count = [], {}, 0
    for spec in specs(name):
        x = train[spec['column']]; p = np.empty(len(q)); losses = []
        for k in range(4):
            use, valid = fold != k, fold == k
            model = fit.logistic(x[use], q[use], spec['ridge']); count += 1
            p[valid] = fit.predict(model, x[valid])
            losses.append(float(brier(p[valid], q[valid]).mean()))
        selections.append(dict(**spec, brier=float(np.mean(losses)), fold_brier=losses)); oof[spec['id']] = p
    chosen = min(selections, key=lambda s:(s['brier'],s['id']))
    model = fit.logistic(train[chosen['column']], q, chosen['ridge']); count += 1
    prediction = fit.predict(model, test[chosen['column']])
    assert np.isfinite(prediction).all() and ((prediction>=0)&(prediction<=1)).all()
    return dict(name=name, selection=selections, selected=chosen, model=model, fits=count,
                prediction=prediction, oof=oof[chosen['id']])


def fit_task(args):
    out, name = Path(args['out']), args['name']; no_test_futures(out)
    for manifest in ('freeze.json','feature_sha256.json','train_sha256.json'):
        verify(out,manifest)
    train,test = [load(out/f'features_{split}.npz') for split in ('train','test')]
    rows = json.loads((out/'rows_train.json').read_text()); fold = np.array([r['fold'] for r in rows])
    q = load(out/'targets_train.npz')['flip'].astype(float)
    assert len(q) == len(rows)
    assert all(r['fold'] == r['source_id'] % 4 for r in rows)
    result = fit_one(name,train,q,fold,test)
    folder = out/'models'/name; folder.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(folder/'predictions.npz',prediction=result.pop('prediction'),oof=result.pop('oof'))
    save(folder/'model.json',result)
    return dict(name=name,fits=result['fits'])


def seal_predictions(out):
    no_test_futures(out)
    manifests = ('freeze.json','probe_sha256.json','derived_sha256.json','finite_sha256.json','observation_sha256.json',
                 'feature_sha256.json','train_sha256.json')
    for name in manifests:
        verify(out,name)
    n = len(json.loads((out/'rows_test.json').read_text()))
    assert {p.name for p in (out/'models').iterdir()} == set(d.MODELS)
    fits = 0
    for name in d.MODELS:
        prediction = load(out/'models'/name/'predictions.npz')['prediction']
        assert prediction.shape == (n,) and np.isfinite(prediction).all() and ((prediction>=0)&(prediction<=1)).all()
        fits += json.loads((out/'models'/name/'model.json').read_text())['fits']
    assert fits == d.FIT_COUNT
    save(out/'PREDICTION_SEAL.json',dict(label='PROSPECTIVE_DEVELOPMENT',
        sealed_utc=datetime.now(timezone.utc).isoformat(),test_future_tasks_submitted=False,
        bound_manifests={name:checksum(out/name) for name in manifests}))
    paths = [out/name for name in (*manifests,'PREDICTION_SEAL.json','targets_train.npz')]
    paths += sorted(p for p in (out/'models').rglob('*') if p.is_file())
    seal(out,'prediction_sha256.json',paths)


def submit_test(out, count):
    no_test_futures(out); verify(out,'prediction_sha256.json')
    save(out/'TEST_SUBMISSION.json',dict(tasks=count,submitted_utc=datetime.now(timezone.utc).isoformat(),
        prediction_manifest_sha256=checksum(out/'prediction_sha256.json')))
    measure.require_test_seal(out)
