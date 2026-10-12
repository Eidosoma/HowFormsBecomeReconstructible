"""Analytic and disposable qualification; never opens main randomness."""
import ast
import copy
import hashlib
import inspect
import multiprocessing as mp
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from learned_reference import audit, model, runner
from learned_reference.reporting import summarize
from learned_reference.spec import ARMS, CONDITIONS, SPEC


class MechanismQualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.arrays, cls.metadata = model.generate_block("qualification", 0)
        cls.replay = audit.audit_block(cls.arrays, cls.metadata)

    def fixture(self):
        # Paired +/- basis samples realize a known, equal-diagonal covariance.
        d = SPEC["channels"]
        cov = self.arrays["population_covariance"][0]
        base = np.concatenate((np.eye(d), -np.eye(d))) * np.sqrt((2 * d - 1) / 2)
        samples = base @ np.linalg.cholesky(cov).T
        route = np.asarray([1, 2, 0, 3, 4, 5, 6, 7])
        return cov, samples, route

    def test_all_40320_mappings_present_in_lexicographic_order(self):
        q = model.mappings(8)
        self.assertEqual(q.shape, (40320, 8))
        self.assertEqual(len(set(map(tuple, q))), 40320)
        np.testing.assert_array_equal(np.sort(q, axis=1), np.tile(np.arange(8), (40320, 1)))
        self.assertEqual(list(map(tuple, q)), sorted(map(tuple, q)))
        self.assertFalse(q.flags.writeable)

    def test_noiseless_unique_search_finds_inverse_of_three_cycle(self):
        cov, samples, route = self.fixture()
        current = cov[np.ix_(route, route)]
        production = model.permutation_losses(cov, current)
        independent = audit.trace_losses(cov, current)
        np.testing.assert_allclose(production, independent, atol=1e-12, rtol=1e-12)
        best = model.mappings(8)[np.argmin(production)]
        np.testing.assert_array_equal(best, np.argsort(route))
        self.assertFalse(np.array_equal(best, route))
        self.assertLess(production.min(), 1e-25)

    def test_isotropic_reference_is_tied_and_identity_wins(self):
        cov, samples, route = self.fixture()
        validation = np.tile(samples[:, route], (32, 1))
        result = model.repair(np.eye(8), samples[:, route], validation)
        self.assertEqual(result["ties"], 40320)
        np.testing.assert_array_equal(result["candidate"], np.arange(8))
        self.assertFalse(result["accepted"])

    def test_gate_accepts_consistently_helpful_mapping(self):
        cov, samples, route = self.fixture()
        result = model.repair(cov, samples[:, route], np.tile(samples[:, route], (32, 1)))
        self.assertTrue(result["accepted"])
        np.testing.assert_array_equal(result["selected"], np.argsort(route))
        self.assertTrue(np.all(result["improvements"] > 0))

    def test_gate_rejects_mapping_when_new_batch_is_intact(self):
        cov, samples, route = self.fixture()
        result = model.repair(cov, samples[:, route], np.tile(samples, (32, 1)))
        self.assertFalse(result["accepted"])
        self.assertTrue(np.all(result["improvements"] < 0))
        np.testing.assert_array_equal(result["selected"], np.arange(8))

    def test_covariance_translation_invariance_and_second_moments(self):
        cov, samples, _ = self.fixture()
        translated = samples + np.arange(8)[None, :]
        np.testing.assert_allclose(model.covariance(translated), cov, atol=1e-13)
        np.testing.assert_allclose(audit.second_moment_covariance(translated), cov, atol=1e-13)

    def test_sensor_known_gain_and_noise_impulses(self):
        d, s = SPEC["channels"], SPEC["sensor_steps"]
        signal = np.eye(d)
        route = np.roll(np.arange(d), 1)
        np.testing.assert_allclose(model.sensor(signal, np.zeros((d, s, d)), route), signal[:, route], atol=1e-14)
        noise = np.zeros((1, s, d))
        noise[0, 0, 0], noise[0, -1, 1] = 1, 1
        result = model.sensor(np.zeros((1, d)), noise, np.arange(d))
        gain = 1 - SPEC["retention"] ** s
        self.assertAlmostEqual(result[0, 0], SPEC["noise_sd"] * SPEC["retention"] ** (s - 1) / gain)
        self.assertAlmostEqual(result[0, 1], SPEC["noise_sd"] / gain)

    def test_population_equal_marginals_and_positive_definiteness(self):
        for cov in self.arrays["population_covariance"]:
            np.testing.assert_allclose(np.diag(cov), np.ones(8), atol=1e-14)
            self.assertGreater(np.linalg.eigvalsh(cov).min(), 0)
        for fault in self.arrays["fault"]:
            self.assertEqual(np.count_nonzero(fault != np.arange(8)), 4)

    def test_only_reference_and_unlabeled_current_batches_are_arguments(self):
        self.assertEqual(tuple(inspect.signature(model.repair).parameters),
                         ("reference", "proposal_readings", "validation_readings"))

    def test_changed_future_records_and_noise_cannot_change_decisions(self):
        original = model.field_rng

        def different_assessment(phase, block, field):
            return original(phase, 91 if field.startswith("assessment_") else block, field)

        with patch.object(model, "field_rng", side_effect=different_assessment):
            changed, _ = model.generate_block("qualification", 0)
        self.assertFalse(np.array_equal(changed["assessment_records"], self.arrays["assessment_records"]))
        for field in ("learned_references", "candidates", "accepted", "selected", "gate_statistics"):
            np.testing.assert_array_equal(changed[field], self.arrays[field])

    def test_reference_and_records_are_readonly_and_byte_sealed(self):
        for field, label in (("assessment_records", "record"), ("learned_references", "reference")):
            array = self.arrays[field]
            self.assertFalse(array.flags.writeable)
            with self.assertRaises(ValueError):
                array.flat[0] = 999
            digest = hashlib.sha256(array.tobytes()).hexdigest()
            self.assertEqual(self.metadata[label + "_sha256_before"], digest)
            self.assertEqual(self.metadata[label + "_sha256_after"], digest)

    def test_fault_and_environment_shift_have_identical_observations(self):
        for field in ("proposal_readings", "validation_readings", "assessment_readings",
                      "candidates", "accepted"):
            np.testing.assert_array_equal(self.arrays[field][:, 1], self.arrays[field][:, 2])
        np.testing.assert_array_equal(self.arrays["selected"][:, 1, :5], self.arrays["selected"][:, 2, :5])
        np.testing.assert_array_equal(self.arrays["predictions"][:, 1, :5], self.arrays["predictions"][:, 2, :5])
        self.assertFalse(np.array_equal(self.arrays["assessment_records"][:, 1], self.arrays["assessment_records"][:, 2]))

    def test_oracle_tracks_hardware_and_frozen_does_not_remove_damage(self):
        for case in range(SPEC["cases"]):
            for condition in range(len(CONDITIONS)):
                np.testing.assert_array_equal(self.arrays["selected"][case, condition, 1], np.arange(8))
                target = np.argsort(self.arrays["fault"][case]) if condition in (1, 4) else np.arange(8)
                np.testing.assert_array_equal(self.arrays["selected"][case, condition, 5], target)
        self.assertTrue(self.arrays["mapping_recovered"][:, :, 5].all())
        self.assertFalse(self.arrays["mapping_recovered"][:, 1, 1].any())

    def test_gate_and_always_share_proposal_without_more_observations(self):
        np.testing.assert_array_equal(self.arrays["selected"][:, :, 2], self.arrays["candidates"][:, :, 0])
        np.testing.assert_array_equal(self.arrays["edited"][:, :, 0], self.arrays["accepted"][:, :, 0])
        np.testing.assert_array_equal(self.arrays["proposed"][:, :, 0], self.arrays["proposed"][:, :, 2])
        self.assertFalse(self.arrays["edited"][:, :, 4].any())

    def test_reference_lesion_sees_same_observations_and_is_replayed(self):
        case, condition = 0, 1
        ref = self.arrays["learned_references"][case, 0]
        q = self.arrays["reference_scramble"][case]
        result = model.repair(ref[np.ix_(q, q)], self.arrays["proposal_readings"][case, condition],
                              self.arrays["validation_readings"][case, condition])
        np.testing.assert_array_equal(result["selected"], self.arrays["selected"][case, condition, 3])

    def test_full_independent_replay(self):
        self.assertTrue(self.replay["passed"])
        self.assertEqual(self.replay["ambiguity_pairs_verified"], 4)
        self.assertLess(self.replay["max_abs_replay_error"], 1e-9)
        np.testing.assert_allclose(self.replay["independent_block_metrics"], model.block_metrics(self.arrays), atol=1e-11)

    def test_auditor_has_no_model_import(self):
        for node in ast.walk(ast.parse(Path(audit.__file__).read_text())):
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn("model", (node.module or "").split("."))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn("model", alias.name.split("."))

    def test_auditor_rejects_corrupted_inputs_and_decisions(self):
        for field in ("proposal_base", "assessment_records", "learned_references", "candidates",
                      "gate_improvements", "predictions", "errors"):
            with self.subTest(field=field):
                changed = dict(self.arrays)
                changed[field] = changed[field].copy()
                changed[field].flat[0] += 1 if field == "candidates" else 0.01
                with self.assertRaises(audit.AuditError):
                    audit.audit_block(changed, self.metadata)

    def test_nonfinite_and_changed_byte_seal_rejected(self):
        bad_metadata = dict(self.metadata, reference_sha256_after="wrong")
        with self.assertRaises(audit.AuditError):
            audit.audit_block(self.arrays, bad_metadata)
        changed = dict(self.arrays)
        changed["errors"] = changed["errors"].copy()
        changed["errors"].flat[0] = np.nan
        with self.assertRaises(audit.AuditError):
            audit.audit_block(changed, self.metadata)

    def test_disposable_stage_and_block_streams_are_distinct(self):
        values = [model.field_rng(phase, block, field).standard_normal(12)
                  for phase, block, field in (("qualification", 0, "proposal_base"),
                  ("qualification", 1, "proposal_base"), ("qualification", 0, "validation_base"),
                  ("benchmark", 0, "proposal_base"))]
        self.assertEqual(len(set(value.tobytes() for value in values)), 4)


