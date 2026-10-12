"""Production continuation using qualified roll-based equations and fixed pairing."""
import numpy as np
import roll_dynamics as d
import support as s


def noise_pair(z, innovation, rhos):
    correlations = list(dict.fromkeys(rhos))
    second = {rho: z.copy() if rho == 1. else rho*z + np.sqrt(1.-rho*rho)*innovation
              for rho in correlations}
    first = d.paired_founders(z)
    draws = np.stack([np.stack((first, d.paired_founders(second[rho])), axis=2) for rho in rhos])
    moments = np.array([[z.sum(), y.sum(), (z*z).sum(), (y*y).sum(), (z*y).sum(), z.size]
                        for y in second.values()])
    return draws, moments


def mechanism(body, mask, previous_mask, beta):
    x = np.tanh(beta*body)
    difference = (x[:, :, :, 0]-x[:, :, :, 1])/2
    q = np.stack((difference*np.roll(difference, -1, -1), difference*np.roll(difference, -1, -2)), axis=-3)
    available = d.available_edges(mask)
    returning = previous_mask.reshape(4, 4, 16, 16) & ~mask
    incident = np.stack((returning | np.roll(returning, -1, -1),
                         returning | np.roll(returning, -1, -2)), axis=-3) & available
    shape = (len(body), 16)
    return dict(available_edges=np.broadcast_to(available, q.shape).sum(axis=(-3, -2, -1)).reshape(shape),
                fallback_edges=((q == 0) & available).sum(axis=(-3, -2, -1)).reshape(shape),
                returning_edges=np.broadcast_to(incident, q.shape).sum(axis=(-3, -2, -1)).reshape(shape),
                returning_fallback_edges=((q == 0) & incident).sum(axis=(-3, -2, -1)).reshape(shape))


def rebuild(packets, previous_mask, identity, generation, cfg, rhos=None):
    rhos = cfg['variant_correlations'] if rhos is None else rhos
    B = len(rhos)
    s.require(packets.shape == (B, 16, 4096), 'Complete production continuation panel')
    dc, cycle = cfg['development_config'], cfg['cycle']
    masks = d.damage_masks(identity, f'E022_renewal_g{generation}', 4)[:, :, 1]
    weights = d.decode(packets.reshape(B, 4, 4, 4096))*d.available_edges(masks)
    denominator = d.incident(abs(weights))
    base = d.stream('E022', identity, 'develop', generation)
    innovation = d.stream(cfg['innovation_namespace'], identity, 'innovation', generation)
    shape = (2, 4, 16, 16)
    birth = dc['birth_sd']*d.matched_cues(base.standard_normal(shape))
    innovation.standard_normal(shape)
    value = np.repeat(birth[None], B, axis=0)
    alive = (~masks)[None, :, :, None]
    cue = d.CUES.reshape(1, 1, 1, 2, 1)
    value *= alive
    value[..., d.PORTS[0]] = cue
    late, moments = [], np.zeros((len(set(rhos)), 6))
    for step in range(cycle['read_steps']):
        noise, sums = noise_pair(base.standard_normal(shape), innovation.standard_normal(shape), rhos)
        moments += sums
        value = d.step(value, weights[:, :, :, None], denominator[:, :, :, None], noise, dc,
                       step >= cycle['settling_steps'])
        value *= alive
        value[..., d.PORTS[0]] = cue
        if step >= cycle['read_steps']-dc['observe_steps']:
            late.append(d.read_ports(value))
    outgoing, _ = d.capture(value, masks, ['exact_rewrite']*B, dc, cfg['tolerance'])
    windows = np.stack(late).reshape(dc['observe_steps'], B, 16, 2, 2)
    return dict(masks=masks.reshape(16, 16, 16), birth=birth.reshape(16, 2, 16, 16),
                end=value.reshape(B, 16, 2, 16, 16), outgoing=outgoing.reshape(B, 16, 4096),
                port_windows=windows, mean_ports=windows.mean(axis=0), noise_moments=moments,
                **mechanism(value, masks, previous_mask, dc['writer_beta']))


def score(ports):
    target = np.repeat([1., -1., 1., -1.], 4)[:, None, None]*np.array([[1., -1.], [-1., 1.]])
    aligned = ports*target
    minimum, opposite = aligned.min(axis=(-2, -1)), -aligned.max(axis=(-2, -1))
    return dict(min_margin=minimum, both_pass=minimum > .25,
                opposite_margin=opposite, opposite_pass=opposite > .25)
