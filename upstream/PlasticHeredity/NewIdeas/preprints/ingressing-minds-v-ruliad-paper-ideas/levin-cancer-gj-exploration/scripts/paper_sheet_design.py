"""Fixed P3 sheet design and provenance; no native integration."""
from paper_restoration_design import (ROOT, SOURCE, REVISION, digest, write_json,
    source_check, LOCAL_FILES as P2_FILES, execution_manifest as p2_manifest)

PREDECESSOR = ROOT / 'runs/paper-restoration-20260909T152245Z-sr2a__1z'
PILOT = ROOT / 'runs/pilot-20260905T232334Z-uw_m4g5f/benchmark_625'
STRATEGIES = {'neither': ('depol',60), 'voltage': ('hypol',60),
              'expression': ('depol',1), 'both': ('hypol',1)}
FINE_BANKS = [('depol','edge'),('nbrDepol','centre'),('hypol','edge')]
FIXED = dict(revision=REVISION,workers=2,worker_timeout_seconds=7200,
    total_budget_seconds=57600,field_shape=[13,13],source_side=4,sample_side=3,
    patch_sides=[2,3],histories=['depol','nbrDepol','hypol'],locations=['edge','centre'],
    acquisition_power=60,acquisition_kd=8.801117367933935e-16,restoration_kd=1.25e-14,
    preparation_horizon=1000,contact_horizon=20000,hold_horizons=[10000,10000],
    probe_shape=[2,2],probe_carriers=3,probe_recipients=1,late_fraction=.95,
    planned_cases=85,planned_integrations=465)
PILOT_CASE = dict(id='benchmark_625',kind='isolation',strategy='none',kd=1.25e-14,
                  dimensions=[1,25,25],expected_fixed=True)
LOCAL_FILES = P2_FILES + [ROOT/'PAPER_SHEET_PROTOCOL.md', ROOT/'configs/paper_sheet_v1.json',
    ROOT/'PILOT_PROTOCOL.md',ROOT/'configs/pilot_v1.json',ROOT/'scripts/run_pilot.py'] + [
    ROOT/'scripts'/n for n in ('paper_sheet_design.py','run_paper_sheet.py',
        'analyze_paper_sheet.py','run_paper_sheet_detached.py','test_paper_sheet.py')]


def bank_id(history,location,blocked=False,fine=False):
    return f'bank__{history}__{location}'+('__blocked' if blocked else '')+('__fine' if fine else '')


def fixed_cases():
    result=[dict(id='reference',kind='reference',fine=False),
            dict(id='benchmark_625',kind='benchmark',fine=False)]
    result += [dict(id='assay__'+label,kind='assay',label=label,fine=False) for label in ('E','M')]
    for blocked,fine,settings in ((False,False,[(a,l) for a in FIXED['histories'] for l in FIXED['locations']]),
            (True,False,[(a,l) for a in FIXED['histories'] for l in FIXED['locations']]),
            (False,True,FINE_BANKS)):
        for history,location in settings:
            result.append(dict(id=bank_id(history,location,blocked,fine),kind='bank',
                history=history,location=location,blocked=blocked,fine=fine))
    def add(history,location,side,strategy,kind='main',fine=False):
        result.append(dict(id=f'{kind}__{history}__{location}__s{side}__{strategy}'+('__fine' if fine else ''),
            kind=kind,history=history,location=location,side=side,strategy=strategy,
            bank=bank_id(history,location,fine=fine),fine=fine))
    for a in FIXED['histories']:
        for l in FIXED['locations']:
            for side in (2,3):
                for strategy in STRATEGIES: add(a,l,side,strategy)
    for kind,strategy in (('blocked','both'),('alone','neither')):
        for a in FIXED['histories']:
            for l in FIXED['locations']: add(a,l,3,strategy,kind)
    for a,l in FINE_BANKS:
        for side in (2,3): add(a,l,side,'both',fine=True)
    return result


def validate_config(config):
    if config!=FIXED: raise ValueError('Not the registered 85-case P3 design')
    return config


def block(row,col,side,cols=13):
    return [(row+r)*cols+col+c for r in range(side) for c in range(side)]


def origins(location):
    return ((0,1),(0,5),(0,5)) if location=='edge' else ((4,1),(4,5),(5,5))


def original_ids():
    return [f'original:r{r:02d}:c{c:02d}' for r in range(13) for c in range(13)]


def execution_manifest():
    result=p2_manifest()
    result.update({str(p.relative_to(ROOT)):digest(p) for p in LOCAL_FILES})
    return result


def input_paths():
    result={'p2/'+n:PREDECESSOR/n for n in ('summary.json','independent_audit.json','gate.json')}
    result.update({'pilot/'+n:PILOT/n for n in ('result.json','endpoints.npz','trajectory-0.npz','trajectory-1.npz')})
    return result
