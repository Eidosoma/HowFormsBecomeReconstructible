import unittest
import numpy as np
from core import binary, joint, summarize_joint, markov, classify, brier


class DiagnosticTests(unittest.TestCase):
    def test_retest_recovery_without_renewal_benefit(self):
        s = summarize_joint(joint([0]*4, [1,1,1,0], [1,1,1,0]))
        self.assertEqual(s['writer_fail']['successor_rate'], .75)
        self.assertEqual(s['writer_fail']['paired_benefit'], 0)

    def test_help_and_harm_must_both_count(self):
        s = summarize_joint(joint([0]*4, [1,1,0,0], [0,0,1,0]))['writer_fail']
        self.assertEqual((s['helped'], s['harmed'], s['paired_benefit']), (2,1,.25))

    def test_absent_state_is_not_zero_recovery(self):
        s = summarize_joint(joint([1,1], [1,1], [1,1]))
        self.assertIsNone(s['writer_fail']['paired_benefit'])
        m = markov([1,1], [1,1])
        self.assertTrue(m['prior_only_recovery'])
        self.assertIsNone(m['empirical_recovery'])
        self.assertEqual(m['recovery'], .5)

    def test_pairing_and_binary_contract(self):
        with self.assertRaises(ValueError): joint([0,1],[1],[0,1])
        with self.assertRaises(ValueError): binary([0,2])
        with self.assertRaises(ValueError): binary([])

    def test_same_marginal_can_have_different_transitions(self):
        # Both have W success 1/2 and successor success 1/2, but different coupling.
        a = markov([0,0,1,1],[0,0,1,1])
        b = markov([0,0,1,1],[1,1,0,0])
        self.assertEqual(a['p0'], b['p0'])
        self.assertNotEqual(a['recovery'], b['recovery'])
        self.assertNotEqual(a['uninterrupted'], b['uninterrupted'])

    def test_horizon_is_transitions_not_number_of_reads(self):
        a = markov([0,0,1,1],[0,1,1,1], horizon=18)
        self.assertEqual(len(a['trajectory']), 19)
        z = markov([0,0,1,1],[0,1,1,1], horizon=0)
        self.assertEqual(z['terminal'], z['p0'])

    def test_original_rule_required_and_strict_threshold(self):
        pattern = np.array([[1.,-1.],[-1.,1.]])
        x = np.broadcast_to(.5*pattern, (3,32,1,2,2)).copy()
        x[1] *= -1
        x[2] *= .5
        c,_ = classify(x, 1)
        np.testing.assert_array_equal(c, [1,-1,0])
        c,_ = classify(x, -1)
        np.testing.assert_array_equal(c, [-1,1,0])

    def test_all_four_entries_required(self):
        x = np.broadcast_to(.5*np.array([[1.,-1.],[-1.,1.]]), (1,32,1,2,2)).copy()
        x[:,:,:,0,0] = 0
        c,_ = classify(x, 1)
        self.assertEqual(c.tolist(), [0])

    def test_brier_on_individual_futures(self):
        self.assertEqual(brier(.5,[0,1]), .25)
        self.assertNotEqual(brier(.5,[0,1]), (.5-.5)**2)


if __name__ == '__main__':
    unittest.main()
