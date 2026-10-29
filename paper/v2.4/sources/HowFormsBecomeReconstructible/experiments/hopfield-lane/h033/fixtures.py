"""Observation isolation, exact replay, grouped inference and end-to-end sealing."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import copy
import json
import tempfile
import unittest
import numpy as np
from h007.io import save, seal
from h019.audit import load
from h031.fixtures import synthetic_probes, synthetic_finite
from h033 import design as d, measure, predict, analysis
from h033.workflow import tasks_for, compare_benchmarks

ROOT = Path(__file__).resolve().parent.parent


def synthetic_observation(finite, inputs):
    n = len(finite['history']); raw = dict(dt=finite['dt'], interval=finite['interval'])
    for key in ('history', 'entries', 'independent_history', 'independent_entries'):
        prefix = np.repeat(finite[key][:, :, None], d.TAILS, axis=2).reshape(n, 36, *finite[key].shape[-2:])
        length = 7 if key.endswith('history') else 6
        array = np.full((n, 36, length, 3), .4); array[..., :prefix.shape[-2], :] = prefix
        if key.endswith('history'):
            for step in range(4, 7):
                decay = np.tile(np.array([.2, .4, .6, .8])**(step-3), 9)
                array[..., step, :] = .4+(prefix[..., -1, :]-.4)*decay[None, :, None]
        else:
            for step in range(3, 6):
                array[..., step, (1, 2, 0)[step % 3]] = inputs['entrants'][..., step]
        raw[key] = array
    raw['target'] = (np.tanh(2*raw['history'][..., 1:, :]) > .5).all(axis=(-2, -1))
    return raw


def synthetic_future(observed):
    n = len(observed['history']); raw = dict(dt=observed['dt'], interval=observed['interval'])
    for key in ('history', 'entries', 'independent_history', 'independent_entries'):
        prefix = observed[key]; length = 25 if key.endswith('history') else 24
        array = np.ones((n, 36, length, 3)); array[..., :prefix.shape[-2], :] = prefix
        if key.endswith('history'):
            array[:, :, 20, 0] = 0.; array[:, 20:28, 20, 0] = 1.
        raw[key] = array
    raw['target'] = (np.tanh(2*raw['history'][..., 13:25, :]) > .5).all(axis=(-2, -1))
    return raw


class H033Fixtures(unittest.TestCase):
    def temporary(self):
        folder = ROOT/'.cache/tmp'; folder.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=folder, prefix='h033_fixture_')

    def example(self):
        data = d.inputs('benchmark', 'train', [0, 1], 2)
        finite, future = d.derive(data, synthetic_probes(data))
        observed = synthetic_observation(synthetic_finite(finite), d.observation_inputs(future))
        return finite, future, observed

    def test_fresh_streams_chunking_and_group_pairing(self):
        a = d.inputs('prediction', 'train', range(16), 0)
        pieces = [d.inputs('prediction', 'train', range(start, start+8), 0) for start in (0, 8)]
        for key in ('initial', 'weights', 'entrants', 'source_keys', 'probe_keys', 'tail_keys', 'tail_uniforms'):
            np.testing.assert_array_equal(a[key], np.concatenate([p[key] for p in pieces]))
        b = d.inputs('prediction', 'train', range(16), 15)
        np.testing.assert_array_equal(a['initial'], b['initial'])
        keys = []
        for mode in ('benchmark', 'prediction'):
            for split in ('train', 'test'):
                for cell in d.CELLS:
                    data = d.inputs(mode, split, range(16), cell)
                    self.assertTrue(d.support(data)); keys.extend(data['tail_keys'].reshape(-1, 8).tolist())
                    self.assertTrue((data['source_keys'][:, 0] == 33033).all())
                    if (mode, split) != ('prediction', 'train'):
                        self.assertFalse(np.array_equal(a['initial'], data['initial']))
        self.assertEqual(len(keys), len({tuple(k) for k in keys}))

    def test_future_inputs_are_removed_from_observation_inputs(self):
        finite, future, _ = self.example(); a = d.observation_inputs(future)
        poisoned = copy.deepcopy(future)
        poisoned['entrants'][..., 6:] = np.nan; poisoned['tail_uniforms'][:] = np.nan
        poisoned['tail_keys'][:] = 0
        poisoned['future_target'] = np.array(True)
        b = d.observation_inputs(poisoned)
        self.assertNotIn('tail_keys', a); self.assertNotIn('tail_uniforms', a)
        self.assertNotIn('future_target', b)
        self.assertEqual(a['entrants'].shape[2], 6)
        for key in a:
            np.testing.assert_array_equal(a[key], b[key]); self.assertTrue(np.isfinite(a[key]).all())
        shaped = a['entrants'].reshape(4, 9, 4, 6)
        for branch in range(9):
            np.testing.assert_array_equal(shaped[:, branch, :, 3:], shaped[:, 0, :, 3:])
            np.testing.assert_array_equal(shaped[:, branch, :, :3], np.repeat(finite['entrants'][:, branch, None], 4, axis=1))

    def test_feature_boundary_poison_fields_and_full_future_rejection(self):
        finite, _, observed = self.example(); table, rows = d.features(finite, observed)
        self.assertEqual({k: v.shape[1] for k, v in table.items()}, d.DIMENSIONS)
        poisoned = dict(observed, target=np.array(np.nan), future_target=np.array(True), tail_uniforms=np.array(np.nan))
        other, metadata = d.features(dict(finite, future_target=np.array(True)), poisoned)
        self.assertEqual(rows, metadata)
        for key in table:
            np.testing.assert_array_equal(table[key], other[key])
        with self.assertRaises(AssertionError):
            d.features(finite, synthetic_future(observed))
        np.testing.assert_array_equal(table['full6'][:, :194], table['raw6'])
        np.testing.assert_array_equal(table['full6'][:, 194:], table['persistence6'][:, 55:])

    def test_ablation_tail_order_and_network_fold(self):
        finite, _, observed = self.example(); table, rows = d.features(finite, observed)
        early = table['persistence3'].reshape(-1, 4, 99)
        np.testing.assert_array_equal(early, np.repeat(early[:, :1], 4, axis=1))
        self.assertFalse(np.array_equal(table['persistence6'][::4], table['persistence6'][3::4]))
        changed = copy.deepcopy(observed); changed['history'][..., 4:, :] += .2
        changed['entries'][..., 3:, :] -= .1
        after, metadata = d.features(finite, changed)
        np.testing.assert_array_equal(table['persistence3'], after['persistence3'])
        self.assertFalse(np.array_equal(table['persistence6'], after['persistence6']))
        self.assertEqual(rows, metadata)
        self.assertEqual([r['tail'] for r in rows], np.tile(np.arange(4), len(rows)//4).tolist())
        self.assertTrue(all(r['fold'] == r['source_id'] % 4 for r in rows))

    def test_both_prefixes_exact_and_sixth_step_fault_rejected(self):
        finite, _, observed = self.example(); short = synthetic_finite(finite)
        future = synthetic_future(observed)
        measure.prefix_parity(short, observed); measure.prefix_parity(short, future)
        measure.observation_parity(observed, future)
        future['history'][0, 0, 6, 0] += 1e-8
        measure.prefix_parity(short, future)
        with self.assertRaises(AssertionError):
            measure.observation_parity(observed, future)

    def test_complete_actual_decay_pipeline_and_clock_guard(self):
        with self.temporary() as directory:
            out = Path(directory); (out/'inputs').mkdir()
            spec = d.benchmark_specs()[0]; data = d.inputs('benchmark', 'train', spec['ids'], 0)
            data['weights'][:] = 0.; data['initial'][:] = 1.; data['entrants'][:] = -.15
            data['interval'] = np.array(.00625)
            np.savez_compressed(out/'inputs'/f'{spec["key"]}.npz', **data)
            seal(out, 'freeze.json', list((out/'inputs').iterdir()))
            item = dict(spec=spec, input_name=spec['key'])
            for mode in ('serial', 'parallel'):
                result = measure.benchmark_task(dict(item, out=str(out), name=spec['key']+'_'+mode))
                self.assertTrue(result['qualified'])
            self.assertGreater(compare_benchmarks(out, [item]), 250)
            folder = out/'raw'/(spec['key']+'_serial'); obs = load(folder/'observation_inputs.npz')
            raws = [load(folder/'observation'/f'raw_{i}.npz') for i in range(3)]
            expected = obs['entrants'][..., [5, 3, 4]]*np.exp(-.00625*np.array([1, 3, 2]))
            np.testing.assert_allclose(raws[-1]['history'][..., -1, :], expected, atol=1e-14, rtol=0)
            broken = copy.deepcopy(raws); broken[0]['dt'] = np.array(.00625)
            self.assertFalse(measure.audit(broken, obs, 'observation')['qualified'])

    def evaluation_inputs(self, n=16):
        rows = [dict(cell=cell, selection=selection, source_id=i, probe_id=0 if selection == d.SELECTIONS[0] else 7,
                     branch=b, tail=tail, actual_fraction=d.FRACTIONS[(b-1)//4], capped=False)
                for cell in d.CELLS for selection in d.SELECTIONS for i in range(n) for b in range(1, 9) for tail in range(4)]
        target = np.zeros((6*n, 9, 4), bool); target[:, 5:7] = True
        predictions = {name: np.full(len(rows), .2) for name in d.MODELS}
        predictions[d.CANDIDATE] = predict.flips(target).astype(float)
        bootstrap = d.rng([d.SEED, 9, 1]).integers(0, n, (d.BOOTSTRAPS, n))
        return predictions, target, rows, bootstrap

    def test_two_verdicts_one_family_and_strict_tie(self):
        p, y, rows, boot = self.evaluation_inputs()
        result = analysis.evaluate(p, y, rows, boot)
        self.assertEqual(result['qualified_representation_panels'], list(range(6)))
        self.assertEqual(result['qualified_observation_panels'], list(range(6)))
        self.assertEqual(len(result['forecast_family']), 30)
        p['same_observation'] = p[d.CANDIDATE].copy()
        tied = analysis.evaluate(p, y, rows, boot)
        self.assertEqual(tied['qualified_representation_panels'], [])
        self.assertEqual(tied['qualified_observation_panels'], list(range(6)))
        p[d.ABLATION] = p[d.CANDIDATE].copy()
        self.assertEqual(analysis.evaluate(p, y, rows, boot)['qualified_observation_panels'], [])
        y[:] = False
        empty = analysis.evaluate(p, y, rows, boot)
        self.assertEqual(empty['qualified_observation_panels'], [])
        self.assertTrue(all(not panel['informative'] for panel in empty['panels']))

    def test_network_bootstrap_matches_independent_calculation(self):
        p, target, rows, boot = self.evaluation_inputs()
        g = d.rng([d.SEED, 9, 2]); y = predict.flips(target)
        for name in p:
            p[name] = g.uniform(0, 1, len(y))
        result = analysis.evaluate(p, target, rows, boot); contrasts = []
        for panel in range(6):
            take = slice(panel*16*32, (panel+1)*16*32)
            candidate = ((p[d.CANDIDATE][take]-y[take])**2).reshape(16, 32).mean(axis=1)
            for comparator in (*d.COMPARATORS, d.ABLATION):
                loss = ((p[comparator][take]-y[take])**2).reshape(16, 32).mean(axis=1)
                contrasts.append(loss-candidate)
        contrasts = np.array(contrasts); point = contrasts.mean(axis=1)
        radius = np.quantile([np.max(abs(contrasts[:, sample].mean(axis=1)-point)) for sample in boot], .95)
        np.testing.assert_allclose(result['simultaneous_radius'], radius, atol=2e-15)
        np.testing.assert_allclose([r['improvement'] for r in result['forecast_family']], point)
        wrong = copy.deepcopy(rows); wrong[0]['tail'] = 3
        with self.assertRaises(AssertionError):
            analysis.evaluate(p, target, wrong, boot)

    def test_train_only_scaling_and_nested_comparator_can_tie(self):
        g = d.rng([d.SEED, 9, 3]); x = g.normal(size=(32, 3)); q = (x[:, 0] > 0).astype(float); fold = np.arange(32) % 4
        train = dict(persistence6=x, full6=x.copy())
        a = predict.fit_one(d.CANDIDATE, train, q, fold, dict(persistence6=np.zeros((4, 3))))
        b = predict.fit_one(d.CANDIDATE, train, q, fold, dict(persistence6=np.full((4, 3), 100.)))
        self.assertEqual(a['model'], b['model']); self.assertEqual(a['selected'], b['selected'])
        np.testing.assert_allclose(a['model']['mean'], x.mean(axis=0)); self.assertEqual(a['fits'], 17)
        same = predict.fit_one('same_observation', train, q, fold, dict(persistence6=np.zeros((4, 3)), full6=np.zeros((4, 3))))
        self.assertEqual(same['fits'], 33)
        np.testing.assert_array_equal(a['prediction'], same['prediction'])

    def test_synthetic_118_fit_sealing_targets_report_and_tamper(self):
        with self.temporary() as directory:
            out = Path(directory); (out/'inputs').mkdir(); (out/'raw').mkdir()
            specs = d.task_specs(8); tasks = tasks_for(out, specs)
            save(out/'config.json', dict(specs=specs, tasks=tasks, sources_per_split=8))
            np.savez_compressed(out/'bootstrap.npz', indices=d.rng([d.SEED, 9, 4]).integers(0, 8, (d.BOOTSTRAPS, 8)))
            for spec in specs:
                np.savez_compressed(out/'inputs'/f'{spec["key"]}.npz', **d.inputs(spec['mode'], spec['split'], spec['ids'], spec['cell']))
            seal(out, 'freeze.json', sorted(p for p in out.rglob('*') if p.is_file()))
            for spec in specs:
                data = load(out/'inputs'/f'{spec["key"]}.npz'); folder = out/'raw'/('probe_'+spec['key']); folder.mkdir()
                for level, raw in enumerate(synthetic_probes(data)):
                    np.savez_compressed(folder/f'raw_{level}.npz', **raw)
                save(folder/'audit.json', dict(qualified=True, synthetic_fixture=True))
            seal(out, 'probe_sha256.json', sorted(p for p in (out/'raw').rglob('*') if p.is_file()))
            predict.derive_inputs(out)
            for kind in ('finite', 'observation'):
                paths = []
                for spec in specs:
                    data = load(out/'derived'/spec['key']/'finite.npz'); folder = out/'raw'/(kind+'_'+spec['key']); folder.mkdir()
                    for level in range(3):
                        raw = synthetic_finite(data, level)
                        if kind == 'observation':
                            raw = synthetic_observation(raw, load(out/'derived'/spec['key']/'observation.npz'))
                        np.savez_compressed(folder/f'raw_{level}.npz', **raw)
                    save(folder/'audit.json', dict(qualified=True, matched_prefix_verified=True, synthetic_fixture=True))
                    paths.extend(folder.iterdir())
                seal(out, kind+'_sha256.json', sorted(paths))
            predict.make_features(out)
            with self.assertRaises(FileNotFoundError):
                predict.submit_test(out, 3)
            def future_group(split):
                paths = []
                for item in tasks[split]:
                    folder = out/'raw'/item['name']; folder.mkdir()
                    observed = load(out/'raw'/('observation_'+item['spec']['key'])/'raw_2.npz')
                    np.savez_compressed(folder/'raw_2.npz', **synthetic_future(observed))
                    save(folder/'audit.json', dict(qualified=True, matched_prefix_verified=True, matched_observation_verified=True,
                        entrants_within_original_support=True, synthetic_fixture=True)); paths.extend(folder.iterdir())
                seal(out, split+'_sha256.json', sorted(paths))
            future_group('train'); target = predict.targets(out, 'train')
            np.savez_compressed(out/'targets_train.npz', target=target, flip=predict.flips(target))
            paths = [out/p for p in json.loads((out/'train_sha256.json').read_text())]
            seal(out, 'train_sha256.json', paths+[out/'targets_train.npz'])
            fits = [predict.fit_task(dict(out=str(out), name=name)) for name in d.MODELS]
            self.assertEqual(sum(r['fits'] for r in fits), 118)
            predict.seal_predictions(out); predict.submit_test(out, 3); measure.require_test_seal(out)
            with self.assertRaises(AssertionError):
                predict.make_features(out)
            with self.assertRaises(AssertionError):
                predict.seal_predictions(out)
            submitted = json.loads((out/'TEST_SUBMISSION.json').read_text())
            save(out/'TEST_SUBMISSION.json', dict(submitted, submitted_utc=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()))
            with self.assertRaises(AssertionError):
                measure.require_test_seal(out)
            save(out/'TEST_SUBMISSION.json', submitted); future_group('test')
            result = analysis.closeout(out)
            self.assertEqual(len(result['forecast_family']), 30)
            self.assertTrue((out/'REPORT.md').is_file() and (out/'overview.pdf').is_file())
            path = out/'models/persistence6/predictions.npz'; path.write_bytes(path.read_bytes()+b'tamper')
            with self.assertRaises(AssertionError):
                measure.require_test_seal(out)


if __name__ == '__main__':
    unittest.main()
