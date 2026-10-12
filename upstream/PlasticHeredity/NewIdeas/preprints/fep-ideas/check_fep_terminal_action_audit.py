#!/usr/bin/env python3
"""Fixed-policy formulation audit; generated records require the external mount."""
import argparse
from collections import Counter, defaultdict
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
STATES = tuple(product(BITS, repeat=11))
OLD = Path('/mnt/bioIce1/fep-ideas/formal-checks/fep-sensor-change-v1/attempt-01')
MOUNT = Path('/mnt/bioIce1')
ROOT = MOUNT / 'fep-ideas/formal-checks/fep-terminal-action-audit-v1'
TOL = D('1e-60')
COUNTS, MAX_ERROR = Counter(), D(0)
PRESERVED = {
    'FEP_SENSOR_CHANGE_V1.md': '68b25252b633200741f5d8d3cc1f48c3d63e40e3c2e9d775b9b1673f50e059fb',
    'check_fep_sensor_change.py': '2ae348a8b7872e9c63040575c69ad8a5441286752bcbb348e7f4ce2f15280e22',
    'FEP_SENSOR_CHANGE_V1_REPORT.md': 'ebb84a4d955c8c5e9b334d7e3c9719cc7e6f49b04716125fdb486e6c28144a0c',
    'FEP_ACTION_SELECTION_AUDIT_V1.md': 'dc13f56393252d07a868e265c31bf623e07bc12afc47162b9553d00293e08c3f',
    'FEP_FORMULATION_AUDIT_2026-09-18.md': '8d8c95cdc73d905a2afdba73b0fb0a60859553a59db08bc4601a38c0dc9f52cc',
    'FEP_USABLE_INFORMATION_MANUSCRIPT_V1.md': '402480808b61ad9718d38fa0f6f494f2c01819b807491cb386fdde89eb5b76f0',
    'FEP_USABLE_INFORMATION_MANUSCRIPT_V2.md': 'fdabe647e938aa4c6b3e828447b4c0162e3ee32644581505776d819889c11d9c',
}
OLD_HASHES = {
    'MANIFEST.json': '31f645a3bff035922360faff4cbd21a6835829bcb800c09850211756b689a71c',
    'PREPARATION.json': '17cf5528ea4a14648c1566c66241becef124b73a835e99e626e2cc344ad5952e',
    'RESULTS.json': '7bc0f0e32a6465a0d5ad9d033b793b294415a360966ac6668a90e74872853d11',
}


def dec(x):
    if isinstance(x, F):
        return D(x.numerator) / D(x.denominator)
    if isinstance(x, str) and '/' in x:
        return dec(F(x))
    return D(x)


def check(group, label, condition):
    if not condition:
        raise AssertionError((group, label))
    COUNTS[group] += 1


def close(group, label, x, y):
    global MAX_ERROR
    error = abs(dec(x) - dec(y))
    MAX_ERROR = max(MAX_ERROR, error)
    check(group, label, error <= TOL)


def bern(p, bit):
    return p if bit else 1-p


def entropy(ps):
    return -sum((dec(p)*dec(p).ln() for p in ps if p), D(0))


def encode(x):
    if isinstance(x, (D, F)):
        return str(x)
    if isinstance(x, dict):
        return {str(k): encode(v) for k, v in x.items()}
    if isinstance(x, (tuple, list)):
        return [encode(v) for v in x]
    return x


def write(path, value):
    path.write_text(json.dumps(encode(value), indent=2, sort_keys=True)+'\n')


def identity(path):
    data = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(data), sha256=sha256(data).hexdigest())


def safe(r):
    x, y = (F(value) for value in r)
    return (0 <= x <= 1 and 0 <= y <= 1
            and F(9, 10)*x+y/10 <= F(1, 3)
            and F(4, 5)*x+y/5 <= F(1, 3)
            and x/10+F(9, 10)*y <= F(4, 55)
            and x/5+F(4, 5)*y <= F(4, 55)
            and F(2, 5)*x+F(3, 5)*y <= F(4, 55))


