"""One fresh nuisance realization per archived injury, with unchanged records."""
from pathlib import Path
from E105_cycle_input_control.plan import BLOCKS,TECHNICAL,VARIANTS,METRICS,CONTRASTS,PRIMARY,SCOPES

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
PARENT=ROOT/'E105_cycle_input_control'


def settings(mode):
    assert mode in ('benchmark','scientific')
    r=4 if mode=='scientific' else 1;n=2048 if mode=='scientific' else 512
    return dict(mode=mode,blocks=list(BLOCKS if mode=='scientific' else TECHNICAL),recipients=r,
        variants=list(VARIANTS),draws=[0,1],config=dict(recipients=r,dt=.2,noise=.02,birth_sd=.05,observe_steps=32,margin=.25),
        reader=dict(read_steps=n,settling_steps=n//2),parent_run='comparison_v1' if mode=='scientific' else 'benchmark_v1',
        reader_stream='E106_fresh',fresh_stream="E106/task/terminal/draw",original_stream="E077/task/E102_terminal_DRAW/0",
        primary=PRIMARY,primary_group='mixture/pooled/pooled/eligible',confidence=.95,bootstrap_samples=10000,
        new_source_blocks=0,new_reader_nuisances=True,new_injuries=False,writer_dynamics_repeated=False,
        witness_reselection=False,source_selection=False,old_outcomes_cached=False,new_D_for_every_case=True,
        identical_packet_variants_derived=True,max_workers=4,automatic_extension=False,automatic_successor=False)
