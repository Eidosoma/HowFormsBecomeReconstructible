#!/usr/bin/env python3
"""Regret certificates from immutable agent-available risk intervals."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal as D
import json
import math
import os
from pathlib import Path
import platform
import statistics as stats
import time
import traceback

import check_fep_local_risk_bound as prior

ZERO, ONE, TAU, PAD = D(0), D(1), D('.1'), D('1e-30')
GUARD, NUMTOL, KKTTOL, TOL, TIE = D('1e-25'), D('1e-25'), D('1e-20'), 1e-10, 1e-12
LN2 = D(2).ln()
COUNTS, RESIDUALS = prior.COUNTS, prior.RESIDUALS
check, close, read, write, identity = prior.check, prior.close, prior.read, prior.write, prior.identity
HERE = Path(__file__).resolve().parent
BASE = Path('/mnt/bioIce1/fep-ideas/formal-checks')
MAIN = BASE/'fep-structured-inference-v1/main-attempt-01'
OLD = BASE/'fep-local-risk-correction-v1/attempt-01'
DEST = BASE/'fep-decision-regret-v1/attempt-01'
SPEC = HERE/'FEP_DECISION_REGRET_V1.md'
FAMILIES, DOMAINS = ('signed', 'combined'), ('global', 'original_cap')
FIELDS = {'h', 'a', 'g', 'plus_source', 'plus_target', 'minus_source', 'minus_target',
          'l0', 'l1', 'u0', 'u1', 'selected', 'original_cap'}


def dec_close(a, b, label):
    residual = abs(D(a)-D(b))
    RESIDUALS[label] = max(RESIDUALS.get(label, 0.), float(residual))
    check(residual <= NUMTOL, label)


def le(a, b, label, tolerance=TOL):
    excess = float(a)-float(b)
    RESIDUALS[label] = max(RESIDUALS.get(label, 0.), max(0., excess))
    check(math.isfinite(excess) and excess <= tolerance, label)


def require(ok, label):
    if not ok:
        raise ValueError(label)


def clip(x, lower, upper):
    return max(lower, min(upper, x))


class ScalarCache:
    def __init__(self):
        self.entropies = {ZERO: LN2, ONE: LN2}
        self.stationary_points = {}
        self.entropy_calls = 0
        self.stationary_calls = 0

    def k(self, r):
        if r not in self.entropies:
            self.entropies[r] = LN2+r*r.ln()+(1-r)*(1-r).ln()
            self.entropy_calls += 1
        return self.entropies[r]

    def stationary(self, slope):
        if slope not in self.stationary_points:
            self.stationary_points[slope] = ONE/(ONE+(-D('.6')+2*slope).exp())
            self.stationary_calls += 1
        return self.stationary_points[slope]


def affine(line, r):
    return line[0]+line[1]*r


def interval(env, r):
    return max(affine(line, r) for line in env['lower']), min(affine(line, r) for line in env['upper'])


def compile_envelopes(view):
    """Strictly whitelisted quantities from the agent's existing certificate."""
    require(set(view) == FIELDS, 'unexpected or missing agent-view field')
    v = {key: D(value) for key, value in view.items()}
    h, delta = v['h'], TAU-v['h']
    physical_lower, physical_upper = (h, h*(1-h)), (TAU, TAU*(1-TAU))
    lower = (v['a']-delta*v['minus_target']-PAD,
             v['g']-delta*((1-h)*v['minus_source']-h*v['minus_target']))
    upper = (v['a']+delta*v['plus_target']+PAD,
             v['g']+delta*((1-h)*v['plus_source']-h*v['plus_target']))
    envs = dict(signed=dict(lower=[physical_lower, lower], upper=[physical_upper, upper]),
                combined=dict(lower=[physical_lower, lower, (v['l0'], v['l1']-v['l0'])],
                              upper=[physical_upper, upper, (v['u0'], v['u1']-v['u0'])]))
    return v, envs


def validate_inputs(h, s, original_cap, envs):
    require(ZERO < h < TAU, 'invalid physical h')
    require(ZERO <= s <= original_cap <= ONE, 'invalid current choice or original cap')
    for env in envs.values():
        require(bool(env['lower']) and bool(env['upper']), 'empty risk envelope')
        require(all(line[0] <= TAU+NUMTOL for line in env['lower']), 'economy excluded by lower envelope')
        for r in (ZERO, ONE):
            lo, hi = interval(env, r)
            require(lo <= hi+NUMTOL, 'inconsistent risk interval')
    require(interval(envs['combined'], s)[1] <= TAU+NUMTOL, 'current choice is not certified feasible')


