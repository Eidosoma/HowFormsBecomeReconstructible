"""Rebuild tables and interpretations from the compact git-portable counts."""
import argparse
import csv
from pathlib import Path
import time
from analysis import (HERE, ROOT, RUN, PILOT, FACTORS, CHECKPOINTS, STAGES, ARMS,
    METRICS, CATEGORIES, read, sha, write_json, load_counts, all_statistics,
    verify_historical, bootstrap_weights, estimate)
from common import cap_cpus, utc
import numpy as np


def pilot_context():
    source = read(PILOT/'summary.json'); result = {}
    for background in ('homogeneous', 'heterogeneous'):
        g = source['groups'][background]; x = np.asarray(g['block_qualified_own'])
        t = g['stages'].index('terminal'); own, foreign, copy = [x[:, t, g['arms'].index(a)] for a in ('rewrite', 'foreign', 'copy')]
        weights = bootstrap_weights(8, 'E001:'+background)
        contrast = estimate(own-foreign, weights); expected = g['contrasts']['terminal']['rewrite_minus_foreign']
        assert contrast['mean'] == expected['mean']; np.testing.assert_array_equal(contrast['ci95'], expected['ci95'])
        q = 0; temporal = 0; amplitude = 0; both = 0; diversity = []
        for f in g['formation']:
            positive = np.asarray(f['positive_fraction']); resolved = np.asarray(f['resolved_fraction'])
            neighbor = np.asarray(f['neighbor_agreement']); stable = np.asarray(f['half_window_agreement'])
            qualifying = (positive >= .1) & (positive <= .9) & (resolved >= .8) & (neighbor >= .65) & (stable >= .8)
            assert qualifying.tolist() == f['qualified']; q += int(qualifying.sum())
            temporal += int((stable < .8).sum()); amplitude += int((resolved < .8).sum()); both += int(((stable < .8) & (resolved < .8)).sum())
            diversity.extend(f['pairwise_disagreement'])
        assert q == g['formation_qualified_count']
        result[background] = dict(blocks=8, founders=32, formation_qualified=q,
            formation_fraction=q/32, temporal_failures=temporal, amplitude_failures=amplitude,
            overlapping_temporal_amplitude_failures=both, mean_pairwise_disagreement=float(np.mean(diversity)),
            formation_gate=g['gates']['formation'], verdict=g['verdict'], historical_contrast=contrast,
            own_agreement=estimate(own, weights), foreign_agreement=estimate(foreign, weights),
            copy_agreement=estimate(copy, weights), source_block_effects=(own-foreign).tolist())
    return result


