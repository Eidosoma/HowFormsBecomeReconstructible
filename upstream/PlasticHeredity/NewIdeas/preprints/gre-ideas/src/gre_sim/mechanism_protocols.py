"""Frozen executable protocols for the staged exploratory mechanism campaign."""

from __future__ import annotations

from .mechanism_config import MechanismCondition, MechanismSpec, SourceSetSpec


STAGE_A_PROTOCOL_DIGEST = (
    "eb0e201ea26df783852c3a134b2b8aace7e94c79a0c5853c5e100942af0de9d0"
)


def phase_1_spec() -> MechanismSpec:
    """Stage A paired noise, carryover, endpoint, and donor decomposition."""

    return MechanismSpec(
        cohort_id="wagner-mechanism-v1-phase-1",
        phase="stage-a-paired-mechanism",
        master_seed=(
            "76aee3d6c8d2cd85b2d31d608cd1aa75a183fd9844c413812f17ed5c5176438e"
        ),
        parent_protocol_digest=STAGE_A_PROTOCOL_DIGEST,
        source_sets=(
            SourceSetSpec(
                "stage_a_boolean", "boolean", 6, 32, "parent", "boolean"
            ),
            SourceSetSpec(
                "stage_a_wagner", "wagner", 10, 32, "parent", "wagner"
            ),
        ),
        conditions=(
            MechanismCondition(
                "boolean-main",
                "stage_a_boolean",
                "boolean_sync",
                ("natural", "acute_mismatch", "target_aligned_own_anchor"),
                (0.0, 0.25, 0.5, 0.75, 1.0),
                ("self", "donor_shuffled"),
                (0.0,),
                16,
            ),
            MechanismCondition(
                "wagner-main",
                "stage_a_wagner",
                "wagner_sequential",
                ("natural", "acute_mismatch", "target_aligned_own_anchor"),
                (0.0, 0.25, 0.5, 0.75, 1.0),
                ("self", "donor_shuffled"),
                (0.0, 0.01, 0.03, 0.1),
                16,
            ),
            MechanismCondition(
                "wagner-compiled-main",
                "stage_a_wagner",
                "wagner_compiled",
                ("natural", "acute_mismatch", "target_aligned_own_anchor"),
                (0.0, 0.25, 0.5, 0.75, 1.0),
                ("self", "donor_shuffled"),
                (0.0,),
                16,
            ),
            MechanismCondition(
                "boolean-controls",
                "stage_a_boolean",
                "boolean_sync",
                ("joint_isomorphic", "single_attractor"),
                (0.0, 1.0),
                ("self", "donor_shuffled"),
                (0.0,),
                16,
            ),
            MechanismCondition(
                "wagner-controls",
                "stage_a_wagner",
                "wagner_sequential",
                ("joint_isomorphic", "single_attractor"),
                (0.0, 1.0),
                ("self", "donor_shuffled"),
                (0.0, 0.1),
                16,
            ),
            MechanismCondition(
                "wagner-compiled-controls",
                "stage_a_wagner",
                "wagner_compiled",
                ("joint_isomorphic", "single_attractor"),
                (0.0, 1.0),
                ("self", "donor_shuffled"),
                (0.0,),
                16,
            ),
            MechanismCondition(
                "wagner-matched-donors",
                "stage_a_wagner",
                "wagner_sequential",
                ("natural", "acute_mismatch", "target_aligned_own_anchor"),
                (1.0,),
                ("destination_matched_donor", "exact_state_donor"),
                (0.0, 0.1),
                64,
            ),
        ),
    )


def phase_2_spec() -> MechanismSpec:
    """Conditional N-by-architecture causal factorial."""

    source_sets = tuple(
        SourceSetSpec(
            f"{engine}_n{genes}",
            engine,
            genes,
            32,
            "sampled",
            require_both_update_modes=True,
        )
        for genes in (6, 10)
        for engine in ("boolean", "wagner")
    )
    conditions: list[MechanismCondition] = []
    arms = ("natural", "acute_mismatch", "target_aligned_own_anchor")
    carryover = (0.0, 0.5, 1.0)
    inheritance = ("self", "donor_shuffled")
    for genes in (6, 10):
        for update in ("sync", "sequential"):
            variant = "boolean_sync" if update == "sync" else "boolean_sequential"
            conditions.append(
                MechanismCondition(
                    f"boolean-n{genes}-{update}",
                    f"boolean_n{genes}",
                    variant,
                    arms,
                    carryover,
                    inheritance,
                    (0.0,),
                    16,
                )
            )
        for update in ("sequential", "synchronous"):
            conditions.append(
                MechanismCondition(
                    f"wagner-n{genes}-{update}",
                    f"wagner_n{genes}",
                    f"wagner_{update}",
                    arms,
                    carryover,
                    inheritance,
                    (0.0, 0.1),
                    16,
                )
            )
            conditions.append(
                MechanismCondition(
                    f"wagner-n{genes}-{update}-compiled",
                    f"wagner_n{genes}",
                    "wagner_compiled",
                    arms,
                    carryover,
                    inheritance,
                    (0.0,),
                    16,
                    compiled_update_mode=update,
                )
            )
    return MechanismSpec(
        cohort_id="wagner-mechanism-v1-phase-2",
        phase="matched-architecture-factorial",
        master_seed=(
            "308a6a62e5adfad8acaaa5410620bd92a84b799689a623e09fee8435747c9e9b"
        ),
        source_sets=source_sets,
        conditions=tuple(conditions),
    )


def phase_3_spec() -> MechanismSpec:
    """Fresh-cohort exploratory replication of native engines and noise effect."""

    return MechanismSpec(
        cohort_id="wagner-mechanism-v1-phase-3",
        phase="fresh-mechanism-replication",
        master_seed=(
            "28d12bf0af5bfff1609b60b2505549d1c2b3ab805ec52749ff7e59f86ec8fbe5"
        ),
        source_sets=(
            SourceSetSpec("fresh_boolean_n6", "boolean", 6, 32),
            SourceSetSpec("fresh_wagner_n10", "wagner", 10, 32),
        ),
        conditions=(
            MechanismCondition(
                "fresh-boolean-main",
                "fresh_boolean_n6",
                "boolean_sync",
                ("natural", "acute_mismatch", "target_aligned_own_anchor"),
                (0.0, 0.5, 1.0),
                ("self", "donor_shuffled"),
                (0.0,),
                64,
            ),
            MechanismCondition(
                "fresh-wagner-main",
                "fresh_wagner_n10",
                "wagner_sequential",
                ("natural", "acute_mismatch", "target_aligned_own_anchor"),
                (0.0, 0.5, 1.0),
                ("self", "donor_shuffled"),
                (0.0, 0.1),
                64,
            ),
            MechanismCondition(
                "fresh-boolean-controls",
                "fresh_boolean_n6",
                "boolean_sync",
                ("joint_isomorphic", "single_attractor"),
                (0.0, 1.0),
                ("self", "donor_shuffled"),
                (0.0,),
                16,
            ),
            MechanismCondition(
                "fresh-wagner-controls",
                "fresh_wagner_n10",
                "wagner_sequential",
                ("joint_isomorphic", "single_attractor"),
                (0.0, 1.0),
                ("self", "donor_shuffled"),
                (0.0, 0.1),
                16,
            ),
        ),
    )
