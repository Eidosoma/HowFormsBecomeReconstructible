"""Analytic fixtures and disposable qualification, with no main random stream."""
import ast
import copy
import hashlib
import inspect
import multiprocessing as mp
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from causal_probe import audit, model, runner
from causal_probe.reporting import summarize
from causal_probe.spec import ARMS, CONDITIONS, PROBES, SPEC
from learned_reference.spec import SPEC as REFERENCE_SPEC


class MechanismQualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a, cls.meta = model.generate_block("qualification", 0)
        cls.replayed = audit.audit_block(cls.a, cls.meta)

    def fixture(self):
        route = np.asarray([1, 2, 0, 3, 4, 5, 6, 7])
        records = np.arange(64, dtype=float).reshape(8, 8) / 30
        noise = np.zeros((8, 8, 8))
        commands = np.zeros((8, 8))
        commands[:, 0] = SPEC["pulse_amplitude"]
        return route, records, noise, commands

    def test_inherited_constants_match_pinned_procedure(self):
        for field in ("channels", "reference_reads", "proposal_reads", "validation_reads", "sensor_steps", "retention", "noise_sd", "tie_tolerance", "gate_se_multiplier", "gate_floor"):
            self.assertEqual(SPEC[field], REFERENCE_SPEC[field])
        self.assertEqual(REFERENCE_SPEC["validation_batches"], 8)

    def test_three_cycle_upstream_pulse_uses_inverse_mapping(self):
        route, records, noise, commands = self.fixture()
        q = np.argsort(route)
        readings = model.pulse_readings(records, route, commands, noise, noise, "upstream")
        np.testing.assert_allclose(readings[:, 1] - readings[:, 0], commands[:, route], atol=1e-14)
        self.assertNotEqual(int(q[0]), int(route[0]))
        result = model.pulse_gate(q, 0, readings)
        self.assertTrue(result["accepted"])
        np.testing.assert_array_equal(result["selected"], q)

    def test_three_cycle_downstream_pulse_stays_at_command_coordinate(self):
        route, records, noise, commands = self.fixture()
        readings = model.pulse_readings(records, route, commands, noise, noise, "downstream")
        np.testing.assert_allclose(readings[:, 1] - readings[:, 0], commands, atol=1e-14)
        self.assertFalse(model.pulse_gate(np.argsort(route), 0, readings)["accepted"])

    def test_world_change_rejects_reference_repair_with_upstream_probe(self):
        route, records, noise, commands = self.fixture()
        readings = model.pulse_readings(records[:, route], np.arange(8), commands, noise, noise, "upstream")
        self.assertFalse(model.pulse_gate(np.argsort(route), 0, readings)["accepted"])

    def test_downstream_histories_remain_bitwise_identical(self):
        route, records, noise, commands = self.fixture()
        damaged = model.pulse_readings(records, route, commands, noise, noise, "downstream")
        shifted = model.pulse_readings(records[:, route], np.arange(8), commands, noise, noise, "downstream")
        np.testing.assert_array_equal(damaged, shifted)

    def test_upstream_histories_differ_on_affected_channel(self):
        route, records, noise, commands = self.fixture()
        damaged = model.pulse_readings(records, route, commands, noise, noise, "upstream")
        shifted = model.pulse_readings(records[:, route], np.arange(8), commands, noise, noise, "upstream")
        np.testing.assert_array_equal(damaged[:, 0], shifted[:, 0])
        self.assertFalse(np.array_equal(damaged[:, 1], shifted[:, 1]))

    def test_unaffected_channel_is_ambiguous_and_abstains(self):
        route, records, noise, commands = self.fixture()
        commands[:] = 0
        commands[:, 7] = 0.25
        damaged = model.pulse_readings(records, route, commands, noise, noise, "upstream")
        shifted = model.pulse_readings(records[:, route], np.arange(8), commands, noise, noise, "upstream")
        np.testing.assert_array_equal(damaged, shifted)
        self.assertFalse(model.pulse_gate(np.argsort(route), 7, damaged)["accepted"])

    def test_single_good_link_does_not_certify_whole_reader(self):
        route, records, noise, commands = self.fixture()
        bad = np.argsort(route)
        bad[1], bad[2] = bad[2], bad[1]
        readings = model.pulse_readings(records, route, commands, noise, noise, "upstream")
        result = model.pulse_gate(bad, 0, readings)
        self.assertTrue(result["accepted"])
        self.assertFalse(np.array_equal(result["selected"], np.argsort(route)))

    def test_zero_and_uncertain_evidence_rejected(self):
        q = np.asarray([1, 0, 2, 3, 4, 5, 6, 7])
        readings = np.zeros((8, 2, 8))
        self.assertFalse(model.pulse_gate(q, 0, readings)["accepted"])
        readings[:, 1, 1] = [1, -1, 1, -1, 1, -1, 1, -0.9]
        self.assertFalse(model.pulse_gate(q, 0, readings)["accepted"])
        readings[:, 1, 1] = 1e-13
        self.assertFalse(model.pulse_gate(q, 0, readings)["accepted"])

    def test_pulse_gate_independent_calculation(self):
        for cond in range(3):
            q = self.a["reference_selected"][0, cond]
            reads = self.a["probe_readings"][0, cond, 0]
            j = int(self.a["command_indices"][0, cond, 0, 0])
            produced = model.pulse_gate(q, j, reads)
            selected, accepted, evidence, stats = audit.replay_pulse(q, j, reads)
            np.testing.assert_array_equal(produced["selected"], selected)
            self.assertEqual(produced["accepted"], accepted)
            np.testing.assert_allclose(produced["statistics"], stats, atol=1e-14)
            np.testing.assert_allclose(produced["evidence"], evidence, atol=1e-14)

    def test_uniform_calibration_recovers_three_cycle_without_history(self):
        route, records, noise, _ = self.fixture()
        readings = model.pulse_readings(records, route, 0.25 * np.eye(8), noise, noise, "upstream")
        result = model.uniform_calibration(readings)
        correction, ties, search = audit.replay_uniform(readings)
        np.testing.assert_array_equal(result["selected"], np.argsort(route))
        np.testing.assert_array_equal(correction, np.argsort(route))
        self.assertEqual(result["ties"], 1)
        self.assertEqual(ties, 1)
        np.testing.assert_allclose(result["search"], search, atol=1e-14)

    def test_uniform_calibration_healthy_shift_stays_identity(self):
        route, records, noise, _ = self.fixture()
        readings = model.pulse_readings(records[:, route], np.arange(8), 0.25 * np.eye(8), noise, noise, "upstream")
        np.testing.assert_array_equal(model.uniform_calibration(readings)["selected"], np.arange(8))

    def test_uniform_tie_is_lexicographic(self):
        readings = np.zeros((8, 2, 8))
        result = model.uniform_calibration(readings)
        self.assertEqual(result["ties"], 40320)
        np.testing.assert_array_equal(result["selected"], np.arange(8))
        self.assertEqual(audit.replay_uniform(readings)[1], 40320)

    def test_sensor_known_gain_and_first_last_noise_impulses(self):
        noise = np.zeros((1, 8, 8))
        noise[0, 0, 0], noise[0, -1, 1] = 1, 1
        observed = model.sensor_drive(np.ones((1, 8)), noise)
        gain = 1 - 0.6 ** 8
        self.assertAlmostEqual(observed[0, 0], 1 + 0.05 * 0.6 ** 7 / gain)
        self.assertAlmostEqual(observed[0, 1], 1 + 0.05 / gain)
        np.testing.assert_allclose(observed[0, 2:], 1, atol=1e-14)

    def test_controller_signatures_cannot_receive_hidden_labels(self):
        self.assertEqual(list(inspect.signature(model.pulse_gate).parameters), ["proposed", "command_index", "paired_readings"])
        self.assertEqual(list(inspect.signature(model.uniform_calibration).parameters), ["paired_readings"])
        self.assertEqual(list(inspect.signature(model.repair).parameters), ["reference", "proposal_readings", "validation_readings"])

    def test_selected_channel_and_identity_fallback(self):
        self.assertEqual(model.selected_channel(np.arange(8)), 0)
        self.assertEqual(model.selected_channel(np.asarray([0, 1, 3, 2, 4, 5, 6, 7])), 2)

    def test_off_on_noise_and_phase_streams_are_separate(self):
        draws = [model.field_rng(phase, 0, field).standard_normal(64) for phase, field in (
            ("qualification", "diagnostic_off_noise"), ("qualification", "diagnostic_on_noise"),
            ("benchmark", "diagnostic_off_noise"), ("qualification", "assessment_noise"))]
        for i in range(len(draws)):
            for j in range(i):
                self.assertFalse(np.array_equal(draws[i], draws[j]))
        replay = model.field_rng("qualification", 0, "diagnostic_off_noise").standard_normal(64)
        np.testing.assert_array_equal(draws[0], replay)

    def test_protected_arrays_cannot_be_mutated(self):
        for field, label in (("assessment_records", "record"), ("learned_references", "reference"), ("diagnostic_records", "diagnostic")):
            self.assertFalse(self.a[field].flags.writeable)
            self.assertEqual(self.meta[label + "_sha256_before"], self.meta[label + "_sha256_after"])
            with self.assertRaises(ValueError):
                self.a[field].flat[0] = 9

    def test_diagnostic_actuation_cannot_enter_assessment(self):
        original = model.pulse_readings
        def disable(records, route, commands, off_noise, on_noise, placement):
            return original(records, route, commands, off_noise, on_noise, "sham")
        with patch.object(model, "pulse_readings", side_effect=disable):
            changed, meta = model.generate_block("qualification", 0)
        for field in ("assessment_records", "assessment_readings", "learned_references", "reference_selected"):
            np.testing.assert_array_equal(changed[field], self.a[field])
        self.assertEqual(meta["record_sha256_after"], self.meta["record_sha256_after"])

    def test_equal_sensing_and_command_norm_allowances(self):
        np.testing.assert_allclose((self.a["commands"] ** 2).sum(axis=(-1, -2)), 0.5, atol=1e-14)
        self.assertEqual(self.a["probe_readings"].shape[-3:], (8, 2, 8))
        # All probes have the same off-read observations, including sham.
        for p in range(1, 5):
            np.testing.assert_array_equal(self.a["probe_readings"][:, :, p, :, 0], self.a["probe_readings"][:, :, 0, :, 0])

    def test_full_disposable_replay_and_compact_archive(self):
        self.assertTrue(self.replayed["passed"])
        self.assertLess(self.replayed["max_abs_replay_error"], 1e-10)
        self.assertFalse(any(key.endswith("_noise") or key.endswith("_base") for key in self.a))
        np.testing.assert_allclose(model.block_metrics(self.a), self.replayed["independent_block_metrics"], atol=1e-12)
        self.assertEqual(model.block_diagnostics(self.a), self.replayed["independent_block_diagnostics"])

    def test_observation_tampering_is_rejected(self):
        changed = dict(self.a)
        changed["probe_readings"] = changed["probe_readings"].copy()
        changed["probe_readings"][0, 0, 0, 0, 1, 0] += 0.01
        with self.assertRaises(audit.AuditError):
            audit.audit_block(changed, self.meta)

    def test_protected_record_tampering_with_resealed_hash_is_rejected(self):
        changed, meta = dict(self.a), dict(self.meta)
        changed["assessment_records"] = changed["assessment_records"].copy()
        changed["assessment_records"][0, 0, 0, 0] += 0.01
        digest = hashlib.sha256(changed["assessment_records"].tobytes()).hexdigest()
        meta["record_sha256_before"] = meta["record_sha256_after"] = digest
        with self.assertRaises(audit.AuditError):
            audit.audit_block(changed, meta)

    def test_wrong_rng_namespace_is_rejected(self):
        meta = {**self.meta, "block": 1}
        with self.assertRaises(audit.AuditError):
            audit.audit_block(self.a, meta)

    def test_wrong_shape_dtype_missing_and_nonfinite_rejected(self):
        mutations = (("fault", self.a["fault"].astype(float)), ("errors", self.a["errors"][:1]),
                     ("errors", np.full_like(self.a["errors"], np.nan)))
        for field, value in mutations:
            with self.subTest(field=field, shape=value.shape):
                with self.assertRaises(audit.AuditError):
                    audit.audit_block({**self.a, field: value}, self.meta)
        missing = dict(self.a)
        missing.pop("commands")
        with self.assertRaises(audit.AuditError):
            audit.audit_block(missing, self.meta)

    def test_auditor_never_imports_production_or_reporting(self):
        tree = ast.parse(inspect.getsource(audit))
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        self.assertNotIn("model", imports)
        self.assertNotIn("reporting", imports)
        self.assertNotIn("learned_reference.model", imports)


