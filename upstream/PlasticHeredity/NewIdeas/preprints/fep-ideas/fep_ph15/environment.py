from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
from numpy.typing import NDArray

from fep_ph1.config import CANDIDATES
from fep_ph1.gard import (
    SimulationError,
    advance_fission,
    apply_ranked_substitution,
    balanced_partition,
    normalized_gate,
    simultaneous_permutation,
    variance_restored_log_morph,
)
from fep_ph1.types import RegimeSpec

from .config import ExperimentConfig
from .types import (
    Action,
    ActionChannel,
    ActuatorSetting,
    AlignmentLevel,
    EnvironmentFamily,
    ExternalRegime,
    GardStep,
    ObservationThresholds,
    RawObservation,
)


@dataclass(frozen=True)
class EnvironmentDesign:
    family: EnvironmentFamily
    channel: ActionChannel
    regime: RegimeSpec
    candidate: str
    partition_seed: int
    permutation_seed: int
    growth_budget: int
    actuator: ActuatorSetting

    def validate(self) -> None:
        if self.candidate not in CANDIDATES:
            raise ValueError(f"unknown candidate {self.candidate!r}")
        if self.growth_budget <= 0:
            raise ValueError("growth budget must be positive")
        self.actuator.validate()


def _ranks(values: NDArray[np.float64]) -> NDArray[np.float64]:
    order = np.argsort(np.asarray(values, dtype=np.float64), kind="stable")
    ranks = np.empty(len(order), dtype=np.float64)
    ranks[order] = np.linspace(0.0, 1.0, len(order), dtype=np.float64)
    return ranks


def encode_observation(
    raw: RawObservation, thresholds: ObservationThresholds
) -> tuple[int, int, int, int]:
    thresholds.validate()
    if raw.terminal:
        growth = 3
    elif raw.growth_steps <= thresholds.growth[0]:
        growth = 0
    elif raw.growth_steps <= thresholds.growth[1]:
        growth = 1
    else:
        growth = 2
    similarity = 0 if raw.boundary_similarity < 0.85 else 1 if raw.boundary_similarity <= 0.90 else 2
    alignment = 0 if raw.alignment_score < thresholds.alignment[0] else 1 if raw.alignment_score < thresholds.alignment[1] else 2
    if not 0 <= int(raw.cue) <= 3:
        raise ValueError("cue is outside its four-category alphabet")
    return growth, similarity, alignment, int(raw.cue)


def apply_molecular_dose(
    composition: NDArray[np.int64], target_scores: NDArray[np.float64], dose: int
) -> tuple[NDArray[np.int64], tuple[tuple[int, int], ...]]:
    if dose not in {1, 2, 4, 8}:
        raise ValueError("molecular dose is outside the frozen setting grid")
    current = np.asarray(composition, dtype=np.int64).copy()
    edits: list[tuple[int, int]] = []
    for _ in range(dose):
        edited, remove_index, add_index = apply_ranked_substitution(current, target_scores)
        if remove_index < 0:
            break
        current = edited
        edits.append((remove_index, add_index))
    return current, tuple(edits)