def relaxed_cap(lower_lines, comparator_cap):
    cap = comparator_cap
    for a, b in lower_lines:
        if b > 0:
            cap = min(cap, max(ZERO, (TAU-a+PAD)/b+PAD))
    return cap


def lower_objective(lower_lines, r, cache):
    return cache.k(r)-5-D('.6')*r+2*max(affine(line, r) for line in lower_lines)


def verify_subgradient(lower_lines, r, cap):
    check(ZERO <= r <= cap, 'lower optimizer within relaxed domain')
    if cap == 0:
        check(r == 0, 'single-point lower optimization')
        return 'single_point'
    check(ZERO < r < ONE, 'nondegenerate entropy optimizer')
    value = max(affine(line, r) for line in lower_lines)
    active = [b for a, b in lower_lines if abs(a+b*r-value) <= NUMTOL]
    derivative = (r/(1-r)).ln()-D('.6')
    left, right = derivative+2*min(active), derivative+2*max(active)
    check(left <= KKTTOL, 'lower optimizer left subgradient')
    if r < cap:
        check(right >= -KKTTOL, 'lower optimizer right subgradient')
    return 'cap' if r == cap else 'kink' if len(set(active)) > 1 else 'stationary'


def minimize_lower(lower_lines, cap, cache):
    candidates = {ZERO, cap}
    for _, b in lower_lines:
        candidates.add(clip(cache.stationary(b), ZERO, cap))
    for i, (a, b) in enumerate(lower_lines):
        for aa, bb in lower_lines[i+1:]:
            if b != bb:
                crossing = (aa-a)/(b-bb)
                if ZERO <= crossing <= cap:
                    candidates.add(crossing)
    value, r = min((lower_objective(lower_lines, x, cache), x) for x in candidates)
    kind = verify_subgradient(lower_lines, r, cap)
    return dict(r=r, value=value-GUARD, kind=kind, candidates=len(candidates))


def psi(r, slope, cache):
    return cache.k(r)-D('.6')*r+2*slope*r


def one_family(h, s, original_cap, env, cache):
    l0, u0 = interval(env, ZERO)
    l1, u1 = interval(env, ONE)
    glo = max(h*(1-TAU), l1-u0-PAD)
    ghi = min(TAU*(1-h), u1-l0+PAD)
    require(glo <= ghi+NUMTOL, 'empty physical risk-slope interval')
    upper_selected = cache.k(s)-5-D('.6')*s+2*interval(env, s)[1]+GUARD
    result = dict(slope_lower=glo, slope_upper=ghi, selected_objective_upper=upper_selected)
    for domain, outer_cap in (('global', ONE), ('original_cap', original_cap)):
        cap = relaxed_cap(env['lower'], outer_cap)
        require(s <= cap+NUMTOL, 'current choice excluded by relaxed comparator')
        minimum = minimize_lower(env['lower'], cap, cache)
        level = upper_selected-minimum['value']
        check(level >= -NUMTOL, 'nonnegative pointwise regret certificate')
        left = clip(cache.stationary(ghi), ZERO, s)
        right = clip(cache.stationary(glo), s, cap)
        slope = max(ZERO, psi(s, ghi, cache)-psi(left, ghi, cache),
                    psi(s, glo, cache)-psi(right, glo, cache))+2*GUARD
        level = max(ZERO, level)
        result[domain] = dict(relaxed_cap=cap, level_bound=level, slope_bound=slope,
                              bound=min(level, slope), lower_optimum=minimum,
                              slope_left_argmin=left, slope_right_argmin=right)
    return result


def derive(h, s, original_cap, envs):
    """Pure interval/objective calculation. No reference or saved outcome input."""
    start = time.process_time()
    validate_inputs(h, s, original_cap, envs)
    cache = ScalarCache()
    result = {name: one_family(h, s, original_cap, envs[name], cache) for name in FAMILIES}
    for domain in DOMAINS:
        for key in ('level_bound', 'slope_bound', 'bound'):
            check(result['combined'][domain][key] <= result['signed'][domain][key]+NUMTOL,
                  'combined information tightens '+key)
    for name in FAMILIES:
        for key in ('level_bound', 'slope_bound', 'bound'):
            check(result[name]['original_cap'][key] <= result[name]['global'][key]+NUMTOL,
                  'restricted comparator tightens '+key)
    result['cpu'] = time.process_time()-start
    result['entropy_calls'] = cache.entropy_calls
    result['stationary_calls'] = cache.stationary_calls
    return result


