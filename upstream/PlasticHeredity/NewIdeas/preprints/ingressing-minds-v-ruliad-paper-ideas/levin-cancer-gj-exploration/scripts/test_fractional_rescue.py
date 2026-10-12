import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from analyze_fractional_rescue import audit_intervention, grid_summary
from memory_metrics import REGULATORS, classify
from run_fractional_rescue import PAIRS, edit_fraction, validate_config
from run_pair_regulator import edit_subset


class FractionalRescueTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((Path(__file__).resolve().parents[1] / "configs/fractional_rescue_v1.json").read_text())
        self.indices = dict(zip(REGULATORS, (5, 6, 7)))
        self.later = np.ones((17, 2))
        self.later[5:8] = [[84, 9], [6, 69], [.4, 63]]
        self.erased = self.later[:, 1, None].repeat(2, axis=1)

    def test_fixed_grid(self):
        validate_config(self.config)
        self.assertEqual(len(self.config["cases"]), 15)
        self.assertEqual(sum(c.get("fine", False) for c in self.config["cases"]), 6)
        self.assertEqual(sum(c["fraction"] == 0 for c in self.config["cases"]), 1)

    def test_changed_grid_rejected(self):
        for key, value in (("workers", 3), ("cases", self.config["cases"][:-1]), ("inherited_wait", 0)):
            config = copy.deepcopy(self.config)
            config[key] = value
            with self.assertRaises(ValueError):
                validate_config(config)
        for key, value in (("fraction", .3), ("state", "M"), ("fine", True), ("targets", list(REGULATORS[:2]))):
            config = copy.deepcopy(self.config)
            config["cases"][1][key] = value
            with self.assertRaises(ValueError):
                validate_config(config)

    def test_exact_endpoints_match_previous_runner(self):
        for names in PAIRS.values():
            np.testing.assert_array_equal(edit_fraction(self.erased, self.later, self.indices, names, 0), self.erased)
            np.testing.assert_array_equal(edit_fraction(self.erased, self.later, self.indices, names, 1), edit_subset(self.erased, self.later, self.indices, names))
        np.testing.assert_array_equal(edit_fraction(self.erased, self.later, self.indices, [], 0), self.erased)

    def test_partial_edits_use_each_cells_actual_value(self):
        before = self.erased.copy()
        before[5:8, 1] *= 1.1
        original, ref = before.copy(), self.later.copy()
        for names in PAIRS.values():
            rows = [self.indices[n] for n in names]
            untouched = [i for i in range(17) if i not in rows]
            for fraction in (.25, .5, .75):
                edited = edit_fraction(before, self.later, self.indices, names, fraction)
                np.testing.assert_allclose(edited[rows] - before[rows], fraction * (self.later[rows, 0, None] - before[rows]), rtol=1e-14, atol=1e-14)
                np.testing.assert_array_equal(edited[untouched], before[untouched])
                self.assertFalse(np.shares_memory(before, edited))
        np.testing.assert_array_equal(before, original)
        np.testing.assert_array_equal(self.later, ref)

    def test_invalid_edits_rejected(self):
        names = PAIRS["e_mir_prot"]
        for fraction in (-.1, 1.1, float("nan"), float("inf"), True, "0.5"):
            with self.assertRaises(ValueError):
                edit_fraction(self.erased, self.later, self.indices, names, fraction)
        for targets in ([], REGULATORS[:2], REGULATORS, [REGULATORS[0]] * 2):
            with self.assertRaises(ValueError):
                edit_fraction(self.erased, self.later, self.indices, targets, .5)
        for packet in (-self.erased, self.erased * np.nan, self.erased[:, :1]):
            with self.assertRaises(ValueError):
                edit_fraction(packet, self.later, self.indices, names, .5)

    def test_grid_reports_only_sampled_success_and_nonmonotonicity(self):
        rows = [{"fraction": f, "relay_rescued": f in (.25, .75, 1)} for f in (0, .25, .5, .75, 1)]
        summary = grid_summary(rows)
        self.assertEqual(summary["smallest_tested_success"], .25)
        self.assertFalse(summary["sampled_outcomes_monotone"])
        self.assertEqual(summary["adjacent_failure_success_samples"], [[0, .25], [.5, .75]])
        self.assertIsNone(grid_summary([dict(r, relay_rescued=False) for r in rows])["smallest_tested_success"])
        self.assertEqual(grid_summary([dict(r, relay_rescued=True) for r in rows])["smallest_tested_success"], 0)

    def test_incomplete_or_duplicated_grid_rejected(self):
        rows = [{"fraction": f, "relay_rescued": False} for f in (0, .25, .5, .75, 1)]
        for bad in (rows[:-1], rows[:-1] + rows[:1]):
            with self.assertRaises(ValueError):
                grid_summary(bad)

    def fixture(self, fraction=.5):
        case = {"id": "synthetic", "state": "E", "history": "learned", "targets": list(PAIRS["e_mir_prot"]), "fraction": fraction}
        ids = ["replacement_a", "replacement_b"]
        edited = edit_fraction(self.erased, self.later, self.indices, case["targets"], fraction)
        after = self.erased.copy()  # Synthetic negative, not a simulated outcome.
        after[0] += .25
        data = {"endpoints.npz": {"before": self.erased.copy(), "edited": edited, "after_wait": after}}
        result = {"incoming_ids": ids, "outgoing_ids": ids, "target_names": case["targets"], "fraction": fraction,
            "sustained_forcing": False, "before_labels": "MM", "immediate_labels": "".join(classify(edited, self.indices)),
            "after_wait_labels": "MM", "carrier_rescued": False,
            "setups": [{"cells": 1, "edges": 0, "miRNA_kd": 0, "active": False}] * 2, "audits": []}
        for cell in (1, 2):
            name = f"cell_{cell}_wait"
            initial, final = edited[:, cell - 1:cell], after[:, cell - 1:cell]
            data[name + ".npz"] = {"initial": initial.copy(), "final": final, "raw_final": final,
                "times": np.array([1., 900.]), "concentrations": np.stack([initial, final])}
            result["audits"].append({"phase": name, "all_labels": "M", "late_label_fractions": {"E": 0., "M": 1., "X": 0.},
                "graph_edges": 0, "miRNA_kd": 0, "requested_horizon": 1000})
        return case, ids, data, result

    def audit_fixture(self, fixture):
        case, ids, data, result = fixture
        with patch("analyze_fractional_rescue.arrays", side_effect=lambda p: data[p.name]), patch.object(Path, "read_text", return_value=json.dumps(result)):
            return audit_intervention(Path("unused"), self.config, case, self.erased, ids, self.later, self.indices)

    def test_audit_accepts_valid_negative_and_transient_flip(self):
        for fraction in (.5, 1):
            _, row, checks, _ = self.audit_fixture(self.fixture(fraction))
            self.assertTrue(all(checks.values()), checks)
            self.assertFalse(row["carrier_rescued"])
            self.assertEqual(row["immediate_E_label_lost"], fraction == 1)

    def test_audit_rejects_wrong_fraction(self):
        fixture = self.fixture()
        fixture[3]["fraction"] = .75
        _, _, checks, _ = self.audit_fixture(fixture)
        self.assertFalse(checks["fraction_matches"])
        fixture = self.fixture()
        fixture[2]["endpoints.npz"]["edited"] = edit_fraction(self.erased, self.later, self.indices, fixture[0]["targets"], .75)
        _, _, checks, _ = self.audit_fixture(fixture)
        self.assertFalse(checks["exact_fractional_edit"])

    def test_audit_rejects_third_regulator_and_ionic_edits(self):
        for row in (6, 0):
            fixture = self.fixture()
            fixture[2]["endpoints.npz"]["edited"][row] += 1
            _, _, checks, _ = self.audit_fixture(fixture)
            self.assertFalse(checks["all_unselected_rows_preserved"])

    def test_audit_rejects_unequal_cell_fraction(self):
        fixture = self.fixture()
        fixture[2]["endpoints.npz"]["edited"][5, 1] += 1
        _, _, checks, _ = self.audit_fixture(fixture)
        self.assertFalse(checks["exact_fractional_edit"])

    def test_audit_rejects_false_carrier_rescue(self):
        fixture = self.fixture(1)
        fixture[3]["carrier_rescued"] = True
        _, _, checks, _ = self.audit_fixture(fixture)
        self.assertFalse(checks["carrier_rescue_recomputed"])


if __name__ == "__main__":
    unittest.main()
