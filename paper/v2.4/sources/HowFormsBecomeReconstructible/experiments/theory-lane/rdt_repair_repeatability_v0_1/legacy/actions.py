"""One current-packet repair; no task, history, injury or future in its API."""
import time
import numpy as np
from study import C, e, repair, optimizer, audit_optimizer, digest, require


def checked_repair(packet):
    before = packet.copy()
    start = time.process_time()
    fixed, solution, magnitude = repair.recipient_repair(packet, C['optimizer'])
    repair_cpu = time.process_time() - start
    start = time.process_time()
    coupling = audit_optimizer.independent_coupling(before)
    require(coupling.tobytes() == (optimizer.influence(before) * np.sign(before)).tobytes(), 'Repair coupling mismatch')
    independent = audit_optimizer.solve(coupling, np.flatnonzero(e.PORTS[0].ravel()), C['optimizer'])
    for name in ('signs', 'candidate_costs', 'flips', 'final_improvable_nodes'):
        require(np.asarray(solution[name]).tobytes() == np.asarray(independent[name]).tobytes(), 'Independent optimizer mismatch: ' + name)
    for name in ('cost', 'initial_cost', 'winner', 'sweeps', 'selected_improvable_nodes'):
        require(solution[name] == independent[name], 'Independent optimizer value: ' + name)
    observed = before != 0
    values = sorted(abs(float(w)) for w in before.ravel() if w != 0)
    count = len(values)
    mid = (values[count // 2] if count % 2 else (values[count // 2 - 1] + values[count // 2]) / 2) if count else 0.
    require(mid == magnitude, 'Independent imputed magnitude mismatch')
    expected = before.copy()
    signs = independent['signs']
    if mid > 0:
        for plane in range(2):
            for y in range(16):
                for x in range(16):
                    if before[plane, y, x] == 0:
                        neighbor = signs[y, (x + 1) % 16] if plane == 0 else signs[(y + 1) % 16, x]
                        expected[plane, y, x] = mid * int(signs[y, x]) * int(neighbor)
    require(packet.tobytes() == before.tobytes(), 'Repair mutated the original packet')
    require(fixed.tobytes() == expected.tobytes(), 'Independent repair construction mismatch')
    require(fixed[observed].tobytes() == before[observed].tobytes(), 'Repair changed observed weights')
    require(np.isfinite(fixed).all(), 'Nonfinite repair')
    audit_cpu = time.process_time() - start
    stats = dict(repair_calls=1, repair_cpu_seconds=repair_cpu, optimizer_audit_cpu_seconds=audit_cpu,
        incoming_sha256=digest(before), repaired_sha256=digest(fixed), observed_edges=int(observed.sum()),
        added_edges=int(np.count_nonzero(fixed[~observed])), added_absolute_weight=float(abs(fixed[~observed]).sum()),
        imputed_magnitude=float(magnitude), cost=float(solution['cost']), sweeps=int(solution['sweeps']),
        winner=int(solution['winner']), independent_check=True)
    saved = {name: np.asarray(solution[name]) for name in ('signs', 'candidate_costs', 'flips', 'final_improvable_nodes')}
    return fixed, stats, saved


def prepare(rows, packets):
    require(len(rows) == len(packets), 'Repair enrollment mismatch')
    result, receipts, raw = [], [], []
    for row, packet in zip(rows, packets, strict=True):
        require(digest(packet) == row['packet_sha256'], 'Repair starts from wrong enrolled packet')
        fixed, stats, details = checked_repair(packet)
        result.append(np.stack((packet, fixed)))
        receipts.append(dict(key=row['key'], **stats))
        raw.append(details)
    return np.stack(result), receipts, {name: np.stack([r[name] for r in raw]) for name in raw[0]}
