#!/usr/bin/env python3
"""Finite action-target/decision-loss audit; no old optimizer or new episode."""
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
LATENTS = tuple(product(BITS, repeat=2))
VERTICES = ((F(0), F(0)), (F(2, 11), F(0)), (F(4, 55),)*2, (F(0), F(8, 99)))
PROGRAMS = tuple(product(BITS, range(4)))
TOL, MAX_ERROR, COUNTS = D('1e-60'), D(0), Counter()
MOUNT = Path('/mnt/bioIce1')
ROOT = MOUNT/'fep-ideas/formal-checks/fep-action-target-audit-v1'
PREVIOUS = MOUNT/'fep-ideas/formal-checks/fep-decision-window-v1/attempt-01'
PREVIOUS_SHA = '1fce0283efdb6620bb8a9678d3aeb641f364edf7f3f7642e70c65dc43a5e4821'
REPORT_SHA = '06d5784fb020a7db6af5e4b3735de63eb444df7367fdda7e28b9af0346fb4314'


def dec(x):
    return D(x.numerator)/D(x.denominator) if isinstance(x, F) else D(x)


def check(group, label, condition):
    if not condition:
        raise AssertionError((group, label))
    COUNTS[group] += 1


def close(group, label, x, y):
    global MAX_ERROR
    error = abs(dec(x)-dec(y))
    MAX_ERROR = max(MAX_ERROR, error)
    check(group, label, error <= TOL)


def bern(p, x):
    return p if x else 1-p


def entropy(q):
    return -sum((dec(p)*dec(p).ln() for p in q if p), D(0))


def kl(q, p):
    return sum((dec(x)*(dec(x)/dec(y)).ln() for x, y in zip(q, p) if x), D(0))


