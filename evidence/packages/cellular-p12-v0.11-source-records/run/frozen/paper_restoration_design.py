"""Registered P2 choices; no integration or source mutation."""
import json
from pathlib import Path

from paper_memory_design import (ROOT, REVISION, SOURCE, digest, write_json,
    source_check, LOCAL_FILES as P1_FILES, execution_manifest as p1_manifest)

PREDECESSOR = ROOT / 'runs/paper-memory-20260909T094809Z-yna2d02r'
PRIMARY = 'bridge__depol__s6__p60'
REPLAYS = (PRIMARY, 'bridge__depol__s6__p8', 'bridge__hypol__s11__p60',
           'bridge__nbrDepol__s11__p8')
STRATEGIES = {'neither': ('depol', 60), 'voltage': ('hypol', 60),
              'expression': ('depol', 1), 'both': ('hypol', 1)}
FIXED = dict(revision=REVISION, predecessor=str(PREDECESSOR.relative_to(ROOT)),
    primary=PRIMARY, workers=2, worker_timeout_seconds=5400,
    total_budget_seconds=28800, gate_cases=6, patch_sizes=[2,6,11],
    kd_values=[1.25e-14,2e-13], contact_horizon=20000, hold_horizons=[10000,10000],
    probe_kd=1.25e-14, field_cells=25, late_fraction=.95)
LOCAL_FILES = P1_FILES + [ROOT / 'PAPER_RESTORATION_PROTOCOL.md',
    ROOT / 'configs/paper_restoration_v1.json'] + [ROOT / 'scripts' / n for n in (
        'paper_restoration_design.py','run_paper_restoration.py',
        'analyze_paper_restoration.py','run_paper_restoration_detached.py',
        'test_paper_restoration.py')]


def fixed_cases():
    cases = [dict(id='replay__'+s, kind='replay', source=s, fine=False) for s in REPLAYS]
    cases += [dict(id='assay__'+label,kind='assay',label=label,source=PRIMARY,fine=False) for label in ('E','M')]
    def add(size,kd,strategy,kind='factorial',oi=.5,blocked=False,alone=False,fine=False):
        c = dict(id=f'{kind}__s{size}__k{0 if kd==1.25e-14 else 1}__{strategy}'+('__fine' if fine else ''),
            kind=kind,source=PRIMARY,size=size,kd=kd,strategy=strategy,
            algorithm=STRATEGIES[strategy][0],power=STRATEGIES[strategy][1],
            oi=oi,mirna_blocked=blocked,alone=alone,fine=fine)
        cases.append(c)
    for size in (2,6,11):
        for kd in (1.25e-14,2e-13):
            for strategy in STRATEGIES:
                add(size,kd,strategy)
    for size in (2,6,11):
        for strategy in ('neither','voltage'):
            add(size,1.25e-14,strategy,'border',oi=0)
    for strategy in STRATEGIES:
        add(6,1.25e-14,strategy,'blocked',blocked=True)
    for strategy in ('neither','voltage'):
        add(6,1.25e-14,strategy,'alone',alone=True)
    for kd,strategies in ((1.25e-14,tuple(STRATEGIES)),(2e-13,('neither','both'))):
        for strategy in strategies:
            add(6,kd,strategy,fine=True)
    return cases


def validate_config(config):
    if config != dict(FIXED,cases=fixed_cases()):
        raise ValueError('Not the registered 48-case P2 design')
    return config


def execution_manifest():
    result = p1_manifest()
    result.update({str(p.relative_to(ROOT)):digest(p) for p in LOCAL_FILES})
    return result


def input_paths():
    paths = {n: PREDECESSOR / n for n in ('summary.json','independent_audit.json','benchmark_gate.json')}
    for s in REPLAYS:
        for n in ('result.json','preparation.npz','isolated_2.npz','onward_contact.npz',
                  'onward_isolated_1.npz','onward_isolated_2.npz'):
            paths[s+'/'+n] = PREDECESSOR / s / n
    return paths


def source_data(inputs, name):
    import numpy as np
    folder = Path(inputs) / name
    result = json.loads((folder / 'result.json').read_text())
    with np.load(folder / 'isolated_2.npz',allow_pickle=False) as a:
        held = a['final'].copy()
    with np.load(folder / 'preparation.npz',allow_pickle=False) as a:
        prepared, bath = a['concentrations'][-1].copy(), a['environment'].copy()
    size = result['case']['tumor_size']
    ids = next(r['setup']['cell_ids'] for r in result['phases'] if r['phase']=='isolated_2')
    return dict(held=held, prepared=prepared, E=prepared[:,size:size+1],
        M=prepared[:,:1], ids=ids, result=result, bath=bath)
