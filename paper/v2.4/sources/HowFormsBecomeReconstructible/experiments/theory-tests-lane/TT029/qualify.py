"""Excluded-data workflow checks and targeted mutation tests; no new physics."""
import copy
from datetime import datetime, timezone
import io
import os
import signal
import time
import traceback
import numpy as np
from common import *
import diagnose
import execute
import report


def main():
    destination = ROOT/'checks/qualification_v1'; destination.mkdir(parents=True, exist_ok=False)
    benchmark = ROOT/'checks/benchmark_v1'; benchmark.mkdir(parents=True, exist_ok=False)
    tick = time.monotonic(); checks = []
    def expire(*_): raise TimeoutError('TT029 qualification exceeded 600 seconds')
    signal.signal(signal.SIGALRM, expire); signal.alarm(600)
    def rejects(name, function):
        try: function()
        except AssertionError: checks.append(name)
        else: raise AssertionError('mutation accepted: '+name)
    try:
        resource = read_json(ROOT/'QUALIFICATION_RESOURCE_CHECK.json')
        assert resource['admission_pass'] and (datetime.now(timezone.utc)-datetime.fromisoformat(resource['recorded_utc'])).total_seconds() < 180
        os.sched_setaffinity(0, {resource['cpu']})
        manifest = read_json(ROOT/'SOURCE_MANIFEST.json'); verify(manifest['evidence'])
        frozen_inputs = execute.inputs(); custody = Custody(dict(manifest['benchmark_files'], **manifest['evidence']))
        write_json(destination/'RUNNING.json', dict(started_utc=now(), inputs=frozen_inputs, new_dynamics=0))
        timings = []; retained = []
        for index in EXCLUDED:
            value = diagnose.process(UPSTREAM/f'runs/benchmark_v1/tissue_{index}', custody)
            execute.retain(benchmark/f'tissue_{index}', value)
            timings.append(value['timing']); retained.append(value)
        checks.append('excluded_source_full_panel_and_checkpoint_prefixes_pass')
        summarized = execute.summarize(benchmark, EXCLUDED, 'benchmark', custody)
        write_json(benchmark/'SUMMARY.json', summarized)
        write_json(benchmark/'CONTROL_TABLE.json', summarized['source_controls'])
        text = report.render(summarized)
        assert text == report.render(read_json(benchmark/'SUMMARY.json'))
        with (benchmark/'REPORT.md').open('x') as stream: stream.write(text)
        checks.append('report_roundtrip_and_declared_table_order')
        directory = UPSTREAM/f'runs/benchmark_v1/tissue_{EXCLUDED[0]}'
        rows = custody.json(directory/'ROWS.json'); bodies = custody.json(directory/'BODIES.json'); config = custody.json(directory/'CONFIG.json')
        baseline = diagnose.validate_source(rows,bodies,config)
        reversed_map = diagnose.validate_source(list(reversed(rows)),list(reversed(bodies)),config)
        assert diagnose.pair_rows(baseline) == diagnose.pair_rows(reversed_map)
        checks.append('row_and_body_order_invariance')
        rejects('missing_paired_observation_rejected',lambda:diagnose.validate_source(rows[:-1],bodies,config))
        rejects('duplicated_observation_rejected',lambda:diagnose.validate_source(rows+[rows[0]],bodies,config))
        for field,value,name in (
            ('full_budget_outgoing',0. if rows[0]['full_budget_outgoing'] != 0 else 1.,'wrong_matched_comparator_rejected'),
            ('developed_score',0. if rows[0]['developed_score'] != 0 else 1.,'wrong_history_reference_rejected'),
            ('outgoing',float('nan'),'nonfinite_credit_rejected'),
            ('outgoing',.2,'unsupported_fractional_credit_rejected'),
            ('message',(rows[0]['message']+1)%4,'wrong_message_identity_rejected')):
            changed = copy.deepcopy(rows); changed[0][field] = value
            rejects(name,lambda changed=changed:diagnose.validate_source(changed,bodies,config))
        rejects('missing_body_intervention_rejected',lambda:diagnose.validate_source(rows,bodies[:-1],config))
        assert units(1/3)==4 and units(.25)==3 and units(.5)==6
        checks.append('fractional_credits_preserved_in_twelfths')

        # Three draws: positive, negative and tied recipient changes, with one fixed body loss.
        synthetic = []
        for draw,(before,after) in enumerate(((3,4),(4,3),(6,6))):
            synthetic.append(dict(block=7,corruption=0,family='residual',damage='mix050',world=0,message=0,
                history='unique_pass',developed_units=12,injury=STRATA[0],draw=draw,n_draws=1,body_repeats=1,
                recipient=[12,6,before,after],donor=[0,0,0],body=[12,12,6]))
        cases = diagnose.fold(synthetic); records = diagnose.fold(cases,record=True)
        out = diagnose.finish(diagnose.aggregate((synthetic,cases,records)))['residual|mix050']
        assert out['receiving_draw']['all']['recipient_effects']['extra_writing']['changes'] == dict(improved=1,worsened=1,tied=1)
        assert out['fixed_output_pair']['all']['n']==out['record_position']['all']['n']==1
        assert out['fixed_output_pair']['all']['recipient_body_joint']['tied|worsened']==1
        assert out['fixed_output_pair']['all']['body_effects']['extra_writing']['pooled_effect']==-.5
        assert out['receiving_draw']['all']['body_effects'] is None
        assert cases[0]['pointwise_conditional_change_interval_95'][0] < 0 < cases[0]['pointwise_conditional_change_interval_95'][1]
        checks.append('recipient_draws_do_not_multiply_bodies_and_cancelled_means_are_tied')
        checks.append('pointwise_conditional_interval_keeps_receiving_uncertainty')
        for level in LEVELS:
            effects = out[level]['all']['recipient_effects']
            assert abs(effects['short_vs_preservation']['pooled_effect']+effects['extra_writing']['pooled_effect']-effects['full_vs_preservation']['pooled_effect'])<2e-15
        checks.append('independent_signed_decomposition_at_all_three_levels')
        duplicated = synthetic+[synthetic[0]]
        rejects('duplicate_draw_within_fixed_output_rejected',lambda:diagnose.fold(duplicated))
        bad_body = copy.deepcopy(synthetic); bad_body[1]['body'][0] = 0
        rejects('body_reference_mismatch_across_receiving_draws_rejected',lambda:diagnose.fold(bad_body))
        two = copy.deepcopy(cases); two.append(copy.deepcopy(cases[0])); two[1]['corruption']=1
        rec = diagnose.fold(two,record=True)[0]
        assert rec['n_draws']==6 and rec['body_repeats']==2 and rec['body']==[24,24,12]
        checks.append('two_corruptions_averaged_without_inventing_body_replicates')
        merged = {}
        for value in retained: diagnose.merge(merged,value['aggregate'])
        direct = diagnose.aggregate(tuple([r for v in retained for r in v[k]] for k in ('pairs','cases','records')))
        assert serialized(merged)==serialized(direct)
        checks.append('streamed_block_aggregation_equals_direct_observations')

        folder = directory/'corruption_00/residual/mix050/own'
        data = []
        for arm in SELECTED[1:]:
            with np.load(io.BytesIO(custody.data(folder/(arm+'_repair.npz'))),allow_pickle=False) as raw:
                data.append({k:raw[k].copy() for k in raw.files})
        assert diagnose.check_prefix(*data)==dict(shared_checkpoint_arrays=12,short_gate_hold_arrays=2)
        changed=copy.deepcopy(data);a=changed[1]['s100_R'];a.flat[0]=np.nextafter(a.flat[0],np.inf)
        rejects('one_ulp_prefix_state_mutation_rejected',lambda:diagnose.check_prefix(*changed))
        changed=copy.deepcopy(data);a=changed[0]['s1000_theta'];a.flat[0]=np.nextafter(a.flat[0],np.inf)
        rejects('post_gate_one_ulp_packet_change_rejected',lambda:diagnose.check_prefix(*changed))
        changed=copy.deepcopy(data);changed[0]['s1_V'].flat[0]=np.nan
        rejects('nonfinite_saved_state_rejected',lambda:diagnose.check_prefix(*changed))
        verify(custody.consumed); assert execute.inputs()==frozen_inputs
        write_json(benchmark/'COMPLETE.json',dict(status='PASS',completed_utc=now(),inputs=frozen_inputs,
            block_timings=timings,verification=summarized['verification'],outputs={str(p):sha(p) for p in sorted(benchmark.rglob('*')) if p.is_file()},
            science_effects_displayed_or_used_for_scope=False,new_dynamics=0,new_receiving_assays=0))
        receipt=dict(status='PASS',completed_utc=now(),seconds=time.monotonic()-tick,inputs=frozen_inputs,
            checks=checks,source_custody_pass=True,new_dynamics=0,new_receiving_assays=0,
            benchmark_scientific_effects_displayed_or_used_for_scope=False)
        write_json(destination/'COMPLETE.json',receipt);signal.alarm(0)
        print(dict(status='PASS',checks=len(checks),seconds=receipt['seconds'],block_timings=timings,new_dynamics=0),flush=True)
    except BaseException as error:
        write_json(destination/'FAILED.json',dict(status='FAILED',failed_utc=now(),error=repr(error),traceback=traceback.format_exc(),automatic_retry=False))
        raise


if __name__ == '__main__': main()
