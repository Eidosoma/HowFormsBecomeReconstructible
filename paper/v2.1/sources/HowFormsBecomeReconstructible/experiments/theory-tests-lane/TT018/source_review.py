"""Retain completed development evidence and independently check its CSV endpoints.

This is an artifact and endpoint-table audit, not a native dynamics replay.
All sources are read-only; outputs are exclusive-create in this new study.
"""
import csv
from collections import defaultdict
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
LANE = HERE.parent
SOURCES = (
    ('budget', 'p08_budgeted_repair_v0_1', 'pilot_v1', 16),
    ('frequency', 'p08_repair_frequency_v0_1', 'pilot_v1', 16),
    ('efficiency', 'p08_repair_efficiency_v0_1', 'prospective_v1', 132),
)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def dump(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def require(condition, label):
    if not condition:
        raise ValueError(label)


def retain(original, destination, expected=None):
    digest = sha(original)
    require(expected is None or digest == expected, 'Source commitment: ' + str(original))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(original.read_bytes())
    require(sha(destination) == digest, 'Copied source identity')
    return dict(original=str(original.resolve()), local=str(destination.relative_to(HERE)),
                sha256=digest, bytes=destination.stat().st_size,
                checked_against_completion=expected is not None)


def check_tables(run, nblocks, integer_summary):
    cases = defaultdict(list)
    raw = {}
    with (run/'reads.csv').open(newline='') as stream:
        for row in csv.DictReader(stream):
            block, gen, case = (int(row[k]) for k in ('block', 'generation', 'case'))
            variant = row['variant']
            key = block, variant, case
            require(0 <= case < 16 and 15 <= gen <= 32, 'Declared generation and case')
            flag = int(row['intended'])
            require(flag == int(float(row['min_margin']) > .25), 'Strict intended margin')
            require(int(row['opposite']) == int(float(row['opposite_margin']) > .25), 'Strict opposite margin')
            cases[key].append((gen, flag, int(row['uninterrupted_so_far'])))
            full_key = block, gen, variant, case
            require(full_key not in raw, 'Duplicate read row')
            raw[full_key] = tuple(row[k] for k in
                ('intended', 'opposite', 'min_margin', 'opposite_margin', 'uninterrupted_so_far'))
    by_block = defaultdict(lambda: dict(uninterrupted=0, terminal=0, first_pass=0))
    for (block, variant, case), rows in cases.items():
        rows.sort()
        require([r[0] for r in rows] == list(range(15, 33)), 'All 18 generations retained')
        running = 1
        for _, flag, saved_running in rows:
            running *= flag
            require(running == saved_running, 'Running endpoint includes earlier failures')
        counts = by_block[block, variant]
        counts['uninterrupted'] += running
        counts['terminal'] += rows[-1][1]
        counts['first_pass'] += rows[0][1]
    variants = sorted({variant for _, variant, _ in cases})
    blocks = sorted({block for block, _, _ in cases})
    require(len(blocks) == nblocks, 'Complete block cohort')
    require(len(cases) == nblocks*16*len(variants), 'Complete policy/case cohort')
    seen = set()
    with (run/'block_summaries.csv').open(newline='') as stream:
        for row in csv.DictReader(stream):
            key = int(row['block']), row['variant']
            require(key not in seen, 'Unique block summary')
            seen.add(key)
            require(int(row['history']) == key[0] % 4, 'History stratum')
            for metric in ('uninterrupted', 'terminal', 'first_pass'):
                value = Fraction(row[metric]) * (1 if integer_summary else 16)
                require(value == by_block[key][metric], 'Recomputed block ' + metric)
    require(seen == set(by_block), 'All block summaries retained')
    analysis = read(run/'analysis.json')
    totals = {}
    for variant in variants:
        totals[variant] = {}
        for metric in ('uninterrupted', 'terminal'):
            count = sum(by_block[b, variant][metric] for b in blocks)
            require(abs(analysis['rates'][variant][metric]['mean'] - count/(nblocks*16)) < 1e-14,
                    'Published rate agrees with all saved read rows')
            for block in blocks:
                require(analysis['rates'][variant][metric]['by_block'][str(block)] ==
                        by_block[block, variant][metric]/16, 'Published block rate')
            totals[variant][metric] = count
    return dict(blocks=blocks, records=nblocks*16, read_rows=len(raw), totals=totals,
                scope='All saved CSV margins, flags, 18-step paths, block summaries and rate point estimates; no raw port-window or dynamics replay.'), raw


def main():
    output = HERE/'SOURCE_REVIEW.json'
    require(not output.exists() and not (HERE/'sources').exists(), 'Preserve prior review attempts')
    (HERE/'sources').mkdir()
    bindings, summaries, panels = [], {}, {}
    for label, study, run_name, nblocks in SOURCES:
        base = LANE.parent/'theory-lane'/study
        run = base/'runs'/run_name
        done = read(run/'COMPLETE.json')
        require(done['status'] == 'COMPLETE', 'Only completed studies may enter planning')
        require(len(done['blocks_completed']) == nblocks, 'Completion cohort size')
        for name in ('COMPLETE.json', 'REPORT.md', 'analysis.json', 'block_summaries.csv', 'reads.csv', 'VERIFICATION.json'):
            expected = None if name == 'COMPLETE.json' else done['outputs_sha256'][name]
            bindings.append(retain(run/name, HERE/'sources'/label/name, expected))
        bindings.append(retain(base/'PROTOCOL.md', HERE/'sources'/label/'PROTOCOL.md'))
        summary, panels[label] = check_tables(HERE/'sources'/label, nblocks, label == 'efficiency')
        summary.update(completed_utc=done['at_utc'], source_scientific_status=done['scientific_status'],
                       complete_sha256=sha(run/'COMPLETE.json'), source_internal_verification=done['independent_verification_passed'])
        summaries[label] = summary
    budget, frequency = panels['budget'], panels['frequency']
    reused = 0
    for old, new in [('periodic', 'repairs_9'), ('repeated', 'repairs_18')]:
        for (block, gen, variant, case), values in budget.items():
            if variant == old:
                require(frequency[block, gen, new, case] == values, 'Reused control read identity')
                reused += 1
    a = read(HERE/'sources/budget/analysis.json')
    warning_delta = Fraction(summaries['budget']['totals']['warning']['uninterrupted'] -
                             summaries['budget']['totals']['periodic']['uninterrupted'], 256)
    require(float(warning_delta) == a['contrasts']['warning_minus_periodic']['uninterrupted']['mean'], 'Warning primary')
    require(warning_delta < 0 and a['primary_direction_observed'] is False, 'Failed warning direction retained')
    a = read(HERE/'sources/efficiency/analysis.json')
    counts = summaries['efficiency']['totals']
    n1, n6, n18 = [counts['repairs_'+str(n)]['uninterrupted'] for n in (1, 6, 18)]
    gain = Fraction(n18-n1, 2112)
    doubled = Fraction(17*n6-10*n18-7*n1, 17*2112)
    require(float(gain) == a['primary']['continual_benefit']['mean'], 'Continual benefit point estimate')
    require(float(doubled) == a['primary']['double_call_efficiency']['mean'], 'Efficiency point estimate')
    require(a['primary']['continual_benefit']['one_sided_95_lower'] > 0 and
            a['primary']['double_call_efficiency']['one_sided_95_lower'] < 0 and
            a['primary']['verdict'] == 'UNRESOLVED', 'Reported unresolved criterion retained')
    evidence = dict(status='PASS', recorded_utc=datetime.now(timezone.utc).isoformat(),
        code_sha256=sha(Path(__file__)), sources=bindings, studies=summaries,
        reused_control_read_rows_identical=reused,
        warning_primary_delta=float(warning_delta), efficiency_gain=float(gain),
        double_call_efficiency_contrast=float(doubled), efficiency_verdict='UNRESOLVED',
        confidence_intervals_independently_recomputed=False, full_native_dynamics_replayed=False,
        new_trajectories_generated=False, all_reviewed_source_cohorts_exposed=True)
    dump(output, evidence)
    print(json.dumps({k:v for k,v in evidence.items() if k not in ('sources', 'studies')}, indent=2))


if __name__ == '__main__':
    main()