def report(summary):
    stats = summary['statistics']; pilot = summary['pilot_context']
    pct = lambda s:f"{100*s['mean']:.3f} [{100*s['ci95'][0]:.3f}, {100*s['ci95'][1]:.3f}]"
    get = lambda factor, stage, arm, metric:stats[f'{factor}/{stage}/{arm}/{metric}']
    lines = ['# Historical specificity and the E014 sign/amplitude decomposition', '',
        'Post hoc reanalysis of the original unprescribed spatial apparatus; no new simulation, filtering, threshold or experimental decision.', '',
        '## Archive location and reproducible handoff', '',
        f'The full archive is `{RUN}`. All 128 requested factor1/factor4 lineage files were found and checked against their original completion hashes (3,227,309,039 bytes). Repository `.gitignore` excludes `**/*.npz`; those raw fields are local rather than stored in git.', '',
        f'The committed `{summary["data_directory"]}/cell_counts.csv.gz` and `endpoint_counts.csv.gz` contain all 20 stages, ten arms, 64 blocks, four founders and two recipients at both budgets. They reproduce this decomposition without the raw archive, but cannot reconstruct the continuous fields. The source index binds each original NPZ hash.', '',
        'All 204,800 original individual qualified scores match exactly. All 480 selected historical mean/interval summaries (all arms, all stages, plus own−foreign and own−copy) reproduce exactly from the integer counts. The original independent audit had already replayed every checkpoint reader; this review does not rerun the dynamics.', '',
        '## Total agreement and historical specificity are different quantities', '',
        'Own-record and foreign-record chains are both scored against the same own-founder prototype. The foreign donor is the next founder within the same background block. Protected copying preserves the initial bytes. Total qualified agreement includes common structure; the own−foreign contrast estimates an incremental record-history effect. Neither is a count of information bits, and the foreign score is not a pure estimate of background contribution.', '',
        '[Checkpoint figure](historical_specificity.png) · [vector SVG](historical_specificity.svg) · [PDF](historical_specificity.pdf)', '',
        '| Bytes | Completed rewrites | Own Q (%) | Foreign Q (%) | Protected Q (%) | Own−foreign (points, 95% CI) |',
        '| --- | ---: | ---: | ---: | ---: | --- |']
    for factor in FACTORS:
        for h in CHECKPOINTS:
            stage = f'after_{h}'
            means = [100*get(factor, stage, arm, 'qualified')['mean'] for arm in ('rewrite', 'foreign', 'copy')]
            lines.append(f'| {2048//factor**2} | {h} | {means[0]:.3f} | {means[1]:.3f} | {means[2]:.3f} | {pct(get(factor, stage, "rewrite_minus_foreign", "qualified"))} |')
    lines += ['', 'Checkpoint readers use the same terminal reset/noise draws across horizons; this explains the constant protected-copy curve. They do not feed back into the lineage. [All16 lineage reads](lineage_agreement.png) are displayed separately: G1 is before any replacement, and G16 is before the sixteenth. They must not be merged with the checkpoint curve as though they shared its reader stream.', '',
        '## Separate signs, amplitude and their joint score', '',
        'For each of all 256 sites, S tests `(v>0)==(prototype>0)` and A tests `abs(v)>.2`. The published score is Q=mean(S∧A). Sign agreement counts matching signs even below the threshold; amplitude qualification ignores whether the sign is correct. No founder-prototype amplitude filter is added.', '',
        '**Exact identity:** Q = sign agreement − matched-but-unresolved fraction. In general Q is not sign agreement multiplied by amplitude qualification.', '',
        '[Decomposition figure](sign_amplitude.png) · [SVG](sign_amplitude.svg) · [PDF](sign_amplitude.pdf)', '',
        '| Bytes | Rewrites | Q (%) | Sign agreement (%) | Amplitude qualified (%) | Matched but unresolved (%) |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for factor in FACTORS:
        for h in CHECKPOINTS:
            vals = [100*get(factor, f'after_{h}', 'rewrite', m)['mean'] for m in ('qualified', 'sign', 'amplitude', 'matched_unresolved')]
            lines.append(f'| {2048//factor**2} | {h} | '+' | '.join(f'{v:.3f}' for v in vals)+' |')
    lines += ['', 'After16 minus after 3, own-record arm; differences in percentage points, pointwise 95% whole-block intervals:', '',
        '| Bytes | Change Q | Change sign agreement | Change amplitude qualification | Change matched-unresolved |',
        '| --- | --- | --- | --- | --- |']
    for factor in FACTORS:
        vals = [get(factor, 'change_16_minus_3', 'rewrite', m) for m in ('qualified', 'sign', 'amplitude', 'matched_unresolved')]
        lines.append(f'| {2048//factor**2} | '+' | '.join(pct(v) for v in vals)+' |')
    lines += ['', '## Paired endpoint accounting', '',
        'Compare the same coordinates in the paired after 3/after 16 fresh readers. Qualified-to-unqualified losses and the reverse gains can involve sign-only endpoint differences, amplitude-only differences, or both. The three net terms below add exactly to the change in Q.', '',
        '| Bytes | Sign-only net (points, 95% CI) | Amplitude-only net | Both-different net | Total change Q |',
        '| --- | --- | --- | --- | --- |']
    for factor in FACTORS:
        vals = [stats[f'{factor}/endpoints_3_16/rewrite/{m}_net'] for m in ('sign_only', 'amplitude_only', 'both')]
        lines.append(f'| {2048//factor**2} | '+' | '.join(pct(v) for v in vals)+f' | {pct(get(factor, "change_16_minus_3", "rewrite", "qualified"))} |')
    lines += ['', 'These are **endpoint differences between fresh bodies**, not observed cell trajectories, counts of all intervening sign/threshold crossings, or a causal decomposition. The both-different category has no unique allocation to signs versus amplitudes. A decline in sign agreement is a decline in coordinate-matched signs; it does not by itself measure spatial-detail loss or translation-tolerant shape.', '',
        '## Historical dependence can coexist with failed formation', '',
        'The homogeneous E001 development pilot belongs to the manuscript’s E31 evidence note; it is a separate eight-block-per-setting cohort and is not pooled with E014 (E43).', '',
        '[Pilot figure](pilot_history_formation.png) · [SVG](pilot_history_formation.svg) · [PDF](pilot_history_formation.pdf)', '',
        '| Pilot background | Founders passing formation | Own−foreign at terminal read (points, 95% CI) | Formation gate |',
        '| --- | --- | --- | --- |']
    for bg, g in pilot.items(): lines.append(f'| {bg} | {g["formation_qualified"]}/32 ({100*g["formation_fraction"]:.2f}%) | {pct(g["historical_contrast"])} | {g["formation_gate"]} |')
    lines += ['', 'Both backgrounds pass the diversity component of formation; the homogeneous setting fails the requirement that at least 75% of founders qualify. Its larger own-history effect therefore demonstrates that historical dependence and stable formation are separate achievements. It cannot rescue the failed formation-to-renewal conjunction.', '',
        '## Scope of uncertainty', '',
        'Every mean averages founders and recipients within each block, then averages 64 E014 blocks. Intervals use the original 10,000 whole-block bootstrap indices. New decomposition intervals are post hoc, descriptive and pointwise 95%; no new primary gates or simultaneous discoveries are claimed. Pilot intervals separately resample its eight blocks. Pixels and recipients are never treated as independent bootstrap units.', '',
        'All original founders and control arms remain included. No E053 results were consumed, no E054 run was launched, and parent manuscripts were not edited.']
    return '\n'.join(lines)+'\n'


def main(data, out):
    cap_cpus(1); started = time.monotonic(); data, out = data.resolve(), out.resolve()
    index = read(data/'SOURCE_INDEX.json')
    assert out.is_relative_to(HERE); out.mkdir(parents=True, exist_ok=False)
    for name, digest in index['derived_sha256'].items(): assert sha(data/name) == digest
    for key, run in (('E014', RUN), ('E001', PILOT)):
        for name, digest in index[key]['receipts_sha256'].items(): assert sha(run/name) == digest
    counts, endpoints = load_counts(data); stats, block_values = all_statistics(counts, endpoints)
    n = verify_historical(counts, stats)
    summary = dict(status='POST_HOC_REANALYSIS', utc=utc(), statistics=stats, pilot_context=pilot_context(),
        blocks=64, founders=256, recipients_per_founder=2, factors=list(FACTORS), stages=list(STAGES),
        checkpoints=list(CHECKPOINTS), arms=list(ARMS), metrics=list(METRICS), categories=list(CATEGORIES),
        native_scale=[0, 1], threshold=.2, denominator=256, bootstrap_samples=10000,
        original_summaries_reproduced=n, new_simulations=0, seconds=time.monotonic()-started,
        data_directory=data.name, source_index_sha256=sha(data/'SOURCE_INDEX.json'), code_sha256={n:sha(HERE/n) for n in ('analysis.py', 'derive.py')})
    write_json(out/'summary.json', summary)
    with (out/'checkpoint_table.csv').open('x', newline='') as f:
        w = csv.writer(f); w.writerow(('factor', 'bytes', 'completed_rewrites', 'arm', 'metric', 'mean', 'ci95_low', 'ci95_high'))
        for factor in FACTORS:
            for h in CHECKPOINTS:
                for arm in (*ARMS, 'rewrite_minus_foreign', 'rewrite_minus_copy'):
                    for metric in METRICS:
                        s = stats[f'{factor}/after_{h}/{arm}/{metric}']
                        w.writerow((factor, 2048//factor**2, h, arm, metric, s['mean'], *s['ci95']))
    (out/'REPORT.md').write_text(report(summary))
    print('Derived', len(stats), 'summaries;', n, 'historical summaries exactly reproduced.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--data', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); main(a.data, a.output)
