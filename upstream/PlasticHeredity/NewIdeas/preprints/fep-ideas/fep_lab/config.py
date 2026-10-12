from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


MASTER_SEED = "7ec423807ef1f72264101d7ab12fc1bfa9e478baecac1ce856e1a49012be4599"


@dataclass(frozen=True)
class LabConfig:
    profile: str
    master_seed: str = MASTER_SEED
    episode_steps: int = 48
    episodes_per_condition: int = 2_048
    blanket_trajectories: int = 256
    blanket_steps: int = 2_048
    blanket_dt: float = 0.05
    bootstrap_repetitions: int = 1_024
    wall_time_limit_seconds: int = 7_200
    graceful_stop_seconds: int = 6_900
    selected_scale: int | None = None

    def validate(self) -> None:
        if self.profile not in {"smoke", "quick", "full"}:
            raise ValueError(f"unknown profile {self.profile!r}")
        integer_fields = (
            self.episode_steps,
            self.episodes_per_condition,
            self.blanket_trajectories,
            self.blanket_steps,
            self.bootstrap_repetitions,
        )
        if any(value <= 0 for value in integer_fields):
            raise ValueError("simulation sizes must be positive")
        if not 0.0 < self.blanket_dt <= 1.0:
            raise ValueError("blanket_dt must lie in (0, 1]")
        if self.graceful_stop_seconds >= self.wall_time_limit_seconds:
            raise ValueError("graceful stop must precede the hard wall-time limit")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def profile_config(profile: str) -> LabConfig:
    if profile == "smoke":
        value = LabConfig(
            profile="smoke",
            episode_steps=8,
            episodes_per_condition=4,
            blanket_trajectories=8,
            blanket_steps=64,
            bootstrap_repetitions=32,
            wall_time_limit_seconds=300,
            graceful_stop_seconds=270,
        )
    elif profile == "quick":
        value = LabConfig(
            profile="quick",
            episode_steps=24,
            episodes_per_condition=128,
            blanket_trajectories=64,
            blanket_steps=512,
            bootstrap_repetitions=256,
            wall_time_limit_seconds=1_800,
            graceful_stop_seconds=1_650,
        )
    elif profile == "full":
        value = LabConfig(profile="full")
    else:
        raise ValueError(f"unknown profile {profile!r}")
    value.validate()
    return value