def construct(view):
    v, envs = compile_envelopes(view)
    return envs, derive(v['h'], v['selected'], v['original_cap'], envs)


def evaluate(result, envs, s, original_cap, a, g, saved=None):
    """Exact-reference scoring starts here, after the regret certificate exists."""
    optimum = min(prior.free(g), (TAU-a)/g)
    capped = min(optimum, original_cap)
    risk, chosen_j = prior.score(s, a, g)
    le(risk, TAU, 'retained choice exact feasibility')
    regrets = {}
    for domain, r in (('global', optimum), ('original_cap', capped)):
        _, best_j = prior.score(r, a, g)
        regret = chosen_j-best_j
        le(0, regret, 'true '+domain+' regret nonnegative')
        regrets[domain] = regret
        for name in FAMILIES:
            item = result[name][domain]
            le(r, item['relaxed_cap'], name+' '+domain+' feasible comparator enclosure')
            le(item['lower_optimum']['value'], best_j, name+' '+domain+' lower optimum valid')
            le(chosen_j, result[name]['selected_objective_upper'], name+' selected objective upper valid')
            for method in ('level_bound', 'slope_bound', 'bound'):
                le(regret, item[method], name+' '+domain+' '+method+' regret coverage')
    for name in FAMILIES:
        le(result[name]['slope_lower'], g, name+' true slope lower coverage')
        le(g, result[name]['slope_upper'], name+' true slope upper coverage')
        for rr in (ZERO, ONE, s, optimum, capped):
            lo, hi = interval(envs[name], rr)
            le(lo, a+rr*g, name+' inherited risk lower coverage')
            le(a+rr*g, hi, name+' inherited risk upper coverage')
    if saved is not None:
        close(s, saved['policies']['combined']['r'], 'unchanged certified choice')
        close(risk, saved['policies']['combined']['actual_risk'], 'reproduced certified risk')
        close(regrets['global'], saved['policies']['combined']['objective_regret'], 'reproduced global regret')
        close(optimum, saved['exact_r'], 'reproduced exact decision')
    return dict(exact_r=optimum, exact_capped_r=capped, actual_risk=risk,
                global_regret=regrets['global'], capped_regret=regrets['original_cap'],
                cap_loss=regrets['global']-regrets['original_cap'])


def scalar_case(name, h, a, g, s, cap, extras=None):
    physical_lo, physical_hi = (h, h*(1-h)), (TAU, TAU*(1-TAU))
    exact = (a, g)
    if extras is None:
        low, high = [physical_lo, exact], [physical_hi, exact]
    else:
        low, high = [physical_lo]+extras[0], [physical_hi]+extras[1]
    envs = dict(signed=dict(lower=low, upper=high),
                combined=dict(lower=low+[exact], upper=high+[exact]))
    result = derive(h, s, cap, envs)
    actual = evaluate(result, envs, s, cap, a, g)
    return dict(name=name, h=h, true_a=a, true_g=g, selected=s, original_cap=cap,
                intervals=envs, certificates=result, evaluation=actual)


