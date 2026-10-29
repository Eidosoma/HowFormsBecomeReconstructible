"""New source IDs through unchanged E065/E068 ancestry and E077 recovery."""
import time
import numpy as np
from E081_fresh_strength_pattern import sources as genealogy
from E077_fresh_reconstruction_tradeoff import model as old, audit_model as audit
from E068_fresh_recovery_confirmation.model import intervene as mix
from E068_fresh_recovery_confirmation.audit_model import intervene as mix_audit
from E083_reader_repeatability.data import save, equal


def generate(run, task, cfg):
    src_cfg = cfg['source']
    # The inherited mode flag gates only comparison with old archive 900041.
    # New excluded IDs retain their actual short schedules but skip that lookup.
    ancestry, controls, timings = genealogy.generate(run, task, dict(src_cfg, mode='scientific'))
    tick = time.monotonic()
    save(run/f'ancestry_{task:06d}.npz', ancestry)
    inter = mix(ancestry); equal(inter, mix_audit(ancestry))
    save(run/f'source_mixture_{task:06d}.npz', inter)
    timings['source_mixture_static'] = time.monotonic()-tick
    tick = time.monotonic()
    first = old.rebuild(inter['packets'], task, 0, src_cfg['config'], src_cfg['source_recovery_cycle'])
    other = audit.rebuild(inter['packets'], task, 0, src_cfg['config'], src_cfg['source_recovery_cycle'])
    equal(first, other)
    timings['source_recovery_both'] = time.monotonic()-tick
    tick = time.monotonic()
    save(run/f'source_recovery_{task:06d}.npz', first)
    pruning = old.intervene(first); equal(pruning, audit.intervene(first))
    save(run/f'source_pruning_{task:06d}.npz', pruning)
    w, e = old.base.decode(pruning['packets']), pruning['eligible']
    assert pruning['packets'].shape == (9,4,cfg['recipients'],4096)
    assert w[:4][~e].tobytes() == w[4:8][~e].tobytes()
    assert (w[:4][e] != 0).all() and not w[4:8][e].any()
    for f in (0,2): assert pruning['packets'][8,f].tobytes() == pruning['packets'][8,f+1].tobytes()
    timings['source_pruning_static'] = time.monotonic()-tick
    controls.update(first_recovery_replayed=True, pruning_replayed=True, source_unchanged_outside_selection=True,
                    erased_founder_pairs_exact=True)
    assert all(controls.values())
    return pruning, controls, timings
