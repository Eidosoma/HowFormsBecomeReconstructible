import json
from pathlib import Path
import unittest

import numpy as np

from run_renewal import carry_donors, founder_names, replace_packet


class RenewalTests(unittest.TestCase):
    def test_fixed_lineage_design(self):
        config = json.loads((Path(__file__).resolve().parents[1] / "configs/renewal_v1.json").read_text())
        self.assertEqual(len(config["cases"]), 8)
        self.assertEqual(config["rounds"], 3)
        self.assertEqual(config["packet_size"], 2)
        self.assertEqual(sum(case.get("fine", False) for case in config["cases"]), 2)

    def test_correct_founders(self):
        self.assertEqual(founder_names({"state": "E", "history": "learned"}), ["m_pulse_01", "m_pulse_02"])
        self.assertEqual(founder_names({"state": "M", "history": "blocked"}), ["e_pulse_01", "e_pulse_02"])
        self.assertEqual(founder_names({"state": "E", "history": "ordinary"}), ["e_naive_01", "e_naive_02"])
        with self.assertRaises(ValueError):
            founder_names({"state": "E", "history": "unknown"})

    def test_only_evolved_donors_are_carried_to_second_write(self):
        contact = np.arange(51.).reshape(17, 3)
        donors = carry_donors(contact)
        np.testing.assert_array_equal(donors, contact[:, 1:])
        donors[0, 0] = -1
        self.assertEqual(contact[0, 1], 1)
        with self.assertRaises(ValueError):
            carry_donors(np.zeros((17, 2)))

    def test_old_ids_cannot_reenter(self):
        cells = [np.zeros((17, 1)), np.ones((17, 1))]
        for ids in (["old", "new"], ["new", "new"], ["new"]):
            with self.assertRaises(ValueError):
                replace_packet({"old", "older"}, ids, cells)

    def test_only_two_new_checkpoints_form_packet(self):
        cells = [np.zeros((17, 1)), np.ones((17, 1))]
        packet = replace_packet({"old_a", "old_b"}, ["new_a", "new_b"], cells)
        np.testing.assert_array_equal(packet[:, :1], cells[0])
        np.testing.assert_array_equal(packet[:, 1:], cells[1])
        cells[0][:] = 100  # Changing a diagnostic/child array cannot repair the packet.
        self.assertTrue(np.all(packet[:, 0] == 0))
        with self.assertRaises(ValueError):
            replace_packet(set(), ["a", "b"], [np.zeros((17, 2)), np.zeros((17, 1))])


if __name__ == "__main__":
    unittest.main()