def physical_base(s):
    th, dd, w, old, fresh, m, b, y, a, t, v = s
    good = th != b
    old_law = F(9 if th else 8, 10)
    fresh_law = F(9 if th else (6 if dd else 8), 10)
    alarm = F(9 if good else (6 if dd else 8), 10) if w else F(1 if good else 2, 10)
    failure = F(2, 25)+(F(11, 40) if w else F(3, 50))*a
    return (F(1, 8)*bern(old_law, old)*bern(fresh_law, fresh)
            *bern(alarm, y)*bern(F(3, 4)+F(3, 20)*a, t)*bern(1-failure, v))


def transcript(s, route):
    _, _, _, old, fresh, m, b, y, a, _, _ = s
    return (m, (old if route == 'stale' else fresh) if m else None, b, y, a)


def phase(prep, kind, route, m, z):
    if kind == 'fallback':
        return dict(channel=0, r=['0', '0'])
    return prep['phases'][route][kind][str(z)] if m else prep['prior'][kind]


def evaluate(prep, old_results, base, preferred, log_z, route, kind, m):
    label = f'{route}/{kind}/{m}'
    law = {}
    for s in STATES:
        z = s[3] if route == 'stale' else s[4]
        ph = phase(prep, kind, route, m, z)
        if s[5] == m and s[6] == ph['channel']:
            p = base[s]*bern(F(ph['r'][s[7]]), s[8])
            if p:
                law[s] = p
    check('joint', label+' normalization', sum(law.values()) == 1)
    for z in BITS if m else (0,):
        check('safety', label+' supported polygon', safe(tuple(F(x) for x in phase(prep, kind, route, m, z)['r'])))
    u = sum(p*(s[9]+F(s[10], 2)) for s, p in law.items())
    correctness = sum(p*s[9] for s, p in law.items())
    failure = sum(p*(1-s[10]) for s, p in law.items())
    po, co = defaultdict(F), defaultdict(D)
    ph, pha, phl, phla = defaultdict(F), defaultdict(F), defaultdict(F), defaultdict(F)
    for s, c in preferred.items():
        co[transcript(s, route)] += c
    for s, p in law.items():
        o = transcript(s, route)
        h, a, latent = o[:-1], o[-1], s[:3]
        po[o] += p
        ph[h] += p
        pha[h, a] += p
        phl[h, latent] += p
        phla[h, latent, a] += p
    close('joint', label+' observation preference normalization', sum(co.values()), 1)
    check('information', label+' conditional execution independence',
          all(p*ph[h] == phl[h, l]*pha[h, a] for (h, l, a), p in phla.items()))
    info = sum((dec(p)*(dec(p*ph[h]/(phl[h, l]*pha[h, a]))).ln()
                for (h, l, a), p in phla.items()), D(0))
    close('information', label+' zero conditional action information', info, 0)
    ha = -sum((dec(p)*dec(p/ph[h]).ln() for (h, a), p in pha.items()), D(0))
    check('information', label+' executed entropy', ha == 0 if kind == 'fallback' else ha > 0)
    action_kl = D(2).ln()-ha
    full = sum((dec(p)*(dec(p)/preferred[s]).ln() for s, p in law.items()), D(0))
    marginal = sum((dec(p)*(dec(p)/co[o]).ln() for o, p in po.items()), D(0))
    gap = sum((dec(p)*((dec(p)/dec(po[transcript(s, route)])) /
                       (preferred[s]/co[transcript(s, route)])).ln() for s, p in law.items()), D(0))
    close('decomposition', label+' full objective', full, 2*D(2).ln()+action_kl-4*dec(u)+log_z)
    close('decomposition', label+' chain rule', full, marginal+gap)
    check('decomposition', label+' nonnegative conditional gap', gap >= -TOL)
    observed_ce = -sum((dec(p)*co[o].ln() for o, p in po.items()), D(0))
    close('decomposition', label+' marginal risk versus information identity', marginal, observed_ce-entropy(po.values()))
    if kind != 'fallback':
        old = next(x for x in old_results['core_cases'] if x['route'] == route
                   and x['intervention'] == ('buy_' if m else 'skip_')+kind)['mixture']
        for field, value in [('U', u), ('correctness', correctness), ('risk', failure), ('full_KL', full), ('response_KL', action_kl)]:
            close('readback', label+' '+field, value, old[field])
    else:
        check('determinism', label+' fallback utility', u == F(121, 100))
    endpoint = defaultdict(F)
    for s, p in law.items():
        endpoint[s[9], s[10], s[5]] += p
    exp_u = {tv: D(4*tv[0]+2*tv[1]).exp() for tv in product(BITS, repeat=2)}
    rows = []
    for price in (D(0), D('.0001'), D(3).ln()):
        weights = {(t, v, mm): exp_u[t, v]*(-price*mm).exp() for t, v, mm in product(BITS, repeat=3)}
        norm = sum(weights.values())
        direct_ce = -sum((dec(p)*(weights[z]/norm).ln() for z, p in endpoint.items()), D(0))
        close('endpoint', label+' cross entropy', direct_ce, -4*dec(u)+price*m+norm.ln())
        physical_z = sum((dec(p)*weights[z] for z, p in endpoint.items()), D(0))
        self_kl = sum((dec(p)*(physical_z/weights[z]).ln() for z, p in endpoint.items()), D(0))
        moment = sum((dec(p)*exp_u[t, v] for (t, v, mm), p in endpoint.items()), D(0))
        close('normalization', label+' policy-specific cost cancellation', self_kl, moment.ln()-4*dec(u))
        rows.append(dict(price=price, endpoint_cross_entropy=direct_ce, self_reference_KL=self_kl))
    return dict(label=label, route=route, kind=kind, purchase=m, U=u, correctness=correctness,
                failure=failure, conditional_action_information=info, action_entropy=ha,
                action_KL=action_kl, full_KL=full, observation_KL=marginal,
                preferred_posterior_gap=gap, transcript_entropy=entropy(po.values()),
                endpoint_and_self_reference=rows)