class WorkflowQualification(unittest.TestCase):
    def synthetic(self):
        values = np.zeros((64, 3, 8, 3))
        values[..., 0] = 1
        values[:, 1, 1:, 0] += np.arange(64)[:, None] / 64 + 1
        diagnostics = {"reference_proposal_counts": [0, 0, 0], "reference_accept_counts": [0, 0, 0],
                       "probe_accept_counts": np.zeros((3, 5), dtype=int).tolist(),
                       "command_pair_counts": np.zeros((3, 5, 8), dtype=int).tolist()}
        return values, [copy.deepcopy(diagnostics) for _ in range(64)]

    def test_block_bootstrap_and_equal_condition_weighting(self):
        values, diagnostics = self.synthetic()
        summary = summarize(values, diagnostics)
        self.assertTrue(audit.audit_summary(summary, values, diagnostics)["passed"])
        expected = (1 + np.arange(64) / 64) / 2
        np.testing.assert_allclose(summary["contrasts"]["primary_downstream_minus_upstream"]["block_effects"], expected)
        self.assertEqual(summary["primary_label"], "GAIN")
        self.assertEqual(len(summary["contrasts"]), 14)

    def test_summary_tampering_rejected(self):
        values, diagnostics = self.synthetic()
        summary = summarize(values, diagnostics)
        for key in ("effect", "diagnostic", "label", "budget"):
            altered = copy.deepcopy(summary)
            if key == "effect":
                altered["contrasts"]["primary_downstream_minus_upstream"]["mean"] += 0.01
            elif key == "diagnostic":
                altered["diagnostics"]["reference_accept_counts"][1] = 1
            elif key == "label":
                altered["primary_label"] = "HARM"
            else:
                altered["read_budget_per_arm_condition"]["diagnostic"] = 8
            with self.subTest(key=key), self.assertRaises(audit.AuditError):
                audit.audit_summary(altered, values, diagnostics)

    def test_partial_blocks_cannot_produce_verdict(self):
        values, diagnostics = self.synthetic()
        with self.assertRaises(ValueError):
            summarize(values[:63], diagnostics[:63])

    def test_four_spawned_workers_obey_affinity_and_thread_limits(self):
        cpus = runner.cpu_limit()
        ctx = mp.get_context("spawn")
        queue = ctx.Queue()
        processes = [ctx.Process(target=runner.workflow_probe, args=(queue,)) for _ in range(4)]
        try:
            for process in processes:
                process.start()
            receipts = [queue.get(timeout=20) for _ in processes]
            self.assertEqual(len({receipt["pid"] for receipt in receipts}), 4)
            for receipt in receipts:
                self.assertEqual(receipt["cpus"], cpus)
                self.assertTrue(all(value == "1" for value in receipt["threads"].values()))
            for process in processes:
                process.join(timeout=20)
                self.assertEqual(process.exitcode, 0)
        finally:
            for process in processes:
                if process.is_alive():
                    process.terminate()
                    process.join()
            queue.close()
            queue.join_thread()

    def test_safe_root_excludes_sister_projects_and_existing_capsules(self):
        with self.assertRaises(ValueError):
            runner.safe_root(runner.PROJECT.parent / "other-project")
        with self.assertRaises(ValueError):
            runner.safe_root(runner.RUNS)
        self.assertEqual(runner.safe_root(runner.RUNS / "im3-v1"), (runner.RUNS / "im3-v1").resolve())

    def test_json_exclusive_receipt_does_not_overwrite(self):
        with tempfile.TemporaryDirectory(dir=runner.RUNS) as directory:
            path = Path(directory) / "claim.json"
            runner.write_json(path, {"run": 1}, exclusive=True)
            with self.assertRaises(FileExistsError):
                runner.write_json(path, {"run": 2}, exclusive=True)
            self.assertEqual(runner.read_json(path), {"run": 1})

    def test_source_closure_contains_pinned_reference_implementation_and_auditor(self):
        hashes = runner.source_hashes()
        for name in ("model.py", "audit.py", "spec.py", "__init__.py"):
            self.assertIn("learned_reference/" + name, hashes)
        self.assertIn("EXPERIMENT_IM3_CAUSAL_PROBE_V1.md", hashes)
        self.assertIn("tests/test_im3_causal_probe.py", hashes)


if __name__ == "__main__":
    unittest.main()
