"""Post-hoc linear decomposition of the actual first captured injured body.

No alternative body, repair, or receiving trajectory is simulated.
"""
import math
import os
from pathlib import Path
import time
import traceback

import numpy as np

import common as c
import design
import diagnose_first_rewrite as d


DESTINATION = c.ROOT/'diagnostics/fill_decomposition_v1'


def projection(field, target):
    vector = (field*target).mean(axis=(1, 2))
    scalar = np.asarray([math.fsum(float(x)*float(y) for x, y in zip(a.flat, b.flat))/256
                         for a, b in zip(field, target)])
    assert np.max(np.abs(vector-scalar)) <= 2e-13
    return scalar


def summarize(rows):
    groups = {}
    for family in design.FAMILIES:
        groups[family] = {}
        for group in d.STRATA:
            selected = [r for r in rows if r['family'] == family and r['injury_stratum'] == group]
            fields = [k for k in rows[0] if k not in ('block', 'future', 'family', 'world', 'injury_stratum')]
            groups[family][group] = dict(n=len(selected), **{key: d.average(r[key] for r in selected) for key in fields})
    return dict(classification='POST_HOC_INJURY_FILL_DECOMPOSITION', families=groups,
        new_dynamics=0, counterfactual_receiving_assays=0, unique_causal_mechanism_established=False)


def main():
    os.nice(10); tick = time.monotonic()
    DESTINATION.mkdir(parents=True, exist_ok=False)
    c.write_json(DESTINATION/'RUNNING.json', dict(started_utc=c.now(),
        scope='Decompose retained body, fixed replacement fill and original jitter in saved R0',
        selected_after_first_rewrite_strata_inspection=True, new_dynamics=0))
    try:
        first = c.ROOT/'diagnostics/first_rewrite_v1'
        receipt = c.read_json(first/'COMPLETE.json'); assert receipt['status'] == 'PASS'
        c.verify(receipt['outputs']); bound = c.read_json(first/'INPUTS.json')
        frozen = c.read_json(c.ROOT/'FREEZE.json')
        assert c.runtime_hashes() == frozen['inputs']
        inputs = dict(frozen['inputs'])
        for path in (Path(__file__).resolve(), Path(d.__file__).resolve(), first/'COMPLETE.json', first/'INPUTS.json'):
            inputs[str(path)] = c.sha(path)
        cfg, _ = design.configs('development')
        rows = []; tissues = {}
        for index in c.BLOCKS:
            ctx = c.model.source.context(index, cfg)
            codes = ctx['codes'][np.arange(16)//4]
            tissues[index] = dict(resting=ctx['tissue'].resting, copy_jitter=ctx['tissue'].copy_jitter)
            for future in range(4):
                for family in design.FAMILIES:
                    path = d.ORIGINAL/f'tissue_{index}'/f'future_{future:02d}'/family/'capture'
                    loaded = {}
                    for name in ('g01_develop.npz', 'g01_boundary.npz', 'g01_repair.npz'):
                        p = path/name; assert c.sha(p) == bound[str(p)]; inputs[str(p)] = bound[str(p)]
                        loaded[name] = c.arrays(p)
                    developed = loaded['g01_develop.npz']['s1000_V']
                    fresh = loaded['g01_boundary.npz']['fresh']
                    actual = loaded['g01_repair.npz']['s0_R']
                    c.ref.exact(actual, loaded['g01_boundary.npz']['injured_V'])
                    retained = np.where(fresh, 0., developed)
                    fill = np.where(fresh, ctx['tissue'].resting, 0.)
                    jitter = actual-(retained+fill)
                    values = {name: projection(field, codes) for name, field in (
                        ('captured_own_projection', actual), ('retained_body_contribution', retained),
                        ('replacement_fill_contribution', fill), ('jitter_contribution', jitter))}
                    assert np.max(np.abs(values['captured_own_projection']-sum(values[k] for k in
                        ('retained_body_contribution', 'replacement_fill_contribution', 'jitter_contribution')))) <= 2e-13
                    values['fill_retained_axis_projection'] = projection(fill, np.where(fresh, -1., 1.))
                    assert np.max(np.abs(values['fill_retained_axis_projection']+ctx['tissue'].resting/2)) <= 2e-13
                    values['captured_fresh_cell_mean'] = (actual*fresh).sum(axis=(1, 2))/128
                    target = np.tanh(actual)
                    values['writer_target_own_projection'] = projection(target, codes)
                    values['writer_target_fresh_contribution'] = projection(np.where(fresh, target, 0.), codes)
                    values['writer_target_retained_contribution'] = projection(np.where(fresh, 0., target), codes)
                    assert np.max(np.abs(values['writer_target_own_projection']-values['writer_target_fresh_contribution']-
                                          values['writer_target_retained_contribution'])) <= 2e-13
                    groups = d.geometry(fresh, codes)
                    for i in range(16):
                        rows.append(dict(block=index, future=future, family=family, world=i,
                            injury_stratum=groups[i], **{key: float(v[i]) for key, v in values.items()}))
        assert len(rows) == 512
        c.verify(inputs); c.write_json(DESTINATION/'INPUTS.json', inputs)
        c.write_json(DESTINATION/'ROWS.json', rows)
        summary = summarize(rows); summary['tissues'] = tissues
        c.write_json(DESTINATION/'SUMMARY.json', summary)
        repeated = summarize(c.read_json(DESTINATION/'ROWS.json')); repeated['tissues'] = tissues
        assert c.serialized(repeated) == (DESTINATION/'SUMMARY.json').read_bytes()
        c.verify(inputs)
        c.write_json(DESTINATION/'COMPLETE.json', dict(status='PASS', completed_utc=c.now(), seconds=time.monotonic()-tick,
            inputs=len(inputs), rows=len(rows), outputs={str(p):c.sha(p) for p in sorted(DESTINATION.iterdir()) if p.is_file()},
            source_outputs_unchanged=True, post_hoc=True, new_dynamics=0, counterfactual_receiving_assays=0,
            scalar_projection_check=True, additive_decomposition_check=True, fill_axis_identity_check=True,
            summary_reproduction_check=True))
        print(c.serialized(summary).decode())
    except BaseException as error:
        c.write_json(DESTINATION/'FAILED.json', dict(failed_utc=c.now(), error=repr(error), traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    main()