def run(out):
    start, cpu = perf_counter(), process_time()
    started = datetime.now(timezone.utc).isoformat()
    source = Path(__file__).resolve().parent
    if not MOUNT.is_mount() or not out.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError('A mounted external FEP output directory is required')
    out.mkdir(parents=True, exist_ok=False)
    (out/'inputs').mkdir()
    def log(message):
        with (out/'RUN_LOG.txt').open('a') as handle:
            handle.write(str(message)+'\n')
        print(message, flush=True)
    inputs, preserved = [], []
    try:
        log('Started '+started+'; one process; fixed-policy analytic audit')
        for name, expected in PRESERVED.items():
            entry = identity(source/name)
            check('integrity', name, entry['sha256'] == expected)
            preserved.append(entry)
        for name, expected in OLD_HASHES.items():
            entry = identity(OLD/name)
            check('integrity', 'prior '+name, entry['sha256'] == expected)
            preserved.append(entry)
        old_manifest = json.loads((OLD/'MANIFEST.json').read_text())
        for group in ('inputs', 'outputs', 'preserved'):
            for entry in old_manifest[group]:
                actual = identity(Path(entry['path']))
                check('integrity', 'previous manifest '+entry['path'], actual == entry)
        originals = [source/'FEP_TERMINAL_ACTION_AUDIT_V1.md', Path(__file__).resolve(),
                     source/'FEP_SENSOR_CHANGE_V1.md', source/'FEP_SENSOR_CHANGE_V1_REPORT.md',
                     OLD/'PREPARATION.json', OLD/'RESULTS.json', OLD/'MANIFEST.json']
        for path in originals:
            entry = identity(path)
            inputs.append(entry)
            shutil.copyfile(path, out/'inputs'/path.name)
            check('integrity', 'copied '+path.name, identity(out/'inputs'/path.name)['sha256'] == entry['sha256'])
        write(out/'PREPARATION.json', dict(inputs=inputs, preserved=preserved,
              scope='10 fixed laws, two routes, no policy optimization or parameter sweep',
              full_joint_entries=2048, decimal_precision=80, tolerance=TOL,
              witnesses=['0', '.0001', 'log(3)', 'kappa=sealed route information (diagnostic only)'],
              primary_sources=['https://arxiv.org/html/2001.07203v2#S6', 'https://arxiv.org/html/2004.08128v5#S3']))
        log('Sources and scope sealed before numerical evaluation')
        prep = json.loads((OLD/'PREPARATION.json').read_text())
        old_results = json.loads((OLD/'RESULTS.json').read_text())
        corners = {str(r): safe(r) for r in product(BITS, repeat=2)}
        check('determinism', 'only fallback binary response feasible', corners == {'(0, 0)': True, '(0, 1)': False, '(1, 0)': False, '(1, 1)': False})
        check('determinism', 'task stochastic response feasible', safe((F(2, 11), F(0))))
        base = {s: physical_base(s) for s in STATES}
        check('joint', 'reference physical normalization', sum(base.values())/8 == 1)
        tilted = {s: dec(p/8)*D(4*s[9]+2*s[10]).exp() for s, p in base.items()}
        z = sum(tilted.values())
        preferred = {s: p/z for s, p in tilted.items()}
        close('joint', 'full preferred normalization', sum(preferred.values()), 1)
        laws = []
        for route in ('stale', 'fresh'):
            for kind, m in [('FEP', 0), ('FEP', 1), ('task', 0), ('task', 1), ('fallback', 0)]:
                row = evaluate(prep, old_results, base, preferred, z.ln(), route, kind, m)
                laws.append(row)
                log(f"{row['label']}: U={dec(row['U']):.15f}, conditional gap={row['preferred_posterior_gap']:.15f}")
        gains = {}
        for route, expected in [('stale', F(19, 440000)), ('fresh', F(71, 880000))]:
            selected = {row['purchase']: row for row in laws if row['route'] == route and row['kind'] == 'task'}
            gain = selected[1]['U']-selected[0]['U']
            check('function', route+' task gain', gain == expected)
            close('function', route+' sealed task gain', gain, prep['science'][route]['task']['gU'])
            info = D(prep['info'][route]['information'])
            threshold = 4*dec(gain)
            decisions = []
            for price in (D(0), D('.0001'), threshold, D(3).ln()):
                buy = price < threshold
                net = dec(gain)-price/4
                check('function', route+' cost alignment', (net > 0) if buy else (net <= 0))
                check('function', route+' skip tie', not buy if price == threshold else True)
                decisions.append(dict(price=price, buys=buy, chosen_gain=net if buy else D(0)))
            check('epistemic diagnostic', route+' information exceeds task boundary', info > threshold)
            info_difference = info-threshold-info
            info_net = dec(gain)-info/4
            check('epistemic diagnostic', route+' purchased diagnostic harms', info_difference < 0 and info_net < 0)
            gains[route] = dict(gain=gain, task_threshold=threshold, decisions=decisions,
                                calibration_information=info, information_bonus_threshold=threshold+info,
                                diagnostic_price=info, diagnostic_score_difference=info_difference,
                                diagnostic_net_gain=info_net)
        check('scope', 'all fixed laws completed', len(laws) == 10)
        for entry in inputs+preserved:
            check('integrity', 'final '+entry['path'], identity(Path(entry['path'])) == entry)
        summary = dict(assertions=sum(COUNTS.values()), groups=dict(COUNTS), max_decimal_residual=MAX_ERROR,
                       laws=10, reproduced_existing_laws=8, new_optimizer=False,
                       selected_operating_price=None, deterministic_feasibility=corners)
        write(out/'RESULTS.json', dict(summary=summary, laws=laws, route_comparisons=gains))
        finished = datetime.now(timezone.utc).isoformat()
        wall, cpu_seconds = perf_counter()-start, process_time()-cpu
        log(f'PASS: {summary["assertions"]} assertions; max residual {MAX_ERROR}; {wall:.6f} seconds wall')
        outputs = [identity(p) for p in sorted(out.rglob('*')) if p.is_file()]
        write(out/'MANIFEST.json', dict(status='complete', started_utc=started, finished_utc=finished,
              wall_seconds=wall, cpu_seconds=cpu_seconds, python=platform.python_version(), processes=1,
              inputs=inputs, outputs=outputs, preserved=preserved, summary=summary))
    except Exception:
        log(traceback.format_exc())
        write(out/'FAILURE.json', dict(status='failed', assertions=sum(COUNTS.values()), groups=dict(COUNTS),
              inputs=inputs, preserved=preserved, wall_seconds=perf_counter()-start))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
