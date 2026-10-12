"""Report the fixed primary even when secondary outcomes look more favorable."""
import support as s


def render(result):
    e = result['primary_effect']
    lines = ['# TT016 prospective serial durability result', '',
             f"Scientific classification: **{result['scientific_verdict']}**.", '',
             'The single primary compares repeated repair with no repair under independent ongoing cue noise.',
             'Success requires the intended task at all 18 actual rebuilds, generations 15–32.',
             'All 1,024 records in 64 new independent blocks are included, with four equally weighted histories.', '',
             f"Primary gain: {100*e['mean']:.4f} percentage points.",
             f"One-sided 95% lower bound: {100*e['lower_one_sided95']:.4f}; fixed practical margin: 5 points.",
             f"Two-sided 95% interval: [{100*e['two_sided95'][0]:.4f}, {100*e['two_sided95'][1]:.4f}] points.",
             f"Block directions: {e['positive_blocks']} positive, {e['tied_blocks']} tied, {e['negative_blocks']} negative.",
             f"Inference: {e['method']}. Student-t coverage is approximate; the zero-variance fallback is conservative.", '',
             '| Policy | Uninterrupted success | Terminal success |', '| --- | ---: | ---: |']
    for name, row in result['rates'].items():
        lines.append(f"| {name} | {100*row['uninterrupted']['mean']:.4f}% | {100*row['terminal']['mean']:.4f}% |")
    lines += ['', 'All secondary contrasts, history summaries, initial strata, generation curves, opposite-task outcomes,',
              'resource accounts and noise/fallback diagnostics are retained in analysis.json and the raw tables.',
              'Secondary bootstrap intervals are descriptive and do not replace the registered primary gate.',
              'Terminal recovery does not restore uninterrupted success. Empty subgroup rates are undefined.', '',
              'Teaching and birth/reset remain matched; only ongoing cue-noise correlation changes.',
              'Repeated repair adds recurring computation. Shuffled policies match their own current input resources,',
              'while histories and total added weights can diverge. Fallback counts do not identify causal mediation.', '',
              'This is prospective validation within the same supplied simulator, lattice, pins, reader and optimizer.',
              'It does not establish autonomy, external replication, transfer or a prediction unique to RDT.',
              'All native trajectories and every optimizer call receive independent verification.',
              'The full cohort ran without scientific optional stopping, substitution, resizing or retuning.',
              'No automatic successor is launched.', '']
    return '\n'.join(lines)


def run(output, result):
    s.dump(output/'SCIENTIFIC_VERDICT.json', dict(audit_status='PASS', scientific_verdict=result['scientific_verdict'],
        primary_name=result['primary_name'], primary_endpoint='uninterrupted', primary_effect=result['primary_effect'],
        new_scientific_cohort=True, within_apparatus_only=True, subgroup_rescue_permitted=False,
        full_native_replay_performed=True, automatic_successor=False))
    with (output/'REPORT.md').open('x') as f:
        f.write(render(result))
    return result