def qualify():
    rows = []
    cases = [
        ('exact_binding', '.01', '.08', '.08', '.2', '.4'),
        ('exact_free', '.01', '.01', '.02', '.5', '.8'),
        ('economy_only', '.01', '.1', '.04', '0', '.3'),
        ('original_cap_limited', '.01', '.01', '.04', '.1', '.2'),
        ('negative_auxiliary_slope', '.01', '.065', '.06', '.02', '.3'),
        ('kink_minimum', '1e-6', '.099', '.002', '.1', '.6'),
        ('parallel_constant', '.01', '.04', '.05', '.1', '.4'),
        ('exact_optimum', '.01', '.02', '.04', None, '.8'),
        ('endpoint_choice', '.01', '.01', '.02', '1', '1'),
    ]
    extras = {
        'negative_auxiliary_slope': ([('.03', '-.02'), ('.025', '.10')], [('.075', '.08')]),
        'kink_minimum': ([('.099', '-.13'), ('-.027', '.05')], [('.099', '.002')]),
        'parallel_constant': ([('.02', '.05'), ('.02', '.05'), ('.03', '0')], [('.05', '.06')]),
    }
    for name, h, a, g, s, cap in cases:
        extra = extras.get(name)
        if extra is not None:
            extra = tuple([tuple(map(D, line)) for line in lines] for lines in extra)
        s = prior.free(D(g)) if s is None else D(s)
        row = scalar_case(name, D(h), D(a), D(g), s, D(cap), extra)
        if name == 'kink_minimum':
            dec_close(row['certificates']['signed']['global']['lower_optimum']['r'], D('.7'), 'intended kink optimizer')
            check(row['certificates']['signed']['global']['lower_optimum']['kind'] == 'kink', 'kink branch exercised')
        if name == 'exact_optimum':
            check(row['certificates']['combined']['global']['bound'] < KKTTOL, 'exact optimum near-zero bound')
        if name == 'economy_only':
            check(row['evaluation']['exact_r'] == 0, 'economy-only true optimum')
        rows.append(row)
    for name in ('infeasible_current', 'inconsistent_interval'):
        h = D('.01')
        pl, pu = (h, h*(1-h)), (TAU, TAU*(1-TAU))
        upper = (D('.08'), D('.08')) if name == 'infeasible_current' else (D('.09'), D('.02'))
        env = dict(lower=[pl, (D('.08'), D('.08'))], upper=[pu, upper])
        rejected, reason = False, ''
        try:
            derive(h, D('.4') if name == 'infeasible_current' else D('.1'), D('.4'),
                   dict(signed=env, combined=env))
        except ValueError as error:
            rejected, reason = True, str(error)
        check(rejected, name+' rejected')
        rows.append(dict(name=name, rejected=rejected, reason=reason))
    return rows


def summarize(records):
    result = dict(queries=len(records),
                  actual_global_regret=stats.fmean(r['evaluation']['global_regret'] for r in records),
                  actual_capped_regret=stats.fmean(r['evaluation']['capped_regret'] for r in records),
                  actual_cap_loss=stats.fmean(r['evaluation']['cap_loss'] for r in records),
                  regret_cpu=sum(r['certificates']['cpu'] for r in records),
                  entropy_calls=sum(r['certificates']['entropy_calls'] for r in records),
                  stationary_calls=sum(r['certificates']['stationary_calls'] for r in records))
    for name in FAMILIES:
        result[name] = {}
        for domain in DOMAINS:
            pp = [r['certificates'][name][domain] for r in records]
            truth = [r['evaluation']['global_regret' if domain == 'global' else 'capped_regret'] for r in records]
            bounds = [float(p['bound']) for p in pp]
            deltas = [float(p['level_bound']-p['slope_bound']) for p in pp]
            result[name][domain] = dict(mean_bound=stats.fmean(bounds), max_bound=max(bounds),
                                       mean_level_bound=stats.fmean(float(p['level_bound']) for p in pp),
                                       mean_slope_bound=stats.fmean(float(p['slope_bound']) for p in pp),
                                       mean_slack=stats.fmean(b-t for b, t in zip(bounds, truth)),
                                       max_slack=max(b-t for b, t in zip(bounds, truth)),
                                       near_zero=sum(p['bound'] <= KKTTOL for p in pp),
                                       slope_better=sum(x > TIE for x in deltas),
                                       level_better=sum(x < -TIE for x in deltas),
                                       tied=sum(abs(x) <= TIE for x in deltas),
                                       minimum_kinds=dict(Counter(p['lower_optimum']['kind'] for p in pp)))
    return result


def aggregate(rows):
    output = {}
    for level in (256, 1024, 4096):
        for kind in ('mf', 'block'):
            rr = [row for row in rows if row['kind'] == kind and row['level'] == level]
            item = {key: stats.fmean(row[key] for row in rr) for key in
                    ('actual_global_regret', 'actual_capped_regret', 'actual_cap_loss', 'regret_cpu')}
            item.update({key: sum(row[key] for row in rr) for key in ('queries', 'entropy_calls', 'stationary_calls')})
            for name in FAMILIES:
                item[name] = {}
                for domain in DOMAINS:
                    pp = [row[name][domain] for row in rr]
                    out = {key: stats.fmean(p[key] for p in pp) for key in
                           ('mean_bound', 'mean_level_bound', 'mean_slope_bound', 'mean_slack')}
                    out.update({key: max(p[key] for p in pp) for key in ('max_bound', 'max_slack')})
                    out.update({key: sum(p[key] for p in pp) for key in ('near_zero', 'slope_better', 'level_better', 'tied')})
                    item[name][domain] = out
            output[kind+'_'+str(level)] = item
    return output


