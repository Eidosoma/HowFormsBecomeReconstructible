"""Analytic fault fixtures and disposable replay; never opens main randomness."""
import ast
import copy
import hashlib
import inspect
import multiprocessing as mp
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from causal_probe.spec import SPEC as PROBE_SPEC
from learned_reference.spec import SPEC as REFERENCE_SPEC
from probe_redundancy import audit, model, runner
from probe_redundancy.reporting import summarize
from probe_redundancy.spec import APPARATUS, ARMS, CONDITIONS, HISTORY, SPEC, TARGET


class MechanismQualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a, cls.meta = model.generate_block("qualification", 0)
        cls.replayed = audit.audit_block(cls.a, cls.meta)

    def fixture(self, reader_failed, environment_changed, failed_paths):
        identity = np.arange(8)
        fault = np.asarray([1, 0, 3, 2, 4, 5, 6, 7])
        records = np.arange(64, dtype=float).reshape(8, 8) / 32
        if environment_changed:
            records = records[:, fault]
        reader = fault if reader_failed else identity
        actuators = [fault if path in failed_paths else identity for path in range(3)]
        noise = np.zeros((8, 8, 8))
        targeted = np.zeros((8, 8))
        targeted[:, 0] = 0.25
        responses = []
        for scheme in range(3):
            commands = 0.25 * np.eye(8) if scheme == 2 else targeted
            responses.append(np.asarray([model.observed_pair(records, reader, actuators[0 if scheme == 1 else path], commands, noise, noise)
                                         for path in range(3)]))
        return fault, responses

    def test_inherited_numerical_contract(self):
        for key in ("channels", "sensor_steps", "retention", "noise_sd", "tie_tolerance", "gate_se_multiplier", "gate_floor"):
            self.assertEqual(SPEC[key], PROBE_SPEC[key])
            self.assertEqual(SPEC[key], REFERENCE_SPEC[key])
        self.assertEqual(SPEC["pulse_amplitude"], PROBE_SPEC["pulse_amplitude"])
        self.assertEqual(SPEC["pairs_per_path"], PROBE_SPEC["probe_pairs"])
        self.assertEqual(SPEC["paths"], 3)

    def test_noncommuting_reader_actuator_composition(self):
        reader = np.asarray([1, 2, 0, 3, 4, 5, 6, 7])
        actuator = np.asarray([0, 2, 3, 1, 4, 5, 6, 7])
        commands = 0.25 * np.eye(8)
        noise = np.zeros((8, 8, 8))
        readings = model.observed_pair(np.zeros((8, 8)), reader, actuator, commands, noise, noise)
        expected = (np.eye(8)[reader] @ np.eye(8)[actuator] @ commands.T).T
        wrong_order = (np.eye(8)[actuator] @ np.eye(8)[reader] @ commands.T).T
        np.testing.assert_allclose(readings[:, 1] - readings[:, 0], expected, atol=1e-14)
        self.assertFalse(np.array_equal(expected, wrong_order))

    def test_inverse_actuator_hides_non_self_inverse_reader(self):
        reader = np.asarray([1, 2, 0, 3, 4, 5, 6, 7])
        commands = 0.25 * np.eye(8)
        noise = np.zeros((8, 8, 8))
        readings = model.observed_pair(np.zeros((8, 8)), reader, np.argsort(reader), commands, noise, noise)
        np.testing.assert_allclose(readings[:, 1] - readings[:, 0], commands, atol=1e-14)

    def test_faulty_actuator_mimics_non_self_inverse_reader(self):
        route = np.asarray([1, 2, 0, 3, 4, 5, 6, 7])
        records = np.arange(64, dtype=float).reshape(8, 8) / 32
        noise = np.zeros((8, 8, 8))
        commands = 0.25 * np.eye(8)
        damaged = model.observed_pair(records, route, np.arange(8), commands, noise, noise)
        shifted = model.observed_pair(records[:, route], np.arange(8), route, commands, noise, noise)
        np.testing.assert_array_equal(damaged, shifted)

    def test_one_fault_all_locations_majority_repairs_reader(self):
        for location in range(3):
            q, responses = self.fixture(True, False, [location])
            result = model.reader_decisions(q, 0, *responses)
            np.testing.assert_array_equal(result["selected"][0], q)
            self.assertEqual(int(result["path_votes"][0].sum()), 2)
            np.testing.assert_array_equal(result["selected"][3], np.arange(8))
            np.testing.assert_array_equal(result["selected"][4], q)

    def test_one_fault_all_locations_majority_rejects_world_misrepair(self):
        for location in range(3):
            q, responses = self.fixture(False, True, [location])
            result = model.reader_decisions(q, 0, *responses)
            np.testing.assert_array_equal(result["selected"][0], np.arange(8))
            self.assertEqual(int(result["path_votes"][0].sum()), 1)
            np.testing.assert_array_equal(result["selected"][4], np.arange(8))

    def test_shared_path_fails_when_its_route_is_corrupted(self):
        q, responses = self.fixture(True, False, [0])
        result = model.reader_decisions(q, 0, *responses)
        np.testing.assert_array_equal(result["selected"][0], q)
        np.testing.assert_array_equal(result["selected"][1:3], np.tile(np.arange(8), (2, 1)))
        q, responses = self.fixture(False, True, [0])
        result = model.reader_decisions(q, 0, *responses)
        np.testing.assert_array_equal(result["selected"][1:3], np.tile(q, (2, 1)))

    def test_two_faults_reverse_majority_decisions(self):
        q, responses = self.fixture(True, False, [0, 1])
        result = model.reader_decisions(q, 0, *responses)
        np.testing.assert_array_equal(result["selected"][0], np.arange(8))
        q, responses = self.fixture(False, True, [0, 1])
        result = model.reader_decisions(q, 0, *responses)
        np.testing.assert_array_equal(result["selected"][0], q)
        np.testing.assert_array_equal(result["selected"][3], np.arange(8))

    def test_common_faults_hide_damage_and_imitate_it_after_world_change(self):
        q, responses = self.fixture(True, False, [0, 1, 2])
        result = model.reader_decisions(q, 0, *responses)
        np.testing.assert_array_equal(result["selected"][0], np.arange(8))
        q, responses = self.fixture(False, True, [0, 1, 2])
        result = model.reader_decisions(q, 0, *responses)
        np.testing.assert_array_equal(result["selected"][0], q)

    def test_pooled_rule_uses_24_observations_instead_of_group_votes(self):
        q = np.asarray([1, 0, 2, 3, 4, 5, 6, 7])
        shared = np.zeros((3, 8, 2, 8))
        shared[0, :, 1, 1] = 0.3
        result = model.reader_decisions(q, 0, shared, shared, np.zeros_like(shared))
        self.assertEqual(int(result["path_votes"][1].sum()), 1)
        self.assertTrue(result["pooled_accepted"])
        np.testing.assert_array_equal(result["selected"][1], np.arange(8))
        np.testing.assert_array_equal(result["selected"][2], q)

    def test_whole_mapping_consensus_and_abstention(self):
        identity = np.arange(8)
        q = np.asarray([1, 0, 2, 3, 4, 5, 6, 7])
        third = np.asarray([0, 1, 3, 2, 4, 5, 6, 7])
        for candidates, expected, accepted in (([q, identity, q], q, True),
                                               ([identity, identity, q], identity, True),
                                               ([identity, q, third], identity, False)):
            selected, agreement = model.mapping_consensus(np.asarray(candidates))
            np.testing.assert_array_equal(selected, expected)
            self.assertEqual(agreement, accepted)

    def test_identity_proposal_does_not_become_fault_diagnosis(self):
        _, responses = self.fixture(False, False, [0])
        result = model.reader_decisions(np.arange(8), 0, *responses)
        self.assertFalse(result["path_votes"].any())
        np.testing.assert_array_equal(result["selected"][:4], np.tile(np.arange(8), (4, 1)))

    def test_policy_signature_has_no_hidden_apparatus_information(self):
        self.assertEqual(list(inspect.signature(model.reader_decisions).parameters),
                         ["proposed", "command_index", "separate_reads", "shared_reads", "uniform_reads"])
        self.assertEqual(list(inspect.signature(model.mapping_consensus).parameters), ["candidates"])

    def test_reference_gate_parameters_and_sample_counts_unchanged(self):
        for key in ("reference_reads", "proposal_reads", "validation_reads"):
            self.assertEqual(SPEC[key], REFERENCE_SPEC[key])
        self.assertEqual(REFERENCE_SPEC["validation_batches"], 8)

    def test_condition_indexing_matches_declared_apparatus(self):
        for cond, name in enumerate(CONDITIONS):
            reader, environment, nfail = APPARATUS[cond]
            self.assertEqual(reader, name.startswith("reader_"))
            self.assertEqual(environment, name.startswith("environment_"))
            self.assertEqual(HISTORY[cond], int(reader != environment))
            self.assertEqual(TARGET[cond], int(environment))
            for case in range(4):
                routes = self.a["actuator_routes"][case, cond]
                self.assertEqual(int(np.any(routes != np.arange(8), axis=1).sum()), nfail)

    def test_shared_failure_histories_exactly_match_with_conflicting_oracles(self):
        for left, right in ((1, 9), (2, 8)):
            np.testing.assert_array_equal(self.a["probe_readings"][:, left], self.a["probe_readings"][:, right])
            np.testing.assert_array_equal(self.a["selected"][:, left, :7], self.a["selected"][:, right, :7])
            self.assertFalse(np.array_equal(self.a["selected"][:, left, 7], self.a["selected"][:, right, 7]))
        self.assertEqual(self.replayed["ambiguity_pairs_verified"], 8)

    def test_off_readings_and_pulse_norm_are_budget_matched(self):
        np.testing.assert_allclose(np.sum(self.a["commands"] ** 2, axis=(-1, -2, -3)), 1.5, atol=1e-14)
        for scheme in (1, 2):
            np.testing.assert_array_equal(self.a["probe_readings"][:, :, 0, :, :, 0], self.a["probe_readings"][:, :, scheme, :, :, 0])
        self.assertEqual(self.a["probe_readings"].shape[-4:], (3, 8, 2, 8))

    def test_path_and_off_on_noise_are_separate(self):
        off = model.field_rng("qualification", 0, "diagnostic_off_noise").standard_normal((4, 3, 8, 8, 8))
        on = model.field_rng("qualification", 0, "diagnostic_on_noise").standard_normal(off.shape)
        self.assertFalse(np.array_equal(off, on))
        for path in (1, 2):
            self.assertFalse(np.array_equal(off[:, 0], off[:, path]))
        other = model.field_rng("benchmark", 0, "diagnostic_off_noise").standard_normal(off.shape)
        self.assertFalse(np.array_equal(off, other))

    def test_protected_records_and_reference(self):
        for field, label in (("learned_references", "reference"), ("assessment_records", "record"), ("diagnostic_records", "diagnostic")):
            self.assertFalse(self.a[field].flags.writeable)
            self.assertEqual(self.meta[label + "_sha256_before"], self.meta[label + "_sha256_after"])
            with self.assertRaises(ValueError):
                self.a[field].flat[0] = 0

    def test_actuation_cannot_enter_assessment_or_prior(self):
        original = model.observed_pair
        def sham(records, reader, actuator, commands, off_noise, on_noise):
            return original(records, reader, actuator, np.zeros_like(commands), off_noise, on_noise)
        with patch.object(model, "observed_pair", side_effect=sham):
            changed, _ = model.generate_block("qualification", 0)
        for field in ("assessment_records", "assessment_readings", "learned_references", "reference_selected"):
            np.testing.assert_array_equal(changed[field], self.a[field])

    def test_complete_replay_and_compact_shared_history_archive(self):
        self.assertTrue(self.replayed["passed"])
        self.assertLess(self.replayed["max_abs_replay_error"], 1e-10)
        np.testing.assert_allclose(model.block_metrics(self.a), self.replayed["independent_block_metrics"], atol=1e-12)
        self.assertEqual(model.block_diagnostics(self.a), self.replayed["independent_block_diagnostics"])
        self.assertEqual(self.a["proposal_readings"].shape[1], 2)
        self.assertNotIn("predictions", self.a)
        self.assertFalse(any(key.endswith("_base") or key.endswith("_noise") for key in self.a))

    def test_tampered_observations_routes_and_errors_rejected(self):
        for key in ("probe_readings", "actuator_routes", "errors"):
            altered = dict(self.a)
            altered[key] = altered[key].copy()
            altered[key].flat[0] += 1
            with self.subTest(field=key), self.assertRaises(audit.AuditError):
                audit.audit_block(altered, self.meta)

    def test_resealed_changed_record_rejected(self):
        altered, meta = dict(self.a), dict(self.meta)
        altered["assessment_records"] = altered["assessment_records"].copy()
        altered["assessment_records"].flat[0] += 0.01
        digest = hashlib.sha256(altered["assessment_records"].tobytes()).hexdigest()
        meta["record_sha256_before"] = meta["record_sha256_after"] = digest
        with self.assertRaises(audit.AuditError):
            audit.audit_block(altered, meta)

    def test_wrong_shape_dtype_missing_and_nonfinite_rejected(self):
        for key, value in (("fault", self.a["fault"].astype(float)), ("errors", self.a["errors"][:1]),
                           ("errors", np.full_like(self.a["errors"], np.nan))):
            with self.subTest(key=key), self.assertRaises(audit.AuditError):
                audit.audit_block({**self.a, key: value}, self.meta)
        altered = dict(self.a)
        altered.pop("commands")
        with self.assertRaises(audit.AuditError):
            audit.audit_block(altered, self.meta)

    def test_wrong_random_namespace_rejected(self):
        with self.assertRaises(audit.AuditError):
            audit.audit_block(self.a, {**self.meta, "block": 1})

    def test_auditor_does_not_import_production(self):
        imported = [node.module for node in ast.walk(ast.parse(inspect.getsource(audit))) if isinstance(node, ast.ImportFrom)]
        for name in ("model", "reporting", "causal_probe.model", "learned_reference.model"):
            self.assertNotIn(name, imported)


