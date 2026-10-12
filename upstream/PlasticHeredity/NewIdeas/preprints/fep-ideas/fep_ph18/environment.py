from __future__ import annotations

import copy
from dataclasses import dataclass, replace
from typing import Any

import numpy as np
from numpy.typing import NDArray

from fep_lab.integrity import canonical_json_bytes, sha256_bytes
from fep_ph1.gard import normalized_gate
from fep_ph15.environment import (
    EnvironmentDesign as BaseEnvironmentDesign,
    GardGoalAlignmentEnvironment as BaseEnvironment,
)
from fep_ph15.types import Action, ActionChannel, ExternalRegime
from .types import InformationArm, SensingTiming


@dataclass(frozen=True)
class EnvironmentDesign(BaseEnvironmentDesign):
    authority_scale: float = 1.0
    information_arm: InformationArm = InformationArm.NONE
    sensing_timing: SensingTiming = SensingTiming.DELAYED


class GardGoalAlignmentEnvironment(BaseEnvironment):
    """FEP–PH1.8 environment with frozen authority and information arms."""

    design: EnvironmentDesign

    def sensing_accuracy(self) -> float:
        if self.design.information_arm == InformationArm.NONE:
            return float(self.config.stage_a_sample_accuracy)
        if self.design.information_arm == InformationArm.INFORMATIVE:
            return float(self.config.informative_sample_accuracy)
        return float(self.config.sham_sample_accuracy)

    def sense_current(self) -> int:
        """Observe the current regime without advancing chemistry or regime time."""

        accuracy = self.sensing_accuracy()
        return 0 if self.observation_rng.random() > accuracy else int(self.regime) + 1

    def _cue(self, sampled: bool) -> int:
        if self.design.information_arm == InformationArm.NONE:
            accuracy = (
                self.config.stage_a_sample_accuracy
                if sampled
                else self.config.stage_a_passive_cue_accuracy
            )
        elif sampled and self.design.information_arm == InformationArm.INFORMATIVE:
            accuracy = self.config.informative_sample_accuracy
        elif sampled:
            accuracy = self.config.sham_sample_accuracy
        else:
            accuracy = self.config.passive_cue_accuracy
        return 0 if self.observation_rng.random() > accuracy else self.regime + 1

    def _controlled_reservoir(self, action: int) -> NDArray[np.float64] | None:
        base = self._base_reservoir()
        if (
            self.design.channel != ActionChannel.UPTAKE
            or action not in (int(Action.ADAPT_A), int(Action.ADAPT_B))
            or self.design.authority_scale == 0.0
        ):
            return base
        scores = self._target_scores(action)
        strength = self.config.gate_strength * self.design.authority_scale
        gate = normalized_gate(scores, 1, strength)
        if base is None:
            base = np.full(self.gard.n_types, 1.0 / self.gard.n_types)
        return base * gate

    def exposure_multiplier(self, action: int) -> float:
        action = int(action)
        if self.design.channel != ActionChannel.UPTAKE:
            return super().exposure_multiplier(action)
        shock = self.regime == int(ExternalRegime.SHOCK)
        baseline = 0.50 if shock else 0.70
        if action == int(Action.SAMPLE):
            return 0.475 if shock else 0.665
        if action == int(Action.WAIT):
            return baseline
        if action not in (int(Action.ADAPT_A), int(Action.ADAPT_B)):
            return baseline
        if shock:
            current = 0.40
        else:
            correct = (
                self.regime == int(ExternalRegime.A)
                and action == int(Action.ADAPT_A)
            ) or (
                self.regime == int(ExternalRegime.B)
                and action == int(Action.ADAPT_B)
            )
            current = 1.20 if correct else 0.45
        scaled = baseline + self.design.authority_scale * (current - baseline)
        return float(np.clip(scaled, 0.05, 1.50))

    def step(self, intended_action: int, *, action_lesion: bool = False):
        # The inherited implementation computes uptake effort at lambda=1.
        # Recompute only that descriptive cost so zero authority is physically
        # costless and strengthened authority reports its actual gate strength.
        pre_regime = int(self.regime)
        executed = int(Action.WAIT) if action_lesion else int(intended_action)
        exposure = self.exposure_multiplier(executed)
        result = super().step(intended_action, action_lesion=action_lesion)
        if (
            self.design.channel == ActionChannel.UPTAKE
            and executed in (int(Action.ADAPT_A), int(Action.ADAPT_B))
        ):
            gate = normalized_gate(
                self._target_scores(executed),
                1,
                self.config.gate_strength * self.design.authority_scale,
            )
            baseline = 0.50 if pre_regime == int(ExternalRegime.SHOCK) else 0.70
            physical_cost = float(np.mean(np.abs(gate - 1.0))) + abs(
                exposure - baseline
            )
            result = replace(result, physical_action_cost=physical_cost)
        return result

    def step_compound(
        self, intended_action: int, *, sensed: bool, action_lesion: bool = False
    ):
        """Execute a same-cycle physical action and account for sensing effort."""

        if int(intended_action) == int(Action.SAMPLE):
            raise ValueError("same-cycle compound action requires WAIT or ADAPT")
        result = self.step(intended_action, action_lesion=action_lesion)
        if sensed:
            result = replace(
                result,
                abstract_action_cost=(
                    float(result.abstract_action_cost) + self.config.action_cost_sample
                ),
                # Same-cycle sensing does not replace growth, but it pays the
                # same explicitly logged sensing burden as delayed sampling.
                physical_action_cost=(
                    float(result.physical_action_cost)
                    + (1.0 - self.config.sampling_exposure_multiplier)
                ),
            )
        return result


@dataclass(frozen=True)
class PlanningSeeds:
    chemistry: int
    environment: int
    observation: int


def clone_environment(
    environment: GardGoalAlignmentEnvironment,
) -> GardGoalAlignmentEnvironment:
    """Create an exact, independent snapshot while sharing immutable physics."""

    value = copy.copy(environment)
    value.composition = environment.composition.copy()
    for name in ("chemistry_rng", "environment_rng", "observation_rng"):
        source = getattr(environment, name)
        bit_generator = type(source.bit_generator)()
        bit_generator.state = copy.deepcopy(source.bit_generator.state)
        setattr(value, name, np.random.Generator(bit_generator))
    return value


def planning_clone(
    environment: GardGoalAlignmentEnvironment, seeds: PlanningSeeds
) -> GardGoalAlignmentEnvironment:
    value = clone_environment(environment)
    value.chemistry_rng = np.random.default_rng(seeds.chemistry)
    value.environment_rng = np.random.default_rng(seeds.environment)
    value.observation_rng = np.random.default_rng(seeds.observation)
    return value


def environment_fingerprint(environment: GardGoalAlignmentEnvironment) -> str:
    payload: dict[str, Any] = {
        "composition": environment.composition.tolist(),
        "base_regime": int(environment.base_regime),
        "regime": int(environment.regime),
        "terminal": bool(environment.terminal),
        "authority_scale": float(environment.design.authority_scale),
        "information_arm": str(environment.design.information_arm),
        "sensing_timing": str(environment.design.sensing_timing),
        "chemistry_rng": environment.chemistry_rng.bit_generator.state,
        "environment_rng": environment.environment_rng.bit_generator.state,
        "observation_rng": environment.observation_rng.bit_generator.state,
    }
    return sha256_bytes(canonical_json_bytes(payload))


__all__ = (
    "EnvironmentDesign",
    "GardGoalAlignmentEnvironment",
    "PlanningSeeds",
    "clone_environment",
    "environment_fingerprint",
    "planning_clone",
)
