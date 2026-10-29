"""Frozen H035 development design: two independently assigned cue rules."""
from __future__ import annotations

import numpy as np
import model as m

ROOT_SEED = 35035
N, HISTORIES, REPLICATES = 64, 4, 2
GENERATIONS, SWEEPS, FORMATION_SWEEPS = 16, 8, 24
CHECKPOINTS = (0, 1, 4, 8, 16)
GAIN, DAMAGE = 4., .5
INPUTS = np.arange(4)
TEACHING_SITES = np.arange(24)
RULES = np.array([[1., 1.], [1., -1.], [-1., 1.], [-1., -1.]])
CUE_AXES = np.array([[1., 1., 1., 1.], [1., -1., 1., -1.]])
POLARITIES = np.array([-1., 1.])
CUES = (CUE_AXES[:, None, :] * POLARITIES[None, :, None]).reshape(4, 4)
TARGETS = (RULES[:, :, None] * POLARITIES).reshape(HISTORIES, 4)
LOADS = ('a_only', 'b_only', 'both')
SCHEDULES = np.array([[0, 1, 0, 1], [2, 3, 2, 3], [0, 1, 2, 3]])
ARMS = ('renewal', 'foreign_a', 'foreign_b', 'foreign_both', 'scrambled',
        'erased', 'read_off', 'write_off', 'protected_copy', 'damaged_copy',
        'writer_scrambled')
DONORS = {'foreign_a': np.array([2, 3, 0, 1]),
          'foreign_b': np.array([1, 0, 3, 2]),
          'foreign_both': np.array([3, 2, 1, 0])}
BENCHMARK_BLOCKS = tuple(range(4))
PILOT_BLOCKS = tuple(range(8))
CLASSIFICATION = 'BOUNDED_DEVELOPMENT_PILOT'


def random(cohort, block, *key):
    if cohort not in ('engineering', 'pilot', 'fixture'):
        raise ValueError('Unknown H035 random namespace')
    return m.rng(ROOT_SEED, 'H035', cohort, int(block), *key)


def orders(cohort, block, *key, sweeps=SWEEPS):
    r = random(cohort, block, *key)
    return np.stack([r.permutation(N) for _ in range(sweeps)])


def inputs(cohort, block, generations=GENERATIONS):
    """All common random inputs; no outcome-dependent draws or selections."""
    def bits(*key, shape):
        return random(cohort, block, *key).choice([-1., 1.], size=shape)
    checkpoints = np.array([g for g in CHECKPOINTS if g <= generations])
    base = m.symmetric(random(cohort, block, 'base').normal(size=(N, N))) * (.12/np.sqrt(N))
    # Canonical cue births are shared across histories and loads. Duplicate
    # single-rule exposures repeat the identical trial, retaining mean scale.
    return dict(base=base,
        founder_birth=bits('formation', 'birth', shape=(4, N)),
        formation_orders=orders(cohort, block, 'formation', 'order', sweeps=FORMATION_SWEEPS),
        body_birth=np.stack([bits('body', g, 'birth', shape=(REPLICATES, 4, N))
                             for g in range(1, generations+1)]),
        body_orders=np.stack([orders(cohort, block, 'body', g, 'order')
                              for g in range(1, generations+1)]),
        assay_birth=np.stack([bits('assay', int(g), 'birth', shape=(REPLICATES, 4, N))
                              for g in checkpoints]),
        assay_orders=np.stack([orders(cohort, block, 'assay', int(g), 'order')
                               for g in checkpoints]),
        damage=np.stack([m.mask_edges(random(cohort, block, 'damage', g),
                                     (REPLICATES, N, N), DAMAGE)
                          for g in range(1, generations+1)]),
        permutation=np.r_[np.arange(8), random(cohort, block, 'permutation').permutation(np.arange(8, N))],
        checkpoints=checkpoints)


def settings():
    return dict(root_seed=ROOT_SEED, neurons=N, histories=RULES.tolist(),
        descendants_per_history=REPLICATES, generations=GENERATIONS,
        sweeps=SWEEPS, formation_sweeps=FORMATION_SWEEPS, checkpoints=CHECKPOINTS,
        gain=GAIN, damage=DAMAGE, cue_axes=CUE_AXES.tolist(), cues=CUES.tolist(),
        loads=LOADS, schedules=SCHEDULES.tolist(), arms=ARMS,
        pilot_blocks=PILOT_BLOCKS, benchmark_blocks=BENCHMARK_BLOCKS,
        output_threshold_strict=.5, pilot_is_confirmation=False)
