"""Registered P6: opposing-cue rewrite after round six, then fresh-E relays."""
from paper_relay_design import (ROOT, SOURCE, REVISION, digest, write_json, source_check,
    LOCAL_FILES as P5_FILES, execution_manifest as p5_manifest, input_paths as p5_inputs)

PREDECESSOR = ROOT / 'runs/paper-relay-20260911T150113Z-b8woml1d'
ANCESTRIES = ('ordinary_E', 'restored_E')
CONDITIONS = ('M_open', 'E_sham', 'M_write_rna', 'M_write_cut', 'no_cue',
              'M_relay_rna', 'M_relay_cut')
FIXED = dict(revision=REVISION, workers=2, worker_timeout_seconds=7200,
    total_budget_seconds=28800, historical_rounds=6, new_rounds=6,
    carriers=3, cue_cells=3, recipients=3, contact_shape=[2,3], hold_shape=[1,3],
    contact_horizon=20000, hold_horizons=[10000,10000], late_fraction=.95,
    writing_algorithms=['depol','hypol'], writing_power=60,
    relay_algorithm='depol', relay_power=60, kd=1.25e-14,
    ancestries=list(ANCESTRIES), conditions=list(CONDITIONS), gate_cases=2,
    assay_cases=4, coarse_rewrite_cases=28, fine_cases=30, planned_cases=62,
    planned_integrations=1194, planned_continuation_rounds=336,
    midway_rewriting=True, stress_panel=False, return_to_E=False,
    binary_reference='always_copy_open_route_v1')
LOCAL_FILES = P5_FILES + [ROOT/'PAPER_REWRITE_PROTOCOL.md', ROOT/'configs/paper_rewrite_v1.json'] + [
    ROOT/'scripts'/name for name in ('paper_rewrite_design.py', 'run_paper_rewrite.py',
        'analyze_paper_rewrite.py', 'run_paper_rewrite_detached.py', 'test_paper_rewrite.py')]


def fixed_cases():
    cases = [dict(id='replay__'+h, kind='replay', ancestry=h,
                  source='relay__'+h+'__open', fine=False) for h in ANCESTRIES]
    cases += [dict(id='assay__'+label+('__fine' if f else ''), kind='assay',
                   label=label, fine=f) for f in (False,True) for label in 'EM']
    cases += [dict(id=f'rewrite__{h}__{algo}__{c}'+('__fine' if f else ''),
                   kind='rewrite', ancestry=h, source='relay__'+h+'__open',
                   algorithm=algo, condition=c, fine=f)
              for f in (False,True) for h in ANCESTRIES
              for algo in ('depol','hypol') for c in CONDITIONS]
    return cases


def validate_config(config):
    if config != FIXED:
        raise ValueError('Not the registered 62-case P6 design')
    return config


def execution_manifest():
    result = p5_manifest()
    result.update({str(p.relative_to(ROOT)):digest(p) for p in LOCAL_FILES})
    return result


def input_paths():
    result = {'p5/'+n:PREDECESSOR/n for n in ('summary.json','independent_audit.json','gate.json')}
    result.update({'p5/inputs/'+n:PREDECESSOR/'inputs'/n for n in p5_inputs()})
    for h in ANCESTRIES:
        name = 'relay__'+h+'__open'
        files = ['result.json'] + [f'r{r:02d}_{part}.npz' for r in range(2,13)
                                   for part in ('contact','isolated_1','isolated_2')]
        result.update({'p5/'+name+'/'+n:PREDECESSOR/name/n for n in files})
    return result
