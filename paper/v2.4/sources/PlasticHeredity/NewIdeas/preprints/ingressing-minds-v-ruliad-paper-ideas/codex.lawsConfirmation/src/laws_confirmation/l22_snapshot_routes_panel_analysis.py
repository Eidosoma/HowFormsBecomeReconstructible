"""Fixed four-block D192 aggregation; no fitting or outcome selection."""

import numpy as np

from . import l22_snapshot_routes_panel_block as block

BLOCKS, FUTURES, METRICS, TOL = block.model.BLOCKS, block.FUTURES, block.METRICS, block.TOL


def stream(data, parents, draws):
    if set(data) != set(BLOCKS): raise ValueError('all four fixed blocks required')
    matrices, values = {}, {}
    for index in BLOCKS:
        rows, ds = data[index]
        block.statistics(rows, ds)
        assert len(rows['common__B1W1']) == 4*parents
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

    contrasts = {}
    for name, coefficients in block.model.comparisons().items():
        v = sum(w*matrices[n] for n, w in coefficients.items())
        d = sum(w*values[n] for n, w in coefficients.items())
        grouped = d.reshape(4, 4, parents, draws, 3)
        contrasts[name] = dict(coefficients=coefficients, **means(v), per_record=v.tolist(),
            per_draw_behavior=d.tolist(), transitions=dict(pooled=transition(d),
                by_block=[transition(a) for a in d],
                by_message=[transition(grouped[:, m]) for m in range(4)],
                by_block_message=[[transition(a) for a in b] for b in grouped]))
    result = dict(schema='d192_four_block_stream_v1', blocks=list(BLOCKS), records=16*parents,
        parents_per_message=parents, reader_draws=draws, fields=list(METRICS), draw_fields=list(METRICS[:3]),
        arms={n: means(v) for n, v in matrices.items()}, contrasts=contrasts,
        pooling_unit='equal_block', new_founders=0, confirmatory=False, fitted_models=0, serial_renewal=False)
    block.checker().panel_stream(data, result, parents, draws)
    return result


def aggregate(data, parents=4, draws=4):
    if set(data) != set(BLOCKS): raise ValueError('retain all four registered blocks and exclude the benchmark')
    if type(parents) is not int or type(draws) is not int or min(parents, draws) < 1:
        raise ValueError('positive integer counts required')
    for i in BLOCKS: block.summary(data[i], i)
    result = dict(schema='d192_snapshot_routes_panel_v1', blocks=list(BLOCKS), futures=list(FUTURES),
        records=16*parents, records_per_block=4*parents, reader_draws_per_future=draws,
        new_draws_per_record=2*draws, named_reads=280, repair_paths=104, body_free_paths=8,
        comparisons=54, native_saved_bridges=48, held_fixed_bridges=8,
        new_founders=0, source_regenerated=False, benchmark_excluded=True, old_outcomes_pooled=False,
        confirmatory=False, fitted_models=0, serial_renewal=False, uncertainty_interval=None,
        pooling_unit='equal_block_equal_future',
        by_future={f: stream({i: data[i][f] for i in BLOCKS}, parents, draws) for f in FUTURES},
        new_only=stream({i: block.pool(data[i]) for i in BLOCKS}, parents, 2*draws))
    block.checker().panel_summary(data, result, parents, draws)
    return result


def load_blocks(directory):
    return {i: block.load_futures(directory/f'tissue_{i}') for i in BLOCKS}
