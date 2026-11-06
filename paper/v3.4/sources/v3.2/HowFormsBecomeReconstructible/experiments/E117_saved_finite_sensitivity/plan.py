"""Bounded saved-data diagnosis; no new trajectories or threshold search."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
PARENT=ROOT/'E116_finite_resolution_pruning'
BLOCKS=tuple(range(1120000,1120032))
TECHNICAL=(9000980,9000981)
REGIMES=tuple(f'T{t}F{f}Q{q}' for t in (0,1) for f in (0,1) for q in (0,1))
EDGE_REGIONS=('selected','outside','all')
CELL_REGIONS=('selected_vertices','ring','remote','outputs','cue','free')
EDGE_METRICS=('available','reference_edges','current_edges','lost_edges','gained_edges','sign_changes',
    'reference_mass','current_mass','lost_reference_mass','weight_l1',
    'reference_coupling_mass','current_coupling_mass','lost_reference_coupling','coupling_l1')
CELL_METRICS=('cells','reference_zero','current_zero','reference_weak','current_weak','newly_isolated',
    'reference_denominator_sum','current_denominator_sum','floor_attenuation_sum','coupling_l1')
ENDPOINTS=('I0','P0','I1','P1','I1_common','P1_common')
FEATURES=('reference_weak_fraction','current_weak_fraction','newly_isolated_fraction',
    'floor_attenuation_mean','coupling_l1_per_cell','grid_lost_edge_fraction',
    'lost_raw_mass_fraction','lost_normalized_mass_fraction','selected_lost_coupling_fraction',
    'outside_lost_coupling_fraction','selected_coupling_change_fraction','output_coupling_change_fraction')
COPY_NAMES=('cases.csv','events.csv','erased.csv','summary.json','source_original_cases.csv',
    'source_original_events.csv','source_original_two_draw_means.csv','source_erased_controls.csv','source_summary.json')

def settings(mode):
    assert mode in ('benchmark','scientific')
    return dict(mode=mode,blocks=list(BLOCKS if mode=='scientific' else TECHNICAL),recipients=4,
        source_run='finite_v1' if mode=='scientific' else 'benchmark_v1',regimes=list(REGIMES),
        edge_regions=list(EDGE_REGIONS),cell_regions=list(CELL_REGIONS),edge_metrics=list(EDGE_METRICS),
        cell_metrics=list(CELL_METRICS),features=list(FEATURES),denominator_threshold=1e-4,grid_step=2**-16,
        readers=['native','common'],draws=[0,1],workers=1,bootstrap_samples=10000,confidence=.95,
        bootstrap_seed=['E117','saved_finite_sensitivity'],no_new_dynamics=True,new_source_blocks=0,
        outcomes_already_known=True,exploratory=True,primary_test=None,all_sources_retained=True,
        outcome_selection=False,threshold_sweep=False,prediction_fitting=False,causal_mediation_claim=False,
        empty_ratios='null, with explicit denominators; zero-denominator bootstrap resamples excluded and counted',
        measurements_fixed_before_scientific_extraction=True,automatic_restart=False,automatic_extension=False,
        automatic_successor=False,shared_cpu_ceiling=12)

def identity(row):return tuple(int(row[k]) for k in ('task','arm','founder','recipient','draw'))
def key(row):return identity(row)+(row['regime'],)

def panels():
    return ([f'h0F{f}Q{q}' for f in (0,1) for q in (0,1)]+['h1'+r for r in REGIMES]+
            [f'commonT{t}F1Q{q}' for t in (0,1) for q in (0,1)])

def indices(regime):
    t,f,q=(int(regime[n]) for n in (1,3,5))
    return 2*f+q,4+4*t+2*f+q,12+2*t+q if f else 4+4*t+q
