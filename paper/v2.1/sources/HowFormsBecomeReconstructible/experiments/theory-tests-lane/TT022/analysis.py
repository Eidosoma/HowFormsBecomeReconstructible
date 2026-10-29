"""All exposed-block serial summaries; no confirmatory significance decisions."""
import math

from common import BLOCKS, read_json
from design import FAMILIES, POLICIES, FUTURES, GENERATIONS, comparisons


def mean(values):
    values = list(values)
    assert values
    return math.fsum(values)/len(values)


def summary(directory):
    data = {}
    for family in FAMILIES:
        data[family] = {}
        for policy in POLICIES:
            data[family][policy] = {i: [read_json(directory/f'tissue_{i}'/f'future_{f:02d}'/family/policy/'records.json')
                                      for f in range(FUTURES)] for i in BLOCKS}
    families = {}
    for family in FAMILIES:
        arms = {}
        for policy in POLICIES:
            source = data[family][policy]
            all_rows = [r for i in BLOCKS for batch in source[i] for r in batch]
            assert len(all_rows) == len(BLOCKS)*16*FUTURES
            arms[policy] = dict(terminal=mean(r['terminal'] for r in all_rows),
                uninterrupted_development=mean(r['uninterrupted_development'] for r in all_rows),
                uninterrupted_repaired=mean(r['uninterrupted_repaired'] for r in all_rows),
                development_by_generation=[mean(r['development'][g] for r in all_rows) for g in range(GENERATIONS)],
                repaired_by_generation=[mean(r['repaired'][g] for r in all_rows) for g in range(GENERATIONS)],
                terminal_by_message=[mean(r['terminal'] for r in all_rows if r['message'] == m) for m in range(4)],
                terminal_by_block={i: mean(r['terminal'] for batch in source[i] for r in batch) for i in BLOCKS},
                terminal_by_record={i: [mean(source[i][f][r]['terminal'] for f in range(FUTURES)) for r in range(16)] for i in BLOCKS},
                chains=len(all_rows))
        contrasts = {}
        for label, (left, right) in comparisons().items():
            a, b = arms[left], arms[right]
            block_values = {i: a['terminal_by_block'][i]-b['terminal_by_block'][i] for i in BLOCKS}
            changes = [a['terminal_by_record'][i][r]-b['terminal_by_record'][i][r] for i in BLOCKS for r in range(16)]
            paired = [(x, y) for i in BLOCKS for f in range(FUTURES)
                      for x, y in zip(data[family][left][i][f], data[family][right][i][f])]
            assert all((x['world'], x['message'], x['replicate']) == (y['world'], y['message'], y['replicate']) for x, y in paired)
            contrasts[label] = dict(left=left, right=right, terminal=mean(block_values.values()),
                terminal_by_block=block_values,
                uninterrupted_development=a['uninterrupted_development']-b['uninterrupted_development'],
                uninterrupted_repaired=a['uninterrupted_repaired']-b['uninterrupted_repaired'],
                improved_records=sum(v > 0 for v in changes), worsened_records=sum(v < 0 for v in changes),
                tied_records=sum(v == 0 for v in changes),
                improved_chain_draws=sum(x['terminal'] > y['terminal'] for x, y in paired),
                worsened_chain_draws=sum(x['terminal'] < y['terminal'] for x, y in paired),
                tied_chain_draws=sum(x['terminal'] == y['terminal'] for x, y in paired))
        families[family] = dict(arms=arms, contrasts=contrasts)
    return dict(classification='EXPOSED_STARTING_RECORD_SERIAL_DEVELOPMENT',
        blocks=list(BLOCKS), population_blocks=len(BLOCKS), records_per_family=64,
        futures_per_record=FUTURES, generations=GENERATIONS, chains_per_policy_family=256,
        families=families, primary='common:capture_vs_ordinary:terminal',
        primary_effect=families['common']['contrasts']['capture_vs_ordinary']['terminal'],
        no_significance_verdict=True, fresh_population_confirmation=False,
        record_bytes=2048, original_message_pairing=True, all_chains_retained=True)


def report(value):
    lines = ['# TT022 serial capture development', '',
        'Four exposed starting blocks; all 64 positions per family; four futures per record; eight replacement cycles.',
        'These are descriptive development results, with four population blocks and no confirmatory significance verdict.', '',
        '| Family | Policy | Final fresh-recipient recognition | Uninterrupted developed bodies | Uninterrupted repaired bodies |',
        '| --- | --- | ---: | ---: | ---: |']
    for family, result in value['families'].items():
        for policy, item in result['arms'].items():
            lines.append(f"| {family} | {policy} | {100*item['terminal']:.3f}% | {100*item['uninterrupted_development']:.3f}% | {100*item['uninterrupted_repaired']:.3f}% |")
    lines += ['', '| Family | Planned contrast | Final recognition difference | Improved / worsened / tied records |',
              '| --- | --- | ---: | --- |']
    for family, result in value['families'].items():
        for label, item in result['contrasts'].items():
            lines.append(f"| {family} | {label} | {100*item['terminal']:.3f} pp | {item['improved_records']} / {item['worsened_records']} / {item['tied_records']} |")
    lines += ['', 'Only each actual outgoing record crosses replacement. Held memory is recaptured from each current injured body.',
        'The fixed and average policies have matched observation schedules; their realized streams can diverge after earlier packet differences.',
        'The averaging implementation computes an unused native-writer sidecar; no equal-compute or scheduling claim is made.',
        'Terminal and uninterrupted endpoints remain separate; all generation, message, block and record summaries are retained.',
        'Four futures are coarse conditional estimates. This experiment is not a fresh-population confirmation or an autonomy claim.', '']
    return '\n'.join(lines)