class WorkflowQualification(unittest.TestCase):
    def synthetic(self):
        values = np.zeros((64, 10, 8, 3))
        values[..., 0] = 1
        values[:, 4, 1:, 0] += 1 + np.arange(64)[:, None] / 64
        shapes = {"reference_proposal_counts": (10,), "reference_accept_counts": (10,), "path_vote_counts": (10, 2, 3),
                  "disagreement_counts": (10, 2), "pooled_accept_counts": (10,), "uniform_consensus_counts": (10,),
                  "failed_location_counts": (3,), "command_pair_counts": (10, 3, 8)}
        diag = {key: np.zeros(shape, dtype=int).tolist() for key, shape in shapes.items()}
        return values, [copy.deepcopy(diag) for _ in range(64)]

    def test_equal_condition_weight_and_whole_block_bootstrap(self):
        values, diagnostics = self.synthetic()
        summary = summarize(values, diagnostics)
        self.assertTrue(audit.audit_summary(summary, values, diagnostics)["passed"])
        np.testing.assert_allclose(summary["contrasts"]["primary_shared_minus_redundant"]["block_effects"], (1 + np.arange(64) / 64) / 2)
        self.assertEqual(summary["primary_label"], "GAIN")
        self.assertEqual(len(summary["contrasts"]), 23)

    def test_out_of_contract_panels_do_not_change_primary(self):
        values, diagnostics = self.synthetic()
        before = summarize(values, diagnostics)
        values[:, 6:, :, 0] += np.arange(8) * 100
        after = summarize(values, diagnostics)
        self.assertEqual(before["contrasts"]["primary_shared_minus_redundant"], after["contrasts"]["primary_shared_minus_redundant"])
        self.assertNotEqual(before["contrasts"]["reader_two_frozen_minus_redundant"], after["contrasts"]["reader_two_frozen_minus_redundant"])

    def test_altered_contrast_diagnostic_label_or_budget_rejected(self):
        values, diagnostics = self.synthetic()
        summary = summarize(values, diagnostics)
        for key in ("contrast", "diagnostic", "label", "budget"):
            altered = copy.deepcopy(summary)
            if key == "contrast":
                altered["contrasts"]["primary_shared_minus_redundant"]["mean"] += 1
            elif key == "diagnostic":
                altered["diagnostics"]["failed_location_counts"][0] += 1
            elif key == "label":
                altered["primary_label"] = "HARM"
            else:
                altered["read_budget_per_arm_condition"]["diagnostic"] = 16
            with self.subTest(key=key), self.assertRaises(audit.AuditError):
                audit.audit_summary(altered, values, diagnostics)

    def test_partial_cohort_cannot_produce_verdict(self):
        values, diagnostics = self.synthetic()
        with self.assertRaises(ValueError):
            summarize(values[:63], diagnostics[:63])

    def test_four_spawned_processes_keep_cpu_and_thread_limits(self):
        cpus = runner.cpu_limit()
        ctx = mp.get_context("spawn")
        queue = ctx.Queue()
        workers = [ctx.Process(target=runner.workflow_probe, args=(queue,)) for _ in range(4)]
        try:
            for process in workers:
                process.start()
            receipts = [queue.get(timeout=20) for _ in workers]
            self.assertEqual(len({row["pid"] for row in receipts}), 4)
            for row in receipts:
                self.assertEqual(row["cpus"], cpus)
                self.assertTrue(all(value == "1" for value in row["threads"].values()))
            for process in workers:
                process.join(timeout=20)
                self.assertEqual(process.exitcode, 0)
        finally:
            for process in workers:
                if process.is_alive():
                    process.terminate()
                    process.join()
            queue.close()
            queue.join_thread()

    def test_source_closure_includes_transitive_frozen_dependencies(self):
        hashes = runner.source_hashes()
        for package in ("learned_reference", "causal_probe"):
            for name in ("model.py", "audit.py", "spec.py", "__init__.py"):
                self.assertIn(package + "/" + name, hashes)
        self.assertIn("EXPERIMENT_IM4_PROBE_REDUNDANCY_V1.md", hashes)
        self.assertIn("tests/test_im4_probe_redundancy.py", hashes)

    def test_safe_root_excludes_external_folders(self):
        with self.assertRaises(ValueError):
            runner.safe_root(runner.PROJECT.parent / "other-project")
        with self.assertRaises(ValueError):
            runner.safe_root(runner.RUNS)
        self.assertEqual(runner.safe_root(runner.RUNS / "im4-v1"), (runner.RUNS / "im4-v1").resolve())

    def test_exclusive_receipt_cannot_overwrite_existing_claim(self):
        with tempfile.TemporaryDirectory(dir=runner.RUNS) as directory:
            path = Path(directory) / "claim.json"
            runner.write_json(path, {"cohort": 1}, exclusive=True)
            with self.assertRaises(FileExistsError):
                runner.write_json(path, {"cohort": 2}, exclusive=True)
            self.assertEqual(runner.read_json(path), {"cohort": 1})


if __name__ == "__main__":
    unittest.main()
