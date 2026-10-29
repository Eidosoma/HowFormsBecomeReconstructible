"""Check draft inference, allocation and unchanged forecasts using known fixtures.

Run with --run design_v1. Each attempt snapshots its exact inputs; it never
generates new native states, acquires test blocks, or launches a scientific job.
"""
import argparse
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shutil
import time
import traceback
import numpy as np
from scipy.stats import norm, t
from source_review import HERE, read, sha, dump, require
import future_statistics as stats
import forecast_adapter as forecast


def tail_interval(k, n, alpha):
    """Independent inversion of finite binomial tail sums by bisection."""
    def tail(p, start, stop):
        return math.fsum(math.comb(n, j)*p**j*(1-p)**(n-j) for j in range(start, stop))
    if k == 0:
        lower = 0.
    else:
        left, right = 0., 1.
        for _ in range(65):
            mid = (left+right)/2
            if tail(mid, k, n+1) < alpha/2:
                left = mid
            else:
                right = mid
        lower = (left+right)/2
    if k == n:
        upper = 1.
    else:
        left, right = 0., 1.
        for _ in range(65):
            mid = (left+right)/2
            if tail(mid, 0, k+1) > alpha/2:
                left = mid
            else:
                right = mid
        upper = (left+right)/2
    return [lower, upper]


