from __future__ import annotations

import hashlib
from dataclasses import replace

from fep_surprise_25.config import Campaign25Config, profile_config as base_profile_config


AMENDMENT_LABEL = "experiment25-amendment1-goldilocks-boundary"
EXPECTED_FULL_REGISTRATION_ID = (
    "d098fed65a31adcc2f96ab9386fb717f5d2f946f39cdc26930296fdc8b21371d"
)
REFERENCE_HALF_QUOTA = {"full": 600, "quick": 48, "smoke": 20}
REGULAR_REFERENCE_LINEAGES = {"full": 16, "quick": 8, "smoke": 4}
SIGMA500_REFERENCE_LINEAGES = {"full": 96, "quick": 16, "smoke": 4}
SCIENTIFIC_BUDGET_SECONDS = 28_800
GRACEFUL_STOP_SECONDS = 27_900
REGISTRATION_PROJECTION_CEILING_SECONDS = 23_400


def amendment_master_seed(source_registration_id: str) -> str:
    material = f"{source_registration_id}|{AMENDMENT_LABEL}".encode("ascii")
    return hashlib.sha256(material).hexdigest()


def reference_half_quota(profile: str) -> int:
    return REFERENCE_HALF_QUOTA[profile]


def reference_lineages(profile: str, atlas_key: str) -> int:
    if atlas_key == "sigma_500":
        return SIGMA500_REFERENCE_LINEAGES[profile]
    return REGULAR_REFERENCE_LINEAGES[profile]


def profile_config(
    profile: str, source_registration_id: str = EXPECTED_FULL_REGISTRATION_ID
) -> Campaign25Config:
    """Return a base-compatible config carrying the sealed amendment choices."""

    base = base_profile_config(profile)
    quota = reference_half_quota(profile)
    regular = reference_lineages(profile, "native")
    confirmation = replace(
        base.confirmation,
        reference_lineages=regular,
        minimum_reference_states=2 * quota,
        training_subsample=quota,
    )
    config = replace(
        base,
        confirmation=confirmation,
        master_seed=amendment_master_seed(source_registration_id),
        scientific_budget_seconds=(
            SCIENTIFIC_BUDGET_SECONDS if profile == "full" else base.scientific_budget_seconds
        ),
        graceful_stop_seconds=(
            GRACEFUL_STOP_SECONDS if profile == "full" else base.graceful_stop_seconds
        ),
    )
    config.validate()
    return config
