#!/usr/bin/env python3
"""Decision-window EFE and exact instrumental VOI; frozen shared physics."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal as D
from fractions import Fraction as F
from functools import lru_cache
from hashlib import sha256
import importlib.util
from itertools import product
import json
from pathlib import Path
import platform
import shutil
import sys
from time import perf_counter, process_time
import traceback
from typing import NamedTuple

sys.dont_write_bytecode = True
MOUNT = Path('/mnt/bioIce1')
ROOT = MOUNT/'fep-ideas/formal-checks/fep-decision-window-v1'
PREVIOUS = MOUNT/'fep-ideas/formal-checks/fep-two-decision-efe-v1/attempt-01'
BASE_SHA = '341e672aded61732f84cf3c340972d6ea99b809cdfc145dc7b09cc6d54b8d5a8'
PREVIOUS_SHA = '5203ecdedaa7fe5a7bb91187ce0a0ea021981668f8b191cf2a5c88796d9ce085'
BASE_REPORT_SHA = '078490e0b9e4f4949e6736c0fae920f0f4f051c1d4e67bcbd4dc07a7886b6391'
b = None


class Value(NamedTuple):
    U: F
    Ic: D
    Iy: D
    Ifb: D
    J: D


ZERO = Value(F(0), D(0), D(0), D(0), D(0))


def add(v, w):
    return Value(*(x+y for x, y in zip(v, w)))


def mean(rows):
    return Value(sum(p*v.U for p, v in rows),
                 *(sum((b.dec(p)*v[j] for p, v in rows), D(0)) for j in range(1, 5)))


def record(v):
    return dict(**b.value_record(v), window_information=v.J)


class Planner:
    kind = 'window'

    def __init__(self, slot, buy):
        self.slot, self.buy, self.nodes = slot, buy, {}

    def score(self, value):
        return -4*b.dec(value.U)-value.J

    @lru_cache(None)
    def solve(self, t, q, live, received):
        b.check('beliefs', 'full positive support', sum(q) == 1 and all(p > 0 for p in q))
        if t == self.slot and self.buy and not received:
            gate = int(live and t < 3)
            rows = []
            for x in b.BITS:
                px, qx, ix = b.update(q, b.cal_law(x))
                rows.append((px, add(self.solve(t, qx, live, True),
                                     Value(F(0), ix, D(0), D(0), gate*ix))))
            result, node = mean(rows), dict(event='calibration', gate=gate)
        elif t == 3:
            result, node = ZERO, dict(event='terminal')
        elif not live:
            result, node = self.solve(t+1, q, False, received), dict(event='inactive')
        else:
            candidates = []
            gate = int(t == 1)
            for channel in b.BITS:
                responses, warnings = {}, {}
                for y in b.BITS:
                    py, qy, iy = b.update(q, b.warning_law(channel, y))
                    warnings[y] = py, iy
                    for a in b.BITS:
                        rows = []
                        for v in b.BITS:
                            pv, qv, iv = b.update(qy, b.feedback_law(channel, y, a, v))
                            later = self.solve(t+1, qv, bool(v), received)
                            local = Value(F(3, 4)+F(3, 20)*a+F(v, 2), D(0), D(0), iv, gate*iv)
                            rows.append((pv, add(local, later)))
                        responses[y, a] = mean(rows)
                start = len(candidates)
                info_y = sum((b.dec(p)*ig for p, ig in warnings.values()), D(0))
                for vertex, response in enumerate(b.VERTICES):
                    rows = [(warnings[y][0]*b.bern(response[y], a), responses[y, a])
                            for y, a in product(b.BITS, repeat=2)]
                    value = add(mean(rows), Value(F(0), D(0), info_y, D(0), gate*info_y))
                    candidates.append(dict(channel=channel, vertex=vertex,
                                           value=value, score=self.score(value)))
                intercept = candidates[start]['score']
                coeff = [b.dec(warnings[y][0])*(self.score(responses[y, 1])-self.score(responses[y, 0]))
                         for y in b.BITS]
                for candidate in candidates[start:]:
                    r = b.VERTICES[candidate['vertex']]
                    b.close('Bellman', 'affine score on complete response polygon', candidate['score'],
                            intercept+sum(b.dec(r[y])*coeff[y] for y in b.BITS))
            selected = candidates[0]
            for candidate in candidates[1:]:
                if candidate['score'] < selected['score']-b.TOL:
                    selected = candidate
            b.check('Bellman', 'complete eight-candidate optimum', len(candidates) == 8 and
                    all(selected['score'] <= c['score']+b.TOL for c in candidates))
            if t == 2:
                utilities = utility_candidates(q)
                b.check('terminal value', 'window chooses task optimum',
                        selected['value'].U == max(utilities.values()))
                for candidate in candidates:
                    b.check('terminal value', 'physical candidate utility', candidate['value'].U ==
                            utilities[candidate['channel'], candidate['vertex']])
                    b.close('terminal value', 'no terminal bonus', candidate['value'].J, 0)
            result = selected['value']
            node = dict(event='decision', gate=gate, channel=selected['channel'], vertex=selected['vertex'],
                        candidates=[dict(channel=c['channel'], vertex=c['vertex'], score=c['score'],
                                         **record(c['value'])) for c in candidates])
        self.nodes[t, q, live, received] = dict(t=t, belief=q, live=live, received=received,
                                              **node, **record(result), score=self.score(result))
        return result

    def choice(self, t, q):
        received = bool(self.buy and self.slot <= t)
        self.solve(t, q, True, received)
        node = self.nodes[t, q, True, received]
        b.check('access', 'committed choice uses pre-warning belief', node['event'] == 'decision')
        return node['channel'], node['vertex']


@lru_cache(None)
def physical_utility(latent, channel, vertex):
    r = b.VERTICES[vertex]
    return sum(F(1, 2)*b.sensor(latent, w, channel, y)*b.bern(r[y], a)*
               (F(3, 4)+F(3, 20)*a+F(1, 2)*(1-b.failure(w, a)))
               for w, y, a in product(b.BITS, repeat=3))


def utility_candidates(q):
    return {(channel, vertex): sum(p*physical_utility(l, channel, vertex)
                                   for p, l in zip(q, b.LATENTS))
            for channel in b.BITS for vertex in range(4)}


def voi_audit(old_policies):
    beliefs = {b.PRIOR: ['fair-prior algebraic example'],
               (F(1, 20), F(1, 20), F(9, 20), F(9, 20)): ['confident-A algebraic example; not asserted reachable']}
    for node in old_policies['task_between']:
        if node['event'] == 'calibration' and node['t'] == 2 and node['live']:
            q = tuple(F(p) for p in node['belief'])
            beliefs.setdefault(q, []).append('frozen task_between live calibration context')
    output = []
    for q, origins in sorted(beliefs.items()):
        candidates = utility_candidates(q)
        best = max(candidates, key=candidates.get)
        value = candidates[best]
        branches, expected, locked, info = [], F(0), F(0), D(0)
        all_candidates = []
        for x in b.BITS:
            px, qx, ix = b.update(q, b.cal_law(x))
            ux = utility_candidates(qx)
            choice = max(ux, key=ux.get)
            expected += px*ux[choice]
            locked += px*ux[best]
            info += b.dec(px)*ix
            all_candidates.append((px, ux))
            branches.append(dict(x=x, probability=px, posterior=qx, information=ix,
                                 best_program=choice, best_utility=ux[choice],
                                 locked_utility=ux[best], candidates=ux))
        for program, utility in candidates.items():
            b.check('VOI', 'posterior tower for each fixed program',
                    sum(px*ux[program] for px, ux in all_candidates) == utility)
        gain = expected-value
        regret = sum(branch['probability']*(branch['best_utility']-branch['locked_utility'])
                     for branch in branches)
        stays_optimal = all(branch['best_utility'] == branch['locked_utility'] for branch in branches)
        b.check('VOI', 'nonnegative instrumental value', gain >= 0)
        b.check('VOI', 'regret decomposition', gain == regret and locked == value)
        b.check('VOI', 'zero iff common optimal program', (gain == 0) == stays_optimal)
        b.check('VOI', 'calibration posterior martingale',
                all(sum(branch['probability']*branch['posterior'][i] for branch in branches) == q[i]
                    for i in range(4)))
        output.append(dict(belief=q, origins=origins, candidates=candidates,
                           prior_program=best, prior_value=value, branches=branches,
                           informed_value=expected, locked_value=locked, VOI=gain,
                           common_optimal_program=stays_optimal, calibration_information=info,
                           task_threshold=4*gain, window_threshold=4*b.dec(gain)+info))
    return output


def event_gate(prefix, event):
    """Depends on the event schedule and preceding observations, never its outcome."""
    if event[0] == 'E':
        bought = prefix[0] == ('M', 1)
        live = all(e[3] == 1 for e in prefix if e[0] == 'F' and e[1] == 1)
        return int(bought and live and event[1] < 3)
    return int(event[0] in ('Y', 'F') and event[1] == 1)


def window_audit(label, joint, result, expected):
    prefixes = defaultdict(lambda: [F(0)]*4)
    for history, row in joint.items():
        for end in range(len(history)+1):
            for i, mass in enumerate(row):
                prefixes[history[:end]][i] += mass
    children = defaultdict(list)
    for prefix in prefixes:
        if prefix and prefix[-1][0] in ('E', 'Y', 'F'):
            children[prefix[:-1]].append(prefix)
    zf = 1+(1+D(4).exp())*(1+D(2).exp())
    total_j, total_i, direct = D(0), D(0), D(2).ln()
    rows, stages = [], {}
    for parent, outcomes in children.items():
        parent_row = prefixes[parent]
        parent_mass = sum(parent_row)
        prior = tuple(p/parent_mass for p in parent_row)
        event = outcomes[0][-1]
        tag, index = event[:2]
        g = event_gate(parent, event)
        b.check('gate', label+' predictable event gate',
                all(event_gate(parent, child[-1]) == g for child in outcomes))
        if tag in ('E', 'Y'):
            preferences = {o: D(1)/3 for o in (0, 1, None)}
        else:
            preferences = {(t, v): D(4*t+2*v).exp()/zf for t, v in product(b.BITS, repeat=2)}
            preferences[None] = 1/zf
        posterior_by_outcome = {}
        local_i, local_ce, local_g = D(0), D(0), D(0)
        for child in outcomes:
            row = prefixes[child]
            mass = sum(row)
            posterior = tuple(p/mass for p in row)
            event = child[-1]
            outcome = event[-1] if tag in ('E', 'Y') else (None if event[2] is None else tuple(event[2:]))
            posterior_by_outcome[outcome] = posterior
            desired_conditional = posterior if g else prior
            local_ce -= b.dec(mass/parent_mass)*preferences[outcome].ln()
            for p, pre, post, desired in zip(row, prior, posterior, desired_conditional):
                weight = b.dec(p/parent_mass)
                local_i += weight*(b.dec(post)/b.dec(pre)).ln()
                local_g += weight*(b.dec(pre)/(b.dec(desired)*preferences[outcome])).ln()
        desired_mass = D(0)
        for outcome, preference in preferences.items():
            conditional = posterior_by_outcome.get(outcome, prior) if g else prior
            desired_mass += preference*sum((b.dec(p) for p in conditional), D(0))
        b.close('desired joint', label+' normalized at event', desired_mass, 1)
        b.close('desired joint', label+' direct window identity', local_g, local_ce-g*local_i)
        b.check('information', label+' nonnegative conditional information', local_i >= -b.TOL)
        weight = b.dec(parent_mass)
        total_j += weight*g*local_i
        total_i += weight*local_i
        direct += weight*local_g
        stage = f'{tag}{index}'
        if tag == 'E' and index == 2:
            live = all(e[3] == 1 for e in parent if e[0] == 'F' and e[1] == 1)
            stage += '_live' if live else '_dead'
        bucket = stages.setdefault(stage, dict(event_mass=F(0), information=D(0), window_information=D(0)))
        bucket['event_mass'] += parent_mass
        bucket['information'] += weight*local_i
        bucket['window_information'] += weight*g*local_i
        rows.append(dict(history_before=parent, probability=parent_mass, gate=g,
                         information=local_i, preference_surprisal=local_ce, direct_score=local_g))
    b.close('window readback', label+' total information', total_i, result['information'])
    b.close('window readback', label+' Bellman window information', total_j, expected.J)
    b.close('window readback', label+' direct total desired-joint score', direct,
            D(2).ln()+3*D(3).ln()+2*zf.ln()-4*b.dec(result['U'])-total_j)
    b.check('window readback', label+' bounded by all information', -b.TOL <= total_j <= total_i+b.TOL)
    for stage in ('Y2', 'F2', 'E3', 'E2_dead'):
        if stage in stages:
            b.close('gate', label+' no bonus at '+stage, stages[stage]['window_information'], 0)
    selected_good = sum(sum(p for l, p in zip(b.LATENTS, row) if l[0] != event[2])
                        for history, row in joint.items() for event in history
                        if event[0] == 'C' and event[1] == 2)
    result.update(window_information=total_j, reduced_window=-4*b.dec(result['U'])-total_j,
                  good_channel_task2_given_reached=selected_good/result['metrics']['reach2'],
                  window_stages=stages)
    return rows


def read_joint(path):
    raw = json.loads(path.read_text())
    return {tuple(tuple(e) for e in row['history']): [F(p) for p in row['joint_mass']]
            for row in raw['rows']}


def identity(path):
    data = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(data), sha256=sha256(data).hexdigest())


def run(output):
    global b
    start, cpu, started = perf_counter(), process_time(), datetime.now(timezone.utc).isoformat()
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
        log('Started '+started+'; one process; frozen shared physics, new planner and joint/VOI audit')
        if identity(PREVIOUS/'MANIFEST.json')['sha256'] != PREVIOUS_SHA:
            raise AssertionError('Previous manifest identity changed')
        if identity(source/'check_fep_two_decision_efe.py')['sha256'] != BASE_SHA:
            raise AssertionError('Frozen physics identity changed')
        if identity(source/'FEP_TWO_DECISION_EFE_V1_REPORT.md')['sha256'] != BASE_REPORT_SHA:
            raise AssertionError('Previous report identity changed')
        originals = [source/'FEP_DECISION_WINDOW_V1.md', Path(__file__).resolve(),
                     source/'FEP_TWO_DECISION_EFE_V1.md', source/'check_fep_two_decision_efe.py',
                     source/'FEP_TWO_DECISION_EFE_V1_REPORT.md', PREVIOUS/'MANIFEST.json',
                     PREVIOUS/'RESULTS.json', PREVIOUS/'POLICIES.json']
        originals += [PREVIOUS/('task_'+timing+'_JOINT.json') for timing in ('skip', 'early', 'between', 'late')]
        for path in originals:
            entry = identity(path)
            inputs.append(entry)
            shutil.copyfile(path, output/'inputs'/path.name)
            if identity(output/'inputs'/path.name)['sha256'] != entry['sha256']:
                raise AssertionError('Snapshot mismatch '+path.name)
        loader = importlib.util.spec_from_file_location('frozen_two_decision', output/'inputs/check_fep_two_decision_efe.py')
        b = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(b)
        old_manifest = json.loads((output/'inputs/MANIFEST.json').read_text())
        for group in ('inputs', 'outputs', 'preserved'):
            for entry in old_manifest[group]:
                b.check('integrity', 'prior '+entry['path'], identity(Path(entry['path'])) == entry)
                preserved.append(entry)
        b.write(output/'PREPARATION.json', dict(inputs=inputs, preserved=preserved,
                shared_physics_sha256=BASE_SHA, processes=1, tolerance=b.TOL,
                scope='four window laws; frozen EFE/task references; declared local VOI contexts',
                primary_sources=['https://arxiv.org/html/2004.08128v5#S3',
                                 'https://arxiv.org/html/2001.07203v2#S7']))
        log('Specification, code, reference records and shared source frozen before qualification')
        qualification = b.qualify()
        b.write(output/'QUALIFICATION.json', qualification)
        log(f'Shared physics qualification passed: {qualification["assertions"]} checks')
        old_policies = json.loads((output/'inputs/POLICIES.json').read_text())
        voi = voi_audit(old_policies)
        b.write(output/'VOI.json', voi)
        log(f'Instrumental VOI identities passed: {len(voi)} declared distinct beliefs')
        planners, values = {}, {}
        for timing, slot, buy in [('skip', 1, 0), ('early', 1, 1), ('between', 2, 1), ('late', 3, 1)]:
            label = 'window_'+timing
            planner = Planner(slot, buy)
            value = planner.solve(1, b.PRIOR, True, False)
            planners[label], values[label] = planner, value
            log(f'Planned {label}: {len(planner.nodes)} contexts; U={b.dec(value.U):.15f}; J={value.J:.15f}')
        b.write(output/'POLICIES.json', {label: list(p.nodes.values()) for label, p in planners.items()})
        planned_counts = {label: len(p.nodes) for label, p in planners.items()}
        results, joints = {}, {}
        for label, planner in planners.items():
            joint, replayed, leaves = b.enumerate_law(planner, planner.slot, planner.buy)
            result = b.analyze_law(label, joint, replayed, leaves, planner, planner.buy, values[label])
            audit = window_audit(label, joint, result, values[label])
            results[label], joints[label] = result, joint
            b.write(output/(label+'_JOINT.json'), dict(latent_order=b.LATENTS,
                    rows=[dict(history=h, joint_mass=row) for h, row in joint.items()]))
            b.write(output/(label+'_EVENT_AUDIT.json'), audit)
            log(f'Read back {label}: {len(joint)} histories, {leaves} physical leaves; gated joint score verified')
        b.check('late control', 'same entire marginalized task law',
                b.project_tasks(joints['window_late']) == b.project_tasks(joints['window_skip']))
        b.check('late control', 'zero late task gain', results['window_late']['U'] == results['window_skip']['U'])
        b.close('late control', 'same window information', values['window_late'].J, values['window_skip'].J)
        previous_results = json.loads((output/'inputs/RESULTS.json').read_text())
        comparisons, reference_comparisons = {}, {}
        baseline = results['window_skip']
        for timing in ('skip', 'early', 'between', 'late'):
            result = results['window_'+timing]
            task = previous_results['laws']['task_'+timing]
            efe = previous_results['laws']['EFE_'+timing]
            old_joint = read_joint(output/('inputs/task_'+timing+'_JOINT.json'))
            b.check('benchmark', timing+' task optimum dominates', result['U'] <= F(task['U']))
            reference_comparisons[timing] = dict(window_minus_task_U=result['U']-F(task['U']),
                    window_minus_EFE_U=result['U']-F(efe['U']),
                    same_task_law=b.project_tasks(joints['window_'+timing]) == b.project_tasks(old_joint),
                    task_U=F(task['U']), EFE_U=F(efe['U']))
            if timing == 'skip':
                continue
            gain = result['U']-baseline['U']
            delta_j = result['window_information']-baseline['window_information']
            raw_boundary = 4*b.dec(gain)+delta_j
            dynamic_boundary = (planners['window_skip'].score(values['window_skip'])-
                                planners['window_'+timing].score(values['window_'+timing]))
            b.close('function', timing+' purchase boundary', raw_boundary, dynamic_boundary)
            boundary = D(0) if abs(raw_boundary) <= b.TOL else raw_boundary
            dynamic_boundary = D(0) if abs(dynamic_boundary) <= b.TOL else dynamic_boundary
            b.check('function', timing+' direct/dynamic purchase decision unchanged by precision',
                    all((price < boundary-b.TOL) == (price < dynamic_boundary-b.TOL)
                        for price in (D(0), D('.0001'), D(3).ln())))
            comparisons[timing] = dict(raw_utility_gain=gain, window_information_change=delta_j,
                    full_information_change=result['information']-baseline['information'],
                    purchase_threshold=boundary, unrounded_purchase_threshold=raw_boundary,
                    functional_price_boundary=4*b.dec(gain),
                    positive_functional_interval=gain > 0,
                    decisions=[dict(price=price, buys=price < boundary-b.TOL,
                                    chosen_net_gain=b.dec(gain)-price/4 if price < boundary-b.TOL else D(0))
                               for price in (D(0), D('.0001'), D(3).ln())])
        b.check('scope', 'enumeration only used frozen planned contexts',
                planned_counts == {label: len(p.nodes) for label, p in planners.items()})
        b.check('scope', 'exactly four new laws', len(results) == 4)
        for entry in inputs+preserved:
            b.check('integrity', 'final '+entry['path'], identity(Path(entry['path'])) == entry)
        summary = dict(assertions=sum(b.COUNTS.values()), groups=dict(b.COUNTS),
                       max_decimal_residual=b.MAX_ERROR, executed_laws=len(results),
                       planned_contexts=sum(len(p.nodes) for p in planners.values()),
                       decision_contexts=sum(n['event'] == 'decision' for p in planners.values() for n in p.nodes.values()),
                       observed_histories=sum(r['observed_histories'] for r in results.values()),
                       physical_leaves=sum(r['physical_leaves'] for r in results.values()),
                       VOI_beliefs=len(voi), selected_operating_price=None)
        b.write(output/'RESULTS.json', dict(summary=summary, laws=results, comparisons=comparisons,
                                          reference_comparisons=reference_comparisons))
        finished = datetime.now(timezone.utc).isoformat()
        wall, cpu_seconds = perf_counter()-start, process_time()-cpu
        log(f'PASS: {summary["assertions"]} checks, max residual {b.MAX_ERROR}; {wall:.6f} seconds wall')
        outputs = [identity(p) for p in sorted(output.rglob('*')) if p.is_file()]
        b.write(output/'MANIFEST.json', dict(status='complete', started_utc=started, finished_utc=finished,
                wall_seconds=wall, cpu_seconds=cpu_seconds, python=platform.python_version(), processes=1,
                inputs=inputs, outputs=outputs, preserved=preserved, summary=summary))
    except Exception:
        log(traceback.format_exc())
        (output/'FAILURE.json').write_text(json.dumps(dict(status='failed', inputs=inputs,
                preserved=preserved, wall_seconds=perf_counter()-start), indent=2)+'\n')
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
