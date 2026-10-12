"""Exploratory classification of saved endpoints; no new trajectories."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from common import cap_cpus, dump, sha, utc
from E015_functional_inheritance.audit import verify
from E032_renewal_failure_diagnosis.metrics import output_features, RULES
from E032_renewal_failure_diagnosis.audit import output as scalar_output
import numpy as np


def main():
    cap_cpus(1)
    source = ROOT/'E033_delayed_expression/runs/expression_v1'
    destination = Path(__file__).with_suffix('.json')
    assert not destination.exists()
    verify(source)
    summary = json.loads((source/'summary.json').read_text())
    assert summary['blocks'] == list(range(27000, 27032))
    assert summary['lineages'] == 512
    classes = []
    hashes = {str(Path(__file__).relative_to(ROOT)): sha(__file__)}
    for rel in ('E032_renewal_failure_diagnosis/metrics.py',
                'E032_renewal_failure_diagnosis/audit.py'):
        hashes[rel] = sha(ROOT/rel)
    for path in (source/'COMPLETE.json', source/'summary.json'):
        hashes[str(path.relative_to(ROOT))] = sha(path)
    for block in summary['blocks']:
        path = source/f'cases_{block:06d}.npz'
        hashes[str(path.relative_to(ROOT))] = sha(path)
        with np.load(path, allow_pickle=False) as z:
            value = z['ports'][..., 0, :].transpose(0, 1, 2, 4, 3, 5)
            vector = output_features(value, RULES[None, :, None, None])
            scalar = scalar_output(value, RULES[None, :, None, None])
            np.testing.assert_array_equal(vector, scalar)
            np.testing.assert_array_equal(vector[..., 0], z['correct'][..., 0].all(axis=3))
            assert (vector[..., :4].sum(axis=-1) == 1).all()
            classes.append(vector[..., :4].argmax(axis=-1))
    classes = np.stack(classes)
    labels = ['both_correct', 'both_reversed', 'locked_output_failure', 'other_failure']
    counts, transitions = {}, {}
    for i, (horizon, timing, receiver) in enumerate(summary['panels']):
        key = f'{horizon}/{receiver}/{timing}'
        counts[key] = {}
        for d, injury in enumerate(summary['damage']):
            n = np.bincount(classes[:, i, ..., d].ravel(), minlength=4)
            assert n.sum() == 512
            assert n[0]/512 == summary['groups'][str(horizon)][receiver][timing]['both_cues'][injury]['own']['mean']
            counts[key][injury] = dict(zip(labels, map(int, n)))
        if timing != 'original':
            original = summary['panels'].index([horizon, 'original', receiver])
            transitions[key] = {}
            for d, injury in enumerate(summary['damage']):
                pair = 4*classes[:, original, ..., d]+classes[:, i, ..., d]
                transitions[key][injury] = np.bincount(pair.ravel(), minlength=16).reshape(4, 4).tolist()
    verify(source)
    for rel, digest in hashes.items():
        assert sha(ROOT/rel) == digest
    result = dict(utc=utc(), status='EXPLORATORY_ARITHMETIC_CROSSCHECK_PASS',
                  scientific_trajectory_audit_pending_at_review=True,
                  new_trajectories=False, all_lineages_retained=512,
                  classes=labels, counts=counts, transition_rows_original_columns_intervention=transitions,
                  sources_sha256=hashes)
    dump(destination, result)
    for horizon in (8, 16):
        for timing in summary['timings']:
            key = f'{horizon}/local_strength/{timing}'
            print(key, counts[key]['scattered'])
        key = f'{horizon}/local_strength/delayed_same_duration'
        print('original-to-delayed class counts:', transitions[key]['scattered'])
    print('Saved exploratory arithmetic check:', destination)


if __name__ == '__main__':
    main()
