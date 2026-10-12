from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import numpy as np

from plastic_ca import motif_causal_attractor as cn
from plastic_ca import motif_inverse_distillation as il
from plastic_ca import motif_writer_closure as wc
from plastic_ca.cli import build_parser
from plastic_ca.life_family import parse_life_rule
from plastic_ca.motif_counterfactual_carrier import (
    DEFAULT_STAGE6N_ROOT,
    CounterfactualCarrierContract,
    _counterfactual_motion_metrics,
    _d4_foreground_overlap,
    _motion_oracle_gate,
    _parent_integrity,
    run_motif_counterfactual_carrier,
)


class CounterfactualCarrierIntegrityTests(unittest.TestCase):
    def test_frozen_stage6n_parent_and_reserve(self) -> None:
        result = _parent_integrity()
        self.assertTrue(result["stage_gate"])
        self.assertTrue(result["procedural_trajectories_sealed"])
        self.assertEqual(result["final_pair_count"], 62)
        self.assertEqual(result["final_audit_trajectory_state"], "untouched")

    def test_caps_precede_output_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "stage6o"
            with self.assertRaises(ValueError):
                run_motif_counterfactual_carrier(
                    root, profile_name="smoke", workers=5
                )
            self.assertFalse(root.exists())
            with self.assertRaises(ValueError):
                run_motif_counterfactual_carrier(
                    root, profile_name="smoke", max_hours=8.01
                )
            self.assertFalse(root.exists())


class CounterfactualCarrierMetricTests(unittest.TestCase):
    def test_d4_form_overlap_accepts_reflection(self) -> None:
        target = np.zeros((32, 32), dtype=np.bool_)
        target[13, 14] = True
        target[14, 14:17] = True
        target[15, 16] = True
        reflected = il._d4_blocks(target.astype(np.float32), 4) > 0
        plain = cn._foreground_overlap(reflected, target)
        aligned = _d4_foreground_overlap(reflected, target)
        self.assertLess(plain["foreground_f1"], 1.0)
        self.assertEqual(aligned["foreground_f1"], 1.0)

    def test_blank_d4_form_does_not_create_success(self) -> None:
        blank = np.zeros((32, 32), dtype=np.bool_)
        result = _d4_foreground_overlap(blank, blank)
        self.assertEqual(result["foreground_f1"], 0.0)

    def test_reversed_glider_preserves_form_but_has_negative_original_sign(self) -> None:
        state = np.zeros((32, 32), dtype=np.bool_)
        state[12, 13] = True
        state[13, 14] = True
        state[14, 12:15] = True
        rule = parse_life_rule("B3/S23")
        target = wc._simulate_history(state, rule, 48)
        target_detection = wc._detect_mover(target)
        self.assertIsNotNone(target_detection)
        assert target_detection is not None
        original = tuple(target_detection["displacement_yx"])
        reversed_history = None
        reversed_direction = None
        for symmetry in range(8):
            transformed = il._d4_blocks(state.astype(np.float32), symmetry) > 0
            history = wc._simulate_history(transformed, rule, 48)
            detection = wc._detect_mover(history)
            if detection is None:
                continue
            displacement = tuple(detection["displacement_yx"])
            if displacement == (-original[0], -original[1]):
                reversed_history = history
                reversed_direction = displacement
                break
        self.assertIsNotNone(reversed_history)
        assert reversed_history is not None and reversed_direction is not None
        result = _counterfactual_motion_metrics(
            reversed_history, target, reversed_direction, original
        )
        self.assertEqual(result["foreground_f1"], 1.0)
        self.assertTrue(result["correct_instruction_direction"])
        self.assertLess(result["signed_original_direction_similarity"], -0.5)


class CounterfactualCarrierGateTests(unittest.TestCase):
    @staticmethod
    def _recovery(
        *,
        form: float = 0.90,
        direction: float = 0.90,
        signed: float = 0.85,
        detected: float = 1.0,
    ) -> dict[str, float]:
        return {
            "mover_detection_fraction": detected,
            "form_success_fraction": form,
            "instruction_direction_fraction": direction,
            "joint_success_fraction": min(form, direction),
            "foreground_f1_mean": form,
            "instruction_direction_similarity_mean": direction,
            "signed_original_direction_similarity_mean": signed,
        }

    def test_both_matching_and_opposite_command_success_can_pass(self) -> None:
        summaries = {
            "intact_generation1": self._recovery(),
            "intact_generation4": self._recovery(),
            "zero_generation4": self._recovery(
                form=0.0, direction=0.0, signed=0.0, detected=0.0
            ),
            "opposite_polarity_generation4": self._recovery(signed=-0.85),
            "matching_rescue_generation3": self._recovery(signed=0.85),
            "opposite_rescue_generation3": self._recovery(signed=-0.85),
        }
        gate, diagnostics = _motion_oracle_gate(
            summaries, 8, CounterfactualCarrierContract()
        )
        self.assertTrue(gate)
        self.assertGreaterEqual(
            diagnostics["signed_rescue_direction_contrast"], 0.40
        )

    def test_reflected_command_must_still_preserve_form(self) -> None:
        summaries = {
            "intact_generation1": self._recovery(),
            "intact_generation4": self._recovery(),
            "zero_generation4": self._recovery(
                form=0.0, direction=0.0, signed=0.0, detected=0.0
            ),
            "opposite_polarity_generation4": self._recovery(
                form=0.65, signed=-0.85
            ),
            "matching_rescue_generation3": self._recovery(signed=0.85),
            "opposite_rescue_generation3": self._recovery(signed=-0.85),
        }
        gate, _ = _motion_oracle_gate(
            summaries, 8, CounterfactualCarrierContract()
        )
        self.assertFalse(gate)


class CounterfactualCarrierCliTests(unittest.TestCase):
    def test_cli_accepts_detached_stage6o(self) -> None:
        args = build_parser().parse_args(
            [
                "ca-motif-lineage",
                "--stage",
                "counterfactual-carrier",
                "--profile",
                "smoke",
                "--output",
                "results/test-stage6o",
                "--stage6n-root",
                str(DEFAULT_STAGE6N_ROOT),
                "--workers",
                "4",
                "--detach",
            ]
        )
        self.assertEqual(args.stage, "counterfactual-carrier")
        self.assertEqual(args.stage6n_root, DEFAULT_STAGE6N_ROOT)
        self.assertEqual(args.workers, 4)
        self.assertTrue(args.detach)


if __name__ == "__main__":
    unittest.main()
