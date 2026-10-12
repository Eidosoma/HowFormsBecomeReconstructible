import copy
from itertools import combinations
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from analyze_pair_regulator import audit_rescue, minimal_successes
from memory_metrics import REGULATORS
from run_pair_regulator import edit_subset, validate_config


class PairRegulatorTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((Path(__file__).resolve().parents[1] / "configs/pair_regulator_v1.json").read_text())
        self.indices = dict(zip(REGULATORS, (5, 6, 7)))
        self.later = np.ones((17, 2))
        self.later[5:8] = [[84, 9], [6, 69], [.4, 63]]
        self.erased = self.later[:, 1, None].repeat(2, axis=1)

    def test_fixed_grid(self):
        validate_config(self.config)
        self.assertEqual(len(self.config["cases"]), 8)
        self.assertEqual(sum(c.get("fine", False) for c in self.config["cases"]), 3)

    def test_changed_grid_budget_or_direction_rejected(self):
        for key, value in (("workers", 3), ("cases", self.config["cases"][:-1]), ("inherited_wait", 0)):
            config = copy.deepcopy(self.config)
            config[key] = value
            with self.assertRaises(ValueError):
                validate_config(config)
        config = copy.deepcopy(self.config)
        config["cases"][0]["state"] = "M"
        with self.assertRaises(ValueError):
            validate_config(config)

    def test_all_pairs_preserve_third_regulator_and_other_rows(self):
        original, ref = self.erased.copy(), self.later.copy()
        for names in combinations(REGULATORS, 2):
            edited = edit_subset(self.erased, self.later, self.indices, names)
            selected = [self.indices[n] for n in names]
            untouched = [i for i in range(17) if i not in selected]
            np.testing.assert_array_equal(edited[selected], self.later[selected, 0, None].repeat(2, axis=1))
            np.testing.assert_array_equal(edited[untouched], original[untouched])
            reverse = edit_subset(self.erased, self.later, self.indices, names[::-1])
            np.testing.assert_array_equal(edited, reverse)
            self.assertFalse(np.shares_memory(edited, self.erased))
        np.testing.assert_array_equal(self.erased, original)
        np.testing.assert_array_equal(self.later, ref)

    def test_invalid_subsets_and_states(self):
        for names in ([REGULATORS[0]], [REGULATORS[0]] * 2, [REGULATORS[0], "Na"]):
            with self.assertRaises(ValueError):
                edit_subset(self.erased, self.later, self.indices, names)
        for state in (-self.erased, self.erased * np.nan, self.erased[:, :1]):
            with self.assertRaises(ValueError):
                edit_subset(state, self.later, self.indices, REGULATORS[:2])

    def test_none_and_full_reset(self):
        np.testing.assert_array_equal(edit_subset(self.erased, self.later, self.indices, []), self.erased)
        full = edit_subset(self.erased, self.later, self.indices, REGULATORS)
        np.testing.assert_array_equal(full[5:8], self.later[5:8, 0, None].repeat(2, axis=1))

    def test_minimal_successes_are_restricted_to_complete_subset_map(self):
        rows = [{"targets": list(c), "relay_rescued": len(c) >= 2 and REGULATORS[2] in c}
                for n in range(4) for c in combinations(REGULATORS, n)]
        minima = {frozenset(c) for c in minimal_successes(rows)}
        self.assertEqual(minima, {frozenset((REGULATORS[0], REGULATORS[2])), frozenset(REGULATORS[1:])})
        with self.assertRaises(ValueError):
            minimal_successes(rows[:-1])
        with self.assertRaises(ValueError):
            minimal_successes(rows[:-1] + rows[:1])
        self.assertEqual(minimal_successes([dict(r, relay_rescued=False) for r in rows]), [])
        self.assertEqual(minimal_successes([dict(r, relay_rescued=True) for r in rows]), [[]])

    def fixture(self):
        case = {"id": "e_mir_mrna", "state": "E", "targets": list(REGULATORS[:2]), "history": "learned"}
        ids = ["replacement_a", "replacement_b"]
        edited = edit_subset(self.erased, self.later, self.indices, case["targets"])
        after = self.erased.copy()  # Synthetic transient label flip, not a simulated result.
        after[0] += .25
        data = {"endpoints.npz": {"before": self.erased.copy(), "edited": edited, "after_wait": after}}
        result = {"incoming_ids": ids, "outgoing_ids": ids, "target_names": case["targets"], "sustained_forcing": False,
            "before_labels": "MM", "immediate_labels": "EE", "after_wait_labels": "MM", "carrier_rescued": False,
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
        with patch("analyze_pair_regulator.arrays", side_effect=lambda p: data[p.name]), patch.object(Path, "read_text", return_value=json.dumps(result)):
            return audit_rescue(Path("unused"), self.config, case, self.erased, ids, self.later, self.indices)

    def test_audit_accepts_valid_negative_without_false_rescue(self):
        _, row, checks, _ = self.audit_fixture(self.fixture())
        self.assertTrue(all(checks.values()), checks)
        self.assertTrue(row["immediate_E_label_lost"])
        self.assertFalse(row["carrier_rescued"])

    def test_audit_rejects_third_regulator_reset(self):
        fixture = self.fixture()
        fixture[2]["endpoints.npz"]["edited"][7] = .4
        _, _, checks, _ = self.audit_fixture(fixture)
        self.assertFalse(checks["all_unselected_rows_preserved"])
        self.assertFalse(checks["exact_selected_E_reference_edit"])

    def test_audit_rejects_ionic_reset_and_false_recovery(self):
        fixture = self.fixture()
        fixture[2]["endpoints.npz"]["edited"][0] = 2
        fixture[3]["carrier_rescued"] = True
        _, _, checks, _ = self.audit_fixture(fixture)
        self.assertFalse(checks["all_unselected_rows_preserved"])
        self.assertFalse(checks["carrier_rescue_recomputed"])


if __name__ == "__main__":
    unittest.main()
