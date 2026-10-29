"""Frozen configuration for the xeno-bridge substrate.

The chemistry deliberately shares NOTHING with GARD's mathematics: species
are binary polymers, reactions are ligation/cleavage, growth is by monomer
influx (ligation conserves mass), and the "rule" is a catalysis table over
(reaction, catalyst-species) pairs. The only things imported from the GARD
program are the OBSERVER constants — the same inheritance, coherence, and
distinctness thresholds and the same strict run/horizon — so that the
frozen behavioral pattern signature is well-posed on both sides.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class XenoConfig:
    mode: str = "full"
    # Chemistry.
    max_length: int = 4
    k_lig0: float = 1.0e-2
    k_clv0: float = 1.0e-4
    influx: float = 2.0  # per monomer species, per unit time
    dilution: float = 0.003  # per molecule, per unit time
    gamma: float = 30.0
    p_cat: float = 0.02
    # Probability of a catalysis entry when the catalyst IS the reaction's
    # product (self-reinforcing loops — the architecture E1 showed carries
    # hereditary capability). 0 disables the bias.
    p_self: float = 0.0
    # Compartment and division.
    mass_max: int = 240
    mass_dead: int = 8
    division_contract: str = "binomial"  # or "even"
    # Observer constants — identical to AtlasConfig on purpose.
    inherit_threshold: float = 0.9
    coherence_threshold: float = 0.9
    distinct_threshold: float = 0.85
    strict_run: int = 8
    strict_horizon: int = 32
    # Engine (adaptive tau-leaping, batched over futures).
    tau_target_events: float = 3.0
    tau_max: float = 2.0
    max_steps_per_generation: int = 40_000
    # Campaign shape.
    n_seeds: int = 16
    seed_mass_fraction: float = 0.6
    futures_per_seed: int = 128
    dev_table_seed_tag: str = "xeno-dev-v1"
    confirm_table_seed_tag: str = "xeno-confirm-v1"
    trajectory_seed_tag: str = "xeno-traj-v1"

    @classmethod
    def tiny(cls) -> "XenoConfig":
        return cls(
            mode="tiny",
            max_length=3,
            mass_max=60,
            mass_dead=4,
            strict_run=3,
            strict_horizon=8,
            n_seeds=4,
            futures_per_seed=32,
            max_steps_per_generation=10_000,
        )

    def validate(self) -> None:
        if self.mode not in ("full", "tiny"):
            raise ValueError("mode must be 'full' or 'tiny'")
        if self.max_length < 2:
            raise ValueError("need polymers of at least length 2")
        if self.mass_max <= 2 * self.mass_dead:
            raise ValueError("division mass must exceed twice the death mass")
        if self.division_contract not in ("binomial", "even"):
            raise ValueError("unknown division contract")
        if not (0 <= self.distinct_threshold <= self.inherit_threshold <= 1):
            raise ValueError("invalid observer thresholds")
        if self.strict_run < 1 or self.strict_horizon <= self.strict_run:
            raise ValueError("strict horizon must leave room for a break and run")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def digest(self) -> str:
        payload = json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


def capsule_root() -> Path:
    return Path(__file__).resolve().parents[2]


def work_root(config: XenoConfig) -> Path:
    return capsule_root() / "work" / config.mode


def results_root(config: XenoConfig) -> Path:
    return capsule_root() / "results" / config.mode
