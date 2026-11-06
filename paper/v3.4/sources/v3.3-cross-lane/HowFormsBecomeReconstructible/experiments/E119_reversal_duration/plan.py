"""Reviewer-priority duration and transport studies; no outcome-adaptive scope."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = dict(duration='E119_reversal_duration', transport='E120_writer_regime_transport',
                   histories='E121_native_regime_histories')
REGIMES = ('matched_exact', 'matched_tolerant', 'independent_exact', 'independent_tolerant')

def settings(study, mode):
    assert study in DIRECTORIES and mode in ('benchmark', 'scientific')
    science = mode == 'scientific'
    blocks = list(range(1210000,1210032) if study == 'histories' else range(41000,41032)) if science else [900041]
    return dict(study=study, mode=mode, blocks=blocks, recipients=4,
        config=dict(recipients=4, dt=.2, noise=.02, birth_sd=.05, writer_beta=3.,
                    observe_steps=32, margin=.25),
        steps=dict(read_steps=2048 if science else 128, settling_steps=1024 if science else 64),
        regimes=list(REGIMES), generations=4 if study=='duration' else 1,
        ancestry_generations=32, continuation_generations=3, acquisition_steps=512,
        acquisition_capture_steps=128, pulse_steps=32 if science else 8,
        pulse_amplitude=1., pulse_sites=64, draws=[0,1], tolerance=1e-4,
        reset_correlation=1., normalization_floor=0., arithmetic='float64', storage='float64',
        quantization_grid=0., success_floor=.5, retention_allowance=.05,
        equivalence_margin=.03, bootstrap_samples=10000, confidence=.95,
        all_sources_retained=True, independent_terminal_draws=True,
        terminal_draws_matched_across_treatments_and_horizons=True,
        assessment_feedback=False, prune_once=True, transmit_after_failure=True,
        max_workers=2, shared_cpu_ceiling=12, timing_margin=3.,
        conservative_resource_limit_seconds=172800,
        automatic_extension=False, automatic_restart=False, automatic_successor=False)

def here(study): return ROOT / DIRECTORIES[study]

def regime_parameters(name):
    return dict(independent=name.startswith('independent'),
                tolerance=1e-4 if name.endswith('tolerant') else 0.)
