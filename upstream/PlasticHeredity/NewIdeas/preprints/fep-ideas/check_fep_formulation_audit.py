"""Four terminal-audit arithmetic checks; emits JSON, creates no files.

Run with python -B. These are checks of the audit's algebra, not a new cohort
or a replacement for any frozen v5 policy calculation.
"""
from datetime import datetime, timezone
from hashlib import sha256
from itertools import product
from math import exp, fsum, log
from pathlib import Path
import json
import platform
from time import perf_counter


def normalized(weights):
    total = fsum(weights.values())
    return {s: p / total for s, p in weights.items()}


def kl(q, p):
    return fsum(v * log(v / p[s]) for s, v in q.items() if v)


def marginal(states, observation):
    result = {}
    for s, p in states.items():
        o = observation(s)
        result[o] = result.get(o, 0) + p
    return result


def main():
    started = perf_counter()
    residuals, rows = {}, []

    def check(name, actual, expected):
        error = abs(actual - expected)
        residuals[name] = max(residuals.get(name, 0), error)
        if error > 1e-12:
            raise AssertionError((name, actual, expected))

    # All choices are fixed illustrations, including a certain-success boundary.
    for p, d in ((0.5, 0.1), (0.5, 0.3), (0.8, 0.1), (1.0, 0.1)):
        beta, b = 4.0, 0.5
        qg = {0: 1 - p, 1: p}
        cg = normalized({g: exp(beta * g) for g in (0, 1)})
        ca = normalized({a: exp(-beta * d * a) for a in (0, 1)})
        cs = {(g, a): cg[g] * ca[a] for g, a in product((0, 1), repeat=2)}
        observe = lambda s: (s[1], str(s[0]) if s[1] else 'null')
        co = marginal(cs, observe)
        alternative = normalized({(0, 'null'): exp(beta * b),
                                  (1, '0'): exp(-beta * d),
                                  (1, '1'): exp(beta * (1 - d))})
        for distribution in (cg, ca, cs, co, alternative):
            check('normalization', fsum(distribution.values()), 1)
        h = -fsum(q * log(q) for q in qg.values() if q)
        discrepancy = kl(qg, cg)
        scores = []
        for a in (0, 1):
            qs = {(g, aa): qg[g] if aa == a else 0.0 for g, aa in cs}
            qo = marginal(qs, observe)
            # Each state emits exactly one observation; conditional entropy is zero.
            information = fsum(q * log(q / (qs[s] * qo[observe(s)]))
                               for s, q in qs.items() if q)
            conditional_kl = fsum(q * log((q / qo[observe(s)]) /
                                         (cs[s] / co[observe(s)]))
                                  for s, q in qs.items() if q)
            latent_cost = -fsum(q * log(cs[s]) for s, q in qs.items() if q)
            values = {'v5_extension': latent_cost - information,
                      'state_risk_efe': kl(qs, cs),
                      'induced_outcome_efe': kl(qo, co),
                      'fixed_null_outcome_efe': kl(qo, alternative)}
            check('kl_chain_rule', values['state_risk_efe'],
                  values['induced_outcome_efe'] + conditional_kl)
            check('information', information, a * h)
            check('posterior_gap', conditional_kl, (1 - a) * discrepancy)
            scores.append({'audit': a, 'utility': p - d * a,
                           'information': information, 'conditional_kl': conditional_kl,
                           'scores': values})
        differences = {name: scores[1]['scores'][name] - scores[0]['scores'][name]
                       for name in scores[0]['scores']}
        expected = {'v5_extension': beta * d - h,
                    'state_risk_efe': beta * d,
                    'induced_outcome_efe': beta * d + discrepancy,
                    'fixed_null_outcome_efe': beta * d - h - beta * (p - b)}
        for name in expected:
            check(name + '_difference', differences[name], expected[name])
        check('physical_audit_cost', scores[1]['utility'] - scores[0]['utility'], -d)
        rows.append({'success_probability': p, 'audit_cost': d, 'beta': beta,
                     'null_success_value': b, 'conditional_scores': scores,
                     'audit_minus_skip': differences,
                     'audit_selected': {name: value < -1e-12 for name, value in differences.items()}})
    result = {'kind': 'four arithmetic illustrations of terminal-audit identities; not a simulation campaign',
              'created_utc': datetime.now(timezone.utc).isoformat(),
              'python': platform.python_version(), 'passed': True,
              'checker_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
              'source_urls': ['https://arxiv.org/html/2001.07203v2#S7',
                              'https://arxiv.org/html/2004.08128v5#S3'],
              'examples': rows, 'max_abs_errors': residuals,
              'elapsed_seconds': perf_counter() - started}
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == '__main__':
    main()