class StatisticsAndWorkflowQualification(unittest.TestCase):
    def synthetic(self):
        out = np.zeros((64, len(CONDITIONS), len(ARMS), 4))
        out[..., 0] = 0.01
        out[:, 1, 1, 0] = np.linspace(0.1, 0.9, 64)
        out[:, 1, 3:5, 0] = 0.5
        out[:, 1, 0, 1:] = 1
        return out

    def test_summary_and_counts_independently_replay(self):
        values = self.synthetic()
        summary = summarize(values)
        self.assertTrue(audit.audit_summary(summary, values)["passed"])
        self.assertAlmostEqual(summary["contrasts"]["primary_frozen_minus_gated"]["mean"], 0.49)
        self.assertEqual(summary["edit_counts"]["structured_damage"]["gated"], 256)

    def test_partial_blocks_and_cases_as_units_rejected(self):
        for n in (63, 256):
            with self.assertRaises(ValueError):
                summarize(np.zeros((n, 5, 6, 4)))

    def test_gain_harm_and_zero_verdicts(self):
        values = np.zeros((64, 5, 6, 4))
        values[..., 0] = 1
        self.assertEqual(summarize(values)["primary_label"], "UNRESOLVED")
        values[:, 1, 1, 0] += 0.25
        self.assertEqual(summarize(values)["primary_label"], "GAIN")
        values[:, 1, 0, 0] += 0.5
        self.assertEqual(summarize(values)["primary_label"], "HARM")

    def test_secondary_environment_gain_cannot_rescue_primary(self):
        values = np.zeros((64, 5, 6, 4))
        values[..., 0] = 1
        values[:, 2, 1, 0] = 2
        summary = summarize(values)
        self.assertGreater(summary["contrasts"]["environment_shift_frozen_minus_gated"]["mean"], 0)
        self.assertEqual(summary["primary_label"], "UNRESOLVED")
        self.assertFalse(summary["maintenance_gates_all_pass"])

    def test_modified_interval_and_count_are_rejected(self):
        values = self.synthetic()
        summary = summarize(values)
        bad = copy.deepcopy(summary)
        bad["contrasts"]["primary_frozen_minus_gated"]["ci95"][0] += 0.1
        with self.assertRaises(audit.AuditError):
            audit.audit_summary(bad, values)
        bad = copy.deepcopy(summary)
        bad["edit_counts"]["structured_damage"]["gated"] -= 1
        with self.assertRaises(audit.AuditError):
            audit.audit_summary(bad, values)

    def test_root_and_freeze_guards(self):
        for path in (runner.PROJECT.parent, runner.PROJECT, runner.RUNS / "../escape"):
            with self.assertRaises(ValueError):
                runner.safe_root(path)
        frozen = {"spec": SPEC, "source_hashes": {"changed.py": "bad"}, "environment": {}}
        with patch.object(runner, "read_json", return_value=frozen):
            with self.assertRaisesRegex(RuntimeError, "Frozen source"):
                runner.check_freeze(runner.RUNS / "disposable")

    def test_four_spawned_processes_inherit_affinity_and_thread_limit(self):
        self.assertEqual(len(os.sched_getaffinity(0)), 4)
        context = mp.get_context("spawn")
        queue = context.Queue()
        children = [context.Process(target=runner.workflow_probe, args=(queue,)) for _ in range(4)]
        try:
            for child in children:
                child.start()
            results = [queue.get(timeout=20) for _ in children]
            self.assertEqual(len({result["pid"] for result in results}), 4)
            for result in results:
                self.assertEqual(result["cpus"], sorted(os.sched_getaffinity(0)))
                self.assertEqual(set(result["threads"].values()), {"1"})
            for child in children:
                child.join(timeout=5)
                self.assertEqual(child.exitcode, 0)
        finally:
            for child in children:
                if child.pid is not None and child.is_alive():
                    child.terminate()
                    child.join()
            queue.close()
            queue.join_thread()


if __name__ == "__main__":
    unittest.main()
