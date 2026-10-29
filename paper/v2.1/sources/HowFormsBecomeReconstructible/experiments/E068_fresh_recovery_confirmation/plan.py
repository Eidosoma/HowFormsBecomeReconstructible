"""New source cohort, unchanged E065 ancestry and E067 recovery requirements."""
from pathlib import Path
from E065_fresh_compatibility_confirmation.plan import settings as source_settings
from E067_ordinary_mixture_rebuilding.plan import settings as recovery_settings
from E067_ordinary_mixture_rebuilding.plan import ARMS, HORIZONS, SLOTS, PRIMARY, CONFIDENCE, index

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BLOCKS = tuple(range(40000, 40032))
TECH_BLOCK = 900041
NAMES = dict(fixture='fixture_v1', benchmark='benchmark_v1', scientific='confirmation_v1')


def settings(mode):
    cfg = recovery_settings(mode)
    source = source_settings(mode)
    cfg.update(blocks=list(BLOCKS) if mode == 'scientific' else [TECH_BLOCK],
        source_config=source['config'], source_cycle=source['source_cycle'],
        body=source['body'], source_continuation=source['continuation'],
        source_experiment='E068_fresh_generation', cohort_reused=False,
        fresh_sources=mode == 'scientific', old_observations_pooled=False,
        source_ancestry_tags=['E016', 'E022', 'E055', 'E058'], recovery_tag='E068')
    return cfg
