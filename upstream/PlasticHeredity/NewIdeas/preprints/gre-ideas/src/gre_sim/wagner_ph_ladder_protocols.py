"""Registered seeds and protocol for Wagner PH Origin Ladder v1."""

from __future__ import annotations

from .artifacts import canonical_digest
from .wagner_ph_ladder_config import WagnerPHLadderSpec


LADDER_SEED = canonical_digest(
    "wagner-ph-origin-ladder-v1-exploration-production-2026-08-24"
)
LADDER_CONFIRMATION_SEED = canonical_digest(
    "wagner-ph-origin-ladder-v1-untouched-confirmation-reserve-2026-08-24"
)


def wagner_ph_ladder_spec(*, smoke: bool = False) -> WagnerPHLadderSpec:
    result = WagnerPHLadderSpec(
        cohort_id="wagner-ph-origin-ladder-v1",
        master_seed=LADDER_SEED,
        confirmation_seed=LADDER_CONFIRMATION_SEED,
    )
    result.validate()
    return result.smoke() if smoke else result


def protocol_digest(spec: WagnerPHLadderSpec) -> str:
    return canonical_digest(spec.to_dict())
