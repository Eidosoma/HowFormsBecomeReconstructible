"""Fixed serial schedules and completely checked current-record-only repair."""
import math
import time
import numpy as np
import native as n
import optimizer as opt
import optimizer_audit as oa
import repair
import support as s

FIELDS = ('signs', 'candidate_costs', 'flips', 'final_improvable_nodes', 'cost',
          'initial_cost', 'winner', 'sweeps', 'selected_improvable_nodes')


def identity(block, cfg):
    s.require(block in cfg['blocks'], 'No cohort substitution')
    return cfg['lineage_namespace']+':'+str(block)


def writer_code(generation, history, cfg):
    s.require(1 <= generation <= 14 and history in range(4), 'Preliminary writer schedule')
    return int(generation in cfg['tolerance_generations'][history])


def schedule(generation):
    s.require(15 <= generation <= 32, 'Fixed continuation horizon')
    return [False, generation == 15, True, True]*2


def prepare(incoming, block, generation, cfg):
    s.require(incoming.shape == (8, 16, 4096) and incoming.dtype == np.uint8, 'Every incoming record')
    weights = n.decode(incoming)
    prepared = weights.copy()
    active = schedule(generation)
    details = dict(applied=np.repeat(np.array(active)[:, None], 16, axis=1),
                   missing_edges=(weights == 0).sum(axis=(-2, -1)),
                   added_edges=np.zeros((8, 16), int), added_abs_weight=np.zeros((8, 16)),
                   magnitude=np.zeros((8, 16)), shuffle_changes=np.zeros((8, 16), int),
                   repair_cpu_seconds=np.zeros((8, 16)), audit_cpu_seconds=np.zeros((8, 16)))
    diagnostics, calls, maximum_error = {}, 0, 0.
    for vi, applied in enumerate(active):
        if not applied:
            continue
        for case in range(16):
            outgoing = weights[vi, case]
            missing = np.flatnonzero(outgoing.ravel() == 0.)
            start = time.process_time()
            completed, solution, magnitude = repair.recipient(outgoing, cfg['optimizer'])
            details['repair_cpu_seconds'][vi, case] = time.process_time()-start
            start = time.process_time()
            coupling = oa.independent_coupling(outgoing.reshape(2, 16, 16))
            s.equal(coupling.ravel(), opt.coupling(outgoing), 'Independent recipient coupling')
            reference = oa.solve(coupling, opt.INPUT_PINS, cfg['optimizer'])
            for key in FIELDS:
                s.equal(np.asarray(solution[key]), np.asarray(reference[key]), 'Independent optimizer '+key)
                value = np.asarray(solution[key])
                if key not in diagnostics:
                    diagnostics[key] = np.zeros((8, 16)+value.shape, value.dtype)
                diagnostics[key][vi, case] = value
            observed = abs(outgoing[outgoing != 0.])
            median = float(np.median(observed)) if len(observed) else 0.
            s.require(magnitude == median, 'Independent median')
            nodes = reference['signs']
            signs = np.stack((nodes*np.roll(nodes, -1, -1), nodes*np.roll(nodes, -1, -2))).ravel()
            expected = outgoing.copy().ravel()
            for edge in missing:
                if median > 0:
                    expected[edge] = median*int(signs[edge])
            s.equal(completed, expected.reshape(2, 256), 'Independent completion')
            value = completed.copy().ravel()
            if vi % 4 == 3:
                order = n.random_stream(cfg['shuffle_namespace'], block, generation, case//4, case % 4).permutation(len(missing))
                value = outgoing.copy().ravel()
                if magnitude > 0:
                    value[missing] = completed.ravel()[missing[order]]
                shuffled = outgoing.copy().ravel()
                for i, edge in enumerate(missing):
                    if median > 0:
                        shuffled[edge] = median*int(signs[missing[int(order[i])]])
                s.equal(value, shuffled, 'Independent shuffled construction')
                s.equal(abs(value), abs(completed.ravel()), 'Own-input shuffle magnitudes')
                s.equal(np.sort(value[missing]), np.sort(completed.ravel()[missing]), 'Added sign multiset')
                details['shuffle_changes'][vi, case] = int((value[missing] != completed.ravel()[missing]).sum())
            s.equal(value[outgoing.ravel() != 0], outgoing.ravel()[outgoing.ravel() != 0], 'Observed edges preserved')
            prepared[vi, case] = value.reshape(2, 256)
            details['magnitude'][vi, case] = magnitude
            details['added_edges'][vi, case] = np.count_nonzero(value[missing])
            total = float(abs(value[missing]).sum())
            scalar = math.fsum(abs(float(v)) for v in value[missing])
            error = abs(total-scalar)
            s.require(error <= 8*np.finfo(float).eps*abs(scalar)+4*np.nextafter(0., 1.), 'Fixed resource sum bound')
            maximum_error = max(maximum_error, error)
            details['added_abs_weight'][vi, case] = total
            details['audit_cpu_seconds'][vi, case] = time.process_time()-start
            calls += 1
    details.update({'optimizer_'+k: v for k, v in diagnostics.items()})
    details.update(independent_optimizer_checks=np.array(calls), resource_max_error=np.array(maximum_error))
    packets = n.encode(prepared)
    for vi, applied in enumerate(active):
        if not applied:
            s.equal(packets[vi], incoming[vi], 'Inactive branch untouched')
    if generation == 15:
        for offset in (0, 4):
            s.equal(packets[offset+1], packets[offset+2], 'First one-time/repeated preparation')
        for vi in range(4):
            s.equal(packets[vi], packets[vi+4], 'Initial preparation paired across noise')
    return packets, details