def encode(value):
    if isinstance(value, (F, D)):
        return str(value)
    if isinstance(value, dict):
        return {str(k): encode(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [encode(v) for v in value]
    return value


def write(path, value):
    path.write_text(json.dumps(encode(value), sort_keys=True, indent=2)+'\n')


def identity(path):
    data = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(data), sha256=sha256(data).hexdigest())


def utility_matrix():
    matrix, target = {}, {}
    for latent in LATENTS:
        theta, changed = latent
        for channel, vertex in PROGRAMS:
            good = theta != channel
            alpha = F(1 if good else 2, 10)
            beta = F(9 if good else (6 if changed else 8), 10)
            r = VERTICES[vertex]
            mass, utility = F(0), F(0)
            for w, y, a, correct, live in product(BITS, repeat=5):
                py = bern(beta if w else alpha, y)
                pfail = F(2, 25)+(F(11, 40) if w else F(3, 50))*a
                p = F(1, 2)*py*bern(r[y], a)*bern(F(3, 4)+F(3, 20)*a, correct)*bern(1-pfail, live)
                mass += p
                utility += p*(correct+F(live, 2))
            closed = F(121, 100)+(F(3, 50)*(1-alpha)+F(1, 160)*(1-beta))*r[0]
            closed += (F(3, 50)*alpha+F(1, 160)*beta)*r[1]
            check('physics', 'one-task program normalized', mass == 1)
            check('physics', 'closed physical utility', utility == closed)
            matrix[latent, (channel, vertex)] = utility
        best = max(PROGRAMS, key=lambda d: matrix[latent, d])
        check('physics', 'known-L optimum unique', sum(matrix[latent, d] == matrix[latent, best] for d in PROGRAMS) == 1)
        target[latent] = best
        for channel in BITS:
            for vertex in (0, 2, 3):
                check('physics', 'pointwise no-warning vertex dominates',
                      matrix[latent, (channel, 1)] > matrix[latent, (channel, vertex)])
        check('physics', 'signed channel gap', matrix[latent, (0, 1)]-matrix[latent, (1, 1)]
              == (2*theta-1)*F(43-10*changed, 44000))
    return matrix, target


def target_belief(q, target):
    labels = sorted(set(target.values()))
    return tuple(sum(p for p, l in zip(q, LATENTS) if target[l] == label) for label in labels)


def candidates(q, matrix):
    return {d: sum(p*matrix[l, d] for p, l in zip(q, LATENTS)) for d in PROGRAMS}


def delta(q):
    return sum(p*(2*th-1)*F(43-10*changed, 44000) for p, (th, changed) in zip(q, LATENTS))


def regret(q, matrix):
    u = candidates(q, matrix)
    w = sum(p*max(matrix[l, d] for d in PROGRAMS) for p, l in zip(q, LATENTS))
    r = w-max(u.values())
    closed = (sum(p*F(43-10*changed, 44000) for p, (_, changed) in zip(q, LATENTS))-abs(delta(q)))/2
    check('regret', 'nonnegative residual Bayes regret', r >= 0)
    check('regret', 'closed regret identity', r == closed)
    check('regret', 'channel margin identity', u[0, 1]-u[1, 1] == delta(q))
    return r


def within_target_kl(posterior, prior, target):
    labels = sorted(set(target.values()))
    post_z, prior_z = target_belief(posterior, target), target_belief(prior, target)
    result = D(0)
    for p, q, latent in zip(posterior, prior, LATENTS):
        z = labels.index(target[latent])
        result += dec(p)*(dec(p/post_z[z])/dec(q/prior_z[z])).ln()
    return result


def local_audit(q, label, origins, matrix, target, frozen=None):
    u = candidates(q, matrix)
    best = max(u, key=u.get)
    z = target_belief(q, target)
    r = regret(q, matrix)
    branches, information, target_info, conditional_info = [], D(0), D(0), D(0)
    actions = {d: F(0) for d in PROGRAMS}
    for x in BITS:
        likelihood = tuple(bern(F(9 if th else (6 if changed else 8), 10), x) for th, changed in LATENTS)
        px = sum(p*l for p, l in zip(q, likelihood))
        qx = tuple(p*l/px for p, l in zip(q, likelihood))
        zx = target_belief(qx, target)
        ux = candidates(qx, matrix)
        decision = max(ux, key=ux.get)
        actions[decision] += px
        ix, iz, within = kl(qx, q), kl(zx, z), within_target_kl(qx, q, target)
        close('information', 'posterior target KL chain', ix, iz+within)
        information += dec(px)*ix
        target_info += dec(px)*iz
        conditional_info += dec(px)*within
        branches.append(dict(x=x, probability=px, posterior=qx, target_posterior=zx,
                             sensor_information=ix, target_information=iz, within_target_information=within,
                             candidates=ux, best_program=decision, best_utility=ux[decision],
                             locked_utility=ux[best], delta=delta(qx), regret=regret(qx, matrix)))
    informed = sum(row['probability']*row['best_utility'] for row in branches)
    voi = informed-u[best]
    regret_gain = r-sum(row['probability']*row['regret'] for row in branches)
    closed_gain = (sum(row['probability']*abs(row['delta']) for row in branches)-abs(delta(q)))/2
    check('VOI', 'regret reduction equals value', voi == regret_gain == closed_gain)
    check('VOI', 'nonnegative task VOI', voi >= 0)
    check('VOI', 'zero iff prior-optimal program remains optimal',
          (voi == 0) == all(row['locked_utility'] == row['best_utility'] for row in branches))
    for d in PROGRAMS:
        check('VOI', 'fixed-program posterior tower', sum(row['probability']*row['candidates'][d] for row in branches) == u[d])
    close('information', 'calibration entropy identity L', information,
          entropy(q)-sum((dec(row['probability'])*entropy(row['posterior']) for row in branches), D(0)))
    close('information', 'calibration entropy identity Z', target_info,
          entropy(z)-sum((dec(row['probability'])*entropy(row['target_posterior']) for row in branches), D(0)))
    close('information', 'calibration information chain', information, target_info+conditional_info)
    check('information', 'data processing for calibration', -TOL <= target_info <= information+TOL)
    if frozen is not None:
        check('frozen local', 'VOI exact readback', voi == F(frozen['VOI']))
        check('frozen local', 'prior decision readback', list(best) == frozen['prior_program'])
        close('frozen local', 'calibration information readback', information, frozen['calibration_information'])
        for d in PROGRAMS:
            check('frozen local', 'prior candidate exact readback', u[d] == F(frozen['candidates'][str(d)]))
        for row, old in zip(branches, frozen['branches']):
            check('frozen local', 'branch mass/posterior readback', row['probability'] == F(old['probability'])
                  and row['posterior'] == tuple(F(p) for p in old['posterior']))
            for d in PROGRAMS:
                check('frozen local', 'posterior candidate readback', row['candidates'][d] == F(old['candidates'][str(d)]))
    thresholds = dict(task=4*dec(voi), sensor=4*dec(voi)+information, action_target=4*dec(voi)+target_info)
    decisions = {kind: [dict(price=price, buys=price < bound-TOL,
                       chosen_net_gain=dec(voi)-price/4 if price < bound-TOL else D(0))
                       for price in (D(0), D('.0001'), D(3).ln())] for kind, bound in thresholds.items()}
    return dict(label=label, origins=origins, belief=q, target_belief=z, candidates=u,
                prior_program=best, delta=delta(q), residual_regret=r, VOI=voi, branches=branches,
                sensor_information=information, target_information=target_info, within_target_information=conditional_info,
                posterior_decision_distribution=actions, posterior_decision_entropy=entropy(actions.values()),
                probability_decision_changes=1-actions[best], thresholds=thresholds, decisions=decisions)


def gate(prefix, event):
    if event[0] == 'E':
        live = all(e[3] == 1 for e in prefix if e[0] == 'F' and e[1] == 1)
        return int(prefix[0] == ('M', 1) and event[1] < 3 and live)
    return int(event[0] in ('Y', 'F') and event[1] == 1)


def rescore(label, joint, old, target):
    check('saved joint', label+' normalized', sum(sum(row) for row in joint.values()) == 1)
    prefixes = defaultdict(lambda: [F(0)]*4)
    utility = F(0)
    for history, row in joint.items():
        for end in range(len(history)+1):
            for i, p in enumerate(row):
                prefixes[history[:end]][i] += p
        utility += sum(row)*sum((F(e[2])+F(e[3], 2) for e in history if e[0] == 'F' and e[2] is not None), F(0))
    check('saved joint', label+' utility readback', utility == F(old['U']))
    children = defaultdict(list)
    for prefix in prefixes:
        if prefix:
            children[prefix[:-1]].append(prefix)
    totals = dict(I_L=D(0), I_Z=D(0), I_within=D(0), J_L=D(0), J_Z=D(0), J_within=D(0))
    event_rows = []
    zf = 1+(1+D(4).exp())*(1+D(2).exp())
    direct_score = D(2).ln()
    for parent, outcomes in children.items():
        mass = sum(prefixes[parent])
        prior = tuple(p/mass for p in prefixes[parent])
        prior_z = target_belief(prior, target)
        event = outcomes[0][-1]
        tag, g = event[0], gate(parent, event)
        check('gate', label+' gate predictable', all(gate(parent, child[-1]) == g for child in outcomes))
        obs = tag in ('E', 'Y', 'F')
        if tag in ('E', 'Y'):
            pref = {o: D(1)/3 for o in (0, 1, None)}
        elif tag == 'F':
            pref = {(t, v): D(4*t+2*v).exp()/zf for t, v in product(BITS, repeat=2)}
            pref[None] = 1/zf
        il, iz, iw, ce, score = (D(0),)*5
        posts = {}
        for child in outcomes:
            row = prefixes[child]
            pmass = sum(row)
            post = tuple(p/pmass for p in row)
            post_z = target_belief(post, target)
            weight = dec(pmass/mass)
            kl_l, kl_z, kl_within = kl(post, prior), kl(post_z, prior_z), within_target_kl(post, prior, target)
            close('chain', label+' posterior KL split', kl_l, kl_z+kl_within)
            il += weight*kl_l
            iz += weight*kl_z
            iw += weight*kl_within
            if not obs:
                check('access', label+' control has zero conditional information', post == prior and post_z == prior_z)
                continue
            e = child[-1]
            outcome = e[-1] if tag in ('E', 'Y') else (None if e[2] is None else tuple(e[2:]))
            posts[outcome] = post_z
            desired = post_z if g else prior_z
            ce -= weight*pref[outcome].ln()
            score += weight*sum((dec(p)*(dec(pre)/(dec(ref)*pref[outcome])).ln()
                                 for p, pre, ref in zip(post_z, prior_z, desired)), D(0))
        check('chain', label+' event data processing', -TOL <= iz <= il+TOL)
        if obs:
            normalized = sum((p*sum((dec(v) for v in (posts.get(o, prior_z) if g else prior_z)), D(0))
                              for o, p in pref.items()), D(0))
            close('desired joint', label+' target joint normalized', normalized, 1)
            close('desired joint', label+' direct target score', score, ce-g*iz)
            direct_score += dec(mass)*score
        for key, value in (('I_L', il), ('I_Z', iz), ('I_within', iw),
                           ('J_L', g*il), ('J_Z', g*iz), ('J_within', g*iw)):
            totals[key] += dec(mass)*value
        event_rows.append(dict(history_before=parent, event=tag, probability=mass, gate=g,
                               I_L=il, I_Z=iz, I_within=iw, preference_surprisal=ce,
                               direct_target_score=score))
    close('saved joint', label+' full information readback', totals['I_L'], old['information'])
    close('saved joint', label+' window information readback', totals['J_L'], old['window_information'])
    close('chain', label+' full information target chain', totals['I_L'], totals['I_Z']+totals['I_within'])
    close('chain', label+' gated information target chain', totals['J_L'], totals['J_Z']+totals['J_within'])
    initial = tuple(prefixes[()])
    final_iz = sum((dec(sum(row))*kl(target_belief(tuple(p/sum(row) for p in row), target),
                                   target_belief(initial, target)) for row in joint.values()), D(0))
    close('chain', label+' full target transcript identity', totals['I_Z'], final_iz)
    constant = D(2).ln()+3*D(3).ln()+2*zf.ln()
    close('desired joint', label+' total target score', direct_score, constant-4*dec(utility)-totals['J_Z'])
    return dict(label=label, scope='fixed saved policy; no target replanning', U=utility,
                **totals, reduced_target_score=-4*dec(utility)-totals['J_Z'],
                direct_target_score_at_zero_price=direct_score, histories=len(joint)), event_rows


def run(output):
    started, start, cpu = datetime.now(timezone.utc).isoformat(), perf_counter(), process_time()
    source = Path(__file__).resolve().parent
    if not MOUNT.is_mount() or not output.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError('Mounted external FEP namespace required')
    output.mkdir(parents=True, exist_ok=False)
    (output/'inputs').mkdir()
    inputs, preserved = [], []
    def log(message):
        with (output/'RUN_LOG.txt').open('a') as stream:
            stream.write(str(message)+'\n')
        print(message, flush=True)
    try:
        log('Started '+started+'; one process; standalone identities and saved-policy rescore; no episode optimizer')
        check('integrity', 'prior manifest', identity(PREVIOUS/'MANIFEST.json')['sha256'] == PREVIOUS_SHA)
        check('integrity', 'prior report', identity(source/'FEP_DECISION_WINDOW_V1_REPORT.md')['sha256'] == REPORT_SHA)
        old_manifest = json.loads((PREVIOUS/'MANIFEST.json').read_text())
        unique = {entry['path']: entry for group in ('inputs', 'outputs', 'preserved') for entry in old_manifest[group]}
        for entry in unique.values():
            check('integrity', 'prior '+entry['path'], identity(Path(entry['path'])) == entry)
            preserved.append(entry)
        originals = [source/'FEP_ACTION_TARGET_AUDIT_V1.md', Path(__file__).resolve(),
                     source/'FEP_DECISION_WINDOW_V1.md', source/'FEP_DECISION_WINDOW_V1_REPORT.md',
                     source/'FEP_TWO_DECISION_EFE_V1.md', PREVIOUS/'MANIFEST.json',
                     PREVIOUS/'VOI.json', PREVIOUS/'RESULTS.json']
        originals += [PREVIOUS/('window_'+timing+'_JOINT.json') for timing in ('skip', 'early', 'between', 'late')]
        for path in originals:
            entry = identity(path)
            inputs.append(entry)
            shutil.copyfile(path, output/'inputs'/path.name)
            check('integrity', 'frozen '+path.name, identity(output/'inputs'/path.name)['sha256'] == entry['sha256'])
        write(output/'PREPARATION.json', dict(inputs=inputs, preserved=preserved, tolerance=TOL,
               scope='ten frozen VOI beliefs plus two algebraic controls; four saved-policy rescores',
               new_episode_laws=0, old_optimizer_imports=False, primary_sources=[
               'https://arxiv.org/html/2004.08128v5#S3', 'https://web.stanford.edu/~bvr/pubs/IDS.pdf']))
        log('Scope and source snapshots sealed before calculation')
        matrix, target = utility_matrix()
        write(output/'UTILITY_TARGET.json', dict(matrix=matrix, target_by_latent=target,
                                               target_labels=sorted(set(target.values()))))
        log('Physical utility, dominance and action-gap identities passed; target map derived')
        old_voi = json.loads((output/'inputs/VOI.json').read_text())
        check('scope', 'ten frozen cases', len(old_voi) == 10)
        cases = [local_audit(tuple(F(p) for p in row['belief']), 'frozen_'+str(i), row['origins'], matrix, target, row)
                 for i, row in enumerate(old_voi)]
        controls = [tuple(F(x, 20) for x in values) for values in ((1, 9, 9, 1), (9, 1, 1, 9))]
        for label, q in zip(('q_plus', 'q_minus'), controls):
            cases.append(local_audit(q, label, ['declared algebraic sufficiency control; not asserted reachable'], matrix, target))
        plus, minus = cases[-2:]
        check('representation', 'same target posterior in controls', plus['target_belief'] == minus['target_belief'])
        check('representation', 'same change marginal in controls',
              sum(p for p, l in zip(controls[0], LATENTS) if l[1]) == sum(p for p, l in zip(controls[1], LATENTS) if l[1]))
        check('representation', 'opposite nonzero action margins', plus['delta'] == -minus['delta'] and plus['delta'] != 0)
        check('representation', 'different optimal programs', plus['prior_program'] != minus['prior_program'])
        write(output/'LOCAL_CASES.json', cases)
        log(f'Local audit completed: {len(cases)} beliefs; information, decision entropy and task regret kept distinct')
        old_results = json.loads((output/'inputs/RESULTS.json').read_text())
        policies = {}
        for timing in ('skip', 'early', 'between', 'late'):
            label = 'window_'+timing
            data = json.loads((output/('inputs/'+label+'_JOINT.json')).read_text())
            check('scope', label+' latent order', tuple(tuple(l) for l in data['latent_order']) == LATENTS)
            joint = {tuple(tuple(e) for e in row['history']): tuple(F(p) for p in row['joint_mass']) for row in data['rows']}
            result, events = rescore(label, joint, old_results['laws'][label], target)
            policies[timing] = result
            write(output/(label+'_EVENT_AUDIT.json'), events)
            log(f'Rescored {label}: {len(joint)} saved histories; J_Z={result["J_Z"]:.15f}')
        comparisons = {}
        for timing in ('early', 'between', 'late'):
            result, baseline = policies[timing], policies['skip']
            gain = result['U']-baseline['U']
            raw = 4*dec(gain)+result['J_Z']-baseline['J_Z']
            boundary = D(0) if abs(raw) <= TOL else raw
            comparisons[timing] = dict(scope='choice between frozen policies; not reoptimized target controller',
                       raw_utility_gain=gain, fixed_policy_target_threshold=boundary, unrounded_threshold=raw,
                       fixed_policy_sensor_threshold=D(old_results['comparisons'][timing]['purchase_threshold']),
                       task_threshold=4*dec(gain),
                       decisions=[dict(price=price, buys=price < boundary-TOL,
                                  chosen_net_gain=dec(gain)-price/4 if price < boundary-TOL else D(0))
                                  for price in (D(0), D('.0001'), D(3).ln())])
        check('late identity', 'no late task difference', policies['late']['U'] == policies['skip']['U'])
        close('late identity', 'no late target window difference', policies['late']['J_Z'], policies['skip']['J_Z'])
        check('scope', 'exactly four saved policies, twelve local beliefs', len(policies) == 4 and len(cases) == 12)
        for entry in inputs+preserved:
            check('integrity', 'final '+entry['path'], identity(Path(entry['path'])) == entry)
        summary = dict(assertions=sum(COUNTS.values()), groups=dict(COUNTS), max_decimal_residual=MAX_ERROR,
                       local_beliefs=len(cases), local_calibration_branches=2*len(cases),
                       saved_policies=len(policies), saved_histories=sum(p['histories'] for p in policies.values()),
                       new_episode_laws=0, selected_operating_price=None)
        write(output/'RESULTS.json', dict(summary=summary, target_by_latent=target,
                  policies=policies, fixed_policy_comparisons=comparisons,
                  local_summary=[{key:c[key] for key in ('label', 'belief', 'VOI', 'sensor_information',
                      'target_information', 'within_target_information', 'posterior_decision_entropy',
                      'probability_decision_changes', 'thresholds')} for c in cases]))
        finished, wall, cpu_seconds = datetime.now(timezone.utc).isoformat(), perf_counter()-start, process_time()-cpu
        log(f'PASS: {summary["assertions"]} checks, max residual {MAX_ERROR}; {wall:.6f} seconds wall')
        outputs = [identity(p) for p in sorted(output.rglob('*')) if p.is_file()]
        write(output/'MANIFEST.json', dict(status='complete', started_utc=started, finished_utc=finished,
              wall_seconds=wall, cpu_seconds=cpu_seconds, python=platform.python_version(), processes=1,
              inputs=inputs, outputs=outputs, preserved=preserved, summary=summary))
    except Exception:
        log(traceback.format_exc())
        write(output/'FAILURE.json', dict(status='failed', inputs=inputs, preserved=preserved,
              assertions=sum(COUNTS.values()), groups=dict(COUNTS), wall_seconds=perf_counter()-start))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
