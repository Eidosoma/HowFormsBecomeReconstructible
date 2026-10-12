"""Regression of all decisions against H003, plus a primary-failure challenge."""
from pathlib import Path
import json
import sys
import numpy as np

LANE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LANE))
from h003.experiment import checksum
from h004.inference import assess


def main():
    source = LANE / 'runs/h003_development_v1'
    seals = json.loads((source / 'checksums.json').read_text())
    for name in ['summary.json', 'config.json', 'raw_sha256.json']:
        assert checksum(source / name) == seals[name], name
    original = json.loads((source / 'summary.json').read_text())
    config = json.loads((source / 'config.json').read_text())
    config.update(mode='confirmation', bootstrap_namespace='H003 whole-block bootstrap')
    raw_seals = json.loads((source / 'raw_sha256.json').read_text())
    late = []
    for seed in config['seeds']:
        path = source / f'function_{seed}.npz'
        assert checksum(path) == raw_seals[path.name], path
        with np.load(path) as raw:
            late.append(raw['late_success'].mean(axis=(-2, -1)))
    values = np.array(original['block_success'])
    late = np.array(late)
    primary, secondary, _ = assess(values, late, original['checkpoints'], original['arms'], config)
    assert primary == original['primary_qualification']
    for key, expected in original['early_intervention_contrast'].items():
        assert secondary[key] == expected, key
    checks = ['Exact H003 primary gates and all 17 statistical contrasts',
              'Exact H003 timing gates and contrast on the original bootstrap tape']
    # A strong timing difference cannot conceal failure of recipient specificity.
    fake = np.zeros_like(values)
    own = original['arms'].index('renewal')
    foreign = original['arms'].index('foreign')
    fake[:, :, 2, own] = 1.
    fake[:, :, 2, foreign] = 1.
    failed, timing, _ = assess(fake, np.zeros_like(late), original['checkpoints'], original['arms'], config)
    assert not failed['qualified']
    assert timing['numerical_gates_passed']
    assert not timing['eligible_after_primary'] and not timing['qualified']
    checks.append('Passing timing gates cannot rescue a failed primary')
    # A lost G8 benefit cannot be replaced by successful G16 performance.
    fake[:, :, 2, foreign] = 0.
    fake[:, original['checkpoints'].index(8), 2, own] = 0.
    failed, _, _ = assess(fake, np.zeros_like(late), original['checkpoints'], original['arms'], config)
    assert not failed['qualified'] and not failed['gates']['g8_completion_at_least_30pct']
    checks.append('G16 success cannot substitute for a failed G8 endpoint')
    result = dict(passed=True, checks=checks,
                  development_summary_sha256=checksum(source / 'summary.json'),
                  source_sha256={name: checksum(LANE / name) for name in
                                 ['h004/check_inference.py', 'h004/inference.py', 'h004/analysis.py']})
    with (LANE / 'h004/INFERENCE_CHECK.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
