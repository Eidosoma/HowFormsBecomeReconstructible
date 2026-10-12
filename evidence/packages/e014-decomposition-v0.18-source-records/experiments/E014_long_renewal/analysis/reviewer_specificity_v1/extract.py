"""Hash-check retained E014 fields and export portable integer sufficient counts."""
import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
import time
from analysis import (HERE, ROOT, RUN, PILOT, BLOCKS, FACTORS, STAGES, ARMS,
    CATEGORIES, read, sha, write_json, gzip_writer, field_counts, transitions)
from common import cap_cpus
import numpy as np


def verify_original(run):
    complete = read(run/'COMPLETE.json'); manifest = read(run/'manifest.json'); audit = read(run/'INDEPENDENT_AUDIT.json')
    assert complete['status'] == 'COMPLETE' and audit['status'] == 'PASS'
    audited_digest = audit.get('complete_sha256', audit.get('audited_complete_sha256'))
    assert audited_digest == sha(run/'COMPLETE.json') and not (run/'FAILED.json').exists()
    for rel, digest in complete['outputs_sha256'].items(): assert sha(run/rel) == digest, rel
    for rel, digest in manifest['inputs_sha256'].items(): assert sha(run/'inputs'/rel) == digest, rel
    return dict(path=str(run.relative_to(ROOT)), resolved_local_path=str(run.resolve()),
        original_outputs_verified=len(complete['outputs_sha256']), frozen_inputs_verified=len(manifest['inputs_sha256']),
        receipts_sha256={n:sha(run/n) for n in ('COMPLETE.json', 'manifest.json', 'INDEPENDENT_AUDIT.json', 'summary.json')})


def main(out):
    cap_cpus(1); started = time.monotonic(); out = out.resolve()
    assert out.is_relative_to(HERE); out.mkdir(parents=True, exist_ok=False)
    index = dict(E014=verify_original(RUN), E001=verify_original(PILOT), raw_lineage_files={})
    summary = read(RUN/'summary.json'); assert summary['source_blocks'] == list(BLOCKS)
    counts_handle, counts_binary = gzip_writer(out/'cell_counts.csv.gz')
    endpoint_handle, endpoint_binary = gzip_writer(out/'endpoint_counts.csv.gz')
    countwriter = csv.writer(counts_handle); countwriter.writerow(('block', 'factor', 'stage', 'founder', 'recipient', 'arm', *CATEGORIES))
    endwriter = csv.writer(endpoint_handle); endwriter.writerow(('block', 'factor', 'founder', 'recipient', 'arm', 'after_3', 'after_16', 'cells'))
    nrows = 0; nend = 0; allcounts = {}
    for factor in FACTORS:
        for block in BLOCKS:
            path = RUN/f'block_{block:06d}_factor_{factor}.npz'
            with np.load(path, allow_pickle=False) as raw:
                prototype = raw['prototype']; v = np.concatenate((raw['generation_read'][:, :, :, :, 0], raw['checkpoint_read'][:, :, :, :, 0]))
                np.testing.assert_array_equal(raw['checkpoint_numbers'], [1, 3, 8, 16])
                cp = raw['checkpoint_read'][:, :, :, ARMS.index('copy')]
                np.testing.assert_array_equal(cp, np.broadcast_to(cp[0], cp.shape))
            counts, codes = field_counts(v, prototype); tab = transitions(codes)
            expected = np.array(summary['groups'][str(factor)]['block_own'])[BLOCKS.index(block)]
            np.testing.assert_array_equal(counts[..., 0].mean(axis=(1, 2))/256, expected)
            allcounts[block, factor] = counts
            for s, stage in enumerate(STAGES):
                for f, r, a in np.ndindex(4, 2, 10):
                    countwriter.writerow((block, factor, stage, f, r, ARMS[a], *counts[s, f, r, a].tolist())); nrows += 1
            for f, r, a, i, j in np.ndindex(4, 2, 10, 4, 4):
                endwriter.writerow((block, factor, f, r, ARMS[a], CATEGORIES[i], CATEGORIES[j], int(tab[f, r, a, i, j]))); nend += 1
            index['raw_lineage_files'][path.name] = dict(sha256=sha(path), bytes=path.stat().st_size)
        print('Extracted factor', factor, 'all64 blocks', flush=True)
    counts_handle.close(); counts_binary.close(); endpoint_handle.close(); endpoint_binary.close()
    # Compare the original individual observer rows, not only cohort means.
    checked = 0
    with (RUN/'observations.csv').open(newline='') as f:
        for row in csv.DictReader(f):
            key = (int(row['block']), int(row['factor']))
            value = allcounts[key][STAGES.index(row['stage']), int(row['founder']), int(row['recipient']), ARMS.index(row['arm']), 0]/256
            assert value == float(row['qualified_own']); checked += 1
    assert nrows == checked == 204800 and nend == 163840
    index.update(utc=datetime.now(timezone.utc).isoformat(), seconds=time.monotonic()-started,
        status='PASS', new_simulations=0, numerical_workers=1, original_individual_scores_exact=checked,
        cell_count_rows=nrows, endpoint_count_rows=nend, raw_lineage_bytes=sum(x['bytes'] for x in index['raw_lineage_files'].values()),
        code_sha256={n:sha(HERE/n) for n in ('PLAN.md', 'analysis.py', 'extract.py')},
        derived_sha256={n:sha(out/n) for n in ('cell_counts.csv.gz', 'endpoint_counts.csv.gz')},
        raw_fields_in_git=False, exclusion='Repository .gitignore: **/*.npz',
        extraction='All20 saved stages, all10 arms, 256 cells per founder/recipient, 64 blocks and two budgets; no filtering')
    write_json(out/'SOURCE_INDEX.json', index)
    print('All204800 original individual qualified scores reproduce exactly.', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--output', type=Path, required=True); main(p.parse_args().output)
