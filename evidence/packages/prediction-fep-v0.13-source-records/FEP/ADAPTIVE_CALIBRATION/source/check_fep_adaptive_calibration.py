#!/usr/bin/env python3
"""Exact optimal stopping for the frozen factor-revision task."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction as F
import gzip
from hashlib import sha256
import importlib.util
from itertools import product
import json
from math import comb, factorial, fsum, log
from pathlib import Path
import platform
import shutil
from time import perf_counter, process_time
import traceback

MOUNT = Path('/mnt/bioIce1')
ROOT = MOUNT/'fep-ideas/formal-checks/fep-adaptive-calibration-v1'
PRIOR = MOUNT/'fep-ideas/formal-checks/fep-factor-revision-v1/attempt-01'
PRIOR_SHA = '1666bab83fe475199da13b7e7c254fd230a583c7558cc4af989d747e868421a4'
CODE_SHA = '208835070d8032dfceb6fa05bde2d63c36b95013eb165531387e91aa5384d880'
REPORT_SHA = '33dc81cb3bbb954cb08830908fe0184160941e801e9005b48d602e7d54ba57ed'
CAP, H, PRICE = 64, 100, F(1, 1000)
METHODS = ('adaptive_edit', 'adaptive_average', 'adaptive_independent', 'adaptive_joint')
OLD = ('edit', 'model_average', 'independent', 'joint_from_start')
TRUTHS = {'independent': (72,18,8,2), 'shared': (80,10,0,10),
          'partial': (76,14,4,6), 'anticorrelated': (70,20,10,0),
          'marginal_shift': (56,14,24,6)}
FACT = [factorial(k) for k in range(2*CAP+3)]
BIN3 = [comb(k, 3) if k >= 3 else 0 for k in range(CAP+5)]
ACTS = tuple(tuple(code//(3**y) % 3 for y in range(4)) for code in range(81))
UNITS = tuple(tuple(sum(1 if d[e if w == 0 else 3-e] == 2 else
                       10*int(d[e if w == 0 else 3-e] != w) for w in (0,1))
                    for e in range(4)) for d in ACTS)
COUNTS, MAX_ERROR, TOL = Counter(), 0.0, 1e-10


def check(group, label, condition):
    if not condition:
        raise AssertionError((group, label))
    COUNTS[group] += 1


def close(group, label, x, y):
    global MAX_ERROR
    error = abs(float(x)-float(y))
    MAX_ERROR = max(MAX_ERROR, error)
    check(group, label, error <= TOL)


def encode(x):
    if isinstance(x, F):
        return dict(exact=str(x), value=float(x))
    if isinstance(x, dict):
        return {str(k): encode(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [encode(v) for v in x]
    return x


def write(path, data):
    path.write_text(json.dumps(encode(data), indent=2, sort_keys=True)+'\n')


def identity(path):
    data = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(data), sha256=sha256(data).hexdigest())


def counts(n):
    for a in range(n+1):
        for b in range(n-a+1):
            for c in range(n-a-b+1):
                yield (a,b,c,n-a-b-c)


def index(n, a, b, c):
    return BIN3[n+3]-BIN3[n-a+3]+b*(n-a+1)-b*(b-1)//2+c


def children(n, c):
    a,b,d,_ = c
    return (index(n+1,a+1,b,d), index(n+1,a,b+1,d),
            index(n+1,a,b,d+1), index(n+1,a,b,d))


def evidence_weights(c, scale):
    n, a, b = sum(c), c[2]+c[3], c[1]+c[3]
    num0 = scale*FACT[a]*FACT[n-a]*FACT[b]*FACT[n-b]
    den0 = FACT[n+1]**2
    num1, den1 = scale, 4**n*FACT[n+1]
    for k in c:
        num1 *= FACT[2*k]
        den1 *= FACT[k]
    w0, rem0 = divmod(num0, den0)
    w1, rem1 = divmod(num1, den1)
    check('integer likelihood', 'common denominator exact', rem0 == rem1 == 0)
    return w0, w1


def layer(n, scale):
    w0, w1 = [], []
    for c in counts(n):
        a,b = evidence_weights(c, scale)
        w0.append(a)
        w1.append(b)
    return w0, w1


def program(v):
    return sum(((0 if v[y] > v[3-y] else 1)
                if 10*min(v[y],v[3-y]) < v[y]+v[3-y] else 2)*3**y
               for y in range(4))


def plan(cap, ledger=None, logline=lambda text: None):
    scale = 4**(cap+1)*FACT[cap+2]**2
    next0, next1 = layer(cap+1, scale)
    next_values = None
    masks, codes = [None]*(cap+1), [None]*(cap+1)
    fixed = [cap*w for w in (10*scale,10*scale,scale,scale)]
    root_info, states, tie_counts = None, 0, [0]*4
    for n in range(cap,-1,-1):
        w0,w1 = layer(n, scale)
        length = len(w0)
        values = [[0]*length for _ in METHODS]
        masks[n], codes[n] = bytearray(length), bytearray(4*length)
        for i,c in enumerate(counts(n)):
            child = children(n,c)
            v0, v1 = tuple(next0[k] for k in child), tuple(next1[k] for k in child)
            check('predictive', 'two likelihood martingales', sum(v0) == w0[i] and sum(v1) == w1[i])
            mix = tuple(9*x+y for x,y in zip(v0,v1))
            joined = w1[i] > 9*w0[i]
            deployment = (v1 if joined else v0, mix, v0, v1)
            forecasts = (mix,mix,v0,v1)
            weights = (9*w0[i]+w1[i],9*w0[i]+w1[i],w0[i],w1[i])
            programs = tuple(program(v) for v in deployment)
            stop, more, mask, ties = [], [], 16*joined, 0
            for j,(pred,w,d) in enumerate(zip(forecasts,weights,programs)):
                s = 5000*sum(p*l for p,l in zip(pred,UNITS[d]))
                cont = None if n == cap else w+sum(next_values[j][k] for k in child)
                buy = cont is not None and cont < s
                value = cont if buy else s
                values[j][i] = value
                codes[n][4*i+j] = d
                mask |= int(buy) << j
                if cont == s:
                    ties |= 1 << j
                    tie_counts[j] += 1
                stop.append(s)
                more.append(cont)
                check('Bellman', 'nonnegative value and finite stop bound', 0 <= value <= s <= H*1000*w)
                if cont is not None:
                    check('Bellman', 'continuation bound and tie stopping', value <= cont and (cont != s or not buy))
                if n == cap:
                    multiplicity = FACT[n]
                    for k in c:
                        multiplicity //= FACT[k]
                    fixed[j] += multiplicity*s
            masks[n][i] = mask
            check('Bellman', 'model averaging dominates MAP under common belief', values[1][i] <= values[0][i])
            if ledger is not None:
                ledger.write(json.dumps([n,*c,mask,ties,list(programs),
                    [s/(1000*w) for s,w in zip(stop,weights)],
                    [None if a is None else a/(1000*w) for a,w in zip(more,weights)]],separators=(',',':'))+'\n')
            if n == 0:
                root_info = {m:dict(value=F(values[j][0],1000*weights[j]),
                             stop_value=F(stop[j],1000*weights[j]),
                             continue_value=F(more[j],1000*weights[j]) if more[j] is not None else None,
                             buys=bool(mask & (1 << j)),
                             fixed_cap_prior_value=F(fixed[j],1000*weights[j]))
                             for j,m in enumerate(METHODS)}
                for j in range(4):
                    check('Bellman', 'root no worse than fixed-cap policy', values[j][0] <= fixed[j])
            states += 1
        next0,next1,next_values = w0,w1,values
        if n == cap or n % 16 == 0:
            logline(f'Planned through remaining layer n={n}; {states} count states')
    check('scope', 'complete lattice', states == comb(cap+4,4))
    return dict(cap=cap,masks=masks,codes=codes,root=root_info,states=states,ties=tie_counts)


def physical(q, code):
    wrong,ask = 0,0
    d = ACTS[code]
    for w in (0,1):
        for e,p in enumerate(q):
            a = d[e if w == 0 else 3-e]
            wrong += p*int(a != 2 and a != w)
            ask += p*int(a == 2)
    return wrong,ask


def evaluate(policy, reference, ledger=None, logline=lambda text: None):
    cap, denominator = policy['cap'],100**policy['cap']
    result, stop_rows = {},0
    for label,q in TRUTHS.items():
        current = [[denominator] for _ in METHODS]
        stops = [[0]*(cap+1) for _ in METHODS]
        wrong,asks,bought,joins = [0]*4,[0]*4,[0]*4,[0]*4
        logloss = [0.0]*4
        physics = [physical(q,code) for code in range(81)]
        oracle = min(10*err+ask for err,ask in physics)
        for n in range(cap+1):
            following = [[0]*comb(n+4,3) for _ in METHODS] if n < cap else None
            for i,c in enumerate(counts(n)):
                if not any(current[j][i] for j in range(4)):
                    continue
                mask, child, predictions = policy['masks'][n][i],None,None
                for j,m in enumerate(METHODS):
                    mass = current[j][i]
                    if not mass:
                        continue
                    if mask & (1 << j):
                        check('stopping', 'no extra calibration and integer propagation', n < cap and mass % 100 == 0)
                        bought[j] += mass
                        if child is None:
                            child = children(n,c)
                        for e,k in enumerate(child):
                            following[j][k] += mass*q[e]//100
                    else:
                        stops[j][n] += mass
                        code = policy['codes'][n][4*i+j]
                        err,ask = physics[code]
                        check('physical', 'known-Q lower bound', 10*err+ask >= oracle)
                        wrong[j] += mass*err
                        asks[j] += mass*ask
                        joins[j] += mass*bool(mask & 16)
                        if predictions is None:
                            old = reference.fit(c)['vectors']
                            predictions = (old[1],old[3],old[0],old[2])
                        v = predictions[j]
                        check('deployment', 'frozen and planned task table agree', ACTS[code] == reference.policy(v))
                        nll = -fsum(p*(log(x)-log(sum(v))) for p,x in zip(q,v))/100
                        logloss[j] += (mass/denominator)*nll
                        if ledger is not None:
                            ledger.write(json.dumps([label,j,n,*c,str(mass),code,nll],separators=(',',':'))+'\n')
                        stop_rows += 1
            current = following
        rows = {}
        for j,m in enumerate(METHODS):
            check('stopping', 'exact total stop probability', sum(stops[j]) == denominator)
            count_sum = sum(n*mass for n,mass in enumerate(stops[j]))
            check('stopping', 'charged every actual observation', count_sum == bought[j])
            expected_n = F(count_sum,denominator)
            err,ask = F(wrong[j],200*denominator),F(asks[j],200*denominator)
            raw = err+ask/10
            rows[m] = dict(expected_calibrations=expected_n, stop_distribution=[F(x,denominator) for x in stops[j]],
                           cap_probability=F(stops[j][-1],denominator), zero_probability=F(stops[j][0],denominator),
                           terminal_MAP_join_probability=F(joins[j],denominator) if j == 0 else None,
                           wrong_probability=err, ask_probability=ask, raw_loss=raw,
                           net_loss=raw+PRICE*expected_n/H, calibration_cost_per_task=PRICE*expected_n/H,
                           predictive_log_loss=logloss[j])
        result[label] = dict(methods=rows, oracle_loss=F(oracle,2000), always_ask_loss=F(1,10),
                             follow_A_loss=F(q[2]+q[3],100))
        logline('Evaluated actual stopping paths for '+label)
    return result,stop_rows


def qualify(reference):
    start = perf_counter()
    scale = 4**4*FACT[5]**2
    for n in range(5):
        child_map = {c:i for i,c in enumerate(counts(n+1))}
        for i,c in enumerate(counts(n)):
            check('qualification', 'count index', index(n,*c[:3]) == i)
            expected = tuple(child_map[tuple(k+int(e == t) for t,k in enumerate(c))] for e in range(4))
            check('qualification', 'child indices', children(n,c) == expected)
            weights = evidence_weights(c,scale)
            check('qualification', 'evidence integral matches frozen checker',
                  tuple(F(w,scale) for w in weights) == reference.evidence(c))
            old = reference.fit(c)
            for v in old['vectors']:
                check('qualification', 'task table matches frozen checker', ACTS[program(v)] == reference.policy(v))
            ev = reference.evidence(c)
            norm = 9*ev[0]/10+ev[1]/10
            posterior = (9*ev[0]/(10*norm),ev[1]/(10*norm))
            free = fsum(float(p)*log(float(p/(prior*e))) for p,prior,e in zip(posterior,(F(9,10),F(1,10)),ev))
            close('VFE', 'structural posterior equality', free,-log(float(norm)))
            for v in old['vectors']:
                for y in range(4):
                    p = (F(v[y],v[y]+v[3-y]),F(v[3-y],v[y]+v[3-y]))
                    free = fsum(float(x)*log(float(x/F(v[t],2*sum(v)))) for x,t in zip(p,(y,3-y)))
                    close('VFE', 'world posterior equality', free,-log(float(F(v[y]+v[3-y],2*sum(v)))))
    root = reference.fit((0,0,0,0))['vectors']
    for e in range(4):
        c = tuple(int(t == e) for t in range(4))
        check('myopic', 'one observation cannot change MAP deployment', reference.policy(reference.fit(c)['vectors'][1]) == (2,2,2,2))
    check('myopic', 'initial deployment asks everywhere', reference.policy(root[1]) == (2,2,2,2))
    toy = plan(3)
    def ordered_value(c,j,future_tasks=100):
        old = reference.fit(c)['vectors']
        deployment = (old[1],old[3],old[0],old[2])[j]
        forecast = (old[3],old[3],old[0],old[2])[j]
        p = tuple(F(v,sum(forecast)) for v in forecast)
        actions = reference.policy(deployment)
        stop = F(0)
        for w,e in product((0,1),range(4)):
            a = actions[e if w == 0 else 3-e]
            stop += future_tasks*p[e]/2*(F(1,10) if a == 2 else int(a != w))
        if sum(c) == 3:
            return stop,False
        more = PRICE+sum(p[e]*ordered_value(tuple(x+int(e == t) for t,x in enumerate(c)),j,future_tasks)[0] for e in range(4))
        return (more,True) if more < stop else (stop,False)
    for j,m in enumerate(METHODS):
        value,buy = ordered_value((0,0,0,0),j)
        check('qualification', 'ordered recursive/count Bellman root', value == toy['root'][m]['value'] and buy == toy['root'][m]['buys'])
        check('no use', 'zero future tasks stop', ordered_value((0,0,0,0),j,0) == (0,False))
    def direct_paths(pol,q,j):
        total,paid,err,ask = F(0),F(0),F(0),F(0)
        def walk(c,p):
            nonlocal total,paid,err,ask
            n,i = sum(c),index(sum(c),*c[:3])
            if pol['masks'][n][i] & (1 << j):
                for e in range(4):
                    walk(tuple(x+int(t == e) for t,x in enumerate(c)),p*F(q[e],100))
            else:
                total += p
                paid += n*p
                actions = ACTS[pol['codes'][n][4*i+j]]
                for w,e in product((0,1),range(4)):
                    a = actions[e if w == 0 else 3-e]
                    err += p*F(q[e],200)*int(a != 2 and a != w)
                    ask += p*F(q[e],200)*int(a == 2)
        walk((0,0,0,0),F(1))
        return total,paid,err,ask
    for label,pol in [('optimized',toy),('outcome-dependent',dict(toy,masks=[bytearray(x) for x in toy['masks']]))]:
        if label == 'outcome-dependent':
            for n in range(4):
                for i,c in enumerate(counts(n)):
                    go = n == 0 or (n == 1 and c[0] == 0)
                    pol['masks'][n][i] = (pol['masks'][n][i] & 16)+(15 if go else 0)
        evaluated,_ = evaluate(pol,reference)
        for truth,q in TRUTHS.items():
            for j,m in enumerate(METHODS):
                total,n,err,ask = direct_paths(pol,q,j)
                row = evaluated[truth]['methods'][m]
                check('qualification', label+' ordered stopped paths', total == 1 and n == row['expected_calibrations'] and err == row['wrong_probability'] and ask == row['ask_probability'])
                if label == 'outcome-dependent':
                    check('qualification', 'known outcome-dependent stopping count', n == 2-F(q[0],100))
    check('price boundary', 'one pair alone exceeds all avoidable initial loss', 11 > H*F(1,10))
    return dict(checks=sum(COUNTS.values()),groups=dict(COUNTS),max_residual=MAX_ERROR,
                wall_seconds=perf_counter()-start, ordered_check_cap=3,
                myopic_initial_buys=False,myopic_initial_value=F(10),
                myopic_one_pair_value=F(10001,1000), expensive_pair_cost=11,
                expensive_initial_rejection='nonnegative future losses; pair cost 11 exceeds always-ask loss 10')


def run(output):
    if not MOUNT.is_mount() or not output.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError('Verified external FEP mount required')
    output.mkdir(parents=True,exist_ok=False)
    (output/'inputs').mkdir()
    start,cpu,started = perf_counter(),process_time(),datetime.now(timezone.utc).isoformat()
    inputs,preserved = [],[]
    source = Path(__file__).resolve().parent
    def logline(s):
        with (output/'RUN_LOG.txt').open('a') as out:
            out.write(s+'\n')
        print(s,flush=True)
    try:
        logline('Started '+started+'; one process; exact integer planning and stopping laws')
        check('integrity','previous manifest hash',identity(PRIOR/'MANIFEST.json')['sha256'] == PRIOR_SHA)
        check('integrity','frozen reference code',identity(source/'check_fep_factor_revision.py')['sha256'] == CODE_SHA)
        check('integrity','previous report',identity(source/'FEP_FACTOR_REVISION_V1_REPORT.md')['sha256'] == REPORT_SHA)
        previous = json.loads((PRIOR/'MANIFEST.json').read_text())
        unique = {e['path']:e for group in ('inputs','outputs','preserved') for e in previous[group]}
        for e in unique.values():
            check('integrity','preserve '+e['path'],identity(Path(e['path'])) == e)
            preserved.append(e)
        originals = [source/'FEP_ADAPTIVE_CALIBRATION_V1.md',Path(__file__).resolve(),
                     source/'FEP_FACTOR_REVISION_V1.md',source/'check_fep_factor_revision.py',
                     source/'FEP_FACTOR_REVISION_V1_REPORT.md',PRIOR/'RESULTS.json',PRIOR/'MANIFEST.json']
        for path in originals:
            e = identity(path)
            inputs.append(e)
            shutil.copyfile(path,output/'inputs'/path.name)
            check('integrity','snapshot '+path.name,identity(output/'inputs'/path.name)['sha256'] == e['sha256'])
        write(output/'PREPARATION.json',dict(inputs=inputs,preserved=preserved,cap=CAP,H=H,pair_price=PRICE,
              truths=TRUTHS,methods=METHODS,prior_model_probabilities=[F(9,10),F(1,10)],
              bellman_columns=['n','c00','c01','c10','c11','mask: four continue bits, bit4 MAP join',
                               'four exact tie bits','four terminal codes','four stop costs','four continuation costs'],
              terminal_columns=['truth','method index','n','c00','c01','c10','c11','exact mass numerator','terminal code','future log loss'],
              terminal_mass_denominator=str(100**CAP),binary64_identity_tolerance=TOL,
              declaration='No outcome tuning; same cap, costs, priors and fixed truth panel'))
        module_spec = importlib.util.spec_from_file_location('frozen_factor_reference',source/'check_fep_factor_revision.py')
        reference = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(reference)
        check('scope','prior constants unchanged', reference.H == H and reference.PRICE == PRICE and reference.TRUTHS == TRUTHS)
        logline('Source snapshots and preparation sealed before qualification')
        qualification = qualify(reference)
        write(output/'QUALIFICATION.json',qualification)
        logline(f'Qualification passed: {qualification["checks"]} checks in {qualification["wall_seconds"]:.3f}s')
        with gzip.open(output/'BELLMAN.jsonl.gz','wt',encoding='utf-8') as ledger:
            policy = plan(CAP,ledger,logline)
        logline('All acquisition policies frozen before fixed-truth stopping evaluation')
        with gzip.open(output/'STOPPED.jsonl.gz','wt',encoding='utf-8') as ledger:
            evaluated,stop_rows = evaluate(policy,reference,ledger,logline)
        old = json.loads((output/'inputs/RESULTS.json').read_text())['budgets']['64']
        for truth,row in evaluated.items():
            row['fixed_64'] = {m:old[truth]['methods'][old_name] for m,old_name in zip(METHODS,OLD)}
            row['myopic_edit'] = dict(expected_calibrations=F(0),raw_loss=F(1,10),net_loss=F(1,10),
                                      wrong_probability=F(0),ask_probability=F(1),predictive_log_loss=log(4))
        aggregate = {m:{key:sum(evaluated[t]['methods'][m][key] for t in ('independent','shared'))/2
                         for key in ('expected_calibrations','raw_loss','net_loss','predictive_log_loss')}
                     for m in METHODS}
        fixed_aggregate = {m:sum(F(old[t]['methods'][old_name]['net_loss']['exact']) for t in ('independent','shared'))/2
                           for m,old_name in zip(METHODS,OLD)}
        primary = aggregate['adaptive_edit']
        gates = dict(shared_pays=evaluated['shared']['methods']['adaptive_edit']['net_loss'] < F(1,10),
                     aggregate_pays=primary['net_loss'] < F(1,10),
                     shared_uses_calibration=evaluated['shared']['methods']['adaptive_edit']['expected_calibrations'] > 0,
                     aggregate_uses_calibration=primary['expected_calibrations'] > 0)
        efficiency = dict(aggregate_no_worse_than_fixed=primary['net_loss'] <= fixed_aggregate['adaptive_edit'],
                          fewer_calibrations=primary['expected_calibrations'] < CAP)
        for e in inputs+preserved:
            check('integrity','unchanged '+e['path'],identity(Path(e['path'])) == e)
        summary = dict(checks=sum(COUNTS.values()),groups=dict(COUNTS),max_binary64_identity_residual=MAX_ERROR,
                       count_states=policy['states'], extra_predictive_layer=comb(CAP+4,3), stopped_ledger_rows=stop_rows,
                       exact_ties=dict(zip(METHODS,policy['ties'])),functional_gates=gates,functional_pass=all(gates.values()),
                       efficiency_gates=efficiency,efficiency_pass=all(efficiency.values()),myopic_initial_buys=False,
                       lookahead_initial_buys=policy['root']['adaptive_edit']['buys'],
                       stopped_mass_is_multinomial=False, FEP_unique_advantage_tested=False)
        write(output/'RESULTS.json',dict(summary=summary,root_prior_predictions=policy['root'],
              truths=evaluated,primary_equal_truth_aggregate=aggregate,fixed_64_equal_truth_aggregate=fixed_aggregate))
        wall,cpu_seconds,finished = perf_counter()-start,process_time()-cpu,datetime.now(timezone.utc).isoformat()
        logline(f'COMPLETE: functional={summary["functional_pass"]}; efficiency={summary["efficiency_pass"]}; {wall:.3f}s wall')
        outputs = [identity(p) for p in sorted(output.rglob('*')) if p.is_file()]
        write(output/'MANIFEST.json',dict(status='complete',started_utc=started,finished_utc=finished,
              wall_seconds=wall,cpu_seconds=cpu_seconds,python=platform.python_version(),processes=1,
              inputs=inputs,outputs=outputs,preserved=preserved,summary=summary))
    except Exception:
        logline(traceback.format_exc())
        write(output/'FAILURE.json',dict(status='failed',inputs=inputs,preserved=preserved,
              checks=sum(COUNTS.values()),groups=dict(COUNTS),wall_seconds=perf_counter()-start))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
