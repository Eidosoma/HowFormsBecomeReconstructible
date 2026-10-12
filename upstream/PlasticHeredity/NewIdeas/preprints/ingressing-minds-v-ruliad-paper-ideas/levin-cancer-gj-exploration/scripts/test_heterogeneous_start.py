import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from analyze_heterogeneous_start import audit_background
from memory_metrics import REGULATORS
from run_fractional_rescue import edit_fraction
from run_heterogeneous_start import BACKGROUNDS, validate_config, vary_start


class HeterogeneousStartTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((Path(__file__).resolve().parents[1] / "configs/heterogeneous_start_v1.json").read_text())
        self.indices = dict(zip(REGULATORS, (5, 6, 7)))
        self.later = np.ones((17, 2))
        self.later[5:8] = [[84, 9], [6, 69], [.4, 63]]
        self.original = self.later[:, 1, None].repeat(2, axis=1)

    def test_fixed_panel(self):
        validate_config(self.config)
        self.assertEqual(len(self.config["cases"]), 16)
        self.assertEqual(sum(c.get("fine", False) for c in self.config["cases"]), 4)
        for background in BACKGROUNDS:
            self.assertEqual(sorted(c["fraction"] for c in self.config["cases"] if c["background"] == background), [0, .75, .75, 1])

    def test_changed_grid_or_factors_rejected(self):
        for key, value in (("workers", 3), ("cases", self.config["cases"][:-1]), ("intervention_horizon", 1100)):
            config = copy.deepcopy(self.config)
            config[key] = value
            with self.assertRaises(ValueError):
                validate_config(config)
        config = copy.deepcopy(self.config)
        config["backgrounds"]["mixed"][0][0] = 1.2
        with self.assertRaises(ValueError):
            validate_config(config)
        config = copy.deepcopy(self.config)
        config["cases"][1]["fraction"] = .8
        with self.assertRaises(ValueError):
            validate_config(config)

    def test_only_regulators_change_without_input_mutation(self):
        original = self.original.copy()
        for factors in BACKGROUNDS.values():
            varied = vary_start(self.original, self.indices, factors)
            np.testing.assert_array_equal(varied[5:8], original[5:8] * np.array(factors))
            np.testing.assert_array_equal(varied[:5], original[:5])
            np.testing.assert_array_equal(varied[8:], original[8:])
            self.assertFalse(np.shares_memory(varied, self.original))
        np.testing.assert_array_equal(self.original, original)

    def test_original_background_is_exact_noop(self):
        np.testing.assert_array_equal(vary_start(self.original, self.indices, BACKGROUNDS["original"]), self.original)

    def test_mixed_cells_remain_distinct_at_preparation(self):
        varied = vary_start(self.original, self.indices, BACKGROUNDS["mixed"])
        np.testing.assert_array_equal(varied[5:8, 0], self.original[5:8, 0] * [1.1, .9, .9])
        np.testing.assert_array_equal(varied[5:8, 1], self.original[5:8, 1] * [.9, 1.1, 1.1])
        self.assertFalse(np.array_equal(varied[5:8, 0], varied[5:8, 1]))

    def test_rescue_preserves_prepared_mrna_not_original_mrna(self):
        varied = vary_start(self.original, self.indices, BACKGROUNDS["mixed"])
        edited = edit_fraction(varied, self.later, self.indices, (REGULATORS[0], REGULATORS[2]), .75)
        np.testing.assert_array_equal(edited[6], varied[6])
        self.assertFalse(np.array_equal(edited[6], self.original[6]))
        np.testing.assert_allclose(edited[[5, 7]], .25 * varied[[5, 7]] + .75 * self.later[[5, 7], 0, None], rtol=0, atol=0)

    def test_invalid_preparation_rejected(self):
        for factors in (np.ones((2, 3)), np.ones((3, 2)) * np.nan, np.ones((3, 2)) * 1.2, np.ones((3, 2)) * .8):
            with self.assertRaises(ValueError):
                vary_start(self.original, self.indices, factors)
        for state in (-self.original, self.original[:, :1], self.original * np.nan):
            with self.assertRaises(ValueError):
                vary_start(state, self.indices, BACKGROUNDS["mixed"])

    def fixture(self):
        factors = np.array(BACKGROUNDS["mixed"])
        varied = vary_start(self.original, self.indices, factors)
        data = {"background.npz": {"original_erased": self.original.copy(), "varied_start": varied.copy(), "factors": factors.copy()},
                "e_erased.npz": {"after_1": varied.copy()}}
        names = ("references.npz", "reference.json", "e_prefix.json", "e_erased.npz")
        record = {"background": "mixed", "factors": factors.tolist(), "extra_relaxation_horizon": 0,
            "original_labels": "MM", "varied_labels": "MM", "prepared_inputs_unchanged": True,
            "prepared_hashes_sha256": {n: n for n in names}, "background_sha256": "background.npz"}
        return data, record

    def audit_fixture(self, fixture, hash_function=lambda p: p.name):
        data, record = fixture
        with patch("analyze_heterogeneous_start.arrays", side_effect=lambda p: data[p.name]), \
             patch("analyze_heterogeneous_start.file_hash", side_effect=hash_function), \
             patch.object(Path, "read_text", return_value=json.dumps(record)):
            return audit_background(Path("branch"), Path("inputs"), self.config, {"background": "mixed"}, self.original, self.indices)

    def test_independent_background_audit_accepts_valid_pair(self):
        _, row, checks = self.audit_fixture(self.fixture())
        self.assertTrue(all(checks.values()), checks)
        self.assertTrue(row["carrier_regulators_differ"])

    def test_audit_rejects_accidental_identical_cells(self):
        fixture = self.fixture()
        fixture[0]["background.npz"]["varied_start"][:, 1] = fixture[0]["background.npz"]["varied_start"][:, 0]
        _, _, checks = self.audit_fixture(fixture)
        self.assertFalse(checks["exact_background_preparation"])
        self.assertFalse(checks["prepared_input_equals_varied_start"])

    def test_audit_rejects_original_checkpoint_reuse(self):
        fixture = self.fixture()
        fixture[0]["e_erased.npz"]["after_1"] = self.original.copy()
        _, _, checks = self.audit_fixture(fixture)
        self.assertFalse(checks["prepared_input_equals_varied_start"])

    def test_audit_rejects_ionic_preparation_and_extra_relaxation(self):
        fixture = self.fixture()
        fixture[0]["background.npz"]["varied_start"][0] += 1
        fixture[1]["extra_relaxation_horizon"] = 1000
        _, _, checks = self.audit_fixture(fixture)
        self.assertFalse(checks["all_nonregulatory_rows_preserved"])
        self.assertFalse(checks["correct_background_record"])

    def test_audit_rejects_changed_derived_inputs_and_references(self):
        fixture = self.fixture()
        fixture[1]["prepared_hashes_sha256"]["e_erased.npz"] = "changed"
        _, _, checks = self.audit_fixture(fixture)
        self.assertFalse(checks["derived_inputs_unchanged"])
        _, _, checks = self.audit_fixture(self.fixture(), lambda p: p.name + ("changed" if p.parent.name == "prepared_inputs" and p.name == "references.npz" else ""))
        self.assertFalse(checks["references_and_ids_copied_exactly"])


if __name__ == "__main__":
    unittest.main()
