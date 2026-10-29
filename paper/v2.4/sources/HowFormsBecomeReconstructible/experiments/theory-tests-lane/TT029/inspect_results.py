"""Record first inspection after completed table-margin and custody review."""
from common import *


def main():
    close = read_json(ROOT/'CLOSEOUT.json'); directory = ROOT/'runs/diagnosis_v1'
    assert close['status'] == 'PASS'
    assert close['summary_sha256'] == sha(directory/'SUMMARY.json')
    assert close['analysis_completion_sha256'] == sha(directory/'COMPLETE.json')
    write_json(ROOT/'RESULT_INSPECTION.json', dict(recorded_utc=now(), study='TT029',
        closeout_sha256=sha(ROOT/'CLOSEOUT.json'), summary_sha256=sha(directory/'SUMMARY.json'),
        inspection_after_review=True, source_population_already_exposed=True,
        no_new_confirmatory_test=True, new_dynamics=0, automatic_successor=False))
    value = read_json(directory/'SUMMARY.json'); findings = {}
    for key,levels in value['panel'].items():
        result = {}
        for level,groups in levels.items():
            result[level] = {}
            for name,g in groups.items():
                if not g['n']:
                    result[level][name] = dict(n=0); continue
                result[level][name] = {k:g[k] for k in ('n','contributing_blocks','recipient_levels','body_levels','donor_levels',
                    'preservation_transition','recipient_body_joint')}
                for field in ('recipient_effects','body_effects'):
                    result[level][name][field] = None if g[field] is None else {k:{f:v[f] for f in
                        ('pooled_effect','equal_nonempty_block_effect','changes','block_changes')} for k,v in g[field].items()}
        findings[key] = result
    write_json(ROOT/'FINDINGS.json', dict(study='TT029', recorded_utc=now(),
        summary_sha256=sha(directory/'SUMMARY.json'), closeout_sha256=sha(ROOT/'CLOSEOUT.json'),
        result_inspection_sha256=sha(ROOT/'RESULT_INSPECTION.json'),
        classification='EXPOSED_SAVED_DATA_DIAGNOSIS', panel=findings,
        all_cases_and_harms_retained=True, no_new_significance_tests=True, no_fitted_policy=True,
        source_primary_classification='NOT_CONFIRMED', new_dynamics=0))
    for key,levels in findings.items():
        draw = levels['receiving_draw']['all']; cases = levels['fixed_output_pair']['all']; records = levels['record_position']['all']
        t = draw['preservation_transition']
        print(key, json.dumps(dict(recipient_extra=draw['recipient_effects']['extra_writing'],
            body_extra=cases['body_effects']['extra_writing'],
            extra_harm_overlap=dict(new_late_harms=t['tied|worsened']+t['improved|worsened'],
                early_harms_removed=t['worsened|tied']+t['worsened|improved'],both=t['worsened|worsened']),
            record_change=records['recipient_effects']['extra_writing']['changes'])))
    key='residual|mix050'
    print('PRIMARY_CONDITION_HISTORY_AND_GEOMETRY')
    for name,g in findings[key]['record_position'].items():
        if name.startswith(('history:','injury:','history_injury:')):
            print(name,json.dumps(dict(n=g['n'],recipient_extra=g.get('recipient_effects',{}).get('extra_writing'),
                body_extra=(g.get('body_effects') or {}).get('extra_writing'))))
    print('PRIMARY_CONDITION_JOINT_FIXED_OUTPUT',json.dumps(findings[key]['fixed_output_pair']['all']['recipient_body_joint']))
    print('PRIMARY_CONDITION_JOINT_RECORD',json.dumps(findings[key]['record_position']['all']['recipient_body_joint']))
    print('PRIMARY_CONDITION_TRANSITIONS',json.dumps(findings[key]['receiving_draw']['all']['preservation_transition']))


if __name__ == '__main__': main()
