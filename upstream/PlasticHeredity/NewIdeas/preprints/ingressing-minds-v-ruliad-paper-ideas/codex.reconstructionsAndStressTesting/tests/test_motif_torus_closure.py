from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import numpy as np

from plastic_ca.cli import build_parser
from plastic_ca import motif_torus_closure as tq
from plastic_ca import motif_writer_closure as wc


class TorusClosureIntegrityTests(unittest.TestCase):
    def test_frozen_stage6p_parent_and_final_reserve(self) -> None:
        result = tq._parent_integrity()
        self.assertTrue(result["stage_gate"])
        self.assertEqual(result["parent_design_digest"], tq.PARENT_STAGE6P_DIGEST)
        self.assertTrue(result["procedural_trajectories_sealed"])
        self.assertEqual(result["final_pair_count"], 62)
        self.assertEqual(result["final_audit_trajectory_state"], "untouched")

    def test_caps_precede_output_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "stage6q"
            with self.assertRaises(ValueError):
                tq.run_motif_torus_closure(root, profile_name="smoke", workers=5)
            self.assertFalse(root.exists())
            with self.assertRaises(ValueError):
                tq.run_motif_torus_closure(
                    root, profile_name="smoke", max_hours=8.01
                )
            self.assertFalse(root.exists())


class TorusClosureObserverTests(unittest.TestCase):
    def _history(self) -> tuple[list[np.ndarray], tuple[int, int]]:
        bank = tq._load_json(
            tq.DEFAULT_STAGE6P_ROOT / "stage6p/MOTION_VALIDATION_BANK.json"
        )
        pair = bank["pairs"][0]
        initial = wc._unpack_state_hex(pair["forward"]["initial_hex"], (32, 32))
        history = wc._simulate_history(initial, int(pair["rule"]), 48)
        return history, tuple(pair["forward"]["displacement_yx"])

    def test_torus_observer_sees_exact_seam_translation(self) -> None:
        history, displacement = self._history()
        signature = tq._torus_translation_signature(history[16])
        self.assertIsNotNone(signature)
        assert signature is not None
        shift = (-signature[1][0], -signature[1][1])
        seam = [np.roll(state, shift, axis=(0, 1)) for state in history]
        self.assertIsNotNone(wc._detect_mover(history))
        self.assertIsNone(wc._detect_mover(seam))
        detected = tq._detect_mover_torus(seam)
        self.assertIsNotNone(detected)
        assert detected is not None
        self.assertEqual(tuple(detected["displacement_yx"]), displacement)

    def test_torus_signature_is_translation_invariant(self) -> None:
        state = np.zeros((32, 32), dtype=np.bool_)
        state[np.ix_((31, 0, 1), (30, 31, 0))] = True
        shifted = np.roll(state, (9, -11), axis=(0, 1))
        left = tq._torus_translation_signature(state)
        right = tq._torus_translation_signature(shifted)
        self.assertIsNotNone(left)
        self.assertIsNotNone(right)
        assert left is not None and right is not None
        self.assertEqual(left[0], right[0])

    def test_observer_audit_confirms_registered_confound(self) -> None:
        audit = tq._run_observer_audit(tq.DEFAULT_STAGE6P_ROOT)
        self.assertTrue(audit["stage_gate"])
        self.assertTrue(audit["legacy_observer_seam_exclusion_confirmed"])
        self.assertTrue(audit["life_update_bitwise_translation_equivariant"])