def check_intervals():
    maximum_error, tested, coverage = 0., 0, []
    for n in (1, 8, 32, 64):
        for alpha in (.05, .05/384):
            intervals = np.array([stats.binomial_interval(k, n, alpha) for k in range(n+1)])
            for k, actual in enumerate(intervals):
                expected = tail_interval(k, n, alpha)
                error = max(abs(actual-np.array(expected)))
                require(error < 2e-12, 'Exact interval agrees with independent binomial tail inversion')
                maximum_error = max(maximum_error, float(error))
                tested += 1
            minimum = 1.
            for p in np.linspace(0, 1, 501):
                mass = [math.comb(n,k)*p**k*(1-p)**(n-k) for k in range(n+1)]
                covered = math.fsum(m for k, m in enumerate(mass) if intervals[k,0]-1e-14 <= p <= intervals[k,1]+1e-14)
                require(covered >= 1-alpha-1e-12, 'Binomial coverage on fixed finite probability grid')
                minimum = min(minimum, covered)
            coverage.append(dict(trials=n, alpha=alpha, minimum_grid_coverage=minimum, grid_points=501))
    width = {}
    for n in (8, 32, 64, 128):
        middle = stats.binomial_interval(n//2, n)
        width[str(n)] = dict(maximum_standard_error=.5/math.sqrt(n), half_success_interval95=middle,
                            half_success_interval_width=middle[1]-middle[0],
                            all_success_interval95=stats.binomial_interval(n, n))
    return dict(intervals_checked=tested, maximum_absolute_error=maximum_error, coverage_checks=coverage,
                precision=width, simultaneous_all_64_success_interval=stats.binomial_interval(64,64,.05/384))


def check_endpoints():
    body = np.ones((64, 64, 3, 18), dtype=bool)
    terminal = np.ones((64, 64, 3), dtype=bool)
    body[0, 0, 0, 0] = False
    terminal[0, 1, 0] = False
    e = stats.endpoints(body, terminal)
    require(not e['uninterrupted'][0,0,0] and e['last_body'][0,0,0] and e['terminal_record'][0,0,0],
            'Earlier failure remains distinct from both later outcomes')
    require(e['uninterrupted'][0,1,0] and e['last_body'][0,1,0] and not e['terminal_record'][0,1,0],
            'Passing body does not override failing outgoing-record assay')
    x = np.tile([True, True, False, False], 16)
    y = np.tile([False, True, True, False], 16)
    paired = stats.paired_probability_difference(x, y)
    require(paired['mean'] == 0 and paired['treated_only'] == paired['control_only'] == 16 and
            paired['conservative_interval'][0] < 0 < paired['conservative_interval'][1], 'Paired harms and rescues retained')
    for action in (lambda: stats.endpoints(body.astype(int), terminal),
                   lambda: stats.endpoints(body[..., :17], terminal),
                   lambda: stats.binomial_interval(65,64),
                   lambda: stats.block_interval(np.zeros(4096))):
        try:
            action()
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid domain or pseudoreplicated inference was accepted')
    return dict(terminal_body_record_disagreement_preserved=True, recovery_does_not_erase_failure=True,
                paired_harms_retained=True, invalid_domains_rejected=4)


def check_inference():
    values = np.array([((i//4)%5-2)/16 for i in range(64)], dtype=float)
    result = stats.block_interval(values)
    variance = sum(float(np.var(values[h::4], ddof=1))/16 for h in range(4))/16
    require(abs(result['se']**2-variance) < 1e-15 and result['independent_units'] == 64, 'Block rather than future precision')
    zero = stats.block_interval(np.zeros(64))
    require(zero['verdict'] != 'PASS' and zero['upper_one_sided95'] > 0, 'Degenerate sample does not imply certainty')
    negative = stats.block_interval(values-.25)
    require(negative['verdict'] == 'UNSUPPORTED', 'Unfavorable primary survives positive secondary scenarios')
    p = np.linspace(.05, .95, 64)
    y = np.arange(64)[None, :] < np.arange(64)[:, None]
    scores = stats.brier_per_record(p, y)
    q = y.mean(axis=1)
    require(np.max(abs(scores-((p-q)**2+q*(1-q)))) < 1e-14, 'Branch Brier decomposition')
    require(np.max(abs(scores-stats.brier_per_record(p,np.repeat(y,2,axis=1)))) < 1e-14,
            'Repeated stored rows do not alter the record-level score')
    anti = np.zeros((64,64), dtype=bool)
    anti[:32,:32] = True
    anti[32:,32:] = True
    covariance = stats.split_half_covariance(anti)
    require(covariance['mean_within_history_covariance'] < 0, 'Negative split-half estimates remain negative')
    return dict(block_variance_checked=True, independent_units=64, zero_variance_fallback=True,
                negative_primary_preserved=True, brier_identity=True, negative_split_half_retained=True)


def check_allocation(design):
    allocation = [dict(offset=i, history=i%4, case=i//4, founder=(i//4)//4, recipient=(i//4)%4) for i in range(64)]
    for h in range(4):
        require(sorted(r['case'] for r in allocation if r['history']==h) == list(range(16)), 'Every case position once per history')
    keys = set()
    for record in range(64):
        for future in range(64):
            for gen in range(15, 33):
                for source, cues in [('injury',(None,)),('reset',(0,1)),('forcing',(0,1))]:
                    for cue in cues:
                        key = stats.stream_key('technical_record_'+str(record),future,gen,source,cue)
                        require(key not in keys, 'Unique source key per independent future and generation')
                        keys.add(key)
            for source, cues in [('terminal_injury',(None,)),('terminal_reset',(0,1)),('terminal_forcing',(0,1))]:
                for cue in cues:
                    key = stats.stream_key('technical_record_'+str(record),future,32,source,cue)
                    require(key not in keys, 'Fresh terminal source distinct from continuation')
                    keys.add(key)
    require(len(keys) == 64*64*(18*5+5), 'Complete planned allocation')
    return dict(allocation=allocation, unique_source_keys_checked=len(keys), policy_not_part_of_stream_key=True,
                physical_random_draws_generated=False, statistical_independence_not_proven_by_hash_uniqueness=True)


def check_forecasts():
    source = HERE/'sources/tt008'
    models = read(source/'FROZEN_MODELS.json')
    def key(row):
        return tuple(row[k] for k in ('block','history','founder','recipient'))
    with (source/'features.csv').open(newline='') as stream:
        features = {key(row):row for row in csv.DictReader(stream)}
    maximum, tested = 0., 0
    with (source/'predictions.csv').open(newline='') as stream:
        for row in csv.DictReader(stream):
            if row['model'] in forecast.MODELS:
                prediction = forecast.predict(features[key(row)],models[row['model']])
                error = abs(prediction-float(row['probability']))
                require(error < 2e-14, 'Unchanged TT008 probabilities reproduced by scalar adapter')
                maximum = max(maximum, error)
                tested += 1
    require(len(features)==4096 and tested==4096*3, 'All prior cohort predictions under three principal models')
    return dict(archived_records=len(features), frozen_predictions_checked=tested,
                maximum_absolute_error=maximum, refitting=False,
                new_boundary_feature_extraction_qualified=False, fresh_forecasts_sealed=False)


def resource_plan(design):
    benchmark = read(HERE/'sources/tt017/benchmark.json')
    timeparts = benchmark['timings_seconds']
    records, futures, policies = 64,64,3
    contexts = records*futures*policies*18
    terminals = records*futures*policies
    repairs = records*futures*19
    # A planning extrapolation only. Changed batching must be measured directly.
    teaching = 64*timeparts['teaching']
    acquisition = 64*14*timeparts['maximum_preliminary_rebuild']
    continuation = contexts*timeparts['maximum_continuation_with_replay']/128
    assays = terminals*timeparts['maximum_continuation_with_replay']/128
    repair = repairs*timeparts['complete_checked_repairs']/96
    proxy = 1.5*(teaching+acquisition+continuation+assays+repair)+900
    sensitivity = []
    critical = float(t.ppf(.95,15))
    for sd in (.10,.20,.30,.50):
        for effect in (.02,.05,.10):
            power = float(norm.sf(critical-(effect-.02)/(sd/math.sqrt(64))))
            sensitivity.append(dict(block_sd_assumption=sd,effect_assumption=effect,
                approximate_normal_power_with_t15_critical=power))
    return dict(selected_starting_records=records, independent_blocks=64, futures_per_record=futures,
        paired_future_environments=records*futures, policy_chains=records*futures*policies,
        preliminary_contexts=64*16*14, continuation_contexts=contexts, fresh_terminal_contexts=terminals,
        scheduled_repair_calls=repairs, full_dynamics_replay_planned=True,
        planning_runtime_seconds=proxy, planning_runtime_hours=proxy/3600,
        timing_status='Unqualified linear proxy from a completed TT017 technical benchmark; no permission to launch.',
        maximum_forecast_seconds=design['maximum_forecast_seconds'],
        population_power_sensitivity=sensitivity,
        scope='TT016/TT017 block SDs average 16 records and must not be transported as measured variance for one selected record per block.')


def main(name):
    require(name.replace('_','').isalnum(), 'Safe unique output name')
    output = HERE/'checks'/name
    output.mkdir(parents=True,exist_ok=False)
    started = time.monotonic()
    inputs = ['design.json','future_statistics.py','forecast_adapter.py','check_design.py',
              'SOURCE_REVIEW.json','PREPARATION_INPUTS.json']
    manifest = {name:sha(HERE/name) for name in inputs}
    (output/'inputs').mkdir()
    for name in inputs:
        shutil.copyfile(HERE/name,output/'inputs'/name)
    dump(output/'manifest.json', dict(recorded_utc=datetime.now(timezone.utc).isoformat(),inputs_sha256=manifest,
        source_bindings_sha256=sha(HERE/'PREPARATION_INPUTS.json'),fresh_native_outcomes_generated=False))
    try:
        for receipt, field in [('SOURCE_REVIEW.json','sources'),('PREPARATION_INPUTS.json','files')]:
            for binding in read(HERE/receipt)[field]:
                require(sha(HERE/binding['local'])==binding['sha256'],'Retained source binding')
        design=read(HERE/'design.json')
        result=dict(status='ANALYSIS_AND_DESIGN_CHECKS_PASS', intervals=check_intervals(),
            endpoints=check_endpoints(), inference=check_inference(), allocation=check_allocation(design),
            forecasts=check_forecasts(), resource_plan=resource_plan(design),
            native_branching_qualified=False, full_native_benchmark_passed=False,
            fresh_native_outcomes_generated=False, registration_complete=False,
            seconds=time.monotonic()-started)
        require(manifest=={name:sha(HERE/name) for name in inputs},'Draft inputs unchanged during checks')
        dump(output/'RESULTS.json',result)
        done=dict(status=result['status'],utc=datetime.now(timezone.utc).isoformat(),seconds=time.monotonic()-started,
            results_sha256=sha(output/'RESULTS.json'),manifest_sha256=sha(output/'manifest.json'),
            native_branching_qualified=False,new_cohort_started=False)
        dump(output/'COMPLETE.json',done)
        print(json.dumps(done,indent=2))
    except BaseException:
        dump(output/'FAILED.json',dict(status='FAILED',utc=datetime.now(timezone.utc).isoformat(),
            seconds=time.monotonic()-started,traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',required=True)
    main(parser.parse_args().run)
