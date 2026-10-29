"""Controls for selection, state restoration, observer clocks and error accounting."""
import csv
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from h007.io import save
from h022 import numerics
from h034 import design as d, measure, analysis


def copy_arrays(data):
    return {key: value.copy() for key, value in data.items()}


class H034Fixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = [dict(split='train', cell=0, source_id=i, probe_id=1,
            tail=i, branch=5, selection=d.SELECTIONS[1], row_index=i) for i in range(2)]
        data = d.future(cls.rows, 0, benchmark=True)
        data.update(benchmark=np.array(True), row_index=np.arange(2), cell=np.array(0),
            global_initial_identities=np.array([9, 7, 8]), interval=np.array(.0125),
            weights=np.broadcast_to(np.eye(3)*.2+.05, (4, 3, 3)).copy(),
            original_initial=np.broadcast_to([.7, .8, .9], (4, 3)).copy())
        data['prefix_entrants'] = np.repeat(-.05-.25*d.rng([987]).random((2, 6)), 2, axis=0)
        data['prefix_entrants'][1::2, 0] += .001
        data['archive_entrants'] = data['entrants'][:, 0].copy()
        cls.full, cls.raws = [], []
        for level, dt in enumerate(d.DTS):
            original = dict(initial=data['original_initial'], weights=data['weights'],
                entrants=np.concatenate((data['prefix_entrants'], data['archive_entrants']), axis=-1)[:, None])
            full = numerics.simulate(original, dt, 24, float(data['interval']))
            cls.full.append(full)
            data[f'initial_{level}'] = full['history'][:, 0, 6].copy()
            data[f'prefix_history_{level}'] = full['history'][:, 0, :7].copy()
            data[f'prefix_entries_{level}'] = full['entries'][:, 0, :6].copy()
            data[f'archive_history_{level}'] = full['history'][:, 0, 6:].copy()
            data[f'archive_entries_{level}'] = full['entries'][:, 0, 6:].copy()
        terminal = (np.tanh(2*data['initial_2']).reshape(2, 2, 3) > .5).all(axis=-1)
        data['early_disagreement'] = terminal[:, 0] != terminal[:, 1]
        d.validate(data)
        cls.data = data
        cls.raws = [measure.simulate(data, level) for level in range(3)]

    def test_future_streams_pair_and_preserve_duplicate_contexts(self):
        duplicate = [self.rows[0], dict(self.rows[0], branch=8, selection=d.SELECTIONS[0])]
        same = d.future(duplicate, 0)
        np.testing.assert_array_equal(same['future_keys'][0], same['future_keys'][1])
        np.testing.assert_array_equal(same['entrants'][0], same['entrants'][3])
        others = [d.future([dict(self.rows[0], split='test')], 0),
                  d.future([dict(self.rows[0], tail=3)], 0),
                  d.future([self.rows[0]], 0, benchmark=True)]
        for other in others:
            self.assertFalse(np.array_equal(same['future_keys'][0], other['future_keys'][0]))
        self.assertEqual(len(np.unique(same['future_keys'][0], axis=0)), 32)

    def test_sampling_census_and_controls_use_early_labels_only(self):
        rows = [dict(cell=cell, selection=selection, source_id=i, final_outcome=bool(i % 2))
                for cell in d.CELLS for selection in d.SELECTIONS for i in range(6)]
        early = np.array([row['source_id'] < 2 for row in rows])
        selected, panels = d.choose(rows, early, 'test', controls=2)
        self.assertEqual(len(selected), 24)
        self.assertEqual(sum(row['early_disagreement'] for row in selected), 12)
        self.assertTrue(all(p['controls'] == 2 and p['early_disagreement'] == 2 for p in panels))
        changed = [dict(row, final_outcome=not row['final_outcome']) for row in rows]
        again, _ = d.choose(changed, early, 'test', controls=2)
        self.assertEqual([r['row_index'] for r in selected], [r['row_index'] for r in again])
        self.assertEqual(len({r['row_index'] for r in selected}), len(selected))

    def test_input_corruption_is_rejected(self):
        for name in ('entrants', 'future_uniforms', 'initial_2', 'weights'):
            broken = copy_arrays(self.data); broken[name].flat[0] += .0001
            with self.assertRaises(AssertionError, msg=name):
                d.validate(broken)

    def test_resume_matches_full_origin_at_every_resolution(self):
        for level, raw in enumerate(self.raws):
            self.assertTrue(measure.audit_one(raw, self.data, level)['qualified'])
            np.testing.assert_array_equal(raw['history'][:, -1], self.full[level]['history'][:, 0, 6:])
            np.testing.assert_array_equal(raw['entries'][:, -1], self.full[level]['entries'][:, 0, 6:])
            np.testing.assert_array_equal(raw['global_identities'], self.full[level]['identities'][6:])
            np.testing.assert_array_equal(raw['window_target'][:, -1], self.full[level]['target'][:, 0])

    def test_wrong_phase_is_refused(self):
        with patch.object(d, 'START', 5):
            with self.assertRaises(AssertionError):
                measure.simulate(self.data, 0)

    def test_clock_identity_observer_and_archive_faults_detected(self):
        for field in ('dt', 'global_endpoints', 'global_identities', 'window_target'):
            broken = copy_arrays(self.raws[0])
            if broken[field].dtype == bool:
                broken[field].flat[0] = ~broken[field].flat[0]
            else:
                broken[field].flat[0] += 1
            self.assertFalse(measure.audit_one(broken, self.data, 0)['qualified'], field)
        broken = copy_arrays(self.data); broken['archive_history_0'].flat[-1] += 1e-12
        self.assertFalse(measure.audit_one(self.raws[0], broken, 0)['archived_full_origin_replay_exact'])
        broken = copy_arrays(self.data); broken['initial_0'].flat[0] += 1e-12
        self.assertFalse(measure.audit_one(self.raws[0], broken, 0)['saved_endpoint_exact'])

    def test_scoring_window_absolute_clock_and_strict_threshold(self):
        history = np.ones((2, 1, 19, 3))
        history[..., :7, :] = -1.
        self.assertTrue(measure.window_target(history).all())
        boundary = np.arctanh(.5)/2
        self.assertEqual(float(np.tanh(2*boundary)), .5)
        history[0, 0, 7, 0] = boundary
        history[1, 0, 18, 2] = -1.
        self.assertFalse(measure.window_target(history).any())
        with self.assertRaises(AssertionError):
            measure.window_target(np.ones((2, 1, 25, 3)))

    def test_four_observer_categories_and_gain_loss(self):
        history = np.ones((8, 32, 19, 3)); history[..., 14, 0] = 0.
        history[3, :, 14, 1] = 0.
        history[5, :, 9, 1] = 0.
        history[7, :, 14, 0] = 1.
        values = measure.outcomes(history)
        np.testing.assert_array_equal(values['category'], np.repeat(np.arange(4)[:, None], 32, axis=1))
        self.assertEqual(values['flip'].sum(), 32)
        self.assertEqual(values['gain'].sum(), 32)
        self.assertEqual(values['loss'].sum(), 0)
        self.assertTrue(values['both_fail'][1:3].all())
        reversed_values = measure.outcomes(history.reshape(4, 2, 32, 19, 3)[:, ::-1].reshape(8, 32, 19, 3))
        np.testing.assert_array_equal(values['gain'], reversed_values['loss'])

    def test_first_new_disagreement_uses_absolute_endpoint(self):
        history = np.ones((2, 32, 19, 3))
        history[1, :16, 1, 0] = 0.
        first = measure.outcomes(history)['first_endpoint_disagreement']
        np.testing.assert_array_equal(first[0], [7]*16+[0]*16)

    def test_identical_restored_states_never_diverge_under_common_future(self):
        data = copy_arrays(self.data); data['benchmark'] = np.array(False)
        for level in range(3):
            data[f'initial_{level}'][1::2] = data[f'initial_{level}'][::2]
        raw = measure.simulate(data, 0)
        np.testing.assert_array_equal(raw['history'][::2], raw['history'][1::2])
        self.assertFalse(measure.outcomes(raw['history'])['flip'].any())

    def test_variance_and_excess_are_unbiased_over_all_bernoulli_samples(self):
        y = np.array(list(itertools.product((False, True), repeat=3)))
        q, p = .25, .7
        probability = q**y.sum(axis=1)*(1-q)**(~y).sum(axis=1)
        result = analysis.decompose(y, np.full((8, 1), p))
        self.assertAlmostEqual(np.sum(result['conditional_variance']*probability), q*(1-q))
        self.assertAlmostEqual(np.sum(result['excess_squared_error'][:, 0]*probability), (p-q)**2)

    def test_negative_monte_carlo_excess_is_not_clipped(self):
        y = np.array([[False, True], [False, False], [True, True]])
        values = analysis.decompose(y, np.full((3, 1), .5))
        np.testing.assert_array_equal(values['conditional_variance'], [.5, 0., 0.])
        self.assertEqual(values['excess_squared_error'][0, 0], -.25)
        np.testing.assert_array_equal(values['brier'][:, 0], [.25, .25, .25])

    def test_report_csv_figures_and_dependent_source_counts(self):
        cache = Path(__file__).resolve().parent.parent/'.cache'
        cache.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='h034_fixtures_', dir=cache) as temporary:
            out = Path(temporary); (out/'inputs').mkdir(); tasks = []
            for split in ('train', 'test'):
                for cell in d.CELLS:
                    rows = [dict(row_index=4*d.CELLS.index(cell)+j, source_id=j % 2,
                        probe_id=0, branch=1, tail=0, split=split, cell=cell,
                        selection=d.SELECTIONS[j//2], early_disagreement=bool(j % 2),
                        inclusion_probability=1.) for j in range(4)]
                    name = f'{split}_{cell}'; folder = out/'raw'/name; folder.mkdir(parents=True)
                    history = np.ones((8, 32, 19, 3)); history[1::2, :16, 10, 0] = -1.
                    values = measure.outcomes(history)
                    for level in range(3):
                        np.savez_compressed(folder/f'raw_{level}.npz', history=history)
                    np.savez_compressed(folder/'outcomes.npz', **values)
                    save(folder/'audit.json', dict(qualified=True))
                    np.savez_compressed(out/'inputs'/f'{name}.npz', saved_forecasts=np.full((4, 6), .3),
                        early_disagreement=np.array([r['early_disagreement'] for r in rows]),
                        row_index=np.array([r['row_index'] for r in rows]))
                    tasks.append(dict(name=name, split=split, rows=rows))
            result = analysis.assemble(out, dict(tasks=tasks))
            self.assertEqual(result['finding'], 'CONDITIONAL_FUTURE_VARIATION_OBSERVED')
            group = result['cohorts']['test']['strata']['early_disagreement']
            self.assertEqual(group['prefixes'], 6)
            self.assertEqual(group['source_networks'], 1)
            self.assertEqual(group['mixed_prefixes'], 6)
            with (out/'prefixes_test.csv').open() as stream:
                records = list(csv.DictReader(stream))
            self.assertEqual(len(records), 12)
            self.assertEqual(float(records[0]['flip_count']), 16.)
            self.assertTrue((out/'overview.png').stat().st_size > 1000)
            self.assertTrue((out/'overview.pdf').stat().st_size > 1000)
            self.assertEqual(json.loads((out/'diagnosis.json').read_text())['models_refitted'], False)


if __name__ == '__main__':
    unittest.main(verbosity=2)