def verify_manifest(path):
    manifest = read(path)
    check(manifest['status'] in ('passed', 'completed'), 'completed dependency')
    for entry in manifest['inputs']+manifest['outputs']:
        check(identity(entry['path']) == entry, 'immutable dependency identity')


def whitelist(h, local, row):
    """Project only available risk inputs; never pass the source row to derive."""
    i, j = row['source'], row['target']
    return dict(h=str(h), a=row['a'], g=row['g'],
                plus_source=local['v_plus'][i], plus_target=local['v_plus'][j],
                minus_source=local['v_minus'][i], minus_target=local['v_minus'][j],
                l0=row['correction_line']['l0'], l1=row['correction_line']['l1'],
                u0=row['correction_line']['u0'], u1=row['correction_line']['u1'],
                selected=row['policies']['combined']['r'], original_cap=row['original'])


def run(output, log):
    qualification = qualify()
    log.write('Nine scalar qualification cases and two invalid-input rejections passed.\n')
    log.flush()
    verify_manifest(MAIN/'MANIFEST.json')
    verify_manifest(OLD/'MANIFEST.json')
    core, old = read(MAIN/'CORE.json'), read(OLD/'RESULTS.json')
    check(not core['gate']['passed'], 'failed original mechanism gate preserved')
    source_rows = {(r['fixture'], r['kind'], r['order'], r['level']): r for r in old['rows']}
    old_queries = {}
    with (OLD/'QUERIES.jsonl').open() as stream:
        for line in stream:
            q = json.loads(line)
            old_queries.setdefault((q['fixture'], q['kind'], q['order'], q['level']), []).append(q)
    rows, querycount = [], 0
    with (output/'QUERIES.jsonl').open('w') as stream:
        for case in core['rows']:
            fixture, kind, order = [case[k] for k in ('fixture', 'kind', 'order')]
            h = D(str(case['h']))
            for level in (256, 1024, 4096):
                key = (fixture, kind, order, level)
                saved_row = source_rows[key]
                prepared = []
                for q in old_queries[key]:
                    view = whitelist(h, saved_row['local'], q)
                    envs, certificate = construct(view)
                    for name in FAMILIES:
                        lo, hi = interval(envs[name], D(q['original']))
                        dec_close(lo, q['policies'][name]['lower'], 'reconstructed '+name+' lower interval')
                        dec_close(hi, q['policies'][name]['upper'], 'reconstructed '+name+' upper interval')
                    dec_close(interval(envs['combined'], D(view['selected']))[1],
                              q['policies']['combined']['certified_upper'], 'reconstructed selected risk upper')
                    prepared.append((q, view, envs, certificate))
                # All certificates for this belief exist before reading its exact reference.
                ref = read(MAIN/f'{fixture}_exact_none/RESULTS.json')['reference']
                model_edges = read(MAIN/f'{fixture}_{kind}_{order}/RESULTS.json')['model']['edges']
                records = []
                for q, view, envs, certificate in prepared:
                    pair = ref['pairs'][q['edge']]
                    pair = {bits: D(str(pair[bits[0]][bits[1]])) for bits in prior.states(2)}
                    if q['source'] != model_edges[q['edge']][0]:
                        pair = {(y, x): w for (x, y), w in pair.items()}
                    a, g = prior.pair_risks(pair, h)
                    evaluation = evaluate(certificate, envs, D(view['selected']), D(view['original_cap']), a, g, saved=q)
                    record = dict(edge=q['edge'], source=q['source'], target=q['target'], agent_view=view,
                                  certificates=certificate, evaluation=evaluation)
                    records.append(record)
                    stream.write(json.dumps(dict(fixture=fixture, kind=kind, order=order, level=level, **record),
                                            default=prior.encode, separators=(',', ':'), allow_nan=False)+'\n')
                summary = summarize(records)
                close(summary['actual_global_regret'], saved_row['combined']['mean_regret'], 'previous mean true regret')
                rows.append(dict(fixture=fixture, kind=kind, order=order, level=level,
                                 preceding_certificate_cpu=saved_row['certificate_cpu'],
                                 preceding_q_reconstruction_cpu=saved_row['q_reconstruction_cpu'],
                                 main_cost=case['cost'], **summary))
                querycount += len(records)
            log.write(f'Completed {fixture} {kind} {order}; all budgets and comparators retained.\n')
            log.flush()
    check(len(rows) == 96 and querycount == 13056, 'all saved checkpoints and queries retained')
    return dict(qualification=qualification, rows=rows, summary=aggregate(rows),
                inherited_model_preparation=old['models'], checkpoints=len(rows), original_queries=querycount,
                regret_certificates=4*querycount)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--spec-sha256', required=True)
    args = parser.parse_args()
    check(args.output.resolve() == DEST and os.path.ismount('/mnt/bioIce1'), 'authorized mounted regret output')
    check(identity(__file__)['sha256'] == args.source_sha256, 'frozen regret checker')
    check(identity(SPEC)['sha256'] == args.spec_sha256, 'frozen regret specification')
    check(identity(prior.__file__)['sha256'] == 'f3f5351cedb7ee4bd1b702866651548d4458ebdd4250864174d7e45dc8c04bf6',
          'unchanged numerical helper')
    check(identity(OLD/'MANIFEST.json')['sha256'] == 'dddd352612b2c8c1f0d2d19c8625e2ad0e725ffe60f81838e2cb4e2977c739bf',
          'pinned risk-correction record')
    paths = [SPEC, Path(__file__), Path(prior.__file__), HERE/'check_fep_local_risk_correction.py',
             HERE/'FEP_LOCAL_RISK_CORRECTION_V1.md', HERE/'FEP_LOCAL_RISK_CORRECTION_V1_REPORT.md',
             OLD/'MANIFEST.json', OLD/'RESULTS.json', OLD/'QUERIES.jsonl', MAIN/'MANIFEST.json', MAIN/'CORE.json',
             MAIN/'RESULTS.json', HERE/'FEP_STRUCTURED_INFERENCE_V1_FREEZE.json',
             HERE/'FEP_STRUCTURED_INFERENCE_V1_REPORT.md', HERE/'FEP_USABLE_INFORMATION_MANUSCRIPT_V1.md',
             HERE/'FEP_USABLE_INFORMATION_MANUSCRIPT_V2.md']
    inputs = [identity(path) for path in paths]
    DEST.mkdir(parents=True, exist_ok=False)
    for path, name in ((SPEC, 'SPECIFICATION.md'), (Path(__file__), 'CHECKER_SOURCE.py'),
                       (Path(prior.__file__), 'REUSED_NUMERICAL_HELPER.py')):
        (DEST/name).write_bytes(path.read_bytes())
    manifest = dict(status='started', started_utc=datetime.now(timezone.utc).isoformat(), inputs=inputs,
                    scope='regret bounds from immutable agent-available risk intervals; no policy or inference changes',
                    python=platform.python_version(), decimal_precision=60, cpu_processes=1,
                    selected_stopping_tolerance=None, primary_comparator='unrestricted true feasible optimum')
    write(DEST/'MANIFEST.json', manifest)
    start, cpu = time.perf_counter(), time.process_time()
    with (DEST/'RUN_LOG.txt').open('w') as log:
        try:
            result = run(DEST, log)
            result.update(status='passed', assertions=sum(COUNTS.values()), assertions_by_label=dict(COUNTS),
                          max_residuals=RESIDUALS, elapsed_seconds=time.perf_counter()-start,
                          cpu_seconds=time.process_time()-cpu)
            write(DEST/'RESULTS.json', result)
            manifest['status'] = 'passed'
            log.write(f"Passed {result['assertions']} checks and {result['regret_certificates']} regret certificates.\n")
            print(json.dumps({key: result[key] for key in ('status', 'assertions', 'elapsed_seconds', 'cpu_seconds',
                              'checkpoints', 'original_queries', 'regret_certificates', 'summary')},
                             default=prior.encode, indent=2))
        except Exception:
            manifest['status'] = 'failed'
            log.write(traceback.format_exc())
            raise
        finally:
            log.flush()
            manifest['outputs'] = [identity(path) for path in sorted(DEST.iterdir()) if path.name != 'MANIFEST.json']
            write(DEST/'MANIFEST.json', manifest)


if __name__ == '__main__':
    main()
