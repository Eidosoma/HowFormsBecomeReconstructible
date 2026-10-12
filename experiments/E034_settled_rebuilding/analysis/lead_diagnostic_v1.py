"""Exploratory saved-endpoint and copied-coordinate review; no new dynamics."""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from common import cap_cpus, dump, sha, utc
from E015_functional_inheritance.audit import verify, unpack
from E031_renewal_durability.audit import load_compact
from E032_renewal_failure_diagnosis.metrics import output_features, RULES
from E032_renewal_failure_diagnosis.audit import output as scalar_output
import numpy as np


def main():
    cap_cpus(1)
    source = ROOT/'E034_settled_rebuilding/runs/rebuilding_v1'
    destination = Path(__file__).with_suffix('.json')
    assert not destination.exists()
    verify(source)
    audit = json.loads((source/'INDEPENDENT_AUDIT.json').read_text())
    assert audit['status'] == 'PASS' and audit['complete_sha256'] == sha(source/'COMPLETE.json')
    summary = json.loads((source/'summary.json').read_text())
    assert summary['blocks'] == list(range(27000, 27032))
    hashes = {str(Path(__file__).relative_to(ROOT)): sha(__file__)}
    for rel in ('E032_renewal_failure_diagnosis/metrics.py', 'E032_renewal_failure_diagnosis/audit.py',
                'E031_renewal_durability/audit.py', 'E015_functional_inheritance/audit.py'):
        hashes[rel] = sha(ROOT/rel)
    for name in ('COMPLETE.json', 'INDEPENDENT_AUDIT.json', 'summary.json'):
        p = source/name; hashes[str(p.relative_to(ROOT))] = sha(p)
    terminal, body, packet = [], [], []
    for block in summary['blocks']:
        paths = [source/f'cases_{block:06d}.npz', source/f'boundary_{block:06d}.npz']
        for p in paths: hashes[str(p.relative_to(ROOT))] = sha(p)
        with np.load(paths[0], allow_pickle=False) as z:
            v = z['ports'][..., 0, :].transpose(0, 1, 2, 4, 3, 5)
            ft = output_features(v, RULES[None, :, None, None])
            np.testing.assert_array_equal(ft, scalar_output(v, RULES[None, :, None, None]))
            np.testing.assert_array_equal(ft[..., 0], z['correct'][..., 0].all(axis=3))
            fb = output_features(z['body_ports'], RULES[None, :, None])
            np.testing.assert_array_equal(fb, scalar_output(z['body_ports'], RULES[None, :, None]))
            np.testing.assert_array_equal(fb[..., 0], z['body_correct'].all(axis=3))
            terminal.append(ft[..., :4].argmax(axis=-1)); body.append(fb[..., :4].argmax(axis=-1))
        raw = load_compact(paths[1], 'boundary')
        held, eligible = raw['retained_edges'][0], raw['eligible_edges'][0]
        np.testing.assert_array_equal(held, raw['retained_edges'][1])
        np.testing.assert_array_equal(eligible, raw['eligible_edges'][1])
        w = unpack(raw['outgoing'])
        changed = w[0] != w[1]
        assert not (changed & held).any() and not (changed & ~eligible).any()
        count = lambda a: a.sum(axis=(-3, -2, -1))
        vector = np.stack((count(held), count(eligible), count(changed)), axis=-1)
        scalar = np.empty_like(vector)
        for f in range(4):
            for r in range(w.shape[2]):
                scalar[f, r] = [sum(bool(x) for x in a[f, r].ravel()) for a in (held, eligible, changed)]
        np.testing.assert_array_equal(vector, scalar)
        packet.append(vector)
    terminal, body, packet = map(np.stack, (terminal, body, packet))
    labels = ['both_correct', 'both_reversed', 'locked_output_failure', 'other_failure']
    def counts(a):
        n = np.bincount(a.ravel(), minlength=4)
        assert n.sum() == 512
        return dict(zip(labels, map(int, n)))
    tc = {}
    for i, (t, r, c) in enumerate(summary['panels']):
        tc[f'{t}/{r}/{c}'] = {}
        for d, injury in enumerate(summary['damage']):
            n = counts(terminal[:, i, ..., d])
            assert n['both_correct']/512 == summary['groups'][t][r][c]['both_cues'][injury]['own']['mean']
            tc[f'{t}/{r}/{c}'][injury] = n
    bc = {name:counts(body[:, i]) for i, name in enumerate(summary['conditions'])}
    for c in summary['conditions']:
        assert bc[c]['both_correct']/512 == summary['body'][c]['both_cues']['mean']
    def transitions(a, b):
        vector = np.bincount((4*a+b).ravel(), minlength=16).reshape(4, 4)
        scalar = np.zeros((4, 4), int)
        for x, y in zip(a.ravel(), b.ravel()): scalar[int(x), int(y)] += 1
        np.testing.assert_array_equal(vector, scalar)
        return vector.tolist()
    pstats = {name:dict(mean_per_lineage=float(packet[..., i].mean()),
                       block_means=packet[..., i].mean(axis=(1, 2)).tolist(),
                       total=int(packet[..., i].sum()))
              for i, name in enumerate(('copied_strong', 'eligible_to_refresh', 'changed_by_delayed_renewal'))}
    pstats['fraction_of_available_edges_copied'] = float(packet[..., 0].sum()/packet[..., :2].sum())
    result = dict(status='EXPLORATORY_ARITHMETIC_CROSSCHECK_PASS', utc=utc(), new_trajectories=False,
        lineages=512, labels=labels, terminal_counts=tc, body_counts=bc, packet_statistics=pstats,
        body_transition_rows_original_columns_delayed=transitions(body[:, 0], body[:, 1]),
        focal_terminal_transition_rows_original_columns_delayed=transitions(terminal[:, 6, ..., 1], terminal[:, 7, ..., 1]),
        sources_sha256=hashes, causal_bottleneck_identified=False)
    verify(source)
    for rel, digest in hashes.items(): assert sha(ROOT/rel) == digest
    dump(destination, result)
    print('Body classes:', bc)
    print('Common delayed normalized scattered terminal:')
    for c in summary['conditions']: print(c, tc[f'delayed/local_strength/{c}']['scattered'])
    print('Terminal transitions:', result['focal_terminal_transition_rows_original_columns_delayed'])
    print('Body transitions:', result['body_transition_rows_original_columns_delayed'])
    print('Packet means:', {k:v['mean_per_lineage'] for k,v in pstats.items() if isinstance(v,dict)})
    print('Available fraction copied:', pstats['fraction_of_available_edges_copied'])
    print('Saved:', destination)


if __name__ == '__main__':
    main()
