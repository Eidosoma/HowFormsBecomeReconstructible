"""Fixed schema and experiment constants; no dynamics or selection routines."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
HISTORIES = ('acquired', 'paired_rewrite', 'paired_preserve',
             'independent_rewrite', 'independent_preserve')
SOURCE_INDICES = (0, 4, 20, 24)
ARMS = ('untouched', 'scale_half', 'magnitude_permute', 'magnitude_equal',
        'sign_switch', 'sign_isolated', 'delete_isolated', 'delete_restore',
        'delete_returning', 'delete_other', 'erased')
INJURIES = ('intact', 'scattered', 'square')
GRAPH_FIELDS = ('edges', 'components', 'cycle_rank', 'negative_basis_cycles',
                'reachable_cells', 'reachable_output_A', 'reachable_output_B')
EXPOSURE_FIELDS = ('changed_edges', 'changed_absolute_mass', 'port_incident_edits',
                   'candidate_repair_edges', 'used_repair_edges')
PRIMARY = ((2, 0), (5, 4), (6, 0))
NAMES = dict(fixture='fixture_v1', benchmark='benchmark_v1', scientific='interventions_v1')
BLOCKS = tuple(range(34000, 34032))
TECH_BLOCK = 900041
SELECTED_CELLS = 8
BINS = 8


def settings(mode):
    assert mode in NAMES
    return dict(mode=mode, blocks=list(BLOCKS) if mode == 'scientific' else [TECH_BLOCK],
        recipients=4 if mode == 'scientific' else 2 if mode == 'fixture' else 1,
        read_steps=2048 if mode == 'scientific' else 24 if mode == 'fixture' else 128,
        settling_steps=1024 if mode == 'scientific' else 12 if mode == 'fixture' else 64,
        observe_steps=4 if mode == 'fixture' else 32,
        dt=.2, noise=.02, birth_sd=.05, margin=.25,
        histories=list(HISTORIES), arms=list(ARMS), injuries=list(INJURIES))
