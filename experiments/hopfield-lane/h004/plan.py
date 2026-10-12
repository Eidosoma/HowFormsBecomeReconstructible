"""Size confirmation from retained development blocks, never fresh outcomes."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import math
import numpy as np

LANE = Path(__file__).resolve().parent.parent
DEVELOPMENT = LANE / 'runs/h003_development_v1'
CONTROLS = ('foreign', 'scrambled', 'erased', 'read_off', 'write_off',
            'damaged_copy', 'writer_scrambled')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_plan():
    seals = json.loads((DEVELOPMENT / 'checksums.json').read_text())
    inputs = {}
    for name in ['summary.json', 'config.json', 'raw_sha256.json', 'audit.json']:
        actual = digest(DEVELOPMENT / name)
        if actual != seals[name]:
            raise AssertionError('Changed development input: ' + name)
        inputs[name] = actual
    summary = json.loads((DEVELOPMENT / 'summary.json').read_text())
    config = json.loads((DEVELOPMENT / 'config.json').read_text())
    if not summary['audit_passed']:
        raise AssertionError('Development integrity did not pass')
    values = np.array(summary['block_success'])
    own = summary['arms'].index('renewal')
    endpoints = {}
    for g in [8, 16]:
        c = summary['checkpoints'].index(g)
        primary = values[:, c, 2, own]
        endpoints[f'g{g}_gain4_own'] = primary
        for control in CONTROLS:
            endpoints[f'g{g}_own_minus_{control}'] = primary - values[
                :, c, 2, summary['arms'].index(control)]
        endpoints[f'g{g}_gain4_minus_baseline'] = primary - values[:, c, 0, own]
    endpoints['g16_gain4_minus_decoy'] = values[:, -1, 2, own] - values[:, -1, 3, own]
    late = []
    raw_seals = json.loads((DEVELOPMENT / 'raw_sha256.json').read_text())
    for i, seed in enumerate(config['seeds']):
        name = f'function_{seed}.npz'
        actual = digest(DEVELOPMENT / name)
        if actual != raw_seals[name]:
            raise AssertionError('Changed development block: ' + name)
        inputs[name] = actual
        with np.load(DEVELOPMENT / name) as raw:
            np.testing.assert_array_equal(raw['success'].mean(axis=(-2, -1)), values[i])
            late.append(raw['late_success'][0, own].mean())
    endpoints['g16_sustained_minus_late_gain4'] = values[:, -1, 2, own] - late
    rows = {}
    for name, points in endpoints.items():
        deviation = float(points.std(ddof=1))
        required = math.ceil((1.96 * 1.25 * deviation / .05) ** 2)
        rows[name] = dict(block_values=points.tolist(), sample_sd=deviation,
                          inflated_sd=1.25 * deviation, required_blocks=required)
    largest = max(row['required_blocks'] for row in rows.values())
    blocks = max(48, 8 * math.ceil(largest / 8))
    for row in rows.values():
        row['planned_95pct_half_width'] = 1.96 * row['inflated_sd'] / math.sqrt(blocks)
    return dict(
        experiment='H004', created_utc=datetime.now(timezone.utc).isoformat(),
        input_classification='H003 DEVELOPMENT ONLY', development_seeds=config['seeds'],
        development_input_sha256=inputs,
        target_marginal_95pct_half_width=.05, sd_inflation=1.25,
        normal_planning_multiplier=1.96, round_up_multiple=8, minimum_blocks=48,
        required_before_rounding=largest, blocks=blocks,
        seeds=list(range(14000, 14000 + blocks)), endpoints=rows,
        note='Approximate precision planning; not a power or guaranteed-coverage calculation. '
             'No confirmation outcomes used. No interim resizing.')


def main():
    result = build_plan()
    out = LANE / 'h004/SAMPLE_SIZE.json'
    with out.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({key: result[key] for key in ['blocks', 'required_before_rounding',
                                                'target_marginal_95pct_half_width']}))


if __name__ == '__main__':
    main()
