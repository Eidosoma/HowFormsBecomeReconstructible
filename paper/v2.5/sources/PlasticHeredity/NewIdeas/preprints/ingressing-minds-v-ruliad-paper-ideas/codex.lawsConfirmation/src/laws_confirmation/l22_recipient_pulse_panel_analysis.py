"""Fixed four-block D195 aggregation; no fitting or outcome selection."""

import numpy as np

from . import l22_recipient_pulse_panel_block as block

BLOCKS, FUTURES, METRICS, TOL = block.model.BLOCKS, block.FUTURES, block.METRICS, block.TOL
ROLES = block.ROLES


def stream(data, parents, draws):
    if set(data) != set(BLOCKS): raise ValueError('all four fixed blocks required')
    matrices, values = {}, {}
    for index in BLOCKS:
        rows, ds = data[index]
        block.statistics(rows, ds)
        assert len(rows['common__A__LL']) == 4*parents
        assert all(d.shape == (4*parents, draws, 3) for d in ds.values())
    for name in block.packet_names():
        matrices[name] = np.array([[[r[k] for k in METRICS] for r in data[i][0][name]] for i in BLOCKS])
        values[name] = np.array([data[i][1][name] for i in BLOCKS])

    def means(v):
        by_block = v.mean(axis=1)
        grouped = v.reshape(4, 4, parents, 7).mean(axis=2)
        dictionary = lambda a: dict(zip(METRICS, a.tolist()))
        return dict(mean=dictionary(by_block.mean(axis=0)), by_block=[dictionary(a) for a in by_block],
            by_message=[dictionary(a) for a in grouped.mean(axis=0)],
            by_block_message=[[dictionary(a) for a in b] for b in grouped],
            leave_one_block_out=[dictionary(np.delete(by_block, i, axis=0).mean(axis=0)) for i in range(4)])

    def count(v):
        return dict(n=int(v.size), improved=int(np.sum(v > TOL)), worsened=int(np.sum(v < -TOL)),
            tied=int(np.sum(np.abs(v) <= TOL)), net=float(v.mean()),
            positive=float(np.maximum(v, 0).mean()), negative=float(np.minimum(v, 0).mean()))

    def transition(v):
        a = v.reshape(-1, draws, 3)
        return {k: dict(records=count(a[:, :, j].mean(axis=1)), draws=count(a[:, :, j]))
                for j, k in enumerate(METRICS[:3])}

    def aggregate_view(vv, dd):
        contrasts = {}
        for name, coefficients in block.model.comparisons().items():
            v = sum(w*vv[n] for n, w in coefficients.items())
            d = sum(w*dd[n] for n, w in coefficients.items())
            grouped = d.reshape(4, 4, parents, draws, 3)
            contrasts[name] = dict(coefficients=coefficients, **means(v), per_record=v.tolist(),
                per_draw_behavior=d.tolist(), transitions=dict(pooled=transition(d),
                    by_block=[transition(a) for a in d],
                    by_message=[transition(grouped[:, m]) for m in range(4)],
                    by_block_message=[[transition(a) for a in b] for b in grouped]))
        return dict(arms={n: means(v) for n, v in vv.items()}, contrasts=contrasts)

    base = tuple(block.model.plan())+block.packet_names()[-5:]
    role_values, role_draws = {}, {}
    for role in ROLES:
        mapping = {n: n.replace('__', '__'+role+'__', 1) if n in block.model.plan() else n for n in base}
        role_values[role] = {n: matrices[actual] for n, actual in mapping.items()}
        role_draws[role] = {n: values[actual] for n, actual in mapping.items()}
    averaged_values = {n: .5*(role_values['A'][n]+role_values['B'][n]) for n in base}
    averaged_draws = {n: .5*(role_draws['A'][n]+role_draws['B'][n]) for n in base}
    result = dict(schema='d195_four_block_stream_v1', blocks=list(BLOCKS), records=16*parents,
        parents_per_message=parents, reader_draws=draws, fields=list(METRICS), draw_fields=list(METRICS[:3]),
        roles=list(ROLES), named_arms={n: means(v) for n, v in matrices.items()},
        by_role={s: aggregate_view(role_values[s], role_draws[s]) for s in ROLES},
        role_mean=aggregate_view(averaged_values, averaged_draws),
        role_pooling='within_record_and_paired_draw', pooling_unit='equal_block',
        new_founders=0, confirmatory=False, fitted_models=0, serial_renewal=False)
    block.checker().panel_stream(data, result, parents, draws)
    return result


def aggregate(data, parents=4, draws=4):
    if set(data) != set(BLOCKS): raise ValueError('retain all four registered blocks and exclude the benchmark')
    if type(parents) is not int or type(draws) is not int or min(parents, draws) < 1:
        raise ValueError('positive integer counts required')
    for i in BLOCKS: block.summary(data[i], i)
    result = dict(schema='d195_recipient_pulse_panel_v1', blocks=list(BLOCKS), futures=list(FUTURES),
        records=16*parents, records_per_block=4*parents, reader_draws_per_future=draws,
        new_draws_per_record=2*draws, named_reads=296, repair_paths=128, body_free_paths=32,
        comparisons=32, own_trace_bridges=16, donor_paths=16, roles=list(ROLES),
        pooled_recorded_writer_identity_is_structural=True,
        new_founders=0, source_regenerated=False, benchmark_excluded=True, old_outcomes_pooled=False,
        confirmatory=False, fitted_models=0, serial_renewal=False, uncertainty_interval=None,
        pooling_unit='equal_block_equal_future_equal_role',
        by_future={f: stream({i: data[i][f] for i in BLOCKS}, parents, draws) for f in FUTURES},
        new_only=stream({i: block.pool(data[i]) for i in BLOCKS}, parents, 2*draws))
    block.checker().panel_summary(data, result, parents, draws)
    return result


def load_blocks(directory):
    return {i: block.load_futures(directory/f'tissue_{i}') for i in BLOCKS}
