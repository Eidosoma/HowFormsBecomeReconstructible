from __future__ import annotations

import inspect
from pathlib import Path
import tempfile
import unittest

import numpy as np

from plastic_ca import motif_phenotype_bridge as pb
from plastic_ca import motif_writer_closure as wc
from plastic_ca.cli import build_parser
from plastic_ca.life_family import parse_life_rule
from plastic_ca.motif_causal_attractor import (
    DEFAULT_STAGE6L_ROOT,
    DEFAULT_STAGE6M_ROOT,
    CausalAttractorContract,
    _binary_medoid_codebook,
    _foreground_overlap,
    _object_motion_metrics,
    _parent_integrity,
    run_motif_causal_attractor,
)


class CausalAttractorIntegrityTests(unittest.TestCase):
    def test_parent_keeps_both_reserves_sealed(self) -> None:
        result = _parent_integrity(DEFAULT_STAGE6M_ROOT, DEFAULT_STAGE6L_ROOT)
        self.assertTrue(result["stage_gate"])
        self.assertTrue(result["procedural_trajectories_sealed"])
        self.assertEqual(result["final_pair_count"], 62)
        self.assertEqual(result["final_audit_trajectory_state"], "untouched")

    def test_caps_precede_output_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "stage6n"
            with self.assertRaises(ValueError):
                run_motif_causal_attractor(root, profile_name="smoke", workers=5)
            self.assertFalse(root.exists())
            with self.assertRaises(ValueError):
                run_motif_causal_attractor(
                    root, profile_name="smoke", max_hours=8.01
                )
            self.assertFalse(root.exists())


class CausalAttractorCompactTests(unittest.TestCase):
    def test_compact_q4_codec_supports_two_values(self) -> None:
        model = {
            "latent_size": 2,
            "latent_scale": [1.0, 1.0],
        }
        codec = pb._field_codec_candidate(
            {
                "compact_latent_carrier": True,
                "closure_model": model,
            }
        )
        self.assertEqual(codec["rank"], 2)
        self.assertEqual(codec["payload_bits"], 8)

    def test_contract_excludes_runtime_parent_and_reserve(self) -> None:
        contract = CausalAttractorContract().to_dict()
        self.assertFalse(contract["runtime_parent_field"])
        self.assertFalse(contract["runtime_incoming_payload"])
        self.assertEqual(
            contract["final_reserve_policy"],
            "unreachable-and-never-open-in-stage-6n",
        )
        parameters = inspect.signature(pb._compact_model_code).parameters
        for forbidden in (
            "target",
            "environment",
            "parent_field",
            "incoming_payload",
            "pair_id",
            "generation",
        ):
            self.assertNotIn(forbidden, parameters)

    def test_registered_attractors_contract_one_bin_damage(self) -> None:
        prediction = np.asarray([[0.2, -0.4, 0.6, -0.1]], dtype=np.float32)
        damaged = prediction.copy()
        damaged[:, 0] += np.float32(1.0 / 7.0)
        for kind in ("leaky", "contractive-tanh", "prototype"):
            model = {
                "attractor_kind": kind,
                "attractor_retention": 0.65,
                "recurrent_gain": 0.55,
                "input_gain": 0.75,
                "prototype_strength": 0.35,
                "latent_prototypes": [prediction[0].tolist()],
            }
            updated = damaged
            for _ in range(3):
                updated = pb._compact_attractor_update(updated, prediction, model)
            self.assertLess(
                float(np.linalg.norm(updated - prediction)),
                float(np.linalg.norm(damaged - prediction)),
            )


class CausalAttractorObjectMetricTests(unittest.TestCase):
    def test_blank_background_always_scores_zero(self) -> None:
        blank = [np.zeros((32, 32), dtype=np.bool_) for _ in range(49)]
        result = _object_motion_metrics(blank, blank, (0, 1))
        self.assertFalse(result["mover_detected"])
        self.assertEqual(result["foreground_f1"], 0.0)
        self.assertFalse(result["form_success"])

    def test_foreground_overlap_is_translation_invariant(self) -> None:
        first = np.zeros((32, 32), dtype=np.bool_)
        first[12, 13] = True
        first[13, 14] = True
        first[14, 12:15] = True
        shifted = np.roll(np.roll(first, 4, axis=0), -3, axis=1)
        score = _foreground_overlap(first, shifted)
        self.assertEqual(score["foreground_f1"], 1.0)
        self.assertEqual(score["foreground_iou"], 1.0)

    def test_real_glider_is_detected_as_an_object(self) -> None:
        state = np.zeros((32, 32), dtype=np.bool_)
        state[12, 13] = True
        state[13, 14] = True
        state[14, 12:15] = True
        history = wc._simulate_history(state, parse_life_rule("B3/S23"), 48)
        detection = wc._detect_mover(history)
        self.assertIsNotNone(detection)
        assert detection is not None
        result = _object_motion_metrics(
            history, history, detection["displacement_yx"]
        )
        self.assertTrue(result["mover_detected"])
        self.assertEqual(result["foreground_f1"], 1.0)
        self.assertTrue(result["correct_direction"])

    def test_binary_codebook_contains_only_observed_medoids(self) -> None:
        values = np.asarray(
            [
                [1, 1, -1, -1],
                [1, -1, -1, -1],
                [-1, -1, 1, 1],
                [-1, -1, 1, -1],
            ],
            dtype=np.float32,
        )
        medoids, labels = _binary_medoid_codebook(values, 2, 7)
        observed = {tuple(row.tolist()) for row in values}
        self.assertTrue(all(tuple(row.tolist()) in observed for row in medoids))
        self.assertEqual(labels.shape, (4,))


class CausalAttractorCliTests(unittest.TestCase):
    def test_cli_accepts_detached_stage6n(self) -> None:
        args = build_parser().parse_args(
            [
                "ca-motif-lineage",
                "--stage",
                "causal-attractor",
                "--profile",
                "smoke",
                "--output",
                "results/test-stage6n",
                "--stage6m-root",
                str(DEFAULT_STAGE6M_ROOT),
                "--workers",
                "4",
                "--detach",
            ]
        )
        self.assertEqual(args.stage, "causal-attractor")
        self.assertEqual(args.stage6m_root, DEFAULT_STAGE6M_ROOT)
        self.assertEqual(args.workers, 4)
        self.assertTrue(args.detach)


if __name__ == "__main__":
    unittest.main()
