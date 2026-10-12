"""Post-result description of exact packet convergence; no new simulations."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, default=Path('runs/h006_development_v1'))
    parser.add_argument('--output', type=Path, default=Path('h006/CLOSEOUT_DIAGNOSTICS.json'))
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Preserve the previous closeout output')
    config = json.loads((args.run/'config.json').read_text())
    blocks, pair_counts = [], []
    for seed in config['assay_seeds']:
        with np.load(args.run/f'assay_{seed}.npz') as present:
            eligible = present['eligible'][0]
        count = int(eligible.sum())
        if not count:
            continue
        forks = []
        discordance = np.zeros((2, 2), dtype=int)
        for fork in range(config['forks']):
            with np.load(args.run/f'future_{seed}_{fork:02d}.npz') as raw:
                records = raw['record_codes'][:, :, 0]  # renewal only
                equality = np.stack([np.all(records[:, v] == records[:, 0], axis=(-2, -1))
                                     for v in (1, 2)], axis=1)
                if np.any(equality[:-1] & ~equality[1:]):
                    raise AssertionError('Identical packets diverged under paired future tapes')
                if equality[0, :, eligible].any():
                    raise AssertionError('Matched intervention did not alter the initial packet')
                forks.append(equality[:, :, eligible].mean(axis=-1))
                terminal = raw['success'][-1, :, 0][:, eligible]
                for v in (1, 2):
                    discordance[v-1, 0] += np.count_nonzero(terminal[0] & ~terminal[v])
                    discordance[v-1, 1] += np.count_nonzero(~terminal[0] & terminal[v])
            del records
        blocks.append(dict(seed=seed, matched=count,
                           exact_packet_equality=np.mean(forks, axis=0).tolist(),
                           terminal_discordance_counts=discordance.tolist()))
        pair_counts.append(count*config['forks'])
    mean = np.mean([row['exact_packet_equality'] for row in blocks], axis=0)
    counts = np.sum([row['terminal_discordance_counts'] for row in blocks], axis=0)
    result = dict(classification='POST_RESULT_DESCRIPTIVE_DIAGNOSTIC',
                  source_run=str(args.run), source_checksums_sha256=hashlib.sha256((args.run/'checksums.json').read_bytes()).hexdigest(),
                  source_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  variants=['output_flips', 'hidden_flips'], comparator='unchanged renewal',
                  weighting='Average matched packets and forks within each base network, then weight networks equally.',
                  matched_packets=sum(r['matched'] for r in blocks), matched_packet_forks=sum(pair_counts),
                  exact_packet_equality=mean.tolist(), generations=list(range(17)),
                  selected_generation_equality={str(g): mean[g].tolist() for g in (0, 1, 4, 8, 16)},
                  terminal_discordance_columns=['unchanged_pass_edited_fail', 'unchanged_fail_edited_pass'],
                  terminal_discordance_counts=counts.tolist(), blocks=blocks,
                  interpretation='Exact convergence under paired tapes describes these matched trajectories. '
                                 'It is not a new qualification test, useful-repair contrast or universal robustness claim. '
                                 'No new future was simulated; the frozen primary verdict is unchanged.')
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({k: result[k] for k in ('classification', 'matched_packets', 'matched_packet_forks',
                                           'selected_generation_equality', 'terminal_discordance_counts')}, indent=2))


if __name__ == '__main__':
    main()
