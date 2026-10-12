"""Two matched generation-nine readings with the unchanged selective writer."""
from dataclasses import replace
import hashlib
from common import rng
from E031_renewal_durability import model as policy, evidence
import numpy as np

base, renewal = policy.base, policy.renewal
CFG, Cycle = policy.CFG, policy.Cycle
PORTS, RULES, CUES = policy.PORTS.copy(), policy.RULES.copy(), policy.CUES.copy()
ARMS, DAMAGE, RECEIVERS = policy.ARMS, policy.DAMAGE, policy.RECEIVERS
CONDITIONS = ('original', 'delayed')
TIMINGS = ('original', 'delayed')
GENERATION = 9
PANELS = tuple((t, r, c) for t in TIMINGS for r in RECEIVERS for c in CONDITIONS)


def schedules(cycle, factor=4):
    assert factor in (2, 4) and factor*cycle.settling_steps < cycle.read_steps
    return cycle, replace(cycle, settling_steps=factor*cycle.settling_steps)


def boundary(incoming, block, cfg, cycle, factor):
    assert incoming.shape == (4, cfg.recipients, 4096)
    mask = base.damage_masks(block, 'E022_renewal_g9', cfg)[:, :, 1]
    masks = np.repeat(mask[None], 2, axis=0)
    available = renewal.surviving_edges(masks)
    packets = base.encode(base.decode(incoming)[None]*available)
    retained_packets, saved_packets = packets.copy(), packets.copy()
    weights = base.decode(packets)[:, :, :, None]
    denominator = renewal.incident_sum(abs(base.decode(packets)))
    stream = rng('E022', block, 'develop', GENERATION)
    birth = cfg.birth_sd*base.paired_founders(stream.standard_normal((2, cfg.recipients, 16, 16)))
    v = np.broadcast_to(birth[None, :, :, None], (2, 4, cfg.recipients, 2, 16, 16)).copy()
    active = (~masks)[:, :, :, None]
    cue = CUES.reshape(1, 1, 2, 1)
    v *= active
    v[..., PORTS[0]] = cue[None]
    trace = []
    clocks = schedules(cycle, factor)
    for t in range(cycle.read_steps):
        noise = base.paired_founders(stream.standard_normal((2, cfg.recipients, 16, 16)))[:, :, None]
        for branch, clock in enumerate(clocks):
            v[branch] = renewal.compensated_step(v[branch], weights[branch], denominator[branch, :, :, None],
                                               noise, cfg, amplification=t >= clock.settling_steps)
        v *= active
        v[..., PORTS[0]] = cue[None]
        if t >= cycle.read_steps-cfg.observe_steps:
            trace.append(np.stack((v[..., PORTS[1]].mean(axis=-1), v[..., PORTS[2]].mean(axis=-1)), axis=-1))
    developed_end = v.copy()
    packets.fill(0)
    computed = renewal.capture_from_activity(v, cfg)
    stream = rng('E022', block, 'write', GENERATION)
    scaffold = available[:, :, :, None].astype(float)
    hashes = np.empty((cycle.write_steps, 2, 32), np.uint8)
    for t in range(cycle.write_steps):
        noise = base.paired_founders(stream.standard_normal((2, cfg.recipients, 16, 16)))[None, :, :, None]
        v = base.step(v, scaffold, 2., noise, cfg)
        v *= active
        v[..., PORTS[0]] = cue[None]
        for branch in range(2):
            hashes[t, branch] = np.frombuffer(hashlib.sha256(np.ascontiguousarray(v[branch], dtype='<f8').tobytes()).digest(), np.uint8)
    outgoing, retained, eligible = policy.selective_packet(retained_packets, computed, available)
    return dict(incoming=incoming.copy(), read_packets=saved_packets, erased_packets=packets,
                retained_packets=retained_packets, retained_edges=retained, eligible_edges=eligible,
                outgoing=outgoing, renewal_mask=mask, body_masks=masks, birth=birth,
                read_denominators=denominator, developed_end=developed_end,
                developed_late_ports=np.stack(trace), write_state_hashes=hashes,
                write_end=v, computed_packets=computed)


def check_original(raw, source):
    np.testing.assert_array_equal(raw['renewal_mask'], source['renewal_mask'])
    for k in ('outgoing', 'retained_edges', 'eligible_edges'):
        np.testing.assert_array_equal(raw[k][0], source[k][0])
    np.testing.assert_array_equal(raw['write_state_hashes'][:, 0], source['write_state_hashes'][:, 0])
    np.testing.assert_array_equal(raw['developed_late_ports'].mean(axis=0)[0], source['developed_mean_ports'][0])


def body_score(mean_ports, cfg):
    desired = RULES[None, :, None, None]*CUES[None, None, None, :]
    a, b = desired*mean_ports[..., 0], -desired*mean_ports[..., 1]
    return (a > cfg.margin) & (b > cfg.margin), np.minimum(a, b), mean_ports


def assay(records, block, cfg, cycle):
    return policy.assay(records, block, GENERATION, cfg, cycle)


def score(mean_ports, cfg):
    return evidence.score_mean(mean_ports, cfg, RULES, CUES)
