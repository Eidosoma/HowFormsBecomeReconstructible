from __future__ import annotations

import inspect
from pathlib import Path
import tempfile
import unittest

import numpy as np

from plastic_ca.motif_acquisition_repair import (
    ACQUISITION_REPAIR_PROFILES,
    AcquisitionRepairContract,
    _prepare_stage6cr,
    _texture_field_at_centers,
    apply_texture_reader,
    build_acquisition_repair_candidates,
    observe_texture,
    run_motif_acquisition_repair,
    texture_decode,
    texture_encode,
    texture_seed_origins,
    walsh_texture_basis,
)
from plastic_ca.motif_synergistic_heredity import _encode_carrier


class AcquisitionRepairPrimitiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = AcquisitionRepairContract()
        cls.candidates = build_acquisition_repair_candidates()

    def test_walsh_basis_is_orthogonal_and_full_rank_roundtrips(self) -> None:
        basis = walsh_texture_basis()
        np.testing.assert_allclose(basis @ basis.T, 16.0 * np.eye(16))
        rng = np.random.default_rng(6200)
        patches = np.where(rng.random((5, 4, 4)) < 0.5, -1.0, 1.0)
        np.testing.assert_allclose(
            texture_decode(texture_encode(patches, 16), 16), patches
        )

    def test_candidate_grid_is_exact_and_rank_stratified(self) -> None:
        self.assertEqual(len(self.candidates), 24)
        self.assertEqual({row["rank"] for row in self.candidates}, {4, 8, 16})
        self.assertEqual(
            {row["read_strength"] for row in self.candidates}, {0.35, 0.60}
        )
        self.assertEqual(
            {row["read_sweeps"] for row in self.candidates}, {32, 48}
        )
        self.assertEqual({row["rho"] for row in self.candidates}, {0.50, 0.75})

    def test_writer_and_reader_apis_have_no_target_or_label(self) -> None:
        for function in (observe_texture, apply_texture_reader):
            parameters = inspect.signature(function).parameters
            for forbidden in ("target", "template", "label", "prototype"):
                self.assertNotIn(forbidden, parameters)

    def test_local_constellation_reconstructs_only_with_all_shares(self) -> None:
        candidate = self.candidates[-1]
        centers = np.asarray([[8, 8], [5, 11]], dtype=np.int16)
        patches = np.asarray(
            [
                np.where(np.indices((4, 4)).sum(axis=0) % 2, 1.0, -1.0),
                np.where(np.indices((4, 4))[0] < 2, 1.0, -1.0),
            ],
            dtype=np.float32,
        )
        payload = texture_encode(patches, int(candidate["rank"]))
        shares, active = _encode_carrier(
            payload, candidate, self.contract, "test-pair", 1
        )
        decoded, valid, _ = _texture_field_at_centers(
            shares, active, centers, candidate, 16, 3
        )
        self.assertTrue(bool(np.all(valid)))
        self.assertGreater(float(np.mean(np.abs(decoded))), 0.0)
        active[:, -1] = False
        decoded, valid, _ = _texture_field_at_centers(
            shares, active, centers, candidate, 16, 3
        )
        self.assertFalse(bool(np.any(valid)))
        np.testing.assert_array_equal(decoded, 0.0)

    def test_environment_observer_reads_visible_cells_only(self) -> None:
        state = np.zeros((2, 16, 16), dtype=np.bool_)
        centers = np.asarray([[8, 8], [4, 12]], dtype=np.int16)
        origins = texture_seed_origins(centers, 16, 3)
        self.assertEqual(origins.shape, (2, 4, 2))
        state[0, 6:10, 6:10] = True
        observed = observe_texture(state, centers)
        np.testing.assert_array_equal(observed[0], 1.0)
        np.testing.assert_array_equal(observed[1], -1.0)


class AcquisitionRepairWorkflowTests(unittest.TestCase):
    def test_worker_and_wall_caps_precede_output_preparation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                run_motif_acquisition_repair(
                    Path(directory), profile_name="smoke", workers=5
                )
            with self.assertRaises(ValueError):
                run_motif_acquisition_repair(
                    Path(directory), profile_name="smoke", max_hours=8.01
                )

    def test_preparation_uses_exposed_pairs_and_keeps_reserve_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            prepared = _prepare_stage6cr(
                Path(directory),
                "smoke",
                auto_final_audit=True,
                stage6c_root=Path("results/ca-motif-lineage-stage-6c"),
                stage6br_root=Path("results/ca-motif-lineage-stage-6br"),
                stage5r_root=Path("results/ca-motif-lineage-stage-5r"),
                stage5_root=Path("results/ca-motif-lineage-stage-5"),
                stage4_root=Path("results/ca-motif-lineage-stage-4"),
                stage3r_root=Path("results/ca-motif-lineage-stage-3r"),
                stage3_root=Path("results/ca-motif-lineage-stage-3"),
                stage2_root=Path("results/ca-motif-lineage-stage-2"),
                stage1_root=Path("results/ca-motif-lineage-stage-1"),
            )
            cohorts = prepared[1]
            self.assertEqual(cohorts["final"], [])
            self.assertEqual(
                sum(len(cohorts[key]) for key in ("screen", "qualification", "endurance")),
                6,
            )
            payload = __import__("json").loads(
                (Path(directory) / "COHORTS.json").read_text()
            )
            self.assertEqual(payload["final_audit_trajectory_state"], "untouched")
            self.assertTrue(payload["final_audit_trajectories_not_loaded"])

    def test_profile_limits_are_within_exposed_bank(self) -> None:
        reference = ACQUISITION_REPAIR_PROFILES["reference"]
        self.assertEqual(
            reference.screen_pairs
            + reference.qualification_pairs
            + reference.endurance_pairs,
            64,
        )
        self.assertEqual(reference.final_pairs, 62)


if __name__ == "__main__":
    unittest.main()
