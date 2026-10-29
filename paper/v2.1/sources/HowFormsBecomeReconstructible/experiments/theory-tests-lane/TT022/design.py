"""Fixed serial development conditions; no outcome-selected enrollment."""
from dataclasses import replace
from common import model

TAG = 'TT022_serial_capture_v1'
FAMILIES = ('common', 'residual')
POLICIES = ('ordinary', 'capture', 'held', 'fixed', 'average', 'capture_once', 'unchanged')
FUTURES = 4
GENERATIONS = 8
WORKERS = 2
PHASES = ('develop', 'fission', 'repair', 'terminal')


def configs(role):
    n = 5 if role == 'qualification' else 100 if role == 'benchmark' else 1000
    parents = 1 if role == 'qualification' else 4
    cfg = replace(model.CONFIG, replicates=parents, sweeps=n, times=(0, 1, n))
    rcfg = replace(model.READOUT, parents=parents, draws=1, sweeps=n, times=(0, 1, n))
    return cfg, rcfg


def schedule(role):
    return (1, 2) if role == 'qualification' else (2, 2) if role == 'benchmark' else (FUTURES, GENERATIONS)


def initial_name(family, policy):
    if policy == 'unchanged': return 'input__'+family
    if policy == 'ordinary': return family+'__own__live'
    suffix = {'capture': 'live', 'capture_once': 'live', 'held': 'reference_held',
              'fixed': 'fixed', 'average': 'average'}[policy]
    return f'capture__{family}__own__{suffix}'


def spec(family, policy):
    assert family in FAMILIES and policy in POLICIES
    capture = policy in ('capture', 'held', 'fixed', 'average')
    base = model.old.Spec(packet=family, body='own',
        reader='fixed' if policy in ('fixed', 'average') else 'live',
        write=policy not in ('capture_once', 'unchanged'), reference_write=policy != 'held')
    return model.Spec(base, capture)


def comparisons():
    return dict(capture_vs_ordinary=('capture', 'ordinary'),
                capture_vs_held=('capture', 'held'),
                repeated_vs_one_time=('capture', 'capture_once'),
                capture_vs_unchanged=('capture', 'unchanged'),
                fixed_vs_average=('fixed', 'average'),
                capture_vs_average=('capture', 'average'))
