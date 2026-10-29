"""Stable rendering in declared cell/group order; no outcome-dependent selection."""
from common import *


def pct(value): return f'{100*value:.3f}'
def triplet(value): return ' / '.join(str(value[s]) for s in SIGNS)


def render(value):
    panel = value['panel']
    lines = ['# TT029: effects of writing after update 100', '',
        'Exposed TT028 cohort; descriptive saved-data diagnosis. No new dynamics, receiving assays '
        'or source cases. All bodies evolve for 1,000 physical steps. The contrast below is '
        '1,000 minus 100 writing updates, after byte-identical saved states through update 100.', '',
        'TT028\'s primary and joint practical-correction claims remain NOT_CONFIRMED. No new '
        'confirmatory decision or validated intervention policy is produced here.', '',
        '| Family | Corruption | Extra recipient credit | Paired recipient gains / harms / ties | Extra body credit | Body gains / harms / ties |',
        '| --- | --- | ---: | --- | ---: | --- |']
    cells = [f+'|'+d for f in FAMILIES for d in DAMAGES if f+'|'+d in panel]
    for key in cells:
        r = panel[key]['receiving_draw']['all']['recipient_effects']['extra_writing']
        b = panel[key]['fixed_output_pair']['all']['body_effects']['extra_writing']
        f,d = key.split('|')
        lines.append(f'| {f} | {d} | {pct(r["pooled_effect"])} pp | {triplet(r["changes"])} | '
            f'{pct(b["pooled_effect"])} pp | {triplet(b["changes"])} |')
    lines += ['', 'Positive extra recipient credit means the 1,000-update output is more useful '
        'than the 100-update output in the paired receiving tests. Positive extra body credit means '
        'the rebuilding body performs better after the same 1,000 physical steps. These are separate '
        'endpoints. A gain against 100 updates need not recover the original record or improve '
        'over preservation.', '']
    for key in cells:
        cell = panel[key]; r = cell['receiving_draw']['all']; fixed = cell['fixed_output_pair']['all']; record = cell['record_position']['all']
        levels = r['recipient_levels']; body = fixed['body_levels']
        lines += [f'## {key.replace("|", ": ")}', '',
            f'Recipient credit: original **{pct(levels[0])}%**, preserved incoming **{pct(levels[1])}%**, '
            f'100 updates **{pct(levels[2])}%**, 1,000 updates **{pct(levels[3])}%**. '
            f'Body credit: preserved **{pct(body[0])}%**, 100 updates **{pct(body[1])}%**, '
            f'1,000 updates **{pct(body[2])}%**.', '',
            f'Counts: {r["n"]:,} paired receiving observations, {fixed["n"]:,} fixed-output/corruption '
            f'pairs, {record["n"]:,} starting record positions, {record["contributing_blocks"]} blocks. '
            'Body outcomes are counted once per intervention pair.', '',
            '| Level of recipient comparison | Extra-writing gains / harms / ties |',
            '| --- | --- |']
        for level in LEVELS:
            lines.append(f'| {level} | {triplet(cell[level]["all"]["recipient_effects"]["extra_writing"]["changes"])} |')
        lines += ['', 'The next table tracks the sign of change against the same preserved incoming '
            'packet in each paired receiving test. Rows are the 100-update result; columns are '
            'the 1,000-update result.', '', '| 100 / 1,000 | Improved | Worsened | Tied |', '| --- | ---: | ---: | ---: |']
        transition = r['preservation_transition']
        for a in SIGNS:
            lines.append('| '+a+' | '+' | '.join(str(transition[a+'|'+b]) for b in SIGNS)+' |')
        newly_harmed = sum(transition[a+'|worsened'] for a in ('improved','tied'))
        rescued = sum(transition['worsened|'+b] for b in ('improved','tied'))
        lines += ['', f'Harms against preservation introduced after 100 updates: **{newly_harmed}**. '
            f'Earlier harms removed: **{rescued}**. Harms present under both budgets: '
            f'**{transition["worsened|worsened"]}**.', '',
            'Recipient/body joint changes below count each fixed-output pair once, averaging its '
            'receiving futures first. Rows are recipient changes; columns are body changes.', '',
            '| Recipient / body | Improved | Worsened | Tied |', '| --- | ---: | ---: | ---: |']
        joint = fixed['recipient_body_joint']
        for a in SIGNS:
            lines.append('| '+a+' | '+' | '.join(str(joint[a+'|'+b]) for b in SIGNS)+' |')
        lines += ['', 'History and injury strata below use starting record-position means. '
            'Pooled and equally weighted nonempty-block means are shown separately. All groups '
            'are descriptive and overlapping; no subset is chosen as a new enrollment rule.', '',
            '| Stratum | Records | Blocks | Extra recipient: pooled | Extra recipient: equal-block | Record gains / harms / ties | Extra body: pooled |',
            '| --- | ---: | ---: | ---: | ---: | --- | ---: |']
        for group in GROUPS[1:]:
            v = cell['record_position'][group]
            if not v['n']:
                lines.append(f'| {group} | 0 | 0 | — | — | — | — |'); continue
            e = v['recipient_effects']['extra_writing']; b = v['body_effects']['extra_writing']
            lines.append(f'| {group} | {v["n"]} | {v["contributing_blocks"]} | {pct(e["pooled_effect"])} pp | '
                f'{pct(e["equal_nonempty_block_effect"])} pp | {triplet(e["changes"])} | {pct(b["pooled_effect"])} pp |')
        lines.append('')
    lines += ['## Scope and retained evidence', '',
        'The complete 54-cell original preservation, writer and body-source control table is '
        'reconstructed independently from all source rows and retained in CONTROL_TABLE.json. '
        'Foreign and neutral 100-update arms do not exist and are not imputed. The full paired '
        'observations, eight-draw fixed-output comparisons and record means are retained per block; '
        'SUMMARY.json contains all contrasts, transition tables, joint tables and block means.', '',
        'The eight-draw paired-credit Hoeffding intervals saved per fixed output are pointwise, '
        'conditional and coarse. Observed mean signs do not precisely characterize individual '
        'capacities. The same developed/injured body and repair forcing are reused across corruptions; '
        'the unmodified branches repeat identical physical repairs with different receiving draws. '
        'Neither repeated bodies nor receiving draws are new population units. Group differences '
        'do not establish why a rewrite helps or harms. Serial durability, autonomous timing and '
        'biological transfer remain outside this analysis.', '',
        'Every source case and harm is retained. No threshold search, fitted classifier, selected '
        'policy, new significance test, sample extension or automatic successor was performed.', '']
    return '\n'.join(lines)
