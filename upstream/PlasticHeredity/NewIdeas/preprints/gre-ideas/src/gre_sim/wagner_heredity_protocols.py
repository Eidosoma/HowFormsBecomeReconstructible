"""Frozen staged protocols for the Wagner plastic-heredity campaign."""

from __future__ import annotations

from dataclasses import replace

from .plastic_memory_config import MarkSetting
from .wagner_heredity_config import (
    HeredityCondition,
    HeredityWriterSpec,
    WagnerHereditySpec,
)
from .wagner_rescue_config import CueIntervention


DISCOVERY_SEED = "9cb3b432674db4ccb8cb8a43ce683978696b2fbea00c6b236ba0bfca050a9702"
CONFIRMATION_SEED = "132fda69a35139d2cc4a0a9017d937a0776f4454da88f3d70456f158af679644"
MARK_DISCOVERY_SEED = "b048a25fe89de30c87ccbbedddd5af5457b70ba9e67fb6f0f15ed5a5dd92ad3f"
MARK_CONFIRMATION_SEED = "0d794f71b88b43e3ba429ace751b4354d32f13a364e896319e10df877f642dbf"
QUICK_SEED = "1c249f27ececa6fe6d97f7549e80752bb66b52661cdaacf6758b0d48bfcba1a8"

NO_MARK = MarkSetting("none", 0, 0.0)
MARK_GRID = tuple(
    MarkSetting(f"half-{half_life}.mu-{coupling:g}", half_life, coupling)
    for half_life in (1, 4, 8, 16)
    for coupling in (0.25, 0.50)
)


def _hard_writer(
    theta: float,
    *,
    name: str | None = None,
    tier: str = "boundary",
    primary: bool = False,
) -> HeredityWriterSpec:
    label = f"{theta:g}"
    writer_name = name or f"hard-theta-{label}"
    return HeredityWriterSpec(
        writer_name,
        tier,
        CueIntervention("persistent_hard", 1.0, 1),
        theta,
        primary,
        writer_name,
    )


def _soft_writer(
    theta: float,
    *,
    name: str | None = None,
    tier: str = "boundary",
    primary: bool = False,
) -> HeredityWriterSpec:
    label = f"{theta:g}"
    return HeredityWriterSpec(
        name or f"soft-theta-{label}",
        tier,
        CueIntervention("target_field", 1.0, 1, 0.5),
        theta,
        primary,
        f"hard-theta-{label}",
    )


def discovery_writers() -> tuple[HeredityWriterSpec, ...]:
    anchors = (
        _hard_writer(0.0, tier="hard", primary=True),
        _soft_writer(0.0, tier="soft", primary=True),
        _hard_writer(0.01, tier="noisy", primary=True),
    )
    extras: list[HeredityWriterSpec] = []
    for theta in (0.0025, 0.005, 0.03, 0.10):
        extras.extend((_hard_writer(theta), _soft_writer(theta)))
    extras.append(_soft_writer(0.01))
    return (*anchors, *extras)


def discovery_spec(parent_candidate_digest: str) -> WagnerHereditySpec:
    writers = discovery_writers()
    conditions: list[HeredityCondition] = []
    for writer in writers:
        if writer.primary:
            conditions.extend(
                (
                    HeredityCondition(
                        f"{writer.name}-state-core",
                        writer.name,
                        (NO_MARK.name,),
                        (
                            "self_continuation",
                            "state_transplant",
                            "reset_both",
                            "destination_matched_donor",
                            "descriptor_matched_null",
                            "state_pattern_shuffle",
                        ),
                        (0,),
                        ("neutral_damage",),
                        64,
                    ),
                    HeredityCondition(
                        f"{writer.name}-state-recurrence",
                        writer.name,
                        (NO_MARK.name,),
                        ("state_transplant", "reset_both"),
                        (0,),
                        ("forced_break",),
                        64,
                    ),
                    HeredityCondition(
                        f"{writer.name}-state-persistence",
                        writer.name,
                        (NO_MARK.name,),
                        ("state_transplant", "reset_both", "state_pattern_shuffle"),
                        (1, 2, 4, 8),
                        ("release_only", "neutral_damage", "forced_break"),
                        32,
                    ),
                )
            )
        else:
            conditions.append(
                HeredityCondition(
                    f"{writer.name}-boundary",
                    writer.name,
                    (NO_MARK.name,),
                    ("state_transplant", "reset_both"),
                    (0, 1),
                    ("release_only", "neutral_damage"),
                    32,
                )
            )
    return WagnerHereditySpec(
        "wagner-heredity-v1-discovery",
        "fresh-transfer-discovery",
        DISCOVERY_SEED,
        parent_candidate_digest,
        10,
        96,
        writers,
        (NO_MARK,),
        tuple(conditions),
        exploratory=True,
    )


