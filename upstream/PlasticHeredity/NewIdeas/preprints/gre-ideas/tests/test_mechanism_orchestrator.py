from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from gre_sim.artifacts import read_json, sha256_file, verify_checksums
from gre_sim.config import StudySpec
from gre_sim.mechanism_config import MechanismCondition, MechanismSpec, SourceSetSpec
from gre_sim.mechanism_orchestrator import run_full_mechanism_campaign
from gre_sim.study import run_study, verify_run


def _base_spec(
    cohort: str,
    source_sets: tuple[SourceSetSpec, ...],
    conditions: tuple[MechanismCondition, ...],
    parent_digest: str | None = None,
) -> MechanismSpec:
    return MechanismSpec(
        cohort_id=cohort,
        phase="orchestrator-test",
        master_seed=f"{cohort}-0123456789abcdef0123456789abcdef",
        source_sets=source_sets,
        conditions=conditions,
        launch_states_per_rulebook=2,
        horizon=12,
        stable_destination_run=2,
        strict_run=2,
        bootstrap_repetitions=8,
        parent_protocol_digest=parent_digest,
    )


def test_full_orchestrator_runs_all_stages_and_resumes_without_mutation(
    tmp_path: Path, monkeypatch
) -> None:
    parent_spec = replace(
        StudySpec.quick_v2(), cohorts=("sampled",), launch_states_per_rulebook=2
    )
    parent = tmp_path / "parent"
    run_study(parent_spec, parent, workers=1)
    parent_digest = verify_run(parent)["protocol_digest"]

    parent_wagner = SourceSetSpec(
        "parent_wagner", "wagner", 10, 1, "parent", "wagner"
    )
    common = {
        "source_set": parent_wagner.name,
        "arms": ("natural", "acute_mismatch"),
        "carryover_values": (0.0, 1.0),
        "inheritance_modes": ("self", "donor_shuffled"),
        "gamma_variances": (0.0,),
        "futures_per_cell": 4,
    }
    phase_1 = _base_spec(
        "orchestrator-phase-1",
        (parent_wagner,),
        (
            MechanismCondition("wagner-main", variant="wagner_sequential", **common),
            MechanismCondition(
                "wagner-compiled-main", variant="wagner_compiled", **common
            ),
        ),
        parent_digest,
    )

    sampled_wagner = SourceSetSpec("sampled_wagner", "wagner", 6, 1)
    phase_2_common = {
        **common,
        "source_set": sampled_wagner.name,
        "arms": ("natural", "acute_mismatch", "target_aligned_own_anchor"),
    }
    phase_2 = _base_spec(
        "orchestrator-phase-2",
        (sampled_wagner,),
        (
            MechanismCondition(
                "fixture-wagner", variant="wagner_sequential", **phase_2_common
            ),
            MechanismCondition(
                "fixture-wagner-compiled",
                variant="wagner_compiled",
                **phase_2_common,
            ),
        ),
    )

    boolean = SourceSetSpec("fresh_boolean", "boolean", 6, 1)
    wagner = SourceSetSpec("fresh_wagner", "wagner", 6, 1)
    phase_3_conditions = []
    for name, source, variant, variances in (
        ("fresh-boolean", boolean, "boolean_sync", (0.0,)),
        ("fresh-wagner", wagner, "wagner_sequential", (0.0,)),
    ):
        phase_3_conditions.extend(
            (
                MechanismCondition(
                    f"{name}-main",
                    source.name,
                    variant,
                    ("natural", "acute_mismatch", "target_aligned_own_anchor"),
                    (0.0, 1.0),
                    ("self", "donor_shuffled"),
                    variances,
                    4,
                ),
                MechanismCondition(
                    f"{name}-controls",
                    source.name,
                    variant,
                    ("joint_isomorphic", "single_attractor"),
                    (0.0, 1.0),
                    ("self", "donor_shuffled"),
                    variances,
                    4,
                ),
            )
        )
    phase_3 = _base_spec(
        "orchestrator-phase-3",
        (boolean, wagner),
        tuple(phase_3_conditions),
    )

    monkeypatch.setattr(
        "gre_sim.mechanism_orchestrator.phase_1_spec", lambda: phase_1
    )
    monkeypatch.setattr(
        "gre_sim.mechanism_orchestrator.phase_2_spec", lambda: phase_2
    )
    monkeypatch.setattr(
        "gre_sim.mechanism_orchestrator.phase_3_spec", lambda: phase_3
    )
    destination = tmp_path / "campaign"
    run_full_mechanism_campaign(parent, destination, workers=1)

    manifest = read_json(destination / "campaign-manifest.json")
    assert manifest["completed"]
    assert set(manifest["phases"]) == {"phase_1", "phase_2", "phase_3"}
    assert manifest["phases"]["phase_2"]["compiled_bridge"]["pathwise_equal"]
    verify_checksums(destination)
    digest = sha256_file(destination / "SHA256SUMS")

    run_full_mechanism_campaign(parent, destination, workers=1)
    assert sha256_file(destination / "SHA256SUMS") == digest