class GardGoalAlignmentEnvironment:
    """GARD body with screen-selected, explicitly engineered action authority."""

    def __init__(
        self,
        config: ExperimentConfig,
        design: EnvironmentDesign,
        beta: NDArray[np.float64],
        initial_composition: NDArray[np.int64],
        chemistry_seed: int,
        environment_seed: int,
        observation_seed: int,
        thresholds: ObservationThresholds | None = None,
    ) -> None:
        design.validate()
        self.config = config
        self.design = design
        self.gard = replace(config.gard, max_growth_steps=design.growth_budget)
        self.base_beta = np.asarray(beta, dtype=np.float64).copy()
        self.composition = np.asarray(initial_composition, dtype=np.int64).copy()
        if self.base_beta.shape != (self.gard.n_types, self.gard.n_types):
            raise ValueError("beta shape does not match the GARD contract")
        if self.composition.shape != (self.gard.n_types,) or np.any(self.composition < 0):
            raise ValueError("initial composition is invalid")
        self.thresholds = thresholds or ObservationThresholds()
        self.thresholds.validate()
        self.chemistry_rng = np.random.default_rng(chemistry_seed)
        self.environment_rng = np.random.default_rng(environment_seed)
        self.observation_rng = np.random.default_rng(observation_seed)
        self.partition = balanced_partition(self.gard.n_types, design.partition_seed)
        order = np.random.default_rng(design.permutation_seed).permutation(self.gard.n_types)
        self.permuted_beta = simultaneous_permutation(self.base_beta, order)
        self.beta_b = variance_restored_log_morph(
            self.base_beta, self.permuted_beta, design.regime.catalytic_morph
        )
        self.beta_shock = variance_restored_log_morph(
            self.base_beta, self.permuted_beta, design.regime.catalytic_shock_morph
        )
        if design.family == EnvironmentFamily.NUTRIENT:
            signed = np.where(self.partition == 0, 1.0, -1.0)
        else:
            native = np.log1p(np.maximum(self.base_beta.mean(axis=1), 0.0))
            changed = np.log1p(np.maximum(self.permuted_beta.mean(axis=1), 0.0))
            signed = native - changed
        self.target_a_scores = _ranks(np.asarray(signed, dtype=np.float64))
        self.target_b_scores = _ranks(np.asarray(-signed, dtype=np.float64))
        self.base_regime = int(ExternalRegime.A)
        self.regime = int(ExternalRegime.A)
        self.terminal = False

    def _target_scores(self, action: int) -> NDArray[np.float64]:
        if action not in (int(Action.ADAPT_A), int(Action.ADAPT_B)):
            return np.full(self.gard.n_types, 0.5, dtype=np.float64)
        direct_a = action == int(Action.ADAPT_A)
        if self.design.actuator.polarity == "inverted":
            direct_a = not direct_a
        return self.target_a_scores if direct_a else self.target_b_scores

    def _regime_scores(self, regime: int | None = None) -> NDArray[np.float64]:
        value = self.regime if regime is None else int(regime)
        if value == int(ExternalRegime.A):
            return self.target_a_scores
        if value == int(ExternalRegime.B):
            return self.target_b_scores
        return 0.5 * (self.target_a_scores + self.target_b_scores)

    def _alignment_score(self, composition: NDArray[np.int64]) -> float:
        values = np.asarray(composition, dtype=np.float64)
        return 0.0 if values.sum() <= 0 else float(np.dot(values / values.sum(), self._regime_scores()))

    def _alignment_level(self, score: float) -> int:
        left, right = self.thresholds.alignment
        return int(AlignmentLevel.LOW if score < left else AlignmentLevel.MEDIUM if score < right else AlignmentLevel.HIGH)

    def _cue(self, sampled: bool) -> int:
        accuracy = self.config.sampled_cue_accuracy if sampled else self.config.passive_cue_accuracy
        return 0 if self.observation_rng.random() > accuracy else self.regime + 1

    def _transition_environment(self) -> None:
        if self.environment_rng.random() < self.design.regime.switch_probability:
            self.base_regime = 1 - self.base_regime
        self.regime = int(ExternalRegime.SHOCK) if self.environment_rng.random() < self.design.regime.shock_probability else self.base_regime

    def _active_beta(self) -> NDArray[np.float64]:
        if self.design.family == EnvironmentFamily.NUTRIENT or self.regime == int(ExternalRegime.A):
            return self.base_beta
        return self.beta_b if self.regime == int(ExternalRegime.B) else self.beta_shock

    def _base_reservoir(self) -> NDArray[np.float64] | None:
        if self.design.family == EnvironmentFamily.CATALYTIC:
            return None
        if self.regime == int(ExternalRegime.SHOCK):
            return np.full(
                self.gard.n_types,
                self.design.regime.shock_supply_multiplier / self.gard.n_types,
                dtype=np.float64,
            )
        direction = 1.0 if self.regime == int(ExternalRegime.A) else -1.0
        signed = np.where(self.partition == 0, 1.0, -1.0)
        weights = np.exp(direction * self.design.regime.nutrient_contrast * signed)
        return weights / float(weights.mean()) / self.gard.n_types

    def _controlled_reservoir(self, action: int) -> NDArray[np.float64] | None:
        base = self._base_reservoir()
        if self.design.channel != ActionChannel.UPTAKE or action not in (int(Action.ADAPT_A), int(Action.ADAPT_B)):
            return base
        scores = self._target_scores(action)
        gate = normalized_gate(scores, 1, self.config.gate_strength)
        if base is None:
            base = np.full(self.gard.n_types, 1.0 / self.gard.n_types, dtype=np.float64)
        return base * gate

    def exposure_multiplier(self, action: int) -> float:
        action = int(action)
        if self.design.channel == ActionChannel.MOLECULAR:
            return self.config.sampling_exposure_multiplier if action == int(Action.SAMPLE) else 1.0
        if self.regime == int(ExternalRegime.SHOCK):
            return 0.475 if action == int(Action.SAMPLE) else 0.40 if action in (int(Action.ADAPT_A), int(Action.ADAPT_B)) else 0.50
        if action == int(Action.SAMPLE):
            return 0.665
        if action == int(Action.WAIT):
            return 0.70
        correct = (self.regime == int(ExternalRegime.A) and action == int(Action.ADAPT_A)) or (self.regime == int(ExternalRegime.B) and action == int(Action.ADAPT_B))
        return 1.20 if correct else 0.45

    def initial_step(self) -> GardStep:
        score = self._alignment_score(self.composition)
        raw = RawObservation(0, 1.0, score, self._cue(False), False)
        return GardStep(
            self.composition.copy(), None, raw, self.regime,
            self._alignment_level(score), int(Action.WAIT), int(Action.WAIT), 0.0, 0.0, True
        )

    def step(self, intended_action: int, *, action_lesion: bool = False) -> GardStep:
        if self.terminal:
            raise RuntimeError("cannot step an absorbing terminal environment")
        intended = Action(int(intended_action))
        executed = Action.WAIT if action_lesion else intended
        composition = self.composition.copy()
        first_remove = -1
        first_add = -1
        substitutions = 0
        if self.design.channel == ActionChannel.MOLECULAR and executed in (Action.ADAPT_A, Action.ADAPT_B):
            composition, edits = apply_molecular_dose(
                composition,
                self._target_scores(int(executed)),
                self.design.actuator.molecular_dose,
            )
            substitutions = len(edits)
            if edits:
                first_remove, first_add = edits[0]
        reservoir = self._controlled_reservoir(int(executed))
        exposure = self.exposure_multiplier(int(executed))
        if executed == Action.SAMPLE:
            abstract_cost = self.config.action_cost_sample
        elif executed in (Action.ADAPT_A, Action.ADAPT_B):
            abstract_cost = (
                self.config.action_cost_uptake
                if self.design.channel == ActionChannel.UPTAKE
                else self.config.molecular_base_cost
                + self.config.molecular_increment_cost * (self.design.actuator.molecular_dose - 1)
            )
        else:
            abstract_cost = 0.0
        if self.design.channel == ActionChannel.MOLECULAR:
            physical_cost = float(substitutions) if executed in (Action.ADAPT_A, Action.ADAPT_B) else 1.0 - exposure if executed == Action.SAMPLE else 0.0
        else:
            baseline_exposure = 0.50 if self.regime == int(ExternalRegime.SHOCK) else 0.70
            if executed == Action.SAMPLE:
                physical_cost = abs(exposure - baseline_exposure)
            elif executed in (Action.ADAPT_A, Action.ADAPT_B):
                gate = normalized_gate(
                    self._target_scores(int(executed)), 1, self.config.gate_strength
                )
                physical_cost = float(np.mean(np.abs(gate - 1.0))) + abs(
                    exposure - baseline_exposure
                )
            else:
                physical_cost = 0.0
        try:
            record = advance_fission(
                composition,
                self._active_beta(),
                self.gard,
                CANDIDATES[self.design.candidate],
                self.chemistry_rng,
                reservoir=reservoir,
                exposure_multiplier=exposure,
            )
        except SimulationError:
            self.terminal = True
            score = self._alignment_score(composition)
            raw = RawObservation(self.design.growth_budget, 0.0, score, 0, True)
            return GardStep(
                composition, None, raw, self.regime, self._alignment_level(score),
                int(intended), int(executed), abstract_cost, physical_cost, False,
                first_remove, first_add,
            )
        self.composition = record.daughter.copy()
        self._transition_environment()
        score = self._alignment_score(self.composition)
        raw = RawObservation(record.growth_steps, record.h, score, self._cue(executed == Action.SAMPLE), False)
        return GardStep(
            self.composition.copy(), record.parent.copy(), raw, self.regime,
            self._alignment_level(score), int(intended), int(executed),
            abstract_cost, physical_cost, True, first_remove, first_add,
        )


def oracle_action(regime: int) -> int:
    if int(regime) == int(ExternalRegime.A):
        return int(Action.ADAPT_A)
    if int(regime) == int(ExternalRegime.B):
        return int(Action.ADAPT_B)
    return int(Action.WAIT)
