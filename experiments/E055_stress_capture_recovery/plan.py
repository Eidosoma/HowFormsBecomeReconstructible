"""E055 fixed design; no dynamics or outcome-dependent selection."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
HISTORIES = ('acquired', 'paired_rewrite', 'independent_rewrite')
SOURCE_INDICES = (0, 20)
ARMS = ('sham_early', 'pulse_early', 'sham_late', 'pulse_late',
        'protected_sham', 'protected_pulse', 'erased')
TIMES = ('before', 'early', 'late')
INJURIES = ('intact', 'scattered', 'square')
BLOCKS = tuple(range(34000, 34032))
TECH_BLOCK = 900041
NAMES = dict(fixture='fixture_v1', benchmark='benchmark_v1', scientific='capture_v1')
PRIMARY_HISTORY = 'independent_rewrite'
GRAPH_FIELDS = ('edges', 'components', 'cycle_rank', 'negative_basis_cycles',
                'reachable_cells', 'reachable_output_A', 'reachable_output_B')


def settings(mode):
    assert mode in NAMES
    scientific = mode == 'scientific'
    fixture = mode == 'fixture'
    return dict(mode=mode, blocks=list(BLOCKS) if scientific else [TECH_BLOCK],
        recipients=4 if scientific else 2 if fixture else 1,
        body_pre_steps=2048 if scientific else 16 if fixture else 128,
        body_settling_steps=1024 if scientific else 8 if fixture else 64,
        pulse_steps=32 if scientific else 4 if fixture else 8,
        recovery_steps=512 if scientific else 8 if fixture else 32,
        read_steps=2048 if scientific else 24 if fixture else 128,
        settling_steps=1024 if scientific else 12 if fixture else 64,
        observe_steps=32 if scientific else 4 if fixture else 8,
        pulse_sites=64, pulse_amplitude=1., dt=.2, noise=.02, birth_sd=.05,
        writer_beta=3., margin=.25, body_cue_noise_correlation=0.,
        body_cue_birth_correlation=1., pulse_cue_correlation=1.,
        assay_cue_noise_correlation=1., histories=list(HISTORIES),
        arms=list(ARMS), times=list(TIMES), injuries=list(INJURIES))
