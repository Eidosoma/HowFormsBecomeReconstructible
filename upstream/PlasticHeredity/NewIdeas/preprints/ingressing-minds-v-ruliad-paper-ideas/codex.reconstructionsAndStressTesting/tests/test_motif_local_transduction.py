from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import numpy as np

from plastic_ca import motif_acquisition_repair as ar
from plastic_ca import motif_phenotype_bridge as pb
from plastic_ca import motif_writeback_ladder as wb
from plastic_ca.motif_local_transduction import (
    DEFAULT_STAGE6F_ROOT,
    LocalTransductionContract,
    _candidate_specs,
    _extract_dataset,
    _fit_linear,
    _predict,
    _stage6f_integrity,
    run_motif_local_transduction,
)
from tests.test_motif_phenotype_bridge import ROOTS, frontends


class LocalTransductionIntegrityTests(unittest.TestCase):
    def test_stage6f_parent_is_complete_observable_and_reserve_sealed(self) -> None:
        result = _stage6f_integrity(DEFAULT_STAGE6F_ROOT)
        self.assertTrue(result["stage_gate"])
        self.assertEqual(result["parent_verdict"], "OBSERVABLE_NOT_WRITABLE")
        self.assertEqual(result["trace_checkpoint_count"], 32)
        self.assertEqual(result["final_audit_trajectory_state"], "untouched")

    def test_worker_and_wall_caps_precede_preparation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                run_motif_local_transduction(
                    Path(directory), profile_name="smoke", workers=5
                )
            with self.assertRaises(ValueError):
                run_motif_local_transduction(
                    Path(directory), profile_name="smoke", max_hours=8.01
                )


class LocalTransductionDecoderTests(unittest.TestCase):
    def test_planted_cross_bit_mapping_is_recovered(self) -> None:
        rng = np.random.default_rng(91)
        features = rng.normal(size=(512, 16)).astype(np.float32)
        permutation = rng.permutation(16)
        targets = np.where(features[:, permutation] >= 0.0, 1.0, -1.0).astype(
            np.float32
        )
        model = _fit_linear(features, targets, 0.1, "full")
        prediction = np.where(_predict(model, features) >= 0.0, 1.0, -1.0)
        self.assertGreater(float(np.mean(prediction == targets)), 0.95)

        shuffled = model["weights"].copy()
        rng.shuffle(shuffled, axis=0)
        wrong = (features - model["input_mean"]) / model["input_scale"]
        wrong = np.where(wrong @ shuffled + model["bias"] >= 0.0, 1.0, -1.0)
        self.assertLess(float(np.mean(wrong == targets)), 0.70)

    def test_reference_training_dataset_is_pair_blocked_and_phase_locked(self) -> None:
        rows = wb._trace_rows(DEFAULT_STAGE6F_ROOT / "replay")
        patch_x, bits, groups = _extract_dataset(rows, 40, "patch", 1, "intact")
        radius_x, radius_bits, radius_groups = _extract_dataset(
            rows, 40, "2", 1, "intact"
        )
        self.assertEqual(patch_x.shape[1], 16)
        self.assertEqual(radius_x.shape[1], 25)
        self.assertEqual(bits.shape[1], 16)
        self.assertEqual(len(set(groups.tolist())), 8)
        np.testing.assert_array_equal(bits, radius_bits)
        np.testing.assert_array_equal(groups, radius_groups)

    def test_candidate_allocation_is_four_four_four_and_frozen(self) -> None:
        frontend = frontends()[0]
        frontend.update({"read_sweeps": 40, "clearance_updates": 1, "trace_sweeps": 1})
        base_transform = {
            "transform_id": "test-transform",
            "kind": "linear",
            "input_mode": "stack",
            "target_space": "visible-bits",
            "input_mean": [0.0] * 16,
            "input_scale": [1.0] * 16,
            "weights": np.eye(16, dtype=np.float32).tolist(),
            "bias": [0.0] * 16,
            "model_frozen": True,
            "training_pair_count": 8,
            "training_pair_ids_sha256": "a" * 64,
            "model_sha256": "b" * 64,
        }
        decoders = []
        for index, (target, radius) in enumerate(
            (("visible-bits", "patch"), ("visible-bits", "2"), ("walsh-coefficients", "patch"), ("walsh-coefficients", "2"))
        ):
            dimension = 16 if radius == "patch" else 25
            transform = dict(base_transform)
            transform.update(
                {
                    "transform_id": f"test-{index}",
                    "target_space": target,
                    "input_mean": [0.0] * dimension,
                    "input_scale": [1.0] * dimension,
                    "weights": np.zeros((dimension, 16), dtype=np.float32).tolist(),
                }
            )
            decoders.append(
                {
                    "decoder_id": f"test-{index}",
                    "source_read_sweeps": 40,
                    "writer_observation_radius": radius,
                    "trace_sweeps": 1,
                    "target_space": target,
                    "carrier_roundtrip_accuracy": {"mean": 0.8, "ci": [0.75, 0.85]},
                    "intact_minus_sham": {"mean": 0.3, "ci": [0.2, 0.4]},
                    "writer_transform": transform,
                }
            )
        specs = _candidate_specs(decoders, frontend)
        self.assertEqual(len(specs), 12)
        self.assertEqual(sum(row["training_mode"] == "label-free" for row in specs), 4)
        self.assertEqual(sum(row["mechanism"] == "timing-only" and row["training_mode"] == "rulebook-assisted" for row in specs), 4)
        self.assertEqual(sum(row["mechanism"] == "somatic-field" for row in specs), 4)
        self.assertTrue(
            all(
                row["writer_transform"]["model_frozen"]
                for row in specs
                if row["training_mode"] == "rulebook-assisted"
            )
        )


