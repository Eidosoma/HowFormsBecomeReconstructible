#!/usr/bin/env python3
"""Bounded analytic FEP sensor-change check; data only on the external mount."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal as D, getcontext
from fractions import Fraction as F
from hashlib import sha256
from itertools import product
import json
from pathlib import Path
import platform
import shutil
from time import perf_counter, process_time
import traceback

getcontext().prec = 80
BITS = (0, 1)
PARAMETERS = tuple(product(BITS, repeat=2))
HIDDEN = tuple(product(BITS, repeat=3))
STATES = tuple(product(BITS, repeat=11))
PRIOR = (F(1, 4),)*4
A, BN, BH, S, TAU = F(2, 25), F(3, 50), F(11, 40), F(4, 55), F(1, 10)
COUNTS = Counter()
TOL, MAX_ERROR = D('1e-65'), D(0)
ROOTS = {}
OLD_RECORD = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-committed-process-v1/attempt-01')
PRESERVED = {
    'FEP_COMMITTED_PROCESS_V1_REPORT.md': 'd3950fcb44126028723135e045fc80cef8fdd745cd39f519388f00d67a46e810',
    'FEP_COMMITTED_PROCESS_V1.md': '30d5efe77c72131032de1b24b7041d3b910546ec53b4b1fc097ed87d30642e6b',
    'check_fep_committed_process.py': '3c05e9b463e7c48274a0955d344480d969704b30163ceded02929e49f2e9664f',
    'audit_fep_committed_process.py': 'd04eef3427dd4527ae4018e8d93ce313926f310c57cd9548e474f2fed133f19c',
    'FEP_ACTION_SELECTION_AUDIT_V1.md': 'dc13f56393252d07a868e265c31bf623e07bc12afc47162b9553d00293e08c3f',
    'FEP_ACTION_SELECTION_AUDIT_V1_CHECKS.md': '7042d3b766967e2112ec4efaf197de433e7039d849260138678c9dcd3efe7d8c',
    'FEP_USABLE_INFORMATION_MANUSCRIPT_V1.md': '402480808b61ad9718d38fa0f6f494f2c01819b807491cb386fdde89eb5b76f0',
    'FEP_USABLE_INFORMATION_MANUSCRIPT_V2.md': 'fdabe647e938aa4c6b3e828447b4c0162e3ee32644581505776d819889c11d9c',
}


def dec(x):
    return D(x.numerator)/D(x.denominator) if isinstance(x, F) else D(x)


def check(group, label, condition):
    if not condition:
        raise AssertionError((group, label))
    COUNTS[group] += 1


def close(group, label, x, y):
    global MAX_ERROR
    residual = abs(dec(x)-dec(y))
    MAX_ERROR = max(MAX_ERROR, residual)
    check(group, label, residual <= TOL)


def bern(p, bit):
    return p if bit else 1-p


def kl(q, p):
    return sum((dec(a)*(dec(a)/dec(b)).ln() for a, b in zip(q, p) if a), D(0))


def k(r):
    return kl((r, 1-r), (F(1, 2), F(1, 2)))


def logit(r):
    return (dec(r)/(1-dec(r))).ln()


def sensor(th, changed, w, b, y):
    good = th != b
    p = (F(9, 10) if good else F(6 if changed else 8, 10)) if w else F(1 if good else 2, 10)
    return bern(p, y)


def calibration(route, th, changed, bit):
    p = F(9, 10) if th else F(6 if changed and route == 'fresh' else 8, 10)
    return bern(p, bit)


def risk(w, r):
    return A+(BH if w else BN)*r


def encode(value):
    if isinstance(value, (F, D)):
        return str(value)
    if isinstance(value, dict):
        return {str(key): encode(val) for key, val in value.items()}
    if isinstance(value, (tuple, list)):
        return [encode(val) for val in value]
    return value


def write(path, value):
    with path.open('w') as handle:
        json.dump(encode(value), handle, sort_keys=True, indent=2)
        handle.write('\n')


def identity(path):
    data = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(data), sha256=sha256(data).hexdigest())


def beliefs():
    info = {}
    for route in ('stale', 'fresh'):
        pz, qs = {}, {}
        for z in BITS:
            joint = tuple(calibration(route, th, dd, z)/4 for th, dd in PARAMETERS)
            pz[z] = sum(joint)
            qs[z] = tuple(p/pz[z] for p in joint)
            check('inference', 'all four hypotheses supported', all(p > 0 for p in qs[z]))
            for b, y in product(BITS, repeat=2):
                raw = tuple(qs[z][2*th+dd]*sensor(th, dd, w, b, y)/2 for th, dd, w in HIDDEN)
                evidence = sum(raw)
                posterior = tuple(p/evidence for p in raw)
                pre = tuple(qs[z][2*th+dd]/2 for th, dd, w in HIDDEN)
                for candidate in (pre, posterior):
                    direct = sum((dec(q)*(dec(q)/dec(j)).ln() for q, j in zip(candidate, raw)), D(0))
                    close('inference', 'joint VFE identity', direct, kl(candidate, posterior)-dec(evidence).ln())
                check('inference', 'world posterior and positive support', sum(posterior) == 1 and all(p > 0 for p in posterior))
        marg_th = {z: sum(q for q, (th, dd) in zip(qs[z], PARAMETERS) if th) for z in BITS}
        marg_d = {z: sum(q for q, (th, dd) in zip(qs[z], PARAMETERS) if dd) for z in BITS}
        information = sum((dec(pz[z])*kl(qs[z], PRIOR) for z in BITS), D(0))
        change_information = sum((dec(pz[z])*k(marg_d[z]) for z in BITS), D(0))
        vfe = sum((dec(pz[z])*kl(PRIOR, qs[z]) for z in BITS), D(0))
        expected = ({0: F(3, 20), 1: F(17, 20)}, {0: F(1, 3), 1: F(9, 17)}, {0: F(1, 2), 1: F(1, 2)}) if route == 'stale' else ({0: F(1, 5), 1: F(4, 5)}, {0: F(1, 4), 1: F(9, 16)}, {0: F(5, 8), 1: F(15, 32)})
        check('identifiability', 'derived calibration posteriors', (pz, marg_th, marg_d) == expected)
        check('identifiability', 'old versus fresh change information', change_information == 0 if route == 'stale' else change_information > 0)
        info[route] = dict(pz=pz, posterior=qs, theta_probability=marg_th,
                           change_probability=marg_d, information=information,
                           change_information=change_information, mean_VFE_decrease=vfe)
    means = [(sensor(th, dd, 1, 0, 1), sensor(th, dd, 1, 1, 1)) for th, dd in PARAMETERS]
    check('identifiability', 'A alone has an aliased pair', len({p[0] for p in means}) == 3)
    check('identifiability', 'both labeled channels identify the supplied family', len(set(means)) == 4)
    check('identifiability', 'finite pair cannot remove support', all(bern(a, x)*bern(b, y) > 0 for a, b in means for x, y in product(BITS, repeat=2)))
    check('identifiability', 'unlabeled sensor/prevalence ambiguity', F(1, 5)+(F(4, 5)-F(1, 5))*F(1, 3) == F(1, 5)+(F(3, 5)-F(1, 5))*F(1, 2) == F(2, 5))
    for alpha, beta in ((F(1, 10), F(9, 10)), (F(1, 5), F(4, 5)), (F(1, 5), F(3, 5))):
        c0 = ((1-alpha)*F(3, 25)+(1-beta)*F(1, 80))/2
        c1 = (alpha*F(3, 25)+beta*F(1, 80))/2
        check('task bound', 'physical quality endpoint implies common task vertex', c0 > 0 and c1 > 0 and c1-F(3, 2)*c0 < 0)
    return info


def response(t, dd):
    key = (t, dd)
    if key in ROOTS:
        return ROOTS[key]
    alpha, beta = F(1, 5)-t/10, F(4, 5)+t/10-dd/5
    q0, q1 = F(1, 2)+dd/10, F(1, 2)-dd/10
    c0 = ((1-alpha)*F(3, 25)+(1-beta)*F(1, 80))/2
    c1 = (alpha*F(3, 25)+beta*F(1, 80))/2
    c = c0-F(2, 3)*c1
    check('optimization', 'utility slope', c == F(91, 2400)+F(43, 4800)*t+dd/480)
    check('task bound', 'task vertex optimal', c0 > 0 and c1 > 0 and c1-F(3, 2)*c0 < 0)
    def derivative(e):
        return dec(q0)*logit(dec(S)+e)-dec(F(2, 3)*q1)*logit(dec(S)-D(2)*e/3)-4*dec(c)
    lo, hi = D(0), dec(F(3, 2)*S)
    check('optimization', 'negative initial derivative', derivative(lo) < 0)
    for _ in range(320):
        mid = (lo+hi)/2
        if derivative(mid) > 0:
            hi = mid
        else:
            lo = mid
    e = F((lo+hi)/2)
    r0, r1 = S+e, S-F(2, 3)*e
    grad0 = dec(q0)*logit(r0)-4*dec(c0)
    multiplier = -grad0/dec(F(2, 5))
    close('optimization', 'scalar root', derivative(dec(e)), 0)
    close('optimization', 'full 2D KKT', dec(q1)*logit(r1)-4*dec(c1)+dec(F(3, 5))*multiplier, 0)
    check('optimization', 'complete polygon feasibility', 0 < r1 < r0 < 1 and multiplier > 0
          and F(9, 10)*r0+r1/10 < F(1, 3) and F(4, 5)*r0+r1/5 < F(1, 3)
          and r0/10+F(9, 10)*r1 < S and r0/5+F(4, 5)*r1 < S
          and F(2, 5)*r0+F(3, 5)*r1 == S)
    utility = F(5, 4)-A/2+F(53, 800)*S+c*e
    penalty = dec(q0)*k(r0)+dec(q1)*k(r1)
    ROOTS[key] = dict(t=t, degraded_probability=dd, alpha=alpha, beta=beta, q0=q0, q1=q1,
                      c0=c0, c1=c1, e=e, r=(r0, r1), U=utility, K=penalty, L=penalty-4*dec(utility))
    return ROOTS[key]


def candidates(q, task=False):
    rows = []
    for b in BITS:
        t = sum(p for p, (th, dd) in zip(q, PARAMETERS) if th != b)
        changed_bad = sum(p for p, (th, dd) in zip(q, PARAMETERS) if th == b and dd)
        fitted = response(t, changed_bad)
        rs = (F(2, 11), F(0)) if task else fitted['r']
        U, T, R, mass = F(0), F(0), F(0), F(0)
        penalty = D(0)
        for th, dd, w, y in product(BITS, repeat=4):
            weight = q[2*th+dd]*sensor(th, dd, w, b, y)/2
            rr, tt = risk(w, rs[y]), F(3, 4)+F(3, 20)*rs[y]
            mass += weight
            U += weight*(tt+(1-rr)/2)
            T += weight*tt
            R += weight*rr
            penalty += dec(weight)*k(rs[y])
        check('physical law', 'phase normalization', mass == 1)
        if not task:
            close('optimization', 'response utility identity', U, fitted['U'])
            close('optimization', 'correct nonfair warning weights', penalty, fitted['K'])
        rows.append(dict(channel=b, r=rs, t=t, degraded_probability=changed_bad,
                         U=U, correctness=T, risk=R, K=penalty, L=penalty-4*dec(U)))
    return rows


def choose(rows, task=False):
    return rows[max(BITS, key=lambda b: rows[b]['U']) if task else min(BITS, key=lambda b: rows[b]['L'])]


def plan_contexts(info):
    prior = {kind: choose(candidates(PRIOR, kind == 'task'), kind == 'task') for kind in ('FEP', 'task')}
    phases, summary, diagnostic = {}, {}, []
    for route in info:
        phases[route], summary[route] = {}, {}
        for kind in ('FEP', 'task'):
            possible = {z: candidates(info[route]['posterior'][z], kind == 'task') for z in BITS}
            phases[route][kind] = {z: choose(possible[z], kind == 'task') for z in BITS}
            selected = phases[route][kind]
            expected_u = sum(info[route]['pz'][z]*selected[z]['U'] for z in BITS)
            expected_k = sum((dec(info[route]['pz'][z])*selected[z]['K'] for z in BITS), D(0))
            gu = expected_u-prior[kind]['U']
            score_gain = prior[kind]['L']-sum((dec(info[route]['pz'][z])*selected[z]['L'] for z in BITS), D(0))
            delta_k = expected_k-prior[kind]['K']
            close('decomposition', 'score versus utility and response penalty', score_gain, 4*dec(gu)-delta_k)
            if kind == 'FEP':
                check('optimization', 'conditional minimization cannot worsen full score', score_gain >= -TOL)
            summary[route][kind] = dict(gU=gu, score_gain=score_gain, delta_response_KL=delta_k,
                                       purchase_threshold=4*dec(gu) if kind == 'task' else score_gain,
                                       positive_functional_interval=gu > 0,
                                       chosen_channels=[selected[z]['channel'] for z in BITS],
                                       good_channel_probability=sum(info[route]['pz'][z]*selected[z]['t'] for z in BITS),
                                       degraded_channel_probability=sum(info[route]['pz'][z]*selected[z]['degraded_probability'] for z in BITS))
            for z in BITS:
                diagnostic.append(dict(route=route, observation=z, kind=kind, candidates=possible[z],
                                       chosen=selected[z]['channel'], raw_utility_winner=max(BITS, key=lambda b: possible[z][b]['U'])))
        # The continuous responses are globally optimized by the full KKT checks.
        # Compare the remaining six distinct deterministic channel programs.
        values = [prior['FEP']['L']]*2
        vals = {z: candidates(info[route]['posterior'][z]) for z in BITS}
        for b0, b1 in product(BITS, repeat=2):
            values.append(sum((dec(info[route]['pz'][z])*vals[z][b]['L'] for z, b in ((0, b0), (1, b1))), D(0)))
        best = min(values)
        close('optimization', 'minimum across all six programs', best, prior['FEP']['L']-summary[route]['FEP']['score_gain'])
    check('optimization', 'nine distinct response contexts', len(ROOTS) == 9)
    return prior, phases, summary, diagnostic


def policy(route, kind, m, prior, phases):
    family = 'FEP' if kind == 'frozen' else kind
    return dict(route=route, kind=kind, m=int(m), prior=prior[family],
                after={z: prior[family] if kind == 'frozen' else phases[route][family][z] for z in BITS})


def rule(pol, old, fresh):
    return pol['after'][old if pol['route'] == 'stale' else fresh] if pol['m'] else pol['prior']


def preference(price):
    raw = []
    for th, dd, w, old, fresh, m, b, y, a, t, v in STATES:
        base = calibration('stale', th, dd, old)*calibration('fresh', th, dd, fresh)*sensor(th, dd, w, b, y)/64
        base *= bern(F(3, 4)+F(3, 20)*a, t)*bern(1-risk(w, a), v)
        raw.append(dec(base)*(4*dec(F(t)+F(v, 2))-price*m).exp())
    norm = sum(raw, D(0))
    target = tuple(p/norm for p in raw)
    close('full joint', 'preferred law normalized', sum(target), 1)
    return norm, target


def evaluate(pol, price, ref, actual=None):
    norm, target = ref
    mass, U, T, R = F(0), F(0), F(0), F(0)
    direct = D(0)
    for state, pref in zip(STATES, target):
        th, dd, w, old, fresh, m, b, y, a, t, v = state
        selected = rule(pol, old, fresh)
        if m != pol['m'] or b != selected['channel']:
            continue
        prob = F(1, 8) if actual is None else F((th, dd, w) == actual)
        prob *= calibration('stale', th, dd, old)*calibration('fresh', th, dd, fresh)*sensor(th, dd, w, b, y)
        prob *= bern(selected['r'][y], a)*bern(F(3, 4)+F(3, 20)*a, t)*bern(1-risk(w, a), v)
        if prob:
            mass += prob
            U += prob*(F(t)+F(v, 2))
            T += prob*t
            R += prob*(1-v)
            direct += dec(prob)*(dec(prob)/pref).ln()
    expected_u, expected_t, expected_r, response_penalty = F(0), F(0), F(0), D(0)
    for th, dd, w, z, y in product(BITS, repeat=5):
        selected = pol['after'][z] if pol['m'] else pol['prior']
        weight = F(1, 8) if actual is None else F((th, dd, w) == actual)
        weight *= calibration(pol['route'], th, dd, z)*sensor(th, dd, w, selected['channel'], y)
        rr, tt = risk(w, selected['r'][y]), F(3, 4)+F(3, 20)*selected['r'][y]
        expected_u += weight*(tt+(1-rr)/2)
        expected_t += weight*tt
        expected_r += weight*rr
        response_penalty += dec(weight)*k(selected['r'][y])
    check('full joint', 'physical normalization and reduced moments', mass == 1 and U == expected_u and T == expected_t and R == expected_r)
    j = 2*D(2).ln()+response_penalty-4*dec(U)+price*pol['m']
    close('full joint', 'complete KL and fixed-hidden-state offset', direct, j+norm.ln()+(D(8).ln() if actual is not None else 0))
    return dict(actual=actual, U=U, correctness=T, risk=R, net_U=dec(U)-price*pol['m']/4,
                response_KL=response_penalty, J=j, full_KL=direct)


def safety(pol, info):
    histories = BITS if pol['m'] else (None,)
    primary, signal, predictive = [], [], []
    for z in histories:
        selected = pol['after'][z] if pol['m'] else pol['prior']
        for th, dd, w in HIDDEN:
            average = sum(sensor(th, dd, w, selected['channel'], y)*risk(w, selected['r'][y]) for y in BITS)
            check('primary safety', 'every supported hidden state and history', average <= TAU)
            primary.append(dict(history=z, theta=th, changed=dd, world=w, risk=average))
            for y in BITS:
                signal.append(dict(history=z, theta=th, changed=dd, world=w, warning=y, risk=risk(w, selected['r'][y])))
        q = info[pol['route']]['posterior'][z] if pol['m'] else PRIOR
        for y in BITS:
            unnormalized = [q[2*th+dd]*sensor(th, dd, w, selected['channel'], y)/2 for th, dd, w in HIDDEN]
            total = sum(unnormalized)
            value = sum(p*risk(w, selected['r'][y]) for p, (th, dd, w) in zip(unnormalized, HIDDEN))/total
            predictive.append(dict(history=z, warning=y, risk=value))
    def summarized(rows):
        return dict(cases=len(rows), failures=sum(r['risk'] > TAU for r in rows), maximum=max(r['risk'] for r in rows), rows=rows)
    return dict(primary=summarized(primary), per_warning=summarized(signal), predictive=summarized(predictive))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    mount = Path('/mnt/bioIce1')
    base = mount/'fep-ideas/formal-checks/fep-sensor-change-v1'
    output = args.output.resolve()
    if not mount.is_mount() or output.parent != base.resolve() or not output.name.startswith('attempt-'):
        raise SystemExit('Require a fresh attempt under the mounted external FEP study directory')
    if output.exists():
        raise SystemExit('Refusing to overwrite an existing attempt')
    base.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    (output/'inputs').mkdir()
    source = Path(__file__).resolve().parent
    names = ('FEP_SENSOR_CHANGE_V1.md', Path(__file__).name, 'FEP_COMMITTED_PROCESS_V1_REPORT.md',
             'FEP_COMMITTED_PROCESS_V1.md', 'FEP_ACTION_SELECTION_AUDIT_V1.md',
             'FEP_ACTION_SELECTION_AUDIT_V1_CHECKS.md', 'FEP_ACTIVE_SENSOR_CHOICE_V1.md')
    manifest = dict(status='running', started_utc=datetime.now(timezone.utc).isoformat(),
                    python=platform.python_version(), processes=1, inputs=[], preserved=[])
    write(output/'MANIFEST.json', manifest)
    wall, cpu = perf_counter(), process_time()
    with (output/'RUN_LOG.txt').open('x') as log:
        try:
            for name in names:
                shutil.copyfile(source/name, output/'inputs'/name)
                manifest['inputs'].append(identity(source/name))
            for name, expected in PRESERVED.items():
                entry = identity(source/name)
                check('integrity', name, entry['sha256'] == expected)
                manifest['preserved'].append(entry)
            for name, expected in (
                ('AGENT_RECORDS.json', '569e96a86ba2769f52cabc99c934bed2068c8052b4284c89e7b885ed802d37f8'),
                ('MANIFEST.json', '4a42728ae9920219095a962f889f270f213fa7d81c4768a5c9ccbf7da9a95da3'),
                ('READBACK.json', '5e88a9804095d8cb557de7826b2a8b662e531424bdef89504a6dea610f3ae936')):
                entry = identity(OLD_RECORD/name)
                check('integrity', 'retained process '+name, entry['sha256'] == expected)
                manifest['preserved'].append(entry)
            write(output/'MANIFEST.json', manifest)
            log.write('Seven source copies frozen, eleven retained identities verified.\n')
            log.flush()
            info = beliefs()
            prior, phases, science, channel_comparisons = plan_contexts(info)
            old = json.loads((OLD_RECORD/'AGENT_RECORDS.json').read_text())
            old_r = tuple(map(F, old['library']['prior']['response']))
            old_failure = risk(1, F(2, 5)*old_r[0]+F(3, 5)*old_r[1])
            check('support boundary', 'old stability-assuming response remains unsafe', old_failure > TAU)
            for row in ROOTS.values():
                rr = row['r']
                check('support boundary', 'exact risk intercept', risk(1, F(2, 5)*rr[0]+F(3, 5)*rr[1]) == TAU)
                check('support boundary', 'positive risk slope below supported sensitivity', BH*(rr[0]-rr[1]) > 0)
            preparation = dict(parameter_order=PARAMETERS, hidden_order=HIDDEN, info=info, roots=list(ROOTS.values()),
                               prior=prior, phases=phases, science= science, channel_comparisons=channel_comparisons,
                               old_prior_response=old_r, old_response_changed_risk=old_failure,
                               preparatory_assertions=sum(COUNTS.values()), groups=dict(COUNTS))
            write(output/'PREPARATION.json', preparation)
            sealed = identity(output/'PREPARATION.json')['sha256']
            log.write('Inference and nine optimal response contexts sealed before direct joint evaluation: '+sealed+'\n')
            log.flush()
            prices = (D(0), D('.0001'), D(3).ln())
            references = {price: preference(price) for price in prices}
            for price, (norm, _) in references.items():
                close('full joint', 'symbolic cost normalizer', norm, references[D(0)][0]*(1+(-price).exp())/2)
            cases, cache, comparisons = [], {}, 0
            for route in info:
                for label, kind, m in (('skip_FEP', 'FEP', 0), ('buy_FEP', 'FEP', 1),
                                       ('skip_task', 'task', 0), ('buy_task', 'task', 1),
                                       ('unused_FEP', 'frozen', 1)):
                    pol = policy(route, kind, m, prior, phases)
                    mixture = evaluate(pol, D(0), references[D(0)])
                    worlds = [evaluate(pol, D(0), references[D(0)], actual) for actual in HIDDEN]
                    comparisons += 9
                    result = dict(route=route, intervention=label, price=D(0), policy=pol,
                                  mixture=mixture, hidden_contexts=worlds, safety=safety(pol, info))
                    cache[route, label] = result
                    cases.append(result)
                for kind in ('FEP', 'task'):
                    no, yes = (cache[route, label+'_'+kind]['mixture'] for label in ('skip', 'buy'))
                    check('function', 'task gain matches physical law', yes['U']-no['U'] == science[route][kind]['gU'])
                    close('decomposition', 'phase value matches full score', no['J']-yes['J'], science[route][kind]['score_gain'])
                check('access', 'unused acquired evidence has no raw benefit', cache[route, 'unused_FEP']['mixture']['U'] == cache[route, 'skip_FEP']['mixture']['U'])
                log.write('Completed zero-cost full-joint laws for '+route+'.\n')
                log.flush()
            optimized = []
            for price in prices:
                for route in info:
                    for kind in ('FEP', 'task'):
                        gains = science[route][kind]
                        m = int(price < gains['purchase_threshold'])
                        pol = policy(route, kind, m, prior, phases)
                        if price == 0:
                            result = cache[route, ('buy_' if m else 'skip_')+kind]
                            mixture, limits = result['mixture'], result['safety']
                        else:
                            mixture, limits = evaluate(pol, price, references[price]), safety(pol, info)
                            comparisons += 1
                        baseline = cache[route, 'skip_'+kind]['mixture']
                        net_gain = mixture['net_U']-baseline['net_U']
                        close('function', 'costed acquisition identity', net_gain, m*(dec(gains['gU'])-price/4))
                        optimized.append(dict(route=route, kind=kind, price=price, purchase=m,
                                              net_gain=net_gain, functional_gain_positive=net_gain > 0,
                                              mixture=mixture, safety=limits))
            check('record', 'complete bounded comparison scope', len(cases) == 10 and len(optimized) == 12 and comparisons == 98)
            check('integrity', 'preparation unchanged', identity(output/'PREPARATION.json')['sha256'] == sealed)
            for entry in manifest['inputs']+manifest['preserved']:
                check('integrity', 'source unchanged '+entry['path'], identity(Path(entry['path'])) == entry)
            summary = dict(assertions=sum(COUNTS.values()), groups=dict(COUNTS),
                           max_decimal_residual=MAX_ERROR, full_joint_entries=len(STATES),
                           full_joint_comparisons=comparisons, root_contexts=len(ROOTS),
                           scientific_comparisons=science, old_response_changed_risk=old_failure,
                           core_primary_safe=sum(c['safety']['primary']['failures'] == 0 for c in cases),
                           selected_operating_price=None)
            write(output/'RESULTS.json', dict(summary=summary, core_cases=cases, optimized=optimized,
                                             normalizers={str(price): z for price, (z, _) in references.items()}))
            manifest.update(status='complete', summary=summary)
        except BaseException:
            manifest.update(status='failed', assertions=sum(COUNTS.values()), groups=dict(COUNTS))
            log.write(traceback.format_exc())
            raise
        finally:
            manifest.update(finished_utc=datetime.now(timezone.utc).isoformat(), wall_seconds=perf_counter()-wall,
                            cpu_seconds=process_time()-cpu)
            log.write('Final: '+json.dumps(encode(manifest))+'\n')
            log.flush()
            manifest['outputs'] = [identity(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'MANIFEST.json']
            write(output/'MANIFEST.json', manifest)
    print(json.dumps(encode(dict(output=str(output), status=manifest['status'], summary=manifest['summary'],
                                wall_seconds=manifest['wall_seconds'])), indent=2))


if __name__ == '__main__':
    main()
