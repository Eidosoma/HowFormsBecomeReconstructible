"""User-requested descriptive look; completed cohort chosen before outcome reads."""
import hashlib
import json
from pathlib import Path
import sys

DEST = Path(__file__).resolve().parent
HERE = DEST.parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from common import cap_cpus, check_inputs, dump, sha, utc
import numpy as np


def read(path):
    return json.loads(path.read_text())


def main():
    cap_cpus(1)
    output = HERE / 'runs/robustness_v1'
    assert not (DEST / 'snapshot.json').exists()
    check_inputs(output)
    manifest = read(output / 'manifest.json')
    c = manifest['contract']
    selected = list(range(36000, 36008))
    assert c['blocks'] == list(range(36000, 36032))
    assert c['mode'] == 'scientific' and c['conditions'][19] == 'noise_0/combined32'
    assert c['config']['recipients'] == 4 and c['cycle']['generations'] == 32
    records = {}
    scores = {str(h): {} for h in (0, 8, 16, 24, 32)}
    checked = 0
    for block in selected:
        receipt = output / f'worker_{block}.json'
        worker = read(receipt)
        assert worker['block'] == block and worker['generations'] == 32
        assert worker['conditions'] == 20 and worker['channel_applications'] == 33
        records[receipt.name] = sha(receipt)
        cases_path = output / f'cases_{block:06d}.npz'
        records[cases_path.name] = sha(cases_path)
        with np.load(cases_path, allow_pickle=False) as cases:
            for h in (0, 8, 16, 24, 32):
                path = output / f'assay_{block:06d}_h{h}.npz'
                records[path.name] = sha(path)
                with np.load(path, allow_pickle=False) as raw:
                    meta = json.loads(raw['__index__'].tobytes())
                    assert meta['kind'] == 'assay'
                    for key in ('panels', 'mean_ports'):
                        value = raw[key]
                        assert meta['arrays'][key] == dict(shape=list(value.shape), dtype=value.dtype.str,
                            sha256=hashlib.sha256(value.tobytes(order='C')).hexdigest())
                    panels = [tuple(v) for v in raw['panels'].tolist()]
                    means = raw['mean_ports']
                    assert means.shape == (37 if h == 0 else 36, 4, 4, 2, 3, 2)
                    desired = np.array([1., -1., 1., -1.])[None, :, None, None, None] * np.array([1., -1.])[None, None, None, :, None]
                    margin = np.minimum(desired * means[..., 0], -desired * means[..., 1])
                    correct = margin > .25
                    assert np.array_equal(correct, cases[f'assay_h{h}_correct'])
                    assert np.array_equal(margin, cases[f'assay_h{h}_margin'])
                    checked += 1
                    for n, name in enumerate(c['conditions']):
                        regime = c['regimes'][n % len(c['regimes'])]
                        native = c['readers'].index([regime['arithmetic'], regime['denominator_floor']])
                        for role, reader in (('native', native), ('common', 0)):
                            index = panels.index((n, reader))
                            for injury, j in (('intact', 0), ('scattered', 1), ('square', 2)):
                                key = f'{name}/{role}/{injury}'
                                scores[str(h)].setdefault(key, []).append(int(correct[index, :, :, :, j].all(axis=2).sum()))
    totals = {h: {key: dict(count=sum(v), denominator=128, percent=100*sum(v)/128,
                           block_counts=v) for key, v in group.items()} for h, group in scores.items()}
    snapshot = dict(status='DESCRIPTIVE_PARTIAL_NOT_INDEPENDENTLY_REPLAYED', utc=utc(),
        cohort_selected_at_utc='2026-10-10T15:55:38.495496+00:00',
        selection='All eight blocks with completed worker receipts at requested status check, before outcomes were read',
        blocks=selected, planned_blocks=c['blocks'], lineages_per_condition=128, planned_lineages_per_condition=512,
        frozen_inputs_sha256=manifest['inputs_sha256'], input_hashes_checked=True,
        source_run_manifest_sha256=sha(output / 'manifest.json'), source_sha256=records,
        analysis_sha256=sha(__file__), assay_score_arrays_recomputed=checked,
        dynamics_independently_replayed=False, confidence_intervals=None, primary_decision=None,
        stopping_or_tuning_decision=None, scientific_run_changed=False, outcomes=totals)
    dump(DEST / 'snapshot.json', snapshot)
    table = []
    for regime in c['regimes']:
        r = regime['id']
        table.append(dict(regime=r, **{p: totals['32'][f'{p}/{r}/native/scattered']['count'] for p in ('paired', 'noise_0')}))
    print(json.dumps(dict(blocks=selected, denominator=128, h32_native_scattered=table,
        independent_combined_common=totals['32']['noise_0/combined32/common/scattered'],
        independent_reference_by_horizon={h: group['noise_0/reference/native/scattered']['count'] for h, group in totals.items()},
        independent_combined_by_horizon={h: group['noise_0/combined32/native/scattered']['count'] for h, group in totals.items()},
        score_arrays_checked=checked), indent=2))


if __name__ == '__main__':
    main()