class TorusClosureCarrierTests(unittest.TestCase):
    def test_paired_summary_indexes_each_lineages_actual_placement(self) -> None:
        def lineage(placement: str) -> dict[str, object]:
            return {
                "pair_id": "pair-a",
                "direction": "forward",
                "condition": "original_seed",
                "placement": placement,
                "noise_name": "standard",
                "generations": [
                    {
                        "decoded_shape_code": 2,
                        "decoded_orientation": 3,
                        "outgoing_writer_shape_code": 1,
                        "outgoing_writer_orientation": 3,
                        "aligned_history_sha256": "same",
                    }
                ],
            }

        rows = [
            {
                "candidate_id": "candidate-a",
                "lineages": [lineage("center"), lineage("translation")],
            }
        ]
        summary = tq._paired_placement_summary(
            rows, "candidate-a", "translation", "standard", 1
        )
        self.assertEqual(summary["count"], 1)
        self.assertEqual(summary["decoded_code_agreement"], 1.0)
        self.assertEqual(summary["outgoing_code_agreement"], 1.0)
        self.assertEqual(summary["aligned_bitwise_agreement"], 1.0)

    def test_extended_hamming_corrects_every_single_bit(self) -> None:
        for value in range(16):
            data = [(value >> bit) & 1 for bit in range(4)]
            encoded = tq._hamming84_encode(data)
            for bit in range(8):
                damaged = encoded.copy()
                damaged[bit] ^= np.uint8(1)
                decoded, diagnostics = tq._hamming84_decode(damaged)
                self.assertEqual(decoded.tolist(), data)
                self.assertEqual(diagnostics["corrected_bit"], bit)

    def test_extended_hamming_flags_double_error(self) -> None:
        damaged = tq._hamming84_encode((1, 0, 1, 1))
        damaged[1] ^= np.uint8(1)
        damaged[4] ^= np.uint8(1)
        _, diagnostics = tq._hamming84_decode(damaged)
        self.assertTrue(diagnostics["uncorrectable_double_error"])

    def test_common_noise_and_exact_spatial_counterfactual(self) -> None:
        bank = tq._load_json(
            tq.DEFAULT_STAGE6P_ROOT / "stage6p/MOTION_VALIDATION_BANK.json"
        )
        fitted = tq._load_json(
            tq.DEFAULT_STAGE6P_ROOT / "stage6p/motion-fit/MODELS.json"
        )
        candidate = next(
            row
            for row in fitted["candidates"]
            if row["candidate_id"] == "stage6p-slow-latch-r90-e32"
        )
        candidate = dict(candidate)
        candidate["candidate_id"] = "test-stage6q-parent-latch"
        center = tq._spatial_lineage(
            candidate,
            bank["pairs"][0],
            "forward",
            "original_seed",
            "center",
            "standard",
            generations=1,
        )["generations"][0]
        seam = tq._spatial_lineage(
            candidate,
            bank["pairs"][0],
            "forward",
            "original_seed",
            "seam",
            "standard",
            generations=1,
        )["generations"][0]
        self.assertEqual(center["copy_seed"], seam["copy_seed"])
        self.assertEqual(center["copied_payload"], seam["copied_payload"])
        self.assertEqual(
            center["aligned_history_sha256"], seam["aligned_history_sha256"]
        )


class TorusClosureCliTests(unittest.TestCase):
    def test_cli_accepts_detached_stage6q(self) -> None:
        args = build_parser().parse_args(
            [
                "ca-motif-lineage",
                "--stage",
                "torus-closure",
                "--profile",
                "smoke",
                "--output",
                "results/test-stage6q",
                "--stage6p-root",
                str(tq.DEFAULT_STAGE6P_ROOT),
                "--workers",
                "4",
                "--detach",
            ]
        )
        self.assertEqual(args.stage, "torus-closure")
        self.assertEqual(args.stage6p_root, tq.DEFAULT_STAGE6P_ROOT)
        self.assertEqual(args.workers, 4)
        self.assertTrue(args.detach)

    def test_contract_registers_paired_torus_gate(self) -> None:
        contract = tq.TorusClosureContract().to_dict()
        self.assertEqual(contract["observer"], "largest-empty-gap-torus-signature")
        self.assertEqual(
            contract["noise_pairing"], "common-random-numbers-across-placement"
        )
        self.assertEqual(contract["motion_payload_maximum_bits"], 8)


if __name__ == "__main__":
    unittest.main()
