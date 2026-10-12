from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import numpy as np

from plastic_ca import motif_phenotype_bridge as pb
from plastic_ca.motif_writeback_ladder import (
    DEFAULT_STAGE6E_ROOT,
    WritebackLadderContract,
    _integrity_audit,
    _oracle_summary,
    _proposal_grid,
    run_motif_writeback_ladder,
)
from tests.test_motif_phenotype_bridge import frontends
from tests.test_motif_phenotype_bridge import ROOTS


class WritebackLadderIntegrityTests(unittest.TestCase):
    def test_invalidated_stage6e_founder_gate_reproduces(self) -> None:
        result = _integrity_audit(DEFAULT_STAGE6E_ROOT)
        self.assertTrue(result["stage_gate"])
        self.assertEqual(result["generation4_founder_write_true_count"], 0)
        self.assertEqual(
            result["generation5_intact_sham_identical_count"],
            result["checkpoint_count"],
        )
        self.assertEqual(result["replacement_status"], "INVALID_ACQUISITION_GATE")

    def test_worker_and_wall_caps_fail_before_campaign_preparation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                run_motif_writeback_ladder(
                    Path(directory), profile_name="smoke", workers=5
                )
            with self.assertRaises(ValueError):
                run_motif_writeback_ladder(
                    Path(directory), profile_name="smoke", max_hours=8.01
                )


class WritebackLadderCandidateTests(unittest.TestCase):
    @staticmethod
    def _trace_row(source: int) -> dict[str, object]:
        samples = 2
        environment = np.ones((samples, 4, 4), dtype=np.float32)
        patches = {
            str(sweep): (
                environment if sweep % 2 == 0 else -environment
            ).tolist()
            for sweep in range(1, 65)
        }
        trace = {"patches_all": patches, "environment": environment.tolist()}
        return {
            "candidate_id": f"source-q4-d{source:02d}",
            "pair_id": f"pair-{source}",
            "conditions": {
                "intact": {"bridge_trace": {"5": trace}},
                "sham": {
                    "bridge_trace": {
                        "5": {
                            "patches_all": {
                                str(sweep): np.zeros((samples, 4, 4)).tolist()
                                for sweep in range(1, 65)
                            },
                            "environment": environment.tolist(),
                        }
                    }
                },
            },
        }

    def test_proposal_grid_is_bounded_diverse_and_sealed(self) -> None:
        rows = [self._trace_row(40), self._trace_row(48)]
        selected_frontends = frontends()
        selected_frontends[0]["read_sweeps"] = 40
        selected_frontends[1]["read_sweeps"] = 48
        observability = {
            "strict_branch_eligible": True,
            "best_carrier_supported": {
                "intact_minus_sham": {"mean": 0.2, "ci": [0.1, 0.3]}
            },
        }
        proposals, selected = _proposal_grid(
            rows,
            selected_frontends,
            observability,
            pb.PHENOTYPE_BRIDGE_PROFILES["smoke"],
            WritebackLadderContract(),
        )
        self.assertLessEqual(len(proposals), 132)
        self.assertEqual(len(selected), 12)
        self.assertEqual(len({row["candidate_id"] for row in selected}), 12)
        self.assertEqual(sum(row["claim_tier"] == "strict" for row in selected), 4)
        self.assertEqual(sum(row["writer_source"] == "visible" for row in selected), 8)
        self.assertEqual(sum(row["writer_source"] == "somatic" for row in selected), 4)

    def test_smoke_oracle_uses_explicit_sample_fallback(self) -> None:
        targets = (
            np.asarray([1.0, -1.0]),
            np.asarray([-1.0, 1.0]),
            np.asarray([1.0, -1.0]),
            np.asarray([-1.0, 1.0]),
        )
        entries = {
            "intact": [("one-pair", target.copy(), target) for target in targets],
            "sham": [("one-pair", np.zeros(2), target) for target in targets],
        }
        summary = _oracle_summary(
            entries,
            WritebackLadderContract(),
            "smoke-fallback-test",
            100,
        )
        self.assertEqual(summary["fold_mode"], "smoke-leave-one-sample-out")
        self.assertEqual(summary["pair_count"], 1)
        self.assertTrue(np.isfinite(summary["intact_accuracy"]["mean"]))

    def test_registered_field_readers_cannot_enter_strict_tier(self) -> None:
        frontend = frontends()[0]
        broad = {
            "candidate_id": "broad-field-reader",
            "claim_tier": "broad",
            "writer_source": "somatic",
            "writer_input_contract": "field-readable",
            "somatic_architecture": "local-reservoir",
            "somatic_channels": 4,
            "somatic_retention": 0.95,
            "somatic_bias": 0.8,
            "frontend": frontend,
        }
        models, _ = pb.build_writeback_candidates([broad])
        self.assertEqual(models[0]["writer_input_contract"], "field-readable")
        strict = broad | {"candidate_id": "illegal", "claim_tier": "strict"}
        with self.assertRaises(ValueError):
            pb.build_writeback_candidates([strict])

    def test_multichannel_field_is_zero_at_birth_and_exit(self) -> None:
        spec = {
            "candidate_id": "multichannel-field-reader",
            "claim_tier": "broad",
            "writer_source": "somatic",
            "writer_input_contract": "field-readable",
            "writer_feature": "temporal-mix",
            "somatic_architecture": "local-reservoir",
            "somatic_channels": 4,
            "somatic_retention": 0.95,
            "somatic_bias": 0.8,
            "somatic_readout": "mean",
            "somatic_acquisition_window": 8,
            "somatic_support_sweeps": 8,
            "frontend": frontends()[0],
        }
        with tempfile.TemporaryDirectory() as directory:
            frozen, cohorts, _, contract, writer_contract, templates, _ = pb._prepare_stage6e(
                Path(directory), "smoke", auto_final_audit=True, **ROOTS
            )
            candidate = pb.build_writeback_candidates([spec])[0][0]
            result, _ = pb.simulate_phenotype_lineage(
                pair=cohorts["bridge"][0],
                configuration=frozen["stage4"]["configuration"],
                candidate=candidate,
                condition="intact",
                replicates=1,
                generations=5,
                reference=frozen["stage4"]["reference"],
                writer_contract=writer_contract,
                contract=contract,
                environmental_template=np.asarray(templates[0]["bits"], dtype=np.bool_),
            )
            self.assertTrue(result["somatic_zero_at_every_birth"])
            self.assertTrue(result["somatic_zero_at_every_exit"])
            self.assertTrue(result["writer_history"]["4"]["fresh_carrier_written"])
            self.assertFalse(result["writer_history"]["4"]["somatic_exposed_to_writer"])
            self.assertTrue(result["writer_history"]["5"]["somatic_exposed_to_writer"])


if __name__ == "__main__":
    unittest.main()
