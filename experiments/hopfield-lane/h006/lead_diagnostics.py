"""Post-result writer compatibility and H005 convergence; no new dynamics."""
from pathlib import Path
import hashlib
import json
import numpy as np


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_sealed(run):
    final = json.loads((run/'checksums.json').read_text())
    manifests = {}
    for name in ('freeze.json', 'raw_sha256.json'):
        assert digest(run/name) == final[name], name
        manifests.update(json.loads((run/name).read_text()))
    return manifests


def load_arrays(run, relative, seals):
    path = run/relative
    assert digest(path) == seals[relative], relative
    with np.load(path) as raw:
        return {name: raw[name] for name in raw.files}


def single_pattern(codes):
    pattern = codes[..., 0, :].copy()
    pattern[..., 0] = 1
    reconstructed = pattern[..., :, None]*pattern[..., None, :]
    diagonal = np.arange(64)
    reconstructed[..., diagonal, diagonal] = 0
    return np.all(codes == reconstructed, axis=(-2, -1))


def main():
    output = Path('h006/LEAD_DIAGNOSTICS.json')
    if output.exists():
        raise FileExistsError('Preserve the earlier diagnostic')
    h005 = Path('runs/h005_development_v1')
    h006 = Path('runs/h006_development_v1')
    seals5, seals6 = load_sealed(h005), load_sealed(h006)
    config5 = json.loads((h005/'config.json').read_text())
    config6 = json.loads((h006/'config.json').read_text())
    original_count = 0
    representable = np.zeros(3, dtype=int)
    coherent_swaps = 0
    for seed in config6['assay_seeds']:
        raw = load_arrays(h006, f'assay_{seed}.npz', seals6)
        eligible = raw['eligible'][0]
        codes = raw['packet_codes'][0]
        original_count += int(eligible.sum())
        representable += single_pattern(codes)[:, eligible].sum(axis=1)
        # All off-diagonal entries must be nonzero for the two-pattern argument.
        off_diagonal = ~np.eye(64, dtype=bool)
        assert np.isin(codes[:, eligible][:, :, off_diagonal], [-1, 1]).all()
        source = load_arrays(h006, f'inputs/source_{seed}.npz', seals6)
        for f, r in zip(*np.where(eligible)):
            code = codes[0, f, r]
            plus = 24+np.flatnonzero(code[0, 24:] == 1)[0]
            minus = 24+np.flatnonzero(code[0, 24:] == -1)[0]
            permutation = np.arange(64)
            permutation[[plus, minus]] = permutation[[minus, plus]]
            swapped = code[np.ix_(permutation, permutation)]
            body = source['source_bodies'][f, r][:, permutation].astype(float)
            written = np.einsum('ti,tj->ij', body, body)/2
            written[np.diag_indices(64)] = 0
            assert np.array_equal(swapped, written)
            assert not np.array_equal(swapped, code)
            assert np.array_equal(swapped[:24, :24], code[:24, :24])
            assert np.array_equal(np.sort(swapped.ravel()), np.sort(code.ravel()))
            assert single_pattern(swapped)
            coherent_swaps += 1

    totals = dict(matched=0, identical=0, distinct=0, both_single_pattern=0,
                  distinct_single_pattern=0, hidden_only_distinct=0)
    rows = []
    group_curves = {name: [] for name in ('all_matched', 'initially_distinct', 'hidden_only_distinct')}
    for seed in config5['seeds']:
        present = load_arrays(h005, f'present_{seed}.npz', seals5)
        source = load_arrays(h005, f'inputs/source_{seed}.npz', seals5)
        eligible = present['eligible']
        codes = np.rint(source['records']*64).astype(np.int8)
        same = np.all(codes[0] == codes[1], axis=(-2, -1))
        both_single = single_pattern(codes).all(axis=0)
        bodies = source['source_bodies']
        same_visible = np.all(bodies[0, ..., :24] == bodies[1, ..., :24], axis=(-2, -1))
        hidden_diff = np.any(bodies[0, ..., 24:] != bodies[1, ..., 24:], axis=(-2, -1))
        hidden_only = eligible & both_single & same_visible & hidden_diff & ~same
        groups = dict(all_matched=eligible, initially_distinct=eligible & ~same, hidden_only_distinct=hidden_only)
        counts = dict(matched=int(eligible.sum()), identical=int((eligible & same).sum()),
                      distinct=int((eligible & ~same).sum()), both_single_pattern=int((eligible & both_single).sum()),
                      distinct_single_pattern=int((eligible & both_single & ~same).sum()),
                      hidden_only_distinct=int(hidden_only.sum()))
        for name, value in counts.items():
            totals[name] += value
        curves = {name: [] for name, mask in groups.items() if mask.any()}
        for fork in range(config5['forks']):
            relative = f'future_{seed}_{fork:02d}.npz'
            assert digest(h005/relative) == seals5[relative], relative
            with np.load(h005/relative) as raw:
                records = raw['record_codes'][:, :, 0]
                same_future = np.all(records[:, 0] == records[:, 1], axis=(-2, -1))
            assert np.array_equal(same_future[0], same)
            assert not np.any(same_future[:-1] & ~same_future[1:])
            for name in curves:
                curves[name].append(same_future[:, groups[name]].mean(axis=-1))
        row = dict(seed=seed, counts=counts, exact_packet_equality={})
        for name, values in curves.items():
            mean = np.mean(values, axis=0)
            row['exact_packet_equality'][name] = mean.tolist()
            group_curves[name].append(mean)
        rows.append(row)
    comparison = {}
    for name, curves in group_curves.items():
        mean = np.mean(curves, axis=0) if curves else None
        comparison[name] = dict(nonempty_blocks=len(curves),
            equality_by_generation=mean.tolist() if mean is not None else None,
            checkpoints={str(g): float(mean[g]) for g in (0, 1, 4, 8, 16)} if mean is not None else None)
    result = dict(classification='POST_RESULT_MECHANISM_DIAGNOSIS_NO_NEW_DYNAMICS',
        source_checksums={str(run): digest(run/'checksums.json') for run in (h005, h006)},
        source_script_sha256=digest(Path(__file__)),
        h006=dict(matched_packets=original_count,
                  single_pattern_representable_counts=dict(zip(('unchanged', 'output_flips', 'hidden_flips'), map(int, representable))),
                  all_off_diagonal_codes_nonzero=True,
                  algebra='For two binary observations, nonzero entries everywhere off the diagonal require their pairwise products '
                          'to agree everywhere, hence the observations differ at most by a global sign. The record must therefore '
                          'be one outer product with its diagonal removed. The altered H006 records fail this condition.',
                  coherent_hidden_swap_candidates_checked=coherent_swaps,
                  candidate_scope='Algebraic feasibility only: swap opposite-phase hidden sites in both source body observations, '
                                  'then apply the unchanged writer. This preserves the visible block, full histogram and coordinate-permutation '
                                  'invariants. Actual reader function and persistence have not been tested.'),
        h005=dict(counts=totals, convergence=comparison, blocks=rows),
        weighting='For each diagnostic group, average matched packets/forks within nonempty networks, then weight networks equally.',
        interpretation='Post-result subgroup descriptions cannot rescue H005/H006 or establish different durability at matched function. '
                       'They motivate a prospective intervention on a coherent hidden activity pattern using the existing writer. '
                       'No H007 experiment has been frozen or launched.')
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(h006=result['h006'], h005_counts=totals,
                         h005_convergence={k: {x: v[x] for x in ('nonempty_blocks', 'checkpoints')} for k, v in comparison.items()}), indent=2))


if __name__ == '__main__':
    main()
