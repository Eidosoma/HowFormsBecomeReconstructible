"""Serial cue-sensitive capture with ordinary coactivity at exact-zero cue products."""
from dataclasses import replace
import hashlib
from common import rng
from E031_renewal_durability import model as previous
import numpy as np

base, acquisition, renewal = previous.base, previous.acquisition, previous.renewal
CFG, Cycle, CYCLE = previous.CFG, previous.Cycle, previous.CYCLE
CYCLE = replace(CYCLE, generations=32)
PORTS, RULES, CUES = previous.PORTS, previous.RULES, previous.CUES
ARMS, DAMAGE, RECEIVERS = previous.ARMS, previous.DAMAGE, previous.RECEIVERS
CONDITIONS = ('standard_preserve', 'standard_rewrite', 'bridge_preserve', 'bridge_rewrite',
              'contrast_preserve', 'bridge_read_blocked', 'bridge_write_blocked',
              'protected_copy', 'masked_copy')
ACTIVE = tuple(range(7))
HORIZONS = (0, 1, 3, 8, 16, 24, 32)
PANELS = tuple((h, c, r) for h in HORIZONS for r in RECEIVERS
               for c in (('initial',) if h == 0 else CONDITIONS))
PAIRS = tuple(('bridge_preserve', c) for c in CONDITIONS if c != 'bridge_preserve')+(
    ('standard_rewrite', 'standard_preserve'), ('bridge_rewrite', 'standard_rewrite'),
    ('bridge_rewrite', 'bridge_preserve'), ('contrast_preserve', 'standard_preserve'))


def terminal_cycle(cycle):
    assert cycle.generations == 32 and 4*cycle.settling_steps < cycle.read_steps
    return replace(cycle, settling_steps=4*cycle.settling_steps)


def capture(body, beta):
    assert body.shape[0] == 7 and body.shape[3:] == (2, 16, 16)
    standard = base.correlations(body, beta).mean(axis=3)
    x = np.tanh(beta*body)
    cue = (x[:, :, :, 0]-x[:, :, :, 1])/2
    contrast = np.stack((cue*np.roll(cue, -1, -1), cue*np.roll(cue, -1, -2)), axis=-3)
    selected = standard.copy()
    bridge = np.where(contrast != 0, contrast, standard)
    selected[[2, 3, 5, 6]] = bridge[[2, 3, 5, 6]]
    selected[4] = contrast[4]
    return base.encode(selected)


def select(incoming, computed, available):
    old, fresh = base.decode(incoming), base.decode(computed)
    retained = np.zeros_like(available)
    for n in (0, 2, 4, 5, 6):
        retained[n] = available[n] & (abs(old[n]) > .5)
    eligible = available & ~retained
    outgoing = np.where(retained, old, np.where(eligible, fresh, 0.))
    return base.encode(outgoing), retained, eligible


def replace_record(incoming, block, generation, cfg=CFG, cycle=CYCLE):
    assert incoming.shape == (9, 4, cfg.recipients, 4096)
    assert 1 <= generation <= cycle.generations == 32
    delayed = terminal_cycle(cycle).settling_steps
    mask = base.damage_masks(block, f'E022_renewal_g{generation}', cfg)[:, :, 1]
    masks = np.repeat(mask[None], 7, axis=0)
    available = renewal.surviving_edges(masks)
    physical = base.encode(base.decode(incoming[:7])*available)
    reading = physical.copy(); reading[5] = 0
    denominators = renewal.incident_sum(abs(base.decode(reading)))
    weights = base.decode(reading)[:, :, :, None]
    stream = rng('E022', block, 'develop', generation)
    birth = cfg.birth_sd*base.paired_founders(stream.standard_normal((2, cfg.recipients, 16, 16)))
    v = np.broadcast_to(birth[None, :, :, None], (7, 4, cfg.recipients, 2, 16, 16)).copy()
    alive = (~masks)[:, :, :, None]; cue = CUES.reshape(1, 1, 1, 2, 1)
    v *= alive; v[..., PORTS[0]] = cue
    late = []
    for t in range(cycle.read_steps):
        noise = base.paired_founders(stream.standard_normal((2, cfg.recipients, 16, 16)))[None, :, :, None]
        v = renewal.compensated_step(v, weights, denominators[:, :, :, None],
                                     noise, cfg, amplification=t >= delayed)
        v *= alive; v[..., PORTS[0]] = cue
        if t >= cycle.read_steps-cfg.observe_steps:
            late.append(np.stack((v[..., PORTS[1]].mean(axis=-1), v[..., PORTS[2]].mean(axis=-1)), axis=-1))
    developed = v.copy()
    erased = reading.copy(); erased.fill(0)
    computed = capture(developed, cfg.writer_beta)
    assert not (base.decode(computed)*(~available)).any()
    stream = rng('E022', block, 'write', generation)
    hashes = np.empty((cycle.write_steps, 7, 32), dtype=np.uint8)
    scaffold = available[:, :, :, None].astype(float)
    for t in range(cycle.write_steps):
        noise = base.paired_founders(stream.standard_normal((2, cfg.recipients, 16, 16)))[None, :, :, None]
        v = base.step(v, scaffold, 2., noise, cfg)
        v *= alive; v[..., PORTS[0]] = cue
        for n in ACTIVE:
            hashes[t, n] = np.frombuffer(hashlib.sha256(np.ascontiguousarray(v[n], dtype='<f8').tobytes()).digest(), np.uint8)
    outgoing = incoming.copy()
    outgoing[:7], retained, eligible = select(physical, computed, available)
    outgoing[6] = 0
    outgoing[8] = base.encode(base.decode(incoming[8])*available[0])
    return dict(incoming=incoming.copy(), renewal_mask=mask, body_masks=masks, retained_packets=physical,
        read_packets=reading, erased_packets=erased, birth=birth, read_denominators=denominators,
        developed_end=developed, developed_late_ports=np.stack(late), computed_packets=computed,
        write_state_hashes=hashes, write_end=v, retained_edges=retained, eligible_edges=eligible, outgoing=outgoing)


def assay(records, block, horizon, cfg=CFG, cycle=CYCLE):
    return previous.assay(records, block, horizon, cfg, terminal_cycle(cycle))


def body_score(mean, cfg=CFG):
    target = RULES[None, :, None, None]*CUES[None, None, None]
    a, b = target*mean[..., 0], -target*mean[..., 1]
    return (a > cfg.margin) & (b > cfg.margin), np.minimum(a, b), mean