def _writer_catalog() -> dict[str, HeredityWriterSpec]:
    return {writer.name: writer for writer in discovery_writers()}


def confirmation_spec(
    parent_candidate_digest: str,
    selected_writers: tuple[str, ...],
) -> WagnerHereditySpec:
    catalog = _writer_catalog()
    required = list(selected_writers)
    for name in selected_writers:
        ceiling = catalog[name].ceiling_writer
        if ceiling is not None and ceiling not in required:
            required.append(ceiling)
    writers = tuple(
        replace(catalog[name], primary=name in selected_writers) for name in required
    )
    conditions: list[HeredityCondition] = []
    for writer in writers:
        if not writer.primary:
            conditions.append(
                HeredityCondition(
                    f"{writer.name}-ceiling",
                    writer.name,
                    (NO_MARK.name,),
                    ("state_transplant",),
                    (0,),
                    ("neutral_damage",),
                    128,
                )
            )
            continue
        conditions.extend(
            (
                HeredityCondition(
                    f"{writer.name}-state-primary",
                    writer.name,
                    (NO_MARK.name,),
                    (
                        "self_continuation",
                        "state_transplant",
                        "reset_both",
                        "destination_matched_donor",
                        "descriptor_matched_null",
                        "state_pattern_shuffle",
                    ),
                    (0,),
                    ("neutral_damage",),
                    128,
                ),
                HeredityCondition(
                    f"{writer.name}-state-recurrence",
                    writer.name,
                    (NO_MARK.name,),
                    ("state_transplant", "reset_both"),
                    (0,),
                    ("forced_break",),
                    128,
                ),
                HeredityCondition(
                    f"{writer.name}-state-persistence",
                    writer.name,
                    (NO_MARK.name,),
                    ("state_transplant", "reset_both", "state_pattern_shuffle"),
                    (1, 2, 4, 8),
                    ("release_only", "neutral_damage", "forced_break"),
                    64,
                ),
            )
        )
    return WagnerHereditySpec(
        "wagner-heredity-v1-confirmation",
        "untouched-minimal-heredity-confirmation",
        CONFIRMATION_SEED,
        parent_candidate_digest,
        10,
        240,
        writers,
        (NO_MARK,),
        tuple(conditions),
        exploratory=False,
    )


def weakest_writer(writer_names: tuple[str, ...]) -> str:
    catalog = _writer_catalog()
    tier_rank = {"noisy": 0, "soft": 1, "hard": 2, "boundary": 3}
    return min(
        writer_names,
        key=lambda name: (tier_rank[catalog[name].tier], -catalog[name].gamma_variance, name),
    )