class LocalTransductionRuntimeTests(unittest.TestCase):
    @staticmethod
    def _translated_spec(*, promotable: bool = True, kind: str = "linear") -> dict[str, object]:
        frontend = frontends()[0]
        frontend.update(
            {
                "frontend_id": "runtime-transform-test",
                "read_sweeps": 40,
                "clearance_updates": 1,
                "trace_sweeps": 1,
            }
        )
        transform: dict[str, object] = {
            "transform_id": "identity-linear-test",
            "kind": kind,
            "model_frozen": True,
        }
        if kind == "linear":
            transform.update(
                {
                    "input_mode": "stack",
                    "target_space": "visible-bits",
                    "input_mean": [0.0] * 16,
                    "input_scale": [1.0] * 16,
                    "weights": np.eye(16, dtype=np.float32).tolist(),
                    "bias": [0.0] * 16,
                }
            )
        return {
            "candidate_id": "runtime-translator",
            "claim_tier": "broad",
            "claim_class": "rulebook-assisted-local",
            "training_mode": (
                "teacher-assisted-control" if kind == "target-ceiling" else "rulebook-assisted"
            ),
            "mechanism": "timing-only",
            "writer_source": "visible",
            "writer_input_contract": "visible-only",
            "writer_feature": "endpoint",
            "writer_observation_radius": "patch",
            "somatic_architecture": "none",
            "somatic_channels": 1,
            "somatic_retention": 0.0,
            "somatic_bias": 0.0,
            "writer_transform": transform,
            "promotable": promotable,
            "frontend": frontend,
        }

    def test_founder_bypasses_frozen_translator_and_daughter_uses_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            frozen, cohorts, _, _, writer_contract, templates, _ = pb._prepare_stage6e(
                Path(directory), "smoke", auto_final_audit=True, **ROOTS
            )
            candidate = pb.build_writeback_candidates([self._translated_spec()])[0][0]
            result, _ = pb.simulate_phenotype_lineage(
                pair=cohorts["bridge"][0],
                configuration=frozen["stage4"]["configuration"],
                candidate=candidate,
                condition="intact",
                replicates=1,
                generations=5,
                reference=frozen["stage4"]["reference"],
                writer_contract=writer_contract,
                contract=LocalTransductionContract(),
                environmental_template=np.asarray(templates[0]["bits"], dtype=np.bool_),
            )
            self.assertEqual(
                result["writer_history"]["4"]["writer_transform_kind"],
                "founder-bypass",
            )
            self.assertEqual(
                result["writer_history"]["5"]["writer_transform_kind"], "linear"
            )
            self.assertTrue(result["writer_history"]["5"]["writer_transform_frozen"])
            self.assertFalse(result["writer_history"]["5"]["writer_transform_target_exposed"])
            self.assertTrue(result["all_renewal_writer_windows_carrier_absent"])
            self.assertTrue(result["environment_not_passed_to_writer"])

    def test_target_exposed_control_cannot_be_promotable(self) -> None:
        with self.assertRaises(ValueError):
            pb.build_writeback_candidates(
                [self._translated_spec(promotable=True, kind="target-ceiling")]
            )
        control = pb.build_writeback_candidates(
            [self._translated_spec(promotable=False, kind="target-ceiling")]
        )[0][0]
        self.assertFalse(control["promotable"])
        self.assertEqual(control["training_mode"], "teacher-assisted-control")


if __name__ == "__main__":
    unittest.main()
