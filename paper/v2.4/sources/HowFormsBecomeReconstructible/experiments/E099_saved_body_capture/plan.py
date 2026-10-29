"""Selected capture on E098 bodies; new readers, no new source dynamics."""
from pathlib import Path
from E098_writer_pairing_tradeoff.plan import settings as previous

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PARENT = ROOT/'E098_writer_pairing_tradeoff'
BLOCKS = tuple(range(980000,980032))
TECHNICAL = (9000980,9000981)
METRICS = ('both','minimum_margin','transfer','aligned_transfer')
STARTS = dict(I_pair_H=0,P_pair_H=4,I_ind_H=9,P_ind_H=13,
              I_pair_O=18,P_pair_O=4,I_ind_O=22,P_ind_O=26,P_ind_S=30,P_ind_M=34)
OLD = dict(I0=0,P0=4,I1_paired=9,P1_paired=13,I1_independent=18,P1_independent=22)
CONTRASTS = {
    'filter_pruned': {'P_ind_H':1,'P_ind_O':-1},
    'noise_pruned_H': {'P_ind_H':1,'P_pair_H':-1},
    'noise_pruned_O': {'P_ind_O':1,'P_pair_O':-1},
    'filter_intact_ind': {'I_ind_H':1,'I_ind_O':-1},
    'filter_intact_pair': {'I_pair_H':1,'I_pair_O':-1},
    'filter_pruned_pair': {'P_pair_H':1,'P_pair_O':-1},
    'sign_at_O_magnitude': {'P_ind_S':1,'P_ind_O':-1},
    'sign_at_H_magnitude': {'P_ind_H':1,'P_ind_M':-1},
    'magnitude_at_O_sign': {'P_ind_M':1,'P_ind_O':-1},
    'magnitude_at_H_sign': {'P_ind_H':1,'P_ind_S':-1},
    'component_interaction': {'P_ind_H':1,'P_ind_M':-1,'P_ind_S':-1,'P_ind_O':1},
    'prune_pair_H': {'P_pair_H':1,'I_pair_H':-1},
    'prune_ind_H': {'P_ind_H':1,'I_ind_H':-1},
    'prune_pair_O': {'P_pair_O':1,'I_pair_O':-1},
    'prune_ind_O': {'P_ind_O':1,'I_ind_O':-1},
    'noise_intact_H': {'I_ind_H':1,'I_pair_H':-1},
    'noise_intact_O': {'I_ind_O':1,'I_pair_O':-1},
    'prune_noise_interaction_H': {'P_ind_H':1,'I_ind_H':-1,'P_pair_H':-1,'I_pair_H':1},
    'prune_noise_interaction_O': {'P_ind_O':1,'I_ind_O':-1,'P_pair_O':-1,'I_pair_O':1},
}
INTERACTIONS = ('component_interaction','prune_noise_interaction_H','prune_noise_interaction_O')
PRIMARY = ('filter_pruned_both','noise_pruned_H_both')


def settings(mode):
    assert mode in ('fixture','benchmark','scientific')
    parent_mode = 'scientific' if mode=='scientific' else 'benchmark'
    old = previous(parent_mode)
    config = dict(old['config']); reader = dict(old['reader'])
    if mode=='fixture':
        config['observe_steps']=4
        reader.update(read_steps=24,settling_steps=12)
    return dict(mode=mode,blocks=list(BLOCKS if mode=='scientific' else TECHNICAL),
        parent_mode=parent_mode,recipients=old['recipients'],config=config,reader=reader,
        draws=[0,1],slots=38,variants=list(STARTS),primary=list(PRIMARY),primary_confidence=.975,
        secondary_confidence=.95,bootstrap_samples=10000,max_workers=4,timing_margin=3,
        summary_allowance_seconds=180,conservative_resource_limit_seconds=21600,
        new_source_blocks=0,source_selection=False,writer_dynamics_repeated=False,
        previous_outcomes_known=True,new_terminal_stream_phase='E099_terminal_DRAW',
        paired_cue_noise=True,paired_cue_birth=True,normalization_floor=0.,dtype='float64',
        support_mismatch='stop_preserve_all_cases_no_replacement',
        legacy_endpoints='historical_context_only_no_new_minus_old_inference',
        practical_reference_points=.03,automatic_extension=False,automatic_successor=False)


def identity(row):
    return tuple(row[k] for k in ('task','arm','founder','recipient'))


def expected_identities(cfg):
    return {(b,a,f,r,d) for b in cfg['blocks'] for a in range(4) for f in range(4)
            for r in range(cfg['recipients']) for d in cfg['draws']}


def references():
    natural = list(range(18))+list(range(4))+list(range(9,13))+list(range(13,17))*3
    ordinary = list(range(18,22))+list(range(4,9))+list(range(22,26))+list(range(26,30))+[17]
    ordinary += list(range(18,30))+list(range(26,30))*2
    assert len(natural)==len(ordinary)==38
    return natural,ordinary
