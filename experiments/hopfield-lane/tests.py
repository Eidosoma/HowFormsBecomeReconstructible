"""Scientific invariants and a scalar reference, not outcome-target tests."""
import unittest
import numpy as np
import model as m
import run


class ModelTests(unittest.TestCase):
    def test_asynchronous_scalar_reference_and_energy(self):
        random = np.random.default_rng(91)
        w = m.symmetric(random.normal(size=(9, 9)))
        x = random.choice([-1., 1.], size=9)
        x[0] = 1
        initial = x.copy()
        orders = np.stack([random.permutation(9) for _ in range(7)])
        energies = [float(m.energy(x, w))]
        for order in orders:
            for i in order:
                if i == 0:
                    continue
                h = sum(float(w[i, j]*x[j]) for j in range(9))
                x[i] = 1 if h > 0 else -1 if h < 0 else x[i]
                energies.append(float(m.energy(x, w)))
        np.testing.assert_array_equal(m.relax(w, initial, orders, [0]), x)
        self.assertLessEqual(max(np.diff(energies)), 1e-12)

    def test_zero_field_retains_state(self):
        x = np.array([-1., 1., -1.])
        np.testing.assert_array_equal(m.relax(np.zeros((3, 3)), x, [[0, 1, 2]]), x)

    def test_writer_only_uses_body_and_has_no_aliases(self):
        body = np.array([[1., -1., 1.], [-1., 1., 1.]])
        record = m.write_body(body)
        expected = sum(np.outer(row, row) for row in body)/6
        np.fill_diagonal(expected, 0)
        np.testing.assert_array_equal(record, expected)
        body.fill(0)
        np.testing.assert_array_equal(record, expected)
        np.testing.assert_array_equal(m.write_body(body), np.zeros((3, 3)))

    def test_organization_controls(self):
        random = np.random.default_rng(18)
        w = m.symmetric(random.normal(size=(8, 8)))
        permutation = random.permutation(8)
        shuffled = m.permute_record(w, permutation)
        np.testing.assert_allclose(np.linalg.eigvalsh(w), np.linalg.eigvalsh(shuffled), atol=1e-12)
        damaged = m.corrupted_record(w, random)
        np.testing.assert_allclose(np.linalg.norm(damaged), np.linalg.norm(w))
        np.testing.assert_allclose(np.sum(damaged*w)/np.sum(w*w), .3)
        np.testing.assert_array_equal(damaged, damaged.T)
        mask = m.mask_edges(random, (3, 8, 8), .5)
        np.testing.assert_array_equal(mask, mask.swapaxes(-1, -2))
        self.assertFalse(np.diagonal(mask, axis1=-2, axis2=-1).any())

    def test_graded_energy_and_refinement(self):
        w = np.full((3, 3), .4)
        np.fill_diagonal(w, 1.2)
        initial = np.array([.06, .1, -1.5])
        coarse = m.graded_flow(initial, w, 3., .025, trace=True)
        fine = m.graded_flow(initial, w, 3., .0125, trace=True)
        self.assertLessEqual(np.diff(m.graded_energy(coarse, w)).max(), 1e-10)
        np.testing.assert_allclose(coarse, fine[::2], atol=2e-7, rtol=0)

    def test_relay_replaces_actual_members(self):
        w = np.eye(3)*1.2
        history, entries, ids = run.relay(np.ones(3), w, .025, -1.5, "open", count=6)
        self.assertFalse(np.isin(ids[-1], ids[0]).any())
        for g in range(6):
            survivor = np.arange(3) != g % 3
            np.testing.assert_array_equal(entries[g, survivor], history[g, survivor])
            np.testing.assert_array_equal(ids[g+1, survivor], ids[g, survivor])
        self.assertTrue((history[-1] < 0).all())


if __name__ == "__main__":
    unittest.main(verbosity=2)
