import unittest

import numpy as np

from run_onward_transfer import assemble_contact, donor_source, retained_label


class OnwardTransferTests(unittest.TestCase):
    def test_source_mapping(self):
        self.assertEqual(donor_source("E", "learned"), "m_pulse")
        self.assertEqual(donor_source("M", "learned"), "e_pulse")
        self.assertEqual(donor_source("E", "blocked"), "m_pulse")
        self.assertEqual(donor_source("E", "origin"), "m_naive")
        self.assertEqual(donor_source("M", "same_state"), "m_naive")
        self.assertIsNone(donor_source("E", "alone"))
        with self.assertRaises(ValueError):
            donor_source("X", "alone")
        with self.assertRaises(ValueError):
            donor_source("E", "unknown")

    def test_donor_never_replaces_fresh_recipient(self):
        fresh = np.arange(17.)[:, None]
        donor = fresh + 100
        contact = assemble_contact(fresh, donor)
        np.testing.assert_array_equal(contact[:, :1], fresh)
        np.testing.assert_array_equal(contact[:, 1:], donor)
        contact[0, :] = -1
        self.assertEqual(fresh[0, 0], 0)
        self.assertEqual(donor[0, 0], 100)

    def test_alone_is_independent_copy(self):
        fresh = np.zeros((17, 1))
        contact = assemble_contact(fresh)
        contact[0, 0] = 1
        self.assertEqual(fresh[0, 0], 0)
        self.assertEqual(contact.shape, (17, 1))

    def test_no_implicit_multiple_donors(self):
        fresh = np.zeros((17, 1))
        with self.assertRaises(ValueError):
            assemble_contact(fresh, np.zeros((17, 5)))
        with self.assertRaises(ValueError):
            assemble_contact(np.zeros((17, 2)))

    def test_retention_requires_both_holds_and_shadow(self):
        hold = {"recipient_label": "E", "late_label_fractions": {"E": 1.}}
        low_fraction = {"recipient_label": "E", "late_label_fractions": {"E": .94}}
        self.assertTrue(retained_label("E", [hold, hold], "E", .95))
        self.assertFalse(retained_label("E", [hold, low_fraction], "E", .95))
        self.assertFalse(retained_label("E", [hold, hold], "M", .95))
        self.assertFalse(retained_label("X", [hold, hold], "X", .95))


if __name__ == "__main__":
    unittest.main()
