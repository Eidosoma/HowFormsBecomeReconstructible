"""Binary-polymer chemistry: species, reactions, catalysis, propensities."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import XenoConfig


@dataclass(frozen=True)
class Chemistry:
    species: tuple[str, ...]
    index: dict[str, int]
    masses: np.ndarray  # (S,) string lengths
    monomer_ids: tuple[int, int]
    # Ligation r: species[left_id[r]] + species[right_id[r]] -> species[product_id[r]]
    left_id: np.ndarray
    right_id: np.ndarray
    product_id: np.ndarray
    # Stoichiometry: (R, S) for ligations; cleavage is the negation.
    lig_stoich: np.ndarray

    @property
    def n_species(self) -> int:
        return len(self.species)

    @property
    def n_reactions(self) -> int:
        return len(self.left_id)


def build_chemistry(config: XenoConfig) -> Chemistry:
    species: list[str] = []
    for length in range(1, config.max_length + 1):
        for value in range(2**length):
            species.append(format(value, f"0{length}b"))
    index = {name: i for i, name in enumerate(species)}
    masses = np.asarray([len(name) for name in species], dtype=np.int64)

    left, right, product = [], [], []
    for a in species:
        for b in species:
            if len(a) + len(b) <= config.max_length:
                left.append(index[a])
                right.append(index[b])
                product.append(index[a + b])
    left_arr = np.asarray(left, dtype=np.int64)
    right_arr = np.asarray(right, dtype=np.int64)
    product_arr = np.asarray(product, dtype=np.int64)

    stoich = np.zeros((len(left_arr), len(species)), dtype=np.int64)
    for r in range(len(left_arr)):
        stoich[r, left_arr[r]] -= 1
        stoich[r, right_arr[r]] -= 1
        stoich[r, product_arr[r]] += 1

    return Chemistry(
        species=tuple(species),
        index=index,
        masses=masses,
        monomer_ids=(index["0"], index["1"]),
        left_id=left_arr,
        right_id=right_arr,
        product_id=product_arr,
        lig_stoich=stoich,
    )


def sample_table(chemistry: Chemistry, config: XenoConfig, rng: np.random.Generator) -> np.ndarray:
    """One catalysis 'rule table': (R, S) entries in {0, gamma}.

    Entries where the catalyst is the reaction's own product are drawn at
    ``p_self`` instead of ``p_cat``, biasing tables toward self-reinforcing
    loops when configured.
    """
    threshold = np.full((chemistry.n_reactions, chemistry.n_species), config.p_cat)
    if config.p_self > 0:
        threshold[np.arange(chemistry.n_reactions), chemistry.product_id] = config.p_self
    mask = rng.random((chemistry.n_reactions, chemistry.n_species)) < threshold
    return mask.astype(np.float64) * config.gamma


def batch_propensities(
    counts: np.ndarray,  # (B, S) int
    table: np.ndarray,  # (R, S)
    chemistry: Chemistry,
    config: XenoConfig,
) -> tuple[np.ndarray, np.ndarray]:
    """Ligation and cleavage propensities for a batch of compartments.

    Boost mirrors GARD's *form* (1 + coupling . counts / mass) without any
    GARD state mathematics: each catalyst molecule contributes
    ``gamma / M`` to the reactions it catalyzes, in both directions.
    """
    counts_f = counts.astype(np.float64)
    mass = np.maximum((counts_f * chemistry.masses).sum(axis=1), 1.0)
    boost = 1.0 + (counts_f @ table.T) / mass[:, None]  # (B, R)

    n_left = counts_f[:, chemistry.left_id]
    n_right = counts_f[:, chemistry.right_id]
    same = chemistry.left_id == chemistry.right_id
    pair_count = np.where(same[None, :], n_left * np.maximum(n_left - 1.0, 0.0), n_left * n_right)
    ligation = config.k_lig0 * pair_count * boost
    cleavage = config.k_clv0 * counts_f[:, chemistry.product_id] * boost
    return ligation, cleavage
