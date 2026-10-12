"""Frozen declarative E053 matrix; no dynamics or inference."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = json.loads((HERE / 'PLAN.json').read_text())
REGIMES = tuple(PLAN['regimes'])
PAIRINGS = tuple((p['id'], p['noise_rho']) for p in PLAN['pairings'])
CONDITIONS = tuple(p + '/' + r['id'] for p, _ in PAIRINGS for r in REGIMES)
PRIMARY = tuple(PLAN['primary']['challenges'])
HORIZONS = (0, 8, 16, 24, 32)
NAMES = dict(fixture='fixture_v1', benchmark='benchmark_v1', scientific='robustness_v1')
READERS = (('float64', 0.), ('float32', 0.), ('float64', 1e-4), ('float32', 1e-4))
# Single-stress trajectories must reproduce E052 excluded trajectories exactly.
COMPAT = tuple((p * 10 + a, old_p * 11 + b) for p, old_p in ((0, 0), (1, 2))
               for a, b in ((0, 0), (1, 3), (2, 5), (3, 9), (8, 2)))
CHANNEL_COUNTS = ('available', 'nonzero_before', 'nonzero_after', 'lost_nonzero',
                  'created_from_zero', 'sign_changed', 'clipped', 'subnormal_before', 'subnormal_after',
                  'grid_lost_nonzero', 'precision_lost_nonzero')
CHANNEL_SUMS = ('absolute_error_sum', 'squared_error_sum', 'maximum_absolute_error')
CAPTURE_COUNTS = ('nonzero_contrast', 'product_underflow_to_zero',
                  'transformed_subnormal', 'contrast_subnormal', 'selected_subnormal')
DENOM_COUNTS = ('live_noninput', 'zero', 'positive', 'floored', 'subnormal')
DENOM_SUMS = ('positive_strength_sum', 'positive_attenuation_sum')
DENOM_BINS = (0., 1e-8, 1e-6, 1e-4, 1e-2, 1., float('inf'))
REPAIR_COUNTS = ('previous_tagged_edges', 'physically_surviving', 'nonzero_surviving',
                 'exposed_positive_cells', 'exposed_zero_cells')
REPAIR_SUMS = ('surviving_absolute_strength', 'exposed_relative_strength_sum')


def assay_layout(horizon):
    """Unique (record index, reader index); -1 erased, -2 unmodified source."""
    panels, mapping = [], []
    for n, name in enumerate(CONDITIONS):
        r = REGIMES[n % len(REGIMES)]
        native = READERS.index((r['arithmetic'], r['denominator_floor']))
        for label, reader in (('native', native), ('common', 0)):
            entry = (n, reader)
            if entry not in panels:
                panels.append(entry)
            mapping.append((name, label, panels.index(entry)))
    for reader in range(len(READERS)):
        panels.append((-1, reader))
    if horizon == 0:
        panels.append((-2, 0))
    return tuple(panels), tuple(mapping)
