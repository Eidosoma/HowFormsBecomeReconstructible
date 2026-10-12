"""Fixed E056 factorial comparison on all E055 outgoing records."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
HISTORIES = ('acquired', 'paired_rewrite', 'independent_rewrite')
TIMES = ('early', 'late')
ARMS = ('sham', 'pulse', 'restore_signs', 'restore_magnitudes', 'erased')
INJURIES = ('intact', 'scattered', 'square')
GRAPH_FIELDS = ('edges', 'components', 'cycle_rank', 'negative_basis_cycles',
                'reachable_cells', 'reachable_output_A', 'reachable_output_B')
PRIMARY = ('sign_on_pulse_magnitudes', 'magnitude_on_pulse_signs',
           'sign_on_sham_magnitudes', 'magnitude_on_sham_signs', 'interaction')
BLOCKS = tuple(range(34000, 34032))
TECH_BLOCK = 900041
NAMES = dict(fixture='fixture_v1', benchmark='benchmark_v1', scientific='substitution_v1')


def settings(mode):
    assert mode in NAMES
    science, fixture = mode == 'scientific', mode == 'fixture'
    return dict(mode=mode, blocks=list(BLOCKS) if science else [TECH_BLOCK],
        recipients=4 if science else 2 if fixture else 1,
        read_steps=2048 if science else 24 if fixture else 512,
        settling_steps=1024 if science else 12 if fixture else 256,
        observe_steps=32 if not fixture else 4,
        dt=.2, noise=.02, birth_sd=.05, margin=.25, dtype='float64',
        normalization_floor=0., cue_birth_correlation=1., cue_noise_correlation=1.,
        histories=list(HISTORIES), times=list(TIMES), arms=list(ARMS), injuries=list(INJURIES),
        primary_history='paired_rewrite', primary_time='early', primary_injury='scattered',
        bootstrap_samples=10000, primary_family_size=5, primary_confidence=.99)
