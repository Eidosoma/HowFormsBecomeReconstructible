"""Check diagnostic table margins and retained evidence before displaying results."""
import math
from common import *


def main():
    directory = ROOT/'runs/diagnosis_v1'
    complete = read_json(directory/'COMPLETE.json')
    assert complete['status'] == 'COMPLETE' and not (directory/'FAILED.json').exists()
    frozen = read_json(ROOT/'FREEZE.json')
    assert complete['freeze_sha256'] == sha(ROOT/'FREEZE.json')
    verify(complete['outputs']); verify(frozen['inputs']); verify(frozen['evidence'])
    value = read_json(directory/'SUMMARY.json')
    assert value['verification'] == frozen['planned_verification'] == complete['verification']
    assert value['source_registered_inference']['primary_classification'] == 'NOT_CONFIRMED'
    assert len(value['source_controls']) == 54
    reviewed = 0
    for levels in value['panel'].values():
        assert set(levels) == set(LEVELS)
        for level,groups in levels.items():
            assert set(groups) == set(GROUPS)
            for group in groups.values():
                if not group['n']: continue
                reviewed += 1
                transition = group['preservation_transition']
                short = group['recipient_effects']['short_vs_preservation']['changes']
                full = group['recipient_effects']['full_vs_preservation']['changes']
                for s in SIGNS:
                    assert sum(transition[s+'|'+b] for b in SIGNS) == short[s]
                    assert sum(transition[a+'|'+s] for a in SIGNS) == full[s]
                joint = group['recipient_body_joint']
                if level == LEVELS[0]:
                    assert joint is None and group['body_effects'] is None
                else:
                    for s in SIGNS:
                        assert sum(joint[s+'|'+b] for b in SIGNS) == group['recipient_effects']['extra_writing']['changes'][s]
                        assert sum(joint[a+'|'+s] for a in SIGNS) == group['body_effects']['extra_writing']['changes'][s]
                for metrics in (group['recipient_effects'], group['body_effects']):
                    if metrics is None: continue
                    for v in metrics.values():
                        assert sum(v['changes'].values()) == group['n']
                        counts = v['block_counts']; blocks = v['blocks']
                        assert set(counts) == set(blocks) and sum(counts.values()) == group['n']
                        pooled = math.fsum(blocks[k]*counts[k] for k in blocks)/group['n']
                        equal = math.fsum(blocks.values())/len(blocks)
                        assert abs(pooled-v['pooled_effect']) <= 2e-15
                        assert abs(equal-v['equal_nonempty_block_effect']) <= 2e-15
                        assert sum(v['block_changes'].values()) == len(blocks)
            assert groups['all']['contributing_blocks'] == 64
            assert groups['all']['n'] == {'receiving_draw':16384,'fixed_output_pair':2048,'record_position':1024}[level]
    receipt = dict(status='PASS', completed_utc=now(), study='TT029',
        analysis_completion_sha256=sha(directory/'COMPLETE.json'), summary_sha256=sha(directory/'SUMMARY.json'),
        reviewed_nonempty_groups=reviewed, transition_margins_match=True, joint_recipient_body_margins_match=True,
        block_weighting_and_counts_match=True, complete_original_control_table_retained=True,
        frozen_inputs_unchanged=True, original_primary_classification_preserved=True,
        source_population_already_exposed=True, new_scientific_effects_displayed_before_review=False,
        new_dynamics=0, new_receiving_assays=0, no_fitted_policy=True,
        no_new_significance_tests=True, automatic_successor=False, code_sha256=sha(__file__))
    write_json(ROOT/'CLOSEOUT.json', receipt)
    print(receipt, flush=True)


if __name__ == '__main__': main()
