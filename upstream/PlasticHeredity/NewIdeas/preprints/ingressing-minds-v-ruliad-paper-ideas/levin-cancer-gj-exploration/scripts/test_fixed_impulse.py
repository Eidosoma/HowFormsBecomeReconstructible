import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from analyze_fixed_impulse import audit_intervention
from memory_metrics import REGULATORS, classify
from run_fixed_impulse import calibrated_delta, edit_fixed, validate_config
from run_fractional_rescue import edit_fraction
from run_heterogeneous_start import BACKGROUNDS, vary_start


class FixedImpulseTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((Path(__file__).resolve().parents[1] / "configs/fixed_impulse_v1.json").read_text())
        self.indices = dict(zip(REGULATORS, (5, 6, 7)))
        self.later = np.ones((17, 2))
        self.later[5:8] = [[84, 9], [6, 69], [.4, 63]]
        self.original = self.later[:, 1, None].repeat(2, axis=1)
        self.varied = vary_start(self.original, self.indices, BACKGROUNDS["mixed"])

    def test_fixed_grid(self):
        validate_config(self.config)
        self.assertEqual(len(self.config["cases"]), 16)
        self.assertEqual(sum(c.get("fine", False) for c in self.config["cases"]), 4)

    def test_changed_calibration_or_grid_rejected(self):
        for key, value in (("workers", 3), ("cases", self.config["cases"][:-1]),
                           ("calibration_fraction", 1), ("anchor_column", 1), ("anchor_column", False)):
            config = copy.deepcopy(self.config)
            config[key] = value
            with self.assertRaises(ValueError):
                validate_config(config)
        for key, value in (("mode", "reference"), ("targets", list(REGULATORS)), ("fraction", .75), ("fine", True)):
            config = copy.deepcopy(self.config)
            config["cases"][1][key] = value
            with self.assertRaises(ValueError):
                validate_config(config)

    def test_identical_delta_in_every_background_and_column(self):
        delta = calibrated_delta(self.original, self.later, self.indices)
        np.testing.assert_allclose(delta, [56.25, -46.95], rtol=0, atol=1e-14)
        for factors in BACKGROUNDS.values():
            varied = vary_start(self.original, self.indices, factors)
            edited = edit_fixed(varied, self.later, self.original, self.indices, "fixed")
            np.testing.assert_array_equal(edited[[5, 7]], varied[[5, 7]] + delta[:, None])
            self.assertTrue((edited >= 0).all())

    def test_original_anchor_not_second_cell_or_mean(self):
        original = self.original.copy()
        original[5:8, 1] *= 1.1
        np.testing.assert_array_equal(calibrated_delta(original, self.later, self.indices),
                                      calibrated_delta(self.original, self.later, self.indices))

    def test_not_state_relative_on_varied_backgrounds(self):
        fixed = edit_fixed(self.varied, self.later, self.original, self.indices, "fixed")
        relative = edit_fraction(self.varied, self.later, self.indices, [REGULATORS[0], REGULATORS[2]], .75)
        self.assertFalse(np.array_equal(fixed[[5, 7]], relative[[5, 7]]))

    def test_preserves_prepared_mrna_other_rows_and_all_inputs(self):
        snapshots = [a.copy() for a in (self.original, self.varied, self.later)]
        changed = edit_fixed(self.varied, self.later, self.original, self.indices, "fixed")
        untouched = [i for i in range(17) if i not in (5, 7)]
        np.testing.assert_array_equal(changed[untouched], self.varied[untouched])
        self.assertFalse(np.array_equal(changed[6], self.original[6]))
        for original, snapshot in zip((self.original, self.varied, self.later), snapshots):
            np.testing.assert_array_equal(original, snapshot)
            self.assertFalse(np.shares_memory(changed, original))

    def test_controls_match_predecessor(self):
        np.testing.assert_array_equal(edit_fixed(self.varied, self.later, self.original, self.indices, "none"), self.varied)
        np.testing.assert_array_equal(edit_fixed(self.varied, self.later, self.original, self.indices, "reference"),
            edit_fraction(self.varied, self.later, self.indices, [REGULATORS[0], REGULATORS[2]], 1))

    def test_invalid_input_and_negative_impulse_rejected_without_clipping(self):
        for packet in (self.varied[:, :1], -self.varied, self.varied * np.nan):
            with self.assertRaises(ValueError):
                edit_fixed(packet, self.later, self.original, self.indices, "fixed")
        packet = self.varied.copy()
        packet[7] = 0
        with self.assertRaises(ValueError):
            edit_fixed(packet, self.later, self.original, self.indices, "fixed")
        with self.assertRaises(ValueError):
            edit_fixed(self.varied, self.later, self.original, self.indices, "unknown")
        for original in (self.original[:, :1], -self.original, self.original * np.inf):
            with self.assertRaises(ValueError):
                calibrated_delta(original, self.later, self.indices)

    def fixture(self):
        case = {"mode": "fixed", "targets": [REGULATORS[0], REGULATORS[2]]}
        ids = ["replacement_a", "replacement_b"]
        edited = edit_fixed(self.varied, self.later, self.original, self.indices, "fixed")
        after = self.original.copy()  # Synthetic negative outcome, not a simulation.
        data = {"endpoints.npz": {"before": self.varied.copy(), "edited": edited.copy(), "after_wait": after}}
        result = {"incoming_ids": ids, "outgoing_ids": ids, "target_names": case["targets"], "mode": "fixed",
            "calibration_fraction": .75, "anchor_column": 0,
            "calibrated_delta": calibrated_delta(self.original, self.later, self.indices).tolist(),
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
        with patch("analyze_fixed_impulse.arrays", side_effect=lambda p: data[p.name]), patch.object(Path, "read_text", return_value=json.dumps(result)):
            return audit_intervention(Path("unused"), self.config, case, self.varied, ids, self.later, self.indices, self.original)

    def test_independent_audit_accepts_valid_negative(self):
        _, row, checks, _ = self.audit_fixture(self.fixture())
        self.assertTrue(all(checks.values()), checks)
        self.assertFalse(row["carrier_rescued"])

    def test_audit_rejects_state_tailored_impulse(self):
        fixture = self.fixture()
        fixture[2]["endpoints.npz"]["edited"] = edit_fraction(self.varied, self.later, self.indices, fixture[0]["targets"], .75)
        _, _, checks, _ = self.audit_fixture(fixture)
        self.assertFalse(checks["exact_fixed_or_control_edit"])

    def test_audit_rejects_wrong_anchor_record(self):
        fixture = self.fixture()
        fixture[3]["anchor_column"] = 1
        _, _, checks, _ = self.audit_fixture(fixture)
        self.assertFalse(checks["calibration_matches_original_anchor"])

    def test_audit_rejects_third_regulator_or_ionic_edit(self):
        for row in (6, 0):
            fixture = self.fixture()
            fixture[2]["endpoints.npz"]["edited"][row] += 1
            _, _, checks, _ = self.audit_fixture(fixture)
            self.assertFalse(checks["all_unselected_rows_preserved"])

    def test_audit_rejects_second_cell_specific_delta(self):
        fixture = self.fixture()
        fixture[2]["endpoints.npz"]["edited"][5, 1] += 1
        _, _, checks, _ = self.audit_fixture(fixture)
        self.assertFalse(checks["exact_fixed_or_control_edit"])

    def test_audit_rejects_false_rescue_and_coupled_wait(self):
        fixture = self.fixture()
        fixture[3]["carrier_rescued"] = True
        fixture[3]["audits"][0]["miRNA_kd"] = 2e-15
        _, _, checks, _ = self.audit_fixture(fixture)
        self.assertFalse(checks["carrier_rescue_recomputed"])
        self.assertFalse(checks["cell_1_wait_isolated_fixed_wait"])


if __name__ == "__main__":
    unittest.main()
