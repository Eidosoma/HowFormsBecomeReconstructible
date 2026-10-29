#!/usr/bin/env python3
"""One prospective factor edit; exhaustive count laws, no sampled outcomes."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction as F
import gzip
from hashlib import sha256
from itertools import product
import json
from math import comb, factorial, fsum, log
from pathlib import Path
import platform
import shutil
from time import perf_counter, process_time
import traceback

MOUNT = Path('/mnt/bioIce1')
ROOT = MOUNT / 'fep-ideas/formal-checks/fep-factor-revision-v1'
NS, H, PRICE = (0, 8, 32, 64), 100, F(1, 1000)
TRUTHS = {
    'independent': (72, 18, 8, 2),
    'shared': (80, 10, 0, 10),
    'partial': (76, 14, 4, 6),
    'anticorrelated': (70, 20, 10, 0),
    'marginal_shift': (56, 14, 24, 6),
}
METHODS = ('independent', 'edit', 'joint_from_start', 'model_average')
FACT = [factorial(n) for n in range(2 * max(NS) + 3)]
LF = [log(x) for x in FACT]
COUNTS, MAX_ERROR, TOL = Counter(), 0.0, 1e-10


def check(group, label, condition):
    if not condition:
        raise AssertionError((group, label))
    COUNTS[group] += 1


def close(group, label, x, y):
    global MAX_ERROR
    err = abs(float(x) - float(y))
    MAX_ERROR = max(MAX_ERROR, err)
    check(group, label, err <= TOL)


def encode(x):
    if isinstance(x, F):
        return {'exact': str(x), 'value': float(x)}
    if isinstance(x, dict):
        return {str(k): encode(v) for k, v in x.items()}
    if isinstance(x, (tuple, list)):
        return [encode(v) for v in x]
    return x


def write(path, data):
    path.write_text(json.dumps(encode(data), indent=2, sort_keys=True) + '\n')


def identity(path):
    b = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(b), sha256=sha256(b).hexdigest())


def join(factors):
    if factors != (('E_A',), ('E_B',)):
        raise ValueError('Only the declared single factor-join is legal')
    return (tuple(v for factor in factors for v in factor),)


def histograms(n):
    for a in range(n + 1):
        for b in range(n - a + 1):
            for c in range(n - a - b + 1):
                yield (a, b, c, n - a - b - c)


def evidence(c):
    n, a, b = sum(c), c[2] + c[3], c[1] + c[3]
    m0 = F(FACT[a] * FACT[n-a] * FACT[b] * FACT[n-b], FACT[n+1] ** 2)
    numerator, denominator = 1, 4 ** n * FACT[n+1]
    for k in c:
        numerator *= FACT[2*k]
        denominator *= FACT[k]
    return m0, F(numerator, denominator)


def fit(c):
    """Agent interface: counts only. No truth, outcomes, or oracle access."""
    n, a, b = sum(c), c[2] + c[3], c[1] + c[3]
    v0 = ((n-a+1)*(n-b+1), (n-a+1)*(b+1),
          (a+1)*(n-b+1), (a+1)*(b+1))
    v1 = tuple(2*k+1 for k in c)
    # e1/e0 as an unreduced integer ratio; exact MAP decisions even near ties.
    num, den = FACT[n+1], 4**n * FACT[a]*FACT[n-a]*FACT[b]*FACT[n-b]
    for k in c:
        num *= FACT[2*k]
        den *= FACT[k]
    edited = num > 9*den
    mix = tuple(18*den*x + num*y*(n+2) for x, y in zip(v0, v1))
    vectors = (v0, v1 if edited else v0, v1, mix)
    log_e0 = LF[a] + LF[n-a] + LF[b] + LF[n-b] - 2*LF[n+1]
    log_e1 = sum(LF[2*k]-LF[k] for k in c) - n*log(4) - LF[n+1]
    return dict(vectors=vectors, edited=edited, model_weight=num/(num+9*den),
                log_evidence=(log_e0, log_e1), log_bayes_factor=log(num)-log(den))


def policy(v):
    # At observed pair y, W=0 has likelihood v[y], W=1 has v[3-y].
    return tuple((0 if v[y] > v[3-y] else 1)
                 if 10*min(v[y], v[3-y]) < v[y]+v[3-y] else 2
                 for y in range(4))


def physical_units(q, actions):
    """Direct W,E enumeration. q sums to 100; probabilities use /200."""
    wrong, ask = 0, 0
    for w in (0, 1):
        for e, mass in enumerate(q):
            act = actions[e if w == 0 else 3-e]
            if act == 2:
                ask += mass
            elif act != w:
                wrong += mass
    return wrong, ask


def multinomial(c):
    result = FACT[sum(c)]
    for k in c:
        result //= FACT[k]
    return result


def weight(c, q, coefficient):
    result = coefficient
    for k, p in zip(c, q):
        result *= p**k
    return result


def qualify():
    start = perf_counter()
    check('grammar', 'one generated join', join((('E_A',), ('E_B',))) == (('E_A', 'E_B'),))
    for label, q in TRUTHS.items():
        check('identifiability', label+' normalized', sum(q) == 100)
        if label != 'marginal_shift':
            check('identifiability', label+' same marginals', (q[2]+q[3], q[1]+q[3]) == (10, 20))
        # Both a common categorical source and a directed conditional sampler
        # generate exactly Q. Equality is observational, not causal identification.
        rows = (F(q[0]+q[1], 100), F(q[2]+q[3], 100))
        directed = tuple(rows[i//2]*F(q[i], q[(i//2)*2]+q[(i//2)*2+1]) for i in range(4))
        check('identifiability', label+' directed sampler equivalent', directed == tuple(F(x, 100) for x in q))
        truth_actions = policy(q)
        err, ask = physical_units(q, truth_actions)
        # Independently minimize over all 3^4 deterministic response tables.
        optimum = min(10*e+a for e, a in
                      (physical_units(q, acts) for acts in product(range(3), repeat=4)))
        check('task', label+' oracle exhaustive optimum', 10*err+ask == optimum)
    check('identifiability', 'shared uniform coupling cell counts',
          tuple(sum((int(k < 10)*2+int(k < 20)) == e for k in range(100)) for e in range(4)) == TRUTHS['shared'])
    short_histograms = 0
    for n in range(5):
        totals = [F(0), F(0)]
        for c in histograms(n):
            short_histograms += 1
            f = fit(c)
            ev = evidence(c)
            coefficient = multinomial(c)
            check('combinatorics', 'multinomial via sequential binomials',
                  coefficient == comb(n, c[0])*comb(n-c[0], c[1])*comb(n-c[0]-c[1], c[2]))
            for m in (0, 1):
                totals[m] += coefficient*ev[m]
                v = f['vectors'][0 if m == 0 else 2]
                close('evidence', 'integral log evidence', f['log_evidence'][m], log(ev[m].numerator)-log(ev[m].denominator))
                for e in range(4):
                    nxt = tuple(k+int(i == e) for i, k in enumerate(c))
                    check('evidence', 'predictive equals evidence ratio',
                          evidence(nxt)[m]/ev[m] == F(v[e], sum(v)))
            check('evidence', 'MAP equals posterior odds', f['edited'] == (ev[1] > 9*ev[0]))
            v0, _, v1, vm = f['vectors']
            for indices in ((2, 3), (1, 3)):
                check('marginals', 'matched posterior predictive marginal',
                      F(sum(v0[i] for i in indices), sum(v0)) == F(sum(v1[i] for i in indices), sum(v1)))
            mw = ev[1]/(9*ev[0]+ev[1])
            for e in range(4):
                check('mixture', 'full structural predictive',
                      F(vm[e], sum(vm)) == (1-mw)*F(v0[e], sum(v0)) + mw*F(v1[e], sum(v1)))
            prior, posterior = (F(9, 10), F(1, 10)), (1-mw, mw)
            fmin = fsum(float(p)*(log(float(p/pr))-log(float(lik)))
                        for p, pr, lik in zip(posterior, prior, ev))
            close('VFE', 'model posterior free energy equals surprisal', fmin, -log(float(sum(pr*lik for pr, lik in zip(prior, ev)))))
            arbitrary = (F(1, 2), F(1, 2))
            fother = fsum(float(p)*(log(float(p/pr))-log(float(lik)))
                          for p, pr, lik in zip(arbitrary, prior, ev))
            gap = fsum(float(p)*log(float(p/post)) for p, post in zip(arbitrary, posterior))
            close('VFE', 'nonposterior free energy gap is KL', fother-fmin, gap)
            for v in f['vectors']:
                for y in range(4):
                    post = (F(v[y], v[y]+v[3-y]), F(v[3-y], v[y]+v[3-y]))
                    py = F(v[y]+v[3-y], 2*sum(v))
                    value = fsum(float(p)*log(float(p/F(v[e], 2*sum(v))))
                                 for p, e in zip(post, (y, 3-y)))
                    close('VFE', 'world posterior identity', value, -log(float(py)))
        check('evidence', 'both short prior-predictive laws normalized', totals == [1, 1])
    # A separate ordered enumeration confirms histogram multiplicities/laws.
    for label, q in TRUTHS.items():
        counts = Counter()
        for sequence in product(range(4), repeat=4):
            c = tuple(sequence.count(i) for i in range(4))
            numerator = 1
            for e in sequence:
                numerator *= q[e]
            counts[c] += numerator
        for c in histograms(4):
            check('combinatorics', label+' ordered/count probability', counts[c] == weight(c, q, multinomial(c)))
    return dict(checks=sum(COUNTS.values()), groups=dict(COUNTS), max_residual=MAX_ERROR,
                short_histograms=short_histograms, wall_seconds=perf_counter()-start,
                continuous_VFE='analytic conjugate integration; finite model/world VFE separately checked')


def enumerate_budget(n, stream, logline):
    start = perf_counter()
    denom = 100**n
    totals = {t: {m: dict(wrong=0, ask=0, logloss=0.0) for m in METHODS} for t in TRUTHS}
    masses, edits, changed = Counter(), Counter(), Counter()
    cases = 0
    for c in histograms(n):
        f = fit(c)
        vectors = f.pop('vectors')
        actions = [policy(v) for v in vectors]
        lp = [tuple(log(x)-log(sum(v)) for x in v) for v in vectors]
        probs = [tuple(x/sum(v) for x in v) for v in vectors]
        for m, (v, p) in enumerate(zip(vectors, probs)):
            close('prediction', 'all predictive cells normalized', sum(p), 1)
            check('prediction', 'all predictive cells positive', min(v) > 0)
        check('marginals', 'all histories retain A and B predictive marginals',
              (vectors[0][2]+vectors[0][3])*sum(vectors[2]) == (vectors[2][2]+vectors[2][3])*sum(vectors[0]) and
              (vectors[0][1]+vectors[0][3])*sum(vectors[2]) == (vectors[2][1]+vectors[2][3])*sum(vectors[0]))
        coefficient = multinomial(c)
        weights = {}
        for label, q in TRUTHS.items():
            numerator = weight(c, q, coefficient)
            weights[label] = str(numerator)
            masses[label] += numerator
            edits[label] += numerator*f['edited']
            changed[label] += numerator*(actions[0] != actions[1])
            if not numerator:
                continue
            oracle_err, oracle_ask = physical_units(q, policy(q))
            for i, m in enumerate(METHODS):
                err, ask = physical_units(q, actions[i])
                check('oracle', 'each physical decision bounded by known-Q optimum',
                      10*err+ask >= 10*oracle_err+oracle_ask)
                totals[label][m]['wrong'] += numerator*err
                totals[label][m]['ask'] += numerator*ask
                totals[label][m]['logloss'] += (numerator/denom)*(-fsum(x*l for x, l in zip(q, lp[i]))/100)
        stream.write(json.dumps(dict(N=n, counts=c, **f, predictions=dict(zip(METHODS, probs)),
                                     actions=dict(zip(METHODS, actions)),
                                     truth_count_mass_numerators=weights), separators=(',', ':'))+'\n')
        cases += 1
    check('scope', 'complete count histogram set', cases == comb(n+3, 3))
    result = {}
    for label, q in TRUTHS.items():
        check('normalization', label+' exact count law', masses[label] == denom)
        rows = {}
        oracle_err, oracle_ask = physical_units(q, policy(q))
        for m, vals in totals[label].items():
            wrong, ask = F(vals['wrong'], 200*denom), F(vals['ask'], 200*denom)
            risk = wrong + ask/10
            check('task', label+' '+m+' bounded loss', 0 <= risk <= 1)
            rows[m] = dict(wrong_probability=wrong, ask_probability=ask, raw_loss=risk,
                           net_loss=risk+n*PRICE/H, predictive_log_loss=vals['logloss'],
                           pair_price_break_even_vs_always_ask=H*(F(1, 10)-risk)/n if n else None)
        result[label] = dict(methods=rows, edit_probability=F(edits[label], denom),
                             changed_policy_probability=F(changed[label], denom),
                             always_ask_loss=F(1, 10), follow_A_loss=F(q[2]+q[3], 100),
                             oracle_loss=F(10*oracle_err+oracle_ask, 2000), oracle_policy=policy(q),
                             truth_entropy=-fsum((x/100)*log(x/100) for x in q if x))
    logline(f'N={n}: {cases} histograms; {perf_counter()-start:.3f}s; exact probability and task aggregates passed')
    return result, cases


def run(output):
    if not MOUNT.is_mount() or not output.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError('Verified external FEP mount required')
    output.mkdir(parents=True, exist_ok=False)
    (output/'inputs').mkdir()
    started, start, cpu = datetime.now(timezone.utc).isoformat(), perf_counter(), process_time()
    source = Path(__file__).resolve().parent
    inputs, preserved = [], []
    def logline(message):
        with (output/'RUN_LOG.txt').open('a') as out:
            out.write(message+'\n')
        print(message, flush=True)
    try:
        logline('Started '+started+'; one process; no random sampling; no old optimizer imports')
        for name in ('FEP_FACTOR_REVISION_V1.md', 'check_fep_factor_revision.py'):
            path = source/name
            entry = identity(path)
            inputs.append(entry)
            shutil.copyfile(path, output/'inputs'/name)
            check('integrity', 'frozen '+name, identity(output/'inputs'/name)['sha256'] == entry['sha256'])
        for name in ('FEP_ACTION_TARGET_AUDIT_V1.md', 'check_fep_action_target_audit.py',
                     'FEP_ACTION_TARGET_AUDIT_V1_REPORT.md', 'FEP_DECISION_WINDOW_V1.md',
                     'check_fep_decision_window.py', 'FEP_DECISION_WINDOW_V1_REPORT.md',
                     'FEP_TWO_DECISION_EFE_V1.md', 'check_fep_two_decision_efe.py',
                     'FEP_TWO_DECISION_EFE_V1_REPORT.md', 'FEP_MODEL_CHECKING_V4.md',
                     'FEP_MODEL_CHECKING_V4_REPORT.md', 'FEP_ACTIVE_WORLD_MODELING_LESSONS_2026-09-21.md',
                     'FEP_USABLE_INFORMATION_MANUSCRIPT_V1.md', 'FEP_USABLE_INFORMATION_MANUSCRIPT_V2.md'):
            preserved.append(identity(source/name))
        write(output/'PREPARATION.json', dict(inputs=inputs, preserved=preserved, N=NS,
              primary_N=64, future_tasks=H, pair_price=PRICE, ask_price=F(1, 10),
              count_probability_denominators={n: str(100**n) for n in NS},
              truths=TRUTHS, structural_prior=[F(9, 10), F(1, 10)],
              factor_before=[['E_A'], ['E_B']], factor_after=join((('E_A',), ('E_B',))),
              numeric_contract='exact integer choices/mass/task loss; binary64 log quantities', tolerance=TOL,
              primary_sources=['https://arxiv.org/html/2001.07203v2', 'https://arxiv.org/html/2605.13740v1']))
        logline('Prospective sources and preparation sealed before qualification and outcome enumeration')
        qualification = qualify()
        write(output/'QUALIFICATION.json', qualification)
        logline(f'Qualification passed: {qualification["checks"]} checks in {qualification["wall_seconds"]:.3f}s')
        results, cases = {}, 0
        with gzip.open(output/'HISTOGRAMS.jsonl.gz', 'wt', encoding='utf-8') as stream:
            for n in NS:
                results[n], count = enumerate_budget(n, stream, logline)
                cases += count
        primary = results[64]
        aggregate = {m: {key: (primary['independent']['methods'][m][key]+primary['shared']['methods'][m][key])/2
                         for key in ('raw_loss', 'net_loss', 'predictive_log_loss')}
                     for m in METHODS}
        ed, ind = primary['shared']['methods']['edit'], primary['shared']['methods']['independent']
        gates = dict(shared_better_prediction=ed['predictive_log_loss'] < ind['predictive_log_loss']-TOL,
                     shared_better_task=ed['raw_loss'] < ind['raw_loss'],
                     shared_pays_vs_no_calibration=ed['net_loss'] < F(1, 10),
                     aggregate_better_than_parameter_only=aggregate['edit']['net_loss'] < aggregate['independent']['net_loss'],
                     aggregate_pays_vs_no_calibration=aggregate['edit']['net_loss'] < F(1, 10))
        check('scope', 'all declared budgets and fits', cases == 54616 and tuple(results) == NS)
        for entry in inputs+preserved:
            check('integrity', 'unchanged '+entry['path'], identity(Path(entry['path'])) == entry)
        summary = dict(checks=sum(COUNTS.values()), groups=dict(COUNTS), max_log_residual=MAX_ERROR,
                       fits=cases, learned_methods=len(METHODS), truth_fixtures=len(TRUTHS),
                       primary_functional_gates=gates, primary_functional_pass=all(gates.values()),
                       calibration_is_committed=True, causal_identification=False,
                       FEP_specific_advantage_tested=False, selected_after_results=False)
        write(output/'RESULTS.json', dict(summary=summary, budgets=results, primary_equal_truth_aggregate=aggregate))
        finished, wall, cpu_seconds = datetime.now(timezone.utc).isoformat(), perf_counter()-start, process_time()-cpu
        logline(f'COMPLETE: {summary["checks"]} qualification/integrity/numerical checks; primary functional gate={all(gates.values())}; wall={wall:.6f}s')
        outputs = [identity(p) for p in sorted(output.rglob('*')) if p.is_file()]
        write(output/'MANIFEST.json', dict(status='complete', started_utc=started, finished_utc=finished,
              wall_seconds=wall, cpu_seconds=cpu_seconds, processes=1, python=platform.python_version(),
              inputs=inputs, outputs=outputs, preserved=preserved, summary=summary))
    except Exception:
        logline(traceback.format_exc())
        write(output/'FAILURE.json', dict(status='failed', inputs=inputs, preserved=preserved,
              checks=sum(COUNTS.values()), groups=dict(COUNTS), wall_seconds=perf_counter()-start))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
