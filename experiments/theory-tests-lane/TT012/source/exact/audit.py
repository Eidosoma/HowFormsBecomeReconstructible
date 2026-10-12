"""Saved-record exact-alignment audit. No native task-success data are read."""
import csv
from collections import Counter
import numpy as np
from common import ROOT, arrays, read, save_arrays, sha, stamp, write
from reader import PORTS, decode, available
from alignment import align, ambiguity, equivalent, grid_edges, hybrid, parity

PINS = np.flatnonzero(PORTS.any(axis=0).ravel())
SOURCE = ROOT.parent/'p05_backup_task_swap_v0_1/runs/pilot_v1'


def sources():
    bindings = read(ROOT/'SOURCE_BINDINGS.json')['bindings']
    for name, item in bindings.items():
        assert sha(item['source']) == item['sha256']
        if name.endswith('.py'):
            assert sha(ROOT/name) == item['sha256']
    receipt = read(SOURCE/'inputs/prepared/COMPLETE.json')
    return receipt


def balance(weights):
    u, v = grid_edges(); support = weights.ravel() != 0
    return parity(256, u[support], v[support], np.signbit(weights.ravel()[support]))['ok']


def run():
    receipt = sources()
    destination = ROOT/'results_v1'
    destination.mkdir(exist_ok=False)
    write(destination/'START.json', dict(at_utc=stamp(), status='DEVELOPMENT_STATIC_AUDIT',
        files_sha256={p.name:sha(p) for p in sorted(ROOT.iterdir()) if p.is_file()},
        source_prepared_sha256=sha(SOURCE/'inputs/prepared/COMPLETE.json')))
    rows = []; certificates = []; comparisons = []; evidence = {}; bound = {}
    u, v = grid_edges()
    for block in range(34000, 34008):
        name = f'cases_{block:06d}.npz'
        expected = receipt['outputs_sha256'][name]
        data = arrays(SOURCE/'inputs/prepared'/name, expected)
        bound[name] = expected
        # Only O and D enter align(). I and previous hybrid signs are not inputs.
        outgoing_panel = decode(data['packets'][:,1])
        donor_panel = decode(data['donor_packets'])
        for case, outgoing in enumerate(outgoing_panel):
            original_available = available(data['original_masks'][case])
            assert not outgoing[~original_available].any()
            common = data['common_edges'][case]
            assert not common[original_available].any()
            pair_alignments = []
            for donor_index, donor in enumerate(donor_panel[case]):
                result = align(outgoing, donor, PINS)
                pair_alignments.append(result)
            # Alignment is complete before retrieving any missing own signs.
            incoming = decode(data['packets'][case,0])
            own = decode(data['packets'][case,3])
            assert np.array_equal(abs(own[common]), abs(incoming[common]))
            aligned = []
            for donor_index, (donor, result) in enumerate(zip(donor_panel[case], pair_alignments)):
                key = f'b{block}_c{case}_d{donor_index}'
                plain, pinned = result['unpinned'], result['pinned']
                overlap = result['overlap']
                row = dict(block=block, case=case, history=int(data['histories'][case]),
                    founder=int(data['founders'][case]), recipient=int(data['recipients'][case]),
                    donor='same_task' if donor_index==0 else 'opposite_task',
                    overlap_edges=int(overlap.sum()), kept_edges=int(np.count_nonzero(outgoing)),
                    common_edges=int(common.sum()),
                    unpinned_ok=bool(plain['ok']), pinned_ok=bool(pinned['ok']),
                    obstruction='none' if pinned['ok'] else ('cycle' if not plain['ok'] else 'port'),
                    unpinned_free_bits=len(plain['free_components']),
                    pinned_free_bits=len(pinned['free_components']) if pinned['ok'] else None,
                    ambiguity_dimension=None, own_equivalent=None,
                    outgoing_balanced=bool(balance(outgoing)), donor_balanced=bool(balance(donor)),
                    incoming_balanced=bool(balance(incoming)))
                item = dict(key=key, overlap_indices=np.flatnonzero(overlap).tolist(),
                            unpinned_witness=plain['witness'], pinned_witness=pinned['witness'])
                if pinned['ok']:
                    flags = ambiguity(256, u, v, outgoing.ravel()!=0, common.ravel(), pinned, PINS)
                    row['ambiguity_dimension'] = flags['dimension']
                    item['ambiguity'] = flags
                    h = hybrid(outgoing, donor, common, abs(incoming), pinned['bits'])
                    row['own_equivalent'] = bool(equivalent(h, own, PINS)['ok'])
                    evidence[key+'_alignment'] = pinned['bits']
                    evidence[key+'_hybrid'] = h
                    aligned.append(h)
                else:
                    aligned.append(None)
                rows.append(row); certificates.append(item)
            both = all(h is not None for h in aligned)
            comparisons.append(dict(block=block, case=case, both_admissible=both,
                aligned_donors_equivalent=bool(equivalent(*aligned, PINS)['ok']) if both else None))
    with (destination/'cases.csv').open('x', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    write(destination/'certificates.json', certificates)
    write(destination/'donor_comparisons.json', comparisons)
    save_arrays(destination/'alignments.npz', evidence)
    summary = {}
    for group in ('all', 'same_task', 'opposite_task'):
        panel = [r for r in rows if group=='all' or r['donor']==group]
        accepted = [r for r in panel if r['pinned_ok']]
        summary[group] = dict(pairs=len(panel), unpinned_ok=sum(r['unpinned_ok'] for r in panel),
            pinned_ok=len(accepted), obstructions=dict(Counter(r['obstruction'] for r in panel)),
            free_bit_counts=dict(Counter(r['pinned_free_bits'] for r in accepted)),
            ambiguity_dimensions=dict(Counter(r['ambiguity_dimension'] for r in accepted)),
            own_equivalent=sum(r['own_equivalent'] for r in accepted),
            outgoing_balanced=sum(r['outgoing_balanced'] for r in panel),
            donor_balanced=sum(r['donor_balanced'] for r in panel),
            incoming_balanced=sum(r['incoming_balanced'] for r in panel))
    summary.update(cases=len(comparisons), both_donors_admissible=sum(c['both_admissible'] for c in comparisons),
        aligned_donors_equivalent=sum(c['aligned_donors_equivalent'] is True for c in comparisons),
        new_task_outcomes=0, source_arrays_sha256=bound, at_utc=stamp())
    write(destination/'analysis.json', summary)
    print(summary)


if __name__ == '__main__':
    run()
