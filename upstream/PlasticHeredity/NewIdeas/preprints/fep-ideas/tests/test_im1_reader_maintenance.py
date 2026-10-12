"""Qualification uses synthetic examples and a disposable namespace only."""
import ast
import copy
import hashlib
import inspect
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from interface_maintenance import audit, model, runner
from interface_maintenance.reporting import summarize
from interface_maintenance.spec import ARMS, SPEC


class ReaderQualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.arrays, cls.metadata = model.generate_block("qualification", 0)
        cls.replay = audit.audit_block(cls.arrays, cls.metadata)

    def test_full_independent_replay(self):
        self.assertTrue(self.replay["passed"])
        self.assertLess(self.replay["max_abs_replay_error"], 1e-10)

    def test_sensor_closed_form_without_noise(self):
        d, s = SPEC["channels"], SPEC["sensor_steps"]
        signals = np.arange(3 * d).reshape(3, d).astype(float)
        route = np.roll(np.arange(d), 3)
        gain = 1 - SPEC["retention"] ** s
        observed = model.sensor(signals, np.zeros((3, s, d)), route)
        np.testing.assert_allclose(observed, gain * signals[:, route], rtol=1e-14, atol=1e-14)

    def test_sensor_noise_impulse_at_first_and_last_step(self):
        d, s = SPEC["channels"], SPEC["sensor_steps"]
        noise = np.zeros((1, s, d))
        noise[0, 0, 0] = 1
        noise[0, -1, 1] = 1
        observed = model.sensor(np.zeros((1, d)), noise, np.arange(d))
        self.assertAlmostEqual(observed[0, 0], SPEC["noise_sd"] * SPEC["retention"] ** (s - 1))
        self.assertAlmostEqual(observed[0, 1], SPEC["noise_sd"])

    def test_oracle_inverts_non_self_inverse_mapping(self):
        d = SPEC["channels"]
        route = np.roll(np.arange(d), 1)
        signals = np.eye(d)
        measured = model.sensor(signals, np.zeros((d, SPEC["sensor_steps"], d)), route)
        np.testing.assert_allclose(measured @ model.oracle_reader(route).T, signals, atol=1e-14)

    def test_damage_is_present_when_updates_are_frozen(self):
        d = SPEC["channels"]
        route = np.arange(d)
        route[:2] = [1, 0]
        signal = np.zeros((1, d))
        signal[0, 0] = 1
        measured = model.sensor(signal, np.zeros((1, SPEC["sensor_steps"], d)), route)
        frozen = measured @ model.initial_reader().T
        self.assertAlmostEqual(frozen[0, 0], 0)
        self.assertAlmostEqual(frozen[0, 1], 1)
        np.testing.assert_allclose(measured @ model.oracle_reader(route).T, signal, atol=1e-14)
        for case in range(SPEC["cases"]):
            np.testing.assert_array_equal(self.arrays["readers"][case, 1, 1], model.initial_reader())

    def test_exactly_eight_channels_damaged_and_values_preserved(self):
        for route in self.arrays["permutations"]:
            self.assertEqual(np.count_nonzero(route != np.arange(SPEC["channels"])), 8)
            np.testing.assert_array_equal(route[route], np.arange(SPEC["channels"]))
            np.testing.assert_array_equal(np.sort(route), np.arange(SPEC["channels"]))

    def test_batch_calibrator_solves_noiseless_full_rank_problem(self):
        d = SPEC["channels"]
        pilots = np.tile(np.eye(d), (3, 1))
        route = np.roll(np.arange(d), 5)
        observed = model.sensor(pilots, np.zeros((len(pilots), SPEC["sensor_steps"], d)), route)
        np.testing.assert_allclose(model.batch_reader(pilots, observed), model.oracle_reader(route), atol=1e-13)

    def test_update_reduces_known_single_probe_error(self):
        d = SPEC["channels"]
        label = np.zeros((1, d))
        label[0, 0] = 1
        response = np.zeros((1, d))
        response[0, 1] = 1
        history = model.learn_reader(label, response)
        before = np.sum((history[0] @ response[0] - label[0]) ** 2)
        after = np.sum((history[-1] @ response[0] - label[0]) ** 2)
        self.assertAlmostEqual(after / before, 0.25, places=10)

    def test_calibration_signature_excludes_fault_and_assessment(self):
        self.assertEqual(tuple(inspect.signature(model.learn_reader).parameters), ("labels", "observations"))
        self.assertEqual(tuple(inspect.signature(model.batch_reader).parameters), ("labels", "observations"))

    def test_changed_assessment_records_and_noise_cannot_change_reader(self):
        original = model.field_rng

        def changed(phase, block, field):
            return original("benchmark" if field in ("records", "assessment_noise") else phase, block, field)

        with patch.object(model, "field_rng", side_effect=changed):
            modified, _ = model.generate_block("qualification", 0)
        self.assertFalse(np.array_equal(modified["records"], self.arrays["records"]))
        self.assertFalse(np.array_equal(modified["predictions"], self.arrays["predictions"]))
        for field in ("readers", "active_history", "sham_history", "yoked_increments"):
            np.testing.assert_array_equal(modified[field], self.arrays[field])

    def test_records_readonly_and_bytes_sealed(self):
        records = self.arrays["records"]
        self.assertFalse(records.flags.writeable)
        with self.assertRaises(ValueError):
            records[0, 0, 0] = 999
        digest = hashlib.sha256(records.tobytes()).hexdigest()
        self.assertEqual(digest, self.metadata["record_sha256_before"])
        self.assertEqual(digest, self.metadata["record_sha256_after"])

    def test_yoke_uses_other_case_same_block_and_same_action_budget(self):
        for case in range(SPEC["cases"]):
            donor = (case + 1) % SPEC["cases"]
            expected = np.diff(self.arrays["active_history"][donor], axis=1)
            np.testing.assert_array_equal(self.arrays["yoked_increments"][case], expected)
            self.assertEqual(expected.shape[1], SPEC["pilots"])
            np.testing.assert_allclose(self.arrays["readers"][case, :, 2], self.arrays["readers"][donor, :, 0], atol=1e-14)

    def test_sham_has_separate_labels_and_equal_number_of_updates(self):
        self.assertFalse(np.array_equal(self.arrays["pilots"], self.arrays["sham_labels"]))
        self.assertEqual(self.arrays["active_history"].shape, self.arrays["sham_history"].shape)
        self.assertEqual(self.arrays["sham_history"].shape[2], SPEC["pilots"] + 1)

    def test_fresh_recipient_uses_same_reader_and_record_with_fresh_noise(self):
        a = self.arrays
        self.assertFalse(np.array_equal(a["assessment_noise"][:, 0], a["assessment_noise"][:, 1]))
        for case in range(SPEC["cases"]):
            expected = a["assessment_observations"][case, 1, 1] @ a["readers"][case, 1, 0].T
            np.testing.assert_array_equal(a["predictions"][case, 1, 1, 0], expected)
            reset = a["assessment_observations"][case, 1, 1] @ model.initial_reader().T
            np.testing.assert_array_equal(a["predictions"][case, 1, 1, 1], reset)

    def test_disposable_namespaces_and_blocks_are_distinct(self):
        values = [model.field_rng(phase, block, "pilots").integers(0, 2**31, 20)
                  for phase, block in (("qualification", 0), ("qualification", 1), ("benchmark", 0))]
        for i in range(len(values)):
            for j in range(i):
                self.assertFalse(np.array_equal(values[i], values[j]))

    def test_auditor_has_no_production_model_import(self):
        tree = ast.parse(Path(audit.__file__).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn("model", (node.module or "").split("."))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn("model", alias.name.split("."))

    def test_replay_rejects_corrupted_inputs_and_outputs(self):
        for field in ("records", "calibration_noise", "assessment_noise", "active_history",
                      "yoked_increments", "readers", "predictions", "errors"):
            with self.subTest(field=field):
                changed = dict(self.arrays)
                changed[field] = changed[field].copy()
                changed[field].flat[-1] += 0.01
                with self.assertRaises(audit.AuditError):
                    audit.audit_block(changed, self.metadata)

    def test_replay_rejects_changed_record_seal_and_nonfinite_data(self):
        metadata = dict(self.metadata, record_sha256_after="wrong")
        with self.assertRaises(audit.AuditError):
            audit.audit_block(self.arrays, metadata)
        changed = dict(self.arrays)
        changed["errors"] = changed["errors"].copy()
        changed["errors"].flat[0] = np.nan
        with self.assertRaises(audit.AuditError):
            audit.audit_block(changed, self.metadata)


class StatisticsAndWorkflowQualification(unittest.TestCase):
    def synthetic(self):
        # Deliberately unequal block scores; no main randomness is opened here.
        values = np.full((SPEC["blocks"], 2, 2, len(ARMS)), 0.01)
        values[:, 1, 0, 1] = np.linspace(0.1, 0.9, SPEC["blocks"])
        values[:, 1, 1, 1] = 0.5
        values[:, 1, 0, 2:4] = 0.7
        return values

    def test_block_bootstrap_and_all_contrasts_independently_replay(self):
        values = self.synthetic()
        summary = summarize(values)
        self.assertTrue(audit.audit_summary(summary, values)["passed"])
        self.assertAlmostEqual(summary["contrasts"]["primary_frozen_minus_active"]["mean"], 0.49)
        self.assertEqual(len(summary["contrasts"]["primary_frozen_minus_active"]["block_effects"]), 64)

    def test_partial_blocks_or_cases_as_units_are_rejected(self):
        for shape in ((63, 2, 2, 6), (256, 2, 2, 6)):
            with self.assertRaises(ValueError):
                summarize(np.zeros(shape))

    def test_gain_harm_and_zero_verdicts(self):
        values = np.ones((64, 2, 2, 6))
        self.assertEqual(summarize(values)["primary_label"], "UNRESOLVED")
        values[:, 1, 0, 1] += 0.25
        self.assertEqual(summarize(values)["primary_label"], "GAIN")
        values[:, 1, 0, 0] += 0.5
        self.assertEqual(summarize(values)["primary_label"], "HARM")

    def test_a_favorable_interaction_cannot_replace_primary(self):
        values = np.ones((64, 2, 2, 6))
        values[:, 0, 0, 0] += 0.5
        summary = summarize(values)
        self.assertGreater(summary["contrasts"]["damage_interaction"]["mean"], 0)
        self.assertEqual(summary["primary_label"], "UNRESOLVED")
        self.assertFalse(summary["maintenance_gates_all_pass"])

    def test_summary_tamper_is_rejected(self):
        values = self.synthetic()
        summary = summarize(values)
        for key in ("primary_label", "absolute_mse", "contrasts"):
            changed = copy.deepcopy(summary)
            if key == "primary_label":
                changed[key] = "HARM"
            elif key == "absolute_mse":
                changed[key]["damaged"]["original"]["active"] += 0.1
            else:
                changed[key]["primary_frozen_minus_active"]["ci95"][0] += 0.1
            with self.subTest(key=key), self.assertRaises(audit.AuditError):
                audit.audit_summary(changed, values)

    def test_run_root_cannot_escape_local_artifact_folder(self):
        for path in (runner.PROJECT.parent, runner.PROJECT, runner.RUNS, runner.RUNS / "../escape"):
            with self.assertRaises(ValueError):
                runner.safe_root(path)
        self.assertEqual(runner.safe_root(runner.RUNS / "qualification-case"), runner.RUNS / "qualification-case")

    def test_changed_source_is_rejected_before_benchmark_or_main(self):
        frozen = {"spec": SPEC, "source_hashes": {"changed.py": "bad"}, "environment": {}}
        with patch.object(runner, "read_json", return_value=frozen):
            with self.assertRaisesRegex(RuntimeError, "Frozen source"):
                runner.check_freeze(runner.RUNS / "disposable")

    def test_four_cpu_and_single_thread_environment(self):
        import os
        self.assertEqual(len(os.sched_getaffinity(0)), SPEC["workers"])
        self.assertEqual(SPEC["workers"], 4)
        for name in runner.THREAD_VARS:
            self.assertEqual(os.environ[name], "1")


if __name__ == "__main__":
    unittest.main()
