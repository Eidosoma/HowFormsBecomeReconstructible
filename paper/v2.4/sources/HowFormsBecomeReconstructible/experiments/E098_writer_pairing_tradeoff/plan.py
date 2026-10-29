"""One rewrite: writer-input pruning crossed with writer cue-noise pairing."""
from pathlib import Path
from E081_fresh_strength_pattern.plan import settings as ancestry

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BLOCKS = tuple(range(980000, 980032))
FIXTURE = (9000982, 9000983)
BENCHMARK = (9000980, 9000981)
ARMS = ('native_sham', 'native_pulse', 'mixture_sham', 'mixture_pulse')
ENDPOINTS = dict(I0=0, P0=4, I1_paired=9, P1_paired=13,
                 I1_independent=18, P1_independent=22)
WRITERS = dict(I_paired=0, P_paired=4, I_independent=9, P_independent=13)
METRICS = ('both', 'minimum_margin', 'transfer', 'aligned_transfer')
CONTRASTS = {
    'pruning_h0': {'P0':1, 'I0':-1},
    'pruning_paired': {'P1_paired':1, 'I1_paired':-1},
    'pruning_independent': {'P1_independent':1, 'I1_independent':-1},
    'interaction': {'P1_independent':1, 'I1_independent':-1, 'P1_paired':-1, 'I1_paired':1},
    'pruned_noise_gain': {'P1_independent':1, 'P1_paired':-1},
    'intact_noise_gain': {'I1_independent':1, 'I1_paired':-1},
}
PRIMARY = ('interaction_both', 'pruned_noise_gain_both')


def settings(mode):
    assert mode in ('fixture','benchmark','scientific')
    s = ancestry(mode)
    return dict(mode=mode, blocks=list(BLOCKS if mode=='scientific' else BENCHMARK if mode=='benchmark' else FIXTURE),
        source=s, recipients=s['recipients'], config=s['config'], cycle=s['cycle'], reader=s['reader'],
        source_recipe='E077', draws=[0,1], writer_draws=1, terminal_slots=27, writer_slots=18,
        cue_noise_correlations=[1.,0.], cue_birth_correlation=1., exact_zero_fallback=True,
        terminal_cue_noise_correlation=1., normalization_floor=0., reader_dtype='float64',
        primary=list(PRIMARY), primary_confidence=.975, bootstrap_samples=10000,
        practical_reference_points=.03, fixed_scientific_blocks=32, max_workers=4,
        timing_margin=3, summary_allowance_seconds=180, conservative_resource_limit_seconds=43200,
        old_scientific_cases_pooled=False, source_selection_by_outcome=False,
        automatic_extension=False, automatic_successor=False)


def identity(row):
    return tuple(row[k] for k in ('task','arm','founder','recipient'))


def expected_identities(cfg):
    return {(b,a,f,r,d) for b in cfg['blocks'] for a in range(4) for f in range(4)
            for r in range(cfg['recipients']) for d in cfg['draws']}
