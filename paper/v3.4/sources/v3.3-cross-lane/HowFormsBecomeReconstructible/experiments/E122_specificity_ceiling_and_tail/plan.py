"""Frozen scientific choices for the E014 continuation."""
from dataclasses import asdict, replace
from pathlib import Path
from E006_compact_renewal import run as compact

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / 'E014_long_renewal/runs/confirmation_v2'
BENCH_SOURCE = ROOT / 'E014_long_renewal/runs/benchmark_v1'
BLOCKS = tuple(range(12000, 12064))
BENCHMARK = 900014
FACTORS = (1, 4)
OLD = (1, 3, 8, 16)
CHECKPOINTS = OLD + (32, 64, 128, 256)
AUDIT_GENERATIONS = (17, 32, 64, 128, 256)
ROUTES = ('own', 'foreign', 'protected_own', 'protected_foreign')
CFG = replace(compact.CFG, generations=256)

def settings(mode):
    assert mode in ('benchmark', 'scientific')
    return dict(experiment='E122', mode=mode,
        blocks=list(BLOCKS) if mode == 'scientific' else [BENCHMARK],
        factors=list(FACTORS), checkpoints=list(CHECKPOINTS),
        continuation_start=17, continuation_end=256, config=asdict(CFG),
        audit_generations=list(AUDIT_GENERATIONS), routes=list(ROUTES),
        bootstrap_samples=10000, fit_bootstrap_samples=2000,
        late_equivalence_margin=.0025, primary_factor=4, primary_horizon=256,
        fit_train_horizons=[1,3,8,16,32,64], fit_test_horizons=[128,256],
        fit_tau_bounds=[.25,65536.], fit_tau_points=257,
        power_tau_points=129, power_p_bounds=[1/32,8.], power_p_points=65,
        fit_C_bounds=[-1.,1.], fit_A_bounds=[-2.,2.],
        protected_reference_is_capacity_bound=False, new_decoder_fitting=False,
        automatic_extension=False, automatic_successor=False)
