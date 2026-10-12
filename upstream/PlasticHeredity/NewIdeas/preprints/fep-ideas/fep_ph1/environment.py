from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .config import CANDIDATES, ExperimentConfig
from .gard import (
    SimulationError,
    advance_fission,
    apply_ranked_substitution,
    balanced_partition,
    normalized_gate,
    simultaneous_permutation,
    variance_restored_log_morph,
)
from .types import (
    Action,
    ActionChannel,
    AlignmentLevel,
    EnvironmentFamily,
    ExternalRegime,
    GardStep,
    ObservationThresholds,
    RawObservation,
    RegimeSpec,
)


@dataclass(frozen=True)
class EnvironmentDesign:
    family: EnvironmentFamily
    channel: ActionChannel
    regime: RegimeSpec
    candidate: str
    partition_seed: int
    permutation_seed: int


def _ranks(values: NDArray[np.float64]) -> NDArray[np.float64]:
    order = np.argsort(np.asarray(values, dtype=np.float64), kind="stable")
    ranks = np.empty(len(order), dtype=np.float64)
    ranks[order] = np.linspace(0.0, 1.0, len(order), dtype=np.float64)
    return ranks


def encode_observation(
    raw: RawObservation,
    thresholds: ObservationThresholds,
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
    if raw.boundary_similarity < 0.85:
        similarity = 0
    elif raw.boundary_similarity <= 0.90:
        similarity = 1
    else:
        similarity = 2
    if raw.alignment_score < thresholds.alignment[0]:
        alignment = 0
    elif raw.alignment_score < thresholds.alignment[1]:
        alignment = 1
    else:
        alignment = 2
    if not 0 <= int(raw.cue) <= 3:
        raise ValueError("cue is outside its four-category alphabet")
    return growth, similarity, alignment, int(raw.cue)


class GardActiveInferenceEnvironment:
    """Controlled GARD process with an explicitly imposed informational boundary."""

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
        if design.candidate not in CANDIDATES:
            raise ValueError(f"unknown candidate {design.candidate!r}")
        self.config = config
        self.design = design
        self.base_beta = np.asarray(beta, dtype=np.float64).copy()
        self.composition = np.asarray(initial_composition, dtype=np.int64).copy()
        n_types = config.gard.n_types
        if self.base_beta.shape != (n_types, n_types):
            raise ValueError("beta shape does not match GARD configuration")
        if self.composition.shape != (n_types,) or np.any(self.composition < 0):
            raise ValueError("initial composition is invalid")
        self.thresholds = thresholds or ObservationThresholds()
        self.thresholds.validate()
        self.chemistry_rng = np.random.default_rng(chemistry_seed)
        self.environment_rng = np.random.default_rng(environment_seed)
        self.observation_rng = np.random.default_rng(observation_seed)
        self.partition = balanced_partition(n_types, design.partition_seed)
        permutation = np.random.default_rng(design.permutation_seed).permutation(n_types)
        self.permuted_beta = simultaneous_permutation(self.base_beta, permutation)
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
        self.step_index = 0

    def _target_scores(self, action: int) -> NDArray[np.float64]:
        if action == int(Action.ADAPT_A):
            return self.target_a_scores
        if action == int(Action.ADAPT_B):
            return self.target_b_scores
        return np.full(self.config.gard.n_types, 0.5, dtype=np.float64)

    def _regime_scores(self, regime: int | None = None) -> NDArray[np.float64]:
        selected = self.regime if regime is None else int(regime)
        if selected == int(ExternalRegime.A):
            return self.target_a_scores
        if selected == int(ExternalRegime.B):
            return self.target_b_scores
        return 0.5 * (self.target_a_scores + self.target_b_scores)

    def _alignment_score(
        self, composition: NDArray[np.int64], regime: int | None = None
    ) -> float:
        values = np.asarray(composition, dtype=np.float64)
        mass = float(values.sum())
        if mass <= 0.0:
            return 0.0
        return float(np.dot(values / mass, self._regime_scores(regime)))

    def _alignment_level(self, score: float) -> int:
        left, right = self.thresholds.alignment
        return int(
            AlignmentLevel.LOW
            if score < left
            else AlignmentLevel.MEDIUM
            if score < right
            else AlignmentLevel.HIGH
        )

    def _cue(self, sampled: bool) -> int:
        accuracy = (
            self.config.sampled_cue_accuracy
            if sampled
            else self.config.passive_cue_accuracy
        )
        if self.observation_rng.random() > accuracy:
            return 0
        return self.regime + 1

    def _transition_environment(self) -> None:
        if self.environment_rng.random() < self.design.regime.switch_probability:
            self.base_regime = 1 - self.base_regime
        if self.environment_rng.random() < self.design.regime.shock_probability:
            self.regime = int(ExternalRegime.SHOCK)
        else:
            self.regime = self.base_regime

    def _active_beta(self) -> NDArray[np.float64]:
        if self.design.family == EnvironmentFamily.NUTRIENT:
            return self.base_beta
        if self.regime == int(ExternalRegime.A):
            return self.base_beta
        if self.regime == int(ExternalRegime.B):
            return self.beta_b
        return self.beta_shock

    def _base_reservoir(self) -> NDArray[np.float64] | None:
        if self.design.family == EnvironmentFamily.CATALYTIC:
            return None
        n_types = self.config.gard.n_types
        if self.regime == int(ExternalRegime.SHOCK):
            return np.full(
                n_types,
                self.design.regime.shock_supply_multiplier / n_types,
                dtype=np.float64,
            )
        direction = 1.0 if self.regime == int(ExternalRegime.A) else -1.0
        signed = np.where(self.partition == 0, 1.0, -1.0)
        weights = np.exp(direction * self.design.regime.nutrient_contrast * signed)
        return weights / float(weights.mean()) / n_types

    def _controlled_reservoir(self, action: int) -> NDArray[np.float64] | None:
        base = self._base_reservoir()
        if self.design.channel != ActionChannel.UPTAKE or action not in (
            int(Action.ADAPT_A),
            int(Action.ADAPT_B),
        ):
            return base
        direction = 1 if action == int(Action.ADAPT_A) else -1
        signed = self.target_a_scores - self.target_b_scores
        gate = normalized_gate(signed, direction, self.config.gate_strength)
        if base is None:
            base = np.full(
                self.config.gard.n_types,
                1.0 / self.config.gard.n_types,
                dtype=np.float64,
            )
        return base * gate

    def initial_step(self) -> GardStep:
        score = self._alignment_score(self.composition)
        raw = RawObservation(0, 1.0, score, self._cue(sampled=False), False)
        return GardStep(
            composition=self.composition.copy(),
            parent=None,
            raw_observation=raw,
            external_regime=self.regime,
            alignment_level=self._alignment_level(score),
            intended_action=int(Action.WAIT),
            executed_action=int(Action.WAIT),
            abstract_action_cost=0.0,
            physical_action_cost=0.0,
            completed=True,
        )

    def step(self, intended_action: int, *, action_lesion: bool = False) -> GardStep:
        if self.terminal:
            raise RuntimeError("cannot step an absorbing terminal environment")
        intended = Action(int(intended_action))
        executed = Action.WAIT if action_lesion else intended
        composition = self.composition
        remove = -1
        add = -1
        if self.design.channel == ActionChannel.MOLECULAR and executed in (
            Action.ADAPT_A,
            Action.ADAPT_B,
        ):
            composition, remove, add = apply_ranked_substitution(
                composition, self._target_scores(int(executed))
            )
        reservoir = self._controlled_reservoir(int(executed))
        exposure = (
            self.config.sampling_exposure_multiplier
            if executed == Action.SAMPLE
            else 1.0
        )
        abstract_cost = (
            self.config.action_cost_sample
            if executed == Action.SAMPLE
            else self.config.action_cost_adapt
            if executed in (Action.ADAPT_A, Action.ADAPT_B)
            else 0.0
        )
        physical_cost = (
            1.0 - exposure
            if executed == Action.SAMPLE
            else 1.0
            if remove >= 0
            else float(np.mean(np.abs(reservoir * self.config.gard.n_types - 1.0)))
            if self.design.channel == ActionChannel.UPTAKE
            and executed in (Action.ADAPT_A, Action.ADAPT_B)
            and reservoir is not None
            else 0.0
        )
        try:
            record = advance_fission(
                composition,
                self._active_beta(),
                self.config.gard,
                CANDIDATES[self.design.candidate],
                self.chemistry_rng,
                reservoir=reservoir,
                exposure_multiplier=exposure,
            )
        except SimulationError:
            self.terminal = True
            score = self._alignment_score(composition)
            raw = RawObservation(
                self.config.gard.max_growth_steps,
                0.0,
                score,
                0,
                True,
            )
            return GardStep(
                composition=np.asarray(composition, dtype=np.int64).copy(),
                parent=None,
                raw_observation=raw,
                external_regime=self.regime,
                alignment_level=self._alignment_level(score),
                intended_action=int(intended),
                executed_action=int(executed),
                abstract_action_cost=abstract_cost,
                physical_action_cost=physical_cost,
                completed=False,
                edit_remove=remove,
                edit_add=add,
            )
        self.composition = record.daughter.copy()
        self.step_index += 1
        self._transition_environment()
        score = self._alignment_score(self.composition)
        raw = RawObservation(
            record.growth_steps,
            record.h,
            score,
            self._cue(sampled=executed == Action.SAMPLE),
            False,
        )
        return GardStep(
            composition=self.composition.copy(),
            parent=record.parent.copy(),
            raw_observation=raw,
            external_regime=self.regime,
            alignment_level=self._alignment_level(score),
            intended_action=int(intended),
            executed_action=int(executed),
            abstract_action_cost=abstract_cost,
            physical_action_cost=physical_cost,
            completed=True,
            edit_remove=remove,
            edit_add=add,
        )

