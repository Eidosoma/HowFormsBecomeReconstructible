import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from analyze_erasure_rescue import audit_intervention
from memory_metrics import REGULATORS, classify
from run_erasure_rescue import edit_plan, overwrite_regulators, validate_config


class ErasureRescueTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((Path(__file__).resolve().parents[1] / "configs/erasure_rescue_v1.json").read_text())
        self.indices = dict(zip(REGULATORS, (5, 6, 7)))
        self.packet = np.arange(34., dtype=float).reshape(17, 2) + 1
        self.later = self.packet + 20
        self.later[5:8] = [[84, 9], [6, 69], [.4, 63]]

    def test_frozen_case_design(self):
        validate_config(self.config)
        self.assertEqual(len(self.config["cases"]), 12)
        self.assertEqual(sum(c.get("fine", False) for c in self.config["cases"]), 4)
        self.assertEqual(self.config["continuing_rounds"], [2, 3])
        for state in ("E", "M"):
            self.assertEqual({c["intervention"] for c in self.config["cases"] if c["state"] == state and not c.get("fine")},
                             {"sham", "overwrite", "rescue", "wrong"})

    def test_edit_plans(self):
        self.assertEqual(edit_plan("sham", "E"), (None, None))
        self.assertEqual(edit_plan("overwrite", "M"), ("E", None))
        self.assertEqual(edit_plan("rescue", "E"), ("M", "E"))
        self.assertEqual(edit_plan("wrong", "E"), ("M", "M"))
        with self.assertRaises(ValueError):
            edit_plan("other", "E")
        with self.assertRaises(ValueError):
            edit_plan("sham", "X")

    def test_only_three_regulators_of_both_cells_are_changed(self):
        original, reference = self.packet.copy(), self.later.copy()
        edited = overwrite_regulators(self.packet, self.later, self.indices, "M")
        np.testing.assert_array_equal(edited[5:8], np.repeat(self.later[5:8, 1, None], 2, axis=1))
        nonreg = list(range(5)) + list(range(8, 17))
        np.testing.assert_array_equal(edited[nonreg], original[nonreg])
        np.testing.assert_array_equal(self.packet, original)
        np.testing.assert_array_equal(self.later, reference)
        edited[:] = 0
        np.testing.assert_array_equal(self.packet, original)

    def test_sham_is_an_independent_exact_copy(self):
        edited = overwrite_regulators(self.packet, self.later, self.indices, None)
        np.testing.assert_array_equal(edited, self.packet)
        self.assertFalse(np.shares_memory(edited, self.packet))

    def test_rescue_keeps_evolved_nonregulatory_state(self):
        changed = overwrite_regulators(self.packet, self.later, self.indices, "M")
        changed[0] += 3
        rescued = overwrite_regulators(changed, self.later, self.indices, "E")
        np.testing.assert_array_equal(rescued[0], self.packet[0] + 3)
        self.assertEqual(classify(rescued, self.indices).tolist(), ["E", "E"])
        self.assertFalse(np.array_equal(rescued, self.packet))

    def test_reject_invalid_states_and_configuration(self):
        for packet in (self.packet[:, :1], self.packet * np.nan, -self.packet):
            with self.assertRaises(ValueError):
                overwrite_regulators(packet, self.later, self.indices, "E")
        for key, value in (("workers", 3), ("continuing_rounds", [1, 2]), ("intervention_horizon", 0)):
            cfg = copy.deepcopy(self.config)
            cfg[key] = value
            with self.assertRaises(ValueError):
                validate_config(cfg)

    def fixture(self):
        prefix = self.later[:, :1].repeat(2, axis=1)
        ids = ["replacement_a", "replacement_b"]
        case = {"id": "e_rescue", "state": "E", "intervention": "rescue", "history": "learned"}
        saved, data = {"prefix_packet": prefix.copy()}, {}
        result = {"incoming_ids": ids, "outgoing_ids": ids, "nominal_extra_duration": 2000,
                  "setups": [{"cells": 1, "edges": 0, "miRNA_kd": 0, "active": False}] * 4,
                  "stages": [], "audits": []}
        packet = prefix.copy()
        for stage, label in enumerate(("M", "E"), 1):
            edited = overwrite_regulators(packet, self.later, self.indices, label)
            after = edited.copy()
            after[0] += .25
            saved.update({f"before_{stage}": packet.copy(), f"edited_{stage}": edited, f"after_{stage}": after})
            result["stages"].append({"anchor": label, "labels_after_wait": label * 2})
            for cell in (1, 2):
                name = f"stage_{stage}_cell_{cell}"
                initial, final = edited[:, cell - 1:cell], after[:, cell - 1:cell]
                data[name + ".npz"] = {"initial": initial, "final": final, "raw_final": final,
                    "times": np.array([1., 900.]), "concentrations": np.stack([initial, final])}
                result["audits"].append({"phase": name, "all_labels": label, "late_label_fractions":
                    {c: float(c == label) for c in ("E", "M", "X")}, "graph_edges": 0, "miRNA_kd": 0, "requested_horizon": 1000})
            packet = after
        data["endpoints.npz"] = saved
        return prefix, ids, case, data, result

    def audit_fixture(self, fixture):
        prefix, ids, case, data, result = fixture
        with patch("analyze_erasure_rescue.arrays", side_effect=lambda p: data[p.name]), patch.object(Path, "read_text", return_value=json.dumps(result)):
            return audit_intervention(Path("unused"), self.config, case, prefix, ids, self.later, self.indices)

    def test_independent_audit_accepts_contiguous_selective_edits(self):
        _, _, checks, _ = self.audit_fixture(self.fixture())
        self.assertTrue(all(checks.values()), checks)

    def test_independent_audit_detects_ionic_restoration(self):
        fixture = self.fixture()
        fixture[3]["endpoints.npz"]["edited_2"][0] -= .25
        _, _, checks, _ = self.audit_fixture(fixture)
        self.assertFalse(checks["stage_2_no_nonregulatory_restoration"])
        self.assertFalse(checks["stage_2_exact_reference_edit"])

    def test_independent_audit_detects_pre_erasure_checkpoint_reuse(self):
        fixture = self.fixture()
        fixture[3]["endpoints.npz"]["before_2"] = fixture[0].copy()
        _, _, checks, _ = self.audit_fixture(fixture)
        self.assertFalse(checks["stage_2_actual_previous_state"])


if __name__ == "__main__":
    unittest.main()
