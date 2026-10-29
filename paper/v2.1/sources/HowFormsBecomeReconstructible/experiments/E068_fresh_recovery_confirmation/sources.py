"""Generate every source anew, independently replaying the E065 history."""
import time
import numpy as np
from common import dump, utc
from E065_fresh_compatibility_confirmation import source_model, source_audit
from E068_fresh_recovery_confirmation import data


def generate(run, block, cfg):
    start = time.monotonic()
    timings = {}
    mode, R = cfg['mode'], cfg['recipients']
    config = source_model.base.Config(**cfg['source_config'])
    controls = dict(acquisition_replayed=True, ancestry_replayed=True,
        source_continuation_replayed=True, source_ports_protected=True, source_injury_count=True)
    def elapsed(name, t):
        timings[name] = timings.get(name, 0.) + time.monotonic() - t
    def add(prefix, values):
        for name, value in values.items():
            timings[prefix + '_' + name] = timings.get(prefix + '_' + name, 0.) + value
    def progress(stage, generation=0):
        dump(run / f'progress_{block}.json', dict(block=block, stage=stage,
            generation_verified=generation, utc=utc()))
    def archive_projection(name, arrays):
        if mode != 'scientific':
            data.equal(arrays, data.reference(mode, name))
    progress('acquisition')
    t = time.monotonic()
    acquired = source_model.reader.acquisition.teach(block, config)
    elapsed('production_acquisition', t)
    t = time.monotonic()
    data.save(run / f'acquisition_{block:06d}.npz', acquired)
    elapsed('production_source_storage', t)
    t = time.monotonic()
    audited, _ = source_audit.source_record(acquired, block, cfg['source_config'])
    elapsed('audit_acquisition', t)
    archive_projection('acquisition_900041.npz', acquired)
    packets = acquired['acquired'][1, :, None].repeat(R, axis=1)[None]
    replay = audited[:, None].repeat(R, axis=1)[None]
    data.equal(dict(packets=packets), dict(packets=replay))
    for g in range(1, 33):
        raw, timing = source_model.rebuild(packets, block, g, config, cfg['source_cycle'], 'E022')
        add('production_ancestry', timing)
        t = time.monotonic()
        data.save(run / f'source_boundary_{block:06d}_g{g}.npz', raw)
        elapsed('production_source_storage', t)
        other, timing = source_audit.rebuild(replay, block, g, cfg['source_config'], cfg['source_cycle'], 'E022')
        add('audit_ancestry', timing)
        data.equal(raw, other)
        archive_projection(f'source_boundary_900041_g{g}.npz', raw)
        controls['source_ports_protected'] &= not raw['masks'][..., source_model.P.any(axis=0)].any()
        controls['source_injury_count'] &= (raw['masks'].sum(axis=(-2, -1)) == 24).all()
        packets, replay = raw['outgoing'].copy(), other['outgoing'].copy()
        progress('ancestry', g)
    t = time.monotonic()
    body, outgoing = source_model.perturb(packets, block, cfg['body'])
    elapsed('production_pulse', t)
    t = time.monotonic()
    data.save(run / f'body_{block:06d}.npz', body)
    data.save(run / f'outgoing_{block:06d}.npz', outgoing)
    elapsed('production_source_storage', t)
    t = time.monotonic()
    body2, outgoing2 = source_audit.perturb(replay, block, cfg['body'])
    elapsed('audit_pulse', t)
    data.equal(body, body2)
    data.equal(outgoing, outgoing2)
    archive_projection('body_900041.npz', body)
    archive_projection('outgoing_900041.npz', outgoing)
    controls.update(before_equal=np.array_equal(body['states'][:, 0, 0], body['states'][:, 1, 0]),
        pulse_ports_protected=not body['pulse_sites'][..., source_model.P.any(axis=0)].any(),
        pulse_living_only=not (body['pulse_sites'] & body['masks']).any(),
        pulse_site_count=(body['pulse_sites'].sum(axis=(-2, -1)) == cfg['body']['pulse_sites']).all())
    initial = outgoing['packets'].copy()
    packets, replay = initial.copy(), outgoing2['packets'].copy()
    for g in range(1, 4):
        raw, timing = source_model.rebuild(packets, block, g, config, cfg['source_continuation'], 'E058')
        add('production_source_continuation', timing)
        t = time.monotonic()
        data.save(run / f'source_continuation_{block:06d}_g{g}.npz', raw)
        elapsed('production_source_storage', t)
        other, timing = source_audit.rebuild(replay, block, g, cfg['source_config'], cfg['source_continuation'], 'E058')
        add('audit_source_continuation', timing)
        data.equal(raw, other)
        archive_projection(f'continuation_900041_g{g}.npz', raw)
        controls['source_ports_protected'] &= not raw['masks'][..., source_model.P.any(axis=0)].any()
        controls['source_injury_count'] &= (raw['masks'].sum(axis=(-2, -1)) == 24).all()
        packets, replay = raw['outgoing'].copy(), other['outgoing'].copy()
        progress('source_continuation', g)
    source = dict(initial=initial, final=packets)
    if mode != 'scientific':
        data.equal(source, data.technical_source(mode))
    source_seconds = time.monotonic() - start
    timings['source_other_static'] = max(0., source_seconds - sum(timings.values()))
    controls = {k: bool(v) for k, v in controls.items()}
    assert all(controls.values()), controls
    progress('recovery_rewrites')
    return source, controls, timings
