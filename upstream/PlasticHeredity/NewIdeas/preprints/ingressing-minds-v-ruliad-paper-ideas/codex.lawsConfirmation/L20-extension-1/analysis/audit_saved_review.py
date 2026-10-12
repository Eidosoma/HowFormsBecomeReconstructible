"""Independent read-only reconstruction of the saved exploratory review.

Does not import the review implementation, frozen dynamics, or any predictor.
"""
import hashlib
import json
from pathlib import Path
import numpy as np

BASE = Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1')
OUT = BASE / 'analyses/d141_heldout_late_loss_v1'
SOURCE = BASE / 'outputs/l20_extension1_heldout_v1_attempt1'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1048576):
            h.update(chunk)
    return h.hexdigest()


def pref(v, role):
    # Deliberately scalar restatement of strict qualification and all-cell denominator.
    total = 0
    for i in range(16):
        for j in range(16):
            if abs(v[i, j]) > .2:
                a, b = i < 8, j % 8 < 4
                own, other = (a, b) if role == 0 else (b, a)
                total += int((v[i, j] > 0) == own) - int((v[i, j] > 0) == other)
    return total / 256


def best(v, role):
    target = np.array([[1. if (i < 8 if role == 0 else j % 8 < 4) else -1.
                        for j in range(16)] for i in range(16)])
    sd = v.std()
    if not sd:
        return 0.
    convolution = np.fft.ifft2(np.conj(np.fft.fft2(target)) * np.fft.fft2(v-v.mean())).real
    return float(convolution.max() / (v.size * sd))


def main():
    receipt, provenance, summary, rows = [read(OUT / f'{n}.json')
        for n in ('COMPLETE', 'provenance', 'summary', 'cases')]
    for name, expected in receipt['outputs'].items():
        assert sha(OUT / name) == expected
    for name, expected in provenance['analysis_inputs'].items():
        assert sha(Path(name)) == expected
    for name, expected in provenance['source_output_sha256'].items():
        assert sha(Path(name)) == expected
    origin = BASE / 'runs/l20_extension1_heldout_v1_attempt1/COMPLETE.json'
    assert sha(origin) == provenance['source_complete_sha256']
    assert summary['primary_result_unchanged'] == read(SOURCE / 'summary.json')['primary']
    assert len(rows) == 256
    checked_bodies = checked_diagnostics = checked_shapes = 0
    for block in range(90000, 90016):
        meta = read(SOURCE / f'lineage_{block}.json')
        with np.load(SOURCE / f'lineage_{block}.npz', allow_pickle=False) as data:
            raw = {k: data[k] for k in ('generation_read_states', 'generation_write_states',
                'terminal_states', 'incoming', 'routed', 'outgoing')}
        with np.load(SOURCE / f'diagnostic_{block}.npz', allow_pickle=False) as data:
            diag = data['terminal_states']
        for row in [r for r in rows if r['block'] == block]:
            life, role, writer = row['life'], row['family'], row['writer']
            cases, probes = meta['lives'][life]['cases'], meta['lives'][life]['probes']
            ci, pi = cases.index([role, writer]), probes.index([role, writer])
            states = list(raw['generation_read_states'][life, ci, :, -1]) + [raw['terminal_states'][life, pi, -1]]
            values = [pref(s[0], role) for s in states]
            assert values == row['preference']
            checked_bodies += 4
            di = 2*role + int(writer == 'aligned')
            for branch in range(3):
                assert pref(diag[life, di, branch, -1, 0], role) == row['diagnostics'][branch]['preference']
                checked_diagnostics += 1
            fields = [raw['incoming'][life, ci, 0]] + list(raw['outgoing'][life, ci])
            correlations = [best(np.frombuffer(b.tobytes(), '<f8').reshape(16, 16), role) for b in fields]
            np.testing.assert_allclose(correlations, [r['own_best'] for r in row['records']], atol=1e-12, rtol=0)
            checked_shapes += 4
            for g in range(3):
                routed = np.frombuffer(raw['routed'][life, ci, g].tobytes(), '<f8').reshape(16, 16)
                b, c, d = (best(x, role) for x in (routed, states[g][2], raw['generation_write_states'][life, ci, g, -1, 2]))
                segment = row['phase_changes'][g]
                for key, value in zip(('routing', 'reading_reference', 'writing_reference', 'record_construction'),
                                      (b-correlations[g], c-b, d-c, correlations[g+1]-d)):
                    assert abs(segment[key] - value) < 1e-12
                checked_shapes += 3
    for name, group in summary['groups'].items():
        family, writer = name.split('_', 1)
        selected = [r for r in rows if r['family'] == ('AB'.index(family)) and r['writer'] == writer]
        assert len(selected) == 64
        for g in range(4):
            assert group['negative_preference_counts'][g] == sum(r['preference'][g] < 0 for r in selected)
            assert group['zero_preference_counts'][g] == sum(r['preference'][g] == 0 for r in selected)
            assert group['guide_non_own_counts'][g] == sum(r['stages'][g]['guide']['inferred_family'] != r['family'] for r in selected)
        assert group['negative_terminal_with_all_three_diagnostics_positive'] == sum(
            r['preference'][-1] < 0 and all(b['preference'] > 0 for b in r['diagnostics']) for r in selected)
        for key, values in group['mean_phase_changes'].items():
            np.testing.assert_allclose(values, [sum(r['phase_changes'][g][key] for r in selected)/64 for g in range(3)], atol=1e-14, rtol=0)
        for model in ('starting_only', 'passive', 'challenge'):
            e = sum((r['predictions'][model] - r['preference'][-1])**2 for r in selected)
            total = sum((r['predictions'][model] - r['preference'][-1])**2 for r in rows)
            assert abs(group['mean_squared_error'][model] - e/64) < 1e-15
            assert abs(group['share_of_all_squared_error'][model] - e/total) < 1e-14
    print(json.dumps(dict(passes=True, cases=len(rows), independent_blocks=16,
        body_preferences=checked_bodies, diagnostic_preferences=checked_diagnostics,
        independent_fft_shape_checks=checked_shapes, source_outputs=102,
        primary_unchanged=True, new_dynamics=0), indent=2))


if __name__ == '__main__':
    main()
