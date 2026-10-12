from __future__ import annotations

import inspect
from pathlib import Path
import tempfile
import unittest

import numpy as np

from plastic_ca import motif_phenotype_bridge as pb
from plastic_ca.cli import build_parser
from plastic_ca.motif_latent_regeneration import (
    DEFAULT_STAGE6L_ROOT,
    LatentRegenerationContract,
    PROFILES,
    _bit_codec_roundtrip,
    _canonicalize_motion_phase,
    _localization_specs,
    _orientation_from_velocity,
    _parent_integrity,
    run_motif_latent_regeneration,
)


class LatentRegenerationIntegrityTests(unittest.TestCase):
    def test_parent_has_retained_traces_and_sealed_reserve(self) -> None:
        result = _parent_integrity(DEFAULT_STAGE6L_ROOT)
        self.assertTrue(result["stage_gate"])
        self.assertEqual(result["retained_trace_count"], 112)
        self.assertEqual(result["final_pair_count"], 62)
        self.assertEqual(result["final_audit_trajectory_state"], "untouched")

    def test_caps_precede_output_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "stage6m"
            with self.assertRaises(ValueError):
                run_motif_latent_regeneration(root, profile_name="smoke", workers=5)
            self.assertFalse(root.exists())
            with self.assertRaises(ValueError):
                run_motif_latent_regeneration(root, profile_name="smoke", max_hours=8.01)
            self.assertFalse(root.exists())


class LatentRegenerationDesignTests(unittest.TestCase):
    def test_localization_grid_contains_promotable_and_ceiling_cells(self) -> None:
        specs = _localization_specs(PROFILES["reference"])
        self.assertEqual(len(specs), 48)
        self.assertEqual(len({row["spec_id"] for row in specs}), 48)
        self.assertTrue(any(row["mode"] == "local" and row["promotable"] for row in specs))
        self.assertTrue(any(row["mode"] == "whole-board" and not row["promotable"] for row in specs))
        self.assertEqual({row["endpoint"] for row in specs}, {16, 24, 32, 40, 48, 64})

    def test_runtime_writer_interface_has_no_target_or_parent_field(self) -> None:
        parameters = inspect.signature(pb._adaptive_handoff_update).parameters
        for forbidden in ("target", "environment", "parent_field", "pair_id", "generation"):
            self.assertNotIn(forbidden, parameters)

    def test_contract_keeps_original_reserve_unreachable(self) -> None:
        contract = LatentRegenerationContract().to_dict()
        self.assertEqual(contract["final_reserve_policy"], "unreachable-and-never-open-in-stage-6m")
        self.assertLessEqual(contract["abstract_payload_bits_maximum"], 8)


class LatentRegenerationCodecTests(unittest.TestCase):
    def test_bit_codec_roundtrip_and_corruption_flag(self) -> None:
        payload = np.asarray([1, 0, 1, 1, 0, 0, 1], dtype=np.uint8)
        decoded, exact = _bit_codec_roundtrip(payload, 7, corruption=0.0)
        np.testing.assert_array_equal(decoded, payload)
        self.assertTrue(exact)

    def test_all_d4_directions_get_an_orientation(self) -> None:
        diagonal = {
            _orientation_from_velocity((dy, dx))
            for dy, dx in ((1, 1), (1, -1), (-1, 1), (-1, -1))
        }
        axial = {
            _orientation_from_velocity((dy, dx))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))
        }
        self.assertEqual(len(diagonal), 4)
        self.assertEqual(len(axial), 4)

    def test_phase_canonicalization_ignores_cycle_start(self) -> None:
        a = np.zeros((32, 32), dtype=np.bool_)
        b = np.zeros_like(a)
        a[15, 15] = True
        b[15, 16] = True
        history = [a, b, a, b]
        first, orientation_a = _canonicalize_motion_phase(history, 0, 2, (1, 1))
        second, orientation_b = _canonicalize_motion_phase(history, 1, 2, (1, 1))
        np.testing.assert_array_equal(first, second)
        self.assertEqual(orientation_a, orientation_b)

    def test_closure_predict_accepts_discrete_latent_codebook(self) -> None:
        rng = np.random.default_rng(61)
        history = [rng.random((2, 16, 16)) < 0.4 for _ in range(32)]
        centers = np.asarray([[5, 7], [10, 11]], dtype=np.int16)
        dimension = 4 * 9 * 9 + 1
        codebook = np.stack((np.full(32, -0.5), np.full(32, 0.5)))
        model = {
            "kind": "sketched-ridge",
            "radius": 4,
            "window": 32,
            "canonicalize": False,
            "input_mean": np.zeros(dimension).tolist(),
            "input_scale": np.ones(dimension).tolist(),
            "projection": np.zeros((dimension, 3)).tolist(),
            "projection_phase": np.zeros(3).tolist(),
            "weights": np.zeros((3, 2)).tolist(),
            "bias": [-1.0, 1.0],
            "latent_kind": "codebook",
            "latent_codebook": codebook.tolist(),
            "output_space": "q4-coefficients",
            "output_rank": 16,
            "model_frozen": True,
            "runtime_target_labels": False,
        }
        prediction = pb._closure_model_predict(history, centers, model)
        self.assertEqual(prediction.shape, (2, 2, 4, 4))
        self.assertTrue(np.all(np.isfinite(prediction)))


class LatentRegenerationCliTests(unittest.TestCase):
    def test_cli_accepts_detached_stage6m(self) -> None:
        args = build_parser().parse_args(
            [
                "ca-motif-lineage",
                "--stage", "latent-regeneration",
                "--profile", "smoke",
                "--output", "results/test-stage6m",
                "--stage6l-root", str(DEFAULT_STAGE6L_ROOT),
                "--workers", "4",
                "--detach",
            ]
        )
        self.assertEqual(args.stage, "latent-regeneration")
        self.assertEqual(args.stage6l_root, DEFAULT_STAGE6L_ROOT)
        self.assertEqual(args.workers, 4)
        self.assertTrue(args.detach)


if __name__ == "__main__":
    unittest.main()
