"""Descriptive outcomes for post-result H005 structural groups; no qualification."""
from pathlib import Path
import json
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from h006.lead_diagnostics import digest, load_sealed, load_arrays, single_pattern


def main():
    output = Path('h006/HIDDEN_PAIR_OUTCOMES.json')
    if output.exists():
        raise FileExistsError('Preserve the earlier outcome diagnostic')
    run = Path('runs/h005_development_v1')
    seals = load_sealed(run)
    assert digest(run/'config.json') == seals['config.json']
    config = json.loads((run/'config.json').read_text())
    rows = {name: [] for name in ('hidden_only', 'not_both_single_pattern')}
    for seed in config['seeds']:
        present = load_arrays(run, f'present_{seed}.npz', seals)
        source = load_arrays(run, f'inputs/source_{seed}.npz', seals)
        eligible = present['eligible']
        codes = np.rint(source['records']*64).astype(np.int8)
        same = np.all(codes[0] == codes[1], axis=(-2, -1))
        both = single_pattern(codes).all(axis=0)
        b = source['source_bodies']
        visible = np.all(b[0, ..., :24] == b[1, ..., :24], axis=(-2, -1))
        hidden = np.any(b[0, ..., 24:] != b[1, ..., 24:], axis=(-2, -1))
        groups = dict(hidden_only=eligible & both & visible & hidden & ~same,
                      not_both_single_pattern=eligible & ~both)
        current = present['validation_success'].mean(axis=0)
        futures = []
        for fork in range(config['forks']):
            relative = f'future_{seed}_{fork:02d}.npz'
            assert digest(run/relative) == seals[relative], relative
            with np.load(run/relative) as raw:
                futures.append(raw['success'][-1, :, 0])
        future = np.mean(futures, axis=0)
        for name, mask in groups.items():
            if mask.any():
                rows[name].append(dict(seed=seed, count=int(mask.sum()),
                    current=current[:, mask].mean(axis=1).tolist(), future=future[:, mask].mean(axis=1).tolist()))
    summary = {}
    for name, group in rows.items():
        summary[name] = dict(pairs=sum(r['count'] for r in group), blocks=len(group),
            current_means=np.mean([r['current'] for r in group], axis=0).tolist(),
            future_means=np.mean([r['future'] for r in group], axis=0).tolist(), block_rows=group)
    result = dict(classification='POST_RESULT_DESCRIPTIVE_SUBGROUPS', source_run=str(run),
        source_checksums_sha256=digest(run/'checksums.json'), source_script_sha256=digest(Path(__file__)),
        helper_script_sha256=digest(Path('h006/lead_diagnostics.py')), histories=config['histories'],
        groups=summary,
        weighting='Average pairs/forks within each nonempty network, then weight those networks equally for each subgroup.',
        scope='Groups were inspected after the primary result. No subgroup interval, new qualification, causal history effect '
              'or identical-current-performance claim is made. These conditional means do not decompose the original '
              'whole-cohort effect, and cannot rescue the unchanged H005/H006 verdicts.')
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({name: {k: v for k, v in group.items() if k != 'block_rows'}
                      for name, group in summary.items()}, indent=2))


if __name__ == '__main__':
    main()
