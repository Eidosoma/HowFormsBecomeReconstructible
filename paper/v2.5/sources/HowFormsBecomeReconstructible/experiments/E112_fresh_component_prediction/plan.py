"""One prospective, stream-label-symmetric prediction on fresh source histories."""
from pathlib import Path
from E098_writer_pairing_tradeoff.plan import settings as ancestry_settings
from E111_halfway_component_cross.plan import CONDITIONS, COMPONENTS, VARIANTS, METRICS, FACTORS, EXTRA, SCOPES

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BLOCKS = tuple(range(1120000, 1120032))
TECHNICAL = (9000980, 9000981)
PRIMARY = 'gross_shared_minus_cue_delta_both'


def settings(mode):
    assert mode in ('benchmark', 'scientific')
    cfg = ancestry_settings(mode)
    blocks = list(BLOCKS if mode == 'scientific' else TECHNICAL)
    cfg.update(blocks=blocks, primary=PRIMARY, primary_group='mixture/pooled/pooled/eligible',
        primary_confidence=.95, confidence=.95, bootstrap_samples=10000,
        source_recipe='unchanged E098 fresh genealogy and E099-E105 static donor construction',
        switch_step=cfg['reader']['settling_steps'], noise_switch_step=cfg['reader']['settling_steps'],
        conditions=list(CONDITIONS), fixed_birth='O', conditions_reused={'OON':'ON', 'NNO':'NO'},
        old_stream='E077/task/E102_terminal_DRAW/0', new_stream='E106/task/terminal/draw',
        stream_labels_exchangeable=True, paired_cue_noise=True, initial_state_bounds=[-2., 2.],
        hybrid_clipping=False, eligibility='existing first safe witness has exactly four edges',
        witness_stratum_priority=[3, 1, 2, 0], longer_witnesses_retained_but_not_intervened=True,
        erased_witnesses_retained=True, all_source_blocks_retained=True,
        no_outcome_selection=True, no_sequential_testing=True, old_scientific_cases_pooled=False,
        automatic_extension=False, automatic_restart=False, automatic_successor=False,
        timing_margin=3, summary_allowance_seconds=240, conservative_resource_limit_seconds=43200)
    # These lists document the new cohort throughout the nested source recipe;
    # generation takes the explicitly supplied task ID and unchanged schedules.
    cfg['source']['blocks'] = blocks
    return cfg


def identity(row):
    return tuple(int(row[k]) for k in ('task', 'arm', 'founder', 'recipient'))


def key(row):
    return identity(row) + (int(row['draw']),)
