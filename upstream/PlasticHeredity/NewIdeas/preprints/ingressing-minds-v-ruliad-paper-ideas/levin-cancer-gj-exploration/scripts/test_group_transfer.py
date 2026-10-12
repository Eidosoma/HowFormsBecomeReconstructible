import json
from pathlib import Path
import unittest

import numpy as np

from run_group_transfer import assemble_group, donor_ids, donor_qualified, make_bank_cases, make_cases


class GroupTransferTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((Path(__file__).resolve().parents[1] / "configs" / "group_transfer_v1.json").read_text())

    def test_grid_is_fixed_and_unique(self):
        cases = make_cases(self.config)
        self.assertEqual(len(cases), 28)
        self.assertEqual(len({case["id"] for case in cases}), 28)
        self.assertEqual(sum(case.get("fine", False) for case in cases), 6)
        self.assertEqual(len(make_bank_cases(self.config)), 20)

    def test_invalid_grid_rejected(self):
        for key, value in (("donor_counts", [1, 6]), ("donor_counts", [1, 1]), ("fine_counts", [4])):
            with self.assertRaises(ValueError):
                make_cases(dict(self.config, **{key: value}))

    def test_donor_histories_are_nested_and_correct(self):
        case = {"learned_state": "E", "history": "learned", "donors": 3}
        self.assertEqual(donor_ids(case), ["m_pulse_01", "m_pulse_02", "m_pulse_03"])
        self.assertEqual(donor_ids(dict(case, donors=1)), donor_ids(case)[:1])
        self.assertEqual(donor_ids(dict(case, history="same_state")), ["e_naive_01", "e_naive_02", "e_naive_03"])
        self.assertEqual(donor_ids(dict(case, history="alone", donors=0)), [])
        with self.assertRaises(ValueError):
            donor_ids(dict(case, history="alone"))

    def test_target_not_overwritten_and_donors_separate(self):
        fresh = np.zeros((17, 1))
        donors = [np.full((17, 1), i) for i in (1., 2., 3.)]
        group = assemble_group(fresh, donors)
        np.testing.assert_array_equal(group[0], [0., 1., 2., 3.])
        group[:] = 9
        self.assertTrue(np.all(fresh == 0))
        self.assertTrue(np.all(donors[1] == 2))
        self.assertEqual(assemble_group(fresh, []).shape, (17, 1))
        with self.assertRaises(ValueError):
            assemble_group(fresh, [np.zeros((17, 2))])

    def test_donor_qualification_rejects_failed_learning(self):
        result = {"execution_pass": True, "expected_label_sequence": True,
                  "case": {"history": "pulse"}, "donor_independent_acquired_recoverable_state": True}
        self.assertTrue(donor_qualified(result))
        self.assertFalse(donor_qualified(dict(result, donor_independent_acquired_recoverable_state=False)))
        self.assertFalse(donor_qualified(dict(result, execution_pass=False)))
        self.assertFalse(donor_qualified(dict(result, expected_label_sequence=False)))

    def test_naive_qualification_requires_retention_and_recovery(self):
        result = {"execution_pass": True, "expected_label_sequence": True, "case": {"history": "naive"},
                  "retained_written_label": True, "recovery": {"recovered": True}}
        self.assertTrue(donor_qualified(result))
        self.assertFalse(donor_qualified(dict(result, retained_written_label=False)))
        self.assertFalse(donor_qualified(dict(result, recovery={"recovered": False})))


if __name__ == "__main__":
    unittest.main()
