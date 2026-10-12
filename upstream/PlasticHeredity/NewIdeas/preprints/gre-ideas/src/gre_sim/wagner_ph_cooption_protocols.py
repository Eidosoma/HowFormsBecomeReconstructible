"""Registered seeds for the Wagner PH co-option campaign."""

from __future__ import annotations

from .artifacts import canonical_digest
from .wagner_ph_cooption_config import CooptionSpec


COOPTION_SEED = canonical_digest(
    "wagner-ph-cooption-v1-exploration-production-2026-08-24"
)
COOPTION_CONFIRMATION_SEED = canonical_digest(
    "wagner-ph-cooption-v1-untouched-confirmation-reserve-2026-08-24"
)


def wagner_ph_cooption_spec(*, smoke: bool = False) -> CooptionSpec:
    spec = CooptionSpec(
        cohort_id="wagner-ph-cooption-v1",
        master_seed=COOPTION_SEED,
        confirmation_seed=COOPTION_CONFIRMATION_SEED,
    )
    spec.validate()
    return spec.smoke() if smoke else spec


def protocol_digest(spec: CooptionSpec) -> str:
    return canonical_digest(spec.to_dict())
