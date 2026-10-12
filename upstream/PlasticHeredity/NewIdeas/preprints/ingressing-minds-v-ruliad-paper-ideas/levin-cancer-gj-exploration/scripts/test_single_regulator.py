import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from analyze_single_regulator import audit_rescue
from memory_metrics import REGULATORS, classify
from run_single_regulator import rescue_edit, target_names, validate_config


class SingleRegulatorTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((Path(__file__).resolve().parents[1] / "configs/single_regulator_v1.json").read_text())
        self.indices = dict(zip(REGULATORS, (5, 6, 7)))
        self.later = np.ones((17, 2))
        self.later[5:8] = [[84, 9], [6, 69], [.4, 63]]
        self.erased = np.repeat(self.later[:, 1, None], 2, axis=1)

    def test_fixed_grid_and_fine_controls(self):
        validate_config(self.config)
        self.assertEqual(len(self.config["cases"]), 16)
        self.assertEqual(sum(c.get("fine", False) for c in self.config["cases"]), 6)

    def test_reject_changed_grid_or_budget(self):
        for key, value in (("workers", 3), ("worker_timeout_seconds", 901), ("cases", self.config["cases"][:-1]), ("inherited_wait", 0)):
            config = copy.deepcopy(self.config)
            config[key] = value
            with self.assertRaises(ValueError):
                validate_config(config)
        config = copy.deepcopy(self.config)
        config["cases"][0]["id"] = "arbitrary"
        with self.assertRaises(ValueError):
            validate_config(config)

    def test_each_single_edit_preserves_every_other_row(self):
        original, ref = self.erased.copy(), self.later.copy()
        for name in REGULATORS:
            edited = rescue_edit(self.erased, self.later, self.indices, "E", name)
            changed = self.indices[name]
            np.testing.assert_array_equal(edited[changed], np.repeat(self.later[changed, 0], 2))
            untouched = [i for i in range(17) if i != changed]
            np.testing.assert_array_equal(edited[untouched], original[untouched])
            self.assertFalse(np.shares_memory(edited, original))
        np.testing.assert_array_equal(self.erased, original)
        np.testing.assert_array_equal(self.later, ref)

    def test_none_and_full_edit(self):
        np.testing.assert_array_equal(rescue_edit(self.erased, self.later, self.indices, "E", "none"), self.erased)
        full = rescue_edit(self.erased, self.later, self.indices, "E", "all")
        np.testing.assert_array_equal(full[5:8], np.repeat(self.later[5:8, 0, None], 2, axis=1))
        self.assertEqual(classify(full, self.indices).tolist(), ["E", "E"])

    def test_invalid_intervention_rejected(self):
        for target in ("Zeb", "ions", "", "all_except_one"):
            with self.assertRaises(ValueError):
                target_names(target)
        for packet in (self.erased[:, :1], -self.erased, self.erased * np.nan):
            with self.assertRaises(ValueError):
                rescue_edit(packet, self.later, self.indices, "E", "miR200_total")
        with self.assertRaises(ValueError):
            rescue_edit(self.erased, self.later, self.indices, "X", "none")

    def fixture(self):
        case = {"id": "e_mir", "state": "E", "target": "miR200_total", "history": "learned"}
        ids = ["replacement_a", "replacement_b"]
        edited = rescue_edit(self.erased, self.later, self.indices, "E", "miR200_total")
        after = self.erased.copy()  # Immediate E label, then return to M: valid negative.
        after[0] += .25
        data = {"endpoints.npz": {"before": self.erased.copy(), "edited": edited, "after_wait": after}}
        result = {"incoming_ids": ids, "outgoing_ids": ids, "target_names": ["miR200_total"],
            "sustained_forcing": False, "before_labels": "MM", "immediate_labels": "EE", "after_wait_labels": "MM",
            "carrier_rescued": False, "setups": [{"cells": 1, "edges": 0, "miRNA_kd": 0, "active": False}] * 2, "audits": []}
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
        with patch("analyze_single_regulator.arrays", side_effect=lambda p: data[p.name]), patch.object(Path, "read_text", return_value=json.dumps(result)):
            return audit_rescue(Path("unused"), self.config, case, self.erased, ids, self.later, self.indices)

    def test_audit_accepts_valid_negative_and_detects_transient_flip(self):
        _, row, checks, _ = self.audit_fixture(self.fixture())
        self.assertTrue(all(checks.values()), checks)
        self.assertTrue(row["immediate_desired_label_lost"])
        self.assertFalse(row["carrier_rescued"])

    def test_audit_rejects_second_regulator_edit(self):
        fixture = self.fixture()
        fixture[2]["endpoints.npz"]["edited"][6] = 6
        _, _, checks, _ = self.audit_fixture(fixture)
        self.assertFalse(checks["every_untouched_row_preserved"])
        self.assertFalse(checks["exact_selected_reference_edit"])

    def test_audit_rejects_ionic_reset_and_wrong_input(self):
        fixture = self.fixture()
        fixture[2]["endpoints.npz"]["edited"][0] = 2
        fixture[2]["endpoints.npz"]["before"][0] = 3
        _, _, checks, _ = self.audit_fixture(fixture)
        self.assertFalse(checks["every_untouched_row_preserved"])
        self.assertFalse(checks["actual_post_erasure_input"])

    def test_audit_rejects_false_recovery_claim(self):
        fixture = self.fixture()
        fixture[3]["carrier_rescued"] = True
        _, row, checks, _ = self.audit_fixture(fixture)
        self.assertFalse(row["carrier_rescued"])
        self.assertFalse(checks["carrier_recovery_recomputed"])


if __name__ == "__main__":
    unittest.main()