def mark_discovery_spec(
    parent_candidate_digest: str,
    writer_name: str,
) -> WagnerHereditySpec:
    writer = replace(
        _writer_catalog()[writer_name], primary=True, ceiling_writer=writer_name
    )
    return WagnerHereditySpec(
        "wagner-heredity-v1-mark-discovery",
        "slow-mark-causal-discovery",
        MARK_DISCOVERY_SEED,
        parent_candidate_digest,
        10,
        96,
        (writer,),
        (NO_MARK, *MARK_GRID),
        (
            HeredityCondition(
                f"{writer.name}-mark-screen",
                writer.name,
                tuple(mark.name for mark in MARK_GRID),
                ("mark_transplant", "reset_both"),
                (0, 8),
                ("forced_break",),
                64,
            ),
            HeredityCondition(
                f"{writer.name}-mark-mechanism",
                writer.name,
                tuple(mark.name for mark in MARK_GRID),
                (
                    "state_and_mark_transplant",
                    "reset_both",
                    "mark_pattern_shuffle",
                    "write_disabled",
                    "mark_inert",
                    "mark_ablation",
                    "mark_random_ablation",
                    "mark_rescue",
                ),
                (0, 8),
                ("neutral_damage", "forced_break"),
                32,
            ),
        ),
        exploratory=True,
    )


def mark_confirmation_spec(
    parent_candidate_digest: str,
    writer_name: str,
    mark_name: str,
) -> WagnerHereditySpec:
    writer = replace(
        _writer_catalog()[writer_name], primary=True, ceiling_writer=writer_name
    )
    mark = next(value for value in MARK_GRID if value.name == mark_name)
    return WagnerHereditySpec(
        "wagner-heredity-v1-mark-confirmation",
        "untouched-slow-mark-confirmation",
        MARK_CONFIRMATION_SEED,
        parent_candidate_digest,
        10,
        240,
        (writer,),
        (NO_MARK, mark),
        (
            HeredityCondition(
                f"{writer.name}-mark-primary",
                writer.name,
                (mark.name,),
                ("mark_transplant", "reset_both"),
                (0,),
                ("forced_break",),
                128,
            ),
            HeredityCondition(
                f"{writer.name}-mark-persistence",
                writer.name,
                (mark.name,),
                ("mark_transplant", "reset_both"),
                (1, 2, 4, 8),
                ("release_only", "neutral_damage", "forced_break"),
                64,
            ),
            HeredityCondition(
                f"{writer.name}-mark-mechanism",
                writer.name,
                (mark.name,),
                (
                    "state_and_mark_transplant",
                    "mark_pattern_shuffle",
                    "write_disabled",
                    "mark_inert",
                    "mark_ablation",
                    "mark_random_ablation",
                    "mark_rescue",
                ),
                (0, 8),
                ("neutral_damage", "forced_break"),
                64,
            ),
        ),
        exploratory=False,
    )


def quick_spec(parent_candidate_digest: str = "0" * 64) -> WagnerHereditySpec:
    writer = HeredityWriterSpec(
        "hard-quick",
        "fixture",
        CueIntervention("persistent_hard", 1.0, 1),
        0.0,
        True,
        "hard-quick",
    )
    mark = MarkSetting("half-1.mu-0.5", 1, 0.5)
    return WagnerHereditySpec(
        "wagner-heredity-quick",
        "engineering-fixture",
        QUICK_SEED,
        parent_candidate_digest,
        4,
        1,
        (writer,),
        (NO_MARK, mark),
        (
            HeredityCondition(
                "hard-quick-state",
                writer.name,
                (NO_MARK.name,),
                (
                    "self_continuation",
                    "state_transplant",
                    "reset_both",
                    "destination_matched_donor",
                    "descriptor_matched_null",
                    "state_pattern_shuffle",
                ),
                (0, 1),
                ("release_only", "neutral_damage", "forced_break"),
                4,
            ),
            HeredityCondition(
                "hard-quick-mark",
                writer.name,
                (mark.name,),
                (
                    "mark_transplant",
                    "state_and_mark_transplant",
                    "reset_both",
                    "mark_pattern_shuffle",
                    "write_disabled",
                    "mark_inert",
                    "mark_ablation",
                    "mark_random_ablation",
                    "mark_rescue",
                ),
                (0, 1),
                ("forced_break",),
                4,
            ),
        ),
        midpoint_count=1,
        horizon=12,
        stable_run=2,
        strict_run=2,
        minimum_basin_fraction=0.0,
        minimum_form_distance=0.25,
        maximum_source_proposals=100_000,
        bootstrap_repetitions=64,
        exploratory=True,
    )
