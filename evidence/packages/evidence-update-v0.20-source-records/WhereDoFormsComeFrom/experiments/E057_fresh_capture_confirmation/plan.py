"""Frozen fresh cohort and confirmatory family; predecessor settings unchanged."""
from dataclasses import asdict, replace
from pathlib import Path
from E015_functional_inheritance.model import Config
from E055_stress_capture_recovery.plan import settings as body_settings
from E056_sign_magnitude_substitution.plan import settings as reader_settings

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BLOCKS = tuple(range(38000, 38032))
TECH_BLOCK = 900041
NAMES = dict(fixture='fixture_v1', benchmark='benchmark_v1', scientific='confirmation_v1')
HISTORIES = ('acquired', 'paired_rewrite', 'independent_rewrite')
PRIMARY = ('early_pulse_loss', 'timing_benefit', 'magnitude_on_pulse_signs', 'magnitude_on_sham_signs')
PRIMARY_CONFIDENCE = .9875


def settings(mode):
    assert mode in NAMES
    cfg = Config()
    cycle = dict(generations=32, read_steps=2048, settling_steps=1024, write_steps=128)
    if mode == 'fixture':
        cfg = replace(cfg, recipients=2, teach_steps=12, capture_steps=6, observe_steps=4)
        cycle.update(read_steps=24, settling_steps=12, write_steps=8)
    elif mode == 'benchmark':
        cfg = replace(cfg, recipients=1)
        cycle.update(read_steps=128, settling_steps=64)
    body = body_settings(mode)
    body = {k: body[k] for k in ('recipients','body_pre_steps','body_settling_steps','pulse_steps',
        'recovery_steps','observe_steps','pulse_sites','pulse_amplitude','dt','noise','birth_sd','writer_beta','margin')}
    reader = reader_settings(mode)
    reader = {k: reader[k] for k in ('recipients','read_steps','settling_steps','observe_steps',
        'dt','noise','birth_sd','margin','dtype','normalization_floor','cue_birth_correlation','cue_noise_correlation')}
    return dict(mode=mode, blocks=list(BLOCKS) if mode=='scientific' else [TECH_BLOCK],
        config=asdict(cfg), cycle=cycle, body=body, reader=reader, histories=list(HISTORIES),
        primary=list(PRIMARY), primary_confidence=PRIMARY_CONFIDENCE, primary_family_size=4,
        bootstrap_samples=10000, fresh_sources=mode=='scientific', prior_cases_pooled=False)
