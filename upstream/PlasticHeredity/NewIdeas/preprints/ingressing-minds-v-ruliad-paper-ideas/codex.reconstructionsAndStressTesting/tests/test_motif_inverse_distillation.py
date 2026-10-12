from __future__ import annotations

import inspect
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from plastic_ca import motif_minimality as mm
from plastic_ca import motif_phenotype_bridge as pb
from plastic_ca.cli import build_parser
from plastic_ca.motif_inverse_distillation import (
    DEFAULT_STAGE6H_ROOT,
    DEFAULT_STAGE6I_ROOT,
    DEFAULT_STAGE6J_ROOT,
    DEFAULT_STAGE6K_ROOT,
    InverseDistillationContract,
    _motion_codec_roundtrip,
    _parent_integrity,
    _procedural_pairs,
    _transform_velocity,
    _writer_configs,
    run_motif_inverse_distillation,
)


class InverseDistillationIntegrityTests(unittest.TestCase):
    def test_parent_has_56_exposed_and_62_sealed(self) -> None:
        result = _parent_integrity(
            DEFAULT_STAGE6K_ROOT,
            DEFAULT_STAGE6J_ROOT,
            DEFAULT_STAGE6I_ROOT,
            DEFAULT_STAGE6H_ROOT,
        )
        self.assertTrue(result["stage_gate"])
        self.assertEqual(result["exposed_pair_count"], 56)
        self.assertEqual(result["final_pair_count"], 62)
        self.assertEqual(result["final_audit_trajectory_state"], "untouched")

    def test_caps_are_checked_before_campaign_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                run_motif_inverse_distillation(root, profile_name="smoke", workers=5)
            self.assertFalse((root / "DESIGN.json").exists())
            with self.assertRaises(ValueError):
                run_motif_inverse_distillation(root, profile_name="smoke", max_hours=8.01)


class InverseDistillationWriterTests(unittest.TestCase):
    def test_factorial_has_exactly_24_coefficient_writers(self) -> None:
        configs = _writer_configs()
        self.assertEqual(len(configs), 24)
        self.assertEqual(len({row["config_id"] for row in configs}), 24)
        self.assertEqual({row["radius"] for row in configs}, {4, 6})
        self.assertEqual({row["window"] for row in configs}, {16, 32})
        self.assertEqual(
            {row["teacher"] for row in configs}, {"stable-oracle", "inverse-control"}
        )
        self.assertTrue(all(not row["canonicalize"] for row in configs))

    def test_runtime_writer_interface_excludes_parent_and_target(self) -> None:
        parameters = inspect.signature(pb._adaptive_handoff_update).parameters
        self.assertNotIn("parent_field", parameters)
        self.assertNotIn("target", parameters)
        self.assertNotIn("environment", parameters)
        self.assertNotIn("pair_id", parameters)
        self.assertNotIn("generation", parameters)

    def test_q4_coefficient_model_decodes_to_two_patches(self) -> None:
        rng = np.random.default_rng(61)
        history = [rng.random((2, 16, 16)) < 0.4 for _ in range(32)]
        centers = np.asarray([[5, 7], [10, 11]], dtype=np.int16)
        dimension = 4 * 13 * 13 + 1
        model = {
            "kind": "equivariant-ridge",
            "radius": 6,
            "window": 32,
            "canonicalize": False,
            "input_mean": np.zeros(dimension).tolist(),
            "input_scale": np.ones(dimension).tolist(),
            "weights": np.zeros((dimension, 32)).tolist(),
            "bias": np.linspace(-0.5, 0.5, 32).tolist(),
            "output_space": "q4-coefficients",
            "output_rank": 16,
            "model_frozen": True,
            "runtime_target_labels": False,
        }
        prediction = pb._closure_model_predict(history, centers, model)
        self.assertEqual(prediction.shape, (2, 2, 4, 4))
        self.assertTrue(np.all(np.isfinite(prediction)))


class InverseDistillationCohortTests(unittest.TestCase):
    def test_procedural_pairs_are_new_and_donor_disjoint(self) -> None:
        all_pairs = mm.load_round3_pairs()[mm.RULE]
        by_id = {str(row["pair_id"]): row for row in all_pairs}
        stage6k = json.loads(
            (DEFAULT_STAGE6K_ROOT / "stage6k/COHORTS.json").read_text()
        )
        frozen = mm.load_frozen_stage5r()
        excluded_ids = set(frozen["later_ids"])
        excluded_ids.update(stage6k["pair_ids"]["exposed"])
        excluded_ids.update(stage6k["pair_ids"]["heldout"])
        excluded_donors = {
            str(by_id[pair_id][side]["donor_id"])
            for pair_id in excluded_ids
            for side in ("donor_a", "donor_b")
        }
        created = _procedural_pairs(
            all_pairs,
            excluded_ids,
            excluded_donors,
            16,
            InverseDistillationContract().namespace,
        )
        self.assertEqual(len(created), 16)
        self.assertFalse({row["pair_id"] for row in created} & excluded_ids)
        self.assertTrue(
            all(
                row["donor_a"]["initial_state_hex"]
                == row["donor_b"]["initial_state_hex"]
                for row in created
            )
        )
        used = {
            str(row[side]["donor_id"])
            for row in created
            for side in ("donor_a", "donor_b")
        }
        self.assertFalse(used & excluded_donors)


class InverseDistillationMotionTests(unittest.TestCase):
    def test_motion_codec_requires_all_four_shares(self) -> None:
        rng = np.random.default_rng(7)
        field = rng.uniform(-1.0, 1.0, size=(4, 8, 8)).astype(np.float32)
        decoded, valid = _motion_codec_roundtrip(field, 9)
        _, subset_valid = _motion_codec_roundtrip(field, 9, subset=True)
        self.assertTrue(valid)
        self.assertFalse(subset_valid)
        self.assertLessEqual(float(np.max(np.abs(decoded - field))), 1.0 / 7.0 + 1e-6)

    def test_d4_velocity_transform_keeps_opposites_opposite(self) -> None:
        for symmetry in range(8):
            forward = np.asarray(_transform_velocity((1, 2), symmetry))
            opposite = np.asarray(_transform_velocity((-1, -2), symmetry))
            np.testing.assert_allclose(forward, -opposite)


class InverseDistillationCliTests(unittest.TestCase):
    def test_cli_accepts_detached_stage6l_and_parent_root(self) -> None:
        args = build_parser().parse_args(
            [
                "ca-motif-lineage",
                "--stage",
                "inverse-distillation",
                "--profile",
                "smoke",
                "--output",
                "results/test-stage6l",
                "--stage6k-root",
                str(DEFAULT_STAGE6K_ROOT),
                "--workers",
                "4",
                "--detach",
            ]
        )
        self.assertEqual(args.stage, "inverse-distillation")
        self.assertEqual(args.stage6k_root, DEFAULT_STAGE6K_ROOT)
        self.assertEqual(args.workers, 4)
        self.assertTrue(args.detach)


if __name__ == "__main__":
    unittest.main()
